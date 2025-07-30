"""
Notification service for alerting sales team about high-priority leads
"""

import logging
from typing import Optional, List
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

from .config import settings
from .models import Email, ClassificationResult, SalesforceContact, NotificationData, EmailClassification
from .salesforce_client import SalesforceClient

logger = logging.getLogger(__name__)

class NotificationService:
    """Service for sending notifications to sales team"""
    
    def __init__(self, salesforce_client: SalesforceClient):
        self.salesforce_client = salesforce_client
        self.notification_recipients = [
            "annie@company.com",  # Customize with actual sales team emails
            "sales@company.com"
        ]
    
    async def notify_sales_team(
        self, 
        email: Email, 
        classification: ClassificationResult, 
        contact: Optional[SalesforceContact]
    ) -> bool:
        """Send notification to sales team for high-priority leads"""
        try:
            # Only notify for interested leads
            if classification.classification != EmailClassification.INTERESTED:
                return False
            
            notification_data = NotificationData(
                contact_id=contact.id if contact else "unknown",
                contact_name=f"{contact.first_name or ''} {contact.last_name or ''}".strip() if contact else "Unknown",
                contact_email=email.sender,
                classification=classification.classification,
                email_subject=email.subject,
                email_body=email.body,
                confidence=classification.confidence,
                priority=self._determine_priority(classification, email)
            )
            
            # Send email notification
            email_sent = await self._send_email_notification(notification_data)
            
            # Create Salesforce task
            task_created = False
            if contact:
                task_created = await self._create_salesforce_task(notification_data, contact)
            
            logger.info(f"Notification sent for interested lead: {email.sender}")
            return email_sent or task_created
            
        except Exception as e:
            logger.error(f"Failed to send notification: {e}")
            return False
    
    def _determine_priority(self, classification: ClassificationResult, email: Email) -> str:
        """Determine notification priority based on email content"""
        body_lower = email.body.lower()
        
        # High priority keywords
        high_priority_keywords = [
            "urgent", "asap", "immediately", "today", "this week",
            "budget approved", "ready to buy", "decision maker"
        ]
        
        # Medium priority keywords
        medium_priority_keywords = [
            "interested", "pricing", "demo", "meeting", "call",
            "next week", "schedule"
        ]
        
        if any(keyword in body_lower for keyword in high_priority_keywords):
            return "high"
        elif any(keyword in body_lower for keyword in medium_priority_keywords):
            return "normal"
        else:
            return "normal"
    
    async def _send_email_notification(self, notification_data: NotificationData) -> bool:
        """Send email notification to sales team"""
        try:
            subject = f"🔥 Interested Lead: {notification_data.contact_name} ({notification_data.priority.upper()} Priority)"
            
            body = f"""
New Interested Lead Alert!

Contact Information:
- Name: {notification_data.contact_name}
- Email: {notification_data.contact_email}
- Salesforce ID: {notification_data.contact_id}

Email Details:
- Subject: {notification_data.email_subject}
- Classification: {notification_data.classification}
- Confidence: {notification_data.confidence:.2%}
- Priority: {notification_data.priority.upper()}

Original Email:
{'-' * 50}
{notification_data.email_body}
{'-' * 50}

Recommended Actions:
{'- Respond immediately (within 1 hour)' if notification_data.priority == 'high' else '- Respond within 4 hours'}
- Schedule a follow-up call
- Prepare pricing/demo materials

This notification was generated automatically by the AI Email Agent.
Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
            
            # Send to each recipient
            for recipient in self.notification_recipients:
                msg = MIMEText(body)
                msg['Subject'] = subject
                msg['From'] = settings.SMTP_USERNAME
                msg['To'] = recipient
                
                with smtplib.SMTP(settings.SMTP_SERVER, settings.SMTP_PORT) as server:
                    server.starttls()
                    server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
                    server.send_message(msg)
            
            logger.info(f"Email notifications sent to {len(self.notification_recipients)} recipients")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email notification: {e}")
            return False
    
    async def _create_salesforce_task(
        self, 
        notification_data: NotificationData, 
        contact: SalesforceContact
    ) -> bool:
        """Create a task in Salesforce for the interested lead"""
        try:
            subject = f"Follow up with interested lead: {notification_data.contact_name}"
            
            description = f"""
Interested lead response received via AI Email Agent

Contact: {notification_data.contact_name} ({notification_data.contact_email})
Classification: {notification_data.classification} (Confidence: {notification_data.confidence:.2%})
Priority: {notification_data.priority.upper()}

Original Email Subject: {notification_data.email_subject}

Email Content:
{notification_data.email_body}

Recommended Actions:
- Respond within {'1 hour' if notification_data.priority == 'high' else '4 hours'}
- Schedule follow-up call
- Prepare relevant materials (pricing, demo, etc.)

Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
            
            priority_map = {
                "high": "High",
                "normal": "Normal",
                "low": "Low"
            }
            
            task_created = await self.salesforce_client.create_task(
                contact_id=contact.id,
                subject=subject,
                description=description,
                priority=priority_map.get(notification_data.priority, "Normal")
            )
            
            if task_created:
                logger.info(f"Salesforce task created for contact {contact.id}")
            
            return task_created
            
        except Exception as e:
            logger.error(f"Failed to create Salesforce task: {e}")
            return False
    
    async def send_daily_summary(self) -> bool:
        """Send daily summary of email processing activity"""
        try:
            # This would typically pull stats from a database
            # For now, we'll create a placeholder implementation
            
            subject = f"Daily AI Email Agent Summary - {datetime.now().strftime('%Y-%m-%d')}"
            
            body = f"""
Daily AI Email Agent Summary

Date: {datetime.now().strftime('%Y-%m-%d')}

Email Processing Summary:
- Total emails processed: [To be implemented with stats tracking]
- Interested leads: [Count]
- Maybe interested: [Count]
- Not interested: [Count]

Response Summary:
- Automated responses sent: [Count]
- Notifications sent: [Count]
- Salesforce tasks created: [Count]

Top Performing Keywords:
- [To be implemented with analytics]

System Status: ✅ Healthy

This summary was generated automatically by the AI Email Agent.
"""
            
            for recipient in self.notification_recipients:
                msg = MIMEText(body)
                msg['Subject'] = subject
                msg['From'] = settings.SMTP_USERNAME
                msg['To'] = recipient
                
                with smtplib.SMTP(settings.SMTP_SERVER, settings.SMTP_PORT) as server:
                    server.starttls()
                    server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
                    server.send_message(msg)
            
            logger.info("Daily summary sent")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send daily summary: {e}")
            return False
    
    def add_notification_recipient(self, email: str):
        """Add a new notification recipient"""
        if email not in self.notification_recipients:
            self.notification_recipients.append(email)
            logger.info(f"Added notification recipient: {email}")
    
    def remove_notification_recipient(self, email: str):
        """Remove a notification recipient"""
        if email in self.notification_recipients:
            self.notification_recipients.remove(email)
            logger.info(f"Removed notification recipient: {email}")
    
    def get_notification_recipients(self) -> List[str]:
        """Get list of current notification recipients"""
        return self.notification_recipients.copy()
