import csv
import os

FILENAME = "students.csv"

# -----------------------------
# 1) Create CSV if not found
# -----------------------------
def initialize_csv():
    if not os.path.exists(FILENAME):
        with open(FILENAME, "w", newline="", encoding="utf-8") as file:
            writer = csv.writer(file)
            writer.writerow(["Username", "Student_Name", "ID", "Role", "Status"])


# -----------------------------
# 2) Login System
# -----------------------------
def login():
    print("===== LOGIN =====")
    username = input("Enter username: ")
    password = input("Enter password: ")

    # Example users (username: {password, role})
    users = {
        "admin": {"password": "passwordadmin123", "role": "admin"},
        "teacher": {"password": "abc", "role": "admin"},
        "mohamed": {"password": "555", "role": "student"},
        "ali": {"password": "777", "role": "student"}
    }

    if username in users and users[username]["password"] == password:
        print("\n✔ Login successful!\n")
        return username, users[username]["role"]
    else:
        print("\n❌ Invalid login. Try again.\n")
        return login()


# -----------------------------
# 3) Add New User (Admin Only)
# -----------------------------
def add_user():
    print("=== Add New User ===")

    username = input("Username: ")
    student_name = input("Student Name: ")
    student_id = input("ID: ")

    # Role validation
    while True:
        role = input("Role (admin/student): ").lower()
        if role in ["admin", "student"]:
            break
        print("❌ Invalid role. Enter admin or student.")

    # Status validation
    while True:
        status = input("Status (active/inactive): ").lower()
        if status in ["active", "inactive"]:
            break
        print("❌ Invalid status. Enter active or inactive.")

    # Save to CSV
    with open(FILENAME, "a", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow([username, student_name, student_id, role, status])

    print("\n✔ User added successfully!\n")


# -----------------------------
# MAIN PROGRAM
# -----------------------------
initialize_csv()
logged_user, role = login()

if role != "admin":
    print("❌ Access denied. Only admins can add new users.")
else:
    while True:
        add_user()
        again = input("Add another user? (y/n): ").lower()
        if again != "y":
            break

print("\nGoodbye!")
