import os
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
from dotenv import load_dotenv

load_dotenv()

class Database:
    def __init__(self):
        self.client = None
        self.db = None
        self.connect()

    def connect(self):
        try:
            # Get MongoDB URI from environment
            mongodb_uri = os.getenv("MONGODB_URI")

            self.client = MongoClient(mongodb_uri)
            print("🔓 Using plain connection for local MongoDB")

            # Extract database name
            db_name = self._extract_database_name(mongodb_uri)

            if not db_name:
                # If no database name in URI, use default
                db_name = os.getenv("MONGODB_DB_NAME")

            self.db = self.client[db_name]

            # Test connection
            self.client.admin.command("ping")
            print("✅ Connected to MongoDB successfully")

            # Create indexes
            self.create_indexes()

        except ConnectionFailure as e:
            print(f"❌ MongoDB connection failed: {e}")
            # Try fallback connection
            self._try_fallback()
        except Exception as e:
            print(f"❌ Database connection error: {e}")
            self._try_fallback()

    def _try_fallback(self):
        """Try fallback local connection"""
        try:
            print("🔄 Trying fallback local connection...")
            mongodb_uri = os.getenv("FALLBACK_MONGODB_URI")
            self.client = MongoClient(mongodb_uri)
            self.db = self.client[os.getenv("MONGODB_DB_NAME")]
            self.client.admin.command("ping")
            print("✅ Connected to local MongoDB on fallback")
        except Exception as e:
            print(f"❌ Fallback connection also failed: {e}")
            raise

    def _extract_database_name(self, mongodb_uri):
        """Extract database name from MongoDB URI"""
        try:
            # Simple extraction - get part after last slash
            if "/" in mongodb_uri:
                parts = mongodb_uri.split("/")
                if len(parts) > 3:
                    db_part = parts[-1]
                    # Remove query parameters
                    if "?" in db_part:
                        db_name = db_part.split("?")[0]
                    else:
                        db_name = db_part
                    return db_name if db_name else None
            return None
        except:
            return None

    def create_indexes(self):
        try:
            # Create indexes if collections exist
            if "sessions" in self.db.list_collection_names():
                self.db.sessions.create_index("session_id", unique=True)

            if "users" in self.db.list_collection_names():
                self.db.users.create_index("email", unique=True)

            print("✅ Database indexes created/verified")
        except Exception as e:
            print(f"⚠️  Note: Could not create indexes: {e}")

    def get_database(self):
        return self.db

    def close_connection(self):
        if self.client:
            self.client.close()
            print("✅ MongoDB connection closed")


# Global database instance
db_instance = None

def get_database():
    global db_instance
    if db_instance is None:
        db_instance = Database()
    return db_instance.get_database()
