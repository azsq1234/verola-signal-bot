"""
Signal Analyzer — High-Frequency (5-minute) Edition
Data sources:
  - ccxt / Kraken  → crypto pairs containing "/"   e.g. BTC/USD
  - yfinance       → commodities, forex, stocks     e.g. GC=F, EURUSD=X
Indicators: RSI, MA crossover, ATR-based TP/SL
"""

import ccxt
import yfinance as yf
import numpy as np
import pandas as pd
from datetime import datetime, timezone

from utils.logger import get_logger

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Default watchlist — major crypto + forex + commodities
# ---------------------------------------------------------------------------
WATCHLIST: list[str] = [
    # ── Crypto (Kraken) ──────────────────────────────
    "BTC/USD",
    "ETH/USD",
    "SOL/USD",
    "XRP/USD",
    "ADA/USD",
    "AVAX/USD",
    "LINK/USD",
    "DOT/USD",
    # ── Commodities (yfinance) ────────────────────────
    "GC=F",       # Gold
    "SI=F",       # Silver
    "CL=F",       # Crude Oil
    # ── Forex (yfinance) ─────────────────────────────
    "EURUSD=X",
    "GBPUSD=X",
    "USDJPY=X",
    "AUDUSD=X",
    "USDCHF=X",
]

# ---------------------------------------------------------------------------
# Display names
# ---------------------------------------------------------------------------
DISPLAY_NAMES: dict[str, str] = {
    "GC=F":     "Gold",
    "SI=F":     "Silver",
    "CL=F":     "Crude Oil",
    "NG=F":     "Natural Gas",
    "PL=F":     "Platinum",
    "EURUSD=X": "EUR/USD",
    "GBPUSD=X": "GBP/USD",
    "USDJPY=X": "USD/JPY",
    "AUDUSD=X": "AUD/USD",
    "USDCHF=X": "USD/CHF",
    "NZDUSD=X": "NZD/USD",
    "USDCAD=X": "USD/CAD",
}

# ---------------------------------------------------------------------------
# Timeframe / indicator settings
# ---------------------------------------------------------------------------
CRYPTO_TIMEFRAME = "5m"
YF_INTERVAL      = "5m"
YF_PERIOD        = "5d"       # 5-day lookback ensures data even on weekends/holidays
RSI_PERIOD       = 14
MA_FAST          = 9
MA_SLOW          = 21
ATR_PERIOD       = 14
ATR_TP_MULT      = 1.5        # TP = entry ± (ATR × 1.5)
ATR_SL_MULT      = 1.0        # SL = entry ∓ (ATR × 1.0)


# ---------------------------------------------------------------------------
# Indicator helpers
# ---------------------------------------------------------------------------

def _compute_rsi(close: pd.Series, period: int = RSI_PERIOD) -> float:
    delta = close.diff()
    gain  = delta.clip(lower=0)
    loss  = -delta.clip(upper=0)
    avg_gain = gain.ewm(com=period - 1, min_periods=period).mean()
    avg_loss = loss.ewm(com=period - 1, min_periods=period).mean()
    rs  = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    return round(float(rsi.iloc[-1]), 2)


def _compute_ma(close: pd.Series, period: int) -> float:
    return round(float(close.rolling(period).mean().iloc[-1]), 6)


def _compute_atr(df: pd.DataFrame, period: int = ATR_PERIOD) -> float:
    high  = df["high"].astype(float)
    low   = df["low"].astype(float)
    close = df["close"].astype(float)
    prev_close = close.shift(1)
    tr = pd.concat([
        high - low,
        (high - prev_close).abs(),
        (low  - prev_close).abs(),
    ], axis=1).max(axis=1)
    atr = tr.ewm(com=period - 1, min_periods=period).mean()
    return float(atr.iloc[-1])


def _is_crypto(symbol: str) -> bool:
    return "/" in symbol


def _asset_icon(symbol: str) -> str:
    if _is_crypto(symbol):  return "🪙"
    if symbol.endswith("=F"): return "🏅"
    if symbol.endswith("=X"): return "💱"
    return "📈"


