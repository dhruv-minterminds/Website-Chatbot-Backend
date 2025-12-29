import google.generativeai as genai
import os
import re
from typing import Dict, List, Optional
from config import Config
from .knowledge_base_service import get_knowledge_service


class GeminiService:
    def __init__(self):
        self.api_key = Config.GEMINI_API_KEY
        self.model_name = "gemini-2.5-flash"
        self.model = None
        self.knowledge_service = get_knowledge_service()
        self._initialize()
    
    def _initialize(self):
        """Initialize Gemini AI"""
        try:
            genai.configure(api_key=self.api_key)
            
            generation_config = {
                "temperature": 0.7,
                "top_p": 0.95,
                "top_k": 40,
                "max_output_tokens": 1024,
            }
            
            safety_settings = [
                {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
                {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
                {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
                {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
            ]
            
            self.model = genai.GenerativeModel(
                model_name=self.model_name,
                generation_config=generation_config,
                safety_settings=safety_settings,
            )
            
            print(f"✅ Gemini AI initialized with model: {self.model_name}")
            
        except Exception as e:
            print(f"❌ Failed to initialize Gemini AI: {e}")
            raise
    
    def generate_response(self, user_message: str, conversation_history: List[Dict] = None) -> Dict:
        """Generate response using Gemini AI with knowledge base"""
        
        # Detect category
        category = self._detect_category(user_message)
        
        # Search knowledge base
        context = self.knowledge_service.search(user_message, category)
        
        # Try direct FAQ match
        direct_faq_answer = self.knowledge_service.get_faq_answer(user_message)
        
        # Build prompt
        prompt = self._build_prompt(user_message, context, category, direct_faq_answer, conversation_history)
        
        try:
            response = self.model.generate_content(prompt)
            bot_response = response.text.strip()
            
            # Check for trigger
            should_trigger = self._check_trigger(user_message, bot_response, conversation_history)
            
            # Clean trigger tag
            if "[TRIGGER_CAPTURE]" in bot_response:
                bot_response = bot_response.replace("[TRIGGER_CAPTURE]", "").strip()
                should_trigger = True
            
            return {
                "response": bot_response,
                "trigger_capture": should_trigger,
                "category": category,
                "direct_faq_used": direct_faq_answer is not None,
                "success": True,
            }
            
        except Exception as e:
            print(f"❌ Gemini AI error: {e}")
            return {
                "response": "I'm having trouble processing your request. Please try again.",
                "trigger_capture": False,
                "success": False,
                "error": str(e),
            }
    
    def _detect_category(self, user_message: str) -> str:
        """Detect category from user message"""
        message_lower = user_message.lower()
        
        if any(word in message_lower for word in ["job", "career", "hire", "apply", "resume", "work", "position"]):
            return "careers"
        elif any(word in message_lower for word in ["train", "learn", "course", "program", "skill", "internship", "certification"]):
            return "trainings"
        elif any(word in message_lower for word in ["service", "develop", "build", "create", "website", "app", "software"]):
            return "services"
        else:
            return "general"
    
    def _build_prompt(self, user_message: str, context: str, category: str, 
                     direct_faq_answer: Optional[str], conversation_history: List[Dict]) -> str:
        """Build prompt for Gemini AI"""
        
        # Format conversation history
        history_text = ""
        if conversation_history:
            history_text = "Previous conversation (most recent first):\n"
            for msg in reversed(conversation_history[-4:]):  # Last 2 exchanges
                role = "User" if msg['role'] == 'user' else "Assistant"
                history_text += f"{role}: {msg['content']}\n"
        
        # Build context section
        context_section = ""
        if direct_faq_answer:
            context_section = f"DIRECT FAQ ANSWER (use this if it answers the question):\n{direct_faq_answer}\n\n"
        
        if context:
            context_section += f"KNOWLEDGE BASE CONTEXT:\n{context}\n"
        
        prompt = f"""You are MinterBot, the AI assistant for Minterminds (minterminds.com).

INSTRUCTIONS:
1. Answer based on the knowledge base context below
2. If information isn't available, say: "I don't have that specific information, but I can connect you with our team."
3. Be helpful, professional, and concise
4. Add [TRIGGER_CAPTURE] at the end if user shows high intent (asking about pricing, applying, scheduling, or after 3+ engaged messages)

{history_text}

{context_section}

USER'S QUESTION: {user_message}

DETECTED CATEGORY: {category}

RESPONSE GUIDELINES:
1. Answer the question using the knowledge base
2. If direct FAQ answer is available and relevant, use it
3. Keep response to 2-3 paragraphs maximum
4. End with [TRIGGER_CAPTURE] if appropriate

Your response:"""
        
        return prompt
    
    def _check_trigger(self, user_message: str, bot_response: str, 
                      conversation_history: List[Dict]) -> bool:
        """Check if lead capture should be triggered"""
        message_lower = user_message.lower()
        
        # Keyword triggers
        trigger_keywords = [
            'price', 'cost', 'how much', 'quote', 'budget', 'fee',
            'apply', 'application', 'submit', 'hire', 'job',
            'enroll', 'register', 'admission', 'sign up', 'join',
            'schedule', 'meeting', 'consultation', 'demo',
            'portfolio', 'examples', 'work', 'projects'
        ]
        
        # Check for keywords
        if any(keyword in message_lower for keyword in trigger_keywords):
            return True
        
        # Check for AI-added trigger
        if "[TRIGGER_CAPTURE]" in bot_response:
            return True
        
        # Engagement trigger (after 3+ messages)
        if conversation_history and len(conversation_history) >= 3:
            return True
        
        return False

# Global Gemini service instance
gemini_service = None

def get_gemini_service():
    global gemini_service
    if gemini_service is None:
        gemini_service = GeminiService()
    return gemini_service