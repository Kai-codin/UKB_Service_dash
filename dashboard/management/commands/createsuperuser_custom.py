from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model


class Command(BaseCommand):
    help = 'Create a superuser with provided username, email and password flags.'

    def add_arguments(self, parser):
        parser.add_argument('--username', required=True, help='Username for the new superuser')
        parser.add_argument('--email', required=True, help='Email for the new superuser')
        parser.add_argument('--password', required=True, help='Password for the new superuser')

    def handle(self, *args, **options):
        username = options['username']
        email = options['email']
        password = options['password']
        User = get_user_model()
        if User.objects.filter(username=username).exists():
            raise CommandError(f"User '{username}' already exists")
        user = User.objects.create_superuser(username=username, email=email, password=password)
        self.stdout.write(self.style.SUCCESS(f"Superuser '{username}' created."))
