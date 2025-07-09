"""Routes package for organizing Flask blueprints."""

from .auth import auth_bp
from .journal import journal_bp
from .tags import tag_bp
from .export import export_bp
from .ai import ai_bp
from .api import api_bp


def register_blueprints(app):
    """Register all blueprints with the Flask application."""
    
    # Register authentication routes
    app.register_blueprint(auth_bp)
    
    # Register journal routes
    app.register_blueprint(journal_bp)
    
    # Register tag management routes
    app.register_blueprint(tag_bp)
    
    # Register export routes
    app.register_blueprint(export_bp, url_prefix='/export')
    
    # Register AI routes
    app.register_blueprint(ai_bp, url_prefix='/ai')
    
    # Register API routes (api_bp already has /api prefix)
    app.register_blueprint(api_bp)


__all__ = ['auth_bp', 'journal_bp', 'tag_bp', 'export_bp', 'ai_bp', 'api_bp', 'register_blueprints']