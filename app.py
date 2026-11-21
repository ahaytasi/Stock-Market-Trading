import os
import sqlite3
import threading
import time
import random
from datetime import datetime, date
from functools import wraps
from flask import Flask, render_template, request, redirect, url_for, session, flash, abort, jsonify
from werkzeug.security import generate_password_hash, check_password_hash

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "stock_trading.db")
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "change-this-development-secret-key")
STARTING_CASH = 25000.00

def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    with db() as con:
        con.executescript("""
        CREATE TABLE IF NOT EXISTS users(
          id INTEGER PRIMARY KEY AUTOINCREMENT, full_name TEXT NOT NULL,
          username TEXT NOT NULL UNIQUE, email TEXT NOT NULL UNIQUE,
          password_hash TEXT NOT NULL, role TEXT NOT NULL DEFAULT 'customer',
          cash_balance REAL NOT NULL DEFAULT 0, created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS stocks(
          id INTEGER PRIMARY KEY AUTOINCREMENT, company_name TEXT NOT NULL,
          ticker TEXT NOT NULL UNIQUE, available_volume INTEGER NOT NULL,
          initial_price REAL NOT NULL, current_price REAL NOT NULL,
          opening_price REAL NOT NULL, day_high REAL NOT NULL, day_low REAL NOT NULL,
          previous_close REAL NOT NULL, active INTEGER NOT NULL DEFAULT 1
        );
        CREATE TABLE IF NOT EXISTS holdings(
          user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
          stock_id INTEGER NOT NULL REFERENCES stocks(id),
          shares INTEGER NOT NULL DEFAULT 0, PRIMARY KEY(user_id, stock_id)
        );
        CREATE TABLE IF NOT EXISTS orders(
          id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL REFERENCES users(id),
          stock_id INTEGER NOT NULL REFERENCES stocks(id), side TEXT NOT NULL,
          shares INTEGER NOT NULL, requested_price REAL NOT NULL,
          status TEXT NOT NULL DEFAULT 'PENDING', created_at TEXT NOT NULL,
          executed_at TEXT, executed_price REAL
        );
        CREATE TABLE IF NOT EXISTS transactions(
          id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL REFERENCES users(id),
          stock_id INTEGER REFERENCES stocks(id), type TEXT NOT NULL,
          shares INTEGER NOT NULL DEFAULT 0, price REAL NOT NULL DEFAULT 0,
          total REAL NOT NULL, created_at TEXT NOT NULL, description TEXT
        );
        CREATE TABLE IF NOT EXISTS market_settings(
          id INTEGER PRIMARY KEY CHECK(id=1), open_time TEXT NOT NULL,
          close_time TEXT NOT NULL, weekdays_only INTEGER NOT NULL DEFAULT 1
        );
        CREATE TABLE IF NOT EXISTS holidays(
          id INTEGER PRIMARY KEY AUTOINCREMENT, holiday_date TEXT NOT NULL UNIQUE,
          description TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS price_history(
          id INTEGER PRIMARY KEY AUTOINCREMENT, stock_id INTEGER NOT NULL REFERENCES stocks(id),
          price REAL NOT NULL, recorded_at TEXT NOT NULL
        );
        """)
        con.execute("INSERT OR IGNORE INTO market_settings(id,open_time,close_time,weekdays_only) VALUES(1,'09:00','16:00',1)")
        admin = con.execute("SELECT id FROM users WHERE username='admin'").fetchone()
        if not admin:
            con.execute("""INSERT INTO users(full_name,username,email,password_hash,role,cash_balance,created_at)
                VALUES(?,?,?,?,?,?,?)""",
                ("System Administrator","admin","admin@example.local",
                 generate_password_hash("Admin123!"),"admin",0,datetime.now().isoformat(timespec="seconds")))
        if con.execute("SELECT COUNT(*) FROM stocks").fetchone()[0] == 0:
            seed = [
              ("Apple Inc.","AAPL",42500000,228.45),("Microsoft Corp.","MSFT",28700000,412.17),
              ("Alphabet Inc.","GOOGL",24300000,182.34),("Amazon.com Inc.","AMZN",32100000,205.67),
              ("Tesla Inc.","TSLA",45800000,346.21),("NVIDIA Corp.","NVDA",51200000,141.88)
            ]
            for company,ticker,volume,price in seed:
                cur=con.execute("""INSERT INTO stocks(company_name,ticker,available_volume,initial_price,current_price,
                    opening_price,day_high,day_low,previous_close) VALUES(?,?,?,?,?,?,?,?,?)""",
                    (company,ticker,volume,price,price,price,price,price,price))
                con.execute("INSERT INTO price_history(stock_id,price,recorded_at) VALUES(?,?,?)",
                    (cur.lastrowid,price,datetime.now().isoformat(timespec="seconds")))

