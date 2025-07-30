"""
Campaign attribution and lead scoring system
"""

import logging
from typing import Optional, Dict, List, Any
from datetime import datetime, timedelta
import re

from .salesforce_client import SalesforceClient
from .models import Email, SalesforceContact, EmailClassification

logger = logging.getLogger(__name__)

class CampaignAttributor:
    """Handles campaign attribution and lead scoring"""
    
    def __init__(self, salesforce_client: SalesforceClient):
        self.sf_client = salesforce_client
        self.campaign_patterns = {}
        self.scoring_rules = self._initialize_scoring_rules()
    
    def _initialize_scoring_rules(self) -> Dict[str, Dict]:
        """Initialize lead scoring rules"""
        return {
            'email_response': {
                'Not Interested': -10,
                'Maybe Interested': 5,
                'Interested': 15
            },
            'engagement_multipliers': {
                'first_response': 1.5,
                'quick_response': 1.2,  # Response within 24 hours
                'detailed_response': 1.3,  # Long, detailed responses
                'question_asking': 1.4,  # Asking questions
                'pricing_inquiry': 2.0,  # Asking about pricing
                'demo_request': 2.5,  # Requesting demo
                'meeting_request': 3.0  # Requesting meeting
            },
            'negative_indicators': {
                'unsubscribe_request': -25,
                'competitor_mention': -5,
                'budget_concerns': -3,
                'timing_issues': -2
            }
        }
    
    async def identify_campaign(self, email: Email, contact: Optional[SalesforceContact]) -> Optional[Dict[str, Any]]:
        """Identify which campaign this email response belongs to"""
        try:
            if not contact:
                return None
            
            # Get active campaigns for this contact
            campaigns = await self.sf_client.get_contact_campaigns(contact.id)
            
            if not campaigns:
                return None
            
            # Try to match email to specific campaign
            best_match = None
            best_score = 0
            
            for campaign in campaigns:
                score = self._calculate_campaign_match_score(email, campaign)
                if score > best_score:
                    best_score = score
                    best_match = campaign
            
            if best_match and best_score > 0.3:  # Minimum confidence threshold
                return {
                    'campaign_id': best_match['Campaign']['Id'],
                    'campaign_name': best_match['Campaign']['Name'],
                    'match_confidence': best_score,
                    'attribution_method': self._get_attribution_method(email, best_match)
                }
            
            # If no specific match, return most recent campaign
            if campaigns:
                most_recent = max(campaigns, key=lambda c: c.get('CreatedDate', ''))
                return {
                    'campaign_id': most_recent['Campaign']['Id'],
                    'campaign_name': most_recent['Campaign']['Name'],
                    'match_confidence': 0.2,
                    'attribution_method': 'most_recent_campaign'
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Campaign identification failed: {e}")
            return None
    
    def _calculate_campaign_match_score(self, email: Email, campaign: Dict) -> float:
        """Calculate how well an email matches a campaign"""
        score = 0.0
        
        campaign_name = campaign['Campaign']['Name'].lower()
        email_subject = email.subject.lower()
        email_body = email.body.lower()
        
        # Subject line matching
        if any(word in email_subject for word in campaign_name.split()):
            score += 0.4
        
        # Body content matching
        campaign_keywords = self._extract_campaign_keywords(campaign_name)
        for keyword in campaign_keywords:
            if keyword in email_body:
                score += 0.1
        
        # Reference matching (In-Reply-To, References headers)
        if email.in_reply_to or email.references:
            score += 0.3
        
        # Time-based matching (recent campaigns more likely)
        created_date = campaign.get('CreatedDate')
        if created_date:
            try:
                campaign_date = datetime.fromisoformat(created_date.replace('Z', '+00:00'))
                days_ago = (datetime.now() - campaign_date).days
                if days_ago <= 7:
                    score += 0.2
                elif days_ago <= 30:
                    score += 0.1
            except:
                pass
        
        return min(score, 1.0)  # Cap at 1.0
    
    def _extract_campaign_keywords(self, campaign_name: str) -> List[str]:
        """Extract keywords from campaign name for matching"""
        # Remove common campaign words
        stop_words = {'campaign', 'email', 'marketing', 'outreach', 'sequence'}
        
        words = re.findall(r'\b\w+\b', campaign_name.lower())
        keywords = [word for word in words if word not in stop_words and len(word) > 2]
        
        return keywords
    
    def _get_attribution_method(self, email: Email, campaign: Dict) -> str:
        """Determine how the campaign was attributed"""
        campaign_name = campaign['Campaign']['Name'].lower()
        
        if any(word in email.subject.lower() for word in campaign_name.split()):
            return 'subject_match'
        elif email.in_reply_to or email.references:
            return 'email_thread'
        else:
            return 'keyword_match'
    
    async def calculate_lead_score_change(
        self, 
        email: Email, 
        classification: EmailClassification, 
        contact: SalesforceContact,
        campaign_info: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Calculate lead score change based on email response"""
        try:
            base_score = self.scoring_rules['email_response'][classification.value]
            multiplier = 1.0
            score_breakdown = {'base_score': base_score}
            
            # Apply engagement multipliers
            engagement_factors = self._analyze_engagement_factors(email)
            for factor, factor_multiplier in engagement_factors.items():
                multiplier *= factor_multiplier
                score_breakdown[f'multiplier_{factor}'] = factor_multiplier
            
            # Apply negative indicators
            negative_factors = self._analyze_negative_factors(email)
            for factor, penalty in negative_factors.items():
                base_score += penalty
                score_breakdown[f'penalty_{factor}'] = penalty
            
            final_score = int(base_score * multiplier)
            
            # Campaign-specific adjustments
            if campaign_info:
                campaign_adjustment = self._get_campaign_score_adjustment(campaign_info)
                final_score += campaign_adjustment
                score_breakdown['campaign_adjustment'] = campaign_adjustment
            
            return {
                'score_change': final_score,
                'breakdown': score_breakdown,
                'total_multiplier': multiplier,
                'engagement_factors': list(engagement_factors.keys()),
                'negative_factors': list(negative_factors.keys())
            }
            
        except Exception as e:
            logger.error(f"Lead score calculation failed: {e}")
            return {'score_change': 0, 'error': str(e)}
    
    def _analyze_engagement_factors(self, email: Email) -> Dict[str, float]:
        """Analyze positive engagement factors in email"""
        factors = {}
        body_lower = email.body.lower()
        
        # Check for pricing inquiries
        pricing_keywords = ['price', 'cost', 'pricing', 'budget', 'quote', 'proposal']
        if any(keyword in body_lower for keyword in pricing_keywords):
            factors['pricing_inquiry'] = self.scoring_rules['engagement_multipliers']['pricing_inquiry']
        
        # Check for demo requests
        demo_keywords = ['demo', 'demonstration', 'show me', 'walk through', 'preview']
        if any(keyword in body_lower for keyword in demo_keywords):
            factors['demo_request'] = self.scoring_rules['engagement_multipliers']['demo_request']
        
        # Check for meeting requests
        meeting_keywords = ['meeting', 'call', 'schedule', 'appointment', 'discuss', 'talk']
        if any(keyword in body_lower for keyword in meeting_keywords):
            factors['meeting_request'] = self.scoring_rules['engagement_multipliers']['meeting_request']
        
        # Check for questions
        if '?' in email.body:
            factors['question_asking'] = self.scoring_rules['engagement_multipliers']['question_asking']
        
        # Check for detailed response (length-based)
        if len(email.body.strip()) > 200:
            factors['detailed_response'] = self.scoring_rules['engagement_multipliers']['detailed_response']
        
        # Check for quick response (would need timestamp comparison)
        # This would require thread context to determine response time
        
        return factors
    
    def _analyze_negative_factors(self, email: Email) -> Dict[str, int]:
        """Analyze negative factors in email"""
        factors = {}
        body_lower = email.body.lower()
        
        # Unsubscribe requests
        unsubscribe_keywords = ['unsubscribe', 'remove me', 'stop sending', 'opt out']
        if any(keyword in body_lower for keyword in unsubscribe_keywords):
            factors['unsubscribe_request'] = self.scoring_rules['negative_indicators']['unsubscribe_request']
        
        # Competitor mentions
        competitor_keywords = ['already have', 'current provider', 'existing solution', 'competitor']
        if any(keyword in body_lower for keyword in competitor_keywords):
            factors['competitor_mention'] = self.scoring_rules['negative_indicators']['competitor_mention']
        
        # Budget concerns
        budget_keywords = ['expensive', 'budget', 'afford', 'cost too much', 'price too high']
        if any(keyword in body_lower for keyword in budget_keywords):
            factors['budget_concerns'] = self.scoring_rules['negative_indicators']['budget_concerns']
        
        # Timing issues
        timing_keywords = ['not right now', 'maybe later', 'future', 'next year', 'busy']
        if any(keyword in body_lower for keyword in timing_keywords):
            factors['timing_issues'] = self.scoring_rules['negative_indicators']['timing_issues']
        
        return factors
    
    def _get_campaign_score_adjustment(self, campaign_info: Dict) -> int:
        """Get campaign-specific score adjustments"""
        # Higher value campaigns get score boosts
        campaign_name = campaign_info.get('campaign_name', '').lower()
        
        high_value_indicators = ['enterprise', 'premium', 'executive', 'vip']
        if any(indicator in campaign_name for indicator in high_value_indicators):
            return 5
        
        return 0
    
    async def update_lead_score(
        self, 
        contact: SalesforceContact, 
        score_change: int,
        reason: str
    ) -> bool:
        """Update lead score in Salesforce"""
        try:
            # Get current lead score
            current_score = await self._get_current_lead_score(contact.id)
            new_score = max(0, current_score + score_change)  # Don't go below 0
            
            # Update in Salesforce
            update_data = {
                'Lead_Score__c': new_score,
                'Last_Score_Update__c': datetime.now().isoformat(),
                'Score_Change_Reason__c': reason
            }
            
            success = await self.sf_client.update_campaign_status(contact.id, update_data)
            
            if success:
                logger.info(f"Updated lead score for {contact.id}: {current_score} -> {new_score} ({score_change:+d})")
            
            return success
            
        except Exception as e:
            logger.error(f"Lead score update failed: {e}")
            return False
    
    async def _get_current_lead_score(self, contact_id: str) -> int:
        """Get current lead score from Salesforce"""
        try:
            loop = asyncio.get_event_loop()
            
            if contact_id.startswith('003'):  # Contact
                query = f"SELECT Lead_Score__c FROM Contact WHERE Id = '{contact_id}'"
            else:  # Lead
                query = f"SELECT Lead_Score__c FROM Lead WHERE Id = '{contact_id}'"
            
            result = await loop.run_in_executor(
                None,
                lambda: self.sf_client.sf.query(query)
            )
            
            if result['totalSize'] > 0:
                score = result['records'][0].get('Lead_Score__c', 0)
                return int(score) if score else 0
            
            return 0
            
        except Exception as e:
            logger.error(f"Failed to get current lead score: {e}")
            return 0
    
    async def should_create_opportunity(
        self, 
        contact: SalesforceContact, 
        classification: EmailClassification,
        lead_score: int,
        engagement_factors: List[str]
    ) -> Dict[str, Any]:
        """Determine if an opportunity should be created"""
        try:
            # Criteria for opportunity creation
            create_opportunity = False
            reasons = []
            
            # High interest classification
            if classification == EmailClassification.INTERESTED:
                create_opportunity = True
                reasons.append("High interest classification")
            
            # High lead score
            if lead_score >= 50:  # Configurable threshold
                create_opportunity = True
                reasons.append(f"High lead score: {lead_score}")
            
            # Strong engagement indicators
            strong_indicators = ['pricing_inquiry', 'demo_request', 'meeting_request']
            if any(factor in engagement_factors for factor in strong_indicators):
                create_opportunity = True
                reasons.append("Strong buying signals detected")
            
            # Check if opportunity already exists
            existing_opportunity = await self._check_existing_opportunity(contact.id)
            if existing_opportunity:
                create_opportunity = False
                reasons = ["Opportunity already exists"]
            
            return {
                'should_create': create_opportunity,
                'reasons': reasons,
                'existing_opportunity': existing_opportunity,
                'recommended_stage': self._get_recommended_stage(engagement_factors),
                'estimated_value': self._estimate_opportunity_value(contact, engagement_factors)
            }
            
        except Exception as e:
            logger.error(f"Opportunity assessment failed: {e}")
            return {'should_create': False, 'error': str(e)}
    
    async def _check_existing_opportunity(self, contact_id: str) -> Optional[Dict]:
        """Check if opportunity already exists for contact"""
        try:
            loop = asyncio.get_event_loop()
            
            # Query for existing opportunities
            if contact_id.startswith('003'):  # Contact
                query = f"""
                SELECT Id, Name, StageName, Amount, CloseDate 
                FROM Opportunity 
                WHERE AccountId IN (SELECT AccountId FROM Contact WHERE Id = '{contact_id}')
                AND IsClosed = false
                ORDER BY CreatedDate DESC
                LIMIT 1
                """
            else:  # Lead - converted leads have opportunities
                query = f"""
                SELECT Id, Name, StageName, Amount, CloseDate 
                FROM Opportunity 
                WHERE Id IN (SELECT ConvertedOpportunityId FROM Lead WHERE Id = '{contact_id}')
                AND IsClosed = false
                LIMIT 1
                """
            
            result = await loop.run_in_executor(
                None,
                lambda: self.sf_client.sf.query(query)
            )
            
            if result['totalSize'] > 0:
                return result['records'][0]
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to check existing opportunity: {e}")
            return None
    
    def _get_recommended_stage(self, engagement_factors: List[str]) -> str:
        """Get recommended opportunity stage based on engagement"""
        if 'meeting_request' in engagement_factors:
            return 'Qualification'
        elif 'demo_request' in engagement_factors:
            return 'Needs Analysis'
        elif 'pricing_inquiry' in engagement_factors:
            return 'Proposal/Price Quote'
        else:
            return 'Prospecting'
    
    def _estimate_opportunity_value(self, contact: SalesforceContact, engagement_factors: List[str]) -> int:
        """Estimate opportunity value based on contact and engagement"""
        base_value = 10000  # Default base value
        
        # Adjust based on company size (if available)
        if contact.company:
            company_lower = contact.company.lower()
            if any(indicator in company_lower for indicator in ['enterprise', 'corp', 'inc']):
                base_value *= 2
        
        # Adjust based on engagement level
        if 'pricing_inquiry' in engagement_factors:
            base_value *= 1.5
        if 'demo_request' in engagement_factors:
            base_value *= 1.3
        
        return int(base_value)
    
    async def create_opportunity(
        self, 
        contact: SalesforceContact, 
        opportunity_data: Dict[str, Any],
        campaign_info: Optional[Dict] = None
    ) -> Optional[str]:
        """Create opportunity in Salesforce"""
        try:
            loop = asyncio.get_event_loop()
            
            # Prepare opportunity data
            opp_data = {
                'Name': f"{contact.company or contact.first_name} - {datetime.now().strftime('%Y-%m-%d')}",
                'StageName': opportunity_data.get('recommended_stage', 'Prospecting'),
                'Amount': opportunity_data.get('estimated_value', 10000),
                'CloseDate': (datetime.now() + timedelta(days=90)).date().isoformat(),
                'LeadSource': 'Email Campaign',
                'Description': f"Opportunity created from email response. Engagement factors: {', '.join(opportunity_data.get('reasons', []))}"
            }
            
            # Set account/contact relationship
            if contact.id.startswith('003'):  # Contact
                # Get Account ID for contact
                contact_query = f"SELECT AccountId FROM Contact WHERE Id = '{contact.id}'"
                contact_result = await loop.run_in_executor(
                    None,
                    lambda: self.sf_client.sf.query(contact_query)
                )
                
                if contact_result['totalSize'] > 0:
                    account_id = contact_result['records'][0]['AccountId']
                    opp_data['AccountId'] = account_id
            
            # Add campaign information if available
            if campaign_info:
                opp_data['CampaignId'] = campaign_info.get('campaign_id')
            
            # Create opportunity
            result = await loop.run_in_executor(
                None,
                lambda: self.sf_client.sf.Opportunity.create(opp_data)
            )
            
            opportunity_id = result['id']
            logger.info(f"Created opportunity {opportunity_id} for contact {contact.id}")
            
            return opportunity_id
            
        except Exception as e:
            logger.error(f"Opportunity creation failed: {e}")
            return None
