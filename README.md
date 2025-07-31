# AI Email Agent for Salesforce

An intelligent email triage and response system that automatically classifies incoming campaign replies, updates Salesforce records, and sends personalized follow-up responses.

## Features

- **AI-Powered Classification**: Automatically categorizes email replies as "Not Interested", "Maybe Interested", or "Interested"
- **Salesforce Integration**: Updates lead/contact records and creates tasks for sales team
- **Automated Responses**: Generates personalized follow-up emails using AI
- **Sales Notifications**: Alerts sales team about high-priority interested leads
- **Real-time Processing**: Monitors email continuously with configurable intervals
- **Comprehensive Logging**: Detailed logging and error handling throughout

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Email Server  │    │  AI Classifier  │    │   Salesforce    │
│   (IMAP/SMTP)   │◄──►│  (OpenAI/Claude)│◄──►│     CRM         │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────────────────────────────────────────────────────┐
│                    FastAPI Application                          │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐│
│  │Email Monitor│ │Response Gen │ │Notification │ │   Logging   ││
│  │   Service   │ │   Service   │ │   Service   │ │   Service   ││
│  └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘│
└─────────────────────────────────────────────────────────────────┘
```

## Installation

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd ai-email-agent
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment variables**:
   ```bash
   cp .env.example .env
   # Edit .env with your actual credentials
   ```

4. **Set up Salesforce custom field**:
   - Create a custom field `Campaign_Status__c` on Lead and Contact objects
   - Set as picklist with values: "Not Interested", "Maybe Interested", "Interested"

## Configuration

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `EMAIL_ADDRESS` | Email address to monitor | Yes |
| `EMAIL_PASSWORD` | Email password/app password | Yes |
| `SALESFORCE_USERNAME` | Salesforce username | Yes |
| `SALESFORCE_PASSWORD` | Salesforce password | Yes |
| `SALESFORCE_SECURITY_TOKEN` | Salesforce security token | Yes |
| `OPENAI_API_KEY` | OpenAI API key | Yes* |
| `ANTHROPIC_API_KEY` | Anthropic API key | Yes* |
| `AI_PROVIDER` | AI provider (openai/anthropic) | Yes |

*One of the AI provider keys is required based on `AI_PROVIDER` setting.

### Email Configuration

The system supports multiple email providers:

- **Gmail**: Use app passwords for authentication
- **Outlook**: Use app passwords or OAuth2
- **Custom IMAP**: Configure IMAP server and port

### Salesforce Setup

1. Create custom fields on Lead and Contact objects:
   - `Campaign_Status__c` (Picklist)
   - `Last_Campaign_Response__c` (DateTime)

2. Ensure API access is enabled for your user

3. Generate security token if needed

## Usage

### Running the Application

1. **Start the server**:
   ```bash
   python main.py
   ```

2. **Access the API**:
   - Health check: `GET http://localhost:8000/`
   - Manual processing: `POST http://localhost:8000/process-emails`
   - Statistics: `GET http://localhost:8000/stats`

### API Endpoints

- `GET /` - Health check and service status
- `POST /process-emails` - Manually trigger email processing
- `GET /stats` - Get processing statistics

### Monitoring

The application automatically processes emails every 5 minutes (configurable). Monitor logs for:

- Email processing status
- Classification results
- Salesforce updates
- Response generation
- Error handling

## Email Classification

The AI classifier categorizes emails into three categories:

### Not Interested
- Clear rejections
- Unsubscribe requests
- Negative responses
- Out-of-office replies

### Maybe Interested
- Neutral responses
- Requests for more information
- Questions about timing
- Polite deferrals

### Interested
- Positive responses
- Meeting requests
- Pricing inquiries
- Clear buying signals

## Response Templates

The system uses AI-generated responses with fallback templates:

- **Maybe Interested**: Focus on providing value and building trust
- **Interested**: Enthusiastic responses with clear next steps
- **Not Interested**: Gracious acknowledgment and removal confirmation

