from models import db, JournalEntry, Tag, Photo, GuidedResponse, ExerciseLog, Location, WeatherData
from validators import sanitize_journal_content, sanitize_tag_name, validate_color_hex
from werkzeug.utils import secure_filename
import json
import uuid
import os
from flask import current_app
from datetime import datetime
from time_utils import TimeUtils
# allowed_file will be passed as parameter


def _handle_location_and_weather(form_data):
    """Handle location and weather data from form submission.
    
    Args:
        form_data: Dictionary containing form data
        
    Returns:
        Tuple of (location_id, weather_id) or (None, None) if no data
    """
    location_id = None
    weather_id = None
    
    try:
        # Check if we have location data
        has_location_data = any([
            form_data.get('location_name'),
            form_data.get('location_latitude') and form_data.get('location_longitude'),
            form_data.get('location_city'),
            form_data.get('location_address')
        ])
        
        if has_location_data:
            # Create or find location
            location = Location()
            
            # Set location fields
            location.name = form_data.get('location_name', '').strip() or None
            location.address = form_data.get('location_address', '').strip() or None
            location.city = form_data.get('location_city', '').strip() or None
            location.state = form_data.get('location_state', '').strip() or None
            location.country = form_data.get('location_country', '').strip() or None
            
            # Handle coordinates
            try:
                latitude = form_data.get('location_latitude')
                longitude = form_data.get('location_longitude')
                
                if latitude and longitude:
                    location.latitude = float(latitude)
                    location.longitude = float(longitude)
                    location.location_type = 'gps'
                else:
                    location.location_type = 'manual'
            except (ValueError, TypeError):
                location.location_type = 'manual'
            
            # Check if this exact location already exists
            existing_location = None
            if location.latitude and location.longitude:
                # For GPS locations, check for nearby locations (within ~100m)
                lat_range = 0.001  # About 100m in latitude degrees
                lon_range = 0.001  # About 100m in longitude degrees
                
                existing_location = Location.query.filter(
                    Location.latitude.between(
                        location.latitude - lat_range, 
                        location.latitude + lat_range
                    ),
                    Location.longitude.between(
                        location.longitude - lon_range, 
                        location.longitude + lon_range
                    )
                ).first()
            elif location.name:
                # For manual locations, check by name
                existing_location = Location.query.filter_by(
                    name=location.name,
                    city=location.city,
                    state=location.state
                ).first()
            
            if existing_location:
                location_id = existing_location.id
                # Update the existing location's updated_at timestamp
                existing_location.updated_at = datetime.utcnow()
            else:
                # Save new location
                db.session.add(location)
                db.session.flush()  # Get ID without committing
                location_id = location.id
        
        # Check if we have weather data
        has_weather_data = any([
            form_data.get('weather_temperature'),
            form_data.get('weather_condition'),
            form_data.get('weather_humidity')
        ])
        
        if has_weather_data:
            # Create weather record
            weather = WeatherData()
            weather.location_id = location_id
            
            # Set weather fields
            try:
                weather.temperature = float(form_data.get('weather_temperature')) if form_data.get('weather_temperature') else None
            except (ValueError, TypeError):
                weather.temperature = None
            
            weather.temperature_unit = 'celsius'  # Default unit
            weather.weather_condition = form_data.get('weather_condition', '').strip() or None
            weather.weather_description = form_data.get('weather_description', '').strip() or None
            
            try:
                weather.humidity = int(form_data.get('weather_humidity')) if form_data.get('weather_humidity') else None
            except (ValueError, TypeError):
                weather.humidity = None
            
            try:
                weather.wind_speed = float(form_data.get('weather_wind_speed')) if form_data.get('weather_wind_speed') else None
            except (ValueError, TypeError):
                weather.wind_speed = None
            
            try:
                weather.pressure = float(form_data.get('weather_pressure')) if form_data.get('weather_pressure') else None
            except (ValueError, TypeError):
                weather.pressure = None
            
            weather.weather_source = 'manual'  # Default to manual for form entries
            
            # Save weather record
            db.session.add(weather)
            db.session.flush()  # Get ID without committing
            weather_id = weather.id
    
    except Exception as e:
        current_app.logger.error(f"Error handling location/weather data: {e}")
        # Don't fail the entire entry creation for location/weather errors
        
    return location_id, weather_id


