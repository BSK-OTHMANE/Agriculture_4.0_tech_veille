import schedule
import time
import subprocess

def run_all_scrapers():
    print("🚀 Starting daily scraping...")
    
    subprocess.run(["E:/anaconda/python.exe", "scrape_ieee.py"])
    subprocess.run(["E:/anaconda/python.exe", "scrape_wiley.py"])
    subprocess.run(["E:/anaconda/python.exe", "scrape_springer.py"])
    subprocess.run(["E:/anaconda/python.exe", "scrape_google_scholar.py"])
    
    print("✅ All scrapers finished!")

# Schedule once today at 00:32
schedule.every().day.at("10.00").do(run_all_scrapers)

print("📅 Scheduler is running... Waiting for 10:00...")

while True:
    schedule.run_pending()
    time.sleep(60)  # Check every 1 min
