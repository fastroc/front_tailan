from django.core.management.base import BaseCommand
from django.contrib.auth.models import User


class Command(BaseCommand):
    help = 'Create a superuser quickly'

    def handle(self, *args, **options):
        email = 'admin@example.com'
        username = 'admin'
        password = 'admin123'
        
        if not User.objects.filter(email=email).exists():
            user = User.objects.create_superuser(
                email=email,
                password=password,
                username=username,
                first_name='Admin',
                last_name='User'
            )
            self.stdout.write(
                self.style.SUCCESS(
                    f'Superuser created successfully!\n'
                    f'Email: {email}\n'
                    f'Username: {username}\n'
                    f'Password: {password}'
                )
            )
        else:
            self.stdout.write(
                self.style.WARNING('Superuser already exists!')
            )
