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
    
    # 1. Memory Optimization: Downscale high-resolution images
    # 512MB RAM is limited; keep images manageable
    MAX_DIM = 1024
    if img.width > MAX_DIM or img.height > MAX_DIM:
        img.thumbnail((MAX_DIM, MAX_DIM), Image.Resampling.LANCZOS)

    # Convert to grayscale
    img = img.convert("L")
    
    # Mode-specific processing
    if mode == 'inverted':
        img = ImageOps.invert(img)
    
    # REMOVED: Doubling image size (too much memory usage)
    
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
        # Priority on --psm 6 (uniform block of text)
        configs = ["--oem 3 --psm 6", "--oem 3 --psm 11"]
        
        current_mode_text = ""
        for cfg in configs:
            try:
                text = pytesseract.image_to_string(img, config=cfg).strip()
                if len(text) > len(current_mode_text):
                    current_mode_text = text
                
                # HEURISTIC: If we found strong indicators in the FIRST mode, stop early to save memory
                from .ocr import extract_amount, extract_utr_from_text # local import for early checks
                if extract_amount(text) and extract_utr_from_text(text):
                    img.close()
                    return text
            except:
                continue
        
        if len(current_mode_text) > len(best_text):
            best_text = current_mode_text
        
        img.close() # Ensure memory is freed
    
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
    """Extract payment amount from text with improved robustness."""
    if not text:
        return None

    potential_amounts = []

    # 1. Strict patterns: match entries preceded by currency symbols or labels
    strict_patterns = [
        # Match "₹ 6,451" or "INR 6,451" or "Rs 6,451"
        r"(?:INR|₹|Rs\.?)\s*([\d\s,]+(?:\.\d{2})?)",
        # Match "Amount: 6,451"
        r"Amount\s*[:\-]?\s*(?:INR|₹|Rs\.?)?\s*([\d\s,]+(?:\.\d{2})?)",
        # Match "Paid 6,451"
        r"Paid\s*(?:INR|₹|Rs\.?)?\s*([\d\s,]+(?:\.\d{2})?)",
    ]
    
    for p in strict_patterns:
        matches = re.finditer(p, text, re.IGNORECASE)
        for match in matches:
            try:
                raw = match.group(1).replace(',', '').replace(' ', '')
                if not raw: continue
                val = float(raw)
                # Save value and whether it has strong currency context
                potential_amounts.append({'val': val, 'priority': 2, 'raw': raw})
            except ValueError:
                continue

    # 2. Safety Fallback: search for naked numbers on lines that look like amounts
    lines = text.split('\n')
    for line in lines[:10]:
        line = line.strip()
        # Look for line-level numbers (e.g. "900" or "900.00" or misread "?900")
        match = re.search(r"^(?:[A-Za-z\?])?\s*([\d,]{3,10}(?:\.\d{2})?)\s*$", line, re.IGNORECASE)
        if match:
            try:
                val_str = match.group(1).replace(',', '').replace(' ', '')
                val = float(val_str)
                
                # Check for the classic Rupee symbol misread (₹ misread as '3' or '2')
                # If we parsed a number >= 1000 starting with 2 or 3, it might be a misread.
                if len(val_str) >= 4 and val_str[0] in ['2', '3']:
                    stripped_val = float(val_str[1:])
                    # If common keywords exist, strongly prefer the stripped version
                    context_keywords = ["fees", "paid", "amount", "total", "successful", "ref", "utr"]
                    has_context = any(k in text.lower() for k in context_keywords)
                    
                    if has_context:
                        potential_amounts.append({'val': stripped_val, 'priority': 1.5, 'raw': val_str[1:]})
                    else:
                        potential_amounts.append({'val': stripped_val, 'priority': 1, 'raw': val_str[1:]})

                potential_amounts.append({'val': val, 'priority': 1, 'raw': val_str})
            except ValueError:
                continue

    if not potential_amounts:
        return None

    # Filter and sort potential amounts
    # Rules:
    # - Ignore common year numbers if priority is low
    # - Prefer priority 2 (strict matches) over priority 1
    # - Prefer larger amounts within common fee ranges (100 - 200,000)
    
    valid_amounts = []
    current_year = datetime.now().year
    years_to_ignore = {current_year, current_year-1, current_year+1, current_year-2}

    for item in potential_amounts:
        val = item['val']
        # Round to integer for the final value
        v_int = int(round(val))
        
        # Heuristic: Ignore numbers that look like years unless they have strict context
        if item['priority'] < 2 and v_int in years_to_ignore:
            continue
            
        # Ignore very small numbers as amounts unless they have strict context and are >= 10
        if v_int < 100 and item['priority'] < 2:
            continue
            
        if v_int < 1:
            continue

        valid_amounts.append(item)

    if not valid_amounts:
        return None

    # Sort by priority desc, then by value desc (prefer largest amount in strict context)
    valid_amounts.sort(key=lambda x: (x['priority'], x['val']), reverse=True)
    
    return int(round(valid_amounts[0]['val']))


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
