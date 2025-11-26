import time
import requests
from bs4 import BeautifulSoup
import smtplib
from email.mime.text import MIMEText
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

from job_scraper_utils import extract_job_description # NEW IMPORT
import re
import os
import csv
from datetime import datetime, timedelta



EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASS = os.getenv("EMAIL_PASS")

CSV_FILE = "sent_jobs.csv"


# ---------------------------------------------------------
#     CSV STORAGE HELPERS
# ---------------------------------------------------------

def ensure_csv_exists():
    if not os.path.exists(CSV_FILE):
        with open(CSV_FILE, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["job_id", "timestamp"])  # header




def load_recent_sent_jobs():
    ensure_csv_exists()
    recent_jobs = set()
    cutoff = datetime.utcnow() - timedelta(hours=24)

    with open(CSV_FILE, "r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            job_time = datetime.fromisoformat(row["timestamp"])
            if job_time >= cutoff:
                recent_jobs.add(row["job_id"])
    return recent_jobs






def is_recent(text):
    """
    Returns True if the posted/updated time is:
    - "moments ago"
    - "1 hour ago"
    - "2 hours ago"
    - ...
    - "5 hours ago"
    """
    text = text.lower()

    if "moments ago" in text:
        return True

    # Find "X hours ago"
    if text and isinstance(text, str):
        match = re.search(r"(\d+)\s+hours?", text)

    else:
        # Handle the case where text is not a valid string
        print("The input 'text' is not a valid string.")

    if match:
        hours = int(match.group(1))
        return hours <= 5

    return False


def get_dice_job_results(keyword, location=""):
    from selenium.webdriver.chrome.options import Options

    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")

    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=chrome_options
    )

    driver.get("https://www.dice.com/jobs")

    # Wait for search bar
    WebDriverWait(driver, 20).until(
        EC.visibility_of_element_located((By.NAME, "q"))
    )


    # Fill keyword
    search_box = driver.find_element(By.NAME, "q")
    search_box.clear()
    search_box.send_keys(keyword)

    # Fill location
    try:
        location_box = driver.find_element(By.NAME, "location")
        location_box.clear()
        location_box.send_keys(location)
    except:
        pass

    search_box.send_keys(Keys.RETURN)

    # Wait for cards
    WebDriverWait(driver, 30).until(
        EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div[data-testid='job-card']"))
    )

    time.sleep(2)

    job_cards = driver.find_elements(By.CSS_SELECTOR, "div[data-testid='job-card']")
    results = []

    for card in job_cards:
        try:
            title_elem = card.find_element(By.CSS_SELECTOR, "a[data-testid='job-search-job-detail-link']")
            job_title = title_elem.text.strip()
            job_link = title_elem.get_attribute("href")

            company_elem = card.find_elements(By.CSS_SELECTOR, "a[href*='company-profile']")
            company = company_elem[0].text.strip() if company_elem else "N/A"

            location_elem = card.find_elements(By.CSS_SELECTOR, "p.text-sm.font-normal.text-zinc-600")
            location_text = location_elem[0].text.strip() if location_elem else "N/A"

            # Extract posted text from card
            posted_text = ""
            for elem in location_elem:
                t = elem.text.lower()
                if "ago" in t or "today" in t:
                    posted_text = t
                    break

            # Fetch job detail page for more accurate posted time
            detail_res = requests.get(job_link, timeout=10)
            soup = BeautifulSoup(detail_res.text, "html.parser")
            detail_dates = soup.find("li", {"data-cy": "postedDate"})


            # detail_dates = soup.find_all("span", {"data-testid": "posted-date"})
            for d in detail_dates:
                posted_text = d.get_text(strip=True)
                break

            if posted_text and is_recent(posted_text):
                results.append({
                    "title": job_title,
                    "company": company,
                    "location": location_text,
                    "posted": posted_text,
                    "link": job_link
                })

        except Exception:
            continue

    driver.quit()
    return results


