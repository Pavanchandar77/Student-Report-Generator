# main.py - student result analysis and report generator
# terminal mode project for ingesting text files, storing in mysql, tabulating, and creating text files

import os
import sys
from pathlib import Path

# fix windows console utf-8 encoding
if sys.platform == "win32":
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8")
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, IntPrompt, Prompt
from rich.rule import Rule
from rich.table import Table
from tabulate import tabulate

import database
import file_handler

console = Console(highlight=False)

BASEDIR = Path(__file__).resolve().parent
SAMPLE_DIR = BASEDIR / "sample_data"


def cls():
    # clear screen
    console.clear()


def wait():
    # pause until enter pressed
    console.print("\n[dim]Press [bold cyan]Enter[/bold cyan] to go back to menu...[/dim]")
    input()


def banner():
    # header banner
    ok, msg = database.checkcon()
    st_clr = "green" if ok else "red"
    st_txt = "[*] Database Connected" if ok else f"[!] DB Error: {msg}"

    grid = Table.grid(expand=True)
    grid.add_column(justify="left")
    grid.add_column(justify="right")
    grid.add_row("[bold white]STUDENT RESULT ANALYSIS & REPORT SYSTEM[/bold white]", f"[{st_clr}]{st_txt}[/]")
    grid.add_row("[dim cyan]CBSE Class XII Multi-Year Analyzer[/dim cyan]", "[dim]Supports Multi-DB by Academic Year[/dim]")

    console.print(Panel(grid, border_style="bright_blue", box=box.ROUNDED, padding=(1, 2)))


def askdb():
    # prompt user to select an academic year database
    dbs = database.getdbs()
    if not dbs:
        console.print("\n[bold red][!] No academic year databases found.[/bold red]")
        console.print("[yellow]Please ingest a text file (.txt) first using Option 1.[/yellow]\n")
        if Confirm.ask("Would you like to import a file now?", default=True):
            importtxt()
            dbs = database.getdbs()
            if not dbs:
                return None
        else:
            return None

    if len(dbs) == 1:
        d = dbs[0]
        console.print(f"\n[dim]Using Database:[/dim] [bold cyan]{d['db']}[/bold cyan] [dim](Year: {d['year']} | {d['studs']} Students)[/dim]\n")
        return d["db"]

    tbl = Table(title="SELECT ACADEMIC YEAR DATABASE", box=box.ROUNDED)
    tbl.add_column("No.", justify="right", style="bold yellow", width=4)
    tbl.add_column("Database", style="bold cyan")
    tbl.add_column("Academic Year", justify="center", style="bold green")
    tbl.add_column("Students", justify="right", style="white")
    tbl.add_column("School", style="dim")

    for i, it in enumerate(dbs, start=1):
        tbl.add_row(str(i), it["db"], it["year"], str(it["studs"]), it["school"])

    console.print("\n", tbl)
    ch = Prompt.ask("[bold cyan]Choose database[/bold cyan]", choices=[str(i) for i in range(1, len(dbs) + 1)], default="1")
    chosen = dbs[int(ch) - 1]
    console.print(f"[dim]Selected:[/dim] [bold green]{chosen['db']}[/bold green] (Year {chosen['year']})\n")
    return chosen["db"]


def askdownload(txt_content, default_filename="report.txt"):
    # asks user if they want to download the displayed report as a text file
    console.print("\n" + "-" * 70)
    dl = Confirm.ask("[bold cyan]Do you want to download / save this report as a text file?[/bold cyan]", default=False)
    if dl:
        out_file = file_handler.savetxt(txt_content, default_filename)
        console.print(f"[bold green][OK] Saved text file to:[/bold green] [cyan]{out_file}[/cyan]")
    else:
        console.print("[dim]Report displayed on screen. No text file saved.[/dim]")
    wait()


def getscope(db=None):
    # ask user if they want entire school or specific class/section
    classes = database.getclasses(db=db)
    if not classes or len(classes) <= 1:
        return None, None

    console.print("\n[bold cyan]Select Filter Scope:[/bold cyan]")
    console.print("  [bold yellow]0.[/bold yellow] Entire School (All Classes)")
    for i, c in enumerate(classes, start=1):
        console.print(f"  [bold yellow]{i}.[/bold yellow] Class: [bold]{c}[/bold]")

    ch = Prompt.ask("Choose scope", choices=[str(x) for x in range(len(classes) + 1)], default="0")
    if ch == "0":
        return None, None

    sel_cls = classes[int(ch) - 1]

    secs = database.getsections(cls=sel_cls, db=db)
    if len(secs) > 1:
        console.print(f"\n[bold cyan]Select Section for Class '{sel_cls}':[/bold cyan]")
        console.print("  [bold yellow]0.[/bold yellow] All Sections")
        for i, s in enumerate(secs, start=1):
            console.print(f"  [bold yellow]{i}.[/bold yellow] Section: [bold]{s}[/bold]")
        sch = Prompt.ask("Choose section", choices=[str(x) for x in range(len(secs) + 1)], default="0")
        if sch != "0":
            return sel_cls, secs[int(sch) - 1]

    return sel_cls, None


# ========== MENU FUNCTIONS ==========

