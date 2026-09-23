# gui.py - the tkinter GUI window
# this creates a nice desktop app with tabs
# dont close the window while data is saving

from __future__ import annotations

import os
import sys
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk
from tkinter.scrolledtext import ScrolledText

import pandas as pd

import database
import file_handler


BASEDIR = Path(__file__).resolve().parent
REPDIR = BASEDIR / "reports"


class App(tk.Tk):
    # main GUI window class

    def __init__(self):
        super().__init__()

        self.title("Student Result & Academic Records System")
        self.geometry("1100x740")
        self.minsize(900, 620)

        REPDIR.mkdir(parents=True, exist_ok=True)

        # text variables that show up on screen
        self.stmsg = tk.StringVar(value="Ready. Input text file or browse database.")
        self.dbst = tk.StringVar(value="Connecting...")
        self.selfv = tk.StringVar(value="No file selected (you can also paste raw text below)")
        self.parsemsg = tk.StringVar(value="")
        self.vmode = tk.StringVar(value="Students")
        self.srch = tk.StringVar(value="")
        self.clssel = tk.StringVar(value="10")
        self.stcnt = tk.StringVar(value="0")
        self.sttop = tk.StringVar(value="N/A")
        self.stavg = tk.StringVar(value="0.0%")
        self.rroll = tk.StringVar(value="")

        # analytics variables
        self.acls = tk.StringVar(value="All")
        self.cs1 = tk.StringVar(value="")
        self.cs2 = tk.StringVar(value="")
        self.topsum = tk.StringVar(value="Compute toppers to see who scored the most marks.")
        self.cmpwin = tk.StringVar(value="Select two students and click Compare.")

        # data holders
        self.lastparsed = None
        self.dbrows = []
        self.rankrows = []
        self.reprows = []
        self.subtoprows = []
        self.cmpdata = None
        self.substats = []

        self.setupstyle()
        self.buildui()
        self.checkdb()

    def setupstyle(self):
        # colors and fonts setup
        self.sty = ttk.Style(self)
        if "clam" in self.sty.theme_names():
            self.sty.theme_use("clam")

        # color palette
        self.bg = "#f1f5f9"
        self.cbg = "#ffffff"
        self.pclr = "#2563eb"
        self.phov = "#1d4ed8"
        self.sclr = "#059669"
        self.hbg = "#1e293b"
        self.txm = "#0f172a"
        self.txl = "#64748b"

        self.configure(bg=self.bg)

        self.sty.configure("TFrame", background=self.bg)
        self.sty.configure("Card.TFrame", background=self.cbg, relief="flat")
        self.sty.configure("TLabel", background=self.bg, foreground=self.txm, font=("Segoe UI", 10))
        self.sty.configure("Card.TLabel", background=self.cbg, foreground=self.txm, font=("Segoe UI", 10))
        self.sty.configure("Header.TLabel", background=self.hbg, foreground="#ffffff", font=("Segoe UI", 15, "bold"))
        self.sty.configure("StatValue.TLabel", background=self.cbg, foreground=self.pclr, font=("Segoe UI", 17, "bold"))

        self.sty.configure("Primary.TButton", font=("Segoe UI", 10, "bold"), background=self.pclr, foreground="#ffffff", borderwidth=0, padding=(14, 7))
        self.sty.map("Primary.TButton", background=[("active", self.phov), ("pressed", "#1e40af")], foreground=[("active", "#ffffff")])

        self.sty.configure("Success.TButton", font=("Segoe UI", 10, "bold"), background=self.sclr, foreground="#ffffff", borderwidth=0, padding=(14, 7))
        self.sty.map("Success.TButton", background=[("active", "#047857"), ("pressed", "#065f46")], foreground=[("active", "#ffffff")])

        self.sty.configure("Secondary.TButton", font=("Segoe UI", 10), padding=(12, 6))

        self.sty.configure("TNotebook", background=self.bg, borderwidth=0)
        self.sty.configure("TNotebook.Tab", font=("Segoe UI", 10, "bold"), padding=(16, 9), background="#e2e8f0", foreground=self.txl)
        self.sty.map("TNotebook.Tab", background=[("selected", self.cbg)], foreground=[("selected", self.pclr)])

        # table styles
        self.sty.configure("Treeview", background="#ffffff", foreground=self.txm, rowheight=26, font=("Segoe UI", 9), fieldbackground="#ffffff", borderwidth=1)
        self.sty.configure("Treeview.Heading", font=("Segoe UI", 9, "bold"), background="#e2e8f0", foreground=self.txm, relief="flat", padding=(6, 5))
        self.sty.map("Treeview.Heading", background=[("active", "#cbd5e1")])

    def buildui(self):
        # build the whole interface
        # 1. top header
        hf = tk.Frame(self, bg=self.hbg, height=65)
        hf.pack(side=tk.TOP, fill=tk.X)
        hf.pack_propagate(False)

        ttk.Label(hf, text="🎓 Student Result & Academic Records System", style="Header.TLabel").pack(side=tk.LEFT, padx=20, pady=(10, 2))

        self.dblbl = tk.Label(hf, textvariable=self.dbst, bg="#334155", fg="#38bdf8", font=("Segoe UI", 9, "bold"), padx=12, pady=4)
        self.dblbl.pack(side=tk.RIGHT, padx=20, pady=15)

        # 2. tabs
        self.nb = ttk.Notebook(self)
        self.nb.pack(fill=tk.BOTH, expand=True, padx=15, pady=10)

        self.tab1 = ttk.Frame(self.nb, style="TFrame")
        self.tab2 = ttk.Frame(self.nb, style="TFrame")
        self.tab3 = ttk.Frame(self.nb, style="TFrame")
        self.tab4 = ttk.Frame(self.nb, style="TFrame")
        self.tab5 = ttk.Frame(self.nb, style="TFrame")

        self.nb.add(self.tab1, text="  📥 Input Text File (.txt)  ")
        self.nb.add(self.tab2, text="  📊 Database Records  ")
        self.nb.add(self.tab3, text="  🏆 Results & Rankings  ")
        self.nb.add(self.tab4, text="  📈 Analytics & Comparison  ")
        self.nb.add(self.tab5, text="  📜 Report Cards  ")

        self.mktab1()
        self.mktab2()
        self.mktab3()
        self.mktab4()
        self.mktab5()

        # 3. status bar
        sb = tk.Frame(self, bg="#cbd5e1", height=28)
        sb.pack(side=tk.BOTTOM, fill=tk.X)
        sb.pack_propagate(False)

        tk.Label(sb, textvariable=self.stmsg, bg="#cbd5e1", fg=self.txm, font=("Segoe UI", 9), anchor="w").pack(side=tk.LEFT, fill=tk.X, padx=15)

    def checkdb(self):
        # check mysql connection
        ok, msg = database.checkcon()
        if ok:
            self.dbst.set("● MySQL Connected")
            self.dblbl.configure(bg="#064e3b", fg="#34d399")
            self.setst("Connected to MySQL database 'student_result_system'.")
        else:
            self.dbst.set("● DB Error")
            self.dblbl.configure(bg="#7f1d1d", fg="#f87171")
            self.setst(f"Database error: {msg}")

    def setst(self, txt):
        self.stmsg.set(txt)

    def askname(self, defname):
        # ask for csv file name
        nm = simpledialog.askstring("CSV Name", "Enter name for the CSV file / report:", initialvalue=defname, parent=self)
        if not nm or not nm.strip():
            return None, None

        cn = nm.strip().replace(" ", "_")
        if cn.lower().endswith(".csv"):
            cn = cn[:-4]

        out = REPDIR / f"{cn}.csv"
        return nm.strip(), out

    # =============================================
    # TAB 1: INPUT TEXT FILE
    # =============================================
    def mktab1(self):
        top = ttk.Frame(self.tab1, style="TFrame")
        top.pack(fill=tk.X, pady=(5, 10))

        ttk.Label(top, text="Input Text File (.txt) ➔ Put in Database ➔ Reveal in CSV", font=("Segoe UI", 12, "bold")).pack(side=tk.LEFT)
        ttk.Button(top, text="📂 Browse .txt File...", style="Primary.TButton", command=self.browse).pack(side=tk.RIGHT, padx=5)

        ttk.Label(self.tab1, textvariable=self.selfv, font=("Segoe UI", 9, "italic"), foreground=self.txl).pack(fill=tk.X, pady=(0, 8))

        ec = ttk.Frame(self.tab1, style="Card.TFrame", padding=10)
        ec.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        ttk.Label(ec, text="Text File Content (browse or paste text directly):", style="Card.TLabel", font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(0, 5))

        self.editor = ScrolledText(ec, wrap=tk.WORD, font=("Consolas", 10), relief="solid", bd=1, bg="#f8fafc", fg="#0f172a")
        self.editor.pack(fill=tk.BOTH, expand=True)

        af = ttk.Frame(self.tab1, style="TFrame")
        af.pack(fill=tk.X, pady=5)

        ttk.Button(af, text="🔍 1. Parse & Check", style="Secondary.TButton", command=self.doparse).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(af, text="💾 2. Put Data into Database", style="Primary.TButton", command=self.dosavedb).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(af, text="📊 3. Reveal in CSV", style="Success.TButton", command=self.doreveal).pack(side=tk.LEFT, padx=(0, 10))

        ttk.Label(af, textvariable=self.parsemsg, font=("Segoe UI", 9, "bold"), foreground=self.pclr).pack(side=tk.LEFT, padx=15)

    def browse(self):
        fp = filedialog.askopenfilename(
            title="Select Text File",
            filetypes=[("Text Files (*.txt)", "*.txt"), ("CSV Files (*.csv)", "*.csv"), ("All Files", "*.*")],
        )
        if fp:
            self.loadfile(fp)

    def loadfile(self, path):
        p = Path(path)
        try:
            txt = p.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            txt = p.read_text(encoding="latin-1")
        self.editor.delete("1.0", tk.END)
        self.editor.insert(tk.END, txt)
        self.selfv.set(f"Selected: {p.resolve()}")
        self.setst(f"Loaded {p.name} into editor.")
        self.doparse()

    def doparse(self):
        # parse text content
        txt = self.editor.get("1.0", tk.END).strip()
        if not txt:
            messagebox.showwarning("Empty Text", "Please enter or browse a text file to parse.")
            return None

        parsed = file_handler.parsetxt(txt)
        sc = len(parsed.get("students", []))
        mc = len(parsed.get("marks", []))
        ec = len(parsed.get("errors", []))

        msg = f"Detected: {sc} student(s), {mc} subject mark(s)."
        if ec > 0:
            msg += f" ({ec} warning)"
        self.parsemsg.set(msg)
        self.setst(msg)
        self.lastparsed = parsed
        return parsed

    def dosavedb(self):
        # save to database
        parsed = self.doparse()
        if not parsed:
            return

        if not parsed.get("students") and not parsed.get("marks"):
            messagebox.showerror("No Data", "No valid student or mark records were found in the text file.")
            return

        try:
            res = file_handler.savetodb(parsed)
            ss = res["students_saved"]
            ms = res["marks_saved"]
            errs = res.get("errors", [])

            msg = f"Successfully put data into Database!\n• {ss} student records saved/updated.\n• {ms} marks saved/updated."
            if errs:
                msg += "\n\nWarnings:\n" + "\n".join(errs[:5])

            messagebox.showinfo("Database Ingestion Complete", msg)
            self.setst(f"Saved {ss} students & {ms} marks to MySQL.")
            self.reftab2()
            self.refclasses()
            self.refrolls()
            self.refanadrops()
        except Exception as e:
            messagebox.showerror("Database Error", f"Failed to save data into MySQL: {e}")

    def doreveal(self):
        # export to csv and open in explorer
        parsed = self.doparse()
        if not parsed:
            return

        studs = parsed.get("students", [])
        marks = parsed.get("marks", [])

        if not studs and not marks:
            messagebox.showwarning("No Data", "No student or mark records available to export.")
            return

        rname, out = self.askname("Imported_Student_Data")
        if not rname or not out:
            return

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
        file_handler.savecsv(df, out, rname=rname)

        ok, msg = file_handler.showfile(out)
        messagebox.showinfo("Revealed in CSV", f"Created CSV with name '{rname}':\n{out.resolve()}\n\n{msg}")
        self.setst(f"Exported and revealed CSV: {out.name}")

    # =============================================
    # TAB 2: DATABASE RECORDS
    # =============================================
    def mktab2(self):
        ctrl = ttk.Frame(self.tab2, style="TFrame")
        ctrl.pack(fill=tk.X, pady=(5, 10))

        ttk.Label(ctrl, text="View:", font=("Segoe UI", 10, "bold")).pack(side=tk.LEFT, padx=(0, 5))

        mc = ttk.Combobox(ctrl, textvariable=self.vmode, values=["Students", "Marks", "Subjects"], state="readonly", width=14)
        mc.pack(side=tk.LEFT, padx=(0, 15))
        mc.bind("<<ComboboxSelected>>", lambda e: self.reftab2())

        ttk.Label(ctrl, text="Search:").pack(side=tk.LEFT, padx=(0, 5))
        se = ttk.Entry(ctrl, textvariable=self.srch, width=20)
        se.pack(side=tk.LEFT, padx=(0, 5))
        se.bind("<KeyRelease>", lambda e: self.filtertab2())

        ttk.Button(ctrl, text="🔄 Refresh", style="Secondary.TButton", command=self.reftab2).pack(side=tk.LEFT, padx=5)
        ttk.Button(ctrl, text="📊 Reveal Table in CSV", style="Success.TButton", command=self.exptab2).pack(side=tk.RIGHT, padx=5)

        tc = ttk.Frame(self.tab2, style="Card.TFrame", padding=1)
        tc.pack(fill=tk.BOTH, expand=True)

        self.dbtree = ttk.Treeview(tc, show="headings")
        ys = ttk.Scrollbar(tc, orient=tk.VERTICAL, command=self.dbtree.yview)
        xs = ttk.Scrollbar(tc, orient=tk.HORIZONTAL, command=self.dbtree.xview)
        self.dbtree.configure(yscrollcommand=ys.set, xscrollcommand=xs.set)

        self.dbtree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        ys.pack(side=tk.RIGHT, fill=tk.Y)
        xs.pack(side=tk.BOTTOM, fill=tk.X)

        self.reftab2()

    def reftab2(self):
        mode = self.vmode.get()
        self.dbtree.delete(*self.dbtree.get_children())

        try:
            if mode == "Students":
                cols = ["roll_no", "name", "class_name", "section", "phone", "email"]
                hdrs = ["Roll No", "Student Name", "Class", "Section", "Phone", "Email"]
                rows = database.fetchstuds()
            elif mode == "Marks":
                cols = ["roll_no", "name", "class_name", "subject_name", "marks_obtained", "max_marks"]
                hdrs = ["Roll No", "Student Name", "Class", "Subject", "Marks Obtained", "Max Marks"]
                rows = database.fetchallmarks()
            else:
                cols = ["subject_id", "subject_name"]
                hdrs = ["Subject ID", "Subject Name"]
                rows = database.fetchsubs()

            self.dbrows = rows
            self.dbtree["columns"] = cols
            for c, h in zip(cols, hdrs):
                self.dbtree.heading(c, text=h)
                self.dbtree.column(c, width=130, anchor="center" if "id" in c or "no" in c or "section" in c else "w")

            for r in rows:
                vals = [r.get(c, "") for c in cols]
                self.dbtree.insert("", tk.END, values=vals)

            self.setst(f"Loaded {len(rows)} record(s) in {mode} view.")
        except Exception as e:
            self.setst(f"Error loading {mode}: {e}")

    def filtertab2(self):
        q = self.srch.get().strip().lower()
        self.dbtree.delete(*self.dbtree.get_children())
        cols = self.dbtree["columns"]

        for r in self.dbrows:
            vals = [str(r.get(c, "") or "") for c in cols]
            if not q or any(q in v.lower() for v in vals):
                self.dbtree.insert("", tk.END, values=vals)

    def exptab2(self):
        mode = self.vmode.get()
        if not self.dbrows:
            messagebox.showwarning("No Data", f"No records available in {mode} to export.")
            return

        rname, out = self.askname(f"Database_{mode}")
        if not rname or not out:
            return

        df = pd.DataFrame(self.dbrows)
        file_handler.savecsv(df, out, rname=rname)
        ok, msg = file_handler.showfile(out)
        messagebox.showinfo("Export & Reveal CSV", f"Created CSV with name '{rname}':\n{out.resolve()}\n\n{msg}")
        self.setst(f"Exported & revealed CSV: {out.name}")

    # =============================================
    # TAB 3: RESULTS & RANKINGS
    # =============================================
    def mktab3(self):
        top = ttk.Frame(self.tab3, style="TFrame")
        top.pack(fill=tk.X, pady=(5, 10))

        ttk.Label(top, text="Select Class:", font=("Segoe UI", 10, "bold")).pack(side=tk.LEFT, padx=(0, 6))

        self.clscmb = ttk.Combobox(top, textvariable=self.clssel, width=10)
        self.clscmb.pack(side=tk.LEFT, padx=(0, 10))

        ttk.Button(top, text="🎯 Compute Rankings", style="Primary.TButton", command=self.dorank).pack(side=tk.LEFT, padx=5)
        ttk.Button(top, text="📊 Reveal in CSV", style="Success.TButton", command=self.exprankcsv).pack(side=tk.RIGHT, padx=5)

        # stat cards
        sf = ttk.Frame(self.tab3, style="TFrame")
        sf.pack(fill=tk.X, pady=(0, 10))

        c1 = ttk.Frame(sf, style="Card.TFrame", padding=12)
        c1.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 8))
        ttk.Label(c1, text="Total Students", style="Card.TLabel", font=("Segoe UI", 9)).pack()
        ttk.Label(c1, textvariable=self.stcnt, style="StatValue.TLabel").pack()

        c2 = ttk.Frame(sf, style="Card.TFrame", padding=12)
        c2.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 8))
        ttk.Label(c2, text="Top Scorer", style="Card.TLabel", font=("Segoe UI", 9)).pack()
        ttk.Label(c2, textvariable=self.sttop, style="StatValue.TLabel", foreground=self.sclr).pack()

        c3 = ttk.Frame(sf, style="Card.TFrame", padding=12)
        c3.pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Label(c3, text="Class Average", style="Card.TLabel", font=("Segoe UI", 9)).pack()
        ttk.Label(c3, textvariable=self.stavg, style="StatValue.TLabel", foreground="#d97706").pack()

        tc = ttk.Frame(self.tab3, style="Card.TFrame", padding=1)
        tc.pack(fill=tk.BOTH, expand=True)

        self.ranktree = ttk.Treeview(tc, show="headings")
        ys = ttk.Scrollbar(tc, orient=tk.VERTICAL, command=self.ranktree.yview)
        self.ranktree.configure(yscrollcommand=ys.set)

        self.ranktree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        ys.pack(side=tk.RIGHT, fill=tk.Y)

        cols = ["rank_position", "roll_no", "name", "class_name", "total", "percentage"]
        hdrs = ["Rank", "Roll No", "Student Name", "Class", "Total Obtained", "Percentage (%)"]
        self.ranktree["columns"] = cols
        for c, h in zip(cols, hdrs):
            self.ranktree.heading(c, text=h)
            self.ranktree.column(c, width=120, anchor="center" if c in ["rank_position", "roll_no", "class_name"] else "w")

        self.refclasses()

    def refclasses(self):
        try:
            studs = database.fetchstuds()
            classes = sorted(list({s["class_name"] for s in studs if s.get("class_name")}))
            if classes:
                self.clscmb["values"] = classes
                if self.clssel.get() not in classes:
                    self.clssel.set(classes[0])
                self.aclscmb["values"] = ["All"] + classes
        except Exception:
            pass

    def dorank(self):
        cn = self.clssel.get().strip()
        if not cn:
            messagebox.showwarning("Class Missing", "Please select or type a class name.")
            return

        self.ranktree.delete(*self.ranktree.get_children())
        try:
            rows = database.getranked(cn)
            self.rankrows = rows

            if not rows:
                self.stcnt.set("0")
                self.sttop.set("N/A")
                self.stavg.set("0.0%")
                self.setst(f"No ranked results found for class '{cn}'.")
                return

            tp = 0.0
            for r in rows:
                pct = float(r.get("percentage") or 0)
                tp += pct
                self.ranktree.insert(
                    "", tk.END,
                    values=[
                        f"#{r.get('rank_position', '')}",
                        r.get("roll_no", ""),
                        r.get("name", ""),
                        r.get("class_name", ""),
                        f"{float(r.get('total') or 0):.2f}",
                        f"{pct:.2f}%",
                    ],
                )

            avg = tp / len(rows) if rows else 0.0
            self.stcnt.set(str(len(rows)))
            self.sttop.set(f"{rows[0]['name']} ({float(rows[0]['percentage']):.1f}%)")
            self.stavg.set(f"{avg:.1f}%")

            self.setst(f"Computed rankings for Class {cn}: {len(rows)} student(s).")
        except Exception as e:
            messagebox.showerror("Ranking Error", f"Failed to compute rankings: {e}")

    def exprankcsv(self):
        cn = self.clssel.get().strip()
        if not self.rankrows:
            self.dorank()

        if not self.rankrows:
            messagebox.showwarning("No Data", f"No ranking results found to export for Class {cn}.")
            return

        rname, out = self.askname(f"Class_{cn}_Rankings")
        if not rname or not out:
            return

        df = pd.DataFrame(self.rankrows)
        file_handler.savecsv(df, out, rname=rname)

        ok, msg = file_handler.showfile(out)
        messagebox.showinfo("Revealed in CSV", f"Class {cn} rankings created with name '{rname}':\n{out.resolve()}\n\n{msg}")
        self.setst(f"Exported & revealed rankings CSV: {out.name}")

    # =============================================
    # TAB 4: ANALYTICS & COMPARISON
    # =============================================
    def mktab4(self):
        anb = ttk.Notebook(self.tab4)
        anb.pack(fill=tk.BOTH, expand=True)

        self.st41 = ttk.Frame(anb, style="TFrame")
        self.st42 = ttk.Frame(anb, style="TFrame")
        self.st43 = ttk.Frame(anb, style="TFrame")

        anb.add(self.st41, text="  🥇 Who Scored the Most?  ")
        anb.add(self.st42, text="  ⚖️ Compare Two Students  ")
        anb.add(self.st43, text="  📊 Subject Statistics  ")

        self.mktoppers(self.st41)
        self.mkcompare(self.st42)
        self.mksubstats(self.st43)

    def mktoppers(self, par):
        ctrl = ttk.Frame(par, style="TFrame")
        ctrl.pack(fill=tk.X, pady=(5, 10))

        ttk.Label(ctrl, text="Filter Class:", font=("Segoe UI", 10, "bold")).pack(side=tk.LEFT, padx=(0, 6))

        self.aclscmb = ttk.Combobox(ctrl, textvariable=self.acls, values=["All"], width=10, state="readonly")
        self.aclscmb.pack(side=tk.LEFT, padx=(0, 10))
        self.aclscmb.bind("<<ComboboxSelected>>", lambda e: self.findtop())

        ttk.Button(ctrl, text="🔍 Find Top Scorers", style="Primary.TButton", command=self.findtop).pack(side=tk.LEFT, padx=5)
        ttk.Button(ctrl, text="📊 Reveal in CSV", style="Success.TButton", command=self.exptopcsv).pack(side=tk.RIGHT, padx=5)

        tc = ttk.Frame(par, style="Card.TFrame", padding=14)
        tc.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(tc, text="🏆 Overall Highest Scorer:", style="Card.TLabel", font=("Segoe UI", 11, "bold"), foreground=self.pclr).pack(anchor="w")
        ttk.Label(tc, textvariable=self.topsum, style="Card.TLabel", font=("Segoe UI", 12)).pack(anchor="w", pady=(3, 0))

        ttk.Label(par, text="Subject-Wise Highest Scorers (Who scored the most in each subject):", font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(5, 4))

        ttc = ttk.Frame(par, style="Card.TFrame", padding=1)
        ttc.pack(fill=tk.BOTH, expand=True)

        self.toptree = ttk.Treeview(ttc, show="headings")
        ys = ttk.Scrollbar(ttc, orient=tk.VERTICAL, command=self.toptree.yview)
        self.toptree.configure(yscrollcommand=ys.set)

        self.toptree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        ys.pack(side=tk.RIGHT, fill=tk.Y)

        cols = ["subject_name", "name", "roll_no", "class_name", "section", "marks_obtained", "max_marks", "percentage"]
        hdrs = ["Subject", "Top Scorer Name", "Roll No", "Class", "Sec", "Marks Scored", "Max Marks", "Percentage (%)"]
        self.toptree["columns"] = cols
        for c, h in zip(cols, hdrs):
            self.toptree.heading(c, text=h)
            self.toptree.column(c, width=120, anchor="center" if c in ["roll_no", "class_name", "section"] else "w")

    def findtop(self):
        cv = self.acls.get().strip()
        cf = None if cv == "All" or not cv else cv

        try:
            ov = database.gettopscorers(cls=cf, lim=1)
            if ov:
                t = ov[0]
                txt = (
                    f"🥇 {t['name']} (Roll No: {t['roll_no']}) scored the most marks!\n"
                    f"Total: {t['total_obtained']} / {t['total_max']}  •  Percentage: {t['percentage']}%  •  Class {t['class_name']}-{t['section']}"
                )
                self.topsum.set(txt)
            else:
                self.topsum.set("No student records or marks found to calculate toppers.")

            st = database.getsubtoppers(cls=cf)
            self.subtoprows = st
            self.toptree.delete(*self.toptree.get_children())

            for r in st:
                self.toptree.insert(
                    "", tk.END,
                    values=[
                        r.get("subject_name", ""),
                        r.get("name", ""),
                        r.get("roll_no", ""),
                        r.get("class_name", ""),
                        r.get("section", ""),
                        float(r.get("marks_obtained") or 0),
                        float(r.get("max_marks") or 100),
                        f"{float(r.get('percentage') or 0):.2f}%",
                    ],
                )

            self.setst(f"Calculated top scorers for {cv} classes: {len(st)} subjects evaluated.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to calculate top scorers: {e}")

    def exptopcsv(self):
        if not self.subtoprows:
            self.findtop()

        if not self.subtoprows:
            messagebox.showwarning("No Data", "No topper records available to export.")
            return

        rname, out = self.askname("Top_Scorers_Report")
        if not rname or not out:
            return

        df = pd.DataFrame(self.subtoprows)
        file_handler.savecsv(df, out, rname=rname)
        ok, msg = file_handler.showfile(out)
        messagebox.showinfo("Revealed in CSV", f"Top scorers created with name '{rname}':\n{out.resolve()}\n\n{msg}")
        self.setst(f"Exported & revealed toppers CSV: {out.name}")

    def mkcompare(self, par):
        ctrl = ttk.Frame(par, style="TFrame")
        ctrl.pack(fill=tk.X, pady=(5, 10))

        ttk.Label(ctrl, text="Student 1:", font=("Segoe UI", 10, "bold")).pack(side=tk.LEFT, padx=(0, 4))
        self.cc1 = ttk.Combobox(ctrl, textvariable=self.cs1, width=15)
        self.cc1.pack(side=tk.LEFT, padx=(0, 15))

        ttk.Label(ctrl, text="vs. Student 2:", font=("Segoe UI", 10, "bold")).pack(side=tk.LEFT, padx=(0, 4))
        self.cc2 = ttk.Combobox(ctrl, textvariable=self.cs2, width=15)
        self.cc2.pack(side=tk.LEFT, padx=(0, 15))

        ttk.Button(ctrl, text="⚖️ Compare Students", style="Primary.TButton", command=self.docmp).pack(side=tk.LEFT, padx=5)
        ttk.Button(ctrl, text="📊 Reveal in CSV", style="Success.TButton", command=self.expcmpcsv).pack(side=tk.RIGHT, padx=5)

        wc = ttk.Frame(par, style="Card.TFrame", padding=14)
        wc.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(wc, text="Comparison Summary:", style="Card.TLabel", font=("Segoe UI", 11, "bold"), foreground=self.pclr).pack(anchor="w")
        ttk.Label(wc, textvariable=self.cmpwin, style="Card.TLabel", font=("Segoe UI", 12)).pack(anchor="w", pady=(3, 0))

        ttc = ttk.Frame(par, style="Card.TFrame", padding=1)
        ttc.pack(fill=tk.BOTH, expand=True)

        self.cmptree = ttk.Treeview(ttc, show="headings")
        ys = ttk.Scrollbar(ttc, orient=tk.VERTICAL, command=self.cmptree.yview)
        self.cmptree.configure(yscrollcommand=ys.set)

        self.cmptree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        ys.pack(side=tk.RIGHT, fill=tk.Y)

        cols = ["subject", "st1_marks", "st2_marks", "diff", "leader"]
        hdrs = ["Subject", "Student 1 Marks", "Student 2 Marks", "Difference (+/-)", "Subject Leader"]
        self.cmptree["columns"] = cols
        for c, h in zip(cols, hdrs):
            self.cmptree.heading(c, text=h)
            self.cmptree.column(c, width=130, anchor="center" if c != "subject" else "w")

    def refanadrops(self):
        try:
            studs = database.fetchstuds()
            rolls = [s["roll_no"] for s in studs]
            self.cc1["values"] = rolls
            self.cc2["values"] = rolls
            if len(rolls) >= 2:
                if not self.cs1.get():
                    self.cs1.set(rolls[0])
                if not self.cs2.get():
                    self.cs2.set(rolls[1])
        except Exception:
            pass

    def docmp(self):
        r1 = self.cs1.get().strip()
        r2 = self.cs2.get().strip()

        if not r1 or not r2:
            messagebox.showwarning("Selection Missing", "Please select two students to compare.")
            return

        if r1 == r2:
            messagebox.showwarning("Same Student", "Please select two different students to compare.")
            return

        try:
            cmp = database.comparetwo(r1, r2)
            if not cmp:
                messagebox.showerror("Error", "Could not retrieve report data for one or both students.")
                return

            self.cmpdata = cmp
            s1 = cmp["student_1"]
            s2 = cmp["student_2"]

            self.cmptree.heading("st1_marks", text=f"{s1['name']} ({s1['roll_no']})")
            self.cmptree.heading("st2_marks", text=f"{s2['name']} ({s2['roll_no']})")

            wt = (
                f"🏆 Overall Leader: {cmp['overall_leader']}  •  "
                f"{s1['name']}: {s1['percentage']}% ({s1['total_obtained']} marks)  vs.  "
                f"{s2['name']}: {s2['percentage']}% ({s2['total_obtained']} marks)  •  "
                f"Margin: {cmp['difference_percentage']}%"
            )
            self.cmpwin.set(wt)

            self.cmptree.delete(*self.cmptree.get_children())
            for itm in cmp["subject_comparison"]:
                ds = f"+{itm['difference']}" if itm["difference"] > 0 else str(itm["difference"])
                self.cmptree.insert(
                    "", tk.END,
                    values=[
                        itm["subject"],
                        itm["student_1_marks"] if itm["student_1_marks"] is not None else "N/A",
                        itm["student_2_marks"] if itm["student_2_marks"] is not None else "N/A",
                        ds,
                        itm["leader"],
                    ],
                )

            self.setst(f"Compared {s1['name']} and {s2['name']}: Leader is {cmp['overall_leader']}.")
        except Exception as e:
            messagebox.showerror("Comparison Error", f"Failed to compare students: {e}")

    def expcmpcsv(self):
        if not self.cmpdata:
            self.docmp()

        if not self.cmpdata:
            messagebox.showwarning("No Data", "Perform a student comparison first before exporting.")
            return

        cmp = self.cmpdata
        s1 = cmp["student_1"]
        s2 = cmp["student_2"]

        dn = f"Comparison_{s1['roll_no']}_vs_{s2['roll_no']}"
        rname, out = self.askname(dn)
        if not rname or not out:
            return

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
            "Subject": "OVERALL TOTAL",
            f"{s1['name']}_{s1['roll_no']}": f"{s1['total_obtained']} ({s1['percentage']}%)",
            f"{s2['name']}_{s2['roll_no']}": f"{s2['total_obtained']} ({s2['percentage']}%)",
            "Difference": f"{cmp['difference_percentage']}%",
            "Subject_Leader": cmp["overall_leader"],
        })

        df = pd.DataFrame(rows)
        file_handler.savecsv(df, out, rname=rname)
        ok, msg = file_handler.showfile(out)
        messagebox.showinfo("Revealed in CSV", f"Comparison CSV created with name '{rname}':\n{out.resolve()}\n\n{msg}")
        self.setst(f"Exported & revealed comparison CSV: {out.name}")

    def mksubstats(self, par):
        top = ttk.Frame(par, style="TFrame")
        top.pack(fill=tk.X, pady=(5, 10))

        ttk.Button(top, text="🔄 Refresh Subject Stats", style="Primary.TButton", command=self.loadstats).pack(side=tk.LEFT, padx=5)
        ttk.Button(top, text="📊 Reveal in CSV", style="Success.TButton", command=self.expstatscsv).pack(side=tk.RIGHT, padx=5)

        ttc = ttk.Frame(par, style="Card.TFrame", padding=1)
        ttc.pack(fill=tk.BOTH, expand=True)

        self.statstree = ttk.Treeview(ttc, show="headings")
        ys = ttk.Scrollbar(ttc, orient=tk.VERTICAL, command=self.statstree.yview)
        self.statstree.configure(yscrollcommand=ys.set)

        self.statstree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        ys.pack(side=tk.RIGHT, fill=tk.Y)

        cols = ["subject_name", "total_students", "avg_marks", "highest_marks", "lowest_marks", "max_marks", "avg_percentage"]
        hdrs = ["Subject", "Total Students", "Average Marks", "Highest Marks", "Lowest Marks", "Max Marks", "Average %"]
        self.statstree["columns"] = cols
        for c, h in zip(cols, hdrs):
            self.statstree.heading(c, text=h)
            self.statstree.column(c, width=120, anchor="center" if c != "subject_name" else "w")

    def loadstats(self):
        try:
            stats = database.getsubstats()
            self.substats = stats
            self.statstree.delete(*self.statstree.get_children())

            for r in stats:
                self.statstree.insert(
                    "", tk.END,
                    values=[
                        r.get("subject_name", ""),
                        r.get("total_students", 0),
                        float(r.get("avg_marks") or 0),
                        float(r.get("highest_marks") or 0),
                        float(r.get("lowest_marks") or 0),
                        float(r.get("max_marks") or 100),
                        f"{float(r.get('avg_percentage') or 0):.2f}%",
                    ],
                )

            self.setst(f"Loaded statistics for {len(stats)} subject(s).")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load subject statistics: {e}")

    def expstatscsv(self):
        if not self.substats:
            self.loadstats()

        if not self.substats:
            messagebox.showwarning("No Data", "No subject statistics available to export.")
            return

        rname, out = self.askname("Subject_Performance_Statistics")
        if not rname or not out:
            return

        df = pd.DataFrame(self.substats)
        file_handler.savecsv(df, out, rname=rname)
        ok, msg = file_handler.showfile(out)
        messagebox.showinfo("Revealed in CSV", f"Subject stats created with name '{rname}':\n{out.resolve()}\n\n{msg}")
        self.setst(f"Exported & revealed stats CSV: {out.name}")

    # =============================================
    # TAB 5: REPORT CARDS
    # =============================================
    def mktab5(self):
        top = ttk.Frame(self.tab5, style="TFrame")
        top.pack(fill=tk.X, pady=(5, 10))

        ttk.Label(top, text="Student Roll No:", font=("Segoe UI", 10, "bold")).pack(side=tk.LEFT, padx=(0, 6))

        self.rollcmb = ttk.Combobox(top, textvariable=self.rroll, width=14)
        self.rollcmb.pack(side=tk.LEFT, padx=(0, 10))

        ttk.Button(top, text="📄 Generate Report Card", style="Primary.TButton", command=self.doreport).pack(side=tk.LEFT, padx=5)
        ttk.Button(top, text="📊 Reveal in CSV", style="Success.TButton", command=self.exprepcsv).pack(side=tk.RIGHT, padx=5)
        ttk.Button(top, text="💾 Save Report (.txt)", style="Secondary.TButton", command=self.savereptxt).pack(side=tk.RIGHT, padx=5)

        pc = ttk.Frame(self.tab5, style="Card.TFrame", padding=10)
        pc.pack(fill=tk.BOTH, expand=True)

        self.repbox = ScrolledText(pc, wrap=tk.WORD, font=("Consolas", 11), bg="#f8fafc", fg="#0f172a", relief="solid", bd=1)
        self.repbox.pack(fill=tk.BOTH, expand=True)

        self.refrolls()
        self.refanadrops()

    def refrolls(self):
        try:
            studs = database.fetchstuds()
            rolls = [s["roll_no"] for s in studs]
            self.rollcmb["values"] = rolls
            if rolls and not self.rroll.get():
                self.rroll.set(rolls[0])
        except Exception:
            pass

    def doreport(self):
        rno = self.rroll.get().strip()
        if not rno:
            messagebox.showwarning("Roll No Missing", "Please select or enter a student Roll No.")
            return

        try:
            rows = database.fetchreport(rno)
            self.reprows = rows
            rc = file_handler.makereportcard(rows)

            self.repbox.delete("1.0", tk.END)
            self.repbox.insert(tk.END, rc)
            self.setst(f"Generated report card for student {rno}.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to fetch report card: {e}")

    def exprepcsv(self):
        rno = self.rroll.get().strip()
        if not self.reprows:
            self.doreport()

        if not self.reprows:
            messagebox.showwarning("No Data", f"No report data found for Roll No '{rno}'.")
            return

        snm = ""
        if self.reprows and self.reprows[0].get("name"):
            snm = self.reprows[0]["name"].replace(" ", "_")
        dn = f"Report_Card_{rno}_{snm}" if snm else f"Report_Card_{rno}"

        rname, out = self.askname(dn)
        if not rname or not out:
            return

        file_handler.savereportcsv(self.reprows, out, rname=rname)
        ok, msg = file_handler.showfile(out)
        messagebox.showinfo("Revealed in CSV", f"Report card created with name '{rname}':\n{out.resolve()}\n\n{msg}")
        self.setst(f"Exported & revealed report card CSV: {out.name}")

    def savereptxt(self):
        rno = self.rroll.get().strip()
        txt = self.repbox.get("1.0", tk.END).strip()
        if not txt:
            messagebox.showwarning("Empty Report", "Generate a report card first before saving.")
            return

        out = REPDIR / f"report_card_{rno}.txt"
        out.write_text(txt, encoding="utf-8")
        ok, msg = file_handler.showfile(out)
        messagebox.showinfo("Report Saved", f"Report card saved to:\n{out.resolve()}\n\n{msg}")
        self.setst(f"Saved report card: {out.name}")


def startgui():
    app = App()
    app.mainloop()


if __name__ == "__main__":
    startgui()
