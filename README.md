Delivery Earnings Tracker
A Python desktop application for recording delivery earnings, fuel and other expenses, and hours worked. It calculates net profit and profit per hour, and provides a dashboard to review delivery activity.

Built as a personal computer science portfolio project to practice Python, desktop UI development, and relational databases.
Features
- Add, edit, and delete delivery records
- Track earnings, fuel costs, other expenses, and hours worked
- Automatically calculate net profit and profit per hour
- View summary cards and a seven-day earnings chart
- Browse recent deliveries, search by date, and filter by week or month
- Export delivery history to CSV
- Store records locally using SQLite
- Import legacy deliveries.json records on first use, when available
Tech stack
- Python 3 — application logic
- Tkinter / ttk — desktop graphical interface
- SQLite — local relational database
- CSV and JSON — export and legacy data import
Run locally
1. Install Python 3 on Windows (with Tkinter support).
2. Clone this repository:
   git clone https://github.com/ghost47x/Delivery-Earnings-Tracker.git
   cd Delivery-Earnings-Tracker
3. Launch the dashboard:
   py desktop_release.py
The application creates deliveries.db locally if it doesn't exist. No additional pip packages are needed for the Python version.
Project files
File	Purpose
desktop_release.py	Main dashboard application and SQLite storage
app_dashboard.py	Earlier dashboard version
app_sqlite.py	Earlier SQLite version
app.py	Earlier desktop GUI version
main.py	Initial command-line tracker


How profit is calculated
Net profit = earnings - fuel expenses - other expenses
Profit per hour = net profit / hours worked
When total hours worked is zero, the app displays zero for profit per hour.
Privacy and data
Delivery records are saved locally, not in GitHub. The .gitignore excludes database files and personal JSON data. Do not commit a database with real financial information.
Future improvements
- Automated tests for calculations and database operations
- Improved handling of data backups and imports
- More detailed monthly reports
- A web version using React and a Python API
Status
The Python dashboard runs locally. A standalone Windows executable is not yet provided as a GitHub release.
