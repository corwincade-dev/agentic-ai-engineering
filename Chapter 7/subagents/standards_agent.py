# subagents/standards_agent.py
# A subagent focused only on coding standards and style

from langchain.tools import tool
from langchain.agents import create_react_agent, AgentExecutor
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain.prompts import PromptTemplate
import os
import re


@tool
def check_naming_conventions(code: str) -> str:
    """Check if naming follows Python conventions (snake_case for functions/vars, PascalCase for classes)."""
    issues = []
    lines = code.split('\n')
    
    # Check function names (should be snake_case)
    func_pattern = r'def\s+([a-zA-Z_][a-zA-Z0-9_]*)\('
    for i, line in enumerate(lines, 1):
        matches = re.findall(func_pattern, line)
        for match in matches:
            if not re.match(r'^[a-z][a-z0-9_]*$', match):
                issues.append(f"Line {i}: Function '{match}' should be snake_case")
    
    # Check class names (should be PascalCase)
    class_pattern = r'class\s+([a-zA-Z_][a-zA-Z0-9_]*)'
    for i, line in enumerate(lines, 1):
        matches = re.findall(class_pattern, line)
        for match in matches:
            if not re.match(r'^[A-Z][a-zA-Z0-9]*$', match):
                issues.append(f"Line {i}: Class '{match}' should be PascalCase")
    
    if issues:
        return "Naming Convention Issues:\n" + "\n".join(issues[:10])
    return "Naming conventions look good."


@tool
def check_docstrings(code: str) -> str:
    """Check if functions and classes have docstrings."""
    issues = []
    lines = code.split('\n')
    
    in_function = False
    function_name = ""
    function_line = 0
    found_docstring = False
    
    for i, line in enumerate(lines, 1):
        if line.strip().startswith('def '):
            in_function = True
            function_name = line.split('def ')[1].split('(')[0]
            function_line = i
            found_docstring = False
        elif in_function and line.strip().startswith('"""'):
            found_docstring = True
        elif in_function and line.strip() and not line.strip().startswith((' ', '"""', '#')):
            # End of function
            if not found_docstring and function_name != '__init__':
                issues.append(f"Line {function_line}: Function '{function_name}' missing docstring")
            in_function = False
    
    if issues:
        return "Docstring Issues:\n" + "\n".join(issues[:10])
    return "Docstrings look good."


@tool
def check_line_length(code: str, max_length: int = 100) -> str:
    """Check if any line exceeds the maximum length."""
    issues = []
    lines = code.split('\n')
    
    for i, line in enumerate(lines, 1):
        if len(line) > max_length and not line.strip().startswith('#'):
            issues.append(f"Line {i}: {len(line)} chars (max {max_length})")
    
    if issues:
        return f"Line Length Issues (>{max_length}):\n" + "\n".join(issues[:10])
    return f"All lines are within {max_length} characters."


STANDARDS_PROMPT = PromptTemplate.from_template("""
You are a coding standards reviewer. Your ONLY job is to check if code follows conventions.

You have these tools:
{tools}

For ANY code you receive, you MUST check:
1. Naming conventions (snake_case for functions, PascalCase for classes)
2. Docstrings (every function needs one)
3. Line length (max 100 characters)

Report only violations. Do not suggest improvements beyond the standard.
If you find no violations, say "No standards violations found."

Code to review:
{input}

{agent_scratchpad}
""")


def create_standards_agent():
    """Create and return the standards subagent."""
    
    if os.getenv("ANTHROPIC_API_KEY"):
        llm = ChatAnthropic(model="claude-3-haiku-20240307", temperature=0)  # Haiku is cheaper for simple tasks
    elif os.getenv("OPENAI_API_KEY"):
        llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0)  # 3.5 is cheaper
    else:
        from langchain.llms.fake import FakeListLLM
        llm = FakeListLLM(responses=["Standards check complete."])
    
    agent = create_react_agent(
        llm=llm,
        tools=[check_naming_conventions, check_docstrings, check_line_length],
        prompt=STANDARDS_PROMPT
    )
    
    executor = AgentExecutor(
        agent=agent,
        tools=[check_naming_conventions, check_docstrings, check_line_length],
        verbose=False,
        max_iterations=8,
        handle_parsing_errors=True
    )
    
    return executor
