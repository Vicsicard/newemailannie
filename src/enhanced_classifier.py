"""
Enhanced AI classifier with context awareness and learning capabilities
"""

import logging
from typing import Optional, List, Dict, Any
import openai
import anthropic
from datetime import datetime
import json
import asyncio

from .config import settings
from .models import Email, ClassificationResult, EmailClassification
from .ai_classifier import AIClassifier
from .thread_manager import EmailThread

logger = logging.getLogger(__name__)

class EnhancedClassifier(AIClassifier):
    """Enhanced AI classifier with context awareness and learning loop"""
    
    def __init__(self):
        super().__init__()
        self.classification_history = []
        self.feedback_data = []
        self.context_enabled = True
        
    def get_context_aware_prompt(self, email: Email, thread_context: str = "", contact_info: Dict = None) -> str:
        """Generate context-aware classification prompt"""
        base_prompt = f"""
You are an expert email classifier for sales campaigns. Analyze the following email reply considering the full conversation context.

CURRENT EMAIL:
Subject: {email.subject}
From: {email.sender}
Body: {email.body}

CONVERSATION CONTEXT:
{thread_context if thread_context else "No previous conversation history"}

CONTACT INFORMATION:
{json.dumps(contact_info, indent=2) if contact_info else "No contact information available"}

CLASSIFICATION CATEGORIES:
1. "Not Interested" - Clear rejection, unsubscribe requests, negative responses, or automated out-of-office replies
2. "Maybe Interested" - Neutral responses, requests for more information, questions about timing, or polite deferrals
3. "Interested" - Positive responses, requests for meetings, pricing inquiries, or clear buying signals

CONTEXT ANALYSIS INSTRUCTIONS:
- Consider the conversation flow and how the prospect's interest has evolved
- Look for changes in tone or engagement level compared to previous emails
- Account for any specific questions or concerns raised in the thread
- Factor in timing and urgency indicators from the conversation
- Consider the relationship building that has occurred

ENHANCED ANALYSIS REQUIREMENTS:
- Analyze sentiment progression throughout the conversation
- Identify specific pain points or interests mentioned
- Look for buying signals that may have developed over time
- Consider the prospect's communication style and preferences
- Account for any objections that have been raised and addressed

Respond with a JSON object containing:
{{
    "classification": "Not Interested" | "Maybe Interested" | "Interested",
    "confidence": 0.0-1.0,
    "reasoning": "Detailed explanation considering conversation context",
    "keywords": ["list", "of", "key", "words", "from", "current", "and", "context"],
    "sentiment_score": -1.0 to 1.0,
    "context_influence": "How conversation history influenced this classification",
    "engagement_trend": "increasing" | "decreasing" | "stable",
    "next_action_recommendation": "Suggested next step based on context"
}}

Focus on the complete conversation journey, not just the current email in isolation.
"""
        return base_prompt
    
    async def classify_with_context(
        self, 
        email: Email, 
        thread_context: str = "", 
        contact_info: Dict = None
    ) -> ClassificationResult:
        """Classify email with conversation context"""
        try:
            prompt = self.get_context_aware_prompt(email, thread_context, contact_info)
            
            if self.provider == "openai" and self.client:
                response = await self.client.chat.completions.create(
                    model="gpt-4",
                    messages=[
                        {
                            "role": "system",
                            "content": "You are an expert email classifier with deep understanding of sales conversations. Always respond with valid JSON."
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    temperature=0.1,
                    max_tokens=600
                )
                result_text = response.choices[0].message.content
                
            elif self.provider == "anthropic" and hasattr(self, 'anthropic_client'):
                response = await self.anthropic_client.messages.create(
                    model="claude-3-sonnet-20240229",
                    max_tokens=600,
                    temperature=0.1,
                    messages=[
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ]
                )
                result_text = response.content[0].text
            else:
                # Fallback to base classifier
                return await super().classify_email(email)
            
            # Parse enhanced JSON response
            result_data = json.loads(result_text)
            
            classification_result = ClassificationResult(
                classification=EmailClassification(result_data["classification"]),
                confidence=float(result_data["confidence"]),
                reasoning=result_data["reasoning"],
                keywords=result_data.get("keywords", []),
                sentiment_score=result_data.get("sentiment_score")
            )
            
            # Store additional context data
            classification_result.context_influence = result_data.get("context_influence", "")
            classification_result.engagement_trend = result_data.get("engagement_trend", "stable")
            classification_result.next_action_recommendation = result_data.get("next_action_recommendation", "")
            
            # Record classification for learning
            self.record_classification(email, classification_result, thread_context, contact_info)
            
            return classification_result
            
        except Exception as e:
            logger.error(f"Context-aware classification failed: {e}")
            # Fallback to standard classification
            return await super().classify_email(email)
    
    def record_classification(
        self, 
        email: Email, 
        result: ClassificationResult, 
        context: str, 
        contact_info: Dict
    ):
        """Record classification for learning and analytics"""
        record = {
            'timestamp': datetime.now().isoformat(),
            'email_id': email.message_id,
            'sender': email.sender,
            'subject': email.subject,
            'body_length': len(email.body),
            'classification': result.classification.value,
            'confidence': result.confidence,
            'reasoning': result.reasoning,
            'keywords': result.keywords,
            'sentiment_score': result.sentiment_score,
            'had_context': bool(context),
            'context_length': len(context) if context else 0,
            'had_contact_info': bool(contact_info),
            'engagement_trend': getattr(result, 'engagement_trend', 'unknown'),
            'model_used': self.provider
        }
        
        self.classification_history.append(record)
        
        # Keep only recent history to prevent memory bloat
        if len(self.classification_history) > 1000:
            self.classification_history = self.classification_history[-800:]
    
    def add_feedback(
        self, 
        email_id: str, 
        actual_classification: str, 
        feedback_source: str = "manual"
    ):
        """Add feedback for learning loop"""
        # Find the original classification
        original_record = None
        for record in self.classification_history:
            if record['email_id'] == email_id:
                original_record = record
                break
        
        if original_record:
            feedback_record = {
                'timestamp': datetime.now().isoformat(),
                'email_id': email_id,
                'original_classification': original_record['classification'],
                'original_confidence': original_record['confidence'],
                'actual_classification': actual_classification,
                'feedback_source': feedback_source,
                'was_correct': original_record['classification'] == actual_classification,
                'confidence_was_appropriate': self._assess_confidence_accuracy(
                    original_record['confidence'], 
                    original_record['classification'] == actual_classification
                )
            }
            
            self.feedback_data.append(feedback_record)
            logger.info(f"Feedback recorded for email {email_id}: {actual_classification}")
        else:
            logger.warning(f"No original classification found for email {email_id}")
    
    def _assess_confidence_accuracy(self, confidence: float, was_correct: bool) -> str:
        """Assess if confidence level was appropriate"""
        if was_correct:
            if confidence >= 0.8:
                return "appropriate_high"
            elif confidence >= 0.6:
                return "appropriate_medium"
            else:
                return "underconfident"
        else:
            if confidence >= 0.8:
                return "overconfident"
            elif confidence >= 0.6:
                return "moderately_overconfident"
            else:
                return "appropriately_uncertain"
    
    def get_learning_insights(self) -> Dict[str, Any]:
        """Get insights from classification history and feedback"""
        if not self.classification_history:
            return {"error": "No classification history available"}
        
        total_classifications = len(self.classification_history)
        total_feedback = len(self.feedback_data)
        
        # Calculate accuracy from feedback
        correct_classifications = sum(1 for f in self.feedback_data if f['was_correct'])
        accuracy = correct_classifications / total_feedback if total_feedback > 0 else 0
        
        # Analyze confidence calibration
        confidence_analysis = self._analyze_confidence_calibration()
        
        # Classification distribution
        classification_counts = {}
        for record in self.classification_history:
            classification = record['classification']
            classification_counts[classification] = classification_counts.get(classification, 0) + 1
        
        # Context impact analysis
        context_impact = self._analyze_context_impact()
        
        return {
            'total_classifications': total_classifications,
            'total_feedback_received': total_feedback,
            'accuracy_rate': accuracy,
            'classification_distribution': classification_counts,
            'confidence_analysis': confidence_analysis,
            'context_impact': context_impact,
            'recent_trends': self._get_recent_trends(),
            'improvement_suggestions': self._get_improvement_suggestions()
        }
    
    def _analyze_confidence_calibration(self) -> Dict[str, Any]:
        """Analyze how well confidence scores match actual accuracy"""
        if not self.feedback_data:
            return {"error": "No feedback data available"}
        
        confidence_buckets = {
            'high_confidence': {'correct': 0, 'total': 0},  # 0.8+
            'medium_confidence': {'correct': 0, 'total': 0},  # 0.6-0.8
            'low_confidence': {'correct': 0, 'total': 0}  # <0.6
        }
        
        for feedback in self.feedback_data:
            confidence = feedback['original_confidence']
            is_correct = feedback['was_correct']
            
            if confidence >= 0.8:
                bucket = 'high_confidence'
            elif confidence >= 0.6:
                bucket = 'medium_confidence'
            else:
                bucket = 'low_confidence'
            
            confidence_buckets[bucket]['total'] += 1
            if is_correct:
                confidence_buckets[bucket]['correct'] += 1
        
        # Calculate accuracy for each bucket
        for bucket in confidence_buckets:
            total = confidence_buckets[bucket]['total']
            if total > 0:
                confidence_buckets[bucket]['accuracy'] = confidence_buckets[bucket]['correct'] / total
            else:
                confidence_buckets[bucket]['accuracy'] = 0
        
        return confidence_buckets
    
    def _analyze_context_impact(self) -> Dict[str, Any]:
        """Analyze impact of context on classification accuracy"""
        with_context = [r for r in self.classification_history if r['had_context']]
        without_context = [r for r in self.classification_history if not r['had_context']]
        
        # Get feedback for context vs non-context classifications
        context_feedback = []
        no_context_feedback = []
        
        for feedback in self.feedback_data:
            original = next((r for r in self.classification_history if r['email_id'] == feedback['email_id']), None)
            if original:
                if original['had_context']:
                    context_feedback.append(feedback)
                else:
                    no_context_feedback.append(feedback)
        
        context_accuracy = sum(1 for f in context_feedback if f['was_correct']) / len(context_feedback) if context_feedback else 0
        no_context_accuracy = sum(1 for f in no_context_feedback if f['was_correct']) / len(no_context_feedback) if no_context_feedback else 0
        
        return {
            'classifications_with_context': len(with_context),
            'classifications_without_context': len(without_context),
            'context_accuracy': context_accuracy,
            'no_context_accuracy': no_context_accuracy,
            'context_improvement': context_accuracy - no_context_accuracy,
            'average_context_length': sum(r['context_length'] for r in with_context) / len(with_context) if with_context else 0
        }
    
    def _get_recent_trends(self) -> Dict[str, Any]:
        """Analyze recent classification trends"""
        if len(self.classification_history) < 10:
            return {"error": "Insufficient data for trend analysis"}
        
        recent_records = self.classification_history[-50:]  # Last 50 classifications
        older_records = self.classification_history[-100:-50] if len(self.classification_history) >= 100 else []
        
        recent_avg_confidence = sum(r['confidence'] for r in recent_records) / len(recent_records)
        older_avg_confidence = sum(r['confidence'] for r in older_records) / len(older_records) if older_records else recent_avg_confidence
        
        return {
            'recent_average_confidence': recent_avg_confidence,
            'confidence_trend': recent_avg_confidence - older_avg_confidence,
            'recent_classification_distribution': self._get_distribution(recent_records),
            'classification_trend': "improving" if recent_avg_confidence > older_avg_confidence else "stable"
        }
    
    def _get_distribution(self, records: List[Dict]) -> Dict[str, float]:
        """Get classification distribution for a set of records"""
        if not records:
            return {}
        
        counts = {}
        for record in records:
            classification = record['classification']
            counts[classification] = counts.get(classification, 0) + 1
        
        total = len(records)
        return {k: v/total for k, v in counts.items()}
    
    def _get_improvement_suggestions(self) -> List[str]:
        """Generate improvement suggestions based on analysis"""
        suggestions = []
        
        if self.feedback_data:
            accuracy = sum(1 for f in self.feedback_data if f['was_correct']) / len(self.feedback_data)
            if accuracy < 0.85:
                suggestions.append("Consider refining classification prompts to improve accuracy")
        
        confidence_analysis = self._analyze_confidence_calibration()
        if 'high_confidence' in confidence_analysis and confidence_analysis['high_confidence']['accuracy'] < 0.9:
            suggestions.append("High confidence classifications need improvement - review prompt specificity")
        
        context_impact = self._analyze_context_impact()
        if context_impact.get('context_improvement', 0) > 0.1:
            suggestions.append("Context significantly improves accuracy - ensure context is always provided")
        
        if not suggestions:
            suggestions.append("Classification performance is good - continue monitoring")
        
        return suggestions
