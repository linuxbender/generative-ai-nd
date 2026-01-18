from typing import Dict, List, Optional
from openai import OpenAI
import os

def generate_response(openai_key: str, user_message: str, context: str, 
                     conversation_history: List[Dict], model: str = "gpt-3.5-turbo",
                     base_url: Optional[str] = None) -> str:
    """
    Generate response using OpenAI with context
    
    Args:
        openai_key: OpenAI API key
        user_message: User's current message
        context: Retrieved context from RAG system
        conversation_history: Previous conversation messages
        model: OpenAI model to use (default: gpt-3.5-turbo)
        base_url: Optional custom base URL for OpenAI API (e.g., Vocareum)
    
    Returns:
        Generated response from the LLM
    """
    try:
        # Define system prompt - NASA expert persona
        system_prompt = """You are an expert NASA historian and space mission specialist with deep knowledge of:
- Apollo missions (Apollo 11, Apollo 13, and others)
- Space Shuttle missions (including Challenger)
- Technical mission details, procedures, and communications
- Astronaut biographies and crew compositions
- Mission transcripts and audio recordings

Your role is to provide accurate, detailed, and engaging responses about NASA space missions.
When answering questions:
1. Use the provided context from mission documents to support your answers
2. Be specific with facts, dates, crew names, and technical details
3. If the context doesn't contain relevant information, acknowledge this
4. Maintain a professional yet accessible tone
5. Cite sources when referencing specific documents or transcripts"""

        # Create OpenAI Client with optional custom base URL
        # Check environment variable if base_url not provided
        if base_url is None:
            base_url = os.getenv("OPENAI_BASE_URL")
        
        if base_url:
            client = OpenAI(api_key=openai_key, base_url=base_url)
        else:
            client = OpenAI(api_key=openai_key)
        
        # Build messages array
        messages = [{"role": "system", "content": system_prompt}]
        
        # Add conversation history (limit to last 10 messages to manage context)
        if conversation_history:
            # Limit history to avoid token limits
            recent_history = conversation_history[-10:]
            messages.extend(recent_history)
        
        # Set context in messages - add context before user message if available
        if context:
            context_message = f"Relevant information from mission documents:\n\n{context}\n\nPlease use this information to answer the user's question."
            messages.append({"role": "system", "content": context_message})
        
        # Add user message
        messages.append({"role": "user", "content": user_message})
        
        # Send request to OpenAI
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0.7,
            max_tokens=1000
        )
        
        # Return response
        return response.choices[0].message.content
        
    except Exception as e:
        return f"Error generating response: {str(e)}"