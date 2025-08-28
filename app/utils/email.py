import smtplib
import secrets
import hashlib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from typing import Optional
import logging

logger = logging.getLogger(__name__)

class EmailService:
    def __init__(self, smtp_server: str, smtp_port: int, smtp_username: str, smtp_password: str, from_email: str):
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.smtp_username = smtp_username
        self.smtp_password = smtp_password
        self.from_email = from_email
    
    @staticmethod
    def generate_verification_token() -> str:
        """Generate a secure random token for email verification"""
        return secrets.token_urlsafe(32)
    
    @staticmethod
    def get_token_expiry_time(hours: int = 24) -> str:
        """Get expiry time for verification token (default 24 hours)"""
        expiry_time = datetime.utcnow() + timedelta(hours=hours)
        return expiry_time.isoformat()
    
    def send_verification_email(self, to_email: str, username: str, verification_token: str, base_url: str) -> bool:
        """
        Send email verification email to user
        
        Args:
            to_email (str): Recipient email address
            username (str): Username of the user
            verification_token (str): Verification token
            base_url (str): Base URL of the application
            
        Returns:
            bool: True if email sent successfully, False otherwise
        """
        try:
            # Create verification URL
            verification_url = f"{base_url}/verify-email?token={verification_token}"
            
            # Email content
            subject = "Verify Your Email Address"
            
            html_body = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <title>Email Verification</title>
                <style>
                    body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                    .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                    .header {{ background-color: #007bff; color: white; padding: 20px; text-align: center; }}
                    .content {{ padding: 20px; background-color: #f9f9f9; }}
                    .button {{ display: inline-block; background-color: #007bff; color: white !important; padding: 12px 24px; text-decoration: none; border-radius: 4px; margin: 20px 0; }}
                    .footer {{ text-align: center; color: #666; font-size: 12px; margin-top: 20px; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>Welcome to Xyphera Systems</h1>
                    </div>
                    <div class="content">
                        <h2>Hello {username},</h2>
                        <p>Thank you for registering with us! To complete your registration, please verify your email address by clicking the button below:</p>
                        
                        <div style="text-align: center;">
                            <a href="{verification_url}" class="button">Verify Email Address</a>
                        </div>
                        
                        <p>Or copy and paste this link into your browser:</p>
                        <p style="word-break: break-all; background-color: #e9ecef; padding: 10px; border-radius: 4px;">{verification_url}</p>
                        
                        <p><strong>Important:</strong> This verification link will expire in 24 hours and can only be used once.</p>
                        
                        <p>If you didn't create this account, please ignore this email.</p>
                    </div>
                    <div class="footer">
                        <p>This email was sent automatically. Please do not reply to this email.</p>
                    </div>
                </div>
            </body>
            </html>
            """
            
            text_body = f"""
            Hello {username},
            
            Thank you for registering with us! To complete your registration, please verify your email address by visiting this link:
            
            {verification_url}
            
            Important: This verification link will expire in 24 hours and can only be used once.
            
            If you didn't create this account, please ignore this email.
            
            This email was sent automatically. Please do not reply to this email.
            """
            
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = self.from_email
            msg['To'] = to_email
            
            # Add both text and HTML parts
            text_part = MIMEText(text_body, 'plain')
            html_part = MIMEText(html_body, 'html')
            
            msg.attach(text_part)
            msg.attach(html_part)
            
            # Send email
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_username, self.smtp_password)
                server.send_message(msg)
            
            logger.info(f"Verification email sent successfully to {to_email}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send verification email to {to_email}: {str(e)}")
            return False
    
    def send_verification_success_email(self, to_email: str, username: str) -> bool:
        """
        Send confirmation email after successful verification
        
        Args:
            to_email (str): Recipient email address
            username (str): Username of the user
            
        Returns:
            bool: True if email sent successfully, False otherwise
        """
        try:
            subject = "Email Verification Successful"
            
            html_body = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <title>Email Verification Successful</title>
                <style>
                    body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                    .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                    .header {{ background-color: #28a745; color: white; padding: 20px; text-align: center; }}
                    .content {{ padding: 20px; background-color: #f9f9f9; }}
                    .success-icon {{ font-size: 48px; color: #28a745; text-align: center; margin: 20px 0; }}
                    .footer {{ text-align: center; color: #666; font-size: 12px; margin-top: 20px; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>Email Verified Successfully!</h1>
                    </div>
                    <div class="content">
                        <div class="success-icon">✓</div>
                        <h2>Hello {username},</h2>
                        <p>Great news! Your email address has been successfully verified.</p>
                        <p>You can now log in to your account and start using our platform.</p>
                        <p>Thank you for joining us!</p>
                    </div>
                    <div class="footer">
                        <p>This email was sent automatically. Please do not reply to this email.</p>
                    </div>
                </div>
            </body>
            </html>
            """
            
            text_body = f"""
            Hello {username},
            
            Great news! Your email address has been successfully verified.
            
            You can now log in to your account and start using our platform.
            
            Thank you for joining us!
            
            This email was sent automatically. Please do not reply to this email.
            """
            
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = self.from_email
            msg['To'] = to_email
            
            # Add both text and HTML parts
            text_part = MIMEText(text_body, 'plain')
            html_part = MIMEText(html_body, 'html')
            
            msg.attach(text_part)
            msg.attach(html_part)
            
            # Send email
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_username, self.smtp_password)
                server.send_message(msg)
            
            logger.info(f"Verification success email sent to {to_email}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send verification success email to {to_email}: {str(e)}")
            return False