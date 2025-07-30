# Code-Server Backend Architecture Guide

## Executive Summary

This guide analyzes code-server's backend architecture, focusing on how frontend components (explorer, editor, terminal) communicate with the server to maintain synchronized state. Code-server uses a multi-layered architecture with WebSocket connections, REST APIs, and VS Code's native communication protocols to enable real-time collaboration between frontend and backend.

## 1. Architecture Overview

### High-Level Architecture
```
┌─────────────────────────────────────────────────────────────────┐
│                    Browser (Frontend)                           │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │   Explorer  │  │   Editor    │  │  Terminal   │             │
│  │             │  │             │  │             │             │
│  └─────────────┘  └─────────────┘  └─────────────┘             │
│         │                 │                 │                   │
│         │                 │                 │                   │
│    ┌─────────────────────────────────────────────────────────┐  │
│    │              WebSocket Connection                       │  │
│    │         (VS Code Protocol Messages)                    │  │
│    └─────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ HTTP/WebSocket
                              │
┌─────────────────────────────────────────────────────────────────┐
│                   Code-Server Backend                           │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │                VS Code Server                               ││
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         ││
│  │  │File System │  │ Extension   │  │  Language   │         ││
│  │  │   Service   │  │   Host      │  │   Server    │         ││
│  │  └─────────────┘  └─────────────┘  └─────────────┘         ││
│  └─────────────────────────────────────────────────────────────┘│
│  ┌─────────────────────────────────────────────────────────────┐│
│  │                Code-Server Layer                            ││
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         ││
│  │  │   HTTP      │  │  WebSocket  │  │    PTY      │         ││
│  │  │   Router    │  │   Handler   │  │   Manager   │         ││
│  │  └─────────────┘  └─────────────┘  └─────────────┘         ││
│  └─────────────────────────────────────────────────────────────┘│
│  ┌─────────────────────────────────────────────────────────────┐│
│  │                   Node.js Layer                             ││
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         ││
│  │  │    File     │  │   Process   │  │   System    │         ││
│  │  │   System    │  │   Manager   │  │   APIs      │         ││
│  │  └─────────────┘  └─────────────┘  └─────────────┘         ││
│  └─────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────┘
```

### Core Components

1. **VS Code Server**: Modified VS Code backend running in Node.js
2. **Code-Server Layer**: Custom middleware for web-specific functionality
3. **WebSocket Handler**: Real-time communication with frontend
4. **HTTP Router**: REST API endpoints for file operations
5. **PTY Manager**: Terminal process management
6. **File System Service**: File watching and operations
7. **Extension Host**: VS Code extension execution environment

## 2. Communication Protocols

### Primary Communication Channels

#### 2.1 WebSocket Protocol (Main Channel)
```javascript
// Frontend connection
const socket = new WebSocket('ws://localhost:8080');

// Message format
const message = {
  type: 'request',
  id: 'unique-request-id',
  vsCodeChannelId: 'channel-id',
  body: {
    // VS Code protocol message
  }
};

// Response format
const response = {
  type: 'response',
  id: 'unique-request-id',
  body: {
    // VS Code protocol response
  }
};
```

#### 2.2 HTTP REST API (Secondary Channel)
```javascript
// File operations
GET    /api/files/:path              // Get file content
POST   /api/files/:path              // Save file
DELETE /api/files/:path              // Delete file
PUT    /api/files/:path              // Create/update file

// Directory operations
GET    /api/directories/:path        // List directory
POST   /api/directories/:path        // Create directory
DELETE /api/directories/:path        // Delete directory

// System operations
GET    /api/system/info              // System information
POST   /api/system/command           // Execute command
```

#### 2.3 VS Code Protocol Messages
```javascript
// File system messages
{
  type: 'fs',
  method: 'readFile',
  args: ['/path/to/file']
}

// Editor messages
{
  type: 'editor',
  method: 'openTextDocument',
  args: [{ uri: 'file:///path/to/file' }]
}

// Extension messages
{
  type: 'extension',
  method: 'activateExtension',
  args: ['extension-id']
}
```

## 3. File System Integration

### File Watching System

