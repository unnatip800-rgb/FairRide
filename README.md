# FairRide — full-stack student prototype

## Stack
- Frontend: HTML5, CSS3, JavaScript
- Backend: Python Flask
- Database: SQLite (created automatically as `fairride.db`)

## Features
- Responsive ride-booking interface with sample ride categories and fares
- Simulated driver assignment and driver-initiated cancellation
- FairFare Lock: proposed 10-minute fare protection window
- Rebooking using saved pickup and destination details
- Fairness report submission
- Fee transparency / feature explanation sections
- Usage-event logging, click events, booking counts, reports and lock counts

## Run
1. Install Python 3.10+.
2. Open this folder in a terminal.
3. Create a virtual environment: `python -m venv venv`
4. Activate it:
   - Windows: `venv\\Scripts\\activate`
   - macOS/Linux: `source venv/bin/activate`
5. Install: `pip install -r requirements.txt`
6. Run: `python app.py`
7. Open `http://127.0.0.1:5000`

## Important
This is a simulated academic prototype. It is not affiliated with or connected to Uber, real drivers, GPS, live maps, payments or live fares. Driver details and fare amounts are sample data. FairFare Lock is a proposed concept with demo rules. Avoid entering personal or sensitive information. Use Flask debug mode only for local development.