def importtxt():
    # 1. read text file and save into MySQL DB corresponding to that year
    console.print(Rule("[bold cyan][Ingest] Input Text File (.txt)[/bold cyan]", style="bright_blue"))
    console.print("[dim]Supported: CBSE Gazette (.txt), Wide table, or Key-Value blocks.[/dim]\n")

    sample_f = SAMPLE_DIR / "result2015.txt"
    def_p = str(sample_f) if sample_f.exists() else ""
    p = Prompt.ask("Enter path to .txt file", default=def_p).strip().strip('"').strip("'")
    fp = Path(p)

    if not fp.exists():
        console.print(f"[bold red][X] File not found:[/bold red] '{p}'")
        wait()
        return

    with console.status("[green]Reading and parsing file...[/green]"):
        res = file_handler.parsetxt(fp)

    sc = len(res.get("studs", []))
    mc = len(res.get("marks", []))
    errs = res.get("errs", [])
    meta = res.get("meta", {})

    if sc == 0:
        console.print("[bold red][X] No student records found in file.[/bold red]")
        wait()
        return

    tbl = Table(title=f"Parsed Summary: {fp.name}", box=box.ROUNDED)
    tbl.add_column("Property / Metric", style="cyan bold")
    tbl.add_column("Value", justify="right", style="green bold")
    if meta.get("school"):
        tbl.add_row("School detected", meta["school"])
    if meta.get("year"):
        tbl.add_row("Exam Year", meta["year"])
    tbl.add_row("Students found", str(sc))
    tbl.add_row("Marks found", str(mc))
    tbl.add_row("Warnings", str(len(errs)))
    console.print(tbl)

    # determine target database
    yr = meta.get("year", "")
    def_db = f"cbse_{yr}" if yr else "cbse_general"
    console.print(f"\n[bold cyan]Target MySQL Database for this batch:[/bold cyan] [bold green]{def_db}[/bold green]")
    target_db = Prompt.ask("Enter database name (or press Enter for default)", default=def_db).strip()

    if not Confirm.ask(f"\nSave these records to database '{target_db}'?", default=True):
        console.print("[yellow]Cancelled.[/yellow]")
        wait()
        return

    with console.status(f"[blue]Saving to MySQL database '{target_db}'...[/blue]"):
        saved = file_handler.savetodb(res, target_db=target_db)

    pnl = Panel(
        f"[bold green][OK] Database '{saved['db']}' Created & Updated Successfully![/bold green]\n\n"
        f"- Target Database: [bold cyan]{saved['db']}[/bold cyan]\n"
        f"- Academic Year: [bold white]{saved.get('year') or 'N/A'}[/bold white]\n"
        f"- Students saved: [bold white]{saved['studs_saved']}[/bold white]\n"
        f"- Marks saved: [bold white]{saved['marks_saved']}[/bold white]\n"
        f"- Status: [bold green]Ready for Analysis[/bold green]",
        title="[bold green]Import Result[/bold green]",
        border_style="green",
        box=box.ROUNDED,
    )
    console.print(pnl)
    wait()


def showtoppers():
    # 2. school toppers (best student top 3) -> asks database, asks count, displays, then asks to download
    console.print(Rule("[bold gold1][Toppers] Best Students / School Toppers[/bold gold1]", style="gold1"))

    # ask database
    db = askdb()
    if not db:
        return

    # ask scope and ranks
    cls_f, sec_f = getscope(db=db)
    lim = IntPrompt.ask("\nHow many top ranks to show (e.g. 3 for Top 3)?", default=3)

    with console.status("[cyan]Loading toppers...[/cyan]"):
        rows = database.gettoppers(cls=cls_f, sec=sec_f, lim=lim, db=db)

    if not rows:
        console.print("[yellow]No records found.[/yellow]")
        wait()
        return

    sc_name = f"{cls_f or 'School'} ({sec_f or 'All Sections'}) [{db}]"
    tbl = Table(title=f"NEW SCHOOL TOPPERS - {sc_name.upper()}", box=box.ROUNDED)
    tbl.add_column("PLACE", justify="center", style="bold yellow")
    tbl.add_column("ROLL NO", justify="center", style="cyan")
    tbl.add_column("NAME", style="bold white", min_width=24)
    tbl.add_column("CLASS-SEC", justify="center", style="dim")
    tbl.add_column("MARK", justify="right", style="bold green")
    tbl.add_column("%", justify="right", style="bold bright_yellow")

    medals = {"I": "[1st] I", "II": "[2nd] II", "III": "[3rd] III"}
    txt_rows = []
    for r in rows:
        pl = medals.get(r["place"], r["place"])
        tbl.add_row(pl, r["roll_no"], r["name"], f"{r['class_name']}-{r['section']}", f"{r['mark']:.0f}/{r['max_mark']:.0f}", f"{r['pct']:.2f}%")
        txt_rows.append([r["place"], r["roll_no"], r["name"], f"{r['class_name']}-{r['section']}", f"{r['mark']:.0f}/{r['max_mark']:.0f}", f"{r['pct']:.2f}%"])

    console.print("\n", tbl)

    # text content ready if user wants to download
    txt_hdr = f"NEW SCHOOL TOPPERS - {sc_name.upper()}\n"
    txt_table = txt_hdr + "\n" + tabulate(txt_rows, headers=["PLACE", "ROLL NO", "NAME", "CLASS-SEC", "MARK", "%"], tablefmt="grid")
    askdownload(txt_table, f"top_{lim}_{db}.txt")


