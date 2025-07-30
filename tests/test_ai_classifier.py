"""
Tests for AI classifier functionality
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from src.ai_classifier import AIClassifier
from src.models import Email, EmailClassification, ClassificationResult

@pytest.fixture
def sample_email():
    """Sample email for testing"""
    return Email(
        message_id="test-123",
        subject="Re: Your proposal",
        sender="test@example.com",
        recipient="annie@company.com",
        body="Thanks for reaching out. I'm interested in learning more about your pricing.",
        received_date=datetime.now()
    )

@pytest.fixture
def ai_classifier():
    """AI classifier instance for testing"""
    with patch('src.config.settings') as mock_settings:
        mock_settings.AI_PROVIDER = "openai"
        mock_settings.OPENAI_API_KEY = "test-key"
        mock_settings.CLASSIFICATION_CONFIDENCE_THRESHOLD = 0.7
        return AIClassifier()

class TestAIClassifier:
    """Test cases for AI classifier"""
    
    @pytest.mark.asyncio
    async def test_classify_interested_email(self, ai_classifier, sample_email):
        """Test classification of interested email"""
        # Mock OpenAI response
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = """
        {
            "classification": "Interested",
            "confidence": 0.9,
            "reasoning": "Email mentions pricing inquiry",
            "keywords": ["interested", "pricing"],
            "sentiment_score": 0.7
        }
        """
        
        with patch.object(ai_classifier.client.chat.completions, 'create', return_value=mock_response):
            result = await ai_classifier.classify_email(sample_email)
            
            assert result.classification == EmailClassification.INTERESTED
            assert result.confidence == 0.9
            assert "pricing" in result.keywords
    
    @pytest.mark.asyncio
    async def test_classify_not_interested_email(self, ai_classifier):
        """Test classification of not interested email"""
        email = Email(
            message_id="test-456",
            subject="Re: Your proposal",
            sender="test@example.com",
            recipient="annie@company.com",
            body="Not interested, please remove me from your list.",
            received_date=datetime.now()
        )
        
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = """
        {
            "classification": "Not Interested",
            "confidence": 0.95,
            "reasoning": "Clear rejection with unsubscribe request",
            "keywords": ["not interested", "remove"],
            "sentiment_score": -0.8
        }
        """
        
        with patch.object(ai_classifier.client.chat.completions, 'create', return_value=mock_response):
            result = await ai_classifier.classify_email(email)
            
            assert result.classification == EmailClassification.NOT_INTERESTED
            assert result.confidence == 0.95
    
    def test_fallback_classification_interested(self, ai_classifier):
        """Test fallback classification for interested keywords"""
        email = Email(
            message_id="test-789",
            subject="Re: Your proposal",
            sender="test@example.com",
            recipient="annie@company.com",
            body="I'm interested in scheduling a demo next week.",
            received_date=datetime.now()
        )
        
        result = ai_classifier.fallback_classification(email)
        
        assert result.classification == EmailClassification.INTERESTED
        assert "interested" in result.keywords
    
    def test_fallback_classification_not_interested(self, ai_classifier):
        """Test fallback classification for not interested keywords"""
        email = Email(
            message_id="test-101",
            subject="Re: Your proposal",
            sender="test@example.com",
            recipient="annie@company.com",
            body="Please unsubscribe me from your emails.",
            received_date=datetime.now()
        )
        
        result = ai_classifier.fallback_classification(email)
        
        assert result.classification == EmailClassification.NOT_INTERESTED
        assert "unsubscribe" in result.keywords
    
    @pytest.mark.asyncio
    async def test_ai_failure_fallback(self, ai_classifier, sample_email):
        """Test that fallback is used when AI fails"""
        with patch.object(ai_classifier.client.chat.completions, 'create', side_effect=Exception("API Error")):
            result = await ai_classifier.classify_email(sample_email)
            
            # Should still return a classification result
            assert isinstance(result, ClassificationResult)
            assert result.classification in [
                EmailClassification.INTERESTED,
                EmailClassification.MAYBE_INTERESTED,
                EmailClassification.NOT_INTERESTED
            ]

if __name__ == "__main__":
    pytest.main([__file__])
