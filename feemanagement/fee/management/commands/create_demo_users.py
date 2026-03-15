from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.conf import settings

class Command(BaseCommand):
    help = 'Create demo admin and student users for review.'

    def handle(self, *args, **kwargs):
        # Create admin user
        if not User.objects.filter(username=settings.DEMO_ADMIN_USERNAME).exists():
            User.objects.create_superuser(
                username=settings.DEMO_ADMIN_USERNAME,
                password=settings.DEMO_ADMIN_PASSWORD,
                email='adminreview@example.com'
            )
            self.stdout.write(self.style.SUCCESS('Demo admin user created.'))
        else:
            self.stdout.write('Demo admin user already exists.')

        # Create student user
        if not User.objects.filter(username=settings.DEMO_STUDENT_USERNAME).exists():
            User.objects.create_user(
                username=settings.DEMO_STUDENT_USERNAME,
                password=settings.DEMO_STUDENT_PASSWORD,
                email='studentreview@example.com'
            )
            self.stdout.write(self.style.SUCCESS('Demo student user created.'))
        else:
            self.stdout.write('Demo student user already exists.')