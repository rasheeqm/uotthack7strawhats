import json

# Path to the JSON file
file_path = "../data/ingredient_to_price_and_url.json"

# Load and parse the JSON file
with open(file_path, 'r') as file:
    data = json.load(file)

# Access the ingredients
ingredients = data.get("ingredients", [])

# Print each ingredient's details
for ingredient in ingredients:
    name = ingredient.get("name")
    price = ingredient.get("price")
    url = ingredient.get("url")
    print(f"Name: {name}, Price: ${price:.2f}, URL: {url}")
