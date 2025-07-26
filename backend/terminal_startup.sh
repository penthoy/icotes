#!/bin/bash

# Terminal startup script for icotes
# This script is executed when a new terminal session starts

# CRITICAL: Fix readline support for arrow keys and history navigation
# This ensures that bash readline interprets arrow keys correctly for command history
set -o emacs  # Enable emacs-style line editing (default, but ensure it's set)
set +o vi     # Disable vi mode if it was somehow enabled

# Ensure readline variables are set correctly for arrow key support
export INPUTRC=/etc/inputrc

# Set up proper terminal environment for readline
export TERM=xterm-256color

# Enable command history with proper size
export HISTSIZE=10000
export HISTFILESIZE=20000
export HISTCONTROL=ignoredups:ignorespace

# Enable history expansion
set -H

# Set up clipboard alias if the clipboard command exists
if [ -n "$ICOTES_CLIPBOARD_PATH" ] && [ -f "$ICOTES_CLIPBOARD_PATH" ]; then
    alias iclip="$ICOTES_CLIPBOARD_PATH"
    echo "✓ Clipboard alias 'iclip' is available"
else
    echo "⚠ Clipboard functionality not available"
fi

# Load user's bashrc if it exists - AFTER our terminal fixes
if [ -f ~/.bashrc ]; then
    source ~/.bashrc
fi

# Display welcome message
echo "🚀 icotes terminal ready!"
echo "📋 Use Ctrl+Shift+C to copy, Ctrl+Shift+V to paste"
echo "🔧 Basic commands: iclip, history, tab completion available"
echo "🏃 Arrow keys enabled for command history navigation"
echo "" 