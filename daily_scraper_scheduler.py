import schedule
import time
import subprocess

def run_all_scrapers():
    print("🚀 Starting daily scraping...")
    #run the sripts of the iee ,weily,springer,scholar,alerts
    subprocess.run(["E:/anaconda/python.exe", "scrape_ieee.py"])
    subprocess.run(["E:/anaconda/python.exe", "scrape_wiley.py"])
    subprocess.run(["E:/anaconda/python.exe", "scrape_springer.py"])
    subprocess.run(["E:/anaconda/python.exe", "scrape_google_scholar.py"])
    subprocess.run(["E:/anaconda/python.exe", "scrape_google_alert.py"])
    #run the ones of the talkwalker 
    # subprocess.run(["E:/anaconda/python.exe", "scrape_talkwalker\auto_save_to_talkwalkerfolder.py"])
    # subprocess.run(["E:/anaconda/python.exe", "scrape_talkwalker\extract_informations_from_talkwalker.py"])
    # run the cerdibility test 
    subprocess.run(["E:/anaconda/python.exe", "credibility_test.py"])
    print("✅ All scrapers finished!")

# Schedule once today at 00:32
schedule.every().day.at("22:00").do(run_all_scrapers)

print("📅 Scheduler is running... Waiting for 22:00...")

while True:
    schedule.run_pending()
    time.sleep(60)  # Check every 1 min
