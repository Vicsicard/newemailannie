"""
AI-powered response generation service
"""

import logging
from typing import Optional, Dict, Any
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from jinja2 import Template
import openai
import anthropic

from .config import settings
from .models import Email, ClassificationResult, EmailResponse, SalesforceContact, EmailClassification
from .ai_classifier import AIClassifier

logger = logging.getLogger(__name__)

class ResponseGenerator:
    """Generate and send personalized email responses"""
    
    def __init__(self, ai_classifier: AIClassifier):
        self.ai_classifier = ai_classifier
        self.templates = self._load_templates()
        
        # Initialize AI client for response generation
        if settings.AI_PROVIDER == "openai":
            self.ai_client = openai.AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        elif settings.AI_PROVIDER == "anthropic":
            self.ai_client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
    
    def _load_templates(self) -> Dict[str, str]:
        """Load email response templates"""
        return {
            "maybe_interested_response": """
Hi {{ first_name or "there" }},

Thank you for your response to our recent outreach. I understand you might need more information to make a decision.

{% if specific_question %}
Regarding your question about {{ specific_question }}, I'd be happy to provide more details.
{% endif %}

I'd love to schedule a brief 15-minute call to discuss how we can help {{ company or "your business" }} achieve {{ relevant_benefit }}. 

Would you be available for a quick call this week or next?

Best regards,
{{ sender_name }}
{{ sender_title }}
{{ sender_company }}
{{ sender_phone }}
""",
            
            "interested_response": """
Hi {{ first_name or "there" }},

Thank you for your interest! I'm excited to learn more about {{ company or "your business" }} and how we can help.

{% if mentioned_pricing %}
I'll prepare some pricing information tailored to your needs.
{% endif %}

{% if mentioned_demo %}
I'd be happy to show you a personalized demo of our solution.
{% endif %}

I'd like to schedule a call at your earliest convenience to discuss your specific requirements and show you exactly how we can help.

Are you available for a 30-minute call this week? I have openings on:
- Tuesday at 2:00 PM or 4:00 PM
- Wednesday at 10:00 AM or 3:00 PM
- Thursday at 1:00 PM or 5:00 PM

Please let me know what works best for you, or suggest an alternative time.

Looking forward to speaking with you!

Best regards,
{{ sender_name }}
{{ sender_title }}
{{ sender_company }}
{{ sender_phone }}
{{ sender_email }}
""",
            
            "not_interested_response": """
Hi {{ first_name or "there" }},

Thank you for taking the time to respond. I completely understand that our solution may not be the right fit for {{ company or "your business" }} at this time.

I'll make sure you're removed from our current campaign sequence.

If your needs change in the future, please don't hesitate to reach out.

Best regards,
{{ sender_name }}
{{ sender_company }}
"""
        }
    
    def get_response_prompt(self, email: Email, classification: ClassificationResult, contact: Optional[SalesforceContact]) -> str:
        """Generate prompt for AI response generation"""
        return f"""
You are a professional sales representative responding to a campaign email reply. Generate a personalized, professional response.

ORIGINAL EMAIL:
Subject: {email.subject}
From: {email.sender}
Body: {email.body}

CLASSIFICATION: {classification.classification}
CONFIDENCE: {classification.confidence}
REASONING: {classification.reasoning}

CONTACT INFO:
Name: {contact.first_name if contact else "Unknown"} {contact.last_name if contact else ""}
Company: {contact.company if contact else "Unknown"}
Email: {email.sender}

RESPONSE REQUIREMENTS:
1. Be professional, friendly, and personalized
2. Reference specific points from their email when relevant
3. Match the tone and interest level of their response
4. Include a clear call-to-action appropriate for their interest level
5. Keep it concise (under 200 words)

For "Maybe Interested": Focus on providing value and building trust
For "Interested": Be enthusiastic and suggest next steps (call, demo, meeting)
For "Not Interested": Be gracious and professional, confirm removal from campaigns

Generate a response email with:
- Subject line (keep it conversational and relevant)
- Email body (professional but personable)
- Suggested next steps if applicable

Respond in JSON format:
{{
    "subject": "Response subject line",
    "body": "Email body text",
    "template_used": "classification_based_template",
    "personalization_data": {{
        "key_points_addressed": ["point1", "point2"],
        "tone": "professional/friendly/enthusiastic",
        "next_steps": "suggested action"
    }}
}}
"""

    async def generate_response_with_ai(
        self, 
        email: Email, 
        classification: ClassificationResult, 
        contact: Optional[SalesforceContact]
    ) -> EmailResponse:
        """Generate response using AI"""
        try:
            prompt = self.get_response_prompt(email, classification, contact)
            
            if settings.AI_PROVIDER == "openai":
                response = await self.ai_client.chat.completions.create(
                    model="gpt-4",
                    messages=[
                        {
                            "role": "system",
                            "content": "You are a professional sales representative. Always respond with valid JSON."
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    temperature=0.3,
                    max_tokens=800
                )
                result_text = response.choices[0].message.content
                
            elif settings.AI_PROVIDER == "anthropic":
                response = await self.ai_client.messages.create(
                    model="claude-3-sonnet-20240229",
                    max_tokens=800,
                    temperature=0.3,
                    messages=[
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ]
                )
                result_text = response.content[0].text
            
            # Parse JSON response
            import json
            result_data = json.loads(result_text)
            
            return EmailResponse(
                subject=result_data["subject"],
                body=result_data["body"],
                template_used=result_data.get("template_used", "ai_generated"),
                personalization_data=result_data.get("personalization_data", {})
            )
            
        except Exception as e:
            logger.error(f"AI response generation failed: {e}")
            return self.generate_template_response(email, classification, contact)
    
    def generate_template_response(
        self, 
        email: Email, 
        classification: ClassificationResult, 
        contact: Optional[SalesforceContact]
    ) -> EmailResponse:
        """Generate response using templates (fallback)"""
        try:
            # Select template based on classification
            template_key = {
                EmailClassification.MAYBE_INTERESTED: "maybe_interested_response",
                EmailClassification.INTERESTED: "interested_response",
                EmailClassification.NOT_INTERESTED: "not_interested_response"
            }.get(classification.classification, "maybe_interested_response")
            
            template_content = self.templates.get(template_key, self.templates["maybe_interested_response"])
            template = Template(template_content)
            
            # Prepare template variables
            template_vars = {
                "first_name": contact.first_name if contact else None,
                "last_name": contact.last_name if contact else None,
                "company": contact.company if contact else None,
                "sender_name": "Annie",  # Customize as needed
                "sender_title": "Sales Representative",
                "sender_company": "Your Company",
                "sender_phone": "(555) 123-4567",
                "sender_email": settings.EMAIL_ADDRESS,
                "relevant_benefit": "your business goals",
                "specific_question": self._extract_questions(email.body),
                "mentioned_pricing": "pricing" in email.body.lower() or "cost" in email.body.lower(),
                "mentioned_demo": "demo" in email.body.lower() or "demonstration" in email.body.lower()
            }
            
            body = template.render(**template_vars)
            
            # Generate subject line
            subject_prefix = "Re: " if not email.subject.startswith("Re:") else ""
            subject = f"{subject_prefix}{email.subject}"
            
            return EmailResponse(
                subject=subject,
                body=body,
                template_used=template_key,
                personalization_data=template_vars
            )
            
        except Exception as e:
            logger.error(f"Template response generation failed: {e}")
            # Ultimate fallback
            return EmailResponse(
                subject=f"Re: {email.subject}",
                body=f"Hi {contact.first_name if contact and contact.first_name else 'there'},\n\nThank you for your response. I'll follow up with you shortly.\n\nBest regards,\nAnnie",
                template_used="fallback",
                personalization_data={}
            )
    
    def _extract_questions(self, email_body: str) -> Optional[str]:
        """Extract questions from email body"""
        sentences = email_body.split('.')
        questions = [s.strip() for s in sentences if '?' in s]
        return questions[0] if questions else None
    
    async def generate_response(
        self, 
        email: Email, 
        classification: ClassificationResult, 
        contact: Optional[SalesforceContact]
    ) -> EmailResponse:
        """Main response generation method"""
        logger.info(f"Generating response for {classification.classification} email from {email.sender}")
        
        try:
            # Use AI for personalized responses, templates as fallback
            if classification.confidence > 0.7:
                response = await self.generate_response_with_ai(email, classification, contact)
            else:
                response = self.generate_template_response(email, classification, contact)
            
            logger.info(f"Response generated using {response.template_used}")
            return response
            
        except Exception as e:
            logger.error(f"Response generation failed: {e}")
            return self.generate_template_response(email, classification, contact)
    
    async def send_response(self, recipient_email: str, response: EmailResponse) -> bool:
        """Send email response"""
        try:
            # Create email message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = response.subject
            msg['From'] = settings.SMTP_USERNAME
            msg['To'] = recipient_email
            
            # Add text body
            text_part = MIMEText(response.body, 'plain')
            msg.attach(text_part)
            
            # Add HTML body if available
            if response.html_body:
                html_part = MIMEText(response.html_body, 'html')
                msg.attach(html_part)
            
            # Send email
            with smtplib.SMTP(settings.SMTP_SERVER, settings.SMTP_PORT) as server:
                server.starttls()
                server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
                server.send_message(msg)
            
            logger.info(f"Response sent to {recipient_email}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send response to {recipient_email}: {e}")
            return False
    
    def should_send_response(self, classification: ClassificationResult) -> bool:
        """Determine if a response should be sent based on classification"""
        # Don't send responses to "Not Interested" unless it's a polite acknowledgment
        if classification.classification == EmailClassification.NOT_INTERESTED:
            return False  # Could be configurable
        
        # Send responses to Maybe and Interested
        return classification.classification in [
            EmailClassification.MAYBE_INTERESTED,
            EmailClassification.INTERESTED
        ]
