"""
Deployment script for AI Email Agent
"""

import os
import subprocess
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def check_environment():
    """Check if all required environment variables are set"""
    required_vars = [
        'EMAIL_ADDRESS',
        'EMAIL_PASSWORD', 
        'SALESFORCE_USERNAME',
        'SALESFORCE_PASSWORD',
        'SALESFORCE_SECURITY_TOKEN',
        'OPENAI_API_KEY',  # or ANTHROPIC_API_KEY
        'SMTP_USERNAME',
        'SMTP_PASSWORD'
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        logger.error(f"Missing environment variables: {missing_vars}")
        logger.info("Please set these variables in your .env file or environment")
        return False
    
    logger.info("✅ All required environment variables are set")
    return True

def build_docker_image():
    """Build Docker image"""
    try:
        logger.info("Building Docker image...")
        result = subprocess.run([
            'docker', 'build', '-t', 'ai-email-agent', '.'
        ], check=True, capture_output=True, text=True)
        
        logger.info("✅ Docker image built successfully")
        return True
        
    except subprocess.CalledProcessError as e:
        logger.error(f"Docker build failed: {e.stderr}")
        return False

def deploy_with_docker_compose():
    """Deploy using docker-compose"""
    try:
        logger.info("Deploying with docker-compose...")
        
        # Stop existing containers
        subprocess.run(['docker-compose', 'down'], capture_output=True)
        
        # Start new containers
        result = subprocess.run([
            'docker-compose', 'up', '-d'
        ], check=True, capture_output=True, text=True)
        
        logger.info("✅ Application deployed successfully")
        logger.info("Application is running at http://localhost:8000")
        return True
        
    except subprocess.CalledProcessError as e:
        logger.error(f"Docker compose deployment failed: {e.stderr}")
        return False

def deploy_to_render():
    """Instructions for deploying to Render"""
    logger.info("""
📋 To deploy to Render:

1. Create a new Web Service on Render
2. Connect your GitHub repository
3. Set the following configuration:
   - Runtime: Python 3
   - Build Command: pip install -r requirements.txt
   - Start Command: python main.py
   - Port: 8000

4. Add environment variables in Render dashboard:
   - EMAIL_ADDRESS
   - EMAIL_PASSWORD
   - SALESFORCE_USERNAME
   - SALESFORCE_PASSWORD
   - SALESFORCE_SECURITY_TOKEN
   - OPENAI_API_KEY (or ANTHROPIC_API_KEY)
   - SMTP_USERNAME
   - SMTP_PASSWORD
   - AI_PROVIDER
   - LOG_LEVEL=INFO
   - ENVIRONMENT=production

5. Deploy and monitor logs for any issues
""")

def deploy_to_aws_lambda():
    """Instructions for deploying to AWS Lambda"""
    logger.info("""
📋 To deploy to AWS Lambda:

1. Install AWS CLI and configure credentials
2. Install serverless framework: npm install -g serverless
3. Create serverless.yml configuration file
4. Package the application: serverless package
5. Deploy: serverless deploy

Note: Lambda has limitations for long-running processes.
Consider using AWS ECS or EC2 for this application instead.
""")

def main():
    """Main deployment function"""
    logger.info("🚀 Starting AI Email Agent deployment...")
    
    # Check environment
    if not check_environment():
        return False
    
    # Check if Docker is available
    try:
        subprocess.run(['docker', '--version'], check=True, capture_output=True)
        docker_available = True
    except (subprocess.CalledProcessError, FileNotFoundError):
        docker_available = False
        logger.warning("Docker not available")
    
    if docker_available:
        # Local Docker deployment
        logger.info("Deploying locally with Docker...")
        if build_docker_image() and deploy_with_docker_compose():
            logger.info("🎉 Local deployment successful!")
            logger.info("Access the application at: http://localhost:8000")
            logger.info("Check health: curl http://localhost:8000/")
            logger.info("View logs: docker-compose logs -f")
            return True
    else:
        # Manual deployment instructions
        logger.info("Docker not available. Manual deployment required.")
        logger.info("Run: python main.py")
    
    # Show cloud deployment options
    logger.info("\n☁️  Cloud Deployment Options:")
    deploy_to_render()
    deploy_to_aws_lambda()
    
    return True

if __name__ == "__main__":
    success = main()
    if not success:
        exit(1)
