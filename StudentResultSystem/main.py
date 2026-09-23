# main.py - the main file, everything starts here
# runs GUI by default, use --cli for terminal mode

from __future__ import annotations

import os
import sys
from pathlib import Path
import pandas as pd

from mysql.connector import Error as MySQLError

import database
import file_handler


BASEDIR = Path(__file__).resolve().parent
REPDIR = BASEDIR / "reports"
SAMPDIR = BASEDIR / "sample_data"


# menu items for terminal mode
MENU = [
    ("1", "init database", "create tables in MySQL"),
    ("2", "add student", "save a new student record"),
    ("3", "show students", "list all students"),
    ("4", "update student", "edit an existing student"),
    ("5", "delete student", "remove a student"),
    ("6", "search student", "find a student by keyword"),
    ("7", "add subject", "save a subject name"),
    ("8", "show subjects", "list all subjects"),
    ("9", "add marks", "enter marks for a student"),
    ("10", "import marks csv", "bulk add marks from a CSV file"),
    ("11", "make report card", "preview and save one student report"),
    ("12", "export class result csv", "export class results to CSV and reveal"),
    ("13", "rank results", "show ranked class results"),
    ("14", "input text file (.txt)", "grab data from text file, put in DB, and reveal in CSV"),
    ("15", "launch gui", "start Tkinter GUI"),
    ("16", "who scored most / compare", "find top scorers and compare student performances"),
    ("0", "exit", "close the program"),
]


def cls():
    # clear screen
    os.system("cls" if os.name == "nt" else "clear")


def wait():
    # pause until enter is pressed
    input("\nPress Enter to continue...")


def getinfo():
    # get student info from user input
    return {
        "roll_no": input("Roll no: ").strip(),
        "name": input("Name: ").strip(),
        "class_name": input("Class: ").strip(),
        "section": input("Section: ").strip(),
        "phone": input("Phone (optional): ").strip(),
        "email": input("Email (optional): ").strip(),
    }


def showmenu():
    # print the main menu
    print("=" * 66)
    print("      STUDENT RESULT & ACADEMIC RECORDS MANAGEMENT SYSTEM")
    print("=" * 66)
    print("Type the number or the menu text.")
    print("")
    for num, title, desc in MENU:
        print(f" {num:>2}. {title:<25} - {desc}")
    print("=" * 66)


def fixchoice(ch):
    # convert text input to menu number
    ch = ch.strip().lower()
    mp = {
        "init database": "1",
        "add student": "2",
        "show students": "3",
        "update student": "4",
        "delete student": "5",
        "search student": "6",
        "add subject": "7",
        "show subjects": "8",
        "add marks": "9",
        "import marks csv": "10",
        "make report card": "11",
        "export class result csv": "12",
        "rank results": "13",
        "input text file": "14",
        "input text file (.txt)": "14",
        "launch gui": "15",
        "gui": "15",
        "who scored most": "16",
        "compare": "16",
        "who scored most / compare": "16",
        "analytics": "16",
        "exit": "0",
    }
    return mp.get(ch, ch)


def header(msg=""):
    # show menu with optional message
    cls()
    showmenu()
    if msg:
        print(msg)
        print("-" * 66)


def nameandcsv(df, defname):
    # ask for csv name and save it
    nm = input(f"Enter name for the CSV file / report [{defname}]: ").strip()
    rname = nm if nm else defname
    fname = rname.replace(" ", "_")
    if not fname.lower().endswith(".csv"):
        fname = f"{fname}.csv"

    out = REPDIR / fname
    file_handler.savecsv(df, out, rname=rname)
    print(f"CSV file created with name '{rname}': {out}")
    ok, msg = file_handler.showfile(out)
    print(msg)
    return out


def importcsv():
    # import marks from csv file
    p = input("CSV path: ").strip()
    df = file_handler.readcsvmarks(p)
    for _, row in df.iterrows():
        database.addmark(
            str(row["roll_no"]),
            int(row["subject_id"]),
            float(row["marks_obtained"]),
            float(row["max_marks"]),
        )
    print(f"Imported {len(df)} mark rows.")


