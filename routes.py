"""
Streamlined routes.py - Main router that registers all blueprints.

This file replaces the original monolithic routes.py file.
All route implementations have been moved to modular blueprints in the routes/ directory.
"""

# Import all blueprints from the routes package
from routes import auth_bp, journal_bp, tag_bp, export_bp, ai_bp, api_bp, register_blueprints

# For backward compatibility with existing imports
# These blueprints are also available at the module level
__all__ = ['auth_bp', 'journal_bp', 'tag_bp', 'export_bp', 'ai_bp', 'api_bp', 'register_blueprints']