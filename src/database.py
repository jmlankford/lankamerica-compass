"""
database.py — SQLite database layer for LankAmerica Compass
"""
import sqlite3
import os
from typing import List, Optional, Dict, Any, Tuple
from pathlib import Path


DEFAULT_EXPENSE_CATEGORIES = [
    "Housing", "Rent/Mortgage", "Utilities", "Internet & Phone", "Insurance",
    "Groceries", "Dining Out", "Coffee & Cafes", "Transportation", "Gas & Fuel",
    "Car Payment", "Car Insurance", "Parking & Tolls", "Public Transit",
    "Healthcare", "Medical Bills", "Prescriptions", "Personal Care",
    "Clothing & Apparel", "Entertainment", "Streaming Services", "Subscriptions",
    "Hobbies", "Travel", "Pets", "Education", "Childcare", "Gifts & Donations",
    "Charity", "Savings Transfer", "Investment Transfer", "Business Expense",
    "Taxes", "Bank Fees", "ATM Fees", "Miscellaneous"
]

DEFAULT_INCOME_CATEGORIES = [
    "Salary/Wages", "Freelance Income", "Business Income", "Rental Income",
    "Investment Income", "Interest Income", "Refund/Reimbursement",
    "Gift Received", "Other Income"
]


class Database:
    def __init__(self, db_path: str):
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA foreign_keys=ON")
        self.conn.commit()
        self.create_tables()

    def _execute(self, sql: str, params: tuple = ()) -> sqlite3.Cursor:
        try:
            cur = self.conn.execute(sql, params)
            self.conn.commit()
            return cur
        except sqlite3.Error as e:
            self.conn.rollback()
            raise

    def _fetchall(self, sql: str, params: tuple = ()) -> List[sqlite3.Row]:
        cur = self.conn.execute(sql, params)
        return cur.fetchall()

    def _fetchone(self, sql: str, params: tuple = ()) -> Optional[sqlite3.Row]:
        cur = self.conn.execute(sql, params)
        return cur.fetchone()

    # -------------------------------------------------------------------------
    # Table creation & seeding
    # -------------------------------------------------------------------------

    def create_tables(self):
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                display_name TEXT NOT NULL,
                color TEXT DEFAULT '#1565C0',
                db_path TEXT,
                created_at TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS accounts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                type TEXT NOT NULL,
                owner_user_id INTEGER NOT NULL,
                opening_balance REAL DEFAULT 0.0,
                notes TEXT,
                is_archived INTEGER DEFAULT 0,
                created_at TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (owner_user_id) REFERENCES users(id)
            );

            CREATE TABLE IF NOT EXISTS account_shares (
                account_id INTEGER,
                user_id INTEGER,
                PRIMARY KEY (account_id, user_id),
                FOREIGN KEY (account_id) REFERENCES accounts(id),
                FOREIGN KEY (user_id) REFERENCES users(id)
            );

            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                category_type TEXT NOT NULL,
                is_default INTEGER DEFAULT 0,
                sort_order INTEGER DEFAULT 0,
                created_at TEXT DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                account_id INTEGER NOT NULL,
                date TEXT NOT NULL,
                type TEXT NOT NULL,
                check_number TEXT,
                description TEXT,
                memo TEXT,
                category_id INTEGER,
                cleared INTEGER DEFAULT 0,
                debit REAL DEFAULT 0.0,
                credit REAL DEFAULT 0.0,
                created_by_user_id INTEGER,
                created_at TEXT DEFAULT (datetime('now')),
                updated_at TEXT DEFAULT (datetime('now')),
                FOREIGN KEY (account_id) REFERENCES accounts(id),
                FOREIGN KEY (category_id) REFERENCES categories(id),
                FOREIGN KEY (created_by_user_id) REFERENCES users(id)
            );

            CREATE TABLE IF NOT EXISTS budgets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category_id INTEGER NOT NULL,
                monthly_amount REAL NOT NULL,
                user_id INTEGER NOT NULL,
                FOREIGN KEY (category_id) REFERENCES categories(id),
                FOREIGN KEY (user_id) REFERENCES users(id)
            );

            CREATE TABLE IF NOT EXISTS app_settings (
                key TEXT NOT NULL,
                value TEXT,
                user_id INTEGER,
                PRIMARY KEY (key, user_id),
                FOREIGN KEY (user_id) REFERENCES users(id)
            );
        """)
        self.conn.commit()
        self._migrate()
        self._seed_categories()

    def _migrate(self):
        """Rename legacy 'reconciled' column to 'cleared' if needed."""
        try:
            cols = [r[1] for r in self.conn.execute("PRAGMA table_info(transactions)").fetchall()]
            if 'reconciled' in cols and 'cleared' not in cols:
                self.conn.execute("ALTER TABLE transactions RENAME COLUMN reconciled TO cleared")
                self.conn.commit()
            elif 'reconciled' in cols and 'cleared' in cols:
                self.conn.execute("UPDATE transactions SET cleared = reconciled WHERE cleared = 0 AND reconciled = 1")
                self.conn.commit()
        except Exception:
            pass

    def _seed_categories(self):
        count = self._fetchone("SELECT COUNT(*) as c FROM categories")
        if count and count['c'] > 0:
            return
        for i, name in enumerate(DEFAULT_EXPENSE_CATEGORIES):
            self._execute(
                "INSERT INTO categories (name, category_type, is_default, sort_order) VALUES (?, 'expense', 1, ?)",
                (name, i)
            )
        for i, name in enumerate(DEFAULT_INCOME_CATEGORIES):
            self._execute(
                "INSERT INTO categories (name, category_type, is_default, sort_order) VALUES (?, 'income', 1, ?)",
                (name, i)
            )

    # -------------------------------------------------------------------------
    # Users
    # -------------------------------------------------------------------------

    def create_user(self, username: str, password_hash: str, display_name: str) -> int:
        cur = self._execute(
            "INSERT INTO users (username, password_hash, display_name) VALUES (?, ?, ?)",
            (username, password_hash, display_name)
        )
        return cur.lastrowid

    def get_user_by_username(self, username: str) -> Optional[Dict]:
        row = self._fetchone("SELECT * FROM users WHERE username = ?", (username,))
        return dict(row) if row else None

    def get_user_by_id(self, user_id: int) -> Optional[Dict]:
        row = self._fetchone("SELECT * FROM users WHERE id = ?", (user_id,))
        return dict(row) if row else None

    def get_all_users(self) -> List[Dict]:
        rows = self._fetchall("SELECT * FROM users ORDER BY display_name")
        return [dict(r) for r in rows]

    def update_user(self, user_id: int, display_name: str = None, color: str = None) -> None:
        if display_name is not None:
            self._execute("UPDATE users SET display_name = ? WHERE id = ?", (display_name, user_id))
        if color is not None:
            self._execute("UPDATE users SET color = ? WHERE id = ?", (color, user_id))

    def update_user_password(self, user_id: int, new_hash: str) -> None:
        self._execute("UPDATE users SET password_hash = ? WHERE id = ?", (new_hash, user_id))

    # -------------------------------------------------------------------------
    # Accounts
    # -------------------------------------------------------------------------

    def create_account(self, name: str, type: str, owner_user_id: int,
                       opening_balance: float = 0.0, notes: str = '') -> int:
        cur = self._execute(
            "INSERT INTO accounts (name, type, owner_user_id, opening_balance, notes) VALUES (?, ?, ?, ?, ?)",
            (name, type, owner_user_id, opening_balance, notes)
        )
        return cur.lastrowid

    def get_accounts_for_user(self, user_id: int) -> List[Dict]:
        sql = """
            SELECT DISTINCT a.*
            FROM accounts a
            LEFT JOIN account_shares s ON s.account_id = a.id
            WHERE (a.owner_user_id = ? OR s.user_id = ?)
              AND a.is_archived = 0
            ORDER BY a.name
        """
        rows = self._fetchall(sql, (user_id, user_id))
        return [dict(r) for r in rows]

    def get_account_by_id(self, account_id: int) -> Optional[Dict]:
        row = self._fetchone("SELECT * FROM accounts WHERE id = ?", (account_id,))
        return dict(row) if row else None

    def update_account(self, account_id: int, name: str, type: str,
                       opening_balance: float, notes: str) -> None:
        self._execute(
            "UPDATE accounts SET name=?, type=?, opening_balance=?, notes=? WHERE id=?",
            (name, type, opening_balance, notes, account_id)
        )

    def archive_account(self, account_id: int) -> None:
        self._execute("UPDATE accounts SET is_archived=1 WHERE id=?", (account_id,))

    def delete_account(self, account_id: int) -> None:
        self._execute("DELETE FROM transactions WHERE account_id=?", (account_id,))
        self._execute("DELETE FROM account_shares WHERE account_id=?", (account_id,))
        self._execute("DELETE FROM accounts WHERE id=?", (account_id,))

    def get_account_shared_users(self, account_id: int) -> List[int]:
        rows = self._fetchall("SELECT user_id FROM account_shares WHERE account_id=?", (account_id,))
        return [r['user_id'] for r in rows]

    def set_account_shares(self, account_id: int, user_ids: List[int]) -> None:
        self._execute("DELETE FROM account_shares WHERE account_id=?", (account_id,))
        for uid in user_ids:
            self._execute(
                "INSERT OR IGNORE INTO account_shares (account_id, user_id) VALUES (?, ?)",
                (account_id, uid)
            )

    # -------------------------------------------------------------------------
    # Transactions
    # -------------------------------------------------------------------------

    def create_transaction(self, account_id: int, date: str, type: str,
                           check_number: str, description: str, memo: str,
                           category_id: Optional[int], cleared: int,
                           debit: float, credit: float,
                           created_by_user_id: Optional[int],
                           # Legacy alias accepted but ignored
                           reconciled: int = None) -> int:
        if reconciled is not None and cleared == 0:
            cleared = reconciled  # accept old callers
        cur = self._execute(
            """INSERT INTO transactions
               (account_id, date, type, check_number, description, memo,
                category_id, cleared, debit, credit, created_by_user_id,
                created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'))""",
            (account_id, date, type, check_number, description, memo,
             category_id, cleared, debit, credit, created_by_user_id)
        )
        return cur.lastrowid

    def update_transaction(self, transaction_id: int, date: str, type: str,
                           check_number: str, description: str, memo: str,
                           category_id: Optional[int], cleared: int,
                           debit: float, credit: float,
                           # Legacy alias
                           reconciled: int = None) -> None:
        if reconciled is not None and cleared == 0:
            cleared = reconciled
        self._execute(
            """UPDATE transactions SET
               date=?, type=?, check_number=?, description=?, memo=?,
               category_id=?, cleared=?, debit=?, credit=?,
               updated_at=datetime('now')
               WHERE id=?""",
            (date, type, check_number, description, memo,
             category_id, cleared, debit, credit, transaction_id)
        )

    def delete_transaction(self, transaction_id: int) -> None:
        self._execute("DELETE FROM transactions WHERE id=?", (transaction_id,))

    def get_transaction_by_id(self, transaction_id: int) -> Optional[Dict]:
        row = self._fetchone("SELECT * FROM transactions WHERE id=?", (transaction_id,))
        return dict(row) if row else None

    def get_transactions(self, account_id: int,
                         start_date: str = None, end_date: str = None,
                         search: str = None, type_filter: str = None,
                         category_id: int = None,
                         cleared_filter: str = 'all',
                         reconciled_filter: str = None) -> List[Dict]:
        """
        Returns all transactions for an account, with optional filters.
        Always returns rows in ascending date order (for balance computation).
        """
        sql = """
            SELECT t.*, c.name as category_name
            FROM transactions t
            LEFT JOIN categories c ON c.id = t.category_id
            WHERE t.account_id = ?
        """
        params = [account_id]

        if start_date:
            sql += " AND t.date >= ?"
            params.append(start_date)
        if end_date:
            sql += " AND t.date <= ?"
            params.append(end_date)
        if search:
            sql += " AND (t.description LIKE ? OR t.memo LIKE ?)"
            params.extend([f'%{search}%', f'%{search}%'])
        if type_filter and type_filter != 'All':
            sql += " AND t.type = ?"
            params.append(type_filter)
        if category_id is not None:
            sql += " AND t.category_id = ?"
            params.append(category_id)
        effective_filter = reconciled_filter if reconciled_filter is not None else cleared_filter
        if effective_filter in ('cleared', 'reconciled'):
            sql += " AND t.cleared = 1"
        elif effective_filter in ('uncleared', 'unreconciled'):
            sql += " AND t.cleared = 0"

        sql += " ORDER BY t.date ASC, t.created_at ASC"
        rows = self._fetchall(sql, tuple(params))
        return [dict(r) for r in rows]

    def get_all_transactions_for_account(self, account_id: int) -> List[Dict]:
        """All transactions in ascending date order (for balance computation)."""
        sql = """
            SELECT t.*, c.name as category_name
            FROM transactions t
            LEFT JOIN categories c ON c.id = t.category_id
            WHERE t.account_id = ?
            ORDER BY t.date ASC, t.created_at ASC
        """
        rows = self._fetchall(sql, (account_id,))
        return [dict(r) for r in rows]

    def mark_cleared(self, transaction_id: int, cleared: int) -> None:
        self._execute(
            "UPDATE transactions SET cleared=?, updated_at=datetime('now') WHERE id=?",
            (cleared, transaction_id)
        )

    # Legacy alias
    def mark_reconciled(self, transaction_id: int, reconciled: int) -> None:
        self.mark_cleared(transaction_id, reconciled)

    def get_transactions_for_export(self, account_ids: List[int],
                                    start_date: str = None, end_date: str = None,
                                    type_filter: List[str] = None,
                                    category_ids: List[int] = None,
                                    cleared_filter: str = 'all',
                                    reconciled_filter: str = None,
                                    sort_order: str = 'date_asc') -> List[Dict]:
        placeholders = ','.join('?' * len(account_ids))
        sql = f"""
            SELECT t.*, c.name as category_name, a.name as account_name,
                   u.display_name as user_name
            FROM transactions t
            LEFT JOIN categories c ON c.id = t.category_id
            LEFT JOIN accounts a ON a.id = t.account_id
            LEFT JOIN users u ON u.id = t.created_by_user_id
            WHERE t.account_id IN ({placeholders})
        """
        params = list(account_ids)

        if start_date:
            sql += " AND t.date >= ?"
            params.append(start_date)
        if end_date:
            sql += " AND t.date <= ?"
            params.append(end_date)
        if type_filter:
            ph = ','.join('?' * len(type_filter))
            sql += f" AND t.type IN ({ph})"
            params.extend(type_filter)
        if category_ids:
            ph = ','.join('?' * len(category_ids))
            sql += f" AND t.category_id IN ({ph})"
            params.extend(category_ids)
        eff = reconciled_filter if reconciled_filter is not None else cleared_filter
        if eff in ('cleared', 'reconciled'):
            sql += " AND t.cleared = 1"
        elif eff in ('uncleared', 'unreconciled'):
            sql += " AND t.cleared = 0"

        sort_map = {
            'date_asc': 'ORDER BY t.date ASC, t.created_at ASC',
            'date_desc': 'ORDER BY t.date DESC, t.created_at DESC',
            'description_az': 'ORDER BY t.description ASC',
            'amount': 'ORDER BY (t.debit + t.credit) DESC',
        }
        sql += " " + sort_map.get(sort_order, 'ORDER BY t.date ASC')
        rows = self._fetchall(sql, tuple(params))
        return [dict(r) for r in rows]

    # -------------------------------------------------------------------------
    # Running balance
    # -------------------------------------------------------------------------

    def get_running_balance(self, account_id: int) -> Dict[int, float]:
        """
        Compute running balance for each transaction in ascending date order.
        Returns dict: {transaction_id: balance_after_transaction}
        """
        account = self.get_account_by_id(account_id)
        opening = account['opening_balance'] if account else 0.0
        rows = self.get_all_transactions_for_account(account_id)

        balances = {}
        running = opening
        for row in rows:
            running += row['credit'] - row['debit']
            balances[row['id']] = running
        return balances

    def get_account_balance(self, account_id: int) -> float:
        """Return the current balance of an account."""
        account = self.get_account_by_id(account_id)
        opening = account['opening_balance'] if account else 0.0
        row = self._fetchone(
            "SELECT COALESCE(SUM(credit),0) - COALESCE(SUM(debit),0) as net FROM transactions WHERE account_id=?",
            (account_id,)
        )
        net = row['net'] if row else 0.0
        return opening + net

    # -------------------------------------------------------------------------
    # Analytics
    # -------------------------------------------------------------------------

    def get_monthly_totals(self, account_id: int, year: int) -> List[Tuple]:
        """Returns list of (month_int, total_debits, total_credits)"""
        sql = """
            SELECT
                CAST(strftime('%m', date) AS INTEGER) as month,
                COALESCE(SUM(debit), 0) as total_debits,
                COALESCE(SUM(credit), 0) as total_credits
            FROM transactions
            WHERE account_id = ?
              AND strftime('%Y', date) = ?
            GROUP BY month
            ORDER BY month
        """
        rows = self._fetchall(sql, (account_id, str(year)))
        return [(r['month'], r['total_debits'], r['total_credits']) for r in rows]

    def get_monthly_totals_all_accounts(self, year: int, user_id: int) -> List[Tuple]:
        """Returns list of (month_int, total_debits, total_credits) across all user accounts."""
        accounts = self.get_accounts_for_user(user_id)
        account_ids = [a['id'] for a in accounts]
        if not account_ids:
            return []
        ph = ','.join('?' * len(account_ids))
        sql = f"""
            SELECT
                CAST(strftime('%m', date) AS INTEGER) as month,
                COALESCE(SUM(debit), 0) as total_debits,
                COALESCE(SUM(credit), 0) as total_credits
            FROM transactions
            WHERE account_id IN ({ph})
              AND strftime('%Y', date) = ?
            GROUP BY month
            ORDER BY month
        """
        params = account_ids + [str(year)]
        rows = self._fetchall(sql, tuple(params))
        return [(r['month'], r['total_debits'], r['total_credits']) for r in rows]

    def get_category_totals(self, account_id: Optional[int],
                            start_date: str, end_date: str,
                            direction: str = 'debit',
                            user_id: int = None) -> List[Dict]:
        """
        Returns list of {category_name, total} for pie charts.
        direction: 'debit' or 'credit'
        """
        amount_col = 'debit' if direction == 'debit' else 'credit'

        if account_id is not None:
            account_filter = "t.account_id = ?"
            base_params = [account_id]
        else:
            if user_id is not None:
                accounts = self.get_accounts_for_user(user_id)
                ids = [a['id'] for a in accounts]
                if not ids:
                    return []
                ph = ','.join('?' * len(ids))
                account_filter = f"t.account_id IN ({ph})"
                base_params = ids
            else:
                account_filter = "1=1"
                base_params = []

        sql = f"""
            SELECT COALESCE(c.name, 'Uncategorized') as category_name,
                   SUM(t.{amount_col}) as total
            FROM transactions t
            LEFT JOIN categories c ON c.id = t.category_id
            WHERE {account_filter}
              AND t.date >= ?
              AND t.date <= ?
              AND t.{amount_col} > 0
            GROUP BY c.name
            ORDER BY total DESC
        """
        params = base_params + [start_date, end_date]
        rows = self._fetchall(sql, tuple(params))
        return [{'category_name': r['category_name'], 'total': r['total']} for r in rows]

    def get_ytd_totals(self, account_id: int, user_id: int) -> Dict:
        """Returns YTD debits and credits for an account."""
        from datetime import date
        year = date.today().year
        start = f"{year}-01-01"
        end = f"{year}-12-31"
        row = self._fetchone(
            """SELECT COALESCE(SUM(debit),0) as ytd_debits,
                      COALESCE(SUM(credit),0) as ytd_credits
               FROM transactions
               WHERE account_id=? AND date >= ? AND date <= ?""",
            (account_id, start, end)
        )
        return {
            'ytd_debits': row['ytd_debits'] if row else 0.0,
            'ytd_credits': row['ytd_credits'] if row else 0.0
        }

    def get_uncleared_count(self, account_id: int) -> int:
        row = self._fetchone(
            "SELECT COUNT(*) as c FROM transactions WHERE account_id=? AND cleared=0",
            (account_id,)
        )
        return row['c'] if row else 0

    # Legacy alias
    def get_unreconciled_count(self, account_id: int) -> int:
        return self.get_uncleared_count(account_id)

    def get_annual_monthly_breakdown(self, year: int, user_id: int) -> Dict:
        """
        Returns { account_id: { month_int: net_amount, ... }, ... }
        for the annual totals widget.
        """
        accounts = self.get_accounts_for_user(user_id)
        result = {}
        for acc in accounts:
            aid = acc['id']
            rows = self._fetchall(
                """SELECT CAST(strftime('%m', date) AS INTEGER) as month,
                          COALESCE(SUM(credit),0) - COALESCE(SUM(debit),0) as net
                   FROM transactions
                   WHERE account_id=? AND strftime('%Y', date)=?
                   GROUP BY month""",
                (aid, str(year))
            )
            month_data = {r['month']: r['net'] for r in rows}
            result[aid] = month_data
        return result

    # -------------------------------------------------------------------------
    # Categories
    # -------------------------------------------------------------------------

    def get_all_categories(self) -> List[Dict]:
        rows = self._fetchall(
            "SELECT * FROM categories ORDER BY category_type, sort_order, name"
        )
        return [dict(r) for r in rows]

    def get_categories_by_type(self, category_type: str) -> List[Dict]:
        rows = self._fetchall(
            "SELECT * FROM categories WHERE category_type=? ORDER BY sort_order, name",
            (category_type,)
        )
        return [dict(r) for r in rows]

    def create_category(self, name: str, category_type: str) -> int:
        row = self._fetchone(
            "SELECT MAX(sort_order) as mx FROM categories WHERE category_type=?",
            (category_type,)
        )
        next_order = (row['mx'] or 0) + 1 if row else 0
        cur = self._execute(
            "INSERT INTO categories (name, category_type, is_default, sort_order) VALUES (?, ?, 0, ?)",
            (name, category_type, next_order)
        )
        return cur.lastrowid

    def rename_category(self, category_id: int, new_name: str) -> None:
        self._execute("UPDATE categories SET name=? WHERE id=?", (new_name, category_id))

    def delete_category(self, category_id: int, reassign_to: Optional[int] = None) -> None:
        if reassign_to is not None:
            self._execute(
                "UPDATE transactions SET category_id=? WHERE category_id=?",
                (reassign_to, category_id)
            )
        self._execute("DELETE FROM budgets WHERE category_id=?", (category_id,))
        self._execute("DELETE FROM categories WHERE id=?", (category_id,))

    def reorder_category(self, category_id: int, new_order: int) -> None:
        self._execute("UPDATE categories SET sort_order=? WHERE id=?", (new_order, category_id))

    def get_category_transaction_count(self, category_id: int) -> int:
        row = self._fetchone(
            "SELECT COUNT(*) as c FROM transactions WHERE category_id=?",
            (category_id,)
        )
        return row['c'] if row else 0

    def get_category_total(self, category_id: int) -> float:
        row = self._fetchone(
            "SELECT COALESCE(SUM(debit+credit),0) as total FROM transactions WHERE category_id=?",
            (category_id,)
        )
        return row['total'] if row else 0.0

    # -------------------------------------------------------------------------
    # Budgets
    # -------------------------------------------------------------------------

    def get_budgets_for_user(self, user_id: int) -> List[Dict]:
        rows = self._fetchall(
            """SELECT b.*, c.name as category_name, c.category_type
               FROM budgets b
               JOIN categories c ON c.id = b.category_id
               WHERE b.user_id=?
               ORDER BY c.category_type, c.sort_order""",
            (user_id,)
        )
        return [dict(r) for r in rows]

    def get_budget(self, category_id: int, user_id: int) -> Optional[Dict]:
        row = self._fetchone(
            "SELECT * FROM budgets WHERE category_id=? AND user_id=?",
            (category_id, user_id)
        )
        return dict(row) if row else None

    def set_budget(self, category_id: int, user_id: int, monthly_amount: float) -> None:
        existing = self.get_budget(category_id, user_id)
        if existing:
            self._execute(
                "UPDATE budgets SET monthly_amount=? WHERE category_id=? AND user_id=?",
                (monthly_amount, category_id, user_id)
            )
        else:
            self._execute(
                "INSERT INTO budgets (category_id, user_id, monthly_amount) VALUES (?, ?, ?)",
                (category_id, user_id, monthly_amount)
            )

    def delete_budget(self, category_id: int, user_id: int) -> None:
        self._execute(
            "DELETE FROM budgets WHERE category_id=? AND user_id=?",
            (category_id, user_id)
        )

    def get_monthly_actual_by_category(self, account_ids: List[int],
                                       year: int, month: int) -> Dict[int, float]:
        """Returns {category_id: total_amount} for a given month across accounts."""
        if not account_ids:
            return {}
        ph = ','.join('?' * len(account_ids))
        start = f"{year:04d}-{month:02d}-01"
        import calendar
        last_day = calendar.monthrange(year, month)[1]
        end = f"{year:04d}-{month:02d}-{last_day:02d}"
        rows = self._fetchall(
            f"""SELECT category_id,
                       COALESCE(SUM(debit),0) as total_debit,
                       COALESCE(SUM(credit),0) as total_credit
                FROM transactions
                WHERE account_id IN ({ph}) AND date >= ? AND date <= ?
                GROUP BY category_id""",
            tuple(account_ids) + (start, end)
        )
        result = {}
        for r in rows:
            if r['category_id'] is not None:
                result[r['category_id']] = (r['total_debit'], r['total_credit'])
        return result

    # -------------------------------------------------------------------------
    # App Settings
    # -------------------------------------------------------------------------

    def get_setting(self, key: str, user_id: int, default: str = None) -> Optional[str]:
        row = self._fetchone(
            "SELECT value FROM app_settings WHERE key=? AND user_id=?",
            (key, user_id)
        )
        return row['value'] if row else default

    def set_setting(self, key: str, value: str, user_id: int) -> None:
        self._execute(
            "INSERT OR REPLACE INTO app_settings (key, value, user_id) VALUES (?, ?, ?)",
            (key, value, user_id)
        )

    def close(self):
        if self.conn:
            self.conn.close()
