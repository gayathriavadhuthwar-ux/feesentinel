from django.contrib.auth.models import User
import sys

username = 'ashajyothi'
email = 'ashajyothi@gmail.com'
password = 'ashajyothi123'

if User.objects.filter(username=username).exists():
    print(f"User {username} already exists.")
    user = User.objects.get(username=username)
    user.email = email
    user.set_password(password)
    user.is_superuser = True
    user.is_staff = True
    user.save()
    print(f"User {username} updated successfully.")
else:
    User.objects.create_superuser(username, email, password)
    print(f"User {username} created successfully.")
