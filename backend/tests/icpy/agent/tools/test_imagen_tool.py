"""
Tests for ImagenTool with Phase 9 updates (google-genai SDK with native aspect_ratio)
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
def mock_genai_client():
    """Mock Google Gen AI SDK client (v1.60+)"""
    # Create a mock response with image parts
    mock_response = MagicMock()
    mock_part = MagicMock()
    mock_inline_data = MagicMock()
    
    # Create a minimal PNG for the mock response
    try:
        from PIL import Image
        img = Image.new('RGB', (10, 10), color='blue')
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        mock_inline_data.data = buffer.getvalue()
    except ImportError:
        mock_inline_data.data = base64.b64decode(
            'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=='
        )
    
    mock_inline_data.mime_type = 'image/png'
    mock_part.inline_data = mock_inline_data
    mock_response.parts = [mock_part]
    mock_response.text = None
    
    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = mock_response
    
    # Patch both the client and the provider
    with patch('icpy.agent.tools.imagen_tool.GENAI_PROVIDER', 'google-genai'), \
         patch('icpy.agent.tools.imagen_tool.GENAI_AVAILABLE', True):
        yield mock_client


@pytest.fixture
def mock_filesystem(tmp_path):
    """Mock contextual filesystem with proper root_path pointing to tmp_path for cleanup"""
    fs = AsyncMock()
    fs.write_file = AsyncMock()
    fs.read_file = AsyncMock()
    # Set root_path to tmp_path so files are written to pytest's temp directory
    # This ensures automatic cleanup after tests
    fs.root_path = str(tmp_path)
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
def imagen_tool(mock_genai_client):
    """Create ImagenTool instance with mocked environment and SDK"""
    with patch.dict(os.environ, {'GOOGLE_API_KEY': 'test-key'}):
        tool = ImagenTool()
        tool._genai_client = mock_genai_client
        return tool


class TestImagenToolBasic:
    """Test basic ImagenTool functionality"""

    def test_init(self, imagen_tool):
        """Test tool initialization"""
        assert imagen_tool.name == "generate_image"
        assert "custom filenames" in imagen_tool.description
        assert "hop contexts" in imagen_tool.description
        
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
            # Should return tuple of (filename, absolute_path)
            assert result is not None
            assert isinstance(result, tuple)
            assert len(result) == 2
            filename, absolute_path = result
            assert filename.endswith('.png')
            assert absolute_path is not None

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
            
            # Should return tuple and use custom filename
            assert isinstance(result, tuple)
            filename, absolute_path = result
            assert filename == "my_custom_image.png"

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
            
            # Should return tuple with generated filename containing sanitized prompt
            assert isinstance(result, tuple)
            filename, absolute_path = result
            assert "generated_image" in filename
            assert "blue_circle" in filename or "a_blue_circle" in filename
            assert filename.endswith('.png')

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
            
            # Should return tuple with sanitized filename
            assert isinstance(result, tuple)
            filename, absolute_path = result
            # Should not contain special characters
            assert '/' not in filename
            assert '\\' not in filename
            assert ':' not in filename
            assert '<' not in filename
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
        # Mock the Google Gen AI SDK response
        mock_response = Mock()
        mock_part = Mock()
        mock_inline = Mock()
        mock_inline.data = sample_image_bytes
        mock_inline.mime_type = 'image/png'
        mock_part.inline_data = mock_inline
        mock_response.parts = [mock_part]
        mock_response.text = None
        
        # Create mock client
        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = mock_response
        
        # Inject the mock client directly
        imagen_tool._genai_client = mock_client
        
        with patch.dict(os.environ, {'GOOGLE_API_KEY': 'test-key'}), \
             patch('icpy.agent.tools.imagen_tool.GENAI_PROVIDER', 'google-genai'), \
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
            assert 'filePath' in result.data
            assert result.data['filePath'] == 'test_output.png'

    @pytest.mark.asyncio
    async def test_edit_workflow_with_file_path(self, imagen_tool, mock_filesystem, mock_context, sample_image_bytes, tmp_path):
        """Test image editing workflow using file:// path"""
        # Create a real file
        test_file = tmp_path / "input.png"
        test_file.write_bytes(sample_image_bytes)
        
        # Mock the Google Gen AI SDK response
        mock_response = Mock()
        mock_part = Mock()
        mock_inline = Mock()
        mock_inline.data = sample_image_bytes
        mock_inline.mime_type = 'image/png'
        mock_part.inline_data = mock_inline
        mock_response.parts = [mock_part]
        mock_response.text = None
        
        # Create mock client
        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = mock_response
        
        # Inject the mock client directly
        imagen_tool._genai_client = mock_client
        
        # Mock filesystem for saving output - configure read_file_binary to return actual bytes
        mock_filesystem.read_file_binary = AsyncMock(return_value=sample_image_bytes)
        mock_filesystem.write_file = AsyncMock()
        
        with patch.dict(os.environ, {'GOOGLE_API_KEY': 'test-key'}), \
             patch('icpy.agent.tools.imagen_tool.GENAI_PROVIDER', 'google-genai'), \
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
            # Should have called the mock client
            assert mock_client.models.generate_content.called

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
        
        # Mock the Google Gen AI SDK response
        mock_response = Mock()
        mock_part = Mock()
        mock_inline = Mock()
        mock_inline.data = sample_image_bytes
        mock_inline.mime_type = 'image/png'
        mock_part.inline_data = mock_inline
        mock_response.parts = [mock_part]
        mock_response.text = None
        
        # Create mock client
        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = mock_response
        
        # Inject the mock client directly
        imagen_tool._genai_client = mock_client
        
        with patch.dict(os.environ, {'GOOGLE_API_KEY': 'test-key'}), \
             patch('icpy.agent.tools.imagen_tool.GENAI_PROVIDER', 'google-genai'), \
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


