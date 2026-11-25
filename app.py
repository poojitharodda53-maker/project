import os
import re
import uuid
import sqlite3
from datetime import datetime
import fitz

from flask import (
    Flask, render_template, request,
    redirect, url_for, flash, session
)

from werkzeug.security import (
    generate_password_hash,
    check_password_hash
)

from werkzeug.utils import secure_filename
from pypdf import PdfReader

from analyzer import (
    UNITS,
    classify_question,
    extract_questions,
    extract_answer_key
)


# ==========================================
# 1. FLASK CONFIGURATION
# ==========================================

app = Flask(__name__)
app.secret_key = "ugc_net_secret_key"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
DATABASE = os.path.join(BASE_DIR, "questions.db")

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = 25 * 1024 * 1024


# ==========================================
# 2. DATABASE CONNECTION
# ==========================================

def get_db():
    con = sqlite3.connect(DATABASE)
    con.row_factory = sqlite3.Row
    return con


# ==========================================
# 3. DATABASE INITIALIZATION
# ==========================================

def init_db():

    with get_db() as con:

        con.execute("""
            CREATE TABLE IF NOT EXISTS papers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT,
                exam_year TEXT,
                exam_session TEXT,
                uploaded_at TEXT
            )
        """)

        con.execute("""
            CREATE TABLE IF NOT EXISTS questions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                paper_id INTEGER,
                original_no TEXT,
                question TEXT,
                option_a TEXT DEFAULT '',
                option_b TEXT DEFAULT '',
                option_c TEXT DEFAULT '',
                option_d TEXT DEFAULT '',
                unit_no INTEGER,
                unit_name TEXT,
                confidence INTEGER,
                FOREIGN KEY(paper_id) REFERENCES papers(id)
            )
        """)

        existing_columns = [
            row["name"]
            for row in con.execute(
                "PRAGMA table_info(questions)"
            ).fetchall()
        ]
        for column in [
    "option_a",
    "option_b",
    "option_c",
    "option_d",
    "correct_answer"
]:
        
            if column not in existing_columns:
                con.execute(
                    f"ALTER TABLE questions "
                    f"ADD COLUMN {column} TEXT DEFAULT ''"
                )

        con.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                role TEXT NOT NULL
            )
        """)


# ==========================================
# 4. LOGIN
# ==========================================

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        username = request.form.get(
            "username", ""
        ).strip()

        password = request.form.get("password", "")
        role = request.form.get("role", "")

        with get_db() as con:

            user = con.execute("""
                SELECT * FROM users
                WHERE username = ? AND role = ?
            """, (username, role)).fetchone()

        if user and check_password_hash(
            user["password"], password
        ):

            session["user_id"] = user["id"]
            session["username"] = user["username"]
            session["role"] = user["role"]

            return redirect(url_for("dashboard"))

        flash("Invalid username or password.")

    return render_template("login.html")


# ==========================================
# 5. DASHBOARD
# ==========================================

@app.route("/dashboard")
def dashboard():

    if "user_id" not in session:
        return redirect(url_for("login"))

    return render_template("dashboard.html")


# ==========================================
# 6. LOGOUT
# ==========================================

@app.route("/logout")
def logout():

    session.clear()
    flash("Logged out successfully.")

    return redirect(url_for("login"))


# ==========================================
# 7. HOME PAGE
# ==========================================

@app.route("/")
def home():

    with get_db() as con:

        total = con.execute(
            "SELECT COUNT(*) FROM questions"
        ).fetchone()[0]

        unclassified = con.execute("""
            SELECT COUNT(*)
            FROM questions
            WHERE unit_no IS NULL
               OR unit_no < 1
               OR unit_no > 10
        """).fetchone()[0]

        papers_count = con.execute(
            "SELECT COUNT(*) FROM papers"
        ).fetchone()[0]

        rows = con.execute("""
            SELECT unit_no, COUNT(*) AS total
            FROM questions
            GROUP BY unit_no
        """).fetchall()

        counts = {
            row["unit_no"]: row["total"]
            for row in rows
        }

    print("TOTAL QUESTIONS:", total)
    print("UNCLASSIFIED QUESTIONS:", unclassified)
    print("CLASSIFIED QUESTIONS:", total - unclassified)

    return render_template(
        "index.html",
        units=UNITS,
        counts=counts,
        total=total,
        papers=papers_count
    )


# ==========================================
# 8. STUDENT REGISTRATION
# ==========================================

@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        username = request.form.get(
            "username", ""
        ).strip()

        password = request.form.get("password", "")

        confirm_password = request.form.get(
            "confirm_password", ""
        )

        if not username or not password:
            flash("Please enter all required details.")
            return redirect(url_for("register"))

        if password != confirm_password:
            flash("Passwords do not match.")
            return redirect(url_for("register"))

        if len(password) < 8:
            flash("Password must contain at least 8 characters.")
            return redirect(url_for("register"))

        with get_db() as con:

            try:

                con.execute("""
                    INSERT INTO users
                    (username, password, role)
                    VALUES (?, ?, 'student')
                """, (
                    username,
                    generate_password_hash(password)
                ))

                flash(
                    "Registration successful! Please login."
                )

                return redirect(url_for("login"))

            except sqlite3.IntegrityError:

                flash("Username already exists.")

    return render_template("register.html")


# ==========================================
# 9. PDF UPLOAD
# ==========================================

@app.route("/upload", methods=["GET", "POST"])
def upload():

    if request.method == "POST":

        file = request.files.get("pdf_file")

        year = request.form.get("exam_year", "")
        exam_session = request.form.get("exam_session", "")

        if not file or file.filename == "":
            flash("Please select a PDF file.")
            return redirect(url_for("upload"))

        if not file.filename.lower().endswith(".pdf"):
            flash("Only PDF files are allowed.")
            return redirect(url_for("upload"))

        filename = secure_filename(file.filename)

        if not filename:
            flash("Invalid file name.")
            return redirect(url_for("upload"))

        saved_name = (
            datetime.now().strftime("%Y%m%d%H%M%S%f")
            + "_" + filename
        )

        filepath = os.path.join(UPLOAD_FOLDER, saved_name)
        file.save(filepath)

        try:

            doc = fitz.open(filepath)

            text_parts = []
            common_passage = ""
            answer_key_text = ""
            answer_key_found = False

            for page in doc:

                page_text = page.get_text("text") or ""

                # Start collecting Answer Key
                if re.search(r"(?i)\bAnswer\s+Key\b", page_text):
                    answer_key_found = True

                # Collect answer key pages
                if answer_key_found:

                    if re.search(
                        r"(?i)Hints\s*&\s*Solutions",
                        page_text
                    ):
                        break

                    answer_key_text += "\n" + page_text
                    continue

                # Read question pages in two-column order
                words = page.get_text("words")
                middle_x = page.rect.width / 2

                columns = [[], []]

                for word in words:

                    x0, y0, x1, y1, word_text = word[:5]

                    if not word_text.strip():
                        continue

                    center_x = (x0 + x1) / 2
                    center_y = (y0 + y1) / 2

                    column_no = 0 if center_x < middle_x else 1

                    columns[column_no].append(
                        (center_y, x0, word_text)
                    )

                for column_words in columns:

                    column_words.sort(
                        key=lambda item: (item[0], item[1])
                    )

                    lines = []

                    for y, x, word_text in column_words:

                        if not lines or abs(lines[-1]["y"] - y) > 3:
                            lines.append({
                                "y": y,
                                "items": []
                            })

                        lines[-1]["items"].append((x, word_text))

                        lines[-1]["y"] = sum(
                            item[0]
                            for item in lines[-1]["items"]
                        ) / len(lines[-1]["items"])

                    column_text = "\n".join(
                        " ".join(
                            word
                            for x, word in sorted(
                                line["items"],
                                key=lambda item: item[0]
                            )
                        )
                        for line in lines
                    )

                    text_parts.append(column_text)

                    if (
                        "Directions" in column_text
                        and "96" in column_text
                        and "100" in column_text
                    ):
                        common_passage = column_text

            doc.close()

           

            if not answer_key_found:
                raise ValueError(
                    "Answer Key section was not detected."
                )

            text = "\n".join(text_parts)

            if not text.strip():
                raise ValueError(
                    "No readable question text found in PDF."
                )

            extracted = extract_questions(text)
                        # Extract answers from PDF Answer Key
            answer_key = extract_answer_key(answer_key_text)

            print("TOTAL ANSWERS FOUND:", len(answer_key))

            # Match each question with its correct answer
            for q in extracted:

                q["correct_answer"] = answer_key.get(
                    q["number"], ""
                )

            print(
                "QUESTIONS WITH ANSWERS:",
                sum(
                    1 for q in extracted
                    if q["correct_answer"]
                )
            )

            # Attach shared passage to Questions 96-100
            if common_passage:

                for q in extracted:

                    if 96 <= q["number"] <= 100:

                        q["question"] = (
                            common_passage
                            + "\n"
                            + q["question"]
                        )

            if not extracted:
                raise ValueError(
                    "Questions not detected. Check analyzer.py."
                )

            with get_db() as con:

                cursor = con.execute("""
                    INSERT INTO papers (
                        filename,
                        exam_year,
                        exam_session,
                        uploaded_at
                    )
                    VALUES (?, ?, ?, ?)
                """, (
                    filename,
                    year,
                    exam_session,
                    datetime.now().strftime("%Y-%m-%d")
                ))

                paper_id = cursor.lastrowid

                for q in extracted:

                    options = q.get("options", {})

                    classification_text = " ".join([
                        q.get("question", ""),
                        options.get("A", ""),
                        options.get("B", ""),
                        options.get("C", ""),
                        options.get("D", "")
                    ])

                    unit_no, confidence = classify_question(
                        classification_text
                    )

                    unit_name = (
                        UNITS[unit_no - 1]["name"]
                        if unit_no
                        else "Unclassified"
                    )

                    con.execute("""
                        INSERT INTO questions (
                            paper_id,
                            original_no,
                            question,
                            option_a,
                            option_b,
                            option_c,
                            option_d,
                            correct_answer,
                            unit_no,
                            unit_name,
                            confidence
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        paper_id,
                        q["number"],
                        q["question"],
                        options.get("A", ""),
                        options.get("B", ""),
                        options.get("C", ""),
                        options.get("D", ""),
                        q.get("correct_answer", ""),
                        unit_no,
                        unit_name,
                        confidence
                    ))

            flash(
                str(len(extracted))
                + " questions extracted successfully!"
            )

            return redirect(
                url_for("paper_detail", paper_id=paper_id)
            )

        except Exception as error:

            if os.path.exists(filepath):
                os.remove(filepath)

            flash("PDF Error: " + str(error))

            return redirect(url_for("upload"))

    return render_template("upload.html")


