# Binance Futures Testnet Trading Bot

A small Python 3 application for placing **MARKET**, **LIMIT**, and bonus **STOP limit** orders on Binance USDT-M Futures Testnet.

It includes:

- Direct REST client with HMAC SHA-256 signing
- CLI order flow with validation and clear output
- Separate client/API, service, validation, and logging layers
- Request, response, and error logging to files
- Lightweight responsive web UI for desktop, tablet, and phone
- Dry-run mode for safe local checks before real testnet order submission

> Testnet base URL used by default: `https://testnet.binancefuture.com`

---

## Project structure

```text
trading_bot/
  bot/
    __init__.py
    client.py            # Binance Futures REST wrapper
    orders.py            # order placement service and response summaries
    validators.py        # CLI/web input validation
    logging_config.py    # rotating file logger
  cli.py                 # CLI entry point
  web.py                 # responsive FastAPI UI
  logs/
    market_order.log     # generated dry-run evidence log
    limit_order.log      # generated dry-run evidence log
    web_orders.log       # created by web UI when used
  .env.example
  requirements.txt
  README.md
```

---

## Setup

### 1. Create Binance Futures Testnet credentials

1. Open Binance Futures Testnet.
2. Register/sign in and activate the account.
3. Generate API credentials.
4. Keep the API secret private. Do not commit a real `.env` file.

### 2. Install dependencies

```bash
cd trading_bot
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Configure environment

```bash
cp .env.example .env
```

Edit `.env`:

```env
BINANCE_API_KEY=your_testnet_key
BINANCE_API_SECRET=your_testnet_secret
BINANCE_BASE_URL=https://testnet.binancefuture.com
BINANCE_DRY_RUN=false
```

---

## CLI usage

### Dry-run MARKET order

No exchange call is made; validation, summary output, and logging still happen.

```bash
python cli.py --symbol BTCUSDT --side BUY --type MARKET --quantity 0.001 --dry-run --log-file logs/market_order.log
```

### Dry-run LIMIT order

```bash
python cli.py --symbol BTCUSDT --side SELL --type LIMIT --quantity 0.001 --price 95000 --dry-run --log-file logs/limit_order.log
```

### Real Binance Futures Testnet MARKET order

After setting `.env` with testnet API keys:

```bash
python cli.py --symbol BTCUSDT --side BUY --type MARKET --quantity 0.001
```

### Real Binance Futures Testnet LIMIT order

```bash
python cli.py --symbol BTCUSDT --side SELL --type LIMIT --quantity 0.001 --price 95000
```

### Bonus STOP limit order

```bash
python cli.py --symbol BTCUSDT --side SELL --type STOP --quantity 0.001 --price 94000 --stop-price 94500
```

### Guided interactive mode

```bash
python cli.py --interactive
```

---

## Web UI usage

The optional UI is built for all device sizes and has no CDN dependency.

```bash
cd trading_bot
uvicorn web:app --host 127.0.0.1 --port 8000 --reload
```

Open:

```text
http://127.0.0.1:8000
```

The UI defaults to **dry-run**. Uncheck dry-run only when your testnet credentials are set correctly.

---

## Output fields

The CLI and UI print or return the key fields requested in the assignment:

- `orderId`
- `status`
- `executedQty`
- `avgPrice` when available
- clear success/failure message

Full raw exchange responses are logged to the configured log file.

---

## Logging

- CLI default log: `logs/trading_bot.log`
- Web UI log: `logs/web_orders.log`
- Example generated logs:
  - `logs/market_order.log`
  - `logs/limit_order.log`

Logged items include:

- validated order request summary
- Binance request endpoint and sanitized params
- Binance response body
- exceptions and API/network failures

Secrets are not logged. API keys are masked and signatures are hidden.

---

## Validation and error handling

The application validates before calling Binance:

- `symbol` must look like a Binance pair, for example `BTCUSDT`
- `side` must be `BUY` or `SELL`
- `type` must be `MARKET`, `LIMIT`, or `STOP`
- `quantity` must be positive
- `price` is required for `LIMIT` and `STOP`
- `stop_price` is required for `STOP`
- `price` is rejected for `MARKET`

Handled failure categories:

- invalid user input
- missing API credentials
- Binance API errors
- network failures
- keyboard cancellation in CLI

---

## Assumptions

- This project targets Binance **USDT-M Futures Testnet**, not Spot and not live Futures.
- Orders use `newOrderRespType=RESULT` so the response includes useful order details when Binance provides them.
- LIMIT and STOP orders use `timeInForce=GTC`.
- STOP order uses `workingType=MARK_PRICE`.
- The included `market_order.log` and `limit_order.log` are dry-run evidence logs because real testnet credentials are not stored in the repository.

---

## Submission note

For final hiring submission, run one MARKET and one LIMIT order with your own Binance Futures Testnet credentials, then include the generated log files or commit them after removing any sensitive information.