def market_is_open(con=None):
    own = con is None
    con = con or db()
    settings = con.execute("SELECT * FROM market_settings WHERE id=1").fetchone()
    now = datetime.now()
    holiday = con.execute("SELECT 1 FROM holidays WHERE holiday_date=?", (now.date().isoformat(),)).fetchone()
    weekdays_ok = not settings["weekdays_only"] or now.weekday() < 5
    open_now = settings["open_time"] <= now.strftime("%H:%M") < settings["close_time"]
    if own: con.close()
    return bool(weekdays_ok and open_now and not holiday)

def price_generator():
    """Small bounded random walk; only changes prices while market is open."""
    while True:
        try:
            with db() as con:
                if market_is_open(con):
                    for stock in con.execute("SELECT * FROM stocks WHERE active=1").fetchall():
                        # Small random movement with a slight mean-reversion component.
                        drift = random.uniform(-0.0018, 0.0018)
                        price = max(0.01, round(stock["current_price"] * (1 + drift), 2))
                        con.execute("""UPDATE stocks SET current_price=?, day_high=MAX(day_high,?),
                            day_low=MIN(day_low,?) WHERE id=?""", (price,price,price,stock["id"]))
                        con.execute("INSERT INTO price_history(stock_id,price,recorded_at) VALUES(?,?,?)",
                            (stock["id"],price,datetime.now().isoformat(timespec="seconds")))
        except Exception as exc:
            app.logger.warning("Price generator issue: %s", exc)
        time.sleep(5)

def login_required(fn):
    @wraps(fn)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            flash("Please sign in to continue.", "error")
            return redirect(url_for("login"))
        return fn(*args, **kwargs)
    return wrapped

def admin_required(fn):
    @wraps(fn)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        if session.get("role") != "admin":
            abort(403)
        return fn(*args, **kwargs)
    return wrapped

def current_user(con):
    if "user_id" not in session: return None
    return con.execute("SELECT * FROM users WHERE id=?", (session["user_id"],)).fetchone()

@app.context_processor
def inject_globals():
    return {"market_open": market_is_open(), "now_year": datetime.now().year}

@app.route("/")
def index():
    if "user_id" not in session: return redirect(url_for("login"))
    with db() as con:
        stocks=con.execute("SELECT * FROM stocks WHERE active=1 ORDER BY ticker").fetchall()
        user=current_user(con)
        holdings=con.execute("""SELECT h.shares,s.ticker,s.company_name,s.current_price,
            h.shares*s.current_price AS market_value FROM holdings h JOIN stocks s ON s.id=h.stock_id
            WHERE h.user_id=? AND h.shares>0 ORDER BY s.ticker""",(user["id"],)).fetchall()
        transactions=con.execute("""SELECT t.*,s.ticker FROM transactions t LEFT JOIN stocks s ON s.id=t.stock_id
            WHERE t.user_id=? ORDER BY t.id DESC LIMIT 50""",(user["id"],)).fetchall()
        orders=con.execute("""SELECT o.*,s.ticker FROM orders o JOIN stocks s ON s.id=o.stock_id
            WHERE o.user_id=? AND o.status='PENDING' ORDER BY o.id DESC""",(user["id"],)).fetchall()
        history={}
        for s in stocks:
            history[s["ticker"]]=[r["price"] for r in con.execute(
                "SELECT price FROM price_history WHERE stock_id=? ORDER BY id DESC LIMIT 30",(s["id"],)).fetchall()][::-1]
        settings=con.execute("SELECT * FROM market_settings WHERE id=1").fetchone()
        holidays=con.execute("SELECT * FROM holidays ORDER BY holiday_date").fetchall() if user["role"]=="admin" else []
    return render_template("index.html",user=user,stocks=stocks,holdings=holdings,
        transactions=transactions,orders=orders,history=history,settings=settings,holidays=holidays)

@app.route("/api/market-data")
@login_required
def market_data():
    """Return the latest simulated market prices for live dashboard updates."""
    with db() as con:
        rows = con.execute("""SELECT id,ticker,company_name,current_price,available_volume,
            opening_price,day_high,day_low FROM stocks WHERE active=1 ORDER BY ticker""").fetchall()
    return jsonify([{
        "ticker": r["ticker"], "company_name": r["company_name"],
        "current_price": r["current_price"], "available_volume": r["available_volume"],
        "market_cap": round(r["current_price"] * r["available_volume"], 2),
        "opening_price": r["opening_price"], "day_high": r["day_high"], "day_low": r["day_low"]
    } for r in rows])

