#!/usr/bin/env python3
# scripts/auto_fix.py
# This script runs after tool calls to fix common mistakes

import json
import sys
import re

def auto_fix():
    """Fix common issues in tool outputs."""
    
    input_data = json.load(sys.stdin)
    tool_name = input_data.get("tool_name", "unknown")
    result = input_data.get("result", "")
    
    if tool_name == "write_file":
        content = result.get("content", "")
        
        # Fix 1: Remove print statements (if they contain debugging text)
        content = re.sub(r'print\([\'"](TODO|FIXME|DEBUG)[\'"]\)', '', content)
        
        # Fix 2: Ensure newline at end of file
        if not content.endswith('\n'):
            content += '\n'
        
        # Fix 3: Replace hardcoded secrets with environment variables
        secret_patterns = {
            r'API_KEY\s*=\s*[\'"]\w+[\'"]': '# API_KEY = os.getenv("API_KEY")',
            r'PASSWORD\s*=\s*[\'"]\w+[\'"]': '# PASSWORD = os.getenv("PASSWORD")',
        }
        for pattern, replacement in secret_patterns.items():
            if re.search(pattern, content):
                content = re.sub(pattern, replacement, content)
                # Add import if not present
                if "import os" not in content:
                    content = "import os\n" + content
        
        # Output the fixed content
        print(json.dumps({
            "action": "modify",
            "modified_content": content,
            "changes_made": True
        }))
        sys.exit(0)
    
    # No fixes needed
    print(json.dumps({"action": "allow"}))
    sys.exit(0)

if __name__ == "__main__":
    auto_fix()
