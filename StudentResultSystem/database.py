# database.py - mysql operations for multi-database academic year result system
# supports separate database per academic year (e.g. cbse_2015, cbse_2017)

import os
from contextlib import contextmanager
import mysql.connector
from mysql.connector import Error

# mysql connection config
DBCONF = {
    "host": os.environ.get("MYSQL_HOST", "localhost"),
    "user": os.environ.get("MYSQL_USER", "root"),
    "password": os.environ.get("MYSQL_PASSWORD", "1234"),
    "database": os.environ.get("MYSQL_DATABASE", "cbse_2015"),
    "port": int(os.environ.get("MYSQL_PORT", 3306)),
}


def setdb(db_name):
    # set active database
    DBCONF["database"] = str(db_name).strip()


def getdb():
    # get active database
    return DBCONF.get("database", "cbse_2015")


def basecon():
    # connect without selecting database
    c = DBCONF.copy()
    c.pop("database", None)
    return mysql.connector.connect(**c)


def getcon(db=None):
    # get connection to specific or active database
    c = DBCONF.copy()
    if db:
        c["database"] = str(db).strip()
    return mysql.connector.connect(**c)


@contextmanager
def getcur(db=None):
    # cursor context manager with auto commit
    con = getcon(db=db)
    cur = con.cursor(dictionary=True)
    try:
        yield con, cur
        con.commit()
    except Error:
        con.rollback()
        raise
    finally:
        cur.close()
        con.close()


def makedb(db=None):
    # create database if not exists
    t = db or getdb()
    con = basecon()
    cur = con.cursor()
    try:
        cur.execute(f"CREATE DATABASE IF NOT EXISTS `{t}`")
        con.commit()
    finally:
        cur.close()
        con.close()


def checkcon():
    # check if mysql is reachable
    try:
        makedb()
        con = getcon()
        con.close()
        return True, "Connected"
    except Exception as e:
        return False, str(e)


def getdbs():
    # list all academic year databases and student counts
    con = basecon()
    cur = con.cursor(dictionary=True)
    res = []
    try:
        cur.execute("SHOW DATABASES")
        all_dbs = [r["Database"] for r in cur.fetchall()]
        cand = [d for d in all_dbs if d.startswith("cbse_") or d.startswith("student_result")]
        for d in sorted(cand):
            try:
                cur.execute(f"SELECT COUNT(*) AS c FROM `{d}`.students")
                sc = cur.fetchone()["c"]
                sch = ""
                yr = ""
                try:
                    cur.execute(f"SELECT k, v FROM `{d}`.school_meta")
                    for r in cur.fetchall():
                        if r["k"] == "school":
                            sch = r["v"]
                        if r["k"] == "year":
                            yr = r["v"]
                except Exception:
                    pass

                if not yr and "_" in d:
                    parts = d.split("_")
                    if parts[-1].isdigit():
                        yr = parts[-1]

                res.append({
                    "db": d,
                    "year": yr or "N/A",
                    "school": sch or "Chinmaya Vidyalaya",
                    "studs": sc,
                })
            except Exception:
                pass
    finally:
        cur.close()
        con.close()
    return res


