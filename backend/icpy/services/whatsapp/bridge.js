/**
 * WhatsApp Bridge for icotes
 * 
 * Node.js process that manages the WhatsApp connection via Baileys.
 * Communicates with the Python backend via stdin/stdout JSON messages.
 * 
 * Protocol:
 *   Python → Node: JSON lines on stdin  (commands)
 *   Node → Python: JSON lines on stdout (events)
 *   Logs go to stderr (not captured as messages)
 * 
 * Message types:
 *   Inbound events (Node → Python):
 *     { type: "qr",         data: { qr: "<base64_png>" } }
 *     { type: "connected",  data: { jid: "...", name: "..." } }
 *     { type: "disconnected", data: { reason: "..." } }
 *     { type: "message",    data: { from, text, isGroup, sender, mentions, messageId, quotedText } }
 *     { type: "error",      data: { message: "..." } }
 *     { type: "ready",      data: {} }
 * 
 *   Outbound commands (Python → Node):
 *     { type: "send",       data: { jid: "...", text: "..." } }
 *     { type: "send_media", data: { jid: "...", path: "...", caption: "...", mediaType: "image"|"video"|"audio"|"document" } }
 *     { type: "typing",     data: { jid: "..." } }
 *     { type: "stop",       data: {} }
 */

import makeWASocket, {
  DisconnectReason,
  useMultiFileAuthState,
  extractMessageContent,
  getContentType,
  isJidGroup,
  downloadMediaMessage,
} from '@whiskeysockets/baileys'
import { Boom } from '@hapi/boom'
import pino from 'pino'
import QRCode from 'qrcode'
import qrcodeTerminal from 'qrcode-terminal'
import NodeCache from 'node-cache'
import fs from 'fs'
import path from 'path'
import { fileURLToPath } from 'url'
import readline from 'readline'

// ─── Configuration ──────────────────────────────────────────

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const AUTH_DIR = process.env.WA_AUTH_DIR || path.join(__dirname, 'auth_store')
const BOT_NAME = process.env.WA_BOT_NAME || 'icotes'
const LOG_LEVEL = process.env.WA_LOG_LEVEL || 'error'

// Logger writes to stderr so stdout is reserved for JSON protocol
const logger = pino({ level: LOG_LEVEL }, pino.destination(2))

// Group metadata cache (5-minute TTL)
const groupCache = new NodeCache({ stdTTL: 300 })

/** Current socket instance */
let sock = null

/** Bot's LID (Linked Identity) — needed for group mention matching */
let selfLid = null

/** Tracks if we're intentionally shutting down */
let isShuttingDown = false

/** Grace period after connection — ignore messages for 5 seconds */
let connectionTimestamp = 0
const GRACE_PERIOD_MS = 5000

// ─── Protocol helpers ───────────────────────────────────────

/**
 * Send a JSON event to the Python backend via stdout
 */
function emit(type, data = {}) {
  const msg = JSON.stringify({ type, data })
  process.stdout.write(msg + '\n')
}

/**
 * Log to stderr (visible in Python process logs but not captured as events)
 */
function log(level, ...args) {
  process.stderr.write(`[WA-Bridge] [${level}] ${args.join(' ')}\n`)
}

// ─── Message extraction ─────────────────────────────────────

/**
 * Extract text content from a WhatsApp message
 */
function extractText(msg) {
  const content = extractMessageContent(msg.message)
  if (!content) return ''

  const type = getContentType(content)
  if (!type) return ''

  const inner = content[type]

  switch (type) {
    case 'conversation':
      return content.conversation || ''
    case 'extendedTextMessage':
      return inner?.text || ''
    case 'imageMessage':
    case 'videoMessage':
    case 'documentMessage':
      return inner?.caption || ''
    default:
      return typeof inner === 'string' ? inner : inner?.text || inner?.caption || ''
  }
}

/**
 * Extract mentioned JIDs from a message
 */
