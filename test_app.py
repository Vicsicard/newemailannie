"""
AI Email Agent for Salesforce - Test Application
Simplified version using mock services
"""

import os
import logging
import asyncio
from datetime import datetime
from fastapi import FastAPI, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from src.config import settings
from src.ai_classifier import AIClassifier
from src.mock_salesforce_client import MockSalesforceClient
from src.mock_email_monitor import MockEmailMonitor
from src.response_generator import ResponseGenerator
from src.notification_service import NotificationService
from src.models import ProcessingStats

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global service instances
email_monitor = None
ai_classifier = None
salesforce_client = None
response_generator = None
notification_service = None

async def initialize_services():
    """Initialize all services with mock implementations"""
    global email_monitor, ai_classifier, salesforce_client, response_generator, notification_service
    
    logger.info("Initializing services...")
    
    # Initialize AI classifier
    ai_classifier = AIClassifier()
    logger.info("AI classifier initialized")
    
    # Initialize mock Salesforce client
    salesforce_client = MockSalesforceClient()
    await salesforce_client.connect()
    logger.info("Mock Salesforce client initialized")
    
    # Initialize response generator
    response_generator = ResponseGenerator(ai_classifier)
    logger.info("Response generator initialized")
    
    # Initialize notification service
    notification_service = NotificationService(salesforce_client)
    logger.info("Notification service initialized")
    
    # Initialize mock email monitor
    email_monitor = MockEmailMonitor(
        ai_classifier,
        salesforce_client,
        response_generator,
        notification_service
    )
    logger.info("Mock email monitor initialized")
    
    logger.info("All services initialized successfully")
    logger.info("AI Email Agent (Test Mode) started successfully")

async def process_emails():
    """Process emails - called by scheduler"""
    if email_monitor:
        logger.info("Manual email processing triggered")
        await email_monitor.process_new_emails()
    else:
        logger.error("Email monitor not initialized")

# Create FastAPI app
app = FastAPI(
    title="AI Email Agent for Salesforce (Test Mode)",
    description="Automated email triage and response system - Using Mock Services",
    version="1.0.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    await initialize_services()

@app.on_event("shutdown")
async def shutdown_event():
    """Clean up on shutdown"""
    logger.info("AI Email Agent shutting down")

@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "message": "AI Email Agent for Salesforce (Test Mode) is running",
        "status": "healthy",
        "services": {
            "email_monitor": "mock",
            "ai_classifier": ai_classifier is not None,
            "salesforce_client": "mock",
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
        return email_monitor.stats.to_dict()
    return ProcessingStats().to_dict()

@app.post("/add-test-email")
async def add_test_email(subject: str, sender: str, body: str):
    """Add a test email for processing"""
    if not isinstance(email_monitor, MockEmailMonitor):
        return {"error": "This endpoint is only available in test mode with mock email monitor"}
    
    message_id = email_monitor.add_test_email(subject, sender, body)
    return {
        "message": "Test email added successfully",
        "message_id": message_id
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)
