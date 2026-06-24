#!/usr/bin/env python3
import csv
import re
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parents[1]
CSV_PATH = ROOT / "fixtures.csv"
OUT_PATH = ROOT / "docs" / "fixtures.ics"

def clean_time(t):
    if t is None:
        return None
    return t.strip().replace(';', ':')

def parse_title(title):
    m = re.match(r'^(.*?)(?:\s*\((H|A)\))?\s*$', title.strip())
    if not m:
        return title.strip(), ""
    opp = m.group(1).strip()
    ha = m.group(2)
    return opp, ("Home" if ha == "H" else "Away" if ha == "A" else "")

def fmt_dt_local(date_str, time_str):
    dt = datetime.fromisoformat(f"{date_str}T{time_str}")
    return dt.strftime("%Y%m%dT%H%M%S")

def escape_text(s):
    return s.replace('\\', '\\\\').replace('\n', '\\n').replace(',', '\\,').replace(';', '\\;').replace(':', '\\:')

def build_vtimezone():
    return [
        "BEGIN:VTIMEZONE",
        "TZID:Europe/London",
        "X-LIC-LOCATION:Europe/London",
        "BEGIN:DAYLIGHT",
        "TZOFFSETFROM:+0000",
        "TZOFFSETTO:+0100",
        "TZNAME:BST",
        "DTSTART:19700329T010000",
        "RRULE:FREQ=YEARLY;BYMONTH=3;BYDAY=-1SU",
        "END:DAYLIGHT",
        "BEGIN:STANDARD",
        "TZOFFSETFROM:+0100",
        "TZOFFSETTO:+0000",
        "TZNAME:GMT",
        "DTSTART:19701025T020000",
        "RRULE:FREQ=YEARLY;BYMONTH=10;BYDAY=-1SU",
        "END:STANDARD",
        "END:VTIMEZONE",
    ]

def main():
    if not CSV_PATH.exists():
        print(f"CSV not found at {CSV_PATH}")
        return

    rows = []
    with CSV_PATH.open(newline='') as f:
        reader = csv.DictReader(f)
        for r in reader:
            date = r.get("Date") or r.get("date")
            start = clean_time(r.get("StartTime") or r.get("Start"))
            end = clean_time(r.get("EndTime") or r.get("End"))
            title = r.get("Title") or r.get("Opponent") or ""
            location = (r.get("Location") or r.get("Venue") or "").strip()
            notes = (r.get("Notes") or "").strip()
            if not date or not start:
                continue
            opponent, homeaway = parse_title(title)
            dtstart = fmt_dt_local(date, start)
            dtend = fmt_dt_local(date, end if end else start)
            rows.append({
                "date": date,
                "start": start,
                "end": end,
                "dtstart": dtstart,
                "dtend": dtend,
                "opponent": opponent,
                "homeaway": homeaway,
                "location": location,
                "notes": notes,
            })

    rows.sort(key=lambda r: r["dtstart"]) 

    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//gbebbs/RuncornTownFixtures//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        "X-WR-CALNAME:Runcorn Town Fixtures",
        "X-WR-TIMEZONE:Europe/London",
    ]
    lines += build_vtimezone()

    now_ts = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    for i, r in enumerate(rows, start=1):
        uid = f"fixture-{i}-{r['dtstart']}@gbebbs.github.io"
        desc_lines = []
        if r["notes"]:
            desc_lines.append(r["notes"])
        if r["location"]:
            desc_lines.append(f"Venue: {r['location']}")
        description = "\\n".join(escape_text(x) for x in desc_lines) if desc_lines else ""
        lines += [
            "BEGIN:VEVENT",
            f"UID:{uid}",
            f"DTSTAMP:{now_ts}",
            f"DTSTART;TZID=Europe/London:{r['dtstart']}",
            f"DTEND;TZID=Europe/London:{r['dtend']}",
            f"SUMMARY:Runcorn Town vs {escape_text(r['opponent'])}" + (f" ({r['homeaway']})" if r['homeaway'] else ""),
            f"LOCATION:{escape_text(r['location'])}" if r['location'] else "LOCATION:",
            f"DESCRIPTION:{description}" if description else "DESCRIPTION:",
            "END:VEVENT",
            "",
        ]

    lines.append("END:VCALENDAR")
    content = "\r\n".join(lines) + "\r\n"

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    old = ""
    if OUT_PATH.exists():
        old = OUT_PATH.read_bytes().decode("utf-8", errors="ignore")
    if old != content:
        OUT_PATH.write_bytes(content.encode("utf-8"))
        print(f"Wrote {OUT_PATH}")
    else:
        print("No changes to ICS")

if __name__ == "__main__":
    main()