function extractMentions(msg) {
  const content = extractMessageContent(msg.message)
  if (!content) return []

  const jids = []
  const type = getContentType(content)
  if (!type) return []

  const inner = content[type]
  const contextInfo = inner?.contextInfo

  if (contextInfo?.mentionedJid) {
    jids.push(...contextInfo.mentionedJid)
  }

  return [...new Set(jids)]
}

/**
 * Extract reply context if the message is a reply
 */
function extractReplyContext(msg) {
  const content = extractMessageContent(msg.message)
  if (!content) return null

  const type = getContentType(content)
  if (!type) return null

  const contextInfo = content[type]?.contextInfo
  if (!contextInfo?.quotedMessage) return null

  const quotedText = contextInfo.quotedMessage.conversation
    || contextInfo.quotedMessage?.extendedTextMessage?.text
    || '[media]'

  return {
    quotedText,
    quotedSender: contextInfo.participant || contextInfo.remoteJid || 'unknown',
  }
}

/**
 * Convert a JID to E164 phone format
 */
function jidToE164(jid) {
  if (!jid) return null
  if (jid.endsWith('@g.us') || jid.endsWith('@lid') || jid === 'status@broadcast') return null
  const number = jid.split(/[:@]/)[0]
  if (!number || !/^\d+$/.test(number)) return null
  return `+${number}`
}

/**
 * Check if the bot was mentioned in a group message
 */
function isBotMentioned(msg, selfJid, selfPhone, aliases = []) {
  const mentions = extractMentions(msg)
  const selfNumber = selfJid?.split(/[:@]/)[0]
  const selfLidNumber = selfLid?.split(/[:@]/)[0]

  log('debug', `Mention check: selfNumber=${selfNumber}, selfLid=${selfLid}, mentions=${JSON.stringify(mentions)}`)

  // Check JID-based mentions (phone JID or LID)
  for (const jid of mentions) {
    const mentionNumber = jid.split(/[:@]/)[0]
    // Match against phone number
    if (selfNumber && mentionNumber === selfNumber) return true
    // Match against LID number
    if (selfLidNumber && mentionNumber === selfLidNumber) return true
    // Match full LID JID
    if (selfLid && jid === selfLid) return true
  }

  // Check text-based mentions (fallback — WhatsApp may use display name)
  const text = extractText(msg).toLowerCase()
  if (selfNumber && text.includes(`@${selfNumber}`)) return true

  // Check bot name and aliases in text (e.g. "@Icotes")
  const botNameLower = BOT_NAME.toLowerCase()
  if (text.includes(`@${botNameLower}`)) return true

  for (const alias of aliases) {
    if (text.includes(`@${alias.toLowerCase()}`)) return true
  }

  log('debug', `Bot not mentioned in: "${text.slice(0, 80)}"`)
  return false
}

// ─── Socket creation & lifecycle ────────────────────────────

/**
 * Create and start a new WhatsApp socket connection
 */
