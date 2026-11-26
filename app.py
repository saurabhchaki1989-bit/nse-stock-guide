import hashlib
import html
import io
import json
import math
import os
import re
import secrets
import urllib.parse
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

import pandas as pd
import plotly.graph_objects as go
import requests
import streamlit as st
import yfinance as yf

try:
    import gspread
    from google.oauth2.service_account import Credentials
    GSHEETS_LIBS_OK = True
except ImportError:
    GSHEETS_LIBS_OK = False

st.set_page_config(
    page_title="NSE/BSE Live Stocks, Quick Wins, SIPs & Gold",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="collapsed",
)


def render_html(markup: str):
    """Strips blank lines & leading spaces so Streamlit NEVER renders HTML as a code block."""
    cleaned = "\n".join(line.strip() for line in markup.splitlines() if line.strip())
    st.markdown(cleaned, unsafe_allow_html=True)


# ------------------------------------------------------------------------------
# MODERN MOBILE-FIRST + DESKTOP RESPONSIVE CSS
# ------------------------------------------------------------------------------
render_html(
    """
    <style>
    .block-container {
        padding-top: 3.5rem !important;
        padding-bottom: 2.5rem !important;
        padding-left: 0.9rem !important;
        padding-right: 0.9rem !important;
        max-width: 1250px;
    }

    .app-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        flex-wrap: wrap;
        gap: 8px;
        margin-bottom: 0.5rem;
    }
    .app-title { font-size: 1.38rem; font-weight: 800; margin: 0; letter-spacing: -0.3px; }
    .header-badges { display: flex; align-items: center; gap: 6px; flex-wrap: wrap; }

    .status-pill {
        display: inline-flex;
        align-items: center;
        gap: 5px;
        padding: 4px 10px;
        border-radius: 999px;
        font-size: 0.76rem;
        font-weight: 600;
        white-space: nowrap;
    }
    .status-open { background: rgba(22, 163, 74, 0.14); color: #16a34a; border: 1px solid rgba(22, 163, 74, 0.3); }
    .status-closed { background: rgba(220, 38, 38, 0.10); color: #dc2626; border: 1px solid rgba(220, 38, 38, 0.28); }
    .status-user { background: rgba(59, 130, 246, 0.12); color: #2563eb; border: 1px solid rgba(59, 130, 246, 0.28); }

    .frozen-banner {
        background: rgba(100, 116, 139, 0.11);
        border: 1px solid rgba(100, 116, 139, 0.28);
        border-radius: 10px;
        padding: 9px 13px;
        font-size: 0.82rem;
        font-weight: 600;
        margin-bottom: 0.65rem;
    }

    .auth-box {
        max-width: 480px;
        margin: 0.8rem auto;
        background: rgba(128, 128, 128, 0.055);
        border: 1px solid rgba(128, 128, 128, 0.22);
        border-radius: 16px;
        padding: 18px 20px;
        text-align: center;
    }

    .sec-title { font-size: 1.08rem; font-weight: 700; margin: 0.85rem 0 0.25rem 0; }
    .sec-sub { font-size: 0.79rem; opacity: 0.72; margin-bottom: 0.65rem; }

    .card-grid {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(290px, 1fr));
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
        .grid-2col-desktop4 { grid-template-columns: repeat(4, 1fr); }
    }

    .fin-card {
        background: rgba(128, 128, 128, 0.055);
        border: 1px solid rgba(128, 128, 128, 0.20);
        border-radius: 14px;
        padding: 12px 14px;
    }
    .fin-row { display: flex; justify-content: space-between; align-items: flex-start; gap: 8px; }
    .fin-name { font-weight: 700; font-size: 0.96rem; line-height: 1.25; }
    .fin-meta { font-size: 0.75rem; opacity: 0.74; margin-top: 2px; }
    .fin-price { font-weight: 800; font-size: 1.08rem; text-align: right; white-space: nowrap; }

    .pill-up {
        display: inline-block;
        background: rgba(22, 163, 74, 0.14);
        color: #16a34a;
        padding: 2px 7px;
        border-radius: 6px;
        font-size: 0.73rem;
        font-weight: 700;
        margin-top: 3px;
        white-space: nowrap;
    }
    .pill-down {
        display: inline-block;
        background: rgba(220, 38, 38, 0.14);
        color: #dc2626;
        padding: 2px 7px;
        border-radius: 6px;
        font-size: 0.73rem;
        font-weight: 700;
        margin-top: 3px;
        white-space: nowrap;
    }
    .pill-tag {
        display: inline-block;
        background: rgba(59, 130, 246, 0.12);
        border: 1px solid rgba(59, 130, 246, 0.25);
        padding: 3px 8px;
        border-radius: 8px;
        font-size: 0.73rem;
        font-weight: 600;
        margin-top: 7px;
        margin-right: 4px;
    }
    .ind-strip { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 8px; font-size: 0.72rem; }
    .ind-chip {
        background: rgba(128, 128, 128, 0.10);
        padding: 2px 7px;
        border-radius: 6px;
        font-weight: 600;
        white-space: nowrap;
    }
    .fin-footer {
        display: flex;
        justify-content: space-between;
        flex-wrap: wrap;
        gap: 6px;
        font-size: 0.76rem;
        opacity: 0.90;
        margin-top: 8px;
        padding-top: 7px;
        border-top: 1px dashed rgba(128, 128, 128, 0.22);
    }

    .kpi-box {
        background: rgba(128, 128, 128, 0.055);
        border: 1px solid rgba(128, 128, 128, 0.20);
        border-radius: 12px;
        padding: 10px 12px;
    }
    .kpi-label { font-size: 0.73rem; opacity: 0.72; font-weight: 600; }
    .kpi-val { font-size: 1.06rem; font-weight: 800; margin-top: 2px; }
    .kpi-sub-up { font-size: 0.74rem; color: #16a34a; font-weight: 700; margin-top: 2px; }
    .kpi-sub-down { font-size: 0.74rem; color: #dc2626; font-weight: 700; margin-top: 2px; }
    .kpi-sub-muted { font-size: 0.73rem; opacity: 0.7; margin-top: 2px; }

    .range-hi { color: #16a34a; font-weight: 700; font-size: 0.84rem; margin-top: 4px; }
    .range-lo { color: #dc2626; font-weight: 700; font-size: 0.84rem; margin-top: 2px; }

    button[data-baseweb="tab"] {
        padding-left: 8px !important;
        padding-right: 8px !important;
        font-weight: 600 !important;
        font-size: 0.84rem !important;
    }

    @media (max-width: 640px) {
        .block-container { padding-top: 3.8rem !important; }
        .app-title { font-size: 1.15rem; }
        .card-grid { grid-template-columns: 1fr; gap: 8px; }
        button[data-baseweb="tab"] { font-size: 0.78rem !important; padding: 6px 6px !important; }
    }
    </style>
    """
)

IST = timezone(timedelta(hours=5, minutes=30))
LOCAL_DB_FILE = "local_users_db.json"

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
# PRIVACY-FIRST MULTI-USER AUTH + PER-USER PERSONAL GOOGLE SHEETS STORAGE
# Master Sheet = ONLY Login directory (username, full_name, hashed_pw, personal_sheet_url)
# Each User's OWN Personal Google Sheet = wallet, holdings, history (100% private!)
# ------------------------------------------------------------------------------
AUTH_USERS_HEADERS = ["username", "full_name", "password_hash", "personal_sheet_url", "created_at"]
PERSONAL_WALLET_HEADERS = ["cash", "total_deposited", "updated_at"]
PERSONAL_HOLDINGS_HEADERS = ["id", "asset_type", "ticker", "name", "buy_price", "qty", "invested", "buy_date", "target_price", "stop_loss"]
PERSONAL_HISTORY_HEADERS = ["Asset", "Qty", "Buy (₹)", "Sell (₹)", "P&L (₹)", "Return (%)", "Sold On"]


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 100000)
    return f"{salt}:{dk.hex()}"


def verify_password(password: str, stored_hash: str) -> bool:
    try:
        salt, expected_hex = stored_hash.split(":", 1)
        dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 100000)
        return secrets.compare_digest(dk.hex(), expected_hex)
    except Exception:
        return False


def _gsheets_configured() -> bool:
    if not GSHEETS_LIBS_OK:
        return False
    try:
        return ("gcp_service_account" in st.secrets) and ("sheet_url" in st.secrets)
    except Exception:
        return False


def get_bot_email() -> str:
    try:
        return str(st.secrets["gcp_service_account"].get("client_email", ""))
    except Exception:
        return ""


@st.cache_resource(show_spinner=False)
def _get_gspread_client():
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]
    creds = Credentials.from_service_account_info(dict(st.secrets["gcp_service_account"]), scopes=scopes)
    return gspread.authorize(creds)


def _get_or_create_ws(sh, title: str, headers: list):
    try:
        ws = sh.worksheet(title)
        if not ws.row_values(1):
            ws.append_row(headers)
        return ws
    except gspread.WorksheetNotFound:
        ws = sh.add_worksheet(title=title, rows=1000, cols=len(headers))
        ws.append_row(headers)
        return ws


