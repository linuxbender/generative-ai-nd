# Error & Info Tab Guide

## Overview

The chat interface now includes **Error & Info log tabs** in the sidebar to provide persistent message history. This ensures important messages don't disappear and helps distinguish between critical errors and informational warnings.

## Features

### 📋 System Messages Section

Located in the sidebar below the evaluation metrics, the System Messages section contains two tabs:

#### ❌ Errors Tab
- **Purpose**: Displays critical errors that prevent the system from functioning
- **Examples**:
  - LLM Generation Error (invalid API key, network issues)
  - System Error (ChromaDB initialization failure)
  - Retrieval Error (database query problems)
- **Features**:
  - Shows last 10 errors with timestamps
  - Expandable entries (click to see full details)
  - "Clear Error Log" button to reset
  - Most recent error expanded by default

#### ℹ️ Info Tab
- **Purpose**: Displays informational messages and non-critical warnings
- **Examples**:
  - Embedding Dimension Mismatch (model version mismatch)
  - RAGAS Evaluation Warning (evaluation failures)
- **Features**:
  - Shows last 10 info messages with timestamps
  - Expandable entries with context-aware solutions
  - "Clear Info Log" button to reset
  - Most recent message expanded by default
  - **Built-in solutions** for common issues

## Message Flow

### Example: Embedding Dimension Mismatch

1. **User asks a question** in the chat
2. **System attempts retrieval** from ChromaDB
3. **Mismatch detected**: Collection has 1536-dim embeddings, code uses 384-dim
4. **Transient error shown** in main chat area
5. **Message logged** to Info tab automatically
6. **Message persists** - user can review it anytime
7. **Solution displayed** when expanding the info message

```
Info Tab Entry:
──────────────────────────────────────────
🔵 Embedding Dimension Mismatch - 14:23:45
Error retrieving documents: Collection 
expecting embedding with dimension of 
1536, got 384

💡 Solution: Delete `chroma_db_openai/` 
and recreate embeddings with: 
python3 embedding_pipeline.py \
  --openai-key $OPENAI_API_KEY \
  --data-path .
```

## Usage Examples

### Viewing Error History

1. Open the chat interface
2. Navigate to sidebar
3. Scroll to **"📋 System Messages"**
4. Click **"❌ Errors"** tab
5. See all recent errors with timestamps
6. Click any entry to expand and view details

### Viewing Info Messages

1. Navigate to **"📋 System Messages"**
2. Click **"ℹ️ Info"** tab
3. See all informational messages
4. Expand to see solutions and details

### Clearing Logs

- Click **"Clear Error Log"** in Errors tab to reset error history
- Click **"Clear Info Log"** in Info tab to reset info history
- Each tab maintains independent history

## Message Categories

### Errors (Critical)
| Type | Description | Impact |
|------|-------------|--------|
| LLM Generation Error | OpenAI API failures | Chat stops, no response generated |
| System Error | Core system failures | Chat stops, system unavailable |
| Retrieval Error | Database query failures | Chat stops, no context retrieved |

### Info (Non-Critical)
| Type | Description | Impact |
|------|-------------|--------|
| Embedding Dimension Mismatch | Model version mismatch | Retrieval fails but system continues |
| RAGAS Evaluation Warning | Evaluation metric failures | Response generated but not evaluated |

## Benefits

✅ **No More Lost Messages**: All errors and warnings are logged persistently

✅ **Clear Distinction**: Errors vs Info helps prioritize issues

✅ **Built-in Solutions**: Info messages include troubleshooting steps

✅ **Timestamped History**: Track when issues occurred

✅ **Non-Intrusive**: Expandable entries don't clutter the UI

✅ **Easy Cleanup**: Clear buttons to reset logs when fixed

## Testing the Feature

### Test 1: Info Message (Embedding Mismatch)

```bash
# Setup: Create database with old model
export OPENAI_API_KEY="your-key"
python3 embedding_pipeline.py --embedding-model text-embedding-ada-002 --data-path .

# Run chat (uses text-embedding-3-small by default)
streamlit run chat.py

# Ask a question - dimension mismatch occurs
# Check: Info tab shows the error with solution
```

### Test 2: Error Message (Invalid API Key)

```bash
# Setup: Use invalid API key
export OPENAI_API_KEY="sk-invalid-key-123"
streamlit run chat.py

# Ask a question
# Check: Errors tab shows "LLM Generation Error"
```

### Test 3: Message Persistence

```bash
# Trigger multiple errors/info messages
# Close and reopen the expanders
# Check: Messages remain visible
# Check: Timestamps show chronological order
```

## Implementation Details

### Session State Variables

```python
st.session_state.error_log = []  # List of error entries
st.session_state.info_log = []   # List of info entries
```

### Log Entry Structure

```python
{
    "timestamp": pd.Timestamp.now(),
    "message": "Error description",
    "type": "Error Type"
}
```

### Smart Categorization

The system automatically categorizes messages:

```python
# Embedding dimension mismatch → Info
if "expecting embedding with dimension" in str(e):
    st.session_state.info_log.append(...)
# Other errors → Errors
else:
    st.session_state.error_log.append(...)
```

## UI Layout

```
┌─────────────────────────────────────┐
│ Sidebar                             │
├─────────────────────────────────────┤
│ Configuration                       │
│ ...                                 │
│ Evaluation Metrics                  │
│ ...                                 │
├─────────────────────────────────────┤
│ 📋 System Messages                  │
│ ┌───────────────┬─────────────────┐ │
│ │ ❌ Errors     │ ℹ️ Info         │ │
│ └───────────────┴─────────────────┘ │
│ ┌─────────────────────────────────┐ │
│ │ Total errors: 3                 │ │
│ │                                 │ │
│ │ 🔴 LLM Generation Error - 14:30 │ │
│ │ [Click to expand]               │ │
│ │                                 │ │
│ │ 🔴 System Error - 14:25         │ │
│ │ [Click to expand]               │ │
│ │                                 │ │
│ │ [Clear Error Log]               │ │
│ └─────────────────────────────────┘ │
└─────────────────────────────────────┘
```

## Troubleshooting

**Q: Messages not appearing in tabs?**
- Check that the error actually occurred (look for error in main chat)
- Verify session state is initialized
- Check browser console for JavaScript errors

**Q: Tabs not visible?**
- Update Streamlit to latest version: `pip install --upgrade streamlit`
- Clear browser cache
- Restart Streamlit server

**Q: Clear button not working?**
- Ensure you're clicking the correct "Clear" button (each tab has its own)
- Check that page reruns after clicking

**Q: Too many messages in history?**
- Logs automatically limit to last 10 entries
- Use Clear button to reset if needed

## Best Practices

1. **Regular Monitoring**: Check tabs periodically during development
2. **Clear After Fixing**: Use Clear buttons after resolving issues
3. **Read Solutions**: Info tab provides actionable solutions - follow them
4. **Save Critical Errors**: Copy error text before clearing if needed for reporting
5. **Check Timestamps**: Verify errors aren't stale from previous sessions

## Future Enhancements

Potential improvements for future versions:

- Export logs to file
- Filter by error type
- Search functionality
- Email notifications for critical errors
- Integration with external monitoring systems
- Configurable retention period
- Severity levels (low, medium, high)

## Related Documentation

- `TROUBLESHOOTING.md` - Detailed troubleshooting guide
- `FINAL_REPORT.md` - Complete implementation analysis
- `REVIEWER_GUIDE.md` - Quick start guide
