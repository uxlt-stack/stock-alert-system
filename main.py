import yfinance as yf
import pandas as pd

with open("tickers.txt", "r") as f:
    tickers = [line.strip() for line in f.readlines() if line.strip()]

for ticker in tickers:
    print(f"\nControllo {ticker}")

    try:
        df = yf.download(ticker, period="1y", auto_adjust=False, progress=False)

        if df.empty:
            print(f"Nessun dato trovato per {ticker}")
            continue

        # Se yfinance crea colonne multi-livello, le appiattiamo
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        df["MA50"] = df["Close"].rolling(50).mean()
        df["MA150"] = df["Close"].rolling(150).mean()
        df["VOL20"] = df["Volume"].rolling(20).mean()
        df["RelVol"] = df["Volume"] / df["VOL20"]

        latest = df.iloc[-1]

        close = float(latest["Close"])
        ma50 = float(latest["MA50"])
        ma150 = float(latest["MA150"])
        relvol = float(latest["RelVol"])

        print(f"Prezzo: {close:.2f}")
        print(f"MA50: {ma50:.2f}")
        print(f"MA150: {ma150:.2f}")
        print(f"Relative Volume: {relvol:.2f}")

        if close > ma50 > ma150:
            print("Trend rialzista")

        if close < ma50 < ma150:
            print("Trend ribassista")

        if relvol > 2:
            print("Volume anomalo")

    except Exception as e:
        print(f"Errore su {ticker}: {e}")
