import yfinance as yf
import pandas as pd

# Legge ticker
with open("tickers.txt", "r") as f:
    tickers = [line.strip() for line in f.readlines()]

for ticker in tickers:

    print(f"\nControllo {ticker}")

    try:
        df = yf.download(ticker, period="1y")

        # Calcolo medie mobili
        df["MA50"] = df["Close"].rolling(50).mean()
        df["MA150"] = df["Close"].rolling(150).mean()

        # Volume relativo
        df["VOL20"] = df["Volume"].rolling(20).mean()
        df["RelVol"] = df["Volume"] / df["VOL20"]

        latest = df.iloc[-1]

        close = latest["Close"]
        ma50 = latest["MA50"]
        ma150 = latest["MA150"]
        relvol = latest["RelVol"]

        print(f"Prezzo: {close:.2f}")
        print(f"MA50: {ma50:.2f}")
        print(f"MA150: {ma150:.2f}")
        print(f"Relative Volume: {relvol:.2f}")

        # Segnali
        if close > ma50 > ma150:
            print("Trend rialzista")

        if close < ma50 < ma150:
            print("Trend ribassista")

        if relvol > 2:
            print("Volume anomalo")

    except Exception as e:
        print(f"Errore su {ticker}: {e}")
