# Student Result System 🎓

this project takes student data from a text file, puts it in mysql database, and shows it in csv. also has a full GUI window using tkinter.

## what this does

1. **GUI Window** - nice desktop app with tabs
   - import text file tab - load ur .txt file and data goes to database
   - database records tab - see all students marks subjects in a table
   - results and rankings tab - who came first who came last
   - analytics tab - who scored the most? compare two students
   - report cards tab - generate proper report card with grades

2. **Text File Input** - give .txt file with student data, it reads and puts in mysql
   - works with comma separated, tab separated, pipe separated, or block format
   - u can even paste text directly in the editor

3. **CSV Export with Name** - asks what name u want for csv file
   - adds name in filename and inside the csv as a column
   - opens the file in explorer automatically

4. **Who Scored Most** - find out the topper
   - overall topper
   - subject wise toppers
   - compare two students side by side
   - subject statistics (average highest lowest)

5. **Report Cards** - proper formatted report card with grades

## how to run

1. start mysql server first (open xampp and start mysql)
   - default: localhost:3306, user: root, password: 1234

2. run the program:
   ```
   python main.py
   ```
   this opens the GUI window automatically

3. want terminal mode instead?
   ```
   python main.py --cli
   ```

## files

- `database.py` - all mysql database functions (addstud, delstud, getranked etc)
- `file_handler.py` - text file parsing and csv export (parsetxt, savecsv etc)
- `main.py` - the main file with CLI menu
- `gui.py` - the tkinter GUI window app

made with ❤️ and lots of chai
