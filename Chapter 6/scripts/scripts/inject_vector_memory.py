#!/usr/bin/env python3
# scripts/inject_vector_memory.py
# PrePrompt hook that injects relevant vector memory into context

import json
import sys
from vector_memory import VectorMemory

def inject_vector_memory():
    """Search vector memory and inject relevant facts."""
    
    input_data = json.load(sys.stdin)
    current_prompt = input_data.get("prompt", "")
    
    # Initialize vector memory for current project
    vm = VectorMemory()
    
    # Search for relevant facts
    relevant_facts = vm.search(current_prompt, n_results=3)
    
    if relevant_facts:
        facts_text = "\n".join([f"- {fact}" for fact in relevant_facts])
        memory_context = f"\n[RELEVANT MEMORIES FROM PAST SESSIONS]\n{facts_text}\n"
        modified_prompt = memory_context + current_prompt
    else:
        modified_prompt = current_prompt
    
    print(json.dumps({"modified_prompt": modified_prompt}))
    sys.exit(0)

if __name__ == "__main__":
    inject_vector_memory()
