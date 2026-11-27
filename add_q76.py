import sqlite3
import pymupdf
from analyzer import extract_questions, classify_question, UNITS

PDF_PATH = r"uploads\20261127114948973610_UGC_Comp_Sep2022.pdf"
PAPER_ID = 17

doc = pymupdf.open(PDF_PATH)
page_text = doc[7].get_text()
doc.close()

questions = extract_questions(page_text)
q76 = next((q for q in questions if str(q["number"]) == "76"), None)

if q76 is None:
    raise Exception("Q76 not found. Database unchanged.")

question_text = q76["question"]

unit_no, confidence = classify_question(
    question_text + " Database normalization BCNF 3NF 2NF 4NF functional dependency partial dependency transitive dependency multivalued dependency"
)

if unit_no != 4:
    raise Exception(f"Unexpected unit: {unit_no}. Database unchanged.")

unit_name = UNITS[unit_no - 1]["name"]

conn = sqlite3.connect("questions.db")

try:
    existing = conn.execute(
        "SELECT id FROM questions WHERE paper_id=? AND original_no=?",
        (PAPER_ID, "76")
    ).fetchone()

    if existing:
        print("Q76 already exists. No changes made.")
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
            PAPER_ID, "76", question_text,
            4, unit_name, confidence,
            q76["options"].get("A", ""),
            q76["options"].get("B", ""),
            q76["options"].get("C", ""),
            q76["options"].get("D", ""),
            "C"
        ))

        conn.commit()
        print("Q76 INSERTED SUCCESSFULLY!")

    print("VERIFICATION:", conn.execute("""
        SELECT original_no, unit_no, unit_name, correct_answer
        FROM questions
        WHERE paper_id=? AND original_no='76'
    """, (PAPER_ID,)).fetchone())

    print("PAPER 17 TOTAL:", conn.execute(
        "SELECT COUNT(*) FROM questions WHERE paper_id=?",
        (PAPER_ID,)
    ).fetchone()[0])

except Exception:
    conn.rollback()
    raise
finally:
    conn.close()
