"""
=============================================================================
  SNIPER BOT - محرك التحليل (11 طبقة)
=============================================================================
"""

import requests
import time
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict

BINANCE_URL = "https://api.binance.com"
WHALE_MULT = 2.5
EXTREME_WHALE_MULT = 5.0
MIN_VOLUME_USD = 500000
PROFIT_TARGET_FIXED = 0.05
MIN_RR = 1.5

@dataclass
class Candle:
    ts: int
    open: float
    high: float
    low: float
    close: float
    vol: float

@dataclass
class AnalysisResult:
    symbol: str
    timestamp: str
    price: float
    entry: float
    sl: float
    tp1: float
    tp2: float
    tp1_fixed: float
    tp2_fixed: float
    rr: float
    rr_fixed: float
    score: int
    whale_score: int
    tech_score: int
    signal: str
    trend: str
    rsi: float
    support: float
    resistance: float
    pattern: str
    rsi_divergence: bool
    bos_choch: str
    position: Dict
    details: List[str]
    timeframe_analysis: Dict
    error: Optional[str] = None
    
    def to_dict(self) -> Dict:
        return asdict(self)

def mean(values: List[float]) -> float:
    return sum(values) / len(values) if values else 0.0

def sma(values: List[float], period: int) -> float:
    if len(values) < period:
        return mean(values)
    return mean(values[-period:])

def ema(values: List[float], period: int) -> float:
    if len(values) < period:
        return values[-1] if values else 0.0
    k = 2.0 / (period + 1)
    val = mean(values[:period])
    for v in values[period:]:
        val = v * k + val * (1.0 - k)
    return val

def pct_change(new_val: float, old_val: float) -> float:
    if old_val == 0:
        return 0.0
    return round((new_val / old_val - 1) * 100, 2)

def atr(candles: List[Candle], period: int = 14) -> float:
    if len(candles) < period + 1:
        return candles[-1].close * 0.02
    trs = []
    for i in range(1, len(candles)):
        h, l, cp = candles[i].high, candles[i].low, candles[i-1].close
        trs.append(max(h - l, abs(h - cp), abs(l - cp)))
    return mean(trs[-period:])

def fetch_candles(symbol: str, interval: str = "1h", limit: int = 150) -> List[Candle]:
    try:
        response = requests.get(
            f"{BINANCE_URL}/api/v3/klines",
            params={"symbol": symbol, "interval": interval, "limit": limit},
            timeout=10
        )
        if response.status_code != 200: return []
        candles = []
        for row in response.json():
            candles.append(Candle(
                ts=int(row[0]),
                open=float(row[1]), high=float(row[2]),
                low=float(row[3]), close=float(row[4]),
                vol=float(row[5])
            ))
        return candles
    except Exception:
        return []

def fetch_trades(symbol: str, limit: int = 100) -> List[Dict]:
    try:
        response = requests.get(
            f"{BINANCE_URL}/api/v3/trades",
            params={"symbol": symbol, "limit": limit},
            timeout=10
        )
        if response.status_code != 200: return []
        return response.json()
    except Exception:
        return []

def fetch_orderbook(symbol: str) -> Dict:
    try:
        response = requests.get(
            f"{BINANCE_URL}/api/v3/depth",
            params={"symbol": symbol, "limit": 20},
            timeout=10
        )
        if response.status_code != 200: return {}
        return response.json()
    except Exception:
        return {}

def get_top_symbols(limit: int = 150) -> List[str]:
    try:
        response = requests.get(f"{BINANCE_URL}/api/v3/ticker/24hr", timeout=15)
        if response.status_code != 200: return []
        pairs = []
        for ticker in response.json():
            symbol = ticker["symbol"]
            if symbol.endswith("USDT") and "BUSD" not in symbol and "TUSD" not in symbol:
                try:
                    usd_volume = float(ticker["quoteVolume"])
                    if usd_volume >= MIN_VOLUME_USD:
                        pairs.append({"symbol": symbol, "volume_usd": usd_volume})
                except: continue
        pairs.sort(key=lambda x: x["volume_usd"], reverse=True)
        return [p["symbol"] for p in pairs[:limit]]
    except Exception:
        return []

