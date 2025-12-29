import os
import re
from typing import Dict, List, Optional, Tuple
from datetime import datetime

class KnowledgeBaseService:
    def __init__(self, knowledge_base_path: str = "./knowledge_base"):
        self.knowledge_base_path = knowledge_base_path
        self.knowledge_content = {}
        print(f"📚 Initializing knowledge base from: {knowledge_base_path}")
        self._load_knowledge_base()
    
    def _load_knowledge_base(self):
        """Load all knowledge base files"""
        print("📖 Loading knowledge base files...")
        
        # Check if knowledge base directory exists
        if not os.path.exists(self.knowledge_base_path):
            print(f"📁 Creating knowledge base directory...")
            os.makedirs(self.knowledge_base_path, exist_ok=True)
            os.makedirs(os.path.join(self.knowledge_base_path, "services"), exist_ok=True)
            print(f"⚠️  Please add your markdown files to: {self.knowledge_base_path}")
            return
        
        # Define files to load with their categories
        files_to_load = [
            ("general.md", "general", "all"),
            ("careers.md", "careers", "all"),
            ("trainings.md", "trainings", "all"),
        ]
        
        # Load root files
        for filename, category, subcategory in files_to_load:
            file_path = os.path.join(self.knowledge_base_path, filename)
            if os.path.exists(file_path):
                self._load_file(file_path, category, subcategory)
            else:
                print(f"⚠️  File not found: {filename}")
        
        # Load service files
        services_dir = os.path.join(self.knowledge_base_path, "services")
        if os.path.exists(services_dir):
            service_files = [
                ("process_overview.md", "services", "process_overview"),
                ("ui_ux_design.md", "services", "ui_ux_design"),
                ("mobile_apps.md", "services", "mobile_apps"),
                ("web_development.md", "services", "web_development"),
            ]
            
            for filename, category, subcategory in service_files:
                file_path = os.path.join(services_dir, filename)
                if os.path.exists(file_path):
                    self._load_file(file_path, category, subcategory)
                else:
                    print(f"⚠️  Service file not found: {filename}")
        
        # Print summary
        if self.knowledge_content:
            total_files = sum(len(v) for v in self.knowledge_content.values())
            print(f"✅ Loaded {total_files} files across {len(self.knowledge_content)} categories")
            
            # Count FAQs
            total_faqs = 0
            for cat_key, docs in self.knowledge_content.items():
                for doc in docs:
                    total_faqs += len(doc.get('faqs', []))
            print(f"📊 Total FAQs: {total_faqs}")
        else:
            print("⚠️  No files loaded. Knowledge base is empty.")
    
    def _load_file(self, file_path: str, category: str, subcategory: str):
        """Load and parse a single markdown file"""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            
            if not content.strip():
                print(f"⚠️  Empty file: {file_path}")
                return
            
            # Extract metadata
            metadata = self._extract_metadata(content)
            
            # Extract FAQs
            faqs = self._extract_faqs(content)
            
            # Extract keywords
            keywords = self._extract_keywords(content)
            
            # Get relative path
            relative_path = os.path.relpath(file_path, self.knowledge_base_path)
            
            # Create document object
            doc = {
                "file": relative_path,
                "title": metadata.get('title', os.path.basename(file_path).replace('.md', '')),
                "content": content,
                "faqs": faqs,
                "keywords": keywords,
                "metadata": metadata,
                "full_path": file_path,
                "priority": metadata.get('priority', 'medium')
            }
            
            # Add to knowledge content
            cat_key = f"{category}:{subcategory}"
            if cat_key not in self.knowledge_content:
                self.knowledge_content[cat_key] = []
            
            self.knowledge_content[cat_key].append(doc)
            
            print(f"  ✅ Loaded: {relative_path} ({len(faqs)} FAQs)")
            
        except Exception as e:
            print(f"  ❌ Failed to load {file_path}: {e}")
    
    def _extract_metadata(self, content: str) -> Dict:
        """Extract metadata from content"""
        metadata = {}
        
        # Extract title from first H1
        title_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
        if title_match:
            metadata['title'] = title_match.group(1).strip()
        
        # Extract category
        category_match = re.search(r'##\s*Category:\s*(.+?)\n', content, re.IGNORECASE)
        if category_match:
            metadata['category'] = category_match.group(1).strip().lower()
        
        # Extract subcategory
        subcategory_match = re.search(r'##\s*Subcategory:\s*(.+?)\n', content, re.IGNORECASE)
        if subcategory_match:
            metadata['subcategory'] = subcategory_match.group(1).strip().lower()
        
        # Extract priority
        priority_match = re.search(r'##\s*Priority:\s*(.+?)\n', content, re.IGNORECASE)
        if priority_match:
            metadata['priority'] = priority_match.group(1).strip().lower()
        
        # Extract last updated
        updated_match = re.search(r'##\s*Last Updated:\s*(.+?)\n', content, re.IGNORECASE)
        if updated_match:
            metadata['last_updated'] = updated_match.group(1).strip()
        
        return metadata
    
    def _extract_faqs(self, content: str) -> List[Dict]:
        """Extract FAQ questions and answers"""
        faqs = []
        
        # Find FAQ section
        faq_section = re.search(r'##\s*FAQ[\s\S]*?(?=##|$)', content, re.IGNORECASE)
        if not faq_section:
            return faqs
        
        faq_text = faq_section.group(0)
        
        # Find Q/A pairs - handle both **Q:** and Q: formats
        qa_pattern = r'(?:\*\*)?[Qq](?:\*\*)?:\s*(.+?)\s*(?:\*\*)?[Aa](?:\*\*)?:\s*(.+?)(?=\n\s*(?:\*\*)?[Qq]|\n##|\Z)'
        matches = re.findall(qa_pattern, faq_text, re.DOTALL)
        
        for question, answer in matches:
            # Clean up the answer
            answer = re.sub(r'\n\s*\n', '\n', answer.strip())
            faqs.append({
                'question': question.strip(),
                'answer': answer
            })
        
        return faqs
    
    def _extract_keywords(self, content: str) -> List[str]:
        """Extract keywords from content"""
        keywords = []
        
        # Extract from keywords section
        keywords_section = re.search(
            r'##\s*Keywords for AI Matching[\s\S]*?(?=##|$)',
            content, re.IGNORECASE
        )
        if keywords_section:
            keyword_text = keywords_section.group(0)
            lines = keyword_text.split('\n')
            for line in lines[1:]:  # Skip header
                line = line.strip()
                if line and not line.startswith('##'):
                    # Split by comma and clean
                    words = [w.strip().lower() for w in line.split(',') if w.strip()]
                    keywords.extend(words)
        
        return list(set(keywords))  # Remove duplicates
    
    def search(self, query: str, category: Optional[str] = None) -> str:
        """Search knowledge base for relevant content"""
        query_lower = query.lower()
        
        print(f"🔍 Searching for: '{query}' (category: {category or 'all'})")
        
        # If no content loaded
        if not self.knowledge_content:
            print("⚠️  Knowledge base is empty")
            return ""
        
        # First, try direct FAQ match across all documents
        direct_faq_answer = self._find_direct_faq_match(query_lower)
        if direct_faq_answer:
            print("  ✅ Found direct FAQ match")
            return f"FAQ ANSWER:\n{direct_faq_answer}"
        
        # Determine which categories to search
        categories_to_search = []
        if category:
            # Search in specific category
            for cat_key in self.knowledge_content:
                if cat_key.startswith(f"{category}:"):
                    categories_to_search.append((cat_key, self.knowledge_content[cat_key]))
        else:
            # Search all categories
            categories_to_search = list(self.knowledge_content.items())
        
        # Score documents
        scored_docs = []
        for cat_key, docs in categories_to_search:
            for doc in docs:
                score = self._calculate_relevance_score(doc, query_lower)
                if score > 0:
                    scored_docs.append((score, doc))
        
        # Sort by score (highest first)
        scored_docs.sort(key=lambda x: x[0], reverse=True)
        
        # Take top 3 documents
        top_docs = scored_docs[:3]
        
        if not top_docs:
            print("  ❌ No relevant documents found")
            return ""
        
        print(f"  ✅ Found {len(top_docs)} relevant documents")
        
        # Build context from top documents
        context = ""
        for score, doc in top_docs:
            # Try to find relevant FAQ in this document
            relevant_faq = self._find_relevant_faq_in_doc(doc, query_lower)
            
            if relevant_faq:
                context += f"--- RELEVANT FAQ from {doc['file']} ---\n"
                context += f"Q: {relevant_faq['question']}\n"
                context += f"A: {relevant_faq['answer']}\n\n"
            else:
                # Extract relevant content (first 500 chars)
                content_preview = doc['content'][:500]
                if len(doc['content']) > 500:
                    content_preview += "..."
                
                context += f"--- From {doc['file']} ---\n"
                context += f"{content_preview}\n\n"
        
        return context.strip()
    
    def _find_direct_faq_match(self, query_lower: str) -> Optional[str]:
        """Find direct FAQ match across all documents"""
        for cat_key, docs in self.knowledge_content.items():
            for doc in docs:
                for faq in doc['faqs']:
                    faq_lower = faq['question'].lower().strip('? ')
                    # Check for exact match or close match
                    if (faq_lower == query_lower or 
                        query_lower in faq_lower or 
                        faq_lower in query_lower):
                        return faq['answer']
        
        return None
    
    def _find_relevant_faq_in_doc(self, doc: Dict, query_lower: str) -> Optional[Dict]:
        """Find relevant FAQ in a document"""
        for faq in doc['faqs']:
            faq_lower = faq['question'].lower()
            # Check if any word from query is in FAQ question
            query_words = set(re.findall(r'\b\w{3,}\b', query_lower))
            faq_words = set(re.findall(r'\b\w{3,}\b', faq_lower))
            
            if query_words.intersection(faq_words):
                return faq
        
        return None
    
    def _calculate_relevance_score(self, doc: Dict, query_lower: str) -> int:
        """Calculate relevance score for a document"""
        score = 0
        
        # Check keyword matches
        for keyword in doc['keywords']:
            if keyword in query_lower:
                score += 3
        
        # Check FAQ matches
        for faq in doc['faqs']:
            faq_lower = faq['question'].lower()
            if any(word in query_lower for word in re.findall(r'\b\w{3,}\b', faq_lower)):
                score += 2
        
        # Check content matches
        content_lower = doc['content'].lower()
        query_words = re.findall(r'\b\w{3,}\b', query_lower)
        for word in query_words:
            if word in content_lower:
                score += 1
        
        return score
    
    def get_faq_answer(self, question: str) -> Optional[str]:
        """Get direct FAQ answer for a question"""
        return self._find_direct_faq_match(question.lower())
    
    def get_stats(self) -> Dict:
        """Get knowledge base statistics"""
        stats = {
            "total_files": sum(len(v) for v in self.knowledge_content.values()),
            "categories": {},
            "total_faqs": 0,
            "status": "loaded" if self.knowledge_content else "empty"
        }
        
        for cat_key, docs in self.knowledge_content.items():
            category, subcategory = cat_key.split(':')
            if category not in stats["categories"]:
                stats["categories"][category] = {}
            
            faq_count = sum(len(doc['faqs']) for doc in docs)
            stats["categories"][category][subcategory] = {
                "file_count": len(docs),
                "faq_count": faq_count,
                "files": [doc['file'] for doc in docs]
            }
            stats["total_faqs"] += faq_count
        
        return stats

# Global instance
kb_service = KnowledgeBaseService()

def get_knowledge_service():
    """Get the knowledge base service instance"""
    return kb_service