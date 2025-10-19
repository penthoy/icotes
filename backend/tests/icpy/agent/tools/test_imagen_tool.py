"""
Tests for ImagenTool with Phase 7 updates (hop support, resolution control, custom filenames)
"""
import pytest
import base64
import os
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from io import BytesIO

# Import the tool
from icpy.agent.tools.imagen_tool import ImagenTool
from icpy.agent.tools.base_tool import ToolResult


@pytest.fixture
def mock_genai():
    """Mock Google Generative AI SDK"""
    with patch('icpy.agent.tools.imagen_tool.genai') as mock:
        yield mock


@pytest.fixture
def mock_filesystem():
    """Mock contextual filesystem"""
    fs = AsyncMock()
    fs.write_file = AsyncMock()
    fs.read_file = AsyncMock()
    return fs


@pytest.fixture
def mock_context():
    """Mock current context"""
    return {
        'contextId': 'local',
        'status': 'disconnected',
        'host': None
    }


@pytest.fixture
def sample_image_bytes():
    """Create a simple 10x10 PNG image for testing"""
    try:
        from PIL import Image
        img = Image.new('RGB', (10, 10), color='red')
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        return buffer.getvalue()
    except ImportError:
        # Fallback: return a minimal valid PNG
        return base64.b64decode(
            'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=='
        )


@pytest.fixture
def imagen_tool(mock_genai):
    """Create ImagenTool instance with mocked environment"""
    with patch.dict(os.environ, {'GOOGLE_API_KEY': 'test-key'}):
        tool = ImagenTool()
        return tool


class TestImagenToolBasic:
    """Test basic ImagenTool functionality"""

    def test_init(self, imagen_tool):
        """Test tool initialization"""
        assert imagen_tool.name == "generate_image"
        assert "custom filenames" in imagen_tool.description
        assert "hop contexts" in imagen_tool.description
        assert "resolution" in imagen_tool.description
        
        # Check new parameters
        assert "filename" in imagen_tool.parameters["properties"]
        assert "width" in imagen_tool.parameters["properties"]
        assert "height" in imagen_tool.parameters["properties"]

    @pytest.mark.asyncio
    async def test_execute_missing_prompt(self, imagen_tool):
        """Test execution fails without prompt"""
        result = await imagen_tool.execute()
        assert not result.success
        assert "prompt is required" in result.error


