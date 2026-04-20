from fuzzywuzzy import fuzz

def check_for_duplicate(receipt):
    """
    Check if the given receipt is a duplicate based on UTR or extracted text similarity.
    Returns (existing receipt, reason_string) if duplicate found, else (None, None).
    """
    from .models import Receipt


    # First, check for exact UTR match
    if receipt.utr:
        duplicate = Receipt.objects.filter(utr=receipt.utr).exclude(id=receipt.id).first()
        if duplicate:
            reason = f"A receipt with the same UTR ID ({receipt.utr}) was already submitted by @{duplicate.student.username}."
            return duplicate, reason

    # Fallback to fuzzy text matching for recent receipts (e.g., last 60 days)
    # This avoids full table scans as the database grows.
    from django.utils import timezone
    from datetime import timedelta
    
    threshold_date = timezone.now() - timedelta(days=60)
    recent_receipts = Receipt.objects.filter(submitted_at__gte=threshold_date).exclude(student=receipt.student).exclude(id=receipt.id)
    
    for existing in recent_receipts:
        if receipt.extracted_text and existing.extracted_text:
            ratio = fuzz.ratio(receipt.extracted_text, existing.extracted_text)
            if ratio > 85:  # 85% similarity
                reason = f"Receipt content matches an existing submission by @{existing.student.username} ({ratio}% similarity)."
                return existing, reason
    return None, None
