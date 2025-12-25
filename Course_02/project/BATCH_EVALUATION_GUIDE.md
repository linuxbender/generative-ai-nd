# Batch Evaluation Guide

This guide explains how to use the batch evaluation system to test the NASA RAG system across multiple questions and get aggregate performance metrics.

## Overview

The batch evaluation system:
1. Loads questions from `evaluation_dataset.txt`
2. For each question, runs the complete RAG pipeline:
   - Retrieves relevant documents from ChromaDB
   - Formats context with deduplication and sorting
   - Generates answer using LLM
   - Computes RAGAS quality metrics
3. Prints per-question results and aggregate statistics
4. Optionally saves results to JSON file

## Prerequisites

1. **ChromaDB Backend** - Run the embedding pipeline first:
   ```bash
   export OPENAI_API_KEY="your-key"
   export OPENAI_BASE_URL="https://openai.vocareum.com/v1"  # Optional
   
   python3 embedding_pipeline.py --openai-key $OPENAI_API_KEY --data-path .
   ```

2. **Evaluation Dataset** - The `evaluation_dataset.txt` file with sample questions

3. **Dependencies** - All required packages installed:
   ```bash
   pip install -r requirements.txt
   ```

## Basic Usage

### Simple Batch Evaluation

Run evaluation on all questions in the dataset:

```bash
python3 batch_evaluate.py --openai-key YOUR_API_KEY
```

### With Vocareum Endpoint

```bash
export OPENAI_API_KEY="voc-10694876731266774594167694c2af1d65632.81978761"
export OPENAI_BASE_URL="https://openai.vocareum.com/v1"

python3 batch_evaluate.py --openai-key $OPENAI_API_KEY --openai-base-url $OPENAI_BASE_URL
```

### Verbose Output

Print detailed per-question results:

```bash
python3 batch_evaluate.py --openai-key YOUR_KEY --verbose
```

### Save Results to File

Save evaluation results to JSON:

```bash
python3 batch_evaluate.py --openai-key YOUR_KEY --output evaluation_results.json
```

## Command-Line Options

| Option | Description | Default |
|--------|-------------|---------|
| `--openai-key` | OpenAI API key | `OPENAI_API_KEY` env var |
| `--openai-base-url` | Custom OpenAI endpoint URL | `OPENAI_BASE_URL` env var |
| `--model` | Model for generation | `gpt-3.5-turbo` |
| `--n-results` | Documents to retrieve per question | `3` |
| `--dataset` | Path to evaluation dataset | `evaluation_dataset.txt` |
| `--chroma-dir` | ChromaDB directory | `chroma_db_openai` |
| `--collection` | Collection name | `nasa_mission_docs` |
| `--verbose` | Print detailed results | `False` |
| `--output` | Save results to JSON file | None |

## Output Format

### Aggregate Statistics

```
📊 AGGREGATE STATISTICS
──────────────────────────────────────────────────────────────────────────────
Total Questions: 10
Successful: 10 (100.0%)
Failed: 0 (0.0%)

📈 RAGAS METRICS SUMMARY
──────────────────────────────────────────────────────────────────────────────
Metric                    Mean     Median   StDev    Min      Max     
───────────────────────── ──────── ──────── ──────── ──────── ────────
response_relevancy        0.847    0.855    0.042    0.785    0.912
faithfulness              0.763    0.771    0.058    0.682    0.851
context_precision         0.691    0.703    0.073    0.589    0.785
```

### Per-Question Results (with --verbose)

```
📝 PER-QUESTION RESULTS
──────────────────────────────────────────────────────────────────────────────

[Question 1] What was Apollo 11 and when did it take place?
  ✓ Retrieved: 3 documents
  ✓ Answer: Apollo 11 was the first crewed mission to land on the Moon...
  📊 Metrics:
     - response_relevancy: 0.892
     - faithfulness: 0.834
     - context_precision: 0.756

[Question 2] What went wrong during the Apollo 13 mission?
  ✓ Retrieved: 3 documents
  ✓ Answer: During Apollo 13, an oxygen tank exploded...
  📊 Metrics:
     - response_relevancy: 0.855
     - faithfulness: 0.771
     - context_precision: 0.703
```

## Interpreting Results

### RAGAS Metrics

1. **Response Relevancy** (Target: > 0.8)
   - Measures how relevant the answer is to the question
   - Higher scores indicate better question-answer alignment
   - Low scores suggest the model is answering the wrong question

