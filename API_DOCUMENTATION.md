# AI Email Agent API Documentation

This document provides comprehensive documentation for all API endpoints in the AI Email Agent for Salesforce application.

## Base URL

For local development: `http://localhost:8000`
For production: `https://your-production-domain.com`

## Authentication

Most endpoints require authentication. Use the following header:

```
Authorization: Bearer YOUR_API_TOKEN
```

## API Endpoints

### Health and Status

#### GET /health
- **Description**: Check if the service is running
- **Authentication**: None
- **Response**: 200 OK
  ```json
  {
    "status": "ok",
    "version": "1.0.0",
    "services": {
      "email_monitor": "running",
      "salesforce_client": "running",
      "ai_classifier": "running"
    }
  }
  ```

### Email Processing

#### POST /process-emails
- **Description**: Manually trigger email processing
- **Authentication**: Required
- **Response**: 200 OK
  ```json
  {
    "processed": 5,
    "interested": 2,
    "maybe_interested": 1,
    "not_interested": 2,
    "processing_time": "3.45s"
  }
  ```

#### GET /emails/search
- **Description**: Search emails with multiple filters
- **Authentication**: Required
- **Query Parameters**:
  - `query` (string): Search text
  - `sender` (string): Filter by sender email
  - `subject` (string): Filter by subject
  - `date_from` (ISO date): Filter by date range start
  - `date_to` (ISO date): Filter by date range end
  - `classification` (string): Filter by classification
  - `page` (int): Page number (default: 1)
  - `page_size` (int): Results per page (default: 20)
- **Response**: 200 OK
  ```json
  {
    "total": 150,
    "page": 1,
    "page_size": 20,
    "results": [
      {
        "id": "email123",
        "sender": "contact@example.com",
        "subject": "Re: Product Demo",
        "received_date": "2023-07-30T14:30:00Z",
        "classification": "Interested",
        "snippet": "I'd like to schedule a demo..."
      }
    ]
  }
  ```

#### GET /emails/{message_id}
- **Description**: Get detailed information about a specific email
- **Authentication**: Required
- **Path Parameters**:
  - `message_id` (string): Email message ID
- **Response**: 200 OK
  ```json
  {
    "id": "email123",
    "sender": "contact@example.com",
    "sender_name": "John Doe",
    "subject": "Re: Product Demo",
    "received_date": "2023-07-30T14:30:00Z",
    "classification": "Interested",
    "confidence": 0.92,
    "body_text": "...",
    "body_html": "...",
    "salesforce_lead_id": "00Q123456789",
    "processed_date": "2023-07-30T14:35:00Z",
    "response_sent": true,
    "response_template": "interested_follow_up"
  }
  ```

### Salesforce Integration

#### GET /salesforce/leads
- **Description**: Get leads from Salesforce
- **Authentication**: Required
- **Query Parameters**:
  - `campaign` (string): Filter by campaign
  - `status` (string): Filter by status
  - `page` (int): Page number
- **Response**: 200 OK
  ```json
  {
    "total": 250,
    "page": 1,
    "results": [
      {
        "id": "00Q123456789",
        "name": "John Doe",
        "email": "john@example.com",
        "company": "Example Inc",
        "status": "Interested",
        "campaign": "Summer Promotion",
        "last_activity": "2023-07-30T14:35:00Z"
      }
    ]
  }
  ```

### Analytics and Reporting

#### GET /stats
- **Description**: Get processing statistics
- **Authentication**: Required
- **Query Parameters**:
  - `period` (string): Time period (day, week, month, all)
- **Response**: 200 OK
  ```json
  {
    "total_emails_processed": 1250,
    "classifications": {
      "Interested": 450,
      "Maybe Interested": 350,
      "Not Interested": 450
    },
    "average_processing_time": 2.3,
    "last_processed": "2023-07-30T14:35:00Z"
  }
  ```

#### GET /analytics/email-processing
- **Description**: Get detailed email processing analytics
- **Authentication**: Required
- **Query Parameters**:
  - `start_date` (ISO date): Start date for analytics
  - `end_date` (ISO date): End date for analytics
- **Response**: 200 OK
  ```json
  {
    "daily_processing": [
      {
        "date": "2023-07-30",
        "total": 45,
        "interested": 15,
        "maybe_interested": 12,
        "not_interested": 18
      }
    ],
    "classification_accuracy": 0.92,
    "processing_time_trend": [
      {
        "date": "2023-07-30",
        "average_time": 2.3
      }
    ]
  }
  ```

#### GET /analytics/campaigns
- **Description**: Get campaign effectiveness analytics
- **Authentication**: Required
- **Response**: 200 OK
  ```json
  {
    "campaigns": [
      {
        "name": "Summer Promotion",
        "sent": 150,
        "opened": 98,
        "responded": 45,
        "conversion_rate": 12.7
      }
    ]
  }
  ```

#### GET /analytics/lead-conversion
- **Description**: Get lead conversion analytics
- **Authentication**: Required
- **Response**: 200 OK
  ```json
  {
    "conversion_rate": 24.5,
    "average_time_to_convert": 14,
    "total_converted": 45,
    "weekly_data": [
      {
        "week": "Week 1",
        "new_leads": 12,
        "converted_leads": 3,
        "conversion_rate": 25.0
      }
    ]
  }
  ```

### Dashboard

#### GET /dashboard
- **Description**: Main dashboard web interface
- **Authentication**: Required (via session cookie)
- **Response**: HTML

#### GET /dashboard/analytics
- **Description**: Analytics dashboard web interface
- **Authentication**: Required (via session cookie)
- **Response**: HTML

#### GET /dashboard/email-search
- **Description**: Email search web interface
- **Authentication**: Required (via session cookie)
- **Response**: HTML

#### GET /dashboard/contact-search
- **Description**: Contact search web interface
- **Authentication**: Required (via session cookie)
- **Response**: HTML

#### GET /dashboard/settings
- **Description**: Settings web interface
- **Authentication**: Required (via session cookie)
- **Response**: HTML

## Error Responses

All endpoints may return the following error responses:

### 400 Bad Request
```json
{
  "error": "Bad Request",
  "message": "Invalid parameters",
  "details": {
    "field": "error details"
  }
}
```

### 401 Unauthorized
```json
{
  "error": "Unauthorized",
  "message": "Authentication required"
}
```

### 403 Forbidden
```json
{
  "error": "Forbidden",
  "message": "Insufficient permissions"
}
```

### 404 Not Found
```json
{
  "error": "Not Found",
  "message": "Resource not found"
}
```

### 500 Internal Server Error
```json
{
  "error": "Internal Server Error",
  "message": "An unexpected error occurred",
  "request_id": "req-123456"
}
```

## Rate Limiting

API requests are limited to 100 requests per minute per API token. When exceeded, the API will return:

### 429 Too Many Requests
```json
{
  "error": "Too Many Requests",
  "message": "Rate limit exceeded",
  "retry_after": 30
}
```
