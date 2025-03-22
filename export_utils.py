"""
Export utilities for the journal application.

This module provides functions to export journal entries to text format.
"""

from datetime import datetime
import pytz

def format_entry_for_text(entry, guided_responses=None, include_header=True, user_timezone=None):
    """Format a journal entry as text.
    
    Args:
        entry: The journal entry to format.
        guided_responses: Optional guided responses for the entry.
        include_header: Whether to include the header with date/time.
        user_timezone: The timezone to display dates in.
        
    Returns:
        str: Formatted text of the journal entry.
    """
    lines = []
    
    # Format the entry date with timezone if provided
    entry_date = entry.created_at
    if user_timezone:
        try:
            tz = pytz.timezone(user_timezone)
            entry_date = pytz.utc.localize(entry_date).astimezone(tz)
        except (pytz.exceptions.UnknownTimeZoneError, AttributeError):
            pass
    
    # Add header with date and time
    if include_header:
        lines.append(f"Journal Entry - {entry_date.strftime('%Y-%m-%d %H:%M')}")
        lines.append(f"Type: {'Quick' if entry.entry_type == 'quick' else 'Guided'} Entry")
        
        # Add tags if present
        if entry.tags:
            tag_names = ', '.join([tag.name for tag in entry.tags])
            lines.append(f"Tags: {tag_names}")
        
        lines.append("-" * 40)
        lines.append("")
    
    # Format content based on entry type
    if entry.entry_type == 'quick':
        lines.append(entry.content)
    else:
        if guided_responses:
            for resp in guided_responses:
                lines.append(f"Q: {resp.question_text}")
                lines.append(f"A: {resp.response}")
                lines.append("")
    
    return "\n".join(lines)

def format_multi_entry_filename(filter_info=None):
    """Generate a filename for multi-entry exports.
    
    Args:
        filter_info: Optional dictionary with filter information.
        
    Returns:
        str: A descriptive filename.
    """
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    # Start with base filename
    if filter_info and filter_info.get('tag'):
        filename = f"journal_entries_tag_{filter_info['tag'].name}_{timestamp}"
    elif filter_info and filter_info.get('query'):
        query = filter_info['query'].replace(' ', '_')[:20]  # Limit length for filename
        filename = f"journal_entries_search_{query}_{timestamp}"
    else:
        filename = f"journal_entries_all_{timestamp}"
    
    # Add extension
    return f"{filename}.txt"