"""Delivery Earnings Tracker — Tkinter desktop application with SQLite storage.

Run on Windows using: py app_sqlite.py
No third-party packages required.
"""

import json
import math
import sqlite3
import tkinter as tk
from datetime import date
from pathlib import Path
from tkinter import messagebox, ttk

PROJECT_FOLDER = Path(__file__).resolve().parent
DATABASE_FILE = PROJECT_FOLDER / "deliveries.db"
LEGACY_JSON_FILE = PROJECT_FOLDER / "deliveries.json"


class DeliveryDatabase:
    """Store delivery records in SQLite and import older JSON data once."""

    def __init__(self, database_file=DATABASE_FILE, legacy_json_file=LEGACY_JSON_FILE):
        self.connection = sqlite3.connect(database_file)
        self.connection.row_factory = sqlite3.Row
        try:
            with self.connection:
                self.connection.execute("""
                    CREATE TABLE IF NOT EXISTS deliveries (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        date TEXT NOT NULL,
                        earnings REAL NOT NULL CHECK (earnings >= 0),
                        fuel REAL NOT NULL CHECK (fuel >= 0),
                        expenses REAL NOT NULL CHECK (expenses >= 0),
                        hours REAL NOT NULL CHECK (hours >= 0)
                    )
                """)
                self.connection.execute("""
                    CREATE TABLE IF NOT EXISTS app_settings (
                        key TEXT PRIMARY KEY,
                        value TEXT NOT NULL
                    )
                """)
            self.import_json_once(legacy_json_file)
        except Exception:
            self.connection.close()
            raise

    def import_json_once(self, legacy_json_file):
        # The marker prevents duplicate imports when restarting the app.
        imported = self.connection.execute(
            "SELECT value FROM app_settings WHERE key = ?",
            ("json_import_complete",),
        ).fetchone()
        if imported is not None:
            return

        records = []
        if Path(legacy_json_file).exists():
            with open(legacy_json_file, "r", encoding="utf-8") as file:
                original_records = json.load(file)
            if not isinstance(original_records, list):
                raise ValueError("deliveries.json must contain a list of records.")
            for index, item in enumerate(original_records, start=1):
                if not isinstance(item, dict):
                    raise ValueError(f"Record #{index} in deliveries.json is invalid.")
                try:
                    entry_date = str(item["date"])
                    date.fromisoformat(entry_date)
                    values = [float(item[key]) for key in ("earnings", "fuel", "expenses", "hours")]
                except (KeyError, ValueError, TypeError) as error:
                    raise ValueError(f"Record #{index} in deliveries.json has invalid data.") from error
                if any(not math.isfinite(value) or value < 0 for value in values):
                    raise ValueError(f"Record #{index} has negative or non-finite numbers.")
                records.append((entry_date, *values))

        # All inserts and the migration marker succeed together, or none do.
        with self.connection:
            self.connection.executemany("""
                INSERT INTO deliveries (date, earnings, fuel, expenses, hours)
                VALUES (?, ?, ?, ?, ?)
            """, records)
            self.connection.execute("""
                INSERT INTO app_settings (key, value) VALUES (?, ?)
            """, ("json_import_complete", "1"))

    def get_all(self):
        return self.connection.execute("""
            SELECT id, date, earnings, fuel, expenses, hours
            FROM deliveries ORDER BY id
        """).fetchall()

    def add(self, record):
        with self.connection:
            self.connection.execute("""
                INSERT INTO deliveries (date, earnings, fuel, expenses, hours)
                VALUES (?, ?, ?, ?, ?)
            """, (record["date"], record["earnings"], record["fuel"],
                  record["expenses"], record["hours"]))

    def update(self, record_id, record):
        with self.connection:
            self.connection.execute("""
                UPDATE deliveries
                SET date = ?, earnings = ?, fuel = ?, expenses = ?, hours = ?
                WHERE id = ?
            """, (record["date"], record["earnings"], record["fuel"],
                  record["expenses"], record["hours"], record_id))

    def delete(self, record_id):
        with self.connection:
            self.connection.execute("DELETE FROM deliveries WHERE id = ?", (record_id,))

    def close(self):
        self.connection.close()