@app.route("/register",methods=["GET","POST"])
def register():
    if request.method=="POST":
        full=request.form.get("full_name","").strip()
        username=request.form.get("username","").strip()
        email=request.form.get("email","").strip().lower()
        password=request.form.get("password","")
        if not all([full,username,email,password]):
            flash("Complete every field to create your account.","error")
        elif len(password)<8:
            flash("Password must be at least 8 characters.","error")
        else:
            try:
                with db() as con:
                    con.execute("""INSERT INTO users(full_name,username,email,password_hash,role,cash_balance,created_at)
                        VALUES(?,?,?,?,?,?,?)""",(full,username,email,generate_password_hash(password),
                        "customer",STARTING_CASH,datetime.now().isoformat(timespec="seconds")))
                flash("Account created. You can now sign in.","success")
                return redirect(url_for("login"))
            except sqlite3.IntegrityError:
                flash("That username or email address is already registered.","error")
    return render_template("auth.html",mode="register")

@app.route("/login",methods=["GET","POST"])
def login():
    if request.method=="POST":
        username=request.form.get("username","").strip()
        password=request.form.get("password","")
        with db() as con:
            user=con.execute("SELECT * FROM users WHERE username=?",(username,)).fetchone()
        if user and check_password_hash(user["password_hash"],password):
            session.clear()
            session["user_id"]=user["id"];session["username"]=user["username"];session["role"]=user["role"]
            return redirect(url_for("index"))
        flash("Invalid username or password.","error")
    return render_template("auth.html",mode="login")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.post("/order")
@login_required
def create_order():
    side=request.form.get("side","").upper()
    ticker=request.form.get("ticker","").upper()
    try: shares=int(request.form.get("shares","0"))
    except ValueError: shares=0
    if side not in ("BUY","SELL") or shares<1:
        flash("Choose a valid order side and share quantity.","error");return redirect(url_for("index"))
    with db() as con:
        stock=con.execute("SELECT * FROM stocks WHERE ticker=? AND active=1",(ticker,)).fetchone()
        if not stock: flash("Stock not found.","error")
        elif not market_is_open(con): flash("The market is closed. Orders cannot be executed now.","error")
        else:
            con.execute("""INSERT INTO orders(user_id,stock_id,side,shares,requested_price,status,created_at)
                VALUES(?,?,?,?,?,'PENDING',?)""",(session["user_id"],stock["id"],side,shares,
                stock["current_price"],datetime.now().isoformat(timespec="seconds")))
            flash("Order submitted and awaiting execution. You may cancel it before execution.","success")
    return redirect(url_for("index"))

@app.post("/order/<int:order_id>/execute")
@login_required
def execute_order(order_id):
    with db() as con:
        order=con.execute("SELECT * FROM orders WHERE id=? AND user_id=?",(order_id,session["user_id"])).fetchone()
        if not order or order["status"]!="PENDING":
            flash("This order is no longer pending.","error");return redirect(url_for("index"))
        if not market_is_open(con):
            flash("The market is closed. This order remains pending.","error");return redirect(url_for("index"))
        stock=con.execute("SELECT * FROM stocks WHERE id=? AND active=1",(order["stock_id"],)).fetchone()
        user=con.execute("SELECT * FROM users WHERE id=?",(session["user_id"],)).fetchone()
        price=stock["current_price"];total=round(price*order["shares"],2)
        holding=con.execute("SELECT shares FROM holdings WHERE user_id=? AND stock_id=?",
            (user["id"],stock["id"])).fetchone()
        owned=holding["shares"] if holding else 0
        if order["side"]=="BUY" and user["cash_balance"]<total:
            flash("Insufficient cash balance. The pending order was not executed.","error")
        elif order["side"]=="SELL" and owned<order["shares"]:
            flash("Insufficient shares. The pending order was not executed.","error")
        else:
            if order["side"]=="BUY":
                con.execute("UPDATE users SET cash_balance=cash_balance-? WHERE id=?",(total,user["id"]))
                con.execute("""INSERT INTO holdings(user_id,stock_id,shares) VALUES(?,?,?)
                    ON CONFLICT(user_id,stock_id) DO UPDATE SET shares=shares+excluded.shares""",
                    (user["id"],stock["id"],order["shares"]))
            else:
                con.execute("UPDATE users SET cash_balance=cash_balance+? WHERE id=?",(total,user["id"]))
                con.execute("UPDATE holdings SET shares=shares-? WHERE user_id=? AND stock_id=?",
                    (order["shares"],user["id"],stock["id"]))
            con.execute("UPDATE orders SET status='EXECUTED',executed_at=?,executed_price=? WHERE id=?",
                (datetime.now().isoformat(timespec="seconds"),price,order_id))
            con.execute("""INSERT INTO transactions(user_id,stock_id,type,shares,price,total,created_at,description)
                VALUES(?,?,?,?,?,?,?,?)""",(user["id"],stock["id"],order["side"],order["shares"],price,total,
                datetime.now().isoformat(timespec="seconds"),"Stock order executed"))
            flash(f"{order['side'].title()} order executed at {price:.2f}.","success")
    return redirect(url_for("index"))

