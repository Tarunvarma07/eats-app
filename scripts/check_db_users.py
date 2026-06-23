#!/usr/bin/env python3
"""Check database for admin users and display credentials"""
import sqlite3
import sys

def check_admin_users():
    conn = sqlite3.connect('test.db')
    cursor = conn.cursor()
    
    try:
        cursor.execute('SELECT id, name, email, role, is_active, is_approved FROM users WHERE role="admin"')
        admins = cursor.fetchall()
        
        if admins:
            print("Admin users found in database:")
            print("-" * 80)
            for admin in admins:
                print(f"ID: {admin[0]}")
                print(f"Name: {admin[1]}")
                print(f"Email: {admin[2]}")
                print(f"Role: {admin[3]}")
                print(f"Active: {admin[4]}")
                print(f"Approved: {admin[5]}")
                print("-" * 80)
            print(f"Total admin users: {len(admins)}")
        else:
            print("No admin users found in database.")
            print("You need to create an admin account via /app/setup.html")
        
        # Also show all users for reference
        cursor.execute('SELECT id, name, email, role, is_active, is_approved FROM users')
        all_users = cursor.fetchall()
        print(f"\nTotal users in database: {len(all_users)}")
        
    except Exception as e:
        print(f"Error checking database: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    check_admin_users()