def _handle_photo_uploads(entry, photos, allowed_file_func):
    """Handle photo uploads for journal entries.
    
    Args:
        entry: The journal entry to attach photos to
        photos: List of uploaded photo files
        allowed_file_func: Function to validate file extensions
    """
    if not photos:
        return
    
    for photo in photos:
        if photo and photo.filename and allowed_file_func(photo.filename):
            try:
                # Create a secure filename with a UUID prefix
                original_filename = secure_filename(photo.filename)
                if len(original_filename) > 255:
                    original_filename = original_filename[-255:]

                # Create unique filename
                filename = f"{uuid.uuid4()}_{secure_filename(photo.filename)}"

                # Save file to upload folder with directory traversal protection
                upload_folder = os.path.join(current_app.root_path, current_app.config['UPLOAD_FOLDER'])
                safe_filename = os.path.basename(filename)
                if not safe_filename or safe_filename in ('.', '..') or '/' in safe_filename or '\\' in safe_filename:
                    raise ValueError("Invalid filename")
                photo_path = os.path.join(upload_folder, safe_filename)

                # Check file size before saving
                photo.seek(0, os.SEEK_END)
                file_size = photo.tell()
                photo.seek(0)

                if file_size > current_app.config.get('MAX_CONTENT_LENGTH', 16 * 1024 * 1024):
                    current_app.logger.warning(f'Photo upload too large: {file_size} bytes')
                    continue

                # Save the file
                photo.save(photo_path)

                # Create photo record in database
                new_photo = Photo(
                    journal_entry_id=entry.id,
                    filename=filename,
                    original_filename=original_filename
                )
                db.session.add(new_photo)
            except Exception as e:
                current_app.logger.error(f'Photo upload error: {str(e)}')


def create_quick_entry(user_id, content, tag_ids, new_tags_json, photos, allowed_file_func, form_data=None):
    """
    Creates a quick journal entry.
    """
    try:
        # Sanitize content
        sanitized_content = sanitize_journal_content(content)

        # Validate content
        if not sanitized_content or len(sanitized_content.strip()) == 0:
            raise ValueError('Journal entry cannot be empty.')

        if len(sanitized_content) > 10000:  # 10KB limit
            raise ValueError('Journal entry is too long. Please shorten your entry.')

        # Handle location and weather data
        location_id, weather_id = None, None
        if form_data:
            location_id, weather_id = _handle_location_and_weather(form_data)

        # Create journal entry
        entry = JournalEntry(
            user_id=user_id,
            content=sanitized_content,
            entry_type='quick',
            location_id=location_id,
            weather_id=weather_id
        )

        # Add selected existing tags
        valid_tag_ids = []
        if tag_ids:
            # Validate tag IDs (ensure they are integers and belong to the user)
            for tag_id in tag_ids:
                try:
                    tag_id_int = int(tag_id)
                    valid_tag_ids.append(tag_id_int)
                except (ValueError, TypeError):
                    # Skip invalid IDs
                    pass

            # Get tags belonging to the current user
            tags = Tag.query.filter(
                Tag.id.in_(valid_tag_ids),
                Tag.user_id == user_id
            ).all()
            entry.tags = tags
        else:
            entry.tags = []

        # Create and add new tags
        if new_tags_json:
            try:
                new_tags_data = json.loads(new_tags_json)
                
                # Bulk load existing tags to prevent N+1 queries
                tag_names = [sanitize_tag_name(tag_data.get('name', '')) for tag_data in new_tags_data]
                existing_tags = Tag.query.filter(
                    Tag.name.in_(tag_names),
                    Tag.user_id == user_id
                ).all()
                
                # Create a map of existing tags by name
                existing_tags_map = {tag.name: tag for tag in existing_tags}
                
                for tag_data in new_tags_data:
                    try:
                        # Sanitize tag name
                        tag_name = sanitize_tag_name(tag_data.get('name', ''))
                        tag_color = validate_color_hex(tag_data.get('color', '#6c757d'))

                        # Check if tag exists using pre-loaded map
                        existing_tag = existing_tags_map.get(tag_name)

                        if existing_tag:
                            # Use existing tag if it exists
                            if existing_tag not in entry.tags:
                                entry.tags.append(existing_tag)
                        else:
                            # Create new tag
                            new_tag = Tag(
                                name=tag_name,
                                color=tag_color,
                                user_id=user_id
                            )
                            db.session.add(new_tag)
                            db.session.flush()  # Get ID without committing
                            entry.tags.append(new_tag)
                    except Exception as e:
                        # Log error but continue with other tags
                        current_app.logger.warning(f'Tag validation error: {str(e)}')
            except json.JSONDecodeError:
                # If JSON parsing fails, log it but continue
                current_app.logger.warning(f'Invalid JSON for new tags: {new_tags_json[:100]}')

        db.session.add(entry)
        db.session.flush()  # Get ID without committing

        # Handle photo uploads
        _handle_photo_uploads(entry, photos, allowed_file_func)

        # Commit changes
        db.session.commit()
        return entry, None
    except ValueError as e:
        return None, str(e)
    except Exception as e:
        # Log unexpected errors
        current_app.logger.error(f'Error saving quick journal entry: {str(e)}')
        return None, 'An error occurred while saving your journal entry. Please try again.'

