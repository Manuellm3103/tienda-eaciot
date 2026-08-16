"""AI product photo enhancement service (#14 on the innovation roadmap).

Provides background removal, auto-contrast/brightness, standard ecommerce
resizing, and social-media square generation. Depends on Pillow (already in
project) and rembg (optional).
"""
import io
from typing import Optional


class ImageEnhancementService:
    """Enhance product photos with optional background removal."""

    def _ensure_pillow(self):
        try:
            from PIL import Image, ImageEnhance
            return Image, ImageEnhance
        except ImportError as exc:
            raise RuntimeError("Pillow is not installed") from exc

    def _ensure_rembg(self):
        try:
            from rembg import remove
            return remove
        except ImportError as exc:
            raise RuntimeError("rembg is not installed") from exc

    def enhance_product_photo(self, image_bytes: bytes) -> bytes:
        """Remove background, adjust contrast/brightness, resize to 800x800."""
        Image, ImageEnhance = self._ensure_pillow()
        remove = self._ensure_rembg()

        img = Image.open(io.BytesIO(image_bytes))
        if img.mode not in ("RGB", "RGBA"):
            img = img.convert("RGBA")

        # Auto-contrast and brightness
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(1.2)
        enhancer = ImageEnhance.Brightness(img)
        img = enhancer.enhance(1.1)

        # Remove background
        img = remove(img)

        # Standardize size
        img = img.resize((800, 800), Image.LANCZOS)

        output = io.BytesIO()
        img.save(output, format="PNG", optimize=True)
        return output.getvalue()

    def generate_social_media_square(
        self,
        image_bytes: bytes,
        text: Optional[str] = None,
    ) -> bytes:
        """Generate a 1080x1080 social-media-ready square image."""
        Image, ImageEnhance = self._ensure_pillow()

        img = Image.open(io.BytesIO(image_bytes))
        if img.mode != "RGBA":
            img = img.convert("RGBA")

        # Crop to square from center
        width, height = img.size
        size = min(width, height)
        left = (width - size) // 2
        top = (height - size) // 2
        img = img.crop((left, top, left + size, top + size))
        img = img.resize((1080, 1080), Image.LANCZOS)

        if text:
            from PIL import ImageDraw, ImageFont
            draw = ImageDraw.Draw(img)
            # Use default font; size may vary by platform
            try:
                font = ImageFont.truetype("arial.ttf", 72)
            except Exception:
                font = ImageFont.load_default()

            # Draw text with a dark translucent strip at the bottom
            overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
            overlay_draw = ImageDraw.Draw(overlay)
            overlay_draw.rectangle((0, 900, 1080, 1080), fill=(0, 0, 0, 160))
            img = Image.alpha_composite(img, overlay)
            draw = ImageDraw.Draw(img)
            bbox = draw.textbbox((0, 0), text, font=font)
            text_width = bbox[2] - bbox[0]
            text_height = bbox[3] - bbox[1]
            x = (1080 - text_width) // 2
            y = 900 + (180 - text_height) // 2
            draw.text((x, y), text, fill=(255, 255, 255, 255), font=font)

        output = io.BytesIO()
        img.save(output, format="PNG", optimize=True)
        return output.getvalue()


image_enhance_service = ImageEnhancementService()
