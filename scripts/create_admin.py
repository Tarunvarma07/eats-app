#!/usr/bin/env python3
"""Safe admin creation script. Run: python scripts/create_admin.py"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.database import SessionLocal
# Import all models to ensure relationships are resolved
from app.models import users, attendance, audit_log, activity_log, token_blacklist
from app.models.users import User
from app.core.security import hash_password

def create_admin(email: str, password: str, name: str, department: str = None):
    db = SessionLocal()
    try:
        existing = db.query(User).filter(User.email == email).first()
        if existing:
            print(f"User {email} already exists. role={existing.role}, is_active={existing.is_active}, is_approved={existing.is_approved}")
            return
        
        admin = User(
            email=email,
            hashed_password=hash_password(password),
            name=name,
            role="admin",        # exact string your codebase uses
            is_active=True,
            is_approved=True,
            department=department
        )
        db.add(admin)
        db.commit()
        print(f"✅ Admin created: {email}")
        print(f"   Name: {name}")
        print(f"   Role: admin")
        print(f"   Active: True")
        print(f"   Approved: True")
    except Exception as e:
        db.rollback()
        print(f"❌ Error: {e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    print("=== Admin Account Creation ===")
    email = input("Admin email: ").strip()
    password = input("Admin password: ").strip()
    name = input("Admin name: ").strip()
    department = input("Department (optional, press Enter to skip): ").strip() or None
    
    if not email or not password or not name:
        print("❌ Email, password, and name are required.")
        sys.exit(1)
    
    if len(password) < 6:
        print("❌ Password must be at least 6 characters.")
        sys.exit(1)
    
    create_admin(email, password, name, department)