async function startSocket() {
  // Clean up previous socket to prevent connectionReplaced conflicts
  if (sock) {
    try {
      sock.ev.removeAllListeners()
      sock.end(undefined)
    } catch {}
    sock = null
  }

  // Ensure auth directory exists
  fs.mkdirSync(AUTH_DIR, { recursive: true })

  const { state, saveCreds } = await useMultiFileAuthState(AUTH_DIR)

  sock = makeWASocket({
    auth: state,
    browser: ['Icotes', 'Chrome', '22.04.4'],
    logger,
    printQRInTerminal: false,
    syncFullHistory: false,
    generateHighQualityLinkPreview: false,
    markOnlineOnConnect: true,
  })

  // Save credentials on update
  sock.ev.on('creds.update', saveCreds)

  // Connection state changes
  sock.ev.on('connection.update', async ({ connection, lastDisconnect, qr }) => {
    if (qr) {
      log('info', 'QR code received, generating PNG...')

      // Print QR to terminal (stderr) for direct scanning
      qrcodeTerminal.generate(qr, { small: true }, (qrStr) => {
        process.stderr.write('\n' + qrStr + '\n')
        process.stderr.write('Scan this QR code with WhatsApp > Linked Devices > Link a Device\n\n')
      })

      try {
        const qrBase64 = await QRCode.toDataURL(qr, { width: 256, margin: 2 })
        emit('qr', { qr: qrBase64 })
      } catch (err) {
        log('error', 'Failed to generate QR PNG:', err.message)
        emit('qr', { qr: null, raw: qr })
      }
    }

    if (connection === 'open') {
      connectionTimestamp = Date.now()
      const selfJid = sock.user?.id || 'unknown'
      const selfName = sock.user?.name || BOT_NAME
      selfLid = sock.user?.lid || null
      log('info', `Connected as ${selfName} (${selfJid}), LID: ${selfLid}`)
      emit('connected', { jid: selfJid, name: selfName, lid: selfLid })
    }

    if (connection === 'close') {
      const boom = lastDisconnect?.error
      const statusCode = boom instanceof Boom ? boom.output?.statusCode : boom?.output?.statusCode
      const reason = DisconnectReason[statusCode] || `unknown (${statusCode})`

      log('info', `Disconnected: ${reason} (code: ${statusCode})`)
      emit('disconnected', { reason, statusCode })

      if (isShuttingDown) {
        log('info', 'Shutting down, not reconnecting')
        return
      }

      // Don't reconnect on these terminal/expected disconnect reasons
      if (statusCode === DisconnectReason.loggedOut) {
        log('warn', 'Logged out — clearing credentials and stopping')
        try {
          fs.rmSync(AUTH_DIR, { recursive: true, force: true })
        } catch {}
        emit('error', { message: 'Logged out. Restart the bot to re-pair.' })
        return
      }

      if (statusCode === DisconnectReason.connectionReplaced) {
        log('info', 'Connection replaced by another session — not reconnecting')
        emit('error', { message: 'Connection replaced. Another instance may be running with the same credentials.' })
        return
      }

      // Auto-reconnect with backoff for transient errors
      const delay = Math.min(3000 + Math.random() * 2000, 10000)
      log('info', `Reconnecting in ${Math.round(delay)}ms...`)
      setTimeout(() => startSocket(), delay)
    }
  })

  // Inbound messages
  sock.ev.on('messages.upsert', async ({ messages, type }) => {
    if (type !== 'notify') return

    for (const msg of messages) {
      // Skip status broadcasts
      if (msg.key.remoteJid === 'status@broadcast') continue
      // Skip own messages
      if (msg.key.fromMe) continue

      // Grace period: ignore messages that arrived before we connected
      const msgTimestamp = (msg.messageTimestamp || 0) * 1000
      if (msgTimestamp < connectionTimestamp - GRACE_PERIOD_MS) continue

      const text = extractText(msg)

      // Check for media (image/video) content
      const msgContent = extractMessageContent(msg.message)
      const msgContentType = msgContent ? getContentType(msgContent) : null
      const hasMedia = ['imageMessage', 'videoMessage'].includes(msgContentType)

      // Skip messages with no text AND no media
      if (!text && !hasMedia) continue

      const isGroup = isJidGroup(msg.key.remoteJid)
      const sender = isGroup ? msg.key.participant : msg.key.remoteJid
      const senderE164 = jidToE164(sender)
      const senderName = msg.pushName || null
      const mentions = extractMentions(msg)
      const replyContext = extractReplyContext(msg)

      // For group messages, check if bot was mentioned
      const selfJid = sock.user?.id
      const selfPhone = jidToE164(selfJid)
      const botMentioned = isGroup ? isBotMentioned(msg, selfJid, selfPhone, [BOT_NAME.toLowerCase()]) : true

      // Strip @mention prefix from text so AI gets clean input
      let cleanText = text
      if (isGroup && botMentioned) {
        // Remove @BotName, @phoneNumber, etc. from start of message
        cleanText = text
          .replace(new RegExp(`^@${BOT_NAME}\\s*`, 'i'), '')
          .replace(new RegExp(`^@${selfJid?.split(/[:@]/)[0]}\\s*`), '')
          .trim() || text
      }

      // Download media if present (images, videos)
      let media = null
      if (hasMedia) {
        try {
          const buffer = await downloadMediaMessage(msg, 'buffer', {}, {
            logger,
            reuploadRequest: sock.updateMediaMessage
          })

          // Size guard: skip media larger than 10MB
          if (buffer.length <= 10 * 1024 * 1024) {
            const mediaType = msgContentType === 'imageMessage' ? 'image' : 'video'
            const mime = msgContent[msgContentType]?.mimetype ||
                          (mediaType === 'image' ? 'image/jpeg' : 'video/mp4')

            // Save to media_cache directory (Python reads the file by path)
            const cacheDir = path.join(__dirname, 'media_cache')
            fs.mkdirSync(cacheDir, { recursive: true })
            const ext = mime.split('/')[1]?.split(';')[0] || 'bin'
            const filename = `wa_${msg.key.id}.${ext}`
            const filePath = path.join(cacheDir, filename)
            fs.writeFileSync(filePath, buffer)

            media = {
              type: mediaType,
              mime,
              path: filePath,
              size: buffer.length,
            }
            log('info', `Downloaded ${mediaType}: ${filename} (${buffer.length} bytes)`)
          } else {
            log('warn', `Skipping large media: ${buffer.length} bytes`)
          }
        } catch (err) {
          log('error', 'Failed to download media:', err.message)
        }
      }

      // Resolve group name for context
      let groupName = null
      if (isGroup) {
        try {
          let meta = groupCache.get(msg.key.remoteJid)
          if (!meta) {
            meta = await sock.groupMetadata(msg.key.remoteJid)
            groupCache.set(msg.key.remoteJid, meta)
          }
          groupName = meta?.subject || null
        } catch (err) {
          log('debug', 'Failed to get group name:', err.message)
        }
      }

      emit('message', {
        from: msg.key.remoteJid,
        text: cleanText || '',
        isGroup,
        sender,
        senderE164,
        senderName,
        mentions,
        messageId: msg.key.id,
        quotedText: replyContext?.quotedText || null,
        quotedSender: replyContext?.quotedSender || null,
        botMentioned,
        timestamp: msgTimestamp,
        groupName,
        media,
      })
    }
  })

  // Group metadata updates
  sock.ev.on('groups.update', async ([event]) => {
    try {
      const meta = await sock.groupMetadata(event.id)
      groupCache.set(event.id, meta)
    } catch {}
  })

  sock.ev.on('group-participants.update', async (event) => {
    try {
      const meta = await sock.groupMetadata(event.id)
      groupCache.set(event.id, meta)
    } catch {}
  })

  emit('ready', {})
}

