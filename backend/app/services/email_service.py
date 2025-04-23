# app/services/email_service.py
import os
import boto3
from botocore.exceptions import ClientError
from fastapi import BackgroundTasks
from typing import List, Optional
import logging

logger = logging.getLogger(__name__)

class EmailService:
    def __init__(self):
        """
        Initialize the Email Service using AWS SES
        """
        self.sender = os.getenv("EMAIL_SENDER", "support@pulsescout.com")
        self.ses_client = boto3.client(
            'ses',
            region_name=os.getenv("AWS_REGION", "us-east-1"),
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY")
        )
        self.base_url = os.getenv("FRONTEND_URL", "http://localhost:5173")
    
    async def send_verification_email(self, email: str, token: str):
        """
        Send a verification email to a user
        """
        verification_link = f"{self.base_url}/verify-email?token={token}"
        subject = "Verify your PulseScout account"
        
        html_content = f"""
        <html>
            <head>
                <style>
                    body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                    .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                    .logo {{ text-align: center; margin-bottom: 20px; }}
                    .button {{ background-color: #4CAF50; color: white; padding: 12px 24px; 
                              text-decoration: none; border-radius: 4px; display: inline-block; }}
                    .footer {{ margin-top: 30px; font-size: 12px; color: #777; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="logo">
                        <h1>PulseScout</h1>
                    </div>
                    <p>Hello,</p>
                    <p>Thank you for registering with PulseScout! Please verify your email address by clicking the button below:</p>
                    <p style="text-align: center;">
                        <a href="{verification_link}" class="button">Verify Email</a>
                    </p>
                    <p>Or copy and paste this link into your browser:</p>
                    <p>{verification_link}</p>
                    <p>This link will expire in 24 hours.</p>
                    <p>If you didn't create an account with PulseScout, please ignore this email.</p>
                    <div class="footer">
                        <p>PulseScout - AI-Enhanced Lead Discovery</p>
                    </div>
                </div>
            </body>
        </html>
        """
        
        text_content = f"""
        Hello,

        Thank you for registering with PulseScout! Please verify your email address by clicking the link below:

        {verification_link}

        This link will expire in 24 hours.

        If you didn't create an account with PulseScout, please ignore this email.

        PulseScout - AI-Enhanced Lead Discovery
        """
        
        await self._send_email(email, subject, html_content, text_content)
    
    async def send_password_reset_email(self, email: str, token: str):
        """
        Send a password reset email to a user
        """
        reset_link = f"{self.base_url}/reset-password?token={token}"
        subject = "Reset your PulseScout password"
        
        html_content = f"""
        <html>
            <head>
                <style>
                    body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                    .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
                    .logo {{ text-align: center; margin-bottom: 20px; }}
                    .button {{ background-color: #4CAF50; color: white; padding: 12px 24px; 
                              text-decoration: none; border-radius: 4px; display: inline-block; }}
                    .footer {{ margin-top: 30px; font-size: 12px; color: #777; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="logo">
                        <h1>PulseScout</h1>
                    </div>
                    <p>Hello,</p>
                    <p>We received a request to reset your PulseScout password. Click the button below to reset it:</p>
                    <p style="text-align: center;">
                        <a href="{reset_link}" class="button">Reset Password</a>
                    </p>
                    <p>Or copy and paste this link into your browser:</p>
                    <p>{reset_link}</p>
                    <p>This link will expire in 1 hour.</p>
                    <p>If you didn't request a password reset, please ignore this email or contact support if you have concerns.</p>
                    <div class="footer">
                        <p>PulseScout - AI-Enhanced Lead Discovery</p>
                    </div>
                </div>
            </body>
        </html>
        """
        
        text_content = f"""
        Hello,

        We received a request to reset your PulseScout password. Click the link below to reset it:

        {reset_link}

        This link will expire in 1 hour.

        If you didn't request a password reset, please ignore this email or contact support if you have concerns.

        PulseScout - AI-Enhanced Lead Discovery
        """
        
        await self._send_email(email, subject, html_content, text_content)
    
    async def _send_email(self, recipient: str, subject: str, html_content: str, text_content: str):
        """
        Send an email using AWS SES
        """
        try:
            response = self.ses_client.send_email(
                Source=self.sender,
                Destination={
                    'ToAddresses': [recipient]
                },
                Message={
                    'Subject': {
                        'Data': subject
                    },
                    'Body': {
                        'Text': {
                            'Data': text_content
                        },
                        'Html': {
                            'Data': html_content
                        }
                    }
                }
            )
            logger.info(f"Email sent! Message ID: {response['MessageId']}")
            return True
        except ClientError as e:
            logger.error(f"Error sending email: {e.response['Error']['Message']}")
            return False