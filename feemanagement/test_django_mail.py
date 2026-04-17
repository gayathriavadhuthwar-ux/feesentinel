import os
import django
from django.conf import settings
from django.core.mail import send_mail

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'feemanagement.settings')
django.setup()

def test_django_mail():
    print("--- Django Mail Integration Test ---")
    print(f"Using Backend: {settings.EMAIL_BACKEND}")
    print(f"Using Host: {settings.EMAIL_HOST}:{settings.EMAIL_PORT}")
    print(f"Using User: {settings.EMAIL_HOST_USER}")
    
    try:
        subject = "Django Integration Test"
        message = "This is a test email sent via Django's core mail system."
        recipient_list = [settings.EMAIL_HOST_USER]
        
        print(f"Attempting to send mail to {recipient_list}...")
        result = send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            recipient_list,
            fail_silently=False,
        )
        print(f"[SUCCESS] send_mail returned: {result}")
        print("Check your inbox/spam folder.")
    except Exception as e:
        print(f"[FAILURE] {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_django_mail()
