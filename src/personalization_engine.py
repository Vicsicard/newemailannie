"""
Advanced personalization engine using Salesforce data
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import json

from .salesforce_client import SalesforceClient
from .models import Email, SalesforceContact, EmailClassification
from .thread_manager import EmailThread

logger = logging.getLogger(__name__)

class PersonalizationEngine:
    """Advanced personalization using comprehensive Salesforce data"""
    
    def __init__(self, salesforce_client: SalesforceClient):
        self.sf_client = salesforce_client
        self.personalization_cache = {}
        
    async def get_comprehensive_contact_data(self, contact: SalesforceContact) -> Dict[str, Any]:
        """Get comprehensive contact data for personalization"""
        try:
            # Check cache first
            cache_key = f"{contact.id}_{datetime.now().strftime('%Y-%m-%d')}"
            if cache_key in self.personalization_cache:
                return self.personalization_cache[cache_key]
            
            contact_data = {
                'basic_info': {
                    'first_name': contact.first_name,
                    'last_name': contact.last_name,
                    'email': contact.email,
                    'company': contact.company,
                    'phone': contact.phone
                }
            }
            
            # Get additional Salesforce data
            loop = asyncio.get_event_loop()
            
            if contact.id.startswith('003'):  # Contact
                # Get Contact details with Account information
                contact_query = f"""
                SELECT Id, FirstName, LastName, Email, Phone, Title, Department,
                       Account.Name, Account.Industry, Account.NumberOfEmployees,
                       Account.AnnualRevenue, Account.Website, Account.BillingCity,
                       Account.BillingState, Account.BillingCountry,
                       LeadSource, CreatedDate, LastActivityDate,
                       Description, Lead_Score__c
                FROM Contact 
                WHERE Id = '{contact.id}'
                """
                
                result = await loop.run_in_executor(
                    None,
                    lambda: self.sf_client.sf.query(contact_query)
                )
                
                if result['totalSize'] > 0:
                    record = result['records'][0]
                    contact_data.update(self._parse_contact_record(record))
                
            else:  # Lead
                # Get Lead details
                lead_query = f"""
                SELECT Id, FirstName, LastName, Email, Phone, Title, Company,
                       Industry, NumberOfEmployees, AnnualRevenue, Website,
                       City, State, Country, LeadSource, CreatedDate,
                       LastActivityDate, Description, Lead_Score__c, Status
                FROM Lead 
                WHERE Id = '{contact.id}'
                """
                
                result = await loop.run_in_executor(
                    None,
                    lambda: self.sf_client.sf.query(lead_query)
                )
                
                if result['totalSize'] > 0:
                    record = result['records'][0]
                    contact_data.update(self._parse_lead_record(record))
            
            # Get campaign history
            contact_data['campaign_history'] = await self._get_campaign_history(contact.id)
            
            # Get activity history
            contact_data['activity_history'] = await self._get_activity_history(contact.id)
            
            # Get opportunity history
            contact_data['opportunity_history'] = await self._get_opportunity_history(contact.id)
            
            # Cache the result
            self.personalization_cache[cache_key] = contact_data
            
            return contact_data
            
        except Exception as e:
            logger.error(f"Failed to get comprehensive contact data: {e}")
            return {'basic_info': contact.dict()}
    
    def _parse_contact_record(self, record: Dict) -> Dict[str, Any]:
        """Parse Salesforce Contact record"""
        account = record.get('Account', {}) or {}
        
        return {
            'contact_details': {
                'title': record.get('Title'),
                'department': record.get('Department'),
                'lead_source': record.get('LeadSource'),
                'created_date': record.get('CreatedDate'),
                'last_activity': record.get('LastActivityDate'),
                'description': record.get('Description'),
                'lead_score': record.get('Lead_Score__c', 0)
            },
            'company_details': {
                'name': account.get('Name'),
                'industry': account.get('Industry'),
                'employee_count': account.get('NumberOfEmployees'),
                'annual_revenue': account.get('AnnualRevenue'),
                'website': account.get('Website'),
                'location': {
                    'city': account.get('BillingCity'),
                    'state': account.get('BillingState'),
                    'country': account.get('BillingCountry')
                }
            }
        }
    
    def _parse_lead_record(self, record: Dict) -> Dict[str, Any]:
        """Parse Salesforce Lead record"""
        return {
            'contact_details': {
                'title': record.get('Title'),
                'lead_source': record.get('LeadSource'),
                'created_date': record.get('CreatedDate'),
                'last_activity': record.get('LastActivityDate'),
                'description': record.get('Description'),
                'lead_score': record.get('Lead_Score__c', 0),
                'status': record.get('Status')
            },
            'company_details': {
                'name': record.get('Company'),
                'industry': record.get('Industry'),
                'employee_count': record.get('NumberOfEmployees'),
                'annual_revenue': record.get('AnnualRevenue'),
                'website': record.get('Website'),
                'location': {
                    'city': record.get('City'),
                    'state': record.get('State'),
                    'country': record.get('Country')
                }
            }
        }
    
    async def _get_campaign_history(self, contact_id: str) -> List[Dict]:
        """Get campaign history for contact"""
        try:
            loop = asyncio.get_event_loop()
            
            query = f"""
            SELECT Campaign.Id, Campaign.Name, Campaign.Type, Campaign.Status,
                   Status, HasResponded, FirstRespondedDate, CreatedDate
            FROM CampaignMember 
            WHERE (ContactId = '{contact_id}' OR LeadId = '{contact_id}')
            ORDER BY CreatedDate DESC
            LIMIT 10
            """
            
            result = await loop.run_in_executor(
                None,
                lambda: self.sf_client.sf.query(query)
            )
            
            return result.get('records', [])
            
        except Exception as e:
            logger.error(f"Failed to get campaign history: {e}")
            return []
    
    async def _get_activity_history(self, contact_id: str) -> List[Dict]:
        """Get recent activity history"""
        try:
            loop = asyncio.get_event_loop()
            
            query = f"""
            SELECT Id, Subject, ActivityDate, Status, Priority, Type,
                   Description, CreatedDate
            FROM Task 
            WHERE WhoId = '{contact_id}'
            ORDER BY CreatedDate DESC
            LIMIT 5
            """
            
            result = await loop.run_in_executor(
                None,
                lambda: self.sf_client.sf.query(query)
            )
            
            return result.get('records', [])
            
        except Exception as e:
            logger.error(f"Failed to get activity history: {e}")
            return []
    
    async def _get_opportunity_history(self, contact_id: str) -> List[Dict]:
        """Get opportunity history"""
        try:
            loop = asyncio.get_event_loop()
            
            if contact_id.startswith('003'):  # Contact
                query = f"""
                SELECT Id, Name, StageName, Amount, CloseDate, IsClosed, IsWon,
                       CreatedDate, LastModifiedDate
                FROM Opportunity 
                WHERE AccountId IN (SELECT AccountId FROM Contact WHERE Id = '{contact_id}')
                ORDER BY CreatedDate DESC
                LIMIT 5
                """
            else:  # Lead
                query = f"""
                SELECT Id, Name, StageName, Amount, CloseDate, IsClosed, IsWon,
                       CreatedDate, LastModifiedDate
                FROM Opportunity 
                WHERE Id IN (SELECT ConvertedOpportunityId FROM Lead WHERE Id = '{contact_id}')
                ORDER BY CreatedDate DESC
                LIMIT 5
                """
            
            result = await loop.run_in_executor(
                None,
                lambda: self.sf_client.sf.query(query)
            )
            
            return result.get('records', [])
            
        except Exception as e:
            logger.error(f"Failed to get opportunity history: {e}")
            return []
    
    def generate_personalization_context(
        self, 
        contact_data: Dict[str, Any],
        email: Email,
        thread: Optional[EmailThread] = None,
        classification: Optional[EmailClassification] = None
    ) -> Dict[str, Any]:
        """Generate comprehensive personalization context"""
        
        context = {
            'contact_info': self._extract_contact_context(contact_data),
            'company_info': self._extract_company_context(contact_data),
            'relationship_context': self._extract_relationship_context(contact_data),
            'engagement_context': self._extract_engagement_context(contact_data, thread),
            'personalization_opportunities': self._identify_personalization_opportunities(contact_data, email)
        }
        
        return context
    
    def _extract_contact_context(self, contact_data: Dict) -> Dict[str, Any]:
        """Extract contact-specific context"""
        basic = contact_data.get('basic_info', {})
        details = contact_data.get('contact_details', {})
        
        return {
            'name': f"{basic.get('first_name', '')} {basic.get('last_name', '')}".strip(),
            'first_name': basic.get('first_name'),
            'title': details.get('title'),
            'department': details.get('department'),
            'lead_score': details.get('lead_score', 0),
            'seniority_level': self._determine_seniority(details.get('title', '')),
            'contact_age_days': self._calculate_contact_age(details.get('created_date'))
        }
    
    def _extract_company_context(self, contact_data: Dict) -> Dict[str, Any]:
        """Extract company-specific context"""
        company = contact_data.get('company_details', {})
        location = company.get('location', {})
        
        return {
            'name': company.get('name'),
            'industry': company.get('industry'),
            'size_category': self._categorize_company_size(company.get('employee_count')),
            'revenue_category': self._categorize_revenue(company.get('annual_revenue')),
            'location': f"{location.get('city', '')}, {location.get('state', '')}".strip(', '),
            'website': company.get('website'),
            'is_enterprise': self._is_enterprise_company(company)
        }
    
    def _extract_relationship_context(self, contact_data: Dict) -> Dict[str, Any]:
        """Extract relationship and history context"""
        campaigns = contact_data.get('campaign_history', [])
        activities = contact_data.get('activity_history', [])
        opportunities = contact_data.get('opportunity_history', [])
        
        return {
            'lead_source': contact_data.get('contact_details', {}).get('lead_source'),
            'campaign_count': len(campaigns),
            'recent_campaigns': [c.get('Campaign', {}).get('Name') for c in campaigns[:3]],
            'has_responded_before': any(c.get('HasResponded') for c in campaigns),
            'activity_count': len(activities),
            'has_opportunities': len(opportunities) > 0,
            'opportunity_stages': [o.get('StageName') for o in opportunities if not o.get('IsClosed')],
            'relationship_age': self._calculate_contact_age(contact_data.get('contact_details', {}).get('created_date'))
        }
    
    def _extract_engagement_context(self, contact_data: Dict, thread: Optional[EmailThread]) -> Dict[str, Any]:
        """Extract engagement-specific context"""
        context = {
            'engagement_level': self._assess_engagement_level(contact_data),
            'communication_style': 'unknown',
            'response_pattern': 'unknown'
        }
        
        if thread:
            context.update({
                'thread_length': len(thread.emails),
                'conversation_duration': (thread.last_email_date - thread.first_email_date).days,
                'communication_style': self._analyze_communication_style(thread),
                'response_pattern': self._analyze_response_pattern(thread)
            })
        
        return context
    
    def _identify_personalization_opportunities(self, contact_data: Dict, email: Email) -> List[str]:
        """Identify specific personalization opportunities"""
        opportunities = []
        
        company = contact_data.get('company_details', {})
        contact = contact_data.get('contact_details', {})
        
        # Industry-specific personalization
        if company.get('industry'):
            opportunities.append(f"industry_specific_{company['industry'].lower().replace(' ', '_')}")
        
        # Title-based personalization
        if contact.get('title'):
            if any(word in contact['title'].lower() for word in ['ceo', 'president', 'founder']):
                opportunities.append('executive_level')
            elif any(word in contact['title'].lower() for word in ['manager', 'director', 'vp']):
                opportunities.append('management_level')
            elif any(word in contact['title'].lower() for word in ['marketing', 'sales']):
                opportunities.append('marketing_sales_focus')
        
        # Company size personalization
        size_category = self._categorize_company_size(company.get('employee_count'))
        if size_category:
            opportunities.append(f'company_size_{size_category}')
        
        # Geographic personalization
        location = company.get('location', {})
        if location.get('city'):
            opportunities.append('geographic_reference')
        
        # Engagement history personalization
        if contact_data.get('relationship_context', {}).get('has_responded_before'):
            opportunities.append('returning_responder')
        
        # Lead score personalization
        lead_score = contact.get('lead_score', 0)
        if lead_score > 50:
            opportunities.append('high_value_prospect')
        
        return opportunities
    
    def _determine_seniority(self, title: str) -> str:
        """Determine seniority level from title"""
        if not title:
            return 'unknown'
        
        title_lower = title.lower()
        
        if any(word in title_lower for word in ['ceo', 'president', 'founder', 'owner']):
            return 'executive'
        elif any(word in title_lower for word in ['vp', 'vice president', 'director', 'head of']):
            return 'senior_management'
        elif any(word in title_lower for word in ['manager', 'lead', 'supervisor']):
            return 'management'
        elif any(word in title_lower for word in ['specialist', 'analyst', 'coordinator']):
            return 'individual_contributor'
        else:
            return 'unknown'
    
    def _categorize_company_size(self, employee_count: Optional[int]) -> Optional[str]:
        """Categorize company by employee count"""
        if not employee_count:
            return None
        
        if employee_count < 10:
            return 'startup'
        elif employee_count < 50:
            return 'small'
        elif employee_count < 200:
            return 'medium'
        elif employee_count < 1000:
            return 'large'
        else:
            return 'enterprise'
    
    def _categorize_revenue(self, annual_revenue: Optional[float]) -> Optional[str]:
        """Categorize company by revenue"""
        if not annual_revenue:
            return None
        
        if annual_revenue < 1000000:  # < $1M
            return 'small'
        elif annual_revenue < 10000000:  # < $10M
            return 'medium'
        elif annual_revenue < 100000000:  # < $100M
            return 'large'
        else:
            return 'enterprise'
    
    def _is_enterprise_company(self, company_data: Dict) -> bool:
        """Determine if company is enterprise-level"""
        employee_count = company_data.get('employee_count', 0)
        annual_revenue = company_data.get('annual_revenue', 0)
        
        return (employee_count and employee_count > 1000) or (annual_revenue and annual_revenue > 100000000)
    
    def _calculate_contact_age(self, created_date: Optional[str]) -> Optional[int]:
        """Calculate how long contact has been in system"""
        if not created_date:
            return None
        
        try:
            created = datetime.fromisoformat(created_date.replace('Z', '+00:00'))
            return (datetime.now() - created).days
        except:
            return None
    
    def _assess_engagement_level(self, contact_data: Dict) -> str:
        """Assess overall engagement level"""
        campaigns = contact_data.get('campaign_history', [])
        activities = contact_data.get('activity_history', [])
        lead_score = contact_data.get('contact_details', {}).get('lead_score', 0)
        
        # Calculate engagement score
        engagement_score = 0
        
        # Campaign engagement
        responded_campaigns = sum(1 for c in campaigns if c.get('HasResponded'))
        engagement_score += responded_campaigns * 10
        
        # Activity engagement
        engagement_score += len(activities) * 5
        
        # Lead score
        engagement_score += lead_score
        
        if engagement_score >= 50:
            return 'high'
        elif engagement_score >= 20:
            return 'medium'
        else:
            return 'low'
    
    def _analyze_communication_style(self, thread: EmailThread) -> str:
        """Analyze communication style from thread"""
        if len(thread.emails) < 2:
            return 'unknown'
        
        # Analyze email lengths and formality
        total_length = sum(len(email.body) for email in thread.emails)
        avg_length = total_length / len(thread.emails)
        
        if avg_length > 300:
            return 'detailed'
        elif avg_length < 100:
            return 'brief'
        else:
            return 'moderate'
    
    def _analyze_response_pattern(self, thread: EmailThread) -> str:
        """Analyze response timing pattern"""
        if len(thread.emails) < 2:
            return 'unknown'
        
        # Calculate average response time (simplified)
        response_times = []
        for i in range(1, len(thread.emails)):
            time_diff = (thread.emails[i].received_date - thread.emails[i-1].received_date).total_seconds() / 3600
            response_times.append(time_diff)
        
        avg_response_hours = sum(response_times) / len(response_times)
        
        if avg_response_hours < 4:
            return 'immediate'
        elif avg_response_hours < 24:
            return 'same_day'
        elif avg_response_hours < 72:
            return 'within_days'
        else:
            return 'delayed'
    
    def generate_personalized_variables(self, personalization_context: Dict[str, Any]) -> Dict[str, str]:
        """Generate template variables for personalized responses"""
        contact = personalization_context.get('contact_info', {})
        company = personalization_context.get('company_info', {})
        relationship = personalization_context.get('relationship_context', {})
        
        variables = {
            # Basic variables
            'first_name': contact.get('first_name', 'there'),
            'full_name': contact.get('name', ''),
            'title': contact.get('title', ''),
            'company_name': company.get('name', 'your company'),
            
            # Personalized greetings
            'personalized_greeting': self._generate_personalized_greeting(contact, relationship),
            
            # Company-specific references
            'industry_reference': self._generate_industry_reference(company.get('industry')),
            'company_size_reference': self._generate_size_reference(company.get('size_category')),
            
            # Relationship references
            'relationship_reference': self._generate_relationship_reference(relationship),
            
            # Value propositions
            'relevant_value_prop': self._generate_relevant_value_prop(personalization_context),
            
            # Call-to-action
            'personalized_cta': self._generate_personalized_cta(personalization_context)
        }
        
        return {k: v for k, v in variables.items() if v}  # Remove empty values
    
    def _generate_personalized_greeting(self, contact: Dict, relationship: Dict) -> str:
        """Generate personalized greeting"""
        first_name = contact.get('first_name', 'there')
        
        if relationship.get('has_responded_before'):
            return f"Hi {first_name}, great to hear from you again!"
        elif contact.get('seniority_level') == 'executive':
            return f"Hello {first_name},"
        else:
            return f"Hi {first_name},"
    
    def _generate_industry_reference(self, industry: Optional[str]) -> str:
        """Generate industry-specific reference"""
        if not industry:
            return ""
        
        industry_references = {
            'Technology': "in the tech space",
            'Healthcare': "in healthcare",
            'Financial Services': "in financial services",
            'Manufacturing': "in manufacturing",
            'Retail': "in retail",
            'Education': "in education"
        }
        
        return industry_references.get(industry, f"in the {industry.lower()} industry")
    
    def _generate_size_reference(self, size_category: Optional[str]) -> str:
        """Generate company size reference"""
        if not size_category:
            return ""
        
        size_references = {
            'startup': "for growing startups",
            'small': "for small businesses",
            'medium': "for mid-size companies",
            'large': "for large organizations",
            'enterprise': "for enterprise companies"
        }
        
        return size_references.get(size_category, "")
    
    def _generate_relationship_reference(self, relationship: Dict) -> str:
        """Generate relationship-based reference"""
        if relationship.get('has_opportunities'):
            return "building on our previous discussions"
        elif relationship.get('has_responded_before'):
            return "following up on our conversation"
        else:
            return ""
    
    def _generate_relevant_value_prop(self, context: Dict) -> str:
        """Generate relevant value proposition"""
        opportunities = context.get('personalization_opportunities', [])
        
        if 'executive_level' in opportunities:
            return "strategic growth and ROI"
        elif 'marketing_sales_focus' in opportunities:
            return "improved lead generation and conversion"
        elif 'high_value_prospect' in opportunities:
            return "enterprise-grade solutions"
        else:
            return "business efficiency and growth"
    
    def _generate_personalized_cta(self, context: Dict) -> str:
        """Generate personalized call-to-action"""
        contact = context.get('contact_info', {})
        engagement = context.get('engagement_context', {})
        
        if contact.get('seniority_level') == 'executive':
            return "Would you be available for a brief executive briefing?"
        elif engagement.get('engagement_level') == 'high':
            return "Shall we schedule a detailed discussion about your specific needs?"
        else:
            return "Would you like to learn more about how this could benefit your team?"