# ==========================================
# 10. UNIT-WISE QUESTIONS
# ==========================================

@app.route("/unit/<int:unit_no>")
def unit_detail(unit_no):

    if unit_no < 1 or unit_no > 10:
        return redirect(url_for("home"))

    unit = UNITS[unit_no - 1]

    with get_db() as con:

        questions = con.execute("""
            SELECT
                q.*,
                p.exam_year,
                p.exam_session
            FROM questions q
            JOIN papers p ON q.paper_id = p.id
            WHERE q.unit_no = ?
            ORDER BY q.id
        """, (unit_no,)).fetchall()

    return render_template(
        "unit.html",
        unit=unit,
        unit_no=unit_no,
        questions=questions,
        total=len(questions),
        repeated=[]
    )


# ==========================================
# 11. PAPER DETAILS
# ==========================================

@app.route("/paper/<int:paper_id>")
def paper_detail(paper_id):

    with get_db() as con:

        paper = con.execute("""
            SELECT * FROM papers
            WHERE id = ?
        """, (paper_id,)).fetchone()

        questions = con.execute("""
            SELECT * FROM questions
            WHERE paper_id = ?
            ORDER BY id
        """, (paper_id,)).fetchall()

    if not paper:
        flash("Paper not found.")
        return redirect(url_for("home"))

    print("TOTAL QUESTIONS:", len(questions))
    print("FIRST TWO QUESTIONS:", [
        dict(q) for q in questions[:2]
    ])

    return render_template(
        "paper.html",
        paper=paper,
        questions=questions,
        units=UNITS
    )


