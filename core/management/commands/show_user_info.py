"""
Management command to show user information and password security status
"""

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone


class Command(BaseCommand):
    help = "Display user information including password security status (no passwords shown)"

    def add_arguments(self, parser):
        parser.add_argument("--username", type=str, help="Show info for specific user")
        parser.add_argument(
            "--all", action="store_true", help="Show info for all users"
        )

    def handle(self, *args, **options):
        if options["username"]:
            try:
                user = User.objects.get(username=options["username"])
                self.show_user_info(user)
            except User.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f'User "{options["username"]}" not found')
                )
        elif options["all"]:
            users = User.objects.all().order_by("username")
            self.stdout.write(f"Found {users.count()} users:\n")
            for user in users:
                self.show_user_info(user, brief=True)
                self.stdout.write("-" * 50)
        else:
            self.stdout.write(self.style.WARNING("Use --username <username> or --all"))

    def show_user_info(self, user, brief=False):
        """Display comprehensive user information"""

        # Header
        self.stdout.write(
            self.style.SUCCESS(f"👤 USER: {user.username} (ID: {user.id})")
        )

        # Basic info
        self.stdout.write(f'Email: {user.email or "Not set"}')
        self.stdout.write(f'Full Name: {user.get_full_name() or "Not set"}')
        self.stdout.write(f'Active: {"✅ Yes" if user.is_active else "❌ No"}')
        self.stdout.write(f'Staff: {"✅ Yes" if user.is_staff else "❌ No"}')
        self.stdout.write(f'Superuser: {"👑 Yes" if user.is_superuser else "❌ No"}')

        # Dates
        self.stdout.write(f'Joined: {user.date_joined.strftime("%Y-%m-%d %H:%M")}')
        if user.last_login:
            days_ago = (timezone.now() - user.last_login).days
            self.stdout.write(
                f'Last Login: {user.last_login.strftime("%Y-%m-%d %H:%M")} ({days_ago} days ago)'
            )
        else:
            self.stdout.write("Last Login: ❌ Never")

        # Password security (NO PASSWORD SHOWN!)
        self.show_password_security(user)

        # Profile info
        try:
            profile = user.userprofile
            self.stdout.write(f"Login Count: {profile.login_count}")
            self.stdout.write(f'Last IP: {profile.last_login_ip or "Unknown"}')
            self.stdout.write(
                f'Profile Created: {profile.created_at.strftime("%Y-%m-%d")}'
            )
        except Exception:
            self.stdout.write("Profile: ❌ Not created")

        # Company access
        try:
            from company.models import UserCompanyAccess

            companies = UserCompanyAccess.objects.filter(user=user)
            if companies.exists():
                self.stdout.write("🏢 Company Access:")
                for access in companies:
                    self.stdout.write(f"  - {access.company.name} ({access.role})")
            else:
                self.stdout.write("🏢 Company Access: None")
        except Exception:
            self.stdout.write("🏢 Company Access: Unknown")

        if not brief:
            # Groups and permissions
            if user.groups.exists():
                self.stdout.write("👥 Groups:")
                for group in user.groups.all():
                    self.stdout.write(f"  - {group.name}")
            else:
                self.stdout.write("👥 Groups: None")

            perm_count = user.user_permissions.count()
            self.stdout.write(f"🔑 Individual Permissions: {perm_count}")

    def show_password_security(self, user):
        """Show password security information (NO ACTUAL PASSWORD!)"""
        if not user.password:
            self.stdout.write(
                self.style.ERROR("🔒 Password: ❌ NOT SET - User cannot log in!")
            )
            return

        # Analyze password hash
        parts = user.password.split("$")
        if len(parts) >= 2:
            algorithm = parts[0]
            iterations = parts[1] if len(parts) > 1 and parts[1].isdigit() else "N/A"

            # Security assessment
            if algorithm == "pbkdf2_sha256":
                security = "🔒 STRONG (PBKDF2-SHA256)"
                color = self.style.SUCCESS
            elif algorithm == "bcrypt":
                security = "🔐 VERY STRONG (bcrypt)"
                color = self.style.SUCCESS
            elif algorithm == "argon2":
                security = "🔐 EXCELLENT (Argon2)"
                color = self.style.SUCCESS
            else:
                security = f"⚠️ UNKNOWN ({algorithm})"
                color = self.style.WARNING

            self.stdout.write(color(f"🔒 Password Security: {security}"))
            self.stdout.write(f"   Algorithm: {algorithm}")
            self.stdout.write(f"   Iterations: {iterations}")
            self.stdout.write(f"   Hash Length: {len(user.password)} characters")

        else:
            self.stdout.write(self.style.WARNING("🔒 Password: ⚠️ UNKNOWN FORMAT"))

        # Security reminders
        self.stdout.write(
            self.style.HTTP_INFO(
                "   📝 Note: Passwords are securely hashed and cannot be retrieved"
            )
        )
