from app import init_db, get_db
from werkzeug.security import generate_password_hash

init_db()

username = input("Enter Admin Username: ").strip()
new_password = input("Enter New Admin Password: ")

if len(new_password) < 8:
    print("Password must contain at least 8 characters.")
else:
    with get_db() as con:
        result = con.execute("""
            UPDATE users
            SET password = ?
            WHERE username = ? AND role = 'admin'
        """, (generate_password_hash(new_password), username))

        if result.rowcount > 0:
            print("Admin Password Updated Successfully!")
        else:
            print("Admin Username Not Found!")