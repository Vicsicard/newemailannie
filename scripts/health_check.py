#!/usr/bin/env python
"""
Health Check Script for AI Email Agent
This script can be used by monitoring systems to check the health of the application.
"""

import argparse
import json
import sys
import requests
from datetime import datetime

def check_health(url, timeout=5, verbose=False):
    """
    Check the health of the AI Email Agent application.
    
    Args:
        url (str): Base URL of the application
        timeout (int): Request timeout in seconds
        verbose (bool): Whether to print detailed output
    
    Returns:
        bool: True if healthy, False otherwise
    """
    health_url = f"{url.rstrip('/')}/health"
    
    try:
        if verbose:
            print(f"Checking health at {health_url}...")
        
        response = requests.get(health_url, timeout=timeout)
        data = response.json()
        
        if verbose:
            print(f"Status code: {response.status_code}")
            print(json.dumps(data, indent=2))
        
        # Check if all services are healthy
        all_services_healthy = all(data.get('services', {}).values())
        db_healthy = data.get('database') == 'ok'
        
        if response.status_code == 200 and all_services_healthy and db_healthy:
            if verbose:
                print("Health check: PASSED")
            return True
        else:
            if verbose:
                print("Health check: FAILED")
                if not all_services_healthy:
                    unhealthy_services = [
                        service for service, status in data.get('services', {}).items() 
                        if not status
                    ]
                    print(f"Unhealthy services: {', '.join(unhealthy_services)}")
                if not db_healthy:
                    print(f"Database issue: {data.get('database')}")
            return False
            
    except requests.RequestException as e:
        if verbose:
            print(f"Health check: FAILED - Connection error: {str(e)}")
        return False

def main():
    parser = argparse.ArgumentParser(description='Health check for AI Email Agent')
    parser.add_argument('--url', default='http://localhost:8000', help='Base URL of the application')
    parser.add_argument('--timeout', type=int, default=5, help='Request timeout in seconds')
    parser.add_argument('--verbose', action='store_true', help='Print detailed output')
    args = parser.parse_args()
    
    is_healthy = check_health(args.url, args.timeout, args.verbose)
    
    if is_healthy:
        sys.exit(0)  # Success exit code
    else:
        sys.exit(1)  # Error exit code

if __name__ == '__main__':
    main()
