import { describe, it, expect } from 'vitest';
import { gpt5Helper } from '../../../../../src/icui/components/chat/modelhelper';

const sampleOutput = "**Success**: [{'file': '/home/penthoy/icotes/workspace/README.md-14-# Features at a glance.', 'line': None, 'snippet': None}, {'file': '/home/penthoy/icotes/workspace/README.md-15-', 'line': None, 'snippet': None}]";

describe('parseSemanticSearchData', () => {
  it('parses Success string with python-like list and hyphen-encoded file-line-snippet', () => {
    const toolCall = {
      id: 't1',
      toolName: 'semantic_search',
      category: 'data',
      status: 'success',
      input: { query: 'agent python files' },
      output: sampleOutput
    } as any;

    const res = gpt5Helper.parseSemanticSearchData(toolCall);
    expect(res.resultCount).toBeGreaterThan(0);
    expect(res.results[0].file).toMatch(/README\.md$/);
    expect(res.results[0].line).toBe(14);
    expect(typeof res.results[0].snippet).toBe('string');
  });
});
