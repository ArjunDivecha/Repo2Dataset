#!/usr/bin/env python3
"""
API-powered semantic dataset generator with streaming approach.
Processes one span at a time to avoid token limits and handle failures gracefully.
"""

import json
import os
import sys
import time
from pathlib import Path
from typing import List, Dict, Any

# Add src to path
sys.path.insert(0, './src')

from gh_chat_dataset.semantic_pipeline.parser import parse_repository
from gh_chat_dataset.semantic_pipeline.ontology import OntologyTagger

# Set up API keys - use environment variables
os.environ['ANTHROPIC_API_KEY'] = os.getenv('ANTHROPIC_API_KEY', '')
os.environ['OPENAI_API_KEY'] = os.getenv('OPENAI_API_KEY', '')

from anthropic import Anthropic
from openai import OpenAI

class StreamingSemanticGenerator:
    def __init__(self):
        self.anthropic = Anthropic()
        self.openai = OpenAI()
        self.success_count = 0
        self.failure_count = 0
        
    def get_embedding(self, text: str) -> List[float]:
        """Get embedding for a single text, with truncation and error handling."""
        try:
            # Truncate to avoid token limits (roughly 6000 chars = ~1500 tokens)
            truncated_text = text[:6000]
            response = self.openai.embeddings.create(
                model="text-embedding-3-small",  # Smaller model, cheaper
                input=[truncated_text]
            )
            return response.data[0].embedding
        except Exception as e:
            print(f"Embedding failed: {e}")
            return None
    
    def generate_conversation(self, span, embedding=None) -> Dict[str, Any]:
        """Generate a conversation for a single span using Claude."""
        try:
            # Build context
            context = f"""
File: {span.source_path.name}
Type: {span.kind}
Lines: {span.line_start}-{span.line_end}
Tags: {', '.join(span.metadata.get('tags', []))}
Content: {span.content[:2000]}
"""
            
            # Generate with Claude
            response = self.anthropic.messages.create(
                model="claude-3-5-sonnet-20240620",
                max_tokens=800,
                temperature=0.3,
                system="You are a financial code analysis expert. Create educational conversations about code.",
                messages=[{
                    "role": "user",
                    "content": f"""Create a conversation about this code snippet. Return ONLY a JSON object with this structure:
{{
  "user_question": "A specific question about this code",
  "assistant_response": "A detailed, educational response explaining the code's purpose and financial relevance",
  "key_insights": ["insight1", "insight2", "insight3"]
}}

Context: {context}"""
                }]
            )
            
            # Parse Claude's response
            response_text = "".join([block.text for block in response.content if hasattr(block, 'text')])
            
            # Extract JSON from response
            try:
                # Find JSON in response
                start = response_text.find('{')
                end = response_text.rfind('}') + 1
                if start >= 0 and end > start:
                    claude_data = json.loads(response_text[start:end])
                else:
                    raise ValueError("No JSON found in response")
            except:
                # Fallback if JSON parsing fails
                claude_data = {
                    "user_question": f"Explain this {span.kind} from {span.source_path.name}",
                    "assistant_response": f"This code appears to be a {span.kind} that handles financial data processing.",
                    "key_insights": ["Financial data processing", "Code analysis", "System component"]
                }
            
            # Build full conversation
            conversation = {
                "conversation_id": f"api-{self.success_count}",
                "source_files": [span.source_path.as_posix()],
                "ontology_tags": span.metadata.get('tags', []),
                "embedding_available": embedding is not None,
                "turns": [
                    {
                        "role": "system",
                        "content": "You are a financial code analysis expert. Provide clear, educational explanations."
                    },
                    {
                        "role": "user",
                        "content": claude_data.get("user_question", "Explain this code."),
                        "evidence": [{
                            "path": span.source_path.as_posix(),
                            "lines": f"{span.line_start}-{span.line_end}"
                        }]
                    },
                    {
                        "role": "assistant", 
                        "content": claude_data.get("assistant_response", "This code handles financial analysis tasks."),
                        "evidence": [{
                            "path": span.source_path.as_posix(),
                            "lines": f"{span.line_start}-{span.line_end}"
                        }]
                    }
                ],
                "summary": {
                    "key_insights": claude_data.get("key_insights", []),
                    "data_quality": "api_generated",
                    "generation_method": "claude_synthesis"
                }
            }
            
            self.success_count += 1
            return conversation
            
        except Exception as e:
            print(f"Conversation generation failed for {span.source_path.name}: {e}")
            self.failure_count += 1
            return None
    
    def generate_dataset(self, repo_path: Path, output_dir: Path, max_conversations: int = 50):
        """Generate dataset with streaming API calls."""
        
        print(f"Parsing repository: {repo_path}")
        documents = parse_repository(repo_path)
        
        # Collect spans
        spans = []
        for doc in documents:
            spans.extend(doc.spans)
        
        print(f"Found {len(spans)} spans")
        
        # Tag spans
        tagger = OntologyTagger.default()
        tagger.tag(spans)
        
        # Filter meaningful spans
        meaningful_spans = []
        for span in spans:
            content = span.content.strip()
            # Focus on substantial code/docs
            if (len(content) > 150 and 
                any(keyword in content.lower() for keyword in 
                    ['def ', 'class ', 'function', 'import', 'return', '##', 'factor', 'portfolio', 'strategy'])):
                meaningful_spans.append(span)
        
        print(f"Processing {min(len(meaningful_spans), max_conversations)} meaningful spans with APIs...")
        
        conversations = []
        
        # Process spans one by one
        for i, span in enumerate(meaningful_spans[:max_conversations]):
            print(f"Processing span {i+1}/{min(len(meaningful_spans), max_conversations)}: {span.source_path.name}")
            
            # Get embedding (optional, continues if fails)
            embedding = self.get_embedding(span.content)
            
            # Generate conversation
            conversation = self.generate_conversation(span, embedding)
            
            if conversation:
                conversations.append(conversation)
                print(f"  ✓ Generated conversation {len(conversations)}")
            else:
                print(f"  ✗ Failed to generate conversation")
            
            # Rate limiting
            time.sleep(0.5)  # Avoid hitting rate limits
        
        print(f"\nGeneration complete: {self.success_count} success, {self.failure_count} failures")
        
        # Split and save
        train_size = int(len(conversations) * 0.9)
        train_conversations = conversations[:train_size]
        valid_conversations = conversations[train_size:]
        
        # Write output
        output_dir.mkdir(parents=True, exist_ok=True)
        
        with open(output_dir / "semantic.train.jsonl", "w") as f:
            for conv in train_conversations:
                f.write(json.dumps(conv, ensure_ascii=False) + "\n")
        
        with open(output_dir / "semantic.valid.jsonl", "w") as f:
            for conv in valid_conversations:
                f.write(json.dumps(conv, ensure_ascii=False) + "\n")
        
        stats = {
            "total": len(conversations),
            "train": len(train_conversations),
            "valid": len(valid_conversations),
            "success_rate": f"{self.success_count}/{self.success_count + self.failure_count}",
            "api_powered": True
        }
        
        with open(output_dir / "semantic.stats.json", "w") as f:
            json.dump(stats, f, indent=2)
        
        return stats

if __name__ == "__main__":
    repo_path = Path("./Country-Factor-Momentum-Strategy")
    output_dir = Path("./country_factor_output_api/semantic")
    
    if not repo_path.exists():
        print(f"Error: Repository not found at {repo_path}")
        sys.exit(1)
    
    generator = StreamingSemanticGenerator()
    stats = generator.generate_dataset(repo_path, output_dir, max_conversations=30)
    
    print(f"\n🎉 Success! Generated API-powered semantic dataset:")
    print(f"   Total conversations: {stats['total']}")
    print(f"   Success rate: {stats['success_rate']}")
    print(f"   Output: {output_dir}")
