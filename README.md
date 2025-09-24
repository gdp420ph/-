# Futures Volume Arbitrage Toolkit

This project provides utilities for comparing 24 hour futures quote volume across Bybit and Binance. It includes both a command line helper and a Tkinter-based desktop GUI that can be used to highlight large discrepancies that may uncover arbitrage opportunities.

## Features

- Reusable library functions for downloading Bybit and Binance quote volume statistics
- Offline fallback snapshot so the toolkit continues to work in environments without external network access
- Command line interface for quick inspection of the largest discrepancies
- Cross-platform Tkinter GUI with adjustable refresh interval and auto-refresh option

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
