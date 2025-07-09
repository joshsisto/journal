"""Tag management routes."""
from flask import Blueprint, render_template
from flask_login import login_required, current_user

from models import db, Tag, entry_tags

tag_bp = Blueprint('tag', __name__)


@tag_bp.route('/tags')
@login_required
def manage_tags():
    """View and manage tags"""
    # Get all tags for the current user
    tags = Tag.query.filter_by(user_id=current_user.id).order_by(Tag.name).all()
    
    # Count entries per tag
    tag_stats = []
    for tag in tags:
        entry_count = db.session.query(entry_tags).filter_by(tag_id=tag.id).count()
        tag_stats.append({
            'tag': tag,
            'entry_count': entry_count
        })
    
    return render_template('journal/tags.html', tag_stats=tag_stats)