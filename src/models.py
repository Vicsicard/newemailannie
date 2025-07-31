"""
Data models for the AI Email Agent
"""

from pydantic import BaseModel, EmailStr
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum

class EmailClassification(str, Enum):
    """Email classification categories"""
    NOT_INTERESTED = "Not Interested"
    MAYBE_INTERESTED = "Maybe Interested"
    INTERESTED = "Interested"

class EmailStatus(str, Enum):
    """Email processing status"""
    PENDING = "pending"
    PROCESSED = "processed"
    FAILED = "failed"
    SKIPPED = "skipped"

class Email(BaseModel):
    """Email data model"""
    message_id: str
    subject: str
    sender: EmailStr
    recipient: EmailStr
    body: str
    html_body: Optional[str] = None
    received_date: datetime
    in_reply_to: Optional[str] = None
    references: Optional[str] = None
    status: EmailStatus = EmailStatus.PENDING
    
class ClassificationResult(BaseModel):
    """AI classification result"""
    classification: EmailClassification
    confidence: float
    reasoning: str
    keywords: List[str] = []
    sentiment_score: Optional[float] = None

class SalesforceContact(BaseModel):
    """Salesforce contact/lead data"""
    id: str
    email: EmailStr
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    company: Optional[str] = None
    phone: Optional[str] = None
    campaign_status: Optional[str] = None
    lead_source: Optional[str] = None
    record_type: Optional[str] = None  # 'Contact' or 'Lead'
    
class EmailResponse(BaseModel):
    """Generated email response"""
    subject: str
    body: str
    html_body: Optional[str] = None
    template_used: str
    personalization_data: Dict[str, Any] = {}

class ProcessingResult(BaseModel):
    """Email processing result"""
    email_id: str
    classification: ClassificationResult
    salesforce_updated: bool
    response_sent: bool
    notification_sent: bool
    errors: List[str] = []
    processing_time: float
    
class CampaignRule(BaseModel):
    """Campaign-specific processing rules"""
    campaign_id: str
    campaign_name: str
    auto_respond: bool = True
    response_templates: Dict[EmailClassification, str] = {}
    notification_recipients: List[EmailStr] = []
    custom_fields: Dict[str, Any] = {}

class NotificationData(BaseModel):
    """Notification data for sales team"""
    contact_id: str
    contact_name: str
    contact_email: EmailStr
    classification: EmailClassification
    email_subject: str
    email_body: str
    confidence: float
    campaign_name: Optional[str] = None
    priority: str = "normal"  # low, normal, high, urgent

class ProcessingStats(BaseModel):
    """Processing statistics"""
    total_emails_processed: int = 0
    classifications: Dict[EmailClassification, int] = {
        EmailClassification.NOT_INTERESTED: 0,
        EmailClassification.MAYBE_INTERESTED: 0,
        EmailClassification.INTERESTED: 0
    }
    responses_sent: int = 0
    notifications_sent: int = 0
    errors: int = 0
    average_processing_time: float = 0.0
    last_processed: Optional[datetime] = None

class SearchResult(BaseModel):
    """Search results with pagination metadata"""
    results: List[SalesforceContact] = []
    total_count: int = 0
    page: int = 1
    page_size: int = 20
    has_more: bool = False
    error: Optional[str] = None
    
class EmailSearchResult(BaseModel):
    """Email search results with pagination metadata"""
    emails: List[Email] = []
    total_count: int = 0
    page: int = 1
    page_size: int = 20
    has_more: bool = False
    error: Optional[str] = None
