"""
Mock email monitoring service for testing without email server access
"""

import logging
from typing import List, Optional
from datetime import datetime
import asyncio
import json
import os
import uuid

from .config import settings
from .models import Email, EmailStatus, ProcessingResult, ProcessingStats
from .ai_classifier import AIClassifier
from .salesforce_client import SalesforceClient
from .response_generator import ResponseGenerator
from .notification_service import NotificationService

logger = logging.getLogger(__name__)

class MockEmailMonitor:
    """Mock email monitor for testing without email server access"""
    
    def __init__(
        self,
        ai_classifier: AIClassifier,
        salesforce_client: SalesforceClient,
        response_generator: ResponseGenerator,
        notification_service: NotificationService
    ):
        self.ai_classifier = ai_classifier
        self.salesforce_client = salesforce_client
        self.response_generator = response_generator
        self.notification_service = notification_service
        self.stats = ProcessingStats()
        self.processed_message_ids = set()
        self.mock_data_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'mock_emails.json')
        self.mock_emails = self._load_mock_emails()
        
    def _load_mock_emails(self) -> List[dict]:
        """Load mock emails from file or create default data"""
        if os.path.exists(self.mock_data_file):
            try:
                with open(self.mock_data_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error loading mock emails: {e}")
        
        # Create default mock emails
        default_emails = [
            {
                "message_id": str(uuid.uuid4()),
                "subject": "Interested in your renewable energy solutions",
                "sender": "potential_client@example.com",
                "recipient": settings.EMAIL_ADDRESS,
                "body": "Hello,\n\nI saw your presentation at the Green Energy Expo and I'm very interested in learning more about your solar panel solutions for our new office building. Could you provide more information about your commercial installations?\n\nBest regards,\nPotential Client",
                "received_date": datetime.now().isoformat(),
                "processed": False
            },
            {
                "message_id": str(uuid.uuid4()),
                "subject": "Re: Green Energy Solutions Proposal",
                "sender": "maybe_interested@example.com",
                "recipient": settings.EMAIL_ADDRESS,
                "body": "Hi Annie,\n\nThanks for sending over the proposal. I'm still reviewing it with my team. We have some questions about the cost estimates and timeline. When would be a good time to schedule a call to discuss further?\n\nRegards,\nMaybe Interested",
                "received_date": datetime.now().isoformat(),
                "processed": False
            },
            {
                "message_id": str(uuid.uuid4()),
                "subject": "Not interested in your services",
                "sender": "not_interested@example.com",
                "recipient": settings.EMAIL_ADDRESS,
                "body": "Hello,\n\nThank you for reaching out, but we've decided to go with another provider for our energy needs. We appreciate your time.\n\nBest,\nNot Interested",
                "received_date": datetime.now().isoformat(),
                "processed": False
            }
        ]
        
        # Save default emails
        self._save_mock_emails(default_emails)
        return default_emails
    
    def _save_mock_emails(self, emails: List[dict]):
        """Save mock emails to file"""
        try:
            with open(self.mock_data_file, 'w') as f:
                json.dump(emails, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving mock emails: {e}")
    
    async def process_new_emails(self):
        """Process new mock emails"""
        logger.info("Starting email processing cycle")
        start_time = datetime.now()
        
        try:
            # Get unprocessed mock emails
            unprocessed_emails = [email for email in self.mock_emails if not email["processed"]]
            logger.info(f"Fetched {len(unprocessed_emails)} new campaign replies")
            
            if not unprocessed_emails:
                logger.info("No new emails to process")
                return
            
            # Process each email
            for mock_email in unprocessed_emails:
                email = Email(
                    message_id=mock_email["message_id"],
                    subject=mock_email["subject"],
                    sender=mock_email["sender"],
                    recipient=mock_email["recipient"],
                    body=mock_email["body"],
                    received_date=datetime.fromisoformat(mock_email["received_date"]),
                    status=EmailStatus.RECEIVED
                )
                
                await self._process_email(email)
                
                # Mark as processed
                mock_email["processed"] = True
            
            # Save updated mock emails
            self._save_mock_emails(self.mock_emails)
            
            # Update stats
            processing_time = (datetime.now() - start_time).total_seconds()
            self.stats.update_processing_time(processing_time)
            logger.info(f"Email processing cycle completed in {processing_time:.2f} seconds")
            
        except Exception as e:
            logger.error(f"Error processing emails: {e}")
            self.stats.increment_errors()
    
    async def _process_email(self, email: Email):
        """Process a single email"""
        try:
            logger.info(f"Processing email: {email.subject}")
            
            # Find contact in Salesforce
            contact = await self.salesforce_client.find_contact_by_email(email.sender)
            
            if not contact:
                logger.warning(f"No contact found for email: {email.sender}")
                email.status = EmailStatus.NO_CONTACT_FOUND
                return
            
            # Classify email
            classification = await self.ai_classifier.classify_email(email.subject, email.body)
            logger.info(f"Email classified as: {classification}")
            
            # Update contact in Salesforce
            await self.salesforce_client.update_contact_campaign_status(contact.id, classification)
            
            # Generate response
            response = await self.response_generator.generate_response(
                email.subject,
                email.body,
                classification,
                contact
            )
            
            # Log the response (would normally send it)
            logger.info(f"Generated response: {response[:100]}...")
            
            # Create activity in Salesforce
            await self.salesforce_client.create_activity(
                contact.id,
                f"Email Response: {email.subject}",
                response
            )
            
            # Send notification if interested
            if classification.value == "Interested":
                await self.notification_service.send_notification(
                    contact,
                    email.subject,
                    email.body,
                    response
                )
                self.stats.increment_notifications()
            
            # Update stats
            self.stats.increment_classification(classification)
            self.stats.increment_responses()
            
            # Update email status
            email.status = EmailStatus.PROCESSED
            
        except Exception as e:
            logger.error(f"Error processing email {email.subject}: {e}")
            email.status = EmailStatus.ERROR
            self.stats.increment_errors()
    
    def add_test_email(self, subject: str, sender: str, body: str):
        """Add a test email for processing"""
        new_email = {
            "message_id": str(uuid.uuid4()),
            "subject": subject,
            "sender": sender,
            "recipient": settings.EMAIL_ADDRESS,
            "body": body,
            "received_date": datetime.now().isoformat(),
            "processed": False
        }
        
        self.mock_emails.append(new_email)
        self._save_mock_emails(self.mock_emails)
        logger.info(f"Added test email: {subject}")
        return new_email["message_id"]
