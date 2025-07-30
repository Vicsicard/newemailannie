"""
Script to test email integration and processing
"""

import asyncio
import logging
from datetime import datetime
from src.email_monitor import EmailMonitor
from src.ai_classifier import AIClassifier
from src.salesforce_client import SalesforceClient
from src.response_generator import ResponseGenerator
from src.notification_service import NotificationService
from src.models import Email, EmailStatus
from src.config import settings, validate_settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Sample test emails for different scenarios
TEST_EMAILS = [
    {
        "message_id": "test-interested-001",
        "subject": "Re: Your marketing services proposal",
        "sender": "john.doe@testcompany.com",
        "body": "Hi Annie, I'm very interested in your marketing services. Can you schedule a demo for next week? I'd also like to see pricing for our 50-person team.",
        "expected_classification": "Interested"
    },
    {
        "message_id": "test-maybe-002", 
        "subject": "Re: Digital marketing consultation",
        "sender": "sarah.smith@example.org",
        "body": "Thanks for reaching out. We might be interested in the future, but we're not looking to make any changes right now. Can you send me more information about your services?",
        "expected_classification": "Maybe Interested"
    },
    {
        "message_id": "test-not-interested-003",
        "subject": "Re: Marketing automation services",
        "sender": "mike.johnson@company.net",
        "body": "Not interested at this time. Please remove me from your mailing list. We already have a marketing solution in place.",
        "expected_classification": "Not Interested"
    },
    {
        "message_id": "test-pricing-inquiry-004",
        "subject": "Re: Your proposal",
        "sender": "lisa.wilson@startup.io",
        "body": "Hi! I reviewed your proposal and I'm interested. What are your pricing options for a small startup? We're looking to get started as soon as possible.",
        "expected_classification": "Interested"
    },
    {
        "message_id": "test-unsubscribe-005",
        "subject": "Re: Marketing services",
        "sender": "robert.brown@corp.com",
        "body": "Please unsubscribe me from all future emails. I am not interested in your services.",
        "expected_classification": "Not Interested"
    }
]

async def create_test_email(test_data):
    """Create a test email object"""
    return Email(
        message_id=test_data["message_id"],
        subject=test_data["subject"],
        sender=test_data["sender"],
        recipient=settings.EMAIL_ADDRESS,
        body=test_data["body"],
        received_date=datetime.now(),
        status=EmailStatus.PENDING
    )

async def test_ai_classification():
    """Test AI classification with sample emails"""
    logger.info("Testing AI classification...")
    
    try:
        ai_classifier = AIClassifier()
        
        for test_data in TEST_EMAILS:
            test_email = await create_test_email(test_data)
            
            logger.info(f"\nTesting email: {test_email.sender}")
            logger.info(f"Expected: {test_data['expected_classification']}")
            
            # Classify the email
            result = await ai_classifier.classify_email(test_email)
            
            logger.info(f"Classified as: {result.classification}")
            logger.info(f"Confidence: {result.confidence:.2%}")
            logger.info(f"Reasoning: {result.reasoning}")
            
            # Check if classification matches expectation
            if result.classification.value == test_data['expected_classification']:
                logger.info("✅ Classification matches expectation")
            else:
                logger.warning("❌ Classification doesn't match expectation")
                
    except Exception as e:
        logger.error(f"AI classification test failed: {e}")

async def test_salesforce_integration():
    """Test Salesforce integration"""
    logger.info("Testing Salesforce integration...")
    
    try:
        sf_client = SalesforceClient()
        await sf_client.connect()
        
        # Test finding a contact (use a test email)
        test_email = "test@example.com"
        contact = await sf_client.find_contact_by_email(test_email)
        
        if contact:
            logger.info(f"✅ Found contact: {contact.first_name} {contact.last_name}")
            
            # Test updating campaign status
            success = await sf_client.update_campaign_status(contact.id, "Interested")
            if success:
                logger.info("✅ Campaign status updated successfully")
            else:
                logger.warning("❌ Failed to update campaign status")
                
        else:
            logger.info(f"No contact found for {test_email} (this is expected for test data)")
            
    except Exception as e:
        logger.error(f"Salesforce integration test failed: {e}")

async def test_response_generation():
    """Test response generation"""
    logger.info("Testing response generation...")
    
    try:
        ai_classifier = AIClassifier()
        response_generator = ResponseGenerator(ai_classifier)
        
        # Test with an interested email
        test_data = TEST_EMAILS[0]  # Interested email
        test_email = await create_test_email(test_data)
        
        # Get classification first
        classification = await ai_classifier.classify_email(test_email)
        
        # Generate response
        response = await response_generator.generate_response(test_email, classification, None)
        
        logger.info(f"✅ Response generated:")
        logger.info(f"Subject: {response.subject}")
        logger.info(f"Template used: {response.template_used}")
        logger.info(f"Body preview: {response.body[:200]}...")
        
    except Exception as e:
        logger.error(f"Response generation test failed: {e}")

async def test_end_to_end_processing():
    """Test complete end-to-end email processing"""
    logger.info("Testing end-to-end email processing...")
    
    try:
        # Initialize all services
        ai_classifier = AIClassifier()
        sf_client = SalesforceClient()
        await sf_client.connect()
        response_generator = ResponseGenerator(ai_classifier)
        notification_service = NotificationService(sf_client)
        
        email_monitor = EmailMonitor(
            ai_classifier=ai_classifier,
            salesforce_client=sf_client,
            response_generator=response_generator,
            notification_service=notification_service
        )
        
        # Process each test email
        for test_data in TEST_EMAILS:
            test_email = await create_test_email(test_data)
            
            logger.info(f"\n--- Processing email from {test_email.sender} ---")
            
            result = await email_monitor.process_email(test_email)
            
            logger.info(f"Classification: {result.classification.classification}")
            logger.info(f"Confidence: {result.classification.confidence:.2%}")
            logger.info(f"Salesforce updated: {result.salesforce_updated}")
            logger.info(f"Response sent: {result.response_sent}")
            logger.info(f"Notification sent: {result.notification_sent}")
            logger.info(f"Processing time: {result.processing_time:.2f}s")
            
            if result.errors:
                logger.warning(f"Errors: {result.errors}")
            else:
                logger.info("✅ Processed successfully")
        
        # Get final stats
        stats = email_monitor.get_stats()
        logger.info(f"\n--- Final Statistics ---")
        logger.info(f"Total emails processed: {stats['total_emails_processed']}")
        logger.info(f"Classifications: {stats['classifications']}")
        logger.info(f"Responses sent: {stats['responses_sent']}")
        logger.info(f"Notifications sent: {stats['notifications_sent']}")
        logger.info(f"Errors: {stats['errors']}")
        
    except Exception as e:
        logger.error(f"End-to-end test failed: {e}")

async def main():
    """Run all tests"""
    logger.info("Starting AI Email Agent integration tests...")
    
    try:
        # Validate configuration
        validate_settings()
        logger.info("✅ Configuration validated")
        
        # Run individual component tests
        await test_ai_classification()
        await test_salesforce_integration()
        await test_response_generation()
        
        # Run end-to-end test
        await test_end_to_end_processing()
        
        logger.info("\n🎉 All tests completed!")
        
    except Exception as e:
        logger.error(f"Test suite failed: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main())
