import requests
import random
import time
from datetime import datetime
from pymongo import MongoClient
from dotenv import load_dotenv
import os

load_dotenv() 

# --- Settings ---
SERPAPI_API_KEY = os.getenv("SERPAPI_KEY")
QUERY = "Agriculture 4.0"
MONGO_URI = "mongodb://localhost:27017/"
DB_NAME = "veille_agriculture"
RELEVANT_COLLECTION = "scholar_agriculture_4_0_relevant"
NEWEST_COLLECTION = "scholar_agriculture_4_0_newest"

# --- User-Agents ---
user_agents = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_5) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 15_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.4 Mobile/15E148 Safari/604.1"
]

# --- MongoDB Setup ---
client = MongoClient(MONGO_URI)
db = client[DB_NAME]
relevant_collection = db[RELEVANT_COLLECTION]
newest_collection = db[NEWEST_COLLECTION]

# --- Function to search and collect articles ---
def search_google_scholar(query, scisbd_value):
    search_mode = "newest" if scisbd_value in [1, 2] else "relevance"
    print(f"🔎 Searching [{search_mode}] articles...")

    params = {
        "engine": "google_scholar",
        "q": query,
        "hl": "en",
        "num": "20",
        "api_key": SERPAPI_API_KEY,
        "scisbd": scisbd_value
    }

    headers = {
        "User-Agent": random.choice(user_agents)
    }

    # Simulate human behavior
    time.sleep(random.uniform(2, 5))

    response = requests.get("https://serpapi.com/search", headers=headers, params=params)
    time.sleep(random.uniform(1, 3))

    data = response.json()
    articles = []
    current_date = datetime.now().strftime("%Y-%m-%d")

    if "organic_results" in data:
        for article in data["organic_results"]:
            title = article.get('title', "No Title")
            url = article.get('link', "No URL")
            snippet = article.get('snippet', "No Snippet")
            publication_info = article.get('publication_info', {}).get('summary', "No Publication Info")
            citations = article.get('inline_links', {}).get('cited_by', {}).get('total', None)
            cached_link = article.get('inline_links', {}).get('cached_page_link', None)

            articles.append({
                "source": "Google Scholar",
                "title": title,
                "url": url,
                "snippet": snippet,
                "publication_info": publication_info,
                "citations": citations,
                "cached_link": cached_link,
                "search_mode": search_mode,
                "date":current_date
            })
    else:
        print(f"⚠️ No {search_mode} articles found!")

    return articles

# --- Fetch articles ---
relevant_articles = search_google_scholar(QUERY, scisbd_value=0)
newest_articles = search_google_scholar(QUERY, scisbd_value=2)

# --- Insert Relevant Articles (refresh all) ---
if relevant_articles:
    relevant_collection.delete_many({})
    relevant_collection.insert_many(relevant_articles)
    print(f"✅ {len(relevant_articles)} relevant articles inserted into '{RELEVANT_COLLECTION}'.")
else:
    print("⚠️ No relevant articles to insert.")

# --- Insert Newest Articles (insert only new) ---
inserted_count = 0
for article in newest_articles:
    if not newest_collection.find_one({"title": article["title"]}):
        newest_collection.insert_one(article)
        inserted_count += 1

print(f"✅ {inserted_count} new newest articles inserted into '{NEWEST_COLLECTION}'.")

client.close()


