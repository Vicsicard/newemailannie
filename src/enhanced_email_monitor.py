"""
Enhanced email monitor integrating all advanced features
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
import asyncio

from .email_monitor import EmailMonitor
from .enhanced_classifier import EnhancedClassifier
from .thread_manager import ThreadManager, EmailThread
from .campaign_attribution import CampaignAttributor
from .personalization_engine import PersonalizationEngine
from .follow_up_sequences import FollowUpSequenceManager
from .analytics_dashboard import AnalyticsDashboard
from .models import Email, ProcessingResult, SalesforceContact
from .salesforce_client import SalesforceClient
from .response_generator import ResponseGenerator
from .notification_service import NotificationService

logger = logging.getLogger(__name__)

class EnhancedEmailMonitor(EmailMonitor):
    """Enhanced email monitor with all advanced features integrated"""
    
    def __init__(
        self,
        salesforce_client: SalesforceClient,
        response_generator: ResponseGenerator,
        notification_service: NotificationService
    ):
        # Initialize enhanced components
        self.enhanced_classifier = EnhancedClassifier()
        self.thread_manager = ThreadManager()
        self.campaign_attributor = CampaignAttributor(salesforce_client)
        self.personalization_engine = PersonalizationEngine(salesforce_client)
        self.follow_up_manager = FollowUpSequenceManager(
            self.personalization_engine, 
            response_generator
        )
        self.analytics_dashboard = AnalyticsDashboard(salesforce_client)
        
        # Initialize base class with enhanced classifier
        super().__init__(
            ai_classifier=self.enhanced_classifier,
            salesforce_client=salesforce_client,
            response_generator=response_generator,
            notification_service=notification_service
        )
    
    async def process_new_emails(self):
        """Enhanced email processing with all advanced features"""
        try:
            logger.info("Starting enhanced email processing cycle")
            
            # Fetch new emails
            emails = await self.fetch_new_emails()
            
            if not emails:
                logger.info("No new emails to process")
                # Process due follow-up sequences
                await self._process_follow_up_sequences()
                return
            
            # Process each email with enhanced pipeline
            results = []
            for email_obj in emails:
                result = await self._process_email_enhanced(email_obj)
                results.append(result)
                
                # Small delay between processing emails
                await asyncio.sleep(1)
            
            # Process follow-up sequences
            await self._process_follow_up_sequences()
            
            # Update analytics
            await self._update_analytics(results)
            
            # Log summary
            successful = len([r for r in results if not r.errors])
            failed = len([r for r in results if r.errors])
            logger.info(f"Enhanced processing complete: {successful} successful, {failed} failed")
            
        except Exception as e:
            logger.error(f"Error in enhanced email processing cycle: {e}")
    
    async def _process_email_enhanced(self, email: Email) -> ProcessingResult:
        """Process email with all enhanced features"""
        start_time = datetime.now()
        errors = []
        
        try:
            logger.info(f"Enhanced processing email from {email.sender}: {email.subject}")
            
            # Step 1: Thread management and duplicate detection
            thread, is_new_thread = self.thread_manager.add_email_to_thread(email)
            
            if not thread:
                logger.info(f"Email filtered out (duplicate/automated): {email.sender}")
                return ProcessingResult(
                    email_id=email.message_id,
                    classification=None,
                    salesforce_updated=False,
                    response_sent=False,
                    notification_sent=False,
                    errors=["Email filtered out"],
                    processing_time=(datetime.now() - start_time).total_seconds()
                )
            
            # Step 2: Get contact information
            contact = await self.salesforce_client.find_contact_by_email(email.sender)
            
            # Step 3: Get comprehensive contact data for personalization
            contact_data = {}
            if contact:
                contact_data = await self.personalization_engine.get_comprehensive_contact_data(contact)
            
            # Step 4: Enhanced classification with context
            thread_context = self.thread_manager.get_thread_context(thread)
            classification = await self.enhanced_classifier.classify_with_context(
                email, 
                thread_context, 
                contact_data.get('basic_info', {})
            )
            
            logger.info(f"Enhanced classification: {classification.classification} (confidence: {classification.confidence})")
            
            # Step 5: Campaign attribution
            campaign_info = None
            if contact:
                campaign_info = await self.campaign_attributor.identify_campaign(email, contact)
                if campaign_info:
                    logger.info(f"Attributed to campaign: {campaign_info['campaign_name']}")
            
            # Step 6: Lead scoring
            lead_score_change = 0
            if contact:
                engagement_factors = getattr(classification, 'engagement_factors', [])
                score_data = await self.campaign_attributor.calculate_lead_score_change(
                    email, classification.classification, contact, campaign_info
                )
                lead_score_change = score_data.get('score_change', 0)
                
                if lead_score_change != 0:
                    await self.campaign_attributor.update_lead_score(
                        contact, lead_score_change, f"Email response: {classification.classification}"
                    )
            
            # Step 7: Opportunity creation assessment
            opportunity_created = False
            if contact and classification.classification.value == 'Interested':
                engagement_factors = getattr(classification, 'engagement_factors', [])
                opportunity_assessment = await self.campaign_attributor.should_create_opportunity(
                    contact, classification.classification, 
                    contact_data.get('contact_details', {}).get('lead_score', 0) + lead_score_change,
                    engagement_factors
                )
                
                if opportunity_assessment.get('should_create', False):
                    opportunity_id = await self.campaign_attributor.create_opportunity(
                        contact, opportunity_assessment, campaign_info
                    )
                    if opportunity_id:
                        opportunity_created = True
                        logger.info(f"Created opportunity {opportunity_id} for {contact.id}")
            
            # Step 8: Update Salesforce with enhanced data
            salesforce_updated = False
            try:
                if contact:
                    # Update campaign status
                    await self.salesforce_client.update_campaign_status(
                        contact.id, 
                        classification.classification.value
                    )
                    
                    # Add additional context to contact record
                    additional_data = {
                        'Last_AI_Classification__c': classification.classification.value,
                        'Classification_Confidence__c': classification.confidence,
                        'Thread_Length__c': len(thread.emails),
                        'Campaign_Attribution__c': campaign_info.get('campaign_name') if campaign_info else None
                    }
                    
                    salesforce_updated = True
                    logger.info(f"Enhanced Salesforce update completed for {contact.id}")
                else:
                    logger.warning(f"Contact not found in Salesforce: {email.sender}")
                    errors.append(f"Contact not found: {email.sender}")
            except Exception as e:
                logger.error(f"Enhanced Salesforce update failed: {e}")
                errors.append(f"Salesforce update failed: {str(e)}")
            
            # Step 9: Enhanced response generation
            response_sent = False
            if classification.classification.value in ['Maybe Interested', 'Interested']:
                try:
                    # Generate personalization context
                    personalization_context = self.personalization_engine.generate_personalization_context(
                        contact_data, email, thread, classification.classification
                    )
                    
                    # Generate enhanced response
                    response = await self.response_generator.generate_response(
                        email, classification, contact
                    )
                    
                    # Apply enhanced personalization
                    variables = self.personalization_engine.generate_personalized_variables(personalization_context)
                    
                    # Update response with personalized content
                    for key, value in variables.items():
                        response.body = response.body.replace(f"{{{key}}}", value)
                        response.subject = response.subject.replace(f"{{{key}}}", value)
                    
                    # Send response
                    await self.response_generator.send_response(email.sender, response)
                    response_sent = True
                    logger.info(f"Enhanced response sent to {email.sender}")
                    
                except Exception as e:
                    logger.error(f"Enhanced response generation/sending failed: {e}")
                    errors.append(f"Response failed: {str(e)}")
            
            # Step 10: Enhanced notifications
            notification_sent = False
            if classification.classification.value == 'Interested':
                try:
                    await self.notification_service.notify_sales_team(
                        email, classification, contact
                    )
                    notification_sent = True
                    logger.info(f"Enhanced notification sent for interested lead: {email.sender}")
                except Exception as e:
                    logger.error(f"Enhanced notification failed: {e}")
                    errors.append(f"Notification failed: {str(e)}")
            
            # Step 11: Start follow-up sequences
            try:
                engagement_factors = getattr(classification, 'engagement_factors', [])
                sequence_type = self.follow_up_manager.determine_sequence_type(
                    email, classification.classification, engagement_factors, contact_data
                )
                
                if sequence_type and contact:
                    await self.follow_up_manager.start_sequence(
                        contact, sequence_type, email, contact_data
                    )
                    logger.info(f"Started follow-up sequence: {sequence_type.value}")
                    
            except Exception as e:
                logger.error(f"Follow-up sequence initiation failed: {e}")
                errors.append(f"Follow-up sequence failed: {str(e)}")
            
            # Step 12: Record feedback for learning
            try:
                self.enhanced_classifier.record_classification(
                    email, classification, thread_context, contact_data.get('basic_info', {})
                )
            except Exception as e:
                logger.error(f"Classification recording failed: {e}")
            
            # Update statistics
            self.stats.total_emails_processed += 1
            self.stats.classifications[classification.classification] += 1
            if response_sent:
                self.stats.responses_sent += 1
            if notification_sent:
                self.stats.notifications_sent += 1
            if errors:
                self.stats.errors += 1
            
            processing_time = (datetime.now() - start_time).total_seconds()
            self.stats.average_processing_time = (
                (self.stats.average_processing_time * (self.stats.total_emails_processed - 1) + processing_time) 
                / self.stats.total_emails_processed
            )
            self.stats.last_processed = datetime.now()
            
            # Create enhanced processing result
            result = ProcessingResult(
                email_id=email.message_id,
                classification=classification,
                salesforce_updated=salesforce_updated,
                response_sent=response_sent,
                notification_sent=notification_sent,
                errors=errors,
                processing_time=processing_time
            )
            
            # Add enhanced metadata
            result.thread_id = thread.thread_id
            result.campaign_attribution = campaign_info
            result.lead_score_change = lead_score_change
            result.opportunity_created = opportunity_created
            result.personalization_factors = list(variables.keys()) if 'variables' in locals() else []
            
            return result
            
        except Exception as e:
            logger.error(f"Enhanced email processing failed for {email.message_id}: {e}")
            self.stats.errors += 1
            return ProcessingResult(
                email_id=email.message_id,
                classification=classification if 'classification' in locals() else None,
                salesforce_updated=False,
                response_sent=False,
                notification_sent=False,
                errors=[str(e)],
                processing_time=(datetime.now() - start_time).total_seconds()
            )
    
    async def _process_follow_up_sequences(self):
        """Process due follow-up sequences"""
        try:
            due_sequences = await self.follow_up_manager.process_due_sequences()
            if due_sequences:
                logger.info(f"Processed {len(due_sequences)} follow-up sequences")
        except Exception as e:
            logger.error(f"Follow-up sequence processing failed: {e}")
    
    async def _update_analytics(self, results: List[ProcessingResult]):
        """Update analytics with processing results"""
        try:
            # This would typically update a database with processing results
            # For now, we'll just log the summary
            total_processed = len(results)
            successful = len([r for r in results if not r.errors])
            
            classifications = {}
            for result in results:
                if result.classification:
                    cls = result.classification.classification.value
                    classifications[cls] = classifications.get(cls, 0) + 1
            
            logger.info(f"Analytics update: {total_processed} processed, {successful} successful")
            logger.info(f"Classifications: {classifications}")
            
        except Exception as e:
            logger.error(f"Analytics update failed: {e}")
    
    def get_enhanced_stats(self) -> Dict[str, Any]:
        """Get enhanced statistics including all new features"""
        base_stats = self.get_stats()
        
        # Add enhanced statistics
        enhanced_stats = {
            **base_stats,
            'thread_management': self.thread_manager.get_thread_statistics(),
            'classification_insights': self.enhanced_classifier.get_learning_insights(),
            'follow_up_sequences': self.follow_up_manager.get_sequence_statistics(),
            'personalization_usage': {
                'cache_size': len(self.personalization_engine.personalization_cache),
                'context_enabled': True
            }
        }
        
        return enhanced_stats
    
    async def get_comprehensive_dashboard(self, days: int = 30) -> Dict[str, Any]:
        """Get comprehensive analytics dashboard"""
        try:
            dashboard = await self.analytics_dashboard.get_performance_dashboard(days)
            
            # Add real-time stats
            dashboard['real_time_stats'] = self.get_enhanced_stats()
            
            return dashboard
            
        except Exception as e:
            logger.error(f"Dashboard generation failed: {e}")
            return {'error': str(e)}
    
    async def add_classification_feedback(self, email_id: str, correct_classification: str):
        """Add feedback for learning loop"""
        try:
            self.enhanced_classifier.add_feedback(email_id, correct_classification, "manual")
            logger.info(f"Feedback added for email {email_id}: {correct_classification}")
        except Exception as e:
            logger.error(f"Failed to add feedback: {e}")
    
    async def cleanup_old_data(self, days_old: int = 30):
        """Clean up old data to prevent memory bloat"""
        try:
            # Clean up old threads
            self.thread_manager.cleanup_old_threads(days_old)
            
            # Clean up personalization cache
            cutoff_date = datetime.now().strftime('%Y-%m-%d')
            keys_to_remove = [
                key for key in self.personalization_engine.personalization_cache.keys()
                if not key.endswith(cutoff_date)
            ]
            
            for key in keys_to_remove:
                del self.personalization_engine.personalization_cache[key]
            
            logger.info(f"Cleaned up {len(keys_to_remove)} old personalization cache entries")
            
        except Exception as e:
            logger.error(f"Data cleanup failed: {e}")
    
    async def export_analytics(self, format_type: str = 'json', days: int = 30) -> Dict[str, Any]:
        """Export comprehensive analytics data"""
        try:
            start_date = datetime.now() - timedelta(days=days)
            end_date = datetime.now()
            
            return await self.analytics_dashboard.export_analytics_data(
                format_type, start_date, end_date
            )
            
        except Exception as e:
            logger.error(f"Analytics export failed: {e}")
            return {'error': str(e)}