// ─── Command handlers (Python → Node) ──────────────────────

/**
 * Send a text message to a JID
 */
async function handleSend({ jid, text }) {
  if (!sock) {
    log('error', 'Cannot send: socket not connected')
    return
  }

  // Show typing indicator
  try {
    await sock.sendPresenceUpdate('composing', jid)
  } catch {}

  // Chunk long messages (WhatsApp practical limit ~4000 chars for readability)
  const MAX_LEN = 4000
  if (text.length <= MAX_LEN) {
    await sock.sendMessage(jid, { text })
  } else {
    const chunks = chunkMessage(text, MAX_LEN)
    for (const chunk of chunks) {
      await sock.sendMessage(jid, { text: chunk })
      // Small delay between chunks
      await new Promise(r => setTimeout(r, 300))
    }
  }

  // Clear typing
  try {
    await sock.sendPresenceUpdate('paused', jid)
  } catch {}
}

/**
 * Send a media message (image, video, audio, document)
 */
async function handleSendMedia({ jid, filePath: mediaPath, caption, mediaType }) {
  if (!sock) {
    log('error', 'Cannot send media: socket not connected')
    return
  }

  if (!fs.existsSync(mediaPath)) {
    log('error', `Media file not found: ${mediaPath}`)
    return
  }

  const buffer = fs.readFileSync(mediaPath)
  const filename = path.basename(mediaPath)

  switch (mediaType) {
    case 'image':
      await sock.sendMessage(jid, { image: buffer, caption, mimetype: 'image/jpeg' })
      break
    case 'video':
      await sock.sendMessage(jid, { video: buffer, caption, mimetype: 'video/mp4' })
      break
    case 'audio':
      await sock.sendMessage(jid, { audio: buffer, ptt: true, mimetype: 'audio/ogg; codecs=opus' })
      break
    case 'document':
      await sock.sendMessage(jid, { document: buffer, fileName: filename, mimetype: 'application/octet-stream' })
      break
    default:
      log('error', `Unknown media type: ${mediaType}`)
  }
}

