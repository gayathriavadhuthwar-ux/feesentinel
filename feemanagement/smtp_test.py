import smtplib
import socket
import ssl
import os
import sys
from dotenv import load_dotenv

# Load settings
load_dotenv()

USER = os.environ.get('EMAIL_HOST_USER')
PASS = os.environ.get('EMAIL_HOST_PASSWORD')
HOST = 'smtp.gmail.com'
PORT = 587

print(f"--- SMTP Diagnostic Script ---")
print(f"Attempting connection to {HOST}:{PORT}...")
print(f"Username: {USER}")
print(f"Password character count: {len(PASS) if PASS else 0}")
print(f"------------------------------")

# Global SSL Fix (Same as in settings.py)
ssl._create_default_https_context = ssl._create_unverified_context
ssl.create_default_context = ssl._create_unverified_context

try:
    # 1. Test DNS
    print("1. Testing DNS resolution...")
    ip = socket.gethostbyname(HOST)
    print(f"   Success: {HOST} resolved to {ip}")

    # 2. Test Connection
    print("2. Opening connection...")
    server = smtplib.SMTP(HOST, PORT, timeout=10)
    server.set_debuglevel(1)
    print("   Success: Connected to server.")

    # 3. Test STARTTLS
    print("3. Attempting STARTTLS...")
    server.starttls()
    print("   Success: TLS encryption established.")

    # 4. Test Login
    print("4. Attempting Login...")
    code, msg = server.login(USER, PASS)
    print(f"   LOGIN SUCCESS! Code: {code}, Message: {msg}")
    
    # 5. Test Send
    print("5. Attempting to send test email to self...")
    server.sendmail(USER, [USER], f"Subject: Diagnostic Success\n\nSMTP integration is working!")
    print("   SEND SUCCESS!")

    server.quit()
    print("\n✅ DIAGNOSTIC PASSED: Everything is working correctly.")

except smtplib.SMTPAuthenticationError as e:
    print(f"\n❌ AUTHENTICATION ERROR: Google rejected your username/password.")
    print(f"Detail: {e}")
    print("\nTIP: Make sure you created an APP PASSWORD for the correct account and copied it without spaces.")
except ssl.SSLError as e:
    print(f"\n❌ SSL ERROR: Certificate verification failed.")
    print(f"Detail: {e}")
except Exception as e:
    print(f"\n❌ UNEXPECTED ERROR: {type(e).__name__}")
    print(f"Detail: {e}")