def calc_rsi(candles: List[Candle], period: int = 14) -> float:
    closes = [c.close for c in candles]
    if len(closes) < period + 1: return 50.0
    gains, losses = [], []
    for i in range(1, len(closes)):
        d = closes[i] - closes[i - 1]
        gains.append(max(d, 0.0))
        losses.append(max(-d, 0.0))
    rs = mean(gains[-period:]) / (mean(losses[-period:]) or 1)
    return round(100.0 - 100.0 / (1.0 + rs), 2)

def calc_macd(candles: List[Candle]) -> Dict:
    closes = [c.close for c in candles]
    if len(closes) < 35:
        return {"cross_up": False, "hist": 0.0, "expanding": False}
    ema12 = [ema(closes[:i + 1], 12) for i in range(len(closes))]
    ema26 = [ema(closes[:i + 1], 26) for i in range(len(closes))]
    macd = [ema12[i] - ema26[i] for i in range(len(closes))]
    sig = [ema(macd[:i + 1], 9) for i in range(len(macd))]
    hist = [macd[i] - sig[i] for i in range(len(macd))]
    return {
        "cross_up": macd[-1] > sig[-1] and macd[-2] <= sig[-2],
        "hist": hist[-1],
        "expanding": abs(hist[-1]) > abs(hist[-2]) if len(hist) > 1 else False
    }

def get_trend(candles: List[Candle]) -> str:
    if len(candles) < 55: return "محايد"
    price = candles[-1].close
    closes = [c.close for c in candles]
    ma20 = sma(closes, 20)
    ma50 = sma(closes, 50)
    return "صاعد" if price > ma20 > ma50 else "هابط" if price < ma20 < ma50 else "محايد"

def detect_rsi_divergence(candles: List[Candle]) -> Dict:
    if len(candles) < 30:
        return {"bullish": False, "bearish": False}
    prices = [c.close for c in candles[-30:]]
    rsis = []
    for i in range(14, len(candles)):
        rsis.append(calc_rsi(candles[max(0, i-20):i+1]))
    if len(rsis) < 10:
        return {"bullish": False, "bearish": False}
    p_recent = prices[-1]
    p_prev = min(prices[-10:-1])
    r_recent = rsis[-1]
    r_prev = rsis[-10] if len(rsis) >= 10 else rsis[0]
    bullish_div = p_recent < p_prev and r_recent > r_prev
    bearish_div = p_recent > p_prev and r_recent < r_prev
    return {"bullish": bullish_div, "bearish": bearish_div}

def detect_order_block(candles: List[Candle]) -> Dict:
    result = {"bullish": None, "bearish": None}
    n = len(candles)
    if n < 10: return result
    for i in range(n - 3, max(n - 30, 1), -1):
        c, c1, c2 = candles[i], candles[i+1], candles[i+2]
        rng = c.high - c.low
        if rng == 0: continue
        body = abs(c.close - c.open)
        if c.close < c.open and body/rng > 0.55:
            if c1.close > c.high or c2.close > c.high:
                result["bullish"] = {"high": c.high, "low": c.low}
                break
    return result

def detect_fvg(candles: List[Candle]) -> Dict:
    result = {"bullish": None, "bearish": None}
    n = len(candles)
    if n < 5: return result
    for i in range(n - 3, max(n - 20, 1), -1):
        prev, nxt = candles[i-1], candles[i+1]
        if nxt.low > prev.high:
            result["bullish"] = {"top": nxt.low, "bottom": prev.high}
            break
    return result

def detect_bos_choch(candles: List[Candle]) -> Dict:
    result = {"bos_bullish": False, "choch_bullish": False, "detail": ""}
    if len(candles) < 20: return result
    recent = candles[-20:]
    highs = [c.high for c in recent]
    lows = [c.low for c in recent]
    closes = [c.close for c in recent]
    prev_high = max(highs[-10:-1])
    prev_low = min(lows[-10:-1])
    curr = closes[-1]
    if curr > prev_high:
        result["bos_bullish"] = True
        result["detail"] = f"BOS صاعد — كسر {round(prev_high, 4)}"
    elif curr > prev_high * 0.98 and closes[-5] < prev_low:
        result["choch_bullish"] = True
        result["detail"] = "CHoCH — تحول محتمل من هابط لصاعد"
    return result

