from ragas.llms import LangchainLLMWrapper
from ragas.embeddings import LangchainEmbeddingsWrapper
from langchain_openai import ChatOpenAI
from langchain_openai import OpenAIEmbeddings
from typing import Dict, List, Optional

# RAGAS imports
try:
    from ragas import SingleTurnSample
    from ragas.metrics import BleuScore, NonLLMContextPrecisionWithReference, ResponseRelevancy, Faithfulness, RougeScore
    from ragas import evaluate
    RAGAS_AVAILABLE = True
except ImportError:
    RAGAS_AVAILABLE = False

def evaluate_response_quality(question: str, answer: str, contexts: List[str]) -> Dict[str, float]:
    """
    Evaluate response quality using RAGAS metrics
    
    Args:
        question: User's question
        answer: Generated answer
        contexts: List of context strings used to generate the answer
    
    Returns:
        Dictionary of metric scores
    
    Note:
        For NonLLMContextPrecisionWithReference, we use the answer as reference
        since we don't have ground truth. In production, you should collect
        ground truth answers for more accurate evaluation.
    """
    if not RAGAS_AVAILABLE:
        return {"error": "RAGAS not available"}
    
    try:
        # Create evaluator LLM with model gpt-3.5-turbo
        evaluator_llm = LangchainLLMWrapper(ChatOpenAI(model="gpt-3.5-turbo"))
        
        # Create evaluator_embeddings with model text-embedding-3-small
        evaluator_embeddings = LangchainEmbeddingsWrapper(
            OpenAIEmbeddings(model="text-embedding-3-small")
        )
        
        # Define an instance for each metric to evaluate
        metrics = [
            ResponseRelevancy(llm=evaluator_llm, embeddings=evaluator_embeddings),
            Faithfulness(llm=evaluator_llm),
            NonLLMContextPrecisionWithReference()
        ]
        
        # Create a SingleTurnSample for evaluation
        sample = SingleTurnSample(
            user_input=question,
            response=answer,
            retrieved_contexts=contexts,
            reference=answer  # Using answer as reference for NonLLMContextPrecisionWithReference
        )
        
        # Evaluate the response using the metrics
        results = {}
        for metric in metrics:
            try:
                score = metric.single_turn_score(sample)
                metric_name = metric.__class__.__name__
                # Convert score to float if it's not already
                if hasattr(score, 'value'):
                    results[metric_name] = float(score.value)
                else:
                    results[metric_name] = float(score)
            except Exception as e:
                # Handle individual metric failures gracefully
                metric_name = metric.__class__.__name__
                results[metric_name] = 0.0
                results[f"{metric_name}_error"] = str(e)
        
        # Return the evaluation results
        return results
        
    except Exception as e:
        return {"error": f"Evaluation failed: {str(e)}"}
