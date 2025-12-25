#!/usr/bin/env python3
"""
NASA RAG Chat with RAGAS Evaluation Integration

Enhanced version of the simple RAG chat that includes real-time evaluation
and feedback collection for continuous improvement.
"""

import streamlit as st
import os
import json
import pandas as pd

import ragas_evaluator
import rag_client
import llm_client

from pathlib import Path
from typing import Dict, List, Optional

# RAGAS imports
try:
    from ragas import SingleTurnSample
    RAGAS_AVAILABLE = True
except ImportError:
    RAGAS_AVAILABLE = False
    st.warning("RAGAS not available. Install with: pip install ragas")

# Page configuration
st.set_page_config(
    page_title="NASA RAG Chat with Evaluation",
    page_icon="🚀",
    layout="wide"
)

def discover_chroma_backends() -> Dict[str, Dict[str, str]]:
    """Discover available ChromaDB backends in the project directory"""

    return rag_client.discover_chroma_backends()

#@st.cache_resource
def initialize_rag_system(chroma_dir: str, collection_name: str):
    """Initialize the RAG system with specified backend (cached for performance)"""

    try:
       return rag_client.initialize_rag_system(chroma_dir, collection_name)
    except Exception as e:
        return None, False, str(e)

def retrieve_documents(collection, query: str, n_results: int = 3, 
                      mission_filter: Optional[str] = None) -> Optional[Dict]:
    """Retrieve relevant documents from ChromaDB with optional filtering"""
    try:
        return rag_client.retrieve_documents(collection, query, n_results, mission_filter)
    except Exception as e:
        error_msg = f"Error retrieving documents: {e}"
        # Check if it's an embedding dimension mismatch (info) or actual error
        if "expecting embedding with dimension" in str(e):
            # This is informational - about model mismatch
            st.session_state.info_log.append({
                "timestamp": pd.Timestamp.now(),
                "message": error_msg,
                "type": "Embedding Dimension Mismatch"
            })
        else:
            # This is an actual error
            st.session_state.error_log.append({
                "timestamp": pd.Timestamp.now(),
                "message": error_msg,
                "type": "Retrieval Error"
            })
        st.error(error_msg)
        return None

def format_context(documents: List[str], metadatas: List[Dict], distances: Optional[List[float]] = None,
                  ids: Optional[List[str]] = None) -> str:
    """Format retrieved documents into context with deduplication"""
    
    return rag_client.format_context(documents, metadatas, distances, ids)

def generate_response(openai_key, user_message: str, context: str, 
                     conversation_history: List[Dict], model: str = "gpt-3.5-turbo",
                     base_url: Optional[str] = None) -> str:
    """Generate response using OpenAI with context"""
    try:
        return llm_client.generate_response(openai_key, user_message, context, conversation_history, model, base_url)
    except Exception as e:
        return f"Error generating response: {e}"

def evaluate_response_quality(question: str, answer: str, contexts: List[str]) -> Dict[str, float]:
    """Evaluate response quality using RAGAS metrics"""
    try:
        return ragas_evaluator.evaluate_response_quality(question, answer, contexts)
    except Exception as e:
        return {"error": f"Evaluation failed: {str(e)}"}

def display_evaluation_metrics(scores: Dict[str, float]):
    """Display evaluation metrics in the sidebar"""
    if "error" in scores:
        st.sidebar.error(f"Evaluation Error: {scores['error']}")
        return
    
    st.sidebar.subheader("📊 Response Quality")
    
    for metric_name, score in scores.items():
        if isinstance(score, (int, float)):
            # Color code based on score
            if score >= 0.8:
                color = "green"
            elif score >= 0.6:
                color = "orange"
            else:
                color = "red"
            
            st.sidebar.metric(
                label=metric_name.replace('_', ' ').title(),
                value=f"{score:.3f}",
                delta=None
            )
            
            # Add progress bar
            st.sidebar.progress(score)

