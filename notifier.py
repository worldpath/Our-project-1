#!/usr/bin/env python3
"""
Notification system for crypto bot alerts
"""

import os
import smtplib
import requests
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

def notify_email(subject: str, message: str):
    """Send email notification"""
    try:
        smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
        smtp_port = int(os.getenv("SMTP_PORT", "587"))
        email_user = os.getenv("EMAIL_USER", "")
        email_pass = os.getenv("EMAIL_PASS", "")
        email_to = os.getenv("EMAIL_TO", "")
        
        if not all([email_user, email_pass, email_to]):
            logger.warning("Email credentials not configured")
            return False
            
        msg = MIMEMultipart()
        msg['From'] = email_user
        msg['To'] = email_to
        msg['Subject'] = f"[Crypto Bot] {subject}"
        
        body = f"{message}\n\nTime: {datetime.now().isoformat()}"
        msg.attach(MIMEText(body, 'plain'))
        
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(email_user, email_pass)
        server.send_message(msg)
        server.quit()
        
        return True
        
    except Exception as e:
        logger.error(f"Email notification failed: {e}")
        return False

def notify_telegram(message: str):
    """Send Telegram notification"""
    try:
        bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "")
        chat_id = os.getenv("TELEGRAM_CHAT_ID", "")
        
        if not all([bot_token, chat_id]):
            logger.warning("Telegram credentials not configured")
            return False
            
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        data = {
            'chat_id': chat_id,
            'text': f"🤖 {message}\n\n📅 {datetime.now().isoformat()}",
            'parse_mode': 'HTML'
        }
        
        response = requests.post(url, data=data, timeout=10)
        return response.status_code == 200
        
    except Exception as e:
        logger.error(f"Telegram notification failed: {e}")
        return False