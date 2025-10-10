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
            'host': '192.168.1.100'
        }
        
        # Mock write_file_binary to succeed (preferred path for remote binary writes)
        mock_filesystem.write_file_binary = AsyncMock()
        
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
    async def test_load_image_from_hop(self, imagen_tool, mock_filesystem, sample_image_bytes):
        """Test loading image from remote hop using file:// path"""
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


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
