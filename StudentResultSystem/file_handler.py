# file_handler.py - parses text files and saves student data to mysql
# supports official CBSE Gazette files (.txt), wide tables, and block format

import csv
import io
import re
from pathlib import Path
import database

# official CBSE subject code mapping
CBSE_CODES = {
    # Languages
    "301": "English",
    "302": "Hindi",
    "303": "Urdu",
    "304": "Sanskrit",
    "318": "Tamil",
    "322": "Sanskrit Core",
    "001": "English Elective",
    "002": "Hindi Elective",
    "022": "Sanskrit Elective",
    "101": "English Communicative",
    # Science & Tech
    "041": "Math",
    "042": "Physics",
    "043": "Chemistry",
    "044": "Biology",
    "048": "Physical Education",
    "083": "Computer Science",
    "065": "Information Practices",
    "045": "Biotechnology",
    "241": "Applied Mathematics",
    # Commerce & Management
    "030": "Economics",
    "054": "Business Studies",
    "055": "Accountancy",
    "066": "Entrepreneurship",
    # Humanities & Social Sciences
    "027": "History",
    "028": "Political Science",
    "029": "Geography",
    "037": "Psychology",
    "039": "Sociology",
    "074": "Legal Studies",
    "049": "Painting",
    "050": "Graphics",
    "051": "Sculpture",
    "052": "Applied Art",
    "064": "Home Science",
}

# common subject name aliases
SUB_MAP = {
    "eng": "English", "english": "English",
    "mat": "Math", "math": "Math", "maths": "Math", "mathematics": "Math",
    "phy": "Physics", "physics": "Physics",
    "chem": "Chemistry", "chemistry": "Chemistry",
    "bio": "Biology", "biology": "Biology",
    "cs": "Computer Science", "computer science": "Computer Science",
    "ip": "Information Practices", "information practices": "Information Practices",
    "eco": "Economics", "economics": "Economics",
    "bst": "Business Studies", "business studies": "Business Studies",
    "acc": "Accountancy", "accounts": "Accountancy", "accountancy": "Accountancy",
    "hist": "History", "history": "History",
    "pol": "Political Science", "pol sci": "Political Science", "political science": "Political Science",
    "psych": "Psychology", "psychology": "Psychology",
    "soc": "Sociology", "sociology": "Sociology",
}


def fixsub(s):
    # cleans up subject name
    k = s.strip().lower()
    return SUB_MAP.get(k, s.strip().title())


def parseval(v):
    # parse marks like 95 or 95/100
    s = str(v).strip()
    if "/" in s:
        p1, p2 = s.split("/", 1)
        return float(p1.strip()), float(p2.strip())
    return float(s), 100.0


def parsecbse(raw, def_cls="STD XII", def_sec="A"):
    # parser for official CBSE Gazette text files
    # extracts school name, exam year, roll no, student name, and all subject marks
    sch_m = re.search(r"SCHOOL\s*:\s*\d+\s+([^\r\n]+)", raw)
    school = sch_m.group(1).strip() if sch_m else "Chinmaya Vidyalaya"

    ex_m = re.search(r"CBSE-([A-Z\s\-]+EXAMINATION)\s+(\d{4})", raw)
    year = ex_m.group(2).strip() if ex_m else ""
    cls_name = f"STD XII - {year}" if year else def_cls

    studs = {}
    mks = []
    errs = []

    # candidate line regex: 7-8 digit roll number, followed by candidate name, followed by 3-digit subject code
    c_pat = re.compile(r"^\s*(\d{7,8})\s+([A-Za-z\s\.\'\-]+?)\s+(\d{3}\s+.*)$", re.MULTILINE)
    # subject block regex: 3-digit code, marks (optionally with trailing letter F), and grade
    sub_pat = re.compile(r"(\d{3})\s+([0-9]{2,3}[A-Za-z]?|[A-Za-z]{2,3})\s+([A-Z0-9]{1,2})")

    for m in c_pat.finditer(raw):
        rno = m.group(1).strip()
        nm = m.group(2).strip()
        rest = m.group(3)

        if rno not in studs:
            studs[rno] = {"rno": rno, "nm": nm, "cls": cls_name, "sec": def_sec}

        subs = sub_pat.findall(rest)
        if not subs:
            errs.append(f"Student {rno} ({nm}): no subject marks parsed.")

        for sc, mv, gr in subs:
            sub_name = CBSE_CODES.get(sc, f"Sub-{sc}")
            digits = re.sub(r"[^\d\.]", "", mv)
            if digits:
                got = float(digits)
            else:
                got = 0.0  # absent / no mark

            mks.append({"rno": rno, "sub": sub_name, "got": got, "mx": 100.0})

    return {
        "studs": list(studs.values()),
        "marks": mks,
        "errs": errs,
        "meta": {"school": school, "year": year, "class_name": cls_name},
    }


