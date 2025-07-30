"""
Email monitoring service for processing incoming campaign replies
"""

import imaplib
import email
import logging
from typing import List, Optional
from datetime import datetime, timedelta
import asyncio
import re

from .config import settings
from .models import Email, EmailStatus, ProcessingResult, ProcessingStats
from .ai_classifier import AIClassifier
from .salesforce_client import SalesforceClient
from .response_generator import ResponseGenerator
from .notification_service import NotificationService

logger = logging.getLogger(__name__)

class EmailMonitor:
    """Monitor and process incoming emails"""
    
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
        
    async def connect_to_email(self) -> imaplib.IMAP4_SSL:
        """Connect to email server"""
        try:
            mail = imaplib.IMAP4_SSL(settings.IMAP_SERVER, settings.IMAP_PORT)
            mail.login(settings.EMAIL_ADDRESS, settings.EMAIL_PASSWORD)
            mail.select('INBOX')
            logger.info(f"Connected to email server: {settings.IMAP_SERVER}")
            return mail
        except Exception as e:
            logger.error(f"Failed to connect to email server: {e}")
            raise
    
    def parse_email_message(self, raw_message: bytes) -> Optional[Email]:
        """Parse raw email message into Email model"""
        try:
            msg = email.message_from_bytes(raw_message)
            
            # Extract basic fields
            message_id = msg.get('Message-ID', '')
            subject = msg.get('Subject', '')
            sender = msg.get('From', '')
            recipient = msg.get('To', settings.EMAIL_ADDRESS)
            date_str = msg.get('Date', '')
            in_reply_to = msg.get('In-Reply-To')
            references = msg.get('References')
            
            # Parse date
            try:
                received_date = email.utils.parsedate_to_datetime(date_str)
            except:
                received_date = datetime.now()
            
            # Extract email body
            body = ""
            html_body = None
            
            if msg.is_multipart():
                for part in msg.walk():
                    content_type = part.get_content_type()
                    if content_type == "text/plain":
                        body = part.get_payload(decode=True).decode('utf-8', errors='ignore')
                    elif content_type == "text/html":
                        html_body = part.get_payload(decode=True).decode('utf-8', errors='ignore')
            else:
                body = msg.get_payload(decode=True).decode('utf-8', errors='ignore')
            
            # Clean sender email
            sender_match = re.search(r'<(.+?)>', sender)
            if sender_match:
                sender = sender_match.group(1)
            
            return Email(
                message_id=message_id,
                subject=subject,
                sender=sender,
                recipient=recipient,
                body=body,
                html_body=html_body,
                received_date=received_date,
                in_reply_to=in_reply_to,
                references=references
            )
            
        except Exception as e:
            logger.error(f"Failed to parse email message: {e}")
            return None
    
    def is_campaign_reply(self, email_obj: Email) -> bool:
        """Check if email is a reply to a campaign"""
        # Check for reply indicators
        reply_indicators = [
            email_obj.in_reply_to is not None,
            email_obj.references is not None,
            email_obj.subject.lower().startswith('re:'),
            'unsubscribe' not in email_obj.body.lower(),
            len(email_obj.body.strip()) > 10  # Not just auto-reply
        ]
        
        return any(reply_indicators)
    
    async def fetch_new_emails(self) -> List[Email]:
        """Fetch new emails from the server"""
        emails = []
        mail = None
        
        try:
            mail = await self.connect_to_email()
            
            # Search for emails from the last 24 hours
            since_date = (datetime.now() - timedelta(days=1)).strftime("%d-%b-%Y")
            search_criteria = f'(SINCE "{since_date}")'
            
            status, message_ids = mail.search(None, search_criteria)
            
            if status == 'OK':
                message_ids = message_ids[0].split()
                logger.info(f"Found {len(message_ids)} emails to check")
                
                for msg_id in message_ids[-settings.MAX_EMAILS_PER_BATCH:]:  # Limit batch size
                    try:
                        status, msg_data = mail.fetch(msg_id, '(RFC822)')
                        if status == 'OK':
                            raw_message = msg_data[0][1]
                            email_obj = self.parse_email_message(raw_message)
                            
                            if email_obj and email_obj.message_id not in self.processed_message_ids:
                                if self.is_campaign_reply(email_obj):
                                    emails.append(email_obj)
                                    self.processed_message_ids.add(email_obj.message_id)
                                else:
                                    logger.debug(f"Skipping non-campaign email: {email_obj.subject}")
                    except Exception as e:
                        logger.error(f"Error processing message {msg_id}: {e}")
                        
        except Exception as e:
            logger.error(f"Error fetching emails: {e}")
        finally:
            if mail:
                try:
                    mail.close()
                    mail.logout()
                except:
                    pass
        
        logger.info(f"Fetched {len(emails)} new campaign replies")
        return emails
    
    async def process_email(self, email_obj: Email) -> ProcessingResult:
        """Process a single email"""
        start_time = datetime.now()
        errors = []
        
        try:
            logger.info(f"Processing email from {email_obj.sender}: {email_obj.subject}")
            
            # Step 1: Classify the email
            classification = await self.ai_classifier.classify_email(email_obj)
            logger.info(f"Classification: {classification.classification} (confidence: {classification.confidence})")
            
            # Step 2: Update Salesforce
            salesforce_updated = False
            try:
                contact = await self.salesforce_client.find_contact_by_email(email_obj.sender)
                if contact:
                    await self.salesforce_client.update_campaign_status(
                        contact.id, 
                        classification.classification.value
                    )
                    salesforce_updated = True
                    logger.info(f"Updated Salesforce contact: {contact.id}")
                else:
                    logger.warning(f"Contact not found in Salesforce: {email_obj.sender}")
                    errors.append(f"Contact not found: {email_obj.sender}")
            except Exception as e:
                logger.error(f"Salesforce update failed: {e}")
                errors.append(f"Salesforce update failed: {str(e)}")
            
            # Step 3: Generate and send response (if appropriate)
            response_sent = False
            if classification.classification in ['Maybe Interested', 'Interested']:
                try:
                    response = await self.response_generator.generate_response(
                        email_obj, classification, contact
                    )
                    await self.response_generator.send_response(email_obj.sender, response)
                    response_sent = True
                    logger.info(f"Response sent to {email_obj.sender}")
                except Exception as e:
                    logger.error(f"Response generation/sending failed: {e}")
                    errors.append(f"Response failed: {str(e)}")
            
            # Step 4: Send notification (for interested leads)
            notification_sent = False
            if classification.classification == 'Interested':
                try:
                    await self.notification_service.notify_sales_team(
                        email_obj, classification, contact
                    )
                    notification_sent = True
                    logger.info(f"Notification sent for interested lead: {email_obj.sender}")
                except Exception as e:
                    logger.error(f"Notification failed: {e}")
                    errors.append(f"Notification failed: {str(e)}")
            
            # Update statistics
            self.stats.total_emails_processed += 1
            self.stats.classifications[classification.classification] += 1
            if response_sent:
                self.stats.responses_sent += 1
            if notification_sent:
                self.stats.notifications_sent += 1
            if errors:
                self.stats.errors += 1
            
            processing_time = (datetime.now() - start_time).total_seconds()
            self.stats.average_processing_time = (
                (self.stats.average_processing_time * (self.stats.total_emails_processed - 1) + processing_time) 
                / self.stats.total_emails_processed
            )
            self.stats.last_processed = datetime.now()
            
            return ProcessingResult(
                email_id=email_obj.message_id,
                classification=classification,
                salesforce_updated=salesforce_updated,
                response_sent=response_sent,
                notification_sent=notification_sent,
                errors=errors,
                processing_time=processing_time
            )
            
        except Exception as e:
            logger.error(f"Error processing email {email_obj.message_id}: {e}")
            self.stats.errors += 1
            return ProcessingResult(
                email_id=email_obj.message_id,
                classification=classification if 'classification' in locals() else None,
                salesforce_updated=False,
                response_sent=False,
                notification_sent=False,
                errors=[str(e)],
                processing_time=(datetime.now() - start_time).total_seconds()
            )
    
    async def process_new_emails(self):
        """Main processing loop"""
        try:
            logger.info("Starting email processing cycle")
            
            # Fetch new emails
            emails = await self.fetch_new_emails()
            
            if not emails:
                logger.info("No new emails to process")
                return
            
            # Process each email
            results = []
            for email_obj in emails:
                result = await self.process_email(email_obj)
                results.append(result)
                
                # Small delay between processing emails
                await asyncio.sleep(1)
            
            # Log summary
            successful = len([r for r in results if not r.errors])
            failed = len([r for r in results if r.errors])
            logger.info(f"Processing complete: {successful} successful, {failed} failed")
            
        except Exception as e:
            logger.error(f"Error in email processing cycle: {e}")
    
    def get_stats(self) -> dict:
        """Get processing statistics"""
        return self.stats.dict()