class TestImagenToolHopSupport:
    """Test hop context support"""

    @pytest.mark.asyncio
    async def test_save_to_local_context(self, imagen_tool, mock_filesystem, mock_context, sample_image_bytes):
        """Test saving image to local context"""
        with patch('icpy.agent.tools.imagen_tool.get_contextual_filesystem', return_value=mock_filesystem), \
             patch('icpy.agent.tools.imagen_tool.get_current_context', return_value=mock_context):
            
            result = await imagen_tool._save_image_to_workspace(
                sample_image_bytes,
                "test prompt",
                None
            )
            
            # Should have called write_file
            assert mock_filesystem.write_file.called
            # Should return a filename
            assert result is not None
            assert result.endswith('.png')

    @pytest.mark.asyncio
    async def test_save_to_remote_context(self, imagen_tool, mock_filesystem, sample_image_bytes):
        """Test saving image to remote hop context"""
        remote_context = {
            'contextId': 'remote-server',
            'status': 'connected',
            'host': '192.168.1.100',
            'username': 'testuser',
            'workspaceRoot': '/home/testuser/icotes/workspace'
        }
        
        # Mock write_file_binary to succeed (preferred path for remote binary writes)
        mock_filesystem.write_file_binary = AsyncMock(return_value=True)
        
        with patch('icpy.agent.tools.imagen_tool.get_contextual_filesystem', return_value=mock_filesystem), \
             patch('icpy.agent.tools.imagen_tool.get_current_context', return_value=remote_context):
            
            result = await imagen_tool._save_image_to_workspace(
                sample_image_bytes,
                "test prompt",
                None
            )
            
            # Should have called write_file_binary for remote binary data
            assert mock_filesystem.write_file_binary.called
            assert result is not None

    @pytest.mark.asyncio
    async def test_remote_write_fallback_to_write_file(self, imagen_tool, mock_filesystem, sample_image_bytes):
        """Test that write_file_binary is the only method used for remote writes"""
        remote_context = {
            'contextId': 'remote-server',
            'status': 'connected',
            'host': '192.168.1.100',
            'username': 'testuser',
            'workspaceRoot': '/home/testuser/icotes/workspace'
        }
        
        # Mock write_file_binary to succeed
        mock_filesystem.write_file_binary = AsyncMock(return_value=True)
        
        with patch('icpy.agent.tools.imagen_tool.get_contextual_filesystem', return_value=mock_filesystem), \
             patch('icpy.agent.tools.imagen_tool.get_current_context', return_value=remote_context):
            
            result = await imagen_tool._save_image_to_workspace(
                sample_image_bytes,
                "test prompt",
                None
            )
            
            # Should have called write_file_binary
            assert mock_filesystem.write_file_binary.called
            assert result is not None

    @pytest.mark.asyncio
    async def test_remote_write_graceful_failure(self, imagen_tool, mock_filesystem, sample_image_bytes):
        """Test that remote write failures return None"""
        remote_context = {
            'contextId': 'remote-server',
            'status': 'connected',
            'host': '192.168.1.100',
            'username': 'testuser',
            'workspaceRoot': '/home/testuser/icotes/workspace'
        }
        
        # Mock write_file_binary to fail
        mock_filesystem.write_file_binary = AsyncMock(return_value=False)
        
        with patch('icpy.agent.tools.imagen_tool.get_contextual_filesystem', return_value=mock_filesystem), \
             patch('icpy.agent.tools.imagen_tool.get_current_context', return_value=remote_context):
            
            result = await imagen_tool._save_image_to_workspace(
                sample_image_bytes,
                "test prompt",
                None
            )
            
            # Should return None on remote write failure
            assert result is None

    @pytest.mark.asyncio
    async def test_load_image_from_hop_via_read_file_binary(self, imagen_tool, mock_filesystem, sample_image_bytes):
        """Test loading image from remote hop using file:// path via read_file_binary"""
        # Mock read_file_binary to return image bytes (preferred path for binary reads)
        mock_filesystem.read_file_binary = AsyncMock(return_value=sample_image_bytes)
        
        with patch('icpy.agent.tools.imagen_tool.get_contextual_filesystem', return_value=mock_filesystem):
            result = await imagen_tool._decode_image_input(
                "file:///workspace/test.png",
                None
            )
            
            # Should have called read_file_binary for binary image data
            assert mock_filesystem.read_file_binary.called
            # Should return valid image part
            assert result is not None
            assert result['mime_type'] == 'image/png'
            assert result['data'] == sample_image_bytes

    @pytest.mark.asyncio
    async def test_load_image_fallback_to_read_file(self, imagen_tool, mock_filesystem, sample_image_bytes):
        """Test fallback to read_file when read_file_binary returns None"""
        # Mock read_file_binary to return None, read_file to return base64
        mock_filesystem.read_file_binary = AsyncMock(return_value=None)
        b64_data = base64.b64encode(sample_image_bytes).decode('utf-8')
        mock_filesystem.read_file = AsyncMock(return_value=b64_data)
        
        with patch('icpy.agent.tools.imagen_tool.get_contextual_filesystem', return_value=mock_filesystem):
            result = await imagen_tool._decode_image_input(
                "file:///workspace/test.png",
                None
            )
            
            # Should have tried read_file_binary first
            assert mock_filesystem.read_file_binary.called
            # Should have fallen back to read_file
            assert mock_filesystem.read_file.called
            # Should return valid image part
            assert result is not None
            assert result['data'] == sample_image_bytes

    @pytest.mark.asyncio
    async def test_load_image_fallback_to_local_file(self, imagen_tool, sample_image_bytes, tmp_path):
        """Test fallback to direct file read when contextual filesystem fails"""
        # Create a real file
        test_file = tmp_path / "test.png"
        test_file.write_bytes(sample_image_bytes)
        
        # Mock filesystem to fail
        mock_filesystem = AsyncMock()
        mock_filesystem.read_file_binary = AsyncMock(side_effect=Exception("Remote read failed"))
        mock_filesystem.read_file = AsyncMock(side_effect=Exception("Remote read failed"))
        
        with patch('icpy.agent.tools.imagen_tool.get_contextual_filesystem', return_value=mock_filesystem):
            result = await imagen_tool._decode_image_input(
                f"file://{test_file}",
                None
            )
            
            # Should have tried contextual filesystem first
            assert mock_filesystem.read_file_binary.called
            # Should have fallen back to direct file access
            assert result is not None
            assert result['data'] == sample_image_bytes

    @pytest.mark.asyncio
    async def test_load_image_handles_string_from_read_file_binary(self, imagen_tool, mock_filesystem, sample_image_bytes):
        """Test handling when read_file_binary returns string (some remote adapters)"""
        # Mock read_file_binary to return base64 string instead of bytes
        b64_string = base64.b64encode(sample_image_bytes).decode('utf-8')
        mock_filesystem.read_file_binary = AsyncMock(return_value=b64_string)
        
        with patch('icpy.agent.tools.imagen_tool.get_contextual_filesystem', return_value=mock_filesystem):
            result = await imagen_tool._decode_image_input(
                "file:///workspace/test.png",
                None
            )
            
            # Should decode the base64 string
            assert result is not None
            assert result['data'] == sample_image_bytes

    @pytest.mark.asyncio
    async def test_load_image_handles_data_uri_from_filesystem(self, imagen_tool, mock_filesystem, sample_image_bytes):
        """Test handling when filesystem returns data URI"""
        # Mock read_file_binary to return data URI string
        b64_string = base64.b64encode(sample_image_bytes).decode('utf-8')
        data_uri = f"data:image/png;base64,{b64_string}"
        mock_filesystem.read_file_binary = AsyncMock(return_value=data_uri)
        
        with patch('icpy.agent.tools.imagen_tool.get_contextual_filesystem', return_value=mock_filesystem):
            result = await imagen_tool._decode_image_input(
                "file:///workspace/test.png",
                None
            )
            
            # Should extract and decode the base64 from data URI
            assert result is not None
            assert result['data'] == sample_image_bytes

    @pytest.mark.asyncio
    async def test_load_image_mime_type_inference(self, imagen_tool, mock_filesystem, sample_image_bytes):
        """Test MIME type inference from file extension"""
        mock_filesystem.read_file_binary = AsyncMock(return_value=sample_image_bytes)
        
        with patch('icpy.agent.tools.imagen_tool.get_contextual_filesystem', return_value=mock_filesystem):
            # Test .png
            result = await imagen_tool._decode_image_input("file:///test.png", None)
            assert result['mime_type'] == 'image/png'
            
            # Test .jpg
            result = await imagen_tool._decode_image_input("file:///test.jpg", None)
            assert result['mime_type'] == 'image/jpeg'
            
            # Test .jpeg
            result = await imagen_tool._decode_image_input("file:///test.jpeg", None)
            assert result['mime_type'] == 'image/jpeg'
            
            # Test .webp
            result = await imagen_tool._decode_image_input("file:///test.webp", None)
            assert result['mime_type'] == 'image/webp'

    @pytest.mark.asyncio
    async def test_load_image_failure_all_methods(self, imagen_tool):
        """Test graceful failure when all loading methods fail"""
        # Mock filesystem to fail
        mock_filesystem = AsyncMock()
        mock_filesystem.read_file_binary = AsyncMock(return_value=None)
        mock_filesystem.read_file = AsyncMock(return_value=None)
        
        with patch('icpy.agent.tools.imagen_tool.get_contextual_filesystem', return_value=mock_filesystem):
            result = await imagen_tool._decode_image_input(
                "file:///nonexistent/test.png",
                None
            )
            
            # Should return None gracefully
            assert result is None


