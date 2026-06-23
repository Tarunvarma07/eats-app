#!/usr/bin/env python3
"""
Test script to reproduce employee registration and approval flow.
This will help identify the real issue with employee login.
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
from app.services.user_service import UserService
from app.services.auth_service import AuthService
from app.schemas.users import UserCreate, UserLogin

def test_employee_flow():
    db = SessionLocal()
    
    try:
        # Step 1: Register a test employee
        print("=" * 60)
        print("STEP 1: Registering test employee...")
        print("=" * 60)
        
        test_email = "test_employee@test.com"
        test_password = "Test123"
        
        # Check if user already exists
        existing = db.query(User).filter(User.email == test_email).first()
        if existing:
            print(f"User {test_email} already exists, deleting...")
            db.delete(existing)
            db.commit()
        
        # Register new employee
        user_data = UserCreate(
            name="Test Employee",
            email=test_email,
            password=test_password,
            department="IT"
        )
        
        registered_user = AuthService.register_user(db, user_data, role="employee")
        print(f"✅ User registered: {registered_user.name}")
        print(f"   Email: {registered_user.email}")
        print(f"   Role: {registered_user.role}")
        print(f"   is_active: {registered_user.is_active}")
        print(f"   is_approved: {registered_user.is_approved}")
        
        # Step 2: Check database state directly
        print("\n" + "=" * 60)
        print("STEP 2: Checking database state after registration...")
        print("=" * 60)
        
        db.refresh(registered_user)
        print(f"   is_approved in DB: {registered_user.is_approved}")
        
        # Step 3: Try to login BEFORE approval
        print("\n" + "=" * 60)
        print("STEP 3: Attempting login BEFORE approval...")
        print("=" * 60)
        
        try:
            login_data = UserLogin(email=test_email, password=test_password)
            result = AuthService.login_user(db, login_data)
            print(f"❌ UNEXPECTED: Login succeeded before approval!")
            print(f"   Token: {result.get('access_token')[:50]}...")
        except ValueError as e:
            print(f"✅ EXPECTED: Login failed with: {e}")
        
        # Step 4: Approve the user
        print("\n" + "=" * 60)
        print("STEP 4: Approving user via UserService.update_user...")
        print("=" * 60)
        
        UserService.update_user(db, registered_user.id, is_approved=True)
        print(f"✅ UserService.update_user called with is_approved=True")
        
        # Step 5: Check database state after approval
        print("\n" + "=" * 60)
        print("STEP 5: Checking database state after approval...")
        print("=" * 60)
        
        db.refresh(registered_user)
        print(f"   is_approved in DB: {registered_user.is_approved}")
        
        # Step 6: Try to login AFTER approval
        print("\n" + "=" * 60)
        print("STEP 6: Attempting login AFTER approval...")
        print("=" * 60)
        
        try:
            login_data = UserLogin(email=test_email, password=test_password)
            result = AuthService.login_user(db, login_data)
            print(f"✅ Login succeeded after approval!")
            print(f"   Token type: {result.get('token_type')}")
            print(f"   Token: {result.get('access_token')[:50]}...")
        except ValueError as e:
            print(f"❌ UNEXPECTED: Login failed after approval with: {e}")
        
        # Cleanup
        print("\n" + "=" * 60)
        print("CLEANUP: Deleting test user...")
        print("=" * 60)
        db.delete(registered_user)
        db.commit()
        print("✅ Test user deleted")
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    test_employee_flow()
