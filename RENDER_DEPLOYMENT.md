# Deploying AI Email Agent to Render

This guide provides step-by-step instructions for deploying the AI Email Agent for Salesforce to Render.

## Prerequisites

1. A Render account (https://render.com)
2. Your code pushed to a Git repository (GitHub, GitLab, or Bitbucket)

## Deployment Steps

### 1. Create a New Web Service on Render

1. Log in to your Render dashboard
2. Click "New" and select "Web Service"
3. Connect your Git repository
4. Select the repository containing your AI Email Agent code

### 2. Configure the Web Service

Use these settings for your Render web service:

- **Name**: `ai-email-agent` (or your preferred name)
- **Environment**: `Python`
- **Region**: Choose the region closest to you and your users
- **Branch**: `main` (or your default branch)
- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`
- **Plan**: Select "Standard" (or higher for production use)

### 3. Set Environment Variables

Add the following environment variables in the Render dashboard:

```
EMAIL_PROVIDER=outlook
EMAIL_ADDRESS=your-email@domain.com
EMAIL_PASSWORD=your-app-password
IMAP_SERVER=outlook.office365.com
IMAP_PORT=993
SALESFORCE_USERNAME=your-salesforce-username
SALESFORCE_PASSWORD=your-salesforce-password
SALESFORCE_SECURITY_TOKEN=your-security-token
SALESFORCE_DOMAIN=login
OPENAI_API_KEY=your-openai-api-key
AI_PROVIDER=openai
ENVIRONMENT=production
LOG_LEVEL=INFO
```

### 4. Deploy the Service

1. Click "Create Web Service"
2. Wait for the build and deployment to complete
3. Once deployed, Render will provide a URL for your application

### 5. Set Up the Keep-Alive Service

To prevent your service from spinning down on Render's free tier (or to ensure consistent performance on paid tiers):

#### Option 1: Use a Secondary Render Service

1. Create a new "Background Worker" service on Render
2. Point it to the same repository
3. Set the build command to `cd scripts && npm install`
4. Set the start command to `cd scripts && node keep_alive.js`
5. Add an environment variable `APP_URL` with the URL of your main web service

#### Option 2: Use an External Service

1. Use a service like UptimeRobot (https://uptimerobot.com) to ping your application
2. Set up a monitor to ping your `/health` endpoint every 5 minutes
3. This will keep your application active

#### Option 3: Run Locally

If you have a computer that's always on:
1. Clone your repository
2. Navigate to the `scripts` directory
3. Run `npm install` (if not already done)
4. Set the `APP_URL` environment variable to your Render app URL
5. Run `node keep_alive.js`

### 6. Verify Deployment

1. Visit your application URL
2. Navigate to `/health` to check the health status
3. Navigate to `/dashboard/analytics` to verify the analytics dashboard is working

## Monitoring and Maintenance

- Check the Render logs for any issues
- Use the `/health` endpoint to monitor application health
- Set up alerts in Render for any service disruptions

## Updating Your Application

1. Push changes to your Git repository
2. Render will automatically rebuild and deploy your application (if auto-deploy is enabled)
3. Monitor the deployment logs for any issues

## Troubleshooting

If you encounter issues with your deployment:

1. Check the Render logs for error messages
2. Verify all environment variables are set correctly
3. Ensure your application works locally before deploying
4. Check that your keep-alive service is running properly

For more help, refer to Render's documentation at https://render.com/docs
