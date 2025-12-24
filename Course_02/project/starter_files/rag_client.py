import chromadb
from chromadb.config import Settings
from typing import Dict, List, Optional
from pathlib import Path

def discover_chroma_backends() -> Dict[str, Dict[str, str]]:
    """
    Discover available ChromaDB backends in the project directory
    
    Returns:
        Dictionary mapping backend keys to backend information
        Format: {key: {directory, collection_name, display_name, document_count}}
    """
    backends = {}
    current_dir = Path(".")
    
    # Look for ChromaDB directories - directories that match specific criteria
    chroma_dirs = [d for d in current_dir.glob("*") if d.is_dir() and 
                   ("chroma" in d.name.lower() or "db" in d.name.lower())]
    
    # Loop through each discovered directory
    for chroma_dir in chroma_dirs:
        # Wrap connection attempt in try-except block for error handling
        try:
            # Initialize database client with directory path and configuration settings
            client = chromadb.PersistentClient(
                path=str(chroma_dir),
                settings=Settings(anonymized_telemetry=False)
            )
            
            # Retrieve list of available collections from the database
            collections = client.list_collections()
            
            # Loop through each collection found
            for collection in collections:
                # Create unique identifier key combining directory and collection names
                backend_key = f"{chroma_dir.name}_{collection.name}"
                
                # Build information dictionary containing:
                try:
                    # Get document count with fallback for unsupported operations
                    doc_count = collection.count()
                except:
                    doc_count = "Unknown"
                
                backends[backend_key] = {
                    # Store directory path as string
                    "directory": str(chroma_dir),
                    # Store collection name
                    "collection_name": collection.name,
                    # Create user-friendly display name
                    "display_name": f"{chroma_dir.name} - {collection.name} ({doc_count} docs)",
                    # Store document count
                    "document_count": doc_count
                }
        
        except Exception as e:
            # Handle connection or access errors gracefully
            # Create fallback entry for inaccessible directories
            error_msg = str(e)
            # Include error information in display name with truncation
            if len(error_msg) > 50:
                error_msg = error_msg[:50] + "..."
            
            backends[f"{chroma_dir.name}_error"] = {
                "directory": str(chroma_dir),
                "collection_name": "error",
                "display_name": f"{chroma_dir.name} - Error: {error_msg}",
                "document_count": 0
            }
    
    # Return complete backends dictionary with all discovered collections
    return backends

def initialize_rag_system(chroma_dir: str, collection_name: str):
    """
    Initialize the RAG system with specified backend (cached for performance)
    
    Args:
        chroma_dir: Directory path for ChromaDB
        collection_name: Name of the collection to use
    
    Returns:
        ChromaDB collection object
    """
    # Create a chromadb persistentclient
    client = chromadb.PersistentClient(
        path=chroma_dir,
        settings=Settings(anonymized_telemetry=False)
    )
    
    # Return the collection with the collection_name
    collection = client.get_collection(name=collection_name)
    return collection

def retrieve_documents(collection, query: str, n_results: int = 3, 
                      mission_filter: Optional[str] = None) -> Optional[Dict]:
    """
    Retrieve relevant documents from ChromaDB with optional filtering
    
    Args:
        collection: ChromaDB collection object
        query: Search query text
        n_results: Maximum number of results to return
        mission_filter: Optional mission name to filter by (e.g., 'apollo_11', 'apollo_13', 'challenger')
    
    Returns:
        Query results dictionary with documents, metadatas, distances, and ids
    """
    # Initialize filter variable to None (represents no filtering)
    where_filter = None
    
    # Check if filter parameter exists and is not set to "all" or equivalent
    if mission_filter and mission_filter.lower() not in ["all", "none", ""]:
        # If filter conditions are met, create filter dictionary with appropriate field-value pairs
        where_filter = {"mission": mission_filter}
    
    # Execute database query with the following parameters:
    results = collection.query(
        # Pass search query in the required format
        query_texts=[query],
        # Set maximum number of results to return
        n_results=n_results,
        # Apply conditional filter (None for no filtering, dictionary for specific filtering)
        where=where_filter
    )
    
    # Return query results to caller
    return results

def format_context(documents: List[str], metadatas: List[Dict]) -> str:
    """
    Format retrieved documents into context
    
    Args:
        documents: List of document text strings
        metadatas: List of metadata dictionaries for each document
    
    Returns:
        Formatted context string ready for LLM consumption
    """
    if not documents:
        return ""
    
    # Initialize list with header text for context section
    context_parts = ["Retrieved Context from NASA Mission Documents:\n"]
    
    # Loop through paired documents and their metadata using enumeration
    for i, (doc, metadata) in enumerate(zip(documents, metadatas), 1):
        # Extract mission information from metadata with fallback value
        mission = metadata.get("mission", "unknown")
        # Clean up mission name formatting (replace underscores, capitalize)
        mission_clean = mission.replace("_", " ").title()
        
        # Extract source information from metadata with fallback value
        source = metadata.get("source", "unknown")
        
        # Extract category information from metadata with fallback value
        category = metadata.get("document_category", "unknown")
        # Clean up category name formatting (replace underscores, capitalize)
        category_clean = category.replace("_", " ").title()
        
        # Create formatted source header with index number and extracted information
        source_header = f"\n[Source {i}] Mission: {mission_clean} | Document: {source} | Category: {category_clean}"
        # Add source header to context parts list
        context_parts.append(source_header)
        
        # Check document length and truncate if necessary
        max_doc_length = 1000
        if len(doc) > max_doc_length:
            doc_content = doc[:max_doc_length] + "..."
        else:
            doc_content = doc
        
        # Add truncated or full document content to context parts list
        context_parts.append(doc_content)
    
    # Join all context parts with newlines and return formatted string
    return "\n".join(context_parts)