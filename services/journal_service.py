from models import db, JournalEntry, Tag, Photo, GuidedResponse, ExerciseLog
from validators import sanitize_journal_content, sanitize_tag_name, validate_color_hex
from werkzeug.utils import secure_filename
import json
import uuid
import os
from flask import current_app
from datetime import datetime
# allowed_file will be passed as parameter

def create_quick_entry(user_id, content, tag_ids, new_tags_json, photos, allowed_file_func):
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

        # Create journal entry
        entry = JournalEntry(
            user_id=user_id,
            content=sanitized_content,
            entry_type='quick'
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
                for tag_data in new_tags_data:
                    try:
                        # Sanitize tag name
                        tag_name = sanitize_tag_name(tag_data.get('name', ''))
                        tag_color = validate_color_hex(tag_data.get('color', '#6c757d'))

                        # Check if tag with this name already exists for this user
                        existing_tag = Tag.query.filter_by(
                            name=tag_name,
                            user_id=user_id
                        ).first()

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
        if photos:
            for photo in photos:
                if photo and photo.filename and allowed_file_func(photo.filename):
                    try:
                        # Create a secure filename with a UUID prefix
                        original_filename = secure_filename(photo.filename)  # Sanitize original filename
                        if len(original_filename) > 255:
                            original_filename = original_filename[-255:]  # Truncate if too long

                        # Create unique filename
                        filename = f"{uuid.uuid4()}_{secure_filename(photo.filename)}"

                        # Save file to upload folder with directory traversal protection
                        upload_folder = os.path.join(current_app.root_path, current_app.config['UPLOAD_FOLDER'])
                        # Ensure filename doesn't contain path separators
                        safe_filename = os.path.basename(filename)
                        if not safe_filename or safe_filename in ('.', '..') or '/' in safe_filename or '\\' in safe_filename:
                            raise ValueError("Invalid filename")
                        photo_path = os.path.join(upload_folder, safe_filename)

                        # Check file size before saving
                        photo.seek(0, os.SEEK_END)
                        file_size = photo.tell()
                        photo.seek(0)  # Reset file pointer

                        if file_size > current_app.config.get('MAX_CONTENT_LENGTH', 16 * 1024 * 1024):
                            # Skip files that are too large
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
                        # Log error but continue with other photos
                        current_app.logger.error(f'Photo upload error: {str(e)}')

        # Commit changes
        db.session.commit()
        return entry, None
    except ValueError as e:
        return None, str(e)
    except Exception as e:
        # Log unexpected errors
        current_app.logger.error(f'Error saving quick journal entry: {str(e)}')
        return None, 'An error occurred while saving your journal entry. Please try again.'

def create_guided_entry(user_id, form_data, tag_ids, new_tags_json, photos, main_content, allowed_file_func):
    """
    Creates a guided journal entry.
    """
    try:
        # First, create the journal entry
        entry = JournalEntry(
            user_id=user_id,
            content=main_content,
            entry_type='guided'
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
                for tag_data in new_tags_data:
                    # Check if tag with this name already exists for this user
                    existing_tag = Tag.query.filter_by(
                        name=tag_data.get('name'),
                        user_id=user_id
                    ).first()

                    if existing_tag:
                        # Use existing tag if it exists
                        if existing_tag not in entry.tags:
                            entry.tags.append(existing_tag)
                    else:
                        # Create new tag
                        new_tag = Tag(
                            name=tag_data.get('name'),
                            color=tag_data.get('color', '#6c757d'),
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

                # Special handling for exercise question
                if question_id == 'exercise' and value == 'Yes':
                    today = datetime.utcnow().date()
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

                # Save the response
                guided_response = GuidedResponse(
                    journal_entry_id=entry.id,
                    question_id=question_id,
                    response=value
                )
                db.session.add(guided_response)

        # Handle photo uploads
        if photos:
            for photo in photos:
                if photo and photo.filename and allowed_file_func(photo.filename):
                    # Create a secure filename with a UUID prefix
                    original_filename = photo.filename
                    filename = f"{uuid.uuid4()}_{secure_filename(photo.filename)}"

                    # Save file to upload folder with directory traversal protection
                    upload_folder = os.path.join(current_app.root_path, current_app.config['UPLOAD_FOLDER'])
                    # Ensure filename doesn't contain path separators
                    safe_filename = os.path.basename(filename)
                    if not safe_filename or safe_filename in ('.', '..') or '/' in safe_filename or '\\' in safe_filename:
                        raise ValueError("Invalid filename")
                    photo_path = os.path.join(upload_folder, safe_filename)
                    photo.save(photo_path)

                    # Create photo record in database
                    new_photo = Photo(
                        journal_entry_id=entry.id,
                        filename=filename,
                        original_filename=original_filename
                    )
                    db.session.add(new_photo)

        db.session.commit()
        return entry, None
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'Error creating guided entry: {e}')
        return None, 'An error occurred while saving your guided journal entry.'