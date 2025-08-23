// Test the semantic search parsing with the exact format from debug output
const testOutput = "[{'file': '/home/penthoy/icotes/workspace/plugins/claude_agent_creator_agent.py', 'line': None, 'snippet': None}, {'file': '/home/penthoy/icotes/workspace/plugins/agent_creator_agent.py', 'line': None, 'snippet': None}]";

// Test the regex pattern I added
const dictPattern = /\{'file':\s*'([^']+)'[^}]*\}/g;
let match;
const extractedResults = [];

while ((match = dictPattern.exec(testOutput)) !== null) {
  extractedResults.push({
    file: match[1].trim(),
    line: undefined,
    snippet: 'No snippet available'
  });
}

console.log('Extracted results:', extractedResults);
console.log('Count:', extractedResults.length);
