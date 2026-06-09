from google import genai
from google.genai import types
import json
import os
from pdf_extractor.pdf_extractor import PDFExtractor
from dotenv import load_dotenv
import datetime
import time


class Gemini:
    """"
    This class represents the gemini API. We can get the competition prices using GEMINI. We can also normalize a PDF invoice into a JSON file.
    """

    def __init__(self):
        # Init
        load_dotenv()
        api_key = os.getenv("EMF_API_KEY")  # Load environement variable of API (for security)
        # LOAD GEMINI
        self.client = genai.Client(api_key=api_key)  # Creates the GenAI client.
        self.model = "gemini-2.5-flash"

        # BASE PROMPTS
        self.base_prompt_extractor = 'Extrait ce pdf avec les instructions systeme: '
        self.base_prompt_price = 'Va chercher le prix de cet item avec ces instructions systeme: '

        # PDF EXTRACTOR
        self.pdf_extractor = PDFExtractor()  # Loading PDF Text Extractor

        # Read and set system instructions for the extractor
        with open("gemini/V2_Extractor/v2_prompt", "r", encoding="utf-8") as f:
            self.instructions_extractor = f.read()

        # Read and set system instructions for the price scrapper
        with open("gemini/V1_CompetitionPricesScrapper/v1_price_scrapper", "r", encoding="utf-8") as f:
            self.instructions_price = f.read()

        # Read and set JSON Schema for response for invoice scrapper
        with open("gemini/V2_Extractor/JSON_SCHEMA.json", "r", encoding="utf-8") as f:
            self.schema = json.load(f)

        # Read and set dealers and categories lists
        with open("gemini/V2_Extractor/config_extraction.json", "r", encoding="utf-8") as f:
            self.config_extraction = json.load(f)
            self.dealers_list = []
            for dealer in self.config_extraction["dealers"]:
                self.dealers_list.append(f"CODE:{dealer['Fournisseur']}, Nom:{dealer['Nom de l’entreprise']}")
            self.categories_list = ", ".join(self.config_extraction["categories"])

        # Makes the final intruction for invoice scrapper. This is what doesn't change between uses.
        self.instructions_extractor += f"\nDealers: {self.dealers_list}\nCategories: {self.categories_list}"
        self.temperature = 0

    def normalize_invoice(self, pdf_path):
        """"
        Extract pdf invoice -> to JSON normalized invoice
        """
        text_pdf = self.pdf_extractor.extract_pdf(pdf_path)  # Get the text from PDF
        today_date = datetime.date.today().strftime(
            "%d-%m-%Y")  # Retrieve date (useful for the ai to set itself in time and get the date extraction correctly)
        full_prompt = f"{self.base_prompt_extractor}\n{text_pdf}\n Aujourd'hui, nous sommes le {today_date}"  # Full prompt
        # Generate the JSON answer with Gemini

        max_retries = 4
        wait_time = 2  # Temps d'attente initial en secondes
        gemini_response = ""
        for retry in range(max_retries):
            try:

                response = self.client.models.generate_content(model=self.model,
                                                               contents=full_prompt,
                                                               config=types.GenerateContentConfig(
                                                                   system_instruction=self.instructions_extractor,
                                                                   temperature=self.temperature,
                                                                   response_schema=self.schema,
                                                                   response_mime_type="application/json"))
                gemini_response = response
                break

            except Exception as e:
                # Si c'est le dernier essai et que ça foire encore, on abandonne proprement
                if retry == max_retries - 1:
                    print(f"Échec définitif pour scrape {pdf_path} après {max_retries} essais. Erreur: {e}")
                    return None
                else:
                    print(
                        f"Serveur saturé (503) ou erreur pour '{pdf_path}'. Réessai {retry + 1}/{max_retries} dans {wait_time}s...")
                    time.sleep(wait_time)
                    wait_time *= 2  # On double le temps d'attente (2s, 4s, 8s...)

        raw_text = gemini_response.text.strip()
        if raw_text.startswith("```json"):
            raw_text = raw_text.removeprefix("```json").removesuffix("```").strip()

        return raw_text

    def get_competition_prices(self, json_path):
        """"
        Get the competition prices using GEMINI and extracted invoice
        """
        with open(json_path, "r", encoding="utf-8") as f:
            json_data = json.load(f)

        today_date = datetime.date.today().strftime("%d-%m-%Y")
        updated_items = []

        for item in json_data["products"]:
            product_description = item.get("description", "") or item.get("product_id", "")

            if not product_description:
                updated_items.append(item)
                continue

            full_prompt = f"{self.base_prompt_price}\nProduit à chercher : {product_description}\nStructure à compléter : {json.dumps(item, ensure_ascii=False)}\nNous sommes le {today_date}"

            max_retries = 4
            wait_time = 2  # Temps d'attente initial en secondes
            completed_item = None
            for retry in range(max_retries):
                try:
                    response = self.client.models.generate_content(model=self.model, contents=full_prompt,
                                                                   config=types.GenerateContentConfig(
                                                                       system_instruction=self.instructions_price,
                                                                       tools=[types.Tool(
                                                                           google_search=types.GoogleSearch())],
                                                                       temperature=self.temperature))
                    raw_text = response.text.strip()
                    if raw_text.startswith("```json"):
                        raw_text = raw_text.removeprefix("```json").removesuffix("```").strip()

                    completed_item = json.loads(raw_text)
                    print(f"Done {completed_item["product_id"]}")
                    break  # Succès ! On casse la boucle de retry pour passer au produit suivant

                except Exception as e:
                    # Si c'est le dernier essai et que ça foire encore, on abandonne proprement
                    if retry == max_retries - 1:
                        print(f"Échec définitif pour '{product_description}' après {max_retries} essais. Erreur: {e}")
                        completed_item = item  # On garde l'item original non complété pour ne pas bloquer le script
                    else:
                        print(
                            f"Serveur saturé (503) ou erreur pour '{product_description}'. Réessai {retry + 1}/{max_retries} dans {wait_time}s...")
                        time.sleep(wait_time)
                        wait_time *= 2  # On double le temps d'attente (2s, 4s, 8s...)

            updated_items.append(completed_item)

            # --- DÉLAI DE COURTOISIE ---
            # Une petite pause de 1.5 seconde entre chaque produit pour éviter de re-saturer l'API
            time.sleep(1.5)

            # On reconstruit le JSON final avec les prix mis à jour
        json_data["products"] = updated_items
        return json.dumps(json_data, ensure_ascii=False, indent=4)

    def close_client(self):
        self.client.close()
