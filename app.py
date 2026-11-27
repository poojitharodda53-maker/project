
import os
import re
import sqlite3
import hashlib
from datetime import datetime
from contextlib import contextmanager
from functools import wraps

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
app.config["MAX_CONTENT_LENGTH"] = 400 * 1024 * 1024

ALLOWED_EXTENSIONS = {"pdf"}


# ==========================================
# 2. DATABASE CONNECTION
# ==========================================

@contextmanager
def get_db():

    con = sqlite3.connect(DATABASE)
    con.row_factory = sqlite3.Row

    try:
        yield con
        con.commit()

    except Exception:
        con.rollback()
        raise

    finally:
        con.close()


# ==========================================
# 3. ROLE PERMISSIONS
# ==========================================

def login_required(func):

    @wraps(func)
    def wrapper(*args, **kwargs):

        if "user_id" not in session:
            flash("Please login first.")
            return redirect(url_for("login"))

        return func(*args, **kwargs)

    return wrapper


def admin_required(func):

    @wraps(func)
    def wrapper(*args, **kwargs):

        if "user_id" not in session:
            flash("Please login first.")
            return redirect(url_for("login"))

        if session.get("role") != "admin":
            flash("Access denied. Admin permission required.")
            return redirect(url_for("home"))

        return func(*args, **kwargs)

    return wrapper


# ==========================================
# 4. DATABASE INITIALIZATION
# ==========================================