def _compute_strength(
    rsi: float,
    ma_fast: float,
    ma_slow: float,
    atr: float,
    price: float,
) -> tuple[int, str]:
    """
    Signal strength score 0-100 built from three independent components:
      - RSI extremity   (0-40 pts): how far RSI is from neutral (50)
      - MA divergence   (0-35 pts): % gap between fast and slow MA
      - ATR momentum    (0-25 pts): ATR as % of price (volatility / energy)
    Returns (score, label).
    """
    # RSI component — max 40 pts
    rsi_dist  = abs(rsi - 50)                        # 0-50
    rsi_score = min(40.0, rsi_dist / 50 * 40)

    # MA divergence component — max 35 pts
    ma_spread_pct = abs(ma_fast - ma_slow) / price * 100  # percent
    ma_score = min(35.0, ma_spread_pct * 700)        # 0.05 % → 35 pts

    # ATR momentum component — max 25 pts
    atr_pct   = atr / price * 100                    # percent
    atr_score = min(25.0, atr_pct * 50)              # 0.5 % → 25 pts

    score = round(min(100, rsi_score + ma_score + atr_score))

    if score >= 85:
        label = "🔥 Very Strong"
    elif score >= 65:
        label = "🟢 Strong"
    elif score >= 40:
        label = "🟡 Moderate"
    else:
        label = "🔴 Weak"

    return score, label


def _fmt_price(symbol: str, price: float) -> str:
    if symbol.endswith("=X"):           # forex — 5 dp
        return f"{price:.5f}"
    if symbol in ("SI=F",):             # silver / cheap commodities
        return f"${price:.3f}"
    if price < 10:
        return f"${price:.4f}"
    return f"${price:,.2f}"


# ---------------------------------------------------------------------------
# Analyzer class
# ---------------------------------------------------------------------------

