import yfinance as yf
import pandas as pd
import ta
import requests
import os

# =====================================
# TELEGRAM SETTINGS
# =====================================

TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

print("TOKEN LENGTH:", len(TOKEN) if TOKEN else "NONE")
print("CHAT_ID:", CHAT_ID)

# =====================================
# INDEX LIST
# =====================================

symbols = {
    "NIFTY": "^NSEI",
    "BANKNIFTY": "^NSEBANK",
    "SENSEX": "^BSESN"
}

# =====================================
# ATM STRIKE FUNCTION
# =====================================

def get_atm_strike(price, step):
    return round(price / step) * step

# =====================================
# FINAL MESSAGE
# =====================================

final_msg = "MULTI INDEX OPTION SCANNER\n\n"

# =====================================
# LOOP
# =====================================

for index_name, symbol in symbols.items():

    try:

        # ==========================
        # DOWNLOAD DATA
        # ==========================

        df = yf.download(
            symbol,
            period="5d",
            interval="5m",
            progress=False
        )

        if df.empty:
            raise Exception("No data received")

        # MultiIndex Fix

        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        # ==========================
        # INDICATORS
        # ==========================

        df["EMA20"] = df["Close"].ewm(
            span=20,
            adjust=False
        ).mean()

        df["EMA50"] = df["Close"].ewm(
            span=50,
            adjust=False
        ).mean()

        df["RSI"] = ta.momentum.RSIIndicator(
            close=df["Close"],
            window=14
        ).rsi()

        # ==========================
        # VWAP
        # ==========================

        typical_price = (
            df["High"] +
            df["Low"] +
            df["Close"]
        ) / 3

        df["VWAP"] = typical_price.expanding().mean()

        # ==========================
        # TODAY DATA
        # ==========================

        today_df = df[
            df.index.date == df.index[-1].date()
        ]

        # ==========================
        # ORB (15 MIN)
        # ==========================

        orb_high = today_df["High"].iloc[:3].max()
        orb_low = today_df["Low"].iloc[:3].min()

        # ==========================
        # LAST CANDLE
        # ==========================

        last = df.iloc[-1]

        # ==========================
        # IST TIME
        # ==========================

        india_time = (
            pd.Timestamp(df.index[-1])
            .tz_convert("Asia/Kolkata")
        )

        india_time_str = india_time.strftime(
            "%d-%m-%Y %I:%M %p IST"
        )

        # ==========================
        # SIGNAL
        # ==========================

        if (
            last["Close"] > last["VWAP"]
            and last["EMA20"] > last["EMA50"]
            and last["RSI"] > 55
            and last["Close"] > orb_high
        ):

            signal = "BUY CE"

        elif (
            last["Close"] < last["VWAP"]
            and last["EMA20"] < last["EMA50"]
            and last["RSI"] < 45
            and last["Close"] < orb_low
        ):

            signal = "BUY PE"

        else:

            signal = "NO TRADE"

        # ==========================
        # ENTRY / SL / TARGET
        # ==========================

        last3_high = df["High"].tail(3).max()
        last3_low = df["Low"].tail(3).min()

        if signal == "BUY CE":

            entry = round(last3_high + 1, 2)

            sl = round(last3_low - 1, 2)

            risk = entry - sl

            target1 = round(entry + risk, 2)

            target2 = round(entry + (risk * 2), 2)

        elif signal == "BUY PE":

            entry = round(last3_low - 1, 2)

            sl = round(last3_high + 1, 2)

            risk = sl - entry

            target1 = round(entry - risk, 2)

            target2 = round(entry - (risk * 2), 2)

        else:

            entry = "-"
            sl = "-"
            target1 = "-"
            target2 = "-"

        # ==========================
        # ATM STRIKE
        # ==========================

        if index_name == "NIFTY":

            strike = get_atm_strike(
                last["Close"],
                50
            )

        else:

            strike = get_atm_strike(
                last["Close"],
                100
            )

        if signal == "BUY CE":

            option = f"{strike} CE"

        elif signal == "BUY PE":

            option = f"{strike} PE"

        else:

            option = "-"

        # ==========================
        # MESSAGE FORMAT
        # ==========================

        if signal != "NO TRADE":

            final_msg += f"""
{index_name}

SIGNAL : {signal}

BUY {index_name} {option}

ENTRY ABOVE : {entry}

STOP LOSS : {sl}

TARGETS :
{target1}
{target2}

IMPORTANT :
WAIT FOR 15 MIN CANDLE
CLOSE ABOVE ENTRY LEVEL

Close : {last['Close']:.2f}
RSI   : {last['RSI']:.2f}

Time  : {india_time_str}

------------------------

"""

        else:

            final_msg += f"""
{index_name}

NO TRADE

Close : {last['Close']:.2f}
RSI   : {last['RSI']:.2f}

Time  : {india_time_str}

------------------------

"""

    except Exception as e:

        final_msg += f"""
{index_name}

ERROR :
{str(e)}

------------------------

"""

# =====================================
# SEND TELEGRAM
# =====================================
print(f"URL = https://api.telegram.org/bot{TOKEN[:10]}***/sendMessage")
print(f"CHAT_ID = {CHAT_ID}")

response = requests.post(
    f"https://api.telegram.org/bot{TOKEN}/sendMessage",
    data={
        "chat_id": CHAT_ID,
        "text": final_msg
    }
)

print(response.text)
