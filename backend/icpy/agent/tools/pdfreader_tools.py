from pypdf import PdfReader

def get_pdf_reader(pdf_path):
    """
    Returns a PDF reader for the LinkedIn profile PDF.
    """
    reader = PdfReader(pdf_path)
    pdfcontent = ""
    for page in reader.pages:
        text = page.extract_text()
        if text:
            pdfcontent += text
    return pdfcontent