def showsummary():
    # 3. overall school average and score breakdown
    console.print(Rule("[bold magenta][Summary] Overall Average & Score Ranges[/bold magenta]", style="magenta"))

    db = askdb()
    if not db:
        return

    cls_f, sec_f = getscope(db=db)

    with console.status("[cyan]Calculating summary...[/cyan]"):
        s = database.getsummary(cls=cls_f, sec=sec_f, db=db)

    tot = s["total"]
    if tot == 0:
        console.print("[yellow]No data found.[/yellow]")
        wait()
        return

    c1 = Panel(f"[bold green]{s['avg']:.2f} %[/bold green]\n[dim]School Average[/dim]", title="AVERAGE", box=box.ROUNDED)
    c2 = Panel(f"[bold white]{tot}[/bold white]\n[dim]Total Appeared[/dim]", title="APPEARED", box=box.ROUNDED)
    c3 = Panel(f"[bold yellow]{s['dist']}[/bold yellow] ([dim]{s['dist']/tot*100:.1f}%[/dim])\n[dim]Distinction (>=75%)[/dim]", title="DISTINCTION", box=box.ROUNDED)

    grid = Table.grid(expand=True, padding=(0, 2))
    grid.add_column(ratio=1)
    grid.add_column(ratio=1)
    grid.add_column(ratio=1)
    grid.add_row(c1, c2, c3)
    console.print("\n", grid, "\n")

    t1 = Table(title=f"OVERALL SCHOOL AVERAGE & CLASSIFICATION ({db})", box=box.ROUNDED)
    t1.add_column("Classification", style="bold white")
    t1.add_column("Count", justify="right", style="bold green")
    t1.add_column("Percentage", justify="right", style="cyan")

    t1.add_row("Total No. appeared", str(tot), "100.00 %")
    t1.add_row("No. of Distinction (>=75%)", str(s["dist"]), f"{s['dist']/tot*100:.2f} %")
    t1.add_row("No. of 1st Class (includes distinction)", str(s["first"]), f"{s['first']/tot*100:.2f} %")
    t1.add_row("No. of 2nd Class (50-59%)", str(s["second"]) if s["second"] > 0 else "-", f"{s['second']/tot*100:.2f} %" if s["second"] > 0 else "-")
    t1.add_row("No. of Compartment (<33%)", str(s["comp"]) if s["comp"] > 0 else "Nil", f"{s['comp']/tot*100:.2f} %" if s["comp"] > 0 else "0.00 %")
    console.print(t1, "\n")

    t2 = Table(title=f"SCORE RANGE DISTRIBUTION ({db})", box=box.ROUNDED)
    t2.add_column("Score Range", style="bold white")
    t2.add_column("No. of Students", justify="right", style="bold green")
    t2.add_column("Percentage", justify="right", style="bold bright_yellow")

    for r in s["ranges"]:
        t2.add_row(r["range"], str(r["cnt"]), f"{r['pct']:.2f} %")
    t2.add_section()
    t2.add_row("TOTAL", str(tot), "100.00 %", style="bold cyan")
    console.print(t2)

    # text content
    txt_out = (
        f"OVERALL SCHOOL AVERAGE & SCORE BREAKDOWN ({db})\n"
        f"School Average: {s['avg']:.2f} %\n\n"
        + tabulate(
            [
                ["Total No. appeared", tot, "100.00 %"],
                ["No. of Distinction (>=75%)", s["dist"], f"{s['dist']/tot*100:.2f} %"],
                ["No. of 1st Class (includes distinction)", s["first"], f"{s['first']/tot*100:.2f} %"],
                ["No. of 2nd Class", s["second"] if s["second"] > 0 else "-", f"{s['second']/tot*100:.2f} %" if s["second"] > 0 else "-"],
                ["No. of Compartment", s["comp"] if s["comp"] > 0 else "Nil", f"{s['comp']/tot*100:.2f} %" if s["comp"] > 0 else "0.00 %"],
            ],
            headers=["Classification", "Count", "Percentage"],
            tablefmt="grid"
        )
        + "\n\nSCORE RANGE DISTRIBUTION:\n"
        + tabulate([[it["range"], it["cnt"], f"{it['pct']:.2f}%"] for it in s["ranges"]] + [["TOTAL", tot, "100.00%"]], headers=["Score Range", "No. of Students", "%"], tablefmt="grid")
    )
    askdownload(txt_out, f"summary_{db}.txt")


def showsubstats():
    # 4. subject average and stats
    console.print(Rule("[bold cyan][Subjects] Subject Average & Statistics Table[/bold cyan]", style="cyan"))

    db = askdb()
    if not db:
        return

    cls_f, sec_f = getscope(db=db)

    with console.status("[cyan]Loading subject stats...[/cyan]"):
        rows = database.getsubstats(cls=cls_f, sec=sec_f, db=db)

    if not rows:
        console.print("[yellow]No records found.[/yellow]")
        wait()
        return

    tbl = Table(title=f"SUBJECT AVERAGE & STATISTICS ({db})", box=box.ROUNDED)
    tbl.add_column("Subject", style="bold white", min_width=20)
    tbl.add_column("No.of Students", justify="right", style="cyan")
    tbl.add_column("Subject Average", justify="right", style="bold green")
    tbl.add_column("Highest Marks", justify="right", style="bold yellow")
    tbl.add_column("No.of Students (Highest)", justify="right", style="white")
    tbl.add_column("No.of Centum", justify="right", style="bold bright_yellow")
    tbl.add_column("Lowest Marks", justify="right", style="dim")

    txt_rows = []
    for r in rows:
        c_str = str(r["cent_cnt"]) if r["cent_cnt"] > 0 else "-"
        tbl.add_row(
            r["subject"], str(r["stu_cnt"]), f"{r['avg']:.2f}", f"{r['high']:.0f}",
            str(r["high_cnt"]), c_str, f"{r['low']:.0f}"
        )
        txt_rows.append([
            r["subject"], r["stu_cnt"], f"{r['avg']:.2f}", f"{r['high']:.0f}",
            r["high_cnt"], c_str, f"{r['low']:.0f}"
        ])

    console.print("\n", tbl)

    txt_hdr = f"SUBJECT AVERAGE & STATISTICS ({db})\n"
    txt_out = txt_hdr + "\n" + tabulate(
        txt_rows,
        headers=["Subject", "No. of Students", "Subject Average", "Highest marks", "No. of Students", "No. of Centum", "Lowest marks"],
        tablefmt="grid"
    )
    askdownload(txt_out, f"subject_averages_{db}.txt")


