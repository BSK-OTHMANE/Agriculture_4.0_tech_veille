import requests
from urllib.parse import urlparse
import whois
from pymongo import MongoClient
from datetime import datetime
import time
import random

# --- MongoDB connection ---
client = MongoClient("mongodb://localhost:27017/")
db = client["veille_agriculture"]

# --- Collections to process ---
collections = [
    "google_alerts_Agriculture4.0",
    "scholar_agriculture_4_0_newest",
    "scholar_agriculture_4_0_relevant",
    "talkwalker_alerts_Agricuture_4.0"
]

# --- Filtering criteria ---
BLACKLISTED_DOMAINS = [
    "infowars.com", "naturalnews.com", "worldnewsdailyreport.com", "beforeitsnews.com",
    "theonion.com", "clickhole.com", "babylonbee.com", "dailybuzzlive.com", "empirenews.net"
]

SUSPICIOUS_TLDS = [
    ".xyz", ".top", ".biz", ".click", ".gq", ".info", ".tk", ".cf", ".ml", ".ga"
]

# --- Function to check domain credibility ---
def check_domain(url):
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        tld = "." + domain.split('.')[-1]

        # Check blacklisted domains
        if any(bad_domain in domain for bad_domain in BLACKLISTED_DOMAINS):
            return False

        # Check suspicious TLDs
        if tld in SUSPICIOUS_TLDS:
            return False

        # Check domain age via WHOIS
        whois_info = whois.whois(domain)
        creation_date = whois_info.creation_date

        if isinstance(creation_date, list):
            creation_date = creation_date[0]

        if not creation_date:
            return False
        
        age_in_days = (datetime.now() - creation_date).days
        if age_in_days < 180:  # Less than 6 months = suspicious
            return False

        return True

    except Exception as e:
        print(f"❌ WHOIS Error for {url}: {e}")
        return False

# --- Main credibility check ---
for coll_name in collections:
    collection = db[coll_name]
    print(f"\n🔎 Vérification de la collection: {coll_name}")

    today = datetime.now().strftime("%Y-%m-%d")
    articles = list(collection.find({"date": today}))

    print(f"Articles trouvés aujourd'hui : {len(articles)}")

    removed_count = 0

    for article in articles:
        url = article.get("url", "")

        if url:
            is_valid = check_domain(url)

            if not is_valid:
                collection.delete_one({"_id": article["_id"]})
                removed_count += 1

            time.sleep(random.uniform(1, 2))  # simulate human behavior

    print(f"🗑️ Articles supprimés (non crédibles) : {removed_count}")

print("\n✅ Vérification de crédibilité terminée pour toutes les collections.")

client.close()
