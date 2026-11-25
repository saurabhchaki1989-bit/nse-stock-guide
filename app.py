import io
import json
import math
import os
import urllib.parse
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

import pandas as pd
import plotly.graph_objects as go
import requests
import streamlit as st
import yfinance as yf

st.set_page_config(page_title="Live NSE/BSE Top 10 Stocks, SIPs, MF & Gold Guide", layout="wide")

IST = timezone(timedelta(hours=5, minutes=30))
PORTFOLIO_FILE = "dummy_portfolio.json"

POPULAR_STOCKS = {
    "RELIANCE": "Reliance Industries",
    "TCS": "Tata Consultancy Services",
    "HDFCBANK": "HDFC Bank",
    "INFY": "Infosys",
    "ICICIBANK": "ICICI Bank",
    "SBIN": "State Bank of India",
    "BHARTIARTL": "Bharti Airtel",
    "ITC": "ITC Ltd",
    "LT": "Larsen & Toubro",
    "HINDUNILVR": "Hindustan Unilever",
    "KOTAKBANK": "Kotak Mahindra Bank",
    "AXISBANK": "Axis Bank",
    "MARUTI": "Maruti Suzuki",
    "SUNPHARMA": "Sun Pharma",
    "TITAN": "Titan Company",
    "BAJFINANCE": "Bajaj Finance",
    "WIPRO": "Wipro",
    "NTPC": "NTPC",
    "POWERGRID": "Power Grid Corp",
    "TATASTEEL": "Tata Steel",
    "M&M": "Mahindra & Mahindra",
    "HCLTECH": "HCL Technologies",
    "ASIANPAINT": "Asian Paints",
    "ADANIENT": "Adani Enterprises",
    "HAL": "Hindustan Aeronautics",
    "BEL": "Bharat Electronics",
    "TRENT": "Trent Ltd",
    "TATAPOWER": "Tata Power",
    "JIOFIN": "Jio Financial Services",
    "ETERNAL": "Eternal (Zomato)",
}

EXTRA_SEARCH_FALLBACK = {
    "APLAPOLLO": "APL Apollo Tubes Limited",
    "APOLLOHOSP": "Apollo Hospitals Enterprise Limited",
    "APOLLOTYRE": "Apollo Tyres Limited",
    "IRCTC": "Indian Railway Catering And Tourism Corp",
    "DMART": "Avenue Supermarts (DMart)",
    "PIDILITIND": "Pidilite Industries Limited",
    "BAJAJFINSV": "Bajaj Finserv Limited",
    "JSWSTEEL": "JSW Steel Limited",
    "COALINDIA": "Coal India Limited",
    "ONGC": "Oil & Natural Gas Corporation",
    "DRREDDY": "Dr. Reddy's Laboratories",
    "CIPLA": "Cipla Limited",
    "DLF": "DLF Limited",
    "INDIGO": "InterGlobe Aviation (IndiGo)",
}

GOLD_AND_ETFS = {
    "GOLDBEES.NS": ("🪙 Gold ETF (Nippon GoldBees)", "Tracks live Indian Gold prices"),
    "SILVERBEES.NS": ("🥈 Silver ETF (Nippon SilverBees)", "Tracks live Indian Silver prices"),
    "NIFTYBEES.NS": ("📊 Nifty 50 Index ETF (NiftyBees)", "Top 50 Indian companies in 1 click"),
    "JUNIORBEES.NS": ("🚀 Nifty Next 50 ETF (JuniorBees)", "Next 50 fast-growing large caps"),
}

POPULAR_MFS = {
    "Parag Parikh Flexi Cap Fund (Direct Growth)": ("122639", "Flexi Cap"),
    "HDFC Mid-Cap Opportunities Fund (Direct Growth)": ("118989", "Mid Cap"),
    "SBI Small Cap Fund (Direct Growth)": ("125497", "Small Cap"),
    "Nippon India Small Cap Fund (Direct Growth)": ("118778", "Small Cap"),
    "UTI Nifty 50 Index Fund (Direct Growth)": ("120716", "Index / Large Cap"),
    "ICICI Prudential Bluechip Fund (Direct Growth)": ("120586", "Large Cap"),
    "Quant Small Cap Fund (Direct Growth)": ("120828", "Small Cap"),
    "Kotak Emerging Equity Fund (Direct Growth)": ("119775", "Mid Cap"),
    "Mirae Asset Large Cap Fund (Direct Growth)": ("118834", "Large Cap"),
    "SBI Contra Fund (Direct Growth)": ("119598", "Contra / Value"),
    "HDFC Flexi Cap Fund (Direct Growth)": ("118968", "Flexi Cap"),
    "Axis ELSS Tax Saver Fund (Direct Growth)": ("120503", "ELSS Tax Saver"),
}

# Root/stem keywords so plurals & verb forms ("falls", "slumps", "tanks", "surges") match accurately
POSITIVE_ROOTS = [
    "rally", "rallies", "surge", "jump", "gain", "profit", "record high", "buy",
    "upgrade", "inflow", "bull", "breakout", "beat", "growth", "strong", "boom",
    "rise", "soar", "outperform", "positive", "order win", "dividend", "boost", "rebound",
]
NEGATIVE_ROOTS = [
    "fall", "drop", "crash", "plunge", "loss", "cut", "downgrade", "weak", "bear",
    "sell", "slump", "fear", "outflow", "decline", "warning", "miss", "probe",
    "penalty", "layoff", "risk", "slip", "tumbl", "tank", "pain", "down", "sink", "shed",
]


def now_ist() -> datetime:
    return datetime.now(IST)


def is_market_open() -> bool:
    n = now_ist()
    return n.weekday() < 5 and (9, 15) <= (n.hour, n.minute) <= (15, 30)


def fmt_delta_rs(amount: float, suffix: str = "") -> str:
    sign = "-" if amount < 0 else "+"
    return f"{sign}₹{abs(amount):,.2f}{suffix}"


# ------------------------------------------------------------------------------
# LIVE INDIAN NEWS & IMPROVED SENTIMENT ENGINE
# ------------------------------------------------------------------------------
def score_headline(title: str) -> str:
    text = title.lower()
    pos = sum(1 for root in POSITIVE_ROOTS if root in text)
    neg = sum(1 for root in NEGATIVE_ROOTS if root in text)
    if neg > pos:
        return "🔴 Cautious"
    if pos > neg:
        return "🟢 Positive"
    return "🟡 Neutral"


@st.cache_data(ttl=600, show_spinner=False)
def fetch_live_news(query: str, max_items: int = 6) -> list:
    items = []
    try:
        q = urllib.parse.quote(query)
        url = f"https://news.google.com/rss/search?q={q}&hl=en-IN&gl=IN&ceid=IN:en"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        resp = requests.get(url, headers=headers, timeout=8)
        if resp.status_code == 200:
            root = ET.fromstring(resp.content)
            for item in root.findall(".//item")[:max_items]:
                title = (item.findtext("title") or "").strip()
                link = (item.findtext("link") or "").strip()
                pub = (item.findtext("pubDate") or "").strip()[:16]
                if title:
                    items.append(
                        {
                            "title": title,
                            "link": link,
                            "published": pub,
                            "mood": score_headline(title),
                        }
                    )
    except Exception:
        pass
    return items