def _get_master_auth_ws():
    """Master sheet holds ONLY account login directory — zero user trading data."""
    gc = _get_gspread_client()
    sh = gc.open_by_url(st.secrets["sheet_url"])
    ws = _get_or_create_ws(sh, "users", AUTH_USERS_HEADERS)
    # Upgrade older master sheet header smoothly if needed
    hdr = ws.row_values(1)
    if "personal_sheet_url" not in hdr:
        ws.update_cell(1, len(hdr) + 1, "personal_sheet_url")
    return ws


def _open_personal_sheet(personal_url: str):
    """Connects directly to the logged-in user's OWN Google Sheet and initializes 3 private tabs."""
    url = personal_url.strip()
    if not url.startswith("https://docs.google.com/spreadsheets/"):
        raise ValueError("Please paste a valid Google Sheet link starting with https://docs.google.com/spreadsheets/")

    gc = _get_gspread_client()
    try:
        sh = gc.open_by_url(url)
    except Exception:
        bot = get_bot_email()
        raise PermissionError(
            f"Cannot open your Google Sheet! Open your sheet → click Share → add **{bot}** as **Editor** → try again."
        )

    ws_wallet = _get_or_create_ws(sh, "wallet", PERSONAL_WALLET_HEADERS)
    if len(ws_wallet.get_all_values()) < 2:
        ws_wallet.append_row([100000.0, 100000.0, now_ist().strftime("%Y-%m-%d %H:%M IST")])

    ws_holdings = _get_or_create_ws(sh, "holdings", PERSONAL_HOLDINGS_HEADERS)
    ws_history = _get_or_create_ws(sh, "history", PERSONAL_HISTORY_HEADERS)
    return ws_wallet, ws_holdings, ws_history


