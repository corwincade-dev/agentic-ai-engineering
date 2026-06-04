#!/usr/bin/env python3
# scripts/inject_context.py
# This script runs before every prompt to inject relevant context

import json
import sys
import os
from pathlib import Path

def inject_context():
    """Inject project-specific context before Claude responds."""
    
    input_data = json.load(sys.stdin)
    current_prompt = input_data.get("prompt", "")
    
    # Load project context
    context_parts = []
    
    # 1. Load CLAUDE.md if it exists
    claude_md = Path(".claude/CLAUDE.md")
    if claude_md.exists():
        context_parts.append(f"Project Memory:\n{claude_md.read_text()}")
    
    # 2. Load recent git commits (last 5)
    try:
        import subprocess
        commits = subprocess.check_output(
            ["git", "log", "--oneline", "-5"],
            text=True
        )
        context_parts.append(f"Recent commits:\n{commits}")
    except:
        pass
    
    # 3. Load current branch
    try:
        import subprocess
        branch = subprocess.check_output(
            ["git", "branch", "--show-current"],
            text=True
        ).strip()
        context_parts.append(f"Current branch: {branch}")
    except:
        pass
    
    # 4. Load open files (if provided)
    open_files = input_data.get("open_files", [])
    if open_files:
        files_text = []
        for file in open_files[:3]:  # Limit to 3 files
            path = Path(file)
            if path.exists():
                files_text.append(f"File: {file}\n{path.read_text()[:2000]}...")  # First 2000 chars
        if files_text:
            context_parts.append("Open Files:\n" + "\n---\n".join(files_text))
    
    # Inject context at the beginning of the prompt
    if context_parts:
        context_text = "\n\n".join(context_parts)
        modified_prompt = f"[SYSTEM CONTEXT]\n{context_text}\n\n[USER QUERY]\n{current_prompt}"
    else:
        modified_prompt = current_prompt
    
    print(json.dumps({"modified_prompt": modified_prompt}))
    sys.exit(0)

if __name__ == "__main__":
    inject_context()
