# Ultra Smart Analytics

An interactive web application for analyzing and comparing ultra-endurance race performance data from Strava activities.

## Features

- **Individual Athlete Analysis**: Detailed performance statistics, pace breakdowns, and visualizations
- **Multi-Athlete Comparisons**: Side-by-side comparison of up to 5 athletes
- **Interactive Dashboard**: Browse all available athletes with quick stats
- **Real-time Visualizations**: Pace charts, distribution plots, and segment analysis
- **Responsive Design**: Works on desktop and mobile devices

## Project Structure

```
ultra-smart/
├── app.py                 # Main Flask application
├── database.py            # Database operations and models
├── data/                  # Race data and database files
├── static/                # CSS, JavaScript, and assets
├── templates/             # HTML templates
├── ultra_smart/           # Core application modules
├── scripts/               # Utility scripts (organized by purpose)
│   ├── data-migration/    # Database import/migration scripts
│   ├── analysis/          # Data analysis and visualization
│   └── utilities/         # General utilities and setup
├── tests/                 # Test files and examples
├── reports/               # Generated analysis reports
├── docs/                  # Documentation
└── images/                # Screenshots and visual assets
```

## Getting Started

### Prerequisites
- Python 3.8+
- Virtual environment (recommended)

### Installation

1. **Clone and setup**:
   ```bash
   cd ultra-smart
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Prepare your data**:
   - Add athlete profile JSON files to `data/` directory
   - Add corresponding CSV split files

3. **Run the application**:
   ```bash
   source venv/bin/activate
   python app.py
   ```

4. **Open in browser**:
   Navigate to `http://localhost:5000`

### Stopping the Application

To stop the Flask application:

- **If running in terminal**: Press `Ctrl+C` to stop the server
- **Kill all Flask instances**: 
  ```bash
  pkill -f "python.*app.py"
  ```
- **Kill by port** (if needed):
  ```bash
  lsof -ti:5000 | xargs kill -9
  ```

### Debugging

Several ways to debug and check variable values:

1. **Print statements** (simplest):
   ```python
   print(f"Variable value: {my_variable}")
   print(f"Type: {type(my_variable)}")
   ```

2. **Flask's app.logger**:
   ```python
   app.logger.debug(f"Debug info: {variable}")
   app.logger.info(f"Info: {variable}")
   app.logger.warning(f"Warning: {variable}")
   ```

3. **Python debugger (pdb)**:
   ```python
   import pdb; pdb.set_trace()  # Breakpoint
   ```

4. **Flask debug mode** (already enabled):
   - Automatic reloading on code changes
   - Detailed error pages with stack traces
   - Interactive debugger in browser

5. **Browser developer tools**:
   - Check Network tab for API calls
   - Console for JavaScript errors
   - Inspect HTML/CSS for frontend issues

## Usage

### Dashboard
- View all available athletes with quick performance stats
- Click "View Analysis" for detailed individual athlete reports
- Use "Add to Comparison" to build multi-athlete comparisons

### Comparison Mode
- Select 2-5 athletes to compare
- Side-by-side performance metrics
- Visual pace comparison charts
- Automatic winner determination

🏃‍♂️ **Ultra Smart Analytics** - Turning ultra-endurance data into actionable insights!
