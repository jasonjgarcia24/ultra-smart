# Scripts Directory

This directory contains utility scripts organized by purpose:

## Subdirectories

### `/data-migration/`
Scripts for importing, migrating, and updating database data:
- `import_cocodona_results.py` - Import race results into database
- `migrate_files_to_database.py` - Migrate existing files to database format
- `update_bib_numbers.py` - Update bib numbers from CSV data

### `/analysis/`
Scripts for data analysis and visualization:
- `analyze_splits.py` - Analyze split timing data
- `compare_athletes.py` - Compare athlete performances 
- `plot_splits.py` - Generate performance plots and charts

### `/utilities/`
General utility and setup scripts:
- `debug_strava.py` - Debug Strava API connections
- `get_token.py` - Obtain Strava API tokens
- `list_activities.py` - List Strava activities
- `setup.py` - Project setup and installation
- `strava_setup.py` - Configure Strava integration

## Usage

Run scripts from the project root directory:
```bash
python scripts/analysis/analyze_splits.py
python scripts/data-migration/update_bib_numbers.py
```