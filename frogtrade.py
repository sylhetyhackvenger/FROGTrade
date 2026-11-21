import os, sys, time, shutil, re, math, random, csv, hashlib
from dataclasses import dataclass, field
from datetime import datetime, timezone

APP = "FROG TRADE"
AUTHOR = "SYLHETYHACKVENGER (THE-ERROR808)"
NOTICE = "WARNING: THIS IS AN EDUCATIONAL REALM FOR PRACTICING TRADING. NOTHING IS LIVE, EVERYTHING IS FICTIONAL."

HISTORY = int(os.getenv("HISTORY", "500"))
POLL_SECS = float(os.getenv("POLL_SECS", "0.25"))
START_BALANCE = 1000.0
PAYOUT = 0.92
BREAKEVEN = 100.0 / (1.0 + PAYOUT)
MIN_BARS = 120
DAILY_LIMIT = 10.0
MAX_OPEN = 2
SPEEDS = [1, 5, 15, 60]
JOURNAL = os.path.join(os.path.dirname(os.path.abspath(__file__)), "frogtrade_journal.csv")
JOURNAL_COLS = ["time", "source", "symbol", "tf", "dir", "stake", "entry", "exit", "result", "pnl"]

TIMEFRAMES = [("1m", 60), ("5m", 300), ("15m", 900), ("30m", 1800), ("1h", 3600), ("4h", 14400)]
HTF_MAP = {60: 300, 300: 900, 900: 3600, 1800: 14400, 3600: 14400, 14400: None}

FX_ALL = ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCAD", "USDCHF", "NZDUSD", "EURGBP", "EURJPY",
          "GBPJPY", "AUDJPY", "EURAUD", "EURCAD", "EURCHF", "EURNZD", "GBPAUD", "GBPCAD", "GBPCHF",
          "GBPNZD", "AUDCAD", "AUDCHF", "AUDNZD", "CADJPY", "CADCHF", "CHFJPY", "NZDJPY", "NZDCAD", "NZDCHF"]
CRYPTO = [(s + "USD", s) for s in ["BTC", "ETH", "LTC", "XRP", "BNB", "SOL", "DOGE", "ADA"]]
METALS = [("XAUUSD", "GOLD"), ("XAGUSD", "SILVER"), ("XPTUSD", "PLATINUM"),
          ("XPDUSD", "PALLADIUM"), ("USCRUDE", "WTI"), ("UKBRENT", "BRENT")]
STOCKS = [(s, s) for s in ["AAPL", "TSLA", "AMZN", "GOOGL", "MSFT", "META", "NFLX", "NVDA"]]
MARKETS = [
    ("Forex", [(p, p[:3] + "/" + p[3:]) for p in FX_ALL]),
    ("Crypto", CRYPTO),
    ("Metals & Energy", METALS),
    ("Stocks", STOCKS),
]
BASE = {"XAUUSD": 2350.0, "XAGUSD": 28.0, "XPTUSD": 980.0, "XPDUSD": 1000.0, "USCRUDE": 78.0, "UKBRENT": 82.0,
        "BTCUSD": 67000.0, "ETHUSD": 3200.0, "LTCUSD": 85.0, "XRPUSD": 0.55, "BNBUSD": 580.0, "SOLUSD": 160.0,
        "DOGEUSD": 0.15, "ADAUSD": 0.45, "AAPL": 190.0, "TSLA": 250.0, "AMZN": 180.0, "GOOGL": 170.0,
        "MSFT": 420.0, "META": 500.0, "NFLX": 650.0, "NVDA": 900.0}
CRYPTO_SET = {s for s, _ in CRYPTO}
METAL_SET = {s for s, _ in METALS}
STOCK_SET = {s for s, _ in STOCKS}


def profile(sym):
    h = int(hashlib.md5(sym.encode()).hexdigest()[:6], 16)
    if sym in BASE:
        base = BASE[sym]
    elif sym.endswith("JPY"):
        base = 95.0 + (h % 80)
    else:
        base = 0.62 + (h % 100) / 100.0
    if sym in CRYPTO_SET:
        vol = 0.0026
    elif sym in METAL_SET:
        vol = 0.0011
    elif sym in STOCK_SET:
        vol = 0.0017
    else:
        vol = 0.00045
    return base, vol


class C:
    R = "\033[0m"; B = "\033[1m"; D = "\033[2m"
    G = "\033[92m"; RD = "\033[91m"; Y = "\033[93m"; CY = "\033[96m"; M = "\033[95m"
    GR = "\033[90m"; W = "\033[97m"; BK = "\033[30m"
    BGG = "\033[42m"; BGR = "\033[41m"; BGY = "\033[43m"; BGM = "\033[45m"


if os.name == "nt":
    os.system("")


def term_size():
    s = shutil.get_terminal_size((100, 40))
    return min(s.columns, 120), s.lines


def clear():
    os.system("cls" if os.name == "nt" else "clear")


_ANSI = re.compile(r"(\033\[[0-9;?]*[A-Za-z])")


def vlen(s):
    return len(_ANSI.sub("", s))


def clip(s, n):
    out, cnt = [], 0
    for tok in _ANSI.split(s):
        if tok.startswith("\033["):
            out.append(tok)
            continue
        room = n - cnt
        if room > 0:
            out.append(tok[:room])
            cnt += min(len(tok), room)
    return "".join(out) + C.R


def read_line(p):
    try:
        return input(p).strip()
    except EOFError:
        return ""


def fmt_price(p):
    if p >= 1000:
        return "{:,.2f}".format(p)
    if p >= 100:
        return "{:.3f}".format(p)
    if p >= 10:
        return "{:.4f}".format(p)
    return "{:.5f}".format(p)


def fmt_t(t, tf, with_date=False):
    d = datetime.fromtimestamp(t)
    if with_date or tf >= 14400:
        return d.strftime("%d %H:%M")
    return d.strftime("%H:%M")


