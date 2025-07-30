"""
Mock Salesforce client for testing without Salesforce API access
"""

import logging
from typing import Optional, List, Dict, Any
import asyncio
from datetime import datetime
import json
import os
import uuid

from .config import settings
from .models import SalesforceContact, EmailClassification

logger = logging.getLogger(__name__)

class MockSalesforceClient:
    """Mock client for Salesforce operations when API access is not available"""
    
    def __init__(self):
        self.sf = None
        self.connected = True
        self.mock_data_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'mock_data.json')
        self.mock_data = self._load_mock_data()
    
    def _load_mock_data(self) -> Dict:
        """Load mock data from file or create default data"""
        if os.path.exists(self.mock_data_file):
            try:
                with open(self.mock_data_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error loading mock data: {e}")
        
        # Create default mock data
        default_data = {
            "contacts": [
                {
                    "id": str(uuid.uuid4()),
                    "email": "test1@example.com",
                    "first_name": "Test",
                    "last_name": "User1",
                    "company": "Test Company",
                    "phone": "555-123-4567",
                    "campaign_status": "Maybe Interested"
                },
                {
                    "id": str(uuid.uuid4()),
                    "email": "test2@example.com",
                    "first_name": "Test",
                    "last_name": "User2",
                    "company": "Another Company",
                    "phone": "555-987-6543",
                    "campaign_status": "Interested"
                }
            ],
            "activities": []
        }
        
        # Save default data
        self._save_mock_data(default_data)
        return default_data
    
    def _save_mock_data(self, data: Dict):
        """Save mock data to file"""
        try:
            with open(self.mock_data_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving mock data: {e}")
    
    async def connect(self):
        """Mock connection to Salesforce"""
        logger.info("Connected to mock Salesforce client (API access not available)")
        await self.ensure_custom_field_exists()
    
    async def ensure_custom_field_exists(self):
        """Mock check for custom field"""
        logger.info("Mock: Campaign_Status__c field exists")
    
    async def find_contact_by_email(self, email: str) -> Optional[SalesforceContact]:
        """Find contact by email in mock data"""
        for contact in self.mock_data["contacts"]:
            if contact["email"].lower() == email.lower():
                return SalesforceContact(
                    id=contact["id"],
                    email=contact["email"],
                    first_name=contact.get("first_name"),
                    last_name=contact.get("last_name"),
                    company=contact.get("company"),
                    phone=contact.get("phone"),
                    campaign_status=contact.get("campaign_status")
                )
        
        # Create new contact if not found
        new_contact = {
            "id": str(uuid.uuid4()),
            "email": email,
            "first_name": None,
            "last_name": "Unknown",
            "company": None,
            "phone": None,
            "campaign_status": None
        }
        
        self.mock_data["contacts"].append(new_contact)
        self._save_mock_data(self.mock_data)
        
        return SalesforceContact(
            id=new_contact["id"],
            email=new_contact["email"],
            first_name=new_contact.get("first_name"),
            last_name=new_contact.get("last_name"),
            company=new_contact.get("company"),
            phone=new_contact.get("phone"),
            campaign_status=new_contact.get("campaign_status")
        )
    
    async def update_contact_campaign_status(self, contact_id: str, classification: EmailClassification) -> bool:
        """Update contact campaign status in mock data"""
        status_mapping = {
            EmailClassification.NOT_INTERESTED: "Not Interested",
            EmailClassification.MAYBE_INTERESTED: "Maybe Interested",
            EmailClassification.INTERESTED: "Interested"
        }
        
        for contact in self.mock_data["contacts"]:
            if contact["id"] == contact_id:
                contact["campaign_status"] = status_mapping[classification]
                self._save_mock_data(self.mock_data)
                logger.info(f"Mock: Updated contact {contact_id} campaign status to {status_mapping[classification]}")
                return True
        
        logger.warning(f"Mock: Contact {contact_id} not found for status update")
        return False
    
    async def create_activity(self, contact_id: str, subject: str, body: str) -> str:
        """Create activity record in mock data"""
        activity_id = str(uuid.uuid4())
        
        activity = {
            "id": activity_id,
            "contact_id": contact_id,
            "subject": subject,
            "body": body,
            "created_date": datetime.now().isoformat()
        }
        
        self.mock_data["activities"].append(activity)
        self._save_mock_data(self.mock_data)
        
        logger.info(f"Mock: Created activity {activity_id} for contact {contact_id}")
        return activity_id
    
    async def get_contact_details(self, contact_id: str) -> Optional[Dict[str, Any]]:
        """Get contact details from mock data"""
        for contact in self.mock_data["contacts"]:
            if contact["id"] == contact_id:
                return {
                    "Id": contact["id"],
                    "Email": contact["email"],
                    "FirstName": contact.get("first_name"),
                    "LastName": contact.get("last_name"),
                    "Company": contact.get("company"),
                    "Phone": contact.get("phone"),
                    "Campaign_Status__c": contact.get("campaign_status")
                }
        
        return None
