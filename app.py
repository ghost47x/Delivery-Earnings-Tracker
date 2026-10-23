import json
import math
import tkinter as tk
from datetime import date
from pathlib import Path
from tkinter import messagebox, ttk

DATA_FILE = Path(__file__).with_name("deliveries.json")


class DeliveryApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Delivery Earnings Tracker")
        self.root.geometry("950x620")
        self.root.minsize(780, 520)

        self.records = self.load_records()
        self.selected_index = None
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

        inputs = [
            ("Date (YYYY-MM-DD)", "date"),
            ("Earnings (NT$)", "earnings"),
            ("Fuel (NT$)", "fuel"),
            ("Other expenses (NT$)", "expenses"),
            ("Hours worked", "hours"),
        ]
        for i, (label, key) in enumerate(inputs):
            row, column = divmod(i, 2)
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

    def load_records(self):
        if not DATA_FILE.exists():
            return []
        with DATA_FILE.open("r", encoding="utf-8") as file:
            return json.load(file)

    def save_records(self):
        with DATA_FILE.open("w", encoding="utf-8") as file:
            json.dump(self.records, file, indent=4)

    def read_form(self):
        entered_date = self.fields["date"].get().strip()
        try:
            date.fromisoformat(entered_date)
        except ValueError:
            raise ValueError("Enter a valid date like 2026-10-23.")

        values = {}
        for key in ("earnings", "fuel", "expenses", "hours"):
            try:
                value = float(self.fields[key].get().strip())
            except ValueError:
                raise ValueError(f"{key.title()} must be a number.")
            if not math.isfinite(value) or value < 0:
                raise ValueError(f"{key.title()} must be zero or greater.")
            values[key] = value
        return {"date": entered_date, **values}

    def add_record(self):
        try:
            record = self.read_form()
        except ValueError as error:
            messagebox.showwarning("Invalid entry", str(error))
            return
        self.records.append(record)
        self.save_records()
        self.refresh()
        self.clear_form()

    def update_record(self):
        if self.selected_index is None:
            messagebox.showinfo("Select a record", "Click a row in the table first.")
            return
        try:
            record = self.read_form()
        except ValueError as error:
            messagebox.showwarning("Invalid entry", str(error))
            return
        self.records[self.selected_index] = record
        self.save_records()
        self.refresh()
        self.clear_form()

    def delete_record(self):
        if self.selected_index is None:
            messagebox.showinfo("Select a record", "Click a row in the table first.")
            return
        if not messagebox.askyesno("Confirm deletion", "Delete the selected record?"):
            return
        self.records.pop(self.selected_index)
        self.save_records()
        self.refresh()
        self.clear_form()

    def on_select(self, event):
        selected = self.table.selection()
        if not selected:
            return
        self.selected_index = int(selected[0])
        record = self.records[self.selected_index]
        for key in self.fields:
            self.fields[key].set(str(record[key]))

    def clear_form(self):
        for key, variable in self.fields.items():
            variable.set(date.today().isoformat() if key == "date" else "0")
        self.selected_index = None
        for item in self.table.selection():
            self.table.selection_remove(item)

    def refresh(self):
        for item in self.table.get_children():
            self.table.delete(item)
        total_earnings = total_expenses = total_hours = 0.0
        for index, record in enumerate(self.records):
            earnings = float(record["earnings"])
            fuel = float(record["fuel"])
            other = float(record["expenses"])
            hours = float(record["hours"])
            profit = earnings - fuel - other
            total_earnings += earnings
            total_expenses += fuel + other
            total_hours += hours
            self.table.insert("", "end", iid=str(index), values=(
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
        self.selected_index = None


if __name__ == "__main__":
    root = tk.Tk()
    DeliveryApp(root)
    root.mainloop()
