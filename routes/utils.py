"""Utility functions for route modules."""
import os
import uuid
import base64
import imghdr
import struct
from flask import current_app


# Magic bytes for common image formats
IMAGE_MAGIC_BYTES = {
    b'\xFF\xD8\xFF': 'jpeg',
    b'\x89\x50\x4E\x47\x0D\x0A\x1A\x0A': 'png',
    b'\x47\x49\x46\x38': 'gif',
    b'\x42\x4D': 'bmp',
}

# Maximum allowed file size (5MB)
MAX_PHOTO_SIZE = 5 * 1024 * 1024


def validate_image_file(image_data):
    """
    Validate that the uploaded file is actually an image using magic bytes.

    SECURITY: This prevents malicious file uploads disguised as images.

    Args:
        image_data: Raw bytes of the uploaded file

    Returns:
        tuple: (is_valid, file_format, error_message)

    Raises:
        ValueError: If file type is invalid or file is too large
    """
    # Check file size
    if len(image_data) > MAX_PHOTO_SIZE:
        raise ValueError(f"Image file too large. Maximum size is {MAX_PHOTO_SIZE // (1024*1024)}MB")

    # Check if file is empty
    if len(image_data) < 10:  # Minimum size for any valid image
        raise ValueError("Image file is empty or too small")

    # Check magic bytes (file signature)
    detected_format = None
    for magic_bytes, format_name in IMAGE_MAGIC_BYTES.items():
        if image_data.startswith(magic_bytes):
            detected_format = format_name
            break

    if detected_format is None:
        # Try imghdr as a fallback
        try:
            detected_format = imghdr.what(None, h=image_data)
        except Exception:
            pass

    if detected_format not in {'jpeg', 'jpg', 'png', 'gif', 'bmp'}:
        raise ValueError(
            f"Invalid image format. Detected: {detected_format or 'unknown'}. "
            f"Only JPEG, PNG, and GIF are allowed."
        )

    # Additional verification: try to parse the image structure
    if detected_format in ('jpeg', 'jpg'):
        # Basic JPEG validation - check for SOI and EOI markers
        if not image_data.startswith(b'\xFF\xD8\xFF'):
            raise ValueError("Invalid JPEG file: missing SOI marker")
        # Look for End of Image marker (FF D9) somewhere in the file
        if b'\xFF\xD9' not in image_data[-100:]:  # Check last 100 bytes
            # Not a critical error, but suspicious
            current_app.logger.warning("JPEG file may be incomplete (missing EOI marker)")

    elif detected_format == 'png':
        # PNG validation
        if not image_data.startswith(b'\x89\x50\x4E\x47\x0D\x0A\x1A\x0A'):
            raise ValueError("Invalid PNG file: incorrect signature")

    elif detected_format == 'gif':
        # GIF validation
        if not (image_data.startswith(b'GIF87a') or image_data.startswith(b'GIF89a')):
            raise ValueError("Invalid GIF file: incorrect signature")

    return True, detected_format, None


def save_photo_from_base64(base64_data, entry_id):
    """
    Save a base64 encoded photo to disk and return the filename.

    SECURITY: Includes file type validation using magic bytes.

    Args:
        base64_data: Base64 encoded image data (with or without data URL prefix)
        entry_id: Journal entry ID for the photo

    Returns:
        str: Filename if successful, None if failed
    """
    try:
        # Remove the data URL prefix if it exists (e.g., "data:image/jpeg;base64,")
        if ',' in base64_data:
            base64_data = base64_data.split(',')[1]

        # Decode the base64 data
        try:
            image_data = base64.b64decode(base64_data, validate=True)
        except Exception as e:
            current_app.logger.warning(f"Invalid base64 data: {str(e)}")
            raise ValueError("Invalid base64 image data")

        # SECURITY: Validate the file type using magic bytes
        is_valid, file_format, error_msg = validate_image_file(image_data)
        if not is_valid:
            current_app.logger.warning(f"Image validation failed: {error_msg}")
            raise ValueError(error_msg)

        # Determine appropriate file extension
        extension_map = {
            'jpeg': 'jpg',
            'jpg': 'jpg',
            'png': 'png',
            'gif': 'gif',
            'bmp': 'bmp',
        }
        extension = extension_map.get(file_format, 'jpg')

        # Use the configured upload folder
        upload_folder = current_app.config.get('UPLOAD_FOLDER', 'uploads/photos')
        photos_dir = os.path.join(current_app.root_path, upload_folder)
        os.makedirs(photos_dir, exist_ok=True)

        # Generate unique filename with correct extension
        filename = f"entry_{entry_id}_{uuid.uuid4().hex[:8]}.{extension}"
        filepath = os.path.join(photos_dir, filename)

        # Save the image
        with open(filepath, 'wb') as f:
            f.write(image_data)

        current_app.logger.info(f"Photo saved: {filepath} (format: {file_format}, size: {len(image_data)} bytes)")
        return filename

    except ValueError as e:
        # Re-raise validation errors
        current_app.logger.warning(f"Photo validation error: {str(e)}")
        return None
    except Exception as e:
        current_app.logger.error(f"Error saving photo: {str(e)}")
        return None