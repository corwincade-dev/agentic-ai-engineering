# subagents/performance_agent.py
# A subagent focused only on performance issues

from langchain.tools import tool
from langchain.agents import create_react_agent, AgentExecutor
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain.prompts import PromptTemplate
import os
import re


@tool
def detect_n_plus_one_queries(code: str) -> str:
    """Detect potential N+1 query patterns in loops."""
    issues = []
    lines = code.split('\n')
    
    # Look for database queries inside loops
    in_loop = False
    loop_line = 0
    
    for i, line in enumerate(lines, 1):
        if re.match(r'^\s*for\s+', line):
            in_loop = True
            loop_line = i
        elif in_loop and re.search(r'\.(query|filter|get|all|objects\.)', line, re.IGNORECASE):
            issues.append(f"Line {i}: Database query inside loop (potential N+1) - loop started at line {loop_line}")
            in_loop = False
        elif in_loop and line.strip() and not line.strip().startswith((' ', '#', 'for')):
            in_loop = False
    
    if issues:
        return "N+1 Query Risks:\n" + "\n".join(issues)
    return "No N+1 query patterns detected."


@tool
def detect_inefficient_loops(code: str) -> str:
    """Detect inefficient loop patterns like nested loops over large datasets."""
    issues = []
    lines = code.split('\n')
    
    nested_loops = 0
    for i, line in enumerate(lines, 1):
        if re.match(r'^\s*for\s+', line):
            nested_loops += 1
        elif nested_loops >= 2 and not line.strip():
            issues.append(f"Line {i}: Nested loops detected (potential O(n²) complexity)")
            nested_loops = 0
    
    # Look for .append in loops (can sometimes be optimized with list comprehension)
    in_loop = False
    for i, line in enumerate(lines, 1):
        if re.match(r'^\s*for\s+', line):
            in_loop = True
        elif in_loop and '.append(' in line:
            issues.append(f"Line {i}: Consider using list comprehension instead of .append in loop")
            in_loop = False
        elif in_loop and line.strip() and not line.strip().startswith((' ', '#', 'for')):
            in_loop = False
    
    if issues:
        return "Inefficient Loop Patterns:\n" + "\n".join(issues)
    return "No inefficient loop patterns detected."


@tool
def detect_memory_leaks(code: str) -> str:
    """Detect potential memory leak patterns."""
    issues = []
    
    # Growing data structures without cleanup
    if 'cache = {}' in code or 'cache = dict()' in code:
        issues.append("Unbounded cache dictionary - may cause memory leak without size limit")
    
    # Global lists that grow
    if re.search(r'^[A-Z_]+ = \[\]', code, re.MULTILINE):
        issues.append("Global list that grows - ensure it has a bounded size")
    
    # Event listeners without removal
    if 'addEventListener' in code or '.on(' in code or 'bind(' in code:
        issues.append("Event listeners added but no removal detected - potential memory leak")
    
    if issues:
        return "Potential Memory Leaks:\n" + "\n".join(issues)
    return "No obvious memory leak patterns detected."


PERFORMANCE_PROMPT = PromptTemplate.from_template("""
You are a performance reviewer. Your ONLY job is to find performance problems.

You have these tools:
{tools}

For ANY code you receive, you MUST check:
1. N+1 queries (database queries inside loops)
2. Inefficient loops (nested loops, O(n²) patterns)
3. Memory leaks (unbounded caches, global lists)

Focus on patterns that will cause problems in production at scale.
If you find no issues, say "No performance issues detected."

Code to review:
{input}

{agent_scratchpad}
""")


def create_performance_agent():
    """Create and return the performance subagent."""
    
    if os.getenv("ANTHROPIC_API_KEY"):
        llm = ChatAnthropic(model="claude-3-haiku-20240307", temperature=0)
    elif os.getenv("OPENAI_API_KEY"):
        llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0)
    else:
        from langchain.llms.fake import FakeListLLM
        llm = FakeListLLM(responses=["Performance analysis complete."])
    
    agent = create_react_agent(
        llm=llm,
        tools=[detect_n_plus_one_queries, detect_inefficient_loops, detect_memory_leaks],
        prompt=PERFORMANCE_PROMPT
    )
    
    executor = AgentExecutor(
        agent=agent,
        tools=[detect_n_plus_one_queries, detect_inefficient_loops, detect_memory_leaks],
        verbose=False,
        max_iterations=8,
        handle_parsing_errors=True
    )
    
    return executor
