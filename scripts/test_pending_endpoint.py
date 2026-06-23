#!/usr/bin/env python3
"""
Test script to check what the pending endpoint returns.
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

def test_pending_endpoint():
    db = SessionLocal()
    
    try:
        print("=" * 60)
        print("Testing pending users query (same as backend endpoint)")
        print("=" * 60)
        
        # This is the exact query from the backend
        pending = (
            db.query(User)
            .filter(User.is_approved == False, User.is_active == True)
            .order_by(User.created_at.desc())
            .all()
        )
        
        print(f"Found {len(pending)} pending users:")
        
        if not pending:
            print("❌ No pending users found!")
        else:
            for u in pending:
                print(f"\n  - ID: {u.id}")
                print(f"    Name: {u.name}")
                print(f"    Email: {u.email}")
                print(f"    Role: {u.role}")
                print(f"    Department: {u.department}")
                print(f"    is_active: {u.is_active}")
                print(f"    is_approved: {u.is_approved}")
                print(f"    created_at: {u.created_at}")
        
        # Also check all users with is_approved=False regardless of is_active
        print("\n" + "=" * 60)
        print("All users with is_approved=False (for comparison)")
        print("=" * 60)
        
        all_unapproved = db.query(User).filter(User.is_approved == False).all()
        print(f"Found {len(all_unapproved)} users with is_approved=False:")
        
        for u in all_unapproved:
            print(f"  - {u.email}: is_active={u.is_active}, is_approved={u.is_approved}")
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    test_pending_endpoint()
