from ..database import Database

if __name__ == "__main__":
    print("🔄 Resetting database...")
    with Database() as db:
        db.reset_database()
    print("✅ Database reset completed!")