2. **Faithfulness** (Target: > 0.7)
   - Measures how grounded the answer is in the retrieved context
   - Higher scores indicate less hallucination
   - Low scores suggest the model is making up information

3. **Context Precision** (Target: > 0.6)
   - Measures how relevant the retrieved documents are
   - Higher scores indicate better retrieval quality
   - Low scores suggest retrieval needs improvement

### Success Criteria

- **Excellent**: All metrics above target, success rate 100%
- **Good**: Most metrics above target, success rate > 90%
- **Acceptable**: Average metrics above 0.6, success rate > 80%
- **Needs Improvement**: Metrics below 0.6 or success rate < 80%

## JSON Output Format

When using `--output`, the JSON file contains:

```json
{
  "statistics": {
    "total_questions": 10,
    "successful": 10,
    "failed": 0,
    "metrics": {
      "response_relevancy": {
        "mean": 0.847,
        "median": 0.855,
        "stdev": 0.042,
        "min": 0.785,
        "max": 0.912,
        "count": 10
      },
      "faithfulness": { ... },
      "context_precision": { ... }
    }
  },
  "results": [
    {
      "question": "What was Apollo 11?",
      "answer": "Apollo 11 was...",
      "context": "Retrieved Context...",
      "retrieved_docs": 3,
      "metrics": {
        "response_relevancy": 0.892,
        "faithfulness": 0.834,
        "context_precision": 0.756
      },
      "expected_info": "- First Moon landing\n- July 1969...",
      "response_type": "Factual historical summary",
      "error": null
    }
  ]
}
```

## Troubleshooting

### "No module named 'chromadb'"

Install dependencies:
```bash
pip install -r requirements.txt
```

### "OpenAI API key required"

Set environment variable or pass as argument:
```bash
export OPENAI_API_KEY="your-key"
# Or
python3 batch_evaluate.py --openai-key your-key
```

### "Failed to initialize ChromaDB"

Run the embedding pipeline first:
```bash
python3 embedding_pipeline.py --openai-key $OPENAI_API_KEY --data-path .
```

### "No questions loaded from dataset"

Ensure `evaluation_dataset.txt` exists in the current directory or specify path:
```bash
python3 batch_evaluate.py --dataset path/to/evaluation_dataset.txt
```

### RAGAS Evaluation Errors

If RAGAS evaluation fails:
- Check network connectivity (RAGAS needs to download tokenizers)
- Use a valid OpenAI API key
- Ensure contexts are not empty
- Check the error message in the output

## Examples

### Quick Evaluation

```bash
# Set credentials
export OPENAI_API_KEY="voc-10694876731266774594167694c2af1d65632.81978761"
export OPENAI_BASE_URL="https://openai.vocareum.com/v1"

# Run evaluation
python3 batch_evaluate.py --openai-key $OPENAI_API_KEY
```

### Detailed Analysis

```bash
# Run with verbose output and save to file
python3 batch_evaluate.py \
  --openai-key $OPENAI_API_KEY \
  --openai-base-url $OPENAI_BASE_URL \
  --verbose \
  --output results_$(date +%Y%m%d_%H%M%S).json
```

### Custom Configuration

```bash
# Use different model and retrieve more documents
python3 batch_evaluate.py \
  --openai-key $OPENAI_API_KEY \
  --model gpt-4 \
  --n-results 5 \
  --chroma-dir my_chroma_db \
  --collection my_collection
```

## Integration with CI/CD

Add to your test pipeline:

```bash
#!/bin/bash
set -e

# Run batch evaluation
python3 batch_evaluate.py \
  --openai-key $OPENAI_API_KEY \
  --output test_results.json

# Check exit code (fails if success rate < 50%)
if [ $? -eq 0 ]; then
  echo "✅ Batch evaluation passed"
else
  echo "❌ Batch evaluation failed"
  exit 1
fi
```

## Best Practices

1. **Run After Changes** - Evaluate after modifying RAG components
2. **Track Over Time** - Save results with timestamps to track improvements
3. **Compare Models** - Test different models and configurations
4. **Analyze Failures** - Use `--verbose` to understand failure patterns
5. **Monitor Metrics** - Set up alerts if metrics fall below thresholds

## Next Steps

After running batch evaluation:

1. **Review Results** - Check aggregate metrics and per-question performance
2. **Identify Issues** - Look for patterns in failed questions
3. **Iterate** - Adjust retrieval, chunking, or prompts based on results
4. **Re-evaluate** - Run again to verify improvements
5. **Document** - Save results and learnings for future reference
