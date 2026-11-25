import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash

DATABASE = "project.db"


def get_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    # Users table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL
        )
    """)

    # Question papers table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS papers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            subject TEXT NOT NULL,
            year INTEGER,
            unit TEXT,
            filename TEXT
        )
    """)

    # Questions table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            paper_id INTEGER,
            question TEXT NOT NULL,
            unit TEXT,
            question_number INTEGER,
            FOREIGN KEY (paper_id) REFERENCES papers(id)
        )
    """)

    conn.commit()
    conn.close()


def create_user(username, password, role):
    if role not in ("admin", "student"):
        return False

    conn = get_connection()

    try:
        hashed_password = generate_password_hash(password)

        conn.execute("""
            INSERT INTO users (username, password, role)
            VALUES (?, ?, ?)
        """, (username, hashed_password, role))

        conn.commit()
        return True

    except sqlite3.IntegrityError:
        return False

    finally:
        conn.close()


def verify_user(username, password, role):
    conn = get_connection()

    user = conn.execute("""
        SELECT * FROM users
        WHERE username = ? AND role = ?
    """, (username, role)).fetchone()

    conn.close()

    if user and check_password_hash(user["password"], password):
        return dict(user)

    return None


def add_paper(subject, year, unit, filename):
    conn = get_connection()

    cursor = conn.execute("""
        INSERT INTO papers (subject, year, unit, filename)
        VALUES (?, ?, ?, ?)
    """, (subject, year, unit, filename))

    paper_id = cursor.lastrowid

    conn.commit()
    conn.close()

    return paper_id


def add_question(paper_id, question, unit, question_number):
    conn = get_connection()

    conn.execute("""
        INSERT INTO questions
        (paper_id, question, unit, question_number)
        VALUES (?, ?, ?, ?)
    """, (paper_id, question, unit, question_number))

    conn.commit()
    conn.close()


def get_units():
    return [
        "Unit 1 - Discrete Structures and Optimization",
        "Unit 2 - Computer System Architecture",
        "Unit 3 - Programming Languages and Computer Graphics",
        "Unit 4 - Database Management Systems",
        "Unit 5 - System Software and Operating Systems",
        "Unit 6 - Software Engineering",
        "Unit 7 - Data Structures and Algorithms",
        "Unit 8 - Theory of Computation and Compilers",
        "Unit 9 - Data Communication and Computer Networks",
        "Unit 10 - Artificial Intelligence"
    ]


init_db()