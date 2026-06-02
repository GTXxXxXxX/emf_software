import pdfplumber

class PDFExtractor:
    """"
    A pdf extractor tool
    """
    def __init__(self):
        pass

    def extract_pdf(self, pdf_path):
        full_text = ''
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                full_text += page.extract_text()

        return full_text
