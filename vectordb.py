import json
from sentence_transformers import SentenceTransformer
import chromadb

# Step 1: Load JSON file
def load_json(file_path):
    with open(file_path, "r") as f:
        data = json.load(f)
    return data

# Step 2: Extract "description" key values from JSON
def extract_descriptions(data):
    descriptions = []
    for item in data:
        if "description" in item:
            descriptions.append(item["description"])
    return descriptions

# Step 3: Convert descriptions to embeddings using BERT
def generate_embeddings(descriptions):
    # Load pre-trained BERT model
    model = SentenceTransformer("all-MiniLM-L6-v2")  # A lightweight and efficient model
    embeddings = model.encode(descriptions, convert_to_numpy=True)
    return embeddings

# Step 4: Store embeddings in ChromaDB
def store_in_chromadb(descriptions, embeddings):
    # Initialize Chroma client with persistence
    client = chromadb.PersistentClient()

    # Create or get a collection
    collection_name = "descriptions_collection"
    collection = client.get_or_create_collection(name=collection_name)

    # Add data to the collection
    ids = [f"id_{i}" for i in range(len(descriptions))]  # Unique IDs for each description
    collection.add(
        ids=ids,
        documents=descriptions,
        embeddings=embeddings.tolist(),  # Convert numpy array to list
    )

    # Persist the database
    print(f"Data stored in ChromaDB collection: {collection_name}")

# Step 5: Main function to process JSON and store data
def main(json_file_path):
    # Load and process JSON
    data = load_json(json_file_path)
    descriptions = extract_descriptions(data)
    
    if not descriptions:
        print("No descriptions found in the JSON file.")
        return
    
    # Generate embeddings
    embeddings = generate_embeddings(descriptions)
    
    # Store embeddings in ChromaDB
    store_in_chromadb(descriptions, embeddings)
    print("Process complete!")

# Example usage
if __name__ == "__main__":
    json_file_path = "/Users/rohitshelke/Downloads/NutritionalInfo.foods.json"  # Replace with your JSON file path
    main(json_file_path)
