import datetime
import json

from db_handler.db_handler import DBHandler
from gemini.gemini import Gemini
import os
from gmail_api import gmail
from utils import clear_console, pause
from termcolor import colored
import signal
import queue
from event_handler import CustomHandler
from watchdog.observers import Observer
import time


class Console:
    def __init__(self, credentials):
        self.messages_retriever = gmail.MessageRetriever(credentials)
        self.gemini = Gemini()
        self.poller = gmail.GmailPoller(30)
        self.unprocessed_dir = "gmail_api/unprocessed"
        self.processed_dir = "treated_invoices_json"
        self.db_name = "processed_invoices"
        self.db_handler = DBHandler(self.db_name)
        self.path_queue = queue.Queue()
        self.event_handler = CustomHandler(self.path_queue)
        self.observer = Observer()

    def main(self):
        mode = input("1 - Debug\n2 - Main:\n > ")
        try:
            mode = int(mode)
            match mode:
                case 1:
                    while True:
                        clear_console()
                        choice = input(
                            'Select an option:\n1- Retrieve attachments from gmail\n2- Scrape an invoice\n3- Get competition prices\n > ')
                        try:
                            choice = int(choice)
                            match choice:
                                case 1:
                                    print('Retrieving attachments...')
                                    nb_of_attachments = self.messages_retriever.get_messages_with_attachments()  # Change name bc it downloads them too.
                                    if not nb_of_attachments is None:
                                        print(f"Done: {nb_of_attachments} new attachments.")

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
                                            print(type(scraped_invoice))
                                            # with open(f"{self.processed_dir}/{invoice_name}", "wb") as file:
                                            pause()
                                        except Exception as e:
                                            print(f'Error : {e}')
                                            pause()

                                    else:
                                        print("No unprocessed invoice found.")
                                case 3:
                                    print("Treated invocies : ")
                                    for index, filename in enumerate(os.listdir(self.processed_dir)):
                                        print(f"{index} > {filename}")
                                    try:
                                        choice = int(input("Scrape invoice number: "))
                                        json_path = f"{self.processed_dir}/{os.listdir(self.processed_dir)[choice]}"
                                        response = self.gemini.get_competition_prices(json_path)
                                        print(response)
                                    except Exception as e:
                                        print(f'Error : {e}')

                            pause()
                        except Exception as e:
                            print(f'Error : {e}')
                            pause()
                case 2:
                    print(colored("Starting main loop...", "light_green"))
                    self.poller.start_polling()
                    self.observer.schedule(self.event_handler, self.unprocessed_dir, recursive=False)
                    self.observer.start()
                    print(f"Monitoring {self.unprocessed_dir} in progress...")
                    while True:
                        # Get the most recent invoice file
                        file_path = self.path_queue.get(block=True)
                        print(f"Modified path: {file_path}")
                        time.sleep(1)

                        # Send the invoice to GEMINI
                        print(f"Scraping {file_path}...")
                        before = time.time()
                        scraped_invoice = self.gemini.normalize_invoice(file_path)
                        print(scraped_invoice)
                        execution_time = time.time() - before

                        # Transform the invoice into a dict to make the name [dealer][inv_nb]
                        dict_json = json.loads(scraped_invoice)
                        invoice_name = dict_json["dealer"].replace(" ", "") + dict_json["invoice_number"]

                        # Write the JSON file
                        json_file_path = f"{self.processed_dir}/{invoice_name}.json"
                        with open(json_file_path, "w", encoding="utf-8") as f:
                            json.dump(dict_json, f, indent=4)

                        print(colored(f"JSON File {json_file_path} written.", "green"))

                        if os.path.exists(file_path):
                            os.remove(file_path)

                        print(colored(f"File {file_path} deleted.", "green"))

                        json_priced = self.gemini.get_competition_prices(json_file_path)
                        priced_json_dict = json.loads(json_priced)

                        with open(json_file_path, "w", encoding="utf-8") as f:
                            json.dump(priced_json_dict, f, indent=4, ensure_ascii=False)
                        print(colored(f"Priced JSON File {json_file_path} written.", "green"))
                        dt_date = datetime.datetime.now().strftime("%Y-%m-%d")

                        self.db_handler.insert_invoice(invoice_name, json_file_path, dt_date, execution_time)

        except Exception as e:
            print(f'Error : {e}')
            self.db_handler.close_connection()
            pause()


if __name__ == '__main__':
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    console = Console(credentials="gmail_api/credentials.json")
    console.main()

# try:
#     response =self.gemini.normalize_invoice(file_path)
#     print(response)
#     os.remove(file_path)
# except ServerError as e:
#     print(e, "\nRecommencement de la boucle")