def mmss(sec):
    sec = max(0, int(sec))
    return "{:d}:{:02d}".format(sec // 60, sec % 60)


def money(x, sign=False):
    s = "{:,.2f}".format(abs(x))
    if x < 0:
        return "-$" + s
    return ("+$" if sign else "$") + s


def stamp(t):
    return datetime.fromtimestamp(t, timezone.utc).isoformat(timespec="seconds")


def journal(row):
    try:
        new = not os.path.exists(JOURNAL)
        with open(JOURNAL, "a", newline="") as f:
            w = csv.writer(f)
            if new:
                w.writerow(JOURNAL_COLS)
            w.writerow(row)
    except Exception:
        pass


@dataclass
class Candle:
    open: float
    high: float
    low: float
    close: float
    time: int


class SimFeed:
    TPC = 24

    def __init__(self, symbol, tf, speed=5, hist=HISTORY):
        self.symbol, self.tf, self.speed = symbol, tf, speed
        self.base_price, vol = profile(symbol)
        self.rng = random.Random()
        self.sig = self.base_price * vol * math.sqrt(tf / 60.0) / math.sqrt(self.TPC)
        self.price = self.base_price * self.rng.uniform(0.97, 1.03)
        self.regime, self.left, self.anchor, self.vm = "range", 0, self.price, 1.0
        self.dt = tf / float(self.TPC)
        self.base = time.time()
        self.real0 = self.base
        self.t0 = (int(self.base // tf) - hist) * tf
        self.n = 0
        self.candles = []
        self.err = ""
        self.last_ok = self.base
        self.frozen = None

    def clock(self):
        if self.frozen is not None:
            return self.frozen
        return self.base + (time.time() - self.real0) * self.speed

    def freeze(self):
        self.frozen = self.clock()

    def thaw(self):
        if self.frozen is not None:
            self.base = self.frozen
            self.real0 = time.time()
            self.frozen = None

    def set_speed(self, speed):
        self.base = self.clock()
        self.real0 = time.time()
        self.speed = speed

    @property
    def now(self):
        return self.clock()

    @property
    def last_price(self):
        return self.candles[-1].close if self.candles else self.price

    def _tick(self):
        if self.left <= 0:
            self.regime = self.rng.choices(("up", "down", "range"), (3, 3, 4))[0]
            self.left = self.rng.randint(60, 260)
            self.anchor = self.price
            self.vm = min(1.8, max(0.6, self.vm * self.rng.uniform(0.8, 1.25)))
        self.left -= 1
        s = self.sig * self.vm
        step = self.rng.gauss(0.0, s)
        if self.regime == "up":
            step += 0.05 * s
        elif self.regime == "down":
            step -= 0.05 * s
        else:
            step += 0.04 * (self.anchor - self.price)
        self.price = max(self.price + step, self.base_price * 0.05)

    def advance(self, target):
        n_target = int((target - self.t0) / self.dt)
        tf, dt, t0 = self.tf, self.dt, self.t0
        cs = self.candles
        while self.n < n_target:
            self.n += 1
            t = t0 + self.n * dt
            self._tick()
            p = self.price
            b = int((t - dt * 0.5) // tf) * tf
            c = cs[-1] if cs else None
            if c is None or c.time != b:
                o = c.close if c else p
                cs.append(Candle(o, max(o, p), min(o, p), p, b))
            else:
                if p > c.high:
                    c.high = p
                if p < c.low:
                    c.low = p
                c.close = p
        if len(cs) > 2600:
            del cs[:-2500]

    def refresh(self, full=False):
        self.advance(self.clock())
        self.last_ok = time.time()
        return True


def closed_candles(cs, tf, now=None):
    now = now or time.time()
    if cs and cs[-1].time + tf > now:
        return cs[:-1]
    return list(cs)


def ema_s(v, p):
    if not v:
        return []
    k = 2.0 / (p + 1)
    out = [v[0]]
    for x in v[1:]:
        out.append(x * k + out[-1] * (1 - k))
    return out


def rsi(cl, p=14):
    if len(cl) < p + 1:
        return 50.0
    ag = al = 0.0
    for i in range(1, p + 1):
        d = cl[i] - cl[i - 1]
        ag += max(d, 0)
        al += max(-d, 0)
    ag /= p
    al /= p
    for i in range(p + 1, len(cl)):
        d = cl[i] - cl[i - 1]
        ag = (ag * (p - 1) + max(d, 0)) / p
        al = (al * (p - 1) + max(-d, 0)) / p
    return 100.0 if al == 0 else 100 - 100 / (1 + ag / al)


def macd_hist(cl):
    e12, e26 = ema_s(cl, 12), ema_s(cl, 26)
    line = [a - b for a, b in zip(e12, e26)]
    sig = ema_s(line, 9)
    h = [a - b for a, b in zip(line, sig)]
    return (h[-1], h[-2]) if len(h) > 1 else (0.0, 0.0)


def atr_list(cs, p=14):
    trs = [max(cs[i].high - cs[i].low, abs(cs[i].high - cs[i - 1].close),
               abs(cs[i].low - cs[i - 1].close)) for i in range(1, len(cs))]
    out, s = [], 0.0
    for i, t in enumerate(trs):
        s += t
        if i >= p:
            s -= trs[i - p]
        if i >= p - 1:
            out.append(s / p)
    return out


def adx(cs, p=14):
    n = len(cs)
    if n < 2 * p + 2:
        return 0.0, 0.0, 0.0
    tr, pdm, mdm = [], [], []
    for i in range(1, n):
        up = cs[i].high - cs[i - 1].high
        dn = cs[i - 1].low - cs[i].low
        pdm.append(up if (up > dn and up > 0) else 0.0)
        mdm.append(dn if (dn > up and dn > 0) else 0.0)
        tr.append(max(cs[i].high - cs[i].low, abs(cs[i].high - cs[i - 1].close),
                      abs(cs[i].low - cs[i - 1].close)))
    st, sp, sm = sum(tr[:p]), sum(pdm[:p]), sum(mdm[:p])
    dxs, pdi, mdi = [], 0.0, 0.0
    for i in range(p, len(tr) + 1):
        if i > p:
            st = st - st / p + tr[i - 1]
            sp = sp - sp / p + pdm[i - 1]
            sm = sm - sm / p + mdm[i - 1]
        pdi = 100 * sp / st if st else 0.0
        mdi = 100 * sm / st if st else 0.0
        s = pdi + mdi
        dxs.append(100 * abs(pdi - mdi) / s if s else 0.0)
    if len(dxs) < p:
        return 0.0, pdi, mdi
    a = sum(dxs[:p]) / p
    for x in dxs[p:]:
        a = (a * (p - 1) + x) / p
    return a, pdi, mdi


def stoch(cs, p=14):
    raw = []
    for i in range(len(cs) - 8, len(cs)):
        w = cs[i - p + 1:i + 1]
        hh = max(c.high for c in w)
        ll = min(c.low for c in w)
        raw.append((cs[i].close - ll) / (hh - ll) * 100 if hh > ll else 50.0)
    k = [sum(raw[i - 2:i + 1]) / 3 for i in range(2, len(raw))]
    d = [sum(k[i - 2:i + 1]) / 3 for i in range(2, len(k))]
    return k[-1], d[-1], k[-2], d[-2]


def pct_b(cl, p=20):
    w = cl[-p:]
    m = sum(w) / p
    sd = math.sqrt(sum((x - m) ** 2 for x in w) / p)
    if sd == 0:
        return 0.5
    lo, hi = m - 2 * sd, m + 2 * sd
    return (cl[-1] - lo) / (hi - lo)


def candle_pattern(cs, atr_v):
    c, p = cs[-1], cs[-2]
    body = abs(c.close - c.open)
    rng = c.high - c.low
    if rng <= 0:
        return 0, ""
    uw = c.high - max(c.open, c.close)
    lw = min(c.open, c.close) - c.low
    if p.close < p.open and c.close > c.open and c.close >= p.open and c.open <= p.close and body > 0.6 * atr_v:
        return 1, "bull engulfing"
    if p.close > p.open and c.close < c.open and c.close <= p.open and c.open >= p.close and body > 0.6 * atr_v:
        return -1, "bear engulfing"
    if lw >= 2 * max(body, 1e-12) and lw > 0.6 * rng and uw < 0.2 * rng:
        return 1, "hammer"
    if uw >= 2 * max(body, 1e-12) and uw > 0.6 * rng and lw < 0.2 * rng:
        return -1, "shooting star"
    return 0, ""


def sr_vote(cs, atr_v, look=100, w=3):
    seg = cs[-look:]
    price = seg[-1].close
    highs, lows = [], []
    for i in range(w, len(seg) - w):
        if all(seg[i].high >= seg[j].high for j in range(i - w, i + w + 1)):
            highs.append(seg[i].high)
        if all(seg[i].low <= seg[j].low for j in range(i - w, i + w + 1)):
            lows.append(seg[i].low)
    tol = 0.5 * atr_v
    res = any(-0.2 * atr_v <= r - price <= tol for r in highs)
    sup = any(-0.2 * atr_v <= price - s <= tol for s in lows)
    if sup and not res:
        return 1.0, "at support"
    if res and not sup:
        return -1.0, "at resistance"
    return 0.0, ""


def resample(cs, tf, htf):
    out, cur = [], None
    for c in cs:
        b = c.time // htf * htf
        if cur is None or cur.time != b:
            if cur is not None:
                out.append(cur)
            cur = Candle(c.open, c.high, c.low, c.close, b)
        else:
            cur.high = max(cur.high, c.high)
            cur.low = min(cur.low, c.low)
            cur.close = c.close
    if cur is not None:
        out.append(cur)
    if out and cs and out[-1].time + htf > cs[-1].time + tf:
        out.pop()
    return out


def htf_bias(cs, tf):
    htf = HTF_MAP.get(tf)
    if not htf:
        return 0, None
    h = resample(cs, tf, htf)
    if len(h) < 55:
        return 0, htf
    cl = [c.close for c in h]
    e20, e50 = ema_s(cl, 20)[-1], ema_s(cl, 50)[-1]
    if e20 > e50 and cl[-1] > e20:
        return 1, htf
    if e20 < e50 and cl[-1] < e20:
        return -1, htf
    return 0, htf


@dataclass
class Analysis:
    verdict: str = "WAIT"
    score: float = 0.0
    confluence: int = 0
    regime: str = "-"
    votes: list = field(default_factory=list)
    blockers: list = field(default_factory=list)
    adx: float = 0.0
    atr_ratio: float = 1.0
    rsi: float = 50.0
    htf: int = 0
    htf_tf: object = None
    note: str = ""
    time: int = 0
    price: float = 0.0


THRESH = {"TREND": 0.40, "MIXED": 0.50, "RANGE": 0.45}


def analyze(closed, tf):
    an = Analysis()
    if len(closed) < MIN_BARS:
        an.blockers = ["need {} closed candles (have {})".format(MIN_BARS, len(closed))]
        return an
    cs = closed
    cl = [c.close for c in cs]
    price = cl[-1]
    an.time, an.price = cs[-1].time, price
    al = atr_list(cs)
    atr_v = al[-1] or 1e-12
    med = sorted(al[-100:])[len(al[-100:]) // 2] or 1e-12
    an.atr_ratio = atr_v / med
    adx_v, pdi, mdi = adx(cs)
    an.adx = adx_v
    r = rsi(cl)
    an.rsi = r
    hist, hist_p = macd_hist(cl)
    k, d, kp, dp = stoch(cs)
    pb = pct_b(cl)
    e20, e50 = ema_s(cl, 20)[-1], ema_s(cl, 50)[-1]
    pat, pat_name = candle_pattern(cs, atr_v)
    sr, sr_name = sr_vote(cs, atr_v)
    hb, htf = htf_bias(cs, tf)
    an.htf, an.htf_tf = hb, htf

    an.regime = "TREND" if adx_v >= 25 else "RANGE" if adx_v <= 20 else "MIXED"
    V = []
    if an.regime == "RANGE":
        V.append(("BB", 1 if pb <= .05 else .5 if pb <= .2 else -1 if pb >= .95 else -.5 if pb >= .8 else 0, 3))
        V.append(("RSI", 1 if r <= 30 else .4 if r <= 40 else -1 if r >= 70 else -.4 if r >= 60 else 0, 2.5))
        V.append(("STO", 1 if (k < 20 and k >= d) else .4 if k < 20 else -1 if (k > 80 and k <= d) else -.4 if k > 80 else 0, 2))
        V.append(("PAT", pat, 2))
        V.append(("S/R", sr, 2))
        V.append(("HTF", hb, 1))
    else:
        if e20 > e50:
            ev = 1 if price > e20 else .5 if price > e50 else 0
        else:
            ev = -1 if price < e20 else -.5 if price < e50 else 0
        V.append(("EMA", ev, 3))
        V.append(("DI", 1 if pdi > mdi else -1, 1.5))
        V.append(("MACD", 1 if (hist > 0 and hist > hist_p) else .4 if hist > 0 else
                  -1 if (hist < 0 and hist < hist_p) else -.4, 2))
        V.append(("RSI", .6 if 50 < r <= 68 else -.2 if r > 68 else -.6 if 32 <= r <= 50 else .2, 1.5))
        cross_up = k > d and kp <= dp
        cross_dn = k < d and kp >= dp
        V.append(("STO", 1 if (cross_up and k < 80) else .4 if (k > d and k < 80) else
                  -1 if (cross_dn and k > 20) else -.4 if (k < d and k > 20) else 0, 1.5))
        V.append(("PAT", pat, 1.5))
        V.append(("S/R", sr, 1.5))
        V.append(("HTF", hb, 3))

    tw = sum(w for _, _, w in V)
    score = sum(v * w for _, v, w in V) / tw
    an.score = round(score, 4)
    an.votes = [(t, v) for t, v, _ in V]
    an.confluence = int(min(100, abs(score) / 0.8 * 100))
    an.note = ", ".join(x for x in (pat_name, sr_name) if x)

    dirn = 1 if score > 0 else -1
    agree = sum(1 for _, v, _ in V if v * dirn >= .4)
    strong_opp = [t for t, v, _ in V if v * dirn <= -.7]
    B = an.blockers
    if abs(score) < THRESH[an.regime]:
        B.append("score {:+.2f} below {:.2f} ({})".format(score, THRESH[an.regime], an.regime))
    if agree < 4:
        B.append("only {} indicators agree (need 4)".format(agree))
    if strong_opp:
        B.append("strong disagreement: " + "/".join(strong_opp))
    if hb != 0 and hb == -dirn:
        B.append("higher timeframe is against it")
    if an.atr_ratio < 0.5:
        B.append("market too quiet")
    if an.atr_ratio > 2.2:
        B.append("volatility spike")
    if (cs[-1].high - cs[-1].low) > 3 * atr_v:
        B.append("spike candle")
    if (dirn == 1 and r > 75) or (dirn == -1 and r < 25):
        B.append("overextended (RSI {:.0f})".format(r))
    an.verdict = "WAIT" if B else ("BUY" if dirn == 1 else "SELL")
    return an


def wilson(w, n, z=1.96):
    if n == 0:
        return 0.0, 100.0
    p = w / n
    dd = 1 + z * z / n
    c = p + z * z / (2 * n)
    m = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return (c - m) / dd * 100, (c + m) / dd * 100


class Tracker:
    def __init__(self, symbol, tf):
        self.symbol, self.tf = symbol, tf
        self.sigs = {}
        self.w = self.l = self.d = 0

    def add(self, an):
        if an.time in self.sigs:
            return
        self.sigs[an.time] = {"dir": an.verdict, "entry_t": an.time + self.tf, "result": None, "price": an.price}

    def settle(self, cs, now):
        by = {c.time: c for c in cs}
        for s in self.sigs.values():
            if s["result"]:
                continue
            c = by.get(s["entry_t"])
            if c is None or c.time + self.tf > now:
                continue
            up = c.close > c.open
            dn = c.close < c.open
            win = (up and s["dir"] == "BUY") or (dn and s["dir"] == "SELL")
            s["result"] = "WIN" if win else ("DRAW" if not (up or dn) else "LOSS")
            if s["result"] == "WIN":
                self.w += 1
            elif s["result"] == "LOSS":
                self.l += 1
            else:
                self.d += 1
            journal([stamp(s["entry_t"]), "signal", self.symbol, self.tf, s["dir"], "", c.open, c.close, s["result"], ""])

    def marks(self):
        return {s["entry_t"]: (s["dir"], s["result"]) for s in self.sigs.values()}


def backtest(candles, tf, now, bars=450):
    closed = closed_candles(candles, tf, now)
    start = max(MIN_BARS, len(closed) - bars - 1)
    w = l = d = 0
    for i in range(start, len(closed) - 1):
        an = analyze(closed[:i + 1], tf)
        if an.verdict == "WAIT":
            continue
        nx = closed[i + 1]
        if nx.close == nx.open:
            d += 1
        elif (nx.close > nx.open) == (an.verdict == "BUY"):
            w += 1
        else:
            l += 1
    n = w + l
    wr = w / n * 100 if n else 0.0
    lo, hi = wilson(w, n)
    return {"w": w, "l": l, "d": d, "n": n, "wr": wr, "lo": lo, "hi": hi,
            "span": len(closed) - start - 1, "net": w * PAYOUT - l}


class Account:
    def __init__(self):
        self.balance = START_BALANCE
        self.day_start = START_BALANCE
        self.risk = 2.0
        self.expiry = 1
        self.auto = False
        self.speed_idx = 1
        self.open = []
        self.closed = []
        self.peak = START_BALANCE
        self.max_dd = 0.0
        self.streak = 0
        self.cool_until = 0.0

    def equity(self):
        return self.balance + sum(t["stake"] for t in self.open)

    def stake(self):
        return max(1.0, round(self.balance * self.risk / 100.0, 2))

    def halted(self):
        return self.day_start - self.equity() >= self.day_start * DAILY_LIMIT / 100.0

    def blocked(self, now):
        if self.halted():
            return "RISK GUARD: daily loss limit reached. Stop, review the journal (l), come back fresh."
        if now < self.cool_until:
            return "Cool-down after 3 losses in a row: {} left. Reset your head.".format(mmss(self.cool_until - now))
        if len(self.open) >= MAX_OPEN:
            return "Max {} open trades. A frog strikes once, then waits.".format(MAX_OPEN)
        if self.stake() > self.balance:
            return "Not enough balance for this stake."
        return ""

    def open_trade(self, sym, tf, direction, price, now, t1, src):
        s = self.stake()
        self.balance = round(self.balance - s, 2)
        t = {"sym": sym, "tf": tf, "dir": direction, "stake": s, "entry": price, "t0": now, "t1": t1,
             "src": src, "result": None, "pnl": 0.0, "exit": None}
        self.open.append(t)
        return t

    def cashout_value(self, t, price, now):
        span = max(1.0, t["t1"] - t["t0"])
        prog = min(1.0, max(0.0, (now - t["t0"]) / span))
        if price == t["entry"]:
            return round(t["stake"] * 0.9, 2)
        win = price > t["entry"] if t["dir"] == "BUY" else price < t["entry"]
        if win:
            return round(t["stake"] * (1 + PAYOUT * (0.35 + 0.45 * prog)), 2)
        return round(t["stake"] * (0.55 - 0.35 * prog), 2)

    def _finish(self, t, price, now, result, pay):
        self.open.remove(t)
        self.balance = round(self.balance + pay, 2)
        t["result"], t["exit"], t["pnl"], t["t_end"] = result, price, round(pay - t["stake"], 2), now
        if t["pnl"] > 0:
            self.streak = max(1, self.streak + 1)
        elif t["pnl"] < 0:
            self.streak = min(-1, self.streak - 1)
            if self.streak <= -3:
                self.cool_until = now + 3 * t["tf"]
                self.streak = 0
        eq = self.equity()
        self.peak = max(self.peak, eq)
        if self.peak > 0:
            self.max_dd = max(self.max_dd, (self.peak - eq) / self.peak * 100)
        self.closed.append(t)
        journal([stamp(now), t["src"], t["sym"], t["tf"], t["dir"], t["stake"], t["entry"], price, result, t["pnl"]])

    def settle(self, price, now):
        done = []
        for t in self.open[:]:
            if now >= t["t1"]:
                if price == t["entry"]:
                    res, pay = "DRAW", t["stake"]
                elif (price > t["entry"]) == (t["dir"] == "BUY"):
                    res, pay = "WIN", t["stake"] * (1 + PAYOUT)
                else:
                    res, pay = "LOSS", 0.0
                self._finish(t, price, now, res, pay)
                done.append(t)
        return done

    def cash_out(self, t, price, now):
        pay = self.cashout_value(t, price, now)
        self._finish(t, price, now, "CASH", pay)
        return t["pnl"]

    def stats(self):
        cl = self.closed
        wins = [t["pnl"] for t in cl if t["pnl"] > 0]
        loss = [t["pnl"] for t in cl if t["pnl"] < 0]
        n = len(wins) + len(loss)
        lo, hi = wilson(len(wins), n)
        net = sum(t["pnl"] for t in cl)
        return {"n": len(cl), "w": len(wins), "l": len(loss), "d": len(cl) - n, "net": net,
                "wr": len(wins) / n * 100 if n else 0.0, "aw": sum(wins) / len(wins) if wins else 0.0,
                "al": sum(loss) / len(loss) if loss else 0.0, "exp": net / len(cl) if cl else 0.0,
                "lo": lo, "hi": hi}


CELL = {(0, 0): " ", (1, 1): "│", (1, 0): "╵", (0, 1): "╷", (2, 2): "█", (2, 0): "▀", (0, 2): "▄",
        (2, 1): "▀", (1, 2): "▄"}


def render_chart(view, tf, rows, bw, marks, last_price, gutter):
    n = len(view)
    sub = rows * 2
    lo = min(c.low for c in view)
    hi = max(c.high for c in view)
    pad = (hi - lo) * 0.05 or abs(hi) * 1e-4 + 1e-9
    lo -= pad
    hi += pad

    def sy(p):
        return max(0, min(sub - 1, int((hi - p) / (hi - lo) * (sub - 1) + 0.5)))
    cols = []
    for c in view:
        st = [0] * sub
        yh, yl, yo, yc = sy(c.high), sy(c.low), sy(c.open), sy(c.close)
        for y in range(yh, yl + 1):
            st[y] = 1
        for y in range(min(yo, yc), max(yo, yc) + 1):
            st[y] = 2
        cols.append((st, C.G if c.close >= c.open else C.RD))
    ry = sy(last_price) // 2 if last_price is not None else -1
    out = []
    for r in range(rows):
        parts = []
        for st, col in cols:
            ch = CELL[(st[2 * r], st[2 * r + 1])]
            parts.append((col + ch + C.R if ch != " " else " ") + " " * (bw - 1))
        price = hi - (r / max(1, rows - 1)) * (hi - lo)
        lbl = fmt_price(price) if r in (0, rows // 2, rows - 1) else ""
        row = "{}{:>9}{} │".format(C.GR, lbl, C.R) + "".join(parts)
        if gutter and r == ry:
            row += "{}{} ◄ {}{}".format(C.B, C.Y, fmt_price(last_price), C.R)
        out.append(row)
    mk = []
    for c in view:
        m = marks.get(c.time)
        if m:
            col = C.Y if m[1] is None else C.G if m[1] == "WIN" else C.RD if m[1] == "LOSS" else C.GR
            mk.append(col + ("▲" if m[0] == "BUY" else "▼") + C.R + " " * (bw - 1))
        else:
            mk.append(" " * bw)
    out.append(" " * 9 + C.GR + " │" + C.R + "".join(mk))
    width = n * bw
    ax = [" "] * width
    multi = datetime.fromtimestamp(view[0].time).date() != datetime.fromtimestamp(view[-1].time).date()

    def put(pos, text):
        pos = max(0, min(width - len(text), pos))
        for i, ch in enumerate(text):
            ax[pos + i] = ch
    put(0, fmt_t(view[0].time, tf, multi))
    if width >= 40:
        put(width // 2 - 3, fmt_t(view[n // 2].time, tf, multi))
    if width >= 20:
        put(width - 6, fmt_t(view[-1].time, tf, multi))
    out.append(" " * 9 + C.GR + " └" + "".join(ax) + C.R)
    return out


@dataclass
class View:
    m_idx: int
    tf_idx: int
    i_idx: int
    offset: int = 0
    bw: int = 2
    nbars: int = 60
    an: object = None
    an_T: int = 0
    locked: dict = field(default_factory=dict)
    tracker: object = None
    bt: object = None
    msg: str = ""
    msg_t: float = 0.0


def note(st, text):
    st.msg = text
    st.msg_t = time.time()


def bar(pct, width=16):
    f = int(pct / 100 * width)
    col = C.G if pct >= 60 else C.Y if pct >= 35 else C.RD
    return "{}{}{}{}{} {:>3d}%".format(col, "█" * f, C.GR, "░" * (width - f), C.R, int(pct))


def render(st, feed, acct):
    W, H = term_size()
    now = feed.clock()
    tf = feed.tf
    name, items = MARKETS[st.m_idx]
    sym, lbl = items[st.i_idx]
    tfl = TIMEFRAMES[st.tf_idx][0]
    cs = feed.candles
    L = []
    clock_s = datetime.fromtimestamp(now).strftime("%H:%M:%S")
    L.append("{}{}◆ FROG TRADE{}  {}{}● RUNNING{} {}x{}  {}{}".format(
        C.B, C.G, C.R, C.B, C.G, C.R, C.D, feed.speed, clock_s, C.R))
    last = cs[-1]
    prev = cs[-2].close if len(cs) > 1 else last.open
    chg = (last.close - prev) / prev * 100 if prev else 0
    pc = C.G if chg >= 0 else C.RD
    L.append("{}{}{} {}{} · {}{}   {}{}{} {}{} {:+.3f}%{}".format(
        C.B, C.CY, lbl, C.R, C.D + name, tfl, C.R, C.B, fmt_price(last.close), C.R,
        pc, "▲" if chg >= 0 else "▼", chg, C.R))

    gutter = 11 if W >= 64 else 0
    avail = W - 12 - gutter
    st.nbars = max(10, avail // st.bw)
    st.offset = max(0, min(st.offset, max(0, len(cs) - st.nbars)))
    end = len(cs) - st.offset
    view = cs[max(0, end - st.nbars):end]
    rows = max(6, min(16, H - 24))
    L += render_chart(view, tf, rows, st.bw, st.tracker.marks(), last.close if st.offset == 0 else None, gutter)
    if st.offset == 0:
        L.append("  {}● live edge{}  {}◀ ▶ scroll · +/- zoom{}   candle closes in {}{}{}".format(
            C.G, C.R, C.D, C.R, C.B, mmss(last.time + tf - now), C.R))
    else:
        L.append("  {}{}◀ HISTORY — {} bars back{} {}(press g for live){}".format(
            C.BGY, C.BK, st.offset, C.R, C.D, C.R))

    an = st.an
    closed = closed_candles(cs, tf, now)
    L.append(C.GR + "─" * W + C.R)
    if an is None or not closed:
        L.append("  {}collecting candles…{}".format(C.D, C.R))
    else:
        if an.verdict == "BUY":
            badge = "{}{}{} ▲ BUY / CALL {}".format(C.BGG, C.BK, C.B, C.R)
        elif an.verdict == "SELL":
            badge = "{}{}{} ▼ SELL / PUT {}".format(C.BGR, C.W, C.B, C.R)
        else:
            badge = "{}{}{} ● WAIT — NO TRADE {}".format(C.BGY, C.BK, C.B, C.R)
        extra = ""
        if an.verdict != "WAIT" and an.time == closed[-1].time:
            el = now - (an.time + tf)
            window = min(tf * 0.5, max(min(15.0, tf * 0.25), 8.0 * feed.speed))
            if el > window:
                extra = "{}LATE ({:.0f}s in) — skip, edge decays{}".format(C.Y, el, C.R)
            else:
                extra = "{}{}ENTER NOW{}  hold {}×{}".format(C.B, C.G, C.R, acct.expiry, tfl)
        L.append("  {}  {}".format(badge, extra))
        hb = {1: "{}▲{}".format(C.G, C.R), -1: "{}▼{}".format(C.RD, C.R), 0: "{}–{}".format(C.GR, C.R)}[an.htf]
        htf_s = TIMEFRAMES[[t for _, t in TIMEFRAMES].index(an.htf_tf)][0] if an.htf_tf else "n/a"
        L.append("  confluence {}   {}{}{}".format(bar(an.confluence), C.D, "score {:+.2f}".format(an.score), C.R))
        L.append("  {}regime{} {} ADX {:.0f} · {}vol{} x{:.1f} · {}HTF {}{} {} · {}RSI{} {:.0f}".format(
            C.D, C.R, an.regime, an.adx, C.D, C.R, an.atr_ratio, C.D, htf_s, C.R, hb, C.D, C.R, an.rsi))
        vs = []
        for t, v in an.votes:
            col = C.G if v >= .4 else C.RD if v <= -.4 else C.GR
            vs.append("{}{}{}{}".format(col, t, "▲" if v >= .4 else "▼" if v <= -.4 else "–", C.R))
        L.append("  " + "  ".join(vs) + ("   {}{}{}".format(C.CY, an.note, C.R) if an.note else ""))
        stake = acct.stake()
        if an.verdict == "WAIT" and an.blockers:
            L.append("  {}coach:{} {} — no setup, no trade. Waiting is a position.".format(C.Y, C.R, an.blockers[0]))
        elif an.verdict != "WAIT":
            L.append("  {}coach:{} stake {} → win {} / lose {} · you need {:.1f}% wins to break even.".format(
                C.Y, C.R, money(stake), money(stake * PAYOUT, True), money(-stake), BREAKEVEN))

    eq = acct.equity()
    day = eq - acct.day_start
    dc = C.G if day >= 0 else C.RD
    L.append("  {}balance{} {}{}{}  {}equity{} {}  {}day{} {}{}{} {}(limit -{:.0f}%){}".format(
        C.D, C.R, C.B, money(acct.balance), C.R, C.D, C.R, money(eq), C.D, C.R, dc, money(day, True), C.R,
        C.D, DAILY_LIMIT, C.R))
    guard = ""
    why = acct.blocked(now)
    if acct.halted():
        guard = "{}{} RISK GUARD: HALTED {}".format(C.BGR, C.W, C.R)
    elif now < acct.cool_until:
        guard = "{}{} COOL-DOWN {} {}{}".format(C.BGY, C.BK, mmss(acct.cool_until - now), C.R, "")
    L.append("  {}risk{} {:.1f}% → stake {}{}{}  {}hold{} {}×{}  {}auto{} {}  {}".format(
        C.D, C.R, acct.risk, C.B, money(acct.stake()), C.R, C.D, C.R, acct.expiry, tfl, C.D, C.R,
        "{}{}ON{}".format(C.B, C.G, C.R) if acct.auto else "{}off{}".format(C.GR, C.R), guard))
    tr = st.tracker
    n = tr.w + tr.l
    if n:
        wr = tr.w / n * 100
        col = C.G if wr >= BREAKEVEN else C.RD
        L.append("  {}signals{} {}W {} / L {} / D {}{}  {}{:.0f}%{} {}(need {:.1f}% · net {:+.2f}u){}".format(
            C.D, C.R, C.B, tr.w, tr.l, tr.d, C.R, col, wr, C.R, C.D, BREAKEVEN, tr.w * PAYOUT - tr.l, C.R))
    else:
        L.append("  {}signals: none settled yet (each one is auto-scored){}".format(C.D, C.R))
    if st.bt:
        b = st.bt
        ok = b["lo"] > BREAKEVEN
        L.append("  {}backtest{} {} trades in {} bars · {}{:.1f}%{} (95% range {:.0f}–{:.0f}%) · {}".format(
            C.D, C.R, b["n"], b["span"], C.G if b["wr"] >= BREAKEVEN else C.RD, b["wr"], C.R, b["lo"], b["hi"],
            "{}edge likely{}".format(C.G, C.R) if ok else "{}edge NOT proven{}".format(C.Y, C.R)))
    price = feed.last_price
    for t in acct.open:
        win = price > t["entry"] if t["dir"] == "BUY" else price < t["entry"]
        flat = price == t["entry"]
        col = C.GR if flat else C.G if win else C.RD
        L.append("  {}{}{} {} {} @ {}  {}{}{}  {} left · cash-out {}{}{} (k)".format(
            col, "▲" if t["dir"] == "BUY" else "▼", C.R, "CALL" if t["dir"] == "BUY" else "PUT", money(t["stake"]),
            fmt_price(t["entry"]), col, "FLAT" if flat else "IN PROFIT" if win else "UNDER WATER", C.R,
            mmss(t["t1"] - now), C.B, money(acct.cashout_value(t, price, now)), C.R))
    if st.msg and time.time() - st.msg_t < 7:
        L.append("  " + st.msg)
    L.append(C.GR + "─" * W + C.R)
    L.append("{}u CALL  p PUT  k cash-out  x auto  [ ] risk  e hold  v speed  m mentor  l journal  b backtest{}".format(C.D, C.R))
    L.append("{}◀▶/a d scroll  g live  +/- zoom  s scan  i instr  t tf  c change  q quit{}".format(C.D, C.R))
    sys.stdout.write("\033[H" + "".join(clip(l, W) + "\033[K\n" for l in L[:H - 1]) + "\033[J")
    sys.stdout.flush()


class Keys:
    SEQ = {"[A": "up", "[B": "down", "[C": "right", "[D": "left", "[5~": "pgup", "[6~": "pgdn",
           "[H": "home", "[F": "end", "[1~": "home", "[4~": "end", "OA": "up", "OB": "down",
           "OC": "right", "OD": "left"}

    def __enter__(self):
        if os.name != "nt":
            import termios, tty
            self.fd = sys.stdin.fileno()
            self.old = termios.tcgetattr(self.fd)
            tty.setcbreak(self.fd)
        return self

    def __exit__(self, *a):
        if os.name != "nt":
            import termios
            termios.tcsetattr(self.fd, termios.TCSADRAIN, self.old)

    def suspend(self):
        if os.name != "nt":
            import termios
            termios.tcsetattr(self.fd, termios.TCSADRAIN, self.old)
        sys.stdout.write("\033[?25h\033[0m")
        sys.stdout.flush()

    def resume(self):
        if os.name != "nt":
            import tty
            tty.setcbreak(self.fd)
        sys.stdout.write("\033[?25l\033[2J")
        sys.stdout.flush()

    def get(self, timeout):
        if os.name == "nt":
            import msvcrt
            end = time.time() + timeout
            while time.time() < end:
                if msvcrt.kbhit():
                    ch = msvcrt.getwch()
                    if ch in ("\x00", "\xe0"):
                        return {"H": "up", "P": "down", "K": "left", "M": "right", "I": "pgup",
                                "Q": "pgdn", "G": "home", "O": "end"}.get(msvcrt.getwch(), "")
                    return self._norm(ch)
                time.sleep(0.02)
            return None
        import select
        r, _, _ = select.select([sys.stdin], [], [], timeout)
        if not r:
            return None
        data = os.read(self.fd, 8).decode(errors="ignore")
        if data.startswith("\x1b"):
            return self.SEQ.get(data[1:], "")
        return self._norm(data[:1])

    @staticmethod
    def _norm(ch):
        if ch in ("\r", "\n"):
            return "enter"
        if ch == "\x03":
            return "quit"
        return ch.lower()


def lerp(a, b, t):
    return a + (b - a) * t


def clamp(x, a=0.0, b=1.0):
    return a if x < a else b if x > b else x


def smooth(x):
    x = clamp(x)
    return x * x * (3.0 - 2.0 * x)


def ramp(t, a, b):
    return smooth((t - a) / (b - a))


def kf(table, t):
    if t <= table[0][0]:
        return table[0][1]
    for i in range(1, len(table)):
        if t <= table[i][0]:
            t0, v0 = table[i - 1]
            t1, v1 = table[i]
            return v0 if t1 == t0 else lerp(v0, v1, smooth((t - t0) / (t1 - t0)))
    return table[-1][1]


def hnoise(x, y, s=0):
    n = (int(x) * 374761393 + int(y) * 668265263 + s * 982451653) & 0xFFFFFFFF
    n = ((n ^ (n >> 13)) * 1274126177) & 0xFFFFFFFF
    return ((n ^ (n >> 16)) & 0xFFFF) / 65535.0


def mix(a, b, t):
    return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, a[2] + (b[2] - a[2]) * t)


def grad(stops, t):
    t = clamp(t)
    for i in range(1, len(stops)):
        if t <= stops[i][0]:
            t0, c0 = stops[i - 1]
            t1, c1 = stops[i]
            return mix(c0, c1, (t - t0) / (t1 - t0) if t1 > t0 else 0.0)
    return stops[-1][1]


def norm_ang(a):
    while a > math.pi:
        a -= 2 * math.pi
    while a < -math.pi:
        a += 2 * math.pi
    return a


SKY = [(0.0, (10, 16, 44)), (0.45, (66, 50, 104)), (0.75, (200, 98, 110)), (1.0, (255, 160, 96))]
MEADOW = [(0.0, (104, 124, 98)), (0.5, (54, 106, 62)), (1.0, (34, 82, 44))]
SOIL = [(0.0, (98, 72, 46)), (1.0, (28, 20, 18))]
WATER = [(0.0, (150, 120, 110)), (0.08, (44, 124, 134)), (0.35, (16, 72, 98)), (1.0, (6, 22, 44))]

CROUCH = [(0, 0.1), (0.8, 0.1), (1.0, 1.0), (1.03, 0.0), (1.4, 0.0), (1.47, 0.9), (1.66, 0.25), (1.8, 1.0),
          (1.83, 0.0), (2.12, 0.0), (2.2, 0.9), (2.38, 0.55), (2.55, 0.95), (2.9, 0.45), (3.7, 0.3),
          (3.85, 0.9), (4.2, 1.0), (4.24, 0.0), (9.0, 0.0)]
MOUTH = [(0, 0.0), (2.3, 0.0), (2.4, 1.0), (2.66, 1.0), (2.85, 0.0), (9.0, 0.0)]
TONGUE = [(0, 0.0), (2.4, 0.0), (2.55, 1.0), (2.66, 1.0), (2.9, 0.0), (9.0, 0.0)]
EYE = [(0, 1.0), (2.95, 1.0), (3.05, 0.1), (3.3, 0.1), (3.45, 1.0), (9.0, 1.0)]

DURATION = 6.0


class Canvas:
    def __init__(self, w, h):
        self.w, self.h = w, h
        self.px = [(0.0, 0.0, 0.0)] * (w * h)

    def put(self, x, y, c, a=1.0):
        if 0 <= x < self.w and 0 <= y < self.h:
            i = y * self.w + x
            if a >= 0.999:
                self.px[i] = c
            elif a > 0.0:
                o = self.px[i]
                self.px[i] = (o[0] + (c[0] - o[0]) * a, o[1] + (c[1] - o[1]) * a, o[2] + (c[2] - o[2]) * a)

    def ellipse(self, cx, cy, rx, ry, col, rot=0.0, alpha=1.0, tex=0.0, spec=0.0, flat=False):
        if rx < 0.3 or ry < 0.3:
            return
        cr, sr = math.cos(rot), math.sin(rot)
        R = max(rx, ry) + 1
        x0 = max(0, int(cx - R))
        x1 = min(self.w - 1, int(cx + R) + 1)
        y0 = max(0, int(cy - R))
        y1 = min(self.h - 1, int(cy + R) + 1)
        mn = min(rx, ry)
        for y in range(y0, y1 + 1):
            dy = y + 0.5 - cy
            for x in range(x0, x1 + 1):
                dx = x + 0.5 - cx
                u = dx * cr + dy * sr
                v = -dx * sr + dy * cr
                nx = u / rx
                ny = v / ry
                d = nx * nx + ny * ny
                if d >= 1.0:
                    continue
                rt = math.sqrt(d)
                cov = min(1.0, (1.0 - rt) * mn * 1.5)
                if flat:
                    m, sp = 1.0, 0.0
                else:
                    nz = math.sqrt(1.0 - d)
                    wx = nx * cr - ny * sr
                    wy = nx * sr + ny * cr
                    df = -0.45 * wx - 0.55 * wy + 0.7 * nz
                    df = 0.0 if df < 0 else df if df < 1 else 1.0
                    m = 0.38 + 0.8 * df
                    sp = spec * (df ** 18) * 255.0 if spec else 0.0
                if tex:
                    m *= 1.0 + tex * (hnoise(x, y, 17) - 0.5)
                self.put(x, y, (col[0] * m + sp, col[1] * m + sp, col[2] * m + sp), cov * alpha)

    def disc(self, cx, cy, r, col, alpha=1.0):
        r = max(r, 0.5)
        for y in range(int(cy - r - 1), int(cy + r) + 2):
            for x in range(int(cx - r - 1), int(cx + r) + 2):
                d = math.hypot(x + 0.5 - cx, y + 0.5 - cy)
                if d <= r:
                    self.put(x, y, col, alpha * clamp(r - d + 0.5))

    def seg(self, x0, y0, x1, y1, w, col, alpha=1.0):
        d = math.hypot(x1 - x0, y1 - y0)
        n = max(1, int(d * 2))
        for i in range(n + 1):
            t = i / n
            self.disc(x0 + (x1 - x0) * t, y0 + (y1 - y0) * t, w / 2.0, col, alpha)

    def ring(self, cx, cy, rx, ry, col, alpha, xmin):
        if rx < 1:
            return
        for i in range(-int(rx), int(rx) + 1):
            xx = int(cx + i)
            if xx < xmin or xx >= self.w:
                continue
            k = 1 - (i / rx) ** 2
            if k < 0:
                continue
            dy = ry * math.sqrt(k)
            self.put(xx, int(cy - dy), col, alpha)
            self.put(xx, int(cy + dy), col, alpha * 0.6)


class Scene:
    def __init__(self, W, H):
        self.W, self.H = W, H
        self.S = clamp(min(W / 100.0, H / 56.0), 0.6, 1.25)
        self.hz = int(H * 0.46)
        self.yg = int(H * 0.72)
        self.yw = int(H * 0.79)
        self.ex = int(W * 0.66)
        self.rng = random.Random(7)
        self.bg = self._build()
        self._extras()
        self.vig = [max(0.0, 1.0 - 0.62 * (((x - W / 2.0) / (W / 2.0)) ** 2 + ((y - H / 2.0) / (H / 2.0)) ** 2))
                    for y in range(H) for x in range(W)]
        gr = random.Random(3)
        self.grain = [[gr.uniform(-0.035, 0.035) for _ in range(W * H)] for _ in range(3)]
        self.water = [(y * W + x, self.bg[y * W + x]) for y in range(self.yw, H)
                      for x in range(W) if self.is_water(x, y)]
        self.fire = [(self.rng.uniform(0.05, 0.95) * W, self.rng.uniform(0.5, 0.7) * H,
                      self.rng.uniform(0, 6.28)) for _ in range(14)]
        self.blades = []
        for x in range(0, self.ex - 2):
            if self.rng.random() < 0.13:
                h = self.rng.randint(2, max(3, int(5 * self.S)))
                col = (self.rng.randint(26, 52), self.rng.randint(78, 120), self.rng.randint(26, 44))
                self.blades.append((x, h, col))
        self.dx, self.dy = W * 0.23, self.yg - 3.4 * self.S
        self.J = [(1.02, 1.40, W * 0.64, W * 0.52, 6.0 * self.S),
                  (1.80, 2.12, W * 0.52, W * 0.42, 5.0 * self.S),
                  (4.22, 4.88, W * 0.42, W * 0.77, 20.0 * self.S)]
        q = (self.yw - self.yg) / (4.0 * self.J[2][4])
        self.u_e = (1 + math.sqrt(1 + 4 * q)) / 2.0
        self.te = self.J[2][0] + (self.J[2][1] - self.J[2][0]) * self.u_e
        self.xe = lerp(self.J[2][2], self.J[2][3], self.u_e)

    def is_water(self, x, y):
        return y >= self.yw and x >= self.ex + (y - self.yg) * 0.5

    def _build(self):
        W, H, hz, yg, ex = self.W, self.H, self.hz, self.yg, self.ex
        sx, sy = W * 0.27, hz - H * 0.02
        sr = max(3.0, H * 0.07)
        px = [None] * (W * H)
        for y in range(H):
            for x in range(W):
                if y >= yg and x < ex + (y - yg) * 0.5:
                    px[y * W + x] = self._soil(x, y)
                elif self.is_water(x, y):
                    px[y * W + x] = self._wcol(x, y)
                elif y < hz:
                    px[y * W + x] = self._sky(x, y, sx, sy, sr)
                else:
                    px[y * W + x] = self._meadow(x, y, sx)
        return px

    def _sky(self, x, y, sx, sy, sr):
        hz, W, H = self.hz, self.W, self.H
        t = y / float(hz)
        c = grad(SKY, t)
        d = math.hypot(x - sx, (y - sy) * 1.5)
        gl = math.exp(-(d / (W * 0.24)) ** 2)
        c = (c[0] + 255 * gl * 0.5, c[1] + 160 * gl * 0.42, c[2] + 50 * gl * 0.15)
        if d < sr:
            c = mix(c, (255, 240, 200), clamp((sr - d) / 1.5) * 0.95)
        elif t < 0.5 and hnoise(x, y, 9) > 0.99:
            c = mix(c, (255, 255, 255), 0.7 * (1 - t / 0.5))
        h1 = hz - (0.07 * H + 0.035 * H * math.sin(x * 0.07 + 0.6) + 0.02 * H * math.sin(x * 0.19 + 2.0))
        if y >= h1:
            c = mix(c, (74, 62, 108), 0.82)
        h2 = hz - (0.018 * H + 0.045 * H * hnoise(x // 2, 5, 2) * (0.55 + 0.45 * math.sin(x * 0.05)))
        if y >= h2:
            k = 0.7 + 0.3 * hnoise(x, y, 6)
            c = (24 * k + 50 * gl, 50 * k + 26 * gl, 52 * k)
        return c

    def _meadow(self, x, y, sx):
        t = clamp((y - self.hz) / float(max(1, self.yg - self.hz)))
        c = grad(MEADOW, t)
        rim = math.exp(-((x - sx) / (self.W * 0.35)) ** 2) * (1 - t)
        n = (hnoise(x, y, 11) - 0.5) * 12
        return (c[0] + 55 * rim + n, c[1] + 34 * rim + n, c[2] + 6 * rim + n)

    def _soil(self, x, y):
        dy = y - self.yg
        n = hnoise(x, y, 5)
        if dy < 2:
            c = (74 + 40 * n, 150 + 30 * n, 50 + 20 * n)
            if dy == 0:
                c = (c[0] + 40, c[1] + 30, c[2] + 20)
            return c
        t = clamp(dy / float(self.H - self.yg))
        c = grad(SOIL, t)
        k = 1 + (n - 0.5) * 0.3
        c = (c[0] * k, c[1] * k, c[2] * k)
        if dy < 4:
            c = mix((58, 104, 42), c, (dy - 2) / 2.0)
        if hnoise(x // 3, y // 3, 4) > 0.93:
            c = (c[0] * 0.5 + 70, c[1] * 0.5 + 68, c[2] * 0.5 + 64)
        if (self.ex + dy * 0.5) - x < 3:
            c = (c[0] * 0.7, c[1] * 0.75, c[2] * 0.8)
        return c

    def _wcol(self, x, y):
        if y == self.yw:
            return (236, 192, 150)
        if y == self.yw + 1:
            return (150, 150, 140)
        d = (y - self.yw) / max(1.0, self.H - self.yw)
        base = grad(WATER, d)
        shaft = 0.5 + 0.5 * math.sin((x + (y - self.yw) * 0.7) * 0.33)
        g = 0.10 * (1 - d) * shaft
        n = (hnoise(x, y, 3) - 0.5) * 6
        return (base[0] + 150 * g + n, base[1] + 200 * g + n, base[2] + 255 * g + n)

    def _set(self, x, y, c):
        if 0 <= x < self.W and 0 <= y < self.H:
            self.bg[y * self.W + x] = c

    def _extras(self):
        W, H, hz, yg, yw, ex, S = self.W, self.H, self.hz, self.yg, self.yw, self.ex, self.S
        rng = self.rng
        for _ in range(26):
            x = rng.randint(0, W - 1)
            by = int(hz + rng.uniform(0.15, 0.85) * (yg - hz))
            h = int(rng.uniform(0.05, 0.13) * H)
            for k in range(h):
                y = by - k
                if y >= yg and x < ex + (y - yg) * 0.5:
                    continue
                self._set(x, y, (92, 62, 40) if k >= h - 2 else (26, 58, 38))
        for k in range(8):
            x0 = int(ex + (W - ex) * (0.12 + 0.11 * k)) + rng.randint(-1, 1)
            hh = int(H * 0.16 * rng.uniform(0.6, 1.0))
            for y in range(H - 1, H - 1 - hh, -1):
                x = x0 + int(round(1.6 * math.sin(y * 0.5 + k)))
                if self.is_water(x, y):
                    self._set(x, y, (16 + 6 * (k % 3), 78 + 10 * (k % 2), 50))
        cv = Canvas(W, H)
        cv.px = self.bg
        cv.ellipse(W * 0.23, yg - 0.2 * S, 4.2 * S, 2.0 * S, (120, 116, 110), tex=0.3, spec=0.15)
        cv.ellipse(W * 0.12, yg + 0.5 * S, 3.0 * S, 1.6 * S, (104, 100, 96), tex=0.3)

    def frog_state(self, t):
        S, yg, yw = self.S, self.yg, self.yw
        x, h = self.J[0][2], 0.0
        stretch, th = 0.0, 0.0
        face = -1 if t < 3.85 else 1
        yb = float(yg)
        under = False
        last = len(self.J) - 1
        for i, (a, b, xa, xb, A) in enumerate(self.J):
            end = self.te if i == last else b
            if t < a:
                break
            if t < end:
                u = (t - a) / (b - a)
                x = lerp(xa, xb, u)
                h = 4 * A * u * (1 - u)
                yb = yg - h
                vx = (xb - xa) / (b - a)
                vy = -4 * A * (1 - 2 * u) / (b - a)
                ang = math.atan2(vy, vx)
                if face < 0:
                    ang -= math.pi
                th = 0.75 * norm_ang(ang)
                stretch = math.sin(math.pi * min(u, 1.0))
                break
            x = xb if i != last else self.xe
            if i == last:
                under = True
        if under:
            tau = t - self.te
            ang = math.atan2(4 * self.J[2][4] * (2 * self.u_e - 1) / (self.J[2][1] - self.J[2][0]),
                             (self.J[2][3] - self.J[2][2]) / (self.J[2][1] - self.J[2][0]))
            th = lerp(0.75 * norm_ang(ang), 1.25, ramp(tau, 0.0, 0.35))
            x = self.xe + 5 * S * (1 - math.exp(-tau * 3))
            yb = yw + 16 * S * (1 - math.exp(-tau * 2.2))
            stretch = 0.6 + 0.4 * math.sin(tau * 14)
        crouch = kf(CROUCH, t) if not under else 0.0
        eye = kf(EYE, t)
        for bt in (0.78, 1.96, 3.9):
            if abs(t - bt) < 0.06:
                eye = min(eye, abs(t - bt) / 0.06)
        rate = 3.2 if t < 2.2 else 11.0 if t < 2.9 else 6.0
        p = (t - 2.95) / 0.65
        return {"x": x, "yb": yb, "face": face, "crouch": crouch, "theta": th, "stretch": stretch,
                "mouth": kf(MOUTH, t), "ext": kf(TONGUE, t), "eye": eye,
                "throat": 0.5 + 0.5 * math.sin(t * rate), "bulge": p if 0 <= p <= 1 else -1.0}

    def draw_frog(self, cv, s, t):
        S, f, th = self.S, s["face"], s["theta"]
        c, st = s["crouch"], s["stretch"]
        rx = (9.0 + 1.6 * c - 1.0 * st) * S
        ry = (6.4 - 1.5 * c - 1.2 * st) * S
        clear = (2.4 * (1 - c) + 0.9) * S
        bx = s["x"]
        by = s["yb"] - ry - clear
        co, si = math.cos(th), math.sin(th)

        def P(lx, ly):
            ux = f * lx
            return bx + ux * co - ly * si, by + ux * si + ly * co

        def E(lx, ly, erx, ery, col, lr=0.0, a=1.0, tex=0.0, spec=0.0, flat=False):
            x, y = P(lx, ly)
            cv.ellipse(x, y, erx, ery, col, f * lr + th, a, tex, spec, flat)

        skin = (66, 148, 58)
        dark = (52, 122, 48)
        E(-0.55 * rx, 0.25 * ry, 0.5 * rx, 0.45 * ry, (40, 100, 40), lr=-0.2)
        E(0, 0, rx, ry, skin, tex=0.25, spec=0.22)
        E(-0.25 * rx, -0.5 * ry, 0.28 * rx, 0.16 * ry, (40, 98, 40), a=0.7, flat=True)
        E(0.08 * rx, -0.3 * ry, 0.18 * rx, 0.12 * ry, (40, 98, 40), a=0.7, flat=True)
        E(-0.55 * rx, -0.05 * ry, 0.2 * rx, 0.12 * ry, (40, 98, 40), a=0.7, flat=True)
        E(0.15 * rx, 0.55 * ry, 0.8 * rx, 0.42 * ry, (205, 220, 140), a=0.85)
        E(0.62 * rx, 0.5 * ry, 0.3 * rx * (1 + 0.5 * s["throat"]), 0.25 * ry * (1 + 0.5 * s["throat"]),
          (228, 238, 164), a=0.55, flat=True)
        if s["bulge"] >= 0:
            p = s["bulge"]
            E(lerp(0.9, 0.1, p) * rx, lerp(0.15, 0.4, p) * ry, 1.7 * S, 1.5 * S, (120, 190, 100), a=0.9, spec=0.4)
        E(lerp(-0.3, -0.9, st) * rx, lerp(0.35, 0.3, st) * ry, 0.62 * rx, 0.55 * ry, dark,
          lr=lerp(-0.25, 0.1, st), spec=0.15)
        E(lerp(-0.05, -1.55, st) * rx, lerp(0.75, 0.45, st) * ry, 0.5 * rx, 0.2 * ry, dark,
          lr=lerp(0.0, 0.15, st))
        E(lerp(0.35, -2.15, st) * rx, lerp(1.05, 0.5, st) * ry, 0.45 * rx, 0.14 * ry, (60, 134, 52))
        E(0.6 * rx, -0.12 * ry, 0.52 * rx, 0.62 * ry, (76, 160, 64), spec=0.3)
        eo = s["eye"]
        re = 2.5 * S
        for ex_, ey_, a in ((0.42 * rx, -0.76 * ry, 0.8), (0.64 * rx, -0.7 * ry, 1.0)):
            ey_ += (1 - eo) * 0.7 * re
            E(ex_, ey_, re, re * (0.55 + 0.45 * eo), (84, 168, 70), a=a, spec=0.3)
            if eo > 0.12:
                E(ex_ + 0.15 * re, ey_, 0.72 * re, 0.72 * re * eo, (238, 188, 40), a=a, spec=0.5)
                E(ex_ + 0.15 * re, ey_, 0.42 * re, 0.2 * re * eo + 0.1, (8, 8, 8), a=a, flat=True)
                wx, wy = P(ex_ - 0.15 * re, ey_ - 0.2 * re)
                cv.disc(wx, wy, 0.4 * S, (255, 255, 255), 0.9 * a)
        m = s["mouth"]
        mx0, my0 = P(1.06 * rx, 0.12 * ry)
        mx1, my1 = P(0.35 * rx, 0.28 * ry)
        cv.seg(mx0, my0, mx1, my1, 0.8 * S, (28, 58, 28), 0.9)
        if m > 0.05:
            E(0.95 * rx, 0.2 * ry + m * 0.8 * S, 0.34 * rx, 0.3 * S + m * 2.0 * S, (176, 54, 74), flat=True)
        nx_, ny_ = P(1.0 * rx, -0.22 * ry)
        cv.disc(nx_, ny_, 0.45 * S, (20, 40, 20), 0.9)
        sx0, sy0 = P(0.45 * rx, 0.55 * ry)
        sx1, sy1 = P(0.62 * rx, ry + clear - 0.5 * S)
        cv.seg(sx0, sy0, sx1, sy1, 1.6 * S, dark)
        E(0.8 * rx, ry + clear - 0.4 * S, 0.28 * rx, 0.16 * ry + 0.3, (62, 136, 54))
        mouth = P(1.0 * rx, 0.16 * ry + m * 0.8 * S)
        if s["ext"] > 0.01:
            tx = mouth[0] + (self.dx - mouth[0]) * s["ext"]
            ty = mouth[1] + (self.dy - mouth[1]) * s["ext"]
            cv.seg(mouth[0], mouth[1], tx, ty, 1.7 * S, (226, 84, 104))
            cv.seg(mouth[0], mouth[1], tx, ty, 0.7 * S, (252, 150, 162), 0.8)
            cv.disc(tx, ty, 1.5 * S, (238, 104, 122))
            return mouth, (tx, ty)
        return mouth, None

    def draw_dragon(self, cv, x, y, t, caught):
        S = self.S
        amp = 0.5 if caught else 0.3 if t > 2.3 else 0.06
        fr = 70.0 if caught else 60.0 if t > 2.3 else 9.0
        fl = math.sin(t * fr) * amp
        tilt = 0.6 * math.sin(t * 30) if caught else 0.0
        co, si = math.cos(tilt), math.sin(tilt)

        def P(lx, ly):
            return x + lx * co - ly * si, y + lx * si + ly * co
        for wl, wy, wr in ((1.8, -0.9, -0.5), (0.9, -0.9, -0.15), (1.8, 0.9, 0.5), (0.9, 0.9, 0.15)):
            px_, py_ = P(wl * S - 2.4 * S, wy * S)
            cv.ellipse(px_, py_, 4.4 * S, 1.1 * S, (200, 228, 255), rot=wr + fl + tilt, alpha=0.32, flat=True)
        for i in range(6):
            ax_, ay_ = P((-i * 1.4 + 0.4) * S, 0.0)
            cv.ellipse(ax_, ay_, 1.1 * S, 0.8 * S * (1 - 0.08 * i),
                       (22, 96, 176) if i % 2 == 0 else (12, 44, 96), rot=tilt, spec=0.3)
        tx_, ty_ = P(1.6 * S, 0.0)
        cv.ellipse(tx_, ty_, 1.9 * S, 1.4 * S, (34, 126, 206), rot=tilt, spec=0.4)
        hx_, hy_ = P(4.0 * S, 0.0)
        cv.ellipse(hx_, hy_, 1.4 * S, 1.3 * S, (20, 180, 170), rot=tilt, spec=0.6)

    def frame(self, t):
        W, H, S = self.W, self.H, self.S
        cv = Canvas(W, H)
        cv.px = self.bg[:]
        for (fx, fy, ph) in self.fire:
            a = 0.5 + 0.5 * math.sin(t * 3 + ph)
            x = fx + 4 * math.sin(t * 0.9 + ph)
            y = fy + 3 * math.sin(t * 1.3 + 2 * ph)
            if y < self.yg - 2:
                cv.put(int(x), int(y), (255, 240, 150), 0.8 * a)
                for ox, oy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    cv.put(int(x) + ox, int(y) + oy, (255, 230, 120), 0.22 * a)
        s = self.frog_state(t)
        dragon_rest = t < 2.55
        if dragon_rest:
            self.draw_dragon(cv, self.dx, self.dy, t, False)
        mouth, tip = self.draw_frog(cv, s, t)
        if not dragon_rest and tip is not None and s["ext"] > 0.12 and t < 2.9:
            self.draw_dragon(cv, tip[0], tip[1], t, True)
        if t >= self.te:
            tau = t - self.te
            for k in range(3):
                tr_ = tau - 0.18 * k
                if tr_ > 0:
                    r = 1.5 * S + tr_ * 26 * S
                    a = clamp(1 - tr_ / 1.0) * 0.8
                    cv.ring(self.xe, self.yw, r, r * 0.16, (235, 245, 255), a, self.ex + (self.yw - self.yg) // 2)
            if tau < 0.35:
                hh = 9 * S * (1 - tau / 0.35)
                cv.ellipse(self.xe, self.yw - hh * 0.5, 2.6 * S, max(0.4, hh * 0.5), (210, 236, 255), alpha=0.6, flat=True)
            for i in range(40):
                r = random.Random(i)
                vx = (r.random() - 0.5) * 30 * S
                vy = -(14 + r.random() * 20) * S
                x = self.xe + vx * tau
                y = self.yw + vy * tau + 0.5 * 55 * S * tau * tau
                if y <= self.yw + 0.5 and tau < 1.3:
                    cv.put(int(x), int(y), (225, 242, 255), clamp(1 - tau / 1.3))
            for k in range(14):
                tb = tau - 0.1 - 0.07 * k
                if tb > 0:
                    bx = s["x"] + math.sin(k * 2.1 + tb * 5) * 2.2 * S + (k % 3 - 1) * 1.5 * S
                    by = self.yw + 12 * S - tb * 16 * S
                    if by > self.yw + 1:
                        cv.disc(bx, by, (0.6 + 0.3 * (k % 3)) * S, (200, 236, 250), 0.5)
            for i, col in self.water:
                o = cv.px[i]
                cv.px[i] = (o[0] + (col[0] - o[0]) * 0.42, o[1] + (col[1] - o[1]) * 0.42, o[2] + (col[2] - o[2]) * 0.42)
        for (x, h, col) in self.blades:
            for k in range(h):
                cv.put(x, self.yg - k, col, 0.95)
        gain = ramp(t, 0.0, 0.6) * (1 - ramp(t, 5.45, 6.0))
        if 2.5 < t < 2.66:
            gain *= 1 + 0.28 * (1 - abs(t - 2.58) / 0.08)
        return cv, gain

    def emit(self, cv, gain, n):
        W = self.W
        px = cv.px
        vig = self.vig
        gr = self.grain[n % 3]
        out = []
        for r in range(self.H // 2):
            a = 2 * r * W
            b = a + W
            last = None
            line = []
            for x in range(W):
                m1 = vig[a + x] * gain * (1 + gr[a + x])
                m2 = vig[b + x] * gain * (1 + gr[b + x])
                t = px[a + x]
                u = px[b + x]
                v0 = int(t[0] * m1); v1 = int(t[1] * m1); v2 = int(t[2] * m1)
                w0 = int(u[0] * m2); w1 = int(u[1] * m2); w2 = int(u[2] * m2)
                key = (0 if v0 < 0 else 252 if v0 > 252 else v0 & 252,
                       0 if v1 < 0 else 252 if v1 > 252 else v1 & 252,
                       0 if v2 < 0 else 252 if v2 > 252 else v2 & 252,
                       0 if w0 < 0 else 252 if w0 > 252 else w0 & 252,
                       0 if w1 < 0 else 252 if w1 > 252 else w1 & 252,
                       0 if w2 < 0 else 252 if w2 > 252 else w2 & 252)
                if key != last:
                    line.append("\033[38;2;%d;%d;%d;48;2;%d;%d;%dm▀" % key)
                    last = key
                else:
                    line.append("▀")
            out.append("".join(line) + "\033[0m\033[K\n")
        return "".join(out)


CAPTIONS = [(0.0, "THE POND AT DAWN — the frog waits"), (1.0, "PATIENCE — no setup, no trade"),
            (2.35, "STRIKE — one precise entry"), (2.9, "SECURE THE PROFIT"),
            (3.8, "PROTECT THE CAPITAL — retreat"), (5.0, "DIVE. SURVIVE. STRIKE AGAIN.")]


def play_intro():
    if not sys.stdout.isatty() or os.getenv("FROG_SKIP_INTRO"):
        return
    cols, rows = shutil.get_terminal_size((100, 40))
    if cols < 60 or rows < 22:
        return
    W = min(cols, 110)
    ch = max(14, min(rows - 5, 30))
    scene = Scene(W, ch * 2)
    pad = " " * ((cols - W) // 2) if cols > W else ""
    title = "F  R  O  G     T  R  A  D  E"
    top = "\033[K\n" + "\033[90m" + title.center(cols) + "\033[0m\033[K\n"
    sys.stdout.write("\033[?25l\033[2J")
    try:
        t0 = time.perf_counter()
        n = 0
        while True:
            t = time.perf_counter() - t0
            if t >= DURATION:
                break
            ts = time.perf_counter()
            cv, gain = scene.frame(t)
            body = scene.emit(cv, gain, n)
            if pad:
                body = "".join(pad + ln + "\n" for ln in body.split("\n")[:-1])
            cap = [c for tt, c in CAPTIONS if tt <= t][-1]
            fade = clamp(gain)
            g = int(150 * fade)
            bottom = "\033[38;2;%d;%d;%dm%s\033[0m\033[K\n\033[K" % (g, min(255, g + 60), g, cap.center(cols))
            sys.stdout.write("\033[H" + top + body + bottom)
            sys.stdout.flush()
            n += 1
            dt = time.perf_counter() - ts
            if dt < 1 / 24.0:
                time.sleep(1 / 24.0 - dt)
    except KeyboardInterrupt:
        pass
    finally:
        sys.stdout.write("\033[0m\033[?25h")
        sys.stdout.flush()
        clear()


FROG_HEAD = [
    r"         .-'''-.             .-'''-.         ",
    r"        / .---. \___________/ .---. \        ",
    r"       | | (@) |             | (@) | |       ",
    r"        \ '---'    _     _    '---' /        ",
    r"       .-'.      (o)   (o)      .'-.         ",
    r"      /    '-._               _.-'    \      ",
    r"     |    .-'   '-.._____..-'   '-.    |     ",
    r"     |   /    \_____________/     \   |      ",
    r"      \  '-.                     .-'  /      ",
    r"       '._  '---...._____....---'  _.'       ",
    r"          '-.._               _..-'          ",
    r"               '-----------'                 ",
]

LETTERS = {
    "F": ["█████", "█    ", "████ ", "█    ", "█    "],
    "R": ["████ ", "█   █", "████ ", "█  █ ", "█   █"],
    "O": [" ███ ", "█   █", "█   █", "█   █", " ███ "],
    "G": [" ████", "█    ", "█  ██", "█   █", " ███ "],
    "T": ["█████", "  █  ", "  █  ", "  █  ", "  █  "],
    "A": [" ███ ", "█   █", "█████", "█   █", "█   █"],
    "D": ["████ ", "█   █", "█   █", "█   █", "████ "],
    "E": ["█████", "█    ", "████ ", "█    ", "█████"],
    " ": ["   ", "   ", "   ", "   ", "   "],
}


def block_text(s):
    rows = ["", "", "", "", ""]
    for chh in s:
        g = LETTERS.get(chh, LETTERS[" "])
        for i in range(5):
            rows[i] += g[i] + "  "
    return rows


def banner():
    clear()
    W, _ = term_size()
    shades = [118, 82, 46, 40, 34]
    lines = []
    for ln in FROG_HEAD:
        lines.append("\033[38;5;70m" + ln.center(W) + C.R)
    lines.append("")
    for i, ln in enumerate(block_text("FROG TRADE")):
        lines.append("\033[1;38;5;%dm" % shades[i] + ln.center(W) + C.R)
    lines.append("")
    lines.append(("{}{}🐸  TOOL NAME: {}{}{}  🐸{}".format(C.B, C.G, C.W, APP, C.G, C.R)).center(W + 14))
    lines.append(("{}AUTHOR: {}{}{}".format(C.B, C.CY, AUTHOR, C.R)).center(W + 12))
    lines.append("")
    lines.append(C.GR + "─" * W + C.R)
    lines.append(("{}{}{}".format(C.B + C.Y, NOTICE, C.R)).center(W + 8) if len(NOTICE) <= W else
                 C.B + C.Y + NOTICE[:W] + C.R)
    lines.append(C.GR + "─" * W + C.R)
    for ln in lines:
        print(ln)
        sys.stdout.flush()
        time.sleep(0.05)
    print()
    read_line("  {}Press Enter to dive in →{} ".format(C.G, C.R))


def pick(step, rows, zero):
    clear()
    W, _ = term_size()
    print("{}{}◆ FROG TRADE{}\n{}{}{}".format(C.B, C.G, C.R, C.GR, "─" * W, C.R))
    print("  {}{}{}\n".format(C.B, step, C.R))
    for i, t in enumerate(rows, 1):
        print("   {}{:>2}.{} {}".format(C.B, i, C.R, t))
    print("\n   {}0.{} {}\n{}{}{}".format(C.B, C.R, zero, C.GR, "─" * W, C.R))
    while True:
        chh = read_line("  # → ")
        if chh in ("0", ""):
            return None
        if chh.isdigit() and 1 <= int(chh) <= len(rows):
            return int(chh) - 1
        print("  {}invalid{}".format(C.RD, C.R))


def pick_market():
    return pick("STEP 1 — Market", ["{} ({})".format(n, len(i)) for n, i in MARKETS], "exit")


def pick_tf():
    return pick("STEP 2 — Timeframe", ["{:<4} ({}s candles)".format(l, s) for l, s in TIMEFRAMES], "back")


def pick_inst(m_idx):
    return pick("STEP 3 — Instrument ({})".format(MARKETS[m_idx][0]),
                ["{:<16} {}".format(lbl, sym) for sym, lbl in MARKETS[m_idx][1]], "back")


def wizard():
    while True:
        m = pick_market()
        if m is None:
            clear()
            sys.exit(0)
        t = pick_tf()
        if t is None:
            continue
        i = pick_inst(m)
        if i is None:
            continue
        return m, t, i


def scan_market(m_idx, tf_idx):
    name, items = MARKETS[m_idx]
    tf = TIMEFRAMES[tf_idx][1]
    res = []
    clear()
    for n, (sym, lbl) in enumerate(items, 1):
        sys.stdout.write("\r  scanning {}/{}  {:<16}".format(n, len(items), lbl))
        sys.stdout.flush()
        f = SimFeed(sym, tf, 1, 330)
        f.refresh(full=True)
        res.append((lbl, analyze(closed_candles(f.candles, tf, f.clock()), tf)))
    res.sort(key=lambda x: (x[1].verdict == "WAIT", -abs(x[1].score)))
    clear()
    print("{}{}SCAN — {} @ {}{}\n".format(C.B, C.G, name, TIMEFRAMES[tf_idx][0], C.R))
    for lbl, an in res:
        col = C.G if an.verdict == "BUY" else C.RD if an.verdict == "SELL" else C.GR
        why = "" if an.verdict != "WAIT" else (an.blockers[0] if an.blockers else "")
        print("  {:<16} {}{:<5}{} conf {:>3d}%  {:<5} {}{}{}".format(
            lbl, col, an.verdict, C.R, an.confluence, an.regime, C.D, why[:34], C.R))
    read_line("\n  Enter to return → ")


EXPLAIN = {
    "BB": "Bollinger %B: a stretch to a band edge hints at a snap-back",
    "RSI": "RSI: momentum extreme in ranges, healthy push in trends",
    "STO": "Stochastic: timing of turns inside the swing",
    "PAT": "Candle pattern: engulfing, hammer, shooting star",
    "S/R": "Support / resistance: is price touching a known wall?",
    "HTF": "Higher timeframe: the tide you are swimming in",
    "EMA": "EMA 20 / 50: trend structure",
    "DI": "+DI vs -DI: which side is pushing harder",
    "MACD": "MACD histogram: momentum building or fading",
}
REGIME_TXT = {
    "TREND": "Trending (ADX 25+). Follow the current: buy dips in uptrends, sell pops in downtrends.",
    "RANGE": "Ranging (ADX 20 or less). Price oscillates. Fade the extremes, never chase.",
    "MIXED": "Transition (ADX 20-25). The frog is picky here and needs more agreement.",
}
LESSONS = [
    ("LESSON 1 — The Frog's First Law: Survive", [
        "A frog that never dives gets eaten. Your capital is your lily pad.",
        "Professionals are not paid for being right. They are paid for staying in the game",
        "long enough for a small edge to play out.",
        "",
        "Rule: protect the balance first, the profit takes care of itself.",
    ]),
    ("LESSON 2 — The Payout Math", [
        "At a 92% payout, a win earns 0.92 and a loss costs 1.00.",
        "Break-even win rate = 100 / (1 + payout) = {:.1f}%.".format(BREAKEVEN),
        "Expectancy per 1.00 staked = win% x 0.92 - loss% x 1.00.",
        "Win 55% of the time: 0.55 x 0.92 - 0.45 = +0.056 per trade. Small. Real. Fragile.",
        "Win 50%: 0.50 x 0.92 - 0.50 = -0.04. You slowly bleed even when 'half right'.",
    ]),
    ("LESSON 3 — Position Sizing", [
        "Risk 1-2% of the balance per trade. This tool defaults to 2%.",
        "Ten losses in a row at 2% costs about 18% of the account. Survivable.",
        "Ten losses in a row at 20% costs about 89%. Game over.",
        "Streaks of losses are guaranteed in any real series. Size so they cannot kill you.",
    ]),
    ("LESSON 4 — Loss Limits and Cool-downs", [
        "Set a daily loss limit ({:.0f}% here) and obey it. The guard locks trading when hit.".format(DAILY_LIMIT),
        "Three losses in a row trigger a cool-down. Revenge trading is the fastest way",
        "to turn a bad hour into a ruined week.",
        "A closed screen is also a position.",
    ]),
    ("LESSON 5 — Read the Regime First", [
        "Before any signal, ask: is the market trending or ranging?",
        "ADX 25+  -> trend: use EMA structure, +DI/-DI, MACD, higher timeframe.",
        "ADX 20-  -> range: use Bollinger %B, RSI and Stochastic extremes, support/resistance.",
        "Using trend tools in a range (or the reverse) is the classic beginner leak.",
    ]),
    ("LESSON 6 — Confluence, Not Hope", [
        "One indicator is an opinion. Four agreeing, plus the higher timeframe, is a case.",
        "The engine demands: enough agreeing votes, no strong objection, the higher timeframe",
        "not against you, sane volatility, no spike candle, no overextended RSI.",
        "If any blocker fires it says WAIT and tells you why.",
    ]),
    ("LESSON 7 — Timing, Holding and Cashing Out", [
        "Signals come from CLOSED candles only, so they never repaint. Enter at the next open.",
        "Late entries lose edge. If the tool says LATE, skip it.",
        "Hold time (key e) is how many candles the trade lives. Match it to your thesis.",
        "Cash-out (key k) locks value early. The later you hold in profit, the more you keep,",
        "but exits before expiry always give up some edge. Use it to protect, not to panic.",
    ]),
    ("LESSON 8 — Journal and Judge by Numbers", [
        "Every trade and signal is written to frogtrade_journal.csv.",
        "Twenty trades prove nothing. The 95% range in the backtest shows how wide the truth is.",
        "Only trust an edge when the LOW end of that range clears {:.1f}%.".format(BREAKEVEN),
        "Review losses without ego: was it a bad trade, or a good trade that lost?",
    ]),
    ("LESSON 9 — When to Dive", [
        "No signal, quiet market, volatility spike, spike candle, higher timeframe against you,",
        "hitting your daily limit: all mean sit out.",
        "The best traders skip most setups. Patience is the strategy.",
        "Dive. Survive. Strike again.",
    ]),
]


def reading_page(st, feed, acct):
    name, items = MARKETS[st.m_idx]
    sym, lbl = items[st.i_idx]
    tfl = TIMEFRAMES[st.tf_idx][0]
    now = feed.clock()
    an = analyze(closed_candles(feed.candles, feed.tf, now), feed.tf)
    L = []
    L.append("{}{}{} · {} · price {}{}".format(C.B, lbl, C.R, tfl, fmt_price(feed.last_price), C.R))
    L.append("")
    if an.regime != "-":
        L.append("{}Regime:{} {}".format(C.Y, C.R, REGIME_TXT[an.regime]))
        L.append("")
    col = C.G if an.verdict == "BUY" else C.RD if an.verdict == "SELL" else C.Y
    L.append("{}Verdict:{} {}{}{}  score {:+.2f}  confluence {}%".format(C.Y, C.R, col, an.verdict, C.R, an.score, an.confluence))
    L.append("")
    L.append("{}What each tool says:{}".format(C.Y, C.R))
    for tag, v in an.votes:
        arrow = "{}▲ leans up{}".format(C.G, C.R) if v >= .4 else "{}▼ leans down{}".format(C.RD, C.R) if v <= -.4 else "{}– neutral{}".format(C.GR, C.R)
        L.append("  {:<5} {}  {}{}{}".format(tag, arrow, C.D, EXPLAIN.get(tag, ""), C.R))
    if an.note:
        L.append("  {}pattern/level: {}{}".format(C.CY, an.note, C.R))
    if an.blockers:
        L.append("")
        L.append("{}Why the frog waits:{}".format(C.Y, C.R))
        for b in an.blockers:
            L.append("  • " + b)
    stake = acct.stake()
    L.append("")
    L.append("{}Risk plan:{}".format(C.Y, C.R))
    L.append("  balance {}  risk {:.1f}%  stake {}".format(money(acct.balance), acct.risk, money(stake)))
    L.append("  win {}  /  lose {}  /  break-even win rate {:.1f}%".format(money(stake * PAYOUT, True), money(-stake), BREAKEVEN))
    if st.bt and st.bt["n"]:
        wr = st.bt["wr"] / 100.0
        ev = wr * PAYOUT - (1 - wr)
        L.append("  backtest win rate {:.1f}% → expectancy {:+.3f} per 1.00 staked ({})".format(
            st.bt["wr"], ev, "positive" if ev > 0 else "negative"))
    else:
        L.append("  press b on the chart to measure the real win rate before trusting a signal")
    return ("COACH'S READING", L)


def mentor(st, feed, acct):
    pages = [reading_page(st, feed, acct)] + LESSONS
    i = 0
    while True:
        clear()
        W, _ = term_size()
        title, lines = pages[i]
        print("{}{}◆ FROG TRADE — MENTOR{}  {}page {}/{}{}\n{}{}{}".format(
            C.B, C.G, C.R, C.D, i + 1, len(pages), C.R, C.GR, "─" * W, C.R))
        print("  {}{}{}\n".format(C.B, title, C.R))
        for ln in lines:
            print("  " + ln)
        print()
        ans = read_line("  {}Enter next · p back · q close →{} ".format(C.D, C.R)).lower()
        if ans == "q":
            return
        if ans == "p":
            i = max(0, i - 1)
        else:
            i += 1
            if i >= len(pages):
                return


def report(acct):
    clear()
    W, _ = term_size()
    s = acct.stats()
    print("{}{}◆ FROG TRADE — JOURNAL{}\n{}{}{}\n".format(C.B, C.G, C.R, C.GR, "─" * W, C.R))
    nc = C.G if s["net"] >= 0 else C.RD
    print("  balance {}   start {}   net {}{}{}".format(money(acct.balance), money(START_BALANCE), nc, money(s["net"], True), C.R))
    print("  trades {}   wins {}   losses {}   draws {}".format(s["n"], s["w"], s["l"], s["d"]))
    if s["w"] + s["l"]:
        wc = C.G if s["wr"] >= BREAKEVEN else C.RD
        print("  win rate {}{:.1f}%{}  (95% range {:.0f}-{:.0f}%, break-even {:.1f}%)".format(wc, s["wr"], C.R, s["lo"], s["hi"], BREAKEVEN))
        print("  avg win {}   avg loss {}   expectancy {} per trade".format(money(s["aw"], True), money(s["al"]), money(s["exp"], True)))
    print("  max drawdown {:.1f}%   daily limit {:.0f}%".format(acct.max_dd, DAILY_LIMIT))
    auto = [t for t in acct.closed if t["src"] == "auto"]
    man = [t for t in acct.closed if t["src"] == "manual"]
    cash = [t for t in acct.closed if t["result"] == "CASH"]
    print("  auto trades {}   manual trades {}   early cash-outs {}".format(len(auto), len(man), len(cash)))
    print("\n  {}Last trades{}".format(C.Y, C.R))
    for t in acct.closed[-10:][::-1]:
        col = C.G if t["pnl"] > 0 else C.RD if t["pnl"] < 0 else C.GR
        print("   {}{:<5}{} {:<8} {:<4} {:<6} stake {:>8}  {}{}{}".format(
            col, t["result"], C.R, t["sym"], "CALL" if t["dir"] == "BUY" else "PUT", t["src"],
            money(t["stake"]), col, money(t["pnl"], True), C.R))
    print("\n  {}Coach:{}".format(C.Y, C.R))
    if s["w"] + s["l"] < 30:
        print("  Sample is too small to judge. Keep trading small and wait for 100+ trades.")
    elif s["lo"] > BREAKEVEN:
        print("  The low end of your range clears break-even. The edge looks real. Stay disciplined.")
    elif s["wr"] < BREAKEVEN:
        print("  Below break-even. Cut the stake, trade only A+ setups, review every loss.")
    else:
        print("  Above break-even but not proven. More trades needed before raising size.")
    read_line("\n  Enter to return → ")


def place(st, feed, acct, direction, src="manual"):
    now = feed.clock()
    if len(closed_candles(feed.candles, feed.tf, now)) < MIN_BARS:
        return "Still collecting candles."
    why = acct.blocked(now)
    if why:
        return "{}{}{}".format(C.Y, why, C.R)
    t = acct.open_trade(feed.symbol, feed.tf, direction, feed.last_price, now, now + acct.expiry * feed.tf, src)
    return "{}{} {} {} placed · expires in {}{}".format(
        C.G, "CALL" if direction == "BUY" else "PUT", money(t["stake"]), src, mmss(acct.expiry * feed.tf), C.R)


def process(st, feed, acct):
    tf = feed.tf
    now = feed.clock()
    cs = feed.candles
    closed = closed_candles(cs, tf, now)
    if len(closed) >= 2:
        T = closed[-1].time
        if T in st.locked:
            st.an = st.locked[T]
        else:
            if st.an is None or st.an_T != T:
                st.an = analyze(closed, tf)
                st.an_T = T
            an = st.an
            if T + tf + 1.0 <= now < T + 2 * tf:
                st.locked[T] = an
                if an.verdict != "WAIT":
                    st.tracker.add(an)
                    if acct.auto:
                        why = acct.blocked(now)
                        if why:
                            note(st, "{}auto skipped: {}{}".format(C.Y, why, C.R))
                        else:
                            t = acct.open_trade(feed.symbol, tf, an.verdict, feed.last_price, now,
                                                an.time + (1 + acct.expiry) * tf, "auto")
                            note(st, "{}AUTO {} {} placed{}".format(
                                C.CY, "CALL" if an.verdict == "BUY" else "PUT", money(t["stake"]), C.R))
    st.tracker.settle(cs, now)
    for t in acct.settle(feed.last_price, now):
        col = C.G if t["pnl"] > 0 else C.RD if t["pnl"] < 0 else C.GR
        note(st, "{}{} {} on {}{}".format(col, t["result"], money(t["pnl"], True), "CALL" if t["dir"] == "BUY" else "PUT", C.R))
        if acct.halted():
            note(st, "{}{} · RISK GUARD ENGAGED, trading halted{}".format(col, t["result"], C.R))


def run_live(sel, acct):
    m_idx, tf_idx, i_idx = sel
    sym, lbl = MARKETS[m_idx][1][i_idx]
    tf = TIMEFRAMES[tf_idx][1]
    feed = SimFeed(sym, tf, SPEEDS[acct.speed_idx], HISTORY)
    print("\n  loading {} …".format(lbl))
    feed.refresh(full=True)
    st = View(m_idx, tf_idx, i_idx, tracker=Tracker(sym, tf))
    process(st, feed, acct)
    with Keys() as keys:
        sys.stdout.write("\033[?25l\033[2J")
        try:
            next_poll = 0.0
            while True:
                now = time.time()
                if now >= next_poll:
                    old = len(feed.candles)
                    feed.refresh()
                    if st.offset > 0:
                        st.offset += max(0, len(feed.candles) - old)
                    process(st, feed, acct)
                    next_poll = now + POLL_SECS
                    render(st, feed, acct)
                k = keys.get(0.05)
                if not k:
                    continue
                page = st.nbars
                if k in ("left", "a"):
                    st.offset += 3
                elif k in ("right", "d"):
                    st.offset -= 3
                elif k == "pgup":
                    st.offset += page
                elif k == "pgdn":
                    st.offset -= page
                elif k == "home":
                    st.offset = 10 ** 6
                elif k in ("end", "g"):
                    st.offset = 0
                elif k in ("+", "=", "up"):
                    st.bw = min(3, st.bw + 1)
                elif k in ("-", "_", "down"):
                    st.bw = max(1, st.bw - 1)
                elif k == "u":
                    note(st, place(st, feed, acct, "BUY"))
                elif k == "p":
                    note(st, place(st, feed, acct, "SELL"))
                elif k == "k":
                    if not acct.open:
                        note(st, "{}nothing open to cash out{}".format(C.GR, C.R))
                    else:
                        tot = sum(acct.cash_out(t, feed.last_price, feed.clock()) for t in acct.open[:])
                        note(st, "{}cashed out early · {}{}".format(C.CY, money(tot, True), C.R))
                elif k == "x":
                    acct.auto = not acct.auto
                    note(st, "auto-follow signals: {}".format("ON — stake follows your risk %" if acct.auto else "off"))
                elif k == "[":
                    acct.risk = max(0.5, round(acct.risk - 0.5, 1))
                    note(st, "risk {:.1f}% per trade".format(acct.risk))
                elif k == "]":
                    acct.risk = min(5.0, round(acct.risk + 0.5, 1))
                    note(st, "risk {:.1f}% per trade{}".format(acct.risk, "  — above 2% the coach frowns" if acct.risk > 2 else ""))
                elif k == "e":
                    acct.expiry = acct.expiry % 3 + 1
                    note(st, "hold time {}×{}".format(acct.expiry, TIMEFRAMES[tf_idx][0]))
                elif k == "v":
                    acct.speed_idx = (acct.speed_idx + 1) % len(SPEEDS)
                    feed.set_speed(SPEEDS[acct.speed_idx])
                    note(st, "clock speed x{}".format(feed.speed))
                elif k == "b":
                    note(st, "{}running backtest…{}".format(C.Y, C.R))
                    render(st, feed, acct)
                    st.bt = backtest(feed.candles, tf, feed.clock())
                    note(st, "")
                elif k == "m":
                    keys.suspend()
                    feed.freeze()
                    mentor(st, feed, acct)
                    feed.thaw()
                    keys.resume()
                elif k == "l":
                    keys.suspend()
                    feed.freeze()
                    report(acct)
                    feed.thaw()
                    keys.resume()
                elif k == "enter":
                    next_poll = 0
                elif k in ("s", "c", "i", "t"):
                    if acct.open:
                        note(st, "{}settle or cash out (k) your open trades first{}".format(C.Y, C.R))
                    else:
                        return {"s": "scan", "c": "wizard", "i": "inst", "t": "tf"}[k]
                elif k in ("q", "quit"):
                    for t in acct.open[:]:
                        acct.cash_out(t, feed.last_price, feed.clock())
                    return "quit"
                st.offset = max(0, st.offset)
                render(st, feed, acct)
        finally:
            sys.stdout.write("\033[?25h\033[0m\n")
            sys.stdout.flush()


def main():
    play_intro()
    banner()
    acct = Account()
    sel = wizard()
    while True:
        act = run_live(sel, acct)
        if act == "quit":
            clear()
            s = acct.stats()
            print("{}{}FROG TRADE{} — session over".format(C.B, C.G, C.R))
            print("  balance {}  net {}  trades {}".format(money(acct.balance), money(s["net"], True), s["n"]))
            print("  journal: {}".format(JOURNAL))
            print("  Dive. Survive. Strike again.")
            return
        if act == "wizard":
            sel = wizard()
        elif act == "inst":
            i = pick_inst(sel[0])
            sel = (sel[0], sel[1], i if i is not None else sel[2])
        elif act == "tf":
            t = pick_tf()
            sel = (sel[0], t if t is not None else sel[1], sel[2])
        elif act == "scan":
            scan_market(sel[0], sel[1])


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.stdout.write("\033[?25h\033[0m")
        clear()
        print("bye.")
