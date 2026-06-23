#!/usr/bin/env python3
"""
Check-admin script for EAT System
Verifies that at least one active admin user exists in the database
Usage: python scripts/check_admin.py
"""

import sys
import os

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.database import get_db
from app.models.users import User


def check_admin():
    """Check if there is at least one active admin user."""
    db = next(get_db())
    try:
        admin_count = db.query(User).filter(
            User.role == "admin",
            User.is_active == True
        ).count()
        
        if admin_count >= 1:
            print(f"✅ Found {admin_count} active admin user(s)")
            for admin in db.query(User).filter(
                User.role == "admin",
                User.is_active == True
            ).all():
                print(f"   - {admin.name} ({admin.email})")
            return True
        else:
            print("❌ No active admin users found")
            print("Please create an admin account using /api/v1/auth/admin-setup")
            return False
    finally:
        db.close()


if __name__ == "__main__":
    success = check_admin()
    sys.exit(0 if success else 1)