def create_guided_entry(user_id, form_data, tag_ids, new_tags_json, photos, main_content, allowed_file_func, template_id=None):
    """
    Creates a guided journal entry.
    
    Args:
        template_id (int, optional): ID of the template used for this entry.
    """
    try:
        # Get the questions to extract question text for responses
        from models import QuestionManager
        questions = QuestionManager.get_questions(template_id)
        question_text_map = {str(q['id']): q['text'] for q in questions}
        
        # Handle location and weather data
        location_id, weather_id = _handle_location_and_weather(form_data)
        
        # First, create the journal entry
        entry = JournalEntry(
            user_id=user_id,
            content=main_content,
            entry_type='guided',
            template_id=template_id,
            location_id=location_id,
            weather_id=weather_id
        )

        # Add selected existing tags
        if tag_ids:
            tags = Tag.query.filter(
                Tag.id.in_(tag_ids),
                Tag.user_id == user_id
            ).all()
            entry.tags = tags
        else:
            entry.tags = []

        # Create and add new tags
        if new_tags_json:
            try:
                new_tags_data = json.loads(new_tags_json)
                
                # Bulk load existing tags to prevent N+1 queries
                tag_names = [sanitize_tag_name(tag_data.get('name', '')) for tag_data in new_tags_data]
                existing_tags = Tag.query.filter(
                    Tag.name.in_(tag_names),
                    Tag.user_id == user_id
                ).all()
                
                # Create a map of existing tags by name
                existing_tags_map = {tag.name: tag for tag in existing_tags}
                
                for tag_data in new_tags_data:
                    # Sanitize tag name
                    tag_name = sanitize_tag_name(tag_data.get('name', ''))
                    tag_color = validate_color_hex(tag_data.get('color', '#6c757d'))
                    
                    # Check if tag exists using pre-loaded map
                    existing_tag = existing_tags_map.get(tag_name)

                    if existing_tag:
                        # Use existing tag if it exists
                        if existing_tag not in entry.tags:
                            entry.tags.append(existing_tag)
                    else:
                        # Create new tag
                        new_tag = Tag(
                            name=tag_name,
                            color=tag_color,
                            user_id=user_id
                        )
                        db.session.add(new_tag)
                        db.session.flush()  # Get ID without committing
                        entry.tags.append(new_tag)
            except json.JSONDecodeError:
                # If JSON parsing fails, log it but continue
                current_app.logger.warning(f'Invalid JSON for new tags: {new_tags_json[:100]}')

        db.session.add(entry)
        db.session.flush()  # Get the ID without committing

        # Process form data
        for key, value in form_data.items():
            if key.startswith('question_'):
                question_id = key.replace('question_', '')

                # Special handling for exercise question - only track "Yes" responses
                # Keep asking until user says "Yes", then stop for that day
                if question_id == 'exercise' and value == 'Yes':
                    today = TimeUtils.get_local_today()
                    exercise_log = ExerciseLog.query.filter_by(
                        user_id=user_id,
                        date=today
                    ).first()

                    if not exercise_log:
                        exercise_log = ExerciseLog(
                            user_id=user_id,
                            date=today,
                            has_exercised=True
                        )
                        db.session.add(exercise_log)
                    else:
                        exercise_log.has_exercised = True

                    # If there's an exercise type question, get its value and update workout_type
                    workout_type = form_data.get('question_exercise_type')
                    if workout_type:
                        exercise_log.workout_type = workout_type

                # Handle additional emotions (JSON array from multiselect)
                if question_id == 'additional_emotions' and value:
                    # Store emotions as a JSON string
                    value = value

                # Get the question text for this question_id
                question_text = question_text_map.get(question_id, '')
                
                # Save the response
                guided_response = GuidedResponse(
                    journal_entry_id=entry.id,
                    question_id=question_id,
                    question_text=question_text,
                    response=value
                )
                db.session.add(guided_response)

        # Handle photo uploads
        _handle_photo_uploads(entry, photos, allowed_file_func)

        db.session.commit()
        return entry, None
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'Error creating guided entry: {e}')
        return None, 'An error occurred while saving your guided journal entry.'