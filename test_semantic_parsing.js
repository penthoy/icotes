// Test semantic search output parsing
console.log("Testing semantic search output parsing...");

// Mock toolCall structure that matches what we'd get from a real semantic search
const mockToolCall = {
  id: "test-semantic-search",
  toolName: "semantic_search",
  category: "data",
  status: "success",
  input: {
    query: "agent python files"
  },
  output: "**Success**: [{'file': '/home/penthoy/icotes/workspace/README.md-14-# Features at a glance.', 'line': None, 'snippet': None}, {'file': '/home/penthoy/icotes/workspace/README.md-15-', 'line': None, 'snippet': None}]",
  metadata: {}
};

console.log("Mock tool call:", JSON.stringify(mockToolCall, null, 2));

// Test the parsing logic from GPT5 model helper
function parseSemanticSearchData(toolCall) {
  const input = toolCall.input || {};
  const output = toolCall.output || {};
  
  let results = [];
  let resultCount = 0;
  
  console.log("Input:", input);
  console.log("Output type:", typeof output);
  console.log("Output:", output);
  
  // Handle different output formats - enhanced for better parsing
  if (Array.isArray(output)) {
    // Direct array
    console.log("Parsing as direct array");
    results = output
      .filter((item) => item && (item.file || item.path))
      .map((item) => ({
        file: item.file || item.path || 'Unknown file',
        line: item.line || item.lineNumber || undefined,
        snippet: item.snippet || item.text || item.content || 'No snippet available'
      }));
  } else if (output && typeof output === 'object') {
    console.log("Parsing as object");
    // Check various nested structures
    if (output.data && Array.isArray(output.data)) {
      console.log("Found data array");
      results = output.data
        .filter((item) => item && (item.file || item.path))
        .map((item) => ({
          file: item.file || item.path || 'Unknown file',
          line: item.line || item.lineNumber || undefined,
          snippet: item.snippet || item.text || item.content || 'No snippet available'
        }));
    } else if (output.results && Array.isArray(output.results)) {
      console.log("Found results array");
      results = output.results
        .filter((item) => item && (item.file || item.path))
        .map((item) => ({
          file: item.file || item.path || 'Unknown file',
          line: item.line || item.lineNumber || undefined,
          snippet: item.snippet || item.text || item.content || 'No snippet available'
        }));
    }
  }
  
  // Handle string output
  if (results.length === 0 && typeof output === 'string') {
    console.log("Parsing as string");
    try {
      let arrayText = output;
      
      // If it's a success message, extract the array part
      if (!output.startsWith('[')) {
        console.log("Extracting array from success message");
        const patterns = [
          /\[[\s\S]*?\]/g,           // Basic array pattern
          /results?:\s*\[[\s\S]*?\]/gi, // "results: [...]" pattern
          /data:\s*\[[\s\S]*?\]/gi,     // "data: [...]" pattern
          /found:\s*\[[\s\S]*?\]/gi     // "found: [...]" pattern
        ];
        
        for (const pattern of patterns) {
          const match = output.match(pattern);
          if (match && match[0]) {
            // Extract just the array part
            const extractMatch = match[0].match(/\[[\s\S]*\]/);
            if (extractMatch) {
              arrayText = extractMatch[0];
              console.log("Extracted array text:", arrayText);
              break;
            }
          }
        }
      }
      
      // Parse the array, handling Python-style syntax
      const cleanedArrayText = arrayText
        .replace(/'/g, '"')           // Single to double quotes
        .replace(/None/g, 'null')     // Python None to JSON null
        .replace(/True/g, 'true')     // Python True to JSON true
        .replace(/False/g, 'false')   // Python False to JSON false
        .replace(/,\s*}/g, '}')       // Remove trailing commas
        .replace(/,\s*]/g, ']');      // Remove trailing commas
        
      console.log("Cleaned array text:", cleanedArrayText);
      
      const parsed = JSON.parse(cleanedArrayText);
      console.log("Parsed array:", parsed);
      
      if (Array.isArray(parsed)) {
        results = parsed
          .filter((item) => item && (item.file || item.path || item.filename))
          .map((item) => ({
            file: item.file || item.path || item.filename || 'Unknown file',
            line: item.line || item.lineNumber || item.line_number || undefined,
            snippet: item.snippet || item.text || item.content || item.match || 'No snippet available'
          }));
      }
      
      console.log("Final results from string parsing:", results);
    } catch (parseError) {
      console.error("Parse error:", parseError);
    }
  }
  
  resultCount = results.length;
  console.log("Result count:", resultCount);
  console.log("Final results:", results);
  
  return {
    query: input.query || '(not provided)',
    scope: input.scope || input.root || '',
    fileTypes: input.fileTypes || input.file_types || [],
    results,
    resultCount
  };
}

// Test the parsing
const parsedData = parseSemanticSearchData(mockToolCall);
console.log("Final parsed data:", JSON.stringify(parsedData, null, 2));