def initdb(db=None):
    # create tables in target or active database
    t = db or getdb()
    makedb(t)
    with getcur(db=t) as (_, cur):
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS school_meta (
                k VARCHAR(50) PRIMARY KEY,
                v VARCHAR(255)
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS students (
                student_id INT AUTO_INCREMENT PRIMARY KEY,
                roll_no VARCHAR(50) NOT NULL UNIQUE,
                name VARCHAR(150) NOT NULL,
                class_name VARCHAR(50) NOT NULL DEFAULT 'STD XII',
                section VARCHAR(20) NOT NULL DEFAULT 'A'
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS subjects (
                subject_id INT AUTO_INCREMENT PRIMARY KEY,
                subject_name VARCHAR(100) NOT NULL UNIQUE
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS marks (
                mark_id INT AUTO_INCREMENT PRIMARY KEY,
                roll_no VARCHAR(50) NOT NULL,
                subject_id INT NOT NULL,
                marks_obtained DECIMAL(6,2) NOT NULL,
                max_marks DECIMAL(6,2) NOT NULL DEFAULT 100.00,
                UNIQUE KEY uq_roll_sub (roll_no, subject_id),
                FOREIGN KEY (roll_no) REFERENCES students(roll_no) ON DELETE CASCADE,
                FOREIGN KEY (subject_id) REFERENCES subjects(subject_id) ON DELETE CASCADE
            )
            """
        )


def resetdb(db=None):
    # clear tables for fresh data in database
    with getcur(db=db) as (_, cur):
        cur.execute("SET FOREIGN_KEY_CHECKS = 0")
        cur.execute("TRUNCATE TABLE marks")
        cur.execute("TRUNCATE TABLE students")
        cur.execute("TRUNCATE TABLE subjects")
        try:
            cur.execute("TRUNCATE TABLE school_meta")
        except Exception:
            pass
        cur.execute("SET FOREIGN_KEY_CHECKS = 1")


def setschoolmeta(k, v, db=None):
    # save school metadata (school name, year, class)
    initdb(db=db)
    with getcur(db=db) as (_, cur):
        cur.execute(
            "INSERT INTO school_meta (k, v) VALUES (%s, %s) ON DUPLICATE KEY UPDATE v = VALUES(v)",
            (str(k), str(v)),
        )


def getschoolmeta(k, def_val="", db=None):
    # get school metadata
    try:
        with getcur(db=db) as (_, cur):
            cur.execute("SELECT v FROM school_meta WHERE k = %s", (str(k),))
            row = cur.fetchone()
            return row["v"] if row else def_val
    except Exception:
        return def_val


# ========== INSERT / UPDATE DATA ==========

def savestud(rno, nm, cls="STD XII", sec="A", db=None):
    # insert student or update if already there
    rno = str(rno).strip()
    nm = str(nm).strip()
    cls = str(cls).strip() if cls else "STD XII"
    sec = str(sec).strip() if sec else "A"
    with getcur(db=db) as (_, cur):
        q = """
        INSERT INTO students (roll_no, name, class_name, section)
        VALUES (%s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE name = VALUES(name), class_name = VALUES(class_name), section = VALUES(section)
        """
        cur.execute(q, (rno, nm, cls, sec))
        return cur.rowcount


def getsubid(sn, db=None):
    # get id of subject, create if new
    sn = str(sn).strip()
    with getcur(db=db) as (_, cur):
        cur.execute("SELECT subject_id FROM subjects WHERE LOWER(subject_name) = LOWER(%s)", (sn,))
        row = cur.fetchone()
        if row:
            return int(row["subject_id"])
        cur.execute("INSERT INTO subjects (subject_name) VALUES (%s)", (sn,))
        return int(cur.lastrowid)


def savemark(rno, sid, got, mx=100.0, db=None):
    # insert or update student mark
    with getcur(db=db) as (_, cur):
        q = """
        INSERT INTO marks (roll_no, subject_id, marks_obtained, max_marks)
        VALUES (%s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE marks_obtained = VALUES(marks_obtained), max_marks = VALUES(max_marks)
        """
        cur.execute(q, (str(rno).strip(), sid, float(got), float(mx)))
        return cur.rowcount


def saveall(studs, marks, db=None):
    # fast batch insert of students and marks in a single transaction
    initdb(db=db)
    with getcur(db=db) as (_, cur):
        sub_names = list({m["sub"] for m in marks if m.get("sub")})
        sub_map = {}
        for sn in sub_names:
            cur.execute("SELECT subject_id FROM subjects WHERE LOWER(subject_name) = LOWER(%s)", (sn,))
            row = cur.fetchone()
            if row:
                sub_map[sn] = int(row["subject_id"])
            else:
                cur.execute("INSERT INTO subjects (subject_name) VALUES (%s)", (sn,))
                sub_map[sn] = int(cur.lastrowid)

        q_st = """
        INSERT INTO students (roll_no, name, class_name, section)
        VALUES (%s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE name = VALUES(name), class_name = VALUES(class_name), section = VALUES(section)
        """
        st_rows = [(st["rno"], st["nm"], st.get("cls", "STD XII"), st.get("sec", "A")) for st in studs]
        if st_rows:
            cur.executemany(q_st, st_rows)

        q_mk = """
        INSERT INTO marks (roll_no, subject_id, marks_obtained, max_marks)
        VALUES (%s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE marks_obtained = VALUES(marks_obtained), max_marks = VALUES(max_marks)
        """
        mk_rows = [(m["rno"], sub_map[m["sub"]], float(m["got"]), float(m.get("mx", 100.0))) for m in marks if m.get("sub") in sub_map]
        if mk_rows:
            cur.executemany(q_mk, mk_rows)

    return len(st_rows), len(mk_rows)


# ========== DROPDOWN / LIST QUERIES ==========

def getclasses(db=None):
    # get list of classes in database
    with getcur(db=db) as (_, cur):
        cur.execute("SELECT DISTINCT class_name FROM students ORDER BY class_name")
        return [r["class_name"] for r in cur.fetchall()]


def getsections(cls=None, db=None):
    # get sections for a class
    with getcur(db=db) as (_, cur):
        if cls:
            cur.execute("SELECT DISTINCT section FROM students WHERE class_name = %s ORDER BY section", (cls,))
        else:
            cur.execute("SELECT DISTINCT section FROM students ORDER BY section")
        return [r["section"] for r in cur.fetchall()]


def getsubjects(db=None):
    # get all subject names
    with getcur(db=db) as (_, cur):
        cur.execute("SELECT subject_name FROM subjects ORDER BY subject_name")
        return [r["subject_name"] for r in cur.fetchall()]


def getstuds(db=None):
    # get all students
    with getcur(db=db) as (_, cur):
        cur.execute("SELECT roll_no, name, class_name, section FROM students ORDER BY roll_no")
        return cur.fetchall()


# ========== REPORT 1: SCHOOL / CLASS TOPPERS (IMAGE 1) ==========

def gettoppers(cls=None, sec=None, lim=3, db=None):
    # top ranks overall: Place, Name, Mark, %
    with getcur(db=db) as (_, cur):
        q = """
        SELECT
            s.roll_no, s.name, s.class_name, s.section,
            ROUND(SUM(m.marks_obtained), 2) AS total_mark,
            ROUND(SUM(m.max_marks), 2) AS max_mark,
            ROUND(SUM(m.marks_obtained) / NULLIF(SUM(m.max_marks), 0) * 100, 2) AS pct,
            DENSE_RANK() OVER (ORDER BY SUM(m.marks_obtained) / NULLIF(SUM(m.max_marks), 0) DESC) AS rk
        FROM students s
        JOIN marks m ON s.roll_no = m.roll_no
        WHERE (%s IS NULL OR s.class_name = %s)
          AND (%s IS NULL OR s.section = %s)
        GROUP BY s.roll_no, s.name, s.class_name, s.section
        ORDER BY rk, total_mark DESC
        LIMIT %s
        """
        cur.execute(q, (cls, cls, sec, sec, lim))
        rows = cur.fetchall()

    places = ["I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X"]
    res = []
    for r in rows:
        k = int(r["rk"])
        pl = places[k - 1] if 1 <= k <= len(places) else str(k)
        res.append({
            "place": pl,
            "rank": k,
            "roll_no": r["roll_no"],
            "name": r["name"],
            "class_name": r["class_name"],
            "section": r["section"],
            "mark": float(r["total_mark"]),
            "max_mark": float(r["max_mark"]),
            "pct": float(r["pct"]),
        })
    return res


# ========== REPORT 2: OVERALL AVERAGE & RANGE DISTRIBUTION (IMAGE 1) ==========

def getsummary(cls=None, sec=None, db=None):
    # overall school average, distinction, 1st class, compartments and range table
    with getcur(db=db) as (_, cur):
        q = """
        SELECT
            s.roll_no, s.name,
            SUM(m.marks_obtained) AS tot_got,
            SUM(m.max_marks) AS tot_max,
            ROUND(SUM(m.marks_obtained) / NULLIF(SUM(m.max_marks), 0) * 100, 2) AS pct,
            MIN(m.marks_obtained / NULLIF(m.max_marks, 0) * 100) AS min_p
        FROM students s
        JOIN marks m ON s.roll_no = m.roll_no
        WHERE (%s IS NULL OR s.class_name = %s)
          AND (%s IS NULL OR s.section = %s)
        GROUP BY s.roll_no, s.name
        """
        cur.execute(q, (cls, cls, sec, sec))
        rows = cur.fetchall()

    n = len(rows)
    if n == 0:
        return {
            "total": 0, "avg": 0.0, "dist": 0, "first": 0, "second": 0, "comp": 0,
            "ranges": [
                {"range": "Above 95% > 475", "cnt": 0, "pct": 0.0},
                {"range": "91-94% (451-474)", "cnt": 0, "pct": 0.0},
                {"range": "81-90% (401-450)", "cnt": 0, "pct": 0.0},
                {"range": "75-80% (375-400)", "cnt": 0, "pct": 0.0},
                {"range": "60-74% (300-374)", "cnt": 0, "pct": 0.0},
                {"range": "Below 60% < 300", "cnt": 0, "pct": 0.0},
            ]
        }

    sum_got = sum(float(r["tot_got"]) for r in rows)
    sum_max = sum(float(r["tot_max"]) for r in rows)
    avg_p = round(sum_got / sum_max * 100, 2) if sum_max > 0 else 0.0

    c_dist = 0
    c_1st = 0
    c_2nd = 0
    c_comp = 0

    r_95 = 0
    r_91_94 = 0
    r_81_90 = 0
    r_75_80 = 0
    r_60_74 = 0
    r_below_60 = 0

    for r in rows:
        p = float(r["pct"] or 0)
        mp = float(r["min_p"] or 0)

        if p >= 75.0:
            c_dist += 1
        if p >= 60.0:
            c_1st += 1
        elif 50.0 <= p < 60.0:
            c_2nd += 1

        if mp < 33.0 or p < 33.0:
            c_comp += 1

        # score distribution ranges
        if p >= 95.0:
            r_95 += 1
        elif 91.0 <= p < 95.0:
            r_91_94 += 1
        elif 81.0 <= p < 91.0:
            r_81_90 += 1
        elif 75.0 <= p < 81.0:
            r_75_80 += 1
        elif 60.0 <= p < 75.0:
            r_60_74 += 1
        else:
            r_below_60 += 1

    ranges = [
        {"range": "Above 95% > 475", "cnt": r_95, "pct": round(r_95 / n * 100, 2)},
        {"range": "91-94% (451-474)", "cnt": r_91_94, "pct": round(r_91_94 / n * 100, 2)},
        {"range": "81-90% (401-450)", "cnt": r_81_90, "pct": round(r_81_90 / n * 100, 2)},
        {"range": "75-80% (375-400)", "cnt": r_75_80, "pct": round(r_75_80 / n * 100, 2)},
        {"range": "60-74% (300-374)", "cnt": r_60_74, "pct": round(r_60_74 / n * 100, 2)},
        {"range": "Below 60% < 300", "cnt": r_below_60, "pct": round(r_below_60 / n * 100, 2)},
    ]

    return {
        "total": n,
        "avg": avg_p,
        "dist": c_dist,
        "first": c_1st,
        "second": c_2nd,
        "comp": c_comp,
        "ranges": ranges,
    }


# ========== REPORT 3: SUBJECT AVERAGE & STATS (IMAGE 1) ==========

def getsubstats(cls=None, sec=None, db=None):
    # subject name, student count, avg mark, highest mark, student count with highest, centum count, lowest
    with getcur(db=db) as (_, cur):
        q = """
        SELECT
            sub.subject_id,
            sub.subject_name,
            COUNT(DISTINCT s.roll_no) AS stu_cnt,
            ROUND(AVG(m.marks_obtained), 2) AS avg_mark,
            ROUND(MAX(m.marks_obtained), 2) AS high_mark,
            ROUND(MIN(m.marks_obtained), 2) AS low_mark,
            MAX(m.max_marks) AS max_m
        FROM subjects sub
        JOIN marks m ON sub.subject_id = m.subject_id
        JOIN students s ON s.roll_no = m.roll_no
        WHERE (%s IS NULL OR s.class_name = %s)
          AND (%s IS NULL OR s.section = %s)
        GROUP BY sub.subject_id, sub.subject_name
        ORDER BY sub.subject_name
        """
        cur.execute(q, (cls, cls, sec, sec))
        subs = cur.fetchall()

        res = []
        for s in subs:
            sid = s["subject_id"]
            hi = s["high_mark"]

            # count students who got highest mark
            cur.execute(
                """
                SELECT COUNT(*) AS c
                FROM marks m JOIN students s ON s.roll_no = m.roll_no
                WHERE m.subject_id = %s AND m.marks_obtained = %s
                  AND (%s IS NULL OR s.class_name = %s)
                  AND (%s IS NULL OR s.section = %s)
                """,
                (sid, hi, cls, cls, sec, sec),
            )
            hi_cnt = cur.fetchone()["c"]

            # count centums (100)
            cur.execute(
                """
                SELECT COUNT(*) AS c
                FROM marks m JOIN students s ON s.roll_no = m.roll_no
                WHERE m.subject_id = %s AND (m.marks_obtained >= 100 OR m.marks_obtained = m.max_marks)
                  AND (%s IS NULL OR s.class_name = %s)
                  AND (%s IS NULL OR s.section = %s)
                """,
                (sid, cls, cls, sec, sec),
            )
            cent_cnt = cur.fetchone()["c"]

            res.append({
                "subject": s["subject_name"],
                "stu_cnt": s["stu_cnt"],
                "avg": float(s["avg_mark"]),
                "high": float(hi),
                "high_cnt": hi_cnt,
                "cent_cnt": cent_cnt,
                "low": float(s["low_mark"]),
            })
        return res


# ========== REPORT 4: SUBJECT TOPPERS ROSTER (IMAGE 2) ==========

def getsubtoppers(cls=None, sec=None, sub=None, db=None):
    # subject toppers list with student names
    with getcur(db=db) as (_, cur):
        q = """
        WITH ranked AS (
            SELECT
                sub.subject_name,
                s.roll_no,
                s.name,
                s.class_name,
                s.section,
                m.marks_obtained,
                DENSE_RANK() OVER (PARTITION BY sub.subject_id ORDER BY m.marks_obtained DESC) AS rk
            FROM marks m
            JOIN students s ON s.roll_no = m.roll_no
            JOIN subjects sub ON sub.subject_id = m.subject_id
            WHERE (%s IS NULL OR s.class_name = %s)
              AND (%s IS NULL OR s.section = %s)
              AND (%s IS NULL OR LOWER(sub.subject_name) = LOWER(%s))
        )
        SELECT subject_name, roll_no, name, class_name, section, marks_obtained
        FROM ranked
        WHERE rk = 1
        ORDER BY subject_name, name
        """
        cur.execute(q, (cls, cls, sec, sec, sub, sub))
        rows = cur.fetchall()

    grps = {}
    for r in rows:
        sn = r["subject_name"]
        if sn not in grps:
            grps[sn] = {
                "subject": sn,
                "high": float(r["marks_obtained"]),
                "students": [],
            }
        grps[sn]["students"].append({
            "roll_no": r["roll_no"],
            "name": r["name"],
            "class_name": r["class_name"],
            "section": r["section"],
        })
    return list(grps.values())


# ========== MERIT LIST & FILTERS ==========

def getmeritlist(cls=None, sec=None, db=None):
    # complete rank list of students
    with getcur(db=db) as (_, cur):
        q = """
        SELECT
            s.roll_no, s.name, s.class_name, s.section,
            ROUND(SUM(m.marks_obtained), 2) AS tot_got,
            ROUND(SUM(m.max_marks), 2) AS tot_max,
            ROUND(SUM(m.marks_obtained) / NULLIF(SUM(m.max_marks), 0) * 100, 2) AS pct,
            MIN(m.marks_obtained / NULLIF(m.max_marks, 0) * 100) AS min_p,
            DENSE_RANK() OVER (ORDER BY SUM(m.marks_obtained) / NULLIF(SUM(m.max_marks), 0) DESC) AS rk
        FROM students s
        JOIN marks m ON s.roll_no = m.roll_no
        WHERE (%s IS NULL OR s.class_name = %s)
          AND (%s IS NULL OR s.section = %s)
        GROUP BY s.roll_no, s.name, s.class_name, s.section
        ORDER BY rk, s.roll_no
        """
        cur.execute(q, (cls, cls, sec, sec))
        rows = cur.fetchall()

    res = []
    for r in rows:
        p = float(r["pct"] or 0)
        mp = float(r["min_p"] or 0)
        if mp < 33.0 or p < 33.0:
            st = "Compartment"
        elif p >= 75.0:
            st = "Distinction"
        elif p >= 60.0:
            st = "1st Class"
        elif p >= 50.0:
            st = "2nd Class"
        else:
            st = "Pass"

        res.append({
            "rank": int(r["rk"]),
            "roll_no": r["roll_no"],
            "name": r["name"],
            "class_name": r["class_name"],
            "section": r["section"],
            "tot_got": float(r["tot_got"]),
            "tot_max": float(r["tot_max"]),
            "pct": p,
            "status": st,
        })
    return res


def getcentums(cls=None, sec=None, db=None):
    # students scoring 100
    with getcur(db=db) as (_, cur):
        q = """
        SELECT sub.subject_name, s.roll_no, s.name, s.class_name, s.section, m.marks_obtained
        FROM marks m
        JOIN students s ON s.roll_no = m.roll_no
        JOIN subjects sub ON sub.subject_id = m.subject_id
        WHERE (m.marks_obtained >= 100 OR m.marks_obtained = m.max_marks)
          AND (%s IS NULL OR s.class_name = %s)
          AND (%s IS NULL OR s.section = %s)
        ORDER BY sub.subject_name, s.name
        """
        cur.execute(q, (cls, cls, sec, sec))
        return cur.fetchall()


def getbycategory(cat, cls=None, sec=None, db=None):
    # filter students by distinction / 1st class / compartment
    all_s = getmeritlist(cls=cls, sec=sec, db=db)
    c = cat.lower()
    if c == "distinction":
        return [s for s in all_s if s["pct"] >= 75.0]
    elif c == "1st":
        return [s for s in all_s if s["pct"] >= 60.0]
    elif c == "compartment":
        return [s for s in all_s if s["status"] == "Compartment"]
    return all_s


def getsubroster(sub, cls=None, sec=None, minm=None, db=None):
    # list students for a specific subject
    with getcur(db=db) as (_, cur):
        q = """
        SELECT
            s.roll_no, s.name, s.class_name, s.section,
            sub.subject_name, m.marks_obtained, m.max_marks,
            ROUND(m.marks_obtained / NULLIF(m.max_marks, 0) * 100, 2) AS pct,
            DENSE_RANK() OVER (ORDER BY m.marks_obtained DESC) AS rk
        FROM marks m
        JOIN students s ON s.roll_no = m.roll_no
        JOIN subjects sub ON sub.subject_id = m.subject_id
        WHERE LOWER(sub.subject_name) = LOWER(%s)
          AND (%s IS NULL OR s.class_name = %s)
          AND (%s IS NULL OR s.section = %s)
          AND (%s IS NULL OR m.marks_obtained >= %s)
        ORDER BY m.marks_obtained DESC, s.name
        """
        cur.execute(q, (sub, cls, cls, sec, sec, minm, minm))
        return cur.fetchall()


def getbyrange(minp, maxp, cls=None, sec=None, db=None):
    # filter students within a percentage range
    all_s = getmeritlist(cls=cls, sec=sec, db=db)
    return [s for s in all_s if minp <= s["pct"] <= maxp]


def getreportcard(qval, db=None):
    # get marks for one student
    qval = str(qval).strip()
    with getcur(db=db) as (_, cur):
        q = """
        SELECT
            s.roll_no, s.name, s.class_name, s.section,
            sub.subject_name, m.marks_obtained, m.max_marks
            FROM students s
        LEFT JOIN marks m ON s.roll_no = m.roll_no
        LEFT JOIN subjects sub ON sub.subject_id = m.subject_id
        WHERE s.roll_no = %s OR LOWER(s.name) = LOWER(%s)
        ORDER BY sub.subject_name
        """
        cur.execute(q, (qval, qval))
        return cur.fetchall()


def comparestuds(r1, r2, db=None):
    # compare two students side by side
    d1 = getreportcard(r1, db=db)
    d2 = getreportcard(r2, db=db)
    if not d1 or not d2:
        return None

    s1 = d1[0]
    s2 = d2[0]

    m1 = {r["subject_name"]: float(r["marks_obtained"]) for r in d1 if r.get("subject_name")}
    m2 = {r["subject_name"]: float(r["marks_obtained"]) for r in d2 if r.get("subject_name")}
    all_subs = sorted(list(set(m1.keys()) | set(m2.keys())))

    rows = []
    t1, t2 = 0.0, 0.0
    for sub in all_subs:
        v1 = m1.get(sub)
        v2 = m2.get(sub)
        if v1 is not None:
            t1 += v1
        if v2 is not None:
            t2 += v2
        d = round((v1 or 0) - (v2 or 0), 2)
        ldr = s1["name"] if d > 0 else (s2["name"] if d < 0 else "Tie")
        rows.append({"sub": sub, "v1": v1, "v2": v2, "diff": d, "leader": ldr})

    p1 = round(t1 / (len(m1) * 100) * 100, 2) if m1 else 0.0
    p2 = round(t2 / (len(m2) * 100) * 100, 2) if m2 else 0.0
    ldr = s1["name"] if p1 > p2 else (s2["name"] if p2 > p1 else "Tie")

    return {
        "s1": {"roll_no": s1["roll_no"], "name": s1["name"], "cls": s1["class_name"], "tot": t1, "pct": p1},
        "s2": {"roll_no": s2["roll_no"], "name": s2["name"], "cls": s2["class_name"], "tot": t2, "pct": p2},
        "leader": ldr,
        "diff_pct": round(abs(p1 - p2), 2),
        "subs": rows,
    }
