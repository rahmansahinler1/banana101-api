import psycopg2
import logging
import base64
import calendar
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
            SELECT user_name, user_surname, user_email, picture_url, user_type, uploads_left, generations_left, recents_left, last_payment_at
            FROM users
            WHERE user_id = %s
        """
        try:
            self.cursor.execute(query, (user_id,))
            result = self.cursor.fetchone()

            if result:
                last_payment = result[8]
                next_renewal = None

                # Calculate next renewal date if premium and has last_payment_at
                if last_payment and result[4] == 'premium':
                    # Add exactly 1 month (handles month-end edge cases properly)
                    year = last_payment.year
                    month = last_payment.month
                    day = last_payment.day

                    # Increment month
                    if month == 12:
                        month = 1
                        year += 1
                    else:
                        month += 1

                    # Handle day overflow (e.g., Jan 31 -> Feb 28/29)
                    max_day = calendar.monthrange(year, month)[1]
                    day = min(day, max_day)

                    next_renewal_date = last_payment.replace(year=year, month=month, day=day)
                    next_renewal = next_renewal_date.strftime("%b %d, %Y")

                return {
                    "name": result[0],
                    "surname": result[1],
                    "email": result[2],
                    "picture_url": result[3],
                    "type": result[4],
                    "uploads_left": result[5],
                    "generations_left": result[6],
                    "recents_left": result[7],
                    "next_renewal_date": next_renewal
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
        # Check if user has upload credits
        credit_check_query = """
        SELECT uploads_left FROM users WHERE user_id = %s
        """

        insert_query = """
        INSERT INTO images (user_id, category, image_bytes, preview_bytes)
        VALUES (%s, %s, %s, %s)
        RETURNING image_id, created_at
        """

        decrement_query = """
        UPDATE users SET uploads_left = uploads_left - 1
        WHERE user_id = %s
        RETURNING uploads_left
        """

        try:
            # Step 1: Check credits
            self.cursor.execute(credit_check_query, (user_id,))
            credit_result = self.cursor.fetchone()

            if not credit_result or credit_result[0] <= 0:
                raise Exception("Insufficient upload credits")

            # Step 2: Insert image
            self.cursor.execute(insert_query, (
                user_id,
                category,
                image_bytes,
                preview_bytes
            ))
            result = self.cursor.fetchone()
            image_id = result[0]
            created_at = result[1]

            # Step 3: Decrement credit
            self.cursor.execute(decrement_query, (user_id,))
            new_credits = self.cursor.fetchone()[0]

            return {
                "image_id": str(image_id),
                "preview_base64": base64.b64encode(preview_bytes).decode('utf8'),
                "created_at": created_at.isoformat(),
                "uploads_left": new_credits
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
        # Check if user has generation credits
        credit_check_query = """
        SELECT generations_left, recents_left FROM users WHERE user_id = %s
        """

        insert_query = """
        INSERT INTO generations (user_id, yourself_image_id, clothing_image_id, image_bytes, preview_bytes)
        VALUES (%s, %s, %s, %s, %s)
        RETURNING image_id, created_at
        """

        decrement_query = """
        UPDATE users SET generations_left = generations_left - 1, recents_left = recents_left - 1
        WHERE user_id = %s
        RETURNING generations_left, recents_left
        """

        try:
            self.cursor.execute(credit_check_query, (user_id,))
            credit_result = self.cursor.fetchone()

            if not credit_result or credit_result[0] <= 0:
                raise Exception("Insufficient generation credits")

            if credit_result[1] <= 0:
                raise Exception("Insufficient recents storage")

            self.cursor.execute(insert_query, (
                user_id,
                yourself_image_id,
                clothing_image_id,
                generated_image_bytes,
                generated_preview_bytes
            ))
            result = self.cursor.fetchone()
            image_id = result[0]
            created_at = result[1]

            self.cursor.execute(decrement_query, (user_id,))
            new_credits = self.cursor.fetchone()

            return {
                "image_id": str(image_id),
                "preview_base64": base64.b64encode(generated_preview_bytes).decode('utf8'),
                "created_at": created_at.isoformat(),
                "generations_left": new_credits[0],
                "recents_left": new_credits[1]
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
        delete_query = """
        DELETE FROM images
        WHERE image_id = %s AND user_id = %s
        """

        increment_query = """
        UPDATE users SET uploads_left = uploads_left + 1
        WHERE user_id = %s
        RETURNING uploads_left
        """

        try:
            self.cursor.execute(delete_query, (image_id, user_id))
            if self.cursor.rowcount == 0:
                return None

            self.cursor.execute(increment_query, (user_id,))
            result = self.cursor.fetchone()
            return {"uploads_left": result[0]}
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
        delete_query = """
        DELETE FROM generations
        WHERE image_id = %s AND user_id = %s
        """

        increment_query = """
        UPDATE users SET recents_left = recents_left + 1
        WHERE user_id = %s
        """

        try:
            self.cursor.execute(delete_query, (image_id, user_id))
            if self.cursor.rowcount == 0:
                return False

            self.cursor.execute(increment_query, (user_id,))
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

    def insert_feedback(
            self,
            user_id,
            message
        ):
        # Check if user has already submitted 5 or more feedbacks
        count_query = """
        SELECT COUNT(*) FROM feedbacks WHERE user_id = %s
        """

        insert_query = """
        INSERT INTO feedbacks (user_id, message)
        VALUES (%s, %s)
        RETURNING feedback_id, created_at
        """

        try:
            # Check feedback count
            self.cursor.execute(count_query, (user_id,))
            count_result = self.cursor.fetchone()

            if count_result and count_result[0] >= 5:
                raise Exception("Feedback limit reached!")

            # Insert feedback
            self.cursor.execute(insert_query, (user_id, message))
            result = self.cursor.fetchone()
            feedback_id = result[0]
            created_at = result[1]
            return {
                "feedback_id": str(feedback_id),
                "created_at": created_at.isoformat()
            }
        except DatabaseError as e:
            logger.error(f'Database error while inserting feedback: {e}')
            self.conn.rollback()
            raise e
        except Exception as e:
            logger.error(f'Exception error while inserting feedback: {e}')
            self.conn.rollback()
            raise e

    def get_user_by_email(self, email):
        query = """
        SELECT user_id
        FROM users
        WHERE user_email = %s
        """
        try:
            self.cursor.execute(query, (email,))
            result = self.cursor.fetchone()

            if result:
                return {
                    "user_id": str(result[0])
                }
            return None

        except DatabaseError as e:
            logger.error(f"Database error fetching user by email: {e}")
            self.conn.rollback()
            raise e
        except Exception as e:
            logger.error(f'Exception error fetching user by email: {e}')
            self.conn.rollback()
            raise e

    def create_google_user(self, email, name, surname, picture_url, google_id):
        insert_query = """
        INSERT INTO users (user_name, user_surname, user_email, google_id, picture_url)
        VALUES (%s, %s, %s, %s, %s)
        RETURNING user_id
        """

        try:
            self.cursor.execute(insert_query, (
                name or "",
                surname or "",
                email,
                google_id,
                picture_url or ""
            ))
            result = self.cursor.fetchone()
            user_id = str(result[0])
            return user_id

        except DatabaseError as e:
            logger.error(f"Database error creating Google user: {e}")
            self.conn.rollback()
            raise e
        except Exception as e:
            logger.error(f'Exception error creating Google user: {e}')
            self.conn.rollback()
            raise e