# ------------------------------------------------------------------------------
# DUMMY PORTFOLIO STORAGE
# ------------------------------------------------------------------------------
def load_portfolio():
    if os.path.exists(PORTFOLIO_FILE):
        try:
            with open(PORTFOLIO_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {"cash": 100000.0, "holdings": [], "history": []}


def save_portfolio(data):
    with open(PORTFOLIO_FILE, "w") as f:
        json.dump(data, f, indent=2)


# ------------------------------------------------------------------------------
# COMPANY AUTOCOMPLETE DIRECTORY
# ------------------------------------------------------------------------------
@st.cache_data(ttl=86400, show_spinner=False)
def load_all_indian_stocks() -> dict:
    directory = {**POPULAR_STOCKS, **EXTRA_SEARCH_FALLBACK}
    try:
        url = "https://nsearchives.nseindia.com/content/equities/EQUITY_L.csv"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code == 200:
            csv_df = pd.read_csv(io.StringIO(resp.text))
            csv_df.columns = [c.strip() for c in csv_df.columns]
            if "SYMBOL" in csv_df.columns and "NAME OF COMPANY" in csv_df.columns:
                for _, r in csv_df.iterrows():
                    sym = str(r["SYMBOL"]).strip().upper()
                    comp = str(r["NAME OF COMPANY"]).strip()
                    if sym and comp:
                        directory[sym] = comp
    except Exception:
        pass
    return directory


@st.cache_data(ttl=300, show_spinner=False)
def search_yahoo_india(query: str) -> list:
    if not query or len(query.strip()) < 2:
        return []
    try:
        url = "https://query2.finance.yahoo.com/v1/finance/search"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        resp = requests.get(url, params={"q": query.strip(), "quotesCount": 12}, headers=headers, timeout=8)
        if resp.status_code == 200:
            results = []
            for q in resp.json().get("quotes", []):
                sym = q.get("symbol", "")
                if sym.endswith(".NS") or sym.endswith(".BO"):
                    name = q.get("shortname") or q.get("longname") or sym
                    results.append((sym, name))
            return results
    except Exception:
        pass
    return []


# ------------------------------------------------------------------------------
# TREND ANALYSIS + EXPECTED HIGH / LOW PRICE RANGE FORECASTER
# ------------------------------------------------------------------------------
def analyze_price_series(
    close: pd.Series,
    volume: pd.Series | None = None,
    live_override: float | None = None,
    in_positive_news: bool = False,
    full_df: pd.DataFrame | None = None,
) -> dict | None:
    close = close.dropna().copy()
    if len(close) < 25:
        return None

    if live_override is not None and live_override > 0:
        today_ist = now_ist().date()
        last_bar_date = close.index[-1].date()
        prev_day = float(close.iloc[-2]) if last_bar_date == today_ist else float(close.iloc[-1])
        price = float(live_override)
    else:
        price = float(close.iloc[-1])
        prev_day = float(close.iloc[-2])

    daily_pct = ((price - prev_day) / prev_day) * 100.0
    weekly_pct = ((price - float(close.iloc[-6])) / float(close.iloc[-6])) * 100.0 if len(close) >= 6 else 0.0
    monthly_pct = ((price - float(close.iloc[-22])) / float(close.iloc[-22])) * 100.0 if len(close) >= 22 else 0.0

    ma20 = float(close.rolling(20).mean().iloc[-1])
    ma50 = float(close.rolling(50).mean().iloc[-1]) if len(close) >= 50 else ma20

    delta = close.diff()
    gain = delta.clip(lower=0).rolling(14).mean().iloc[-1]
    loss = (-delta.clip(upper=0)).rolling(14).mean().iloc[-1]
    rsi = float(100 - (100 / (1 + (gain / (loss + 1e-9)))))

    # Volume Activity (clarifies Buying vs Selling pressure!)
    vol_ratio = 1.0
    if volume is not None:
        vol_clean = volume.dropna()
        if len(vol_clean) >= 20:
            avg_v = float(vol_clean.tail(21).iloc[:-1].mean())
            latest_v = float(vol_clean.iloc[-1])
            if avg_v > 0 and latest_v > 0:
                vol_ratio = round(latest_v / avg_v, 2)

    if vol_ratio >= 1.35:
        vol_label = f"{vol_ratio}x (Heavy Buying 🟢)" if daily_pct >= 0 else f"{vol_ratio}x (Heavy Selling 🔴)"
    else:
        vol_label = f"{vol_ratio}x avg"

    # Expected High / Low Price Range Forecast (Volatility + Historical Support/Resistance)
    daily_returns = close.pct_change().dropna()
    daily_vol = float(daily_returns.tail(20).std()) if len(daily_returns) >= 10 else 0.02
    # Clamp volatility between 0.8% and 5.5% per day so forecasts stay realistic even on crash days
    daily_vol = max(0.008, min(daily_vol, 0.055))

    day_move = min(daily_vol * 1.25, 0.08)
    week_move = min(daily_vol * math.sqrt(5), 0.20)
    month_move = min(daily_vol * math.sqrt(21), 0.35)

    # Slight trend tilt: uptrend leans slightly higher, downtrend leans slightly lower
    trend_bias = 0.015 if price > ma20 else -0.015

    day_high = round(price * (1 + day_move), 2)
    day_low = round(price * (1 - day_move), 2)
    week_high = round(price * (1 + week_move + max(0, trend_bias)), 2)
    week_low = round(price * (1 - week_move + min(0, trend_bias)), 2)
    month_high = round(price * (1 + month_move + max(0, trend_bias * 2)), 2)
    month_low = round(price * (1 - month_move + min(0, trend_bias * 2)), 2)

    if full_df is not None and "High" in full_df.columns and "Low" in full_df.columns:
        high_52w = round(float(full_df["High"].max()), 2)
        low_52w = round(float(full_df["Low"].min()), 2)
    else:
        high_52w = round(float(close.max()), 2)
        low_52w = round(float(close.min()), 2)

    avg_daily_move = float(daily_returns.abs().tail(14).mean()) if not daily_returns.empty else 0.02
    target_pct = max(0.05, min(avg_daily_move * 4.5, 0.12))
    stop_pct = max(0.03, min(avg_daily_move * 2.5, 0.06))

    sell_target = round(price * (1 + target_pct), 2)
    stop_loss = round(price * (1 - stop_pct), 2)

    score = 50.0
    score += 18 if price > ma20 else -15
    score += 12 if price > ma50 else -10

    if 45 <= rsi <= 68:
        score += 12
    elif rsi > 75:
        score -= 10
    elif rsi < 32:
        score += 5

    score += min(weekly_pct * 1.5, 10) if weekly_pct > 0 else max(weekly_pct * 1.5, -10)
    if vol_ratio >= 1.3 and daily_pct > 0:
        score += 8
    if vol_ratio >= 1.5 and daily_pct < -2.0:
        score -= 10
    if in_positive_news:
        score += 6
    score = round(max(0, min(100, score)), 1)

    heavy_buying = (vol_ratio >= 1.35 and daily_pct >= 0.8)
    heavy_selling = (vol_ratio >= 1.5 and daily_pct <= -2.0)
    news_rising = (in_positive_news and daily_pct >= 0.5)

    if heavy_selling:
        move_badge = "⚠️ HEAVY SELLING PRESSURE"
        is_on_move = False
    elif heavy_buying and news_rising:
        move_badge = "🔥 HEAVY BUYING + NEWS"
        is_on_move = True
    elif heavy_buying:
        move_badge = "🔥 HEAVY BUYING SURGE"
        is_on_move = True
    elif news_rising:
        move_badge = "📰 POSITIVE NEWS & RISING"
        is_on_move = True
    elif price > ma20 and weekly_pct >= 2.0 and rsi < 70:
        move_badge = "🚀 STARTING TO RISE (Good Entry)"
        is_on_move = True
    elif monthly_pct >= 4.0 and score >= 65:
        move_badge = "🏆 STEADY PROFIT MAKER"
        is_on_move = False
    elif rsi < 35:
        move_badge = "💡 OVERSOLD DIP (Watch for Bounce)"
        is_on_move = False
    else:
        move_badge = "➡️ NORMAL ACTIVITY"
        is_on_move = False

    if score >= 70:
        trend = "Going Up 📈"
        action = "BUY"
        reason = "Strong upward trend above 20 & 50-day averages with active buyer interest."
    elif score >= 50:
        trend = "Steady / Sideways ➡️"
        action = "HOLD / WATCH"
        reason = "Steady movement. Good to hold or wait for a clearer breakout."
    else:
        trend = "Going Down 📉"
        action = "AVOID / SELL"
        reason = "Trading below recent averages with weak momentum (wait for selling to stabilize before buying)."

    return {
        "price": round(price, 2),
        "daily_pct": round(daily_pct, 2),
        "weekly_pct": round(weekly_pct, 2),
        "monthly_pct": round(monthly_pct, 2),
        "ma20": round(ma20, 2),
        "ma50": round(ma50, 2),
        "rsi": round(rsi, 1),
        "vol_ratio": vol_ratio,
        "vol_label": vol_label,
        "score": score,
        "trend": trend,
        "action": action,
        "move_badge": move_badge,
        "is_on_move": is_on_move,
        "reason": reason,
        "sell_target": sell_target,
        "stop_loss": stop_loss,
        "day_high": day_high,
        "day_low": day_low,
        "week_high": week_high,
        "week_low": week_low,
        "month_high": month_high,
        "month_low": month_low,
        "high_52w": high_52w,
        "low_52w": low_52w,
    }


@st.cache_data(ttl=1800, show_spinner=False)
def _fetch_market_history(exchange: str):
    suffix = ".NS" if exchange == "NSE" else ".BO"
    tickers = [f"{sym}{suffix}" for sym in POPULAR_STOCKS.keys()]
    return yf.download(tickers, period="6mo", interval="1d", group_by="ticker", progress=False, auto_adjust=True)


@st.cache_data(ttl=12, show_spinner=False)
def _fetch_live_1m_prices(tickers: tuple) -> dict:
    live_prices = {}
    if not tickers:
        return live_prices
    try:
        raw = yf.download(list(tickers), period="1d", interval="1m", group_by="ticker", progress=False, auto_adjust=True)
        if raw.empty:
            return live_prices
        if len(tickers) == 1:
            t = tickers[0]
            closes = raw["Close"].dropna() if "Close" in raw.columns else raw[t]["Close"].dropna()
            if not closes.empty:
                live_prices[t] = float(closes.iloc[-1])
        else:
            for t in tickers:
                try:
                    closes = raw[t]["Close"].dropna()
                    if not closes.empty:
                        live_prices[t] = float(closes.iloc[-1])
                except Exception:
                    continue
    except Exception:
        pass
    return live_prices


def scan_market_live(exchange: str, news_headlines: list) -> pd.DataFrame:
    suffix = ".NS" if exchange == "NSE" else ".BO"
    tickers = tuple(f"{sym}{suffix}" for sym in POPULAR_STOCKS.keys())
    hist_raw = _fetch_market_history(exchange)
    live_map = _fetch_live_1m_prices(tickers)

    pos_news_text = " ".join(n["title"].lower() for n in news_headlines if "Positive" in n["mood"])

    rows = []
    for sym, name in POPULAR_STOCKS.items():
        full_ticker = f"{sym}{suffix}"
        try:
            sub_df = hist_raw[full_ticker] if len(tickers) > 1 else hist_raw
            vol_series = sub_df["Volume"] if "Volume" in sub_df.columns else None
            first_word = name.split()[0].lower()
            in_pos_news = (sym.lower() in pos_news_text) or (len(first_word) > 3 and first_word in pos_news_text)

            info = analyze_price_series(
                sub_df["Close"],
                volume=vol_series,
                live_override=live_map.get(full_ticker),
                in_positive_news=in_pos_news,
                full_df=sub_df,
            )
            if info:
                rows.append(
                    {
                        "Symbol": full_ticker,
                        "Company": name,
                        "Price (₹)": info["price"],
                        "Daily (%)": info["daily_pct"],
                        "Weekly (%)": info["weekly_pct"],
                        "Monthly (%)": info["monthly_pct"],
                        "Volume Activity": info["vol_label"],
                        "Highlight": info["move_badge"],
                        "IsOnMove": info["is_on_move"],
                        "Trend": info["trend"],
                        "Suggestion": info["action"],
                        "Score": info["score"],
                        "Target Sell (₹)": info["sell_target"],
                        "Safety Stop (₹)": info["stop_loss"],
                        "Why": info["reason"],
                    }
                )
        except Exception:
            continue

    return pd.DataFrame(rows)


@st.cache_data(ttl=1800, show_spinner=False)
def _fetch_single_history(full_ticker: str) -> pd.DataFrame:
    # 1 year of history gives accurate 52-Week Floor & Ceiling levels
    df = yf.download(full_ticker, period="1y", interval="1d", progress=False, auto_adjust=True)
    if df.empty:
        return pd.DataFrame()
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    return df


def fetch_single_stock_live(full_ticker: str):
    df = _fetch_single_history(full_ticker)
    if df.empty:
        return pd.DataFrame(), None
    live_map = _fetch_live_1m_prices((full_ticker,))
    vol_series = df["Volume"] if "Volume" in df.columns else None
    info = analyze_price_series(df["Close"], volume=vol_series, live_override=live_map.get(full_ticker), full_df=df)
    return df, info


# ------------------------------------------------------------------------------
# MUTUAL FUND LIVE AMFI LEADERBOARD
# ------------------------------------------------------------------------------
@st.cache_data(ttl=3600, show_spinner=False)
def search_amfi_mutual_funds(query: str) -> list:
    if not query or len(query.strip()) < 3:
        return []
    try:
        resp = requests.get(f"https://api.mfapi.in/mf/search?q={query.strip()}", timeout=10)
        if resp.status_code == 200:
            return resp.json()[:25]
    except Exception:
        pass
    return []


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_mf_nav(scheme_code: str):
    resp = requests.get(f"https://api.mfapi.in/mf/{scheme_code}", timeout=15)
    resp.raise_for_status()
    payload = resp.json()
    meta = payload.get("meta", {})
    raw_data = payload.get("data", [])
    if not raw_data:
        return meta, pd.DataFrame(), None

    df = pd.DataFrame(raw_data)
    df["date"] = pd.to_datetime(df["date"], format="%d-%m-%Y")
    df["nav"] = pd.to_numeric(df["nav"], errors="coerce")
    df = df.dropna().sort_values("date").set_index("date")
    info = analyze_price_series(df["nav"])
    return meta, df, info


@st.cache_data(ttl=3600, show_spinner=False)
def scan_top_mutual_funds() -> pd.DataFrame:
    def _process_one(item):
        mf_name, (code, category) = item
        try:
            _, df, info = fetch_mf_nav(code)
            if df.empty or info is None:
                return None
            latest_nav = float(df["nav"].iloc[-1])
            latest_dt = df.index[-1]

            def cagr(yrs):
                past = df[df.index <= latest_dt - pd.DateOffset(years=yrs)]
                if past.empty:
                    return 0.0
                return round((((latest_nav / float(past["nav"].iloc[-1])) ** (1 / yrs)) - 1) * 100, 1)

            r1y = cagr(1)
            r3y = cagr(3)
            r1m = info["monthly_pct"]

            start_dt = latest_dt - pd.DateOffset(years=3)
            sip_slice = df[df.index >= start_dt]
            monthly_pts = sip_slice.groupby(sip_slice.index.to_period("M")).head(1)
            invested = len(monthly_pts) * 5000.0
            units = sum(5000.0 / float(n) for n in monthly_pts["nav"])
            val_today = units * latest_nav
            profit_rs = round(val_today - invested, 0)
            profit_pct = round((profit_rs / max(invested, 1)) * 100, 1)

            if r1m >= 2.5 and r1y >= 10:
                status = "🔥 ON THE MOVE (Strong Momentum)"
                is_hot = True
            elif r3y >= 15 and r1m < 0:
                status = "💡 GREAT TIME TO START SIP (Dip)"
                is_hot = True
            elif r3y >= 14:
                status = "🏆 TOP PROFIT SIP"
                is_hot = False
            else:
                status = "➡️ STEADY COMPOUNDER"
                is_hot = False

            sign = "-" if profit_rs < 0 else "+"
            return {
                "Fund Name": mf_name,
                "Code": code,
                "Category": category,
                "Latest NAV (₹)": round(latest_nav, 2),
                "1-Month (%)": r1m,
                "1-Year (%)": r1y,
                "3-Year (%/yr)": r3y,
                "₹5k/mo SIP Profit (3Y)": f"{sign}₹{abs(profit_rs):,.0f} ({profit_pct:+.1f}%)",
                "ProfitVal": profit_rs,
                "Highlight": status,
                "IsHot": is_hot,
            }
        except Exception:
            return None

    with ThreadPoolExecutor(max_workers=6) as ex:
        results = list(ex.map(_process_one, POPULAR_MFS.items()))

    valid = [r for r in results if r is not None]
    if not valid:
        return pd.DataFrame()
    return pd.DataFrame(valid).sort_values("ProfitVal", ascending=False)


def predict_when_to_sell(holding: dict, live_info: dict) -> tuple[str, str]:
    live_price = live_info["price"]
    buy_price = holding["buy_price"]
    pnl_pct = ((live_price - buy_price) / buy_price) * 100.0
    is_mf = holding.get("asset_type") == "MF"

    if is_mf:
        if pnl_pct >= 20 and live_info["rsi"] > 72:
            return "🟠 BOOK PARTIAL PROFIT", f"Strong gain (+{pnl_pct:.1f}%) and fund is overheated. Good zone to book partial profits."
        if live_info["action"] == "AVOID / SELL":
            return "🟢 GOOD TIME TO ADD SIP", "Fund is in a dip — great time to stay invested or add more SIP units."
        return "🟢 HOLD & CONTINUE SIP", f"Steady long-term growth ({pnl_pct:+.1f}%). Mutual funds work best when held 1+ year."

    if live_price >= holding["target_price"]:
        return "🔴 SELL NOW (Target Hit!)", f"You hit your target profit (+{pnl_pct:.1f}%). Good time to book profits."
    if live_price <= holding["stop_loss"]:
        return "🔴 SELL NOW (Safety Stop Hit)", f"Price dropped below your safety limit ({pnl_pct:.1f}%). Exit to protect capital."
    if live_info["rsi"] > 75 and pnl_pct > 2:
        return "🟠 CONSIDER SELLING (Overheated)", f"Stock rose sharply (RSI {live_info['rsi']}) and may cool down soon."
    if live_info["action"] == "AVOID / SELL":
        return "🟠 SELL / EXIT SOON (Trend Weakening)", "Trend dropped below its 20-day average."
    return "🟢 HOLD (Trend Still Strong)", f"Stay invested. Suggested sell target is ₹{holding['target_price']:,.2f}."


# ------------------------------------------------------------------------------
# TOP HEADER + LIVE CONTROLS
# ------------------------------------------------------------------------------
st.title("📈 Live NSE & BSE Top 10 Stocks, SIPs, Mutual Funds & Gold")

top_c1, top_c2, top_c3, top_c4 = st.columns([1.2, 1.3, 1.2, 1])
exchange = top_c1.radio("Choose Indian Exchange:", ["NSE", "BSE"], horizontal=True)
live_mode = top_c2.toggle("🔴 Live Auto-Update (Every 15s)", value=True)
if is_market_open():
    top_c3.success("🟢 Indian Market OPEN")
else:
    top_c3.info("⚪ Market Closed (Last Close)")

if top_c4.button("🔄 Refresh Now"):
    _fetch_live_1m_prices.clear()
    fetch_live_news.clear()
    st.rerun()

AUTO_INTERVAL = 15 if live_mode else None

tab1, tab2, tab3, tab4 = st.tabs(
    [
        "🏆 Top 10 Stocks, Buzz & Bottom Performers",
        "🔍 Search Stock, Price Forecast & Buy Dummy",
        "🪙 Top 10 Profitable SIPs, MFs & Gold",
        "🎮 My Dummy Portfolio & Sell Alerts",
    ]
)

# ==============================================================================
# TAB 1: TOP 10 PROFITABLE STOCKS, ON-THE-MOVE BUZZ & BOTTOM PERFORMERS
# ==============================================================================
with tab1:
    stock_news = fetch_live_news("NSE BSE Indian stocks rally buy volume surge", max_items=6)

    @st.fragment(run_every=AUTO_INTERVAL)
    def render_live_market_board():
        market_df = scan_market_live(exchange, stock_news)
        st.caption(f"⏱️ Last Live Update: **{now_ist().strftime('%I:%M:%S %p IST')}**  |  Source: Yahoo Finance 1-min live feed + Google News India")

        if market_df.empty:
            st.error("Could not load market data right now. Please check your internet connection.")
            return

        on_move_df = market_df[market_df["IsOnMove"]].sort_values("Score", ascending=False).head(5)
        st.subheader(f"🔥 {exchange} Stocks On The Move Right Now (Buying Surge / News / Starting to Rise)")
        if not on_move_df.empty:
            mcols = st.columns(min(len(on_move_df), 5))
            for idx, (_, row) in enumerate(on_move_df.iterrows()):
                with mcols[idx]:
                    with st.container(border=True):
                        st.markdown(f"**{row['Company']}**")
                        st.caption(f"{row['Symbol']}  |  Vol: **{row['Volume Activity']}**")
                        st.metric("Live Price", f"₹{row['Price (₹)']:,.2f}", delta=f"{row['Daily (%)']:+.2f}% today")
                        st.markdown(f"**{row['Highlight']}**")
                        st.caption(f"🎯 Sell: ₹{row['Target Sell (₹)']:,.2f} | 🛡️ Stop: ₹{row['Safety Stop (₹)']:,.2f}")
        else:
            st.info("No sudden volume spikes right now — showing top steady performers below.")

        with st.expander("📰 Live Indian Stock Market News & Insights (Click to Read)", expanded=False):
            if stock_news:
                for n in stock_news:
                    st.markdown(f"{n['mood']} — [{n['title']}]({n['link']})  `{n['published']}`")
            else:
                st.caption("News feed temporarily unavailable.")

        st.divider()

        st.subheader(f"🏆 Top 10 Profitable {exchange} Stocks to Invest Right Now")
        st.caption("Ranked by upward trend, buyer momentum, and recent profit performance.")

        top10 = market_df.sort_values(["Score", "Monthly (%)"], ascending=False).head(10)
        top10_display = top10.copy()
        top10_display.insert(0, "Rank", range(1, len(top10_display) + 1))

        st.dataframe(
            top10_display[
                [
                    "Rank",
                    "Company",
                    "Symbol",
                    "Highlight",
                    "Price (₹)",
                    "Daily (%)",
                    "Weekly (%)",
                    "Monthly (%)",
                    "Volume Activity",
                    "Suggestion",
                    "Target Sell (₹)",
                    "Safety Stop (₹)",
                ]
            ],
            use_container_width=True,
            hide_index=True,
        )

        st.divider()

        st.subheader(f"📉 Bottom Performers ({exchange}) — Live / Daily, Weekly & Monthly")
        period_choice = st.radio(
            "View worst performers by timeframe:",
            ["Daily (Today / Live)", "Weekly (7 Days)", "Monthly (30 Days)"],
            horizontal=True,
            key="perf_timeframe",
        )
        col_map = {
            "Daily (Today / Live)": "Daily (%)",
            "Weekly (7 Days)": "Weekly (%)",
            "Monthly (30 Days)": "Monthly (%)",
        }
        sort_col = col_map[period_choice]

        bottom_df = market_df.sort_values(sort_col, ascending=True).head(8)
        top_gainers_df = market_df.sort_values(sort_col, ascending=False).head(5)

        b_col, g_col = st.columns(2)
        with b_col:
            st.markdown(f"#### 🔴 Bottom Performers ({period_choice})")
            st.dataframe(
                bottom_df[["Company", "Symbol", "Price (₹)", "Daily (%)", "Weekly (%)", "Monthly (%)", "Trend"]],
                use_container_width=True,
                hide_index=True,
            )
        with g_col:
            st.markdown(f"#### 🟢 Top Gainers ({period_choice})")
            st.dataframe(
                top_gainers_df[["Company", "Symbol", "Price (₹)", "Daily (%)", "Weekly (%)", "Monthly (%)", "Trend"]],
                use_container_width=True,
                hide_index=True,
            )

    render_live_market_board()

# ==============================================================================
# TAB 2: LIVE SEARCH + HOW HIGH / HOW LOW FORECAST + STOCK NEWS + BUY DUMMY
# ==============================================================================
with tab2:
    st.subheader("🔍 Search Any Indian Stock (Live Suggestions While You Type)")

    all_stocks = load_all_indian_stocks()
    option_map = {f"{name} ({sym})": sym for sym, name in sorted(all_stocks.items(), key=lambda x: x[1])}

    selected_label = st.selectbox(
        "Start typing any company name or symbol (e.g., Apollo Tubes, Reliance, HAL, Tata, HDFC):",
        options=list(option_map.keys()),
        index=None,
        placeholder="Type here for instant live suggestions (e.g. Apollo Tubes)...",
    )

    full_ticker = None
    display_name = None

    if selected_label:
        sym = option_map[selected_label]
        full_ticker = f"{sym}.NS" if exchange == "NSE" else f"{sym}.BO"
        display_name = selected_label

    with st.expander("Didn't find your stock above? Search live on Yahoo Finance (NSE & BSE)"):
        custom_q = st.text_input("Type company name and press Enter:", placeholder="e.g. Mazagon Dock, Cochin Shipyard")
        if custom_q:
            matches = search_yahoo_india(custom_q)
            if matches:
                y_map = {f"{name} ({sym})": sym for sym, name in matches}
                picked_y = st.selectbox("Select matching live stock:", list(y_map.keys()))
                full_ticker = y_map[picked_y]
                display_name = picked_y
            else:
                st.warning("No matching Indian stocks found for that name.")

    if not full_ticker:
        st.info("👆 Click the search box above and start typing any company name (like **Apollo Tubes**, **HAL**, or **Infosys**).")
    else:
        @st.fragment(run_every=AUTO_INTERVAL)
        def render_searched_stock_live(ticker_to_show, label_to_show):
            sdf, sinfo = fetch_single_stock_live(ticker_to_show)
            if sinfo is None and ticker_to_show.endswith(".BO"):
                alt_ticker = ticker_to_show.replace(".BO", ".NS")
                sdf, sinfo = fetch_single_stock_live(alt_ticker)
                if sinfo is not None:
                    ticker_to_show = alt_ticker

            if sinfo is None:
                st.error(f"Could not fetch live prices for **{ticker_to_show}** right now.")
                return

            st.caption(f"⏱️ Live Quote Updated: **{now_ist().strftime('%I:%M:%S %p IST')}**")
            st.markdown(f"### {label_to_show}  —  {sinfo['move_badge']}  |  Suggestion: **{sinfo['action']}**")

            m1, m2, m3, m4, m5, m6 = st.columns(6)
            m1.metric("Live Price", f"₹{sinfo['price']:,.2f}", delta=f"{sinfo['daily_pct']:+.2f}% today")
            m2.metric("Weekly", f"{sinfo['weekly_pct']:+.2f}%")
            m3.metric("Monthly", f"{sinfo['monthly_pct']:+.2f}%")
            m4.metric("Volume Activity", sinfo["vol_label"])
            m5.metric("🎯 Sell Target", f"₹{sinfo['sell_target']:,.2f}")
            m6.metric("🛡️ Safety Stop", f"₹{sinfo['stop_loss']:,.2f}")

            st.info(f"**Simple Insight:** {sinfo['reason']}")

            # NEW: HOW HIGH CAN IT GO & HOW LOW CAN IT FALL (LIVE VOLATILITY + 52-WEEK LEVELS)
            st.markdown("#### 📊 Expected Price Range Forecast (How High / How Low From Live Price)")
            st.caption("Estimated using this stock's live volatility and 1-year historical price floors/ceilings (not guaranteed during major breaking news).")

            f1, f2, f3, f4 = st.columns(4)
            with f1:
                with st.container(border=True):
                    st.markdown("**Next 1–2 Days**")
                    st.markdown(f"🟢 Possible High: **₹{sinfo['day_high']:,.2f}**")
                    st.markdown(f"🔴 Possible Low: **₹{sinfo['day_low']:,.2f}**")
            with f2:
                with st.container(border=True):
                    st.markdown("**Next 1 Week (5 Days)**")
                    st.markdown(f"🟢 Possible High: **₹{sinfo['week_high']:,.2f}**")
                    st.markdown(f"🔴 Possible Low: **₹{sinfo['week_low']:,.2f}**")
            with f3:
                with st.container(border=True):
                    st.markdown("**Next 1 Month (21 Days)**")
                    st.markdown(f"🟢 Possible High: **₹{sinfo['month_high']:,.2f}**")
                    st.markdown(f"🔴 Possible Low: **₹{sinfo['month_low']:,.2f}**")
            with f4:
                with st.container(border=True):
                    st.markdown("**1-Year Chart Ceiling / Floor**")
                    st.markdown(f"⬆️ 52-Wk High: **₹{sinfo['high_52w']:,.2f}**")
                    st.markdown(f"⬇️ 52-Wk Low: **₹{sinfo['low_52w']:,.2f}**")

            # Live Stock-Specific News (Now accurately detects negative crash words!)
            clean_name = label_to_show.split("(")[0].strip()
            comp_news = fetch_live_news(f"{clean_name} stock share price India", max_items=4)
            if comp_news:
                with st.expander(f"📰 Latest Live News for {clean_name}", expanded=True):
                    for n in comp_news:
                        st.markdown(f"{n['mood']} — [{n['title']}]({n['link']})  `{n['published']}`")

            sdf_plot = sdf.tail(90).copy()
            sdf_plot["20-Day Avg"] = sdf["Close"].rolling(20).mean().tail(90)

            fig = go.Figure()
            fig.add_trace(go.Scatter(x=sdf_plot.index, y=sdf_plot["Close"], name="Stock Price (₹)", line=dict(color="#1f77b4", width=2.5)))
            fig.add_trace(go.Scatter(x=sdf_plot.index, y=sdf_plot["20-Day Avg"], name="20-Day Trend Line", line=dict(color="orange", dash="dot")))
            fig.add_hline(y=sinfo["week_high"], line_dash="dash", line_color="green", annotation_text=f"1-Wk High ₹{sinfo['week_high']}")
            fig.add_hline(y=sinfo["week_low"], line_dash="dash", line_color="red", annotation_text=f"1-Wk Low ₹{sinfo['week_low']}")
            fig.update_layout(height=350, title=f"{ticker_to_show} — 3-Month Trend & Expected 1-Week High/Low Range", margin=dict(l=10, r=10, t=40, b=10))
            st.plotly_chart(fig, use_container_width=True)

            st.divider()
            st.subheader("🎮 Practice Investing Dummy Money in This Stock")
            portfolio = load_portfolio()
            st.caption(f"Your Available Dummy Cash: **₹{portfolio['cash']:,.2f}**")

            d1, d2 = st.columns([2, 1])
            dummy_amt = d1.number_input(
                "How much dummy money do you want to invest? (₹)",
                min_value=500.0,
                max_value=max(500.0, float(portfolio["cash"])),
                value=min(10000.0, max(500.0, float(portfolio["cash"]))),
                step=500.0,
                key="stock_dummy_amt",
            )
            qty = int(dummy_amt // sinfo["price"])
            actual_cost = round(qty * sinfo["price"], 2)
            d1.caption(f"Buys **{qty} dummy shares** at ₹{sinfo['price']:,.2f} each (Total: ₹{actual_cost:,.2f}).")

            if d2.button("💸 Invest Dummy Money Now", type="primary", key="buy_stock_btn"):
                if qty <= 0:
                    st.warning("Increase the amount to buy at least 1 share.")
                elif actual_cost > portfolio["cash"]:
                    st.error("Not enough dummy cash! Check Tab 4.")
                else:
                    portfolio["cash"] = round(portfolio["cash"] - actual_cost, 2)
                    portfolio["holdings"].append(
                        {
                            "id": int(now_ist().timestamp()),
                            "asset_type": "STOCK",
                            "ticker": ticker_to_show,
                            "name": label_to_show,
                            "buy_price": sinfo["price"],
                            "qty": qty,
                            "invested": actual_cost,
                            "buy_date": now_ist().strftime("%d %b %Y, %I:%M %p"),
                            "target_price": sinfo["sell_target"],
                            "stop_loss": sinfo["stop_loss"],
                        }
                    )
                    save_portfolio(portfolio)
                    st.success(f"Bought {qty} dummy shares of **{label_to_show}** for ₹{actual_cost:,.2f}! Check **Tab 4** for live sell alerts.")

        render_searched_stock_live(full_ticker, display_name)

# ==============================================================================
# TAB 3: TOP 10 PROFITABLE SIPs & MFs + ON-THE-MOVE + GOLD & SILVER
# ==============================================================================
with tab3:
    mf_news = fetch_live_news("India mutual fund SIP inflow top performing funds gold", max_items=6)

    with st.spinner("Loading Top 10 Profitable Indian SIPs & Mutual Funds (Official AMFI)..."):
        mf_board = scan_top_mutual_funds()

    st.subheader("🔥 SIPs & Mutual Funds On The Move / Best to Start Investing Now")
    if not mf_board.empty:
        hot_mfs = mf_board[mf_board["IsHot"]].head(4)
        if hot_mfs.empty:
            hot_mfs = mf_board.head(4)
        hcols = st.columns(len(hot_mfs))
        for idx, (_, row) in enumerate(hot_mfs.iterrows()):
            with hcols[idx]:
                with st.container(border=True):
                    st.markdown(f"**{row['Fund Name'].replace(' (Direct Growth)', '')}**")
                    st.caption(f"{row['Category']}  |  NAV: ₹{row['Latest NAV (₹)']}")
                    st.metric("3-Yr Yearly Return", f"{row['3-Year (%/yr)']}%", delta=f"{row['1-Month (%)']:+.1f}% (1M)")
                    st.markdown(f"**{row['Highlight']}**")
                    st.caption(f"₹5k/mo SIP (3Y): **{row['₹5k/mo SIP Profit (3Y)']}**")

    with st.expander("📰 Live Mutual Fund, SIP & Gold News Insights (Click to Read)", expanded=False):
        if mf_news:
            for n in mf_news:
                st.markdown(f"{n['mood']} — [{n['title']}]({n['link']})  `{n['published']}`")
        else:
            st.caption("News feed temporarily unavailable.")

    st.divider()

    st.subheader("🏆 Top 10 Popular SIPs & Mutual Funds Where People Are Making Profit")
    st.caption("Calculated from official AMFI daily NAVs (showing real profit on a ₹5,000/month SIP over the last 3 years).")
    if not mf_board.empty:
        top10_mf = mf_board.head(10).copy()
        top10_mf.insert(0, "Rank", range(1, len(top10_mf) + 1))
        st.dataframe(
            top10_mf[
                [
                    "Rank",
                    "Fund Name",
                    "Category",
                    "Highlight",
                    "Latest NAV (₹)",
                    "1-Month (%)",
                    "1-Year (%)",
                    "3-Year (%/yr)",
                    "₹5k/mo SIP Profit (3Y)",
                ]
            ],
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.warning("Could not load AMFI leaderboard right now.")

    st.divider()

    @st.fragment(run_every=AUTO_INTERVAL)
    def render_live_gold_etfs():
        st.subheader("🪙 Invest in Gold, Silver & Nifty Index (Live NSE ETFs)")
        st.caption(f"⏱️ Live ETF Prices Updated: **{now_ist().strftime('%I:%M:%S %p IST')}**")

        etf_cols = st.columns(4)
        portfolio = load_portfolio()

        for idx, (etf_ticker, (etf_title, etf_desc)) in enumerate(GOLD_AND_ETFS.items()):
            _, etf_info = fetch_single_stock_live(etf_ticker)
            with etf_cols[idx]:
                with st.container(border=True):
                    st.markdown(f"**{etf_title}**")
                    st.caption(etf_desc)
                    if etf_info:
                        st.metric("Live Price", f"₹{etf_info['price']:,.2f}", delta=f"{etf_info['daily_pct']:+.2f}% today")
                        st.markdown(f"**{etf_info['move_badge']}**")
                        st.caption(f"🎯 Target: ₹{etf_info['sell_target']} | 🛡️ Stop: ₹{etf_info['stop_loss']}")
                        if st.button("Buy ₹5,000 Dummy", key=f"buy_etf_{etf_ticker}", use_container_width=True):
                            qty = int(5000 // etf_info["price"])
                            cost = round(qty * etf_info["price"], 2)
                            if qty > 0 and cost <= portfolio["cash"]:
                                portfolio["cash"] = round(portfolio["cash"] - cost, 2)
                                portfolio["holdings"].append(
                                    {
                                        "id": int(now_ist().timestamp()) + idx,
                                        "asset_type": "ETF",
                                        "ticker": etf_ticker,
                                        "name": etf_title,
                                        "buy_price": etf_info["price"],
                                        "qty": qty,
                                        "invested": cost,
                                        "buy_date": now_ist().strftime("%d %b %Y, %I:%M %p"),
                                        "target_price": etf_info["sell_target"],
                                        "stop_loss": etf_info["stop_loss"],
                                    }
                                )
                                save_portfolio(portfolio)
                                st.success(f"Invested ₹{cost:,.2f} dummy into {etf_title}!")
                                st.rerun()
                            else:
                                st.warning("Not enough dummy cash! Check Tab 4.")
                    else:
                        st.warning("Price unavailable")

    render_live_gold_etfs()

    st.divider()

    st.subheader("🔍 Search Any Mutual Fund, Calculate SIP & Try Dummy Investing")

    mf_c1, mf_c2 = st.columns([1.5, 1.5])
    mf_choice_mode = mf_c1.selectbox("Pick from Top Popular Funds:", list(POPULAR_MFS.keys()))
    mf_search_text = mf_c2.text_input("Or search ANY Indian Mutual Fund by name:", placeholder="e.g. Axis Bluechip, Quant Mid Cap, Tata Digital...")

    selected_scheme_code = POPULAR_MFS[mf_choice_mode][0]
    selected_mf_name = mf_choice_mode

    if mf_search_text and len(mf_search_text.strip()) >= 3:
        mf_results = search_amfi_mutual_funds(mf_search_text)
        if mf_results:
            mf_map = {f"{m['schemeName']}": str(m["schemeCode"]) for m in mf_results}
            picked_mf = st.selectbox("Select matching Mutual Fund from AMFI:", list(mf_map.keys()))
            selected_scheme_code = mf_map[picked_mf]
            selected_mf_name = picked_mf
        else:
            st.warning("No matching Mutual Fund found. Showing selected popular fund instead.")

    try:
        meta, mf_df, mf_info = fetch_mf_nav(selected_scheme_code)
    except Exception:
        mf_df, mf_info = pd.DataFrame(), None

    if mf_info is not None and not mf_df.empty:
        latest_nav = float(mf_df["nav"].iloc[-1])
        latest_dt = mf_df.index[-1]

        s1, s2, s3 = st.columns([1.2, 1.2, 1.6])
        sip_monthly = s1.number_input("Monthly SIP Amount (₹)", min_value=500, value=5000, step=500)
        sip_years = s2.slider("If you had done this SIP for (Years):", 1, 5, 3)

        start_dt = latest_dt - pd.DateOffset(years=sip_years)
        sip_slice = mf_df[mf_df.index >= start_dt]
        monthly_points = sip_slice.groupby(sip_slice.index.to_period("M")).head(1)
        invested_sip = len(monthly_points) * sip_monthly
        units_sip = sum(sip_monthly / float(n) for n in monthly_points["nav"])
        val_sip = units_sip * latest_nav
        profit_sip = val_sip - invested_sip
        sip_sign = "-" if profit_sip < 0 else "+"

        with s3:
            with st.container(border=True):
                st.markdown(f"**{selected_mf_name[:42]}**")
                st.markdown(f"Invested: **₹{invested_sip:,.0f}**  →  Today: **₹{val_sip:,.0f}**")
                st.markdown(f"Profit: **{sip_sign}₹{abs(profit_sip):,.0f}** ({(profit_sip / max(invested_sip, 1)) * 100:+.1f}%)")

        portfolio = load_portfolio()
        mf_b1, mf_b2 = st.columns([2, 1])
        mf_dummy_amt = mf_b1.number_input(
            "Invest Dummy Money in this Mutual Fund (₹):",
            min_value=500.0,
            max_value=max(500.0, float(portfolio["cash"])),
            value=min(5000.0, max(500.0, float(portfolio["cash"]))),
            step=500.0,
            key="mf_dummy_amt",
        )
        if mf_b2.button("💸 Start Dummy MF Investment", type="primary"):
            if mf_dummy_amt <= portfolio["cash"]:
                units = round(mf_dummy_amt / latest_nav, 4)
                portfolio["cash"] = round(portfolio["cash"] - mf_dummy_amt, 2)
                portfolio["holdings"].append(
                    {
                        "id": int(now_ist().timestamp()),
                        "asset_type": "MF",
                        "ticker": selected_scheme_code,
                        "name": f"MF: {selected_mf_name[:45]}",
                        "buy_price": round(latest_nav, 2),
                        "qty": units,
                        "invested": round(mf_dummy_amt, 2),
                        "buy_date": now_ist().strftime("%d %b %Y, %I:%M %p"),
                        "target_price": round(latest_nav * 1.20, 2),
                        "stop_loss": round(latest_nav * 0.85, 2),
                    }
                )
                save_portfolio(portfolio)
                st.success(f"Invested ₹{mf_dummy_amt:,.2f} dummy money ({units} units) into **{selected_mf_name}**! Track it in Tab 4.")
            else:
                st.error("Not enough dummy cash! Check Tab 4.")

# ==============================================================================
# TAB 4: LIVE AUTO-UPDATING DUMMY PORTFOLIO & SELL ALERTS
# ==============================================================================
with tab4:
    @st.fragment(run_every=AUTO_INTERVAL)
    def render_live_dummy_portfolio():
        st.subheader("🎮 My Dummy Portfolio & Live Sell Predictions")
        st.caption(f"⏱️ Live P&L Updated: **{now_ist().strftime('%I:%M:%S %p IST')}**")
        portfolio = load_portfolio()

        holdings = portfolio["holdings"]
        total_invested = 0.0
        total_current = 0.0
        enriched_holdings = []

        for h in holdings:
            asset_type = h.get("asset_type", "STOCK")
            if asset_type == "MF":
                try:
                    _, _, live_info = fetch_mf_nav(h["ticker"])
                except Exception:
                    live_info = None
            else:
                _, live_info = fetch_single_stock_live(h["ticker"])

            live_price = live_info["price"] if live_info else h["buy_price"]
            cur_val = round(live_price * h["qty"], 2)
            pnl = round(cur_val - h["invested"], 2)
            pnl_pct = round((pnl / h["invested"]) * 100.0, 2) if h["invested"] > 0 else 0.0

            if live_info:
                sell_signal, sell_reason = predict_when_to_sell(h, live_info)
            else:
                sell_signal, sell_reason = "⏳ Unable to fetch live price", "Click Refresh Now above."

            total_invested += h["invested"]
            total_current += cur_val
            enriched_holdings.append((h, live_price, cur_val, pnl, pnl_pct, sell_signal, sell_reason))

        total_net_worth = portfolio["cash"] + total_current
        overall_pnl = total_net_worth - 100000.0
        holdings_pnl = total_current - total_invested

        p1, p2, p3, p4 = st.columns(4)
        p1.metric("Virtual Net Worth", f"₹{total_net_worth:,.2f}", delta=fmt_delta_rs(overall_pnl, " overall"))
        p2.metric("Dummy Cash Left", f"₹{portfolio['cash']:,.2f}")
        p3.metric("Currently Invested", f"₹{total_invested:,.2f}")
        p4.metric("Current Holdings Value", f"₹{total_current:,.2f}", delta=fmt_delta_rs(holdings_pnl))

        if not enriched_holdings:
            st.info("You have no active dummy investments yet. Try buying a stock in **Tab 2** or Gold / Mutual Funds in **Tab 3**!")
        else:
            st.markdown("### Active Dummy Investments — When Should You Sell?")
            for h, live_price, cur_val, pnl, pnl_pct, sell_signal, sell_reason in enriched_holdings:
                with st.container(border=True):
                    c1, c2, c3, c4 = st.columns([1.8, 1.5, 2.5, 1.2])
                    label = h.get("name", h["ticker"])
                    unit_word = "units" if h.get("asset_type") == "MF" else "shares"
                    c1.markdown(f"**{label}**")
                    c1.caption(f"Bought {h['qty']} {unit_word} @ ₹{h['buy_price']:,.2f}\nOn {h['buy_date']}")

                    c2.metric("Live Value", f"₹{cur_val:,.2f}", delta=fmt_delta_rs(pnl, f" ({pnl_pct:+.2f}%)"))
                    c2.caption(f"Live Price / NAV: ₹{live_price:,.2f}")

                    c3.markdown(f"**Sell Prediction:** {sell_signal}")
                    c3.caption(sell_reason)
                    if h.get("asset_type") != "MF":
                        c3.caption(f"🎯 Target: ₹{h['target_price']:,.2f}  |  🛡️ Stop-Loss: ₹{h['stop_loss']:,.2f}")

                    if c4.button("Sell Now (Dummy)", key=f"sell_{h['id']}", type="primary"):
                        portfolio["cash"] = round(portfolio["cash"] + cur_val, 2)
                        portfolio["history"].append(
                            {
                                "Asset": label,
                                "Qty": h["qty"],
                                "Buy (₹)": h["buy_price"],
                                "Sell (₹)": live_price,
                                "Profit/Loss (₹)": pnl,
                                "Return (%)": pnl_pct,
                                "Sold On": now_ist().strftime("%d %b %Y, %I:%M %p"),
                            }
                        )
                        portfolio["holdings"] = [item for item in portfolio["holdings"] if item["id"] != h["id"]]
                        save_portfolio(portfolio)
                        st.rerun()

        if portfolio["history"]:
            st.divider()
            st.markdown("### Past Completed Dummy Trades")
            st.dataframe(pd.DataFrame(portfolio["history"]).iloc[::-1], use_container_width=True, hide_index=True)

        st.divider()
        if st.button("🔁 Reset Dummy Wallet Back to ₹1,00,000"):
            save_portfolio({"cash": 100000.0, "holdings": [], "history": []})
            st.rerun()

    render_live_dummy_portfolio()