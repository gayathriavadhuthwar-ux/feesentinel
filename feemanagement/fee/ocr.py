import re
from typing import Optional
from datetime import datetime

from PIL import Image, ImageEnhance, ImageFilter, ImageOps
import pytesseract

from django.conf import settings

if hasattr(settings, 'TESSERACT_CMD'):
    pytesseract.pytesseract.tesseract_cmd = settings.TESSERACT_CMD
else:
    # Fallback for non-django environments if needed
    pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"


# Patterns to match common UTR/transaction reference formats.
# Adjust patterns as needed for your receipt formats.
# Uses lax digit matching (allows spaces/hyphens) and then strips non-digits.
_UTR_PATTERNS = [
    # Example: "UTR: 628048695248" or "UTR - 628048695248"
    re.compile(r"\bUTR\s*[:\-]?\s*([0-9][0-9\s\-]{10,30}[0-9])\b", re.IGNORECASE),
    # Example: "Reference 628048695248"
    re.compile(r"\bRef(?:erence)?\s*[:\-]?\s*([0-9][0-9\s\-]{10,30}[0-9])\b", re.IGNORECASE),
    # Fallback: any 12 to 18 digit sequence (possibly separated by spaces/hyphens)
    re.compile(r"(?<!\d)([0-9]{12,18})(?!\d)"),
]


def _preprocess_image(image_path: str, mode: str = 'normal') -> Image.Image:
    """Load and preprocess an image to improve OCR accuracy."""
    img = Image.open(image_path)
    # Convert to grayscale
    img = img.convert("L")
    
    # Mode-specific processing
    if mode == 'inverted':
        img = ImageOps.invert(img)
    
    # Resize to improve OCR on small text
    resample_filter = getattr(Image, 'Resampling', Image).LANCZOS
    img = img.resize((img.width * 2, img.height * 2), resample_filter)
    
    if mode == 'sharpened':
        enhancer = ImageEnhance.Sharpness(img)
        img = enhancer.enhance(3.0)
    else:
        enhancer = ImageEnhance.Sharpness(img)
        img = enhancer.enhance(2.0)
    
    # Simple thresholding
    img = img.point(lambda x: 0 if x < 140 else 255, "1")
    return img


def extract_text_from_image(image_path: str) -> str:
    """Extract text using multi-pass strategy (Normal, Inverted, Sharpened)."""
    modes = ['normal', 'inverted', 'sharpened']
    best_text = ""
    
    for mode in modes:
        img = _preprocess_image(image_path, mode)
        
        # Try multiple OCR configurations per image mode
        configs = ["--oem 3 --psm 6", "--oem 3 --psm 11"]
        
        for cfg in configs:
            try:
                text = pytesseract.image_to_string(img, config=cfg).strip()
                # If we found a valid amount and UTR in this mode, stop early
                if extract_amount(text) and extract_utr_from_text(text):
                    return text
                if len(text) > len(best_text):
                    best_text = text
            except:
                continue
    
    return best_text


def extract_utr_from_text(text: str) -> Optional[str]:
    """Extract a UTR (transaction reference) from OCR text."""
    if not text:
        return None

    for pattern in _UTR_PATTERNS:
        match = pattern.search(text)
        if match:
            # Keep only digits (strip any spaces/hyphens captured by the regex)
            return re.sub(r"\D", "", match.group(1)).strip()

    return None


def extract_transaction_time(text: str) -> Optional[datetime]:
    """Extract a transaction datetime from OCR text.

    Looks for patterns like "09:26 pm on 21 Nov 2025" and returns a datetime.
    """
    if not text:
        return None

    match = re.search(r"(\d{1,2}:\d{2}\s*(?:am|pm))\s*on\s*(\d{1,2}\s+\w+\s+\d{4})", text, re.IGNORECASE)
    if match:
        raw = f"{match.group(1)} {match.group(2)}"
        try:
            return datetime.strptime(raw, "%I:%M %p %d %b %Y")
        except ValueError:
            # fallback: try without AM/PM or different locales
            try:
                return datetime.strptime(raw, "%H:%M %d %b %Y")
            except ValueError:
                return None
    return None


