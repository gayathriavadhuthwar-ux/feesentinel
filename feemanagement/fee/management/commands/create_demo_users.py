from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.conf import settings

class Command(BaseCommand):
    help = 'Create demo admin and student users for review.'

    def handle(self, *args, **kwargs):
        # List of admins to ensure exist
        admins = [
            {
                'username': settings.DEMO_ADMIN_USERNAME,
                'password': settings.DEMO_ADMIN_PASSWORD,
                'email': 'adminreview@example.com'
            },
            {
                'username': 'ashajyothi',
                'password': 'ashajyothi@cse',
                'email': 'feemanagementjnwn@gmail.com'
            }
        ]

        for admin in admins:
            admin_user, created = User.objects.get_or_create(username=admin['username'])
            admin_user.set_password(admin['password'])
            admin_user.is_superuser = True
            admin_user.is_staff = True
            admin_user.email = admin['email']
            admin_user.save()
            
            status = "created" if created else "password reset and permissions verified"
            self.stdout.write(self.style.SUCCESS(f'Admin user "{admin["username"]}" {status}.'))

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