"""
Tests for read_doc_tool

Tests document reading functionality for various formats:
- Excel (.xlsx)
- Word (.docx)
- PDF
- PowerPoint (.pptx)
- CSV/TSV
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from icpy.agent.tools.read_doc_tool import ReadDocTool
from icpy.agent.tools.base_tool import ToolResult


class TestReadDocTool:
    """Test ReadDocTool implementation"""
    
    def test_tool_properties(self):
        """Test tool has correct properties"""
        tool = ReadDocTool()
        assert tool.name == "read_doc"
        assert "Read and extract text" in tool.description
        assert tool.parameters["type"] == "object"
        assert "filePath" in tool.parameters["properties"]
        assert "options" in tool.parameters["properties"]
        assert tool.parameters["required"] == ["filePath"]
    
    def test_openai_function_format(self):
        """Test tool converts to OpenAI function format"""
        tool = ReadDocTool()
        func = tool.to_openai_function()
        
        assert func["name"] == "read_doc"
        assert "description" in func
        assert "parameters" in func
        assert func["parameters"]["required"] == ["filePath"]
    
    @pytest.mark.asyncio
    async def test_missing_filepath(self):
        """Test error when filePath is missing"""
        tool = ReadDocTool()
        result = await tool.execute()
        
        assert result.success is False
        assert "filePath is required" in result.error
    
    @pytest.mark.asyncio
    async def test_unsupported_format(self):
        """Test error for unsupported file format"""
        tool = ReadDocTool()
        
        with patch.object(tool, '_parse_path_parameter', return_value=("local", "/test/file.unknown")):
            result = await tool.execute(filePath="/test/file.unknown")
        
        assert result.success is False
        assert "Unsupported file format" in result.error
    
    @pytest.mark.asyncio
    @patch('icpy.agent.tools.read_doc_tool.get_workspace_service')
    async def test_read_csv_file(self, mock_ws_service):
        """Test reading CSV file"""
        # Setup workspace mock
        mock_ws = AsyncMock()
        mock_ws.get_workspace_root.return_value = "/workspace"
        mock_ws_service.return_value = mock_ws
        
        # Create CSV content
        csv_content = b"name,score\nAlice,95\nBob,87\n"
        
        tool = ReadDocTool()
        
        with patch.object(tool, '_parse_path_parameter', return_value=("local", "/workspace/data.csv")):
            with patch.object(tool, '_read_file_bytes', return_value=csv_content):
                result = await tool.execute(filePath="data.csv")
        
        assert result.success is True
        assert result.data["format"] == "csv"
        assert "Alice" in result.data["content"]
        assert "Bob" in result.data["content"]
        assert len(result.data["tables"]) > 0
        assert result.data["tables"][0]["columns"] == ["name", "score"]
    
    @pytest.mark.asyncio
    @patch('icpy.agent.tools.read_doc_tool.get_workspace_service')
    async def test_read_tsv_file(self, mock_ws_service):
        """Test reading TSV file"""
        mock_ws = AsyncMock()
        mock_ws.get_workspace_root.return_value = "/workspace"
        mock_ws_service.return_value = mock_ws
        
        tsv_content = b"name\tscore\nAlice\t95\nBob\t87\n"
        
        tool = ReadDocTool()
        
        with patch.object(tool, '_parse_path_parameter', return_value=("local", "/workspace/data.tsv")):
            with patch.object(tool, '_read_file_bytes', return_value=tsv_content):
                result = await tool.execute(filePath="data.tsv")
        
        assert result.success is True
        assert result.data["format"] == "tsv"
        assert "Alice" in result.data["content"]
    
    @pytest.mark.asyncio
    async def test_read_file_bytes_failure(self):
        """Test error when file read fails"""
        tool = ReadDocTool()
        
        with patch.object(tool, '_parse_path_parameter', return_value=("local", "/workspace/test.csv")):
            with patch.object(tool, '_read_file_bytes', return_value=None):
                result = await tool.execute(filePath="test.csv")
        
        assert result.success is False
        assert "Failed to read file" in result.error
    
    @pytest.mark.asyncio
    async def test_return_full_data(self):
        """Test returnFullData includes path info"""
        csv_content = b"col1,col2\nval1,val2\n"
        
        tool = ReadDocTool()
        
        with patch.object(tool, '_parse_path_parameter', return_value=("local", "/workspace/data.csv")):
            with patch.object(tool, '_read_file_bytes', return_value=csv_content):
                with patch.object(tool, '_format_path_info', return_value={
                    "formatted_path": "local:/workspace/data.csv",
                    "namespace": "local",
                }):
                    result = await tool.execute(filePath="data.csv", returnFullData=True)
        
        assert result.success is True
        assert "filePath" in result.data
        assert "absolutePath" in result.data
        assert "pathInfo" in result.data
    
    @pytest.mark.asyncio
    async def test_options_passed_to_handler(self):
        """Test that options are passed to the handler"""
        csv_content = b"a,b\n1,2\n3,4\n5,6\n7,8\n9,10\n"
        
        tool = ReadDocTool()
        
        with patch.object(tool, '_parse_path_parameter', return_value=("local", "/workspace/data.csv")):
            with patch.object(tool, '_read_file_bytes', return_value=csv_content):
                result = await tool.execute(
                    filePath="data.csv",
                    options={"max_rows": 2}
                )
        
        assert result.success is True
        # With max_rows=2, we should only see limited rows


class TestReadDocToolExcelHandler:
    """Tests specifically for Excel handling"""
    
    @pytest.mark.asyncio
    async def test_xlsx_format_detection(self):
        """Test that xlsx files are detected correctly"""
        from icpy.agent.tools.doc_processor.base import detect_format, DocumentFormat
        
        fmt = detect_format("/path/to/file.xlsx")
        assert fmt == DocumentFormat.EXCEL_XLSX
        
        fmt = detect_format("/path/to/file.xls")
        assert fmt == DocumentFormat.EXCEL_XLS
        
        fmt = detect_format("/path/to/file.xlsb")
        assert fmt == DocumentFormat.EXCEL_XLSB


class TestReadDocToolPDFHandler:
    """Tests specifically for PDF handling"""
    
    @pytest.mark.asyncio
    async def test_pdf_format_detection(self):
        """Test that PDF files are detected correctly"""
        from icpy.agent.tools.doc_processor.base import detect_format, DocumentFormat
        
        fmt = detect_format("/path/to/file.pdf")
        assert fmt == DocumentFormat.PDF


class TestReadDocToolWordHandler:
    """Tests specifically for Word handling"""
    
    @pytest.mark.asyncio
    async def test_docx_format_detection(self):
        """Test that Word files are detected correctly"""
        from icpy.agent.tools.doc_processor.base import detect_format, DocumentFormat
        
        fmt = detect_format("/path/to/file.docx")
        assert fmt == DocumentFormat.WORD_DOCX
        
        fmt = detect_format("/path/to/file.doc")
        assert fmt == DocumentFormat.WORD_DOCX  # Falls back to docx handler


class TestReadDocToolPPTXHandler:
    """Tests specifically for PowerPoint handling"""
    
    @pytest.mark.asyncio
    async def test_pptx_format_detection(self):
        """Test that PowerPoint files are detected correctly"""
        from icpy.agent.tools.doc_processor.base import detect_format, DocumentFormat
        
        fmt = detect_format("/path/to/presentation.pptx")
        assert fmt == DocumentFormat.POWERPOINT


class TestDocumentHandlerRegistry:
    """Test handler registration"""
    
    def test_handlers_registered(self):
        """Test that all handlers are registered"""
        from icpy.agent.tools.doc_processor import get_handler_for_format, DocumentFormat
        
        # CSV should always be available (built-in)
        handler = get_handler_for_format(DocumentFormat.CSV)
        assert handler is not None
        
        handler = get_handler_for_format(DocumentFormat.TSV)
        assert handler is not None
    
    def test_get_all_supported_formats(self):
        """Test getting list of supported formats"""
        from icpy.agent.tools.doc_processor.base import get_all_supported_formats
        
        formats = get_all_supported_formats()
        assert ".csv" in formats
        assert ".xlsx" in formats
        assert ".pdf" in formats
        assert ".docx" in formats
        assert ".pptx" in formats


class TestReadDocToolTruncation:
    """Tests for content truncation functionality"""
    
    def test_no_truncation_for_small_content(self):
        """Test that small content is not truncated"""
        tool = ReadDocTool()
        content = "Line 1\nLine 2\nLine 3"
        
        result, info = tool._apply_truncation(
            content=content,
            max_chars=20000,
            max_lines=1000
        )
        
        assert result == content
        assert info is None  # No truncation info when not truncated
    
    def test_auto_truncation_by_chars(self):
        """Test auto-truncation when content exceeds max_chars"""
        tool = ReadDocTool()
        # Create content larger than max_chars
        content = "x" * 1000
        
        result, info = tool._apply_truncation(
            content=content,
            max_chars=500,
            max_lines=1000
        )
        
        assert len(result) < len(content) + 200  # Truncated + notice
        assert info["truncated"] is True
        assert info["total_chars"] == 1000
        assert info["returned_chars"] < 1000
        assert "TRUNCATED" in result
    
    def test_auto_truncation_by_lines(self):
        """Test auto-truncation when content exceeds max_lines"""
        tool = ReadDocTool()
        # Create content with many lines
        lines = [f"Line {i}" for i in range(100)]
        content = "\n".join(lines)
        
        result, info = tool._apply_truncation(
            content=content,
            max_chars=100000,
            max_lines=10
        )
        
        assert info["truncated"] is True
        assert info["total_lines"] == 100
        assert info["returned_lines"] <= 10
        assert "TRUNCATED" in result
        assert "suggested_next" in info
    
    def test_line_range_extraction(self):
        """Test extracting specific line range (like head/tail)"""
        tool = ReadDocTool()
        lines = [f"Line {i}" for i in range(1, 101)]  # Lines 1-100
        content = "\n".join(lines)
        
        result, info = tool._apply_truncation(
            content=content,
            max_chars=100000,
            max_lines=1000,
            start_line=10,
            end_line=20
        )
        
        # Should contain lines 10-20
        assert "Line 10" in result
        assert "Line 20" in result
        assert "Line 9" not in result
        assert "Line 21" not in result
        
        assert info["truncated"] is True
        assert info["start_line"] == 10
        assert info["end_line"] == 20
        assert info["returned_lines"] == 11  # 10 to 20 inclusive
    
    def test_line_range_with_has_more(self):
        """Test that has_more indicates remaining content"""
        tool = ReadDocTool()
        lines = [f"Line {i}" for i in range(1, 101)]
        content = "\n".join(lines)
        
        result, info = tool._apply_truncation(
            content=content,
            max_chars=100000,
            max_lines=1000,
            start_line=1,
            end_line=50
        )
        
        assert info["has_more"] is True
        assert info["suggested_next"]["start_line"] == 51
    
    def test_summary_mode(self):
        """Test summary_only mode returns preview of start/end"""
        tool = ReadDocTool()
        # Create content with clear start and end markers
        content = "START MARKER" + "x" * 2000 + "END MARKER"
        
        result, info = tool._apply_truncation(
            content=content,
            max_chars=100000,
            max_lines=1000,
            summary_only=True
        )
        
        assert "DOCUMENT SUMMARY" in result
        assert "START MARKER" in result  # First preview
        assert "Total characters:" in result
        assert info["truncated"] is True
        assert info["mode"] == "summary"
    
    def test_empty_content(self):
        """Test handling of empty content"""
        tool = ReadDocTool()
        result, info = tool._apply_truncation(
            content="",
            max_chars=20000,
            max_lines=1000
        )
        
        assert result == ""
        assert info is None
    
    @pytest.mark.asyncio
    @patch('icpy.agent.tools.read_doc_tool.get_workspace_service')
    async def test_truncation_in_execute(self, mock_ws_service):
        """Test that truncation is applied in execute method"""
        mock_ws = AsyncMock()
        mock_ws.get_workspace_root.return_value = "/workspace"
        mock_ws_service.return_value = mock_ws
        
        # Create large CSV content (many lines)
        lines = ["name,value"] + [f"row{i},{i}" for i in range(200)]
        csv_content = "\n".join(lines).encode('utf-8')
        
        tool = ReadDocTool()
        
        with patch.object(tool, '_parse_path_parameter', return_value=("local", "/workspace/big.csv")):
            with patch.object(tool, '_read_file_bytes', return_value=csv_content):
                result = await tool.execute(
                    filePath="big.csv",
                    options={"max_lines": 50}
                )
        
        assert result.success is True
        assert result.data.get("truncated") is True
        assert result.data["truncation_info"]["total_lines"] > 50
        assert result.data["truncation_info"]["returned_lines"] <= 50

