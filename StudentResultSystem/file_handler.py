# file_handler.py - reads files and exports csv
# this file parses text files to extract student data
# also handles saving to csv and opening in explorer

from __future__ import annotations

import csv
import io
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

import pandas as pd
from tabulate import tabulate

import database


def readcsvstuds(p):
    # read students from csv file
    return pd.read_csv(p)


def readcsvmarks(p):
    # read marks from csv file
    return pd.read_csv(p)


def savecsv(df, out, rname=None):
    # save dataframe to csv file
    # rname = report name, gets added as a column in csv
    out = Path(out).resolve()
    if not str(out).lower().endswith(".csv"):
        out = out.with_name(f"{out.name}.csv")
    out.parent.mkdir(parents=True, exist_ok=True)
    d = df.copy()
    if rname:
        d.insert(0, "Report_Name", rname)
    d.to_csv(out, index=False)
    return out


def showfile(fp):
    # open file in explorer so u can see it right away
    p = Path(fp).resolve()
    if not p.exists():
        return False, f"File does not exist: {p}"

    try:
        if sys.platform == "win32":
            subprocess.run(["explorer", f"/select,{str(p)}"], check=False)
            return True, f"Revealed in Explorer: {p.name}"
        elif sys.platform == "darwin":
            subprocess.run(["open", "-R", str(p)], check=False)
            return True, f"Revealed in Finder: {p.name}"
        else:
            subprocess.run(["xdg-open", str(p.parent)], check=False)
            return True, f"Opened directory: {p.parent}"
    except Exception as e:
        return False, f"Could not reveal file: {e}"


def maketxtreport(rows, out):
    # make a text report file with nice table format
    rp = Path(out).resolve()
    rp.parent.mkdir(parents=True, exist_ok=True)
    tbl = tabulate(list(rows), headers="keys", tablefmt="grid")
    rp.write_text(tbl, encoding="utf-8")
    return rp


def makereportcard(rows):
    # build report card string for one student
    if not rows:
        return "No report data found."
    stud = rows[0]
    data = []
    totgot = 0.0
    totmax = 0.0
    for r in rows:
        if r.get("subject_name") is None:
            continue
        got = float(r.get("marks_obtained") or 0)
        mx = float(r.get("max_marks") or 0)
        totgot += got
        totmax += mx
        data.append({
            "Subject": r["subject_name"],
            "Marks Obtained": got,
            "Max Marks": mx,
        })

    # percentage and grade
    pct = round(totgot / totmax * 100, 2) if totmax else 0.0
    if pct >= 90:
        grd = "A+"
    elif pct >= 80:
        grd = "A"
    elif pct >= 70:
        grd = "B"
    elif pct >= 60:
        grd = "C"
    elif pct >= 50:
        grd = "D"
    else:
        grd = "F"

    lines = [
        "Student Report Card",
        f"Roll No: {stud.get('roll_no', '')}",
        f"Name: {stud.get('name', '')}",
        f"Class: {stud.get('class_name', '')}",
        f"Section: {stud.get('section', '')}",
        f"Phone: {stud.get('phone') or 'N/A'}",
        f"Email: {stud.get('email') or 'N/A'}",
        "",
        tabulate(data, headers="keys", tablefmt="grid") if data else "No marks found.",
        "",
        f"Total: {round(totgot, 2)} / {round(totmax, 2)}",
        f"Percentage: {pct}%",
        f"Grade: {grd}",
    ]
    return "\n".join(lines)


def savereportcsv(rows, out, rname=None):
    # export student report card to csv
    if not rows:
        df = pd.DataFrame(columns=["Roll No", "Name", "Class", "Section", "Subject", "Marks Obtained", "Max Marks"])
        return savecsv(df, out, rname=rname)

    stud = rows[0]
    data = []
    totgot = 0.0
    totmax = 0.0
    for r in rows:
        sub = r.get("subject_name")
        if not sub:
            continue
        got = float(r.get("marks_obtained") or 0)
        mx = float(r.get("max_marks") or 0)
        totgot += got
        totmax += mx
        data.append({
            "Roll No": stud.get("roll_no", ""),
            "Name": stud.get("name", ""),
            "Class": stud.get("class_name", ""),
            "Section": stud.get("section", ""),
            "Subject": sub,
            "Marks Obtained": got,
            "Max Marks": mx,
        })

    # total row at bottom
    if data:
        data.append({
            "Roll No": stud.get("roll_no", ""),
            "Name": stud.get("name", ""),
            "Class": stud.get("class_name", ""),
            "Section": stud.get("section", ""),
            "Subject": "TOTAL",
            "Marks Obtained": round(totgot, 2),
            "Max Marks": round(totmax, 2),
        })

    df = pd.DataFrame(data)
    return savecsv(df, out, rname=rname)


# ========== TEXT FILE PARSING ==========
# this section reads text files and pulls out student + marks data
# works with comma/tab/pipe separated rows or block format (key: value style)

