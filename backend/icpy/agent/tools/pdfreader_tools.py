from dotenv import load_dotenv
from openai import OpenAI
from pypdf import PdfReader

load_dotenv(override=True)
openai = OpenAI()

reader = PdfReader("tazhang_linkedIn.pdf")
linkedin = ""
for page in reader.pages:
    text = page.extract_text()
    if text:
        linkedin += text