class TestImagenToolResolution:
    """Test resolution control functionality"""

    @pytest.mark.skipif(not hasattr(ImagenTool, '_resize_image'), reason="Pillow not available")
    def test_resize_with_width_only(self, imagen_tool, sample_image_bytes):
        """Test resizing with only width specified"""
        try:
            from PIL import Image
            resized_bytes, mime = imagen_tool._resize_image(sample_image_bytes, width=50, height=None)
            
            # Verify image was resized
            img = Image.open(BytesIO(resized_bytes))
            assert img.width == 50
            # Height should maintain aspect ratio (original was 10x10, so should be 50x50)
            assert img.height == 50
        except ImportError:
            pytest.skip("PIL not available")

    @pytest.mark.skipif(not hasattr(ImagenTool, '_resize_image'), reason="Pillow not available")
    def test_resize_with_height_only(self, imagen_tool, sample_image_bytes):
        """Test resizing with only height specified"""
        try:
            from PIL import Image
            resized_bytes, mime = imagen_tool._resize_image(sample_image_bytes, width=None, height=100)
            
            # Verify image was resized
            img = Image.open(BytesIO(resized_bytes))
            assert img.height == 100
            # Width should maintain aspect ratio
            assert img.width == 100
        except ImportError:
            pytest.skip("PIL not available")

    @pytest.mark.skipif(not hasattr(ImagenTool, '_resize_image'), reason="Pillow not available")
    def test_resize_with_both_dimensions(self, imagen_tool, sample_image_bytes):
        """Test resizing with only width and height specified"""
        try:
            from PIL import Image
            resized_bytes, mime = imagen_tool._resize_image(sample_image_bytes, width=200, height=150)
            
            # Verify exact dimensions
            img = Image.open(BytesIO(resized_bytes))
            assert img.width == 200
            assert img.height == 150
        except ImportError:
            pytest.skip("PIL not available")

    def test_resize_without_pil(self, imagen_tool, sample_image_bytes):
        """Test that resize returns original image when PIL unavailable"""
        with patch('icpy.agent.tools.imagen_tool.PIL_AVAILABLE', False):
            resized_bytes, mime = imagen_tool._resize_image(sample_image_bytes, width=100, height=100)
            
            # Should return original bytes unchanged
            assert resized_bytes == sample_image_bytes


