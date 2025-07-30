"""
Multi-touch email follow-up sequences based on response classification
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import asyncio

from .models import Email, EmailClassification, SalesforceContact
from .personalization_engine import PersonalizationEngine
from .response_generator import ResponseGenerator

logger = logging.getLogger(__name__)

class SequenceType(str, Enum):
    """Types of follow-up sequences"""
    NOT_INTERESTED_NURTURE = "not_interested_nurture"
    MAYBE_INTERESTED_NURTURE = "maybe_interested_nurture"
    INTERESTED_ACCELERATION = "interested_acceleration"
    DEMO_FOLLOW_UP = "demo_follow_up"
    PRICING_FOLLOW_UP = "pricing_follow_up"
    MEETING_FOLLOW_UP = "meeting_follow_up"

@dataclass
class SequenceStep:
    """Individual step in a follow-up sequence"""
    step_number: int
    delay_days: int
    template_key: str
    subject_template: str
    conditions: Dict[str, Any]
    priority: str = "normal"  # low, normal, high
    requires_manual_review: bool = False

@dataclass
class ActiveSequence:
    """Active follow-up sequence for a contact"""
    sequence_id: str
    contact_id: str
    sequence_type: SequenceType
    current_step: int
    started_date: datetime
    next_send_date: datetime
    completed_steps: List[int]
    paused: bool = False
    pause_reason: Optional[str] = None

class FollowUpSequenceManager:
    """Manages multi-touch email follow-up sequences"""
    
    def __init__(self, personalization_engine: PersonalizationEngine, response_generator: ResponseGenerator):
        self.personalization_engine = personalization_engine
        self.response_generator = response_generator
        self.active_sequences: Dict[str, ActiveSequence] = {}
        self.sequence_templates = self._initialize_sequence_templates()
        
    def _initialize_sequence_templates(self) -> Dict[SequenceType, List[SequenceStep]]:
        """Initialize follow-up sequence templates"""
        return {
            SequenceType.NOT_INTERESTED_NURTURE: [
                SequenceStep(
                    step_number=1,
                    delay_days=30,
                    template_key="not_interested_nurture_1",
                    subject_template="Quick industry insight for {company_name}",
                    conditions={"no_unsubscribe": True},
                    priority="low"
                ),
                SequenceStep(
                    step_number=2,
                    delay_days=60,
                    template_key="not_interested_nurture_2", 
                    subject_template="New feature that might interest you",
                    conditions={"no_unsubscribe": True},
                    priority="low"
                ),
                SequenceStep(
                    step_number=3,
                    delay_days=90,
                    template_key="not_interested_nurture_3",
                    subject_template="Quarterly check-in",
                    conditions={"no_unsubscribe": True},
                    priority="low"
                )
            ],
            
            SequenceType.MAYBE_INTERESTED_NURTURE: [
                SequenceStep(
                    step_number=1,
                    delay_days=3,
                    template_key="maybe_interested_follow_1",
                    subject_template="Following up on your questions",
                    conditions={},
                    priority="normal"
                ),
                SequenceStep(
                    step_number=2,
                    delay_days=7,
                    template_key="maybe_interested_follow_2",
                    subject_template="Thought you might find this helpful",
                    conditions={"no_response_to_step_1": True},
                    priority="normal"
                ),
                SequenceStep(
                    step_number=3,
                    delay_days=14,
                    template_key="maybe_interested_follow_3",
                    subject_template="Quick check-in about your needs",
                    conditions={"no_response_to_previous": True},
                    priority="normal"
                ),
                SequenceStep(
                    step_number=4,
                    delay_days=30,
                    template_key="maybe_interested_follow_4",
                    subject_template="Is now a better time?",
                    conditions={"no_response_to_previous": True},
                    priority="low"
                )
            ],
            
            SequenceType.INTERESTED_ACCELERATION: [
                SequenceStep(
                    step_number=1,
                    delay_days=1,
                    template_key="interested_immediate_follow",
                    subject_template="Next steps for {company_name}",
                    conditions={},
                    priority="high"
                ),
                SequenceStep(
                    step_number=2,
                    delay_days=3,
                    template_key="interested_follow_2",
                    subject_template="Scheduling our conversation",
                    conditions={"no_meeting_scheduled": True},
                    priority="high"
                ),
                SequenceStep(
                    step_number=3,
                    delay_days=7,
                    template_key="interested_follow_3",
                    subject_template="Don't let this opportunity slip away",
                    conditions={"no_meeting_scheduled": True},
                    priority="normal",
                    requires_manual_review=True
                )
            ],
            
            SequenceType.DEMO_FOLLOW_UP: [
                SequenceStep(
                    step_number=1,
                    delay_days=1,
                    template_key="demo_immediate_follow",
                    subject_template="Demo scheduling for {company_name}",
                    conditions={},
                    priority="high"
                ),
                SequenceStep(
                    step_number=2,
                    delay_days=3,
                    template_key="demo_follow_2",
                    subject_template="Demo options and availability",
                    conditions={"no_demo_scheduled": True},
                    priority="high"
                ),
                SequenceStep(
                    step_number=3,
                    delay_days=7,
                    template_key="demo_follow_3",
                    subject_template="Quick demo alternative",
                    conditions={"no_demo_scheduled": True},
                    priority="normal"
                )
            ],
            
            SequenceType.PRICING_FOLLOW_UP: [
                SequenceStep(
                    step_number=1,
                    delay_days=1,
                    template_key="pricing_immediate_follow",
                    subject_template="Pricing information for {company_name}",
                    conditions={},
                    priority="high"
                ),
                SequenceStep(
                    step_number=2,
                    delay_days=3,
                    template_key="pricing_follow_2",
                    subject_template="Custom pricing proposal",
                    conditions={"no_response_to_pricing": True},
                    priority="high"
                ),
                SequenceStep(
                    step_number=3,
                    delay_days=7,
                    template_key="pricing_follow_3",
                    subject_template="Questions about our pricing?",
                    conditions={"no_response_to_pricing": True},
                    priority="normal"
                )
            ],
            
            SequenceType.MEETING_FOLLOW_UP: [
                SequenceStep(
                    step_number=1,
                    delay_days=1,
                    template_key="meeting_confirmation",
                    subject_template="Confirming our meeting",
                    conditions={},
                    priority="high"
                ),
                SequenceStep(
                    step_number=2,
                    delay_days=1,  # Day of meeting
                    template_key="meeting_day_reminder",
                    subject_template="Looking forward to our call today",
                    conditions={"meeting_today": True},
                    priority="high"
                ),
                SequenceStep(
                    step_number=3,
                    delay_days=1,  # Day after meeting
                    template_key="meeting_follow_up",
                    subject_template="Thank you for your time yesterday",
                    conditions={"meeting_completed": True},
                    priority="high"
                )
            ]
        }
    
    def determine_sequence_type(
        self, 
        email: Email, 
        classification: EmailClassification,
        engagement_factors: List[str],
        contact_data: Dict[str, Any]
    ) -> Optional[SequenceType]:
        """Determine appropriate follow-up sequence type"""
        
        # Check for specific engagement types first
        if 'demo_request' in engagement_factors:
            return SequenceType.DEMO_FOLLOW_UP
        elif 'pricing_inquiry' in engagement_factors:
            return SequenceType.PRICING_FOLLOW_UP
        elif 'meeting_request' in engagement_factors:
            return SequenceType.MEETING_FOLLOW_UP
        
        # General classification-based sequences
        if classification == EmailClassification.INTERESTED:
            return SequenceType.INTERESTED_ACCELERATION
        elif classification == EmailClassification.MAYBE_INTERESTED:
            return SequenceType.MAYBE_INTERESTED_NURTURE
        elif classification == EmailClassification.NOT_INTERESTED:
            # Only nurture if not explicitly unsubscribed
            if 'unsubscribe' not in email.body.lower():
                return SequenceType.NOT_INTERESTED_NURTURE
        
        return None
    
    async def start_sequence(
        self, 
        contact: SalesforceContact,
        sequence_type: SequenceType,
        trigger_email: Email,
        context_data: Dict[str, Any]
    ) -> bool:
        """Start a new follow-up sequence"""
        try:
            # Check if contact already has an active sequence
            existing_sequence = self._get_active_sequence_for_contact(contact.id)
            if existing_sequence:
                # Pause existing sequence if new one has higher priority
                if self._should_replace_sequence(existing_sequence.sequence_type, sequence_type):
                    await self.pause_sequence(existing_sequence.sequence_id, "Replaced by higher priority sequence")
                else:
                    logger.info(f"Contact {contact.id} already has active sequence: {existing_sequence.sequence_type}")
                    return False
            
            # Create new sequence
            sequence_id = f"{contact.id}_{sequence_type.value}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            # Calculate first step send date
            first_step = self.sequence_templates[sequence_type][0]
            next_send_date = datetime.now() + timedelta(days=first_step.delay_days)
            
            active_sequence = ActiveSequence(
                sequence_id=sequence_id,
                contact_id=contact.id,
                sequence_type=sequence_type,
                current_step=0,
                started_date=datetime.now(),
                next_send_date=next_send_date,
                completed_steps=[]
            )
            
            self.active_sequences[sequence_id] = active_sequence
            
            logger.info(f"Started {sequence_type.value} sequence for contact {contact.id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to start sequence: {e}")
            return False
    
    def _get_active_sequence_for_contact(self, contact_id: str) -> Optional[ActiveSequence]:
        """Get active sequence for a contact"""
        for sequence in self.active_sequences.values():
            if sequence.contact_id == contact_id and not sequence.paused:
                return sequence
        return None
    
    def _should_replace_sequence(self, current_type: SequenceType, new_type: SequenceType) -> bool:
        """Determine if new sequence should replace current one"""
        priority_order = {
            SequenceType.MEETING_FOLLOW_UP: 1,
            SequenceType.DEMO_FOLLOW_UP: 2,
            SequenceType.PRICING_FOLLOW_UP: 3,
            SequenceType.INTERESTED_ACCELERATION: 4,
            SequenceType.MAYBE_INTERESTED_NURTURE: 5,
            SequenceType.NOT_INTERESTED_NURTURE: 6
        }
        
        return priority_order.get(new_type, 10) < priority_order.get(current_type, 10)
    
    async def process_due_sequences(self) -> List[Dict[str, Any]]:
        """Process all sequences that are due for next step"""
        due_sequences = []
        current_time = datetime.now()
        
        for sequence in self.active_sequences.values():
            if (not sequence.paused and 
                sequence.next_send_date <= current_time and
                sequence.current_step < len(self.sequence_templates[sequence.sequence_type])):
                
                result = await self._execute_sequence_step(sequence)
                due_sequences.append(result)
        
        return due_sequences
    
    async def _execute_sequence_step(self, sequence: ActiveSequence) -> Dict[str, Any]:
        """Execute the next step in a sequence"""
        try:
            sequence_steps = self.sequence_templates[sequence.sequence_type]
            current_step = sequence_steps[sequence.current_step]
            
            # Check step conditions
            if not await self._check_step_conditions(sequence, current_step):
                logger.info(f"Step conditions not met for sequence {sequence.sequence_id}")
                return await self._advance_to_next_step(sequence, skipped=True)
            
            # Get contact data for personalization
            contact_data = await self.personalization_engine.get_comprehensive_contact_data(
                SalesforceContact(id=sequence.contact_id, email="", first_name="", last_name="")
            )
            
            # Generate personalized email
            personalization_context = self.personalization_engine.generate_personalization_context(
                contact_data, None, None, None
            )
            
            variables = self.personalization_engine.generate_personalized_variables(personalization_context)
            
            # Create email content
            email_content = await self._generate_sequence_email(
                current_step, variables, sequence.sequence_type
            )
            
            # Send email (if not requires manual review)
            if current_step.requires_manual_review:
                logger.info(f"Step {current_step.step_number} requires manual review for sequence {sequence.sequence_id}")
                return {
                    'sequence_id': sequence.sequence_id,
                    'step': current_step.step_number,
                    'status': 'pending_review',
                    'email_content': email_content
                }
            else:
                # Send the email
                contact_email = contact_data.get('basic_info', {}).get('email', '')
                if contact_email:
                    sent = await self.response_generator.send_response(contact_email, email_content)
                    
                    if sent:
                        return await self._advance_to_next_step(sequence, sent=True)
                    else:
                        logger.error(f"Failed to send sequence email for {sequence.sequence_id}")
                        return {
                            'sequence_id': sequence.sequence_id,
                            'step': current_step.step_number,
                            'status': 'send_failed'
                        }
                else:
                    logger.error(f"No email address for contact {sequence.contact_id}")
                    return {
                        'sequence_id': sequence.sequence_id,
                        'step': current_step.step_number,
                        'status': 'no_email'
                    }
            
        except Exception as e:
            logger.error(f"Failed to execute sequence step: {e}")
            return {
                'sequence_id': sequence.sequence_id,
                'step': sequence.current_step,
                'status': 'error',
                'error': str(e)
            }
    
    async def _check_step_conditions(self, sequence: ActiveSequence, step: SequenceStep) -> bool:
        """Check if step conditions are met"""
        # This would typically check Salesforce for various conditions
        # For now, we'll implement basic logic
        
        conditions = step.conditions
        
        if not conditions:
            return True
        
        # Example condition checks (would be expanded with real Salesforce queries)
        if conditions.get('no_unsubscribe'):
            # Check if contact has unsubscribed (simplified)
            return True
        
        if conditions.get('no_response_to_step_1'):
            # Check if contact responded to previous step
            return True
        
        if conditions.get('no_meeting_scheduled'):
            # Check if meeting has been scheduled
            return True
        
        return True
    
    async def _generate_sequence_email(
        self, 
        step: SequenceStep, 
        variables: Dict[str, str],
        sequence_type: SequenceType
    ) -> Any:  # EmailResponse type
        """Generate email content for sequence step"""
        
        # Get template content
        template_content = self._get_template_content(step.template_key, sequence_type)
        
        # Apply variables to template
        subject = step.subject_template.format(**variables)
        body = template_content.format(**variables)
        
        # Create EmailResponse object (simplified)
        from .models import EmailResponse
        return EmailResponse(
            subject=subject,
            body=body,
            template_used=step.template_key,
            personalization_data=variables
        )
    
    def _get_template_content(self, template_key: str, sequence_type: SequenceType) -> str:
        """Get email template content"""
        # This would typically load from a template system
        # For now, return basic templates
        
        templates = {
            'not_interested_nurture_1': """
