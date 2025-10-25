import psycopg2
import logging
import sys
from configparser import ConfigParser
from pathlib import Path


logger = logging.getLogger(__name__)

class MigrationRunner:
    def __init__(self):
        self.db_config = self._config()
        self.migrations_dir = Path(__file__).parent / "migrations"

    def _config(self, config_path="api/db/database.ini", section="postgresql"):
        parser = ConfigParser()
        parser.read(config_path)
        db_config = {}
        if parser.has_section(section):
            params = parser.items(section)
            for param in params:
                db_config[param[0]] = param[1]
        else:
            raise Exception(f"Section {section} is not found in {config_path} file.")
        return db_config

    def get_migration_files(self):
        files = sorted(self.migrations_dir.glob("v*.sql"))
        return files

    def apply_migration(self, cursor, migration_file):
        """Apply a single migration file"""
        version = migration_file.stem.split('_')[0]

        logger.info(f"Applying migration: {migration_file.name}")

        with migration_file.open('r') as f:
            sql = f.read()

        try:
            cursor.execute(sql)
            return True
        except Exception as e:
            logger.error(f"✗ Migration {version} failed: {e}")
            raise

    def run_all_migrations(self):
        conn = psycopg2.connect(**self.db_config)
        conn.autocommit = False
        cursor = conn.cursor()

        try:
            migration_files = self.get_migration_files()
            logger.info(f"Found {len(migration_files)} migration file(s)")

            for migration_file in migration_files:
                self.apply_migration(cursor, migration_file)

            conn.commit()
            logger.info(f"✓ Successfully applied {len(migration_files)} migration(s)")

        except Exception as e:
            conn.rollback()
            logger.error(f"✗ Migration failed, rolled back: {e}")
            raise
        finally:
            cursor.close()
            conn.close()

    def run_specific_migration(self, target_version):
        conn = psycopg2.connect(**self.db_config)
        conn.autocommit = False
        cursor = conn.cursor()

        try:
            migration_files = self.get_migration_files()
            logger.info(f"Target migration: {target_version}")

            # Find the specific migration file
            target_file = None
            for migration_file in migration_files:
                version = migration_file.stem.split('_')[0]
                if version == target_version:
                    target_file = migration_file
                    break

            if not target_file:
                logger.error(f"✗ Migration {target_version} not found")
                logger.info(f"Available migrations: {[f.stem.split('_')[0] for f in migration_files]}")
                return

            # Apply the specific migration
            self.apply_migration(cursor, target_file)
            conn.commit()
            logger.info(f"✓ Successfully applied migration {target_version}")

        except Exception as e:
            conn.rollback()
            logger.error(f"✗ Migration failed, rolled back: {e}")
            raise
        finally:
            cursor.close()
            conn.close()

    def reset_database(self):
        reset_file = Path(__file__).parent / "migrations" / "reset.sql"

        conn = psycopg2.connect(**self.db_config)
        conn.autocommit = False
        cursor = conn.cursor()

        try:
            with reset_file.open('r') as f:
                sql = f.read()
            cursor.execute(sql)
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"✗ Reset failed: {e}")
            raise
        finally:
            cursor.close()
            conn.close()

def main():
    # Show usage if no arguments
    if len(sys.argv) < 2:
        logger.error("✗ No operation specified")
        logger.info("")
        logger.info("Usage:")
        logger.info("  python -m api.db.migrate --reset      # Reset database (deletes everything)")
        logger.info("  python -m api.db.migrate --all        # Run all migrations from v0")
        logger.info("  python -m api.db.migrate --v0         # Run only v0 migration")
        logger.info("  python -m api.db.migrate --v1         # Run only v1 migration")
        logger.info("  python -m api.db.migrate --v2         # Run only v2 migration (etc.)")
        logger.info("")
        return

    runner = MigrationRunner()
    arg = sys.argv[1]

    if arg == "--reset":
        confirm = input("⚠️  This will DELETE ALL DATA. Type 'YES' to confirm: ")
        if confirm == "YES":
            runner.reset_database()
            logger.info("✓ Database reset complete (no migrations applied)")
        else:
            logger.info("Reset cancelled")

    elif arg == "--all":
        logger.info("Running all migrations...")
        runner.run_all_migrations()

    elif arg.startswith("--v"):
        # Extract version number (e.g., --v1 -> v1)
        version_str = arg[2:]  # Remove '--' prefix
        if not version_str.startswith('v'):
            version_str = 'v' + version_str
        runner.run_specific_migration(version_str)

    else:
        logger.error(f"✗ Unknown argument: {arg}")
        logger.info("")
        logger.info("Usage:")
        logger.info("  python -m api.db.migrate --reset      # Reset database (deletes everything)")
        logger.info("  python -m api.db.migrate --all        # Run all migrations from v0")
        logger.info("  python -m api.db.migrate --v0         # Run only v0 migration")
        logger.info("  python -m api.db.migrate --v1         # Run only v1 migration")
        logger.info("")

if __name__ == "__main__":
    main()
