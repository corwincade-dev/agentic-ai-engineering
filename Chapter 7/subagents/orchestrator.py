# orchestrator.py
# The master orchestrator that delegates to subagents

from langgraph.graph import StateGraph, END
from typing import TypedDict, List
import asyncio
from concurrent.futures import ThreadPoolExecutor, as_completed

# Import our subagents
from subagents.security_agent import create_security_agent
from subagents.standards_agent import create_standards_agent
from subagents.performance_agent import create_performance_agent


# ------------------------------------------------------------------
# STATE DEFINITION
# ------------------------------------------------------------------

class CodeReviewState(TypedDict):
    """State that flows through the orchestration graph."""
    code: str                    # The code to review
    security_results: str        # Output from security agent
    standards_results: str       # Output from standards agent
    performance_results: str     # Output from performance agent
    final_review: str            # Combined final output
    errors: List[str]            # Any errors encountered


# ------------------------------------------------------------------
# ORCHESTRATOR FUNCTIONS
# ------------------------------------------------------------------

def create_agents():
    """Create all subagents (lazy initialization)."""
    return {
        "security": create_security_agent(),
        "standards": create_standards_agent(),
        "performance": create_performance_agent()
    }


def run_parallel_reviews(state: CodeReviewState) -> CodeReviewState:
    """
    Run all three subagents in parallel.
    This is where the performance gain happens.
    """
    code = state["code"]
    agents = create_agents()
    
    results = {}
    errors = []
    
    # Run agents in parallel using threading
    # (LangGraph subagents would be better, but this works for demonstration)
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = {}
        
        for name, agent in agents.items():
            future = executor.submit(agent.invoke, {"input": code})
            futures[future] = name
        
        for future in as_completed(futures):
            name = futures[future]
            try:
                result = future.result(timeout=60)  # 60 second timeout per agent
                results[f"{name}_results"] = result["output"]
            except Exception as e:
                errors.append(f"{name} agent failed: {str(e)}")
                results[f"{name}_results"] = f"Error: {name} review failed"
    
    return {
        **state,
        "security_results": results.get("security_results", "No security review completed"),
        "standards_results": results.get("standards_results", "No standards review completed"),
        "performance_results": results.get("performance_results", "No performance review completed"),
        "errors": errors
    }


def aggregate_results(state: CodeReviewState) -> CodeReviewState:
    """
    Combine results from all subagents into a unified review.
    This runs after all parallel reviews complete.
    """
    code = state["code"]
    security = state["security_results"]
    standards = state["standards_results"]
    performance = state["performance_results"]
    errors = state.get("errors", [])
    
    # Count issue severity
    critical_indicators = ["CRITICAL", "SQL Injection", "Hardcoded Secret", "eval(", "exec("]
    warning_indicators = ["Warning", "Issue", "Risk", "Potential"]
    
    critical_count = 0
    warning_count = 0
    
    for result in [security, standards, performance]:
        for indicator in critical_indicators:
            if indicator in result:
                critical_count += 1
        for indicator in warning_indicators:
            if indicator in result:
                warning_count += 1
    
    # Build final review
    review = f"""
# CODE REVIEW REPORT

## Summary
- **Critical Issues:** {critical_count}
- **Warnings:** {warning_count}
- **Errors encountered:** {len(errors)}

## Security Review
{security}

## Standards Review
{standards}

## Performance Review
{performance}
"""
    
    # Add recommendations based on counts
    if critical_count > 0:
        review += f"""
## Recommendation: REQUIRES CHANGES
Found {critical_count} critical issue(s). Do not merge until all critical issues are resolved.
"""
    elif warning_count > 0:
        review += f"""
## Recommendation: CHANGES SUGGESTED
Found {warning_count} warning(s). Consider addressing before merging.
"""
    else:
        review += """
## Recommendation: APPROVED
No critical issues or warnings found. Ready for merge.
"""
    
    if errors:
        review += f"\n## Errors Encountered\n- " + "\n- ".join(errors)
    
    return {
        **state,
        "final_review": review
    }


# ------------------------------------------------------------------
# BUILD THE GRAPH
# ------------------------------------------------------------------

def create_review_orchestrator():
    """Create the complete orchestration graph."""
    
    # Create the state graph
    graph = StateGraph(CodeReviewState)
    
    # Add nodes
    graph.add_node("parallel_reviews", run_parallel_reviews)
    graph.add_node("aggregate", aggregate_results)
    
    # Add edges
    graph.set_entry_point("parallel_reviews")
    graph.add_edge("parallel_reviews", "aggregate")
    graph.add_edge("aggregate", END)
    
    # Compile
    return graph.compile()


# ------------------------------------------------------------------
# MAIN ORCHESTRATOR EXECUTOR
# ------------------------------------------------------------------

class CodeReviewOrchestrator:
    """High-level interface for the code review system."""
    
    def __init__(self):
        self.graph = create_review_orchestrator()
    
    def review_code(self, code: str) -> str:
        """Review a piece of code and return the final report."""
        initial_state = {
            "code": code,
            "security_results": "",
            "standards_results": "",
            "performance_results": "",
            "final_review": "",
            "errors": []
        }
        
        result = self.graph.invoke(initial_state)
        return result["final_review"]
    
    def review_file(self, filepath: str) -> str:
        """Review a file on disk."""
        with open(filepath, 'r') as f:
            code = f.read()
        return self.review_code(code)


# ------------------------------------------------------------------
# COMMAND LINE INTERFACE
# ------------------------------------------------------------------

if __name__ == "__main__":
    import sys
    
    orchestrator = CodeReviewOrchestrator()
    
    if len(sys.argv) > 1:
        # Review a file
        filepath = sys.argv[1]
        print(f"Reviewing {filepath}...")
        print(orchestrator.review_file(filepath))
    else:
        # Interactive mode
        print("Code Review Orchestrator (type 'quit' to exit)")
        print("-" * 50)
        
        while True:
            print("\nPaste code to review (or 'file:path' to review a file):")
            user_input = input("> ")
            
            if user_input.lower() in ['quit', 'exit', 'q']:
                break
            
            if user_input.startswith("file:"):
                filepath = user_input[5:].strip()
                try:
                    print(f"\nReviewing {filepath}...\n")
                    print(orchestrator.review_file(filepath))
                except FileNotFoundError:
                    print(f"File not found: {filepath}")
            else:
                print("\nReviewing code...\n")
                print(orchestrator.review_code(user_input))
