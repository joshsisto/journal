"""Journal routes for creating, viewing, and managing entries."""
from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, request, flash, current_app
from flask_login import login_required, current_user
from sqlalchemy import desc
import json
import os
import uuid
import base64

from models import db, JournalEntry, GuidedResponse, JournalTemplate, TemplateQuestion, Location, WeatherData, Photo, Tag
from services.weather_service import weather_service
from .utils import save_photo_from_base64

journal_bp = Blueprint('journal', __name__)


@journal_bp.route('/')
@login_required
def index():
    # Redirect to dashboard
    return redirect(url_for('journal.dashboard'))


@journal_bp.route('/dashboard')
@login_required
def dashboard():
    """Enhanced dashboard with immediate writing and compact design"""
    page = request.args.get('page', 1, type=int)
    entries_per_page = 20  # Show more entries per page for better overview
    
    # Get entries query for current user
    query = JournalEntry.query.filter_by(user_id=current_user.id)
    
    # Paginate entries
    paginated_entries = query.order_by(JournalEntry.created_at.desc()).paginate(
        page=page, per_page=entries_per_page, error_out=False
    )
    entries = paginated_entries.items
    
    # Load available templates
    system_templates = JournalTemplate.query.filter_by(is_system=True).all()
    user_templates = JournalTemplate.query.filter_by(user_id=current_user.id).all()
    
    return render_template(
        'dashboard.html', 
        entries=entries,
        paginated_entries=paginated_entries,
        system_templates=system_templates,
        user_templates=user_templates
    )


@journal_bp.route('/journal/guided', methods=['GET'])
@login_required
def guided_journal():
    """Display the guided journal entry form."""
    system_templates = JournalTemplate.query.filter_by(is_system=True).all()
    user_templates = JournalTemplate.query.filter_by(user_id=current_user.id).all()
    
    return render_template('journal/guided.html', 
                         system_templates=system_templates,
                         user_templates=user_templates)


@journal_bp.route('/journal/guided', methods=['POST'])
@login_required
def guided_journal_post():
    """Handle guided journal entry submission."""
    return dashboard_post_guided()


@journal_bp.route('/dashboard', methods=['POST'])
@login_required
def dashboard_post():
    """Handle journal entry submission from dashboard (both quick and guided)"""
    entry_type = request.form.get('entry_type', 'quick')
    template_id = request.form.get('template_id', '').strip()
    location_data = request.form.get('location_data', '').strip()
    weather_data = request.form.get('weather_data', '').strip()
    photo_data = request.form.get('photo_data', '').strip()
    
    if entry_type == 'guided':
        return dashboard_post_guided()
    else:
        # Handle quick journal entry
        content = request.form.get('content', '').strip()
        if content:
            try:
                entry = JournalEntry(
                    user_id=current_user.id,
                    content=content,
                    entry_type='quick'
                )
                db.session.add(entry)
                db.session.flush()
                
                # Handle location and weather data for quick entries too
                if location_data:
                    try:
                        loc_data = json.loads(location_data)
                        location_record = Location(
                            name=loc_data.get('name', ''),
                            latitude=loc_data.get('latitude'),
                            longitude=loc_data.get('longitude'),
                            address=loc_data.get('address', ''),
                            city=loc_data.get('city', 'Unknown'),
                            state=loc_data.get('state', 'Unknown'),
                            country=loc_data.get('country', ''),
                            postal_code=loc_data.get('postal_code', ''),
                            location_type=loc_data.get('location_type', 'manual')
                        )
                        db.session.add(location_record)
                        db.session.flush()
                        entry.location_id = location_record.id
                    except (json.JSONDecodeError, KeyError) as e:
                        current_app.logger.warning(f"Invalid location data: {e}")
                
                if weather_data:
                    try:
                        weather_info = json.loads(weather_data)
                        weather_record = WeatherData(
                            temperature=weather_info.get('temperature'),
                            weather_condition=weather_info.get('condition', ''),
                            humidity=weather_info.get('humidity'),
                            journal_entry_id=entry.id
                        )
                        db.session.add(weather_record)
                        db.session.flush()
                        entry.weather_id = weather_record.id
                    except (json.JSONDecodeError, KeyError) as e:
                        current_app.logger.warning(f"Invalid weather data: {e}")
                
                # Handle photo data for quick entries
                if photo_data:
                    try:
                        photo_info = json.loads(photo_data)
                        if 'data' in photo_info:
                            # Save photo to disk
                            photo_filename = save_photo_from_base64(photo_info['data'], entry.id)
                            if photo_filename:
                                photo_record = Photo(
                                    journal_entry_id=entry.id,
                                    filename=photo_filename,
                                    original_filename=f"photo_{entry.id}.jpg"
                                )
                                db.session.add(photo_record)
                    except (json.JSONDecodeError, KeyError) as e:
                        current_app.logger.warning(f"Invalid photo data: {e}")
                
                db.session.commit()
                flash('Journal entry saved successfully!', 'success')
            except Exception as e:
                db.session.rollback()
                current_app.logger.error(f"Error saving quick entry: {str(e)}")
                flash('Error saving entry. Please try again.', 'error')
    
    return redirect(url_for('journal.dashboard'))


