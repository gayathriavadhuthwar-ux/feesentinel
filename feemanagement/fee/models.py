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

    STATUS_CHOICES = [
        ('pending', 'Pending Review'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
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
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    rejection_reason = models.TextField(blank=True, null=True)
    processed_at = models.DateTimeField(null=True, blank=True)
    processed_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='processed_receipts')
    is_duplicate = models.BooleanField(default=False)
    duplicate_of = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL)

    # Detailed extraction fields
    amount = models.PositiveIntegerField(null=True, blank=True)
    receiver_name = models.CharField(max_length=100, null=True, blank=True)
    bank_name = models.CharField(max_length=100, null=True, blank=True)
    bank_account_name = models.CharField(max_length=100, null=True, blank=True)
    transaction_id = models.CharField(max_length=64, null=True, blank=True)

    # Dynamic dropdown fields
    REGULATIONS = [
        ('r18', 'R18'),
        ('r22', 'R22'),
        ('r25', 'R25'),
    ]
    ACADEMIC_YEARS = [
        ('1', '1st Year'),
        ('2', '2nd Year'),
        ('3', '3rd Year'),
        ('4', '4th Year'),
    ]
    EXAM_CATEGORIES = [
        ('regular', 'Regular Exam'),
        ('supply', 'Supply Exam'),
    ]

    BRANCH_CHOICES = [
        ('CSE', 'Computer Science & Engineering'),
        ('CSM', 'CSE (AI & ML)'),
        ('ECE', 'Electronics & Communication'),
        ('CIVIL', 'Civil Engineering'),
        ('MECH', 'Mechanical Engineering'),
    ]
    
    regulation = models.CharField(max_length=10, choices=REGULATIONS, null=True, blank=True)
    branch = models.CharField(max_length=10, choices=BRANCH_CHOICES, null=True, blank=True)
    academic_year = models.CharField(max_length=10, choices=ACADEMIC_YEARS, null=True, blank=True)
    exam_category = models.CharField(max_length=10, choices=EXAM_CATEGORIES, null=True, blank=True)
    exam_details = models.CharField(max_length=100, null=True, blank=True)

    def save(self, *args, **kwargs):
        if self.extracted_text and not self.text_hash:
            self.text_hash = hashlib.sha256(self.extracted_text.encode()).hexdigest()

        super().save(*args, **kwargs)

    def get_utr(self):
        """Return the stored UTR (transaction reference)."""
        return self.utr

    def __str__(self):
        return f"{self.student.username} - {self.hallticket_number} - {self.fee_type} - {self.submitted_at}"

class Feedback(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Feedback from {self.user.username} at {self.created_at}"
