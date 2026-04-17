from fuzzywuzzy import fuzz
from .models import Receipt

def check_for_duplicate(receipt):
    """
    Check if the given receipt is a duplicate based on UTR or extracted text similarity.
    Returns the existing receipt if duplicate found, else None.
    """
    # First, check for exact UTR match
    if receipt.utr:
        duplicate = Receipt.objects.filter(utr=receipt.utr).exclude(id=receipt.id).first()
        if duplicate:
            return duplicate

    # Fallback to fuzzy text matching for recent receipts (e.g., last 30 days)
    # This avoids full table scans as the database grows.
    from django.utils import timezone
    from datetime import timedelta
    
    threshold_date = timezone.now() - timedelta(days=60)
    recent_receipts = Receipt.objects.filter(submitted_at__gte=threshold_date).exclude(student=receipt.student).exclude(id=receipt.id)
    
    for existing in recent_receipts:
        if fuzz.ratio(receipt.extracted_text, existing.extracted_text) > 85:  # 85% similarity
            return existing
    return None
