from flask import Flask, render_template, request, jsonify, Response
import sqlite3, csv, io
from pathlib import Path
from datetime import datetime, timedelta

app = Flask(__name__)
DB = Path(__file__).with_name("fairride.db")   # permanent file: keep it to keep your data
LOCK_MINUTES = 10      # length of one FairFare Lock window
FREE_SECONDS = 120     # free-cancellation grace period after booking (demo rule)

def connect():
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    return c

def init_db():
    with connect() as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS bookings(
          id INTEGER PRIMARY KEY AUTOINCREMENT, pickup TEXT, destination TEXT,
          ride_type TEXT, original_fare REAL, current_fare REAL, status TEXT,
          driver TEXT, created_at TEXT, cancelled_by TEXT, reason TEXT,
          lock_until TEXT, rebook_count INTEGER DEFAULT 0);
        CREATE TABLE IF NOT EXISTS reports(
          id INTEGER PRIMARY KEY AUTOINCREMENT, booking_id INTEGER, category TEXT,
          details TEXT, status TEXT DEFAULT 'Received', created_at TEXT);
        CREATE TABLE IF NOT EXISTS usage_events(
          id INTEGER PRIMARY KEY AUTOINCREMENT, session_id TEXT, event_type TEXT,
          event_value TEXT, duration_seconds REAL, created_at TEXT);
        """)
        have = {r[1] for r in c.execute("PRAGMA table_info(bookings)")}   # upgrade older databases
        for n, ddl in [("lock_enabled","INTEGER DEFAULT 0"),("lock_count","INTEGER DEFAULT 0"),
                       ("delay_alert","INTEGER DEFAULT 0"),("cancel_fee","REAL")]:
            if n not in have: c.execute(f"ALTER TABLE bookings ADD COLUMN {n} {ddl}")
init_db()

def stamp(): return datetime.now().isoformat(timespec="seconds")

def level(f0, k):
    """Illustrative fare ladder: level 0 = original, level 1 = +22%, then +10% per 10-min window."""
    return round(f0) if k <= 0 else round(f0 * 1.22 * 1.1 ** (k - 1))

def state(r):
    c = r["lock_count"] or 0
    left = 0
    if r["lock_until"]:
        left = max(0, int((datetime.fromisoformat(r["lock_until"]) - datetime.now()).total_seconds()))
    active = left > 0
    f0 = r["original_fare"]; quote = level(f0, max(c, 1))
    payable = level(f0, c - 1) if active else quote
    return dict(id=r["id"], status=r["status"], lock_active=active, seconds_left=left, lock_count=c,
                original_fare=round(f0), locked_fare=level(f0, c - 1) if c else None, quote=quote,
                next_lock_fare=level(f0, c), payable=payable, savings=quote - payable,
                delay_alert=bool(r["delay_alert"]), lock_enabled=bool(r["lock_enabled"]))

def get(c, bid):
    return c.execute("SELECT * FROM bookings WHERE id=?", (bid,)).fetchone()

def ev(c, d, kind, value="", dur=None):
    c.execute("INSERT INTO usage_events(session_id,event_type,event_value,duration_seconds,created_at) VALUES(?,?,?,?,?)",
              (d.get("session_id", "server"), kind, str(value)[:300], dur, stamp()))

def start_lock(c, bid):
    until = datetime.now() + timedelta(minutes=LOCK_MINUTES)
    c.execute("UPDATE bookings SET lock_until=?, lock_count=lock_count+1 WHERE id=?", (until.isoformat(timespec="seconds"), bid))

@app.route("/")
def index(): return render_template("index.html")

@app.post("/api/book")
def book():
    d = request.get_json(force=True)
    pickup = (d.get("pickup") or "").strip(); dest = (d.get("destination") or "").strip()
    if not pickup or not dest: return jsonify(error="Enter pickup and destination."), 400
    fare = {"FairGo":180,"FairAuto":120,"FairMoto":90,"FairPlus":260}.get(d.get("ride_type"), 180)
    with connect() as c:
        cur = c.execute("""INSERT INTO bookings(pickup,destination,ride_type,original_fare,current_fare,status,driver,created_at,lock_enabled)
        VALUES(?,?,?,?,?,?,?,?,?)""", (pickup, dest, d.get("ride_type","FairGo"), fare, fare, "Driver assigned", "Aarav", stamp(), 1 if d.get("lock_enabled") else 0))
        ev(c, d, "booking_created", cur.lastrowid)
    return jsonify(id=cur.lastrowid, pickup=pickup, destination=dest, fare=fare, driver="Aarav",
                   status="Driver assigned", lock_enabled=bool(d.get("lock_enabled")))

@app.post("/api/delay")        # demo trigger for the Delay Alert (no real driver needed)
def delay():
    d = request.get_json(force=True)
    with connect() as c:
        r = get(c, d.get("booking_id"))
        if not r: return jsonify(error="Booking not found."), 404
        c.execute("UPDATE bookings SET delay_alert=1 WHERE id=?", (r["id"],)); ev(c, d, "delay_alert_shown", r["id"])
    return jsonify(ok=True)

@app.get("/api/cancel-fee")
def cancel_fee():
    with connect() as c:
        r = get(c, request.args.get("booking_id"))
        if not r: return jsonify(error="Booking not found."), 404
        waited = int((datetime.now() - datetime.fromisoformat(r["created_at"])).total_seconds())
        if r["delay_alert"]: fee, why = 0, "Waived: your driver is delayed (Delay Alert was shown)."
        elif waited <= FREE_SECONDS: fee, why = 0, f"Free: you are within the {FREE_SECONDS // 60}-minute grace period."
        else: fee, why = max(20, round(r["original_fare"] * 0.10)), "Grace period over: 10% of fare (minimum ₹20) covers the driver's wasted trip."
    return jsonify(fee=fee, why=why, waited=waited, grace=FREE_SECONDS)

@app.post("/api/cancel-user")
def cancel_user():
    d = request.get_json(force=True)
    with connect() as c:
        r = get(c, d.get("booking_id"))
        if not r: return jsonify(error="Booking not found."), 404
        if r["status"] not in ("Driver assigned", "Replacement ride assigned"): return jsonify(error="This ride can't be cancelled now."), 400
        waited = int((datetime.now() - datetime.fromisoformat(r["created_at"])).total_seconds())
        fee = 0 if (r["delay_alert"] or waited <= FREE_SECONDS) else max(20, round(r["original_fare"] * 0.10))
        c.execute("UPDATE bookings SET status='Cancelled by user',cancelled_by='User',reason='User cancelled',cancel_fee=? WHERE id=?", (fee, r["id"]))
        ev(c, d, "user_cancelled", f"{r['id']} fee={fee}")
    return jsonify(fee=fee)

@app.post("/api/cancel-driver")
def cancel_driver():
    d = request.get_json(force=True)
    with connect() as c:
        r = get(c, d.get("booking_id"))
        if not r: return jsonify(error="Booking not found."), 404
        c.execute("UPDATE bookings SET status='Driver cancelled',cancelled_by='Driver',reason='Driver cancelled after accepting' WHERE id=?", (r["id"],))
        if r["lock_enabled"]: start_lock(c, r["id"]); ev(c, d, "lock_activated", f"{r['id']} auto")
        ev(c, d, "driver_cancelled", r["id"])
        return jsonify(state(get(c, r["id"])))

@app.post("/api/lock")         # user chooses to activate (or re-activate) the 10-minute lock
def lock():
    d = request.get_json(force=True)
    with connect() as c:
        r = get(c, d.get("booking_id"))
        if not r: return jsonify(error="Booking not found."), 404
        if r["cancelled_by"] != "Driver" or r["status"] != "Driver cancelled": return jsonify(error="FairFare Lock is available after a driver cancellation."), 400
        if state(r)["lock_active"]: return jsonify(error="Lock is already active."), 400
        start_lock(c, r["id"]); ev(c, d, "lock_activated", f"{r['id']} manual")
        return jsonify(state(get(c, r["id"])))

@app.get("/api/booking/<int:bid>")
def booking_state(bid):
    with connect() as c:
        r = get(c, bid)
        return jsonify(state(r)) if r else (jsonify(error="Booking not found."), 404)

@app.post("/api/rebook")
def rebook():
    d = request.get_json(force=True)
    with connect() as c:
        r = get(c, d.get("booking_id"))
        if not r: return jsonify(error="Booking not found."), 404
        if r["status"] != "Driver cancelled": return jsonify(error="Rebooking is available after a driver cancellation."), 400
        s = state(r)
        c.execute("UPDATE bookings SET current_fare=?,status='Replacement ride assigned',driver='Meera',rebook_count=rebook_count+1,lock_until=NULL WHERE id=?", (s["payable"], r["id"]))
    return jsonify(payable_fare=s["payable"], quote=s["quote"], savings=s["savings"], driver="Meera")

@app.post("/api/report")
def report():
    d = request.get_json(force=True); category = (d.get("category") or "").strip()
    if not category: return jsonify(error="Choose a report category."), 400
    with connect() as c:
        cur = c.execute("INSERT INTO reports(booking_id,category,details,created_at) VALUES(?,?,?,?)", (d.get("booking_id"), category, d.get("details",""), stamp()))
    return jsonify(id=cur.lastrowid, status="Received")

@app.post("/api/event")
def event():
    d = request.get_json(force=True)
    with connect() as c: ev(c, d, d.get("event_type","interaction"), d.get("event_value",""), d.get("duration_seconds"))
    return jsonify(ok=True)

@app.get("/api/measurements")
def measurements():
    with connect() as c:
        one = lambda sql: c.execute(sql).fetchone()[0] or 0
        return jsonify(
            bookings=one("SELECT COUNT(*) FROM bookings"), locks=one("SELECT SUM(lock_count) FROM bookings"),
            driver_cancels=one("SELECT COUNT(*) FROM bookings WHERE cancelled_by='Driver'"),
            user_cancels=one("SELECT COUNT(*) FROM bookings WHERE cancelled_by='User'"),
            delay_alerts=one("SELECT COUNT(*) FROM bookings WHERE delay_alert=1"),
            fees_charged=one("SELECT SUM(cancel_fee) FROM bookings WHERE cancelled_by='User'"),
            fees_waived=one("SELECT COUNT(*) FROM bookings WHERE cancelled_by='User' AND cancel_fee=0"),
            reports=one("SELECT COUNT(*) FROM reports"), events=one("SELECT COUNT(*) FROM usage_events"),
            avg_recovery=round(one("SELECT AVG(duration_seconds) FROM usage_events WHERE event_type='rebooking_completed'"), 1),
            since=c.execute("SELECT MIN(created_at) FROM usage_events").fetchone()[0],
            recent=[dict(x) for x in c.execute("SELECT created_at,event_type,event_value FROM usage_events WHERE event_type!='click' ORDER BY id DESC LIMIT 12")])

@app.get("/export.csv")
def export():
    with connect() as c:
        out = io.StringIO(); w = csv.writer(out)
        w.writerow(["id","session","event_type","event_value","duration_seconds","created_at"])
        w.writerows([tuple(r) for r in c.execute("SELECT id,session_id,event_type,event_value,duration_seconds,created_at FROM usage_events ORDER BY id")])
    return Response(out.getvalue(), mimetype="text/csv", headers={"Content-Disposition": "attachment; filename=fairride_measurements.csv"})

if __name__ == "__main__":
    app.run(debug=True)
