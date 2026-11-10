# main.py - student result analysis and report generator
# terminal mode project for ingesting text files, storing in mysql, and tabulating results

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

import database
import file_handler

console = Console(highlight=False)

BASEDIR = Path(__file__).resolve().parent
SAMPLE_FILE = BASEDIR / "sample_data" / "cbse_class12_results.txt"


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
    grid.add_row("[dim cyan]CBSE Class XII Result Analyzer[/dim cyan]", "[dim]Python + MySQL Project[/dim]")

    console.print(Panel(grid, border_style="bright_blue", box=box.ROUNDED, padding=(1, 2)))


def getscope():
    # ask user if they want entire school or specific class/section
    classes = database.getclasses()
    if not classes:
        return None, None

    console.print("\n[bold cyan]Select Filter Scope:[/bold cyan]")
    console.print("  [bold yellow]0.[/bold yellow] Entire School (All Classes)")
    for i, c in enumerate(classes, start=1):
        console.print(f"  [bold yellow]{i}.[/bold yellow] Class: [bold]{c}[/bold]")

    ch = Prompt.ask("Choose scope", choices=[str(x) for x in range(len(classes) + 1)], default="0")
    if ch == "0":
        return None, None

    sel_cls = classes[int(ch) - 1]

    # ask section if multiple
    secs = database.getsections(cls=sel_cls)
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
    # 1. read text file and save into mysql
    console.print(Rule("[bold cyan][Ingest] Input Text File (.txt)[/bold cyan]", style="bright_blue"))
    console.print("[dim]Supported: Wide table (Pipe/Tab/Comma), Key-Value block format, or columns.[/dim]\n")

    def_p = str(SAMPLE_FILE) if SAMPLE_FILE.exists() else ""
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

    if sc == 0:
        console.print("[bold red][X] No student records found in file.[/bold red]")
        wait()
        return

    tbl = Table(title=f"Parsed Summary: {fp.name}", box=box.ROUNDED)
    tbl.add_column("Metric", style="cyan bold")
    tbl.add_column("Count", justify="right", style="green bold")
    tbl.add_row("Students found", str(sc))
    tbl.add_row("Marks found", str(mc))
    tbl.add_row("Warnings", str(len(errs)))
    console.print(tbl)

    if not Confirm.ask("\nSave these records to the database?", default=True):
        console.print("[yellow]Cancelled.[/yellow]")
        wait()
        return

    with console.status("[blue]Saving to MySQL database...[/blue]"):
        saved = file_handler.savetodb(res)

    pnl = Panel(
        f"[bold green][OK] Database Updated Successfully![/bold green]\n\n"
        f"- Students saved: [bold white]{saved['studs_saved']}[/bold white]\n"
        f"- Marks saved: [bold white]{saved['marks_saved']}[/bold white]\n"
        f"- Status: [bold green]Ready[/bold green]",
        title="[bold green]Import Result[/bold green]",
        border_style="green",
        box=box.ROUNDED,
    )
    console.print(pnl)
    wait()


def showtoppers():
    # 2. school toppers matching image 1
    console.print(Rule("[bold gold1][Toppers] School / Class Toppers[/bold gold1]", style="gold1"))
    cls_f, sec_f = getscope()
    lim = IntPrompt.ask("\nHow many ranks to show?", default=5)

    with console.status("[cyan]Loading toppers...[/cyan]"):
        rows = database.gettoppers(cls=cls_f, sec=sec_f, lim=lim)

    if not rows:
        console.print("[yellow]No records found.[/yellow]")
        wait()
        return

    sc_name = f"{cls_f or 'School'} ({sec_f or 'All Sections'})"
    tbl = Table(title=f"NEW SCHOOL TOPPERS - {sc_name.upper()}", box=box.ROUNDED)
    tbl.add_column("PLACE", justify="center", style="bold yellow")
    tbl.add_column("ROLL NO", justify="center", style="cyan")
    tbl.add_column("NAME", style="bold white", min_width=24)
    tbl.add_column("CLASS-SEC", justify="center", style="dim")
    tbl.add_column("MARK", justify="right", style="bold green")
    tbl.add_column("%", justify="right", style="bold bright_yellow")

    medals = {"I": "[1st] I", "II": "[2nd] II", "III": "[3rd] III"}
    for r in rows:
        pl = medals.get(r["place"], r["place"])
        tbl.add_row(pl, r["roll_no"], r["name"], f"{r['class_name']}-{r['section']}", f"{r['mark']:.0f}/{r['max_mark']:.0f}", f"{r['pct']:.2f}")

    console.print("\n", tbl)
    wait()


