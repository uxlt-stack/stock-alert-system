import yfinance as yf
import pandas as pd
import requests
import os
from io import StringIO

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
SCAN_MODE = os.environ.get("SCAN_MODE", "eod")

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

    requests.post(
        url,
        data={
            "chat_id": CHAT_ID,
            "text": message
        }
    )


def get_nasdaq100_tickers():

    url = "https://en.wikipedia.org/wiki/Nasdaq-100"

    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    response = requests.get(url, headers=headers)
    response.raise_for_status()

    tables = pd.read_html(StringIO(response.text))

    for table in tables:

        if "Ticker" in table.columns:

            tickers = table["Ticker"].dropna().tolist()

            return [
                str(t).replace(".", "-")
                for t in tickers
            ]

    raise Exception("Lista Nasdaq-100 non trovata")


tickers = get_nasdaq100_tickers()

print(f"Modalità scanner: {SCAN_MODE}")
print(f"Ticker trovati: {len(tickers)}")

all_setups = []
new_alerts = []

for ticker in tickers:

    print(f"\nControllo {ticker}")

    try:

        df = yf.download(
            ticker,
            period="1y",
            auto_adjust=False,
            progress=False,
            prepost=True
        )

        if df.empty or len(df) < 160:
            print("Dati insufficienti")
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
        prev_close = float(previous["Close"])

        ma50 = float(latest["MA50"])
        ma150 = float(latest["MA150"])

        relvol = float(latest["RelVol"])

        high20 = float(latest["High20"])
        low20 = float(latest["Low20"])

        gap_pct = ((close - prev_close) / prev_close) * 100

        signals = []

        bullish_score = 0
        risk_score = 0

        bullish_trend = close > ma50 > ma150
        bearish_trend = close < ma50 < ma150

        breakout_20d = close > high20 and relvol > 1.5
        breakdown_20d = close < low20 and relvol > 1.5

        volume_spike = relvol > 2
        huge_volume = relvol > 3

        # =========================
        # PREMARKET MODE
        # =========================

        if SCAN_MODE == "premarket":

            if gap_pct > 5:
                signals.append(f"🚀 Gap Up +{gap_pct:.1f}%")
                bullish_score += 3

            if gap_pct > 10:
                signals.append("🔥 Strong Premarket Momentum")
                bullish_score += 2

            if gap_pct < -5:
                signals.append(f"🔴 Gap Down {gap_pct:.1f}%")
                risk_score += 3

            if gap_pct < -10:
                signals.append("⚠️ Earnings Shock / Crash Risk")
                risk_score += 4

            if volume_spike:
                signals.append(f"🔥 Relative Volume {relvol:.1f}x")
                bullish_score += 2

            if huge_volume:
                bullish_score += 1

            if bullish_trend:
                signals.append("🟢 Bullish Trend")
                bullish_score += 2

            if bearish_trend:
                signals.append("🔴 Bearish Trend")
                risk_score += 2

        # =========================
        # EOD MODE
        # =========================

        else:

            if bullish_trend:
                bullish_score += 2

            if breakout_20d:
                signals.append("🚀 Breakout 20 giorni")
                bullish_score += 4

            if breakdown_20d:
                signals.append("📉 Breakdown 20 giorni")
                risk_score += 4

            if volume_spike:
                signals.append(f"🔥 Relative Volume {relvol:.1f}x")
                bullish_score += 2

            if huge_volume:
                bullish_score += 1

            if gap_pct < -8:
                signals.append(f"⚠️ Forte selloff {gap_pct:.1f}%")
                risk_score += 3

            if gap_pct > 8:
                signals.append(f"🚀 Forte rally +{gap_pct:.1f}%")
                bullish_score += 3

        total_score = bullish_score - risk_score

        setup = {
            "ticker": ticker,
            "price": close,
            "gap": gap_pct,
            "relvol": relvol,
            "bullish_score": bullish_score,
            "risk_score": risk_score,
            "score": total_score,
            "signals": signals
        }

        all_setups.append(setup)
        signals_df = pd.DataFrame(all_setups)
        signals_df.to_csv("signals.csv", index=False)

        if signals:

            alert_id = (
                f"{SCAN_MODE}-"
                f"{ticker}-"
                f"{'-'.join(signals)}"
            )

            if alert_id not in sent_alerts:

                new_alerts.append(setup)

                sent_alerts.add(alert_id)

                with open(ALERT_FILE, "a") as f:
                    f.write(alert_id + "\n")

        print(
            f"{ticker} "
            f"Score={total_score} "
            f"Gap={gap_pct:.1f}% "
            f"RelVol={relvol:.1f}"
        )

    except Exception as e:

        print(f"Errore su {ticker}: {e}")

# =========================
# RANKING
# =========================

bullish_rank = sorted(
    all_setups,
    key=lambda x: x["score"],
    reverse=True
)[:10]

risk_rank = sorted(
    all_setups,
    key=lambda x: x["score"]
)[:10]

# =========================
# TELEGRAM MESSAGE
# =========================

if SCAN_MODE == "premarket":
    title = "🚨 PREMARKET SCANNER"
else:
    title = "📊 END OF DAY SCANNER"

message = f"{title}\n\n"

if new_alerts:

    message += "🔥 Nuovi segnali:\n"

    for item in sorted(
        new_alerts,
        key=lambda x: x["score"],
        reverse=True
    )[:10]:

        message += (
            f"\n{item['ticker']}"
            f"\nScore: {item['score']}"
            f"\nGap: {item['gap']:.1f}%"
            f"\nRelVol: {item['relvol']:.1f}x"
            f"\n"
            + "\n".join(item["signals"])
            + "\n"
        )

message += "\n🏆 Top Bullish Setup:\n"

for i, item in enumerate(bullish_rank[:5], start=1):

    message += (
        f"\n{i}. {item['ticker']}"
        f" | Score {item['score']}"
        f" | Gap {item['gap']:.1f}%"
    )

message += "\n\n⚠️ Top Risk Setup:\n"

for i, item in enumerate(risk_rank[:5], start=1):

    message += (
        f"\n{i}. {item['ticker']}"
        f" | Score {item['score']}"
        f" | Gap {item['gap']:.1f}%"
    )

send_telegram(message)

print(message)
