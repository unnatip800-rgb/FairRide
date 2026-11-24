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

## Updates
- FairFare Lock is optional: switch at booking, or press "Activate FairFare Lock" after a driver cancellation. Each lock lasts 10 minutes; when it expires the fare has increased and the rider can lock the new fare for another 10 minutes (illustrative ladder: +22%, then +10% per window).
- Riders can cancel their own ride; the Fee Explainer shows the fee before confirming (free in the first 2 minutes or after a Delay Alert, otherwise 10%, minimum Rs 20).
- Delay Alert works without real drivers: a demo ETA timer runs after booking, and "Simulate driver delay" triggers it instantly.
- Measurements are saved permanently in `fairride.db` (keep this file). The Measurement section shows the saved log and a Download CSV button (`/export.csv`).
