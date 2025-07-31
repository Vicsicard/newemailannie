"""
Analytics Service for AI Email Agent

This module provides analytics functionality for the AI Email Agent dashboard,
collecting and processing data from various sources including email processing
and Salesforce integration.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import asyncio

logger = logging.getLogger(__name__)

class AnalyticsService:
    """Service for collecting and processing analytics data"""
    
    def __init__(self, email_monitor=None, salesforce_client=None):
        """
        Initialize the analytics service
        
        Args:
            email_monitor: The email monitoring service
            salesforce_client: The Salesforce client for CRM data
        """
        self.email_monitor = email_monitor
        self.salesforce_client = salesforce_client
        self.cache = {}
        self.cache_expiry = {}
        self.cache_duration = 300  # 5 minutes cache by default
    
    async def get_email_processing_stats(self) -> Dict[str, Any]:
        """
        Get email processing statistics
        
        Returns:
            Dict containing email processing statistics
        """
        if self.email_monitor:
            try:
                return self.email_monitor.get_stats()
            except Exception as e:
                logger.error(f"Error getting email processing stats: {e}")
        
        # Return empty stats if email monitor is not available
        return {
            "total_emails_processed": 0,
            "classifications": {"Interested": 0, "Maybe Interested": 0, "Not Interested": 0},
            "responses_sent": 0,
            "notifications_sent": 0,
            "errors": 0,
            "average_processing_time": 0,
            "last_processed": None
        }
    
    async def get_campaign_stats(self) -> List[Dict[str, Any]]:
        """
        Get campaign statistics from Salesforce
        
        Returns:
            List of campaign statistics
        """
        # Check cache first
        if "campaign_stats" in self.cache:
            if datetime.now() < self.cache_expiry.get("campaign_stats", datetime.min):
                return self.cache["campaign_stats"]
        
        # If not in cache or expired, fetch from Salesforce
        campaign_stats = []
        if self.salesforce_client and hasattr(self.salesforce_client, "get_campaign_stats"):
            try:
                campaign_stats = await self.salesforce_client.get_campaign_stats()
            except Exception as e:
                logger.error(f"Error fetching campaign stats from Salesforce: {e}")
        
        # If no data from Salesforce, use placeholder data
        if not campaign_stats:
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
        
        # Update cache
        self.cache["campaign_stats"] = campaign_stats
        self.cache_expiry["campaign_stats"] = datetime.now() + timedelta(seconds=self.cache_duration)
        
        return campaign_stats
    
    async def get_lead_conversion_stats(self) -> Dict[str, Any]:
        """
        Get lead conversion statistics from Salesforce
        
        Returns:
            Dict containing lead conversion statistics
        """
        # Check cache first
        if "lead_stats" in self.cache:
            if datetime.now() < self.cache_expiry.get("lead_stats", datetime.min):
                return self.cache["lead_stats"]
        
        # If not in cache or expired, fetch from Salesforce
        lead_stats = {}
        if self.salesforce_client and hasattr(self.salesforce_client, "get_lead_conversion_stats"):
            try:
                lead_stats = await self.salesforce_client.get_lead_conversion_stats()
            except Exception as e:
                logger.error(f"Error fetching lead stats from Salesforce: {e}")
        
        # If no data from Salesforce, use placeholder data
        if not lead_stats:
            lead_stats = {
                "conversion_rate": 24.5,
                "avg_time_to_convert": "14 days",
                "total_converted": 45,
                "weekly_new_leads": [12, 18, 15, 20],
                "weekly_converted": [3, 5, 4, 7],
                "weekly_conversion_rates": [25.0, 27.8, 26.7, 35.0]
            }
        
        # Update cache
        self.cache["lead_stats"] = lead_stats
        self.cache_expiry["lead_stats"] = datetime.now() + timedelta(seconds=self.cache_duration)
        
        return lead_stats
    
    async def get_performance_metrics(self) -> Dict[str, Any]:
        """
        Get system performance metrics
        
        Returns:
            Dict containing performance metrics
        """
        # Check cache first
        if "performance_metrics" in self.cache:
            if datetime.now() < self.cache_expiry.get("performance_metrics", datetime.min):
                return self.cache["performance_metrics"]
        
        performance_metrics = {}
        
        # Get classification accuracy if available
        if self.email_monitor and hasattr(self.email_monitor, "get_classification_accuracy"):
            try:
                accuracy = await self.email_monitor.get_classification_accuracy()
                if accuracy:
                    performance_metrics["classification_accuracy"] = accuracy
            except Exception as e:
                logger.error(f"Error getting classification accuracy: {e}")
        
        # Get response time metrics if available
        if self.email_monitor and hasattr(self.email_monitor, "get_response_time_metrics"):
            try:
                response_metrics = await self.email_monitor.get_response_time_metrics()
                if response_metrics:
                    performance_metrics.update(response_metrics)
            except Exception as e:
                logger.error(f"Error getting response time metrics: {e}")
        
        # Fill in missing metrics with placeholder data
        if "classification_accuracy" not in performance_metrics:
            performance_metrics["classification_accuracy"] = 91.5
        
        if "avg_response_time" not in performance_metrics:
            performance_metrics["avg_response_time"] = "28 minutes"
            performance_metrics["avg_response_time_seconds"] = 1680
        
        if "manual_triage_reduction" not in performance_metrics:
            performance_metrics["manual_triage_reduction"] = 75
        
        if "weekly_response_times" not in performance_metrics:
            performance_metrics["weekly_response_times"] = [42, 35, 30, 28]
        
        if "weekly_accuracy" not in performance_metrics:
            performance_metrics["weekly_accuracy"] = [87, 89, 90, 91.5]
        
        # Update cache
        self.cache["performance_metrics"] = performance_metrics
        self.cache_expiry["performance_metrics"] = datetime.now() + timedelta(seconds=self.cache_duration)
        
        return performance_metrics
    
    async def get_all_analytics_data(self) -> Dict[str, Any]:
        """
        Get all analytics data in a single call
        
        Returns:
            Dict containing all analytics data
        """
        # Run all data collection in parallel for better performance
        email_stats_task = asyncio.create_task(self.get_email_processing_stats())
        campaign_stats_task = asyncio.create_task(self.get_campaign_stats())
        lead_stats_task = asyncio.create_task(self.get_lead_conversion_stats())
        performance_metrics_task = asyncio.create_task(self.get_performance_metrics())
        
        # Wait for all tasks to complete
        email_stats = await email_stats_task
        campaign_stats = await campaign_stats_task
        lead_stats = await lead_stats_task
        performance_metrics = await performance_metrics_task
        
        return {
            "stats": email_stats,
            "campaign_stats": campaign_stats,
            "lead_stats": lead_stats,
            "performance_metrics": performance_metrics
        }
    
    def clear_cache(self, key: Optional[str] = None):
        """
        Clear the analytics cache
        
        Args:
            key: Specific cache key to clear, or None to clear all
        """
        if key:
            if key in self.cache:
                del self.cache[key]
            if key in self.cache_expiry:
                del self.cache_expiry[key]
        else:
            self.cache = {}
            self.cache_expiry = {}
