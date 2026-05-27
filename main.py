import yfinance as yf
import pandas as pd
import requests
import os

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

def send_telegram(message):
    if not BOT_TOKEN or not CHAT_ID:
        print("Telegram secrets mancanti")
        return

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": CHAT_ID, "text": message})


with open("tickers.txt", "r") as f:
    tickers = [line.strip() for line in f.readlines() if line.strip()]


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

        df["MA50"] = df["Close"].rolling(50).mean()
        df["MA150"] = df["Close"].rolling(150).mean()
        df["VOL20"] = df["Volume"].rolling(20).mean()
        df["RelVol"] = df["Volume"] / df["VOL20"]

        df["High20"] = df["High"].rolling(20).max().shift(1)
        df["Low20"] = df["Low"].rolling(20).min().shift(1)

        latest = df.iloc[-1]
        previous = df.iloc[-2]

        close = float(latest["Close"])
        ma50 = float(latest["MA50"])
        ma150 = float(latest["MA150"])
        relvol = float(latest["RelVol"])
        high20 = float(latest["High20"])
        low20 = float(latest["Low20"])

        prev_close = float(previous["Close"])
        prev_ma50 = float(previous["MA50"])
        prev_ma150 = float(previous["MA150"])

        signals = []

        bullish_trend = close > ma50 > ma150
        bearish_trend = close < ma50 < ma150

        new_bullish_trend = (
            close > ma50 > ma150 and
            not (prev_close > prev_ma50 > prev_ma150)
        )

        new_bearish_trend = (
            close < ma50 < ma150 and
            not (prev_close < prev_ma50 < prev_ma150)
        )

        breakout_20d = close > high20 and relvol > 1.5
        breakdown_20d = close < low20 and relvol > 1.5

        volume_spike = relvol > 2
        strong_volume_spike = relvol > 3

        golden_cross = previous["MA50"] <= previous["MA150"] and latest["MA50"] > latest["MA150"]
        death_cross = previous["MA50"] >= previous["MA150"] and latest["MA50"] < latest["MA150"]

        print(f"Prezzo: {close:.2f}")
        print(f"MA50: {ma50:.2f}")
        print(f"MA150: {ma150:.2f}")
        print(f"Relative Volume: {relvol:.2f}")
        print(f"High20 precedente: {high20:.2f}")
        print(f"Low20 precedente: {low20:.2f}")

        if new_bullish_trend:
            signals.append("🟢 Nuovo trend rialzista")

        if new_bearish_trend:
            signals.append("🔴 Nuovo trend ribassista")

        if golden_cross:
            signals.append("✨ Golden Cross MA50 > MA150")

        if death_cross:
            signals.append("⚠️ Death Cross MA50 < MA150")

        if breakout_20d:
            signals.append("🚀 Breakout 20 giorni con volume")

        if breakdown_20d:
            signals.append("📉 Breakdown 20 giorni con volume")

        if strong_volume_spike:
            signals.append("🔥 Volume molto anomalo > 3x")
        elif volume_spike:
            signals.append("🔥 Volume anomalo > 2x")

        if signals:
            message = (
                f"📊 {ticker}\n\n"
                + "\n".join(signals)
                + f"\n\nPrezzo: {close:.2f}"
                + f"\nMA50: {ma50:.2f}"
                + f"\nMA150: {ma150:.2f}"
                + f"\nRelative Volume: {relvol:.2f}"
            )

            print(message)
            send_telegram(message)
        else:
            print("Nessun alert smart")

    except Exception as e:
        print(f"Errore su {ticker}: {e}")
