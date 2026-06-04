# subagents/security_agent.py
# A subagent focused only on security vulnerabilities

from langchain.tools import tool
from langchain.agents import create_react_agent, AgentExecutor
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic
from langchain.prompts import PromptTemplate
import os
import re

# ------------------------------------------------------------------
# SECURITY TOOLS
# ------------------------------------------------------------------

@tool
def detect_sql_injection(code: str) -> str:
    """
    Detect potential SQL injection vulnerabilities in code.
    Looks for string concatenation in database queries.
    """
    issues = []
    
    # Pattern: string concatenation in SQL queries
    patterns = [
        (r'f".*SELECT.*\{.*\}.*"', "F-string in SQL query - possible injection"),
        (r'".*SELECT.*" \+ .*', "String concatenation in SQL query"),
        (r"'.*SELECT.*' \. format\(", ".format() in SQL query"),
        (r'execute\(.*\+.*\)', "Variable concatenation in execute()"),
    ]
    
    lines = code.split('\n')
    for i, line in enumerate(lines, 1):
        for pattern, message in patterns:
            if re.search(pattern, line, re.IGNORECASE):
                issues.append(f"Line {i}: {message}")
    
    if issues:
        return f"SQL Injection Risks Found:\n" + "\n".join(issues)
    return "No SQL injection patterns detected."


@tool
def detect_hardcoded_secrets(code: str) -> str:
    """
    Detect hardcoded secrets, API keys, passwords, and tokens.
    """
    issues = []
    
    secret_patterns = [
        (r'API_KEY\s*=\s*[\'"][A-Za-z0-9]+[\'"]', "Hardcoded API key"),
        (r'SECRET_KEY\s*=\s*[\'"][A-Za-z0-9]+[\'"]', "Hardcoded secret key"),
        (r'PASSWORD\s*=\s*[\'"][^\'"]+[\'"]', "Hardcoded password"),
        (r'token\s*=\s*[\'"][A-Za-z0-9_\-]+[\'"]', "Hardcoded token"),
        (r'AWS_.*_KEY\s*=\s*[\'"][A-Za-z0-9]+[\'"]', "Hardcoded AWS credential"),
    ]
    
    lines = code.split('\n')
    for i, line in enumerate(lines, 1):
        for pattern, message in secret_patterns:
            if re.search(pattern, line, re.IGNORECASE):
                issues.append(f"Line {i}: {message}")
    
    if issues:
        return f"Hardcoded Secrets Found:\n" + "\n".join(issues)
    return "No hardcoded secrets detected."


@tool
def detect_unsafe_functions(code: str) -> str:
    """
    Detect usage of unsafe or deprecated functions.
    """
    issues = []
    
    unsafe_functions = [
        ('eval', 'eval() can execute arbitrary code - security risk'),
        ('exec', 'exec() can execute arbitrary code - security risk'),
        ('__import__', 'Dynamic imports can bypass security controls'),
        ('pickle.loads', 'Pickle can execute arbitrary code during deserialization'),
        ('os.system', 'Shell injection risk - use subprocess instead'),
        ('subprocess.Popen(shell=True)', 'Shell=True is a security risk'),
    ]
    
    lines = code.split('\n')
    for i, line in enumerate(lines, 1):
        for func, message in unsafe_functions:
            if func in line:
                issues.append(f"Line {i}: {message}")
    
    if issues:
        return f"Unsafe Functions Detected:\n" + "\n".join(issues)
    return "No unsafe functions detected."


# ------------------------------------------------------------------
# SECURITY AGENT PROMPT
# ------------------------------------------------------------------

SECURITY_PROMPT = PromptTemplate.from_template("""
You are a security-focused code reviewer. Your ONLY job is to find security vulnerabilities.

You have these tools:
{tools}

For ANY code you receive, you MUST:
1. First, run detect_sql_injection
2. Then, run detect_hardcoded_secrets
3. Then, run detect_unsafe_functions
4. Summarize the findings

Be thorough. False positives are better than false negatives.
If you find ANY critical issue (SQL injection, hardcoded secrets), mark it as "CRITICAL".

Code to review:
{input}

{agent_scratchpad}
""")


def create_security_agent():
    """Create and return the security subagent."""
    
    # Use Claude if available, otherwise mock
    if os.getenv("ANTHROPIC_API_KEY"):
        llm = ChatAnthropic(model="claude-3-sonnet-20241022", temperature=0)
    elif os.getenv("OPENAI_API_KEY"):
        llm = ChatOpenAI(model="gpt-4", temperature=0)
    else:
        from langchain.llms.fake import FakeListLLM
        llm = FakeListLLM(responses=["Security scan complete."])
    
    agent = create_react_agent(
        llm=llm,
        tools=[detect_sql_injection, detect_hardcoded_secrets, detect_unsafe_functions],
        prompt=SECURITY_PROMPT
    )
    
    executor = AgentExecutor(
        agent=agent,
        tools=[detect_sql_injection, detect_hardcoded_secrets, detect_unsafe_functions],
        verbose=False,
        max_iterations=10,
        handle_parsing_errors=True
    )
    
    return executor


# For testing
if __name__ == "__main__":
    agent = create_security_agent()
    test_code = """
    def get_user(request):
        user_id = request.GET.get('id')
        query = f"SELECT * FROM users WHERE id = {user_id}"
        return db.execute(query)
    
    API_KEY = "sk-1234567890"
    """
    result = agent.invoke({"input": test_code})
    print(result["output"])
