import base64
import os
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from threading import Thread
from time import sleep

from termcolor import colored

SCOPES = ['https://www.googleapis.com/auth/gmail.modify']


class MessageRetriever:
    def __init__(self, credentials):
        self.creds = self._authenticate(credentials)
        self.service = build('gmail', 'v1', credentials=self.creds)

    def _authenticate(self, credentials):
        creds = None
        # Le fichier token.json stocke les jetons d'accès de l'utilisateur.
        if os.path.exists('token.json'):
            creds = Credentials.from_authorized_user_file('token.json', SCOPES)

        # Si aucun jeton valide n'est dispo, on se connecte.
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                # Charge fichier credentials.json téléchargé depuis Google Cloud Console
                flow = InstalledAppFlow.from_client_secrets_file(credentials, SCOPES)
                creds = flow.run_local_server(port=0)

            # Sauvegarde le jeton pour la prochaine fois
            with open('token.json', 'w') as token:
                token.write(creds.to_json())
        return creds

    def get_messages_with_attachments(self, user_id='me', query='is:unread has:attachment'):
        global parts, nb_of_files
        results = self.service.users().messages().list(userId=user_id, q=query).execute()
        messages = results.get('messages', [])
        attachments_paths = []

        if not messages:
            print(colored("No new unread messages with attachments.","yellow"))
            return

        for msg in messages:
            msg_id = msg['id']
            message = self.service.users().messages().get(userId=user_id, id=msg_id, format='full').execute()
            # 1. On récupère les headers du message
            headers = message.get('payload', {}).get('headers', [])

            # 2. On cherche le header qui s'appelle 'Subject'
            subject = next((header['value'] for header in headers if header['name'].lower() == 'subject'), "Sans objet")

            print(colored(f"Treating : {msg_id}\nObject : {subject} ...", "light_green"))

            # Extraction des pièces jointes (Gestion récursive simple)
            parts = [message['payload']]
            nb_of_files = 0
            while parts:
                part = parts.pop()
                if 'parts' in part:
                    parts.extend(part['parts'])

                filename = part.get('filename')
                if filename and filename.split('.')[-1] == 'pdf':
                    att_id = part['body'].get('attachmentId')
                    attachment = self.service.users().messages().attachments().get(
                        userId=user_id, messageId=msg_id, id=att_id
                    ).execute()

                    file_data = base64.urlsafe_b64decode(attachment['data'].encode('UTF-8'))

                    with open(f"gmail_api/unprocessed/{filename}", 'wb') as f:
                        f.write(file_data)
                        if f'unprocessed/{filename}' not in attachments_paths:
                            attachments_paths.append(f"unprocessed/{filename}")
                    print(f" -> Downloaded file : {filename}")
                    nb_of_files += 1

            # --- IMPORTANT : Marquer comme lu pour ne pas le retraiter ---
            self.service.users().messages().modify(
                userId=user_id, id=msg_id,
                body={'removeLabelIds': ['UNREAD']}
            ).execute()
            print(f"Message {msg_id} mark as read.")

        return nb_of_files


class GmailPoller:
    def __init__(self, poll_delay):
        self.messages = MessageRetriever(credentials="credentials.json")
        self.poll_delay = poll_delay

    def poll(self):
        while True:
            print("Polling...")
            self.messages.get_messages_with_attachments()
            print(f"Next poll in {self.poll_delay} seconds...")
            sleep(self.poll_delay)

    def start_polling(self):
        thread = Thread(target=self.poll)
        thread.start()