def showsummary():
    # 3. overall school average and score breakdown matching image 1
    console.print(Rule("[bold magenta][Summary] Overall Average & Score Ranges[/bold magenta]", style="magenta"))
    cls_f, sec_f = getscope()

    with console.status("[cyan]Calculating summary...[/cyan]"):
        s = database.getsummary(cls=cls_f, sec=sec_f)

    tot = s["total"]
    if tot == 0:
        console.print("[yellow]No data found.[/yellow]")
        wait()
        return

    # summary cards
    c1 = Panel(f"[bold green]{s['avg']:.2f} %[/bold green]\n[dim]School Average[/dim]", title="AVERAGE", box=box.ROUNDED)
    c2 = Panel(f"[bold white]{tot}[/bold white]\n[dim]Total Appeared[/dim]", title="APPEARED", box=box.ROUNDED)
    c3 = Panel(f"[bold yellow]{s['dist']}[/bold yellow] ([dim]{s['dist']/tot*100:.1f}%[/dim])\n[dim]Distinction (>=75%)[/dim]", title="DISTINCTION", box=box.ROUNDED)

    grid = Table.grid(expand=True, padding=(0, 2))
    grid.add_column(ratio=1)
    grid.add_column(ratio=1)
    grid.add_column(ratio=1)
    grid.add_row(c1, c2, c3)
    console.print("\n", grid, "\n")

    # classification table
    t1 = Table(title="OVERALL SCHOOL AVERAGE & CLASSIFICATION", box=box.ROUNDED)
    t1.add_column("Classification", style="bold white")
    t1.add_column("Count", justify="right", style="bold green")
    t1.add_column("Percentage", justify="right", style="cyan")

    t1.add_row("Total No. appeared", str(tot), "100.00 %")
    t1.add_row("No. of Distinction (>= 75%)", str(s["dist"]), f"{s['dist']/tot*100:.2f} %")
    t1.add_row("No. of 1st Class (>= 60%, includes distinction)", str(s["first"]), f"{s['first']/tot*100:.2f} %")
    t1.add_row("No. of 2nd Class (50-59%)", str(s["second"]), f"{s['second']/tot*100:.2f} %")
    cmp_style = "bold red" if s["comp"] > 0 else "dim"
    t1.add_row("No. of Compartment (< 33%)", f"[{cmp_style}]{s['comp']}[/]", f"{s['comp']/tot*100:.2f} %")
    console.print(t1, "\n")

    # score range distribution table
    t2 = Table(title="SCORE RANGE DISTRIBUTION BREAKDOWN", box=box.ROUNDED)
    t2.add_column("Score Range", style="bold white", min_width=25)
    t2.add_column("No. of Students", justify="right", style="bold green", width=18)
    t2.add_column("Percentage", justify="right", style="bold cyan", width=16)

    for item in s["ranges"]:
        t2.add_row(item["range"], str(item["cnt"]), f"{item['pct']:.2f} %")
    t2.add_section()
    t2.add_row("TOTAL APPEARED", str(tot), "100.00 %", style="bold bright_white")

    console.print(t2)
    wait()


