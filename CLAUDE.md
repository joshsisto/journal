# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Build & Run Commands
- Run application: `python app.py`
- Create DB tables: `python recreate_db.py`
- Run DB updates: `python add_tag_tables.py`, `python add_timezone_column.py`, etc.

## Code Style Guidelines
- **Imports**: Group imports: 1) standard library, 2) third-party, 3) local modules
- **Docstrings**: Use Google-style docstrings with Args/Returns sections
- **Error Handling**: Use try/except blocks with specific exceptions
- **Naming**: 
  - Classes: PascalCase
  - Functions/Variables: snake_case
  - Constants: UPPER_CASE
- **Type Hints**: Optional but recommended for function parameters and returns
- **Models**: Define relationships clearly with backref and lazy loading options
- **Routes**: Group related routes in blueprints
- **Database**: Use SQLAlchemy models with descriptive __repr__ methods
- **Templates**: Keep template logic minimal; use Jinja2 filters for formatting