def _load_local_db() -> dict:
    if os.path.exists(LOCAL_DB_FILE):
        try:
            with open(LOCAL_DB_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {"users": {}}


def _save_local_db(db: dict):
    with open(LOCAL_DB_FILE, "w") as f:
        json.dump(db, f, indent=2)


def db_register_user(username: str, full_name: str, password: str, personal_sheet_url: str = "") -> tuple[bool, str]:
    uname = username.strip().lower()
    if not re.match(r"^[a-z0-9_]{3,20}$", uname):
        return False, "Username must be 3–20 characters (letters, numbers, or underscore only)."
    if len(password) < 4:
        return False, "Password must be at least 4 characters."

    p_url = personal_sheet_url.strip()
    pw_hash = hash_password(password)
    created = now_ist().strftime("%Y-%m-%d %H:%M IST")

    if _gsheets_configured():
        # Verify user's personal Google Sheet first if they provided one
        if p_url:
            try:
                _open_personal_sheet(p_url)
            except Exception as e:
                return False, str(e)

        try:
            ws_users = _get_master_auth_ws()
            existing = ws_users.col_values(1)
            if uname in [str(u).strip().lower() for u in existing[1:]]:
                return False, "Username already exists. Please choose another or log in."

            hdr = ws_users.row_values(1)
            row_map = {
                "username": uname,
                "full_name": full_name.strip() or uname,
                "password_hash": pw_hash,
                "personal_sheet_url": p_url,
                "created_at": created,
            }
            new_row = [row_map.get(col, "") for col in hdr]
            ws_users.append_row(new_row)
            return True, "Account created! Your private Google Sheet is connected." if p_url else "Account created! Link your personal Google Sheet in the Dummy tab to save permanently."
        except Exception as e:
            return False, f"Auth database error: {e}"
    else:
        db = _load_local_db()
        if uname in db["users"]:
            return False, "Username already exists."
        db["users"][uname] = {
            "full_name": full_name.strip() or uname,
            "password_hash": pw_hash,
            "personal_sheet_url": p_url,
            "cash": 100000.0,
            "total_deposited": 100000.0,
            "created_at": created,
            "holdings": [],
            "history": [],
        }
        _save_local_db(db)
        return True, "Account created locally!"


def db_authenticate_user(username: str, password: str) -> tuple[bool, str, dict | None]:
    uname = username.strip().lower()
    if _gsheets_configured():
        try:
            ws_users = _get_master_auth_ws()
            for r in ws_users.get_all_records():
                if str(r.get("username", "")).strip().lower() == uname:
                    if verify_password(password, str(r.get("password_hash", ""))):
                        return True, "Welcome back!", {
                            "username": uname,
                            "full_name": str(r.get("full_name", uname)),
                            "personal_sheet_url": str(r.get("personal_sheet_url", "")).strip(),
                        }
                    return False, "Incorrect password.", None
            return False, "Username not found. Please Create Account first.", None
        except Exception as e:
            return False, f"Login error: {e}", None
    else:
        db = _load_local_db()
        u = db["users"].get(uname)
        if not u:
            return False, "Username not found. Please Create Account first.", None
        if verify_password(password, u["password_hash"]):
            return True, "Welcome back!", {
                "username": uname,
                "full_name": u.get("full_name", uname),
                "personal_sheet_url": u.get("personal_sheet_url", ""),
            }
        return False, "Incorrect password.", None


def db_update_personal_sheet_url(username: str, new_url: str, current_portfolio: dict) -> tuple[bool, str]:
    """Tests user's personal Google Sheet, saves link to their profile, and loads/syncs data."""
    uname = username.strip().lower()
    p_url = new_url.strip()
    if not _gsheets_configured():
        return False, "Google Sheets Cloud Secrets are not configured on this server yet."

    try:
        ws_wallet, ws_holdings, ws_history = _open_personal_sheet(p_url)
    except Exception as e:
        return False, str(e)

    try:
        ws_users = _get_master_auth_ws()
        hdr = ws_users.row_values(1)
        url_col = hdr.index("personal_sheet_url") + 1
        col_a = ws_users.col_values(1)
        for idx, val in enumerate(col_a[1:], start=2):
            if str(val).strip().lower() == uname:
                ws_users.update_cell(idx, url_col, p_url)
                break

        # If personal sheet is brand new (no trades yet) and user had temporary session trades, migrate them!
        if len(ws_holdings.get_all_values()) <= 1 and current_portfolio.get("holdings"):
            ws_wallet.update_cell(2, 1, round(current_portfolio["cash"], 2))
            ws_wallet.update_cell(2, 2, round(current_portfolio["total_deposited"], 2))
            ws_wallet.update_cell(2, 3, now_ist().strftime("%Y-%m-%d %H:%M IST"))
            for h in current_portfolio["holdings"]:
                ws_holdings.append_row([str(h["id"]), h["asset_type"], h["ticker"], h["name"], h["buy_price"], h["qty"], h["invested"], h["buy_date"], h["target_price"], h["stop_loss"]])

        return True, "Connected! All your trades are now saved privately in YOUR own Google Sheet."
    except Exception as e:
        return False, f"Failed to link sheet: {e}"


def db_fetch_user_portfolio(user_obj: dict) -> dict:
    uname = user_obj["username"]
    p_url = user_obj.get("personal_sheet_url", "").strip()

    if _gsheets_configured():
        if not p_url:
            # No personal sheet connected yet: strictly session-only (NEVER writes to master sheet!)
            return {"cash": 100000.0, "total_deposited": 100000.0, "holdings": [], "history": []}
        try:
            ws_wallet, ws_holdings, ws_history = _open_personal_sheet(p_url)
            w_recs = ws_wallet.get_all_records()
            cash = float(w_recs[0].get("cash", 100000.0)) if w_recs else 100000.0
            total_dep = float(w_recs[0].get("total_deposited", 100000.0)) if w_recs else 100000.0

            holdings = []
            for r in ws_holdings.get_all_records():
                holdings.append(
                    {
                        "id": str(r.get("id")),
                        "asset_type": str(r.get("asset_type", "STOCK")),
                        "ticker": str(r.get("ticker", "")),
                        "name": str(r.get("name", "")),
                        "buy_price": float(r.get("buy_price", 0)),
                        "qty": float(r.get("qty", 0)) if str(r.get("asset_type")) == "MF" else int(float(r.get("qty", 0))),
                        "invested": float(r.get("invested", 0)),
                        "buy_date": str(r.get("buy_date", "")),
                        "target_price": float(r.get("target_price", 0)),
                        "stop_loss": float(r.get("stop_loss", 0)),
                    }
                )

            history = []
            for r in ws_history.get_all_records():
                history.append(
                    {
                        "Asset": str(r.get("Asset", "")),
                        "Qty": r.get("Qty", 0),
                        "Buy (₹)": float(r.get("Buy (₹)", 0)),
                        "Sell (₹)": float(r.get("Sell (₹)", 0)),
                        "P&L (₹)": float(r.get("P&L (₹)", 0)),
                        "Return (%)": float(r.get("Return (%)", 0)),
                        "Sold On": str(r.get("Sold On", "")),
                    }
                )
            return {"cash": cash, "total_deposited": total_dep, "holdings": holdings, "history": history}
        except Exception as e:
            st.warning(f"Could not read your personal Google Sheet: {e}")
            return {"cash": 100000.0, "total_deposited": 100000.0, "holdings": [], "history": []}
    else:
        db = _load_local_db()
        u = db["users"].get(uname, {})
        return {
            "cash": float(u.get("cash", 100000.0)),
            "total_deposited": float(u.get("total_deposited", 100000.0)),
            "holdings": list(u.get("holdings", [])),
            "history": list(u.get("history", [])),
        }


def db_record_buy(user_obj: dict, holding: dict, new_cash: float, total_deposited: float):
    uname = user_obj["username"]
    p_url = user_obj.get("personal_sheet_url", "").strip()
    if _gsheets_configured():
        if p_url:
            ws_wallet, ws_holdings, _ = _open_personal_sheet(p_url)
            ws_wallet.update_cell(2, 1, round(new_cash, 2))
            ws_wallet.update_cell(2, 2, round(total_deposited, 2))
            ws_wallet.update_cell(2, 3, now_ist().strftime("%Y-%m-%d %H:%M IST"))
            ws_holdings.append_row([str(holding["id"]), holding["asset_type"], holding["ticker"], holding["name"], holding["buy_price"], holding["qty"], holding["invested"], holding["buy_date"], holding["target_price"], holding["stop_loss"]])
    else:
        db = _load_local_db()
        if uname in db["users"]:
            db["users"][uname]["cash"] = round(new_cash, 2)
            db["users"][uname]["total_deposited"] = round(total_deposited, 2)
            db["users"][uname]["holdings"].append(holding)
            _save_local_db(db)


def db_record_sell(user_obj: dict, holding_id: str, history_row: dict, new_cash: float, total_deposited: float):
    uname = user_obj["username"]
    p_url = user_obj.get("personal_sheet_url", "").strip()
    if _gsheets_configured():
        if p_url:
            ws_wallet, ws_holdings, ws_history = _open_personal_sheet(p_url)
            ws_wallet.update_cell(2, 1, round(new_cash, 2))
            ws_wallet.update_cell(2, 2, round(total_deposited, 2))
            ws_wallet.update_cell(2, 3, now_ist().strftime("%Y-%m-%d %H:%M IST"))
            rows = ws_holdings.get_all_values()
            for idx in range(len(rows) - 1, 0, -1):
                if str(rows[idx][0]) == str(holding_id):
                    ws_holdings.delete_rows(idx + 1)
                    break
            ws_history.append_row([history_row["Asset"], history_row["Qty"], history_row["Buy (₹)"], history_row["Sell (₹)"], history_row["P&L (₹)"], history_row["Return (%)"], history_row["Sold On"]])
    else:
        db = _load_local_db()
        if uname in db["users"]:
            db["users"][uname]["cash"] = round(new_cash, 2)
            db["users"][uname]["holdings"] = [h for h in db["users"][uname]["holdings"] if str(h["id"]) != str(holding_id)]
            db["users"][uname]["history"].append(history_row)
            _save_local_db(db)


def db_add_cash(user_obj: dict, new_cash: float, new_deposited: float):
    uname = user_obj["username"]
    p_url = user_obj.get("personal_sheet_url", "").strip()
    if _gsheets_configured():
        if p_url:
            ws_wallet, _, _ = _open_personal_sheet(p_url)
            ws_wallet.update_cell(2, 1, round(new_cash, 2))
            ws_wallet.update_cell(2, 2, round(new_deposited, 2))
            ws_wallet.update_cell(2, 3, now_ist().strftime("%Y-%m-%d %H:%M IST"))
    else:
        db = _load_local_db()
        if uname in db["users"]:
            db["users"][uname]["cash"] = round(new_cash, 2)
            db["users"][uname]["total_deposited"] = round(new_deposited, 2)
            _save_local_db(db)


def db_reset_user_wallet(user_obj: dict):
    uname = user_obj["username"]
    p_url = user_obj.get("personal_sheet_url", "").strip()
    if _gsheets_configured():
        if p_url:
            ws_wallet, ws_holdings, ws_history = _open_personal_sheet(p_url)
            ws_wallet.update_cell(2, 1, 100000.0)
            ws_wallet.update_cell(2, 2, 100000.0)
            ws_wallet.update_cell(2, 3, now_ist().strftime("%Y-%m-%d %H:%M IST"))
            ws_holdings.clear()
            ws_holdings.append_row(PERSONAL_HOLDINGS_HEADERS)
            ws_history.clear()
            ws_history.append_row(PERSONAL_HISTORY_HEADERS)
    else:
        db = _load_local_db()
        if uname in db["users"]:
            db["users"][uname]["cash"] = 100000.0
            db["users"][uname]["total_deposited"] = 100000.0
            db["users"][uname]["holdings"] = []
            db["users"][uname]["history"] = []
            _save_local_db(db)


def get_session_portfolio() -> dict:
    if "user_portfolio" not in st.session_state:
        st.session_state["user_portfolio"] = db_fetch_user_portfolio(st.session_state["auth_user"])
    return st.session_state["user_portfolio"]


# ------------------------------------------------------------------------------
# LOGIN / PRIVATE PERSONAL GOOGLE SHEET SIGN-UP GATE
# ------------------------------------------------------------------------------
if "auth_user" not in st.session_state:
    gs_ready = _gsheets_configured()
    storage_msg = (
        "🔒 Privacy-First Cloud Mode (Each User Uses Their Own Google Sheet)"
        if gs_ready
        else "💾 Local Mode (Add Google Secrets on Streamlit Cloud for Personal Sheets)"
    )
    render_html(
        f"""
        <div class="auth-box">
            <div style="font-size:1.5rem; font-weight:800;">📈 India Stock, SIP &amp; Gold</div>
            <div style="font-size:0.83rem; opacity:0.75; margin-top:4px;">
                Live NSE/BSE Guide · Private Per-User Dummy Trading
            </div>
            <div style="margin-top:10px;"><span class="status-pill status-user">{storage_msg}</span></div>
        </div>
        """
    )

    _, mid_col, _ = st.columns([1, 1.8, 1])
    with mid_col:
        auth_t1, auth_t2 = st.tabs(["🔐 Login", "✨ Create Account"])

        with auth_t1:
            with st.form("login_form"):
                l_user = st.text_input("Username", placeholder="e.g. saurabh")
                l_pass = st.text_input("Password", type="password", placeholder="Enter your password")
                if st.form_submit_button("Login", type="primary", use_container_width=True):
                    ok, msg, user_obj = db_authenticate_user(l_user, l_pass)
                    if ok and user_obj:
                        st.session_state["auth_user"] = user_obj
                        st.session_state["user_portfolio"] = db_fetch_user_portfolio(user_obj)
                        st.rerun()
                    else:
                        st.error(msg)

        with auth_t2:
            if gs_ready:
                bot_email = get_bot_email()
                st.info(
                    "**Keep your dummy trades 100% private in YOUR own Google Sheet:**\n"
                    "1. Open [sheets.new](https://sheets.new) to create your own blank Google Sheet.\n"
                    "2. Click **Share** → add the bot email below as **Editor** → **Send**.\n"
                    "3. Paste your Google Sheet link below!"
                )
                st.code(bot_email, language=None)

            with st.form("signup_form"):
                s_name = st.text_input("Full Name", placeholder="e.g. Saurabh Chaki")
                s_user = st.text_input("Choose Username (letters/numbers)", placeholder="e.g. saurabh")
                s_pass1 = st.text_input("Create Password", type="password")
                s_pass2 = st.text_input("Confirm Password", type="password")
                s_sheet = st.text_input(
                    "Your Personal Google Sheet URL (Recommended — Keeps Your Trades 100% Private)",
                    placeholder="https://docs.google.com/spreadsheets/d/...",
                ) if gs_ready else ""

                if st.form_submit_button("Create Account (₹1,00,000 Dummy Cash)", type="primary", use_container_width=True):
                    if s_pass1 != s_pass2:
                        st.error("Passwords do not match.")
                    else:
                        ok, msg = db_register_user(s_user, s_name, s_pass1, s_sheet)
                        if ok:
                            uname = s_user.strip().lower()
                            user_obj = {
                                "username": uname,
                                "full_name": s_name.strip() or uname,
                                "personal_sheet_url": s_sheet.strip(),
                            }
                            st.session_state["auth_user"] = user_obj
                            st.session_state["user_portfolio"] = db_fetch_user_portfolio(user_obj)
                            st.success(msg)
                            st.rerun()
                        else:
                            st.error(msg)

    st.stop()


# ------------------------------------------------------------------------------
# HTML CARD RENDERERS
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
    render_html("".join(cards_html))


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
    render_html("".join(cards_html))


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
    render_html("".join(cards_html))


# ------------------------------------------------------------------------------
# NEWS, DIRECTORY & MARKET DATA ENGINES
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


@st.cache_data(ttl=15, show_spinner=False)
def scan_instant_win_setups(exchange: str) -> pd.DataFrame:
    suffix = ".NS" if exchange == "NSE" else ".BO"
    tickers = [f"{sym}{suffix}" for sym in POPULAR_STOCKS.keys()]
    try:
        raw = yf.download(tickers, period="5d", interval="15m", group_by="ticker", progress=False, auto_adjust=True)
    except Exception:
        return pd.DataFrame()
    if raw is None or raw.empty:
        return pd.DataFrame()

    rows = []
    eps = 1e-9

    for sym, name in POPULAR_STOCKS.items():
        full_ticker = f"{sym}{suffix}"
        try:
            sub = raw[full_ticker].dropna().copy() if len(tickers) > 1 else raw.dropna().copy()
            if len(sub) < 25:
                continue
            if sub.index.tz is not None:
                sub.index = sub.index.tz_convert("Asia/Kolkata")

            close = sub["Close"]
            price = float(close.iloc[-1])

            latest_date = sub.index[-1].date()
            today_mask = sub.index.date == latest_date
            prev_bars = sub[~today_mask]
            today_bars = sub[today_mask]

            prev_close = float(prev_bars["Close"].iloc[-1]) if not prev_bars.empty else float(today_bars["Open"].iloc[0])
            day_pct = ((price - prev_close) / (prev_close + eps)) * 100.0

            tp = (today_bars["High"] + today_bars["Low"] + today_bars["Close"]) / 3.0
            t_vol_sum = float(today_bars["Volume"].sum())
            vwap = float((tp * today_bars["Volume"]).sum() / t_vol_sum) if t_vol_sum > 0 else price
            above_vwap = price >= vwap
            vwap_pct = ((price - vwap) / (vwap + eps)) * 100.0

            ema9 = float(close.ewm(span=9, adjust=False).mean().iloc[-1])
            ema21 = float(close.ewm(span=21, adjust=False).mean().iloc[-1])
            ema_bull = ema9 > ema21
            ema_spread_pct = ((ema9 - ema21) / (price + eps)) * 100.0

            delta = close.diff()
            gain = float(delta.clip(lower=0).rolling(14).mean().iloc[-1])
            loss = float((-delta.clip(upper=0)).rolling(14).mean().iloc[-1])
            rsi = float(100.0 - (100.0 / (1.0 + gain / (loss + eps))))

            vol_spike = 1.0
            if not prev_bars.empty and t_vol_sum > 0:
                prev_day_vols = prev_bars.groupby(prev_bars.index.date)["Volume"].sum()
                avg_full_day_vol = float(prev_day_vols.mean())
                if avg_full_day_vol > 0:
                    session_progress = min(1.0, max(len(today_bars) / 25.0, 0.08))
                    vol_spike = round(t_vol_sum / (avg_full_day_vol * session_progress + eps), 2)

            day_ranges = []
            for _, grp in sub.groupby(sub.index.date):
                if len(grp) >= 5:
                    day_ranges.append((float(grp["High"].max()) - float(grp["Low"].min())) / (float(grp["Close"].iloc[-1]) + eps))
            avg_day_range = float(sum(day_ranges) / len(day_ranges)) if day_ranges else 0.018

            up_pct = round(max(0.90, min(avg_day_range * 85.0, 4.50)), 2)
            down_pct = -round(max(0.55, min(avg_day_range * 48.0, 2.50)), 2)
            target_px = round(price * (1.0 + up_pct / 100.0), 2)
            stop_px = round(price * (1.0 + down_pct / 100.0), 2)
            rr = round(up_pct / max(abs(down_pct), 0.1), 1)

            score = 46.0
            score += max(-16.0, min(16.0, vwap_pct * 15.0))
            score += max(-14.0, min(14.0, ema_spread_pct * 18.0))
            if 45.0 <= rsi <= 68.0:
                score += 11.0 - abs(rsi - 58.0) * 0.45
            elif rsi <= 33.0:
                score += 7.0
            elif rsi > 74.0:
                score -= min(12.0, (rsi - 74.0) * 1.1)

            if day_pct > 0:
                score += min(11.0, max(0.0, (vol_spike - 0.85) * 9.5))
            elif day_pct < -0.5:
                score -= min(11.0, max(0.0, (vol_spike - 0.85) * 9.5))

            score += max(-7.0, min(7.0, day_pct * 2.2))
            score_int = int(round(max(15.0, min(94.0, score))))

            if above_vwap and ema_bull and vol_spike >= 1.15 and score_int >= 72 and rsi <= 72:
                flag, bucket = "⚡ QUICK BREAKOUT BUY", "BULLISH"
            elif score_int >= 66 and above_vwap:
                flag, bucket = "🔥 HIGH-MOMENTUM BUY", "BULLISH"
            elif rsi <= 33:
                flag, bucket = "🔄 OVERSOLD QUICK BOUNCE", "BOUNCE"
            elif score_int < 45:
                flag, bucket = "🔴 AVOID / BEARISH PRESSURE", "AVOID"
            else:
                flag, bucket = "⏳ WAIT / SIDEWAYS", "NEUTRAL"

            rows.append(
                {
                    "Symbol": full_ticker,
                    "Company": name,
                    "Price (₹)": round(price, 2),
                    "Today (%)": round(day_pct, 2),
                    "Setup Score": score_int,
                    "Flag": flag,
                    "Bucket": bucket,
                    "VWAP": f"✅ Above ({vwap_pct:+.1f}%)" if above_vwap else f"🔻 Below ({vwap_pct:+.1f}%)",
                    "EMA": "🟢 9>21 Up" if ema_bull else "🔴 9<21 Down",
                    "RSI": round(rsi, 1),
                    "Vol": f"{vol_spike}x",
                    "Target (₹)": target_px,
                    "Up (%)": up_pct,
                    "Stop (₹)": stop_px,
                    "Down (%)": down_pct,
                    "R:R": f"1:{rr}",
                }
            )
        except Exception:
            continue

    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows).sort_values(["Setup Score", "Today (%)"], ascending=False)


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
    target_pct = max(0.04, min(avg_daily_move * 4.5, 0.12))
    stop_pct = max(0.025, min(avg_daily_move * 2.5, 0.06))

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
        move_badge, is_on_move = "⚠️ HEAVY SELLING PRESSURE", False
    elif heavy_buying and news_rising:
        move_badge, is_on_move = "🔥 HEAVY BUYING + NEWS", True
    elif heavy_buying:
        move_badge, is_on_move = "🔥 HEAVY BUYING SURGE", True
    elif news_rising:
        move_badge, is_on_move = "📰 POSITIVE NEWS & RISING", True
    elif price > ma20 and weekly_pct >= 2.0 and rsi < 70:
        move_badge, is_on_move = "🚀 STARTING TO RISE", True
    elif monthly_pct >= 4.0 and score >= 65:
        move_badge, is_on_move = "🏆 STEADY PROFIT MAKER", False
    elif rsi < 35:
        move_badge, is_on_move = "💡 OVERSOLD DIP", False
    else:
        move_badge, is_on_move = "➡️ NORMAL ACTIVITY", False

    if score >= 70:
        trend, action, reason = "Going Up 📈", "BUY", "Strong upward trend above 20 & 50-day averages with active buyer interest."
    elif score >= 50:
        trend, action, reason = "Steady ➡️", "HOLD / WATCH", "Steady movement. Good to hold or wait for a clearer breakout."
    else:
        trend, action, reason = "Going Down 📉", "AVOID / SELL", "Trading below recent averages with weak momentum (wait for selling to stabilize)."

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
    """Upgrade Hook: Replace this function with Angel One SmartAPI / Upstox / Dhan LTP API for 0-sec ticks."""
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


