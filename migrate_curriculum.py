"""
Database migration script to add new tables for curriculum builder
Run this after updating models to create the new tables
"""

from app.core.database import engine, Base
from app.models import Section, Quiz, QuizQuestion, QuizAttempt

def migrate():
    print("Creating new tables...")
    Base.metadata.create_all(bind=engine)
    print("✓ Migration complete!")
    print("New tables created:")
    print("  - sections")
    print("  - quizzes")
    print("  - quiz_questions")
    print("  - quiz_attempts")

if __name__ == "__main__":
    migrate()
