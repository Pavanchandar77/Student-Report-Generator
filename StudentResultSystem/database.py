# database.py - handles all mysql database stuff
# this file connects to mysql and does all the table work
# run initdb() first before doing anything else

import os
from contextlib import contextmanager

import mysql.connector
from mysql.connector import Error


# connection details - change password if urs is different
DBCONF = {
    "host": os.environ.get("MYSQL_HOST", "localhost"),
    "user": os.environ.get("MYSQL_USER", "root"),
    "password": os.environ.get("MYSQL_PASSWORD", "1234"),
    "database": os.environ.get("MYSQL_DATABASE", "student_result_system"),
    "port": int(os.environ.get("MYSQL_PORT", 3306)),
}


def basecon(cfg=None):
    # connect without picking a database (needed to create db)
    c = DBCONF.copy()
    if cfg:
        c.update(cfg)
    c.pop("database", None)
    return mysql.connector.connect(**c)


def makedb(cfg=None):
    # create the database if it doesnt exist yet
    c = DBCONF.copy()
    if cfg:
        c.update(cfg)
    db = c.get("database", "student_result_system")

    con = basecon(c)
    cur = con.cursor()
    try:
        cur.execute(
            f"CREATE DATABASE IF NOT EXISTS `{db}` "
            "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
        )
        con.commit()
    finally:
        cur.close()
        con.close()


def checkcon(cfg=None):
    # check if mysql is running and we can connect
    try:
        makedb(cfg)
        con = getcon(cfg)
        con.close()
        return True, "Connected to MySQL database."
    except Error as e:
        return False, f"MySQL Error: {e.msg}"
    except Exception as e:
        return False, f"Connection Error: {e}"


def getcon(cfg=None):
    # get a mysql connection
    c = DBCONF.copy()
    if cfg:
        c.update(cfg)
    return mysql.connector.connect(**c)


@contextmanager
def getcur(cfg=None):
    # gives u a cursor, auto commits when done, rollback if error
    con = getcon(cfg)
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


