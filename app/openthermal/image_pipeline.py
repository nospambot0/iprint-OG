"""384-dot SC03h image preview preparation.

This module intentionally does not implement iPrint's proprietary compression.
"""
from PIL import Image, ImageOps

SC03H_WIDTH = 384


def prepare_monochrome(image: Image.Image, *, width: int = SC03H_WIDTH,
                       threshold: int = 160, dither: bool = True) -> Image.Image:
    """Fit an image to the printer width; return a 1-bit preview raster."""
    if width <= 0 or width % 8:
        raise ValueError("width must be a positive multiple of 8")
    if not 0 <= threshold <= 255:
        raise ValueError("threshold must be between 0 and 255")
    src = ImageOps.exif_transpose(image).convert("RGB")
    target_h = max(1, round(src.height * width / src.width))
    resized = src.resize((width, target_h), Image.Resampling.LANCZOS)
    padded_h = ((target_h + 7) // 8) * 8
    canvas = Image.new("RGB", (width, padded_h), "white")
    canvas.paste(resized, (0, 0))
    gray = ImageOps.grayscale(canvas)
    if dither:
        return gray.convert("1", dither=Image.Dither.FLOYDSTEINBERG)
    return gray.point(lambda p: 255 if p >= threshold else 0, mode="1")


def raster_bytes_msb(image_1bit: Image.Image) -> bytes:
    """Pack row-wise MSB-first raw raster bytes for diagnostics, not BLE printing."""
    img = image_1bit.convert("1")
    if img.width % 8:
        raise ValueError("image width must be divisible by 8")
    out = bytearray()
    pixels = img.load()
    for y in range(img.height):
        for x0 in range(0, img.width, 8):
            value = 0
            for bit in range(8):
                if pixels[x0 + bit, y] == 0:
                    value |= 0x80 >> bit
            out.append(value)
    return bytes(out)
