"""Export routes for journal entries."""
from flask import Blueprint, render_template, send_file, flash, redirect, url_for
from flask_login import login_required, current_user
import io
import zipfile
from datetime import datetime

from models import JournalEntry
from export_utils import format_entry_for_text, format_multi_entry_filename

export_bp = Blueprint('export', __name__)


@export_bp.route('/export/entries', methods=['POST'])
@login_required
def export_entries():
    """Export journal entries in various formats."""
    # This is a placeholder - add export functionality as needed
    flash('Export functionality not yet implemented.', 'info')
    return redirect(url_for('journal.dashboard'))