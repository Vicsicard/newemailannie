#!/usr/bin/env python
"""
Render Setup Script for AI Email Agent
This script helps prepare your application for deployment to Render.
"""

import os
import json
import shutil
import argparse
from pathlib import Path

def create_directories():
    """Create necessary directories for Render deployment"""
    os.makedirs("logs", exist_ok=True)
    os.makedirs("data", exist_ok=True)
    print("✓ Created necessary directories")

def check_requirements():
    """Check if requirements.txt has all necessary packages for Render"""
    required_packages = {
        "fastapi": "For the web framework",
        "uvicorn": "For the ASGI server",
        "gunicorn": "For production WSGI HTTP Server",
        "python-dotenv": "For environment variable management",
        "requests": "For HTTP requests",
        "jinja2": "For HTML templates",
        "aiofiles": "For async file operations",
        "python-multipart": "For form data parsing"
    }
    
    missing_packages = []
    
    with open("requirements.txt", "r") as f:
        installed_packages = [line.strip().split("==")[0].lower() for line in f if line.strip() and not line.startswith("#")]
    
    for package, purpose in required_packages.items():
        if package.lower() not in installed_packages:
            missing_packages.append((package, purpose))
    
    if missing_packages:
        print("⚠️ Missing required packages for Render deployment:")
        for package, purpose in missing_packages:
            print(f"  - {package}: {purpose}")
        
        add_packages = input("Would you like to add these packages to requirements.txt? (y/n): ")
        if add_packages.lower() == "y":
            with open("requirements.txt", "a") as f:
                f.write("\n# Packages required for Render deployment\n")
                for package, _ in missing_packages:
                    f.write(f"{package}\n")
            print("✓ Added missing packages to requirements.txt")
    else:
        print("✓ All required packages are in requirements.txt")

def setup_render_config():
    """Check if render.yaml exists and is properly configured"""
    if not os.path.exists("render.yaml"):
        print("⚠️ render.yaml not found. Creating a default configuration...")
        with open("render.yaml", "w") as f:
            f.write("""services:
  - type: web
    name: ai-email-agent
    env: python
    buildCommand: pip install -r requirements.txt
    startCommand: uvicorn main:app --host 0.0.0.0 --port $PORT
    plan: standard
    autoDeploy: false
    envVars:
      - key: PYTHON_VERSION
        value: 3.9.0
      - key: ENVIRONMENT
        value: production
      - key: LOG_LEVEL
        value: INFO
    healthCheckPath: /health
    healthCheckTimeout: 5
""")
        print("✓ Created render.yaml with default configuration")
    else:
        print("✓ render.yaml already exists")

def check_procfile():
    """Check if Procfile exists and is properly configured"""
    if not os.path.exists("Procfile"):
        print("⚠️ Procfile not found. Creating a default Procfile...")
        with open("Procfile", "w") as f:
            f.write("web: uvicorn main:app --host 0.0.0.0 --port $PORT")
        print("✓ Created Procfile with default configuration")
    else:
        print("✓ Procfile already exists")

