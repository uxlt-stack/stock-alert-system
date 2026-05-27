import yfinance as yf
import pandas as pd
import requests
import os

# =========================
# TELEGRAM CONFIG
# =========================

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

def send_telegram(message):

    if not BOT_TOKEN or not CHAT_ID:
        print("Telegram secrets mancanti")
        return

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

    payload = {
        "chat_id": CHAT_ID,
        "text": message
    }

    requests.post(url, data=payload)

# =========================
# LETTURA TICKER
# =========================

with open("tickers.txt", "r") as f:
    tickers = [line.strip() for line in f.readlines() if line.strip()]

# =========================
# ANALISI TITOLI
# =========================

for ticker in tickers:

    print(f"\nControllo {ticker}")

    try:

        df = yf.download(
            ticker,
            period="1y",
            auto_adjust=False,
            progress=False
        )

        if df.empty:
            print(f"Nessun dato trovato per {ticker}")
            continue

        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        # =========================
        # INDICATORI
        # =========================

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

        # =========================
        # SEGNALI
        # =========================

        bullish = close > ma50 > ma150
        bearish = close < ma50 < ma150
        volume_spike = relvol > 2

        if bullish:

            print("Trend rialzista")

            message = (
                f"🚀 {ticker}\n"
                f"Trend rialzista\n"
                f"Prezzo: {close:.2f}\n"
                f"MA50: {ma50:.2f}\n"
                f"MA150: {ma150:.2f}\n"
                f"Relative Volume: {relvol:.2f}"
            )

            send_telegram(message)

        if bearish:

            print("Trend ribassista")

        if volume_spike:

            print("Volume anomalo")

            message = (
                f"🔥 {ticker}\n"
                f"Volume anomalo rilevato\n"
                f"Relative Volume: {relvol:.2f}"
            )

            send_telegram(message)

    except Exception as e:

        print(f"Errore su {ticker}: {e}")
