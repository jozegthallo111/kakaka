import time
import csv
import os
import zipfile
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

CHROMEDRIVER_PATH = "/usr/local/bin/chromedriver"
CHROME_BINARY_PATH = "/opt/google/chrome-linux64/chrome"

BASE_URL = "https://www.pricecharting.com"
CATEGORY_URL = "https://www.pricecharting.com/category/pokemon-cards"
PROCESSED_CARDS_FILE = "scraped_cards.txt"
CSV_FILENAME = "allcorectpricees.csv"
ZIP_FILENAME = "allcorectpricees.zip"

def init_driver():
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920x1080")
    options.binary_location = CHROME_BINARY_PATH
    service = Service(CHROMEDRIVER_PATH)
    return webdriver.Chrome(service=service, options=options)

def fetch_console_urls(driver):
    driver.get(CATEGORY_URL)
    try:
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div.sets"))
        )
    except TimeoutException:
        print(f"⚠️ Timeout while loading CATEGORY_URL: {CATEGORY_URL}")
        return []

    anchors = driver.find_elements(By.CSS_SELECTOR, "a[href^='/console/']")
    urls = set()
    for a in anchors:
        href = a.get_attribute("href")
        text = a.text.lower()
        # Skip Japanese/Chinese sets
        if "japanese" in text or "chinese" in text:
            print(f"⏭️ Skipping set due to language: {text}")
            continue
        if href.startswith(BASE_URL + "/console/pokemon"):
            urls.add(href)
    return list(urls)

def get_card_links_from_console(driver, console_url):
    driver.get(console_url)
    time.sleep(2)  # let page load

    card_links = set()
    last_height = driver.execute_script("return document.body.scrollHeight")
    while True:
        # Scroll down to bottom
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)  # wait for lazy loading

        # Collect card links on the page
        cards = driver.find_elements(By.CSS_SELECTOR, "a[href^='/game/pokemon-promo/'], a[href^='/game/pokemon-']")
        # Added both promo and normal cards selector to catch cards under different URLs
        for card in cards:
            href = card.get_attribute("href")
            if href and href.startswith(BASE_URL + "/game/"):
                card_links.add(href)

        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            break
        last_height = new_height

    return list(card_links)

def clean_price(price_elem):
    if price_elem:
        text = price_elem.text.strip()
        return text if text != "-" else "N/A"
    return "N/A"

def fetch_card_data(driver, card_url):
    driver.get(card_url)
    try:
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "h1#product_name"))
        )
    except TimeoutException:
        print(f"⚠️ Timeout loading card page: {card_url}")
        return None

    try:
        name = driver.find_element(By.CSS_SELECTOR, "h1#product_name").text.strip()
    except NoSuchElementException:
        name = "N/A"

    prices = driver.find_elements(By.CSS_SELECTOR, "span.price.js-price")

    def get_optional_text(selector):
        try:
            return driver.find_element(By.CSS_SELECTOR, selector).text.strip()
        except NoSuchElementException:
            return "N/A"

    def get_image_url():
        for img in driver.find_elements(By.CSS_SELECTOR, "img"):
            src = img.get_attribute("src")
            if src and "1600.jpg" in src:
                return src
        return "N/A"

    return {
        "Name": name,
        "Raw Price": clean_price(prices[0]) if len(prices) > 0 else "N/A",
        "Grade 7 Price": clean_price(prices[1]) if len(prices) > 1 else "N/A",
        "Grade 8 Price": clean_price(prices[2]) if len(prices) > 2 else "N/A",
        "Grade 9 Price": clean_price(prices[3]) if len(prices) > 3 else "N/A",
        "Grade 9.5 Price": clean_price(prices[4]) if len(prices) > 4 else "N/A",
        "PSA 10 Price": clean_price(prices[5]) if len(prices) > 5 else "N/A",
        "Rarity": get_optional_text("td.details[itemprop='description']"),
        "Model Number": get_optional_text("td.details[itemprop='model-number']"),
        "Image URL": get_image_url(),
        "Card URL": card_url
    }

def save_to_csv(data, filename=CSV_FILENAME, write_header=False, mode='a'):
    if not data:
        print("⚠️ No data to save.")
        return
    with open(filename, mode, newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=data[0].keys())
        if write_header:
            writer.writeheader()
        writer.writerows(data)
    print(f"✅ Saved {len(data)} records to {filename}")

def zip_csv_file(csv_filename=CSV_FILENAME, zip_filename=ZIP_FILENAME):
    if os.path.exists(csv_filename):
        with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
            zipf.write(csv_filename, arcname=os.path.basename(csv_filename))
        print(f"📦 Zipped {csv_filename} to {zip_filename}")
    else:
        print(f"⚠️ Cannot zip, {csv_filename} not found.")

def load_processed_cards():
    if not os.path.exists(PROCESSED_CARDS_FILE):
        return set()
    with open(PROCESSED_CARDS_FILE, "r", encoding="utf-8") as f:
        return set(line.strip() for line in f if line.strip())

def main():
    driver = init_driver()
    try:
        console_urls = fetch_console_urls(driver)
        if not console_urls:
            print("⚠️ No console URLs found to process.")
            return

        processed_cards = load_processed_cards()
        all_cards_data = []
        first_save = not os.path.exists(CSV_FILENAME)
        processed_count = 0

        for console_url in console_urls:
            print(f"🕹️ Processing set: {console_url}")
            card_links = get_card_links_from_console(driver, console_url)
            if not card_links:
                print(f"⚠️ No cards found in set: {console_url}")
                continue

            for i, card_url in enumerate(card_links, 1):
                if card_url in processed_cards:
                    # Already processed this card
                    continue

                print(f"🔎 Scraping card {i}/{len(card_links)}: {card_url}")
                card_data = fetch_card_data(driver, card_url)
                if card_data:
                    all_cards_data.append(card_data)

                    # Save processed URL
                    with open(PROCESSED_CARDS_FILE, "a", encoding="utf-8") as f:
                        f.write(card_url + "\n")
                    processed_cards.add(card_url)
                    processed_count += 1

                # Save every 10 cards scraped
                if processed_count % 10 == 0 and all_cards_data:
                    save_to_csv(all_cards_data, write_header=first_save)
                    all_cards_data = []
                    first_save = False

                # Zip every 500 cards
                if processed_count > 0 and processed_count % 500 == 0:
                    zip_csv_file()

                time.sleep(1)  # be polite, avoid hammering server

        # Save any remaining data
        if all_cards_data:
            save_to_csv(all_cards_data, write_header=first_save)

        # Final zip after scraping
        zip_csv_file()

        # Debug info
        print(f"CSV file exists after scraping? {os.path.exists(CSV_FILENAME)}")
        print(f"CSV absolute path: {os.path.abspath(CSV_FILENAME)}")

    finally:
        driver.quit()
        print("👋 Driver closed.")

if __name__ == "__main__":
    main()