def parsetxt(p, def_cls="STD XII", def_sec="A"):
    # read and parse .txt file (CBSE gazette, block format, or table)
    fp = Path(p) if isinstance(p, (str, Path)) else None
    if fp and fp.exists():
        try:
            raw = fp.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            raw = fp.read_text(encoding="latin-1")
    else:
        raw = str(p)

    lines = [l.strip() for l in raw.splitlines()]
    clean = [l for l in lines if l and not l.startswith("#") and not l.startswith("//")]

    if not clean:
        return {"studs": [], "marks": [], "errs": ["File is empty."], "meta": {}}

    # 1. Check if official CBSE Gazette format
    is_cbse = (
        "CBSE-SENIOR SCHOOL" in raw
        or "CBSE-SECONDARY SCHOOL" in raw
        or bool(re.search(r"^\s*\d{7,8}\s+[A-Za-z\s\.\'\-]+\s+\d{3}\s+[0-9]{2,3}", raw, re.MULTILINE))
    )
    if is_cbse:
        return parsecbse(raw, def_cls=def_cls, def_sec=def_sec)

    studs = {}
    mks = []
    errs = []

    # 2. Check if key-value block format (Roll No: ..., Name: ...)
    is_block = sum(1 for l in clean if re.match(r"^(roll|roll_no|name|class)\s*:", l, re.IGNORECASE)) >= 2

    if is_block:
        blks = re.split(r"\n\s*(?:[-=]{3,}|\n)\s*", raw)
        for b in blks:
            bl = [x.strip() for x in b.splitlines() if x.strip() and not x.strip().startswith("#")]
            if not bl:
                continue

            sd = {"cls": def_cls, "sec": def_sec}
            in_mks = False

            for ln in bl:
                if re.match(r"^marks?\s*:", ln, re.IGNORECASE):
                    in_mks = True
                    after = ln.split(":", 1)[1].strip()
                    if after:
                        for itm in after.split(","):
                            if ":" in itm or "=" in itm:
                                sep = ":" if ":" in itm else "="
                                sn, mv = itm.split(sep, 1)
                                try:
                                    g, x = parseval(mv)
                                    rno = sd.get("rno")
                                    if rno:
                                        mks.append({"rno": rno, "sub": fixsub(sn), "got": g, "mx": x})
                                except Exception:
                                    pass
                    continue

                if in_mks:
                    m = re.match(r"^([A-Za-z0-9\s]+?)\s*[:=-]\s*([0-9.]+(?:\s*/\s*[0-9.]+)?)$", ln)
                    if m:
                        sn, mv = m.group(1).strip(), m.group(2).strip()
                        try:
                            g, x = parseval(mv)
                            rno = sd.get("rno")
                            if rno:
                                mks.append({"rno": rno, "sub": fixsub(sn), "got": g, "mx": x})
                        except Exception:
                            pass
                        continue
                    else:
                        in_mks = False

                if ":" in ln:
                    k, v = ln.split(":", 1)
                    k = k.strip().lower().replace(" ", "_")
                    if k in ("roll", "roll_no", "id"):
                        sd["rno"] = v.strip()
                    elif k in ("name", "student_name"):
                        sd["nm"] = v.strip()
                    elif k in ("class", "class_name", "std"):
                        sd["cls"] = v.strip()
                    elif k in ("section", "sec"):
                        sd["sec"] = v.strip()

            rno = sd.get("rno")
            if rno:
                studs[rno] = {
                    "rno": rno,
                    "nm": sd.get("nm", f"Student {rno}"),
                    "cls": sd.get("cls", def_cls),
                    "sec": sd.get("sec", def_sec),
                }

    else:
        # 3. Delimited or tabular format
        dlm = None
        for d in ["\t", "|", ",", ";"]:
            if d in clean[0]:
                dlm = d
                break

        if dlm:
            rdr = csv.reader(io.StringIO("\n".join(clean)), delimiter=dlm)
            rows = [[c.strip() for c in r] for r in rdr if r and any(c.strip() for c in r)]
        else:
            rows = [re.split(r"\s{2,}|\t", l) for l in clean if l]

        if not rows:
            return {"studs": [], "marks": [], "errs": ["No rows found."], "meta": {}}

        hdrs = [h.strip().lower().replace(" ", "_") for h in rows[0]]

        # check wide format: columns after roll/name/class/sec are subjects
        sub_cols = []
        for i, h in enumerate(hdrs):
            if h not in ("roll", "roll_no", "id", "name", "student_name", "candidate_name", "class", "class_name", "std", "section", "sec", "total", "percentage", "rank"):
                sub_cols.append((i, fixsub(rows[0][i])))

        is_wide = len(sub_cols) >= 1

        for ri, row in enumerate(rows[1:], start=2):
            if not row or not any(row):
                continue

            rno = row[0] if len(row) > 0 else ""
            if not rno or rno.lower() in ("roll", "roll_no", "rank", "total"):
                continue

            nm = row[1] if len(row) > 1 else f"Student {rno}"
            cls = row[2] if len(row) > 2 and row[2] else def_cls
            sec = row[3] if len(row) > 3 and row[3] else def_sec

            if rno not in studs:
                studs[rno] = {"rno": rno, "nm": nm, "cls": cls, "sec": sec}

            if is_wide:
                for col_i, sub_name in sub_cols:
                    if col_i < len(row):
                        val = row[col_i].strip()
                        if val and val not in ("-", "NA", "N/A", "AB"):
                            try:
                                g, x = parseval(val)
                                mks.append({"rno": rno, "sub": sub_name, "got": g, "mx": x})
                            except Exception as e:
                                errs.append(f"Row {ri} {sub_name}: invalid mark '{val}'")
            else:
                # long format (roll, name, class, sec, subject, marks)
                if len(row) >= 6:
                    sn = row[4].strip()
                    val = row[5].strip()
                    if sn and val and val not in ("-", "NA", "N/A"):
                        try:
                            g, x = parseval(val)
                            mks.append({"rno": rno, "sub": fixsub(sn), "got": g, "mx": x})
                        except Exception:
                            pass

    return {
        "studs": list(studs.values()),
        "marks": mks,
        "errs": errs,
        "meta": {},
    }


def savetodb(parsed):
    # save parsed data into mysql
    database.initdb()

    meta = parsed.get("meta", {})
    if meta.get("school"):
        database.setschoolmeta("school", meta["school"])
    if meta.get("year"):
        database.setschoolmeta("year", meta["year"])
    if meta.get("class_name"):
        database.setschoolmeta("class_name", meta["class_name"])

    studs = parsed.get("studs", [])
    mks = parsed.get("marks", [])
    s_cnt, m_cnt = database.saveall(studs, mks)

    return {"studs_saved": s_cnt, "marks_saved": m_cnt}


def savetxt(txt, fname="report.txt"):
    # save printable text report into reports folder
    p = Path(__file__).resolve().parent / "reports" / fname
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(txt, encoding="utf-8")
    return p


