"""
Tests for write_doc_tool

Tests document writing functionality for various formats:
- Excel (.xlsx)
- Word (.docx)
- PDF
- PowerPoint (.pptx)
- CSV/TSV
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from icpy.agent.tools.write_doc_tool import WriteDocTool
from icpy.agent.tools.base_tool import ToolResult


class TestWriteDocTool:
    """Test WriteDocTool implementation"""
    
    def test_tool_properties(self):
        """Test tool has correct properties"""
        tool = WriteDocTool()
        assert tool.name == "write_doc"
        assert "Create document files" in tool.description
        assert tool.parameters["type"] == "object"
        assert "filePath" in tool.parameters["properties"]
        assert "content" in tool.parameters["properties"]
        assert "options" in tool.parameters["properties"]
        assert tool.parameters["required"] == ["filePath", "content"]
    
    def test_openai_function_format(self):
        """Test tool converts to OpenAI function format"""
        tool = WriteDocTool()
        func = tool.to_openai_function()
        
        assert func["name"] == "write_doc"
        assert "description" in func
        assert "parameters" in func
        assert "filePath" in func["parameters"]["required"]
        assert "content" in func["parameters"]["required"]
    
    @pytest.mark.asyncio
    async def test_missing_filepath(self):
        """Test error when filePath is missing"""
        tool = WriteDocTool()
        result = await tool.execute(content="test")
        
        assert result.success is False
        assert "filePath is required" in result.error
    
    @pytest.mark.asyncio
    async def test_missing_content(self):
        """Test error when content is missing"""
        tool = WriteDocTool()
        result = await tool.execute(filePath="test.csv")
        
        assert result.success is False
        assert "content is required" in result.error
    
    @pytest.mark.asyncio
    async def test_unsupported_format(self):
        """Test error for unsupported file format"""
        tool = WriteDocTool()
        
        with patch.object(tool, '_parse_path_parameter', return_value=("local", "/test/file.unknown")):
            result = await tool.execute(filePath="/test/file.unknown", content="test")
        
        assert result.success is False
        assert "Unsupported file format" in result.error
    
    @pytest.mark.asyncio
    async def test_write_csv_from_list(self):
        """Test writing CSV from list of dicts"""
        tool = WriteDocTool()
        
        content = [
            {"name": "Alice", "score": 95},
            {"name": "Bob", "score": 87}
        ]
        
        with patch.object(tool, '_parse_path_parameter', return_value=("local", "/workspace/output.csv")):
            with patch.object(tool, '_ensure_directories', return_value=True):
                with patch.object(tool, '_write_file_bytes', return_value=True) as mock_write:
                    result = await tool.execute(filePath="output.csv", content=content)
        
        assert result.success is True
        assert result.data["format"] == "csv"
        assert result.data["size"] > 0
        
        # Verify the written content
        written_bytes = mock_write.call_args[0][1]
        written_content = written_bytes.decode('utf-8')
        assert "name" in written_content
        assert "Alice" in written_content
        assert "Bob" in written_content
    
    @pytest.mark.asyncio
    async def test_write_csv_from_text(self):
        """Test writing CSV from plain text"""
        tool = WriteDocTool()
        
        content = "name,score\nAlice,95\nBob,87"
        
        with patch.object(tool, '_parse_path_parameter', return_value=("local", "/workspace/output.csv")):
            with patch.object(tool, '_ensure_directories', return_value=True):
                with patch.object(tool, '_write_file_bytes', return_value=True) as mock_write:
                    result = await tool.execute(filePath="output.csv", content=content)
        
        assert result.success is True
        written_bytes = mock_write.call_args[0][1]
        assert b"Alice" in written_bytes
    
    @pytest.mark.asyncio
    async def test_write_tsv(self):
        """Test writing TSV file"""
        tool = WriteDocTool()
        
        content = [{"col1": "a", "col2": "b"}]
        
        with patch.object(tool, '_parse_path_parameter', return_value=("local", "/workspace/output.tsv")):
            with patch.object(tool, '_ensure_directories', return_value=True):
                with patch.object(tool, '_write_file_bytes', return_value=True) as mock_write:
                    result = await tool.execute(filePath="output.tsv", content=content)
        
        assert result.success is True
        assert result.data["format"] == "tsv"
        
        # TSV should use tab delimiter
        written_bytes = mock_write.call_args[0][1]
        written_content = written_bytes.decode('utf-8')
        assert "\t" in written_content
    
    @pytest.mark.asyncio
    async def test_write_file_bytes_failure(self):
        """Test error when file write fails"""
        tool = WriteDocTool()
        
        content = [{"a": 1}]
        
        with patch.object(tool, '_parse_path_parameter', return_value=("local", "/workspace/test.csv")):
            with patch.object(tool, '_ensure_directories', return_value=True):
                with patch.object(tool, '_write_file_bytes', return_value=False):
                    result = await tool.execute(filePath="test.csv", content=content)
        
        assert result.success is False
        assert "Failed to write file" in result.error
    
    @pytest.mark.asyncio
    async def test_return_full_data(self):
        """Test returnFullData includes path info"""
        tool = WriteDocTool()
        
        content = [{"a": 1}]
        
        with patch.object(tool, '_parse_path_parameter', return_value=("local", "/workspace/output.csv")):
            with patch.object(tool, '_ensure_directories', return_value=True):
                with patch.object(tool, '_write_file_bytes', return_value=True):
                    with patch.object(tool, '_format_path_info', return_value={
                        "formatted_path": "local:/workspace/output.csv",
                        "namespace": "local",
                    }):
                        result = await tool.execute(
                            filePath="output.csv",
                            content=content,
                            returnFullData=True
                        )
        
        assert result.success is True
        assert "filePath" in result.data
        assert "absolutePath" in result.data
        assert "pathInfo" in result.data
    
    @pytest.mark.asyncio
    async def test_create_directories_option(self):
        """Test createDirectories option"""
        tool = WriteDocTool()
        
        content = [{"a": 1}]
        
        with patch.object(tool, '_parse_path_parameter', return_value=("local", "/workspace/new/dir/output.csv")):
            with patch.object(tool, '_ensure_directories', return_value=True) as mock_ensure:
                with patch.object(tool, '_write_file_bytes', return_value=True):
                    result = await tool.execute(
                        filePath="new/dir/output.csv",
                        content=content,
                        createDirectories=True
                    )
        
        assert result.success is True
        mock_ensure.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_options_passed_to_handler(self):
        """Test that options are passed to the handler"""
        tool = WriteDocTool()
        
        content = [{"a": 1, "b": 2}]
        
        with patch.object(tool, '_parse_path_parameter', return_value=("local", "/workspace/output.csv")):
            with patch.object(tool, '_ensure_directories', return_value=True):
                with patch.object(tool, '_write_file_bytes', return_value=True) as mock_write:
                    result = await tool.execute(
                        filePath="output.csv",
                        content=content,
                        options={"delimiter": ";"}
                    )
        
        assert result.success is True
        # With custom delimiter, content should use semicolons
        written_bytes = mock_write.call_args[0][1]
        written_content = written_bytes.decode('utf-8')
        assert ";" in written_content


class TestWriteDocToolExcel:
    """Tests specifically for Excel writing"""
    
    @pytest.mark.asyncio
    async def test_write_xlsx_simple(self):
        """Test writing simple Excel file"""
        tool = WriteDocTool()
        
        content = [
            {"Product": "Widget", "Price": 10.99, "Quantity": 100},
            {"Product": "Gadget", "Price": 25.50, "Quantity": 50}
        ]
        
        with patch.object(tool, '_parse_path_parameter', return_value=("local", "/workspace/output.xlsx")):
            with patch.object(tool, '_ensure_directories', return_value=True):
                with patch.object(tool, '_write_file_bytes', return_value=True) as mock_write:
                    result = await tool.execute(filePath="output.xlsx", content=content)
        
        assert result.success is True
        assert result.data["format"] == "xlsx"
        
        # Verify Excel bytes were written (should start with PK for zip format)
        written_bytes = mock_write.call_args[0][1]
        assert written_bytes[:2] == b'PK'


class TestWriteDocToolWord:
    """Tests specifically for Word writing"""
    
    @pytest.mark.asyncio
    async def test_write_docx_simple(self):
        """Test writing simple Word document"""
        tool = WriteDocTool()
        
        content = "# My Document\n\nThis is a paragraph.\n\n## Section 1\n\nMore text here."
        
        with patch.object(tool, '_parse_path_parameter', return_value=("local", "/workspace/output.docx")):
            with patch.object(tool, '_ensure_directories', return_value=True):
                with patch.object(tool, '_write_file_bytes', return_value=True) as mock_write:
                    result = await tool.execute(filePath="output.docx", content=content)
        
        assert result.success is True
        assert result.data["format"] == "docx"
        
        # Verify docx bytes were written (should start with PK for zip format)
        written_bytes = mock_write.call_args[0][1]
        assert written_bytes[:2] == b'PK'


class TestWriteDocToolPowerPoint:
    """Tests specifically for PowerPoint writing"""
    
    @pytest.mark.asyncio
    async def test_write_pptx_structured(self):
        """Test writing PowerPoint with structured content"""
        tool = WriteDocTool()
        
        content = {
            "slides": [
                {"title": "Introduction", "content": ["Welcome", "Overview"]},
                {"title": "Details", "content": ["Point 1", "Point 2", "Point 3"]}
            ]
        }
        
        with patch.object(tool, '_parse_path_parameter', return_value=("local", "/workspace/presentation.pptx")):
            with patch.object(tool, '_ensure_directories', return_value=True):
                with patch.object(tool, '_write_file_bytes', return_value=True) as mock_write:
                    result = await tool.execute(filePath="presentation.pptx", content=content)
        
        assert result.success is True
        assert result.data["format"] == "pptx"
        
        # Verify pptx bytes were written
        written_bytes = mock_write.call_args[0][1]
        assert written_bytes[:2] == b'PK'
