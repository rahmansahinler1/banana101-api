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
    
    def get_user_info(self, user_id):
        query = """
            SELECT user_id, user_name, user_surname, user_email, user_type, created_at
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
            logger.error(f"Database error fetching user info: {e}")
            self.conn.rollback()
            raise e
        except Exception as e:
            logger.error(f'Exception error fetching user info: {e}')
            self.conn.rollback()
            raise e
    
    def upload_file(self, user_id, category, file_bytes, preview_bytes):
        query = """
        INSERT INTO pictures (user_id, category, file_bytes, preview_bytes)
        VALUES (%s, %s, %s, %s)
        RETURNING picture_id, created_at
        """
        decoded_bytes = base64.b64decode(file_bytes)
        try:
            self.cursor.execute(query, (
                user_id,
                category,
                decoded_bytes,
                preview_bytes
            ))
            result = self.cursor.fetchone()
            picture_id = result[0]
            created_at = result[1]
            return {
                "picture_id": str(picture_id),
                "preview_base64": base64.b64encode(preview_bytes).decode('utf-8'),
                "created_at": created_at.isoformat()
            }
        except DatabaseError as e:
            logger.error(f'Database error while uploading files: {e}')
            self.conn.rollback()
            raise e
        except Exception as e:
            logger.error(f'Exception error while uploading files: {e}')
            self.conn.rollback()
            raise e
    
    def get_preview_images(self, user_id):
        query = """
        SELECT picture_id, category, preview_bytes, created_at
        FROM pictures
        WHERE user_id = %s
        ORDER BY created_at DESC
        """
        try:
            self.cursor.execute(query, (user_id,))
            data = self.cursor.fetchall()

            if not data:
                return {}
            
            # Get picture id and preview from fetched data
            result = {"yourself": [], "clothing": []}
            for row in data:
                category = row[1]
                result[category].append({
                    "id": str(row[0]),
                    "base64": base64.b64encode(row[2]).decode('utf-8'),
                    "created_at": row[3].isoformat()
                })
            return result
            
        except DatabaseError as e:
            logger.error(f'Database error while getting preview files: {e}')
            self.conn.rollback()
            raise e
        except Exception as e:
            logger.error(f'Exception error while getting preview files: {e}')
            self.conn.rollback()
            raise e
        
    def get_full_image(self, user_id, picture_id):
        query = """
        SELECT file_bytes
        FROM pictures
        WHERE user_id = %s AND picture_id = %s
        """
        try:
            self.cursor.execute(query, (user_id, picture_id))
            data = self.cursor.fetchone()

            if not data:
                return None
            
            return base64.b64encode(data[0]).decode('utf-8')
            
        except DatabaseError as e:
            logger.error(f'Database error while getting full image bytes: {e}')
            self.conn.rollback()
            raise e
        except Exception as e:
            logger.error(f'Exception error while gettin full image byes: {e}')
            self.conn.rollback()
            raise e

    def delete_picture(self, user_id, picture_id):
        query = """
        DELETE FROM pictures
        WHERE picture_id = %s AND user_id = %s
        """
        try:
            self.cursor.execute(query, (picture_id, user_id))
            # Check if any row was deleted
            if self.cursor.rowcount == 0:
                return False
            return True
        except DatabaseError as e:
            logger.error(f"Database error deleting picture: {e}")
            self.conn.rollback()
            raise e
        except Exception as e:
            logger.error(f'Exception error deleting picture: {e}')
            self.conn.rollback()
            raise e
