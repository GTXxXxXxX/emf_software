from google import genai
from google.genai import types
import json
import os
from pdf_extractor.pdf_extractor import PDFExtractor
from dotenv import load_dotenv


class Gemini:
    def __init__(self):
        load_dotenv()
        api_key = os.getenv("EMF_API_KEY")
        self.client = genai.Client(api_key=api_key)
        self.model = "gemini-2.5-flash"
        self.base_prompt = 'Extrait ce pdf avec les instructions systeme: '
        self.pdf_extractor = PDFExtractor()

        with open("gemini/V2_Extractor/v2_prompt", "r", encoding="utf-8") as f:
            self.instructions = f.read()

        with open("gemini/JSON_SCHEMA.json", "r", encoding="utf-8") as f:
            self.schema = json.load(f)

        with open("gemini/V2_Extractor/config_extraction.json", "r", encoding="utf-8") as f:
            self.config_extraction = json.load(f)
            self.dealers_list = []
            for dealer in self.config_extraction["dealers"]:
                self.dealers_list.append(f"CODE:{dealer['Fournisseur']}, Nom:{dealer['Nom de l’entreprise']}")
            self.categories_list = ", ".join(self.config_extraction["categories"])

        self.instructions += f"\nDealers: {self.dealers_list}\nCategories: {self.categories_list}"
        self.temperature = 0

    def normalize_invoice(self, pdf_path):
        text_pdf = self.pdf_extractor.extract_pdf(pdf_path)
        full_prompt = f"{self.base_prompt}\n{text_pdf}"
        print(full_prompt)
        response = self.client.models.generate_content(model=self.model,
                                                       contents=full_prompt,
                                                       config=types.GenerateContentConfig(
                                                           system_instruction=self.instructions,
                                                           temperature=self.temperature,
                                                           response_mime_type="application/json",
                                                           response_schema=self.schema))
        return response.text

    def get_competition_prices(self):
        pass

    def close_client(self):
        self.client.close()
