import django

django.setup()

from api.import_views import ImportHRRecordsAPIView
from pypdf import PdfReader


pdf_path = "/home/hrsh/Downloads/hr_employee_records_100.pdf"

reader = PdfReader(pdf_path)

text = ""

for page in reader.pages:
    page_text = page.extract_text()

    if page_text:
        text += page_text + "\n"


lines = [
    line.strip()
    for line in text.splitlines()
    if line.strip()
]


print("Total extracted lines:", len(lines))

print("\nFirst 20 lines:")
for line in lines[:20]:
    print(repr(line))