def showsubtoppers():
    # 5. subject toppers roster
    console.print(Rule("[bold green][Roster] Subject Toppers List[/bold green]", style="green"))

    db = askdb()
    if not db:
        return

    cls_f, sec_f = getscope(db=db)

    subs = database.getsubjects(db=db)
    console.print("\n[bold cyan]Choose Filter Option:[/bold cyan]")
    console.print("  [bold yellow]0.[/bold yellow] All Subjects (Complete Roster)")
    for i, s in enumerate(subs, start=1):
        console.print(f"  [bold yellow]{i}.[/bold yellow] {s}")

    ch = Prompt.ask("Choose subject", choices=[str(i) for i in range(len(subs) + 1)], default="0")
    sel_sub = None if ch == "0" else subs[int(ch) - 1]

    with console.status("[cyan]Loading subject toppers...[/cyan]"):
        grps = database.getsubtoppers(cls=cls_f, sec=sec_f, sub=sel_sub, db=db)

    if not grps:
        console.print("[yellow]No records found.[/yellow]")
        wait()
        return

    txt_lines = [f"SUBJECT TOPPERS ROSTER ({db})", "=" * 60]

    for g in grps:
        hi = g["high"]
        st_list = g["students"]
        n_st = len(st_list)
        suffix = "student" if n_st == 1 else "students"

        tbl = Table(title=f"{g['subject'].upper()} ({hi:.0f} marks - {n_st} {suffix})", box=box.ROUNDED)
        tbl.add_column("Roll No", justify="center", style="cyan")
        tbl.add_column("Student Name", style="bold white", min_width=28)
        tbl.add_column("Class-Sec", justify="center", style="dim")
        tbl.add_column("Mark", justify="right", style="bold green")

        txt_lines.append(f"\n{g['subject'].upper()} ({hi:.0f} marks - {n_st} {suffix})")
        txt_lines.append("-" * 40)

        for st in st_list:
            tbl.add_row(st["roll_no"], st["name"], f"{st['class_name']}-{st['section']}", f"{hi:.0f}")
            txt_lines.append(f"  {st['roll_no']}  {st['name']}  ({st['class_name']}-{st['section']})")

        console.print(tbl)

    txt_out = "\n".join(txt_lines)
    askdownload(txt_out, f"subject_toppers_{db}.txt")


def showmeritlist():
    # 6. full ranked merit list
    console.print(Rule("[bold bright_white][Merit] Full Ranked Merit List[/bold bright_white]", style="bright_white"))

    db = askdb()
    if not db:
        return

    cls_f, sec_f = getscope(db=db)

    with console.status("[cyan]Generating rank list...[/cyan]"):
        rows = database.getmeritlist(cls=cls_f, sec=sec_f, db=db)

    if not rows:
        console.print("[yellow]No records found.[/yellow]")
        wait()
        return

    tbl = Table(title=f"MERIT LIST ({len(rows)} Students) [{db}]", box=box.ROUNDED)
    tbl.add_column("Rank", justify="right", style="bold yellow")
    tbl.add_column("Roll No", justify="center", style="cyan")
    tbl.add_column("Name", style="bold white", min_width=24)
    tbl.add_column("Class-Sec", justify="center", style="dim")
    tbl.add_column("Total", justify="right", style="bold green")
    tbl.add_column("%", justify="right", style="bold bright_yellow")
    tbl.add_column("Status", justify="center", style="bold white")

    txt_rows = []
    st_colors = {"Distinction": "bold green", "1st Class": "green", "2nd Class": "yellow", "Compartment": "bold red", "Pass": "white"}

    for r in rows:
        clr = st_colors.get(r["status"], "white")
        tbl.add_row(str(r["rank"]), r["roll_no"], r["name"], f"{r['class_name']}-{r['section']}", f"{r['tot_got']:.0f}/{r['tot_max']:.0f}", f"{r['pct']:.2f}%", f"[{clr}]{r['status']}[/]")
        txt_rows.append([r["rank"], r["roll_no"], r["name"], f"{r['class_name']}-{r['section']}", f"{r['tot_got']:.0f}/{r['tot_max']:.0f}", f"{r['pct']:.2f}%", r["status"]])

    console.print("\n", tbl)

    txt_hdr = f"FULL RANKED MERIT LIST ({len(rows)} Students) [{db}]\n"
    txt_out = txt_hdr + "\n" + tabulate(
        txt_rows,
        headers=["Rank", "Roll No", "Name", "Class-Sec", "Total", "%", "Status"],
        tablefmt="grid"
    )
    askdownload(txt_out, f"merit_list_{db}.txt")