```javascript
// Backend file watcher implementation
class FileWatcher {
  constructor() {
    this.watchers = new Map();
    this.clients = new Set();
  }
  
  watchDirectory(path) {
    const watcher = chokidar.watch(path, {
      persistent: true,
      ignoreInitial: false
    });
    
    watcher
      .on('add', (filePath) => this.notifyClients('fileAdded', filePath))
      .on('change', (filePath) => this.notifyClients('fileChanged', filePath))
      .on('unlink', (filePath) => this.notifyClients('fileDeleted', filePath))
      .on('addDir', (dirPath) => this.notifyClients('directoryAdded', dirPath))
      .on('unlinkDir', (dirPath) => this.notifyClients('directoryDeleted', dirPath));
    
    this.watchers.set(path, watcher);
  }
  
  notifyClients(event, path) {
    const message = {
      type: 'fileSystemEvent',
      event,
      path,
      timestamp: Date.now()
    };
    
    this.clients.forEach(client => {
      if (client.readyState === WebSocket.OPEN) {
        client.send(JSON.stringify(message));
      }
    });
  }
}
```

### File Operations API

```javascript
// File operations handler
class FileOperationsHandler {
  constructor(fileSystem) {
    this.fs = fileSystem;
  }
  
  async readFile(path) {
    try {
      const content = await this.fs.readFile(path, 'utf8');
      const stats = await this.fs.stat(path);
      
      return {
        content,
        size: stats.size,
        modified: stats.mtime,
        encoding: 'utf8'
      };
    } catch (error) {
      throw new Error(`Failed to read file: ${error.message}`);
    }
  }
  
  async writeFile(path, content) {
    try {
      await this.fs.writeFile(path, content, 'utf8');
      const stats = await this.fs.stat(path);
      
      // Notify file watchers
      this.notifyFileChange(path, 'modified');
      
      return {
        success: true,
        size: stats.size,
        modified: stats.mtime
      };
    } catch (error) {
      throw new Error(`Failed to write file: ${error.message}`);
    }
  }
  
  async listDirectory(path) {
    try {
      const entries = await this.fs.readdir(path, { withFileTypes: true });
      
      return entries.map(entry => ({
        name: entry.name,
        type: entry.isDirectory() ? 'directory' : 'file',
        path: join(path, entry.name)
      }));
    } catch (error) {
      throw new Error(`Failed to list directory: ${error.message}`);
    }
  }
}
```

## 4. Explorer Component Integration

### Explorer State Management

```javascript
// Explorer backend service
class ExplorerService {
  constructor(fileWatcher, fileOperations) {
    this.fileWatcher = fileWatcher;
    this.fileOperations = fileOperations;
    this.explorerState = new Map();
  }
  
  async getDirectoryTree(rootPath) {
    const tree = await this.buildDirectoryTree(rootPath);
    
    // Store state for client
    this.explorerState.set('directoryTree', tree);
    
    // Start watching the directory
    this.fileWatcher.watchDirectory(rootPath);
    
    return tree;
  }
  
  async buildDirectoryTree(path) {
    const entries = await this.fileOperations.listDirectory(path);
    
    const tree = {
      name: basename(path),
      path,
      type: 'directory',
      children: []
    };
    
    for (const entry of entries) {
      if (entry.type === 'directory') {
        // Recursively build subdirectory tree
        tree.children.push(await this.buildDirectoryTree(entry.path));
      } else {
        tree.children.push({
          name: entry.name,
          path: entry.path,
          type: 'file'
        });
      }
    }
    
    return tree;
  }
  
  handleFileSystemEvent(event, path) {
    switch (event) {
      case 'fileAdded':
        this.updateTreeAddFile(path);
        break;
      case 'fileDeleted':
        this.updateTreeRemoveFile(path);
        break;
      case 'directoryAdded':
        this.updateTreeAddDirectory(path);
        break;
      case 'directoryDeleted':
        this.updateTreeRemoveDirectory(path);
        break;
    }
    
    // Notify connected clients
    this.broadcastExplorerUpdate();
  }
}
```

### Real-time Explorer Updates

