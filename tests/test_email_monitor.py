"""
Tests for email monitoring functionality
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime
import email

from src.email_monitor import EmailMonitor
from src.models import Email, EmailStatus, ClassificationResult, EmailClassification

@pytest.fixture
def mock_services():
    """Mock services for testing"""
    ai_classifier = Mock()
    salesforce_client = Mock()
    response_generator = Mock()
    notification_service = Mock()
    
    return ai_classifier, salesforce_client, response_generator, notification_service

@pytest.fixture
def email_monitor(mock_services):
    """Email monitor instance for testing"""
    ai_classifier, salesforce_client, response_generator, notification_service = mock_services
    return EmailMonitor(ai_classifier, salesforce_client, response_generator, notification_service)

class TestEmailMonitor:
    """Test cases for email monitor"""
    
    def test_parse_email_message(self, email_monitor):
        """Test email message parsing"""
        raw_message = b"""From: test@example.com
To: annie@company.com
Subject: Re: Your proposal
Date: Mon, 1 Jan 2024 12:00:00 +0000
Message-ID: <test-123@example.com>

I'm interested in your services. Can you send me pricing information?
"""
        
        email_obj = email_monitor.parse_email_message(raw_message)
        
        assert email_obj is not None
        assert email_obj.sender == "test@example.com"
        assert email_obj.subject == "Re: Your proposal"
        assert "pricing information" in email_obj.body
    
    def test_is_campaign_reply(self, email_monitor):
        """Test campaign reply detection"""
        # Email with reply indicators
        reply_email = Email(
            message_id="test-123",
            subject="Re: Your proposal",
            sender="test@example.com",
            recipient="annie@company.com",
            body="Thanks for your email. I'm interested in learning more.",
            received_date=datetime.now(),
            in_reply_to="<original-123@company.com>"
        )
        
        assert email_monitor.is_campaign_reply(reply_email) == True
        
        # Email without reply indicators
        new_email = Email(
            message_id="test-456",
            subject="New inquiry",
            sender="test@example.com",
            recipient="annie@company.com",
            body="Hi there",
            received_date=datetime.now()
        )
        
        # This should still be considered a campaign reply based on other criteria
        result = email_monitor.is_campaign_reply(new_email)
        assert isinstance(result, bool)
    
    @pytest.mark.asyncio
    async def test_process_email_interested(self, email_monitor, mock_services):
        """Test processing of interested email"""
        ai_classifier, salesforce_client, response_generator, notification_service = mock_services
        
        # Setup mocks
        classification = ClassificationResult(
            classification=EmailClassification.INTERESTED,
            confidence=0.9,
            reasoning="Customer expressed interest",
            keywords=["interested"]
        )
        
        contact = Mock()
        contact.id = "003123456789"
        
        ai_classifier.classify_email = AsyncMock(return_value=classification)
        salesforce_client.find_contact_by_email = AsyncMock(return_value=contact)
        salesforce_client.update_campaign_status = AsyncMock(return_value=True)
        response_generator.generate_response = AsyncMock(return_value=Mock())
        response_generator.send_response = AsyncMock(return_value=True)
        notification_service.notify_sales_team = AsyncMock(return_value=True)
        
        # Test email
        test_email = Email(
            message_id="test-123",
            subject="Re: Your proposal",
            sender="test@example.com",
            recipient="annie@company.com",
            body="I'm very interested in your services!",
            received_date=datetime.now()
        )
        
        result = await email_monitor.process_email(test_email)
        
        assert result.classification.classification == EmailClassification.INTERESTED
        assert result.salesforce_updated == True
        assert result.response_sent == True
        assert result.notification_sent == True
        assert len(result.errors) == 0
    
    @pytest.mark.asyncio
    async def test_process_email_not_interested(self, email_monitor, mock_services):
        """Test processing of not interested email"""
        ai_classifier, salesforce_client, response_generator, notification_service = mock_services
        
        # Setup mocks
        classification = ClassificationResult(
            classification=EmailClassification.NOT_INTERESTED,
            confidence=0.95,
            reasoning="Customer requested removal",
            keywords=["not interested"]
        )
        
        contact = Mock()
        contact.id = "003123456789"
        
        ai_classifier.classify_email = AsyncMock(return_value=classification)
        salesforce_client.find_contact_by_email = AsyncMock(return_value=contact)
        salesforce_client.update_campaign_status = AsyncMock(return_value=True)
        
        # Test email
        test_email = Email(
            message_id="test-456",
            subject="Re: Your proposal",
            sender="test@example.com",
            recipient="annie@company.com",
            body="Not interested, please remove me.",
            received_date=datetime.now()
        )
        
        result = await email_monitor.process_email(test_email)
        
        assert result.classification.classification == EmailClassification.NOT_INTERESTED
        assert result.salesforce_updated == True
        assert result.response_sent == False  # No response for not interested
        assert result.notification_sent == False  # No notification for not interested
    
    @pytest.mark.asyncio
    async def test_process_email_with_errors(self, email_monitor, mock_services):
        """Test processing email with errors"""
        ai_classifier, salesforce_client, response_generator, notification_service = mock_services
        
        # Setup mocks with failures
        classification = ClassificationResult(
            classification=EmailClassification.INTERESTED,
            confidence=0.9,
            reasoning="Customer expressed interest",
            keywords=["interested"]
        )
        
        ai_classifier.classify_email = AsyncMock(return_value=classification)
        salesforce_client.find_contact_by_email = AsyncMock(side_effect=Exception("Salesforce error"))
        
        test_email = Email(
            message_id="test-789",
            subject="Re: Your proposal",
            sender="test@example.com",
            recipient="annie@company.com",
            body="I'm interested!",
            received_date=datetime.now()
        )
        
        result = await email_monitor.process_email(test_email)
        
        assert len(result.errors) > 0
        assert "Salesforce" in result.errors[0]
    
    def test_get_stats(self, email_monitor):
        """Test statistics retrieval"""
        stats = email_monitor.get_stats()
        
        assert "total_emails_processed" in stats
        assert "classifications" in stats
        assert "responses_sent" in stats
        assert "notifications_sent" in stats

if __name__ == "__main__":
    pytest.main([__file__])