def dashboard_post_guided():
    """Handle guided journal entry submission (extracted from dashboard_post)."""
    template_id = request.form.get('template_id', '').strip()
    location_data = request.form.get('location_data', '').strip()
    weather_data = request.form.get('weather_data', '').strip()
    photo_data = request.form.get('photo_data', '').strip()
    
    try:
        # Create the journal entry
        entry = JournalEntry(
            user_id=current_user.id,
            content='',  # Guided entries store content in responses
            entry_type='guided',
            template_id=int(template_id) if template_id else None
        )
        db.session.add(entry)
        db.session.flush()  # Get the entry ID
        
        # Handle location and weather data
        location_record = None
        weather_record = None
        
        if location_data:
            try:
                loc_data = json.loads(location_data)
                location_record = Location(
                    name=loc_data.get('name', ''),
                    latitude=loc_data.get('latitude'),
                    longitude=loc_data.get('longitude'),
                    address=loc_data.get('address', ''),
                    city=loc_data.get('city', 'Unknown'),
                    state=loc_data.get('state', 'Unknown'),
                    country=loc_data.get('country', ''),
                    postal_code=loc_data.get('postal_code', ''),
                    location_type=loc_data.get('location_type', 'manual')
                )
                db.session.add(location_record)
                db.session.flush()
                entry.location_id = location_record.id
            except (json.JSONDecodeError, KeyError) as e:
                current_app.logger.warning(f"Invalid location data: {e}")
        
        if weather_data:
            try:
                weather_info = json.loads(weather_data)
                weather_record = WeatherData(
                    temperature=weather_info.get('temperature'),
                    weather_condition=weather_info.get('condition', ''),
                    humidity=weather_info.get('humidity'),
                    journal_entry_id=entry.id
                )
                db.session.add(weather_record)
                db.session.flush()
                entry.weather_id = weather_record.id
            except (json.JSONDecodeError, KeyError) as e:
                current_app.logger.warning(f"Invalid weather data: {e}")
        
        # Handle photo data
        if photo_data:
            try:
                photo_info = json.loads(photo_data)
                if 'data' in photo_info:
                    # Save photo to disk
                    photo_filename = save_photo_from_base64(photo_info['data'], entry.id)
                    if photo_filename:
                        photo_record = Photo(
                            journal_entry_id=entry.id,
                            filename=photo_filename,
                            original_filename=f"photo_{entry.id}.jpg"
                        )
                        db.session.add(photo_record)
            except (json.JSONDecodeError, KeyError) as e:
                current_app.logger.warning(f"Invalid photo data: {e}")
        
        # Store guided responses
        guided_responses = []
        
        if template_id:
            # Load template questions and process responses
            template = JournalTemplate.query.get(int(template_id))
            if template:
                entry_content_set = False
                for question in template.questions.order_by(TemplateQuestion.question_order):
                    response_value = request.form.get(question.question_id, '').strip()
                    if response_value:
                        guided_responses.append(GuidedResponse(
                            journal_entry_id=entry.id,
                            question_id=question.question_id,
                            question_text=question.question_text,
                            response=response_value
                        ))
                        
                        # Set main content from first text response or content/day questions
                        if not entry_content_set and (
                            'content' in question.question_id.lower() or 
                            'day' in question.question_id.lower() or
                            question.question_type == 'text'
                        ):
                            entry.content = response_value
                            entry_content_set = True
        else:
            # Default guided questions
            question_texts = {
                'feeling_scale': 'How are you feeling?',
                'additional_emotions': 'Select emotions',
                'feeling_reason': 'Why do you feel that way?',
                'about_day': 'Tell me about your day',
                'exercise': 'Did you exercise today?',
                'exercise_type': 'What type of workout?',
                'anything_else': 'Anything else to discuss?'
            }
            
            for question_id, question_text in question_texts.items():
                response_value = request.form.get(question_id, '').strip()
                
                # Skip exercise_type if exercise wasn't "Yes"
                if question_id == 'exercise_type':
                    exercise_response = request.form.get('exercise', '').strip()
                    if exercise_response != 'Yes':
                        continue
                
                if response_value:
                    guided_responses.append(GuidedResponse(
                        journal_entry_id=entry.id,
                        question_id=question_id,
                        question_text=question_text,
                        response=response_value
                    ))
                    
                    # Set main content from about_day for entry content
                    if question_id == 'about_day':
                        entry.content = response_value
        
        # Handle tags
        tag_ids = request.form.getlist('tags')
        new_tags_json = request.form.get('new_tags', '[]')
        
        try:
            new_tags = json.loads(new_tags_json) if new_tags_json else []
        except json.JSONDecodeError:
            new_tags = []
        
        # Add existing tags
        if tag_ids:
            for tag_id in tag_ids:
                tag = Tag.query.get(int(tag_id))
                if tag and tag.user_id == current_user.id:
                    entry.tags.append(tag)
        
        # Create new tags
        for tag_name in new_tags:
            if tag_name.strip():
                new_tag = Tag(name=tag_name.strip(), user_id=current_user.id)
                db.session.add(new_tag)
                db.session.flush()
                entry.tags.append(new_tag)
        
        # Add all responses to session
        for response in guided_responses:
            db.session.add(response)
        
        db.session.commit()
        flash('Guided journal entry saved successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error saving guided entry: {str(e)}")
        flash('Error saving guided entry. Please try again.', 'error')
    
    return redirect(url_for('journal.dashboard'))


@journal_bp.route('/entry/<int:entry_id>')
@login_required
def view_entry(entry_id):
    """View individual journal entry with options to delete or have AI conversation"""
    entry = JournalEntry.query.filter_by(id=entry_id, user_id=current_user.id).first_or_404()
    
    return render_template(
        'view_entry.html',
        entry=entry
    )


@journal_bp.route('/entry/<int:entry_id>/delete', methods=['POST'])
@login_required
def delete_entry(entry_id):
    """Delete a journal entry"""
    entry = JournalEntry.query.filter_by(id=entry_id, user_id=current_user.id).first_or_404()
    
    try:
        # Clear weather record references before deletion (if any)
        if entry.weather_id:
            weather_record = db.session.get(WeatherData, entry.weather_id)
            if weather_record and weather_record.journal_entry_id == entry.id:
                weather_record.journal_entry_id = None

        # Clear any other weather records referencing this entry
        WeatherData.query.filter_by(journal_entry_id=entry.id).update({'journal_entry_id': None})
        
        # Flush to ensure weather references are cleared before deleting entry
        db.session.flush()
        
        # Delete guided responses if any
        if entry.guided_responses:
            for response in entry.guided_responses:
                db.session.delete(response)
        
        # Delete the entry itself
        db.session.delete(entry)
        db.session.commit()
        
        flash('Journal entry deleted successfully!', 'success')
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error deleting entry {entry_id}: {str(e)}")
        flash('Error deleting entry. Please try again.', 'error')
    
    return redirect(url_for('journal.dashboard'))


@journal_bp.route('/dashboard/legacy')
@login_required
def dashboard_legacy():
    """Legacy dashboard with full calendar and filtering features"""
    return render_template("dashboard_legacy.html")


@journal_bp.route('/create_template')
@login_required
def create_template():
    """Template creation page"""
    return render_template('journal/create_template.html')


@journal_bp.route('/templates')
@login_required
def templates():
    """View and manage journal templates"""
    # Get user templates
    user_templates = JournalTemplate.query.filter_by(
        user_id=current_user.id,
        is_system=False
    ).order_by(JournalTemplate.name).all()
    
    # Get system templates
    system_templates = JournalTemplate.query.filter_by(
        is_system=True
    ).order_by(JournalTemplate.name).all()
    
    return render_template('journal/templates.html', 
                         user_templates=user_templates,
                         system_templates=system_templates)


@journal_bp.route('/map')
@login_required
def map():
    """View journal entries on a map"""
    # Get all entries with location data
    entries_with_location = JournalEntry.query.filter_by(
        user_id=current_user.id
    ).filter(JournalEntry.location_id.isnot(None)).all()
    
    # Prepare location data for the map
    locations = []
    for entry in entries_with_location:
        if entry.location and entry.location.latitude and entry.location.longitude:
            locations.append({
                'id': entry.id,
                'lat': entry.location.latitude,
                'lng': entry.location.longitude,
                'title': entry.location.name or f"{entry.location.city}, {entry.location.state}",
                'date': entry.created_at.strftime('%B %d, %Y'),
                'preview': entry.content[:100] + '...' if len(entry.content) > 100 else entry.content
            })
    
    return render_template('journal/map.html', locations=locations)