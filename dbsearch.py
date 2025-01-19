from sentence_transformers import SentenceTransformer
import chromadb

def search_chromadb(query, persist_directory="chroma_persistence", collection_name="descriptions_collection"):
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

    # Step 5: Display results
    print("Search Results:")
    for i, doc in enumerate(results["documents"]):
        print(f"{i+1}. {doc} (ID: {results['ids'][i]})")

    return results

# Example usage
if __name__ == "__main__":
    query = "The ingredient egg"  # Replace with your search query
    search_chromadb(query)