class TestImagenToolRouteFallback:
    """Tests for route-proxy fallback behavior when GOOGLE_API_KEY is missing."""

    @pytest.mark.asyncio
    async def test_route_fallback_generates_image_success(
        self,
        imagen_tool,
        sample_image_bytes,
        mock_context,
    ):
        """Route fallback should return a successful generated image result."""
        class _Ref:
            image_id = "img_route_123"
            absolute_path = "/tmp/img_route_123.png"
            relative_path = "workspace/images/img_route_123.png"

            def to_dict(self):
                return {
                    "image_id": self.image_id,
                    "absolute_path": self.absolute_path,
                    "relative_path": self.relative_path,
                }

        image_reference_service = AsyncMock()
        image_reference_service.create_reference = AsyncMock(return_value=_Ref())
        image_cache = MagicMock()

        with patch.dict(os.environ, {}, clear=True), \
               patch("icpy.agent.clients.is_icotes_route_enabled", return_value=True), \
             patch.object(imagen_tool, "_execute_route_image_generation", new=AsyncMock(return_value=(
                 sample_image_bytes,
                 "image/png",
                 {
                     "routeProxy": True,
                     "provider": "atlascloud",
                     "requestId": "pred_123",
                     "status": "completed",
                     "attemptedModels": [{"model": "atlascloud/image-v1", "error": None}],
                 },
             ))), \
             patch("icpy.agent.tools.imagen_tool.get_current_context", return_value=mock_context), \
             patch("icpy.services.image_reference_service.get_image_reference_service", return_value=image_reference_service), \
             patch("icpy.services.image_cache.get_image_cache", return_value=image_cache):
            result = await imagen_tool.execute(
                prompt="A horse drinking chocolate",
                save_to_workspace=False,
            )

        assert result.success is True
        assert result.data is not None
        assert result.data.get("routeProxy") is True
        assert result.data.get("provider") == "atlascloud"
        assert result.data.get("routeRequestId") == "pred_123"

    @pytest.mark.asyncio
    async def test_route_fallback_edit_mode_requires_google_key(self, imagen_tool, sample_image_bytes):
        """Route fallback currently supports generation-only, not edit mode."""
        image_b64 = base64.b64encode(sample_image_bytes).decode("utf-8")
        with patch.dict(os.environ, {}, clear=True), \
             patch("icpy.agent.clients.is_icotes_route_enabled", return_value=True):
            result = await imagen_tool.execute(
                prompt="make it brighter",
                image_data=f"data:image/png;base64,{image_b64}",
                mode="edit",
                save_to_workspace=False,
            )

        assert result.success is False
        assert "requires GOOGLE_API_KEY" in (result.error or "")


class TestImagenToolEditContentsStructure:
    """Tests specifically for verifying edit mode API call structure"""
    
    @pytest.mark.asyncio
    async def test_edit_mode_contents_structure(self, imagen_tool, mock_filesystem, mock_context, sample_image_bytes, tmp_path):
        """
        Verify that edit mode sends [image_part, text_instruction] to the API.
        
        This test ensures the fix for the edit mode bug where the API was receiving
        malformed contents structure.
        """
        # Create a real test file
        test_file = tmp_path / "input.png"
        test_file.write_bytes(sample_image_bytes)
        
        # Mock the Google Gen AI SDK response
        mock_response = Mock()
        mock_part = Mock()
        mock_inline = Mock()
        # Return DIFFERENT bytes to prove a new image was generated
        edited_image = sample_image_bytes + b'EDITED'
        mock_inline.data = edited_image
        mock_inline.mime_type = 'image/png'
        mock_part.inline_data = mock_inline
        mock_response.parts = [mock_part]
        mock_response.text = None
        
        # Create mock client that captures the call args
        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = mock_response
        
        # Inject the mock client
        imagen_tool._genai_client = mock_client
        
        # Mock filesystem
        mock_filesystem.read_file_binary = AsyncMock(return_value=sample_image_bytes)
        mock_filesystem.write_file = AsyncMock()
        
        with patch.dict(os.environ, {'GOOGLE_API_KEY': 'test-key'}), \
             patch('icpy.agent.tools.imagen_tool.GENAI_PROVIDER', 'google-genai'), \
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
            assert result.data.get('mode') == 'edit'
            
            # Verify the API was called
            assert mock_client.models.generate_content.called
            
            # Get the call arguments
            call_kwargs = mock_client.models.generate_content.call_args
            contents = call_kwargs.kwargs.get('contents')
            
            # Contents should be a list with exactly 2 elements: [Part, string]
            assert contents is not None
            assert isinstance(contents, list), f"Expected list, got {type(contents)}"
            assert len(contents) == 2, f"Expected 2 elements, got {len(contents)}"
            
            # First element should be Part.from_bytes (not a raw dict)
            image_element = contents[0]
            assert hasattr(image_element, 'inline_data') or hasattr(image_element, 'data'), \
                f"First element should be a Part object, got {type(image_element)}"
            
            # Second element should be the instruction string
            text_element = contents[1]
            assert isinstance(text_element, str), f"Second element should be string, got {type(text_element)}"
            assert "make it brighter" in text_element


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
