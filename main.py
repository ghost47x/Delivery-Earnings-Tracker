import json 
from pathlib import Path
from datetime import date


#file where we store delivery records

DATA_FILE = Path(__file__).with_name("deliveries.json")

def load_deliveries():
    if DATA_FILE.exists():
        with open(DATA_FILE, 'r') as file:
            return json.load(file)
    return []
def save_deliveries(deliveries):
    with open(DATA_FILE, 'w') as file:
        json.dump(deliveries, file, indent=4)
def get_number(message):
    while True:
        try:
            number = float(input(message))
            if number < 0:
                print(" enter a positive number")
                continue
            return number
        except ValueError:
            print('invalid input')
def add_delivery():
    print("\n--- ADD DELIVERY RECORD ---")

    today = date.today().isoformat()

    while True:
        entry_date = input(
            f"Date (YYYY-MM-DD) [{today}]: "
        ).strip() or today

        try:
            date.fromisoformat(entry_date)
            break
        except ValueError:
            print("Please enter a valid date.")

    earnings = get_number("Total earnings (NT$): ")
    fuel = get_number("Fuel expenses (NT$): ")
    expenses = get_number("Other expenses (NT$): ")
    hours = get_number("Hours worked: ")

    profit = earnings - fuel - expenses

    delivery = {
        "date": entry_date,
        "earnings": earnings,
        "fuel": fuel,
        "expenses": expenses,
        "hours": hours
    }

    deliveries = load_deliveries()
    deliveries.append(delivery)
    save_deliveries(deliveries)

    print("\nDelivery saved successfully!")
    print(f"Net profit: NT${profit:.2f}")


def view_deliveries():
    deliveries = load_deliveries()

    if not deliveries:
        print("\nNo delivery records found.")
        return

    print("\n--- DELIVERY HISTORY ---")

    for index, delivery in enumerate(deliveries, start=1):
        profit = (
            delivery["earnings"]
            - delivery["fuel"]
            - delivery["expenses"]
        )

        print(f"\nRecord #{index}")
        print(f"Date: {delivery['date']}")
        print(f"Earnings: NT${delivery['earnings']:.2f}")
        print(f"Fuel: NT${delivery['fuel']:.2f}")
        print(f"Other expenses: NT${delivery['expenses']:.2f}")
        print(f"Hours: {delivery['hours']}")
        print(f"Net profit: NT${profit:.2f}")


def show_summary():
    deliveries = load_deliveries()

    if not deliveries:
        print("\nNo data available.")
        return

    total_earnings = sum(d["earnings"] for d in deliveries)
    total_fuel = sum(d["fuel"] for d in deliveries)
    total_expenses = sum(d["expenses"] for d in deliveries)
    total_hours = sum(d["hours"] for d in deliveries)

    net_profit = total_earnings - total_fuel - total_expenses

    hourly_profit = (
        net_profit / total_hours if total_hours > 0 else 0
    )

    print("\n====== EARNINGS SUMMARY ======")
    print(f"Total earnings: NT${total_earnings:.2f}")
    print(f"Fuel expenses: NT${total_fuel:.2f}")
    print(f"Other expenses: NT${total_expenses:.2f}")
    print(f"Net profit: NT${net_profit:.2f}")
    print(f"Total hours: {total_hours:.1f}")
    print(f"Profit per hour: NT${hourly_profit:.2f}")


def edit_delivery():
    deliveries = load_deliveries()

    if not deliveries:
        print("\nNo records available to edit.")
        return

    view_deliveries()

    try:
        number = int(input("\nEnter record number to edit: "))
    except ValueError:
        print("Please enter a valid record number.")
        return

    if number < 1 or number > len(deliveries):
        print("Record not found.")
        return

    delivery = deliveries[number - 1]

    print("\n--- EDIT DELIVERY ---")
    print("Enter the new information.")

    delivery["earnings"] = get_number("New earnings (NT$): ")
    delivery["fuel"] = get_number("New fuel expenses (NT$): ")
    delivery["expenses"] = get_number("New other expenses (NT$): ")
    delivery["hours"] = get_number("New hours worked: ")

    save_deliveries(deliveries)

    print("\nDelivery updated successfully!")

def delete_delivery():
    deliveries = load_deliveries()

    if not deliveries:
        print("\nNo records available to delete.")
        return

    view_deliveries()

    try:
        number = int(input("\nEnter record number to delete: "))
    except ValueError:
        print("Please enter a valid record number.")
        return

    if number < 1 or number > len(deliveries):
        print("Record not found.")
        return

    confirm = input(
        f"Are you sure you want to delete record #{number}? (yes/no): "
    ).strip().lower()

    if confirm == "yes":
        deliveries.pop(number - 1)
        save_deliveries(deliveries)
        print("\nDelivery deleted successfully!")
    else:
        print("\nDeletion cancelled.")






def main():
    while True:
        print("\n==============================")
        print("  DELIVERY EARNINGS TRACKER")
        print("==============================")
        print("1. Add delivery record")
        print("2. View delivery history")
        print("3. View earnings summary")
        print("4. Edit delivery record")
        print("5. Delete delivery record")
        print("6. Exit")

        choice = input("\nChoose an option: ").strip()
        print(f"DEBUG: You selected option {choice!r}")

        if choice == "1":
            add_delivery()
        elif choice == "2":
            view_deliveries()
        elif choice == "3":
            show_summary()
        elif choice == "4":
            edit_delivery()
        elif choice == "5":
            delete_delivery()
        elif choice == "6":
            print("Goodbye!")
            break
        else:
            print("Invalid option. Try again.")


if __name__ == "__main__":
    main()
