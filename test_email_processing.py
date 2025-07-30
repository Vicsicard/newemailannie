"""
AI Email Agent for Salesforce - Test Email Processing Script
This script tests the core functionality of the AI Email Agent without requiring a web server
"""

import asyncio
import logging
import json
import os
from datetime import datetime

from src.config import settings
from src.ai_classifier import AIClassifier
from src.mock_salesforce_client import MockSalesforceClient
from src.response_generator import ResponseGenerator
from src.notification_service import NotificationService
from src.models import Email, EmailStatus, SalesforceContact, EmailClassification

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
# Set all loggers to DEBUG level
for log_name in logging.root.manager.loggerDict:
    logging.getLogger(log_name).setLevel(logging.DEBUG)

# Sample test emails
TEST_EMAILS = [
    {
        "subject": "Interested in your renewable energy solutions",
        "sender": "potential_client@example.com",
        "body": """Hello,

I saw your presentation at the Green Energy Expo and I'm very interested in learning more about your solar panel solutions for our new office building. Could you provide more information about your commercial installations?

Best regards,
Potential Client"""
    },
    {
        "subject": "Re: Green Energy Solutions Proposal",
        "sender": "maybe_interested@example.com",
        "body": """Hi Annie,

Thanks for sending over the proposal. I'm still reviewing it with my team. We have some questions about the cost estimates and timeline. When would be a good time to schedule a call to discuss further?

Regards,
Maybe Interested"""
    },
    {
        "subject": "Not interested in your services",
        "sender": "not_interested@example.com",
        "body": """Hello,

Thank you for reaching out, but we've decided to go with another provider for our energy needs. We appreciate your time.

Best,
Not Interested"""
    }
]

async def process_test_email(email_data, ai_classifier, salesforce_client, response_generator, notification_service):
    """Process a single test email"""
    logger.info(f"Processing test email: {email_data['subject']}")
    
    # Create Email object
    email = Email(
        message_id=f"test-{hash(email_data['subject'])}",
        subject=email_data["subject"],
        sender=email_data["sender"],
        recipient=settings.EMAIL_ADDRESS,
        body=email_data["body"],
        received_date=datetime.now(),
        status=EmailStatus.PENDING
    )
    
    try:
        # Find contact in Salesforce
        contact = await salesforce_client.find_contact_by_email(email.sender)
        
        if not contact:
            logger.warning(f"No contact found for email: {email.sender}")
            logger.info("Creating mock contact for testing")
            # Create a mock contact for testing
            contact = SalesforceContact(
                id=f"mock-{hash(email.sender)}",
                email=email.sender,
                first_name="Test",
                last_name="Contact",
                company="Test Company",
                campaign_status="New"
            )
        
        # Use fallback classification instead of making API calls
        classification = ai_classifier.fallback_classification(email)
        logger.info(f"Email classified as: {classification}")
        
        # Update contact in Salesforce - extract just the classification value
        await salesforce_client.update_contact_campaign_status(contact.id, classification.classification)
        
        # Generate response
        response = await response_generator.generate_response(
            email,
            classification,
            contact
        )
        
        logger.info(f"Generated response for '{email.subject}':")
        logger.info("-" * 40)
        logger.info(response[:500] + "..." if len(response) > 500 else response)
        logger.info("-" * 40)
        
        # Create activity in Salesforce
        await salesforce_client.create_activity(
            contact.id,
            f"Email Response: {email.subject}",
            response
        )
        
        # Send notification if interested
        if classification == EmailClassification.INTERESTED:
            await notification_service.send_notification(
                contact,
                email.subject,
                email.body,
                response
            )
            logger.info(f"Notification sent for interested contact: {contact.email}")
        
        # Update email status
        email.status = EmailStatus.PROCESSED
        logger.info(f"Successfully processed email: {email.subject}")
        
    except Exception as e:
        logger.error(f"Error processing email {email.subject}: {e}")
        email.status = EmailStatus.FAILED

async def main():
    """Main test function"""
    logger.info("Initializing services for testing...")
    
    # Initialize AI classifier
    ai_classifier = AIClassifier()
    logger.info("AI classifier initialized")
    
    # Initialize mock Salesforce client
    salesforce_client = MockSalesforceClient()
    await salesforce_client.connect()
    logger.info("Mock Salesforce client initialized")
    
    # Initialize response generator
    response_generator = ResponseGenerator(ai_classifier)
    logger.info("Response generator initialized")
    
    # Initialize notification service
    notification_service = NotificationService(salesforce_client)
    logger.info("Notification service initialized")
    
    logger.info("All services initialized successfully")
    logger.info("Starting test email processing...")
    
    # Process each test email
    for email_data in TEST_EMAILS:
        await process_test_email(
            email_data,
            ai_classifier,
            salesforce_client,
            response_generator,
            notification_service
        )
    
    logger.info("Test email processing completed")
    
    # Show mock data
    mock_data_file = os.path.join(os.path.dirname(__file__), 'mock_data.json')
    if os.path.exists(mock_data_file):
        try:
            with open(mock_data_file, 'r') as f:
                mock_data = json.load(f)
                logger.info("Mock Salesforce data:")
                logger.info(json.dumps(mock_data, indent=2))
        except Exception as e:
            logger.error(f"Error reading mock data: {e}")

if __name__ == "__main__":
    asyncio.run(main())