## Testing

Run the test suite:

```bash
pytest tests/ -v
```

Test coverage includes:
- Email classification accuracy
- Salesforce integration
- Response generation
- Error handling
- Email parsing

## Deployment

### Local Development
```bash
python main.py
```

### Production Deployment

#### Prerequisites
- Python 3.9+ installed
- Git for version control
- Access to email server (IMAP/SMTP)
- Salesforce API access
- AI provider API key (OpenAI or Anthropic)

#### Deployment Options

1. **Render Deployment (Recommended)**
   - Use the provided `render.yaml` configuration
   - Follow the detailed instructions in `RENDER_DEPLOYMENT.md`
   - Set up the keep-alive script to prevent service spin-down
   - Utilize the `/health` endpoint for monitoring
   ```bash
   # Run the keep-alive script locally (if needed)
   cd scripts
   node keep_alive.js
   ```

2. **Docker Deployment**
   ```bash
   # Build the Docker image
   docker build -t ai-email-agent .
   
   # Run the container
   docker run -d --name ai-email-agent -p 8000:8000 --env-file .env ai-email-agent
   ```

3. **Cloud Platform (AWS, Azure, GCP)**
   - Use the provided `deployment.yml` configuration
   - Set all environment variables in the cloud platform
   - Configure auto-scaling based on traffic patterns
   - Set up health checks at `/health` endpoint

4. **Serverless Deployment (AWS Lambda, Azure Functions)**
   - Package the application with dependencies
   - Configure environment variables
   - Set up API Gateway for HTTP endpoints
   - Configure scheduled triggers for email checking

#### Production Checklist

- [ ] Environment variables securely configured
- [ ] Database backups enabled (if applicable)
- [ ] Logging and monitoring set up
- [ ] Error alerting configured
- [ ] SSL/TLS certificates installed
- [ ] Rate limiting implemented
- [ ] Health checks configured
- [ ] Backup email processing strategy in place

## Monitoring & Analytics

### Analytics Dashboard

The system includes a comprehensive analytics dashboard accessible at `/dashboard/analytics` that provides real-time insights into system performance and business impact metrics.

#### Core Business Impact Metrics
- **Email Classification Distribution**: Visualizes the breakdown of emails by classification category
- **Campaign Effectiveness**: Tracks open rates, response rates, and conversion rates by campaign
- **Lead Conversion Tracking**: Monitors new leads, converted leads, and conversion rates over time

#### System Performance Metrics
- **Classification Accuracy**: Measures AI classification precision over time (target: 90%+)
- **Processing Time**: Tracks average email processing time (target: <1 minute)
- **Manual Triage Reduction**: Percentage reduction in manual email handling

#### Dashboard Features
- Real-time data visualization with Chart.js
- Responsive design for desktop and mobile access
- Key performance indicators with status indicators
- Data caching for improved performance

### Key Metrics
- Classification accuracy (target: 90%+)
- Processing time per email
- Response rates
- Error rates
- Salesforce update success

### Logging
- All email processing events
- Classification decisions with confidence scores
- Salesforce API interactions
- Response generation and sending
- Error tracking and debugging

## Troubleshooting

### Common Issues

1. **Email Connection Failures**
   - Verify email credentials
   - Check IMAP server settings
   - Ensure app passwords are used for Gmail

2. **Salesforce Integration Issues**
   - Verify API credentials
   - Check security token
   - Ensure custom fields exist

3. **AI Classification Errors**
   - Verify API keys
   - Check rate limits
   - Monitor confidence scores

4. **Response Sending Failures**
   - Verify SMTP settings
   - Check email authentication
   - Monitor deliverability

### Debug Mode

Enable debug logging by setting `LOG_LEVEL=DEBUG` in your environment.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure all tests pass
5. Submit a pull request

## License

[Add your license information here]

## Support

For support and questions:
- Check the troubleshooting section
- Review logs for error details
- Contact the development team

---

**Built with ❤️ for Annie's sales team**
