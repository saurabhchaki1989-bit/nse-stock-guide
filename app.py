import html
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

st.set_page_config(
    page_title="NSE/BSE Live Stocks, SIPs & Gold",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ------------------------------------------------------------------------------
# MODERN MOBILE-FIRST + DESKTOP RESPONSIVE CSS (LIGHT & DARK MODE FRIENDLY)
# ------------------------------------------------------------------------------
st.markdown(
    """
    <style>
    /* Tighten page spacing for mobile & desktop */
    .block-container {
        padding-top: 1rem !important;
        padding-bottom: 2rem !important;
        padding-left: 0.9rem !important;
        padding-right: 0.9rem !important;
        max-width: 1250px;
    }

    /* Clean compact app header */
    .app-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        flex-wrap: wrap;
        gap: 8px;
        margin-bottom: 0.4rem;
    }
    .app-title {
        font-size: 1.45rem;
        font-weight: 800;
        margin: 0;
        letter-spacing: -0.3px;
    }
    .status-pill {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 4px 10px;
        border-radius: 999px;
        font-size: 0.78rem;
        font-weight: 600;
    }
    .status-open { background: rgba(22, 163, 74, 0.14); color: #16a34a; border: 1px solid rgba(22, 163, 74, 0.3); }
    .status-closed { background: rgba(100, 116, 139, 0.14); color: #64748b; border: 1px solid rgba(100, 116, 139, 0.3); }

    /* Compact section headings */
    .sec-title {
        font-size: 1.1rem;
        font-weight: 700;
        margin: 0.8rem 0 0.25rem 0;
    }
    .sec-sub {
        font-size: 0.8rem;
        opacity: 0.72;
        margin-bottom: 0.65rem;
    }

    /* Responsive Fintech Card Grid (1 col on Mobile, 2-3 cols on Desktop) */
    .card-grid {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(285px, 1fr));
        gap: 10px;
        margin-bottom: 0.8rem;
    }
    .grid-2col {
        display: grid;
        grid-template-columns: repeat(2, 1fr);
        gap: 8px;
        margin-bottom: 0.8rem;
    }
    @media (min-width: 769px) {
        .grid-2col-desktop4 {
            grid-template-columns: repeat(4, 1fr);
        }
    }

    /* Modern Stock / MF Card */
    .fin-card {
        background: rgba(128, 128, 128, 0.055);
        border: 1px solid rgba(128, 128, 128, 0.20);
        border-radius: 14px;
        padding: 12px 14px;
        transition: border-color 0.2s ease;
    }
    .fin-row {
        display: flex;
        justify-content: space-between;
        align-items: flex-start;
        gap: 8px;
    }
    .fin-name {
        font-weight: 700;
        font-size: 0.96rem;
        line-height: 1.25;
    }
    .fin-meta {
        font-size: 0.75rem;
        opacity: 0.7;
        margin-top: 2px;
    }
    .fin-price {
        font-weight: 800;
        font-size: 1.08rem;
        text-align: right;
        white-space: nowrap;
    }
    .pill-up {
        display: inline-block;
        background: rgba(22, 163, 74, 0.14);
        color: #16a34a;
        padding: 2px 7px;
        border-radius: 6px;
        font-size: 0.74rem;
        font-weight: 700;
        margin-top: 3px;
    }
    .pill-down {
        display: inline-block;
        background: rgba(220, 38, 38, 0.14);
        color: #dc2626;
        padding: 2px 7px;
        border-radius: 6px;
        font-size: 0.74rem;
        font-weight: 700;
        margin-top: 3px;
    }
    .pill-tag {
        display: inline-block;
        background: rgba(59, 130, 246, 0.12);
        border: 1px solid rgba(59, 130, 246, 0.25);
        padding: 3px 8px;
        border-radius: 8px;
        font-size: 0.74rem;
        font-weight: 600;
        margin-top: 8px;
    }
    .fin-footer {
        display: flex;
        justify-content: space-between;
        font-size: 0.76rem;
        opacity: 0.85;
        margin-top: 8px;
        padding-top: 7px;
        border-top: 1px dashed rgba(128, 128, 128, 0.22);
    }

    /* Compact KPI stat box (2x2 on mobile, 4-across on desktop) */
    .kpi-box {
        background: rgba(128, 128, 128, 0.055);
        border: 1px solid rgba(128, 128, 128, 0.20);
        border-radius: 12px;
        padding: 10px 12px;
    }
    .kpi-label {
        font-size: 0.73rem;
        opacity: 0.72;
        font-weight: 600;
    }
    .kpi-val {
        font-size: 1.08rem;
        font-weight: 800;
        margin-top: 2px;
    }
    .kpi-sub-up { font-size: 0.74rem; color: #16a34a; font-weight: 700; margin-top: 2px; }
    .kpi-sub-down { font-size: 0.74rem; color: #dc2626; font-weight: 700; margin-top: 2px; }
    .kpi-sub-muted { font-size: 0.73rem; opacity: 0.7; margin-top: 2px; }

    /* Forecast Range Box */
    .range-hi { color: #16a34a; font-weight: 700; font-size: 0.84rem; margin-top: 4px; }
    .range-lo { color: #dc2626; font-weight: 700; font-size: 0.84rem; margin-top: 2px; }

    /* Make tabs evenly spaced & crisp on mobile */
    button[data-baseweb="tab"] {
        padding-left: 10px !important;
        padding-right: 10px !important;
        font-weight: 600 !important;
        font-size: 0.88rem !important;
    }

    /* Mobile-only tweaks */
    @media (max-width: 640px) {
        .app-title { font-size: 1.2rem; }
        .card-grid { grid-template-columns: 1fr; gap: 8px; }
        button[data-baseweb="tab"] { font-size: 0.82rem !important; padding: 6px 8px !important; }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

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
    "GOLDBEES.NS": ("🪙 Gold ETF (GoldBees)", "Tracks live Indian Gold"),
    "SILVERBEES.NS": ("🥈 Silver ETF (SilverBees)", "Tracks live Indian Silver"),
    "NIFTYBEES.NS": ("📊 Nifty 50 ETF (NiftyBees)", "Top 50 Indian companies"),
    "JUNIORBEES.NS": ("🚀 Nifty Next 50 ETF", "Fast-growing large caps"),
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


def pct_pill(val: float, suffix: str = "") -> str:
    cls = "pill-up" if val >= 0 else "pill-down"
    arrow = "▲" if val >= 0 else "▼"
    return f'<span class="{cls}">{arrow} {val:+.2f}%{suffix}</span>'


def rs_signed(val: float) -> str:
    sign = "-" if val < 0 else "+"
    return f"{sign}₹{abs(val):,.2f}"


# ------------------------------------------------------------------------------
# HTML CARD RENDERERS (SLEEK MOBILE + DESKTOP CARDS)
# ------------------------------------------------------------------------------
def render_stock_cards(df: pd.DataFrame, rank_start: int | None = None):
    cards_html = ['<div class="card-grid">']
    for idx, (_, row) in enumerate(df.iterrows()):
        rank_prefix = f"#{rank_start + idx} " if rank_start is not None else ""
        comp = html.escape(str(row["Company"]))
        sym = html.escape(str(row["Symbol"]))
        vol = html.escape(str(row["Volume Activity"]))
        badge = html.escape(str(row["Highlight"]))
        card = f"""
        <div class="fin-card">
            <div class="fin-row">
                <div>
                    <div class="fin-name">{rank_prefix}{comp}</div>
                    <div class="fin-meta">{sym} · Vol: {vol}</div>
                </div>
                <div style="text-align:right;">
                    <div class="fin-price">₹{row['Price (₹)']:,.2f}</div>
                    {pct_pill(row['Daily (%)'], ' today')}
                </div>
            </div>
            <div><span class="pill-tag">{badge}</span></div>
            <div class="fin-footer">
                <span>🎯 Sell: <b>₹{row['Target Sell (₹)']:,.2f}</b></span>
                <span>🛡️ Stop: <b>₹{row['Safety Stop (₹)']:,.2f}</b></span>
            </div>
            <div class="fin-meta" style="margin-top:5px;">
                Wk: <b>{row['Weekly (%)']:+.1f}%</b> · Mo: <b>{row['Monthly (%)']:+.1f}%</b> · Action: <b>{row['Suggestion']}</b>
            </div>
        </div>
        """
        cards_html.append(card)
    cards_html.append("</div>")
    st.markdown("".join(cards_html), unsafe_allow_html=True)


def render_perf_cards(df: pd.DataFrame, highlight_col: str):
    cards_html = ['<div class="card-grid">']
    for _, row in df.iterrows():
        comp = html.escape(str(row["Company"]))
        sym = html.escape(str(row["Symbol"]))
        main_val = float(row[highlight_col])
        card = f"""
        <div class="fin-card">
            <div class="fin-row">
                <div>
                    <div class="fin-name">{comp}</div>
                    <div class="fin-meta">{sym} · {html.escape(str(row['Trend']))}</div>
                </div>
                <div style="text-align:right;">
                    <div class="fin-price">₹{row['Price (₹)']:,.2f}</div>
                    {pct_pill(main_val)}
                </div>
            </div>
            <div class="fin-footer">
                <span>1D: <b>{row['Daily (%)']:+.1f}%</b></span>
                <span>1W: <b>{row['Weekly (%)']:+.1f}%</b></span>
                <span>1M: <b>{row['Monthly (%)']:+.1f}%</b></span>
            </div>
        </div>
        """
        cards_html.append(card)
    cards_html.append("</div>")
    st.markdown("".join(cards_html), unsafe_allow_html=True)


def render_mf_cards(df: pd.DataFrame, ranked: bool = True):
    cards_html = ['<div class="card-grid">']
    for idx, (_, row) in enumerate(df.iterrows()):
        rank_prefix = f"#{idx + 1} " if ranked else ""
        fname = html.escape(str(row["Fund Name"]).replace(" (Direct Growth)", ""))
        cat = html.escape(str(row["Category"]))
        badge = html.escape(str(row["Highlight"]))
        sip_p = html.escape(str(row["₹5k/mo SIP Profit (3Y)"]))
        card = f"""
        <div class="fin-card">
            <div class="fin-row">
                <div>
                    <div class="fin-name">{rank_prefix}{fname}</div>
                    <div class="fin-meta">{cat} · NAV ₹{row['Latest NAV (₹)']:,.2f}</div>
                </div>
                <div style="text-align:right;">
                    <div class="fin-price">{row['3-Year (%/yr)']}%/yr</div>
                    {pct_pill(row['1-Month (%)'], ' (1M)')}
                </div>
            </div>
            <div><span class="pill-tag">{badge}</span></div>
            <div class="fin-footer">
                <span>1Y: <b>{row['1-Year (%)']:+.1f}%</b></span>
                <span>₹5k SIP (3Y): <b>{sip_p}</b></span>
            </div>
        </div>
        """
        cards_html.append(card)
    cards_html.append("</div>")
    st.markdown("".join(cards_html), unsafe_allow_html=True)


# ------------------------------------------------------------------------------
# NEWS, PORTFOLIO & DATA FUNCTIONS
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
                    items.append({"title": title, "link": link, "published": pub, "mood": score_headline(title)})
    except Exception:
        pass
    return items


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

    vol_ratio = 1.0
    if volume is not None:
        vol_clean = volume.dropna()
        if len(vol_clean) >= 20:
            avg_v = float(vol_clean.tail(21).iloc[:-1].mean())
            latest_v = float(vol_clean.iloc[-1])
            if avg_v > 0 and latest_v > 0:
                vol_ratio = round(latest_v / avg_v, 2)

    if vol_ratio >= 1.35:
        vol_label = f"{vol_ratio}x Buying 🟢" if daily_pct >= 0 else f"{vol_ratio}x Selling 🔴"
    else:
        vol_label = f"{vol_ratio}x avg"

    daily_returns = close.pct_change().dropna()
    daily_vol = float(daily_returns.tail(20).std()) if len(daily_returns) >= 10 else 0.02
    daily_vol = max(0.008, min(daily_vol, 0.055))

    day_move = min(daily_vol * 1.25, 0.08)
    week_move = min(daily_vol * math.sqrt(5), 0.20)
    month_move = min(daily_vol * math.sqrt(21), 0.35)
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
        move_badge = "🚀 STARTING TO RISE"
        is_on_move = True
    elif monthly_pct >= 4.0 and score >= 65:
        move_badge = "🏆 STEADY PROFIT MAKER"
        is_on_move = False
    elif rsi < 35:
        move_badge = "💡 OVERSOLD DIP"
        is_on_move = False
    else:
        move_badge = "➡️ NORMAL ACTIVITY"
        is_on_move = False

    if score >= 70:
        trend = "Going Up 📈"
        action = "BUY"
        reason = "Strong upward trend above 20 & 50-day averages with active buyer interest."
    elif score >= 50:
        trend = "Steady ➡️"
        action = "HOLD / WATCH"
        reason = "Steady movement. Good to hold or wait for a clearer breakout."
    else:
        trend = "Going Down 📉"
        action = "AVOID / SELL"
        reason = "Trading below recent averages with weak momentum (wait for selling to stabilize)."

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
                status = "🔥 ON THE MOVE"
                is_hot = True
            elif r3y >= 15 and r1m < 0:
                status = "💡 GREAT TIME TO START SIP"
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
                "₹5k/mo SIP Profit (3Y)": f"{sign}₹{abs(profit_rs):,.0f} ({profit_pct:+.0f}%)",
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
            return "🟠 BOOK PARTIAL PROFIT", f"Strong gain (+{pnl_pct:.1f}%) and overheated. Good zone to book partial profit."
        if live_info["action"] == "AVOID / SELL":
            return "🟢 GOOD TIME TO ADD SIP", "Fund is in a dip — great time to add SIP units."
        return "🟢 HOLD & CONTINUE SIP", f"Steady growth ({pnl_pct:+.1f}%). Mutual funds work best held 1+ year."

    if live_price >= holding["target_price"]:
        return "🔴 SELL NOW (Target Hit!)", f"Hit your profit target (+{pnl_pct:.1f}%). Book profits now."
    if live_price <= holding["stop_loss"]:
        return "🔴 SELL NOW (Stop Hit)", f"Dropped below safety stop ({pnl_pct:.1f}%). Exit to protect capital."
    if live_info["rsi"] > 75 and pnl_pct > 2:
        return "🟠 CONSIDER SELLING", f"Rose sharply (RSI {live_info['rsi']}) and may pull back soon."
    if live_info["action"] == "AVOID / SELL":
        return "🟠 EXIT SOON (Weak Trend)", "Dropped below its 20-day average."
    return "🟢 HOLD (Trend Strong)", f"Stay invested. Target sell: ₹{holding['target_price']:,.2f}."


# ------------------------------------------------------------------------------
# COMPACT MODERN HEADER (GREAT ON MOBILE & DESKTOP)
# ------------------------------------------------------------------------------
mkt_badge = (
    '<span class="status-pill status-open">● Market OPEN</span>'
    if is_market_open()
    else '<span class="status-pill status-closed">● Market Closed</span>'
)
st.markdown(
    f"""
    <div class="app-header">
        <div class="app-title">📈 India Stock, SIP & Gold</div>
        <div>{mkt_badge}</div>
    </div>
    """,
    unsafe_allow_html=True,
)

ctrl1, ctrl2, ctrl3 = st.columns([1.2, 1.4, 0.9])
exchange = ctrl1.radio("Exchange", ["NSE", "BSE"], horizontal=True, label_visibility="collapsed")
live_mode = ctrl2.toggle("🔴 Live (15s)", value=True)
if ctrl3.button("🔄 Refresh", use_container_width=True):
    _fetch_live_1m_prices.clear()
    fetch_live_news.clear()
    st.rerun()

AUTO_INTERVAL = 15 if live_mode else None

# SHORT, MOBILE-FRIENDLY TABS (ALL 4 VISIBLE AT ONCE ON IPHONE & ANDROID!)
tab1, tab2, tab3, tab4 = st.tabs(
    [
        "🏆 Stocks",
        "🔍 Search",
        "🪙 SIP & Gold",
        "🎮 Dummy",
    ]
)

# ==============================================================================
# TAB 1: TOP 10 STOCKS, ON-THE-MOVE BUZZ & BOTTOM PERFORMERS
# ==============================================================================
with tab1:
    stock_news = fetch_live_news("NSE BSE Indian stocks rally buy volume surge", max_items=6)

    @st.fragment(run_every=AUTO_INTERVAL)
    def render_live_market_board():
        market_df = scan_market_live(exchange, stock_news)
        st.caption(f"⏱️ Updated {now_ist().strftime('%I:%M:%S %p IST')} · {exchange} Live Feed")

        if market_df.empty:
            st.error("Could not load market data right now. Tap Refresh.")
            return

        # 1. ON THE MOVE CARDS
        on_move_df = market_df[market_df["IsOnMove"]].sort_values("Score", ascending=False).head(6)
        st.markdown(f'<div class="sec-title">🔥 {exchange} On The Move</div>', unsafe_allow_html=True)
        st.markdown('<div class="sec-sub">Active buying surge, positive news, or fresh breakout</div>', unsafe_allow_html=True)

        if not on_move_df.empty:
            render_stock_cards(on_move_df)
        else:
            st.info("No sudden volume surges right now — see Top 10 picks below.")

        with st.expander("📰 Live Market News & Insights"):
            if stock_news:
                for n in stock_news:
                    st.markdown(f"{n['mood']} · [{n['title']}]({n['link']}) `{n['published']}`")
            else:
                st.caption("News feed temporarily unavailable.")

        # 2. TOP 10 PROFITABLE STOCKS (CARD VIEW FOR MOBILE + OPTIONAL TABLE FOR DESKTOP)
        st.markdown(f'<div class="sec-title">🏆 Top 10 Profitable {exchange} Stocks</div>', unsafe_allow_html=True)
        view_mode = st.radio("Layout", ["📱 Modern Cards", "📊 Full Table"], horizontal=True, label_visibility="collapsed", key="top10_view")

        top10 = market_df.sort_values(["Score", "Monthly (%)"], ascending=False).head(10)
        if view_mode == "📱 Modern Cards":
            render_stock_cards(top10, rank_start=1)
        else:
            top10_tbl = top10.copy()
            top10_tbl.insert(0, "Rank", range(1, len(top10_tbl) + 1))
            st.dataframe(
                top10_tbl[
                    ["Rank", "Company", "Symbol", "Highlight", "Price (₹)", "Daily (%)", "Weekly (%)", "Monthly (%)", "Volume Activity", "Target Sell (₹)", "Safety Stop (₹)"]
                ],
                use_container_width=True,
                hide_index=True,
            )

        # 3. BOTTOM PERFORMERS & TOP GAINERS (DAILY / WEEKLY / MONTHLY)
        st.markdown(f'<div class="sec-title">📉 Bottom Performers & Gainers</div>', unsafe_allow_html=True)
        period_choice = st.radio("Timeframe", ["Daily", "Weekly", "Monthly"], horizontal=True, label_visibility="collapsed", key="perf_tf")
        col_map = {"Daily": "Daily (%)", "Weekly": "Weekly (%)", "Monthly": "Monthly (%)"}
        sort_col = col_map[period_choice]

        perf_sub = st.radio("Show", ["🔴 Bottom Performers", "🟢 Top Gainers"], horizontal=True, label_visibility="collapsed", key="perf_side")
        if perf_sub == "🔴 Bottom Performers":
            render_perf_cards(market_df.sort_values(sort_col, ascending=True).head(6), sort_col)
        else:
            render_perf_cards(market_df.sort_values(sort_col, ascending=False).head(6), sort_col)

    render_live_market_board()

# ==============================================================================
# TAB 2: LIVE SEARCH + EXPECTED HIGH/LOW FORECAST + NEWS + DUMMY BUY
# ==============================================================================
with tab2:
    st.markdown('<div class="sec-title">🔍 Search Any Indian Stock</div>', unsafe_allow_html=True)

    all_stocks = load_all_indian_stocks()
    option_map = {f"{name} ({sym})": sym for sym, name in sorted(all_stocks.items(), key=lambda x: x[1])}

    selected_label = st.selectbox(
        "Type company name for live suggestions:",
        options=list(option_map.keys()),
        index=None,
        placeholder="Type e.g. Apollo Tubes, Reliance, HAL...",
        label_visibility="collapsed",
    )

    full_ticker = None
    display_name = None

    if selected_label:
        sym = option_map[selected_label]
        full_ticker = f"{sym}.NS" if exchange == "NSE" else f"{sym}.BO"
        display_name = selected_label

    with st.expander("More stocks (Search Yahoo Finance NSE/BSE)"):
        custom_q = st.text_input("Company name:", placeholder="e.g. Mazagon Dock, Cochin Shipyard")
        if custom_q:
            matches = search_yahoo_india(custom_q)
            if matches:
                y_map = {f"{name} ({sym})": sym for sym, name in matches}
                picked_y = st.selectbox("Select match:", list(y_map.keys()))
                full_ticker = y_map[picked_y]
                display_name = picked_y
            else:
                st.warning("No matching Indian stocks found.")

    if not full_ticker:
        st.info("👆 Tap the search box above and start typing any company name (like **Apollo Tubes**, **HAL**, or **Tata Power**).")
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
                st.error(f"Could not fetch live price for **{ticker_to_show}**.")
                return

            st.caption(f"⏱️ Live Quote: {now_ist().strftime('%I:%M:%S %p IST')}")

            # Hero Fintech Summary Card
            safe_label = html.escape(label_to_show)
            st.markdown(
                f"""
                <div class="fin-card" style="margin-bottom:10px;">
                    <div class="fin-row">
                        <div>
                            <div class="fin-name" style="font-size:1.08rem;">{safe_label}</div>
                            <div class="fin-meta">{html.escape(ticker_to_show)} · Vol: {html.escape(sinfo['vol_label'])}</div>
                        </div>
                        <div style="text-align:right;">
                            <div class="fin-price" style="font-size:1.25rem;">₹{sinfo['price']:,.2f}</div>
                            {pct_pill(sinfo['daily_pct'], ' today')}
                        </div>
                    </div>
                    <div>
                        <span class="pill-tag">{html.escape(sinfo['move_badge'])}</span>
                        <span class="pill-tag">Action: {html.escape(sinfo['action'])}</span>
                    </div>
                    <div class="fin-footer">
                        <span>🎯 Sell Target: <b>₹{sinfo['sell_target']:,.2f}</b></span>
                        <span>🛡️ Safety Stop: <b>₹{sinfo['stop_loss']:,.2f}</b></span>
                    </div>
                    <div class="fin-meta" style="margin-top:6px;">
                        1W: <b>{sinfo['weekly_pct']:+.2f}%</b> · 1M: <b>{sinfo['monthly_pct']:+.2f}%</b> · {html.escape(sinfo['reason'])}
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            # 2x2 Responsive Price Range Forecast Grid (compact on mobile, 4-across on desktop!)
            st.markdown('<div class="sec-title">📊 Expected High / Low Forecast</div>', unsafe_allow_html=True)
            st.markdown(
                f"""
                <div class="grid-2col grid-2col-desktop4">
                    <div class="kpi-box">
                        <div class="kpi-label">Next 1–2 Days</div>
                        <div class="range-hi">▲ ₹{sinfo['day_high']:,.2f}</div>
                        <div class="range-lo">▼ ₹{sinfo['day_low']:,.2f}</div>
                    </div>
                    <div class="kpi-box">
                        <div class="kpi-label">Next 1 Week</div>
                        <div class="range-hi">▲ ₹{sinfo['week_high']:,.2f}</div>
                        <div class="range-lo">▼ ₹{sinfo['week_low']:,.2f}</div>
                    </div>
                    <div class="kpi-box">
                        <div class="kpi-label">Next 1 Month</div>
                        <div class="range-hi">▲ ₹{sinfo['month_high']:,.2f}</div>
                        <div class="range-lo">▼ ₹{sinfo['month_low']:,.2f}</div>
                    </div>
                    <div class="kpi-box">
                        <div class="kpi-label">52-Wk Ceiling/Floor</div>
                        <div class="range-hi">⬆️ ₹{sinfo['high_52w']:,.2f}</div>
                        <div class="range-lo">⬇️ ₹{sinfo['low_52w']:,.2f}</div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            # Clean Mobile-Friendly Chart (no cluttered toolbar)
            sdf_plot = sdf.tail(90).copy()
            sdf_plot["20-Day Avg"] = sdf["Close"].rolling(20).mean().tail(90)

            fig = go.Figure()
            fig.add_trace(go.Scatter(x=sdf_plot.index, y=sdf_plot["Close"], name="Price (₹)", line=dict(color="#2563eb", width=2.4)))
            fig.add_trace(go.Scatter(x=sdf_plot.index, y=sdf_plot["20-Day Avg"], name="20D Trend", line=dict(color="#f59e0b", dash="dot", width=1.6)))
            fig.add_hline(y=sinfo["week_high"], line_dash="dash", line_color="#16a34a", annotation_text=f"1W Hi ₹{sinfo['week_high']}")
            fig.add_hline(y=sinfo["week_low"], line_dash="dash", line_color="#dc2626", annotation_text=f"1W Lo ₹{sinfo['week_low']}")
            fig.update_layout(
                height=290,
                margin=dict(l=6, r=6, t=28, b=6),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
                xaxis=dict(fixedrange=True),
                yaxis=dict(fixedrange=True),
            )
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

            # Live Stock News
            clean_name = label_to_show.split("(")[0].strip()
            comp_news = fetch_live_news(f"{clean_name} stock share price India", max_items=4)
            if comp_news:
                with st.expander(f"📰 Live News: {clean_name}", expanded=True):
                    for n in comp_news:
                        st.markdown(f"{n['mood']} · [{n['title']}]({n['link']}) `{n['published']}`")

            # Dummy Buy Box
            st.markdown('<div class="sec-title">🎮 Practice Dummy Buy</div>', unsafe_allow_html=True)
            portfolio = load_portfolio()
            st.caption(f"Dummy Cash Available: **₹{portfolio['cash']:,.2f}**")

            d1, d2 = st.columns([1.6, 1])
            dummy_amt = d1.number_input(
                "Amount (₹)",
                min_value=500.0,
                max_value=max(500.0, float(portfolio["cash"])),
                value=min(10000.0, max(500.0, float(portfolio["cash"]))),
                step=500.0,
                key="stock_dummy_amt",
            )
            qty = int(dummy_amt // sinfo["price"])
            actual_cost = round(qty * sinfo["price"], 2)
            st.caption(f"Buys **{qty} shares** @ ₹{sinfo['price']:,.2f} (Total: ₹{actual_cost:,.2f})")

            if d2.button("💸 Buy Dummy", type="primary", use_container_width=True, key="buy_stock_btn"):
                if qty <= 0:
                    st.warning("Increase amount to buy at least 1 share.")
                elif actual_cost > portfolio["cash"]:
                    st.error("Not enough dummy cash! Check Dummy tab.")
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
                    st.success(f"Bought {qty} dummy shares of **{label_to_show}**! Check the **🎮 Dummy** tab.")

        render_searched_stock_live(full_ticker, display_name)

# ==============================================================================
# TAB 3: TOP 10 PROFITABLE SIPs, MUTUAL FUNDS & GOLD
# ==============================================================================
with tab3:
    mf_news = fetch_live_news("India mutual fund SIP inflow top performing funds gold", max_items=6)

    with st.spinner("Loading Top 10 Profitable SIPs & Mutual Funds..."):
        mf_board = scan_top_mutual_funds()

    # 1. HOT SIPs & MFs
    st.markdown('<div class="sec-title">🔥 SIPs & MFs On The Move</div>', unsafe_allow_html=True)
    if not mf_board.empty:
        hot_mfs = mf_board[mf_board["IsHot"]].head(4)
        if hot_mfs.empty:
            hot_mfs = mf_board.head(4)
        render_mf_cards(hot_mfs, ranked=False)

    with st.expander("📰 Live Mutual Fund, SIP & Gold News"):
        if mf_news:
            for n in mf_news:
                st.markdown(f"{n['mood']} · [{n['title']}]({n['link']}) `{n['published']}`")
        else:
            st.caption("News feed temporarily unavailable.")

    # 2. TOP 10 PROFITABLE SIPs & MFs
    st.markdown('<div class="sec-title">🏆 Top 10 Profitable SIPs & MFs</div>', unsafe_allow_html=True)
    st.markdown('<div class="sec-sub">Ranked by real 3-year profit on a ₹5,000/month SIP (Official AMFI NAVs)</div>', unsafe_allow_html=True)
    mf_view = st.radio("MF Layout", ["📱 Modern Cards", "📊 Full Table"], horizontal=True, label_visibility="collapsed", key="mf_view")

    if not mf_board.empty:
        top10_mf = mf_board.head(10).copy()
        if mf_view == "📱 Modern Cards":
            render_mf_cards(top10_mf, ranked=True)
        else:
            top10_mf.insert(0, "Rank", range(1, len(top10_mf) + 1))
            st.dataframe(
                top10_mf[["Rank", "Fund Name", "Category", "Highlight", "Latest NAV (₹)", "1-Month (%)", "1-Year (%)", "3-Year (%/yr)", "₹5k/mo SIP Profit (3Y)"]],
                use_container_width=True,
                hide_index=True,
            )

    # 3. LIVE GOLD, SILVER & INDEX ETFs
    @st.fragment(run_every=AUTO_INTERVAL)
    def render_live_gold_etfs():
        st.markdown('<div class="sec-title">🪙 Gold, Silver & Nifty ETFs (Live)</div>', unsafe_allow_html=True)
        st.caption(f"⏱️ Live ETF Prices: {now_ist().strftime('%I:%M:%S %p IST')}")

        portfolio = load_portfolio()
        etf_cols = st.columns(2)
        for idx, (etf_ticker, (etf_title, etf_desc)) in enumerate(GOLD_AND_ETFS.items()):
            _, etf_info = fetch_single_stock_live(etf_ticker)
            with etf_cols[idx % 2]:
                if etf_info:
                    st.markdown(
                        f"""
                        <div class="fin-card" style="margin-bottom:6px;">
                            <div class="fin-row">
                                <div>
                                    <div class="fin-name">{html.escape(etf_title)}</div>
                                    <div class="fin-meta">{html.escape(etf_desc)}</div>
                                </div>
                                <div style="text-align:right;">
                                    <div class="fin-price">₹{etf_info['price']:,.2f}</div>
                                    {pct_pill(etf_info['daily_pct'], ' today')}
                                </div>
                            </div>
                            <div><span class="pill-tag">{html.escape(etf_info['move_badge'])}</span></div>
                            <div class="fin-footer">
                                <span>🎯 ₹{etf_info['sell_target']}</span>
                                <span>🛡️ ₹{etf_info['stop_loss']}</span>
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                    if st.button(f"Buy ₹5,000 Dummy ({etf_ticker.replace('.NS', '')})", key=f"buy_etf_{etf_ticker}", use_container_width=True):
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
                            st.warning("Not enough dummy cash!")

    render_live_gold_etfs()

    # 4. SEARCH ANY MUTUAL FUND + SIP CALCULATOR
    st.markdown('<div class="sec-title">🔍 Search Any Mutual Fund & SIP Calculator</div>', unsafe_allow_html=True)
    mf_choice_mode = st.selectbox("Pick a Popular Fund:", list(POPULAR_MFS.keys()))
    mf_search_text = st.text_input("Or search ANY Indian Mutual Fund:", placeholder="e.g. Axis Bluechip, Quant Mid Cap...")

    selected_scheme_code = POPULAR_MFS[mf_choice_mode][0]
    selected_mf_name = mf_choice_mode

    if mf_search_text and len(mf_search_text.strip()) >= 3:
        mf_results = search_amfi_mutual_funds(mf_search_text)
        if mf_results:
            mf_map = {f"{m['schemeName']}": str(m["schemeCode"]) for m in mf_results}
            picked_mf = st.selectbox("Select matching AMFI Fund:", list(mf_map.keys()))
            selected_scheme_code = mf_map[picked_mf]
            selected_mf_name = picked_mf

    try:
        meta, mf_df, mf_info = fetch_mf_nav(selected_scheme_code)
    except Exception:
        mf_df, mf_info = pd.DataFrame(), None

    if mf_info is not None and not mf_df.empty:
        latest_nav = float(mf_df["nav"].iloc[-1])
        latest_dt = mf_df.index[-1]

        sc1, sc2 = st.columns(2)
        sip_monthly = sc1.number_input("Monthly SIP (₹)", min_value=500, value=5000, step=500)
        sip_years = sc2.slider("Duration (Years)", 1, 5, 3)

        start_dt = latest_dt - pd.DateOffset(years=sip_years)
        sip_slice = mf_df[mf_df.index >= start_dt]
        monthly_pts = sip_slice.groupby(sip_slice.index.to_period("M")).head(1)
        invested_sip = len(monthly_pts) * sip_monthly
        units_sip = sum(sip_monthly / float(n) for n in monthly_pts["nav"])
        val_sip = units_sip * latest_nav
        profit_sip = val_sip - invested_sip
        sip_pct = (profit_sip / max(invested_sip, 1)) * 100

        st.markdown(
            f"""
            <div class="fin-card" style="margin:8px 0;">
                <div class="fin-name">{html.escape(selected_mf_name)}</div>
                <div class="fin-meta">Official NAV: ₹{latest_nav:,.2f} ({latest_dt.strftime('%d %b %Y')})</div>
                <div class="fin-footer">
                    <span>Invested: <b>₹{invested_sip:,.0f}</b></span>
                    <span>Today: <b>₹{val_sip:,.0f}</b></span>
                </div>
                <div style="margin-top:6px;">Profit: <b>{rs_signed(profit_sip)}</b> {pct_pill(sip_pct)}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        portfolio = load_portfolio()
        mb1, mb2 = st.columns([1.5, 1])
        mf_dummy_amt = mb1.number_input(
            "Dummy MF Amount (₹)",
            min_value=500.0,
            max_value=max(500.0, float(portfolio["cash"])),
            value=min(5000.0, max(500.0, float(portfolio["cash"]))),
            step=500.0,
            key="mf_dummy_amt",
        )
        if mb2.button("💸 Buy Dummy MF", type="primary", use_container_width=True):
            if mf_dummy_amt <= portfolio["cash"]:
                units = round(mf_dummy_amt / latest_nav, 4)
                portfolio["cash"] = round(portfolio["cash"] - mf_dummy_amt, 2)
                portfolio["holdings"].append(
                    {
                        "id": int(now_ist().timestamp()),
                        "asset_type": "MF",
                        "ticker": selected_scheme_code,
                        "name": f"MF: {selected_mf_name[:42]}",
                        "buy_price": round(latest_nav, 2),
                        "qty": units,
                        "invested": round(mf_dummy_amt, 2),
                        "buy_date": now_ist().strftime("%d %b %Y, %I:%M %p"),
                        "target_price": round(latest_nav * 1.20, 2),
                        "stop_loss": round(latest_nav * 0.85, 2),
                    }
                )
                save_portfolio(portfolio)
                st.success(f"Invested ₹{mf_dummy_amt:,.2f} dummy into this Mutual Fund! Check **🎮 Dummy** tab.")
            else:
                st.error("Not enough dummy cash!")

# ==============================================================================
# TAB 4: MOBILE-FRIENDLY DUMMY PORTFOLIO & LIVE SELL ALERTS
# ==============================================================================
with tab4:
    @st.fragment(run_every=AUTO_INTERVAL)
    def render_live_dummy_portfolio():
        st.markdown('<div class="sec-title">🎮 My Dummy Portfolio</div>', unsafe_allow_html=True)
        st.caption(f"⏱️ Live P&L Updated: {now_ist().strftime('%I:%M:%S %p IST')}")
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
                sell_signal, sell_reason = "⏳ Updating...", "Tap Refresh above."

            total_invested += h["invested"]
            total_current += cur_val
            enriched_holdings.append((h, live_price, cur_val, pnl, pnl_pct, sell_signal, sell_reason))

        total_net_worth = portfolio["cash"] + total_current
        overall_pnl = total_net_worth - 100000.0
        holdings_pnl = total_current - total_invested

        nw_cls = "kpi-sub-up" if overall_pnl >= 0 else "kpi-sub-down"
        nw_arrow = "▲" if overall_pnl >= 0 else "▼"
        hp_cls = "kpi-sub-up" if holdings_pnl >= 0 else "kpi-sub-down"
        hp_arrow = "▲" if holdings_pnl >= 0 else "▼"

        # 2x2 Summary Grid on Mobile (4-across on Desktop!)
        st.markdown(
            f"""
            <div class="grid-2col grid-2col-desktop4">
                <div class="kpi-box">
                    <div class="kpi-label">Virtual Net Worth</div>
                    <div class="kpi-val">₹{total_net_worth:,.2f}</div>
                    <div class="{nw_cls}">{nw_arrow} {rs_signed(overall_pnl)} overall</div>
                </div>
                <div class="kpi-box">
                    <div class="kpi-label">Dummy Cash Left</div>
                    <div class="kpi-val">₹{portfolio['cash']:,.2f}</div>
                    <div class="kpi-sub-muted">Ready to invest</div>
                </div>
                <div class="kpi-box">
                    <div class="kpi-label">Currently Invested</div>
                    <div class="kpi-val">₹{total_invested:,.2f}</div>
                    <div class="kpi-sub-muted">{len(holdings)} active trades</div>
                </div>
                <div class="kpi-box">
                    <div class="kpi-label">Holdings Value</div>
                    <div class="kpi-val">₹{total_current:,.2f}</div>
                    <div class="{hp_cls}">{hp_arrow} {rs_signed(holdings_pnl)}</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        if not enriched_holdings:
            st.info("No active dummy investments yet. Buy a stock in **🔍 Search** or Gold/MF in **🪙 SIP & Gold**!")
        else:
            st.markdown('<div class="sec-title">Active Holdings & Sell Alerts</div>', unsafe_allow_html=True)
            for h, live_price, cur_val, pnl, pnl_pct, sell_signal, sell_reason in enriched_holdings:
                label = html.escape(h.get("name", h["ticker"]))
                unit_word = "units" if h.get("asset_type") == "MF" else "shares"
                pnl_cls = "pill-up" if pnl >= 0 else "pill-down"
                pnl_arrow = "▲" if pnl >= 0 else "▼"
                target_line = (
                    f"<span>🎯 Target: <b>₹{h['target_price']:,.2f}</b></span><span>🛡️ Stop: <b>₹{h['stop_loss']:,.2f}</b></span>"
                    if h.get("asset_type") != "MF"
                    else f"<span>Live NAV: <b>₹{live_price:,.2f}</b></span><span>Long-term SIP</span>"
                )

                st.markdown(
                    f"""
                    <div class="fin-card" style="margin-bottom:6px;">
                        <div class="fin-row">
                            <div>
                                <div class="fin-name">{label}</div>
                                <div class="fin-meta">{h['qty']} {unit_word} @ ₹{h['buy_price']:,.2f} · Live ₹{live_price:,.2f}</div>
                            </div>
                            <div style="text-align:right;">
                                <div class="fin-price">₹{cur_val:,.2f}</div>
                                <span class="{pnl_cls}">{pnl_arrow} {rs_signed(pnl)} ({pnl_pct:+.2f}%)</span>
                            </div>
                        </div>
                        <div><span class="pill-tag">{html.escape(sell_signal)}</span></div>
                        <div class="fin-meta" style="margin-top:5px;">{html.escape(sell_reason)}</div>
                        <div class="fin-footer">{target_line}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                if st.button(f"Sell Now (Dummy) — {h.get('name', h['ticker'])[:24]}", key=f"sell_{h['id']}", type="primary", use_container_width=True):
                    portfolio["cash"] = round(portfolio["cash"] + cur_val, 2)
                    portfolio["history"].append(
                        {
                            "Asset": h.get("name", h["ticker"]),
                            "Qty": h["qty"],
                            "Buy (₹)": h["buy_price"],
                            "Sell (₹)": live_price,
                            "P&L (₹)": pnl,
                            "Return (%)": pnl_pct,
                            "Sold On": now_ist().strftime("%d %b, %I:%M %p"),
                        }
                    )
                    portfolio["holdings"] = [item for item in portfolio["holdings"] if item["id"] != h["id"]]
                    save_portfolio(portfolio)
                    st.rerun()

        if portfolio["history"]:
            st.markdown('<div class="sec-title">Past Completed Trades</div>', unsafe_allow_html=True)
            st.dataframe(pd.DataFrame(portfolio["history"]).iloc[::-1], use_container_width=True, hide_index=True)

        st.divider()
        if st.button("🔁 Reset Dummy Wallet to ₹1,00,000", use_container_width=True):
            save_portfolio({"cash": 100000.0, "holdings": [], "history": []})
            st.rerun()

    render_live_dummy_portfolio()
