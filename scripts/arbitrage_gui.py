"""Tkinter GUI for monitoring futures volume differences between exchanges."""

from __future__ import annotations

import logging
import math
import pathlib
import sys
import tkinter as tk
from tkinter import ttk
from typing import Optional

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from arbitrage import calculate_volume_differences, fetch_exchange_volumes

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


class ArbitrageApp:
    def __init__(self, master: tk.Tk) -> None:
        self.master = master
        master.title("出来高アービトラージモニター")
        master.geometry("900x500")

        self._refresh_job: Optional[str] = None

        self.limit_var = tk.StringVar(value="15")
        self.threshold_var = tk.StringVar(value="0")
        self.interval_var = tk.StringVar(value="30")
        self.status_var = tk.StringVar(value="待機中")

        self._build_controls(master)
        self._build_table(master)
        self._build_status(master)

    # UI builders ---------------------------------------------------------
    def _build_controls(self, master: tk.Tk) -> None:
        frame = ttk.Frame(master, padding=10)
        frame.pack(side=tk.TOP, fill=tk.X)

        ttk.Label(frame, text="表示件数:").grid(row=0, column=0, sticky=tk.W)
        ttk.Entry(frame, width=6, textvariable=self.limit_var).grid(row=0, column=1, padx=(0, 12))

        ttk.Label(frame, text="最小差額 (USDT):").grid(row=0, column=2, sticky=tk.W)
        ttk.Entry(frame, width=10, textvariable=self.threshold_var).grid(row=0, column=3, padx=(0, 12))

        ttk.Label(frame, text="更新間隔 (秒):").grid(row=0, column=4, sticky=tk.W)
        ttk.Entry(frame, width=6, textvariable=self.interval_var).grid(row=0, column=5, padx=(0, 12))

        refresh_btn = ttk.Button(frame, text="今すぐ更新", command=self.refresh)
        refresh_btn.grid(row=0, column=6)

        auto_btn = ttk.Button(frame, text="自動更新開始", command=self.toggle_auto_refresh)
        auto_btn.grid(row=0, column=7, padx=(12, 0))
        self.auto_button = auto_btn

    def _build_table(self, master: tk.Tk) -> None:
        columns = ("symbol", "bybit", "binance", "diff", "ratio")
        tree = ttk.Treeview(master, columns=columns, show="headings", height=18)
        tree.heading("symbol", text="シンボル")
        tree.heading("bybit", text="Bybit 出来高")
        tree.heading("binance", text="Binance 出来高")
        tree.heading("diff", text="差分")
        tree.heading("ratio", text="比率")

        tree.column("symbol", width=120, anchor=tk.W)
        tree.column("bybit", width=200, anchor=tk.E)
        tree.column("binance", width=200, anchor=tk.E)
        tree.column("diff", width=160, anchor=tk.E)
        tree.column("ratio", width=120, anchor=tk.E)

        tree.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        self.tree = tree

    def _build_status(self, master: tk.Tk) -> None:
        frame = ttk.Frame(master, padding=10)
        frame.pack(side=tk.BOTTOM, fill=tk.X)
        ttk.Label(frame, textvariable=self.status_var).pack(side=tk.LEFT)

    # Refresh logic -------------------------------------------------------
    def _parse_int(self, value: str, *, default: int) -> int:
        try:
            return int(value)
        except (TypeError, ValueError):
            return default

    def _parse_float(self, value: str, *, default: float) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    def refresh(self) -> None:
        limit = self._parse_int(self.limit_var.get(), default=10)
        threshold = self._parse_float(self.threshold_var.get(), default=0.0)

        self.status_var.set("出来高を取得中…")
        self.master.update_idletasks()
        try:
            volumes = fetch_exchange_volumes()
            diffs = calculate_volume_differences(
                volumes["bybit"],
                volumes["binance"],
                min_difference=threshold,
                limit=limit,
            )
        except Exception as exc:  # pragma: no cover - safety net for GUI
            logging.exception("Failed to refresh data")
            self.status_var.set(f"エラー: {exc}")
            return

        self.tree.delete(*self.tree.get_children())
        for item in diffs:
            self.tree.insert(
                "",
                tk.END,
                values=(
                    item.symbol,
                    f"{item.base_volume:,.2f}",
                    f"{item.quote_volume:,.2f}",
                    f"{item.difference:,.2f}",
                    f"{item.ratio:,.2%}" if not math.isinf(item.ratio) else "∞",
                ),
            )
        self.status_var.set(f"{len(diffs)} 件のシンボルを更新しました")

    def toggle_auto_refresh(self) -> None:
        if self._refresh_job is None:
            interval = max(self._parse_int(self.interval_var.get(), default=30), 5)
            self.auto_button.config(text="自動更新停止")
            self._schedule_refresh(interval)
            self.status_var.set(f"{interval} 秒ごとに自動更新中")
        else:
            self._cancel_refresh()
            self.status_var.set("自動更新を停止しました")

    def _schedule_refresh(self, interval: int) -> None:
        self.refresh()
        self._refresh_job = self.master.after(interval * 1000, lambda: self._schedule_refresh(interval))

    def _cancel_refresh(self) -> None:
        if self._refresh_job is not None:
            self.master.after_cancel(self._refresh_job)
            self._refresh_job = None
            self.auto_button.config(text="自動更新開始")


def main() -> int:
    root = tk.Tk()
    app = ArbitrageApp(root)
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
