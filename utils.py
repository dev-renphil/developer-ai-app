import hmac
import hashlib
import base64
import os
import io
import logging

from PIL import Image
from typing import Optional
from dotenv import load_dotenv

logger = logging.getLogger(__name__)
load_dotenv()
SECRET_KEY = os.getenv("SECRET_KEY").encode()

def generate_signature(payload: str) -> str:
    signature = hmac.new(SECRET_KEY, payload.encode(), hashlib.sha256).digest()
    return base64.b64encode(signature).decode()

def verify_signature(payload: str, signature: str) -> bool:
    expected = generate_signature(payload)
    return hmac.compare_digest(expected, signature)

def encode_image_to_base64_compressed(
    filepath: str,
    quality: int = 85,
    max_size: Optional[int] = 2048,
    format: str = "JPEG"
) -> str:
    """
    Compress and encode an image to base64 string.   
    Args:
        filepath: Path to the image file to compress and encode
        quality: JPEG quality (1-100, default: 85). Higher values = better quality but larger size.
                 Recommended: 85-90 for OpenAI Vision API
        max_size: Maximum width/height in pixels. Images larger than this will be resized.
                 Set to None to disable resizing. Default: 2048 (OpenAI's recommended max)
        format: Output image format. Default: "JPEG"
    
    Returns:
        Base64-encoded string of the compressed image
    
    Raises:
        FileNotFoundError: If the image file doesn't exist
        IOError: If the image cannot be opened or processed
    """
    original_size = os.path.getsize(filepath)
    original_size_kb = original_size / 1024
    
    img = Image.open(filepath)
    original_dimensions = (img.width, img.height)
    
    resized = False
    if max_size and (img.width > max_size or img.height > max_size):
        # Maintain aspect ratio
        img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
        resized = True
    
    # Convert to RGB if necessary (JPEG doesn't support transparency)
    mode_changed = False
    if img.mode in ('RGBA', 'LA', 'P'):
        background = Image.new('RGB', img.size, (255, 255, 255))
        if img.mode == 'P':
            img = img.convert('RGBA')
        # Paste image onto background, using alpha channel as mask if available
        if img.mode == 'RGBA':
            background.paste(img, mask=img.split()[-1])  # Use alpha channel as mask
        else:
            background.paste(img)
        img = background
        mode_changed = True
    elif img.mode != 'RGB':
        img = img.convert('RGB')
        mode_changed = True
    
    # Compress to JPEG (or specified format)
    buffer = io.BytesIO()
    img.save(
        buffer,
        format=format,
        quality=quality,
        optimize=True 
    )
    buffer.seek(0)
    compressed_bytes = buffer.read()
    compressed_size = len(compressed_bytes)
    compressed_size_kb = compressed_size / 1024
    
    compression_ratio = (1 - compressed_size / original_size) * 100 if original_size > 0 else 0
    
    logger.info(
        f"[IMAGE_COMPRESSION] {os.path.basename(filepath)}: "
        f"{original_size_kb:.1f}KB → {compressed_size_kb:.1f}KB ({compression_ratio:.0f}% reduction)"
    )
    
    base64_encoded = base64.b64encode(compressed_bytes).decode("utf-8")
    
    return base64_encoded


def encode_image_to_base64(filepath: str) -> str:
    """
    Encode an image to base64 string without compression.
    Args:
        filepath: Path to the image file to encode
    
    Returns:
        Base64-encoded string of the image
    """
    with open(filepath, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")
