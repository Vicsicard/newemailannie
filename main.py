"""
AI Email Agent for Salesforce
Main application entry point
"""

import os
import logging
import asyncio
import imaplib
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from threading import Thread
from fastapi import FastAPI, BackgroundTasks, Query, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from contextlib import asynccontextmanager
import schedule
import time
from threading import Thread

from src.config import settings
from src.email_monitor import EmailMonitor
from src.mock_email_monitor import MockEmailMonitor
from src.ai_classifier import AIClassifier
from src.analytics_service import AnalyticsService
from src.salesforce_client import SalesforceClient
from src.mock_salesforce_client import MockSalesforceClient
from src.response_generator import ResponseGenerator
from src.notification_service import NotificationService
from src.email_search_service import EmailSearchService
from src.models import SearchResult, SalesforceContact, EmailSearchResult, Email

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize services
salesforce_client = None
email_monitor = None
ai_classifier = None
response_generator = None
notification_service = None
email_search_service = None
analytics_service = None

async def initialize_services():
    """Initialize all services"""
    global email_monitor, ai_classifier, salesforce_client, response_generator, notification_service, email_search_service, analytics_service
    
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
    
    # Initialize notification service
    notification_service = NotificationService(salesforce_client)
    
    # Initialize email search service
    email_search_service = EmailSearchService()
    
    # Initialize response generator
    response_generator = ResponseGenerator(ai_classifier)
    
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
    
    # Initialize analytics service
    analytics_service = AnalyticsService(email_monitor, salesforce_client)
    logger.info("Analytics service initialized")
    
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

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure templates and static files
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def root():
    """Main endpoint"""
    return {
        "message": "AI Email Agent for Salesforce is running",
        "status": "healthy"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring and deployment systems"""
    # Check if all required services are running
    services_status = {
        "email_monitor": email_monitor is not None,
        "ai_classifier": ai_classifier is not None,
        "salesforce_client": salesforce_client is not None,
        "response_generator": response_generator is not None,
        "notification_service": notification_service is not None,
        "email_search_service": email_search_service is not None,
        "analytics_service": analytics_service is not None
    }
    
    # Check if database is accessible
    db_status = "ok"
    try:
        # Simple check - in a real app, this would check the actual database connection
        pass
    except Exception as e:
        db_status = f"error: {str(e)}"
    
    # Get system metrics
    system_metrics = {
        "uptime": "unknown",  # Would be calculated from app start time
        "memory_usage": "unknown",  # Would use a library like psutil
        "cpu_usage": "unknown"
    }
    
    # Determine overall health status
    all_services_healthy = all(services_status.values())
    status_code = 200 if all_services_healthy and db_status == "ok" else 503
    
    response = {
        "status": "healthy" if status_code == 200 else "unhealthy",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0",
        "services": services_status,
        "database": db_status,
        "system": system_metrics
    }
    
    return JSONResponse(content=response, status_code=status_code)

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

@app.get("/contacts/search", response_model=SearchResult)
async def search_contacts(
    search_term: Optional[str] = Query(None, description="Text to search for across contact fields"),
    fields: Optional[str] = Query(None, description="Comma-separated list of fields to search in"),
    record_type: Optional[str] = Query(None, description="Filter by record type: 'Contact' or 'Lead'"),
    limit: int = Query(20, ge=1, le=100, description="Maximum number of records to return"),
    page: int = Query(1, ge=1, description="Page number for pagination")
):
    """Search for contacts and leads in Salesforce"""
    try:
        if not salesforce_client or not salesforce_client.is_connected():
            raise HTTPException(status_code=503, detail="Salesforce client not available")
            
        # Convert page to offset
        offset = (page - 1) * limit
        
        # Parse search fields if provided
        search_fields = fields.split(',') if fields else None
        
        # Perform search
        result = await salesforce_client.search_contacts(
            search_term=search_term,
            search_fields=search_fields,
            record_type=record_type,
            limit=limit,
            offset=offset
        )
        
        return result
    except Exception as e:
        logger.error(f"Error searching contacts: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/contacts/{contact_id}")
async def get_contact_details(contact_id: str):
    """Get detailed information about a contact or lead"""
    try:
        if not salesforce_client or not salesforce_client.is_connected():
            raise HTTPException(status_code=503, detail="Salesforce client not available")
            
        result = await salesforce_client.get_contact_details(contact_id)
        
        if 'error' in result:
            raise HTTPException(status_code=404, detail=result['error'])
            
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting contact details: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/emails/search", response_model=EmailSearchResult)
async def search_emails(
    search_term: Optional[str] = Query(None, description="Text to search for in subject or body"),
    sender: Optional[str] = Query(None, description="Filter by sender email address"),
    subject: Optional[str] = Query(None, description="Filter by subject text"),
    date_from: Optional[str] = Query(None, description="Filter emails after this date (YYYY-MM-DD)"),
    date_to: Optional[str] = Query(None, description="Filter emails before this date (YYYY-MM-DD)"),
    limit: int = Query(20, ge=1, le=100, description="Maximum number of emails to return"),
    page: int = Query(1, ge=1, description="Page number for pagination")
):
    """Search for emails in the monitored inbox"""
    try:
        if not email_search_service:
            raise HTTPException(status_code=503, detail="Email search service not available")
        
        # Parse dates if provided
        from_date = None
        to_date = None
        
        if date_from:
            try:
                from_date = datetime.strptime(date_from, "%Y-%m-%d")
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid date_from format. Use YYYY-MM-DD")
        
        if date_to:
            try:
                to_date = datetime.strptime(date_to, "%Y-%m-%d")
                # Set to end of day
                to_date = to_date.replace(hour=23, minute=59, second=59)
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid date_to format. Use YYYY-MM-DD")
        
        # Convert page to offset
        offset = (page - 1) * limit
        
        # Perform search
        result = await email_search_service.search_emails(
            search_term=search_term,
            sender=sender,
            subject=subject,
            date_from=from_date,
            date_to=to_date,
            limit=limit,
            offset=offset
        )
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error searching emails: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/emails/{message_id}")
async def get_email_details(message_id: str):
    """Get detailed information about an email"""
    try:
        if not email_search_service:
            raise HTTPException(status_code=503, detail="Email search service not available")
            
        email = await email_search_service.get_email_by_id(message_id)
        
        if not email:
            raise HTTPException(status_code=404, detail=f"Email with ID {message_id} not found")
            
        return email
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting email details: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/emails/{message_id}/thread")
async def get_email_thread(message_id: str):
    """Get all emails in the same thread"""
    try:
        if not email_search_service:
            raise HTTPException(status_code=503, detail="Email search service not available")
            
        emails = await email_search_service.get_email_thread(message_id)
        
        if not emails:
            raise HTTPException(status_code=404, detail=f"Email thread for ID {message_id} not found")
            
        return {"emails": emails, "count": len(emails)}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting email thread: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Dashboard routes
@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Dashboard home page"""
    try:
        # Get processing statistics
        stats = email_monitor.get_stats() if email_monitor else {
            "total_emails_processed": 0,
            "classifications": {"Interested": 0, "Maybe Interested": 0, "Not Interested": 0},
            "responses_sent": 0,
            "notifications_sent": 0,
            "errors": 0,
            "average_processing_time": 0,
            "last_processed": None
        }
        
        # Get recent emails (if available)
        recent_emails = []
        if email_search_service:
            try:
                search_result = await email_search_service.search_emails(limit=5)
                recent_emails = search_result.emails
            except Exception as e:
                logger.error(f"Error fetching recent emails: {e}")
        
        # Format today's date for quick search
        today = datetime.now().strftime("%Y-%m-%d")
        
        return templates.TemplateResponse(
            "dashboard.html",
            {
                "request": request,
                "active_page": "dashboard",
                "stats": stats,
                "recent_emails": recent_emails,
                "today": today
            }
        )
    except Exception as e:
        logger.error(f"Error rendering dashboard: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/dashboard/email-search", response_class=HTMLResponse)
async def email_search_page(request: Request, 
                           search_term: Optional[str] = None,
                           sender: Optional[str] = None,
                           subject: Optional[str] = None,
                           date_from: Optional[str] = None,
                           date_to: Optional[str] = None,
                           page: int = 1,
                           limit: int = 20):
    """Email search page"""
    try:
        emails = []
        total_count = 0
        has_more = False
        page_size = limit
        search_performed = any([search_term, sender, subject, date_from, date_to])
        
        if search_performed and email_search_service:
            # Parse dates if provided
            from_date = None
            to_date = None
            
            if date_from:
                try:
                    from_date = datetime.strptime(date_from, "%Y-%m-%d")
                except ValueError:
                    pass
            
            if date_to:
                try:
                    to_date = datetime.strptime(date_to, "%Y-%m-%d")
                    # Set to end of day
                    to_date = to_date.replace(hour=23, minute=59, second=59)
                except ValueError:
                    pass
            
            # Calculate offset from page
            offset = (page - 1) * limit
            
            # Perform search
            result = await email_search_service.search_emails(
                search_term=search_term,
                sender=sender,
                subject=subject,
                date_from=from_date,
                date_to=to_date,
                limit=limit,
                offset=offset
            )
            
            emails = result.emails
            total_count = result.total_count
            has_more = result.has_more
            page_size = result.page_size
        
        # Build pagination URL
        pagination_params = []
        if search_term:
            pagination_params.append(f"search_term={search_term}")
        if sender:
            pagination_params.append(f"sender={sender}")
        if subject:
            pagination_params.append(f"subject={subject}")
        if date_from:
            pagination_params.append(f"date_from={date_from}")
        if date_to:
            pagination_params.append(f"date_to={date_to}")
        if limit != 20:
            pagination_params.append(f"limit={limit}")
            
        pagination_url = "/dashboard/email-search?" + "&".join(pagination_params)
        
        return templates.TemplateResponse(
            "email_search.html",
            {
                "request": request,
                "active_page": "email_search",
                "emails": emails,
                "total_count": total_count,
                "has_more": has_more,
                "page": page,
                "page_size": page_size,
                "search_performed": search_performed,
                "pagination_url": pagination_url
            }
        )
    except Exception as e:
        logger.error(f"Error rendering email search page: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/dashboard/contact-search", response_class=HTMLResponse)
async def contact_search_page(request: Request,
                             search_term: Optional[str] = None,
                             fields: Optional[str] = None,
                             record_type: Optional[str] = None,
                             page: int = 1,
                             limit: int = 20):
    """Contact search page"""
    try:
        contacts = []
        total_count = 0
        has_more = False
        page_size = limit
        search_performed = any([search_term, fields, record_type])
        
        if search_performed and salesforce_client and salesforce_client.is_connected():
            # Parse search fields if provided
            search_fields = fields.split(',') if fields else None
            
            # Calculate offset from page
            offset = (page - 1) * limit
            
            # Perform search
            result = await salesforce_client.search_contacts(
                search_term=search_term,
                search_fields=search_fields,
                record_type=record_type,
                limit=limit,
                offset=offset
            )
            
            contacts = result.results
            total_count = result.total_count
            has_more = result.has_more
            page_size = result.page_size
        
        # Build pagination URL
        pagination_params = []
        if search_term:
            pagination_params.append(f"search_term={search_term}")
        if fields:
            pagination_params.append(f"fields={fields}")
        if record_type:
            pagination_params.append(f"record_type={record_type}")
        if limit != 20:
            pagination_params.append(f"limit={limit}")
            
        pagination_url = "/dashboard/contact-search?" + "&".join(pagination_params)
        
        return templates.TemplateResponse(
            "contact_search.html",
            {
                "request": request,
                "active_page": "contact_search",
                "contacts": contacts,
                "total_count": total_count,
                "has_more": has_more,
                "page": page,
                "page_size": page_size,
                "search_performed": search_performed,
                "pagination_url": pagination_url
            }
        )
    except Exception as e:
        logger.error(f"Error rendering contact search page: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/dashboard/emails/{message_id}", response_class=HTMLResponse)
async def email_detail_page(request: Request, message_id: str):
    """Email detail page"""
    try:
        if not email_search_service:
            raise HTTPException(status_code=503, detail="Email search service not available")
            
        email = await email_search_service.get_email_by_id(message_id)
        
        if not email:
            raise HTTPException(status_code=404, detail=f"Email with ID {message_id} not found")
        
        # Get contact information if available
        contact = None
        if salesforce_client and salesforce_client.is_connected():
            try:
                contact = await salesforce_client.find_contact_by_email(email.sender)
            except Exception as e:
                logger.error(f"Error fetching contact for email: {e}")
        
        return templates.TemplateResponse(
            "email_detail.html",
            {
                "request": request,
                "active_page": "email_search",
                "email": email,
                "contact": contact
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error rendering email detail page: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/dashboard/contacts/{contact_id}", response_class=HTMLResponse)
async def contact_detail_page(request: Request, contact_id: str):
    """Contact detail page"""
    try:
        if not salesforce_client or not salesforce_client.is_connected():
            raise HTTPException(status_code=503, detail="Salesforce client not available")
            
        contact_details = await salesforce_client.get_contact_details(contact_id)
        
        if 'error' in contact_details:
            raise HTTPException(status_code=404, detail=contact_details['error'])
        
        return templates.TemplateResponse(
            "contact_detail.html",
            {
                "request": request,
                "active_page": "contact_search",
                "contact": contact_details
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error rendering contact detail page: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Dashboard Analytics Route
@app.get("/dashboard/analytics", response_class=HTMLResponse)
async def analytics_page(request: Request):
    """Analytics dashboard page"""
    try:
        if analytics_service:
            # Get all analytics data from the analytics service
            analytics_data = await analytics_service.get_all_analytics_data()
            
            # Extract individual components
            stats = analytics_data.get("stats", {})
            campaign_stats = analytics_data.get("campaign_stats", [])
            lead_stats = analytics_data.get("lead_stats", {})
            performance_metrics = analytics_data.get("performance_metrics", {})
        else:
            # Fallback if analytics service is not available
            logger.warning("Analytics service not available, using default values")
            
            # Get processing statistics from email monitor directly
            stats = email_monitor.get_stats() if email_monitor else {
                "total_emails_processed": 0,
                "classifications": {"Interested": 0, "Maybe Interested": 0, "Not Interested": 0},
                "responses_sent": 0,
                "notifications_sent": 0,
                "errors": 0,
                "average_processing_time": 0,
                "last_processed": None
            }
            
            # Use placeholder data for other metrics
            campaign_stats = [
                {
                    "name": "Summer Promotion",
                    "sent": 150,
                    "opened": 98,
                    "responded": 45,
                    "open_rate": 65.3,
                    "response_rate": 30.0,
                    "conversion_rate": 12.7
                },
                {
                    "name": "Product Launch",
                    "sent": 200,
                    "opened": 175,
                    "responded": 89,
                    "open_rate": 87.5,
                    "response_rate": 44.5,
                    "conversion_rate": 18.5
                }
            ]
            
            lead_stats = {
                "conversion_rate": 24.5,
                "avg_time_to_convert": "14 days",
                "total_converted": 45,
                "weekly_new_leads": [12, 18, 15, 20],
                "weekly_converted": [3, 5, 4, 7],
                "weekly_conversion_rates": [25.0, 27.8, 26.7, 35.0]
            }
            
            performance_metrics = {
                "classification_accuracy": 91.5,
                "avg_response_time": "28 minutes",
                "avg_response_time_seconds": 1680,
                "manual_triage_reduction": 75,
                "weekly_response_times": [42, 35, 30, 28],
                "weekly_accuracy": [87, 89, 90, 91.5]
            }
        
        return templates.TemplateResponse(
            "analytics.html",
            {
                "request": request,
                "active_page": "analytics",
                "stats": stats,
                "campaign_stats": campaign_stats,
                "lead_stats": lead_stats,
                "performance_metrics": performance_metrics
            }
        )
    except Exception as e:
        logger.error(f"Error rendering analytics page: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# API Documentation configuration
app.title = "AI Email Agent for Salesforce"
app.description = """
### AI Email Agent for Salesforce API

This API provides endpoints for:
- Email processing and classification
- Salesforce contact management
- Email search and retrieval
- Analytics and reporting

#### Contact Search
Use the `/contacts/search` endpoint to search for contacts and leads in Salesforce.

#### Email Search
Use the `/emails/search` endpoint to search through your monitored emails.
This helps overcome limitations in Outlook's search functionality.

#### Dashboard
A user-friendly dashboard is available at `/dashboard` for Annie to easily search and view emails and contacts.
"""
app.version = "1.2.0"

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
