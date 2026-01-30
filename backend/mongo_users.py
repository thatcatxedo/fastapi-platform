"""
MongoDB user management for per-user authentication.

This module handles creating, retrieving, and deleting MongoDB users
for platform users, ensuring each user can only access their own database.
"""
import os
import secrets
import logging
import base64
from typing import Optional, Tuple
from urllib.parse import urlparse, urlunparse, quote_plus

from motor.motor_asyncio import AsyncIOMotorClient
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

logger = logging.getLogger(__name__)

# MongoDB connection
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")


def _get_encryption_key() -> bytes:
    """
    Derive a Fernet-compatible encryption key from SECRET_KEY.
    Uses PBKDF2 to derive a 32-byte key suitable for Fernet.
    """
    secret_key = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")
    salt = b"fastapi-platform-mongo-users"  # Static salt for deterministic key derivation
    
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
    )
    key = base64.urlsafe_b64encode(kdf.derive(secret_key.encode()))
    return key


def encrypt_password(password: str) -> str:
    """Encrypt a password for storage."""
    key = _get_encryption_key()
    f = Fernet(key)
    encrypted = f.encrypt(password.encode())
    return encrypted.decode()


def decrypt_password(encrypted_password: str) -> str:
    """Decrypt a stored password."""
    key = _get_encryption_key()
    f = Fernet(key)
    decrypted = f.decrypt(encrypted_password.encode())
    return decrypted.decode()


def generate_mongo_password() -> str:
    """Generate a secure random password for MongoDB user."""
    return secrets.token_urlsafe(24)


def get_mongo_username(user_id: str) -> str:
    """Get MongoDB username for a platform user."""
    return f"user_{user_id}"


async def create_mongo_user(client: AsyncIOMotorClient, user_id: str) -> Tuple[str, str]:
    """
    Create a MongoDB user for a platform user.
    
    Args:
        client: MongoDB client with admin privileges
        user_id: Platform user ID
        
    Returns:
        Tuple of (username, password)
    """
    username = get_mongo_username(user_id)
    password = generate_mongo_password()
    db_name = f"user_{user_id}"
    
    admin_db = client.admin
    
    try:
        # Check if user already exists
        users_info = await admin_db.command("usersInfo", username)
        if users_info.get("users"):
            logger.info(f"MongoDB user {username} already exists, updating password")
            # Update existing user's password
            await admin_db.command(
                "updateUser",
                username,
                pwd=password,
                roles=[{"role": "readWrite", "db": db_name}]
            )
        else:
            # Create new user
            await admin_db.command(
                "createUser",
                username,
                pwd=password,
                roles=[{"role": "readWrite", "db": db_name}]
            )
            logger.info(f"Created MongoDB user {username} with readWrite on {db_name}")
    except Exception as e:
        logger.error(f"Failed to create MongoDB user {username}: {e}")
        raise
    
    return username, password


async def delete_mongo_user(client: AsyncIOMotorClient, user_id: str) -> bool:
    """
    Delete a MongoDB user for a platform user.
    
    Args:
        client: MongoDB client with admin privileges
        user_id: Platform user ID
        
    Returns:
        True if user was deleted, False if user didn't exist
    """
    username = get_mongo_username(user_id)
    admin_db = client.admin
    
    try:
        # Check if user exists
        users_info = await admin_db.command("usersInfo", username)
        if not users_info.get("users"):
            logger.info(f"MongoDB user {username} does not exist, nothing to delete")
            return False
        
        await admin_db.command("dropUser", username)
        logger.info(f"Deleted MongoDB user {username}")
        return True
    except Exception as e:
        logger.error(f"Failed to delete MongoDB user {username}: {e}")
        raise


async def verify_mongo_user_exists(client: AsyncIOMotorClient, user_id: str) -> bool:
    """Check if a MongoDB user exists for a platform user."""
    username = get_mongo_username(user_id)
    admin_db = client.admin
    
    try:
        users_info = await admin_db.command("usersInfo", username)
        return bool(users_info.get("users"))
    except Exception as e:
        logger.error(f"Failed to check MongoDB user {username}: {e}")
        return False


def build_user_mongo_uri(user_id: str, password: str) -> str:
    """
    Build a MongoDB connection string with per-user credentials.
    
    Args:
        user_id: Platform user ID
        password: User's MongoDB password (decrypted)
        
    Returns:
        MongoDB URI with user-specific credentials and database
    """
    base_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017/fastapi_platform_db")
    parsed = urlparse(base_uri)
    
    username = get_mongo_username(user_id)
    db_name = f"user_{user_id}"
    
    # URL-encode username and password for safety
    encoded_username = quote_plus(username)
    encoded_password = quote_plus(password)
    
    # Determine host:port
    hostname = parsed.hostname or "localhost"
    port = parsed.port or 27017
    
    # Build new URI with user credentials
    # Preserve query parameters (like authSource, replicaSet, etc.)
    netloc = f"{encoded_username}:{encoded_password}@{hostname}:{port}"
    
    # Add authSource if not present (user is created in admin db)
    query = parsed.query
    if "authSource" not in query:
        if query:
            query = f"{query}&authSource=admin"
        else:
            query = "authSource=admin"
    
    return urlunparse((
        parsed.scheme,
        netloc,
        f"/{db_name}",
        parsed.params,
        query,
        parsed.fragment
    ))


async def get_user_mongo_uri_from_db(
    client: AsyncIOMotorClient,
    user_id: str,
    users_collection
) -> Optional[str]:
    """
    Get the MongoDB URI for a user by fetching their encrypted password from the database.
    
    Args:
        client: MongoDB client
        user_id: Platform user ID
        users_collection: The users collection from the platform database
        
    Returns:
        MongoDB URI with user credentials, or None if user not found
    """
    from bson import ObjectId
    
    user = await users_collection.find_one({"_id": ObjectId(user_id)})
    if not user:
        logger.error(f"User {user_id} not found in database")
        return None
    
    encrypted_password = user.get("mongo_password_encrypted")
    if not encrypted_password:
        logger.error(f"User {user_id} does not have MongoDB credentials")
        return None
    
    try:
        password = decrypt_password(encrypted_password)
        return build_user_mongo_uri(user_id, password)
    except Exception as e:
        logger.error(f"Failed to decrypt MongoDB password for user {user_id}: {e}")
        return None
