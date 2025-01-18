import argparse
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support.ui import Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
import chromedriver_autoinstaller

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
        results = WebDriverWait(driver, 10).until(
            EC.presence_of_all_elements_located((By.CLASS_NAME, "search-result-item"))  # Adjust locator if needed
        )
        print(f"Number of results found: {len(results)}")

        # Extract and display search results
        for idx, result in enumerate(results):
            print(f"{idx + 1}: {result.text}")

    except Exception as e:
        print(f"An error occurred: {e}")

    finally:
        driver.quit()

if __name__ == "__main__":
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="Search Grocery Tracker website.")
    parser.add_argument("search_term", type=str, help="The term to search for")
    args = parser.parse_args()

    # Values for dropdown selections
    store_type_value = "nofrills"  # Value for "No Frills"
    specific_store_value = "3643"  # Value for "Rocco's NOFRILLS Toronto"

    # Perform the search
    search_grocery_tracker(store_type_value, specific_store_value, args.search_term)
