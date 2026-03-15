from django.db import models
from django.contrib.auth.models import User

class StudentProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    hallticket_number = models.CharField(max_length=32, unique=True)

    def __str__(self):
        return f"{self.user.username} ({self.hallticket_number})"
