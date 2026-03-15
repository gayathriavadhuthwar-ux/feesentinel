import re
from typing import Optional
from datetime import datetime

from PIL import Image
import pytesseract

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


def _preprocess_image(image_path: str) -> Image.Image:
    """Load and preprocess an image to improve OCR accuracy."""
    img = Image.open(image_path)
    # Convert to grayscale
    img = img.convert("L")
    # Resize to improve OCR on small text
    img = img.resize((img.width * 2, img.height * 2), Image.LANCZOS)
    # Optionally apply simple thresholding
    img = img.point(lambda x: 0 if x < 140 else 255, "1")
    return img


def extract_text_from_image(image_path: str) -> str:
    """Extract text from an image using Tesseract OCR.

    Tries a few Tesseract page segmentation modes and returns the best result
    (preferring outputs that contain a UTR)."""
    img = _preprocess_image(image_path)

    # Try multiple OCR configurations to improve detection accuracy.
    configs = [
        "--oem 3 --psm 6",  # Assume a single uniform block of text
        "--oem 3 --psm 11",  # Sparse text
        "--oem 3 --psm 3",  # Fully automatic page segmentation
    ]

    best_text = ""
    for cfg in configs:
        text = pytesseract.image_to_string(img, config=cfg).strip()
        if extract_utr_from_text(text):
            return text
        if len(text) > len(best_text):
            best_text = text

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


def extract_text_and_utr_from_image(image_path: str) -> tuple[str, Optional[str], Optional[str]]:
    """Extract text, UTR, and transaction time from an image."""
    text = extract_text_from_image(image_path)
    utr = extract_utr_from_text(text)
    txn_time = extract_transaction_time(text)
    return text, utr, txn_time


def extract_utr_from_image(image_path: str) -> Optional[str]:
    """Extract UTR from an image by running OCR and parsing the result."""
    text = extract_text_from_image(image_path)
    return extract_utr_from_text(text)
