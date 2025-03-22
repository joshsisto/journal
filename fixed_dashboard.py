"""
Simplified dashboard implementation for troubleshooting.
"""

from datetime import datetime, timedelta
from sqlalchemy import extract, func
from flask import render_template, request, redirect, url_for
from flask_login import login_required, current_user

from models import db, JournalEntry, GuidedResponse, Tag

def get_entries_by_month(user_id):
    # This approach works better with SQLite
    entries = JournalEntry.query.filter_by(user_id=user_id).all()
    
    # Group by year and month manually
    result = {}
    for entry in entries:
        year = entry.created_at.strftime('%Y')
        month = entry.created_at.strftime('%m')
        
        if year not in result:
            result[year] = {}
        
        if month not in result[year]:
            result[year][month] = 0
            
        result[year][month] += 1
    
    # Format for the template
    timeline_data = []
    for year in sorted(result.keys()):
        for month in sorted(result[year].keys()):
            timeline_data.append({
                'year': year,
                'month': month,
                'count': result[year][month]
            })
    
    return timeline_data

def get_archive_data(user_id):
    entries = JournalEntry.query.filter_by(user_id=user_id).all()
    
    # Group by year and month manually
    result = {}
    for entry in entries:
        year = entry.created_at.strftime('%Y')
        month = entry.created_at.strftime('%m')
        
        if year not in result:
            result[year] = {}
        
        if month not in result[year]:
            result[year][month] = 0
            
        result[year][month] += 1
    
    # Format for the template
    archive_data = {}
    for year in sorted(result.keys()):
        archive_data[year] = []
        for month in sorted(result[year].keys()):
            archive_data[year].append({
                'month': month,
                'count': result[year][month]
            })
    
    return archive_data

@login_required
def simplified_dashboard():
    # Get tag filter if present
    tag_id = request.args.get('tag')
    page = request.args.get('page', 1, type=int)
    entries_per_page = request.args.get('per_page', 10, type=int)
    
    # Base query
    query = JournalEntry.query.filter_by(user_id=current_user.id)
    
    # Apply tag filter if provided
    if tag_id:
        tag = Tag.query.filter_by(id=tag_id, user_id=current_user.id).first_or_404()
        query = query.filter(JournalEntry.tags.any(Tag.id == tag_id))
        selected_tag = tag
    else:
        selected_tag = None
    
    # Count total entries
    total_entries = query.count()
    
    # Get paginated entries
    paginated_entries = query.order_by(JournalEntry.created_at.desc()).paginate(
        page=page, per_page=entries_per_page, error_out=False
    )
    entries = paginated_entries.items
    
    # Get all user tags for filter menu
    tags = Tag.query.filter_by(user_id=current_user.id).all()
    
    # Get feeling data for guided entries
    feeling_data = {}
    guided_entry_ids = [entry.id for entry in entries if entry.entry_type == 'guided']
    if guided_entry_ids:
        feeling_responses = GuidedResponse.query.filter(
            GuidedResponse.journal_entry_id.in_(guided_entry_ids),
            GuidedResponse.question_id == 'feeling_scale'
        ).all()
        
        for resp in feeling_responses:
            feeling_data[resp.journal_entry_id] = resp.response
    
    # Get timeline and archive data
    timeline_data = get_entries_by_month(current_user.id)
    archive_data = get_archive_data(current_user.id)
    
    return render_template(
        'dashboard.html', 
        entries=entries,
        paginated_entries=paginated_entries,
        tags=tags, 
        selected_tag=selected_tag,
        feeling_data=feeling_data,
        total_entries=total_entries,
        timeline_data=timeline_data,
        archive_data=archive_data,
        selected_year=None,
        selected_month=None,
        start_date=None,
        end_date=None,
        page=page,
        entries_per_page=entries_per_page
    )