def init_db():

    with get_db() as con:

        con.execute("""
            CREATE TABLE IF NOT EXISTS papers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT,
                exam_year TEXT,
                exam_session TEXT,
                uploaded_at TEXT,
                file_hash TEXT
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
                correct_answer TEXT DEFAULT '',
                unit_no INTEGER,
                unit_name TEXT,
                confidence INTEGER DEFAULT 0,
                FOREIGN KEY(paper_id) REFERENCES papers(id)
            )
        """)

        con.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                role TEXT NOT NULL
            )
        """)

        migrations = {
            "papers": {
                "filename": "TEXT",
                "exam_year": "TEXT",
                "exam_session": "TEXT",
                "uploaded_at": "TEXT",
                "file_hash": "TEXT"
            },

            "questions": {
                "paper_id": "INTEGER",
                "original_no": "TEXT",
                "question": "TEXT",
                "option_a": "TEXT DEFAULT ''",
                "option_b": "TEXT DEFAULT ''",
                "option_c": "TEXT DEFAULT ''",
                "option_d": "TEXT DEFAULT ''",
                "correct_answer": "TEXT DEFAULT ''",
                "unit_no": "INTEGER",
                "unit_name": "TEXT",
                "confidence": "INTEGER DEFAULT 0"
            }
        }

        for table, columns in migrations.items():

            existing = {
                row["name"]
                for row in con.execute(
                    f"PRAGMA table_info({table})"
                ).fetchall()
            }

            for column, definition in columns.items():

                if column not in existing:

                    con.execute(
                        f"ALTER TABLE {table} "
                        f"ADD COLUMN {column} {definition}"
                    )

        con.execute("""
            CREATE INDEX IF NOT EXISTS idx_questions_unit
            ON questions(unit_no)
        """)

        con.execute("""
            CREATE INDEX IF NOT EXISTS idx_questions_paper
            ON questions(paper_id)
        """)

        con.execute("""
            CREATE INDEX IF NOT EXISTS idx_papers_file_hash
            ON papers(file_hash)
        """)

        # Fill missing exam years from existing filenames.
        old_papers = con.execute("""
            SELECT id, filename, exam_year
            FROM papers
            WHERE exam_year IS NULL
               OR TRIM(exam_year) = ''
        """).fetchall()

        for paper in old_papers:

            match = re.search(
                r"(20\d{2})",
                paper["filename"] or ""
            )

            if match:

                con.execute("""
                    UPDATE papers
                    SET exam_year = ?
                    WHERE id = ?
                """, (
                    match.group(1),
                    paper["id"]
                ))


# ==========================================
# 5. HELPER FUNCTIONS
# ==========================================

def allowed_file(filename):

    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower()
        in ALLOWED_EXTENSIONS
    )


def get_unit_name(unit_no):

    try:
        unit_no = int(unit_no)
    except (TypeError, ValueError):
        return "Unclassified"

    if 1 <= unit_no <= len(UNITS):
        return UNITS[unit_no - 1]["name"]

    return "Unclassified"


# ==========================================
# PDF YEAR AND EXAM SESSION DETECTION
# ==========================================

def get_pdf_details(
    filename,
    default_year="",
    default_session=""
):

    filename = filename or ""

    year_match = re.search(
        r"(20\d{2})",
        filename
    )

    year = (
        year_match.group(1)
        if year_match
        else default_year
    )

    lower_name = filename.lower()

    if "june" in lower_name:
        exam_session = "June"

    elif (
        "december" in lower_name
        or "dec" in lower_name
    ):
        exam_session = "December"

    elif (
        "september" in lower_name
        or "sep" in lower_name
    ):
        exam_session = "September"

    elif (
        "november" in lower_name
        or "nov" in lower_name
    ):
        exam_session = "November"

    elif "july" in lower_name:
        exam_session = "July"

    else:
        exam_session = default_session

    return year, exam_session


def calculate_file_hash(filepath):

    sha256 = hashlib.sha256()

    with open(filepath, "rb") as file:

        for chunk in iter(
            lambda: file.read(1024 * 1024),
            b""
        ):
            sha256.update(chunk)

    return sha256.hexdigest()


def normalize_question(question):

    question = str(question or "").lower()

    question = re.sub(
        r"\s+",
        " ",
        question
    )

    question = re.sub(
        r"[^\w\s]",
        "",
        question
    )

    return question.strip()


# ==========================================
# 6. PDF TEXT EXTRACTION
# ==========================================

def extract_pdf_content(filepath):

    doc = fitz.open(filepath)

    text_parts = []
    answer_key_text = ""

    answer_key_found = False
    common_passage = ""

    try:

        for page in doc:

            page_text = page.get_text("text") or ""

            # Detect the beginning of the answer key.
            if re.search(
                r"(?i)\bAnswer\s*Key\b",
                page_text
            ):
                answer_key_found = True

            if answer_key_found:

                if re.search(
                    r"(?i)Hints\s*&\s*Solutions",
                    page_text
                ):
                    break

                answer_key_text += "\n" + page_text
                continue

            words = page.get_text("words")

            # If word extraction is unavailable,
            # use the page's normal text.
            if not words:

                if page_text.strip():
                    text_parts.append(page_text)

                continue

            middle_x = page.rect.width / 2

            columns = [[], []]

            for word in words:

                x0, y0, x1, y1, word_text = word[:5]

                if not word_text.strip():
                    continue

                center_x = (x0 + x1) / 2

                column_no = (
                    0 if center_x < middle_x else 1
                )

                columns[column_no].append(
                    (y0, x0, word_text)
                )

            for column_words in columns:

                column_words.sort(
                    key=lambda item: (
                        item[0],
                        item[1]
                    )
                )

                lines = []

                for y, x, word_text in column_words:

                    if (
                        not lines
                        or abs(lines[-1]["y"] - y) > 3
                    ):

                        lines.append({
                            "y": y,
                            "items": []
                        })

                    lines[-1]["items"].append(
                        (x, word_text)
                    )

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

                if column_text.strip():
                    text_parts.append(column_text)

                # Detect common passage for questions 96-100.
                if (
                    "Directions" in column_text
                    and "96" in column_text
                    and "100" in column_text
                ):
                    common_passage = column_text

    finally:
        doc.close()

    return (
        "\n".join(text_parts),
        answer_key_text,
        common_passage
    )


# ==========================================
# 7. PROCESS ONE PDF
# ==========================================

def process_pdf(
    file,
    default_year="",
    default_session=""
):

    original_filename = secure_filename(
        file.filename or ""
    )

    if (
        not original_filename
        or not allowed_file(original_filename)
    ):
        raise ValueError(
            "Please select a valid PDF file."
        )

    saved_name = (
        datetime.now().strftime("%Y%m%d%H%M%S%f")
        + "_"
        + original_filename
    )

    filepath = os.path.join(
        UPLOAD_FOLDER,
        saved_name
    )

    file.save(filepath)

    try:

        # Calculate file hash.
        file_hash = calculate_file_hash(filepath)

        # Check whether the PDF already exists.
        with get_db() as con:

            existing_paper = con.execute("""
                SELECT id
                FROM papers
                WHERE file_hash = ?
                LIMIT 1
            """, (file_hash,)).fetchone()

        if existing_paper:

            raise ValueError(
                "This PDF has already been uploaded. "
                "Existing Paper ID: "
                + str(existing_paper["id"])
            )

        # Extract PDF content.
        text, answer_text, common_passage = (
            extract_pdf_content(filepath)
        )

        if not text.strip():

            raise ValueError(
                "No readable question text found in PDF."
            )

        # Extract questions and options.
        extracted = extract_questions(text)

        if not extracted:

            raise ValueError(
                "Questions not detected. Check analyzer.py."
            )

        # Remove duplicate question blocks.
        unique_questions = []
        seen_questions = set()

        for q in extracted:

            number = str(
                q.get("number", "")
            )

            normalized = normalize_question(
                q.get("question", "")
            )

            key = (
                number,
                normalized
            )

            if (
                not normalized
                or key in seen_questions
            ):
                continue

            seen_questions.add(key)
            unique_questions.append(q)

        extracted = unique_questions

        if not extracted:

            raise ValueError(
                "No unique questions found in this PDF."
            )

        # Extract answer key.
        answer_key = {}

        if answer_text.strip():

            answer_key = extract_answer_key(
                answer_text
            )

        for q in extracted:

            q_number = str(
                q.get("number", "")
            )

            answer = answer_key.get(
                q_number,
                ""
            )

            if not answer and q_number.isdigit():

                answer = answer_key.get(
                    int(q_number),
                    ""
                )

            q["correct_answer"] = answer

        # Attach common passage to questions 96-100.
        if common_passage:

            for q in extracted:

                try:
                    number = int(
                        q.get("number", 0)
                    )

                except (TypeError, ValueError):
                    number = 0

                if 96 <= number <= 100:

                    q["question"] = (
                        common_passage
                        + "\n"
                        + q.get("question", "")
                    )

        # Detect exam year and session.
        year, exam_session = get_pdf_details(
            original_filename,
            default_year,
            default_session
        )

        # Save paper and questions.
        with get_db() as con:

            duplicate = con.execute("""
                SELECT id
                FROM papers
                WHERE file_hash = ?
                LIMIT 1
            """, (file_hash,)).fetchone()

            if duplicate:

                raise ValueError(
                    "This PDF has already been uploaded. "
                    "Existing Paper ID: "
                    + str(duplicate["id"])
                )

            cursor = con.execute("""
                INSERT INTO papers (
                    filename,
                    exam_year,
                    exam_session,
                    uploaded_at,
                    file_hash
                )
                VALUES (?, ?, ?, ?, ?)
            """, (
                original_filename,
                year,
                exam_session,
                datetime.now().strftime("%Y-%m-%d"),
                file_hash
            ))

            paper_id = cursor.lastrowid

            inserted_count = 0

            for q in extracted:

                options = q.get(
                    "options",
                    {}
                ) or {}

                # Classify question and options.
                unit_no, confidence = classify_question(
                    q.get("question", ""),
                    options
                )

                unit_name = get_unit_name(
                    unit_no
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
                    str(q.get("number", "")),
                    q.get("question", "") or "",
                    options.get("A", "") or "",
                    options.get("B", "") or "",
                    options.get("C", "") or "",
                    options.get("D", "") or "",
                    q.get("correct_answer", "") or "",
                    unit_no,
                    unit_name,
                    confidence
                ))

                inserted_count += 1

        return paper_id, inserted_count

    except Exception:

        if os.path.exists(filepath):
            os.remove(filepath)

        raise


# ==========================================
# 8. LOGIN
# ==========================================

@app.route(
    "/login",
    methods=["GET", "POST"]
)
def login():

    if request.method == "POST":

        username = request.form.get(
            "username",
            ""
        ).strip()

        password = request.form.get(
            "password",
            ""
        )

        role = request.form.get(
            "role",
            ""
        ).strip().lower()

        if role not in ("admin", "student"):

            flash(
                "Please select a valid login role."
            )

            return redirect(
                url_for("login")
            )

        with get_db() as con:

            user = con.execute("""
                SELECT *
                FROM users
                WHERE username = ?
                  AND role = ?
            """, (
                username,
                role
            )).fetchone()

        if user and check_password_hash(
            user["password"],
            password
        ):

            session.clear()

            session["user_id"] = user["id"]
            session["username"] = user["username"]
            session["role"] = user["role"]

            flash("Login successful.")

            return redirect(
                url_for("dashboard")
            )

        flash(
            "Invalid username, password or role."
        )

    return render_template("login.html")


# ==========================================
# 9. STUDENT REGISTRATION
# ==========================================

@app.route(
    "/register",
    methods=["GET", "POST"]
)
def register():

    if request.method == "POST":

        username = request.form.get(
            "username",
            ""
        ).strip()

        password = request.form.get(
            "password",
            ""
        )

        confirm_password = request.form.get(
            "confirm_password",
            ""
        )

        if not username or not password:

            flash(
                "Please enter all required details."
            )

            return redirect(
                url_for("register")
            )

        if password != confirm_password:

            flash(
                "Passwords do not match."
            )

            return redirect(
                url_for("register")
            )

        if len(password) < 8:

            flash(
                "Password must contain at least 8 characters."
            )

            return redirect(
                url_for("register")
            )

        try:

            with get_db() as con:

                con.execute("""
                    INSERT INTO users (
                        username,
                        password,
                        role
                    )
                    VALUES (?, ?, 'student')
                """, (
                    username,
                    generate_password_hash(password)
                ))

            flash(
                "Registration successful. Please login."
            )

            return redirect(
                url_for("login")
            )

        except sqlite3.IntegrityError:

            flash(
                "Username already exists."
            )

    return render_template("register.html")


# ==========================================
# 10. DASHBOARD AND LOGOUT
# ==========================================

@app.route("/dashboard")
@login_required
def dashboard():

    return redirect(
        url_for("home")
    )


@app.route("/logout")
def logout():

    session.clear()

    flash(
        "Logged out successfully."
    )

    return redirect(
        url_for("login")
    )


# ==========================================
# 11. HOME PAGE / DASHBOARD
# ==========================================

@app.route("/")
@login_required
def home():

    with get_db() as con:

        total = con.execute("""
            SELECT COUNT(*)
            FROM questions
        """).fetchone()[0]

        papers_count = con.execute("""
            SELECT COUNT(*)
            FROM papers
        """).fetchone()[0]

        rows = con.execute("""
            SELECT
                unit_no,
                COUNT(*) AS total
            FROM questions
            WHERE unit_no BETWEEN 1 AND 10
            GROUP BY unit_no
        """).fetchall()

        counts = {
            row["unit_no"]: row["total"]
            for row in rows
        }

        unclassified = con.execute("""
            SELECT COUNT(*)
            FROM questions
            WHERE unit_no IS NULL
               OR unit_no NOT BETWEEN 1 AND 10
        """).fetchone()[0]

        last_updated = con.execute("""
            SELECT MAX(uploaded_at)
            FROM papers
        """).fetchone()[0]

    return render_template(
        "index.html",
        units=UNITS,
        counts=counts,
        total=total,
        papers=papers_count,
        unclassified=unclassified,
        last_updated=last_updated
    )


# ==========================================
# 12. PDF UPLOAD - ADMIN ONLY
# ==========================================

@app.route(
    "/upload",
    methods=["GET", "POST"]
)
@admin_required
def upload():

    if request.method == "POST":

        files = request.files.getlist(
            "pdf_files"
        )

        if (
            not files
            or not any(f.filename for f in files)
        ):

            single_file = request.files.get(
                "pdf_file"
            )

            files = (
                [single_file]
                if single_file and single_file.filename
                else []
            )

        files = [
            f for f in files
            if f and f.filename
        ]

        if not files:

            flash(
                "Please select PDF files."
            )

            return redirect(
                url_for("upload")
            )

        year = request.form.get(
            "exam_year",
            ""
        ).strip()

        exam_session = request.form.get(
            "exam_session",
            ""
        ).strip()

        success_count = 0
        total_questions = 0
        errors = []

        for file in files:

            try:

                paper_id, question_count = process_pdf(
                    file,
                    year,
                    exam_session
                )

                success_count += 1
                total_questions += question_count

            except Exception as error:

                errors.append(
                    (file.filename or "PDF")
                    + ": "
                    + str(error)
                )

        if success_count:

            flash(
                str(success_count)
                + " PDF(s) uploaded successfully. "
                + str(total_questions)
                + " questions extracted."
            )

        for error in errors:
            flash(error)

        return redirect(
            url_for("papers")
        )

    return render_template(
        "upload.html"
    )


# ==========================================
# 13. UNIT PAGE - SHOW PDF YEARS
# ==========================================

@app.route("/unit/<int:unit_no>")
@login_required
def unit_detail(unit_no):

    if (
        unit_no < 1
        or unit_no > len(UNITS)
    ):
        return redirect(
            url_for("home")
        )

    unit = UNITS[unit_no - 1]

    with get_db() as con:

        papers = con.execute("""
            SELECT
                p.id,
                p.filename,
                p.exam_year,
                p.exam_session,
                p.uploaded_at,
                COUNT(q.id) AS total
            FROM papers p
            JOIN questions q
                ON q.paper_id = p.id
            WHERE q.unit_no = ?
            GROUP BY
                p.id,
                p.filename,
                p.exam_year,
                p.exam_session,
                p.uploaded_at
            ORDER BY
                CASE
                    WHEN p.exam_year IS NULL
                         OR p.exam_year = ''
                    THEN 1
                    ELSE 0
                END,
                p.exam_year DESC,
                p.id DESC
        """, (
            unit_no,
        )).fetchall()

        total = con.execute("""
            SELECT COUNT(*)
            FROM questions
            WHERE unit_no = ?
        """, (
            unit_no,
        )).fetchone()[0]

    return render_template(
        "unit.html",
        unit=unit,
        unit_no=unit_no,
        papers=papers,
        total=total
    )


# ==========================================
# 14. SELECTED YEAR PDF QUESTIONS
# ==========================================

@app.route(
    "/unit/<int:unit_no>/paper/<int:paper_id>"
)
@login_required
def unit_paper_questions(
    unit_no,
    paper_id
):

    if (
        unit_no < 1
        or unit_no > len(UNITS)
    ):
        return redirect(
            url_for("home")
        )

    unit = UNITS[unit_no - 1]

    with get_db() as con:

        paper = con.execute("""
            SELECT *
            FROM papers
            WHERE id = ?
        """, (
            paper_id,
        )).fetchone()

        if not paper:

            flash("Paper not found.")

            return redirect(
                url_for(
                    "unit_detail",
                    unit_no=unit_no
                )
            )

        questions = con.execute("""
            SELECT *
            FROM questions
            WHERE paper_id = ?
              AND unit_no = ?
            ORDER BY
                CAST(original_no AS INTEGER),
                id
        """, (
            paper_id,
            unit_no
        )).fetchall()

    return render_template(
        "unit_questions.html",
        unit=unit,
        unit_no=unit_no,
        paper=paper,
        questions=questions,
        total=len(questions)
    )


# ==========================================
# 15. COMPLETE PAPER DETAILS
# ==========================================

@app.route("/paper/<int:paper_id>")
@login_required
def paper_detail(paper_id):

    with get_db() as con:

        paper = con.execute("""
            SELECT *
            FROM papers
            WHERE id = ?
        """, (
            paper_id,
        )).fetchone()

        if not paper:

            flash("Paper not found.")

            return redirect(
                url_for("home")
            )

        questions = con.execute("""
            SELECT *
            FROM questions
            WHERE paper_id = ?
            ORDER BY
                CAST(original_no AS INTEGER),
                id
        """, (
            paper_id,
        )).fetchall()

    return render_template(
        "paper.html",
        paper=paper,
        questions=questions,
        units=UNITS
    )


# ==========================================
# 16. REASSIGN QUESTION - ADMIN ONLY
# ==========================================

@app.route(
    "/reassign/<int:question_id>",
    methods=["POST"]
)
@admin_required
def reassign(question_id):

    try:

        unit_no = int(
            request.form.get(
                "unit_no",
                0
            )
        )

    except (ValueError, TypeError):

        unit_no = 0

    if unit_no not in range(1, 11):
        unit_no = 0

    unit_name = get_unit_name(
        unit_no
    )

    with get_db() as con:

        result = con.execute("""
            SELECT paper_id
            FROM questions
            WHERE id = ?
        """, (
            question_id,
        )).fetchone()

        if result:

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

    if result:

        return redirect(
            url_for(
                "paper_detail",
                paper_id=result["paper_id"]
            )
        )

    return redirect(
        url_for("home")
    )


# ==========================================
# 17. ALL UPLOADED PAPERS - VIEW
# ==========================================

@app.route("/papers")
@login_required
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
# 18. DELETE PAPER - ADMIN ONLY
# ==========================================

@app.route(
    "/delete-paper/<int:paper_id>",
    methods=["POST"]
)
@admin_required
def delete_paper(paper_id):

    with get_db() as con:

        paper = con.execute("""
            SELECT filename
            FROM papers
            WHERE id = ?
        """, (
            paper_id,
        )).fetchone()

        if not paper:

            flash("Paper not found.")

            return redirect(
                url_for("papers")
            )

        con.execute("""
            DELETE FROM questions
            WHERE paper_id = ?
        """, (
            paper_id,
        ))

        con.execute("""
            DELETE FROM papers
            WHERE id = ?
        """, (
            paper_id,
        ))

    original_filename = (
        paper["filename"] or ""
    )

    for saved_filename in os.listdir(
        UPLOAD_FOLDER
    ):

        if saved_filename.endswith(
            "_" + original_filename
        ):

            filepath = os.path.join(
                UPLOAD_FOLDER,
                saved_filename
            )

            if os.path.isfile(filepath):
                os.remove(filepath)

    flash(
        "Paper deleted successfully."
    )

    return redirect(
        url_for("papers")
    )


# ==========================================
# 19. REPORTS - UNIT COUNTS
# ==========================================

@app.route(
    "/analysis",
    methods=["GET", "POST"]
)
@login_required
def analysis():

    unit_data = []
    questions = []

    selected_unit = ""
    analyzed = False

    with get_db() as con:

        unit_data = con.execute("""
            SELECT
                unit_no,
                unit_name,
                COUNT(*) AS total
            FROM questions
            WHERE unit_no BETWEEN 1 AND 10
            GROUP BY
                unit_no,
                unit_name
            ORDER BY unit_no
        """).fetchall()

        if request.method == "POST":

            selected_unit = request.form.get(
                "unit",
                ""
            ).strip()

            analyzed = True

            if selected_unit == "":

                questions = con.execute("""
                    SELECT *
                    FROM questions
                    WHERE unit_no BETWEEN 1 AND 10
                    ORDER BY
                        unit_no,
                        paper_id,
                        CAST(original_no AS INTEGER)
                """).fetchall()

            elif (
                selected_unit.isdigit()
                and 1 <= int(selected_unit) <= 10
            ):

                questions = con.execute("""
                    SELECT *
                    FROM questions
                    WHERE unit_no = ?
                    ORDER BY
                        paper_id,
                        CAST(original_no AS INTEGER)
                """, (
                    int(selected_unit),
                )).fetchall()

    return render_template(
        "analysis.html",
        units=UNITS,
        unit_data=unit_data,
        year_data=[],
        questions=questions,
        selected_unit=selected_unit,
        analyzed=analyzed
    )


# ==========================================
# 20. ERROR HANDLING
# ==========================================

@app.errorhandler(413)
def file_too_large(error):

    flash(
        "Uploaded files exceed the allowed size."
    )

    if session.get("role") == "admin":

        return redirect(
            url_for("upload")
        )

    return redirect(
        url_for("home")
    )


# ==========================================
# 21. RUN APPLICATION
# ==========================================

if __name__ == "__main__":

    init_db()

    print("===================================")
    print("UGC NET CS ANALYZER")
    print("Official 10 Units Loaded")
    print("Admin and Student Roles Enabled")
    print("Admin-only PDF Management Enabled")
    print("PDF Year and Session Detection Enabled")
    print("Database Ready")
    print("===================================")

    app.run(
        debug=True,
        use_reloader=False,
        host="127.0.0.1",
        port=5000
    )
