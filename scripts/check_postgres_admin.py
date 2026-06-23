#!/usr/bin/env python3
"""Check PostgreSQL database for admin users and display credentials"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.database import SessionLocal
# Import all models to ensure relationships are resolved
from app.models import users, attendance, audit_log, activity_log, token_blacklist
from app.models.users import User

def check_admin_users():
    db = SessionLocal()
    try:
        admins = db.query(User).filter(User.role == "admin").all()
        
        if admins:
            print("Admin users found in database:")
            print("-" * 80)
            for admin in admins:
                print(f"ID: {admin.id}")
                print(f"Name: {admin.name}")
                print(f"Email: {admin.email}")
                print(f"Role: {admin.role}")
                print(f"Active: {admin.is_active}")
                print(f"Approved: {admin.is_approved}")
                print(f"Hash starts with bcrypt: {admin.hashed_password.startswith('$2b$')}")
                print(f"Password hash (first 50 chars): {admin.hashed_password[:50]}")
                print("-" * 80)
            print(f"Total admin users: {len(admins)}")
        else:
            print("No admin users found in database.")
            print("You need to create an admin account via /app/setup.html")
        
        # Also show all users for reference
        all_users = db.query(User).all()
        print(f"\nTotal users in database: {len(all_users)}")
        
    except Exception as e:
        print(f"Error checking database: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    check_admin_users()
