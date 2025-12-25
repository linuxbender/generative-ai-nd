#!/usr/bin/env python3
"""
Batch Evaluation Script for NASA RAG System

This script loads evaluation_dataset.txt, runs the complete RAG pipeline 
(retrieve → build context → generate answer → compute RAGAS metrics) for 
each question, and prints per-question results plus aggregate statistics.

Usage:
    python3 batch_evaluate.py --openai-key YOUR_KEY [--openai-base-url URL]
    
Environment Variables:
    OPENAI_API_KEY - OpenAI API key (alternative to --openai-key)
    OPENAI_BASE_URL - OpenAI base URL for custom endpoints (optional)
"""

import argparse
import json
import logging
import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import statistics

# Import our components
import rag_client
import llm_client

# Try to import RAGAS evaluator
try:
    import ragas_evaluator
    RAGAS_AVAILABLE = True
except Exception as e:
    RAGAS_AVAILABLE = False
    logging.warning(f"RAGAS not available: {e}")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def parse_evaluation_dataset(file_path: str) -> List[Dict[str, str]]:
    """
    Parse evaluation_dataset.txt and extract questions with their expected responses.
    
    Args:
        file_path: Path to evaluation_dataset.txt
        
    Returns:
        List of dictionaries with 'question', 'expected_info', and 'response_type'
    """
    questions = []
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Split by question sections (## Question N:)
        question_sections = re.split(r'\n---\n', content)
        
        for section in question_sections:
            if not section.strip() or section.startswith('#'):
                continue
            
            # Extract question
            question_match = re.search(r'\*\*Question:\*\*\s*\n(.+?)(?=\n\*\*|\n\n|\Z)', section, re.DOTALL)
            if not question_match:
                continue
            
            question_text = question_match.group(1).strip()
            
            # Extract expected response information
            expected_match = re.search(r'\*\*Expected Response Should Include:\*\*\s*\n(.+?)(?=\n\*\*|\Z)', section, re.DOTALL)
            expected_info = expected_match.group(1).strip() if expected_match else ""
            
            # Extract response type
            response_type_match = re.search(r'\*\*Response Type:\*\*\s*\n(.+?)(?=\n|\Z)', section)
            response_type = response_type_match.group(1).strip() if response_type_match else "General"
            
            questions.append({
                'question': question_text,
                'expected_info': expected_info,
                'response_type': response_type
            })
    
    except FileNotFoundError:
        logger.error(f"Evaluation dataset not found: {file_path}")
        return []
    except Exception as e:
        logger.error(f"Error parsing evaluation dataset: {e}")
        return []
    
    logger.info(f"Loaded {len(questions)} questions from dataset")
    return questions


def run_single_evaluation(
    question: str,
    collection,
    openai_key: str,
    n_results: int = 3,
    model: str = "gpt-3.5-turbo",
    base_url: Optional[str] = None
) -> Dict:
    """
    Run complete RAG pipeline for a single question and evaluate.
    
    Args:
        question: Question to evaluate
        collection: ChromaDB collection
        openai_key: OpenAI API key
        n_results: Number of documents to retrieve
        model: Model to use for generation
        base_url: Optional custom base URL
        
    Returns:
        Dictionary with results including answer, context, and metrics
    """
    result = {
        'question': question,
        'answer': None,
        'context': None,
        'retrieved_docs': 0,
        'metrics': {},
        'error': None
    }
    
    try:
        # Step 1: Retrieve documents
        docs_result = rag_client.retrieve_documents(collection, question, n_results)
        
        if not docs_result or not docs_result.get("documents"):
            result['error'] = "No documents retrieved"
            return result
        
        result['retrieved_docs'] = len(docs_result["documents"][0])
        
        # Step 2: Format context with deduplication
        distances = docs_result.get("distances", [None])[0] if docs_result.get("distances") else None
        ids = docs_result.get("ids", [None])[0] if docs_result.get("ids") else None
        
        context = rag_client.format_context(
            docs_result["documents"][0],
            docs_result["metadatas"][0],
            distances,
            ids
        )
        result['context'] = context
        contexts_list = docs_result["documents"][0]
        
        # Step 3: Generate answer
        answer = llm_client.generate_response(
            openai_key,
            question,
            context,
            [],  # Empty conversation history for evaluation
            model,
            base_url
        )
        result['answer'] = answer
        
        # Check for generation errors
        if answer.startswith("Error generating response:"):
            result['error'] = answer
            return result
        
        # Step 4: Evaluate with RAGAS
        if RAGAS_AVAILABLE:
            try:
                metrics = ragas_evaluator.evaluate_response_quality(
                    question,
                    answer,
                    contexts_list
                )
                result['metrics'] = metrics
            except Exception as e:
                result['metrics'] = {'error': str(e)}
                logger.warning(f"Evaluation failed for question: {e}")
        else:
            result['metrics'] = {'info': 'RAGAS not available'}
    
    except Exception as e:
        result['error'] = str(e)
        error_msg = str(e)
        
        # Check if this is an embedding dimension mismatch - expected if collection uses different model
        if "expecting embedding with dimension" in error_msg:
            logger.warning(f"Embedding dimension mismatch (expected with different embedding models): {e}")
            logger.info("Note: This error can be ignored if you intentionally created the collection with a different embedding model")
        else:
            logger.error(f"Error in evaluation pipeline: {e}")
    
    return result


def calculate_statistics(results: List[Dict]) -> Dict:
    """
    Calculate aggregate statistics from evaluation results.
    
    Args:
        results: List of evaluation results
        
    Returns:
        Dictionary with aggregate statistics
    """
    stats = {
        'total_questions': len(results),
        'successful': 0,
        'failed': 0,
        'metrics': {}
    }
    
    # Collect all metric scores
    metric_scores = {}
    
    for result in results:
        if result.get('error'):
            stats['failed'] += 1
        else:
            stats['successful'] += 1
            
            # Collect metric scores
            for metric_name, score in result.get('metrics', {}).items():
                if isinstance(score, (int, float)) and metric_name != 'error':
                    if metric_name not in metric_scores:
                        metric_scores[metric_name] = []
                    metric_scores[metric_name].append(score)
    
    # Calculate statistics for each metric
    for metric_name, scores in metric_scores.items():
        if scores:
            stats['metrics'][metric_name] = {
                'mean': statistics.mean(scores),
                'median': statistics.median(scores),
                'stdev': statistics.stdev(scores) if len(scores) > 1 else 0.0,
                'min': min(scores),
                'max': max(scores),
                'count': len(scores)
            }
    
    return stats


def print_results(results: List[Dict], stats: Dict, verbose: bool = False):
    """
    Print evaluation results in a formatted way.
    
    Args:
        results: List of evaluation results
        stats: Aggregate statistics
        verbose: Whether to print detailed results
    """
    print("\n" + "="*80)
    print("NASA RAG SYSTEM - BATCH EVALUATION RESULTS")
    print("="*80)
    
    # Print aggregate statistics
    print(f"\n📊 AGGREGATE STATISTICS")
    print(f"{'─'*80}")
    print(f"Total Questions: {stats['total_questions']}")
    print(f"Successful: {stats['successful']} ({stats['successful']/stats['total_questions']*100:.1f}%)")
    print(f"Failed: {stats['failed']} ({stats['failed']/stats['total_questions']*100:.1f}%)")
    
    # Check for embedding dimension mismatch errors
    dimension_mismatch_count = sum(1 for r in results if r.get('error') and "expecting embedding with dimension" in r.get('error', ''))
    if dimension_mismatch_count > 0:
        print(f"\n⚠️  Note: {dimension_mismatch_count} question(s) skipped due to embedding dimension mismatch")
        print(f"   This occurs when the collection was created with a different embedding model.")
        print(f"   To resolve: Delete chroma_db_openai/ and recreate with current embedding model.")
    
    print(f"\n📈 RAGAS METRICS SUMMARY")
    print(f"{'─'*80}")
    
    if stats['metrics']:
        # Print header
        print(f"{'Metric':<25} {'Mean':<8} {'Median':<8} {'StDev':<8} {'Min':<8} {'Max':<8}")
        print(f"{'─'*25} {'─'*8} {'─'*8} {'─'*8} {'─'*8} {'─'*8}")
        
        # Print each metric
        for metric_name, metric_stats in sorted(stats['metrics'].items()):
            print(f"{metric_name:<25} "
                  f"{metric_stats['mean']:<8.3f} "
                  f"{metric_stats['median']:<8.3f} "
                  f"{metric_stats['stdev']:<8.3f} "
                  f"{metric_stats['min']:<8.3f} "
                  f"{metric_stats['max']:<8.3f}")
    else:
        print("No metrics available")
    
    # Print per-question results
    if verbose:
        print(f"\n📝 PER-QUESTION RESULTS")
        print(f"{'─'*80}")
        
        for i, result in enumerate(results, 1):
            print(f"\n[Question {i}] {result['question']}")
            
            if result.get('error'):
                error_msg = result['error']
                # Check if this is an embedding dimension mismatch
                if "expecting embedding with dimension" in error_msg:
                    print(f"  ⚠️  Skipped (embedding dimension mismatch - collection uses different model)")
                    print(f"      Details: {error_msg}")
                else:
                    print(f"  ❌ Error: {error_msg}")
            else:
                print(f"  ✓ Retrieved: {result['retrieved_docs']} documents")
                print(f"  ✓ Answer: {result['answer'][:100]}...")
                
                if result.get('metrics') and not result['metrics'].get('error'):
                    print(f"  📊 Metrics:")
                    for metric_name, score in result['metrics'].items():
                        if isinstance(score, (int, float)):
                            print(f"     - {metric_name}: {score:.3f}")
    
    print(f"\n{'='*80}\n")


def main():
    """Main entry point for batch evaluation."""
    parser = argparse.ArgumentParser(
        description='Batch evaluate NASA RAG system using evaluation_dataset.txt'
    )
    parser.add_argument(
        '--openai-key',
        type=str,
        default=os.getenv('OPENAI_API_KEY'),
        help='OpenAI API key (or set OPENAI_API_KEY env var)'
    )
    parser.add_argument(
        '--openai-base-url',
        type=str,
        default=os.getenv('OPENAI_BASE_URL'),
        help='OpenAI base URL for custom endpoints (or set OPENAI_BASE_URL env var)'
    )
    parser.add_argument(
        '--model',
        type=str,
        default='gpt-3.5-turbo',
        help='Model to use for generation (default: gpt-3.5-turbo)'
    )
    parser.add_argument(
        '--n-results',
        type=int,
        default=3,
        help='Number of documents to retrieve per question (default: 3)'
    )
    parser.add_argument(
        '--dataset',
        type=str,
        default='evaluation_dataset.txt',
        help='Path to evaluation dataset (default: evaluation_dataset.txt)'
    )
    parser.add_argument(
        '--chroma-dir',
        type=str,
        default='chroma_db_openai',
        help='ChromaDB directory (default: chroma_db_openai)'
    )
    parser.add_argument(
        '--collection',
        type=str,
        default='nasa_space_missions_text',
        help='Collection name (default: nasa_space_missions_text)'
    )
    parser.add_argument(
        '--embedding-model',
        type=str,
        default='text-embedding-3-small',
        help='Embedding model used to create the collection (default: text-embedding-3-small)'
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Print detailed per-question results'
    )
    parser.add_argument(
        '--output',
        type=str,
        help='Optional: Save results to JSON file'
    )
    
    args = parser.parse_args()
    
    # Validate API key
    if not args.openai_key:
        logger.error("OpenAI API key required. Use --openai-key or set OPENAI_API_KEY env var")
        sys.exit(1)
    
    # Load evaluation dataset
    logger.info(f"Loading evaluation dataset from {args.dataset}")
    questions = parse_evaluation_dataset(args.dataset)
    
    if not questions:
        logger.error("No questions loaded from dataset")
        sys.exit(1)
    
    # Initialize ChromaDB
    logger.info(f"Initializing ChromaDB: {args.chroma_dir}/{args.collection}")
    logger.info(f"Using embedding model: {args.embedding_model}")
    if args.openai_base_url:
        logger.info(f"Using custom base URL: {args.openai_base_url}")
    
    try:
        collection = rag_client.initialize_rag_system(
            args.chroma_dir, 
            args.collection,
            args.openai_key,
            args.embedding_model,
            args.openai_base_url
        )
    except Exception as e:
        logger.error(f"Failed to initialize ChromaDB: {e}")
        sys.exit(1)
    
    # Run evaluations
    logger.info(f"Running batch evaluation on {len(questions)} questions...")
    results = []
    
    for i, q in enumerate(questions, 1):
        logger.info(f"[{i}/{len(questions)}] Evaluating: {q['question'][:60]}...")
        
        result = run_single_evaluation(
            q['question'],
            collection,
            args.openai_key,
            args.n_results,
            args.model,
            args.openai_base_url
        )
        
        # Add expected info to result
        result['expected_info'] = q['expected_info']
        result['response_type'] = q['response_type']
        
        results.append(result)
    
    # Calculate statistics
    stats = calculate_statistics(results)
    
    # Print results
    print_results(results, stats, args.verbose)
    
    # Save to file if requested
    if args.output:
        output_data = {
            'statistics': stats,
            'results': results
        }
        with open(args.output, 'w') as f:
            json.dump(output_data, f, indent=2)
        logger.info(f"Results saved to {args.output}")
    
    # Return exit code based on success rate
    success_rate = stats['successful'] / stats['total_questions'] if stats['total_questions'] > 0 else 0
    if success_rate < 0.5:
        sys.exit(1)
    
    logger.info("Batch evaluation completed successfully!")


if __name__ == "__main__":
    main()