def cleankey(k):
    # maps different header names to standard ones
    # like "roll" or "rollno" both become "roll_no"
    c = k.strip().lower().replace(" ", "_").replace("-", "_")
    mp = {
        "roll": "roll_no",
        "roll_no": "roll_no",
        "rollno": "roll_no",
        "roll_number": "roll_no",
        "id": "roll_no",
        "student_name": "name",
        "name": "name",
        "student": "name",
        "class": "class_name",
        "class_name": "class_name",
        "standard": "class_name",
        "grade": "class_name",
        "section": "section",
        "sec": "section",
        "phone": "phone",
        "phone_no": "phone",
        "mobile": "phone",
        "contact": "phone",
        "email": "email",
        "email_id": "email",
        "mail": "email",
        "subject": "subject_name",
        "subject_name": "subject_name",
        "sub": "subject_name",
        "marks_obtained": "marks_obtained",
        "marks": "marks_obtained",
        "score": "marks_obtained",
        "mark": "marks_obtained",
        "obtained": "marks_obtained",
        "max_marks": "max_marks",
        "max": "max_marks",
        "total_marks": "max_marks",
    }
    return mp.get(c, c)


def parsemarkval(v):
    # parse mark values like "85/100" or just "85" (assumes max 100)
    v = str(v).strip()
    if "/" in v:
        parts = v.split("/")
        got = float(parts[0].strip())
        mx = float(parts[1].strip())
        return got, mx
    got = float(v)
    return got, 100.0


