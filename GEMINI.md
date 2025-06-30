# GEMINI.md

This file provides guidance to Gemini when working with code in this repository.

## Project Overview
This is a web-based journaling application built with Flask. It allows users to create, view, and manage journal entries. The application supports two types of entries: "quick" entries (simple text) and "guided" entries (a series of questions and answers). It also includes features like user authentication, email notifications, tagging, and data export.

## Tech Stack
- **Backend:** Python, Flask
- **Database:** SQLAlchemy with SQLite
- **Frontend:** HTML, CSS, JavaScript, Jinja2
- **Libraries:**
    - `flask-login`: User session management
    - `flask-wtf`: Form handling and CSRF protection
    - `flask-mail`: Sending emails
    - `werkzeug`: WSGI utility library
    - `python-dotenv`: Environment variable management
    - `pytz`: Timezone handling
    - `google-generativeai`: Google Gemini AI integration
    - `bleach`, `flask-talisman`, `html-sanitizer`, `flask-limiter`: Security features

## Key Files
- **`app.py`**: The main application file. It initializes the Flask app, configures extensions, and registers blueprints.
- **`config.py`**: Defines the application's configuration, including secret keys, database URI, and email server settings.
- **`models.py`**: Contains the SQLAlchemy database models for `User`, `JournalEntry`, `GuidedResponse`, `Tag`, and other database tables.
- **`routes.py`**: Defines the application's routes and view functions, organized into blueprints for authentication, journal, tags, and export.
- **`requirements.txt`**: Lists the Python dependencies for the project.
- **`templates/`**: Contains the Jinja2 templates for rendering the application's UI.
- **`static/`**: Contains static assets like CSS and JavaScript files.

## Development Commands
- **Run the application:** `python app.py`
- **Create database tables:** `python recreate_db.py` (if it exists)
- **Manage the production service (if applicable):**
    - Restart: `sudo systemctl restart journal-app.service`
    - Stop: `sudo systemctl stop journal-app.service`
    - Start: `sudo systemctl start journal-app.service`
    - View logs: `sudo journalctl -u journal-app.service -f`

## Code Style
- **Imports:** Grouped into standard library, third-party, and local modules.
- **Docstrings:** Google-style docstrings with `Args` and `Returns` sections.
- **Error Handling:** Use `try/except` blocks with specific exceptions.
- **Naming Conventions:**
    - Classes: `PascalCase`
    - Functions/Variables: `snake_case`
    - Constants: `UPPER_CASE`
- **Type Hinting:** Optional but recommended.
- **Database:** SQLAlchemy models with descriptive `__repr__` methods.
- **Routes:** Grouped into Flask Blueprints.

## Database
The application uses a relational database managed by SQLAlchemy. The main models are:
- **`User`**: Stores user information, including credentials and preferences.
- **`JournalEntry`**: Represents a single journal entry, which can be of type 'quick' or 'guided'.
- **`GuidedResponse`**: Stores the user's answers to guided journal questions, linked to a `JournalEntry`.
- **`Tag`**: Allows users to categorize their journal entries.
- **`Photo`**: Stores information about photos uploaded with journal entries.
