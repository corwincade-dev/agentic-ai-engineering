#!/usr/bin/env python3
# scripts/audit_tool_call.py
# This script runs BEFORE every tool call
# It logs the call and can block dangerous actions

import json
import sys
import os
from datetime import datetime

def audit_tool_call():
    """Audit a tool call before it executes."""
    
    # Claude Code passes information via stdin
    input_data = json.load(sys.stdin)
    
    tool_name = input_data.get("tool_name", "unknown")
    arguments = input_data.get("arguments", {})
    session_id = input_data.get("session_id", "unknown")
    
    # Log to audit file
    audit_log = os.path.expanduser("~/.claude/audit.log")
    with open(audit_log, "a") as f:
        f.write(json.dumps({
            "timestamp": datetime.utcnow().isoformat(),
            "session_id": session_id,
            "tool_name": tool_name,
            "arguments": arguments,
            "action": "attempted"
        }) + "\n")
    
    # Check for dangerous commands
    dangerous_patterns = [
        "rm -rf",
        "DROP TABLE",
        "DELETE FROM",
        "sudo",
        "chmod 777",
        "> /dev/null"
    ]
    
    if tool_name == "bash":
        command = arguments.get("command", "")
        for pattern in dangerous_patterns:
            if pattern in command:
                # Block the command
                print(json.dumps({
                    "action": "block",
                    "reason": f"Dangerous pattern detected: {pattern}"
                }))
                sys.exit(1)  # Non-zero exit blocks the tool
    
    # Allow the tool to run
    print(json.dumps({"action": "allow"}))
    sys.exit(0)

if __name__ == "__main__":
    audit_tool_call()
