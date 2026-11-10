# Academic Result Analysis & Tabulation System 🎓

A modern, high-performance academic result analysis and tabulation suite built with Python, MySQL, and Rich CLI. Designed for school administrators and exam controllers to ingest raw text files, store academic records in a relational database, and tabulate comprehensive CBSE & school examination reports with multi-dimensional filtering.

---

## ✨ Key Features

1. **Text File Ingestion (.txt -> Database)**
   - Automatically parses multiple standard school formats:
     - **Wide Tabular Format** (`Roll No | Name | Class | Section | Subject1 | Subject2 ...`)
     - **Block Format** (`Roll No: ... Name: ... Marks: English: 98, Math: 100 ...`)
     - **Delimited Long Format** (`Roll, Name, Class, Section, Subject, Marks`)
   - Auto-normalizes subject aliases (`Maths` -> `Math`, `CS` -> `Computer Science`, `Pol Sci` -> `Political Science`, etc.).
   - Directly commits and updates records in MySQL with zero manual typing required.

2. **Official Result Analysis Tabulations (Matching Board / School Sheets)**
   - **School / Class Toppers**: Place I, II, III... Roll No, Name, Total Marks, Percentage, Class & Section.
   - **Overall Performance Summary**:
     - Overall School / Class Average %
     - Cohort Counts: Total Appeared, Distinctions (≥ 75%), 1st Class (≥ 60%), 2nd Class (50–59%), Compartment (< 33%)
     - Standard Score Distribution Bins: Above 95% (> 475), 91–94%, 81–90%, 75–80%, 60–74%, Below 60%.
   - **Subject Average & Performance Statistics**:
     - Subject Name, Student Count, Subject Average, Highest Marks, Count of Toppers, Number of Centums (100/100), Lowest Marks.
   - **Subject Toppers Roster**:
     - Grouped cards per subject showing top mark, number of top students, and full student names.
   - **Full Tabulated Merit Roster**:
     - Ranked listing with total scores, percentages, and academic statuses.

3. **Advanced Multi-Dimensional Filtering**
   - Filter by Entire School vs Specific Class vs Specific Section.
   - **Centum Club**: Filter all students scoring a perfect 100 in any subject.
   - **Distinction / First Class / Compartment filters**.
   - **Subject-Specific Roster** with minimum mark cut-off.
   - **Custom Percentage Range** filter.

4. **Individual & Head-to-Head Analytics**
   - **Individual Student Report Card**: Complete subject marks breakdown, percentage, CBSE letter grades (A1, A2, B1, etc.), and status.
   - **Side-by-Side Comparison**: Compare any two students subject by subject with differential margin analysis.

---

## 🚀 How to Run

1. **Start MySQL Server** (e.g., via XAMPP or native service).
   - Default configuration: `localhost:3306`, user: `root`, database: `student_result_system`.
   - Override using environment variables: `MYSQL_HOST`, `MYSQL_USER`, `MYSQL_PASSWORD`, `MYSQL_DATABASE`, `MYSQL_PORT`.

2. **Launch the CLI**:
   ```powershell
   python main.py
   ```
   Or from inside `StudentResultSystem/`:
   ```powershell
   python main.py
   ```

3. **Sample Data**:
   Sample test files are located in `StudentResultSystem/sample_data/`:
   - `cbse_class12_results.txt`: Wide tabular format containing CBSE Std XII results.
   - `cbse_block_format.txt`: Key-value block format example.

---

## 📁 File Structure

- `main.py` (root launcher) -> launches `StudentResultSystem/main.py`.
- `StudentResultSystem/main.py` -> Rich CLI interactive menu and report generation engine.
- `StudentResultSystem/database.py` -> MySQL schema initialization, aggregation queries, and filtering engine.
- `StudentResultSystem/file_handler.py` -> Universal text file parser and database ingestion pipeline.
- `StudentResultSystem/sample_data/` -> Real-world CBSE sample input files.
