"""
AI-powered email classification service
"""

import logging
from typing import Optional
import openai
import anthropic
from datetime import datetime

from .config import settings
from .models import Email, ClassificationResult, EmailClassification

logger = logging.getLogger(__name__)

class AIClassifier:
    """AI service for classifying email responses"""
    
    def __init__(self):
        self.provider = settings.AI_PROVIDER
        
        if self.provider == "openai":
            self.client = openai.AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        elif self.provider == "anthropic":
            self.client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
        else:
            raise ValueError(f"Unsupported AI provider: {self.provider}")
    
    def get_classification_prompt(self, email: Email) -> str:
        """Generate classification prompt for the email"""
        return f"""
You are an expert email classifier for sales campaigns. Analyze the following email reply and classify the sender's interest level.

EMAIL DETAILS:
Subject: {email.subject}
From: {email.sender}
Body: {email.body}

CLASSIFICATION CATEGORIES:
1. "Not Interested" - Clear rejection, unsubscribe requests, negative responses, or automated out-of-office replies
2. "Maybe Interested" - Neutral responses, requests for more information, questions about timing, or polite deferrals
3. "Interested" - Positive responses, requests for meetings, pricing inquiries, or clear buying signals

ANALYSIS REQUIREMENTS:
- Consider the tone, language, and specific words used
- Look for buying signals like "pricing", "demo", "meeting", "interested"
- Identify rejection signals like "not interested", "remove", "unsubscribe"
- Account for polite but non-committal responses
- Consider context clues from the subject line

Respond with a JSON object containing:
{{
    "classification": "Not Interested" | "Maybe Interested" | "Interested",
    "confidence": 0.0-1.0,
    "reasoning": "Brief explanation of your classification decision",
    "keywords": ["list", "of", "key", "words", "that", "influenced", "decision"],
    "sentiment_score": -1.0 to 1.0 (negative to positive sentiment)
}}

Be precise and confident in your classification. Focus on the actual intent behind the words.
"""

    async def classify_with_openai(self, email: Email) -> ClassificationResult:
        """Classify email using OpenAI"""
        try:
            response = await self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert email classifier for sales campaigns. Always respond with valid JSON."
                    },
                    {
                        "role": "user",
                        "content": self.get_classification_prompt(email)
                    }
                ],
                temperature=0.1,
                max_tokens=500
            )
            
            result_text = response.choices[0].message.content
            
            # Parse JSON response
            import json
            result_data = json.loads(result_text)
            
            return ClassificationResult(
                classification=EmailClassification(result_data["classification"]),
                confidence=float(result_data["confidence"]),
                reasoning=result_data["reasoning"],
                keywords=result_data.get("keywords", []),
                sentiment_score=result_data.get("sentiment_score")
            )
            
        except Exception as e:
            logger.error(f"OpenAI classification failed: {e}")
            # Fallback classification
            return self.fallback_classification(email)
    
    async def classify_with_anthropic(self, email: Email) -> ClassificationResult:
        """Classify email using Anthropic Claude"""
        try:
            response = await self.client.messages.create(
                model="claude-3-sonnet-20240229",
                max_tokens=500,
                temperature=0.1,
                messages=[
                    {
                        "role": "user",
                        "content": self.get_classification_prompt(email)
                    }
                ]
            )
            
            result_text = response.content[0].text
            
            # Parse JSON response
            import json
            result_data = json.loads(result_text)
            
            return ClassificationResult(
                classification=EmailClassification(result_data["classification"]),
                confidence=float(result_data["confidence"]),
                reasoning=result_data["reasoning"],
                keywords=result_data.get("keywords", []),
                sentiment_score=result_data.get("sentiment_score")
            )
            
        except Exception as e:
            logger.error(f"Anthropic classification failed: {e}")
            # Fallback classification
            return self.fallback_classification(email)
    
    def fallback_classification(self, email: Email) -> ClassificationResult:
        """Fallback rule-based classification when AI fails"""
        body_lower = email.body.lower()
        subject_lower = email.subject.lower()
        
        # Not interested keywords
        not_interested_keywords = [
            "not interested", "no thank", "unsubscribe", "remove", "stop",
            "don't contact", "not looking", "already have", "satisfied with current"
        ]
        
        # Interested keywords
        interested_keywords = [
            "interested", "pricing", "cost", "demo", "meeting", "call",
            "schedule", "discuss", "more information", "tell me more"
        ]
        
        # Maybe interested keywords
        maybe_keywords = [
            "maybe", "perhaps", "might be", "could be", "future", "later",
            "not right now", "busy", "timing"
        ]
        
        # Check for keywords
        for keyword in not_interested_keywords:
            if keyword in body_lower or keyword in subject_lower:
                return ClassificationResult(
                    classification=EmailClassification.NOT_INTERESTED,
                    confidence=0.8,
                    reasoning=f"Fallback classification based on keyword: {keyword}",
                    keywords=[keyword]
                )
        
        for keyword in interested_keywords:
            if keyword in body_lower or keyword in subject_lower:
                return ClassificationResult(
                    classification=EmailClassification.INTERESTED,
                    confidence=0.7,
                    reasoning=f"Fallback classification based on keyword: {keyword}",
                    keywords=[keyword]
                )
        
        for keyword in maybe_keywords:
            if keyword in body_lower or keyword in subject_lower:
                return ClassificationResult(
                    classification=EmailClassification.MAYBE_INTERESTED,
                    confidence=0.6,
                    reasoning=f"Fallback classification based on keyword: {keyword}",
                    keywords=[keyword]
                )
        
        # Default to maybe interested if no clear signals
        return ClassificationResult(
            classification=EmailClassification.MAYBE_INTERESTED,
            confidence=0.5,
            reasoning="Fallback classification - no clear interest signals detected",
            keywords=[]
        )
    
    async def classify_email(self, email: Email) -> ClassificationResult:
        """Main classification method"""
        logger.info(f"Classifying email from {email.sender}")
        
        try:
            if self.provider == "openai":
                result = await self.classify_with_openai(email)
            elif self.provider == "anthropic":
                result = await self.classify_with_anthropic(email)
            else:
                result = self.fallback_classification(email)
            
            # Validate confidence threshold
            if result.confidence < settings.CLASSIFICATION_CONFIDENCE_THRESHOLD:
                logger.warning(f"Low confidence classification: {result.confidence}")
                # Could implement human review queue here
            
            logger.info(f"Classification complete: {result.classification} (confidence: {result.confidence})")
            return result
            
        except Exception as e:
            logger.error(f"Classification failed: {e}")
            return self.fallback_classification(email)
    
    def get_response_template_key(self, classification: EmailClassification) -> str:
        """Get template key for response generation"""
        template_map = {
            EmailClassification.NOT_INTERESTED: "not_interested_response",
            EmailClassification.MAYBE_INTERESTED: "maybe_interested_response",
            EmailClassification.INTERESTED: "interested_response"
        }
        return template_map.get(classification, "default_response")