def txtfileprocess():
    # full pipeline: text file -> database -> csv
    p = input("Enter path to .txt file: ").strip()
    fp = Path(p)
    if not fp.exists():
        print(f"Error: File not found at '{p}'")
        return

    print(f"Reading and parsing '{fp.name}'...")
    parsed = file_handler.parsetxt(fp)
    sc = len(parsed.get("students", []))
    mc = len(parsed.get("marks", []))
    print(f"Grabbed data: {sc} student record(s), {mc} mark record(s).")

    if parsed.get("errors"):
        print("Warnings/Notes:")
        for e in parsed["errors"]:
            print(f" - {e}")

    # put into database
    print("Putting data into database...")
    res = file_handler.savetodb(parsed)
    print(f"Database updated: {res['students_saved']} student(s) and {res['marks_saved']} mark(s) saved.")

    # reveal in csv
    ch = input("Reveal and export in CSV? (y/n) [y]: ").strip().lower()
    if ch != "n":
        studs = parsed.get("students", [])
        marks = parsed.get("marks", [])
        smap = {s["roll_no"]: s for s in studs}
        rows = []

        if marks:
            for m in marks:
                rno = m["roll_no"]
                st = smap.get(rno, {})
                rows.append({
                    "Roll No": rno,
                    "Name": st.get("name", "Unknown"),
                    "Class": st.get("class_name", ""),
                    "Section": st.get("section", ""),
                    "Subject": m.get("subject_name", ""),
                    "Marks Obtained": m.get("marks_obtained", 0),
                    "Max Marks": m.get("max_marks", 100),
                    "Phone": st.get("phone", ""),
                    "Email": st.get("email", ""),
                })
        else:
            for s in studs:
                rows.append({
                    "Roll No": s["roll_no"],
                    "Name": s["name"],
                    "Class": s["class_name"],
                    "Section": s["section"],
                    "Subject": "N/A",
                    "Marks Obtained": 0,
                    "Max Marks": 0,
                    "Phone": s.get("phone", ""),
                    "Email": s.get("email", ""),
                })

        df = pd.DataFrame(rows)
        nameandcsv(df, defname=f"Imported_{fp.stem}")


def showtable(rows):
    # print data as a nice table
    print(pd.DataFrame(rows).to_string(index=False) if rows else "No data found.")


def analytics():
    # analytics and comparison menu
    print("\n--- Analytics & Comparison ---")
    print(" 1. Who scored the most marks overall?")
    print(" 2. Who scored the most marks in each subject?")
    print(" 3. Compare two students side-by-side")
    print(" 4. Subject performance statistics (average, highest, lowest)")
    ch = input("\nChoose an option (1-4): ").strip()

    if ch == "1":
        cf = input("Enter class name (or press Enter for all): ").strip() or None
        top = database.gettopscorers(cls=cf, lim=5)
        if top:
            t = top[0]
            print(f"\n[TOP SCORER] {t['name']} (Roll: {t['roll_no']})")
            print(f"   Total: {t['total_obtained']} / {t['total_max']} | Percentage: {t['percentage']}% | Class: {t['class_name']}-{t['section']}")
            print("\nTop Scorers Table:")
            showtable(top)
            ex = input("\nExport & reveal to CSV? (y/n) [n]: ").strip().lower()
            if ex == "y":
                nameandcsv(pd.DataFrame(top), defname="Overall_Top_Scorers")
        else:
            print("No records found.")

    elif ch == "2":
        cf = input("Enter class name (or press Enter for all): ").strip() or None
        st = database.getsubtoppers(cls=cf)
        if st:
            print("\nSubject-Wise Highest Scorers:")
            showtable(st)
            ex = input("\nExport & reveal to CSV? (y/n) [n]: ").strip().lower()
            if ex == "y":
                nameandcsv(pd.DataFrame(st), defname="Subject_Top_Scorers")
        else:
            print("No records found.")

    elif ch == "3":
        r1 = input("Enter Roll No for Student 1: ").strip()
        r2 = input("Enter Roll No for Student 2: ").strip()
        cmp = database.comparetwo(r1, r2)
        if cmp:
            s1 = cmp["student_1"]
            s2 = cmp["student_2"]
            print(f"\n--- Comparison: {s1['name']} ({r1}) vs {s2['name']} ({r2}) ---")
            print(f"[LEADER] {cmp['overall_leader']} (Difference: {cmp['difference_percentage']}%)")
            print(f"   {s1['name']}: {s1['total_obtained']} marks ({s1['percentage']}%)")
            print(f"   {s2['name']}: {s2['total_obtained']} marks ({s2['percentage']}%)")
            print("\nSubject Breakdown:")
            showtable(cmp["subject_comparison"])
            ex = input("\nExport & reveal comparison to CSV? (y/n) [n]: ").strip().lower()

            if ex == "y":
                rows = []
                for itm in cmp["subject_comparison"]:
                    rows.append({
                        "Subject": itm["subject"],
                        f"{s1['name']}_{s1['roll_no']}": itm["student_1_marks"],
                        f"{s2['name']}_{s2['roll_no']}": itm["student_2_marks"],
                        "Difference": itm["difference"],
                        "Subject_Leader": itm["leader"],
                    })
                rows.append({
                    "Subject": "OVERALL",
                    f"{s1['name']}_{s1['roll_no']}": f"{s1['total_obtained']} ({s1['percentage']}%)",
                    f"{s2['name']}_{s2['roll_no']}": f"{s2['total_obtained']} ({s2['percentage']}%)",
                    "Difference": f"{cmp['difference_percentage']}%",
                    "Subject_Leader": cmp["overall_leader"],
                })
                nameandcsv(pd.DataFrame(rows), defname=f"Comparison_{r1}_vs_{r2}")
        else:
            print("Could not compare students. Please check the roll numbers.")

    elif ch == "4":
        stats = database.getsubstats()
        if stats:
            print("\nSubject Performance Overview:")
            showtable(stats)
            ex = input("\nExport & reveal to CSV? (y/n) [n]: ").strip().lower()
            if ex == "y":
                nameandcsv(pd.DataFrame(stats), defname="Subject_Performance_Statistics")
        else:
            print("No records found.")


