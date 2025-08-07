#!/bin/bash

# Terminal startup script for icotes
# This script is executed when a new terminal session starts

# Set up clipboard alias if the clipboard command exists
if [ -n "$ICOTES_CLIPBOARD_PATH" ] && [ -f "$ICOTES_CLIPBOARD_PATH" ]; then
    alias iclip="$ICOTES_CLIPBOARD_PATH"
    echo "✓ Clipboard alias 'iclip' is available"
else
    echo "⚠ Clipboard functionality not available"
fi

# Load user's bashrc if it exists
if [ -f ~/.bashrc ]; then
    source ~/.bashrc
fi

# Change to workspace directory if WORKSPACE_ROOT is set and exists
if [ -n "$WORKSPACE_ROOT" ] && [ -d "$WORKSPACE_ROOT" ]; then
    echo "🔄 Changing to workspace: $WORKSPACE_ROOT"
    cd "$WORKSPACE_ROOT"
    echo "📁 Current directory: $(pwd)"
else
    echo "⚠ Workspace directory not found: $WORKSPACE_ROOT"
    echo "📁 Starting in: $(pwd)"
fi

# Display welcome message
echo "🚀 icotes terminal ready!"
echo "📋 Use Ctrl+Shift+C to copy, Ctrl+Shift+V to paste"
echo "🔧 Basic commands: iclip, history, tab completion available"
echo "" 