def main():
    st.title("🚀 NASA Space Mission Chat with Evaluation")
    st.markdown("Chat with AI about NASA space missions with real-time quality evaluation")
    
    # Initialize session state
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "current_backend" not in st.session_state:
        st.session_state.current_backend = None
    if "last_evaluation" not in st.session_state:
        st.session_state.last_evaluation = None
    if "last_contexts" not in st.session_state:
        st.session_state.last_contexts = []
    if "system_messages" not in st.session_state:
        st.session_state.system_messages = []
    
    # Sidebar for configuration
    with st.sidebar:
        st.header("🔧 Configuration")
        
        # Discover available backends
        with st.spinner("Discovering ChromaDB backends..."):
            available_backends = discover_chroma_backends()
        
        if not available_backends:
            st.error("No ChromaDB backends found!")
            st.info("Please run the embedding pipeline first:\n`python run_text_embedding.py`")
            st.stop()
        
        # Backend selection
        st.subheader("📊 ChromaDB Backend")
        backend_options = {k: v["display_name"] for k, v in available_backends.items()}
        
        selected_backend_key = st.selectbox(
            "Select Document Collection",
            options=list(backend_options.keys()),
            format_func=lambda x: backend_options[x],
            help="Choose which document collection to use for retrieval"
        )
        
        selected_backend = available_backends[selected_backend_key]
        
        # API Key input
        st.subheader("🔑 OpenAI Settings")
        openai_key = st.text_input(
            "OpenAI API Key", 
            type="password",
            value=os.getenv("OPENAI_API_KEY", ""),
            help="Enter your OpenAI API key"
        )
        
        # Base URL input (optional for Vocareum or custom endpoints)
        openai_base_url = st.text_input(
            "OpenAI Base URL (Optional)",
            value=os.getenv("OPENAI_BASE_URL", ""),
            help="Custom OpenAI API base URL (e.g., https://openai.vocareum.com/v1). Leave empty for default."
        )
        
        if not openai_key:
            st.warning("Please enter your OpenAI API key")
            st.stop()
        else:
            os.environ["CHROMA_OPENAI_API_KEY"] = openai_key
            if openai_base_url:
                os.environ["OPENAI_BASE_URL"] = openai_base_url
        
        # Model selection
        model_choice = st.selectbox(
            "OpenAI Model",
            options=["gpt-3.5-turbo", "gpt-4", "gpt-4-turbo-preview"],
            help="Choose the OpenAI model for responses"
        )
        
        # Retrieval settings
        st.subheader("🔍 Retrieval Settings")
        n_docs = st.slider("Documents to retrieve", 1, 10, 3)
        
        # Evaluation settings
        st.subheader("📊 Evaluation Settings")
        enable_evaluation = st.checkbox("Enable RAGAS Evaluation", value=RAGAS_AVAILABLE)
        
        # Initialize RAG system when backend changes
        if (st.session_state.current_backend != selected_backend_key):
            st.session_state.current_backend = selected_backend_key
            # Clear cache to force reinitialization
            st.cache_resource.clear()
    
    # Initialize RAG system
    with st.spinner("Initializing RAG system..."):
        try:
            collection = initialize_rag_system(
                selected_backend["directory"], 
                selected_backend["collection_name"]
            )
            success = True
            error = None
        except Exception as e:
            collection = None
            success = False
            error = str(e)
    
    if not success:
        st.error(f"Failed to initialize RAG system: {error}")
        st.stop()
    
    # Display evaluation metrics if available
    if st.session_state.last_evaluation and enable_evaluation:
        display_evaluation_metrics(st.session_state.last_evaluation)
    
    # Add System Messages in sidebar
    st.sidebar.markdown("---")
    st.sidebar.subheader("📋 System Messages")
    
    if st.session_state.system_messages:
        st.sidebar.caption(f"Total messages: {len(st.session_state.system_messages)}")
        for idx, log_entry in enumerate(reversed(st.session_state.system_messages[-10:])):  # Show last 10
            # Choose icon based on severity
            icon = "🔴" if log_entry['severity'] == "error" else "🔵"
            with st.sidebar.expander(f"{icon} {log_entry['type']} - {log_entry['timestamp'].strftime('%H:%M:%S')}", expanded=(idx==0)):
                st.text(log_entry['message'])
                # Add helpful info for specific message types
                if "embedding with dimension" in log_entry['message']:
                    st.info("**Solution:** Delete `chroma_db_openai/` and recreate embeddings with: `python3 embedding_pipeline.py --openai-key $OPENAI_API_KEY --data-path .`")
        if st.sidebar.button("Clear Message Log", key="clear_messages"):
            st.session_state.system_messages = []
            st.rerun()
    else:
        st.sidebar.info("No messages")
    
    # Display chat messages
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
    
    # Chat input
    if prompt := st.chat_input("Ask about NASA space missions..."):
        # Add user message to chat history
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Generate assistant response
        with st.chat_message("assistant"):
            # Create a persistent error container
            error_container = st.container()
            
            with st.spinner("Searching documents and generating response..."):
                try:
                    # Retrieve relevant documents
                    docs_result = retrieve_documents(
                        collection, 
                        prompt, 
                        n_docs
                    )
                    
                    # Format context
                    context = ""
                    contexts_list = []
                    if docs_result and docs_result.get("documents"):
                        # Extract distances and IDs for deduplication and sorting
                        distances = docs_result.get("distances", [None])[0] if docs_result.get("distances") else None
                        ids = docs_result.get("ids", [None])[0] if docs_result.get("ids") else None
                        
                        context = format_context(
                            docs_result["documents"][0], 
                            docs_result["metadatas"][0],
                            distances,
                            ids
                        )
                        contexts_list = docs_result["documents"][0]
                        st.session_state.last_contexts = contexts_list
                    
                    # Generate response
                    response = generate_response(
                        openai_key, 
                        prompt, 
                        context, 
                        st.session_state.messages[:-1],
                        model_choice,
                        openai_base_url if openai_base_url else None
                    )
                    
                    # Check for error in response
                    if response.startswith("Error generating response:"):
                        error_msg = response
                        st.session_state.system_messages.append({
                            "timestamp": pd.Timestamp.now(),
                            "message": error_msg,
                            "type": "LLM Generation Error",
                            "severity": "error"
                        })
                        with error_container:
                            st.error("⚠️ **Generation Error (Persistent)**")
                            st.error(response)
                            st.info("💡 **Troubleshooting:** Check your API key, base URL, and network connection.")
                        st.stop()
                    
                    st.markdown(response)
                    
                    # Evaluate response quality if enabled
                    if enable_evaluation and RAGAS_AVAILABLE:
                        with st.spinner("Evaluating response quality..."):
                            try:
                                evaluation_scores = evaluate_response_quality(
                                    prompt, 
                                    response, 
                                    contexts_list
                                )
                                st.session_state.last_evaluation = evaluation_scores
                            except Exception as eval_error:
                                # Evaluation errors are informational, not critical
                                eval_msg = f"Evaluation failed: {eval_error}"
                                st.session_state.system_messages.append({
                                    "timestamp": pd.Timestamp.now(),
                                    "message": eval_msg,
                                    "type": "RAGAS Evaluation Warning",
                                    "severity": "info"
                                })
                                with error_container:
                                    st.warning(f"⚠️ {eval_msg}")
                                    st.session_state.last_evaluation = {"error": str(eval_error)}
                
                except Exception as e:
                    error_msg = f"An error occurred: {str(e)}"
                    # Categorize the error type
                    if "expecting embedding with dimension" in str(e):
                        severity = "info"
                        error_type = "Embedding Dimension Mismatch"
                    else:
                        severity = "error"
                        error_type = "System Error"
                    
                    st.session_state.system_messages.append({
                        "timestamp": pd.Timestamp.now(),
                        "message": error_msg,
                        "type": error_type,
                        "severity": severity
                    })
                    with error_container:
                        if severity == "error":
                            st.error("⚠️ **System Error (Persistent)**")
                        else:
                            st.warning("⚠️ **System Warning (Persistent)**")
                        st.error(error_msg)
                        st.info("💡 **Troubleshooting:**")
                        st.markdown("""
                        - Check ChromaDB backend is initialized
                        - Verify documents are indexed correctly
                        - Check API credentials and network
                        - See TROUBLESHOOTING.md for details
                        """)
                    import logging
                    logging.error(f"Chat error: {str(e)}", exc_info=True)
                    st.stop()
        
        # Add assistant response to chat history
        st.session_state.messages.append({"role": "assistant", "content": response})
        st.rerun()


if __name__ == "__main__":
    main()
