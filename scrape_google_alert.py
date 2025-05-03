import os
import base64
import json
import pymongo
from bs4 import BeautifulSoup
from datetime import datetime
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from dotenv import load_dotenv
import os

load_dotenv() 
token_path = os.getenv("GMAIL_TOKEN_PATH")
Credentials_path=os.getenv("GMAIL_CREDENTIALS_PATH")
# MongoDB setup
client = pymongo.MongoClient('mongodb://localhost:27017/')
db = client['veille_agriculture']
collection = db['google_alerts_Agriculture4.0']

# Gmail API Scope
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

def get_gmail_service():
    creds = None
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                Credentials_path, SCOPES)  # Make sure your credentials.json is correct
            creds = flow.run_local_server(port=0)

        with open(token_path, 'w') as token:
            token.write(creds.to_json())

    service = build('gmail', 'v1', credentials=creds)
    return service

def fetch_new_google_alerts(service):
    """Fetch new Google Alert emails with pagination"""
    next_page_token = None

    while True:
        query_params = {
            'userId': 'me',
            'labelIds': ['INBOX'],
            'q': 'from:googlealerts-noreply@google.com is:unread'
        }

        if next_page_token:
            query_params['pageToken'] = next_page_token

        results = service.users().messages().list(**query_params).execute()
        messages = results.get('messages', [])

        if not messages:
            print('No more Google Alerts found.')
            break

        for msg in messages:
            process_message(service, msg['id'])

        next_page_token = results.get('nextPageToken')
        if not next_page_token:
            break

def process_message(service, message_id):
    """Fetch and process one email"""
    msg_data = service.users().messages().get(userId='me', id=message_id, format='full').execute()
    payload = msg_data.get('payload', {})
    parts = payload.get('parts', [])
    html_content = ""

    for part in parts:
        if part['mimeType'] == 'text/html':
            html_content = part['body']['data']
            break
        elif part.get('parts'):
            for subpart in part['parts']:
                if subpart['mimeType'] == 'text/html':
                    html_content = subpart['body']['data']
                    break

    if html_content:
        html_content = base64.urlsafe_b64decode(html_content).decode('utf-8')
        extract_articles_from_json(html_content)

def extract_articles_from_json(html_content):
    """Extract Title, Description, URL, and add Source + Date from the embedded JSON"""
    soup = BeautifulSoup(html_content, 'html.parser')
    script_tag = soup.find('script', {'type': 'application/json'})

    if not script_tag:
        print("⚠️ No JSON script found in email.")
        return

    try:
        data = json.loads(script_tag.string)
    except json.JSONDecodeError:
        print("⚠️ Failed to parse JSON.")
        return

    # Use current date for all articles
    current_date = datetime.now().strftime("%Y-%m-%d")

    cards = data.get('cards', [])
    for card in cards:
        widgets = card.get('widgets', [])
        for widget in widgets:
            if widget.get('type') == 'LINK':
                title = widget.get('title', '')
                description = widget.get('description', '')
                url = widget.get('url', '')

                if title and url:
                    article_data = {
                        'title': title,
                        'description': description,
                        'url': url,
                        'source': "Google Alerts",
                        'date': current_date
                    }
                    print(article_data)
                    collection.insert_one(article_data)

if __name__ == '__main__':
    service = get_gmail_service()
    fetch_new_google_alerts(service)