class TestImagenToolCustomFilename:
    """Test custom filename functionality"""

    @pytest.mark.asyncio
    async def test_custom_filename(self, imagen_tool, mock_filesystem, mock_context, sample_image_bytes):
        """Test saving with custom filename"""
        with patch('icpy.agent.tools.imagen_tool.get_contextual_filesystem', return_value=mock_filesystem), \
             patch('icpy.agent.tools.imagen_tool.get_current_context', return_value=mock_context):
            
            result = await imagen_tool._save_image_to_workspace(
                sample_image_bytes,
                "test prompt",
                custom_filename="my_custom_image"
            )
            
            # Should use custom filename
            assert result == "my_custom_image.png"

    @pytest.mark.asyncio
    async def test_auto_generated_filename(self, imagen_tool, mock_filesystem, mock_context, sample_image_bytes):
        """Test auto-generated filename from prompt"""
        with patch('icpy.agent.tools.imagen_tool.get_contextual_filesystem', return_value=mock_filesystem), \
             patch('icpy.agent.tools.imagen_tool.get_current_context', return_value=mock_context):
            
            result = await imagen_tool._save_image_to_workspace(
                sample_image_bytes,
                "a blue circle",
                custom_filename=None
            )
            
            # Should contain sanitized prompt in filename
            assert "generated_image" in result
            assert "blue_circle" in result or "a_blue_circle" in result
            assert result.endswith('.png')

    @pytest.mark.asyncio
    async def test_filename_sanitization(self, imagen_tool, mock_filesystem, mock_context, sample_image_bytes):
        """Test that special characters are sanitized from filename"""
        with patch('icpy.agent.tools.imagen_tool.get_contextual_filesystem', return_value=mock_filesystem), \
             patch('icpy.agent.tools.imagen_tool.get_current_context', return_value=mock_context):
            
            result = await imagen_tool._save_image_to_workspace(
                sample_image_bytes,
                "test!@#$%^&*()prompt",
                custom_filename="my/file\\with:bad<chars>"
            )
            
            # Should not contain special characters
            assert '/' not in result
            assert '\\' not in result
            assert ':' not in result
            assert '<' not in result
            assert '>' not in result