Hi {first_name},

I hope you're doing well. I know you mentioned you weren't interested in our solution right now, and I completely respect that.

I wanted to share a quick industry insight that might be relevant to {company_name} {industry_reference}. We've been seeing some interesting trends that could impact your business.

[Industry insight content would go here]

No need to respond - just thought you might find it useful.

Best regards,
Annie
""",
            
            'maybe_interested_follow_1': """
Hi {first_name},

Thanks for your response! I wanted to follow up on the questions you raised about our solution.

{relationship_reference}, I think there are a few key points that might address your concerns:

1. [Specific point based on their questions]
2. [Another relevant point]
3. [Third point]

{personalized_cta}

Best regards,
Annie
""",
            
            'interested_immediate_follow': """
Hi {first_name},

Thank you for expressing interest in our solution! I'm excited to help {company_name} achieve {relevant_value_prop}.

Based on your response, I think the next step would be to schedule a brief call to discuss your specific needs and show you exactly how we can help.

I have availability:
- Tomorrow at 2:00 PM or 4:00 PM
- Day after at 10:00 AM or 3:00 PM

Which works better for you?

Looking forward to our conversation!

Best regards,
Annie
""",
            
            'demo_immediate_follow': """
Hi {first_name},

Great to hear you're interested in seeing a demo! I'd love to show you exactly how our solution can benefit {company_name}.

