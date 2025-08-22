// Test script to verify that explanatory remarks are preserved
// while tool execution blocks are still properly stripped

function testStripAllToolText() {
  // Simulate the updated stripAllToolText function
  function stripAllToolText(text) {
    let cleanedText = text;

    // First, remove complete tool execution blocks (full cycle from start to finish)
    cleanedText = cleanedText.replace(
      /🔧\s*\*\*Executing tools\.\.\.\*\*\s*\n([\s\S]*?)🔧\s*\*\*Tool execution complete\. Continuing\.\.\.\*\*/g,
      ''
    );

    // Remove standalone "Executing tools..." without completion (but preserve preceding text)
    cleanedText = cleanedText.replace(
      /🔧\s*\*\*Executing tools\.\.\.\*\*\s*(?!\s*\n[\s\S]*?🔧\s*\*\*Tool execution complete)/g,
      ''
    );

    // Remove individual tool headers and results, but only within tool execution blocks
    // This is more targeted to avoid removing explanatory text
    const toolBlockPattern = /^(📋\s*\*\*[^:]+\*\*:\s*(?:\{[^}]*\}|[^\n]*)\s*(?:\n✅\s*\*\*Success\*\*:[\s\S]*?(?=\n\n|📋|🔧|$)|❌\s*\*\*Error\*\*:[\s\S]*?(?=\n\n|📋|🔧|$))?)/gm;
    cleanedText = cleanedText.replace(toolBlockPattern, '');

    // Remove standalone success/error blocks
    cleanedText = cleanedText.replace(/✅\s*\*\*Success\*\*:[\s\S]*?(?=\n\n|\n[A-Z]|$)/g, '');
    cleanedText = cleanedText.replace(/❌\s*\*\*Error\*\*:[\s\S]*?(?=\n\n|\n[A-Z]|$)/g, '');

    // Clean up Python code artifacts and logger statements that leak through
    const codeCleanupPattern = new RegExp([
      // Logger statements and debug output
      'logger\\.(info|error|debug|warning)\\([^)]*\\)',
      // Large blocks of escaped code 
      '([\'"]content[\'"]:\\s*[\'"][^\'\"]*?(?:logger\\.|import |def |class |try:|except |if __name__|yield )[^\'\"]*?[\'"])',
      // Python code artifacts that leak through
      '\\\\n\\s*except Exception as e:\\\\n\\s*logger\\.error.*?\\\\n',
      '\\\\n\\s*yield f[\'\""][^\'\"]*?\\\\n',
      // Raw Python code blocks
      '\\n\\s*logger\\.(info|error|debug|warning)\\([^)]*\\)\\s*\\n',
      '\\n\\s*(import |from |def |class |try:|except |if __name__|yield )[^\\n]*\\n'
    ].join('|'), 'g');

    cleanedText = cleanedText.replace(codeCleanupPattern, '');

    // Clean up formatting and escape sequences
    cleanedText = cleanedText
      // Clean up multiple consecutive newlines
      .replace(/\n{3,}/g, '\n\n')
      // Handle escape sequences in a single pass
      .replace(/\\n\\n/g, '\n')
      .replace(/\\n/g, '\n')
      .replace(/\\"/g, '"')
      .replace(/\\"\\n/g, '\n')
      .replace(/\\\\\n/g, '\n')
      .replace(/\\'/g, "'")
      // Remove error handling blocks that leak through
      .replace(/\n\s*except Exception as e:\s*\n[\s\S]*?(?=\n\n|\n[A-Z]|\n#|$)/g, '\n')
      .trim();

    return cleanedText;
  }

  // Test case from the chat history
  const testInput = `I will search the workspace to locate the existing agent_creator_agent.py and any related agent patterns to use as a reference.

🔧 **Executing tools...**

📋 **semantic_search**: {'query': 'agent_creator_agent.py or similar agent files that define chat(message, history) and metadata', 'scope': 'plugins', 'fileTypes': ['py'], 'mode': 'smart', 'root': 'workspace'}
✅ **Success**: [{'file': '/home/penthoy/icotes/workspace/plugins/example_tool_using_agent.py-1-"""', 'line': None, 'snippet': None}, {'file': '/home/penthoy/icotes/workspace/plugins/example_tool_using_agent.py', 'li... (truncated)

🔧 **Tool execution complete. Continuing...**

I will open the existing agent_creator_agent.py and the agents.json to mirror structure and understand how to register the new agent.

🔧 **Executing tools...**

📋 **semantic_search**: {'query': 'agent_creator_agent.py', 'scope': 'plugins', 'fileTypes': ['py'], 'root': 'workspace'}
✅ **Success**: [{'file': '/home/penthoy/icotes/workspace/plugins/agent_creator_agent.py', 'line': None, 'snippet': None}]

🔧 **Tool execution complete. Continuing...**

I will update the get_tools function to gracefully fall back to OpenAI-style tool definitions if Anthropic-specific ones are unavailable.

🔧 **Executing tools...**

📋 **replace_string_in_file**: {'filePath': '/home/penthoy/icotes/workspace/plugins/claude_agent_creator_agent.py', 'oldString': 'def get_tools()...', 'newString': 'def get_tools()...'}
✅ **Success**: Replaced 1 occurrence(s) in file.

🔧 **Tool execution complete. Continuing...**`;

  const result = stripAllToolText(testInput);
  
  console.log("=== ORIGINAL INPUT ===");
  console.log(testInput);
  console.log("\n=== CLEANED OUTPUT ===");
  console.log(result);
  
  // Check if explanatory remarks are preserved
  const hasFirstRemark = result.includes("I will search the workspace to locate the existing agent_creator_agent.py");
  const hasSecondRemark = result.includes("I will open the existing agent_creator_agent.py and the agents.json");
  const hasThirdRemark = result.includes("I will update the get_tools function to gracefully fall back");
  
  // Check if tool execution blocks are removed
  const hasToolBlocks = result.includes("🔧 **Executing tools...**") || result.includes("📋 **semantic_search**");
  
  console.log("\n=== TEST RESULTS ===");
  console.log("First remark preserved:", hasFirstRemark);
  console.log("Second remark preserved:", hasSecondRemark);
  console.log("Third remark preserved:", hasThirdRemark);
  console.log("Tool blocks removed:", !hasToolBlocks);
  
  if (hasFirstRemark && hasSecondRemark && hasThirdRemark && !hasToolBlocks) {
    console.log("✅ TEST PASSED: Remarks preserved, tool blocks removed");
  } else {
    console.log("❌ TEST FAILED");
  }
}

testStripAllToolText();