def showsubstats():
    # 4. subject average table matching image 1
    console.print(Rule("[bold cyan][Subjects] Subject Average & Centum Table[/bold cyan]", style="bright_cyan"))
    cls_f, sec_f = getscope()

    with console.status("[cyan]Loading subject statistics...[/cyan]"):
        rows = database.getsubstats(cls=cls_f, sec=sec_f)

    if not rows:
        console.print("[yellow]No subject records found.[/yellow]")
        wait()
        return

    tbl = Table(title="SUBJECT AVERAGE & CENTUM REPORT", box=box.ROUNDED, expand=True)
    tbl.add_column("Subject", style="bold white", ratio=3)
    tbl.add_column("Students", justify="right", style="cyan", width=10)
    tbl.add_column("Average", justify="right", style="bold bright_yellow", width=11)
    tbl.add_column("Highest", justify="right", style="bold green", width=9)
    tbl.add_column("Toppers", justify="right", style="white", width=9)
    tbl.add_column("Centum", justify="right", style="bold bright_white", width=10)
    tbl.add_column("Lowest", justify="right", style="dim", width=8)

    tot_c = 0
    tot_s = 0
    for r in rows:
        c_val = r["cent_cnt"]
        tot_c += c_val
        tot_s += r["stu_cnt"]
        c_str = f"[bold green]{c_val}[/]" if c_val > 0 else "[dim]-[/dim]"
        tbl.add_row(r["subject"], str(r["stu_cnt"]), f"{r['avg']:.2f}", f"{r['high']:.0f}", str(r["high_cnt"]), c_str, f"{r['low']:.0f}")

    tbl.add_section()
    tbl.add_row("TOTAL", str(tot_s), "-", "-", "-", f"[bold green]{tot_c} Centums[/]", "-", style="bold white")

    console.print("\n", tbl)
    wait()


def showsubtoppers():
    # 5. subject toppers list matching image 2
    console.print(Rule("[bold gold1][Roster] Subject Toppers List[/bold gold1]", style="gold1"))
    cls_f, sec_f = getscope()

    subs = database.getsubjects()
    sel_sub = None
    if subs:
        console.print("\n[bold cyan]Filter by Subject:[/bold cyan]")
        console.print("  [bold yellow]0.[/bold yellow] All Subjects")
        for i, sn in enumerate(subs, start=1):
            console.print(f"  [bold yellow]{i}.[/bold yellow] {sn}")
        sch = Prompt.ask("Choose option", choices=[str(x) for x in range(len(subs) + 1)], default="0")
        if sch != "0":
            sel_sub = subs[int(sch) - 1]

    with console.status("[cyan]Loading subject toppers...[/cyan]"):
        grps = database.getsubtoppers(cls=cls_f, sec=sec_f, sub=sel_sub)

    if not grps:
        console.print("[yellow]No toppers found.[/yellow]")
        wait()
        return

    console.print("\n[bold bright_white]SUBJECT TOPPERS LISTING[/bold bright_white]\n")

    for g in grps:
        sn = g["subject"].upper()
        hi = g["high"]
        st_list = g["students"]
        n_st = len(st_list)
        suffix = "student" if n_st == 1 else "students"

        # title like: ENGLISH (100 marks - 1 student)
        hi_clr = "bright_green" if hi >= 100 else "bright_yellow"
        title = f"[bold white]{sn}[/bold white] [dim]([/dim][bold {hi_clr}]{hi:.0f} marks[/] - [bold white]{n_st} {suffix}[/bold white][dim])[/dim]"

        gt = Table.grid(padding=(0, 2))
        gt.add_column(style="bold cyan", width=12)
        gt.add_column(style="bold white", min_width=25)
        gt.add_column(style="dim", justify="right")

        for idx, st in enumerate(st_list, start=1):
            gt.add_row(f"#{idx}  {st['roll_no']}", st["name"], f"Class {st['class_name']} ({st['section']})")

        pnl = Panel(gt, title=title, title_align="left", box=box.ROUNDED, border_style="gold1" if hi >= 100 else "cyan")
        console.print(pnl)

    wait()


