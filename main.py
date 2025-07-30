"""
AI Email Agent for Salesforce
Main application entry point
"""

import os
import logging
import asyncio
import imaplib
from datetime import datetime, timedelta
from typing import Optional
from threading import Thread
from fastapi import FastAPI, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import schedule
import time
from threading import Thread

from src.config import settings
from src.email_monitor import EmailMonitor
from src.mock_email_monitor import MockEmailMonitor
from src.ai_classifier import AIClassifier
from src.salesforce_client import SalesforceClient
from src.mock_salesforce_client import MockSalesforceClient
from src.response_generator import ResponseGenerator
from src.notification_service import NotificationService

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global services
email_monitor = None
ai_classifier = None
salesforce_client = None
response_generator = None
notification_service = None

async def initialize_services():
    """Initialize all services"""
    global email_monitor, ai_classifier, salesforce_client, response_generator, notification_service
    
    logger.info("Initializing services...")
    
    # Initialize AI classifier
    ai_classifier = AIClassifier()
    
    # Initialize Salesforce client
    logger.info("Attempting to connect to Salesforce...")
    try:
        sf_client = SalesforceClient()
        await sf_client.connect()
        salesforce_client = sf_client
    except Exception as e:
        if "API_DISABLED_FOR_ORG" in str(e):
            logger.warning("Salesforce API access is disabled. Using mock Salesforce client instead.")
            logger.warning("Please contact your Salesforce administrator to enable API access.")
            salesforce_client = MockSalesforceClient()
            await salesforce_client.connect()
        else:
            logger.error(f"Failed to initialize Salesforce client: {e}")
            raise
    
    # Initialize response generator
    response_generator = ResponseGenerator(ai_classifier)
    
    # Initialize notification service
    notification_service = NotificationService(salesforce_client)
    
    # Initialize email monitor
    logger.info("Attempting to connect to email server...")
    try:
        # Create the real email monitor
        real_email_monitor = EmailMonitor(
            ai_classifier,
            salesforce_client,
            response_generator,
            notification_service
        )
        
        # Test connection by creating a temporary connection
        # We'll create a new connection when actually processing emails
        test_mail = None
        try:
            test_mail = imaplib.IMAP4_SSL(settings.IMAP_SERVER, settings.IMAP_PORT)
            test_mail.login(settings.EMAIL_ADDRESS, settings.EMAIL_PASSWORD)
            test_mail.select('INBOX')
            logger.info(f"Successfully connected to email server: {settings.IMAP_SERVER}")
            email_monitor = real_email_monitor
        except Exception as mail_error:
            logger.warning(f"Failed to connect to email server: {mail_error}")
            logger.warning("Using mock email monitor instead.")
            logger.warning("Please check your email credentials in the .env file or enable app password if using MFA.")
            email_monitor = MockEmailMonitor(
                ai_classifier,
                salesforce_client,
                response_generator,
                notification_service
            )
            logger.info("Mock email monitor initialized")
        finally:
            # Close test connection if it was opened
            if test_mail:
                try:
                    test_mail.close()
                    test_mail.logout()
                except:
                    pass
    except Exception as e:
        logger.error(f"Failed to initialize email monitor: {e}")
        raise
    
    logger.info("All services initialized successfully")
    logger.info("AI Email Agent started successfully")

async def process_emails():
    """Process emails - called by scheduler"""
    try:
        if email_monitor:
            await email_monitor.process_new_emails()
    except Exception as e:
        logger.error(f"Error processing emails: {e}")

def run_scheduler():
    """Run the email processing scheduler in a separate thread"""
    schedule.every(settings.CHECK_INTERVAL_MINUTES).minutes.do(
        lambda: asyncio.create_task(process_emails())
    )
    
    while True:
        schedule.run_pending()
        time.sleep(1)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    await initialize_services()
    
    # Start scheduler in background thread
    scheduler_thread = Thread(target=run_scheduler, daemon=True)
    scheduler_thread.start()
    
    logger.info("AI Email Agent started successfully")
    
    yield
    
    # Shutdown
    logger.info("AI Email Agent shutting down")

# Create FastAPI app
app = FastAPI(
    title="AI Email Agent for Salesforce",
    description="Automated email triage and response system",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "message": "AI Email Agent for Salesforce is running",
        "status": "healthy",
        "services": {
            "email_monitor": email_monitor is not None,
            "ai_classifier": ai_classifier is not None,
            "salesforce_client": salesforce_client is not None,
            "response_generator": response_generator is not None,
            "notification_service": notification_service is not None
        }
    }

@app.post("/process-emails")
async def manual_process_emails(background_tasks: BackgroundTasks):
    """Manually trigger email processing"""
    background_tasks.add_task(process_emails)
    return {"message": "Email processing started"}

@app.get("/stats")
async def get_stats():
    """Get processing statistics"""
    if email_monitor:
        return email_monitor.get_stats()
    return {"error": "Email monitor not initialized"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
