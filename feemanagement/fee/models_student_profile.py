from django.db import models
from django.contrib.auth.models import User

class StudentProfile(models.Model):
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

    BRANCH_CHOICES = [
        ('CSE', 'Computer Science & Engineering'),
        ('CSM', 'CSE (AI & ML)'),
        ('ECE', 'Electronics & Communication'),
        ('CIVIL', 'Civil Engineering'),
        ('MECH', 'Mechanical Engineering'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    hallticket_number = models.CharField(max_length=32, unique=True)
    regulation = models.CharField(max_length=10, choices=REGULATIONS, null=True, blank=True)
    branch = models.CharField(max_length=10, choices=BRANCH_CHOICES, null=True, blank=True)
    academic_year = models.CharField(max_length=10, choices=ACADEMIC_YEARS, null=True, blank=True)

    def __str__(self):
        return f"{self.user.username} ({self.hallticket_number})"
