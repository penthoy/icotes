"""
Enhanced tests for SemanticSearchTool smart behavior
"""
"""
Enhanced tests for SemanticSearchTool smart behavior
"""

import os
import pytest
from unittest.mock import patch, MagicMock

from icpy.agent.tools.semantic_search_tool import SemanticSearchTool


class TestSemanticSearchToolEnhancements:
    @pytest.mark.asyncio
    @patch('icpy.agent.tools.semantic_search_tool.get_workspace_service')
    @patch('icpy.agent.tools.semantic_search_tool.subprocess.run')
    async def test_filename_search_detection(self, mock_run, mock_ws_service):
        """When query looks like a filename, tool should try filename listing with rg --files."""
        mock_ws = MagicMock()
        mock_ws.get_workspace_root.return_value = "/workspace"
        mock_ws_service.return_value = mock_ws

        def side_effect(cmd, capture_output, text, timeout):
            # Expect --files in the command for filename search
            if '--files' in cmd and any('agent_creator_agent.py' in arg for arg in cmd):
                m = MagicMock()
                m.returncode = 0
                m.stdout = "/workspace/plugins/agent_creator_agent.py\n/workspace/other/agent_creator_agent.py"
                return m
            # Fallback content search shouldn't be needed
            m = MagicMock()
            m.returncode = 1
            m.stdout = ''
            return m

        mock_run.side_effect = side_effect

        tool = SemanticSearchTool()
        result = await tool.execute(query="agent_creator_agent.py")

        assert result.success is True
        assert len(result.data) == 2
        assert result.data[0]['file'].endswith('agent_creator_agent.py')
        # Filename results have no line number
        assert result.data[0].get('line') is None

    @pytest.mark.asyncio
    @patch('icpy.agent.tools.semantic_search_tool.get_workspace_service')
    @patch('icpy.agent.tools.semantic_search_tool.subprocess.run')
    async def test_case_insensitive_fallback(self, mock_run, mock_ws_service):
        """If exact search returns nothing, retry with -i and return matches."""
        mock_ws = MagicMock()
        mock_ws.get_workspace_root.return_value = "/workspace"
        mock_ws_service.return_value = mock_ws

        calls = {'count': 0}

        def side_effect(cmd, capture_output, text, timeout):
            calls['count'] += 1
            # First pass: exact (no -i) -> no results
            if '-i' not in cmd:
                m = MagicMock(); m.returncode = 1; m.stdout = ''; return m
            # Second pass: case-insensitive -> found
            m = MagicMock(); m.returncode = 0; m.stdout = "test.py:1:Value"; return m

        mock_run.side_effect = side_effect

        tool = SemanticSearchTool()
        result = await tool.execute(query="value")

        assert result.success is True
        assert len(result.data) == 1
        assert calls['count'] >= 2

    @pytest.mark.asyncio
    @patch('icpy.agent.tools.semantic_search_tool.get_workspace_service')
    @patch('icpy.agent.tools.semantic_search_tool.subprocess.run')
    async def test_tokenized_and_regex_fallback(self, mock_run, mock_ws_service):
        """Multi-token queries should fall back to an AND-ordered regex with context lines."""
        mock_ws = MagicMock()
        mock_ws.get_workspace_root.return_value = "/workspace"
        mock_ws_service.return_value = mock_ws

        def side_effect(cmd, capture_output, text, timeout):
            # Only succeed when regex includes tokens joined by .*
            pattern = None
            if '-e' in cmd:
                e_idx = cmd.index('-e')
                pattern = cmd[e_idx + 1]
            if pattern and 'anthropic' in pattern and 'OpenAIStreamingHandler' in pattern and '.*' in pattern:
                m = MagicMock(); m.returncode = 0; m.stdout = "svc.py:10:handler = OpenAIStreamingHandler()"; return m
            m = MagicMock(); m.returncode = 1; m.stdout = ''
            return m

        mock_run.side_effect = side_effect

        tool = SemanticSearchTool()
        q = "Claude Sonnet 4 anthropic OpenAIStreamingHandler"
        result = await tool.execute(query=q)

        assert result.success is True
        assert len(result.data) == 1
        # Ensure context lines are requested in later passes
        called_cmds = [c[0][0] for c in mock_run.call_args_list]
        assert any('-C' in cmd for cmd in called_cmds)

    @pytest.mark.asyncio
    @patch('icpy.agent.tools.semantic_search_tool.get_workspace_service')
    @patch('icpy.agent.tools.semantic_search_tool.subprocess.run')
    async def test_or_tokens_final_fallback(self, mock_run, mock_ws_service):
        """If AND regex finds nothing, fall back to OR tokens using multiple -e flags."""
        mock_ws = MagicMock()
        mock_ws.get_workspace_root.return_value = "/workspace"
        mock_ws_service.return_value = mock_ws

        def side_effect(cmd, capture_output, text, timeout):
            # Simulate that only when multiple -e are provided do we get a match
            if cmd.count('-e') >= 2:
                m = MagicMock(); m.returncode = 0; m.stdout = "mod.ts:3:export const Claude = {}"; return m
            m = MagicMock(); m.returncode = 1; m.stdout = ''
            return m

        mock_run.side_effect = side_effect

        tool = SemanticSearchTool()
        result = await tool.execute(query="Claude anthropic handler")

        assert result.success is True
        assert result.data and result.data[0]['file'].endswith('mod.ts')

    @pytest.mark.asyncio
    @patch('icpy.agent.tools.semantic_search_tool.get_workspace_service')
    @patch('icpy.agent.tools.semantic_search_tool.subprocess.run')
    async def test_include_hidden_and_limits(self, mock_run, mock_ws_service):
        """Hidden files flag should add --hidden and results should respect maxResults and contextLines."""
        mock_ws = MagicMock()
        mock_ws.get_workspace_root.return_value = "/workspace"
        mock_ws_service.return_value = mock_ws

        # Produce 10 lines
        stdout = "\n".join([f"file{i}.py:{i}:line {i}" for i in range(1, 11)])

        def side_effect(cmd, capture_output, text, timeout):
            # Hidden must always be present
            assert '--hidden' in cmd
            # Force first pass (exact) to fail so tool tries broadened regex with -C
            if '-C' not in cmd:
                m = MagicMock(); m.returncode = 1; m.stdout = ''; return m
            # Broadened pass returns results
            m = MagicMock(); m.returncode = 0; m.stdout = stdout; return m

        mock_run.side_effect = side_effect

        tool = SemanticSearchTool()
        result = await tool.execute(query="line", includeHidden=True, maxResults=5, contextLines=2)
        assert result.success is True
        assert len(result.data) == 5
        # Ensure at least one call used context lines
        called_cmds = [c[0][0] for c in mock_run.call_args_list]
        assert any('-C' in cmd for cmd in called_cmds)

    @pytest.mark.asyncio
    @patch('icpy.agent.tools.semantic_search_tool.get_workspace_service')
    @patch('icpy.agent.tools.semantic_search_tool.subprocess.run')
    async def test_repo_root_scope(self, mock_run, mock_ws_service):
        """Support selecting repo root via env when root='repo'."""
        mock_ws = MagicMock()
        mock_ws.get_workspace_root.return_value = "/workspace"
        mock_ws_service.return_value = mock_ws

        os.environ['PROJECT_ROOT'] = '/repo'

        def side_effect(cmd, capture_output, text, timeout):
            # The final path argument should be /repo when root='repo'
            assert cmd[-1].startswith('/repo')
            m = MagicMock(); m.returncode = 0; m.stdout = "repo.py:1:ok"; return m

        mock_run.side_effect = side_effect

        tool = SemanticSearchTool()
        result = await tool.execute(query="ok", root="repo")

        assert result.success is True
        assert result.data[0]['file'].endswith('repo.py')

        tool = SemanticSearchTool()
        result = await tool.execute(query="ok", root="repo")

        assert result.success is True
        assert result.data[0]['file'].endswith('repo.py')