@app.post("/order/<int:order_id>/cancel")
@login_required
def cancel_order(order_id):
    with db() as con:
        cur=con.execute("UPDATE orders SET status='CANCELLED' WHERE id=? AND user_id=? AND status='PENDING'",
            (order_id,session["user_id"]))
        flash("Pending order cancelled." if cur.rowcount else "Order could not be cancelled.", "success" if cur.rowcount else "error")
    return redirect(url_for("index"))

@app.post("/cash")
@login_required
def cash_action():
    action=request.form.get("action")
    try: amount=round(float(request.form.get("amount","0")),2)
    except ValueError: amount=0
    if action not in ("deposit","withdraw") or amount<=0:
        flash("Enter a valid amount.","error");return redirect(url_for("index"))
    with db() as con:
        user=con.execute("SELECT * FROM users WHERE id=?",(session["user_id"],)).fetchone()
        if action=="withdraw" and amount>user["cash_balance"]:
            flash("Withdrawal exceeds your available cash balance.","error")
        else:
            delta=amount if action=="deposit" else -amount
            con.execute("UPDATE users SET cash_balance=cash_balance+? WHERE id=?",(delta,user["id"]))
            con.execute("""INSERT INTO transactions(user_id,type,shares,price,total,created_at,description)
                VALUES(?,?,0,0,?,?,?)""",(user["id"],action.upper(),amount,
                datetime.now().isoformat(timespec="seconds"),f"Cash {action}"))
            flash(f"{action.title()} completed: ${amount:,.2f}.","success")
    return redirect(url_for("index"))

@app.post("/admin/stock")
@admin_required
def add_stock():
    company=request.form.get("company_name","").strip()
    ticker=request.form.get("ticker","").strip().upper()
    try: volume=int(request.form.get("volume","0"));price=round(float(request.form.get("initial_price","0")),2)
    except ValueError: volume=0;price=0
    if not company or not ticker or len(ticker)>10 or not ticker.replace(".", "").replace("-", "").isalnum() or volume<1 or price<=0:
        flash("Enter a company, ticker, positive volume, and positive initial price.","error")
    else:
        try:
            with db() as con:
                cur=con.execute("""INSERT INTO stocks(company_name,ticker,available_volume,initial_price,current_price,
                    opening_price,day_high,day_low,previous_close) VALUES(?,?,?,?,?,?,?,?,?)""",
                    (company,ticker,volume,price,price,price,price,price,price))
                con.execute("INSERT INTO price_history(stock_id,price,recorded_at) VALUES(?,?,?)",
                    (cur.lastrowid,price,datetime.now().isoformat(timespec="seconds")))
            flash(f"{ticker} added to the market.","success")
        except sqlite3.IntegrityError: flash("That ticker is already in use. Choose a unique ticker.","error")
        except sqlite3.Error as exc:
            app.logger.exception("Could not create stock")
            flash(f"The stock could not be saved: {exc}","error")
    return redirect(url_for("index"))

@app.post("/admin/market")
@admin_required
def update_market():
    opening=request.form.get("open_time","09:00");closing=request.form.get("close_time","16:00")
    if opening>=closing:
        flash("Market closing time must be later than opening time.","error")
    else:
        with db() as con:
            con.execute("UPDATE market_settings SET open_time=?,close_time=?,weekdays_only=? WHERE id=1",
                (opening,closing,1 if request.form.get("weekdays_only") else 0))
        flash("Market settings updated.","success")
    return redirect(url_for("index"))

@app.post("/admin/holiday")
@admin_required
def add_holiday():
    holiday=request.form.get("holiday_date","");description=request.form.get("description","").strip()
    try:
        date.fromisoformat(holiday)
        with db() as con: con.execute("INSERT INTO holidays(holiday_date,description) VALUES(?,?)",(holiday,description or "Market holiday"))
        flash("Holiday added to the market calendar.","success")
    except (ValueError,sqlite3.IntegrityError): flash("Enter a valid date that is not already listed.","error")
    return redirect(url_for("index"))

@app.post("/admin/holiday/<int:holiday_id>/delete")
@admin_required
def delete_holiday(holiday_id):
    with db() as con: con.execute("DELETE FROM holidays WHERE id=?",(holiday_id,))
    flash("Holiday removed.","success")
    return redirect(url_for("index"))

@app.errorhandler(403)
def forbidden(_): return "Administrator access required.",403

if __name__=="__main__":
    init_db()
    if not app.config.get("PRICE_THREAD_STARTED"):
        threading.Thread(target=price_generator,daemon=True).start()
        app.config["PRICE_THREAD_STARTED"]=True
    app.run(debug=True, use_reloader=False)