def showmeritlist():
    # 6. full ranked merit list
    console.print(Rule("[bold blue][Merit] Full Ranked Merit List[/bold blue]", style="blue"))
    cls_f, sec_f = getscope()

    with console.status("[cyan]Loading merit rankings...[/cyan]"):
        rows = database.getmeritlist(cls=cls_f, sec=sec_f)

    if not rows:
        console.print("[yellow]No students found.[/yellow]")
        wait()
        return

    tbl = Table(title=f"MERIT LIST ({len(rows)} Students)", box=box.ROUNDED)
    tbl.add_column("RANK", justify="center", style="bold yellow")
    tbl.add_column("ROLL NO", justify="center", style="cyan")
    tbl.add_column("NAME", style="bold white", min_width=22)
    tbl.add_column("CLASS-SEC", justify="center", style="dim")
    tbl.add_column("TOTAL", justify="right", style="bold green")
    tbl.add_column("%", justify="right", style="bold bright_yellow")
    tbl.add_column("STATUS", justify="center")

    for r in rows:
        st = r["status"]
        st_clr = "bold green" if st == "Distinction" else ("green" if st == "1st Class" else ("yellow" if st == "2nd Class" else ("bold red" if st == "Compartment" else "cyan")))
        tbl.add_row(str(r["rank"]), r["roll_no"], r["name"], f"{r['class_name']}-{r['section']}", f"{r['tot_got']:.0f}/{r['tot_max']:.0f}", f"{r['pct']:.2f}", f"[{st_clr}]{st}[/]")

    console.print("\n", tbl)
    wait()


