# Core admin - auto-registration is handled in admin_automation.py
# Enhanced user admin is imported here
try:
    from .enhanced_user_admin import EnhancedUserAdmin
    # This automatically unregisters default User admin and replaces it
    print("✅ Enhanced User Admin loaded successfully")
except ImportError as e:
    print(f"Could not load enhanced user admin: {e}")

# This file is kept for Django admin autodiscovery
