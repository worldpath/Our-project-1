# Bot Enhancements Pack

This pack contains drop-in modules to harden your Binance.US spot trading bot for **performance**, **stability**, and **tax reporting** with **Postgres** persistence.

## Modules

- `binance_filters.py` — Pre-trade filter enforcement & precise rounding for PRICE_FILTER, LOT_SIZE, MIN_NOTIONAL/NOTIONAL, and side-based percent price limits. Works with `/exchangeInfo` JSON.
- `liquidity_filters.py` — Liquidity and spread gating (min 24h USD volume, max spread bps, top-N universe).
- `rate_governor.py` — Adaptive token-bucket rate limiter honoring Binance weight model.
- `risk_constraints.py` — Pydantic-validated risk profiles (conservative / moderate / aggressive / ultra).
- `logger_setup.py` — Structured JSON logging + rotating files.
- `circuit_breaker.py` — Trip-on-loss and trip-on-errors; safe-mode demotion.
- `backoff.py` — Exponential jitter backoff helpers.
- `db.py` — SQLAlchemy models for Postgres (trades, fills, lots, realized PnL, settings, metrics).
- `settings_watch.py` — Postgres LISTEN/NOTIFY helper for hot-reloading bot parameters.
- `tax_ledger.py` — Lot-level ledger supporting FIFO/HIFO/LIFO/Specific ID + Form 8949 CSV export.

## Install

```bash
pip install "sqlalchemy>=2.0" "psycopg2-binary>=2.9" "pydantic>=2.7" "python-dateutil>=2.9"
```

Add prometheus-client if you want /metrics export.

## Integrate (short)

- Load /api/v3/exchangeInfo once per hour; pass the JSON into binance_filters.ExchangeFilters.
- Before placing any order, call filters.preflight_order(symbol, price, qty, side) to clamp/round/validate.
- Gate your symbol universe with liquidity_filters.is_tradeable(...) and rotate a top-N list.
- Wrap REST/WS calls with rate_governor.RateGovernor and use its record_weight() per endpoint.
- Construct a RiskConfig from env or file and call risk_constraints.validate_config(config) at startup.
- Persist every execution report to Postgres via db.Session. Update lots via tax_ledger.Ledger.
- Subscribe to settings_watch.listen_for_settings() to hot-apply UI changes via NOTIFY.
- Emit Prometheus gauges (exposure, heat, PnL, error counts, weight remaining) for external dashboards.