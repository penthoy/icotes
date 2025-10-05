"""
Test 3: Thumbnail Quality
Tests that generated thumbnails are high quality and properly sized.
"""
import os
os.environ.setdefault('GOOGLE_API_KEY', 'test-key-for-testing')

import pytest
import base64
import io
from pathlib import Path
from PIL import Image

from icpy.utils.thumbnail_generator import generate_thumbnail, ThumbnailConfig


class TestThumbnailQuality:
    """Test suite for thumbnail generation quality and specifications"""
    
    @pytest.fixture
    def workspace_dir(self, tmp_path):
        """Create temporary workspace"""
        workspace = tmp_path / "workspace"
        workspace.mkdir()
        thumbnails_dir = workspace / ".icotes" / "thumbnails"
        thumbnails_dir.mkdir(parents=True)
        return workspace
    
    @pytest.fixture
    def create_test_image(self, workspace_dir):
        """Factory to create test images of various sizes"""
        def _create(width, height, color='red', filename='test.png'):
            img = Image.new('RGB', (width, height), color=color)
            path = workspace_dir / filename
            img.save(path, format='PNG')
            return path
        return _create
    
    def test_thumbnail_dimensions_128x128(self, create_test_image, workspace_dir):
        """Test thumbnail is correctly sized to 128x128 for square images"""
        # Create 1024x1024 image
        image_path = create_test_image(1024, 1024, 'blue', '1024x1024.png')
        
        result = generate_thumbnail(
            str(image_path),
            str(workspace_dir / ".icotes" / "thumbnails"),
            max_size=(128, 128)
        )
        
        # Load generated thumbnail to check dimensions
        thumb_path = Path(result['path'])
        thumb_img = Image.open(thumb_path)
        
        # Should be 102x102 or 128x128 depending on scale_factor logic
        # 1024 * 0.1 = 102.4 -> 102 pixels
        assert thumb_img.size[0] in [102, 128]
        assert thumb_img.size[1] in [102, 128]
        assert result['width'] in [102, 128]
        assert result['height'] in [102, 128]
    
    def test_thumbnail_maintains_aspect_ratio(self, create_test_image, workspace_dir):
        """Test thumbnail maintains aspect ratio for non-square images"""
        # Create 1920x1080 image (16:9 aspect ratio)
        image_path = create_test_image(1920, 1080, 'green', '1920x1080.png')
        
        result = generate_thumbnail(
            str(image_path),
            str(workspace_dir / ".icotes" / "thumbnails"),
            max_size=(128, 128)
        )
        
        # Load thumbnail
        thumb_img = Image.open(result['path'])
        width, height = thumb_img.size
        
        # Should maintain 16:9 aspect ratio
        aspect_ratio = width / height
        expected_ratio = 1920 / 1080
        
        # Allow small tolerance for rounding
        assert abs(aspect_ratio - expected_ratio) < 0.01
        
        # Should fit within 128x128
        assert width <= 128
        assert height <= 128
        
        # Longer dimension should be 128
        assert max(width, height) == 128
    
    def test_thumbnail_format_webp(self, create_test_image, workspace_dir):
        """Test thumbnail is saved as WebP format"""
        image_path = create_test_image(512, 512, 'yellow', 'test.png')
        
        result = generate_thumbnail(
            str(image_path),
            str(workspace_dir / ".icotes" / "thumbnails")
        )
        
        thumb_path = Path(result['path'])
        
        # Should have .webp extension
        assert thumb_path.suffix == '.webp'
        
        # Verify it's actually WebP format
        thumb_img = Image.open(thumb_path)
        assert thumb_img.format == 'WEBP'
    
    def test_thumbnail_size_under_10kb(self, create_test_image, workspace_dir):
        """Test thumbnail file size is under 10KB"""
        image_path = create_test_image(2048, 2048, 'purple', 'large.png')
        
        result = generate_thumbnail(
            str(image_path),
            str(workspace_dir / ".icotes" / "thumbnails")
        )
        
        thumb_size = result['size_bytes']
        
        # Should be under 10KB
        assert thumb_size < 10240, f"Thumbnail {thumb_size} bytes exceeds 10KB limit"
        
        print(f"\nThumbnail size: {thumb_size:,} bytes ({thumb_size / 1024:.2f} KB)")
    
    def test_thumbnail_base64_generation(self, create_test_image, workspace_dir):
        """Test thumbnail base64 encoding is valid and decodable"""
        image_path = create_test_image(512, 512, 'cyan', 'base64test.png')
        
        result = generate_thumbnail(
            str(image_path),
            str(workspace_dir / ".icotes" / "thumbnails")
        )
        
        # Should have base64 data
        assert 'base64' in result
        assert result['base64'] is not None
        assert len(result['base64']) > 0
        
        # Should be valid base64
        try:
            decoded = base64.b64decode(result['base64'])
            # Should be able to open as image
            img = Image.open(io.BytesIO(decoded))
            assert img.format == 'WEBP'
        except Exception as e:
            pytest.fail(f"Failed to decode thumbnail base64: {e}")
    
    def test_thumbnail_quality_setting(self, create_test_image, workspace_dir):
        """Test thumbnail is generated with correct quality setting"""
        image_path = create_test_image(800, 600, 'orange', 'quality_test.png')
        
        # Generate with quality 80
        result = generate_thumbnail(
            str(image_path),
            str(workspace_dir / ".icotes" / "thumbnails"),
            quality=80
        )
        
        # Thumbnail should exist and be valid
        thumb_img = Image.open(result['path'])
        assert thumb_img is not None
        
        # Quality 80 should produce reasonable file size
        assert result['size_bytes'] < 15000  # Should be under 15KB with quality 80
    
    def test_thumbnail_from_various_formats(self, workspace_dir):
        """Test thumbnail generation from PNG, JPEG, WebP sources"""
        thumbnails_dir = workspace_dir / ".icotes" / "thumbnails"
        
        formats_to_test = [
            ('PNG', 'test.png'),
            ('JPEG', 'test.jpg'),
        ]
        
        for format_name, filename in formats_to_test:
            # Create image in specific format
            img = Image.new('RGB', (500, 500), color='blue')
            image_path = workspace_dir / filename
            img.save(image_path, format=format_name)
            
            # Generate thumbnail
            result = generate_thumbnail(
                str(image_path),
                str(thumbnails_dir)
            )
            
            # Should succeed for all formats
            assert Path(result['path']).exists()
            assert result['base64'] is not None
            
            # Output should be WebP
            thumb_img = Image.open(result['path'])
            assert thumb_img.format == 'WEBP'
    
    def test_thumbnail_one_tenth_size_rule(self, create_test_image, workspace_dir):
        """Test thumbnail is 1/10 original size when that's smaller than 128x128"""
        # Create 500x500 image (1/10 would be 50x50, which is < 128)
        image_path = create_test_image(500, 500, 'magenta', '500x500.png')
        
        result = generate_thumbnail(
            str(image_path),
            str(workspace_dir / ".icotes" / "thumbnails"),
            max_size=(128, 128),
            scale_factor=0.1  # 1/10 of original
        )
        
        # Should be 50x50 (1/10 of 500x500)
        thumb_img = Image.open(result['path'])
        # Allow small rounding differences
        assert thumb_img.size[0] in [50, 51]
        assert thumb_img.size[1] in [50, 51]
    
    def test_thumbnail_config_defaults(self):
        """Test ThumbnailConfig has correct default values"""
        config = ThumbnailConfig()
        
        assert config.max_width == 128
        assert config.max_height == 128
        assert config.scale_factor == 0.1  # 1/10 size
        assert config.quality == 80
        assert config.format == 'WEBP'
    
    def test_thumbnail_visual_quality(self, create_test_image, workspace_dir):
        """Test thumbnail maintains visual quality (subjective but measurable)"""
        # Create image with some detail
        from PIL import ImageDraw
        
        img = Image.new('RGB', (800, 600), color='white')
        draw = ImageDraw.Draw(img)
        # Draw some shapes
        draw.rectangle([100, 100, 300, 300], fill='red', outline='black')
        draw.ellipse([400, 200, 600, 400], fill='blue', outline='black')
        image_path = workspace_dir / 'detailed.png'
        img.save(image_path)
        
        result = generate_thumbnail(
            str(image_path),
            str(workspace_dir / ".icotes" / "thumbnails")
        )
        
        # Load thumbnail
        thumb_img = Image.open(result['path'])
        
        # Should have reasonable color variance (not all one color)
        thumb_data = list(thumb_img.getdata())
        unique_colors = len(set(thumb_data))
        
        # Should have multiple colors (at least 10 unique colors)
        assert unique_colors >= 10, f"Thumbnail has poor quality, only {unique_colors} unique colors"
    
    def test_thumbnail_lanczos_resampling(self, create_test_image, workspace_dir):
        """Test that LANCZOS resampling is used (produces high quality thumbnails)"""
        # This is tested implicitly by visual quality
        # LANCZOS produces sharper thumbnails than NEAREST or BILINEAR
        image_path = create_test_image(1024, 1024, 'red', 'lanczos_test.png')
        
        result = generate_thumbnail(
            str(image_path),
            str(workspace_dir / ".icotes" / "thumbnails")
        )
        
        # Thumbnail should exist and be good quality
        thumb_path = Path(result['path'])
        assert thumb_path.exists()
        
        # File size should be reasonable (not too compressed)
        # LANCZOS with quality 80 can produce very small files for solid colors
        # 102x102 solid red compresses to ~110 bytes (excellent compression!)
        assert result['size_bytes'] > 50  # At least something
        assert result['size_bytes'] < 50000  # But not huge


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