```javascript
// WebSocket message handler for explorer
class ExplorerWebSocketHandler {
  constructor(explorerService) {
    this.explorerService = explorerService;
  }
  
  handleMessage(client, message) {
    switch (message.type) {
      case 'explorer.getDirectoryTree':
        return this.handleGetDirectoryTree(client, message);
      case 'explorer.createFile':
        return this.handleCreateFile(client, message);
      case 'explorer.deleteFile':
        return this.handleDeleteFile(client, message);
      case 'explorer.renameFile':
        return this.handleRenameFile(client, message);
    }
  }
  
  async handleGetDirectoryTree(client, message) {
    const tree = await this.explorerService.getDirectoryTree(message.path);
    
    client.send(JSON.stringify({
      type: 'explorer.directoryTree',
      requestId: message.id,
      data: tree
    }));
  }
  
  async handleCreateFile(client, message) {
    const { path, content = '' } = message.data;
    
    try {
      await this.explorerService.createFile(path, content);
      
      client.send(JSON.stringify({
        type: 'explorer.fileCreated',
        requestId: message.id,
        data: { path, success: true }
      }));
    } catch (error) {
      client.send(JSON.stringify({
        type: 'explorer.error',
        requestId: message.id,
        error: error.message
      }));
    }
  }
}
```

## 5. Editor Component Integration

### Editor State Synchronization

```javascript
// Editor backend service
class EditorService {
  constructor(fileOperations) {
    this.fileOperations = fileOperations;
    this.openDocuments = new Map();
    this.documentVersions = new Map();
  }
  
  async openDocument(path) {
    // Check if document is already open
    if (this.openDocuments.has(path)) {
      return this.openDocuments.get(path);
    }
    
    const fileContent = await this.fileOperations.readFile(path);
    
    const document = {
      path,
      content: fileContent.content,
      version: 1,
      modified: false,
      lastSaved: fileContent.modified
    };
    
    this.openDocuments.set(path, document);
    this.documentVersions.set(path, 1);
    
    return document;
  }
  
  async saveDocument(path, content) {
    const document = this.openDocuments.get(path);
    
    if (!document) {
      throw new Error('Document not open');
    }
    
    // Save to file system
    await this.fileOperations.writeFile(path, content);
    
    // Update document state
    document.content = content;
    document.modified = false;
    document.lastSaved = new Date();
    document.version++;
    
    this.documentVersions.set(path, document.version);
    
    return document;
  }
  
  updateDocumentContent(path, changes) {
    const document = this.openDocuments.get(path);
    
    if (!document) {
      throw new Error('Document not open');
    }
    
    // Apply changes to document
    document.content = this.applyChanges(document.content, changes);
    document.modified = true;
    document.version++;
    
    this.documentVersions.set(path, document.version);
    
    return document;
  }
  
  applyChanges(content, changes) {
    // Implementation of operational transformation
    // to apply incremental changes to document
    let result = content;
    
    for (const change of changes) {
      result = this.applyChange(result, change);
    }
    
    return result;
  }
}
```

### Real-time Editor Updates

```javascript
// Editor WebSocket handler
class EditorWebSocketHandler {
  constructor(editorService) {
    this.editorService = editorService;
  }
  
  handleMessage(client, message) {
    switch (message.type) {
      case 'editor.openDocument':
        return this.handleOpenDocument(client, message);
      case 'editor.saveDocument':
        return this.handleSaveDocument(client, message);
      case 'editor.documentChange':
        return this.handleDocumentChange(client, message);
      case 'editor.closeDocument':
        return this.handleCloseDocument(client, message);
    }
  }
  
  async handleOpenDocument(client, message) {
    try {
      const document = await this.editorService.openDocument(message.path);
      
      client.send(JSON.stringify({
        type: 'editor.documentOpened',
        requestId: message.id,
        data: document
      }));
    } catch (error) {
      client.send(JSON.stringify({
        type: 'editor.error',
        requestId: message.id,
        error: error.message
      }));
    }
  }
  
  async handleDocumentChange(client, message) {
    const { path, changes, version } = message.data;
    
    try {
      const document = this.editorService.updateDocumentContent(path, changes);
      
      // Broadcast changes to other clients
      this.broadcastDocumentChange(path, changes, version, client);
      
      client.send(JSON.stringify({
        type: 'editor.documentChanged',
        requestId: message.id,
        data: { version: document.version }
      }));
    } catch (error) {
      client.send(JSON.stringify({
        type: 'editor.error',
        requestId: message.id,
        error: error.message
      }));
    }
  }
  
  broadcastDocumentChange(path, changes, version, sender) {
    const message = {
      type: 'editor.documentChangeNotification',
      data: { path, changes, version }
    };
    
    // Send to all connected clients except sender
    this.clients.forEach(client => {
      if (client !== sender && client.readyState === WebSocket.OPEN) {
        client.send(JSON.stringify(message));
      }
    });
  }
}
```

