import psycopg2
import logging
import base64
from psycopg2 import DatabaseError
from configparser import ConfigParser

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Database:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Database, cls).__new__(cls)
            cls._instance.db_config = cls._config()
        return cls._instance

    def __enter__(self):
        self.conn = psycopg2.connect(**self.db_config)
        self.cursor = self.conn.cursor()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if hasattr(self, "cursor") and self.cursor:
            self.cursor.close()
        if hasattr(self, "conn") and self.conn:
            if exc_type is None:
                self.conn.commit()
            else:
                self.conn.rollback()
            self.conn.close()

    def _config(filename="api/db/database.ini", section="postgresql"):
        parser = ConfigParser()
        parser.read(filename)
        db_config = {}
        if parser.has_section(section):
            for key, value in parser.items(section):
                db_config[key] = value
        else:
            raise Exception(f"Section {section} not found in {filename}")
        return db_config
    
    def get_user_info(
            self,
            user_id
        ):
        query = """
            SELECT user_id, user_name, user_surname, user_email, user_type, created_at
            FROM users
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
    
    def insert_image(
            self,
            user_id,
            category,
            image_bytes,
            preview_bytes
        ):
        query = """
        INSERT INTO images (user_id, category, image_bytes, preview_bytes)
        VALUES (%s, %s, %s, %s)
        RETURNING image_id, created_at
        """
        try:
            self.cursor.execute(query, (
                user_id,
                category,
                image_bytes,
                preview_bytes
            ))
            result = self.cursor.fetchone()
            image_id = result[0]
            created_at = result[1]
            return {
                "image_id": str(image_id),
                "preview_base64": base64.b64encode(preview_bytes).decode('utf8'),
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
    
    def insert_generated_image(
            self,
            user_id,
            yourself_image_id,
            clothing_image_id,
            generated_image_bytes,
            generated_preview_bytes
        ):
        query = """
        INSERT INTO generations (user_id, yourself_image_id, clothing_image_id, image_bytes, preview_bytes)
        VALUES (%s, %s, %s, %s, %s)
        RETURNING image_id, created_at
        """
        try:
            self.cursor.execute(query, (
                user_id,
                yourself_image_id,
                clothing_image_id,
                generated_image_bytes,
                generated_preview_bytes
            ))
            result = self.cursor.fetchone()
            image_id = result[0]
            created_at = result[1]
            return {
                "image_id": str(image_id),
                "preview_base64": base64.b64encode(generated_preview_bytes).decode('utf8'),
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
    
    def get_preview_images(
            self,
            user_id
        ):
        query = """
        SELECT image_id, category, preview_bytes, faved, created_at
        FROM images
        WHERE user_id = %s
        ORDER BY created_at DESC
        """
        try:
            self.cursor.execute(query, (user_id,))
            data = self.cursor.fetchall()

            if not data:
                return {}

            # Get image id and preview from fetched data
            result = {"yourself": [], "clothing": []}
            for row in data:
                category = row[1]
                result[category].append({
                    "id": str(row[0]),
                    "base64": base64.b64encode(row[2]).decode('utf-8'),
                    "faved": row[3],
                    "created_at": row[4].isoformat()
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
    
    def get_preview_generations(
            self,
            user_id
        ):
        query = """
        SELECT image_id, preview_bytes, faved, created_at
        FROM generations
        WHERE user_id = %s
        ORDER BY created_at DESC
        """
        try:
            self.cursor.execute(query, (user_id,))
            data = self.cursor.fetchall()

            if not data:
                return []
            
            # Get image id and preview from fetched data
            result = []
            for row in data:
                result.append({
                    "id": str(row[0]),
                    "base64": base64.b64encode(row[1]).decode('utf-8'),
                    "faved": row[2],
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
        
    def get_full_image(
            self,
            user_id,
            image_id
        ):
        query = """
        SELECT image_bytes
        FROM images
        WHERE user_id = %s AND image_id = %s
        """
        try:
            self.cursor.execute(query, (user_id, image_id))
            data = self.cursor.fetchone()

            if not data:
                return None

            return data[0]

        except DatabaseError as e:
            logger.error(f'Database error while getting full image bytes: {e}')
            self.conn.rollback()
            raise e
        except Exception as e:
            logger.error(f'Exception error while gettin full image byes: {e}')
            self.conn.rollback()
            raise e

    def get_full_generated_image(
            self,
            user_id,
            image_id
        ):
        query = """
        SELECT image_bytes
        FROM generations
        WHERE user_id = %s AND image_id = %s
        """
        try:
            self.cursor.execute(query, (user_id, image_id))
            data = self.cursor.fetchone()

            if not data:
                return None

            return data[0]

        except DatabaseError as e:
            logger.error(f'Database error while getting full generated image bytes: {e}')
            self.conn.rollback()
            raise e
        except Exception as e:
            logger.error(f'Exception error while getting full generated image bytes: {e}')
            self.conn.rollback()
            raise e

    def delete_image(
            self,
            user_id,
            image_id
        ):
        query = """
        DELETE FROM images
        WHERE image_id = %s AND user_id = %s
        """
        try:
            self.cursor.execute(query, (image_id, user_id))
            # Check if any row was deleted
            if self.cursor.rowcount == 0:
                return False
            return True
        except DatabaseError as e:
            logger.error(f"Database error deleting image: {e}")
            self.conn.rollback()
            raise e
        except Exception as e:
            logger.error(f'Exception error deleting image: {e}')
            self.conn.rollback()
            raise e
    
    def delete_generated_image(
            self,
            user_id,
            image_id
        ):
        query = """
        DELETE FROM generations
        WHERE image_id = %s AND user_id = %s
        """
        try:
            self.cursor.execute(query, (image_id, user_id))
            # Check if any row was deleted
            if self.cursor.rowcount == 0:
                return False
            return True
        except DatabaseError as e:
            logger.error(f"Database error deleting image: {e}")
            self.conn.rollback()
            raise e
        except Exception as e:
            logger.error(f'Exception error deleting image: {e}')
            self.conn.rollback()
            raise e
    
    def update_fav(
            self,
            user_id,
            image_id
        ):
        query = """
        UPDATE generations
        SET faved = NOT faved
        WHERE image_id = %s AND user_id = %s
        RETURNING faved
        """
        try:
            self.cursor.execute(query, (image_id, user_id))
            result = self.cursor.fetchone()

            # Check if any row was updated
            if not result:
                return False

            return True
        except DatabaseError as e:
            logger.error(f"Database error updating fav: {e}")
            self.conn.rollback()
            raise e
        except Exception as e:
            logger.error(f'Exception error updating fav: {e}')
            self.conn.rollback()
            raise e

    def update_image_fav(
            self,
            user_id,
            image_id
        ):
        query = """
        UPDATE images
        SET faved = NOT faved
        WHERE image_id = %s AND user_id = %s
        RETURNING faved
        """
        try:
            self.cursor.execute(query, (image_id, user_id))
            result = self.cursor.fetchone()

            # Check if any row was updated
            if not result:
                return False

            return True
        except DatabaseError as e:
            logger.error(f"Database error updating image fav: {e}")
            self.conn.rollback()
            raise e
        except Exception as e:
            logger.error(f'Exception error updating image fav: {e}')
            self.conn.rollback()
            raise e
    
    def get_image(
            self,
            user_id,
            image_id
        ):
        query = """
        SELECT image_bytes
        FROM images
        WHERE user_id = %s AND image_id = %s
        """
        try:
            # Get yourself image
            self.cursor.execute(query, (user_id, image_id))
            data = self.cursor.fetchone()
            if not data:
                return None
            image_bytes = bytes(data[0])
            
            return image_bytes
            
        except DatabaseError as e:
            logger.error(f'Database error while getting preview files: {e}')
            self.conn.rollback()
            raise e
        except Exception as e:
            logger.error(f'Exception error while getting preview files: {e}')
            self.conn.rollback()
            raise e
