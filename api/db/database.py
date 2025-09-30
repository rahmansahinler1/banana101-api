from psycopg2 import extras
from psycopg2 import DatabaseError
from pathlib import Path
from datetime import datetime
import psycopg2
import logging
import uuid
import base64

from .utils.config import GenerateConfig

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Database:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Database, cls).__new__(cls)
            cls._instance.db_config = GenerateConfig.config()
        return cls._instance

    def __enter__(self):
        self.conn = psycopg2.connect(**self.db_config)
        self.cursor = self.conn.cursor()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.cursor:
            self.cursor.close()
        if self.conn:
            if exc_type is None:
                self.conn.commit()
            else:
                self.conn.rollback()
            self.conn.close()

    def initialize_database(self):
        sql_path = Path(__file__).resolve().parent / "sql" / "initialize.sql"
        with sql_path.open("r") as file:
            query = file.read()
        try:
            self.cursor.execute(query)
            self.conn.commit()
        except DatabaseError as e:
            self.conn.rollback()
            raise e
    
    def insert_test_users(self):
        sql_path = Path(__file__).resolve().parent / "sql" / "insert_test_data.sql"
        with sql_path.open("r") as file:
            query = file.read()
        try:
            self.cursor.execute(query)
            self.conn.commit()
        except DatabaseError as e:
            self.conn.rollback()
            raise e

    def reset_database(self):
        sql_path = Path(__file__).resolve().parent / "sql" / "reset.sql"
        with sql_path.open("r") as file:
            query = file.read()
        try:
            self.cursor.execute(query)
            self.conn.commit()
        except DatabaseError as e:
            self.conn.rollback()
            raise e
        
    def get_init_data(self, user_id):
        try:
            user_info = self.get_user_info(user_id)
            return user_info
        except DatabaseError as e:
            self.conn.rollback()
            raise e
            
        except DatabaseError as e:
            logger.error(f"Error in get_init_data: {e}")
            raise e
    
    def get_user_info(self, user_id):
        query = """
            SELECT user_id, user_name, user_surname, user_email, user_type, user_created_at
            FROM user_info 
            WHERE user_id = %s
        """
        try:
            self.cursor.execute(query, (user_id,))
            result = self.cursor.fetchone()
            
            if result:
                return {
                    "user_id": str(result[0]),
                    "user_name": result[1],
                    "user_surname": result[2], 
                    "user_email": result[3],
                    "user_type": result[4],
                    "user_created_at": result[5].isoformat() if result[5] else None
                }
            return None
            
        except DatabaseError as e:
            logger.error(f"Error fetching user info: {e}")
            raise e
    
    def upload_file(self, user_id, category, file_bytes):
        query = """
        INSERT INTO pictures (user_id, category, file_bytes)
        VALUES (%s, %s, %s)
        """
        decoded_bytes = base64.b64decode(file_bytes)
        try:
            self.cursor.execute(query, (
                user_id,
                category,
                decoded_bytes
            ))
            return True
        except DatabaseError as e:
            logger.error(f'Error while uploading files: {e}')
            self.conn.rollback()
            raise e
        except Exception as e:
            logger.error(f'Error while uploading files: {e}')
            self.conn.rollback()
            raise e
        