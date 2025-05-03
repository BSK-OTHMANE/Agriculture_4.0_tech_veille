import random
import time
from datetime import datetime
import requests
from bs4 import BeautifulSoup
from pymongo import MongoClient

# MongoDB Setup
client = MongoClient("mongodb://localhost:27017/")
db = client["veille_agriculture"]

# List of User-Agents
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_5) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Firefox/113.0",
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:113.0) Gecko/20100101 Firefox/113.0"
]

def fetch_articles(url, collection_name):
    headers = {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive"
    }

    # Random human-like delay
    time.sleep(random.uniform(2, 5))

    response = requests.get(url, headers=headers)

    # Another small random wait
    time.sleep(random.uniform(1, 3))

    soup = BeautifulSoup(response.content, "html.parser")
    base_url = "https://link.springer.com"

    results = soup.select('li[data-test="search-result-item"]')
    print(f"Found {len(results)} articles for {collection_name}.")

    collection = db[collection_name]
    
    current_date = datetime.now().strftime("%Y-%m-%d")

    articles = []
    for item in results:
        try:
            title_tag = item.select_one('h3[data-test="title"] a')
            desc_tag = item.select_one('div[data-test="description"]')
            date_tag = item.select_one('span[data-test="published"]')
            authors_tag = item.select_one('span[data-test="authors"]')

            title = title_tag.get_text(strip=True) if title_tag else "No Title"
            url_article = base_url + title_tag['href'] if title_tag and title_tag.has_attr('href') else "No URL"
            description = desc_tag.get_text(strip=True) if desc_tag else "No Description"
            published_date = date_tag.get_text(strip=True) if date_tag else "No Date"
            authors = authors_tag.get_text(strip=True) if authors_tag else "No Authors"

            article = {
                "source": "SpringerLink",
                "title": title,
                "url": url_article,
                "description": description,
                "authors": authors,
                "published": published_date,
                "date":current_date
            }

            # Insert only if not already existing
            if not collection.find_one({"title": title, "url": url_article}):
                articles.append(article)

        except Exception as e:
            print(f"❌ Error parsing an article: {e}")

    if articles:
        collection.insert_many(articles)
        print(f"✅ {len(articles)} new articles inserted into '{collection_name}'.")
    else:
        print(f"⚠️ No new articles to insert for '{collection_name}'.")

# --- Main ---

# URLs
newest_url = "https://link.springer.com/search?new-search=true&query=agriculture+4.0&content-type=article&content-type=research&sortBy=newestFirst"
relevant_url = "https://link.springer.com/search?new-search=true&query=agriculture+4.0&content-type=article&content-type=research&sortBy=relevance"

# Fetch both
fetch_articles(newest_url, "springer_agriculture_4_0_newest")
fetch_articles(relevant_url, "springer_agriculture_4_0_relevant")
