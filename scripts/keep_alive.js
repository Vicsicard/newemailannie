/**
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
setInterval(pingApplication, PING_INTERVAL);
