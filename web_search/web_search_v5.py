import time
import json
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support.ui import Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
import chromedriver_autoinstaller
from bs4 import BeautifulSoup


def locate_search_bar(driver):
    """
    Locate the search bar dynamically based on the screen size (desktop or mobile).
    """
    try:
        search_box = WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "input.d-none.d-sm-block.form-control"))
        )
        print("Desktop search bar found.")
    except:
        search_box = WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "input.d-block.d-sm-none.form-control"))
        )
        print("Mobile search bar found.")

    return search_box


def extract_results(driver):
    """
    Extract search results using BeautifulSoup.
    """
    soup = BeautifulSoup(driver.page_source, "html.parser")
    cards = soup.select(".col .card.border-dark")
    print(f"Found {len(cards)} products.")

    results = []
    for card in cards:
        title = card.select_one(".card-title").text.strip() if card.select_one(".card-title") else "N/A"
        subtitle = card.select_one(".card-subtitle").text.strip() if card.select_one(".card-subtitle") else "N/A"
        prices = card.select_one(".cardPrices .sale").text.strip() if card.select_one(".cardPrices .sale") else "N/A"
        unit_size = card.select_one(".unitSize").text.strip() if card.select_one(".unitSize") else "N/A"
        unit_price = card.select_one(".unitPrice").text.strip() if card.select_one(".unitPrice") else "N/A"

        numeric_unit_price = float(unit_price.split("/")[0].replace("$", "").strip()) if "/" in unit_price else float(
            "inf"
        )

        results.append({
            "title": title,
            "subtitle": subtitle,
            "prices": prices,
            "unit_size": unit_size,
            "unit_price": unit_price,
            "numeric_unit_price": numeric_unit_price,
        })

    return results


def select_store(driver, store_type_value, specific_store_value, retries=2):
    """
    Select the store type and specific store, with retry logic if it fails.
    """
    attempt = 0
    while attempt <= retries:
        try:
            print("Selecting store type and specific store...")

            # Select the store type
            store_type_dropdown = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "select.form-select"))
            )
            store_type_selector = Select(store_type_dropdown)
            store_type_selector.select_by_value(store_type_value)
            print(f"Selected store type: {store_type_value}")

            # Select the specific store
            specific_store_dropdown = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//select[@class='form-select'][2]"))
            )
            specific_store_selector = Select(specific_store_dropdown)
            specific_store_selector.select_by_value(specific_store_value)
            print(f"Selected specific store: {specific_store_value}")

            return  # Success, exit the function
        except Exception as e:
            print(f"Error selecting store: {e}. Retrying in 2 seconds... (Attempt {attempt + 1}/{retries + 1})")
            attempt += 1
            time.sleep(2)  # Wait before retrying
            driver.get("https://grocerytracker.ca/")  # Reload the website

    raise Exception("Failed to select store type and value after retries.")


def search_grocery_tracker(store_type_value, specific_store_value, grocery_items):
    """
    Automates the Grocery Tracker website to select a store and perform a search for a list of grocery items.
    """
    # Automatically install ChromeDriver
    chromedriver_autoinstaller.install()

    # Configure Chrome options
    options = Options()
    options.add_argument('--headless')  # Optional: Run in headless mode
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')

    driver = webdriver.Chrome(options=options)

    try:
        # Prepare a dictionary to store the cheapest products for each grocery item
        cheapest_products = {}

        for search_term in grocery_items:
            print(f"Searching for: {search_term}")

            # Open Grocery Tracker website and refresh for each search
            driver.get("https://grocerytracker.ca/")
            print("Page loaded.")

            # Select the store type and value with retry
            select_store(driver, store_type_value, specific_store_value)

            # Locate the appropriate search bar
            search_box = locate_search_bar(driver)
            search_box.clear()
            search_box.send_keys(search_term)

            # Locate and click the search button
            search_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "button.btn.btn-primary"))
            )
            search_button.click()
            print("Search button clicked.")

            # Wait for search results to load
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".col .card.border-dark"))
            )
            print("Search results loaded.")

            # Extract results
            results = extract_results(driver)

            # Find the cheapest product by numeric unit price
            if results:
                cheapest_product = min(results, key=lambda x: x["numeric_unit_price"])
                print(f"Cheapest product for {search_term}: {cheapest_product['title']} - {cheapest_product['unit_price']}")
                cheapest_products[search_term] = cheapest_product
            else:
                print(f"No results found for {search_term}.")
                cheapest_products[search_term] = None

            # Wait for 3 seconds before the next search
            time.sleep(3)

        # Save all cheapest products to a JSON file
        with open("search_to_cheapest_ingredient.json", "w") as f:
            json.dump(cheapest_products, f, indent=4)
        print("Cheapest products written to search_to_cheapest_ingredient.json")

    except Exception as e:
        print(f"An error occurred: {e}")

    finally:
        driver.quit()


# Example usage
if __name__ == "__main__":
    store_type_value = "nofrills"  # Example store type value
    specific_store_value = "3643"  # Example specific store value
    grocery_items = ["banana", "apple", "milk"]  # Example grocery items

    search_grocery_tracker(store_type_value, specific_store_value, grocery_items)