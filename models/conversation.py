import json
import os
from typing import List, Dict
from config.llm_config import llm_generic

CONVERSATION_DIR = "database/store/conversations"

class ConversationStore:
    """Manages conversation history with summary + last k messages"""
    
    def __init__(self, thread_id: str, max_recent_messages: int = 5):
        self.thread_id = thread_id
        self.max_recent_messages = max_recent_messages
        self.filepath = os.path.join(CONVERSATION_DIR, f"{thread_id}.json")
        os.makedirs(CONVERSATION_DIR, exist_ok=True)
        self._load()
    
    def _load(self):
        """Load conversation from disk"""
        if os.path.exists(self.filepath):
            with open(self.filepath, 'r') as f:
                data = json.load(f)
                self.summary = data.get('summary', '')
                self.recent_messages = data.get('recent_messages', [])
        else:
            self.summary = ''
            self.recent_messages = []
    
    def _save(self):
        """Save conversation to disk"""
        with open(self.filepath, 'w') as f:
            json.dump({
                'summary': self.summary,
                'recent_messages': self.recent_messages
            }, f, indent=2)
    
    def add_message(self, role: str, content: str):
        """Add message to conversation"""
        self.recent_messages.append({
            'role': role,
            'content': content
        })
        
        # Keep only last k messages
        if len(self.recent_messages) > self.max_recent_messages * 2:
            # Summarize old messages
            self._update_summary()
            # Keep only recent messages
            self.recent_messages = self.recent_messages[-(self.max_recent_messages * 2):]
        
        self._save()
    
    def _update_summary(self):
        """Update conversation summary using LLM"""
        if len(self.recent_messages) <= self.max_recent_messages:
            return
        
        messages_to_summarize = self.recent_messages[:-(self.max_recent_messages)]
        messages_text = "\n".join([
            f"{msg['role']}: {msg['content']}" 
            for msg in messages_to_summarize
        ])
        
        prompt = f"""Summarize the following conversation concisely (max 3 sentences):

Previous summary: {self.summary if self.summary else 'None'}

New messages:
{messages_text}

Provide a brief summary that captures key information discussed:"""
        
        try:
            response = llm_generic.generate(prompt)
            new_summary = response['results'][0]['generated_text'].strip()
            self.summary = new_summary
        except Exception as e:
            print(f"Error updating summary: {e}")
    
    def get_context(self) -> str:
        """Get conversation context as string"""
        context_parts = []
        
        if self.summary:
            context_parts.append(f"Previous conversation summary: {self.summary}")
        
        if self.recent_messages:
            context_parts.append("\nRecent messages:")
            for msg in self.recent_messages:
                context_parts.append(f"{msg['role']}: {msg['content']}")
        
        return "\n".join(context_parts) if context_parts else "No previous conversation"
    
    def clear(self):
        """Clear conversation history"""
        self.summary = ''
        self.recent_messages = []
        if os.path.exists(self.filepath):
            os.remove(self.filepath)