I can prepare a customized demo that focuses on your specific use case {industry_reference}. The demo typically takes about 30 minutes and I can tailor it to show the features most relevant to your needs.

When would be a good time for you? I have these slots available:
- [Time slots]

Please let me know what works best for your schedule.

Best regards,
Annie
""",
            
            'pricing_immediate_follow': """
Hi {first_name},

Thank you for your interest in our pricing! I'd be happy to provide you with detailed pricing information tailored to {company_name}'s needs.

Our pricing is based on several factors including company size, specific features needed, and implementation requirements. To give you the most accurate quote, I'd like to understand:

1. What's your current team size?
2. Which features are most important to you?
3. Do you have any specific integration requirements?

I can also schedule a brief call to discuss your needs and provide a custom proposal. Would that be helpful?

Best regards,
Annie
"""
        }
        
        return templates.get(template_key, "Default template content for {template_key}")
    
    async def _advance_to_next_step(self, sequence: ActiveSequence, sent: bool = False, skipped: bool = False) -> Dict[str, Any]:
        """Advance sequence to next step"""
        # Mark current step as completed
        if not skipped:
            sequence.completed_steps.append(sequence.current_step)
        
        # Move to next step
        sequence.current_step += 1
        
        # Check if sequence is complete
        if sequence.current_step >= len(self.sequence_templates[sequence.sequence_type]):
            sequence.paused = True
            sequence.pause_reason = "Sequence completed"
            
            return {
                'sequence_id': sequence.sequence_id,
                'status': 'completed',
                'total_steps': len(sequence.completed_steps)
            }
        
        # Schedule next step
        next_step = self.sequence_templates[sequence.sequence_type][sequence.current_step]
        sequence.next_send_date = datetime.now() + timedelta(days=next_step.delay_days)
        
        return {
            'sequence_id': sequence.sequence_id,
            'step': sequence.current_step - 1,
            'status': 'sent' if sent else 'skipped',
            'next_step_date': sequence.next_send_date.isoformat()
        }
    
    async def pause_sequence(self, sequence_id: str, reason: str) -> bool:
        """Pause a sequence"""
        if sequence_id in self.active_sequences:
            self.active_sequences[sequence_id].paused = True
            self.active_sequences[sequence_id].pause_reason = reason
            logger.info(f"Paused sequence {sequence_id}: {reason}")
            return True
        return False
    
    async def resume_sequence(self, sequence_id: str) -> bool:
        """Resume a paused sequence"""
        if sequence_id in self.active_sequences:
            sequence = self.active_sequences[sequence_id]
            sequence.paused = False
            sequence.pause_reason = None
            
            # Recalculate next send date
            if sequence.current_step < len(self.sequence_templates[sequence.sequence_type]):
                current_step = self.sequence_templates[sequence.sequence_type][sequence.current_step]
                sequence.next_send_date = datetime.now() + timedelta(days=current_step.delay_days)
            
            logger.info(f"Resumed sequence {sequence_id}")
            return True
        return False
    
    def get_sequence_statistics(self) -> Dict[str, Any]:
        """Get statistics about active sequences"""
        total_sequences = len(self.active_sequences)
        active_sequences = sum(1 for s in self.active_sequences.values() if not s.paused)
        paused_sequences = total_sequences - active_sequences
        
        # Count by type
        type_counts = {}
        for sequence in self.active_sequences.values():
            seq_type = sequence.sequence_type.value
            type_counts[seq_type] = type_counts.get(seq_type, 0) + 1
        
        # Due sequences
        current_time = datetime.now()
        due_sequences = sum(
            1 for s in self.active_sequences.values() 
            if not s.paused and s.next_send_date <= current_time
        )
        
        return {
            'total_sequences': total_sequences,
            'active_sequences': active_sequences,
            'paused_sequences': paused_sequences,
            'due_sequences': due_sequences,
            'sequences_by_type': type_counts,
            'completion_rate': self._calculate_completion_rate()
        }
    
    def _calculate_completion_rate(self) -> float:
        """Calculate sequence completion rate"""
        if not self.active_sequences:
            return 0.0
        
        completed = sum(
            1 for s in self.active_sequences.values() 
            if s.pause_reason == "Sequence completed"
        )
        
        return completed / len(self.active_sequences)