def scan_market_live(exchange: str, news_headlines: list, market_open: bool) -> pd.DataFrame:
    suffix = ".NS" if exchange == "NSE" else ".BO"
    tickers = tuple(f"{sym}{suffix}" for sym in POPULAR_STOCKS.keys())
    hist_raw = _fetch_market_history(exchange)
    live_map = _fetch_live_1m_prices(tickers) if market_open else {}
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


def fetch_single_stock_live(full_ticker: str, market_open: bool):
    df = _fetch_single_history(full_ticker)
    if df.empty:
        return pd.DataFrame(), None
    live_map = _fetch_live_1m_prices((full_ticker,)) if market_open else {}
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

            r1y, r3y, r1m = cagr(1), cagr(3), info["monthly_pct"]
            start_dt = latest_dt - pd.DateOffset(years=3)
            sip_slice = df[df.index >= start_dt]
            monthly_pts = sip_slice.groupby(sip_slice.index.to_period("M")).head(1)
            invested = len(monthly_pts) * 5000.0
            units = sum(5000.0 / float(n) for n in monthly_pts["nav"])
            val_today = units * latest_nav
            profit_rs = round(val_today - invested, 0)
            profit_pct = round((profit_rs / max(invested, 1)) * 100, 1)

            if r1m >= 2.5 and r1y >= 10:
                status, is_hot = "🔥 ON THE MOVE", True
            elif r3y >= 15 and r1m < 0:
                status, is_hot = "💡 GREAT TIME TO START SIP", True
            elif r3y >= 14:
                status, is_hot = "🏆 TOP PROFIT SIP", False
            else:
                status, is_hot = "➡️ STEADY COMPOUNDER", False

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
    return pd.DataFrame(valid).sort_values("ProfitVal", ascending=False) if valid else pd.DataFrame()


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
# LOGGED-IN APP HEADER + CONTROLS
# ------------------------------------------------------------------------------
ACTIVE_USER = st.session_state["auth_user"]
MARKET_OPEN = is_market_open()

