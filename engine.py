"""Extraction -> hybrid schedule linking -> confidence routing -> validation/audit -> institutional memory."""
from __future__ import annotations
import re, datetime as dt, random
import numpy as np, pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from data import DISC, PLAN

AUTO, REVIEW = 0.70, 0.40   # confidence thresholds
KIND_KW = {
    "exc": ["excavat", "digging", "earthwork", "pit"], "pcc": ["pcc", "lean concrete", "blinding concrete", "blinding"],
    "reb": ["rebar", "reinforc"], "con": ["concret", "casting", "raft"], "bkf": ["backfill", "soil filling"],
    "erc": ["erect", "spool", "shifted"], "wld": ["weld"], "hyd": ["hydro", "pressure test"], "pnt": ["paint", "coating"],
    "tray": ["tray"], "pull": ["pulling", "cable laid", "cable laying", "pull"], "term": ["terminat", "gland", "lugging"],
    "meg": ["megger", "insulation resistance"], "inst": ["transmitter", "instrument"], "cal": ["calibrat"], "loop": ["loop"]}
WEAK = {"transmitter", "instrument"}
START = re.compile(r"\b(start(?:ed)?|commenc\w+|began|begun|mobili[sz]ed|kick(?:ed)? off)\b", re.I)
FIN = re.compile(r"\b(complet\w+|finish\w+|done|closed out|signed off)\b|\b100\s*%", re.I)
PROG = re.compile(r"in progress|ongoing|continu\w+|\bwip\b|\d{1,2}\s*%", re.I)
PAST = re.compile(r"\b(erected|poured|laid|terminated|installed|calibrated|backfilled|excavated|welded|painted|dug)\b", re.I)
FUTURE = re.compile(r"\b(yet to|to start|to begin|tomorrow|planned)\b", re.I)
LINE_RE = re.compile(r'(\d{1,2})\s*(?:"|”|in(?:ch)?\b)?\s*[- ]?\s*([A-Za-z]{2})\s*[-–]\s*(\d{3})')
TAG_RE = re.compile(r"\b([A-Za-z]{2,4})[-–]([A-Za-z]?\d{1,3})\b")
DISC_RE = re.compile(r"^\W*(civil|piping|electrical|instrumentation|hse)\W*$", re.I)


def detect_kind(text):
    low = text.lower(); best, bs = None, 0
    for k, kws in KIND_KW.items():
        s = sum(1 if w in WEAK else len(w) for w in kws if w in low)
        if s > bs: best, bs = k, s
    return best


def find_tag(text):
    m = LINE_RE.search(text)
    if m: return f'{m.group(1)}"-{m.group(2).upper()}-{m.group(3)}'
    m = TAG_RE.search(text)
    return f"{m.group(1).upper()}-{m.group(2).upper()}" if m else None


def clean_text(t):
    t = LINE_RE.sub(" ", t); t = TAG_RE.sub(" ", t)
    for r in (START, FIN, PROG, PAST): t = r.sub(" ", t)
    return re.sub(r"[^a-z ]", " ", t.lower()).strip()


def parse_date(s):
    for f in ("%d-%b-%Y", "%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%d %b %Y"):
        try: return dt.datetime.strptime(s.strip(), f).date()
        except ValueError: pass
    return None


# ---------------- extraction ----------------
def _event(raw, date, disc, doc, status=None, pct=None):
    if FUTURE.search(raw): return None
    if status:
        s = status.lower()
        ev = "start" if "start" in s else "finish" if ("complet" in s or "done" in s) else "progress"
        if pct is not None and float(pct) >= 100: ev = "finish"
    elif START.search(raw): ev = "start"
    elif FIN.search(raw): ev = "finish"
    elif PROG.search(raw): ev = "progress"
    elif PAST.search(raw): ev = "finish"
    else: return None
    if pct is None:
        m = re.search(r"(\d{1,3})\s*%", raw); pct = int(m.group(1)) if m else None
    if date and re.search(r"\byesterday\b", raw, re.I): date = date - dt.timedelta(days=1)
    return dict(doc=doc, raw=raw, event=ev, date=date, discipline=disc, tag=find_tag(raw), pct=pct)


def extract_text(text, doc="report", date=None):
    out, disc = [], None
    for line in re.split(r"[\n;]", text):
        s = line.strip()
        if not s: continue
        m = re.match(r"(?i)date\s*[:\-]\s*(.+)", s)
        if m: date = parse_date(m.group(1)) or date; continue
        m = DISC_RE.match(s)
        if m: disc = m.group(1).title() if m.group(1).lower() != "hse" else "HSE"; continue
        s = re.sub(r"^(?:[-*•]|\d+[.)])\s+", "", s)
        e = _event(s, date, disc, doc)
        if e: out.append(e)
    return out


def extract_chat(text, doc="chat", date=None):
    out = []
    for line in text.splitlines():
        s = line.strip()
        if not s: continue
        m = re.match(r"(?i)(civil|piping|electrical|instrumentation|hse)\s*[:\-]\s*(.*)", s)
        disc, body = (m.group(1).title(), m.group(2)) if m else (None, s)
        e = _event(body, date, disc, doc)
        if e: out.append(e)
    return out


def extract_sheet(df, doc="sheet"):
    out = []
    for _, r in df.iterrows():
        d = parse_date(str(r.get("Date", ""))) if r.get("Date") is not None else None
        pct = r.get("% Complete"); pct = None if pd.isna(pct) else pct
        e = _event(str(r["Work Description"]), d, r.get("Discipline"), doc, status=str(r.get("Status", "")), pct=pct)
        if e: out.append(e)
    return out


