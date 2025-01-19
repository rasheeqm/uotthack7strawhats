import json
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
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
        # Attempt to locate the desktop search bar
        search_box = WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "input.d-none.d-sm-block.form-control"))
        )
        print("Desktop search bar found.")
    except:
        # Fall back to locating the mobile search bar
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

        # Remove unwanted characters from unit price for sorting
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

def search_grocery_tracker(store_type_value, specific_store_value, search_term):
    """
    Automates the Grocery Tracker website to select a store and perform a search.
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
        # Open Grocery Tracker website
        driver.get("https://grocerytracker.ca/")
        print("Page loaded.")

        # Select the store type (e.g., "No Frills")
        store_type_dropdown = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "select.form-select"))
        )
        store_type_selector = Select(store_type_dropdown)
        store_type_selector.select_by_value(store_type_value)
        print(f"Selected store type: {store_type_value}")

        # Select the specific store (e.g., "Rocco's NOFRILLS Toronto")
        specific_store_dropdown = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//select[@class='form-select'][2]"))  # Second dropdown
        )
        specific_store_selector = Select(specific_store_dropdown)
        specific_store_selector.select_by_value(specific_store_value)
        print(f"Selected specific store: {specific_store_value}")

        # Locate the appropriate search bar
        search_box = locate_search_bar(driver)
        search_box.send_keys(search_term)
        print(f"Search term entered: {search_term}")

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
        for idx, result in enumerate(results, start=1):
            print(f"Product {idx}:")
            print(f"  Title: {result['title']}")
            print(f"  Subtitle: {result['subtitle']}")
            print(f"  Price: {result['prices']}")
            print(f"  Unit Size: {result['unit_size']}")
            print(f"  Unit Price: {result['unit_price']}")
            print("-" * 50)

        # Find the cheapest product by numeric unit price
        if results:
            cheapest_product = min(results, key=lambda x: x["numeric_unit_price"])
            print(f"Cheapest product: {cheapest_product['title']} - {cheapest_product['unit_price']}")
            return {
                "search_term": search_term,
                "cheapest_product": cheapest_product
            }
        else:
            print("No results found to determine the cheapest product.")
            return {
                "search_term": search_term,
                "cheapest_product": None
            }

    except Exception as e:
        print(f"An error occurred: {e}")
        return {
            "search_term": search_term,
            "cheapest_product": None
        }

    finally:
        driver.quit()

if __name__ == "__main__":
    # Input values
    store_type_value = "nofrills"  # Value for "No Frills"
    specific_store_value = "3643"  # Value for "Rocco's NOFRILLS Toronto"

    # List of search items
    search_items = ["milk", "bread", "eggs"]

    # Output JSON file
    output_file = "cheapest_products.json"

    all_results = []

    # Perform searches
    for search_term in search_items:
        print(f"Searching for: {search_term}")
        result = search_grocery_tracker(store_type_value, specific_store_value, search_term)
        all_results.append(result)

    # Write all results to the same JSON file
    with open(output_file, "w") as f:
        json.dump(all_results, f, indent=4)

    print(f"All results written to {output_file}")
