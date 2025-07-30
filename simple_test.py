"""
AI Email Agent for Salesforce - Simple Test Script
This script tests the core functionality of the AI Email Agent with a single test email
"""

import asyncio
import logging
import json
from datetime import datetime

from src.config import settings
from src.ai_classifier import AIClassifier
from src.mock_salesforce_client import MockSalesforceClient
from src.response_generator import ResponseGenerator
from src.models import Email, EmailStatus, SalesforceContact, EmailClassification

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Test email data
TEST_EMAIL = {
    "subject": "Interested in your renewable energy solutions",
    "sender": "potential_client@example.com",
    "body": """Hello,

I saw your presentation at the Green Energy Expo and I'm very interested in learning more about your solar panel solutions for our new office building. Could you provide more information about your commercial installations?

Best regards,
Potential Client"""
}

async def main():
    """Main test function"""
    logger.info("Starting simple test of AI Email Agent core functionality...")
    
    # Create test email
    email = Email(
        message_id="test-123456",
        subject=TEST_EMAIL["subject"],
        sender=TEST_EMAIL["sender"],
        recipient=settings.EMAIL_ADDRESS,
        body=TEST_EMAIL["body"],
        received_date=datetime.now(),
        status=EmailStatus.PENDING
    )
    
    # Initialize AI classifier
    logger.info("Initializing AI classifier...")
    ai_classifier = AIClassifier()
    
    # Classify email using the fallback method (no API call)
    logger.info("Classifying test email...")
    classification_result = ai_classifier.fallback_classification(email)
    logger.info(f"Email classified as: {classification_result.classification.value}")
    logger.info(f"Classification confidence: {classification_result.confidence}")
    logger.info(f"Reasoning: {classification_result.reasoning}")
    
    # Initialize mock Salesforce client
    logger.info("Initializing mock Salesforce client...")
    salesforce_client = MockSalesforceClient()
    await salesforce_client.connect()
    
    # Create a mock contact
    logger.info("Creating mock contact...")
    contact = SalesforceContact(
        id="mock-contact-123",
        email=email.sender,
        first_name="Test",
        last_name="Client",
        company="Test Company",
        campaign_status="New"
    )
    
    # Update contact in Salesforce
    logger.info("Updating contact in Salesforce...")
    await salesforce_client.update_contact_campaign_status(
        contact.id, 
        classification_result.classification
    )
    
    # Check the updated contact
    updated_contact = await salesforce_client.find_contact_by_email(email.sender)
    if updated_contact:
        logger.info(f"Contact updated with campaign status: {updated_contact.campaign_status}")
    
    # Initialize response generator
    logger.info("Initializing response generator...")
    response_generator = ResponseGenerator(ai_classifier)
    
    # Generate response using template (fallback method)
    logger.info("Generating response...")
    response = response_generator.generate_template_response(email, classification_result, updated_contact)
    
    logger.info(f"Response generated using template: {response.template_used}")
    logger.info(f"Subject: {response.subject}")
    logger.info("Body:")
    logger.info(response.body)
    
    # Save response to file for review
    with open('test_response.json', 'w') as f:
        json.dump({
            'subject': response.subject,
            'body': response.body,
            'template_used': response.template_used,
            'personalization_data': response.personalization_data
        }, f, indent=2)
    logger.info("Response saved to test_response.json")
    
    logger.info("Test completed successfully!")

if __name__ == "__main__":
    asyncio.run(main())
