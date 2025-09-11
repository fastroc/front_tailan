from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver


class UserProfile(models.Model):
    """Simple profile for basic user info - KISS principle!"""
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    login_count = models.IntegerField(default=0)
    last_login_ip = models.GenericIPAddressField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def get_initials(self):
        """Get user initials for avatar display."""
        name = self.user.get_full_name() or self.user.username
        return ''.join([part[0].upper() for part in name.split()[:2]])
    
    def __str__(self):
        return f"Profile for {self.user.username}"


# Auto-create profile when user is created
@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    try:
        instance.userprofile.save()
    except UserProfile.DoesNotExist:
        UserProfile.objects.create(user=instance)
