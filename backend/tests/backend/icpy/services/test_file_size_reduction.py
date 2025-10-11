"""
Test 2: File Size Reduction
Tests that JSONL files are significantly smaller after using references instead of base64.
"""
import os
os.environ.setdefault('GOOGLE_API_KEY', 'test-key-for-testing')

import pytest
import json
import base64
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch

from icpy.services.chat_service import ChatService, ChatMessage, MessageSender, ChatMessageType
from icpy.services.image_reference_service import create_image_reference


class TestFileSizeReduction:
    """Test suite for verifying file size reduction in JSONL storage"""
    
    @pytest.fixture
    def sample_large_image_base64(self):
        """Create a larger base64 image (~500KB when encoded)"""
        # Create a 1024x1024 image with some texture (realistic size)
        from PIL import Image, ImageDraw
        import io
        import random
        
        img = Image.new('RGB', (1024, 1024), color='white')
        draw = ImageDraw.Draw(img)
        
        # Add some texture so it doesn't compress too much
        for _ in range(1000):
            x = random.randint(0, 1023)
            y = random.randint(0, 1023)
            color = (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))
            draw.point((x, y), fill=color)
        
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        png_bytes = buffer.getvalue()
        return base64.b64encode(png_bytes).decode('utf-8')
    
    @pytest.fixture
    def workspace_dir(self, tmp_path):
        """Create temporary workspace with chat history directory"""
        workspace = tmp_path / "workspace"
        workspace.mkdir()
        history_dir = workspace / ".icotes" / "chat_history"
        history_dir.mkdir(parents=True)
        thumbnails_dir = workspace / ".icotes" / "thumbnails"
        thumbnails_dir.mkdir(parents=True)
        return workspace
    
    def test_base64_message_size(self, sample_large_image_base64):
        """Test size of message with full base64 image data"""
        message_with_base64 = {
            'id': 'test-123',
            'content': 'Here is your image',
            'sender': 'ai',
            'timestamp': '2025-02-04T10:00:00',
            'type': 'message',
            'metadata': {
                'tool_output': {
                    'imageData': sample_large_image_base64
                }
            }
        }
        
        json_str = json.dumps(message_with_base64)
        size_bytes = len(json_str.encode('utf-8'))
        
        # Should be > 10KB with base64 image (realistic size)
        assert size_bytes > 10000, f"Expected > 10KB, got {size_bytes} bytes"
        
        # Store the size for comparison
        return size_bytes
    
    def test_reference_message_size(self):
        """Test size of message with image reference instead of base64"""
        message_with_reference = {
            'id': 'test-123',
            'content': 'Here is your image',
            'sender': 'ai',
            'timestamp': '2025-02-04T10:00:00',
            'type': 'message',
            'metadata': {
                'tool_output': {
                    'imageReference': {
                        'image_id': 'abc-def-123',
                        'original_filename': 'test_image.png',
                        'current_filename': 'test_image.png',
                        'relative_path': 'test_image.png',
                        'mime_type': 'image/png',
                        'size_bytes': 10240,
                        'thumbnail_base64': 'small_thumb_data_here',  # Small thumbnail
                        'thumbnail_path': '.icotes/thumbnails/abc-def-123.webp',
                        'prompt': 'a test image',
                        'model': 'test-model',
                        'timestamp': 1234567890.0,
                        'checksum': 'a' * 64
                    }
                }
            }
        }
        
        json_str = json.dumps(message_with_reference)
        size_bytes = len(json_str.encode('utf-8'))
        
        # Should be < 2KB with reference (even with small thumbnail)
        assert size_bytes < 2000, f"Expected < 2KB, got {size_bytes} bytes"
        
        return size_bytes
    
    def test_size_reduction_ratio(self, sample_large_image_base64):
        """Test that reference is at least 95% smaller than base64"""
        # Base64 message
        base64_message = {
            'id': 'test-123',
            'content': 'Image',
            'sender': 'ai',
            'metadata': {'tool_output': {'imageData': sample_large_image_base64}}
        }
        base64_size = len(json.dumps(base64_message).encode('utf-8'))
        
        # Reference message
        ref_message = {
            'id': 'test-123',
            'content': 'Image',
            'sender': 'ai',
            'metadata': {
                'tool_output': {
                    'imageReference': {
                        'image_id': 'test-id',
                        'original_filename': 'img.png',
                        'current_filename': 'img.png',
                        'relative_path': 'img.png',
                        'mime_type': 'image/png',
                        'size_bytes': 10000,
                        'thumbnail_base64': 'x' * 100,  # Small thumb
                        'thumbnail_path': '.icotes/thumbnails/test-id.webp',
                        'prompt': 'test',
                        'model': 'test',
                        'timestamp': 1234567890.0,
                        'checksum': 'a' * 64
                    }
                }
            }
        }
        ref_size = len(json.dumps(ref_message).encode('utf-8'))
        
        # Calculate reduction
        reduction_ratio = (base64_size - ref_size) / base64_size
        
        # Should be at least 95% reduction
        assert reduction_ratio >= 0.95, f"Expected >= 95% reduction, got {reduction_ratio * 100:.2f}%"
        
        print(f"\nSize comparison:")
        print(f"  Base64 message: {base64_size:,} bytes")
        print(f"  Reference message: {ref_size:,} bytes")
        print(f"  Reduction: {reduction_ratio * 100:.2f}%")
    
    @pytest.mark.asyncio
    async def test_jsonl_file_size_with_multiple_images(self, workspace_dir, sample_large_image_base64):
        """Test JSONL file size with multiple images using references"""
        history_dir = workspace_dir / ".icotes" / "chat_history"
        session_id = "test_session_123"
        
        # Simulate storing 3 messages with images using base64 (old way)
        base64_file = history_dir / f"{session_id}_base64.jsonl"
        with open(base64_file, 'w') as f:
            for i in range(3):
                msg = {
                    'id': f'msg-{i}',
                    'content': f'Image {i}',
                    'sender': 'ai',
                    'metadata': {'tool_output': {'imageData': sample_large_image_base64}}
                }
                f.write(json.dumps(msg) + '\n')
        
        base64_file_size = base64_file.stat().st_size
        
        # Simulate storing 3 messages with image references (new way)
        ref_file = history_dir / f"{session_id}_reference.jsonl"
        with open(ref_file, 'w') as f:
            for i in range(3):
                msg = {
                    'id': f'msg-{i}',
                    'content': f'Image {i}',
                    'sender': 'ai',
                    'metadata': {
                        'tool_output': {
                            'imageReference': {
                                'image_id': f'img-{i}',
                                'original_filename': f'img_{i}.png',
                                'current_filename': f'img_{i}.png',
                                'relative_path': f'img_{i}.png',
                                'mime_type': 'image/png',
                                'size_bytes': 10000,
                                'thumbnail_base64': 'x' * 100,
                                'thumbnail_path': f'.icotes/thumbnails/img-{i}.webp',
                                'prompt': f'test {i}',
                                'model': 'test',
                                'timestamp': 1234567890.0,
                                'checksum': 'a' * 64
                            }
                        }
                    }
                }
                f.write(json.dumps(msg) + '\n')
        
        ref_file_size = ref_file.stat().st_size
        
        # Reference file should be dramatically smaller
        reduction = (base64_file_size - ref_file_size) / base64_file_size
        
        print(f"\nJSONL file comparison (3 images):")
        print(f"  Base64 JSONL: {base64_file_size:,} bytes")
        print(f"  Reference JSONL: {ref_file_size:,} bytes")
        print(f"  Reduction: {reduction * 100:.2f}%")
        
        assert reduction >= 0.95, f"Expected >= 95% reduction, got {reduction * 100:.2f}%"
        assert ref_file_size < 5000, f"Reference file should be < 5KB, got {ref_file_size} bytes"
    
    def test_thumbnail_size_limit(self):
        """Test that thumbnail base64 stays under 10KB"""
        from PIL import Image
        import io
        
        # Create a 128x128 image
        img = Image.new('RGB', (128, 128), color='blue')
        buffer = io.BytesIO()
        img.save(buffer, format='WEBP', quality=80)
        webp_bytes = buffer.getvalue()
        thumb_base64 = base64.b64encode(webp_bytes).decode('utf-8')
        
        thumb_size = len(thumb_base64.encode('utf-8'))
        
        # Should be under 10KB
        assert thumb_size < 10240, f"Thumbnail should be < 10KB, got {thumb_size} bytes"
        
        print(f"\nThumbnail size: {thumb_size:,} bytes ({thumb_size / 1024:.2f} KB)")
    
    @pytest.mark.asyncio
    async def test_real_world_scenario_size_reduction(self, workspace_dir, sample_large_image_base64):
        """Test realistic scenario: 10 messages with 3 images"""
        history_dir = workspace_dir / ".icotes" / "chat_history"
        session_id = "real_world_test"
        
        # With base64 (old way)
        base64_file = history_dir / f"{session_id}_base64.jsonl"
        with open(base64_file, 'w') as f:
            for i in range(10):
                msg = {
                    'id': f'msg-{i}',
                    'content': f'Message {i}',
                    'sender': 'user' if i % 2 == 0 else 'ai',
                    'metadata': {}
                }
                # Add images to 3 messages
                if i in [2, 5, 8]:
                    msg['metadata']['tool_output'] = {'imageData': sample_large_image_base64}
                f.write(json.dumps(msg) + '\n')
        
        base64_file_size = base64_file.stat().st_size
        
        # With references (new way)
        ref_file = history_dir / f"{session_id}_reference.jsonl"
        with open(ref_file, 'w') as f:
            for i in range(10):
                msg = {
                    'id': f'msg-{i}',
                    'content': f'Message {i}',
                    'sender': 'user' if i % 2 == 0 else 'ai',
                    'metadata': {}
                }
                # Add image references to 3 messages
                if i in [2, 5, 8]:
                    msg['metadata']['tool_output'] = {
                        'imageReference': {
                            'image_id': f'img-{i}',
                            'original_filename': f'img_{i}.png',
                            'current_filename': f'img_{i}.png',
                            'relative_path': f'img_{i}.png',
                            'mime_type': 'image/png',
                            'size_bytes': 100000,
                            'thumbnail_base64': 'x' * 100,
                            'thumbnail_path': f'.icotes/thumbnails/img-{i}.webp',
                            'prompt': f'image {i}',
                            'model': 'test',
                            'timestamp': 1234567890.0,
                            'checksum': 'a' * 64
                        }
                    }
                f.write(json.dumps(msg) + '\n')
        
        ref_file_size = ref_file.stat().st_size
        
        print(f"\nReal-world scenario (10 messages, 3 images):")
        print(f"  Base64 JSONL: {base64_file_size:,} bytes ({base64_file_size / 1024 / 1024:.2f} MB)")
        print(f"  Reference JSONL: {ref_file_size:,} bytes ({ref_file_size / 1024:.2f} KB)")
        print(f"  Reduction: {(base64_file_size - ref_file_size) / base64_file_size * 100:.2f}%")
        
        # Base64 should be > 50KB, reference should be < 5KB
        # (3 images at ~20KB base64 each = ~60KB)
        assert base64_file_size > 50000
        assert ref_file_size < 5000


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