def initdb(cfg=None):
    # creates all three tables - run this first before anything
    makedb(cfg)

    with getcur(cfg) as (_, cur):
        # students table - stores student info
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS students (
                student_id INT AUTO_INCREMENT PRIMARY KEY,
                roll_no VARCHAR(20) NOT NULL UNIQUE,
                name VARCHAR(100) NOT NULL,
                class_name VARCHAR(50) NOT NULL,
                section VARCHAR(10) NOT NULL,
                phone VARCHAR(20),
                email VARCHAR(100)
            )
            """
        )
        # subjects table - maths physics chemistry etc
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS subjects (
                subject_id INT AUTO_INCREMENT PRIMARY KEY,
                subject_name VARCHAR(100) NOT NULL UNIQUE
            )
            """
        )
        # marks table - stores who got how much in what
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS marks (
                mark_id INT AUTO_INCREMENT PRIMARY KEY,
                roll_no VARCHAR(20) NOT NULL,
                subject_id INT NOT NULL,
                marks_obtained DECIMAL(5,2) NOT NULL,
                max_marks DECIMAL(5,2) NOT NULL,
                UNIQUE KEY uq_roll_sub (roll_no, subject_id),
                FOREIGN KEY (roll_no) REFERENCES students(roll_no)
                    ON DELETE CASCADE,
                FOREIGN KEY (subject_id) REFERENCES subjects(subject_id)
                    ON DELETE CASCADE
            )
            """
        )


# ========== STUDENT FUNCTIONS ==========
# CRUD = Create Read Update Delete
# basically add, see, change, remove students

def addstud(rno, nm, cls, sec, ph=None, em=None, cfg=None):
    # add one new student
    with getcur(cfg) as (_, cur):
        cur.execute(
            "INSERT INTO students (roll_no, name, class_name, section, phone, email) VALUES (%s, %s, %s, %s, %s, %s)",
            (rno, nm, cls, sec, ph, em),
        )
        return int(cur.lastrowid)


def upsertstud(rno, nm, cls, sec, ph=None, em=None, cfg=None):
    # if student exists update, else insert new one
    with getcur(cfg) as (_, cur):
        cur.execute(
            """
            INSERT INTO students (roll_no, name, class_name, section, phone, email)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                name = VALUES(name),
                class_name = VALUES(class_name),
                section = VALUES(section),
                phone = COALESCE(VALUES(phone), phone),
                email = COALESCE(VALUES(email), email)
            """,
            (rno, nm, cls, sec, ph, em),
        )
        return cur.rowcount


def updatestud(rno, nm, cls, sec, ph=None, em=None, cfg=None):
    # update an existing student's info
    with getcur(cfg) as (_, cur):
        cur.execute(
            """
            UPDATE students
            SET name = %s, class_name = %s, section = %s, phone = %s, email = %s
            WHERE roll_no = %s
            """,
            (nm, cls, sec, ph, em, rno),
        )
        return cur.rowcount


def delstud(rno, cfg=None):
    # delete a student by roll number
    with getcur(cfg) as (_, cur):
        cur.execute("DELETE FROM students WHERE roll_no = %s", (rno,))
        return cur.rowcount


def searchstud(kw, cfg=None):
    # search students by any keyword (name, roll, class, section)
    with getcur(cfg) as (_, cur):
        cur.execute(
            """
            SELECT s.roll_no, s.name, s.class_name, s.section, s.phone, s.email
            FROM students s
            WHERE s.roll_no LIKE %s OR s.name LIKE %s OR s.class_name LIKE %s OR s.section LIKE %s
            ORDER BY s.roll_no
            """,
            (tuple(f"%{kw}%" for _ in range(4))),
        )
        return cur.fetchall()


def fetchstuds(cfg=None):
    # get all students from database
    with getcur(cfg) as (_, cur):
        cur.execute(
            """
            SELECT roll_no, name, class_name, section, phone, email
            FROM students
            ORDER BY roll_no
            """
        )
        return cur.fetchall()


# ========== SUBJECT FUNCTIONS ==========

def addsub(subname, cfg=None):
    # add one subject
    with getcur(cfg) as (_, cur):
        cur.execute("INSERT INTO subjects (subject_name) VALUES (%s)", (subname,))
        return int(cur.lastrowid)


def getorcreatesub(subname, cfg=None):
    # get subject id, or create it if it doesnt exist
    clean = str(subname).strip()
    with getcur(cfg) as (_, cur):
        cur.execute(
            "SELECT subject_id FROM subjects WHERE LOWER(subject_name) = LOWER(%s)",
            (clean,),
        )
        row = cur.fetchone()
        if row:
            return int(row["subject_id"])
        cur.execute("INSERT INTO subjects (subject_name) VALUES (%s)", (clean,))
        return int(cur.lastrowid)


def fetchsubs(cfg=None):
    # get all subjects
    with getcur(cfg) as (_, cur):
        cur.execute("SELECT subject_id, subject_name FROM subjects ORDER BY subject_name")
        return cur.fetchall()


# ========== MARKS FUNCTIONS ==========

def addmark(rno, subid, got, mx, cfg=None):
    # add one mark entry
    with getcur(cfg) as (_, cur):
        cur.execute(
            "INSERT INTO marks (roll_no, subject_id, marks_obtained, max_marks) VALUES (%s, %s, %s, %s)",
            (rno, subid, got, mx),
        )
        return int(cur.lastrowid)


def upsertmark(rno, subid, got, mx, cfg=None):
    # insert mark or update if already exists
    with getcur(cfg) as (_, cur):
        cur.execute(
            """
            INSERT INTO marks (roll_no, subject_id, marks_obtained, max_marks)
            VALUES (%s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                marks_obtained = VALUES(marks_obtained),
                max_marks = VALUES(max_marks)
            """,
            (rno, subid, got, mx),
        )
        return cur.rowcount


def fetchallmarks(cfg=None):
    # get all marks joined with student and subject names
    with getcur(cfg) as (_, cur):
        cur.execute(
            """
            SELECT
                m.mark_id, s.roll_no, s.name, s.class_name,
                sub.subject_name, m.marks_obtained, m.max_marks
            FROM marks m
            JOIN students s ON s.roll_no = m.roll_no
            JOIN subjects sub ON sub.subject_id = m.subject_id
            ORDER BY s.roll_no, sub.subject_name
            """
        )
        return cur.fetchall()


# ========== RESULTS & REPORTS ==========

def fetchclassresults(cls, cfg=None):
    # get all results for one class
    with getcur(cfg) as (_, cur):
        cur.execute(
            """
            SELECT
                s.roll_no, s.name, s.class_name, s.section,
                sub.subject_name, m.marks_obtained, m.max_marks
            FROM students s
            JOIN marks m ON s.roll_no = m.roll_no
            JOIN subjects sub ON sub.subject_id = m.subject_id
            WHERE s.class_name = %s
            ORDER BY s.roll_no, sub.subject_name
            """,
            (cls,),
        )
        return cur.fetchall()


def fetchreport(rno, cfg=None):
    # get one student's full report card data
    with getcur(cfg) as (_, cur):
        cur.execute(
            """
            SELECT
                s.roll_no, s.name, s.class_name, s.section,
                s.phone, s.email,
                sub.subject_name, m.marks_obtained, m.max_marks
            FROM students s
            LEFT JOIN marks m ON s.roll_no = m.roll_no
            LEFT JOIN subjects sub ON sub.subject_id = m.subject_id
            WHERE s.roll_no = %s
            ORDER BY sub.subject_name
            """,
            (rno,),
        )
        return cur.fetchall()


def getranked(cls, cfg=None):
    # get ranked results for a class (1st, 2nd, 3rd etc)
    with getcur(cfg) as (_, cur):
        cur.execute(
            """
            SELECT
                s.roll_no, s.name, s.class_name,
                ROUND(SUM(m.marks_obtained), 2) AS total,
                ROUND(SUM(m.marks_obtained) / NULLIF(SUM(m.max_marks), 0) * 100, 2) AS percentage,
                ROW_NUMBER() OVER (
                    ORDER BY SUM(m.marks_obtained) / NULLIF(SUM(m.max_marks), 0) DESC, s.roll_no
                ) AS rank_position
            FROM students s
            JOIN marks m ON s.roll_no = m.roll_no
            WHERE s.class_name = %s
            GROUP BY s.roll_no, s.name, s.class_name
            ORDER BY rank_position
            """,
            (cls,),
        )
        return cur.fetchall()


# ========== ANALYTICS - WHO SCORED MOST ==========

def gettopscorers(cls=None, lim=10, cfg=None):
    # find who scored the most marks overall
    with getcur(cfg) as (_, cur):
        q = """
        SELECT
            s.roll_no, s.name, s.class_name, s.section,
            ROUND(SUM(m.marks_obtained), 2) AS total_obtained,
            ROUND(SUM(m.max_marks), 2) AS total_max,
            ROUND(SUM(m.marks_obtained) / NULLIF(SUM(m.max_marks), 0) * 100, 2) AS percentage,
            DENSE_RANK() OVER (
                ORDER BY SUM(m.marks_obtained) / NULLIF(SUM(m.max_marks), 0) DESC, SUM(m.marks_obtained) DESC
            ) AS rank_position
        FROM students s
        JOIN marks m ON s.roll_no = m.roll_no
        WHERE (%s IS NULL OR s.class_name = %s)
        GROUP BY s.roll_no, s.name, s.class_name, s.section
        ORDER BY rank_position, total_obtained DESC
        LIMIT %s
        """
        cur.execute(q, (cls, cls, lim))
        return cur.fetchall()


def getsubtoppers(cls=None, sub=None, cfg=None):
    # find who scored the most in each subject
    with getcur(cfg) as (_, cur):
        q = """
        WITH ranked AS (
            SELECT
                sub.subject_name, s.roll_no, s.name,
                s.class_name, s.section,
                m.marks_obtained, m.max_marks,
                ROUND(m.marks_obtained / NULLIF(m.max_marks, 0) * 100, 2) AS percentage,
                DENSE_RANK() OVER (
                    PARTITION BY sub.subject_id
                    ORDER BY m.marks_obtained / NULLIF(m.max_marks, 0) DESC, m.marks_obtained DESC
                ) AS rk
            FROM marks m
            JOIN students s ON s.roll_no = m.roll_no
            JOIN subjects sub ON sub.subject_id = m.subject_id
            WHERE (%s IS NULL OR s.class_name = %s)
              AND (%s IS NULL OR LOWER(sub.subject_name) = LOWER(%s))
        )
        SELECT subject_name, roll_no, name, class_name, section,
               marks_obtained, max_marks, percentage
        FROM ranked
        WHERE rk = 1
        ORDER BY subject_name, name
        """
        cur.execute(q, (cls, cls, sub, sub))
        return cur.fetchall()


def getsubstats(cls=None, cfg=None):
    # subject wise stats - average, highest, lowest marks
    with getcur(cfg) as (_, cur):
        q = """
        SELECT
            sub.subject_name,
            COUNT(DISTINCT s.roll_no) AS total_students,
            ROUND(AVG(m.marks_obtained), 2) AS avg_marks,
            ROUND(MAX(m.marks_obtained), 2) AS highest_marks,
            ROUND(MIN(m.marks_obtained), 2) AS lowest_marks,
            MAX(m.max_marks) AS max_marks,
            ROUND(AVG(m.marks_obtained / NULLIF(m.max_marks, 0) * 100), 2) AS avg_percentage
        FROM subjects sub
        JOIN marks m ON sub.subject_id = m.subject_id
        JOIN students s ON s.roll_no = m.roll_no
        WHERE (%s IS NULL OR s.class_name = %s)
        GROUP BY sub.subject_id, sub.subject_name
        ORDER BY sub.subject_name
        """
        cur.execute(q, (cls, cls))
        return cur.fetchall()


def comparetwo(rno1, rno2, cfg=None):
    # compare two students side by side across all subjects
    r1 = fetchreport(rno1, cfg)
    r2 = fetchreport(rno2, cfg)

    if not r1 or not r2:
        return None

    s1 = r1[0]
    s2 = r2[0]

    m1 = {r["subject_name"]: r for r in r1 if r.get("subject_name")}
    m2 = {r["subject_name"]: r for r in r2 if r.get("subject_name")}

    allsubs = sorted(list(set(m1.keys()) | set(m2.keys())))

    comp = []
    t1, t2 = 0.0, 0.0
    mx1, mx2 = 0.0, 0.0

    for sub in allsubs:
        a = m1.get(sub)
        b = m2.get(sub)

        o1 = float(a["marks_obtained"]) if a and a.get("marks_obtained") is not None else None
        x1 = float(a["max_marks"]) if a and a.get("max_marks") is not None else None
        o2 = float(b["marks_obtained"]) if b and b.get("marks_obtained") is not None else None
        x2 = float(b["max_marks"]) if b and b.get("max_marks") is not None else None

        if o1 is not None:
            t1 += o1
            mx1 += (x1 or 100.0)
        if o2 is not None:
            t2 += o2
            mx2 += (x2 or 100.0)

        if o1 is not None and o2 is not None:
            d = round(o1 - o2, 2)
            if d > 0:
                ld = s1["name"]
            elif d < 0:
                ld = s2["name"]
            else:
                ld = "Tie"
        elif o1 is not None:
            d = round(o1, 2)
            ld = s1["name"]
        elif o2 is not None:
            d = round(-o2, 2)
            ld = s2["name"]
        else:
            d = 0.0
            ld = "N/A"

        comp.append({
            "subject": sub,
            "student_1_marks": o1,
            "student_2_marks": o2,
            "difference": d,
            "leader": ld,
        })

    p1 = round((t1 / mx1 * 100), 2) if mx1 else 0.0
    p2 = round((t2 / mx2 * 100), 2) if mx2 else 0.0

    boss = s1["name"] if p1 > p2 else (s2["name"] if p2 > p1 else "Tie")

    return {
        "student_1": {
            "roll_no": s1["roll_no"],
            "name": s1["name"],
            "class_name": s1["class_name"],
            "total_obtained": round(t1, 2),
            "total_max": round(mx1, 2),
            "percentage": p1,
        },
        "student_2": {
            "roll_no": s2["roll_no"],
            "name": s2["name"],
            "class_name": s2["class_name"],
            "total_obtained": round(t2, 2),
            "total_max": round(mx2, 2),
            "percentage": p2,
        },
        "overall_leader": boss,
        "difference_percentage": round(abs(p1 - p2), 2),
        "subject_comparison": comp,
    }