## 6. Terminal Integration

### Terminal Process Management

```javascript
// Terminal backend service
class TerminalService {
  constructor() {
    this.terminals = new Map();
    this.terminalSequence = 0;
  }
  
  createTerminal(options = {}) {
    const terminalId = `terminal-${++this.terminalSequence}`;
    
    const ptyProcess = pty.spawn(options.shell || 'bash', [], {
      name: 'xterm-color',
      cols: options.cols || 80,
      rows: options.rows || 24,
      cwd: options.cwd || process.cwd(),
      env: { ...process.env, ...options.env }
    });
    
    const terminal = {
      id: terminalId,
      process: ptyProcess,
      clients: new Set(),
      created: new Date()
    };
    
    // Handle terminal data
    ptyProcess.onData(data => {
      this.broadcastTerminalData(terminalId, data);
    });
    
    // Handle terminal exit
    ptyProcess.onExit(({ exitCode, signal }) => {
      this.handleTerminalExit(terminalId, exitCode, signal);
    });
    
    this.terminals.set(terminalId, terminal);
    
    return terminal;
  }
  
  attachClient(terminalId, client) {
    const terminal = this.terminals.get(terminalId);
    
    if (!terminal) {
      throw new Error('Terminal not found');
    }
    
    terminal.clients.add(client);
    
    // Send initial terminal state
    client.send(JSON.stringify({
      type: 'terminal.attached',
      terminalId,
      data: {
        cols: terminal.process.cols,
        rows: terminal.process.rows
      }
    }));
  }
  
  writeToTerminal(terminalId, data) {
    const terminal = this.terminals.get(terminalId);
    
    if (!terminal) {
      throw new Error('Terminal not found');
    }
    
    terminal.process.write(data);
  }
  
  resizeTerminal(terminalId, cols, rows) {
    const terminal = this.terminals.get(terminalId);
    
    if (!terminal) {
      throw new Error('Terminal not found');
    }
    
    terminal.process.resize(cols, rows);
  }
  
  broadcastTerminalData(terminalId, data) {
    const terminal = this.terminals.get(terminalId);
    
    if (!terminal) return;
    
    const message = {
      type: 'terminal.data',
      terminalId,
      data
    };
    
    terminal.clients.forEach(client => {
      if (client.readyState === WebSocket.OPEN) {
        client.send(JSON.stringify(message));
      }
    });
  }
}
```

## 7. State Synchronization

### Client State Management

```javascript
// Client state synchronizer
class ClientStateManager {
  constructor() {
    this.clientStates = new Map();
  }
  
  addClient(clientId, websocket) {
    const state = {
      id: clientId,
      websocket,
      openDocuments: new Set(),
      watchedDirectories: new Set(),
      attachedTerminals: new Set(),
      lastActivity: new Date()
    };
    
    this.clientStates.set(clientId, state);
    
    // Send initial state
    this.sendInitialState(clientId);
  }
  
  removeClient(clientId) {
    const state = this.clientStates.get(clientId);
    
    if (!state) return;
    
    // Clean up client resources
    state.openDocuments.forEach(docPath => {
      this.editorService.closeDocument(docPath, clientId);
    });
    
    state.attachedTerminals.forEach(terminalId => {
      this.terminalService.detachClient(terminalId, state.websocket);
    });
    
    this.clientStates.delete(clientId);
  }
  
  sendInitialState(clientId) {
    const state = this.clientStates.get(clientId);
    
    if (!state) return;
    
    const initialState = {
      type: 'initialState',
      data: {
        workspaceRoot: this.workspaceRoot,
        openDocuments: Array.from(state.openDocuments),
        directoryTree: this.explorerService.getDirectoryTree()
      }
    };
    
    state.websocket.send(JSON.stringify(initialState));
  }
  
  updateClientState(clientId, updates) {
    const state = this.clientStates.get(clientId);
    
    if (!state) return;
    
    Object.assign(state, updates);
    state.lastActivity = new Date();
  }
}
```

