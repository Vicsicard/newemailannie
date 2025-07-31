"""
Email search service for searching through monitored emails
"""

import imaplib
import email
import logging
from typing import List, Dict, Optional, Any, Union
from datetime import datetime, timedelta
import asyncio
import re
from email.header import decode_header

from .config import settings
from .models import Email, EmailSearchResult

logger = logging.getLogger(__name__)

class EmailSearchService:
    """Service for searching through emails in the monitored inbox"""
    
    def __init__(self):
        self.email_cache = {}  # Cache to store retrieved emails
        self.last_cache_update = None
    
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
    
    def decode_mime_header(self, header_value):
        """Decode MIME encoded email headers"""
        if not header_value:
            return ""
            
        decoded_parts = []
        for part, encoding in decode_header(header_value):
            if isinstance(part, bytes):
                if encoding:
                    try:
                        decoded_parts.append(part.decode(encoding))
                    except:
                        decoded_parts.append(part.decode('utf-8', errors='replace'))
                else:
                    decoded_parts.append(part.decode('utf-8', errors='replace'))
            else:
                decoded_parts.append(part)
                
        return " ".join(decoded_parts)
    
    def parse_email_message(self, raw_message: bytes) -> Optional[Email]:
        """Parse raw email message into Email model"""
        try:
            msg = email.message_from_bytes(raw_message)
            
            # Extract basic fields
            message_id = msg.get('Message-ID', '')
            subject = self.decode_mime_header(msg.get('Subject', ''))
            sender = self.decode_mime_header(msg.get('From', ''))
            recipient = self.decode_mime_header(msg.get('To', settings.EMAIL_ADDRESS))
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
                        payload = part.get_payload(decode=True)
                        if payload:
                            body = payload.decode('utf-8', errors='ignore')
                    elif content_type == "text/html":
                        payload = part.get_payload(decode=True)
                        if payload:
                            html_body = payload.decode('utf-8', errors='ignore')
            else:
                payload = msg.get_payload(decode=True)
                if payload:
                    body = payload.decode('utf-8', errors='ignore')
            
            # Clean sender email
            sender_match = re.search(r'<(.+?)>', sender)
            if sender_match:
                sender_email = sender_match.group(1)
            else:
                sender_email = sender
            
            return Email(
                message_id=message_id,
                subject=subject,
                sender=sender_email,
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
    
    async def refresh_email_cache(self, days: int = 30) -> bool:
        """Refresh the email cache with emails from the past X days"""
        mail = None
        
        try:
            # Only refresh if cache is empty or older than 1 hour
            current_time = datetime.now()
            if (self.last_cache_update and 
                (current_time - self.last_cache_update).total_seconds() < 3600 and 
                self.email_cache):
                logger.info("Using cached emails (cache is less than 1 hour old)")
                return True
                
            mail = await self.connect_to_email()
            
            # Search for emails from the last X days
            since_date = (current_time - timedelta(days=days)).strftime("%d-%b-%Y")
            search_criteria = f'(SINCE "{since_date}")'
            
            status, message_ids = mail.search(None, search_criteria)
            
            if status != 'OK':
                logger.error("Failed to search emails")
                return False
                
            message_ids = message_ids[0].split()
            logger.info(f"Found {len(message_ids)} emails in the last {days} days")
            
            # Clear the cache
            self.email_cache = {}
            
            # Process emails in batches to avoid memory issues
            batch_size = 100
            for i in range(0, len(message_ids), batch_size):
                batch_ids = message_ids[i:i+batch_size]
                
                for msg_id in batch_ids:
                    try:
                        status, msg_data = mail.fetch(msg_id, '(RFC822)')
                        if status == 'OK' and msg_data and msg_data[0]:
                            raw_message = msg_data[0][1]
                            email_obj = self.parse_email_message(raw_message)
                            
                            if email_obj and email_obj.message_id:
                                self.email_cache[email_obj.message_id] = email_obj
                    except Exception as e:
                        logger.error(f"Error processing message {msg_id}: {e}")
            
            self.last_cache_update = current_time
            logger.info(f"Email cache refreshed with {len(self.email_cache)} emails")
            return True
            
        except Exception as e:
            logger.error(f"Error refreshing email cache: {e}")
            return False
        finally:
            if mail:
                try:
                    mail.close()
                    mail.logout()
                except:
                    pass
    
    async def search_emails(self, 
                           search_term: str = None,
                           sender: str = None, 
                           subject: str = None,
                           date_from: datetime = None,
                           date_to: datetime = None,
                           limit: int = 20,
                           offset: int = 0) -> EmailSearchResult:
        """
        Search through cached emails with various filters
        
        Args:
            search_term: General search term to look for in subject or body
            sender: Filter by sender email address
            subject: Filter by subject text
            date_from: Filter emails after this date
            date_to: Filter emails before this date
            limit: Maximum number of emails to return
            offset: Number of emails to skip for pagination
            
        Returns:
            EmailSearchResult with matching emails and pagination metadata
        """
        try:
            # Ensure cache is up to date
            cache_refreshed = await self.refresh_email_cache()
            if not cache_refreshed:
                return EmailSearchResult(
                    emails=[],
                    total_count=0,
                    page=1,
                    page_size=limit,
                    has_more=False,
                    error="Failed to refresh email cache"
                )
            
            # Apply filters
            filtered_emails = list(self.email_cache.values())
            
            if sender:
                sender = sender.lower()
                filtered_emails = [e for e in filtered_emails if sender in e.sender.lower()]
                
            if subject:
                subject = subject.lower()
                filtered_emails = [e for e in filtered_emails if subject in e.subject.lower()]
                
            if search_term:
                search_term = search_term.lower()
                filtered_emails = [
                    e for e in filtered_emails 
                    if search_term in e.subject.lower() or search_term in e.body.lower()
                ]
                
            if date_from:
                filtered_emails = [e for e in filtered_emails if e.received_date >= date_from]
                
            if date_to:
                filtered_emails = [e for e in filtered_emails if e.received_date <= date_to]
            
            # Sort by date (newest first)
            filtered_emails.sort(key=lambda x: x.received_date, reverse=True)
            
            # Apply pagination
            total_count = len(filtered_emails)
            paginated_emails = filtered_emails[offset:offset+limit]
            
            return EmailSearchResult(
                emails=paginated_emails,
                total_count=total_count,
                page=offset // limit + 1 if limit > 0 else 1,
                page_size=limit,
                has_more=total_count > (offset + len(paginated_emails))
            )
            
        except Exception as e:
            logger.error(f"Error searching emails: {e}")
            return EmailSearchResult(
                emails=[],
                total_count=0,
                page=1,
                page_size=limit,
                has_more=False,
                error=str(e)
            )
    
    async def get_email_by_id(self, message_id: str) -> Optional[Email]:
        """Get a specific email by its message ID"""
        try:
            # Check cache first
            if message_id in self.email_cache:
                return self.email_cache[message_id]
            
            # If not in cache, try to refresh cache
            await self.refresh_email_cache()
            
            # Check again after refresh
            if message_id in self.email_cache:
                return self.email_cache[message_id]
            
            # If still not found, try to fetch directly
            mail = await self.connect_to_email()
            
            try:
                status, message_ids = mail.search(None, f'(HEADER Message-ID "{message_id}")')
                
                if status == 'OK' and message_ids[0]:
                    msg_id = message_ids[0].split()[0]
                    status, msg_data = mail.fetch(msg_id, '(RFC822)')
                    
                    if status == 'OK' and msg_data and msg_data[0]:
                        raw_message = msg_data[0][1]
                        email_obj = self.parse_email_message(raw_message)
                        
                        if email_obj:
                            # Add to cache
                            self.email_cache[email_obj.message_id] = email_obj
                            return email_obj
            finally:
                mail.close()
                mail.logout()
            
            logger.warning(f"Email with message ID {message_id} not found")
            return None
            
        except Exception as e:
            logger.error(f"Error getting email by ID {message_id}: {e}")
            return None
    
    async def get_email_thread(self, message_id: str) -> List[Email]:
        """Get all emails in the same thread as the specified email"""
        try:
            # Get the initial email
            email_obj = await self.get_email_by_id(message_id)
            if not email_obj:
                return []
            
            # Find all related emails in the cache
            thread_emails = []
            
            # Ensure cache is up to date
            await self.refresh_email_cache()
            
            # Find emails in the same thread
            for cached_email in self.email_cache.values():
                # Check if this email is part of the thread
                is_in_thread = False
                
                # Check if message_id matches references or in_reply_to
                if cached_email.references and email_obj.message_id in cached_email.references:
                    is_in_thread = True
                    
                if cached_email.in_reply_to and email_obj.message_id == cached_email.in_reply_to:
                    is_in_thread = True
                
                # Check if email's references or in_reply_to match this message_id
                if email_obj.references and cached_email.message_id in email_obj.references:
                    is_in_thread = True
                    
                if email_obj.in_reply_to and cached_email.message_id == email_obj.in_reply_to:
                    is_in_thread = True
                
                # Add to thread if related
                if is_in_thread:
                    thread_emails.append(cached_email)
            
            # Add the original email if not already included
            if email_obj not in thread_emails:
                thread_emails.append(email_obj)
            
            # Sort by date
            thread_emails.sort(key=lambda x: x.received_date)
            
            return thread_emails
            
        except Exception as e:
            logger.error(f"Error getting email thread for {message_id}: {e}")
            return []
