import yfinance as yf
import pandas as pd
import requests
import os

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
ALERT_FILE = "alerts_sent.txt"

if os.path.exists(ALERT_FILE):
    with open(ALERT_FILE, "r") as f:
        sent_alerts = set(f.read().splitlines())
else:
    sent_alerts = set()


def send_telegram(message):
    if not BOT_TOKEN or not CHAT_ID:
        print("Telegram secrets mancanti")
        return

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": CHAT_ID, "text": message})


def get_nasdaq100_tickers():
    url = "https://en.wikipedia.org/wiki/Nasdaq-100"
    tables = pd.read_html(url)

    for table in tables:
        if "Ticker" in table.columns:
            tickers = table["Ticker"].dropna().tolist()
            return [t.replace(".", "-") for t in tickers]

    raise Exception("Impossibile trovare lista Nasdaq-100")


tickers = get_nasdaq100_tickers()

print(f"Ticker Nasdaq-100 trovati: {len(tickers)}")

all_setups = []
new_alerts = []

for ticker in tickers:
    print(f"\nControllo {ticker}")

    try:
        df = yf.download(
            ticker,
            period="1y",
            auto_adjust=False,
            progress=False
        )

        if df.empty or len(df) < 160:
            print(f"Dati insufficienti per {ticker}")
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
        score = 0

        bullish_trend = close > ma50 > ma150
        bearish_trend = close < ma50 < ma150

        new_bullish_trend = bullish_trend and not (prev_close > prev_ma50 > prev_ma150)
        new_bearish_trend = bearish_trend and not (prev_close < prev_ma50 < prev_ma150)

        breakout_20d = close > high20 and relvol > 1.5
        breakdown_20d = close < low20 and relvol > 1.5

        volume_spike = relvol > 2
        strong_volume_spike = relvol > 3

        golden_cross = previous["MA50"] <= previous["MA150"] and latest["MA50"] > latest["MA150"]
        death_cross = previous["MA50"] >= previous["MA150"] and latest["MA50"] < latest["MA150"]

        if bullish_trend:
            score += 2
        if bearish_trend:
            score -= 2

        if breakout_20d:
            signals.append("🚀 Breakout 20 giorni con volume")
            score += 4

        if volume_spike:
            signals.append("🔥 Volume anomalo > 2x")
            score += 3

        if strong_volume_spike:
            signals.append("🔥🔥 Volume molto anomalo > 3x")
            score += 2

        if new_bullish_trend:
            signals.append("🟢 Nuovo trend rialzista")
            score += 3

        if golden_cross:
            signals.append("✨ Golden Cross MA50 > MA150")
            score += 3

        if new_bearish_trend:
            signals.append("🔴 Nuovo trend ribassista")
            score -= 3

        if death_cross:
            signals.append("⚠️ Death Cross MA50 < MA150")
            score -= 3

        if breakdown_20d:
            signals.append("📉 Breakdown 20 giorni con volume")
            score -= 4

        distance_ma50 = ((close - ma50) / ma50) * 100
        score += min(max(distance_ma50 / 5, -3), 3)

        setup = {
            "ticker": ticker,
            "price": close,
            "ma50": ma50,
            "ma150": ma150,
            "relvol": relvol,
            "score": round(score, 1),
            "signals": signals
        }

        all_setups.append(setup)

        if signals:
            alert_id = f"{ticker}-{'-'.join(signals)}"

            if alert_id not in sent_alerts:
                new_alerts.append(setup)
                sent_alerts.add(alert_id)

                with open(ALERT_FILE, "a") as f:
                    f.write(alert_id + "\n")

        print(f"{ticker} score: {score:.1f}")

    except Exception as e:
        print(f"Errore su {ticker}: {e}")


top_setups = sorted(all_setups, key=lambda x: x["score"], reverse=True)[:10]
new_alerts = sorted(new_alerts, key=lambda x: x["score"], reverse=True)

message = "📊 NASDAQ-100 SCANNER\n\n"

if new_alerts:
    message += "🚨 Nuovi segnali:\n"

    for item in new_alerts[:10]:
        message += (
            f"\n{item['ticker']} | Score: {item['score']}\n"
            + "\n".join(item["signals"])
            + f"\nPrezzo: {item['price']:.2f}"
            + f"\nRelVol: {item['relvol']:.2f}\n"
        )
else:
    message += "Nessun nuovo segnale.\n"

message += "\n\n🏆 Top 10 setup Nasdaq-100:\n"

for i, item in enumerate(top_setups, start=1):
    message += (
        f"\n{i}. {item['ticker']} | Score: {item['score']}"
        f" | RelVol: {item['relvol']:.2f}"
        f" | Prezzo: {item['price']:.2f}"
    )

send_telegram(message)
print(message)
