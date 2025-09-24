# Futures Volume Arbitrage Toolkit

This project provides utilities for comparing 24 hour futures quote volume across Bybit and Binance and for monitoring live arbitrage opportunities. It includes command line helpers, a Japanese-localised Tkinter desktop GUI, and a real-time WebSocket listener that flags profitable spreads for the configured symbols.

## Features

- Reusable library functions for downloading Bybit and Binance quote volume statistics
- Command line interface for quick inspection of the largest discrepancies
- Cross-platform Tkinter GUI with Japanese labels, adjustable refresh interval, and auto-refresh option
- Real-time WebSocket listener that focuses on user-specified symbols and prints arbitrage alerts
- Offline fallback snapshot so the toolkit continues to work in environments without external network access

## Usage

### Command line comparison

Run the CLI helper to print the symbols with the largest absolute volume gap:

```bash
python scripts/arbitrage_volume.py --limit 10 --threshold 50000000
```

### Exporting results for review

To download the comparison output for spreadsheets or manual audits, export it as a CSV file:

```bash
python scripts/download_volumes.py --output data/volume_differences.csv --limit 25 --threshold 10000000
```

The command above creates `data/volume_differences.csv` with columns for the symbol, each exchange's quote volume, the absolute difference, and the gap ratio. Use `--overwrite` if you would like to replace an existing file.

### GUI dashboard

```bash
python scripts/arbitrage_gui.py
```

When the execution environment blocks outbound network access the toolkit automatically falls back to a bundled volume snapshot. The GUI displays the fallback data just like live data, and the CLI prints a warning describing the situation.

### Real-time spread detection

Install the optional `websockets` package (``pip install websockets``) to enable real-time feeds. When the dependency or network access is unavailable, run the tool with `--offline` to generate realistic simulated data.

```bash
python scripts/realtime_arbitrage.py --symbols BTCUSDT,ETHUSDT --spread 5 --percent 0.05
```

- `--symbols`: Comma separated list of symbols to monitor (default: `BTCUSDT,ETHUSDT`).
- `--spread`: Minimum absolute spread (USDT) required to emit a signal.
- `--percent`: Minimum profit ratio (in percent) required to emit a signal.
- `--offline`: Switch to deterministic simulated prices when WebSocket connectivity is unavailable.

Example output (in Japanese):

```
2024-01-01 12:34:56 INFO 監視開始: シンボル=BTCUSDT,ETHUSDT, 最小差額=5.0000, 最小利幅=0.050% (リアルタイム)
2024-01-01 12:34:58 INFO シグナル検出: [2024-01-01 12:34:58] BTCUSDT: binanceで買い bybitで売り | 差額 5.1234 USDT (0.051%)
```
