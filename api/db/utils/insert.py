from ..database import Database

if __name__ == "__main__":
    print("👥 Inserting test users...")
    with Database() as db:
        db.insert_test_users()
    print("✅ Test data inserted!")