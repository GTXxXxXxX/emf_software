from gemini.gemini import Gemini
import os
from gmail_api import gmail

from utils import clear_console, pause

class App:
    def __init__(self, credentials):
        self.messages_retriever = gmail.MessageRetriever(credentials)
        self.gemini = Gemini()
        self.unprocessed_dir = "gmail_api/unprocessed"

    def main(self):
        while True:
            clear_console()
            choice = input('Select an option:\n1- Retrieve attachments from gmail\n2- Scrape an invoice\n > ')
            try :
                choice = int(choice)
                match choice:
                    case 1:
                        print('Retrieving attachments...')
                        nb_of_attachments = self.messages_retriever.get_messages_with_attachments()  # Change name bc it downloads them too.
                        if not nb_of_attachments is None:
                            print(f"Done: {nb_of_attachments} new attachments.")

                        pause()
                    case 2:
                        if os.listdir(self.unprocessed_dir):
                            print("Invoices : ")
                            for index, filename in enumerate(os.listdir(self.unprocessed_dir)):
                                print(f"{index} > {filename}")


                            chosed_invoice_index = input("Scrape invoice number?: ")
                            try:
                                invoice_name = os.listdir(self.unprocessed_dir)[int(chosed_invoice_index)]
                                file_path = f"{self.unprocessed_dir}/{invoice_name}"
                                print(f"Scraping {file_path}...")
                                scraped_invoice = self.gemini.normalize_invoice(file_path)
                                print(scraped_invoice)
                            except Exception as e:
                                print(f'Error : {e}')
                                pause()

                        else:
                            print("No unprocessed invoice found.")

                            pause()
            except Exception as e:
                print(f'Error : {e}')
                pause()

if __name__ == '__main__':
    app = App(credentials="gmail_api/credentials.json")
    app.main()



# try:
#     response =self.gemini.normalize_invoice(file_path)
#     print(response)
#     os.remove(file_path)
# except ServerError as e:
#     print(e, "\nRecommencement de la boucle")