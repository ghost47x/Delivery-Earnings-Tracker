"""Delivery Earnings Tracker — portable Windows desktop release.

Run in VS Code: py desktop_release.py
Build Windows executable with PyInstaller:
    py -m pip install pyinstaller
    py -m PyInstaller --onefile --windowed --name DeliveryEarningsTracker desktop_release.py

Data storage:
- Python launch: deliveries.db beside this script.
- Frozen .exe: deliveries.db beside the executable.
- Before starting the .exe, close the Python app and copy deliveries.db into dist/.
- No database is bundled inside the executable. Do not publish personal data.
"""

import csv
import json
import math
import sqlite3
import sys
import tkinter as tk
from datetime import date, timedelta
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

# PyInstaller unpacks --onefile bundles to a temporary directory.
# Use the executable's folder rather than the temporary directory so that
# database changes persist after the application closes.
if getattr(sys, "frozen", False):
    PROJECT_FOLDER = Path(sys.executable).resolve().parent
else:
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



# Colors for the desktop interface
BG = "#0B1220"
SIDEBAR = "#09101D"
PANEL = "#141F32"
PANEL_2 = "#1B2940"
BORDER = "#293851"
TEXT = "#F2F6FC"
MUTED = "#9BACBF"
ACCENT = "#4FDED1"
BLUE = "#72A6FF"
RED = "#FF7983"
WHITE = "#FFFFFF"
FONT = "Segoe UI"


def money(value):
    return f"NT${value:,.2f}"


def add_label(parent, text, size=11, color=TEXT, bold=False, **kwargs):
    return tk.Label(parent, text=text, fg=color, bg=parent.cget("bg"),
                    font=(FONT, size, "bold" if bold else "normal"), **kwargs)


def flat_button(parent, title, command, bg=PANEL_2, fg=TEXT, width=None):
    return tk.Button(parent, text=title, command=command,
                     bg=bg, fg=fg, activebackground=BORDER,
                     activeforeground=TEXT, relief="flat", bd=0,
                     padx=16, pady=10, cursor="hand2", width=width,
                     font=(FONT, 10, "bold"))


