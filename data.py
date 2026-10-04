"""Synthetic L5/L6 schedule, field-language phrases and sample inputs (modeled on typical DPR / discipline sheets)."""
import datetime as dt
import pandas as pd

D0 = dt.date(2026, 3, 2)
DISC = {"exc": "Civil", "pcc": "Civil", "reb": "Civil", "con": "Civil", "bkf": "Civil",
        "erc": "Piping", "wld": "Piping", "hyd": "Piping", "pnt": "Piping",
        "tray": "Electrical", "pull": "Electrical", "term": "Electrical", "meg": "Electrical",
        "inst": "Instrumentation", "cal": "Instrumentation", "loop": "Instrumentation"}
PLAN = {"exc": "Excavation for foundation {t}", "pcc": "PCC for foundation {t}",
        "reb": "Rebar fixing for foundation {t}", "con": "Concrete pour for foundation {t}",
        "bkf": "Backfilling of foundation {t}", "erc": "Erect Line {t}", "wld": "Weld Line {t}",
        "hyd": "Hydrotest Line {t}", "pnt": "Paint Line {t}", "tray": "Install cable tray {t}",
        "pull": "Pull power cable {t}", "term": "Terminate cable {t}", "meg": "Megger test cable {t}",
        "inst": "Install transmitter {t}", "cal": "Calibrate transmitter {t}", "loop": "Loop check {t}"}
# How supervisors actually say it ({t} = equipment/line tag, may be dropped)
PHRASES = {
    "exc": ["excavation for {t}", "digging of {t} pit", "earthwork at {t}"],
    "pcc": ["PCC for {t}", "lean concrete below {t}", "blinding concrete {t}"],
    "reb": ["rebar fixing {t}", "reinforcement tying for {t}", "rebar cage of {t}"],
    "con": ["concrete pour {t}", "concreting of {t}", "raft casting {t}"],
    "bkf": ["backfilling {t}", "soil filling around {t}"],
    "erc": ["spool erection {t}", "erection of pipe spools for {t}", "pipe spools shifted and fixed on {t}"],
    "wld": ["welding on {t}", "weld joints of {t}", "butt welding {t}"],
    "hyd": ["hydrotest of {t}", "pressure test on {t}", "hydro testing {t}"],
    "pnt": ["painting of {t}", "coating work on {t}"],
    "tray": ["cable tray installation {t}", "tray fixing at {t}", "laying of cable trays {t}"],
    "pull": ["cable pulling {t}", "power cable laid for {t}", "cable laying {t}"],
    "term": ["cable termination {t}", "glanding and lugging of {t}", "terminating cables {t}"],
    "meg": ["megger test {t}", "insulation resistance test {t}"],
    "inst": ["transmitter installation {t}", "mounting of instrument {t}", "fixing {t} transmitter"],
    "cal": ["calibration of {t}", "calibrating instrument {t}"],
    "loop": ["loop check {t}", "loop testing {t}"]}
WRAP = {"start": ["{d} started", "commenced {d}", "{d} kicked off", "started {d}"],
        "finish": ["{d} completed", "{d} done", "completed {d}", "{d} finished", "{d} 100% complete"],
        "progress": ["{d} in progress (40%)", "{d} ongoing", "{d} in progress (70%)"]}
# Work that is NOT in the plan (should be flagged, never silently linked)
DISTRACT = ["scaffolding erection near tank T-5", "housekeeping of laydown area", "crane inspection by third party",
            "welder qualification test", "site barricading near gate 2", "temporary lighting at tank T-5"]


def build_schedule() -> pd.DataFrame:
    rows = []

    def add(kind, tag, off, dur):
        rows.append(dict(id=f"A{len(rows)+1:04d}", discipline=DISC[kind], name=PLAN[kind].format(t=tag), tag=tag,
                         planned_start=D0 + dt.timedelta(days=off),
                         planned_end=D0 + dt.timedelta(days=off + dur - 1), kind_true=kind))
    for i in range(3):
        for k, o, d in [("exc", 0, 3), ("pcc", 3, 1), ("reb", 4, 3), ("con", 7, 1), ("bkf", 9, 2)]:
            add(k, f"FDN-P{101+i}", i * 3 + o, d)
    for i, t in enumerate(['24"-PW-101', '16"-CW-102', '12"-FW-103']):
        for k, o, d in [("erc", 0, 5), ("wld", 5, 6), ("hyd", 11, 2), ("pnt", 13, 3)]:
            add(k, t, 10 + i * 4 + o, d)
    for i in range(3):
        add("tray", f"TRY-A{i+1}", 12 + i * 3, 4)
        for k, o, d in [("pull", 0, 3), ("term", 3, 2), ("meg", 5, 1)]:
            add(k, f"CBL-P{101+i}", 18 + i * 2 + o, d)
        for k, o, d in [("inst", 0, 2), ("cal", 2, 1), ("loop", 3, 1)]:
            add(k, f"PT-{101+i}", 22 + i * 2 + o, d)
    return pd.DataFrame(rows)


SAMPLE_DATE = dt.date(2026, 3, 14)
SAMPLE_REPORT = """DAILY PROGRESS REPORT
Date: 14-Mar-2026
Contractor: M/s Sharma Constructions
[CIVIL]
- rebar tying for FDN-P103 completed
- earthwork at FDN-P103 done
[PIPING]
- pipe spools shifted and fixed on 24in-PW-101 in progress (60%)
- welding on 16 inch CW-102 to start tomorrow
[ELECTRICAL]
- laying of cable trays TRY-A1 started
- power cable laid for CBL-P101
[HSE]
- scaffolding erection near tank T-5 completed
- housekeeping of laydown area done
"""
SAMPLE_SHEET = pd.DataFrame([
    ["2026-03-14", "Civil", "lean concrete below FDN-P102", "Completed", 100],
    ["2026-03-14", "Piping", "hydro testing 24in-PW-101", "Started", 0],
    ["2026-03-14", "Electrical", "glanding and lugging of CBL-P102", "WIP", 30],
    ["2026-03-14", "Instrumentation", "fixing PT-101 transmitter", "Started", 0],
], columns=["Date", "Discipline", "Work Description", "Status", "% Complete"])
SAMPLE_CHAT = """Civil: concreting of FDN-P103 just started
Piping: spool erection 24" PW-101 completed
Instrumentation: mounting of instrument PT-101 done
Electrical: tray fixing completed"""