def parsetxt(src):
    # THE MAIN PARSER - reads text and extracts students + marks
    # handles two formats:
    # 1. block format (Roll No: 1, Name: xyz etc on separate lines)
    # 2. delimited format (comma/tab/pipe separated rows like csv)

    if isinstance(src, Path) or (isinstance(src, str) and "\n" not in src and Path(src).exists()):
        fp = Path(src)
        try:
            raw = fp.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            raw = fp.read_text(encoding="latin-1")
    else:
        raw = str(src)

    studs = {}  # found students
    mks = []    # found marks
    errs = []   # warnings

    lines = [l.strip() for l in raw.splitlines()]
    good = [l for l in lines if l]

    if not good:
        return {
            "students": [],
            "marks": [],
            "errors": ["File is empty."],
            "raw_line_count": 0,
        }

    # check if its block format or delimited
    blockcnt = sum(
        1 for l in good if re.match(r"^(roll|roll_no|roll\s*no|name|student|class)\s*:", l, re.IGNORECASE)
    )

    if blockcnt >= 2:
        # BLOCK FORMAT - each student is key:value pairs
        blocks = re.split(r"\n\s*(?:[-=]{3,}|\n)\s*", raw)
        for bi, blk in enumerate(blocks, start=1):
            blines = [b.strip() for b in blk.splitlines() if b.strip() and not b.strip().startswith("#")]
            if not blines:
                continue

            sd = {}
            inmarks = False

            for ln in blines:
                if any(d in ln for d in ["|", "\t", ","]) and ":" not in ln:
                    dlm = "|" if "|" in ln else ("\t" if "\t" in ln else ",")
                    pts = [p.strip() for p in ln.split(dlm)]
                    if len(pts) >= 4:
                        rno = pts[0]
                        studs[rno] = {
                            "roll_no": rno,
                            "name": pts[1] if len(pts) > 1 else "Unknown",
                            "class_name": pts[2] if len(pts) > 2 else "10",
                            "section": pts[3] if len(pts) > 3 else "A",
                            "phone": pts[4] if len(pts) > 4 and pts[4] else None,
                            "email": pts[5] if len(pts) > 5 and pts[5] else None,
                        }
                        if len(pts) >= 8:
                            sn = pts[6]
                            try:
                                g, x = parsemarkval(f"{pts[7]}/{pts[8]}" if len(pts) > 8 else pts[7])
                                mks.append({
                                    "roll_no": rno,
                                    "subject_name": sn,
                                    "marks_obtained": g,
                                    "max_marks": x,
                                })
                            except Exception:
                                pass
                        continue

                if re.match(r"^marks?\s*:", ln, re.IGNORECASE):
                    inmarks = True
                    after = ln.split(":", 1)[1].strip()
                    if after:
                        items = after.split(",")
                        for itm in items:
                            if ":" in itm:
                                sn, mv = itm.split(":", 1)
                                try:
                                    g, x = parsemarkval(mv)
                                    rno = sd.get("roll_no")
                                    if rno:
                                        mks.append({
                                            "roll_no": rno,
                                            "subject_name": sn.strip(),
                                            "marks_obtained": g,
                                            "max_marks": x,
                                        })
                                except Exception:
                                    pass
                    continue

                if inmarks:
                    mm = re.match(r"^([A-Za-z0-9\s]+?)\s*[:=-]\s*([0-9.]+(?:\s*/\s*[0-9.]+)?)$", ln)
                    if mm:
                        sn = mm.group(1).strip()
                        mv = mm.group(2).strip()
                        try:
                            g, x = parsemarkval(mv)
                            rno = sd.get("roll_no")
                            if rno:
                                mks.append({
                                    "roll_no": rno,
                                    "subject_name": sn,
                                    "marks_obtained": g,
                                    "max_marks": x,
                                })
                            else:
                                errs.append(f"Mark found for {sn} before roll_no defined in block {bi}.")
                        except Exception as e:
                            errs.append(f"Invalid mark value '{mv}' for subject '{sn}': {e}")
                        continue
                    else:
                        inmarks = False

                if ":" in ln:
                    k, v = ln.split(":", 1)
                    ck = cleankey(k)
                    cv = v.strip()
                    sd[ck] = cv

            rno = sd.get("roll_no")
            if rno:
                studs[rno] = {
                    "roll_no": rno,
                    "name": sd.get("name", "Unknown"),
                    "class_name": sd.get("class_name", "10"),
                    "section": sd.get("section", "A"),
                    "phone": sd.get("phone") or None,
                    "email": sd.get("email") or None,
                }
            elif blines and not any(r in studs for r in studs):
                errs.append(f"Block {bi} missing 'Roll No'.")

    else:
        # DELIMITED FORMAT - rows and columns like csv
        first = good[0]
        dlm = ","
        for d in ["\t", "|", ";", ","]:
            if d in first:
                dlm = d
                break

        rdr = csv.reader(io.StringIO(raw), delimiter=dlm)
        allrows = [r for r in rdr if r and any(c.strip() for c in r)]

        if not allrows:
            return {
                "students": [],
                "marks": [],
                "errors": ["No data rows detected."],
                "raw_line_count": len(lines),
            }

        hdrs = [cleankey(c) for c in allrows[0]]

        hashdr = any(h in ["roll_no", "name", "class_name", "subject_name"] for h in hdrs)
        start = 1 if hashdr else 0

        defhdrs = ["roll_no", "name", "class_name", "section", "phone", "email"]
        usehdrs = hdrs if hashdr else defhdrs

        for ri, row in enumerate(allrows[start:], start=start + 1):
            rd = {}
            for i, cell in enumerate(row):
                v = cell.strip()
                if i < len(usehdrs):
                    rd[usehdrs[i]] = v
                else:
                    rd[f"col_{i}"] = v

            rno = rd.get("roll_no")
            if not rno and row:
                rno = row[0].strip()
                rd["roll_no"] = rno

            if not rno:
                continue

            if rno not in studs:
                studs[rno] = {
                    "roll_no": rno,
                    "name": rd.get("name", "Unknown"),
                    "class_name": rd.get("class_name", "10"),
                    "section": rd.get("section", "A"),
                    "phone": rd.get("phone") or None,
                    "email": rd.get("email") or None,
                }
            else:
                for f in ["name", "class_name", "section", "phone", "email"]:
                    if rd.get(f) and not studs[rno].get(f):
                        studs[rno][f] = rd[f]

            sn = rd.get("subject_name")
            mv = rd.get("marks_obtained")
            xv = rd.get("max_marks", "100")

            if sn and mv is not None and str(mv).strip() != "":
                try:
                    g, x = parsemarkval(f"{mv}/{xv}" if "/" not in str(mv) else str(mv))
                    mks.append({
                        "roll_no": rno,
                        "subject_name": sn,
                        "marks_obtained": g,
                        "max_marks": x,
                    })
                except Exception as e:
                    errs.append(f"Row {ri}: Invalid marks for {sn}: {e}")

    return {
        "students": list(studs.values()),
        "marks": mks,
        "errors": errs,
        "raw_line_count": len(lines),
    }


def savetodb(parsed, cfg=None):
    # save parsed data into mysql
    # uses upsert so running twice wont create duplicates
    database.initdb(cfg)

    saved = 0
    msaved = 0
    dberrs = []

    for st in parsed.get("students", []):
        try:
            database.upsertstud(
                rno=st["roll_no"],
                nm=st["name"],
                cls=st["class_name"],
                sec=st["section"],
                ph=st.get("phone"),
                em=st.get("email"),
                cfg=cfg,
            )
            saved += 1
        except Exception as e:
            dberrs.append(f"Error saving student {st.get('roll_no')}: {e}")

    for mk in parsed.get("marks", []):
        try:
            sid = database.getorcreatesub(mk["subject_name"], cfg=cfg)
            database.upsertmark(
                rno=mk["roll_no"],
                subid=sid,
                got=float(mk["marks_obtained"]),
                mx=float(mk["max_marks"]),
                cfg=cfg,
            )
            msaved += 1
        except Exception as e:
            dberrs.append(f"Error saving mark for {mk.get('roll_no')} - {mk.get('subject_name')}: {e}")

    return {
        "students_saved": saved,
        "marks_saved": msaved,
        "errors": dberrs,
    }