# ---------------- hybrid linking ----------------
class Linker:
    def __init__(self, sched):
        self.s = sched.reset_index(drop=True)
        names = self.s["name"].tolist()
        self.kinds = [detect_kind(n) for n in names]
        self.ctags = [find_tag(t) for t in self.s["tag"]]
        self.known = set(self.ctags)
        self.vec = TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True).fit([clean_text(n) for n in names])
        self.M = self.vec.transform([clean_text(n) for n in names])

    def rank(self, raw, tag=None, date=None, disc=None, k=3):
        if tag and tag not in self.known:
            return dict(cands=[], best=None, conf=0.0, status="unmatched", reason=f"tag {tag} not in schedule (new activity?)")
        kind = detect_kind(raw)
        txt = cosine_similarity(self.vec.transform([clean_text(raw)]), self.M)[0]
        sc = np.zeros(len(self.s))
        for i, r in self.s.iterrows():
            dw = 0.5
            if date:
                gap = max((r.planned_start - dt.timedelta(days=1) - date).days, (date - r.planned_end - dt.timedelta(days=1)).days, 0)
                dw = 1 / (1 + gap / 3)
            s = 0.40 * (kind is not None and kind == self.kinds[i]) + 0.30 * (tag is not None and tag == self.ctags[i]) \
                + 0.15 * dw + 0.15 * txt[i]
            if disc and disc != r.discipline: s *= 0.85
            sc[i] = s
        top = np.argsort(-sc)[:k]
        cands = [(self.s.id[i], round(float(sc[i]), 3)) for i in top]
        conf = float(sc[top[0]])
        status = "auto" if conf >= AUTO else "review" if conf >= REVIEW else "unmatched"
        why = {"auto": "kind+tag+date agree", "review": "ambiguous (e.g. no tag) - planner to confirm",
               "unmatched": "no plan activity fits - flagged as possible new activity"}[status]
        return dict(cands=cands, best=cands[0][0], conf=conf, status=status, reason=why)


# ---------------- validation + audit ----------------
class Store:
    def __init__(self, sched):
        self.sched = sched; self.actual = {}; self.audit = []

    def apply(self, ev, act_id, conf, status):
        a = self.actual.setdefault(act_id, {"start": None, "end": None, "pct": 0}); w = []; d = ev["date"]; e = ev["event"]
        if e == "start":
            if a["start"]: w.append("duplicate start report (earliest kept)"); a["start"] = min(a["start"], d) if d else a["start"]
            else: a["start"] = d
        elif e == "progress":
            if not a["start"]: a["start"] = d; w.append("start inferred from first progress evidence")
            if ev.get("pct"): a["pct"] = max(a["pct"], int(ev["pct"]))
        elif e == "finish":
            if not a["start"]: w.append("finish reported with no start on record")
            elif d and d < a["start"]: w.append("finish date before start date")
            if a["end"]: w.append("activity already finished")
            else: a["end"] = d; a["pct"] = 100
        self.audit.append(dict(time=dt.datetime.now().isoformat(timespec="seconds"), activity_id=act_id, event=e, date=d,
                               confidence=round(conf, 2), status=status, source=ev["doc"], text=ev["raw"], warnings="; ".join(w)))
        return w

    def table(self):
        t = self.sched[["id", "discipline", "name", "planned_start", "planned_end"]].copy()
        t["actual_start"] = t.id.map(lambda i: self.actual.get(i, {}).get("start"))
        t["actual_end"] = t.id.map(lambda i: self.actual.get(i, {}).get("end"))
        t["% done"] = t.id.map(lambda i: self.actual.get(i, {}).get("pct", 0))
        t["start_var_days"] = [(a - p).days if a else None for a, p in zip(t.actual_start, t.planned_start)]
        return t


def process(events, linker, store, default_date=None):
    rows = []
    for ev in events:
        if ev["date"] is None: ev["date"] = default_date
        r = linker.rank(ev["raw"], ev["tag"], ev["date"], ev["discipline"])
        row = dict(source=ev["doc"], text=ev["raw"], event=ev["event"], date=ev["date"], tag=ev["tag"], pct=ev["pct"],
                   activity_id=r["best"], confidence=round(r["conf"], 2), status=r["status"], reason=r["reason"],
                   cands=r["cands"], _ev=ev)
        if r["status"] == "auto": row["warnings"] = "; ".join(store.apply(ev, r["best"], r["conf"], "auto"))
        rows.append(row)
    return rows


# ---------------- institutional memory (synthetic past projects) ----------------
CAUSES = ["material delay", "rework", "weather", "manpower shortage", "permit / PTW delay", "design change"]


def history(sched, seed=7):
    rng = random.Random(seed); rows = []
    for proj in ("Project-A", "Project-B", "Project-C", "Project-D"):
        for _, r in sched.iterrows():
            p = (r.planned_end - r.planned_start).days + 1
            a = max(1, round(p * rng.uniform(0.9, 1.7)))
            rows.append(dict(project=proj, kind=r.kind_true, discipline=r.discipline, activity=r["name"].split(" ")[0],
                             planned_days=p, actual_days=a, delay_cause=rng.choice(CAUSES) if a > p else ""))
    return pd.DataFrame(rows)


def memory_answer(q, hist):
    k = detect_kind(q)
    if not k: return None, "Couldn't tell which activity you mean - try e.g. 'typical duration of pipe erection'."
    h = hist[hist.kind == k]
    causes = h[h.delay_cause != ""].delay_cause.value_counts().head(3)
    txt = (f"**{PLAN[k].split(' {')[0]}** across {h.project.nunique()} past projects: planned avg {h.planned_days.mean():.1f} d, "
           f"actual avg {h.actual_days.mean():.1f} d ({(h.actual_days.mean()/h.planned_days.mean()-1)*100:+.0f}%). "
           f"Top delay causes: {', '.join(f'{c} ({n})' for c, n in causes.items())}.")
    return h, txt