class DashboardApp:
    def __init__(self, root, db):
        self.root = root
        self.db = db
        self.selected_id = None
        self.current_page = "dashboard"
        self.last_records = []
        self.nav_buttons = {}
        self.inputs = {
            "date": tk.StringVar(value=date.today().isoformat()),
            "earnings": tk.StringVar(value="0"),
            "fuel": tk.StringVar(value="0"),
            "expenses": tk.StringVar(value="0"),
            "hours": tk.StringVar(value="0"),
        }
        self.search = tk.StringVar()
        self.period = tk.StringVar(value="All dates")

        root.title("Delivery Earnings Tracker | Dashboard")
        root.geometry("1190x750")
        root.minsize(980, 650)
        root.configure(bg=BG)

        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Dark.Treeview", background=PANEL, foreground=TEXT,
                        fieldbackground=PANEL, borderwidth=0, rowheight=32,
                        font=(FONT, 10))
        style.configure("Dark.Treeview.Heading", background=PANEL_2, foreground=MUTED,
                        borderwidth=0, relief="flat", font=(FONT, 10, "bold"))
        style.map("Dark.Treeview", background=[("selected", "#27556B")],
                  foreground=[("selected", WHITE)])
        style.map("Dark.Treeview.Heading", background=[("active", PANEL_2)])
        style.configure("Dark.Vertical.TScrollbar", background=PANEL_2,
                        troughcolor=PANEL, arrowcolor=TEXT, bordercolor=PANEL)

        self.sidebar = tk.Frame(root, bg=SIDEBAR, width=215)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)
        add_label(self.sidebar, "DELIVERY", size=17, bold=True).pack(
            anchor="w", padx=23, pady=(32, 0))
        add_label(self.sidebar, "EARNINGS TRACKER", size=10, color=ACCENT,
                  bold=True).pack(anchor="w", padx=23, pady=(0, 38))
        self.make_nav("dashboard", "  Dashboard")
        self.make_nav("deliveries", "  Delivery records")
        tk.Frame(self.sidebar, bg=SIDEBAR).pack(fill="both", expand=True)
        add_label(self.sidebar, "LOCAL DATA  •  SQLITE", size=9,
                  color=MUTED).pack(anchor="w", padx=22, pady=(0, 8))
        add_label(self.sidebar, "Your records stay on this PC.", size=9,
                  color=MUTED).pack(anchor="w", padx=22, pady=(0, 28))

        self.main = tk.Frame(root, bg=BG)
        self.main.pack(side="left", fill="both", expand=True)
        header = tk.Frame(self.main, bg=BG)
        header.pack(fill="x", padx=30, pady=(24, 15))
        title_wrap = tk.Frame(header, bg=BG)
        title_wrap.pack(side="left")
        self.page_title = add_label(title_wrap, "Overview", size=23, bold=True)
        self.page_title.pack(anchor="w")
        self.subtitle = add_label(title_wrap, "Your delivery earnings at a glance",
                                  size=10, color=MUTED)
        self.subtitle.pack(anchor="w", pady=(4, 0))
        flat_button(header, "+ New record", lambda: self.open_new_record(),
                    bg=ACCENT, fg=SIDEBAR).pack(side="right", padx=(10, 0))
        flat_button(header, "Refresh", self.refresh).pack(side="right")

        self.pages = tk.Frame(self.main, bg=BG)
        self.pages.pack(fill="both", expand=True, padx=30, pady=(0, 26))
        self.build_dashboard()
        self.build_deliveries()
        self.search.trace_add("write", lambda *_: self.refresh_history())
        self.show_page("dashboard")
        self.refresh()

    def make_nav(self, key, label):
        btn = tk.Button(self.sidebar, text=label, anchor="w", padx=24, pady=13,
                        bg=SIDEBAR, fg=MUTED, activebackground=PANEL_2,
                        activeforeground=TEXT, relief="flat", bd=0,
                        font=(FONT, 11), cursor="hand2",
                        command=lambda: self.show_page(key))
        btn.pack(fill="x", padx=8, pady=3)
        self.nav_buttons[key] = btn

    def section(self, parent):
        return tk.Frame(parent, bg=PANEL, highlightbackground=BORDER,
                        highlightthickness=1)

    def make_table(self, parent, columns):
        wrapper = tk.Frame(parent, bg=PANEL)
        wrapper.pack(fill="both", expand=True, padx=14, pady=(6, 14))
        table = ttk.Treeview(wrapper, columns=[column[0] for column in columns],
                             show="headings", style="Dark.Treeview")
        for key, heading, width in columns:
            table.heading(key, text=heading)
            table.column(key, width=width, minwidth=70,
                         anchor="w" if key == "date" else "center", stretch=True)
        scroll = ttk.Scrollbar(wrapper, orient="vertical", command=table.yview,
                               style="Dark.Vertical.TScrollbar")
        table.configure(yscrollcommand=scroll.set)
        table.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")
        return table

    def build_dashboard(self):
        self.dashboard = tk.Frame(self.pages, bg=BG)
        cards = tk.Frame(self.dashboard, bg=BG)
        cards.pack(fill="x", pady=(0, 18))
        self.stats = {}
        stats_fields = [
            ("earnings", "TOTAL EARNINGS", BLUE),
            ("expenses", "TOTAL EXPENSES", RED),
            ("profit", "NET PROFIT", ACCENT),
            ("hourly", "PROFIT / HOUR", TEXT),
        ]
        for index, (key, label, color) in enumerate(stats_fields):
            cards.grid_columnconfigure(index, weight=1, uniform="stats")
            card = self.section(cards)
            card.grid(row=0, column=index, sticky="nsew", padx=(0, 12 if index < 3 else 0))
            add_label(card, label, size=9, color=MUTED, bold=True).pack(
                anchor="w", padx=16, pady=(18, 9))
            display = add_label(card, money(0), size=17, color=color, bold=True)
            display.pack(anchor="w", padx=16, pady=(0, 17))
            self.stats[key] = display

        chart_section = self.section(self.dashboard)
        chart_section.pack(fill="both", expand=True, pady=(0, 18))
        add_label(chart_section, "Earnings in the last 7 days", size=13,
                  bold=True).pack(anchor="w", padx=17, pady=(17, 0))
        add_label(chart_section, "Daily income before expenses", size=9,
                  color=MUTED).pack(anchor="w", padx=17, pady=(2, 2))
        self.chart = tk.Canvas(chart_section, bg=PANEL, highlightthickness=0,
                               height=215)
        self.chart.pack(fill="both", expand=True, padx=16, pady=(4, 15))
        self.chart.bind("<Configure>", lambda _event: self.draw_chart())

        recent_section = self.section(self.dashboard)
        recent_section.pack(fill="both", expand=True)
        recent_header = tk.Frame(recent_section, bg=PANEL)
        recent_header.pack(fill="x", padx=16, pady=(14, 5))
        add_label(recent_header, "Recent delivery records", size=13,
                  bold=True).pack(side="left")
        flat_button(recent_header, "View all →", lambda: self.show_page("deliveries"),
                    bg=PANEL, fg=ACCENT).pack(side="right")
        cols = [("date", "Date", 120), ("earnings", "Earnings", 120),
                ("expenses", "Expenses", 110), ("profit", "Net profit", 120)]
        self.recent_table = self.make_table(recent_section, cols)

    def build_deliveries(self):
        self.deliveries = tk.Frame(self.pages, bg=BG)
        table_section = self.section(self.deliveries)
        table_section.pack(fill="both", expand=True, pady=(0, 14))
        filters = tk.Frame(table_section, bg=PANEL)
        filters.pack(fill="x", padx=15, pady=(15, 10))
        add_label(filters, "Delivery history", size=14,
                  bold=True).pack(side="left")
        flat_button(filters, "Export CSV", self.export_csv, bg=PANEL_2).pack(side="right", padx=(8, 0))
        period_menu = ttk.Combobox(filters, textvariable=self.period,
                                   state="readonly", width=13,
                                   values=("All dates", "This week", "This month"))
        period_menu.pack(side="right", padx=(8, 0))
        period_menu.bind("<<ComboboxSelected>>", lambda _event: self.refresh_history())
        search_entry = tk.Entry(filters, textvariable=self.search, width=22,
                                bg=PANEL_2, fg=TEXT, insertbackground=TEXT,
                                bd=0, relief="flat", font=(FONT, 11))
        search_entry.pack(side="right", ipady=7, padx=(8, 0))
        add_label(filters, "Search date:", color=MUTED, size=9).pack(side="right")
        cols = [("date", "Date", 120), ("earnings", "Earnings", 110),
                ("fuel", "Fuel", 100), ("expenses", "Other expenses", 130),
                ("hours", "Hours", 75), ("profit", "Net profit", 110)]
        self.history_table = self.make_table(table_section, cols)
        self.history_table.bind("<<TreeviewSelect>>", self.select_record)

        editor = self.section(self.deliveries)
        editor.pack(fill="x")
        top = tk.Frame(editor, bg=PANEL)
        top.pack(fill="x", padx=16, pady=(14, 8))
        add_label(top, "Add or edit a delivery", size=13, bold=True).pack(side="left")
        add_label(top, "Select a row to edit it", size=9,
                  color=MUTED).pack(side="right")
        form = tk.Frame(editor, bg=PANEL)
        form.pack(fill="x", padx=16)
        field_labels = [
            ("date", "Date (YYYY-MM-DD)"),
            ("earnings", "Earnings (NT$)"),
            ("fuel", "Fuel (NT$)"),
            ("expenses", "Other expenses (NT$)"),
            ("hours", "Hours worked"),
        ]
        for index, (key, label) in enumerate(field_labels):
            form.grid_columnconfigure(index, weight=1, uniform="fields")
            column = tk.Frame(form, bg=PANEL)
            column.grid(row=0, column=index, sticky="ew", padx=(0, 10 if index < 4 else 0))
            add_label(column, label, size=9, color=MUTED).pack(anchor="w", pady=(0, 5))
            entry = tk.Entry(column, textvariable=self.inputs[key],
                             bg=PANEL_2, fg=TEXT, insertbackground=TEXT,
                             relief="flat", bd=0, font=(FONT, 11))
            entry.pack(fill="x", ipady=8)
            if key == "date":
                self.date_entry = entry
        actions = tk.Frame(editor, bg=PANEL)
        actions.pack(fill="x", padx=16, pady=14)
        flat_button(actions, "+ Add record", self.add_record,
                    bg=ACCENT, fg=SIDEBAR).pack(side="left", padx=(0, 8))
        flat_button(actions, "Save changes", self.update_record).pack(side="left", padx=(0, 8))
        flat_button(actions, "Delete selected", self.delete_record,
                    bg="#4A2634", fg="#FFD4D6").pack(side="left", padx=(0, 8))
        flat_button(actions, "Clear form", self.clear_form, bg=PANEL).pack(side="left")

    def show_page(self, page):
        self.current_page = page
        for widget in (self.dashboard, self.deliveries):
            widget.pack_forget()
        if page == "dashboard":
            self.dashboard.pack(fill="both", expand=True)
            self.page_title.config(text="Overview")
            self.subtitle.config(text="Your delivery earnings at a glance")
            self.draw_chart()
        else:
            self.deliveries.pack(fill="both", expand=True)
            self.page_title.config(text="Delivery records")
            self.subtitle.config(text="Add, edit, search and export your deliveries")
        for key, button in self.nav_buttons.items():
            button.configure(bg=PANEL_2 if key == page else SIDEBAR,
                             fg=ACCENT if key == page else MUTED)

    def open_new_record(self):
        self.show_page("deliveries")
        self.clear_form()
        self.date_entry.focus_set()

    def read_form(self):
        entry_date = self.inputs["date"].get().strip()
        try:
            date.fromisoformat(entry_date)
        except ValueError as error:
            raise ValueError("Enter a real date in YYYY-MM-DD format.") from error
        result = {"date": entry_date}
        for key in ("earnings", "fuel", "expenses", "hours"):
            try:
                value = float(self.inputs[key].get().strip())
            except ValueError as error:
                raise ValueError(f"{key.title()} must be a number.") from error
            if not math.isfinite(value) or value < 0:
                raise ValueError(f"{key.title()} must be zero or greater.")
            result[key] = value
        return result

    def add_record(self):
        try:
            self.db.add(self.read_form())
        except ValueError as error:
            messagebox.showwarning("Invalid entry", str(error))
            return
        except sqlite3.Error as error:
            messagebox.showerror("Database error", str(error))
            return
        self.refresh()
        self.clear_form()

    def update_record(self):
        if self.selected_id is None:
            messagebox.showinfo("No selection", "Select a record from the history table first.")
            return
        try:
            self.db.update(self.selected_id, self.read_form())
        except ValueError as error:
            messagebox.showwarning("Invalid entry", str(error))
            return
        except sqlite3.Error as error:
            messagebox.showerror("Database error", str(error))
            return
        self.refresh()
        self.clear_form()

    def delete_record(self):
        if self.selected_id is None:
            messagebox.showinfo("No selection", "Select a record from the history table first.")
            return
        if not messagebox.askyesno("Confirm deletion", "Permanently delete this record?"):
            return
        try:
            self.db.delete(self.selected_id)
        except sqlite3.Error as error:
            messagebox.showerror("Database error", str(error))
            return
        self.refresh()
        self.clear_form()

    def select_record(self, _event=None):
        selected = self.history_table.selection()
        if not selected:
            return
        selected_id = int(selected[0])
        record = next((r for r in self.last_records if r["id"] == selected_id), None)
        if record is None:
            return
        self.selected_id = selected_id
        for key in self.inputs:
            self.inputs[key].set(str(record[key]))

    def clear_form(self):
        self.selected_id = None
        for key, entry in self.inputs.items():
            entry.set(date.today().isoformat() if key == "date" else "0")
        for selection in self.history_table.selection():
            self.history_table.selection_remove(selection)

    def refresh(self):
        try:
            self.last_records = list(self.db.get_all())
        except sqlite3.Error as error:
            messagebox.showerror("Database error", str(error))
            return
        total_earnings = sum(r["earnings"] for r in self.last_records)
        total_expenses = sum(r["fuel"] + r["expenses"] for r in self.last_records)
        total_hours = sum(r["hours"] for r in self.last_records)
        net_profit = total_earnings - total_expenses
        for key, value in {
            "earnings": total_earnings,
            "expenses": total_expenses,
            "profit": net_profit,
            "hourly": net_profit / total_hours if total_hours else 0,
        }.items():
            self.stats[key].config(text=money(value))

        for item in self.recent_table.get_children():
            self.recent_table.delete(item)
        latest = sorted(self.last_records, key=lambda r: (r["date"], r["id"]), reverse=True)
        for record in latest[:5]:
            expenses = record["fuel"] + record["expenses"]
            self.recent_table.insert("", "end", iid=str(record["id"]), values=(
                record["date"], money(record["earnings"]), money(expenses),
                money(record["earnings"] - expenses)))
        self.refresh_history()
        self.draw_chart()

    def filtered_records(self):
        query = self.search.get().strip().lower()
        today = date.today()
        start_week = today - timedelta(days=today.weekday())
        records = []
        for r in self.last_records:
            if query and query not in r["date"].lower():
                continue
            try:
                d = date.fromisoformat(r["date"])
            except ValueError:
                continue
            if self.period.get() == "This week" and not (start_week <= d <= today):
                continue
            if self.period.get() == "This month" and not (d.year == today.year and d.month == today.month):
                continue
            records.append(r)
        return sorted(records, key=lambda r: (r["date"], r["id"]), reverse=True)

    def refresh_history(self):
        if not hasattr(self, "history_table"):
            return
        for item in self.history_table.get_children():
            self.history_table.delete(item)
        for record in self.filtered_records():
            net_profit = record["earnings"] - record["fuel"] - record["expenses"]
            self.history_table.insert("", "end", iid=str(record["id"]), values=(
                record["date"], money(record["earnings"]), money(record["fuel"]),
                money(record["expenses"]), f'{record["hours"]:g}', money(net_profit)))
        # The selected row may disappear when filters change.
        if self.selected_id is not None and not self.history_table.exists(str(self.selected_id)):
            self.selected_id = None

    def draw_chart(self):
        if not hasattr(self, "chart"):
            return
        canvas = self.chart
        canvas.delete("all")
        width = max(canvas.winfo_width(), 350)
        height = max(canvas.winfo_height(), 190)
        today = date.today()
        days = [today - timedelta(days=6 - i) for i in range(7)]
        totals = {day.isoformat(): 0.0 for day in days}
        for r in self.last_records:
            if r["date"] in totals:
                totals[r["date"]] += r["earnings"]
        max_value = max(totals.values(), default=0)
        left, right, top, bottom = 18, width - 18, 26, height - 36
        grid_height = bottom - top
        for proportion in (0, 0.5, 1):
            y = bottom - grid_height * proportion
            canvas.create_line(left, y, right, y, fill=BORDER, dash=(3, 4))
        space = (right - left) / 7
        bar_width = min(52, space * 0.52)
        for i, day in enumerate(days):
            amount = totals[day.isoformat()]
            x = left + space * (i + 0.5)
            normalized = amount / max_value if max_value > 0 else 0
            bar_height = max(0, (grid_height - 8) * normalized)
            if amount > 0:
                canvas.create_rectangle(x - bar_width / 2, bottom - bar_height,
                                        x + bar_width / 2, bottom, fill=ACCENT, outline="")
                if height >= 205:
                    canvas.create_text(x, max(top - 5, bottom - bar_height - 11),
                                       text=f"{amount:,.0f}", fill=TEXT,
                                       font=(FONT, 9))
            canvas.create_text(x, bottom + 17, text=day.strftime("%a"),
                               fill=MUTED, font=(FONT, 9))
        if not any(totals.values()):
            canvas.create_text(width / 2, (top + bottom) / 2,
                               text="No delivery earnings in the last 7 days",
                               fill=MUTED, font=(FONT, 11))

    def export_csv(self):
        records = self.filtered_records()
        if not records:
            messagebox.showinfo("Nothing to export", "No records match your current filter.")
            return
        dest = filedialog.asksaveasfilename(
            title="Export delivery records", defaultextension=".csv",
            filetypes=[("CSV files", "*.csv")], initialfile="delivery_earnings.csv")
        if not dest:
            return
        try:
            with open(dest, "w", encoding="utf-8-sig", newline="") as file:
                writer = csv.writer(file)
                writer.writerow(["ID", "Date", "Earnings (NTD)", "Fuel (NTD)",
                                 "Other expenses (NTD)", "Hours", "Net profit (NTD)"])
                for r in records:
                    writer.writerow([r["id"], r["date"], r["earnings"],
                                     r["fuel"], r["expenses"], r["hours"],
                                     r["earnings"] - r["fuel"] - r["expenses"]])
        except OSError as error:
            messagebox.showerror("Export failed", str(error))
            return
        messagebox.showinfo("Export complete", "CSV file saved successfully.")


def main():
    root = tk.Tk()
    db = None
    try:
        db = DeliveryDatabase()
        DashboardApp(root, db)
        root.mainloop()
    except (sqlite3.Error, OSError, ValueError) as error:
        messagebox.showerror("Could not open application", str(error))
    finally:
        if db is not None:
            db.close()
        root.destroy()


if __name__ == "__main__":
    main()
