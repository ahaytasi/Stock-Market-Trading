# Stock Trading System – Full Client/Server Prototype

## Requirements
- Python 3.10+
- Flask (installed from requirements.txt)

## Run locally
1. Extract the project ZIP.
2. Open a terminal in the extracted folder.
3. Create and activate a virtual environment (recommended):
   - Windows: `py -m venv .venv` then `.venv\\Scripts\\activate`
   - macOS/Linux: `python3 -m venv .venv` then `source .venv/bin/activate`
4. Install dependencies: `pip install -r requirements.txt`
5. Start the app: `python app.py`
6. Open `http://127.0.0.1:5000` in your browser.

The SQLite relational database (`stock_trading.db`) is created automatically on first run.
It is stored in the project folder.

## Demo administrator
- Username: `admin`
- Password: `Admin123!`

Change the demo administrator password and set a strong SECRET_KEY before any deployment.
Example PowerShell: `$env:SECRET_KEY="replace-with-a-long-random-secret"`

## Customer account creation
Use "Create an account" on the sign-in page. Registration asks for full name, username,
email, and password. New demo customer accounts receive a $25,000 simulated starting cash
balance so the trading workflow can be tested immediately.

## Included functions
- Customer registration, sign-in, sign-out, and session-based access.
- Admin-only stock creation, market-hours configuration, weekday toggle, and holiday calendar.
- Market dashboard showing ticker, company, current price, available volume, market cap,
  opening price, daily high, and daily low.
- Buy/sell order submission, pending-order cancellation, and explicit execution while market is open.
- Purchases deduct cash and add shares; sales require owned shares and credit sale proceeds to cash.
- Cash deposits and withdrawals; withdrawals cannot exceed available cash.
- Portfolio and transaction history persisted in SQLite.
- Background price generator uses small random price movements only during configured market hours,
  weekdays (when enabled), and non-holiday dates.
- Responsive desktop and mobile layout.

## Order workflow
1. Submit a buy or sell order from the market table. It is saved as PENDING.
2. Before execution, the customer can cancel it.
3. During approved market hours, select Execute. The server checks cash or owned shares and
   completes the transaction at the then-current simulated market price.
4. Executed orders are written to the transaction history and update cash and holdings.

## Testing notes
- Market hours use the computer/server's local time.
- The default market schedule is 09:00–16:00, Monday–Friday.
- To test order execution immediately, sign in as admin and temporarily set market hours to
  cover the current local time, or run the test during configured market hours.
- Stock price generation runs every 10 seconds while the market is open.
- The demo app is not connected to a real broker, real exchange, payment processor, or market feed.
- For production use, add CSRF protection, rate limiting, email verification, password reset,
  audit logging, secure secret management, HTTPS, deployment hardening, and comprehensive tests.

### Recent interface updates
- Admin stock creation now stores all required opening/day/previous-close price fields and reports duplicate tickers clearly. Newly created stocks appear in the Available stocks table after submission.
- Click any stock row (or focus it and press Enter/Space) to open a details window showing its ticker, current price, available volume, market capitalization, opening price, daily high, and daily low. The Trade button continues to open the order form without opening the details window.


Market simulation: while the market is open, stock prices make small random movements every 5 seconds. The dashboard refreshes displayed prices every 5 seconds without reloading the page.