### Event Broadcasting

```javascript
// Event broadcasting system
class EventBroadcaster {
  constructor() {
    this.subscribers = new Map();
  }
  
  subscribe(eventType, callback) {
    if (!this.subscribers.has(eventType)) {
      this.subscribers.set(eventType, new Set());
    }
    
    this.subscribers.get(eventType).add(callback);
  }
  
  broadcast(eventType, data) {
    const callbacks = this.subscribers.get(eventType);
    
    if (!callbacks) return;
    
    callbacks.forEach(callback => {
      try {
        callback(data);
      } catch (error) {
        console.error('Error in event callback:', error);
      }
    });
  }
  
  // Broadcast to specific clients
  broadcastToClients(eventType, data, clientFilter = null) {
    const message = {
      type: eventType,
      data,
      timestamp: new Date().toISOString()
    };
    
    this.clientStates.forEach((state, clientId) => {
      if (clientFilter && !clientFilter(clientId, state)) {
        return;
      }
      
      if (state.websocket.readyState === WebSocket.OPEN) {
        state.websocket.send(JSON.stringify(message));
      }
    });
  }
}
```

## 8. Error Handling and Recovery

### Error Handling Strategy

```javascript
// Error handling middleware
class ErrorHandler {
  constructor() {
    this.errorHandlers = new Map();
  }
  
  handleError(error, context) {
    const errorType = this.classifyError(error);
    const handler = this.errorHandlers.get(errorType);
    
    if (handler) {
      return handler(error, context);
    }
    
    // Default error handling
    return this.defaultErrorHandler(error, context);
  }
  
  classifyError(error) {
    if (error.code === 'ENOENT') return 'FILE_NOT_FOUND';
    if (error.code === 'EACCES') return 'PERMISSION_DENIED';
    if (error.code === 'ENOTDIR') return 'NOT_DIRECTORY';
    if (error.syscall === 'spawn') return 'PROCESS_SPAWN_ERROR';
    
    return 'UNKNOWN_ERROR';
  }
  
  defaultErrorHandler(error, context) {
    console.error('Unhandled error:', error);
    
    return {
      success: false,
      error: {
        message: error.message,
        code: error.code,
        context
      }
    };
  }
}
```

## 9. Performance Optimizations

### Caching Strategy

```javascript
// Caching system
class CacheManager {
  constructor() {
    this.fileCache = new Map();
    this.directoryCache = new Map();
    this.cacheExpiry = 30000; // 30 seconds
  }
  
  getCachedFile(path) {
    const cached = this.fileCache.get(path);
    
    if (!cached) return null;
    
    if (Date.now() - cached.timestamp > this.cacheExpiry) {
      this.fileCache.delete(path);
      return null;
    }
    
    return cached.content;
  }
  
  setCachedFile(path, content) {
    this.fileCache.set(path, {
      content,
      timestamp: Date.now()
    });
  }
  
  invalidateCache(path) {
    this.fileCache.delete(path);
    
    // Invalidate directory cache for parent directory
    const parentDir = dirname(path);
    this.directoryCache.delete(parentDir);
  }
}
```

### Connection Pooling

```javascript
// Connection pool manager
class ConnectionPool {
  constructor() {
    this.connections = new Map();
    this.maxConnections = 100;
  }
  
  addConnection(clientId, websocket) {
    if (this.connections.size >= this.maxConnections) {
      throw new Error('Connection limit exceeded');
    }
    
    this.connections.set(clientId, {
      websocket,
      created: new Date(),
      lastActivity: new Date()
    });
  }
  
  removeConnection(clientId) {
    this.connections.delete(clientId);
  }
  
  updateActivity(clientId) {
    const connection = this.connections.get(clientId);
    if (connection) {
      connection.lastActivity = new Date();
    }
  }
  
  cleanupStaleConnections() {
    const staleThreshold = 5 * 60 * 1000; // 5 minutes
    const now = Date.now();
    
    this.connections.forEach((connection, clientId) => {
      if (now - connection.lastActivity.getTime() > staleThreshold) {
        this.removeConnection(clientId);
      }
    });
  }
}
```

