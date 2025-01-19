import json
import requests
from typing import Dict, Any
from sentence_transformers import SentenceTransformer
import chromadb

def search_chromadb(query, persist_directory="chroma_persistence", collection_name="descriptions_collection"):
    """
    Searches ChromaDB for the given query and returns the top result.
    """
    # Step 1: Reopen the ChromaDB client
    client = chromadb.PersistentClient(path="chroma")

    # Step 2: Access the existing collection
    collection = client.get_collection(name=collection_name)

    # Step 3: Generate an embedding for the query
    model = SentenceTransformer("all-MiniLM-L6-v2")  # Use the same model as during storage
    query_embedding = model.encode([query], convert_to_numpy=True)

    # Step 4: Perform the query
    results = collection.query(
        query_embeddings=query_embedding.tolist(),
        n_results=1  # Number of results to return
    )

    # Return the top document
    return results

def retrieve_nutrition_information() -> Dict[str, Any]:
    """
    Retrieve Nutrition Information from the database for items in the price list.
    Returns a dictionary containing nutrition data for all items.
    """
    try:
        # Read the price list JSON
        with open('item_prices.json', 'r') as f:
            price_data = json.load(f)
        
        # Extract all item names from the price list
        item_names = [item['name'] for item in price_data.get('items', [])]
        
        # Search each item name using search_chromadb
        searched_names = [str(search_chromadb(item_name)['documents'][0][0]) for item_name in item_names]
        print("Searched Names:", searched_names)

        # Prepare the request to the nutrition API
        url = "http://127.0.0.1:8000/nutrition/nutrition/"
        data = {
            "name": searched_names
        }
        print("JSON Payload:", data)  # Debugging the request payload

        try:
            # Make the POST request to get nutrition data
            response = requests.post(url, json=data)  # Pass the dictionary directly
            response.raise_for_status()  # Raise an exception for HTTP errors
            return response.json()  # Return parsed JSON data
        except requests.exceptions.RequestException as e:
            print(f"Error during API call: {e}")
            return {}
    except (json.JSONDecodeError, FileNotFoundError) as e:
        print(f"Error reading the JSON file: {e}")
        return {}

if __name__ == "__main__":
    result = retrieve_nutrition_information()
    print("Nutrition Data:", result)