def extract_bank_name(text: str) -> Optional[str]:
    """Extract bank name from text."""
    # Look for common bank keywords or "Bank: <Name>"
    match = re.search(r"Bank\s*[:\-]?\s*([A-Z\s]{3,30})", text, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    
    # Check for specific banks
    known_banks = [
        "State Bank of India", "SBI", "HDFC BANK", "ICICI BANK", 
        "Axis Bank", "Canara Bank", "Punjab National Bank", "PNB",
        "Telangana Grameena Bank", "Union Bank of India", "IDBI",
        "Bank of Baroda", "Kotak", "IndusInd", "Federal Bank"
    ]
    for bank in known_banks:
        if bank.lower() in text.lower():
            return bank
    return None


def extract_receiver_name(text: str) -> Optional[str]:
    """Extract receiver name from text."""
    # Look for "Paid to:", "To:", "Payee:", "Receiver:"
    # Improved to handle educational institutions like JNTUH
    patterns = [
        r"(?:Paid to|To|Payee|Receiver|Transfer to)\s*[:\-]?\s*(?:[\d\s]*)\s*([A-Z\s\./#]{2,40})",
        r"([A-Z\s\.]+(?:University|College|Institution|JNTUH|Principal|Academy)[A-Z\s\.]*)",
    ]
    for p in patterns:
        match = re.search(p, text, re.IGNORECASE)
        if match:
            name = match.group(1).strip()
            # Clean up trailing junk
            name = name.split('\n')[0].strip()
            if len(name) > 3:
                return name
    return None


def extract_bank_account_name(text: str) -> Optional[str]:
    """Extract bank account name from text."""
    # Look for "Account Name:" or "Banking Name:"
    patterns = [
        r"(?:Account|Banking)\s*Name\s*[:\-]?\s*([A-Z][A-Z\s\./]{2,40})",
    ]
    for p in patterns:
        match = re.search(p, text, re.IGNORECASE)
        if match:
            return match.group(1).strip().split('\n')[0].strip()
    return None


def extract_amount(text: str) -> Optional[float]:
    """Extract payment amount from text."""
    # Look for INR symbols or "Amount" words followed by numbers
    patterns = [
        # Match "₹ 6,451" or "INR 6,451" or "Rs 6,451" (handles spaces/commas)
        r"(?:INR|₹|Rs\.?)\s*([\d\s,]+(?:\.\d{2})?)",
        # Match "Amount: 6,451"
        r"Amount\s*[:\-]?\s*(?:INR|₹|Rs\.?)?\s*([\d\s,]+(?:\.\d{2})?)",
        # Match "Paid 6,451"
        r"Paid\s*(?:INR|₹|Rs\.?)?\s*([\d\s,]+(?:\.\d{2})?)",
        # Match plain large number on a line by itself
        r"^\s*([\d\s,]{3,10}(?:\.\d{2})?)\s*$",
    ]
    lines = text.split('\n')
    # Check first few lines for a large number which is likely the amount in UPI apps
    for line in lines[:5]:
        line = line.strip()
        # Look for something like "1,000.00" or "₹1,000" (more flexible regex)
        match = re.search(r"(?:₹|INR|Rs\.?)?\s*([\d\s,]{3,10}(?:\.\d{2})?)", line, re.IGNORECASE)
        if match:
            try:
                # Remove spaces and commas before converting
                val_str = match.group(1).replace(',', '').replace(' ', '')
                val = float(val_str)
                if val >= 10: # Ignore very small noise numbers
                    return int(round(val))
            except ValueError:
                continue

    for p in patterns:
        match = re.search(p, text, re.IGNORECASE)
        if match:
            try:
                # Clean up extracted string
                raw = match.group(1).replace(',', '').replace(' ', '')
                
                # SPECIAL FIX: Common Indian OCR misread symbols at start of amounts
                # Often '₹' is read as '2', 'z', 'E', 's', or 'l'. 
                if len(raw) > 3:
                    first_char = raw[0]
                    # Targeted fix for misread Rupee symbol as '2' or 'z'
                    if first_char in '2zE' and len(raw) >= 4:
                         # Strip the suspect character and see if the rest is a valid amount
                         try:
                             stripped_val = int(round(float(raw[1:])))
                             # If stripping '2' results in a number like 6451 (which is precisely the case reported)
                             # and the context is payment-related, we prioritize the stripped version.
                             context = text.lower()
                             if any(k in context for k in ["fees", "paid", "amount", "total", "successfully", "hostel"]):
                                 # We log this for confirmation in ocr_debug.txt later
                                 return stripped_val
                         except:
                             pass

                val = int(round(float(raw)))
                # IGNORE SMALL NOISE: If amount is under 100 and looks like a date/day, ignore it.
                if val < 100 and any(m in text for m in ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]):
                    continue
                
                return val
            except ValueError:
                continue
    return None


def extract_transaction_id(text: str) -> Optional[str]:
    """Extract generic transaction ID or UPI specific IDs."""
    # Specific UPI App Patterns
    patterns = [
        r"UPI\s*Transaction\s*ID\s*[:\-]?\s*(\d{10,20})",  # GPay / PhonePe UPI ID
        r"Google\s*Transaction\s*ID\s*[:\-]?\s*([\w\-]{10,40})", # GPay ID
        r"Transaction\s*ID\s*[:\-]?\s*([\w\-]{10,40})", # Generic
        r"Wallet\s*Order\s*ID\s*[:\-]?\s*(\d{10,20})", # Paytm
    ]
    for p in patterns:
        match = re.search(p, text, re.IGNORECASE)
        if match:
            return match.group(1).strip()
    return None


def extract_detailed_data(image_path: str) -> dict:
    """Run full extraction and return a dictionary of all details."""
    text = extract_text_from_image(image_path)
    amount = extract_amount(text)
    
    # Debug Logging to help with misread amounts
    try:
        log_path = settings.BASE_DIR / 'ocr_debug.txt'
        with open(log_path, 'a', encoding='utf-8') as f:
            f.write(f"\n--- {datetime.now()} ---\n")
            f.write(f"Extracted Amount: {amount}\n")
            f.write(f"Raw Text:\n{text}\n")
            f.write("-" * 50 + "\n")
    except:
        pass

    return {
        'text': text,
        'utr': extract_utr_from_text(text),
        'txn_time': extract_transaction_time(text),
        'bank_name': extract_bank_name(text),
        'receiver_name': extract_receiver_name(text),
        'bank_account_name': extract_bank_account_name(text),
        'transaction_id': extract_transaction_id(text),
        'amount': amount,
    }


def extract_text_and_utr_from_image(image_path: str) -> tuple[str, Optional[str], Optional[str]]:
    """Legacy helper: Extract text, UTR, and transaction time from an image."""
    data = extract_detailed_data(image_path)
    return data['text'], data['utr'], data['txn_time']


def extract_utr_from_image(image_path: str) -> Optional[str]:
    """Extract UTR from an image by running OCR and parsing the result."""
    text = extract_text_from_image(image_path)
    return extract_utr_from_text(text)