class DeliveryApp:
    def __init__(self, root, database):
        self.root = root
        self.database = database
        self.selected_record_id = None
        root.title("Delivery Earnings Tracker — SQLite")
        root.geometry("950x620")
        root.minsize(780, 520)

        self.fields = {
            "date": tk.StringVar(value=date.today().isoformat()),
            "earnings": tk.StringVar(value="0"),
            "fuel": tk.StringVar(value="0"),
            "expenses": tk.StringVar(value="0"),
            "hours": tk.StringVar(value="0"),
        }

        main = ttk.Frame(root, padding=16)
        main.pack(fill="both", expand=True)
        ttk.Label(main, text="Delivery Earnings Tracker", font=("Segoe UI", 18, "bold")).pack(anchor="w")

        form = ttk.LabelFrame(main, text="Delivery details", padding=12)
        form.pack(fill="x", pady=12)
        labels = [
            ("Date (YYYY-MM-DD)", "date"),
            ("Earnings (NT$)", "earnings"),
            ("Fuel (NT$)", "fuel"),
            ("Other expenses (NT$)", "expenses"),
            ("Hours worked", "hours"),
        ]
        for index, (label, key) in enumerate(labels):
            row, column = divmod(index, 2)
            ttk.Label(form, text=label).grid(row=row, column=column * 2, padx=5, pady=6, sticky="w")
            ttk.Entry(form, textvariable=self.fields[key], width=22).grid(
                row=row, column=column * 2 + 1, padx=5, pady=6, sticky="ew"
            )
        form.columnconfigure(1, weight=1)
        form.columnconfigure(3, weight=1)

        actions = ttk.Frame(main)
        actions.pack(fill="x", pady=(0, 12))
        ttk.Button(actions, text="Add Record", command=self.add_record).pack(side="left", padx=(0, 8))
        ttk.Button(actions, text="Update Selected", command=self.update_record).pack(side="left", padx=(0, 8))
        ttk.Button(actions, text="Delete Selected", command=self.delete_record).pack(side="left", padx=(0, 8))
        ttk.Button(actions, text="Clear Form", command=self.clear_form).pack(side="left")

        table_frame = ttk.LabelFrame(main, text="Delivery history", padding=8)
        table_frame.pack(fill="both", expand=True)
        columns = ("date", "earnings", "fuel", "expenses", "hours", "profit")
        self.table = ttk.Treeview(table_frame, columns=columns, show="headings", height=9)
        for key, heading, width in [
            ("date", "Date", 130),
            ("earnings", "Earnings", 130),
            ("fuel", "Fuel", 110),
            ("expenses", "Other expenses", 150),
            ("hours", "Hours", 100),
            ("profit", "Net profit", 130),
        ]:
            self.table.heading(key, text=heading)
            self.table.column(key, width=width, anchor="center")
        self.table.pack(side="left", fill="both", expand=True)
        scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self.table.yview)
        scrollbar.pack(side="right", fill="y")
        self.table.configure(yscrollcommand=scrollbar.set)
        self.table.bind("<<TreeviewSelect>>", self.on_select)

        self.summary = ttk.Label(main, font=("Segoe UI", 11, "bold"))
        self.summary.pack(anchor="w", pady=(12, 0))
        self.refresh()

    def read_form(self):
        entered_date = self.fields["date"].get().strip()
        try:
            date.fromisoformat(entered_date)
        except ValueError as error:
            raise ValueError("Enter a valid date like 2026-10-23.") from error

        values = {}
        for key in ("earnings", "fuel", "expenses", "hours"):
            try:
                value = float(self.fields[key].get().strip())
            except ValueError as error:
                raise ValueError(f"{key.title()} must be a number.") from error
            if not math.isfinite(value) or value < 0:
                raise ValueError(f"{key.title()} must be zero or greater.")
            values[key] = value
        return {"date": entered_date, **values}

    def add_record(self):
        try:
            self.database.add(self.read_form())
        except ValueError as error:
            messagebox.showwarning("Invalid entry", str(error))
            return
        except sqlite3.Error as error:
            messagebox.showerror("Database error", str(error))
            return
        self.refresh()
        self.clear_form()

    def update_record(self):
        if self.selected_record_id is None:
            messagebox.showinfo("Select a record", "Click a row in the table first.")
            return
        try:
            self.database.update(self.selected_record_id, self.read_form())
        except ValueError as error:
            messagebox.showwarning("Invalid entry", str(error))
            return
        except sqlite3.Error as error:
            messagebox.showerror("Database error", str(error))
            return
        self.refresh()
        self.clear_form()

    def delete_record(self):
        if self.selected_record_id is None:
            messagebox.showinfo("Select a record", "Click a row in the table first.")
            return
        if not messagebox.askyesno("Confirm deletion", "Delete the selected record?"):
            return
        try:
            self.database.delete(self.selected_record_id)
        except sqlite3.Error as error:
            messagebox.showerror("Database error", str(error))
            return
        self.refresh()
        self.clear_form()

    def on_select(self, _event):
        selected = self.table.selection()
        if not selected:
            return
        self.selected_record_id = int(selected[0])
        records = self.database.get_all()
        record = next((item for item in records if item["id"] == self.selected_record_id), None)
        if record is not None:
            for key in self.fields:
                self.fields[key].set(str(record[key]))

    def clear_form(self):
        for key, variable in self.fields.items():
            variable.set(date.today().isoformat() if key == "date" else "0")
        self.selected_record_id = None
        for item in self.table.selection():
            self.table.selection_remove(item)

    def refresh(self):
        for item in self.table.get_children():
            self.table.delete(item)
        total_earnings = total_expenses = total_hours = 0.0
        for record in self.database.get_all():
            earnings = record["earnings"]
            fuel = record["fuel"]
            other = record["expenses"]
            hours = record["hours"]
            profit = earnings - fuel - other
            total_earnings += earnings
            total_expenses += fuel + other
            total_hours += hours
            self.table.insert("", "end", iid=str(record["id"]), values=(
                record["date"], f"NT${earnings:.2f}", f"NT${fuel:.2f}",
                f"NT${other:.2f}", f"{hours:g}", f"NT${profit:.2f}"
            ))
        net_profit = total_earnings - total_expenses
        per_hour = net_profit / total_hours if total_hours else 0
        self.summary.config(text=(
            f"Earnings: NT${total_earnings:.2f}     "
            f"Expenses: NT${total_expenses:.2f}     "
            f"Profit: NT${net_profit:.2f}     "
            f"Profit/hour: NT${per_hour:.2f}"
        ))
        self.selected_record_id = None


def main():
    root = tk.Tk()
    try:
        database = DeliveryDatabase()
    except (OSError, ValueError, sqlite3.Error, json.JSONDecodeError) as error:
        messagebox.showerror("Could not open delivery data", str(error))
        root.destroy()
        return
    try:
        DeliveryApp(root, database)
        root.mainloop()
    finally:
        database.close()


if __name__ == "__main__":
    main()