def detect_candle_pattern(candles: List[Candle]) -> str:
    if len(candles) < 3: return "محايد"
    c, p, pp = candles[-1], candles[-2], candles[-3]
    rng = c.high - c.low
    if rng == 0: return "محايد"
    body = abs(c.close - c.open)
    lw = min(c.open, c.close) - c.low
    uw = c.high - max(c.open, c.close)
    if lw > body * 2 and uw < body * 0.5 and c.close > c.open:
        return "🔨 مطرقة"
    if uw > body * 2 and lw < body * 0.5 and c.close < c.open:
        return "💫 شهاب"
    if (c.close > c.open and p.close < p.open and 
        c.open < p.close and c.close > p.open):
        return "📈 ابتلاع صاعد"
    if (c.close < c.open and p.close > p.open and 
        c.open > p.close and c.close < p.open):
        return "📉 ابتلاع هابط"
    if (pp.close < pp.open and 
        abs(p.close - p.open) < (p.high - p.low) * 0.3 and
        c.close > c.open and c.close > pp.open):
        return "⭐ نجمة الصباح"
    if body / rng < 0.1:
        return "〰️ دوجي"
    return "محايد"

def get_support_resistance(candles: List[Candle]) -> Tuple[float, float]:
    price = candles[-1].close
    window = candles[-50:] if len(candles) >= 50 else candles
    highs = [c.high for c in window]
    lows = [c.low for c in window]
    res_lst = [h for h in highs if h > price]
    sup_lst = [l for l in lows if l < price]
    return max(sup_lst) if sup_lst else price * 0.95, min(res_lst) if res_lst else price * 1.05

def analyze_whale_volume(candles_1h: List[Candle], candles_15m: List[Candle]) -> Dict:
    result = {"score": 0, "details": [], "direction": "محايد", "bearish_whale": False}
    if len(candles_1h) >= 21:
        vols = [c.vol for c in candles_1h[-21:-1]]
        avg_vol = mean(vols)
        last = candles_1h[-1]
        ratio = round(last.vol / avg_vol, 2) if avg_vol > 0 else 0
        direction = "شراء" if last.close > last.open else "بيع"
        result["direction"] = direction
        if ratio >= EXTREME_WHALE_MULT:
            result["score"] += 4
            result["details"].append(f"🐋🐋 حوت ضخم جداً (1H) x{ratio}")
            if direction == "بيع":
                result["bearish_whale"] = True
        elif ratio >= WHALE_MULT:
            result["score"] += 3
            result["details"].append(f"🐋 حوت قوي (1H) x{ratio}")
            if direction == "بيع":
                result["bearish_whale"] = True
        elif ratio >= 1.8:
            result["score"] += 2
            result["details"].append(f"📈 حجم مرتفع (1H) x{ratio}")

    # تأكيد إضافي من فريم 15 دقيقة (كان يُجلب سابقاً ولا يُستخدم إطلاقاً)
    if len(candles_15m) >= 21:
        vols_15m = [c.vol for c in candles_15m[-21:-1]]
        avg_vol_15m = mean(vols_15m)
        last_15m = candles_15m[-1]
        ratio_15m = round(last_15m.vol / avg_vol_15m, 2) if avg_vol_15m > 0 else 0
        if ratio_15m >= WHALE_MULT:
            direction_15m = "شراء" if last_15m.close > last_15m.open else "بيع"
            if direction_15m == "شراء":
                result["score"] += 1
                result["details"].append(f"🐋 دعم حجم (15m) x{ratio_15m}")
            else:
                if ratio_15m >= EXTREME_WHALE_MULT:
                    result["bearish_whale"] = True
                result["details"].append(f"🔴 ضغط بيع حجم (15m) x{ratio_15m}")

    return result

def analyze_whale_trades(trades: List[Dict]) -> Dict:
    result = {"score": 0, "details": []}
    if not trades:
        return result
    sizes = [float(t.get("qty", 0)) * float(t.get("price", 0)) for t in trades]
    avg_size = mean(sizes) if sizes else 0
    threshold = max(avg_size * 5, 2000)
    buys = sells = 0
    for t in trades:
        size_usd = float(t.get("qty", 0)) * float(t.get("price", 0))
        if size_usd >= threshold:
            if t.get("isBuyerMaker", False):
                sells += 1
            else:
                buys += 1
    if buys >= 5 and buys > sells * 2:
        result["score"] += 3
        result["details"].append(f"🐋 ضغط شراء مؤسسي: {buys} شراء")
    elif sells > buys * 2:
        result["score"] -= 1
        result["details"].append(f"🔴 ضغط بيع: {sells} بيع")
    return result

