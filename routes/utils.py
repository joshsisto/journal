"""Utility functions for route modules."""
import os
import uuid
import base64
from flask import current_app


def save_photo_from_base64(base64_data, entry_id):
    """Save a base64 encoded photo to disk and return the filename."""
    try:
        # Remove the data URL prefix if it exists
        if ',' in base64_data:
            base64_data = base64_data.split(',')[1]
        
        # Decode the base64 data
        image_data = base64.b64decode(base64_data)
        
        # Create photos directory if it doesn't exist
        photos_dir = os.path.join(current_app.static_folder, 'photos')
        os.makedirs(photos_dir, exist_ok=True)
        
        # Generate unique filename
        filename = f"entry_{entry_id}_{uuid.uuid4().hex[:8]}.jpg"
        filepath = os.path.join(photos_dir, filename)
        
        # Save the image
        with open(filepath, 'wb') as f:
            f.write(image_data)
        
        return filename
        
    except Exception as e:
        current_app.logger.error(f"Error saving photo: {str(e)}")
        return None