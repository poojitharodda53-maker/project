
import fitz
import re

pdf_path = "uploads/20261127110215481292_UGC_Comp_June2024_ReExam.pdf"

doc = fitz.open(pdf_path)

page = doc[12]
text = page.get_text("text")

match = re.search(r"(?m)^\s*Q80\s*$", text)

if match:
    print("QUESTION 80 FOUND")
    print(text[match.start():match.start() + 1500])
else:
    print("QUESTION 80 NOT FOUND")