def showfilters():
    # 7. advanced filter queries
    console.print(Rule("[bold orange1][Filters] Advanced Query Filters[/bold orange1]", style="orange1"))

    db = askdb()
    if not db:
        return

    cls_f, sec_f = getscope(db=db)

    console.print("  [bold yellow]1.[/bold yellow] Centum Club (Students scoring 100/100)")
    console.print("  [bold yellow]2.[/bold yellow] Distinction List (>= 75%)")
    console.print("  [bold yellow]3.[/bold yellow] First Class List (>= 60%)")
    console.print("  [bold yellow]4.[/bold yellow] Compartment / Remedial List (< 33%)")
    console.print("  [bold yellow]5.[/bold yellow] Subject Filter by Minimum Mark Cut-off")
    console.print("  [bold yellow]6.[/bold yellow] Custom Percentage Range (e.g. 90% to 100%)")
    console.print("  [bold yellow]0.[/bold yellow] Back to Menu\n")

    fch = Prompt.ask("Choose filter", choices=[str(i) for i in range(7)], default="1")
    if fch == "0":
        return

    txt_title = ""
    txt_rows = []
    txt_hdrs = []

    if fch == "1":
        # centum
        rows = database.getcentums(cls=cls_f, sec=sec_f, db=db)
        txt_title = f"CENTUM CLUB (100 MARKS) [{db}]"
        tbl = Table(title=txt_title, box=box.ROUNDED)
        tbl.add_column("Subject", style="bold yellow")
        tbl.add_column("Roll No", justify="center", style="cyan")
        tbl.add_column("Name", style="bold white", min_width=24)
        tbl.add_column("Class-Sec", justify="center", style="dim")
        tbl.add_column("Marks", justify="right", style="bold green")

        txt_hdrs = ["Subject", "Roll No", "Name", "Class-Sec", "Marks"]
        for r in rows:
            tbl.add_row(r["subject_name"], r["roll_no"], r["name"], f"{r['class_name']}-{r['section']}", f"{r['marks_obtained']:.0f}")
            txt_rows.append([r["subject_name"], r["roll_no"], r["name"], f"{r['class_name']}-{r['section']}", f"{r['marks_obtained']:.0f}"])
        console.print(tbl)

    elif fch in ("2", "3", "4"):
        cat_map = {"2": "Distinction", "3": "1st", "4": "Compartment"}
        cat_name = cat_map[fch]
        rows = database.getbycategory(cat_name, cls=cls_f, sec=sec_f, db=db)
        txt_title = f"{cat_name.upper()} STUDENTS ({len(rows)} Students) [{db}]"
        tbl = Table(title=txt_title, box=box.ROUNDED)
        tbl.add_column("Rank", justify="right", style="bold yellow")
        tbl.add_column("Roll No", justify="center", style="cyan")
        tbl.add_column("Name", style="bold white", min_width=24)
        tbl.add_column("Class-Sec", justify="center", style="dim")
        tbl.add_column("Total", justify="right", style="bold green")
        tbl.add_column("%", justify="right", style="bold bright_yellow")

        txt_hdrs = ["Rank", "Roll No", "Name", "Class-Sec", "Total", "%"]
        for r in rows:
            tbl.add_row(str(r["rank"]), r["roll_no"], r["name"], f"{r['class_name']}-{r['section']}", f"{r['tot_got']:.0f}/{r['tot_max']:.0f}", f"{r['pct']:.2f}%")
            txt_rows.append([r["rank"], r["roll_no"], r["name"], f"{r['class_name']}-{r['section']}", f"{r['tot_got']:.0f}/{r['tot_max']:.0f}", f"{r['pct']:.2f}%"])
        console.print(tbl)

    elif fch == "5":
        subs = database.getsubjects(db=db)
        for i, s in enumerate(subs, start=1):
            console.print(f"  {i}. {s}")
        sch = Prompt.ask("Choose subject", choices=[str(i) for i in range(1, len(subs) + 1)])
        sub_name = subs[int(sch) - 1]
        cut = IntPrompt.ask(f"Enter minimum mark cut-off for {sub_name}", default=90)

        rows = database.getsubroster(sub_name, cls=cls_f, sec=sec_f, minm=cut, db=db)
        txt_title = f"{sub_name.upper()} >= {cut} MARKS ({len(rows)} Students) [{db}]"
        tbl = Table(title=txt_title, box=box.ROUNDED)
        tbl.add_column("Rank", justify="right", style="bold yellow")
        tbl.add_column("Roll No", justify="center", style="cyan")
        tbl.add_column("Name", style="bold white", min_width=24)
        tbl.add_column("Marks", justify="right", style="bold green")
        tbl.add_column("%", justify="right", style="bold bright_yellow")

        txt_hdrs = ["Rank", "Roll No", "Name", "Marks", "%"]
        for r in rows:
            tbl.add_row(str(r["rk"]), r["roll_no"], r["name"], f"{r['marks_obtained']:.0f}", f"{r['pct']:.2f}%")
            txt_rows.append([r["rk"], r["roll_no"], r["name"], f"{r['marks_obtained']:.0f}", f"{r['pct']:.2f}%"])
        console.print(tbl)

    elif fch == "6":
        p_min = IntPrompt.ask("Enter minimum percentage", default=90)
        p_max = IntPrompt.ask("Enter maximum percentage", default=100)
        rows = database.getbyrange(p_min, p_max, cls=cls_f, sec=sec_f, db=db)
        txt_title = f"STUDENTS IN RANGE {p_min}% - {p_max}% ({len(rows)} Students) [{db}]"
        tbl = Table(title=txt_title, box=box.ROUNDED)
        tbl.add_column("Rank", justify="right", style="bold yellow")
        tbl.add_column("Roll No", justify="center", style="cyan")
        tbl.add_column("Name", style="bold white", min_width=24)
        tbl.add_column("Class-Sec", justify="center", style="dim")
        tbl.add_column("Total", justify="right", style="bold green")
        tbl.add_column("%", justify="right", style="bold bright_yellow")

        txt_hdrs = ["Rank", "Roll No", "Name", "Class-Sec", "Total", "%"]
        for r in rows:
            tbl.add_row(str(r["rank"]), r["roll_no"], r["name"], f"{r['class_name']}-{r['section']}", f"{r['tot_got']:.0f}/{r['tot_max']:.0f}", f"{r['pct']:.2f}%")
            txt_rows.append([r["rank"], r["roll_no"], r["name"], f"{r['class_name']}-{r['section']}", f"{r['tot_got']:.0f}/{r['tot_max']:.0f}", f"{r['pct']:.2f}%"])
        console.print(tbl)

    txt_out = txt_title + "\n\n" + tabulate(txt_rows, headers=txt_hdrs, tablefmt="grid")
    askdownload(txt_out, f"filter_report_{db}.txt")