# ==========================================
# 12. REASSIGN QUESTION UNIT
# ==========================================

@app.route("/reassign/<int:question_id>", methods=["POST"])
def reassign(question_id):

    try:
        unit_no = int(
            request.form.get("unit_no", 0)
        )
    except (ValueError, TypeError):
        unit_no = 0

    if unit_no not in range(1, 11):
        unit_no = 0

    unit_name = (
        UNITS[unit_no - 1]["name"]
        if unit_no
        else "Unclassified"
    )

    with get_db() as con:

        con.execute("""
            UPDATE questions
            SET
                unit_no = ?,
                unit_name = ?,
                confidence = 1
            WHERE id = ?
        """, (
            unit_no,
            unit_name,
            question_id
        ))

        result = con.execute("""
            SELECT paper_id
            FROM questions
            WHERE id = ?
        """, (question_id,)).fetchone()

    if result:
        return redirect(
            url_for(
                "paper_detail",
                paper_id=result["paper_id"]
            )
        )

    return redirect(url_for("home"))


# ==========================================
# 13. DELETE PAPER
# ==========================================

@app.route("/delete-paper/<int:paper_id>", methods=["POST"])
def delete_paper(paper_id):

    with get_db() as con:

        con.execute(
            "DELETE FROM questions WHERE paper_id = ?",
            (paper_id,)
        )

        con.execute(
            "DELETE FROM papers WHERE id = ?",
            (paper_id,)
        )

    flash("Paper deleted successfully.")

    return redirect(url_for("papers"))


# ==========================================
# 14. ALL UPLOADED PAPERS
# ==========================================

@app.route("/papers")
def papers():

    with get_db() as con:

        data = con.execute("""
            SELECT
                p.*,
                COUNT(q.id) AS total
            FROM papers p
            LEFT JOIN questions q
                ON p.id = q.paper_id
            GROUP BY p.id
            ORDER BY p.id DESC
        """).fetchall()

    return render_template(
        "papers.html",
        papers=data
    )


# ==========================================
# 15. ANALYSIS
# ==========================================

@app.route("/analysis")
def analysis():

    with get_db() as con:

        unit_data = con.execute("""
            SELECT
                unit_no,
                unit_name,
                COUNT(*) AS total
            FROM questions
            GROUP BY unit_no, unit_name
        """).fetchall()

        year_data = con.execute("""
            SELECT
                p.exam_year,
                COUNT(q.id) AS total
            FROM papers p
            LEFT JOIN questions q
                ON p.id = q.paper_id
            GROUP BY p.exam_year
        """).fetchall()

    return render_template(
        "analysis.html",
        units=UNITS,
        unit_data=unit_data,
        year_data=year_data
    )


# ==========================================
# 16. RUN APPLICATION
# ==========================================

if __name__ == "__main__":

    init_db()

    app.run(
        debug=True,
        host="127.0.0.1",
        port=5000
    )