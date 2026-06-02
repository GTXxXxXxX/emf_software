from google import genai
from google.genai import types
import json
import os
from pdf_extractor.pdf_extractor import PDFExtractor
from dotenv import load_dotenv
import datetime


class Gemini:
    """"
    This class represents the gemini API. We can get the competition prices using GEMINI. We can also normalize a PDF invoice into a JSON file.
    """
    def __init__(self):
        # Init
        load_dotenv()
        api_key = os.getenv("EMF_API_KEY")  # Load environement variable of API (for security)
        self.client = genai.Client(api_key=api_key)  # Creates the GenAI client.
        self.model = "gemini-2.5-flash"
        self.base_prompt = 'Extrait ce pdf avec les instructions systeme: '
        self.pdf_extractor = PDFExtractor()  # Loading PDF Text Extractor

        # Read and set system instructions
        with open("gemini/V2_Extractor/v2_prompt", "r", encoding="utf-8") as f:
            self.instructions = f.read()

        # Read and set JSON Schema for response
        with open("gemini/V2_Extractor/JSON_SCHEMA.json", "r", encoding="utf-8") as f:
            self.schema = json.load(f)

        # Read and set dealers and categories lists
        with open("gemini/V2_Extractor/config_extraction.json", "r", encoding="utf-8") as f:
            self.config_extraction = json.load(f)
            self.dealers_list = []
            for dealer in self.config_extraction["dealers"]:
                self.dealers_list.append(f"CODE:{dealer['Fournisseur']}, Nom:{dealer['Nom de l’entreprise']}")
            self.categories_list = ", ".join(self.config_extraction["categories"])

        # Makes the final intruction. This is what changes between uses. It changes everytime we extract an invoice
        self.instructions += f"\nDealers: {self.dealers_list}\nCategories: {self.categories_list}"
        self.temperature = 0

    def normalize_invoice(self, pdf_path):
        """"
        Extract pdf invoice -> to JSON normalized invoice
        """
        text_pdf = self.pdf_extractor.extract_pdf(pdf_path)  # Get the text from PDF
        today_date = datetime.date.today().strftime("%d-%m-%Y")  # Retrieve date (useful for the ai to set itself in time and get the date extraction correctly)
        full_prompt = f"{self.base_prompt}\n{text_pdf}\n Aujourd'hui, nous sommes le {today_date}"  # Full prompt
        # Generate the JSON answer with Gemini
        response = self.client.models.generate_content(model=self.model,
                                                       contents=full_prompt,
                                                       config=types.GenerateContentConfig(
                                                           system_instruction=self.instructions,
                                                           temperature=self.temperature,
                                                           response_mime_type="application/json",
                                                           response_schema=self.schema))
        return response.text

    def get_competition_prices(self, json_path):
        """"
        Get the competition prices using GEMINI and extracted invoice
        """
        with open(json_path, "r", encoding="utf-8") as f:
            json_data = json.load(f)

        print(json_data)
        pass

    def close_client(self):
        self.client.close()
