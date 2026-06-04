#!/usr/bin/env python3
# scripts/vector_memory.py
# A vector memory system for Claude Code
# Stores facts in ChromaDB and retrieves relevant ones on demand

import json
import sys
import os
from pathlib import Path
import hashlib

# Try to import vector database libraries
try:
    import chromadb
    from sentence_transformers import SentenceTransformer
    HAS_VECTOR_LIBS = True
except ImportError:
    HAS_VECTOR_LIBS = False
    print("Warning: chromadb or sentence-transformers not installed. Run: pip install chromadb sentence-transformers")

class VectorMemory:
    """Store and retrieve facts using semantic search."""
    
    def __init__(self, project_path: str = "."):
        self.project_path = Path(project_path).resolve()
        self.db_path = self.project_path / ".claude" / "vector_memory"
        
        if not HAS_VECTOR_LIBS:
            self.client = None
            self.model = None
            return
        
        # Initialize ChromaDB
        self.client = chromadb.PersistentClient(path=str(self.db_path))
        
        # Get or create collection
        self.collection = self.client.get_or_create_collection(
            name="project_memory",
            metadata={"hnsw:space": "cosine"}
        )
        
        # Initialize embedding model (runs locally, no API key needed)
        # Using a small, fast model that runs on CPU
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
    
    def add_fact(self, fact: str, category: str = "general"):
        """Add a fact to vector memory."""
        if not self.client:
            print("Vector memory not available. Install chromadb and sentence-transformers.")
            return
        
        # Create a unique ID from the fact content
        fact_id = hashlib.md5(fact.encode()).hexdigest()
        
        # Generate embedding
        embedding = self.model.encode(fact).tolist()
        
        # Store in ChromaDB
        self.collection.upsert(
            ids=[fact_id],
            embeddings=[embedding],
            metadatas=[{"category": category, "fact": fact}],
            documents=[fact]
        )
        print(f"Added fact to vector memory: {fact[:50]}...")
    
    def search(self, query: str, n_results: int = 5) -> list:
        """Search for facts relevant to the query."""
        if not self.client:
            return []
        
        # Generate embedding for query
        query_embedding = self.model.encode(query).tolist()
        
        # Search
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results
        )
        
        # Extract documents
        documents = results.get('documents', [[]])[0]
        return documents
    
    def add_from_claude_md(self):
        """Parse existing CLAUDE.md files and add to vector memory."""
        memory_files = [
            Path.home() / ".claude" / "CLAUDE.md",
            self.project_path / ".claude" / "CLAUDE.md",
            self.project_path / "CLAUDE.md"
        ]
        
        for file_path in memory_files:
            if file_path.exists():
                content = file_path.read_text()
                # Split into sections and bullet points
                lines = content.split('\n')
                current_section = "general"
                for line in lines:
                    if line.startswith('#'):
                        current_section = line.strip('# ').lower()
                    elif line.strip().startswith('-'):
                        fact = line.strip('- ').strip()
                        if fact and len(fact) > 10:
                            self.add_fact(fact, current_section)
        
        print(f"Imported facts from memory files. Total facts: {self.collection.count()}")

def main():
    """Command-line interface for vector memory."""
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python vector_memory.py add <fact>")
        print("  python vector_memory.py search <query>")
        print("  python vector_memory.py import")
        sys.exit(1)
    
    command = sys.argv[1]
    vm = VectorMemory()
    
    if command == "add":
        fact = " ".join(sys.argv[2:])
        vm.add_fact(fact)
    
    elif command == "search":
        query = " ".join(sys.argv[2:])
        results = vm.search(query)
        print("\nRelevant facts:")
        for i, result in enumerate(results, 1):
            print(f"{i}. {result}")
    
    elif command == "import":
        vm.add_from_claude_md()
    
    else:
        print(f"Unknown command: {command}")

if __name__ == "__main__":
    main()
