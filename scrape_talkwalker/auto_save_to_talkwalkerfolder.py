import imaplib
from dotenv import load_dotenv
import os

load_dotenv()

# Configuration
EMAIL = os.getenv("IMAP_EMAIL")
APP_PASSWORD = os.getenv("IMAP_PASSWORD")  # Mot de passe d'application
SERVER = "imap.gmail.com"
FOLDER = "Talkwalker"  # Nom du dossier à créer

# Connexion
mail = imaplib.IMAP4_SSL(SERVER)
mail.login(EMAIL, APP_PASSWORD)

# Créer le dossier (ignore s'il existe déjà)
mail.create(FOLDER)

# Rechercher et déplacer les e-mails
mail.select("INBOX")
status, messages = mail.search(None, '(FROM "alerts@talkwalker.com")')
for eid in messages[0].split():
    mail.copy(eid, FOLDER)  # Copie vers le dossier
    mail.store(eid, "+FLAGS", "\\Deleted")  # Supprime de la boîte de réception

mail.expunge()  # Finalise les suppressions
mail.close()
print("✅ E-mails déplacés vers le dossier", FOLDER)