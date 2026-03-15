from django.db import models
from django.contrib.auth.models import User
import hashlib

from .ocr import extract_utr_from_text

class Receipt(models.Model):
    FEE_TYPES = [
        ('college', 'College Fee'),
        ('special', 'Special Fee'),
        ('exam', 'Exam Fee'),
    ]

    student = models.ForeignKey(User, on_delete=models.CASCADE)
    fee_type = models.CharField(max_length=10, choices=FEE_TYPES)
    hallticket_number = models.CharField(max_length=32, null=True, blank=True)
    image = models.ImageField(upload_to='receipts/')
    extracted_text = models.TextField(blank=True)
    text_hash = models.CharField(max_length=64, blank=True)
    utr = models.CharField(max_length=64, blank=True)
    transaction_at = models.DateTimeField(null=True, blank=True)
    submitted_at = models.DateTimeField(auto_now_add=True)
    is_duplicate = models.BooleanField(default=False)
    duplicate_of = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL)

    def save(self, *args, **kwargs):
        if self.extracted_text and not self.text_hash:
            self.text_hash = hashlib.sha256(self.extracted_text.encode()).hexdigest()

        super().save(*args, **kwargs)

    def get_utr(self):
        """Return the stored UTR (transaction reference)."""
        return self.utr

    def __str__(self):
        return f"{self.student.username} - {self.hallticket_number} - {self.fee_type} - {self.submitted_at}"