mkt_badge = (
    '<span class="status-pill status-open">● Market OPEN</span>'
    if MARKET_OPEN
    else '<span class="status-pill status-closed">🔒 Market Closed</span>'
)
user_badge = f'<span class="status-pill status-user">👤 {html.escape(ACTIVE_USER["full_name"])}</span>'

render_html(
    f"""
    <div class="app-header">
        <div class="app-title">📈 India Stock, SIP &amp; Gold</div>
        <div class="header-badges">{user_badge}{mkt_badge}</div>
    </div>
    """
)

if not MARKET_OPEN:
    render_html(
        """
        <div class="frozen-banner">
            🔒 Indian Market is CLOSED (Trading Hours: Mon–Fri, 9:15 AM – 3:30 PM IST).
            Prices are frozen at last close and all Buy/Sell trading options are disabled until market reopens.
        </div>
        """
    )

ctrl1, ctrl2, ctrl3, ctrl4 = st.columns([1.1, 1.2, 0.9, 0.8])
exchange = ctrl1.radio("Exchange", ["NSE", "BSE"], horizontal=True, label_visibility="collapsed")
live_mode = ctrl2.toggle("🔴 Live (15s)", value=MARKET_OPEN, disabled=not MARKET_OPEN)
if MARKET_OPEN:
    if ctrl3.button("🔄 Refresh", use_container_width=True):
        _fetch_live_1m_prices.clear()
        scan_instant_win_setups.clear()
        fetch_live_news.clear()
        st.rerun()
else:
    ctrl3.button("❄️ Frozen", disabled=True, use_container_width=True)

if ctrl4.button("🚪 Logout", use_container_width=True):
    st.session_state.pop("auth_user", None)
    st.session_state.pop("user_portfolio", None)
    st.rerun()

AUTO_INTERVAL = 15 if (MARKET_OPEN and live_mode) else None

tab_quick, tab1, tab2, tab3, tab4 = st.tabs(["⚡ Quick", "🏆 Top 10", "🔍 Search", "🪙 SIP", "🎮 Dummy"])