/**
 * Show typing indicator in a chat
 */
async function handleTyping({ jid }) {
  if (!sock) return
  try {
    await sock.sendPresenceUpdate('composing', jid)
  } catch {}
}

/**
 * Gracefully stop the bot
 */
async function handleStop() {
  isShuttingDown = true
  log('info', 'Stopping WhatsApp bridge...')
  if (sock) {
    try {
      await sock.logout()
    } catch {
      try {
        sock.end(undefined)
      } catch {}
    }
  }
  setTimeout(() => process.exit(0), 1000)
}

// ─── Utility ────────────────────────────────────────────────

/**
 * Split a long message into chunks at paragraph/sentence boundaries
 */
function chunkMessage(text, maxLength = 4000) {
  if (text.length <= maxLength) return [text]

  const chunks = []
  let remaining = text

  while (remaining.length > 0) {
    if (remaining.length <= maxLength) {
      chunks.push(remaining)
      break
    }

    let splitAt = maxLength
    // Try to split at paragraph boundary
    const paraBreak = remaining.lastIndexOf('\n\n', maxLength)
    if (paraBreak > maxLength * 0.5) {
      splitAt = paraBreak + 2
    } else {
      // Try sentence boundary
      const sentenceBreak = remaining.lastIndexOf('. ', maxLength)
      if (sentenceBreak > maxLength * 0.5) {
        splitAt = sentenceBreak + 2
      } else {
        // Try line break
        const lineBreak = remaining.lastIndexOf('\n', maxLength)
        if (lineBreak > maxLength * 0.5) {
          splitAt = lineBreak + 1
        }
      }
    }

    chunks.push(remaining.slice(0, splitAt))
    remaining = remaining.slice(splitAt)
  }

  return chunks
}

// ─── Stdin command reader ───────────────────────────────────

const rl = readline.createInterface({ input: process.stdin })

rl.on('line', async (line) => {
  let cmd
  try {
    cmd = JSON.parse(line.trim())
  } catch (err) {
    log('error', 'Invalid JSON from Python:', line)
    return
  }

  try {
    switch (cmd.type) {
      case 'send':
        await handleSend(cmd.data)
        break
      case 'send_media':
        await handleSendMedia(cmd.data)
        break
      case 'typing':
        await handleTyping(cmd.data)
        break
      case 'stop':
        await handleStop()
        break
      default:
        log('warn', `Unknown command type: ${cmd.type}`)
    }
  } catch (err) {
    log('error', `Error handling command ${cmd.type}:`, err.message)
    emit('error', { message: err.message, command: cmd.type })
  }
})

rl.on('close', () => {
  log('info', 'Stdin closed, shutting down')
  handleStop()
})

// ─── Start ──────────────────────────────────────────────────

log('info', 'WhatsApp bridge starting...')
log('info', `Auth directory: ${AUTH_DIR}`)

startSocket().catch((err) => {
  log('error', 'Failed to start socket:', err.message)
  emit('error', { message: `Startup failed: ${err.message}` })
  process.exit(1)
})
