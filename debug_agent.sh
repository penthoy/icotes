#!/bin/bash

# Debug Agent Runner
# Usage: ./debug_agent.sh <agent_name>
# Example: ./debug_agent.sh agent_creator_agent

AGENT_NAME=${1:-agent_creator_agent}
AGENT_FILE="workspace/.icotes/plugins/${AGENT_NAME}.py"

if [ ! -f "$AGENT_FILE" ]; then
    echo "❌ Agent file not found: $AGENT_FILE"
    echo "Available agents:"
    ls -1 workspace/.icotes/plugins/*.py 2>/dev/null | sed 's/.*\///' | sed 's/\.py$//'
    exit 1
fi

echo "🚀 Running agent: $AGENT_NAME"
echo "📂 Agent file: $AGENT_FILE"
echo "🔧 Using backend virtual environment..."
echo ""

cd backend
source .venv/bin/activate
python3 "../$AGENT_FILE"