class SignalAnalyzer:
    def __init__(self, exchange_id: str = "kraken"):
        self.exchange: ccxt.Exchange = getattr(ccxt, exchange_id)(
            {"enableRateLimit": True}
        )
        self._watchlist: list[str] = list(WATCHLIST)
        logger.info(
            "Exchange: %s (crypto) + yfinance (commodities/forex) | interval: %s",
            exchange_id, CRYPTO_TIMEFRAME,
        )

    # ------------------------------------------------------------------
    # Watchlist management
    # ------------------------------------------------------------------

    def get_watchlist(self) -> list[str]:
        return list(self._watchlist)

    def add_symbol(self, symbol: str) -> tuple[bool, str]:
        normalized = symbol.upper()
        if normalized in [s.upper() for s in self._watchlist]:
            return False, f"`{symbol}` is already in the watchlist."
        self._watchlist.append(normalized)
        logger.info("Added %s to watchlist", normalized)
        return True, f"✅ `{normalized}` added to the watchlist."

    def remove_symbol(self, symbol: str) -> tuple[bool, str]:
        normalized = symbol.upper()
        for entry in self._watchlist:
            if entry.upper() == normalized:
                self._watchlist.remove(entry)
                logger.info("Removed %s from watchlist", entry)
                return True, f"✅ `{entry}` removed from the watchlist."
        return False, f"❌ `{symbol}` was not found in the watchlist."

    # ------------------------------------------------------------------
    # Data fetching
    # ------------------------------------------------------------------

    def _fetch_crypto(self, symbol: str) -> pd.DataFrame:
        limit = max(RSI_PERIOD, MA_SLOW, ATR_PERIOD) + 10
        raw   = self.exchange.fetch_ohlcv(symbol, timeframe=CRYPTO_TIMEFRAME, limit=limit)
        df    = pd.DataFrame(raw, columns=["timestamp", "open", "high", "low", "close", "volume"])
        return df.astype({"open": float, "high": float, "low": float, "close": float})

    def _fetch_yfinance(self, symbol: str) -> pd.DataFrame:
        ticker = yf.Ticker(symbol)
        df = ticker.history(period=YF_PERIOD, interval=YF_INTERVAL)
        if df.empty:
            raise ValueError(f"No data returned from yfinance for {symbol}")
        df = df.rename(columns={"Open": "open", "High": "high", "Low": "low", "Close": "close"})
        return df[["open", "high", "low", "close"]].reset_index()

    def _fetch(self, symbol: str) -> tuple[pd.DataFrame, str]:
        if _is_crypto(symbol):
            return self._fetch_crypto(symbol), "Kraken"
        return self._fetch_yfinance(symbol), "yfinance"

    # ------------------------------------------------------------------
    # Signal generation
    # ------------------------------------------------------------------

    def analyze(self, symbol: str) -> str:
        df, source = self._fetch(symbol)
        close = df["close"]

        entry   = round(float(close.iloc[-1]), 6)
        rsi     = _compute_rsi(close)
        ma_fast = _compute_ma(close, MA_FAST)
        ma_slow = _compute_ma(close, MA_SLOW)
        atr     = _compute_atr(df)

        # ── Signal decision ──────────────────────────────────────────
        if rsi < 30 and ma_fast > ma_slow:
            action, direction = "🟢 BUY",       "BUY"
        elif rsi > 70 and ma_fast < ma_slow:
            action, direction = "🔴 SELL",      "SELL"
        elif rsi < 35 and ma_fast >= ma_slow:
            action, direction = "🟡 WEAK BUY",  "BUY"
        elif rsi > 65 and ma_fast <= ma_slow:
            action, direction = "🟠 WEAK SELL", "SELL"
        else:
            action, direction = "⚪ HOLD",      "HOLD"

        # ── ATR-based TP / SL ────────────────────────────────────────
        if direction == "BUY":
            tp = entry + atr * ATR_TP_MULT
            sl = entry - atr * ATR_SL_MULT
        elif direction == "SELL":
            tp = entry - atr * ATR_TP_MULT
            sl = entry + atr * ATR_SL_MULT
        else:
            tp = sl = None

        # ── Strength score ────────────────────────────────────────────
        score, strength_label = _compute_strength(rsi, ma_fast, ma_slow, atr, entry)

        # Build a visual bar: filled blocks out of 10
        filled = round(score / 10)
        bar    = "█" * filled + "░" * (10 - filled)

        # ── Helpers ──────────────────────────────────────────────────
        trend     = "📈 Bullish" if ma_fast > ma_slow else "📉 Bearish"
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        icon      = _asset_icon(symbol)
        label     = DISPLAY_NAMES.get(symbol, symbol)
        timeframe = CRYPTO_TIMEFRAME if _is_crypto(symbol) else YF_INTERVAL

        entry_str = _fmt_price(symbol, entry)
        tp_str    = _fmt_price(symbol, tp) if tp is not None else "—"
        sl_str    = _fmt_price(symbol, sl) if sl is not None else "—"

        # ── Lot size tiers ───────────────────────────────────────────
        lot_section = (
            f"💼 *SUGGESTED LOT SIZE*\n"
            f"┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄\n"
            f"🟡 $100 – $500    →  `0.01`\n"
            f"🟢 $501 – $1,000  →  `0.05`\n"
            f"🔵 $1,000+        →  `0.10`"
        )

        # ── Message ──────────────────────────────────────────────────
        message = (
            f"📡 *VEROLA SIGNAL*\n"
            f"{'─' * 30}\n"
            f"{icon} *{label}*   `{timeframe}`\n"
            f"\n"
            f"🚦 *{action}*\n"
            f"\n"
            f"💰 *Entry:*   `{entry_str}`\n"
            f"🎯 *TP:*      `{tp_str}`\n"
            f"🛡️ *SL:*      `{sl_str}`\n"
            f"📈 *Trend:*   {trend}\n"
            f"\n"
            f"{'─' * 30}\n"
            f"💪 *SIGNAL STRENGTH*\n"
            f"`{bar}` *{score}/100* — {strength_label}\n"
            f"\n"
            f"{'─' * 30}\n"
            f"{lot_section}\n"
            f"{'─' * 30}\n"
            f"⚠️ _Not financial advice. DYOR._"
        )

        logger.info(
            "Signal for %s (%s): %s | Entry %s | TP %s | SL %s",
            symbol, source, action, entry_str, tp_str, sl_str,
        )
        return message
