"""
Image enhancer — remove background + upscale product images.
Uses rembg for background removal and Pillow for processing.
"""
import io
from pathlib import Path

from PIL import Image, ImageEnhance, ImageFilter

from core.logger import logger


async def remove_background(image_bytes: bytes) -> bytes:
    from rembg import remove
    result = remove(image_bytes)
    logger.info("bg_removed", input_size=len(image_bytes), output_size=len(result))
    return result


async def enhance_product_image(
    image_bytes: bytes,
    target_size: tuple[int, int] = (800, 800),
    bg_color: tuple[int, int, int] = (255, 255, 255),
    sharpen: bool = True,
    brightness: float = 1.05,
    contrast: float = 1.1,
) -> bytes:
    # Remove background
    no_bg = await remove_background(image_bytes)

    img = Image.open(io.BytesIO(no_bg)).convert("RGBA")

    # Create white background
    canvas = Image.new("RGBA", target_size, (*bg_color, 255))

    # Resize product to fit in canvas with padding
    ratio = min(
        (target_size[0] * 0.85) / img.width,
        (target_size[1] * 0.85) / img.height,
    )
    new_size = (int(img.width * ratio), int(img.height * ratio))
    img = img.resize(new_size, Image.Resampling.LANCZOS)

    # Center on canvas
    offset = (
        (target_size[0] - new_size[0]) // 2,
        (target_size[1] - new_size[1]) // 2,
    )
    canvas.paste(img, offset, img)

    # Convert to RGB
    result = canvas.convert("RGB")

    # Enhance
    if sharpen:
        result = result.filter(ImageFilter.SHARPEN)

    if brightness != 1.0:
        result = ImageEnhance.Brightness(result).enhance(brightness)

    if contrast != 1.0:
        result = ImageEnhance.Contrast(result).enhance(contrast)

    # Export
    buf = io.BytesIO()
    result.save(buf, format="JPEG", quality=90)
    output = buf.getvalue()

    logger.info("image_enhanced", input_size=len(image_bytes), output_size=len(output), target=target_size)
    return output


async def batch_enhance(
    image_paths: list[str],
    output_dir: str,
    **kwargs,
) -> list[str]:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    results = []
    for path in image_paths:
        try:
            with open(path, "rb") as f:
                image_bytes = f.read()

            enhanced = await enhance_product_image(image_bytes, **kwargs)

            out_file = output_path / f"enhanced_{Path(path).name}"
            with open(out_file, "wb") as f:
                f.write(enhanced)

            results.append(str(out_file))
            logger.info("image_batch_processed", source=path, output=str(out_file))
        except Exception as e:
            logger.error("image_batch_failed", source=path, error=str(e))

    return results
