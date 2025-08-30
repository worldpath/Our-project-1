#!/usr/bin/env python3
"""
Test Email Notifications System
"""

import os
from dotenv import load_dotenv
from notifier import notify_email

# Load environment variables
load_dotenv()

def test_email_system():
    """Test the email notification system"""
    
    print("📧 TESTING EMAIL NOTIFICATION SYSTEM")
    print("=" * 40)
    
    # Check credentials
    email_user = os.getenv('EMAIL_USER')
    email_pass = os.getenv('EMAIL_PASS')
    email_to = os.getenv('EMAIL_TO')
    
    print(f"Email From: {email_user}")
    print(f"Email To: {email_to}")
    print(f"Password: {'*' * len(email_pass) if email_pass else 'Not set'}")
    print()
    
    if not all([email_user, email_pass, email_to]):
        print("❌ Missing email configuration!")
        return False
    
    # Send test email
    print("📤 Sending test notification email...")
    
    subject = "🚀 Crypto Trading Bot - LIVE MONITORING ACTIVE"
    message = """
🔥 AGGRESSIVE CRYPTO TRADING BOT - PRODUCTION MONITORING ACTIVATED

✅ Email notifications are now ACTIVE and working!
✅ You will be automatically alerted for any system issues

Current Status:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💰 Portfolio Value: $344.27 (REAL BINANCE.US ACCOUNT)
⚡ Trading Mode: AGGRESSIVE_LIVE
🎯 Portfolio Risk: 80% (MAXIMUM AGGRESSION)
💸 Position Size: $172.13 per trade
🔄 Monitoring: Every 60 seconds
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

You will receive email alerts for:
• Trading bot offline/crashes
• Dashboard unavailable  
• Live trading disabled
• API connection errors
• System performance issues
• High losses or low balance warnings

🎉 READY FOR 1000x GAINS WITH FULL MONITORING!

This is a test message confirming your email notifications are working.
"""
    
    success = notify_email(subject, message)
    
    if success:
        print("✅ SUCCESS: Test email sent successfully!")
        print(f"📧 Check your inbox at {email_to}")
        print("🔔 Email notifications are now ACTIVE!")
        return True
    else:
        print("❌ FAILED: Could not send test email")
        print("Please check your Gmail settings and app password")
        return False

if __name__ == "__main__":
    success = test_email_system()
    
    if success:
        print("\n🎉 EMAIL MONITORING FULLY ACTIVATED!")
        print("You will now receive automatic alerts for any system issues.")
    else:
        print("\n⚠️ Please verify Gmail settings and try again.")