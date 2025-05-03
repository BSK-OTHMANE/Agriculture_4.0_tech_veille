import random
import time
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from pymongo import MongoClient

# List of User-Agents
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.6167.160 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_6) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.6099.199 Safari/537.36",
]

def get_driver():
    chrome_options = Options()
    user_agent = random.choice(USER_AGENTS)
    chrome_options.add_argument(f"user-agent={user_agent}")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--start-maximized")
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    return driver

def fetch_articles(url):
    driver = get_driver()
    driver.get(url)

    try:
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'div.result-item-align h3 a'))
        )
    except:
        print(f"❌ Timeout loading articles from {url}")
        driver.quit()
        return []

    time.sleep(random.uniform(3, 6))

    results = driver.find_elements(By.CSS_SELECTOR, 'div.result-item-align')
    print(f"Found {len(results)} articles from {url}")
    
    current_date = datetime.now().strftime("%Y-%m-%d")

    articles = []

    for item in results:
        try:
            title_elem = item.find_element(By.CSS_SELECTOR, 'h3 a')
            title = title_elem.text
            article_url = title_elem.get_attribute('href')
        except:
            title, article_url = "No Title", "No URL"

        try:
            authors = item.find_element(By.CSS_SELECTOR, 'p.author').text
        except:
            authors = "No Authors"

        try:
            conference = item.find_element(By.CSS_SELECTOR, 'div.description a').text
        except:
            conference = "No Conference"

        try:
            year = item.find_element(By.XPATH, ".//span[contains(text(),'Year:')]").text
        except:
            year = "No Year"

        articles.append({
            "source": "IEEE Xplore",
            "title": title,
            "url": article_url,
            "authors": authors,
            "conference": conference,
            "year": year,
            "date":current_date
        })

    driver.quit()
    return articles

# MongoDB setup
client = MongoClient("mongodb://localhost:27017/")
db = client["veille_agriculture"]
newest_collection = db["ieee_agriculture_4_0_newest"]
relevant_collection = db["ieee_agriculture_4_0_relevant"]

# URLs
newest_url = "https://ieeexplore.ieee.org/search/searchresult.jsp?queryText=Agriculture%204.0&highlight=true&returnType=SEARCH&returnFacets=ALL&sortType=newest"
relevant_url = "https://ieeexplore.ieee.org/search/searchresult.jsp?queryText=Agriculture%204.0&highlight=true&returnType=SEARCH&returnFacets=ALL"

# Fetch newest
newest_articles = fetch_articles(newest_url)

newest_to_insert = []
for article in newest_articles:
    if not newest_collection.find_one({"title": article["title"], "url": article["url"]}):
        newest_to_insert.append(article)

if newest_to_insert:
    newest_collection.insert_many(newest_to_insert)
    print(f"✅ {len(newest_to_insert)} new 'newest' articles inserted into MongoDB.")
else:
    print("⚠️ No new 'newest' articles to insert.")

# Fetch relevant
relevant_articles = fetch_articles(relevant_url)

if relevant_articles:
    relevant_collection.delete_many({})
    relevant_collection.insert_many(relevant_articles)
    print(f"✅ Replaced 'relevant' articles collection with {len(relevant_articles)} articles.")
else:
    print("⚠️ No 'relevant' articles found to insert.")
