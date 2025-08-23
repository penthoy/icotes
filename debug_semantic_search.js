// Debug semantic search parsing issue
// Based on the raw output: "{'file': '/home/penthoy/icotes/workspace/README.md-14-# Features at a glance.', 'line': None, 'snippet': None}, {'file': '/home/penthoy/icotes/workspace/README.md-15-'"

// Sample raw output that's failing to parse
const rawOutput = "**Success**: [{'file': '/home/penthoy/icotes/workspace/README.md-14-# Features at a glance.', 'line': None, 'snippet': None}, {'file': '/home/penthoy/icotes/workspace/README.md-15-', 'line': None, 'snippet': None}]";

console.log("Raw output:", rawOutput);

// Try parsing with current logic
function parseSemanticSearchOutput(output) {
  let results = [];
  
  // Extract array part
  let arrayText = output;
  
  // If it's a success message, extract the array part
  if (!output.startsWith('[')) {
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
  
  try {
    const parsed = JSON.parse(cleanedArrayText);
    console.log("Parsed successfully:", parsed);
    
    if (Array.isArray(parsed)) {
      results = parsed
        .filter((item) => item && (item.file || item.path || item.filename)) // Only include items with valid file paths
        .map((item) => ({
          file: item.file || item.path || item.filename || 'Unknown file',
          line: item.line || item.lineNumber || item.line_number || undefined,
          snippet: item.snippet || item.text || item.content || item.match || 'No snippet available'
        }));
    }
    
    console.log("Final results:", results);
    console.log("Result count:", results.length);
  } catch (parseError) {
    console.error("Parse error:", parseError);
  }
  
  return results;
}

// Test the parsing
const results = parseSemanticSearchOutput(rawOutput);