def showreportcard():
    # 8. individual report card
    console.print(Rule("[bold deep_sky_blue1][Report Card] Student Marks Lookup[/bold deep_sky_blue1]", style="deep_sky_blue1"))

    db = askdb()
    if not db:
        return

    qval = Prompt.ask("\nEnter Student Roll No or Full Name").strip()
    if not qval:
        return

    rows = database.getreportcard(qval, db=db)
    if not rows:
        console.print(f"[bold red][X] No student found for:[/bold red] '{qval}'")
        wait()
        return

    s = rows[0]
    mks = [r for r in rows if r.get("subject_name")]
    tot_got = sum(float(r["marks_obtained"]) for r in mks)
    tot_max = sum(float(r["max_marks"]) for r in mks)
    pct = (tot_got / tot_max * 100) if tot_max > 0 else 0.0

    pnl = Panel(
        f"[bold white]Roll No:[/bold white] [cyan]{s['roll_no']}[/cyan]   "
        f"[bold white]Name:[/bold white] [bold yellow]{s['name']}[/bold yellow]   "
        f"[bold white]Class:[/bold white] [green]{s['class_name']}-{s['section']}[/green]   "
        f"[bold white]Database:[/bold white] [cyan]{db}[/cyan]",
        title="[bold green]STUDENT DETAILS[/bold green]",
        box=box.ROUNDED,
    )
    console.print(pnl)

    tbl = Table(box=box.ROUNDED)
    tbl.add_column("Subject", style="bold white", min_width=22)
    tbl.add_column("Marks Obtained", justify="right", style="bold green", width=16)
    tbl.add_column("Maximum", justify="right", style="dim", width=12)
    tbl.add_column("Percentage", justify="right", style="bold bright_yellow", width=14)

    txt_rows = []
    for m in mks:
        g = float(m["marks_obtained"])
        x = float(m["max_marks"])
        p = g / x * 100 if x > 0 else 0.0
        tbl.add_row(m["subject_name"], f"{g:.0f}", f"{x:.0f}", f"{p:.2f} %")
        txt_rows.append([m["subject_name"], f"{g:.0f}", f"{x:.0f}", f"{p:.2f} %"])

    tbl.add_section()
    tbl.add_row("TOTAL", f"{tot_got:.0f}", f"{tot_max:.0f}", f"{pct:.2f} %", style="bold cyan")
    txt_rows.append(["TOTAL", f"{tot_got:.0f}", f"{tot_max:.0f}", f"{pct:.2f} %"])
    console.print(tbl)

    txt_hdr = f"REPORT CARD: {s['name']} (Roll: {s['roll_no']}) - Class: {s['class_name']}-{s['section']} [{db}]\n"
    txt_out = txt_hdr + "\n" + tabulate(txt_rows, headers=["Subject", "Marks", "Max", "%"], tablefmt="grid")
    askdownload(txt_out, f"report_card_{s['roll_no']}_{db}.txt")