def showfilters():
    # 7. filter menu (centum, distinction, 1st class, compartment, subject cut-off, range)
    console.print(Rule("[bold bright_magenta][Filters] Advanced Student Filters[/bold bright_magenta]", style="bright_magenta"))
    console.print("  [bold yellow]1.[/bold yellow] [Centum Club] - Students who scored 100 in any subject")
    console.print("  [bold yellow]2.[/bold yellow] [Distinction] - Overall Percentage >= 75%")
    console.print("  [bold yellow]3.[/bold yellow] [First Class] - Overall Percentage >= 60%")
    console.print("  [bold yellow]4.[/bold yellow] [Compartment] - Failed in any subject (< 33%)")
    console.print("  [bold yellow]5.[/bold yellow] [Subject Roster] - Filter by subject and minimum mark")
    console.print("  [bold yellow]6.[/bold yellow] [Custom Range] - Specify Min % and Max %")
    console.print("  [bold yellow]0.[/bold yellow] Back to Menu\n")

    fch = Prompt.ask("Choose filter", choices=["0", "1", "2", "3", "4", "5", "6"], default="1")
    if fch == "0":
        return

    cls_f, sec_f = getscope()

    if fch == "1":
        with console.status("[cyan]Loading centum scorers...[/cyan]"):
            rows = database.getcentums(cls=cls_f, sec=sec_f)
        if not rows:
            console.print("[yellow]No 100/100 centum marks found.[/yellow]")
        else:
            tbl = Table(title=f"PERFECT CENTUM SCORERS (100 MARKS) - {len(rows)} Records", box=box.ROUNDED)
            tbl.add_column("SUBJECT", style="bold green", min_width=20)
            tbl.add_column("ROLL NO", style="cyan", justify="center")
            tbl.add_column("NAME", style="bold white", min_width=22)
            tbl.add_column("CLASS-SEC", style="dim", justify="center")
            tbl.add_column("MARKS", style="bold bright_green", justify="right")
            for r in rows:
                tbl.add_row(r["subject_name"], r["roll_no"], r["name"], f"{r['class_name']}-{r['section']}", f"{r['marks_obtained']:.0f}/100")
            console.print("\n", tbl)

    elif fch in ("2", "3", "4"):
        cmap = {"2": "distinction", "3": "1st", "4": "compartment"}
        cat = cmap[fch]
        with console.status(f"[cyan]Filtering {cat}...[/cyan]"):
            rows = database.getbycategory(cat, cls=cls_f, sec=sec_f)
        if not rows:
            console.print(f"[yellow]No students found for category '{cat}'.[/yellow]")
        else:
            tbl = Table(title=f"FILTERED: {cat.upper()} ({len(rows)} Students)", box=box.ROUNDED)
            tbl.add_column("RANK", justify="center", style="bold yellow")
            tbl.add_column("ROLL NO", style="cyan", justify="center")
            tbl.add_column("NAME", style="bold white", min_width=24)
            tbl.add_column("TOTAL", justify="right", style="green")
            tbl.add_column("PERCENTAGE", justify="right", style="bold bright_yellow")
            tbl.add_column("STATUS", justify="center", style="bold")
            for r in rows:
                tbl.add_row(str(r["rank"]), r["roll_no"], r["name"], f"{r['tot_got']:.0f}/{r['tot_max']:.0f}", f"{r['pct']:.2f}%", r["status"])
            console.print("\n", tbl)

    elif fch == "5":
        subs = database.getsubjects()
        if not subs:
            console.print("[yellow]No subjects in database.[/yellow]")
            wait()
            return
        console.print("\n[bold cyan]Select Subject:[/bold cyan]")
        for i, sn in enumerate(subs, start=1):
            console.print(f"  [bold yellow]{i}.[/bold yellow] {sn}")
        si = IntPrompt.ask("Choose subject", default=1)
        sub_n = subs[si - 1] if 1 <= si <= len(subs) else subs[0]
        min_m = Prompt.ask(f"Minimum marks for {sub_n} [press Enter for all]", default="")
        min_v = float(min_m) if min_m.strip() else 0.0

        with console.status("[cyan]Loading subject students...[/cyan]"):
            rows = database.getsubroster(sub_n, cls=cls_f, sec=sec_f, minm=min_v)
        if not rows:
            console.print(f"[yellow]No students found for {sub_n}.[/yellow]")
        else:
            tbl = Table(title=f"SUBJECT: {sub_n.upper()} ({len(rows)} Students)", box=box.ROUNDED)
            tbl.add_column("RANK", justify="center", style="bold yellow")
            tbl.add_column("ROLL NO", style="cyan", justify="center")
            tbl.add_column("NAME", style="bold white", min_width=24)
            tbl.add_column("MARKS", justify="right", style="bold green")
            tbl.add_column("PERCENTAGE", justify="right", style="cyan")
            for r in rows:
                tbl.add_row(str(r["rk"]), r["roll_no"], r["name"], f"{r['marks_obtained']:.0f}/{r['max_marks']:.0f}", f"{r['pct']:.2f}%")
            console.print("\n", tbl)

    elif fch == "6":
        p1 = float(Prompt.ask("Minimum Percentage (e.g. 80.0)", default="80.0"))
        p2 = float(Prompt.ask("Maximum Percentage (e.g. 100.0)", default="100.0"))
        with console.status("[cyan]Filtering percentage range...[/cyan]"):
            rows = database.getbyrange(p1, p2, cls=cls_f, sec=sec_f)
        if not rows:
            console.print(f"[yellow]No students between {p1}% and {p2}%.[/yellow]")
        else:
            tbl = Table(title=f"PERCENTAGE RANGE [{p1}% - {p2}%] ({len(rows)} Students)", box=box.ROUNDED)
            tbl.add_column("RANK", justify="center", style="bold yellow")
            tbl.add_column("ROLL NO", style="cyan", justify="center")
            tbl.add_column("NAME", style="bold white", min_width=24)
            tbl.add_column("TOTAL", justify="right", style="green")
            tbl.add_column("PERCENTAGE", justify="right", style="bold bright_yellow")
            tbl.add_column("STATUS", justify="center", style="bold")
            for r in rows:
                tbl.add_row(str(r["rank"]), r["roll_no"], r["name"], f"{r['tot_got']:.0f}/{r['tot_max']:.0f}", f"{r['pct']:.2f}%", r["status"])
            console.print("\n", tbl)

    wait()


