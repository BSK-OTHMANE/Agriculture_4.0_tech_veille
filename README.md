# Veille Agricole 4.0 - Scraper Project

This project collects scientific articles related to **"Agriculture 4.0"** from multiple sources, and stores them into a MongoDB database.

## 📚 Project Structure

```
├── scrape_ieee.py                # Scrapes IEEE Xplore (relevant + newest)
├── scrape_wiley.py               # Scrapes Wiley Online Library (relevant + newest)
├── scrape_springer.py            # Scrapes SpringerLink (relevant + newest)
├── scrape_google_scholar.py      # Fetches articles from Google Scholar using SerpAPI
├── daily_scraper_scheduler.py    # Runs all scrapers automatically every day at a scheduled time
├── veille_agriculture/           # MongoDB database where all articles are stored
└── README.md                     # This file
```

## ⚙️ How to Use

1. Install the required Python libraries:

```bash
pip install selenium webdriver-manager pymongo schedule requests beautifulsoup4
```

2. Make sure **MongoDB** is running locally (`localhost:27017`).

3. Run the scheduler:

```bash
python daily_scraper_scheduler.py
```

- The scheduler will automatically run all scrapers **once per day** at the configured time.
- Each scraper waits for page content to load before extracting articles.

## 📦 Collections in MongoDB

- `ieee_agriculture_4_0`
- `wiley_agriculture_4_0`
- `springer_agriculture_4_0`
- `scholar_agriculture_4_0`

Each collection contains **only new articles**. Duplicates are automatically avoided.

## 🧠 Features

- **Human-like behavior**: randomized delays, multiple User-Agent headers.
- **Incremental updates**:
  - For relevant results (relevance mode): updates and refreshes collection.
  - For newest results (latest mode): adds only genuinely new articles.
- **Separation by source**: Each scraper handles a specific source separately.
- **Easy scheduling**: Uses Python `schedule` to run daily.

## 🛠️ Customization

- You can **change the scheduled time** in `daily_scraper_scheduler.py`:

```python
schedule.every().day.at("10:00").do(run_all_scrapers)
```

(Change `10:00` to any time you prefer.)

- To **add a new source** later, just create a new script and add it inside the scheduler.

---

> 🧩 Project created for academic purposes: **Veille Technologique - Agriculture 4.0**  
> Developed with ❤️ and Python.

---
