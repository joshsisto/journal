# Journal App

A personal journaling web application built with Flask that helps you track your thoughts, moods, and daily activities.

## Features

- **User Authentication**: Register and login to your personal journal
- **Quick Journal**: Write free-form journal entries quickly
- **Guided Journal**: Follow structured prompts to reflect on your day
- **Exercise Tracking**: Log your workouts as part of your journal
- **Tags/Categories**: Categorize and filter your entries with customizable tags
- **Advanced Search**: Find specific journal entries with powerful search capabilities:
  - Full-text search across all entry content
  - Filter by tags, dates, and entry types
  - Context highlighting for search matches
- **Export Functionality**: Export your journal entries as text files:
  - Export individual entries with all details preserved
  - Export search results with all filters applied
  - Export your entire journal with entry metadata
  - Well-formatted plain text with headers and separators
- **Timezone Support**: Entries are displayed in your local timezone

## Setup and Installation

1. Clone the repository:
```
git clone <repository-url>
cd journal
```

2. Create and activate a virtual environment:
```
python -m venv venv
source venv/bin/activate  # On Windows, use: venv\Scripts\activate
```

3. Install dependencies:
```
pip install -r requirements.txt
```

4. Run the application:
```
python app.py
```

5. Open your browser and navigate to:
```
http://127.0.0.1:5000/
```

## Database Migrations

If you're upgrading from an earlier version without tags, run:
```
python add_tag_tables.py
```

## License

See the LICENSE file for details.