def send_email_for_job(job):
    # --- NEW: Extract Job Description ---
    job_description = extract_job_description(job['link'])

    email_body = f"""
    A NEW job has been posted that matches your criteria!
    
    Title: {job['title']}
    Company: {job['company']}
    Location: {job['location']}
    Posted: {job['posted']}
    
    Link: {job['link']}
    
    --- JOB DESCRIPTION ---
    
    {job_description}
    
    -----------------------
    """

    msg = MIMEText(email_body)
    
#    msg = MIMEText(f"New job posted:\n{job['title']}\n{job['link']}")
    msg["Subject"] = f"New Job: {job['title']}"
    msg["From"] = EMAIL_USER
    msg["To"] = EMAIL_USER

    print(f"\n📧 Sending email for NEW job: {job['title']} at {job['company']}\n")
    
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(EMAIL_USER, EMAIL_PASS)
        server.sendmail(EMAIL_USER, EMAIL_USER, msg.as_string())





def load_sent_jobs():
    """Load already emailed job links from file."""
    if not os.path.exists(SENT_JOBS_FILE):
        print("unable to open previous file")
        return set()
    with open(SENT_JOBS_FILE, "r") as f:
        return set(line.strip() for line in f if line.strip())



def save_sent_job(job_id):
    with open(CSV_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([job_id, datetime.utcnow().isoformat()])





def display_job_results(jobs):
    if not jobs:
        print("No recent jobs found (<= 5 hours old).")
        return

    for i, job in enumerate(jobs, 1):
        print(f"Job #{i}")
        print(f"  Title:   {job['title']}")
        print(f"  Company: {job['company']}")
        print(f"  Location: {job['location']}")
        print(f"  Posted:  {job['posted']}")
        print(f"  Link:    {job['link']}")
        print("-" * 40)




# ... all your existing functions above this line ...

if __name__ == "__main__":
    
    # Define the list of keywords you want to search for
    # You can add or remove keywords here easily
    search_keywords = ["SAP BW", "Datasphere"]
    loc = os.getenv("JOB_LOCATION", "") # Location can remain the same for all searches

    print("--- Starting Job Search Program ---")
    
    # Load job links sent in the last 24 hours from CSV once
    sent_jobs = load_recent_sent_jobs()
    
    # Loop through each keyword in the list
    for kw in search_keywords:
        print(f"\n##################################################")
        print(f"## Searching for jobs with keyword: {kw} ##")
        print(f"##################################################\n")
        
        # 1. Get job results for the current keyword
        jobs = get_dice_job_results(kw, loc)
        
        # 2. Display the found jobs (optional)
        display_job_results(jobs)

        # 3. Process and send emails for new jobs
        for job in jobs:
            # The job link serves as the unique ID for checking if it's already sent
            job_id = job["link"] 
            
            if job_id not in sent_jobs:
                # Send email only for NEW jobs
                send_email_for_job(job)

                # Add the job ID to the set of sent jobs immediately to avoid duplicates in the same run
                sent_jobs.add(job_id)
                
                # Mark as sent in the CSV file
                save_sent_job(job_id)
            else:
                print(f"Skipping already-sent job: {job['title']} ({job['link']})")
                
    print("\n--- Job Search Program Finished ---")






# if __name__ == "__main__":

# #    kw = input("Enter job keyword: ")
# #    loc = input("Enter location (optional): ")

#     kw = os.getenv("JOB_KEYWORD", "SAP FICO")
#     loc = os.getenv("JOB_LOCATION", "")


#     jobs = get_dice_job_results(kw, loc)
#     display_job_results(jobs)

#     # Load job links sent in last 24 hours from CSV
#     sent_jobs = load_recent_sent_jobs()

    
#     for job in jobs:
#         if job["link"] not in sent_jobs:
#             # Send email only for NEW jobs
#             send_email_for_job(job)

#             # Mark as sent
#             save_sent_job(job["link"])
#         else:
#             print(f"Skipping already-sent job: {job['title']} ({job['link']})")

