def showreportcard():
    # 8. student individual report card
    console.print(Rule("[bold cyan][Report] Individual Student Report Card[/bold cyan]", style="bright_cyan"))
    q = Prompt.ask("Enter Roll No or Student Name").strip()
    if not q:
        return

    with console.status("[cyan]Finding student...[/cyan]"):
        rows = database.getreportcard(q)

    if not rows:
        console.print(f"[bold red][X] Student '{q}' not found.[/bold red]")
        wait()
        return

    st = rows[0]
    tot_g = 0.0
    tot_m = 0.0

    tbl = Table(box=box.ROUNDED)
    tbl.add_column("Subject", style="bold white", min_width=22)
    tbl.add_column("Marks", justify="right", style="bold green", width=12)
    tbl.add_column("Max", justify="right", style="cyan", width=10)
    tbl.add_column("%", justify="right", style="bold yellow", width=10)
    tbl.add_column("Grade", justify="center", style="bold", width=10)

    for r in rows:
        if not r.get("subject_name"):
            continue
        g = float(r["marks_obtained"] or 0)
        x = float(r["max_marks"] or 100)
        tot_g += g
        tot_m += x
        p = round(g / x * 100, 2) if x > 0 else 0.0
        grd = "[green]A1[/]" if p >= 90 else ("[green]A2[/]" if p >= 80 else ("[cyan]B1[/]" if p >= 70 else ("[cyan]B2[/]" if p >= 60 else ("[yellow]C[/]" if p >= 50 else ("[yellow]D[/]" if p >= 33 else "[bold red]E (Fail)[/]")))))
        tbl.add_row(r["subject_name"], f"{g:.0f}", f"{x:.0f}", f"{p:.2f}%", grd)

    tot_p = round(tot_g / tot_m * 100, 2) if tot_m > 0 else 0.0
    status = "[bold green]PASS (DISTINCTION)[/]" if tot_p >= 75 else ("[bold green]PASS (1st CLASS)[/]" if tot_p >= 60 else ("[bold yellow]PASS (2nd CLASS)[/]" if tot_p >= 50 else ("[bold red]COMPARTMENT[/]" if tot_p < 33 else "[cyan]PASS[/]")))

    tbl.add_section()
    tbl.add_row("GRAND TOTAL", f"[bold green]{tot_g:.0f}[/]", f"[bold cyan]{tot_m:.0f}[/]", f"[bold bright_yellow]{tot_p:.2f}%[/]", status)

    hdr = f"[bold white]{st['name'].upper()}[/bold white]\nRoll No: [bold cyan]{st['roll_no']}[/bold cyan]   |   Class: [bold]{st['class_name']}[/bold]   |   Section: [bold]{st['section']}[/bold]"
    console.print(Panel(hdr, box=box.ROUNDED, border_style="cyan"))
    console.print(tbl)
    wait()


def comparetwo():
    # 9. compare two students
    console.print(Rule("[bold magenta][Compare] Side-by-Side Comparison[/bold magenta]", style="magenta"))
    r1 = Prompt.ask("Enter Roll No for Student 1").strip()
    r2 = Prompt.ask("Enter Roll No for Student 2").strip()

    with console.status("[cyan]Comparing...[/cyan]"):
        cmp_res = database.comparestuds(r1, r2)

    if not cmp_res:
        console.print("[bold red][X] Could not compare. Check roll numbers.[/bold red]")
        wait()
        return

    s1 = cmp_res["s1"]
    s2 = cmp_res["s2"]

    pnl = Panel(
        f"[bold cyan]{s1['name']}[/bold cyan] ({s1['roll_no']}) vs [bold magenta]{s2['name']}[/bold magenta] ({s2['roll_no']})\n"
        f"Leader: [bold green]{cmp_res['leader']}[/bold green] (Difference: [bold yellow]{cmp_res['diff_pct']} %[/bold yellow])",
        title="HEAD TO HEAD",
        box=box.ROUNDED,
    )
    console.print(pnl)

    tbl = Table(box=box.ROUNDED)
    tbl.add_column("Subject", style="bold white", min_width=22)
    tbl.add_column(f"{s1['name']} ({s1['roll_no']})", justify="right", style="cyan", width=22)
    tbl.add_column(f"{s2['name']} ({s2['roll_no']})", justify="right", style="magenta", width=22)
    tbl.add_column("Diff", justify="right", style="yellow", width=12)
    tbl.add_column("Leader", justify="center", style="bold green", width=18)

    for itm in cmp_res["subs"]:
        d_str = f"+{itm['diff']:.0f}" if itm["diff"] > 0 else f"{itm['diff']:.0f}"
        v1_str = f"{itm['v1']:.0f}" if itm["v1"] is not None else "-"
        v2_str = f"{itm['v2']:.0f}" if itm["v2"] is not None else "-"
        tbl.add_row(itm["sub"], v1_str, v2_str, d_str, itm["leader"])

    tbl.add_section()
    tbl.add_row(
        "TOTAL",
        f"{s1['tot']:.0f} ({s1['pct']:.2f}%)",
        f"{s2['tot']:.0f} ({s2['pct']:.2f}%)",
        f"{cmp_res['diff_pct']:.2f}%",
        f"[bold bright_green]{cmp_res['leader']}[/]",
        style="bold white",
    )

    console.print("\n", tbl)
    wait()


