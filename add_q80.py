import sqlite3
import pymupdf

from analyzer import extract_questions, classify_question, UNITS

PDF_PATH = r"uploads\20261127110215481292_UGC_Comp_June2024_ReExam.pdf"
PAPER_ID = 12

# Read Q80 from the original PDF (page 13)
doc = pymupdf.open(PDF_PATH)
page_text = doc[12].get_text()
doc.close()

questions = extract_questions(page_text)
q80 = next((q for q in questions if str(q["number"]) == "80"), None)

if q80 is None:
    raise Exception("Q80 not found in PDF. Database was not changed.")

question_text = q80["question"]

# Verify unit classification
unit_no, confidence = classify_question(question_text)

if unit_no != 9:
    raise Exception(f"Unexpected unit classification: {unit_no}. Database was not changed.")

unit_name = UNITS[unit_no - 1]["name"]

# Answer verified from the PDF answer key
correct_answer = "B"

conn = sqlite3.connect("questions.db")

try:
    paper = conn.execute(
        "SELECT id FROM papers WHERE id = ?", (PAPER_ID,)
    ).fetchone()

    if paper is None:
        raise Exception("Paper ID 12 not found.")

    existing = conn.execute(
        "SELECT id FROM questions WHERE paper_id = ? AND original_no = ?",
        (PAPER_ID, "80")
    ).fetchone()

    if existing:
        print("Q80 already exists. No changes made.")
    else:
        conn.execute("""
            INSERT INTO questions (
                paper_id, original_no, question,
                unit_no, unit_name, confidence,
                option_a, option_b, option_c, option_d,
                correct_answer
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            PAPER_ID, "80", question_text,
            unit_no, unit_name, confidence,
            "", "", "", "",
            correct_answer
        ))

        conn.commit()
        print("Q80 INSERTED SUCCESSFULLY!")

    result = conn.execute("""
        SELECT original_no, unit_no, unit_name, correct_answer
        FROM questions
        WHERE paper_id = ? AND original_no = '80'
    """, (PAPER_ID,)).fetchone()

    print("VERIFICATION:", result)

    total = conn.execute(
        "SELECT COUNT(*) FROM questions WHERE paper_id = ?",
        (PAPER_ID,)
    ).fetchone()[0]

    print("PAPER 12 TOTAL QUESTIONS:", total)

except Exception:
    conn.rollback()
    raise

finally:
    conn.close()