def climain():
    # main terminal loop - keeps running until u pick exit
    while True:
        header()
        ch = fixchoice(input("Choose an option: "))

        try:
            if ch == "1":
                database.initdb()
                print("database ready")
                wait()
            elif ch == "2":
                info = getinfo()
                sid = database.addstud(
                    info["roll_no"],
                    info["name"],
                    info["class_name"],
                    info["section"],
                    info["phone"] or None,
                    info["email"] or None,
                )
                print(f"student added with id {sid}")
                wait()
            elif ch == "3":
                header("Student list")
                showtable(database.fetchstuds())
                wait()
            elif ch == "4":
                header("Update student")
                rno = input("Roll no to update: ").strip()
                info = getinfo()
                cnt = database.updatestud(
                    rno,
                    info["name"],
                    info["class_name"],
                    info["section"],
                    info["phone"] or None,
                    info["email"] or None,
                )
                print(f"updated {cnt} row(s)")
                wait()
            elif ch == "5":
                header("Delete student")
                rno = input("Roll no to delete: ").strip()
                cnt = database.delstud(rno)
                print(f"deleted {cnt} row(s)")
                wait()
            elif ch == "6":
                header("Search student")
                kw = input("Search keyword: ").strip()
                showtable(database.searchstud(kw))
                wait()
            elif ch == "7":
                header("Add subject")
                sn = input("Subject name: ").strip()
                sid = database.addsub(sn)
                print(f"subject added with id {sid}")
                wait()
            elif ch == "8":
                header("Subject list")
                showtable(database.fetchsubs())
                wait()
            elif ch == "9":
                header("Add marks")
                rno = input("Roll no: ").strip()
                sid = int(input("Subject ID: ").strip())
                got = float(input("Marks obtained: ").strip())
                mx = float(input("Max marks: ").strip())
                mid = database.addmark(rno, sid, got, mx)
                print(f"mark added with id {mid}")
                wait()
            elif ch == "10":
                header("Import marks from CSV")
                importcsv()
                wait()
            elif ch == "11":
                header("Make report card")
                rno = input("Roll no: ").strip()
                rows = database.fetchreport(rno)
                rc = file_handler.makereportcard(rows)
                print("")
                print(rc)
                print("")
                sv = input("Export report card to CSV? (y/n): ").strip().lower()
                if sv == "y":
                    snm = rows[0].get("name", "").replace(" ", "_") if rows else ""
                    dn = f"Report_Card_{rno}_{snm}" if snm else f"Report_Card_{rno}"
                    nm = input(f"Enter name for CSV file / report [{dn}]: ").strip()
                    rname = nm if nm else dn
                    out = REPDIR / f"{rname.replace(' ', '_')}.csv"
                    file_handler.savereportcsv(rows, out, rname=rname)
                    print(f"Report card CSV created with name '{rname}': {out}")
                    file_handler.showfile(out)
                wait()
            elif ch == "12":
                header("Export class result CSV")
                cn = input("Class name: ").strip()
                rows = database.fetchclassresults(cn)
                if rows:
                    nameandcsv(pd.DataFrame(rows), defname=f"Class_{cn}_Results")
                else:
                    print("No results found for this class.")
                wait()
            elif ch == "13":
                header("Rank results")
                cn = input("Class name: ").strip()
                rows = database.getranked(cn)
                showtable(rows)
                if rows:
                    ex = input("Export and reveal ranked results in CSV? (y/n): ").strip().lower()
                    if ex == "y":
                        nameandcsv(pd.DataFrame(rows), defname=f"Class_{cn}_Rankings")
                wait()
            elif ch == "14":
                header("Input Text File (.txt) -> Database -> Reveal in CSV")
                txtfileprocess()
                wait()
            elif ch == "15":
                import gui
                gui.startgui()
            elif ch == "16":
                header("Analytics: Who Scored Most & Student Comparison")
                analytics()
                wait()
            elif ch == "0":
                print("Bye! study well!")
                break
            else:
                print("wrong choice, type properly")
                wait()
        except MySQLError:
            print("MySQL is not running or the connection details are wrong.")
            print("Start MySQL Server and check MYSQL_HOST, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DATABASE, MYSQL_PORT.")
            wait()


def main():
    # entry point - no flag = GUI, --cli flag = terminal
    if "--cli" in sys.argv:
        climain()
    else:
        try:
            import gui
            gui.startgui()
        except Exception as e:
            print(f"Could not start GUI ({e}). Falling back to CLI mode...")
            climain()


if __name__ == "__main__":
    main()
