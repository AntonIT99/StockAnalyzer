import argparse
import tkinter as tk
from stock_app import StockApp

def parse_args():
    parser = argparse.ArgumentParser(description="Stock technical chart viewer")
    parser.add_argument(
        "--ticker",
        default="",
        help="Ticker symbol to load on startup, for example AAPL, MSFT, SPY, or BTC-USD"
    )
    return parser.parse_args()

if __name__ == "__main__":
    args = parse_args()
    tk_root = tk.Tk()
    app = StockApp(tk_root, initial_ticker=args.ticker.strip().upper())
    tk_root.mainloop()
