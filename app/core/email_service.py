from typing import List, Optional
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import asyncio
from pathlib import Path
import logging

from ..core.config import settings

logger = logging.getLogger(__name__)


class EmailService:
    """Service for sending emails via SMTP"""
    
    def __init__(self):
        self.smtp_host = settings.SMTP_HOST
        self.smtp_port = settings.SMTP_PORT
        self.smtp_user = settings.SMTP_USER
        self.smtp_password = settings.SMTP_PASSWORD
        self.from_email = settings.FROM_EMAIL
        self.from_name = settings.FROM_NAME or "LMS Platform"
    
    def _create_message(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        text_content: Optional[str] = None
    ) -> MIMEMultipart:
        """Create email message"""
        message = MIMEMultipart("alternative")
        message["From"] = f"{self.from_name} <{self.from_email}>"
        message["To"] = to_email
        message["Subject"] = subject
        
        # Add text version if provided
        if text_content:
            part1 = MIMEText(text_content, "plain")
            message.attach(part1)
        
        # Add HTML version
        part2 = MIMEText(html_content, "html")
        message.attach(part2)
        
        return message
    
    async def send_email_async(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        text_content: Optional[str] = None
    ) -> bool:
        """Send email asynchronously"""
        try:
            # Run blocking SMTP operation in thread pool
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                self._send_email_sync,
                to_email,
                subject,
                html_content,
                text_content
            )
            logger.info(f"Email sent successfully to {to_email}")
            return True
        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {str(e)}")
            return False
    
    def _send_email_sync(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        text_content: Optional[str] = None
    ):
        """Synchronous email sending (called in thread pool)"""
        message = self._create_message(to_email, subject, html_content, text_content)
        
        # Connect to SMTP server and send
        with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
            server.starttls()  # Enable TLS
            server.login(self.smtp_user, self.smtp_password)
            server.send_message(message)
    
    async def send_welcome_email(self, to_email: str, full_name: str) -> bool:
        """Send welcome email after registration"""
        subject = f"Welcome to {self.from_name}! 🎉"
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    line-height: 1.6;
                    color: #333;
                    max-width: 600px;
                    margin: 0 auto;
                    padding: 20px;
                }}
                .header {{
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    padding: 30px;
                    text-align: center;
                    border-radius: 10px 10px 0 0;
                }}
                .content {{
                    background: #f9f9f9;
                    padding: 30px;
                    border-radius: 0 0 10px 10px;
                }}
                .button {{
                    display: inline-block;
                    padding: 12px 30px;
                    background: #667eea;
                    color: white;
                    text-decoration: none;
                    border-radius: 5px;
                    margin: 20px 0;
                }}
                .features {{
                    background: white;
                    padding: 20px;
                    margin: 20px 0;
                    border-radius: 8px;
                    border-left: 4px solid #667eea;
                }}
                .footer {{
                    text-align: center;
                    color: #666;
                    margin-top: 30px;
                    padding-top: 20px;
                    border-top: 1px solid #ddd;
                    font-size: 12px;
                }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>Welcome to LMS! 🎓</h1>
            </div>
            <div class="content">
                <h2>Hi {full_name},</h2>
                <p>Thank you for joining our learning platform! We're excited to have you as part of our community.</p>
                
                <p>Your account has been successfully created and you can now access thousands of courses to enhance your skills and knowledge.</p>
                
                <div class="features">
                    <h3>What's Next?</h3>
                    <ul>
                        <li>📚 Browse our extensive course catalog</li>
                        <li>🎯 Set your learning goals</li>
                        <li>💡 Enroll in courses that interest you</li>
                        <li>🏆 Earn certificates upon completion</li>
                        <li>🤝 Connect with fellow learners</li>
                    </ul>
                </div>
                
                <div style="text-align: center;">
                    <a href="{settings.FRONTEND_URL}/courses" class="button">Explore Courses</a>
                </div>
                
                <p>If you have any questions or need assistance, our support team is always here to help.</p>
                
                <p>Happy Learning!<br>
                The LMS Team</p>
            </div>
            <div class="footer">
                <p>You received this email because you registered at {self.from_name}</p>
                <p>&copy; 2025 LMS Platform. All rights reserved.</p>
            </div>
        </body>
        </html>
        """
        
        text_content = f"""
        Welcome to {self.from_name}!
        
        Hi {full_name},
        
        Thank you for joining our learning platform! We're excited to have you as part of our community.
        
        Your account has been successfully created and you can now access thousands of courses to enhance your skills and knowledge.
        
        What's Next?
        - Browse our extensive course catalog
        - Set your learning goals
        - Enroll in courses that interest you
        - Earn certificates upon completion
        - Connect with fellow learners
        
        Visit {settings.FRONTEND_URL}/courses to get started!
        
        If you have any questions or need assistance, our support team is always here to help.
        
        Happy Learning!
        The LMS Team
        """
        
        return await self.send_email_async(to_email, subject, html_content, text_content)
    
    async def send_password_reset_email(self, to_email: str, full_name: str, reset_token: str) -> bool:
        """Send password reset email"""
        reset_link = f"{settings.FRONTEND_URL}/reset-password?token={reset_token}"
        subject = "Reset Your Password - LMS"
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    line-height: 1.6;
                    color: #333;
                    max-width: 600px;
                    margin: 0 auto;
                    padding: 20px;
                }}
                .header {{
                    background: #667eea;
                    color: white;
                    padding: 30px;
                    text-align: center;
                    border-radius: 10px 10px 0 0;
                }}
                .content {{
                    background: #f9f9f9;
                    padding: 30px;
                    border-radius: 0 0 10px 10px;
                }}
                .button {{
                    display: inline-block;
                    padding: 12px 30px;
                    background: #667eea;
                    color: white;
                    text-decoration: none;
                    border-radius: 5px;
                    margin: 20px 0;
                }}
                .warning {{
                    background: #fff3cd;
                    border: 1px solid #ffc107;
                    padding: 15px;
                    border-radius: 5px;
                    margin: 20px 0;
                }}
                .footer {{
                    text-align: center;
                    color: #666;
                    margin-top: 30px;
                    padding-top: 20px;
                    border-top: 1px solid #ddd;
                    font-size: 12px;
                }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>Password Reset Request 🔐</h1>
            </div>
            <div class="content">
                <h2>Hi {full_name},</h2>
                <p>We received a request to reset your password for your LMS account.</p>
                
                <p>Click the button below to reset your password:</p>
                
                <div style="text-align: center;">
                    <a href="{reset_link}" class="button">Reset Password</a>
                </div>
                
                <p>Or copy and paste this link into your browser:</p>
                <p style="word-break: break-all; color: #667eea;">{reset_link}</p>
                
                <div class="warning">
                    <strong>⚠️ Security Notice:</strong>
                    <ul>
                        <li>This link will expire in 1 hour</li>
                        <li>If you didn't request this reset, please ignore this email</li>
                        <li>Never share this link with anyone</li>
                    </ul>
                </div>
                
                <p>If you have any concerns, please contact our support team immediately.</p>
                
                <p>Best regards,<br>
                The LMS Team</p>
            </div>
            <div class="footer">
                <p>&copy; 2025 LMS Platform. All rights reserved.</p>
            </div>
        </body>
        </html>
        """
        
        text_content = f"""
        Password Reset Request
        
        Hi {full_name},
        
        We received a request to reset your password for your LMS account.
        
        Click this link to reset your password:
        {reset_link}
        
        Security Notice:
        - This link will expire in 1 hour
        - If you didn't request this reset, please ignore this email
        - Never share this link with anyone
        
        If you have any concerns, please contact our support team immediately.
        
        Best regards,
        The LMS Team
        """
        
        return await self.send_email_async(to_email, subject, html_content, text_content)
    
    async def send_enrollment_confirmation_email(
        self, 
        to_email: str, 
        full_name: str, 
        course_title: str
    ) -> bool:
        """Send enrollment confirmation email"""
        subject = f"Enrollment Confirmed: {course_title}"
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    line-height: 1.6;
                    color: #333;
                    max-width: 600px;
                    margin: 0 auto;
                    padding: 20px;
                }}
                .header {{
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    padding: 30px;
                    text-align: center;
                    border-radius: 10px 10px 0 0;
                }}
                .content {{
                    background: #f9f9f9;
                    padding: 30px;
                    border-radius: 0 0 10px 10px;
                }}
                .course-box {{
                    background: white;
                    padding: 20px;
                    margin: 20px 0;
                    border-radius: 8px;
                    border-left: 4px solid #667eea;
                }}
                .button {{
                    display: inline-block;
                    padding: 12px 30px;
                    background: #667eea;
                    color: white;
                    text-decoration: none;
                    border-radius: 5px;
                    margin: 20px 0;
                }}
                .footer {{
                    text-align: center;
                    color: #666;
                    margin-top: 30px;
                    padding-top: 20px;
                    border-top: 1px solid #ddd;
                    font-size: 12px;
                }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>🎉 Enrollment Confirmed!</h1>
            </div>
            <div class="content">
                <h2>Hi {full_name},</h2>
                <p>Congratulations! You've successfully enrolled in:</p>
                
                <div class="course-box">
                    <h3>{course_title}</h3>
                </div>
                
                <p>You can now access all course materials and start learning right away!</p>
                
                <div style="text-align: center;">
                    <a href="{settings.FRONTEND_URL}/dashboard" class="button">Go to Dashboard</a>
                </div>
                
                <p>Happy Learning!<br>
                The LMS Team</p>
            </div>
            <div class="footer">
                <p>&copy; 2025 LMS Platform. All rights reserved.</p>
            </div>
        </body>
        </html>
        """
        
        text_content = f"""
        Enrollment Confirmed!
        
        Hi {full_name},
        
        Congratulations! You've successfully enrolled in:
        {course_title}
        
        You can now access all course materials and start learning right away!
        
        Visit {settings.FRONTEND_URL}/dashboard to get started.
        
        Happy Learning!
        The LMS Team
        """
        
        return await self.send_email_async(to_email, subject, html_content, text_content)


# Create global email service instance
email_service = EmailService()