# ==============================================================================
# TAB 0: QUICK WIN SETUPS
# ==============================================================================
with tab_quick:
    @st.fragment(run_every=AUTO_INTERVAL)
    def render_instant_wins():
        render_html(f'<div class="sec-title">⚡ {exchange} Quick Win Setups (15-Min Indicators)</div>')
        render_html('<div class="sec-sub">Graded setups using VWAP, EMA 9/21, RSI, Pro-Rated Volume &amp; real daily volatility.</div>')
        st.caption(f"⏱️ Live Scan {now_ist().strftime('%I:%M:%S %p IST')}" if MARKET_OPEN else "❄️ Frozen at Last Market Close (3:30 PM IST)")

        qdf = scan_instant_win_setups(exchange)
        if qdf.empty:
            st.warning("Intraday data temporarily unavailable.")
            return

        if MARKET_OPEN:
            f_col1, f_col2 = st.columns([1.6, 1])
            q_filter = f_col1.radio("Filter", ["🔥 Top Quick Buys", "🔄 Oversold Bounces", "🔴 Weak / Avoid", "All 30"], horizontal=True, label_visibility="collapsed", key="quick_filter")
            quick_buy_amt = f_col2.selectbox("1-Tap Dummy Size (₹)", [5000, 10000, 25000, 50000, 100000], index=1, key="quick_buy_amt")
        else:
            q_filter = st.radio("Filter", ["🔥 Top Quick Buys", "🔄 Oversold Bounces", "🔴 Weak / Avoid", "All 30"], horizontal=True, label_visibility="collapsed", key="quick_filter")
            quick_buy_amt = 10000

        if q_filter == "🔥 Top Quick Buys":
            show_df = qdf[qdf["Bucket"] == "BULLISH"].head(8)
            if show_df.empty:
                show_df = qdf.head(6)
        elif q_filter == "🔄 Oversold Bounces":
            show_df = qdf[qdf["Bucket"] == "BOUNCE"].head(8)
            if show_df.empty:
                st.info("No extreme oversold stocks right now (RSI ≤ 33). Showing lowest RSI stocks:")
                show_df = qdf.sort_values("RSI", ascending=True).head(6)
        elif q_filter == "🔴 Weak / Avoid":
            show_df = qdf.sort_values("Setup Score", ascending=True).head(8)
        else:
            show_df = qdf

        portfolio = get_session_portfolio()
        if MARKET_OPEN:
            st.caption(f"Available Dummy Cash: **₹{portfolio['cash']:,.2f}**")

        cols = st.columns(2)
        for idx, (_, r) in enumerate(show_df.iterrows()):
            with cols[idx % 2]:
                comp = html.escape(str(r["Company"]))
                sym = html.escape(str(r["Symbol"]))
                flag = html.escape(str(r["Flag"]))
                vwap_s = html.escape(str(r["VWAP"]))
                ema_s = html.escape(str(r["EMA"]))
                render_html(
                    f"""
                    <div class="fin-card" style="margin-bottom:8px;">
                        <div class="fin-row">
                            <div>
                                <div class="fin-name">#{idx + 1} {comp}</div>
                                <div class="fin-meta">{sym} · Setup Score: <b>{r['Setup Score']}%</b> · R:R <b>{r['R:R']}</b></div>
                            </div>
                            <div style="text-align:right;">
                                <div class="fin-price">₹{r['Price (₹)']:,.2f}</div>
                                {pct_pill(r['Today (%)'], ' today')}
                            </div>
                        </div>
                        <div><span class="pill-tag">{flag}</span></div>
                        <div class="ind-strip">
                            <span class="ind-chip">VWAP: {vwap_s}</span>
                            <span class="ind-chip">EMA: {ema_s}</span>
                            <span class="ind-chip">RSI: {r['RSI']}</span>
                            <span class="ind-chip">Vol: {r['Vol']}</span>
                        </div>
                        <div class="fin-footer">
                            <span style="color:#16a34a;">🎯 Target: <b>₹{r['Target (₹)']:,.2f} (+{r['Up (%)']}%)</b></span>
                            <span style="color:#dc2626;">🛡️ Stop: <b>₹{r['Stop (₹)']:,.2f} ({r['Down (%)']}%)</b></span>
                        </div>
                    </div>
                    """
                )

                if MARKET_OPEN:
                    if st.button(f"⚡ Quick Dummy Buy ₹{quick_buy_amt:,} — {sym.replace('.NS', '').replace('.BO', '')}", key=f"qbuy_{sym}_{idx}", use_container_width=True):
                        qty = int(quick_buy_amt // r["Price (₹)"])
                        cost = round(qty * r["Price (₹)"], 2)
                        if qty <= 0:
                            st.warning("Increase 1-Tap Dummy Size to buy at least 1 share.")
                        elif cost > portfolio["cash"]:
                            st.error("Not enough dummy cash! Add more in **🎮 Dummy** tab.")
                        else:
                            new_cash = round(portfolio["cash"] - cost, 2)
                            holding = {
                                "id": str(int(now_ist().timestamp() * 1000) + idx),
                                "asset_type": "STOCK",
                                "ticker": sym,
                                "name": f"⚡ {r['Company']} (Quick)",
                                "buy_price": r["Price (₹)"],
                                "qty": qty,
                                "invested": cost,
                                "buy_date": now_ist().strftime("%d %b, %I:%M %p"),
                                "target_price": r["Target (₹)"],
                                "stop_loss": r["Stop (₹)"],
                            }
                            db_record_buy(ACTIVE_USER, holding, new_cash, portfolio["total_deposited"])
                            portfolio["cash"] = new_cash
                            portfolio["holdings"].append(holding)
                            st.success(f"Saved privately! Bought {qty} dummy shares of **{r['Company']}**.")

        with st.expander("📊 View All 30 Stocks Quick-Win Indicator Table"):
            st.dataframe(
                qdf[["Company", "Symbol", "Flag", "Setup Score", "Price (₹)", "Today (%)", "VWAP", "EMA", "RSI", "Vol", "Target (₹)", "Up (%)", "Stop (₹)", "Down (%)", "R:R"]],
                use_container_width=True,
                hide_index=True,
            )

    render_instant_wins()

# ==============================================================================
# TAB 1: TOP 10 STOCKS & BOTTOM PERFORMERS
# ==============================================================================
with tab1:
    stock_news = fetch_live_news("NSE BSE Indian stocks rally buy volume surge", max_items=6)

    @st.fragment(run_every=AUTO_INTERVAL)
    def render_live_market_board():
        market_df = scan_market_live(exchange, stock_news, MARKET_OPEN)
        st.caption(f"⏱️ Updated {now_ist().strftime('%I:%M:%S %p IST')} · {exchange} Live" if MARKET_OPEN else f"❄️ Frozen at Last {exchange} Close")

        if market_df.empty:
            st.error("Could not load market data right now.")
            return

        on_move_df = market_df[market_df["IsOnMove"]].sort_values("Score", ascending=False).head(6)
        render_html(f'<div class="sec-title">🔥 {exchange} On The Move</div>')
        render_html('<div class="sec-sub">Active buying surge, positive news, or fresh breakout</div>')
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

        render_html(f'<div class="sec-title">🏆 Top 10 Profitable {exchange} Stocks</div>')
        view_mode = st.radio("Layout", ["📱 Modern Cards", "📊 Full Table"], horizontal=True, label_visibility="collapsed", key="top10_view")

        top10 = market_df.sort_values(["Score", "Monthly (%)"], ascending=False).head(10)
        if view_mode == "📱 Modern Cards":
            render_stock_cards(top10, rank_start=1)
        else:
            top10_tbl = top10.copy()
            top10_tbl.insert(0, "Rank", range(1, len(top10_tbl) + 1))
            st.dataframe(
                top10_tbl[["Rank", "Company", "Symbol", "Highlight", "Price (₹)", "Daily (%)", "Weekly (%)", "Monthly (%)", "Volume Activity", "Target Sell (₹)", "Safety Stop (₹)"]],
                use_container_width=True,
                hide_index=True,
            )

        render_html('<div class="sec-title">📉 Bottom Performers & Gainers</div>')
        period_choice = st.radio("Timeframe", ["Daily", "Weekly", "Monthly"], horizontal=True, label_visibility="collapsed", key="perf_tf")
        sort_col = {"Daily": "Daily (%)", "Weekly": "Weekly (%)", "Monthly": "Monthly (%)"}[period_choice]
        perf_sub = st.radio("Show", ["🔴 Bottom Performers", "🟢 Top Gainers"], horizontal=True, label_visibility="collapsed", key="perf_side")
        if perf_sub == "🔴 Bottom Performers":
            render_perf_cards(market_df.sort_values(sort_col, ascending=True).head(6), sort_col)
        else:
            render_perf_cards(market_df.sort_values(sort_col, ascending=False).head(6), sort_col)

    render_live_market_board()

# ==============================================================================
# TAB 2: LIVE SEARCH + HIGH/LOW FORECAST
# ==============================================================================
with tab2:
    render_html('<div class="sec-title">🔍 Search Any Indian Stock</div>')

    all_stocks = load_all_indian_stocks()
    option_map = {f"{name} ({sym})": sym for sym, name in sorted(all_stocks.items(), key=lambda x: x[1])}
    selected_label = st.selectbox("Search:", options=list(option_map.keys()), index=None, placeholder="Type e.g. Apollo Tubes, Reliance, HAL...", label_visibility="collapsed")

    full_ticker, display_name = None, None
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
                full_ticker, display_name = y_map[picked_y], picked_y
            else:
                st.warning("No matching Indian stocks found.")

    if not full_ticker:
        st.info("👆 Tap the search box above and start typing any company name (like **Apollo Tubes**, **HAL**, or **Tata Power**).")
    else:
        @st.fragment(run_every=AUTO_INTERVAL)
        def render_searched_stock_live(ticker_to_show, label_to_show):
            sdf, sinfo = fetch_single_stock_live(ticker_to_show, MARKET_OPEN)
            if sinfo is None and ticker_to_show.endswith(".BO"):
                alt_ticker = ticker_to_show.replace(".BO", ".NS")
                sdf, sinfo = fetch_single_stock_live(alt_ticker, MARKET_OPEN)
                if sinfo is not None:
                    ticker_to_show = alt_ticker

            if sinfo is None:
                st.error(f"Could not fetch price for **{ticker_to_show}**.")
                return

            st.caption(f"⏱️ Live Quote: {now_ist().strftime('%I:%M:%S %p IST')}" if MARKET_OPEN else "❄️ Frozen at Last Market Close")

            safe_label = html.escape(label_to_show)
            render_html(
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
                """
            )

            render_html('<div class="sec-title">📊 Expected High / Low Forecast</div>')
            render_html(
                f"""
                <div class="grid-2col grid-2col-desktop4">
                    <div class="kpi-box"><div class="kpi-label">Next 1–2 Days</div><div class="range-hi">▲ ₹{sinfo['day_high']:,.2f}</div><div class="range-lo">▼ ₹{sinfo['day_low']:,.2f}</div></div>
                    <div class="kpi-box"><div class="kpi-label">Next 1 Week</div><div class="range-hi">▲ ₹{sinfo['week_high']:,.2f}</div><div class="range-lo">▼ ₹{sinfo['week_low']:,.2f}</div></div>
                    <div class="kpi-box"><div class="kpi-label">Next 1 Month</div><div class="range-hi">▲ ₹{sinfo['month_high']:,.2f}</div><div class="range-lo">▼ ₹{sinfo['month_low']:,.2f}</div></div>
                    <div class="kpi-box"><div class="kpi-label">52-Wk Ceiling/Floor</div><div class="range-hi">⬆️ ₹{sinfo['high_52w']:,.2f}</div><div class="range-lo">⬇️ ₹{sinfo['low_52w']:,.2f}</div></div>
                </div>
                """
            )

            sdf_plot = sdf.tail(90).copy()
            sdf_plot["20-Day Avg"] = sdf["Close"].rolling(20).mean().tail(90)
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=sdf_plot.index, y=sdf_plot["Close"], name="Price (₹)", line=dict(color="#2563eb", width=2.4)))
            fig.add_trace(go.Scatter(x=sdf_plot.index, y=sdf_plot["20-Day Avg"], name="20D Trend", line=dict(color="#f59e0b", dash="dot", width=1.6)))
            fig.add_hline(y=sinfo["week_high"], line_dash="dash", line_color="#16a34a", annotation_text=f"1W Hi ₹{sinfo['week_high']}")
            fig.add_hline(y=sinfo["week_low"], line_dash="dash", line_color="#dc2626", annotation_text=f"1W Lo ₹{sinfo['week_low']}")
            fig.update_layout(height=290, margin=dict(l=6, r=6, t=28, b=6), legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0), xaxis=dict(fixedrange=True), yaxis=dict(fixedrange=True))
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

            clean_name = label_to_show.split("(")[0].strip()
            comp_news = fetch_live_news(f"{clean_name} stock share price India", max_items=4)
            if comp_news:
                with st.expander(f"📰 Live News: {clean_name}", expanded=True):
                    for n in comp_news:
                        st.markdown(f"{n['mood']} · [{n['title']}]({n['link']}) `{n['published']}`")

            if MARKET_OPEN:
                render_html('<div class="sec-title">🎮 Practice Dummy Buy</div>')
                portfolio = get_session_portfolio()
                st.caption(f"Dummy Cash Available: **₹{portfolio['cash']:,.2f}**")
                d1, d2 = st.columns([1.6, 1])
                dummy_amt = d1.number_input("Amount (₹)", min_value=500.0, max_value=max(500.0, float(portfolio["cash"])), value=min(10000.0, max(500.0, float(portfolio["cash"]))), step=500.0, key="stock_dummy_amt")
                qty = int(dummy_amt // sinfo["price"])
                actual_cost = round(qty * sinfo["price"], 2)
                st.caption(f"Buys **{qty} shares** @ ₹{sinfo['price']:,.2f} (Total: ₹{actual_cost:,.2f})")

                if d2.button("💸 Buy Dummy", type="primary", use_container_width=True, key="buy_stock_btn"):
                    if qty <= 0:
                        st.warning("Increase amount to buy at least 1 share.")
                    elif actual_cost > portfolio["cash"]:
                        st.error("Not enough dummy cash! Add more in **🎮 Dummy** tab.")
                    else:
                        new_cash = round(portfolio["cash"] - actual_cost, 2)
                        holding = {
                            "id": str(int(now_ist().timestamp() * 1000)),
                            "asset_type": "STOCK",
                            "ticker": ticker_to_show,
                            "name": label_to_show,
                            "buy_price": sinfo["price"],
                            "qty": qty,
                            "invested": actual_cost,
                            "buy_date": now_ist().strftime("%d %b, %I:%M %p"),
                            "target_price": sinfo["sell_target"],
                            "stop_loss": sinfo["stop_loss"],
                        }
                        db_record_buy(ACTIVE_USER, holding, new_cash, portfolio["total_deposited"])
                        portfolio["cash"] = new_cash
                        portfolio["holdings"].append(holding)
                        st.success(f"Saved privately! Bought {qty} dummy shares of **{label_to_show}**.")

        render_searched_stock_live(full_ticker, display_name)

# ==============================================================================
# TAB 3: TOP 10 SIPs, MUTUAL FUNDS & GOLD
# ==============================================================================
with tab3:
    mf_news = fetch_live_news("India mutual fund SIP inflow top performing funds gold", max_items=6)
    with st.spinner("Loading Top 10 Profitable SIPs & Mutual Funds..."):
        mf_board = scan_top_mutual_funds()

    render_html('<div class="sec-title">🔥 SIPs & MFs On The Move</div>')
    if not mf_board.empty:
        hot_mfs = mf_board[mf_board["IsHot"]].head(4)
        render_mf_cards(hot_mfs if not hot_mfs.empty else mf_board.head(4), ranked=False)

    with st.expander("📰 Live Mutual Fund, SIP & Gold News"):
        if mf_news:
            for n in mf_news:
                st.markdown(f"{n['mood']} · [{n['title']}]({n['link']}) `{n['published']}`")
        else:
            st.caption("News feed temporarily unavailable.")

    render_html('<div class="sec-title">🏆 Top 10 Profitable SIPs & MFs</div>')
    render_html('<div class="sec-sub">Ranked by real 3-year profit on a ₹5,000/month SIP (Official AMFI NAVs)</div>')
    mf_view = st.radio("MF Layout", ["📱 Modern Cards", "📊 Full Table"], horizontal=True, label_visibility="collapsed", key="mf_view")

    if not mf_board.empty:
        top10_mf = mf_board.head(10).copy()
        if mf_view == "📱 Modern Cards":
            render_mf_cards(top10_mf, ranked=True)
        else:
            top10_mf.insert(0, "Rank", range(1, len(top10_mf) + 1))
            st.dataframe(top10_mf[["Rank", "Fund Name", "Category", "Highlight", "Latest NAV (₹)", "1-Month (%)", "1-Year (%)", "3-Year (%/yr)", "₹5k/mo SIP Profit (3Y)"]], use_container_width=True, hide_index=True)

    @st.fragment(run_every=AUTO_INTERVAL)
    def render_live_gold_etfs():
        render_html('<div class="sec-title">🪙 Gold, Silver & Nifty ETFs</div>')
        st.caption(f"⏱️ Live ETF Prices: {now_ist().strftime('%I:%M:%S %p IST')}" if MARKET_OPEN else "❄️ Frozen at Last Market Close")

        portfolio = get_session_portfolio()
        etf_cols = st.columns(2)
        for idx, (etf_ticker, (etf_title, etf_desc)) in enumerate(GOLD_AND_ETFS.items()):
            _, etf_info = fetch_single_stock_live(etf_ticker, MARKET_OPEN)
            with etf_cols[idx % 2]:
                if etf_info:
                    render_html(
                        f"""
                        <div class="fin-card" style="margin-bottom:8px;">
                            <div class="fin-row">
                                <div><div class="fin-name">{html.escape(etf_title)}</div><div class="fin-meta">{html.escape(etf_desc)}</div></div>
                                <div style="text-align:right;"><div class="fin-price">₹{etf_info['price']:,.2f}</div>{pct_pill(etf_info['daily_pct'], ' today')}</div>
                            </div>
                            <div><span class="pill-tag">{html.escape(etf_info['move_badge'])}</span></div>
                            <div class="fin-footer"><span>🎯 ₹{etf_info['sell_target']}</span><span>🛡️ ₹{etf_info['stop_loss']}</span></div>
                        </div>
                        """
                    )
                    if MARKET_OPEN:
                        if st.button(f"Buy ₹5,000 Dummy ({etf_ticker.replace('.NS', '')})", key=f"buy_etf_{etf_ticker}", use_container_width=True):
                            qty = int(5000 // etf_info["price"])
                            cost = round(qty * etf_info["price"], 2)
                            if qty > 0 and cost <= portfolio["cash"]:
                                new_cash = round(portfolio["cash"] - cost, 2)
                                holding = {
                                    "id": str(int(now_ist().timestamp() * 1000) + idx),
                                    "asset_type": "ETF",
                                    "ticker": etf_ticker,
                                    "name": etf_title,
                                    "buy_price": etf_info["price"],
                                    "qty": qty,
                                    "invested": cost,
                                    "buy_date": now_ist().strftime("%d %b, %I:%M %p"),
                                    "target_price": etf_info["sell_target"],
                                    "stop_loss": etf_info["stop_loss"],
                                }
                                db_record_buy(ACTIVE_USER, holding, new_cash, portfolio["total_deposited"])
                                portfolio["cash"] = new_cash
                                portfolio["holdings"].append(holding)
                                st.success(f"Saved privately! Invested ₹{cost:,.2f} dummy into {etf_title}.")
                                st.rerun()
                            else:
                                st.warning("Not enough dummy cash!")

    render_live_gold_etfs()

    render_html('<div class="sec-title">🔍 Search Any Mutual Fund & SIP Calculator</div>')
    mf_choice_mode = st.selectbox("Pick a Popular Fund:", list(POPULAR_MFS.keys()))
    mf_search_text = st.text_input("Or search ANY Indian Mutual Fund:", placeholder="e.g. Axis Bluechip, Quant Mid Cap...")

    selected_scheme_code, selected_mf_name = POPULAR_MFS[mf_choice_mode][0], mf_choice_mode
    if mf_search_text and len(mf_search_text.strip()) >= 3:
        mf_results = search_amfi_mutual_funds(mf_search_text)
        if mf_results:
            mf_map = {f"{m['schemeName']}": str(m["schemeCode"]) for m in mf_results}
            picked_mf = st.selectbox("Select matching AMFI Fund:", list(mf_map.keys()))
            selected_scheme_code, selected_mf_name = mf_map[picked_mf], picked_mf

    try:
        meta, mf_df, mf_info = fetch_mf_nav(selected_scheme_code)
    except Exception:
        mf_df, mf_info = pd.DataFrame(), None

    if mf_info is not None and not mf_df.empty:
        latest_nav, latest_dt = float(mf_df["nav"].iloc[-1]), mf_df.index[-1]
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

        render_html(
            f"""
            <div class="fin-card" style="margin:8px 0;">
                <div class="fin-name">{html.escape(selected_mf_name)}</div>
                <div class="fin-meta">Official NAV: ₹{latest_nav:,.2f} ({latest_dt.strftime('%d %b %Y')})</div>
                <div class="fin-footer"><span>Invested: <b>₹{invested_sip:,.0f}</b></span><span>Today: <b>₹{val_sip:,.0f}</b></span></div>
                <div style="margin-top:6px;">Profit: <b>{rs_signed(profit_sip)}</b> {pct_pill(sip_pct)}</div>
            </div>
            """
        )

        if MARKET_OPEN:
            portfolio = get_session_portfolio()
            mb1, mb2 = st.columns([1.5, 1])
            mf_dummy_amt = mb1.number_input("Dummy MF Amount (₹)", min_value=500.0, max_value=max(500.0, float(portfolio["cash"])), value=min(5000.0, max(500.0, float(portfolio["cash"]))), step=500.0, key="mf_dummy_amt")
            if mb2.button("💸 Buy Dummy MF", type="primary", use_container_width=True):
                if mf_dummy_amt <= portfolio["cash"]:
                    units = round(mf_dummy_amt / latest_nav, 4)
                    new_cash = round(portfolio["cash"] - mf_dummy_amt, 2)
                    holding = {
                        "id": str(int(now_ist().timestamp() * 1000)),
                        "asset_type": "MF",
                        "ticker": selected_scheme_code,
                        "name": f"MF: {selected_mf_name[:42]}",
                        "buy_price": round(latest_nav, 2),
                        "qty": units,
                        "invested": round(mf_dummy_amt, 2),
                        "buy_date": now_ist().strftime("%d %b, %I:%M %p"),
                        "target_price": round(latest_nav * 1.20, 2),
                        "stop_loss": round(latest_nav * 0.85, 2),
                    }
                    db_record_buy(ACTIVE_USER, holding, new_cash, portfolio["total_deposited"])
                    portfolio["cash"] = new_cash
                    portfolio["holdings"].append(holding)
                    st.success(f"Saved privately! Invested ₹{mf_dummy_amt:,.2f} dummy into this Mutual Fund.")
                else:
                    st.error("Not enough dummy cash!")

# ==============================================================================
# TAB 4: 100% PRIVATE PER-USER PERSONAL GOOGLE SHEET DUMMY PORTFOLIO
# ==============================================================================
with tab4:
    @st.fragment(run_every=AUTO_INTERVAL)
    def render_live_dummy_portfolio():
        top_p1, top_p2 = st.columns([2, 1])
        with top_p1:
            render_html(f'<div class="sec-title">🎮 {html.escape(ACTIVE_USER["full_name"])}\'s Private Dummy Portfolio</div>')
        if top_p2.button("☁️ Sync My Sheet", use_container_width=True):
            st.session_state["user_portfolio"] = db_fetch_user_portfolio(ACTIVE_USER)
            st.rerun()

        has_personal_sheet = bool(ACTIVE_USER.get("personal_sheet_url", "").strip())
        if _gsheets_configured():
            if has_personal_sheet:
                st.caption(f"🔒 Synced to **YOUR Personal Google Sheet** · [Open My Sheet]({ACTIVE_USER['personal_sheet_url']})")
            else:
                st.warning(
                    "⚠️ **No Personal Google Sheet connected yet!** Your trades are currently session-only "
                    "(never saved to anyone else's sheet). Connect your own Google Sheet below to save permanently!"
                )
        else:
            st.caption("💾 Local Account Storage · Add Google Secrets on Streamlit Cloud for Personal Sheets.")

        portfolio = get_session_portfolio()
        holdings = portfolio["holdings"]
        total_invested, total_current = 0.0, 0.0
        enriched_holdings = []

        for h in holdings:
            if h.get("asset_type") == "MF":
                try:
                    _, _, live_info = fetch_mf_nav(h["ticker"])
                except Exception:
                    live_info = None
            else:
                _, live_info = fetch_single_stock_live(h["ticker"], MARKET_OPEN)

            live_price = live_info["price"] if live_info else h["buy_price"]
            cur_val = round(live_price * h["qty"], 2)
            pnl = round(cur_val - h["invested"], 2)
            pnl_pct = round((pnl / h["invested"]) * 100.0, 2) if h["invested"] > 0 else 0.0
            sell_signal, sell_reason = predict_when_to_sell(h, live_info) if live_info else ("⏳ Updating...", "Waiting for quote.")

            total_invested += h["invested"]
            total_current += cur_val
            enriched_holdings.append((h, live_price, cur_val, pnl, pnl_pct, sell_signal, sell_reason))

        total_deposited = float(portfolio.get("total_deposited", 100000.0))
        total_net_worth = portfolio["cash"] + total_current
        overall_pnl = total_net_worth - total_deposited
        holdings_pnl = total_current - total_invested

        nw_cls, nw_arrow = ("kpi-sub-up", "▲") if overall_pnl >= 0 else ("kpi-sub-down", "▼")
        hp_cls, hp_arrow = ("kpi-sub-up", "▲") if holdings_pnl >= 0 else ("kpi-sub-down", "▼")

        render_html(
            f"""
            <div class="grid-2col grid-2col-desktop4">
                <div class="kpi-box"><div class="kpi-label">Virtual Net Worth</div><div class="kpi-val">₹{total_net_worth:,.2f}</div><div class="{nw_cls}">{nw_arrow} {rs_signed(overall_pnl)} P&amp;L</div></div>
                <div class="kpi-box"><div class="kpi-label">Dummy Cash Left</div><div class="kpi-val">₹{portfolio['cash']:,.2f}</div><div class="kpi-sub-muted">Capital Added: ₹{total_deposited:,.0f}</div></div>
                <div class="kpi-box"><div class="kpi-label">Currently Invested</div><div class="kpi-val">₹{total_invested:,.2f}</div><div class="kpi-sub-muted">{len(holdings)} active trades</div></div>
                <div class="kpi-box"><div class="kpi-label">Holdings Value</div><div class="kpi-val">₹{total_current:,.2f}</div><div class="{hp_cls}">{hp_arrow} {rs_signed(holdings_pnl)}</div></div>
            </div>
            """
        )

        # PERSONAL GOOGLE SHEET CONNECTION PANEL (100% PRIVATE PER USER)
        if _gsheets_configured():
            with st.expander("🔗 Connect / Change My Personal Google Sheet (100% Private)", expanded=not has_personal_sheet):
                bot_email = get_bot_email()
                st.markdown(
                    "1. Create your own blank Google Sheet at **[sheets.new](https://sheets.new)**.\n"
                    "2. Click **Share** → add this bot email as **Editor** → **Send**:"
                )
                st.code(bot_email, language=None)
                new_sheet_input = st.text_input(
                    "3. Paste YOUR Google Sheet URL here:",
                    value=ACTIVE_USER.get("personal_sheet_url", ""),
                    placeholder="https://docs.google.com/spreadsheets/d/...",
                    key="personal_sheet_input",
                )
                if st.button("💾 Connect My Personal Google Sheet", type="primary", use_container_width=True):
                    ok, msg = db_update_personal_sheet_url(ACTIVE_USER["username"], new_sheet_input, portfolio)
                    if ok:
                        st.session_state["auth_user"]["personal_sheet_url"] = new_sheet_input.strip()
                        st.session_state["user_portfolio"] = db_fetch_user_portfolio(st.session_state["auth_user"])
                        st.success(msg)
                        st.rerun()
                    else:
                        st.error(msg)

        with st.expander("💰 Increase Dummy Account Value (Add Virtual Cash)", expanded=False):
            st.caption("Saved privately to your own Google Sheet without skewing your real Profit/Loss.")
            qc1, qc2, qc3 = st.columns(3)
            for col_btn, amt in [(qc1, 50000.0), (qc2, 100000.0), (qc3, 500000.0)]:
                if col_btn.button(f"+ ₹{amt:,.0f}", use_container_width=True, key=f"add_{int(amt)}"):
                    new_c, new_d = round(portfolio["cash"] + amt, 2), round(total_deposited + amt, 2)
                    db_add_cash(ACTIVE_USER, new_c, new_d)
                    portfolio["cash"], portfolio["total_deposited"] = new_c, new_d
                    st.rerun()

            ac1, ac2 = st.columns([1.6, 1])
            custom_add = ac1.number_input("Custom amount to add (₹):", min_value=1000.0, max_value=10000000.0, value=25000.0, step=5000.0, key="custom_cash_add")
            if ac2.button("➕ Add Cash", type="primary", use_container_width=True):
                new_c, new_d = round(portfolio["cash"] + float(custom_add), 2), round(total_deposited + float(custom_add), 2)
                db_add_cash(ACTIVE_USER, new_c, new_d)
                portfolio["cash"], portfolio["total_deposited"] = new_c, new_d
                st.rerun()

        if not enriched_holdings:
            st.info("No active dummy investments." + (" Start in **⚡ Quick** or **🔍 Search**!" if MARKET_OPEN else " Trading opens at **9:15 AM IST (Mon–Fri)**."))
        else:
            render_html('<div class="sec-title">Active Holdings & Sell Alerts</div>')
            for h, live_price, cur_val, pnl, pnl_pct, sell_signal, sell_reason in enriched_holdings:
                label = html.escape(h.get("name", h["ticker"]))
                unit_word = "units" if h.get("asset_type") == "MF" else "shares"
                pnl_cls, pnl_arrow = ("pill-up", "▲") if pnl >= 0 else ("pill-down", "▼")
                target_line = (
                    f"<span>🎯 Target: <b>₹{h['target_price']:,.2f}</b></span><span>🛡️ Stop: <b>₹{h['stop_loss']:,.2f}</b></span>"
                    if h.get("asset_type") != "MF"
                    else f"<span>Live NAV: <b>₹{live_price:,.2f}</b></span><span>Long-term SIP</span>"
                )

                render_html(
                    f"""
                    <div class="fin-card" style="margin-bottom:8px;">
                        <div class="fin-row">
                            <div><div class="fin-name">{label}</div><div class="fin-meta">{h['qty']} {unit_word} @ ₹{h['buy_price']:,.2f} · Last ₹{live_price:,.2f}</div></div>
                            <div style="text-align:right;"><div class="fin-price">₹{cur_val:,.2f}</div><span class="{pnl_cls}">{pnl_arrow} {rs_signed(pnl)} ({pnl_pct:+.2f}%)</span></div>
                        </div>
                        <div><span class="pill-tag">{html.escape(sell_signal)}</span></div>
                        <div class="fin-meta" style="margin-top:5px;">{html.escape(sell_reason)}</div>
                        <div class="fin-footer">{target_line}</div>
                    </div>
                    """
                )

                if MARKET_OPEN:
                    if st.button(f"Sell Now (Dummy) — {h.get('name', h['ticker'])[:24]}", key=f"sell_{h['id']}", type="primary", use_container_width=True):
                        new_cash = round(portfolio["cash"] + cur_val, 2)
                        hist_row = {
                            "Asset": h.get("name", h["ticker"]),
                            "Qty": h["qty"],
                            "Buy (₹)": h["buy_price"],
                            "Sell (₹)": live_price,
                            "P&L (₹)": pnl,
                            "Return (%)": pnl_pct,
                            "Sold On": now_ist().strftime("%d %b, %I:%M %p"),
                        }
                        db_record_sell(ACTIVE_USER, str(h["id"]), hist_row, new_cash, total_deposited)
                        portfolio["cash"] = new_cash
                        portfolio["holdings"] = [item for item in portfolio["holdings"] if str(item["id"]) != str(h["id"])]
                        portfolio["history"].append(hist_row)
                        st.rerun()

        if portfolio["history"]:
            render_html('<div class="sec-title">Past Completed Trades</div>')
            st.dataframe(pd.DataFrame(portfolio["history"]).iloc[::-1], use_container_width=True, hide_index=True)

        st.divider()
        if st.button("🔁 Reset My Dummy Wallet Back to ₹1,00,000", use_container_width=True):
            db_reset_user_wallet(ACTIVE_USER)
            st.session_state["user_portfolio"] = {"cash": 100000.0, "total_deposited": 100000.0, "holdings": [], "history": []}
            st.rerun()

    render_live_dummy_portfolio()
