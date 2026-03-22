===============================================================
  LankAmerica Compass — Personal Financial Planner
  README & Setup Guide
===============================================================

REQUIREMENTS
------------
  - Windows 10 or 11 (64-bit)
  - Python 3.10 or later  (python.org)
  - Internet connection for first-time dependency install only

FIRST-TIME SETUP
----------------
1. Install Python from https://www.python.org (check "Add to PATH")

2. Open a Command Prompt in this folder and run:
      pip install -r requirements.txt

3. Launch the app:
      pythonw main.py
      (Use 'pythonw' to hide the console window, or 'python' to see errors)

   A splash screen will appear, followed by the login window.

4. On your first launch, click "Create Account" to register.
   Your database file is created automatically at:
      Documents\LankAmericaCompass\compass.db

BUILDING A PORTABLE .EXE (optional)
-------------------------------------
  Install PyInstaller, then run:
      pip install pyinstaller
      pyinstaller build.spec

  The finished app will appear in:
      dist\LankAmericaCompass\LankAmericaCompass.exe

  Copy the entire dist\LankAmericaCompass\ folder to any machine.
  No Python installation required on the target machine.

CLOUD SYNC SETUP
-----------------
LankAmerica Compass stores all data in a single .db file.
To sync between computers or share accounts with another user:

  1. Install OneDrive, Google Drive, Dropbox, or Nextcloud on both machines.

  2. In the app, go to Settings → Database Location → Browse / Move Database.
     Choose a path inside your synced folder, e.g.:
       C:\Users\You\OneDrive\LankAmericaCompass\compass.db
       C:\Users\You\Dropbox\LankAmericaCompass\compass.db
       C:\Users\You\Google Drive\LankAmericaCompass\compass.db

  3. The app copies your existing database to the new location.
     Restart the app to use it from there.

  4. On the second machine, launch the app and use the Browse button
     on the login screen to point to the same synced .db file.

  SHARING ACCOUNTS:
  - Both users must be registered on the same .db file.
  - The account owner can share individual accounts by editing the account
    and checking the boxes next to other users.
  - Both machines must have a synced copy of the same .db file.

  SIMULTANEOUS EDITING:
  - The database uses WAL (Write-Ahead Logging) to minimize conflicts.
  - Avoid having two users edit at the exact same moment.
  - The app will show a warning if a file lock is detected.

QUICK FEATURE GUIDE
--------------------
  ACCOUNTS       Add, edit, archive any number of accounts (Checking,
                 Savings, Credit Card, Cash, Investment, Other).

  REGISTER       Click an account in the sidebar to open its register.
                 - Use the date/month filter bar at the top.
                 - Click month pills (Jan-Dec) to jump to a month.
                 - Double-click any row to edit a transaction.
                 - Right-click a row for a context menu.
                 - "Find Next Unreconciled" jumps to the first open item.

  TRANSACTIONS   Add via the "+ Add Transaction" button.
                 - Choose Debit (money out) or Credit (money in).
                 - Select a category from the dropdown.
                 - Check "Mark as Reconciled" to grey out the row.

  CATEGORIES     Sidebar → Categories
                 - Add, rename, delete expense and income categories.
                 - Renaming updates ALL existing transactions automatically.
                 - Deleting asks you to reassign existing transactions.

  BUDGETS        Sidebar → Budgets
                 - Set optional monthly budget amounts per category.
                 - View actual vs. budget for any month.
                 - Over-budget expenses show in RED, over-budget income in GREEN.
                 - Categories with no budget set show no status color.

  CHARTS         Sidebar → Charts
                 - Pie Chart: break down spending or income by category,
                   account type, or transaction type for any date range.
                   Export as PNG or PDF.
                 - Bar Chart: see monthly income (bars above zero) vs.
                   expenses (bars below zero) with a net line overlay.
                   Export as PNG or PDF.

  ANNUAL TOTALS  Sidebar → Annual Totals
                 - Table of monthly debits, credits, and net per account.
                 - Click any cell to drill into that month's register.
                 - Export the table to CSV.

  EXPORT CSV     Settings → Export All Data to CSV  (or use any account's
                 export button). Choose accounts, date range, types,
                 categories, reconciled status, and columns to include.

  BACKUP         Settings → Backup Database
                 - Creates a point-in-time copy of your .db file.

SUPPORT
-------
  This application was built with Python, PyQt6, SQLite, and Matplotlib.
  Data is never sent to any server. Everything stays on your machine (or
  in your chosen cloud folder).

===============================================================
