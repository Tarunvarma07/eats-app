#!/usr/bin/env python3
"""
Script to check user approval status in database.
Usage: python scripts/check_user_approval.py <email>
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import all models to resolve SQLAlchemy relationships
from app.models.users import User
from app.models.attendance import AttendanceSession
from app.models.activity_log import ActivityLog
from app.models.audit_log import AuditLog

from app.db.database import SessionLocal

def check_user_approval(email: str):
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email).first()
        if not user:
            print(f"❌ User with email '{email}' not found in database")
            return
        
        print(f"✅ User found: {user.name}")
        print(f"   Email: {user.email}")
        print(f"   Role: {user.role}")
        print(f"   Department: {user.department}")
        print(f"   is_active: {user.is_active}")
        print(f"   is_approved: {user.is_approved}")
        print(f"   created_at: {user.created_at}")
        
        if user.is_approved:
            print(f"\n✅ User IS APPROVED - should be able to login")
        else:
            print(f"\n❌ User IS NOT APPROVED - login will fail with 'pending admin approval'")
            
    except Exception as e:
        print(f"❌ Error checking user: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/check_user_approval.py <email>")
        sys.exit(1)
    
    email = sys.argv[1]
    check_user_approval(email)
