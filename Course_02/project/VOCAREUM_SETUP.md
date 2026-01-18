# Vocareum OpenAI Connection Guide

## Overview

The NASA RAG Chat system now supports custom OpenAI API endpoints, including Vocareum. This allows you to use alternative OpenAI-compatible endpoints.

## Configuration

### Method 1: Environment Variables

Set the `OPENAI_BASE_URL` environment variable:

```bash
export OPENAI_API_KEY="voc-10694876731266774594167694c2af1d65632.81978761"
export OPENAI_BASE_URL="https://openai.vocareum.com/v1"
```

### Method 2: Command-Line Arguments

For the embedding pipeline, use the `--openai-base-url` argument:

```bash
python3 embedding_pipeline.py \
  --openai-key "voc-10694876731266774594167694c2af1d65632.81978761" \
  --openai-base-url "https://openai.vocareum.com/v1" \
  --data-path .
```

### Method 3: Streamlit UI

The chat interface includes an optional "OpenAI Base URL" input field in the sidebar. Simply enter your custom endpoint URL there.

## Usage Examples

### Processing Documents with Vocareum

```bash
# Set environment variables
export OPENAI_API_KEY="voc-10694876731266774594167694c2af1d65632.81978761"
export OPENAI_BASE_URL="https://openai.vocareum.com/v1"

# Run embedding pipeline
python3 embedding_pipeline.py --openai-key $OPENAI_API_KEY --data-path .

# The base URL is automatically picked up from the environment variable
```

Or explicitly specify it:

```bash
python3 embedding_pipeline.py \
  --openai-key "voc-10694876731266774594167694c2af1d65632.81978761" \
  --openai-base-url "https://openai.vocareum.com/v1" \
  --data-path . \
  --chroma-dir ./chroma_db_openai
```

### Running the Chat Interface

```bash
# Set environment variables
export OPENAI_API_KEY="voc-10694876731266774594167694c2af1d65632.81978761"
export OPENAI_BASE_URL="https://openai.vocareum.com/v1"

# Launch Streamlit
streamlit run chat.py
```

The interface will automatically populate the API key and base URL from environment variables, but you can override them in the UI if needed.

## Implementation Details

### LLM Client

The `llm_client.py` now accepts an optional `base_url` parameter:

```python
response = generate_response(
    openai_key="your-key",
    user_message="What was Apollo 11?",
    context="...",
    conversation_history=[],
    model="gpt-3.5-turbo",
    base_url="https://openai.vocareum.com/v1"  # Optional
)
```

If `base_url` is not provided, it checks the `OPENAI_BASE_URL` environment variable.

### Embedding Pipeline

The `ChromaEmbeddingPipelineTextOnly` class now accepts an optional `openai_base_url` parameter:

```python
pipeline = ChromaEmbeddingPipelineTextOnly(
    openai_api_key="your-key",
    openai_base_url="https://openai.vocareum.com/v1"  # Optional
)
```

### Chat Interface

The Streamlit chat interface includes an optional text input for the base URL in the sidebar settings.

## Troubleshooting

### Connection Errors

If you encounter connection errors:

1. Verify the base URL is correct (include `/v1` suffix)
2. Check that your API key is valid for the custom endpoint
3. Ensure you have network access to the endpoint
4. Test the connection with a simple curl command:

```bash
curl -H "Authorization: Bearer voc-10694876731266774594167694c2af1d65632.81978761" \
     https://openai.vocareum.com/v1/models
```

### API Key Format

Note that Vocareum API keys start with `voc-` rather than the standard OpenAI `sk-` prefix. This is normal and expected.

## Standard OpenAI

To use standard OpenAI (default behavior):

1. Don't set `OPENAI_BASE_URL` environment variable
2. Don't provide `--openai-base-url` argument
3. Leave the "OpenAI Base URL" field empty in the UI

The system will automatically use the default OpenAI endpoint.
