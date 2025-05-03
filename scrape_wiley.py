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

# Setup MongoDB
client = MongoClient("mongodb://localhost:27017/")
db = client["veille_agriculture"]

# Random User-Agents
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_5) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36"
]

def create_driver():
    options = Options()
    user_agent = random.choice(USER_AGENTS)
    options.add_argument(f"user-agent={user_agent}")
    return webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

def scrape_wiley(url, collection_name):
    driver = create_driver()
    driver.get(url)

    try:
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'li.search__item'))
        )
    except:
        print(f"❌ Timeout while loading {collection_name}.")
        driver.quit()
        return

    time.sleep(random.uniform(3, 6))

    articles = []
    results = driver.find_elements(By.CSS_SELECTOR, 'li.search__item')
    print(f"Found {len(results)} articles for {collection_name}.")

    collection = db[collection_name]
    
    current_date = datetime.now().strftime("%Y-%m-%d")


    for item in results:
        try:
            title_elem = item.find_element(By.CSS_SELECTOR, 'h2.meta__title a')
            title = title_elem.text
            url = title_elem.get_attribute('href')
        except:
            title, url = "No Title", "No URL"

        try:
            authors = item.find_element(By.CSS_SELECTOR, 'div.meta__authors').text
        except:
            authors = "No Authors"

        try:
            journal = item.find_element(By.CSS_SELECTOR, 'a.publication_meta_serial').text
        except:
            journal = "No Journal"

        try:
            publication_date = item.find_element(By.CSS_SELECTOR, 'p.meta__epubDate').text.replace("First published: ", "")
        except:
            publication_date = "No Date"

        article = {
            "source": "Wiley Online Library",
            "title": title,
            "url": url,
            "authors": authors,
            "journal": journal,
            "publication_date": publication_date,
            "date":current_date
        }

        # Insert only if not already existing
        if not collection.find_one({"title": title, "url": url}):
            articles.append(article)

    driver.quit()

    if articles:
        collection.insert_many(articles)
        print(f"✅ Inserted {len(articles)} new articles into '{collection_name}'.")
    else:
        print(f"⚠️ No new articles to insert for '{collection_name}'.")

# --- Main ---

# URLs
earliest_url = "https://onlinelibrary.wiley.com/action/doSearch?AllField=Agriculture+4.0&startPage=0&sortBy=Earliest"
relevant_url = "https://onlinelibrary.wiley.com/action/doSearch?AllField=Agriculture+4.0&startPage=0&sortBy=relevancy"

# Scrape both
scrape_wiley(earliest_url, "wiley_agriculture_4_0_newest")
scrape_wiley(relevant_url, "wiley_agriculture_4_0_relevant")