## 10. Security Considerations

### Authentication and Authorization

```javascript
// Security middleware
class SecurityManager {
  constructor() {
    this.sessions = new Map();
    this.rateLimiter = new Map();
  }
  
  authenticateRequest(req) {
    const token = req.headers.authorization;
    
    if (!token) {
      throw new Error('No authorization token');
    }
    
    const session = this.sessions.get(token);
    
    if (!session || session.expired) {
      throw new Error('Invalid or expired session');
    }
    
    return session.user;
  }
  
  checkRateLimit(clientId, action) {
    const key = `${clientId}:${action}`;
    const limit = this.rateLimiter.get(key) || { count: 0, resetTime: Date.now() + 60000 };
    
    if (Date.now() > limit.resetTime) {
      limit.count = 0;
      limit.resetTime = Date.now() + 60000;
    }
    
    if (limit.count >= 100) { // 100 requests per minute
      throw new Error('Rate limit exceeded');
    }
    
    limit.count++;
    this.rateLimiter.set(key, limit);
  }
  
  validatePath(path) {
    // Prevent path traversal attacks
    const normalizedPath = normalize(path);
    
    if (normalizedPath.includes('..') || normalizedPath.startsWith('/')) {
      throw new Error('Invalid path');
    }
    
    return normalizedPath;
  }
}
```

## 11. Deployment Considerations

### Production Configuration

```javascript
// Production server setup
class ProductionServer {
  constructor() {
    this.server = null;
    this.wsServer = null;
  }
  
  start() {
    const app = express();
    
    // Security middleware
    app.use(helmet());
    app.use(cors({
      origin: process.env.ALLOWED_ORIGINS?.split(',') || ['http://localhost:3000'],
      credentials: true
    }));
    
    // Rate limiting
    app.use(rateLimit({
      windowMs: 15 * 60 * 1000, // 15 minutes
      max: 100 // limit each IP to 100 requests per windowMs
    }));
    
    // Compression
    app.use(compression());
    
    // Static file serving
    app.use(express.static('public'));
    
    // API routes
    app.use('/api', this.createAPIRoutes());
    
    // Start HTTP server
    this.server = app.listen(process.env.PORT || 8080);
    
    // Start WebSocket server
    this.wsServer = new WebSocket.Server({ 
      server: this.server,
      path: '/ws'
    });
    
    this.setupWebSocketHandlers();
  }
  
  setupWebSocketHandlers() {
    this.wsServer.on('connection', (ws, req) => {
      const clientId = this.generateClientId();
      
      // Setup client handlers
      this.setupClientHandlers(clientId, ws);
      
      // Handle client disconnect
      ws.on('close', () => {
        this.handleClientDisconnect(clientId);
      });
    });
  }
}
```

## Conclusion

Code-server's backend architecture succeeds through:

1. **Layered Architecture**: Clean separation between VS Code server, code-server middleware, and Node.js layer
2. **Real-time Communication**: WebSocket-based protocol for immediate state synchronization
3. **Comprehensive State Management**: Centralized state tracking for all client connections
4. **Efficient File Operations**: Optimized file system operations with caching and watching
5. **Robust Error Handling**: Comprehensive error handling and recovery mechanisms
6. **Security Focus**: Built-in authentication, rate limiting, and path validation
7. **Performance Optimization**: Caching, connection pooling, and resource management

The key insight is that code-server maintains **bidirectional state synchronization** between frontend and backend through a combination of WebSocket messages for real-time updates and HTTP APIs for discrete operations. This architecture enables multiple clients to collaborate on the same workspace while maintaining consistent state across all connected instances.

To implement a similar system:

1. **Start with WebSocket communication** for real-time updates
2. **Implement file watching** for automatic state synchronization
3. **Use HTTP APIs** for discrete operations (CRUD)
4. **Add caching and optimization** for performance
5. **Include comprehensive error handling** for reliability
6. **Implement security measures** for production deployment

This architecture pattern enables building robust, multi-user development environments that feel responsive and collaborative while maintaining data consistency across all connected clients.
