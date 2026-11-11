"""
Personal Budget & Financial Planning Tool
-----------------------------------------
A command-line app that:
  * records monthly income and bills (commitments)
  * tracks income versus commitments and the monthly surplus
  * lets you set savings goals with a target amount and deadline
  * allocates the monthly surplus across savings, investments, goals and
    spending money, based on percentages you choose

Data is saved to budget_data.json in the same folder, so it persists
between sessions. Uses the Python standard library only (Python 3.8+).

Run with:  python budget_planner.py
"""

import json
from datetime import date
from pathlib import Path

DATA_FILE = Path(__file__).with_name("budget_data.json")

DEFAULT_DATA = {
    "income": [],      # {"name": str, "amount": float}
    "bills": [],       # {"name": str, "amount": float, "due_day": int}
    "goals": [],       # {"name": str, "target": float, "saved": float, "deadline": "YYYY-MM"}
    "allocation": {    # % of monthly surplus; must total 100
        "savings": 30,
        "investments": 30,
        "goals": 30,
        "spending": 10,
    },
}


# ---------------------------------------------------------------- storage
def load_data():
    if DATA_FILE.exists():
        try:
            with open(DATA_FILE, encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            print("Could not read saved data, starting fresh.")
    return json.loads(json.dumps(DEFAULT_DATA))  # deep copy


def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


# ---------------------------------------------------------------- input helpers
def ask_text(prompt):
    while True:
        value = input(prompt).strip()
        if value:
            return value
        print("  Please enter a value.")


def ask_float(prompt, minimum=0.0):
    while True:
        try:
            value = float(input(prompt).replace("£", "").replace(",", "").strip())
            if value < minimum:
                print(f"  Must be at least {minimum}.")
                continue
            return round(value, 2)
        except ValueError:
            print("  Please enter a number.")


def ask_int(prompt, low, high):
    while True:
        try:
            value = int(input(prompt).strip())
            if low <= value <= high:
                return value
            print(f"  Enter a whole number from {low} to {high}.")
        except ValueError:
            print("  Please enter a whole number.")


def ask_month(prompt):
    """Ask for a YYYY-MM month in the future."""
    while True:
        text = input(prompt).strip()
        try:
            year, month = map(int, text.split("-"))
            if not 1 <= month <= 12:
                raise ValueError
            if (year, month) <= (date.today().year, date.today().month):
                print("  The deadline must be a future month.")
                continue
            return f"{year:04d}-{month:02d}"
        except ValueError:
            print("  Use the format YYYY-MM, e.g. 2027-06.")


# ---------------------------------------------------------------- calculations
def total_income(data):
    return sum(i["amount"] for i in data["income"])


def total_bills(data):
    return sum(b["amount"] for b in data["bills"])


def months_until(deadline):
    year, month = map(int, deadline.split("-"))
    today = date.today()
    return max(1, (year - today.year) * 12 + (month - today.month))


def monthly_needed(goal):
    remaining = max(0.0, goal["target"] - goal["saved"])
    return remaining / months_until(goal["deadline"])


def money(value):
    return f"£{value:,.2f}"


# ---------------------------------------------------------------- actions
def add_income(data):
    name = ask_text("Income source (e.g. Salary): ")
    amount = ask_float("Monthly amount after tax (£): ")
    data["income"].append({"name": name, "amount": amount})
    print(f"Added {name}: {money(amount)}")


def add_bill(data):
    name = ask_text("Bill name (e.g. Rent): ")
    amount = ask_float("Monthly amount (£): ")
    due_day = ask_int("Day of month it is due (1-28): ", 1, 28)
    data["bills"].append({"name": name, "amount": amount, "due_day": due_day})
    print(f"Added {name}: {money(amount)} due on day {due_day}")


def add_goal(data):
    name = ask_text("Goal name (e.g. House deposit): ")
    target = ask_float("Target amount (£): ", minimum=1)
    saved = ask_float("Already saved towards it (£): ")
    deadline = ask_month("Deadline (YYYY-MM): ")
    data["goals"].append(
        {"name": name, "target": target, "saved": saved, "deadline": deadline}
    )
    print(f"Added goal {name}: needs {money(monthly_needed(data['goals'][-1]))} per month")


def update_goal_savings(data):
    if not data["goals"]:
        print("No goals yet.")
        return
    for n, g in enumerate(data["goals"], 1):
        print(f"  {n}. {g['name']} ({money(g['saved'])} of {money(g['target'])})")
    choice = ask_int("Which goal? ", 1, len(data["goals"]))
    amount = ask_float("Amount to add (£): ")
    data["goals"][choice - 1]["saved"] += amount
    print("Updated.")


def set_allocation(data):
    print("Split your monthly surplus across four pots. Must total 100%.")
    while True:
        new = {
            "savings": ask_int("  % to savings account: ", 0, 100),
            "investments": ask_int("  % to investments: ", 0, 100),
            "goals": ask_int("  % to goals: ", 0, 100),
            "spending": ask_int("  % to spending money: ", 0, 100),
        }
        if sum(new.values()) == 100:
            data["allocation"] = new
            print("Allocation saved.")
            return
        print(f"  That totals {sum(new.values())}%, it must be exactly 100%. Try again.")


def show_summary(data):
    income, bills = total_income(data), total_bills(data)
    surplus = income - bills
    print("\n=== INCOME vs COMMITMENTS ===")
    print("Income")
    for i in data["income"]:
        print(f"  {i['name']:<25}{money(i['amount']):>12}")
    print(f"  {'Total income':<25}{money(income):>12}")
    print("Bills (by due date)")
    for b in sorted(data["bills"], key=lambda x: x["due_day"]):
        print(f"  {b['name']:<25}{money(b['amount']):>12}   due day {b['due_day']}")
    print(f"  {'Total bills':<25}{money(bills):>12}")
    print("-" * 40)
    print(f"  {'Monthly surplus':<25}{money(surplus):>12}")
    if income > 0:
        share = bills / income * 100
        print(f"  Bills take up {share:.0f}% of your income.")
        if share > 70:
            print("  Warning: commitments are above 70% of income.")
    if surplus < 0:
        print(f"  Warning: you are {money(-surplus)} short each month.")


def show_plan(data):
    surplus = total_income(data) - total_bills(data)
    print("\n=== MONTHLY ALLOCATION PLAN ===")
    if surplus <= 0:
        print("There is no surplus to allocate. Reduce bills or increase income first.")
        return
    alloc = data["allocation"]
    pots = {name: surplus * pct / 100 for name, pct in alloc.items()}
    print(f"Surplus to allocate: {money(surplus)}")
    for name, pct in alloc.items():
        print(f"  {name.capitalize():<14}{pct:>3}%   {money(pots[name]):>12}")

    print("\n=== GOAL PROGRESS ===")
    if not data["goals"]:
        print("No goals set.")
        return
    needs = [monthly_needed(g) for g in data["goals"]]
    required = sum(needs)
    pot = pots["goals"]
    ratio = 1.0 if required == 0 else min(1.0, pot / required)
    for g, need in zip(data["goals"], needs):
        funded = need * ratio
        pct_done = g["saved"] / g["target"] * 100
        status = "on track" if ratio >= 1 else f"short by {money(need - funded)}/month"
        print(f"  {g['name']}: {pct_done:.0f}% saved ({money(g['saved'])} of {money(g['target'])}), "
              f"by {g['deadline']}")
        print(f"      needs {money(need)}/month, funded {money(funded)} - {status}")
    if ratio < 1:
        print(f"\n  Your goals pot ({money(pot)}) is less than the {money(required)} "
              f"needed. Increase the goals % or extend a deadline.")
    elif pot > required:
        print(f"\n  Goals are fully funded with {money(pot - required)} to spare. "
              f"Consider moving it to savings or investments.")


def load_demo(data):
    data["income"] = [{"name": "Salary", "amount": 2100.0}]
    data["bills"] = [
        {"name": "Rent", "amount": 750.0, "due_day": 1},
        {"name": "Council tax", "amount": 120.0, "due_day": 5},
        {"name": "Energy", "amount": 95.0, "due_day": 10},
        {"name": "Phone and broadband", "amount": 45.0, "due_day": 15},
        {"name": "Travel", "amount": 80.0, "due_day": 20},
        {"name": "Subscriptions", "amount": 25.0, "due_day": 25},
    ]
    next_year = date.today().year + 1
    data["goals"] = [
        {"name": "House deposit", "target": 8000.0, "saved": 1500.0,
         "deadline": f"{next_year + 1}-06"},
        {"name": "Holiday", "target": 1200.0, "saved": 200.0,
         "deadline": f"{next_year}-07"},
    ]
    print("Demo data loaded (not saved until you choose Save and exit).")


# ---------------------------------------------------------------- menu
MENU = """
===== PERSONAL BUDGET & FINANCIAL PLANNING TOOL =====
 1. Add income
 2. Add bill
 3. Add savings goal
 4. Add money to a goal
 5. Set surplus allocation (%)
 6. Show income vs commitments
 7. Show allocation plan and goal progress
 8. Load demo data
 9. Save and exit
"""

ACTIONS = {
    "1": add_income,
    "2": add_bill,
    "3": add_goal,
    "4": update_goal_savings,
    "5": set_allocation,
    "6": show_summary,
    "7": show_plan,
    "8": load_demo,
}


def main():
    data = load_data()
    while True:
        print(MENU)
        try:
            choice = input("Choose an option: ").strip()
        except EOFError:
            choice = "9"
        if choice == "9":
            save_data(data)
            print("Saved. Goodbye.")
            break
        action = ACTIONS.get(choice)
        if action:
            action(data)
            save_data(data)
        else:
            print("Please choose a number from 1 to 9.")


if __name__ == "__main__":
    main()