class TestImagenToolImageDecoding:
    """Test various image input formats for editing"""

    @pytest.mark.asyncio
    async def test_decode_data_uri(self, imagen_tool, sample_image_bytes):
        """Test decoding data URI format"""
        b64_string = base64.b64encode(sample_image_bytes).decode('utf-8')
        data_uri = f"data:image/png;base64,{b64_string}"
        
        result = await imagen_tool._decode_image_input(data_uri, None)
        
        assert result is not None
        assert result['mime_type'] == 'image/png'
        assert result['data'] == sample_image_bytes

    @pytest.mark.asyncio
    async def test_decode_data_uri_jpeg(self, imagen_tool, sample_image_bytes):
        """Test decoding JPEG data URI"""
        b64_string = base64.b64encode(sample_image_bytes).decode('utf-8')
        data_uri = f"data:image/jpeg;base64,{b64_string}"
        
        result = await imagen_tool._decode_image_input(data_uri, None)
        
        assert result is not None
        assert result['mime_type'] == 'image/jpeg'
        assert result['data'] == sample_image_bytes

    @pytest.mark.asyncio
    async def test_decode_raw_base64(self, imagen_tool, sample_image_bytes):
        """Test decoding raw base64 string"""
        b64_string = base64.b64encode(sample_image_bytes).decode('utf-8')
        
        result = await imagen_tool._decode_image_input(b64_string, "image/png")
        
        assert result is not None
        assert result['mime_type'] == 'image/png'
        assert result['data'] == sample_image_bytes

    @pytest.mark.asyncio
    async def test_decode_base64_with_whitespace(self, imagen_tool, sample_image_bytes):
        """Test decoding base64 with whitespace (should be stripped)"""
        b64_string = base64.b64encode(sample_image_bytes).decode('utf-8')
        # Add various whitespace
        b64_with_whitespace = f"{b64_string[:10]}\n{b64_string[10:20]} {b64_string[20:]}"
        
        result = await imagen_tool._decode_image_input(b64_with_whitespace, "image/png")
        
        assert result is not None
        assert result['data'] == sample_image_bytes

    @pytest.mark.asyncio
    async def test_decode_empty_input(self, imagen_tool):
        """Test handling of empty input"""
        result = await imagen_tool._decode_image_input("", None)
        assert result is None
        
        result = await imagen_tool._decode_image_input(None, None)
        assert result is None

    @pytest.mark.asyncio
    async def test_decode_invalid_base64(self, imagen_tool):
        """Test handling of invalid base64"""
        result = await imagen_tool._decode_image_input("not-valid-base64!!!", None)
        assert result is None


