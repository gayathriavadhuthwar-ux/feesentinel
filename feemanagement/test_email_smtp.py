import smtplib
import ssl
import os
from dotenv import load_dotenv

# Load .env file
load_dotenv()

EMAIL_HOST = os.getenv('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = int(os.getenv('EMAIL_PORT', 587))
EMAIL_USER = os.getenv('EMAIL_HOST_USER')
EMAIL_PASS = os.getenv('EMAIL_HOST_PASSWORD')

print(f"--- SMTP Diagnostic Test ---")
print(f"Host: {EMAIL_HOST}")
print(f"Port: {EMAIL_PORT}")
print(f"User: {EMAIL_USER}")
print(f"Password: {'****' if EMAIL_PASS else 'MISSING'}")

# Global SSL bypass used in settings.py
ssl._create_default_https_context = ssl._create_unverified_context

def test_connection():
    try:
        print("\n1. Creating SSL context (unverified as per settings.py)...")
        context = ssl._create_unverified_context()
        
        print(f"2. Connecting to {EMAIL_HOST}:{EMAIL_PORT}...")
        server = smtplib.SMTP(EMAIL_HOST, EMAIL_PORT, timeout=10)
        server.set_debuglevel(1) # See full handshake
        
        print("3. Sending EHLO...")
        server.ehlo()
        
        print("4. Starting TLS...")
        server.starttls(context=context)
        
        print("5. Sending EHLO after STARTTLS...")
        server.ehlo()
        
        print(f"6. Attempting login for {EMAIL_USER}...")
        server.login(EMAIL_USER, EMAIL_PASS)
        
        print("\n[SUCCESS] SMTP Login successful!")
        
        # Optional: Send test mail
        recipient = EMAIL_USER # Send to self
        subject = "SMTP Test - Fee Management"
        body = "If you are reading this, your Google App Password and SMTP settings are working"
        message = f"Subject: {subject}\n\n{body}"
        
        print(f"7. Sending test email to {recipient}...")
        server.sendmail(EMAIL_USER, recipient, message)
        print("[SUCCESS] Test email sent successfully!")
        
        server.quit()
        return True
    except Exception as e:
        print(f"\n[FAILURE] {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_connection()