def setup_keep_alive():
    """Set up the keep-alive script for Render"""
    scripts_dir = Path("scripts")
    keep_alive_js = scripts_dir / "keep_alive.js"
    package_json = scripts_dir / "package.json"
    
    if not keep_alive_js.exists():
        print("⚠️ keep_alive.js not found. Creating the script...")
        with open(keep_alive_js, "w") as f:
            f.write("""/**
 * Keep-Alive Script for AI Email Agent on Render
 * 
 * This script pings the application every 30 seconds to prevent it from spinning down.
 * It can be run on a separate always-on service or using a free service like UptimeRobot.
 */

const https = require('https');
const http = require('http');

// Configuration
const APP_URL = process.env.APP_URL || 'https://ai-email-agent.onrender.com'; // Replace with your actual Render URL
const PING_INTERVAL = 30000; // 30 seconds
const PING_ENDPOINT = '/health'; // Use the health endpoint for pinging
const USE_HTTPS = APP_URL.startsWith('https');

console.log(`Keep-Alive service started for ${APP_URL}`);
console.log(`Pinging ${PING_ENDPOINT} every ${PING_INTERVAL / 1000} seconds`);

// Function to ping the application
function pingApplication() {
  const requestOptions = {
    hostname: APP_URL.replace(/^https?:\/\//, ''),
    port: USE_HTTPS ? 443 : 80,
    path: PING_ENDPOINT,
    method: 'GET',
    timeout: 10000, // 10 second timeout
    headers: {
      'User-Agent': 'AI-Email-Agent-KeepAlive/1.0'
    }
  };

  const requestLib = USE_HTTPS ? https : http;
  
  const req = requestLib.request(requestOptions, (res) => {
    const currentTime = new Date().toISOString();
    
    if (res.statusCode === 200) {
      console.log(`[${currentTime}] Ping successful - Status: ${res.statusCode}`);
    } else {
      console.warn(`[${currentTime}] Ping returned non-200 status: ${res.statusCode}`);
    }
    
    // Consume response data to free up memory
    res.resume();
  });

  req.on('error', (e) => {
    console.error(`[${new Date().toISOString()}] Ping failed: ${e.message}`);
  });

  req.on('timeout', () => {
    console.error(`[${new Date().toISOString()}] Ping timed out`);
    req.abort();
  });

  req.end();
}

// Initial ping
pingApplication();

// Set up interval for regular pinging
setInterval(pingApplication, PING_INTERVAL);""")
        print("✓ Created keep_alive.js script")
    else:
        print("✓ keep_alive.js already exists")
    
    if not package_json.exists():
        print("⚠️ package.json not found in scripts directory. Creating the file...")
        with open(package_json, "w") as f:
            f.write("""{
  "name": "ai-email-agent-keep-alive",
  "version": "1.0.0",
  "description": "Keep-alive service for AI Email Agent on Render",
  "main": "keep_alive.js",
  "scripts": {
    "start": "node keep_alive.js"
  },
  "engines": {
    "node": ">=14.0.0"
  },
  "author": "Annie",
  "license": "MIT",
  "dependencies": {}
}""")
        print("✓ Created package.json in scripts directory")
    else:
        print("✓ package.json already exists in scripts directory")

def create_env_sample():
    """Create a sample .env file for Render if it doesn't exist"""
    if not os.path.exists(".env.example"):
        print("⚠️ .env.example not found. Creating a sample file...")
        with open(".env.example", "w") as f:
            f.write("""# Email Configuration
EMAIL_PROVIDER=outlook
EMAIL_ADDRESS=your-email@domain.com
EMAIL_PASSWORD=your-app-password
IMAP_SERVER=outlook.office365.com
IMAP_PORT=993

# Salesforce Configuration
SALESFORCE_USERNAME=your-salesforce-username
SALESFORCE_PASSWORD=your-salesforce-password
SALESFORCE_SECURITY_TOKEN=your-security-token
SALESFORCE_DOMAIN=login

# AI Configuration
OPENAI_API_KEY=your-openai-api-key
AI_PROVIDER=openai

# Application Configuration
ENVIRONMENT=production
LOG_LEVEL=INFO
""")
        print("✓ Created .env.example with sample configuration")
    else:
        print("✓ .env.example already exists")

def check_health_endpoint():
    """Check if the health endpoint exists in main.py"""
    try:
        with open("main.py", "r") as f:
            content = f.read()
            if "/health" in content:
                print("✓ Health endpoint exists in main.py")
            else:
                print("⚠️ Health endpoint not found in main.py")
                print("  Please add a health endpoint for Render's health checks")
                print("  Example: @app.get('/health') async def health_check(): return {'status': 'healthy'}")
    except FileNotFoundError:
        print("⚠️ main.py not found. Please make sure your main application file exists.")

def main():
    parser = argparse.ArgumentParser(description='Setup script for deploying to Render')
    parser.add_argument('--check-only', action='store_true', help='Only check configuration without making changes')
    args = parser.parse_args()
    
    print("🚀 Setting up AI Email Agent for Render deployment")
    print("=" * 50)
    
    if not args.check_only:
        create_directories()
    
    check_requirements()
    
    if not args.check_only:
        setup_render_config()
        check_procfile()
        setup_keep_alive()
        create_env_sample()
    
    check_health_endpoint()
    
    print("=" * 50)
    print("✅ Setup complete! Your application is ready for Render deployment.")
    print("📝 Follow the instructions in RENDER_DEPLOYMENT.md to deploy your application.")

if __name__ == "__main__":
    main()