class TestImagenToolIntegration:
    """Integration tests for complete workflow"""

    @pytest.mark.asyncio
    async def test_full_generation_workflow(self, imagen_tool, mock_filesystem, mock_context, sample_image_bytes):
        """Test complete image generation workflow"""
        # Mock the Gemini model response
        mock_response = Mock()
        mock_part = Mock()
        mock_inline = Mock()
        mock_inline.data = sample_image_bytes
        mock_inline.mime_type = 'image/png'
        mock_part.inline_data = mock_inline
        mock_response.parts = [mock_part]
        
        mock_model = Mock()
        mock_model.generate_content.return_value = mock_response
        
        with patch('icpy.agent.tools.imagen_tool.genai.GenerativeModel', return_value=mock_model), \
             patch('icpy.agent.tools.imagen_tool.get_contextual_filesystem', return_value=mock_filesystem), \
             patch('icpy.agent.tools.imagen_tool.get_current_context', return_value=mock_context):
            
            result = await imagen_tool.execute(
                prompt="a test image",
                filename="test_output",
                width=100,
                height=100,
                save_to_workspace=True
            )
            
            # Should succeed
            assert result.success
            assert result.data is not None
            assert 'imageData' in result.data
            assert 'filePath' in result.data
            assert result.data['filePath'] == 'test_output.png'
            assert 'resizedTo' in result.data

    @pytest.mark.asyncio
    async def test_edit_workflow_with_file_path(self, imagen_tool, mock_filesystem, mock_context, sample_image_bytes, tmp_path):
        """Test image editing workflow using file:// path"""
        # Create a real file
        test_file = tmp_path / "input.png"
        test_file.write_bytes(sample_image_bytes)
        
        # Mock the Gemini model response
        mock_response = Mock()
        mock_part = Mock()
        mock_inline = Mock()
        mock_inline.data = sample_image_bytes
        mock_inline.mime_type = 'image/png'
        mock_part.inline_data = mock_inline
        mock_response.parts = [mock_part]
        
        mock_model = Mock()
        mock_model.generate_content.return_value = mock_response
        
        # Mock filesystem for saving output
        mock_filesystem.write_file = AsyncMock()
        
        with patch('icpy.agent.tools.imagen_tool.genai.GenerativeModel', return_value=mock_model), \
             patch('icpy.agent.tools.imagen_tool.get_contextual_filesystem', return_value=mock_filesystem), \
             patch('icpy.agent.tools.imagen_tool.get_current_context', return_value=mock_context):
            
            result = await imagen_tool.execute(
                prompt="make it brighter",
                image_data=f"file://{test_file}",
                mode="edit",
                save_to_workspace=True
            )
            
            # Should succeed
            assert result.success
            assert result.data is not None
            assert result.data.get('mode') == 'edit'
            # Should have loaded the input file
            assert mock_model.generate_content.called

    @pytest.mark.asyncio
    async def test_generation_in_remote_context(self, imagen_tool, sample_image_bytes):
        """Test complete generation workflow in remote hop context"""
        remote_context = {
            'contextId': 'remote-server',
            'status': 'connected',
            'host': '192.168.1.100',
            'username': 'testuser',
            'workspaceRoot': '/home/testuser/icotes/workspace'
        }
        
        # Mock filesystem
        mock_filesystem = AsyncMock()
        mock_filesystem.write_file_binary = AsyncMock(return_value=True)
        mock_filesystem.write_file = AsyncMock()
        
        # Mock the Gemini model response
        mock_response = Mock()
        mock_part = Mock()
        mock_inline = Mock()
        mock_inline.data = sample_image_bytes
        mock_inline.mime_type = 'image/png'
        mock_part.inline_data = mock_inline
        mock_response.parts = [mock_part]
        
        mock_model = Mock()
        mock_model.generate_content.return_value = mock_response
        
        with patch('icpy.agent.tools.imagen_tool.genai.GenerativeModel', return_value=mock_model), \
             patch('icpy.agent.tools.imagen_tool.get_contextual_filesystem', return_value=mock_filesystem), \
             patch('icpy.agent.tools.imagen_tool.get_current_context', return_value=remote_context):
            
            result = await imagen_tool.execute(
                prompt="a test image",
                save_to_workspace=True
            )
            
            # Should succeed
            assert result.success
            # Should have attempted remote write via write_file_binary
            assert mock_filesystem.write_file_binary.called


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