def comparetwo():
    # 9. side by side comparison
    console.print(Rule("[bold violet][Compare] Compare Two Students[/bold violet]", style="violet"))

    db = askdb()
    if not db:
        return

    r1 = Prompt.ask("Enter Roll No or Name of Student 1").strip()
    r2 = Prompt.ask("Enter Roll No or Name of Student 2").strip()

    cmp_res = database.comparestuds(r1, r2, db=db)
    if not cmp_res:
        console.print("[bold red][X] One or both students could not be found in database.[/bold red]")
        wait()
        return

    s1, s2 = cmp_res["s1"], cmp_res["s2"]

    pnl = Panel(
        f"[bold cyan]{s1['name']} ({s1['roll_no']})[/bold cyan] vs [bold magenta]{s2['name']} ({s2['roll_no']})[/bold magenta]\n"
        f"Leader: [bold bright_green]{cmp_res['leader']}[/] (Margin: [yellow]{cmp_res['diff_pct']} %[/yellow])",
        title=f"COMPARISON [{db}]",
        box=box.ROUNDED,
    )
    console.print(pnl)

    tbl = Table(box=box.ROUNDED)
    tbl.add_column("Subject", style="bold white", min_width=22)
    tbl.add_column(f"{s1['name']} ({s1['roll_no']})", justify="right", style="cyan", width=22)
    tbl.add_column(f"{s2['name']} ({s2['roll_no']})", justify="right", style="magenta", width=22)
    tbl.add_column("Diff", justify="right", style="yellow", width=12)
    tbl.add_column("Leader", justify="center", style="bold green", width=18)

    txt_rows = []
    for itm in cmp_res["subs"]:
        d_str = f"+{itm['diff']:.0f}" if itm["diff"] > 0 else f"{itm['diff']:.0f}"
        v1_str = f"{itm['v1']:.0f}" if itm["v1"] is not None else "-"
        v2_str = f"{itm['v2']:.0f}" if itm["v2"] is not None else "-"
        tbl.add_row(itm["sub"], v1_str, v2_str, d_str, itm["leader"])
        txt_rows.append([itm["sub"], v1_str, v2_str, d_str, itm["leader"]])

    tbl.add_section()
    tbl.add_row(
        "TOTAL",
        f"{s1['tot']:.0f} ({s1['pct']:.2f}%)",
        f"{s2['tot']:.0f} ({s2['pct']:.2f}%)",
        f"{cmp_res['diff_pct']:.2f}%",
        f"[bold bright_green]{cmp_res['leader']}[/]",
        style="bold white",
    )
    txt_rows.append(["TOTAL", f"{s1['tot']:.0f} ({s1['pct']:.2f}%)", f"{s2['tot']:.0f} ({s2['pct']:.2f}%)", f"{cmp_res['diff_pct']:.2f}%", cmp_res["leader"]])
    console.print("\n", tbl)

    txt_hdr = f"COMPARISON: {s1['name']} ({s1['roll_no']}) vs {s2['name']} ({s2['roll_no']}) [{db}]\nLeader: {cmp_res['leader']} (Margin: {cmp_res['diff_pct']}%)\n"
    txt_out = txt_hdr + "\n" + tabulate(
        txt_rows,
        headers=["Subject", f"{s1['name']} ({s1['roll_no']})", f"{s2['name']} ({s2['roll_no']})", "Diff", "Leader"],
        tablefmt="grid"
    )
    askdownload(txt_out, f"comparison_{s1['roll_no']}_vs_{s2['roll_no']}_{db}.txt")


def makefullsheet():
    # 10. create complete 2-page CBSE printable analysis sheet matching Image 1 + Image 2
    console.print(Rule("[bold bright_green][Full Sheet] Generate Complete Result Analysis Sheet[/bold bright_green]", style="bright_green"))

    db = askdb()
    if not db:
        return

    cls_f, sec_f = getscope(db=db)

    with console.status(f"[cyan]Generating complete school analysis document for '{db}'...[/cyan]"):
        toppers = database.gettoppers(cls=cls_f, sec=sec_f, lim=10, db=db)
        summary = database.getsummary(cls=cls_f, sec=sec_f, db=db)
        sub_stats = database.getsubstats(cls=cls_f, sec=sec_f, db=db)
        sub_toppers = database.getsubtoppers(cls=cls_f, sec=sec_f, db=db)

    tot = summary["total"]
    if tot == 0:
        console.print("[yellow]No data found.[/yellow]")
        wait()
        return

    sch_title = database.getschoolmeta("school", "Chinmaya Vidyalaya, Anna Nagar, Chennai - 600 040.", db=db)
    yr = database.getschoolmeta("year", "2025-26", db=db)
    ex_hdr = f"CBSE EXAM STD - XII RESULT ANALYSIS ({yr})" if yr else "CBSE EXAM STD - XII RESULT ANALYSIS"

    lines = [
        "Hari Om",
        sch_title,
        ex_hdr,
        "=" * 82,
        "",
        "NEW SCHOOL TOPPERS",
        "-" * 82,
    ]

    t_rows = [[r["place"], r["name"], f"{r['mark']:.0f}", f"{r['pct']:.2f}%"] for r in toppers]
    lines.append(tabulate(t_rows, headers=["PLACE", "NAME", "MARK", "%"], tablefmt="grid"))
    lines.append("")

    lines.append(f"OVERALL SCHOOL AVERAGE = {summary['avg']:.2f} %\n")
    s_rows = [
        ["Total No. appeared", tot],
        ["No. of Distinction (>=75%)", summary["dist"]],
        ["No. of 1st Class (includes distinction)", summary["first"]],
        ["No. of 2nd Class", summary["second"] if summary["second"] > 0 else "-"],
        ["No. of Compartment", summary["comp"] if summary["comp"] > 0 else "Nil"],
    ]
    lines.append(tabulate(s_rows, headers=["Metric", "Count"], tablefmt="grid"))
    lines.append("")

    lines.append("SCORE RANGE DISTRIBUTION:")
    r_rows = [[it["range"], it["cnt"]] for it in summary["ranges"]]
    r_rows.append(["TOTAL", tot])
    lines.append(tabulate(r_rows, headers=["Score Range", "No. of Students"], tablefmt="grid"))
    lines.append("")

    lines.append("SUBJECT AVERAGE")
    lines.append("-" * 82)
    sub_rows = [
        [s["subject"], s["stu_cnt"], f"{s['avg']:.2f}", f"{s['high']:.0f}", s["high_cnt"], s["cent_cnt"] if s["cent_cnt"] > 0 else "-"]
        for s in sub_stats
    ]
    lines.append(tabulate(sub_rows, headers=["Subject", "No. of Students", "Subject Average", "Highest marks", "No. of Students", "No. of Centum"], tablefmt="grid"))
    lines.append("")

    lines.append("=" * 82)
    lines.append("SUBJECT TOPPERS")
    lines.append("=" * 82)
    for g in sub_toppers:
        hi = g["high"]
        st_list = g["students"]
        n_st = len(st_list)
        suffix = "student" if n_st == 1 else "students"
        lines.append(f"\n{g['subject'].upper()} ({hi:.0f} marks - {n_st} {suffix})")
        lines.append("-" * 40)
        for st in st_list:
            lines.append(f"  {st['name']}")

    full_doc = "\n".join(lines)

    # display preview
    console.print(Panel(
        f"[bold white]{sch_title}[/bold white]\n"
        f"[cyan]{ex_hdr}[/cyan]\n\n"
        f"- Toppers generated: [bold green]{len(toppers)}[/bold green]\n"
        f"- Overall School Average: [bold yellow]{summary['avg']:.2f} %[/bold yellow]\n"
        f"- Total Students Appeared: [bold white]{tot}[/bold white]\n"
        f"- Subjects analyzed: [bold green]{len(sub_stats)}[/bold green]\n"
        f"- Subject Toppers analyzed: [bold green]{len(sub_toppers)}[/bold green]",
        title=f"[bold green]Complete Analysis Ready ({db})[/bold green]",
        box=box.ROUNDED,
    ))

    askdownload(full_doc, f"complete_cbse_analysis_{db}.txt")


