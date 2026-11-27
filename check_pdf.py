
import pymupdf
import glob
import os

files = glob.glob("uploads/*June2024*")

for filepath in files:
    print("PDF:", os.path.basename(filepath))

    doc = pymupdf.open(filepath)

    for page_no, page in enumerate(doc):
        text = page.get_text("text")

        if "Q79" in text or "Q81" in text or "Q80" in text:
            print("\n========== PAGE", page_no + 1, "==========")
            print(text)
