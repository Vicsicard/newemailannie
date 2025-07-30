"""
Salesforce integration client
"""

import logging
from typing import Optional, List, Dict, Any
from simple_salesforce import Salesforce
import asyncio
from datetime import datetime

from .config import settings
from .models import SalesforceContact, EmailClassification

logger = logging.getLogger(__name__)

class SalesforceClient:
    """Client for Salesforce REST API operations"""
    
    def __init__(self):
        self.sf = None
        self.connected = False
    
    async def connect(self):
        """Connect to Salesforce"""
        try:
            # Run Salesforce connection in thread pool since it's not async
            loop = asyncio.get_event_loop()
            self.sf = await loop.run_in_executor(
                None,
                lambda: Salesforce(
                    username=settings.SALESFORCE_USERNAME,
                    password=settings.SALESFORCE_PASSWORD,
                    security_token=settings.SALESFORCE_SECURITY_TOKEN,
                    domain=settings.SALESFORCE_DOMAIN
                )
            )
            self.connected = True
            logger.info("Successfully connected to Salesforce")
            
            # Verify custom field exists
            await self.ensure_custom_field_exists()
            
        except Exception as e:
            logger.error(f"Failed to connect to Salesforce: {e}")
            raise
    
    async def ensure_custom_field_exists(self):
        """Ensure the Campaign_Status__c custom field exists"""
        try:
            # Check if custom field exists on Lead object
            loop = asyncio.get_event_loop()
            lead_describe = await loop.run_in_executor(
                None,
                lambda: self.sf.Lead.describe()
            )
            
            field_exists = any(
                field['name'] == 'Campaign_Status__c' 
                for field in lead_describe['fields']
            )
            
            if not field_exists:
                logger.warning(
                    "Campaign_Status__c field not found on Lead object. "
                    "Please create this custom field in Salesforce with picklist values: "
                    "Not Interested, Maybe Interested, Interested"
                )
            else:
                logger.info("Campaign_Status__c field found on Lead object")
                
        except Exception as e:
            logger.error(f"Error checking custom field: {e}")
    
    async def find_contact_by_email(self, email: str) -> Optional[SalesforceContact]:
        """Find contact or lead by email address"""
        try:
            loop = asyncio.get_event_loop()
            
            # First try to find as Contact
            contact_query = f"SELECT Id, Email, FirstName, LastName, Account.Name, Phone, Campaign_Status__c FROM Contact WHERE Email = '{email}' LIMIT 1"
            contact_result = await loop.run_in_executor(
                None,
                lambda: self.sf.query(contact_query)
            )
            
            if contact_result['totalSize'] > 0:
                record = contact_result['records'][0]
                return SalesforceContact(
                    id=record['Id'],
                    email=record['Email'],
                    first_name=record.get('FirstName'),
                    last_name=record.get('LastName'),
                    company=record.get('Account', {}).get('Name') if record.get('Account') else None,
                    phone=record.get('Phone'),
                    campaign_status=record.get('Campaign_Status__c')
                )
            
            # If not found as Contact, try Lead
            lead_query = f"SELECT Id, Email, FirstName, LastName, Company, Phone, Campaign_Status__c, LeadSource FROM Lead WHERE Email = '{email}' AND IsConverted = false LIMIT 1"
            lead_result = await loop.run_in_executor(
                None,
                lambda: self.sf.query(lead_query)
            )
            
            if lead_result['totalSize'] > 0:
                record = lead_result['records'][0]
                return SalesforceContact(
                    id=record['Id'],
                    email=record['Email'],
                    first_name=record.get('FirstName'),
                    last_name=record.get('LastName'),
                    company=record.get('Company'),
                    phone=record.get('Phone'),
                    campaign_status=record.get('Campaign_Status__c'),
                    lead_source=record.get('LeadSource')
                )
            
            logger.warning(f"No contact or lead found for email: {email}")
            return None
            
        except Exception as e:
            logger.error(f"Error finding contact by email {email}: {e}")
            return None
    
    async def update_campaign_status(self, contact_id: str, status: str) -> bool:
        """Update campaign status for a contact or lead"""
        try:
            loop = asyncio.get_event_loop()
            
            # Determine if it's a Contact or Lead based on ID prefix
            if contact_id.startswith('003'):  # Contact ID prefix
                await loop.run_in_executor(
                    None,
                    lambda: self.sf.Contact.update(contact_id, {
                        'Campaign_Status__c': status,
                        'Last_Campaign_Response__c': datetime.now().isoformat()
                    })
                )
                logger.info(f"Updated Contact {contact_id} campaign status to: {status}")
                
            elif contact_id.startswith('00Q'):  # Lead ID prefix
                await loop.run_in_executor(
                    None,
                    lambda: self.sf.Lead.update(contact_id, {
                        'Campaign_Status__c': status,
                        'Last_Campaign_Response__c': datetime.now().isoformat()
                    })
                )
                logger.info(f"Updated Lead {contact_id} campaign status to: {status}")
                
            else:
                logger.error(f"Unknown record type for ID: {contact_id}")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error updating campaign status for {contact_id}: {e}")
            return False
    
    async def create_task(self, contact_id: str, subject: str, description: str, priority: str = "Normal") -> bool:
        """Create a task in Salesforce"""
        try:
            loop = asyncio.get_event_loop()
            
            # Determine WhoId based on record type
            who_id = contact_id if contact_id.startswith(('003', '00Q')) else None
            
            task_data = {
                'Subject': subject,
                'Description': description,
                'Priority': priority,
                'Status': 'Not Started',
                'ActivityDate': datetime.now().date().isoformat(),
                'WhoId': who_id
            }
            
            result = await loop.run_in_executor(
                None,
                lambda: self.sf.Task.create(task_data)
            )
            
            logger.info(f"Created task {result['id']} for contact {contact_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error creating task for {contact_id}: {e}")
            return False
    
    async def get_campaign_members(self, campaign_id: str) -> List[Dict[str, Any]]:
        """Get members of a specific campaign"""
        try:
            loop = asyncio.get_event_loop()
            
            query = f"""
            SELECT Id, ContactId, LeadId, Status, HasResponded, 
                   Contact.Email, Contact.FirstName, Contact.LastName,
                   Lead.Email, Lead.FirstName, Lead.LastName
            FROM CampaignMember 
            WHERE CampaignId = '{campaign_id}'
            """
            
            result = await loop.run_in_executor(
                None,
                lambda: self.sf.query_all(query)
            )
            
            return result['records']
            
        except Exception as e:
            logger.error(f"Error getting campaign members for {campaign_id}: {e}")
            return []
    
    async def remove_from_campaign(self, contact_id: str, campaign_id: str) -> bool:
        """Remove contact from campaign (for not interested responses)"""
        try:
            loop = asyncio.get_event_loop()
            
            # Find campaign member record
            query = f"""
            SELECT Id FROM CampaignMember 
            WHERE CampaignId = '{campaign_id}' 
            AND (ContactId = '{contact_id}' OR LeadId = '{contact_id}')
            """
            
            result = await loop.run_in_executor(
                None,
                lambda: self.sf.query(query)
            )
            
            if result['totalSize'] > 0:
                member_id = result['records'][0]['Id']
                
                # Update status instead of deleting (preserve history)
                await loop.run_in_executor(
                    None,
                    lambda: self.sf.CampaignMember.update(member_id, {
                        'Status': 'Unsubscribed',
                        'HasResponded': True
                    })
                )
                
                logger.info(f"Removed contact {contact_id} from campaign {campaign_id}")
                return True
            else:
                logger.warning(f"Campaign member not found: {contact_id} in {campaign_id}")
                return False
                
        except Exception as e:
            logger.error(f"Error removing from campaign: {e}")
            return False
    
    async def get_contact_campaigns(self, contact_id: str) -> List[Dict[str, Any]]:
        """Get all campaigns for a contact"""
        try:
            loop = asyncio.get_event_loop()
            
            query = f"""
            SELECT Campaign.Id, Campaign.Name, Status, HasResponded
            FROM CampaignMember 
            WHERE (ContactId = '{contact_id}' OR LeadId = '{contact_id}')
            AND Status != 'Unsubscribed'
            """
            
            result = await loop.run_in_executor(
                None,
                lambda: self.sf.query_all(query)
            )
            
            return result['records']
            
        except Exception as e:
            logger.error(f"Error getting contact campaigns for {contact_id}: {e}")
            return []
    
    def is_connected(self) -> bool:
        """Check if connected to Salesforce"""
        return self.connected and self.sf is not None
