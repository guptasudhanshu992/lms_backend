"""
CAUTION: This script will delete the entire database and recreate it.
All data will be lost. Use only for development.

Run this to update the database schema after model changes.
"""

import os
from app.core.database import engine, Base, SessionLocal
from app.core.security import get_password_hash
from app.core.config import settings
from app.models import User, Course, Lesson, Section, Quiz, QuizQuestion, QuizAttempt, SCO, LearnerAttempt, Enrollment, Payment, Blog

def reset_database():
    # Get database path
    db_path = "lms.db"
    
    print("⚠️  WARNING: This will delete all data in the database!")
    print(f"Database location: {os.path.abspath(db_path)}")
    
    response = input("Are you sure you want to continue? (yes/no): ")
    if response.lower() != 'yes':
        print("❌ Operation cancelled")
        return
    
    # Delete existing database
    if os.path.exists(db_path):
        os.remove(db_path)
        print(f"✓ Deleted existing database: {db_path}")
    
    # Create all tables with new schema
    print("Creating new database tables...")
    Base.metadata.create_all(bind=engine)
    print("✓ Database tables created successfully!")
    
    # Recreate admin user
    db = SessionLocal()
    try:
        admin_user = User(
            email=settings.ADMIN_EMAIL,
            full_name=settings.ADMIN_FULL_NAME,
            hashed_password=get_password_hash(settings.ADMIN_PASSWORD),
            role="admin",
            is_active=True
        )
        db.add(admin_user)
        db.commit()
        print(f"✓ Admin user created: {settings.ADMIN_EMAIL}")
    except Exception as e:
        print(f"❌ Error creating admin user: {e}")
        db.rollback()
    finally:
        db.close()
    
    print("\n✅ Database reset complete!")
    print("Tables created:")
    print("  - users")
    print("  - courses (with SCORM fields)")
    print("  - sections (NEW)")
    print("  - lessons (enhanced with lesson_type)")
    print("  - quizzes (NEW)")
    print("  - quiz_questions (NEW)")
    print("  - quiz_attempts (NEW)")
    print("  - scos")
    print("  - learner_attempts")
    print("  - enrollments")
    print("  - payments")
    print("  - blogs")

if __name__ == "__main__":
    reset_database()