def dbtools():
    # 10. database count and reset
    console.print(Rule("[bold yellow][Database] Database Status & Reset[/bold yellow]", style="yellow"))
    studs = database.getstuds()
    subs = database.getsubjects()
    classes = database.getclasses()

    tbl = Table(title="DATABASE STATUS", box=box.ROUNDED)
    tbl.add_column("Entity", style="bold white")
    tbl.add_column("Count", justify="right", style="bold green")
    tbl.add_row("Enrolled Students", str(len(studs)))
    tbl.add_row("Subjects", str(len(subs)))
    tbl.add_row("Classes", ", ".join(classes) if classes else "None")
    console.print(tbl, "\n")

    console.print("  [bold yellow]1.[/bold yellow] Reset / Wipe Database (Clear all data)")
    console.print("  [bold yellow]0.[/bold yellow] Back to Menu\n")

    ch = Prompt.ask("Choose option", choices=["0", "1"], default="0")
    if ch == "1":
        if Confirm.ask("[bold red][!] Wipe all tables for fresh import?[/bold red]", default=False):
            database.resetdb()
            console.print("[bold green][OK] Database cleared.[/bold green]")
        else:
            console.print("[yellow]Cancelled.[/yellow]")
    wait()


# ========== MAIN LOOP ==========

def main():
    database.initdb()

    menu_items = [
        ("1", "[Ingest] Input Text File (.txt)", "Parse text file and save into MySQL DB"),
        ("2", "[Toppers] School / Class Toppers", "Place I, II, III... Mark & % [Image 1]"),
        ("3", "[Summary] Overall Average & Ranges", "Average %, Distinction, Range bins [Image 1]"),
        ("4", "[Subjects] Subject Average & Stats", "Avg, Highest, Count, Centums [Image 1]"),
        ("5", "[Roster] Subject Toppers List", "Highest score per subject & student names [Image 2]"),
        ("6", "[Merit] Full Ranked Merit List", "Complete rank roster with total and %"),
        ("7", "[Filter] Advanced Student Filters", "Filter by Centum, Distinction, Subject, Range"),
        ("8", "[Report] Individual Report Card", "Lookup student marks by Roll No or Name"),
        ("9", "[Compare] Side-by-Side Comparison", "Compare two students head to head"),
        ("10", "[Database] Status & Reset", "View table counts or wipe database"),
        ("0", "[Exit] Quit", "Close program"),
    ]

    while True:
        cls()
        banner()

        tbl = Table.grid(padding=(0, 2))
        tbl.add_column(style="bold yellow", justify="right", width=4)
        tbl.add_column(style="bold white", min_width=32)
        tbl.add_column(style="dim", min_width=45)

        for num, title, desc in menu_items:
            tbl.add_row(f"{num}.", title, f"- {desc}")

        pnl = Panel(tbl, title="[bold white]MAIN MENU[/bold white]", border_style="bright_blue", box=box.ROUNDED, padding=(1, 2))
        console.print(pnl)

        ch = Prompt.ask("\n[bold cyan]Choose option[/bold cyan]", choices=[str(i) for i in range(11)], default="1")

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
                comparetwo()
            elif ch == "10":
                dbtools()
            elif ch == "0":
                console.print("\n[bold green]Goodbye! Study well![/bold green]\n")
                break
        except Exception as e:
            console.print(f"\n[bold red]Error: {e}[/bold red]")
            wait()


if __name__ == "__main__":
    main()
