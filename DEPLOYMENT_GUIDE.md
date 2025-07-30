# Deployment Guide - AI Email Agent for Salesforce

This guide provides step-by-step instructions for deploying the AI Email Agent in different environments.

## Prerequisites

1. **Environment Variables**: Copy `.env.example` to `.env` and fill in all required values
2. **Salesforce Setup**: Create the `Campaign_Status__c` custom field on Lead and Contact objects
3. **Email Configuration**: Set up app passwords for Gmail/Outlook
4. **AI API Keys**: Obtain OpenAI or Anthropic API keys

## Quick Start (Local Development)

1. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure Environment**:
   ```bash
   cp .env.example .env
   # Edit .env with your credentials
   ```

3. **Test Configuration**:
   ```bash
   python scripts/setup_salesforce.py
   ```

4. **Run Application**:
   ```bash
   python main.py
   ```

5. **Test Integration**:
   ```bash
   python scripts/test_email_integration.py
   ```

## Production Deployment Options

### Option 1: Docker (Recommended)

1. **Build and Deploy**:
   ```bash
   python scripts/deploy.py
   ```

2. **Or manually**:
   ```bash
   docker-compose up -d
   ```

3. **Monitor**:
   ```bash
   docker-compose logs -f
   ```

### Option 2: Render (Cloud Platform)

1. **Create Render Account**: Sign up at render.com
2. **Connect Repository**: Link your GitHub repository
3. **Create Web Service**:
   - Runtime: Python 3
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `python main.py`
   - Port: 8000

4. **Set Environment Variables** in Render dashboard:
   ```
   EMAIL_ADDRESS=your-email@domain.com
   EMAIL_PASSWORD=your-app-password
   SALESFORCE_USERNAME=your-sf-username
   SALESFORCE_PASSWORD=your-sf-password
   SALESFORCE_SECURITY_TOKEN=your-sf-token
   OPENAI_API_KEY=your-openai-key
   SMTP_USERNAME=your-smtp-username
   SMTP_PASSWORD=your-smtp-password
   AI_PROVIDER=openai
   LOG_LEVEL=INFO
   ENVIRONMENT=production
   ```

5. **Deploy**: Click "Deploy" in Render dashboard

### Option 3: AWS EC2

1. **Launch EC2 Instance**: Ubuntu 20.04 LTS recommended
2. **Install Dependencies**:
   ```bash
   sudo apt update
   sudo apt install python3 python3-pip git
   ```

3. **Clone Repository**:
   ```bash
   git clone <your-repo-url>
   cd ai-email-agent
   ```

4. **Install Python Dependencies**:
   ```bash
   pip3 install -r requirements.txt
   ```

5. **Configure Environment**:
   ```bash
   cp .env.example .env
   nano .env  # Edit with your credentials
   ```

6. **Create Systemd Service**:
   ```bash
   sudo nano /etc/systemd/system/ai-email-agent.service
   ```
   
   Content:
   ```ini
   [Unit]
   Description=AI Email Agent for Salesforce
   After=network.target

   [Service]
   Type=simple
   User=ubuntu
   WorkingDirectory=/home/ubuntu/ai-email-agent
   ExecStart=/usr/bin/python3 main.py
   Restart=always
   RestartSec=10

   [Install]
   WantedBy=multi-user.target
   ```

7. **Start Service**:
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable ai-email-agent
   sudo systemctl start ai-email-agent
   ```

## Configuration Checklist

### Email Setup
- [ ] Email provider configured (Gmail/Outlook/IMAP)
- [ ] App passwords generated (not regular passwords)
- [ ] IMAP access enabled
- [ ] SMTP settings configured for sending responses

### Salesforce Setup
- [ ] API access enabled for user
- [ ] Security token generated
- [ ] Custom field `Campaign_Status__c` created on Lead object
- [ ] Custom field `Campaign_Status__c` created on Contact object
- [ ] Picklist values set: "Not Interested", "Maybe Interested", "Interested"

### AI Configuration
- [ ] OpenAI or Anthropic API key obtained
- [ ] API key has sufficient credits/quota
- [ ] AI provider correctly set in environment

### Notification Setup
- [ ] SMTP credentials for sending notifications
- [ ] Sales team email addresses configured
- [ ] Notification templates customized

## Testing Your Deployment

1. **Health Check**:
   ```bash
   curl http://your-domain:8000/
   ```

2. **Manual Email Processing**:
   ```bash
   curl -X POST http://your-domain:8000/process-emails
   ```

3. **View Statistics**:
   ```bash
   curl http://your-domain:8000/stats
   ```

4. **Run Integration Tests**:
   ```bash
   python scripts/test_email_integration.py
   ```

## Monitoring and Maintenance

### Log Monitoring
- Check application logs regularly
- Monitor classification accuracy
- Track response rates and errors

### Performance Metrics
- Email processing time
- API response times (Salesforce, AI)
- Memory and CPU usage
- Error rates

### Regular Maintenance
- Update AI prompts based on performance
- Review and update response templates
- Monitor API usage and costs
- Update dependencies regularly

## Troubleshooting

### Common Issues

1. **Email Connection Failures**
   - Verify IMAP settings and credentials
   - Check if 2FA is enabled (use app passwords)
   - Ensure firewall allows IMAP connections

2. **Salesforce API Errors**
   - Verify username, password, and security token
   - Check API limits and usage
   - Ensure custom fields exist

3. **AI Classification Issues**
   - Verify API keys and quotas
   - Check prompt formatting
   - Monitor confidence scores

4. **Response Sending Failures**
   - Verify SMTP settings
   - Check email authentication (SPF/DKIM)
   - Monitor deliverability rates

### Debug Mode
Set `LOG_LEVEL=DEBUG` to enable detailed logging for troubleshooting.

## Security Considerations

1. **Environment Variables**: Never commit `.env` files to version control
2. **API Keys**: Rotate API keys regularly
3. **Email Passwords**: Use app-specific passwords, not account passwords
4. **Network Security**: Use HTTPS in production
5. **Access Control**: Limit API access to necessary IP ranges

## Scaling Considerations

### High Volume Processing
- Implement email batching
- Add Redis for caching
- Use database for persistent storage
- Consider multiple worker processes

### Multi-tenant Support
- Add tenant isolation
- Implement per-tenant configuration
- Scale Salesforce API usage
- Monitor per-tenant metrics

## Support and Maintenance

For ongoing support:
1. Monitor application logs
2. Set up alerting for errors
3. Regular performance reviews
4. Update AI models and prompts as needed
5. Backup configuration and data

---

**Deployment completed successfully! 🎉**

Your AI Email Agent is now ready to automatically process campaign replies, update Salesforce, and notify your sales team of interested leads.
