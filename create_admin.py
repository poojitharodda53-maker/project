from app import init_db, get_db
from werkzeug.security import generate_password_hash
import getpass

init_db()

print("===== ADMIN ACCOUNT CREATION =====")

username = input("Enter Admin Username: ").strip()
password = input("Enter Admin Password: ")

if not username or len(password) < 8:
    print("Username is required and password must have 8 characters.")
else:
    with get_db() as con:
        try:
            con.execute("""
                INSERT INTO users (username, password, role)
                VALUES (?, ?, 'admin')
            """, (
                username,
                generate_password_hash(password)
            ))

            print("Admin Account Created Successfully!")

        except Exception:
            print("Username already exists or account creation failed.")