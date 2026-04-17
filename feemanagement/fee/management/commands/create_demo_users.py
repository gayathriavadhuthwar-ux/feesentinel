from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.conf import settings

class Command(BaseCommand):
    help = 'Create demo admin and student users for review.'

    def handle(self, *args, **kwargs):
        # Create or update admin user
        admin_user, created = User.objects.get_or_create(username=settings.DEMO_ADMIN_USERNAME)
        admin_user.set_password(settings.DEMO_ADMIN_PASSWORD)
        admin_user.is_superuser = True
        admin_user.is_staff = True
        admin_user.email = 'adminreview@example.com'
        admin_user.save()
        
        if created:
            self.stdout.write(self.style.SUCCESS(f'Demo admin user "{settings.DEMO_ADMIN_USERNAME}" created.'))
        else:
            self.stdout.write(self.style.SUCCESS(f'Demo admin user "{settings.DEMO_ADMIN_USERNAME}" password reset and permissions verified.'))

        # Create student user 1
        if not User.objects.filter(username=settings.DEMO_STUDENT1_USERNAME).exists():
            User.objects.create_user(
                username=settings.DEMO_STUDENT1_USERNAME,
                password=settings.DEMO_STUDENT1_PASSWORD,
                email='studentreview1@example.com'
            )
            self.stdout.write(self.style.SUCCESS('Demo student user 1 created.'))
        else:
            self.stdout.write('Demo student user 1 already exists.')

        # Create student user 2
        if not User.objects.filter(username=settings.DEMO_STUDENT2_USERNAME).exists():
            User.objects.create_user(
                username=settings.DEMO_STUDENT2_USERNAME,
                password=settings.DEMO_STUDENT2_PASSWORD,
                email='studentreview2@example.com'
            )
            self.stdout.write(self.style.SUCCESS('Demo student user 2 created.'))
        else:
            self.stdout.write('Demo student user 2 already exists.')