def dbtools():
    # 11. database status, switch, and reset
    console.print(Rule("[bold yellow][Database] Academic Year Databases[/bold yellow]", style="yellow"))
    dbs = database.getdbs()

    tbl = Table(title="ACADEMIC YEAR DATABASES", box=box.ROUNDED)
    tbl.add_column("No.", justify="right", style="bold yellow", width=4)
    tbl.add_column("Database", style="bold cyan")
    tbl.add_column("Year", justify="center", style="bold green")
    tbl.add_column("Students", justify="right", style="white")
    tbl.add_column("School", style="dim")

    for i, it in enumerate(dbs, start=1):
        tbl.add_row(str(i), it["db"], it["year"], str(it["studs"]), it["school"])
    console.print(tbl, "\n")

    console.print("  [bold yellow]1.[/bold yellow] Wipe / Reset a Specific Database")
    console.print("  [bold yellow]0.[/bold yellow] Back to Menu\n")

    ch = Prompt.ask("Choose option", choices=["0", "1"], default="0")
    if ch == "1" and dbs:
        sel = Prompt.ask("Choose database number to wipe", choices=[str(i) for i in range(1, len(dbs) + 1)])
        chosen_db = dbs[int(sel) - 1]["db"]
        if Confirm.ask(f"[bold red][!] Wipe all tables in database '{chosen_db}'?[/bold red]", default=False):
            database.resetdb(db=chosen_db)
            console.print(f"[bold green][OK] Database '{chosen_db}' cleared.[/bold green]")
        else:
            console.print("[yellow]Cancelled.[/yellow]")
    wait()


# ========== MAIN LOOP ==========

def main():
    database.initdb()

    menu_items = [
        ("1", "[Ingest] Input Text File (.txt)", "Parse CBSE gazette / text file into a year database"),
        ("2", "[Toppers] Best Students (Top 3)", "Select database, show top ranks, option to download"),
        ("3", "[Summary] Overall Average & Ranges", "School average %, distinctions, score range table"),
        ("4", "[Subjects] Subject Average & Stats", "Averages, highest marks, count of toppers, centums"),
        ("5", "[Roster] Subject Toppers List", "Highest score per subject with student names"),
        ("6", "[Merit] Full Ranked Merit List", "Complete rank roster with total marks and percentage"),
        ("7", "[Filter] Advanced Query Filters", "Centum club, distinction, cut-offs, custom % range"),
        ("8", "[Report] Individual Report Card", "Lookup student marks by Roll No or Name"),
        ("9", "[Compare] Side-by-Side Comparison", "Compare two students head to head"),
        ("10", "[Full Sheet] Master Print Document", "Generate complete 2-page CBSE analysis sheet"),
        ("11", "[Database] Academic Year Databases", "View active databases or reset a batch"),
        ("0", "[Exit] Quit", "Close program"),
    ]

    while True:
        cls()
        banner()

        tbl = Table.grid(padding=(0, 2))
        tbl.add_column(style="bold yellow", justify="right", width=4)
        tbl.add_column(style="bold white", min_width=34)
        tbl.add_column(style="dim", min_width=45)

        for num, title, desc in menu_items:
            tbl.add_row(f"{num}.", title, f"- {desc}")

        pnl = Panel(tbl, title="[bold white]MAIN MENU[/bold white]", border_style="bright_blue", box=box.ROUNDED, padding=(1, 2))
        console.print(pnl)

        ch = Prompt.ask("\n[bold cyan]Choose option[/bold cyan]", choices=[str(i) for i in range(12)], default="2")

        try:
            if ch == "1":
                importtxt()
            elif ch == "2":
                showtoppers()
            elif ch == "3":
                showsummary()
            elif ch == "4":
                showsubstats()
            elif ch == "5":
                showsubtoppers()
            elif ch == "6":
                showmeritlist()
            elif ch == "7":
                showfilters()
            elif ch == "8":
                showreportcard()
            elif ch == "9":
                comparestwo()
            elif ch == "10":
                makefullsheet()
            elif ch == "11":
                dbtools()
            elif ch == "0":
                console.print("\n[bold green]Goodbye! Study well![/bold green]\n")
                break
        except KeyboardInterrupt:
            break
        except Exception as e:
            console.print(f"\n[bold red][!] Error:[/bold red] {e}")
            wait()


if __name__ == "__main__":
    main()
