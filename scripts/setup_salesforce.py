"""
Script to set up Salesforce custom fields and validate configuration
"""

import asyncio
import logging
from src.salesforce_client import SalesforceClient
from src.config import settings, validate_settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def setup_salesforce():
    """Set up Salesforce configuration and validate custom fields"""
    try:
        # Validate configuration
        validate_settings()
        logger.info("Configuration validated successfully")
        
        # Connect to Salesforce
        sf_client = SalesforceClient()
        await sf_client.connect()
        logger.info("Connected to Salesforce successfully")
        
        # Test basic operations
        logger.info("Testing Salesforce operations...")
        
        # Test querying leads
        try:
            import asyncio
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                lambda: sf_client.sf.query("SELECT Id, Email FROM Lead LIMIT 1")
            )
            logger.info(f"Lead query test successful: {result['totalSize']} records found")
        except Exception as e:
            logger.error(f"Lead query test failed: {e}")
        
        # Test querying contacts
        try:
            result = await loop.run_in_executor(
                None,
                lambda: sf_client.sf.query("SELECT Id, Email FROM Contact LIMIT 1")
            )
            logger.info(f"Contact query test successful: {result['totalSize']} records found")
        except Exception as e:
            logger.error(f"Contact query test failed: {e}")
        
        # Check for custom fields
        logger.info("Checking for required custom fields...")
        
        # Check Lead object
        try:
            lead_describe = await loop.run_in_executor(
                None,
                lambda: sf_client.sf.Lead.describe()
            )
            
            campaign_status_field = next(
                (field for field in lead_describe['fields'] if field['name'] == 'Campaign_Status__c'),
                None
            )
            
            if campaign_status_field:
                logger.info("✅ Campaign_Status__c field found on Lead object")
                logger.info(f"   Field type: {campaign_status_field['type']}")
                if campaign_status_field['type'] == 'picklist':
                    values = [val['value'] for val in campaign_status_field['picklistValues']]
                    logger.info(f"   Picklist values: {values}")
            else:
                logger.warning("❌ Campaign_Status__c field NOT found on Lead object")
                logger.info("   Please create this field manually in Salesforce Setup")
                
        except Exception as e:
            logger.error(f"Error checking Lead custom fields: {e}")
        
        # Check Contact object
        try:
            contact_describe = await loop.run_in_executor(
                None,
                lambda: sf_client.sf.Contact.describe()
            )
            
            campaign_status_field = next(
                (field for field in contact_describe['fields'] if field['name'] == 'Campaign_Status__c'),
                None
            )
            
            if campaign_status_field:
                logger.info("✅ Campaign_Status__c field found on Contact object")
            else:
                logger.warning("❌ Campaign_Status__c field NOT found on Contact object")
                
        except Exception as e:
            logger.error(f"Error checking Contact custom fields: {e}")
        
        logger.info("Salesforce setup validation complete!")
        
    except Exception as e:
        logger.error(f"Salesforce setup failed: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(setup_salesforce())
