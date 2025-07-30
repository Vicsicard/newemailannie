"""
Email thread management for context-aware processing
"""

import logging
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
import re
from dataclasses import dataclass

from .models import Email
from .config import settings

logger = logging.getLogger(__name__)

@dataclass
class EmailThread:
    """Represents an email conversation thread"""
    thread_id: str
    subject: str
    participants: List[str]
    emails: List[Email]
    first_email_date: datetime
    last_email_date: datetime
    is_campaign_thread: bool = False
    campaign_id: Optional[str] = None

class ThreadManager:
    """Manages email threads and conversation context"""
    
    def __init__(self):
        self.threads: Dict[str, EmailThread] = {}
        self.processed_message_ids = set()
    
    def normalize_subject(self, subject: str) -> str:
        """Normalize email subject for thread grouping"""
        # Remove Re:, Fwd:, etc.
        normalized = re.sub(r'^(Re:|RE:|Fwd:|FWD:|Fw:|FW:)\s*', '', subject, flags=re.IGNORECASE)
        
        # Remove extra whitespace
        normalized = ' '.join(normalized.split())
        
        # Convert to lowercase for comparison
        return normalized.lower().strip()
    
    def extract_thread_id(self, email: Email) -> str:
        """Extract or generate thread ID for an email"""
        # Use Message-ID references if available
        if email.in_reply_to:
            # Find existing thread with this message ID
            for thread_id, thread in self.threads.items():
                for thread_email in thread.emails:
                    if thread_email.message_id == email.in_reply_to:
                        return thread_id
        
        # Use normalized subject + sender domain as thread ID
        normalized_subject = self.normalize_subject(email.subject)
        sender_domain = email.sender.split('@')[1] if '@' in email.sender else email.sender
        
        return f"{sender_domain}_{hash(normalized_subject)}"
    
    def is_duplicate_email(self, email: Email) -> bool:
        """Check if email has already been processed"""
        return email.message_id in self.processed_message_ids
    
    def is_automated_response(self, email: Email) -> bool:
        """Detect automated responses, bounces, and spam"""
        body_lower = email.body.lower()
        subject_lower = email.subject.lower()
        
        # Auto-reply indicators
        auto_reply_indicators = [
            'auto-reply', 'automatic reply', 'out of office', 'out-of-office',
            'vacation reply', 'away message', 'automated response',
            'delivery failure', 'undelivered mail', 'mail delivery failed',
            'bounce', 'mailer-daemon', 'postmaster', 'no-reply', 'noreply',
            'do not reply', 'this is an automated', 'automatically generated'
        ]
        
        # Check subject and body for auto-reply indicators
        for indicator in auto_reply_indicators:
            if indicator in subject_lower or indicator in body_lower:
                return True
        
        # Check for very short responses (likely automated)
        if len(email.body.strip()) < 20:
            return True
        
        # Check sender patterns
        automated_senders = [
            'mailer-daemon', 'postmaster', 'no-reply', 'noreply',
            'automated', 'system', 'admin'
        ]
        
        sender_local = email.sender.split('@')[0].lower()
        for pattern in automated_senders:
            if pattern in sender_local:
                return True
        
        return False
    
    def add_email_to_thread(self, email: Email) -> Tuple[EmailThread, bool]:
        """Add email to appropriate thread, return (thread, is_new_thread)"""
        # Check for duplicates
        if self.is_duplicate_email(email):
            logger.info(f"Duplicate email detected: {email.message_id}")
            return None, False
        
        # Check for automated responses
        if self.is_automated_response(email):
            logger.info(f"Automated response detected: {email.sender}")
            return None, False
        
        thread_id = self.extract_thread_id(email)
        is_new_thread = thread_id not in self.threads
        
        if is_new_thread:
            # Create new thread
            thread = EmailThread(
                thread_id=thread_id,
                subject=self.normalize_subject(email.subject),
                participants=[email.sender, email.recipient],
                emails=[email],
                first_email_date=email.received_date,
                last_email_date=email.received_date,
                is_campaign_thread=self.is_campaign_email(email)
            )
            self.threads[thread_id] = thread
            logger.info(f"Created new thread: {thread_id}")
        else:
            # Add to existing thread
            thread = self.threads[thread_id]
            thread.emails.append(email)
            thread.last_email_date = email.received_date
            
            # Add participant if not already in thread
            if email.sender not in thread.participants:
                thread.participants.append(email.sender)
            
            # Sort emails by date
            thread.emails.sort(key=lambda e: e.received_date)
            logger.info(f"Added email to existing thread: {thread_id}")
        
        # Mark as processed
        self.processed_message_ids.add(email.message_id)
        
        return thread, is_new_thread
    
    def is_campaign_email(self, email: Email) -> bool:
        """Determine if email is part of a campaign"""
        # Check for campaign indicators in subject/body
        campaign_indicators = [
            'campaign', 'newsletter', 'promotion', 'offer',
            'marketing', 'announcement', 'update'
        ]
        
        subject_lower = email.subject.lower()
        body_lower = email.body.lower()
        
        # Check for reply indicators (likely campaign responses)
        is_reply = (
            email.in_reply_to is not None or
            email.references is not None or
            subject_lower.startswith('re:')
        )
        
        # Check for unsubscribe links (campaign emails)
        has_unsubscribe = 'unsubscribe' in body_lower
        
        return is_reply or has_unsubscribe
    
    def get_thread_context(self, thread: EmailThread, max_emails: int = 5) -> str:
        """Get conversation context for AI classification"""
        if len(thread.emails) <= 1:
            return ""
        
        # Get recent emails in thread (excluding current one)
        recent_emails = thread.emails[-max_emails-1:-1]  # Exclude the latest (current) email
        
        context_parts = []
        for i, email in enumerate(recent_emails):
            context_parts.append(f"""
Email {i+1} ({email.received_date.strftime('%Y-%m-%d %H:%M')}):
From: {email.sender}
Subject: {email.subject}
Body: {email.body[:300]}{'...' if len(email.body) > 300 else ''}
""")
        
        return "\n".join(context_parts)
    
    def get_thread_summary(self, thread: EmailThread) -> Dict[str, any]:
        """Get thread summary for analytics"""
        return {
            'thread_id': thread.thread_id,
            'subject': thread.subject,
            'email_count': len(thread.emails),
            'participants': thread.participants,
            'duration_days': (thread.last_email_date - thread.first_email_date).days,
            'is_campaign_thread': thread.is_campaign_thread,
            'campaign_id': thread.campaign_id,
            'first_email': thread.first_email_date.isoformat(),
            'last_email': thread.last_email_date.isoformat()
        }
    
    def cleanup_old_threads(self, days_old: int = 30):
        """Clean up old threads to prevent memory bloat"""
        cutoff_date = datetime.now() - timedelta(days=days_old)
        
        threads_to_remove = []
        for thread_id, thread in self.threads.items():
            if thread.last_email_date < cutoff_date:
                threads_to_remove.append(thread_id)
        
        for thread_id in threads_to_remove:
            del self.threads[thread_id]
            logger.info(f"Cleaned up old thread: {thread_id}")
        
        logger.info(f"Cleaned up {len(threads_to_remove)} old threads")
    
    def get_active_threads(self, days: int = 7) -> List[EmailThread]:
        """Get threads with activity in the last N days"""
        cutoff_date = datetime.now() - timedelta(days=days)
        
        active_threads = []
        for thread in self.threads.values():
            if thread.last_email_date >= cutoff_date:
                active_threads.append(thread)
        
        return sorted(active_threads, key=lambda t: t.last_email_date, reverse=True)
    
    def get_thread_statistics(self) -> Dict[str, any]:
        """Get thread management statistics"""
        total_threads = len(self.threads)
        campaign_threads = sum(1 for t in self.threads.values() if t.is_campaign_thread)
        total_emails = sum(len(t.emails) for t in self.threads.values())
        
        return {
            'total_threads': total_threads,
            'campaign_threads': campaign_threads,
            'non_campaign_threads': total_threads - campaign_threads,
            'total_emails': total_emails,
            'processed_message_ids': len(self.processed_message_ids),
            'active_threads_7d': len(self.get_active_threads(7)),
            'active_threads_30d': len(self.get_active_threads(30))
        }