def analyze_whale_orderbook(book: Dict) -> Dict:
    result = {"score": 0, "details": []}
    if not book or not book.get("bids") or not book.get("asks"):
        return result
    bid_vol = sum(float(b[1]) * float(b[0]) for b in book["bids"][:10])
    ask_vol = sum(float(a[1]) * float(a[0]) for a in book["asks"][:10])
    ratio = round(bid_vol / ask_vol, 2) if ask_vol > 0 else 0
    if ratio >= 2.5:
        result["score"] += 3
        result["details"].append(f"🐋 سيولة شراء ضخمة! نسبة {ratio}:1")
    elif ratio < 0.7:
        result["score"] -= 1
        result["details"].append(f"🔴 ضغط بيع: {ratio}:1")
    return result

def analyze_single_coin(symbol: str) -> AnalysisResult:
    c1h = fetch_candles(symbol, "1h", 150)
    c15m = fetch_candles(symbol, "15m", 80)
    c4h = fetch_candles(symbol, "4h", 60)
    c1d = fetch_candles(symbol, "1d", 60)
    
    if len(c1h) < 60:
        return AnalysisResult(
            symbol=symbol, timestamp=datetime.now().isoformat(),
            price=0, entry=0, sl=0, tp1=0, tp2=0,
            tp1_fixed=0, tp2_fixed=0, rr=0, rr_fixed=0,
            score=0, whale_score=0, tech_score=0,
            signal="انتظار", trend="محايد", rsi=50,
            support=0, resistance=0, pattern="محايد",
            rsi_divergence=False, bos_choch="",
            position={}, details=[], timeframe_analysis={},
            error="بيانات غير كافية"
        )
    
    price = c1h[-1].close
    details = []
    tech_score = 0
    whale_score = 0
    
    rsi = calc_rsi(c1h)
    if rsi > 72:
        return AnalysisResult(
            symbol=symbol, timestamp=datetime.now().isoformat(),
            price=price, entry=0, sl=0, tp1=0, tp2=0,
            tp1_fixed=0, tp2_fixed=0, rr=0, rr_fixed=0,
            score=0, whale_score=0, tech_score=0,
            signal="مرفوض", trend="محايد",
            rsi=rsi, support=0, resistance=0, pattern="محايد",
            rsi_divergence=False, bos_choch="",
            position={}, details=["RSI تشبع شراء"], timeframe_analysis={},
            error="RSI تشبع شراء"
        )
    elif 32 <= rsi <= 62:
        tech_score += 1
        details.append(f"✅ +1 RSI={rsi} منطقة مثالية")
    elif rsi < 32:
        tech_score += 1
        details.append(f"✅ +1 RSI={rsi} تشبع بيع")
    
    div = detect_rsi_divergence(c1h)
    if div["bullish"]:
        tech_score += 2
        details.append("🔥 +2 انحراف RSI صاعد")
    elif div["bearish"]:
        tech_score -= 1
        details.append("🔴 -1 انحراف RSI هابط")
    
    macd = calc_macd(c1h)
    if macd["cross_up"] or (macd["hist"] > 0 and macd["expanding"]):
        tech_score += 1
        details.append("✅ +1 MACD تقاطع صاعد")
    
    t1h = get_trend(c1h)
    t4h = get_trend(c4h) if len(c4h) >= 55 else "محايد"
    t1d = get_trend(c1d) if len(c1d) >= 55 else "محايد"
    bullish_tfs = sum(1 for t in [t1h, t4h, t1d] if t == "صاعد")
    if bullish_tfs == 3:
        tech_score += 2
        details.append("✅ +2 اتجاه صاعد 1H+4H+1D")
    elif bullish_tfs == 2:
        tech_score += 1
        details.append(f"🟡 +1 اتجاه صاعد على {bullish_tfs}/3")
    elif t1h == "هابط":
        details.append("🔴 0 اتجاه هابط")
    
    ob = detect_order_block(c1h)
    if ob["bullish"]:
        ob_lo, ob_hi = ob["bullish"]["low"], ob["bullish"]["high"]
        if ob_lo <= price <= ob_hi * 1.02:
            tech_score += 2
            details.append(f"✅ +2 داخل OB صاعد")
        else:
            tech_score += 1
            details.append(f"🟡 +1 OB قريب")
    
    fvg = detect_fvg(c1h)
    if fvg["bullish"]:
        fb, ft = fvg["bullish"]["bottom"], fvg["bullish"]["top"]
        if fb <= price <= ft * 1.01:
            tech_score += 1
            details.append(f"✅ +1 داخل FVG")
    
    bos = detect_bos_choch(c1h)
    if bos["bos_bullish"] or bos["choch_bullish"]:
        tech_score += 1
        details.append(f"✅ +1 {bos['detail']}")
    
    pattern = detect_candle_pattern(c1h)
    bullish_patterns = ["🔨 مطرقة", "📈 ابتلاع صاعد", "⭐ نجمة الصباح"]
    if pattern in bullish_patterns:
        tech_score += 1
        details.append(f"✅ +1 شمعة: {pattern}")
    else:
        details.append(f"⚪ 0 شمعة: {pattern}")
    
    w1 = analyze_whale_volume(c1h, c15m)
    w2 = analyze_whale_trades(fetch_trades(symbol, 100))
    w3 = analyze_whale_orderbook(fetch_orderbook(symbol))
    
    whale_score = w1["score"] + w2["score"] + w3["score"]
    details.extend(w1["details"] + w2["details"] + w3["details"])
    
    total_score = whale_score + tech_score
    
    support, resistance = get_support_resistance(c1h)
    atr_value = atr(c1h, 14)
    
    from config import MIN_SCORE
    
    if total_score >= MIN_SCORE and not w1.get("bearish_whale"):
        sl_sr = support * 0.99
        sl_atr = price - (atr_value * 1.8)
        sl = min(sl_sr, sl_atr)
        sl_pct = abs(price - sl) / price
        
        tp1_rr = price + (price - sl) * 2.0
        tp2_rr = price + (price - sl) * 3.0
        rr = round((tp1_rr - price) / (price - sl), 2) if (price - sl) > 0 else 0
        
        tp1_fixed = price * (1 + PROFIT_TARGET_FIXED)
        tp2_fixed = price * (1 + PROFIT_TARGET_FIXED * 2)
        rr_fixed = round(PROFIT_TARGET_FIXED / sl_pct, 2) if sl_pct > 0 else 0
        
        best_rr = max(rr, rr_fixed)
        best_tp1 = tp1_rr if rr >= rr_fixed else tp1_fixed
        best_tp2 = tp2_rr if rr >= rr_fixed else tp2_fixed
        
        if best_rr >= MIN_RR:
            risk_amount = 10000 * 0.02
            units = risk_amount / (price - sl) if (price - sl) > 0 else 0
            position = {
                "risk_usd": round(risk_amount, 2),
                "sl_dist": round(price - sl, 6),
                "units": round(units, 4),
                "position_usd": round(units * price, 2)
            }
            
            return AnalysisResult(
                symbol=symbol, timestamp=datetime.now().isoformat(),
                price=round(price, 6), entry=round(price, 6),
                sl=round(sl, 6), tp1=round(best_tp1, 6),
                tp2=round(best_tp2, 6),
                tp1_fixed=round(tp1_fixed, 6),
                tp2_fixed=round(tp2_fixed, 6),
                rr=best_rr, rr_fixed=rr_fixed,
                score=total_score, whale_score=whale_score,
                tech_score=tech_score, signal="شراء",
                trend=t1h, rsi=rsi,
                support=round(support, 6), resistance=round(resistance, 6),
                pattern=pattern, rsi_divergence=div["bullish"],
                bos_choch=bos["detail"] if bos["bos_bullish"] or bos["choch_bullish"] else "",
                position=position, details=details,
                timeframe_analysis={}
            )
    
    return AnalysisResult(
        symbol=symbol, timestamp=datetime.now().isoformat(),
        price=round(price, 6), entry=0, sl=0, tp1=0, tp2=0,
        tp1_fixed=0, tp2_fixed=0, rr=0, rr_fixed=0,
        score=total_score, whale_score=whale_score,
        tech_score=tech_score, signal="انتظار",
        trend=t1h, rsi=rsi,
        support=round(support, 6), resistance=round(resistance, 6),
        pattern=pattern, rsi_divergence=div["bullish"],
        bos_choch=bos["detail"] if bos["bos_bullish"] or bos["choch_bullish"] else "",
        position={}, details=details,
        timeframe_analysis={}
    )