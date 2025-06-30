# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Production Environment
- **Hosting**: Ubuntu server running as systemd service
- **Service Name**: `journal-app.service`
- **Service Status**: `sudo systemctl status journal-app.service`
- **Service Control**: 
  - Restart: `sudo systemctl restart journal-app.service`
  - Stop: `sudo systemctl stop journal-app.service` 
  - Start: `sudo systemctl start journal-app.service`
- **Process**: `/home/josh/Sync2/projects/journal/.venv/bin/python app.py` (PID varies)
- **Domain**: https://journal.joshsisto.com/ (behind Cloudflare)
- **Logs**: Use `sudo journalctl -u journal-app.service -f` to follow logs

## Build & Run Commands
- **Production**: Service runs automatically via systemd
- **Development**: `python app.py` (for local testing)
- **Create DB tables**: `python recreate_db.py`
- **Run DB updates**: `python add_tag_tables.py`, `python add_timezone_column.py`, etc.
- **Restart production service**: `python3 service_control.py reload`

## Backup System
- **Create backup**: `./backup.sh backup` or `./backup.sh pre-deploy`
- **List backups**: `./backup.sh list --size`
- **Cleanup old backups**: `./backup.sh cleanup`
- **Emergency rollback**: `./backup.sh rollback TIMESTAMP`

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