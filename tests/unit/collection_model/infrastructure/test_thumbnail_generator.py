"""Unit tests for ThumbnailGenerator.

Story 2.13: Thumbnail Generation for AI Tiered Vision Processing
"""

import io

import pytest
from collection_model.infrastructure.thumbnail_generator import ThumbnailGenerator
from PIL import Image


class TestThumbnailGenerator:
    """Tests for ThumbnailGenerator class."""

    @pytest.fixture
    def generator(self) -> ThumbnailGenerator:
        """Create a ThumbnailGenerator instance."""
        return ThumbnailGenerator()

    def _create_test_image(self, width: int, height: int, format: str = "JPEG", mode: str = "RGB") -> bytes:
        """Create a test image as bytes."""
        image = Image.new(mode, (width, height), color="red")
        output = io.BytesIO()
        if format == "JPEG" and mode != "RGB":
            image = image.convert("RGB")
        image.save(output, format=format)
        return output.getvalue()

    # =========================================================================
    # supports_format tests
    # =========================================================================

    def test_supports_format_jpeg(self, generator: ThumbnailGenerator) -> None:
        """Test that JPEG format is supported."""
        assert generator.supports_format("image/jpeg") is True

    def test_supports_format_png(self, generator: ThumbnailGenerator) -> None:
        """Test that PNG format is supported."""
        assert generator.supports_format("image/png") is True

    def test_supports_format_unsupported(self, generator: ThumbnailGenerator) -> None:
        """Test that unsupported formats return False."""
        assert generator.supports_format("image/gif") is False
        assert generator.supports_format("image/webp") is False
        assert generator.supports_format("application/pdf") is False

    # =========================================================================
    # generate_thumbnail tests - successful cases
    # =========================================================================

    def test_generate_thumbnail_large_jpeg(self, generator: ThumbnailGenerator) -> None:
        """Test thumbnail generation for large JPEG image."""
        image_bytes = self._create_test_image(1024, 768)

        result = generator.generate_thumbnail(image_bytes)

        assert result is not None
        # Verify result is valid JPEG
        img = Image.open(io.BytesIO(result))
        assert img.format == "JPEG"
        assert max(img.size) <= 256

    def test_generate_thumbnail_large_png(self, generator: ThumbnailGenerator) -> None:
        """Test thumbnail generation for large PNG image."""
        image_bytes = self._create_test_image(800, 600, format="PNG")

        result = generator.generate_thumbnail(image_bytes)

        assert result is not None
        img = Image.open(io.BytesIO(result))
        assert img.format == "JPEG"  # Output is always JPEG
        assert max(img.size) <= 256

    def test_generate_thumbnail_preserves_aspect_ratio(self, generator: ThumbnailGenerator) -> None:
        """Test that aspect ratio is preserved."""
        # Create 2:1 aspect ratio image
        image_bytes = self._create_test_image(800, 400)

        result = generator.generate_thumbnail(image_bytes)

        assert result is not None
        img = Image.open(io.BytesIO(result))
        # Width should be 256, height should be ~128 to maintain 2:1 ratio
        assert img.size[0] <= 256
        assert img.size[1] <= 256
        # Aspect ratio should be approximately preserved
        original_ratio = 800 / 400
        result_ratio = img.size[0] / img.size[1]
        assert abs(original_ratio - result_ratio) < 0.1

    def test_generate_thumbnail_custom_size(self, generator: ThumbnailGenerator) -> None:
        """Test thumbnail generation with custom size."""
        image_bytes = self._create_test_image(1000, 1000)

        result = generator.generate_thumbnail(image_bytes, size=(128, 128))

        assert result is not None
        img = Image.open(io.BytesIO(result))
        assert max(img.size) <= 128

    def test_generate_thumbnail_custom_quality(self, generator: ThumbnailGenerator) -> None:
        """Test thumbnail generation with custom quality."""
        image_bytes = self._create_test_image(500, 500)

        # High quality
        result_high = generator.generate_thumbnail(image_bytes, quality=95)
        # Low quality
        result_low = generator.generate_thumbnail(image_bytes, quality=20)

        assert result_high is not None
        assert result_low is not None
        # High quality should be larger
        assert len(result_high) > len(result_low)

    def test_generate_thumbnail_rgba_png(self, generator: ThumbnailGenerator) -> None:
        """Test thumbnail generation for PNG with alpha channel."""
        image_bytes = self._create_test_image(500, 500, format="PNG", mode="RGBA")

        result = generator.generate_thumbnail(image_bytes)

        assert result is not None
        img = Image.open(io.BytesIO(result))
        assert img.format == "JPEG"
        assert img.mode == "RGB"  # RGBA converted to RGB

    # =========================================================================
    # generate_thumbnail tests - skip small images
    # =========================================================================

    def test_generate_thumbnail_skip_small_image(self, generator: ThumbnailGenerator) -> None:
        """Test that small images are skipped (return None)."""
        # Image smaller than MIN_THUMBNAIL_DIMENSION
        image_bytes = self._create_test_image(200, 200)

        result = generator.generate_thumbnail(image_bytes)

        assert result is None

    def test_generate_thumbnail_skip_tiny_image(self, generator: ThumbnailGenerator) -> None:
        """Test that very small images are skipped."""
        image_bytes = self._create_test_image(50, 50)

        result = generator.generate_thumbnail(image_bytes)

        assert result is None

    def test_generate_thumbnail_exactly_at_threshold(self, generator: ThumbnailGenerator) -> None:
        """Test image at exactly the minimum dimension threshold."""
        # At threshold - should generate thumbnail
        image_bytes = self._create_test_image(256, 256)

        result = generator.generate_thumbnail(image_bytes)

        assert result is not None

    def test_generate_thumbnail_just_below_threshold(self, generator: ThumbnailGenerator) -> None:
        """Test image just below the minimum dimension threshold."""
        image_bytes = self._create_test_image(255, 255)

        result = generator.generate_thumbnail(image_bytes)

        assert result is None

    # =========================================================================
    # generate_thumbnail tests - error handling
    # =========================================================================

    def test_generate_thumbnail_corrupt_data(self, generator: ThumbnailGenerator) -> None:
        """Test graceful handling of corrupt image data."""
        corrupt_bytes = b"not an image at all"

        result = generator.generate_thumbnail(corrupt_bytes)

        assert result is None  # Graceful degradation

    def test_generate_thumbnail_empty_data(self, generator: ThumbnailGenerator) -> None:
        """Test graceful handling of empty data."""
        result = generator.generate_thumbnail(b"")

        assert result is None

    def test_generate_thumbnail_truncated_data(self, generator: ThumbnailGenerator) -> None:
        """Test graceful handling of truncated image data."""
        image_bytes = self._create_test_image(500, 500)
        truncated = image_bytes[:100]  # Truncate to first 100 bytes

        result = generator.generate_thumbnail(truncated)

        assert result is None

    # =========================================================================
    # Security tests
    # =========================================================================

    def test_generate_thumbnail_oversized_file(self, generator: ThumbnailGenerator) -> None:
        """Test rejection of files exceeding MAX_FILE_SIZE_BYTES."""
        # Create bytes larger than 50MB limit
        oversized_bytes = b"x" * (51 * 1024 * 1024)

        result = generator.generate_thumbnail(oversized_bytes)

        assert result is None

    def test_generate_thumbnail_within_file_size_limit(self, generator: ThumbnailGenerator) -> None:
        """Test acceptance of files within size limit."""
        image_bytes = self._create_test_image(500, 500)

        result = generator.generate_thumbnail(image_bytes)

        assert result is not None
