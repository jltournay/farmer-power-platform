"""Thumbnail generator for image processing.

This module provides the ThumbnailGenerator class for generating thumbnails
from images during ingestion. Thumbnails are used by AI Model's Tiered Vision
processing to reduce LLM costs.

Story 2.13: Thumbnail Generation for AI Tiered Vision Processing
"""

import io
from typing import ClassVar

import structlog
from PIL import Image

logger = structlog.get_logger(__name__)


class ThumbnailGenerator:
    """Generator for image thumbnails.

    Generates JPEG thumbnails from images while preserving aspect ratio.
    Used by ZipExtractionProcessor for image files.

    Key behaviors:
    - Small images (max dimension < 256px): Skip thumbnail, return None
    - Large images: Resize to fit within size while preserving aspect ratio
    - Corrupt images: Return None (graceful degradation)
    - Unsupported formats: Return None

    Attributes:
        SUPPORTED_MIME_TYPES: Set of MIME types that can be processed.
        MIN_THUMBNAIL_DIMENSION: Minimum dimension for thumbnail generation.
        MAX_IMAGE_DIMENSION: Maximum allowed image dimension (security).
        MAX_FILE_SIZE_BYTES: Maximum allowed file size (security).
    """

    SUPPORTED_MIME_TYPES: ClassVar[set[str]] = {"image/jpeg", "image/png"}
    MIN_THUMBNAIL_DIMENSION: int = 256  # Skip if image smaller than this
    MAX_IMAGE_DIMENSION: int = 10000  # Prevent decompression bombs
    MAX_FILE_SIZE_BYTES: int = 50 * 1024 * 1024  # 50MB

    def supports_format(self, mime_type: str) -> bool:
        """Check if the given MIME type is supported for thumbnail generation.

        Args:
            mime_type: The MIME type to check (e.g., "image/jpeg").

        Returns:
            True if the format is supported, False otherwise.
        """
        return mime_type in self.SUPPORTED_MIME_TYPES

    def generate_thumbnail(
        self,
        image_bytes: bytes,
        size: tuple[int, int] = (256, 256),
        quality: int = 60,
    ) -> bytes | None:
        """Generate a thumbnail from image bytes.

        Preserves aspect ratio by fitting the image within the given size
        using PIL's thumbnail() method. Converts to RGB for JPEG output.

        Args:
            image_bytes: The source image as bytes.
            size: Maximum dimensions (width, height) for the thumbnail.
                  Defaults to (256, 256).
            quality: JPEG quality (1-100). Defaults to 60.

        Returns:
            Thumbnail as JPEG bytes, or None if:
            - Image is too small (max dimension < MIN_THUMBNAIL_DIMENSION)
            - Image is corrupt or invalid
            - Image dimensions exceed MAX_IMAGE_DIMENSION
            - File size exceeds MAX_FILE_SIZE_BYTES
            - Any other error occurs (graceful degradation)
        """
        try:
            # Validate file size BEFORE opening (security)
            if len(image_bytes) > self.MAX_FILE_SIZE_BYTES:
                logger.warning(
                    "Image too large for thumbnail generation",
                    size_bytes=len(image_bytes),
                    max_size_bytes=self.MAX_FILE_SIZE_BYTES,
                )
                return None

            # Open image from bytes
            image = Image.open(io.BytesIO(image_bytes))

            # Validate dimensions (prevent decompression bombs)
            if max(image.size) > self.MAX_IMAGE_DIMENSION:
                logger.warning(
                    "Image dimensions too large for thumbnail generation",
                    width=image.size[0],
                    height=image.size[1],
                    max_dimension=self.MAX_IMAGE_DIMENSION,
                )
                return None

            # Skip small images - no benefit to resizing up
            # AI Model will use original directly
            if max(image.size) < self.MIN_THUMBNAIL_DIMENSION:
                logger.debug(
                    "Image too small for thumbnail, skipping",
                    width=image.size[0],
                    height=image.size[1],
                    min_dimension=self.MIN_THUMBNAIL_DIMENSION,
                )
                return None

            # Convert to RGB if needed (RGBA, P modes can't be saved as JPEG)
            if image.mode in ("RGBA", "P", "LA", "L"):
                # Create white background for transparency
                if image.mode in ("RGBA", "LA", "P"):
                    background = Image.new("RGB", image.size, (255, 255, 255))
                    if image.mode == "P":
                        image = image.convert("RGBA")
                    background.paste(image, mask=image.split()[-1] if image.mode in ("RGBA", "LA") else None)
                    image = background
                else:
                    image = image.convert("RGB")

            # Resize preserving aspect ratio
            # thumbnail() modifies in place and fits within size
            image.thumbnail(size, Image.Resampling.LANCZOS)

            # Save to bytes as JPEG
            output = io.BytesIO()
            image.save(output, format="JPEG", quality=quality)

            thumbnail_bytes = output.getvalue()

            logger.debug(
                "Thumbnail generated successfully",
                original_size=len(image_bytes),
                thumbnail_size=len(thumbnail_bytes),
                dimensions=image.size,
            )

            return thumbnail_bytes

        except Exception as e:
            # Graceful degradation - log warning and return None
            logger.warning(
                "Thumbnail generation failed",
                error=str(e),
                exc_info=True,
            )
            return None
