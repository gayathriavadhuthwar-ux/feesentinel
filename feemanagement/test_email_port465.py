import smtplib
import ssl
import os
from dotenv import load_dotenv

load_dotenv()

HOST = 'smtp.gmail.com'
PORT = 465 # SMTP_SSL
USER = os.getenv('EMAIL_HOST_USER')
PASS = os.getenv('EMAIL_HOST_PASSWORD')

print(f"--- Port 465 (SSL) Diagnostic Test ---")
print(f"Connecting to {HOST}:{PORT}...")

# Global bypass
ssl._create_default_https_context = ssl._create_unverified_context

def test_465():
    try:
        context = ssl._create_unverified_context()
        print("1. Establishing SSL Connection...")
        server = smtplib.SMTP_SSL(HOST, PORT, context=context, timeout=10)
        server.set_debuglevel(1)
        
        print(f"2. Attempting login for {USER}...")
        server.login(USER, PASS)
        print("\n[SUCCESS] Login successful on Port 465!")
        
        server.quit()
        return True
    except Exception as e:
        print(f"\n[FAILURE] {str(e)}")
        return False

if __name__ == "__main__":
    test_465()
