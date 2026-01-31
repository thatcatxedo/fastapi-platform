"""
Shared deployment helpers
"""
from kubernetes.client.rest import ApiException
from urllib.parse import urlparse, urlunparse, parse_qs, urlencode, quote_plus
import logging

from config import PLATFORM_NAMESPACE, MONGO_URI
from .k8s_client import custom_objects

logger = logging.getLogger(__name__)


def get_user_mongo_uri_legacy(user_id: str) -> str:
    """
    DEPRECATED: Construct per-user MongoDB URI using shared platform credentials.
    This is insecure and only used for backwards compatibility during migration.
    Use get_user_mongo_uri_secure() for new deployments.
    """
    base_uri = MONGO_URI if not MONGO_URI.endswith("/fastapi_platform_db") else MONGO_URI.replace("/fastapi_platform_db", "") + "/fastapi_platform_db"
    parsed = urlparse(base_uri)
    user_db_path = f"/user_{user_id}"
    return urlunparse((
        parsed.scheme,
        parsed.netloc,
        user_db_path,
        parsed.params,
        parsed.query,
        parsed.fragment
    ))


def get_user_mongo_uri_secure(user_id: str, user: dict, database_id: str = None) -> str:
    """
    Construct per-user MongoDB URI with user-specific credentials.

    Args:
        user_id: Platform user ID
        user: User document containing databases array
        database_id: Specific database ID, or None for user's default

    Returns:
        MongoDB URI with per-user credentials, or legacy URI if credentials not available
    """
    from mongo_users import decrypt_password, get_mongo_username, get_mongo_db_name

    # Determine which database to use
    if database_id is None:
        database_id = user.get("default_database_id", "default")

    databases = user.get("databases", [])

    # Find the database entry
    db_entry = next((db for db in databases if db["id"] == database_id), None)

    if not db_entry:
        # Fallback: try legacy single-database format for backwards compatibility
        encrypted_password = user.get("mongo_password_encrypted")
        if encrypted_password:
            logger.warning(f"Database {database_id} not found, using legacy credentials for user {user_id}")
            try:
                password = decrypt_password(encrypted_password)
                username = get_mongo_username(user_id)  # Legacy: no database_id
                db_name = f"user_{user_id}"  # Legacy: no database_id suffix

                base_uri = MONGO_URI if not MONGO_URI.endswith("/fastapi_platform_db") else MONGO_URI.replace("/fastapi_platform_db", "") + "/fastapi_platform_db"
                parsed = urlparse(base_uri)
                hostname = parsed.hostname or "localhost"
                port = parsed.port or 27017

                encoded_username = quote_plus(username)
                encoded_password = quote_plus(password)
                netloc = f"{encoded_username}:{encoded_password}@{hostname}:{port}"

                query_params = parse_qs(parsed.query)
                query_params['authSource'] = ['admin']
                query = urlencode(query_params, doseq=True)

                return urlunparse((
                    parsed.scheme, netloc, f"/{db_name}",
                    parsed.params, query, parsed.fragment
                ))
            except Exception as e:
                logger.error(f"Failed to decrypt legacy password for user {user_id}: {e}")

        logger.warning(f"No credentials found for user {user_id}, using legacy URI")
        return get_user_mongo_uri_legacy(user_id)

    # Multi-database: use database-specific credentials
    try:
        encrypted_password = db_entry.get("mongo_password_encrypted")
        if not encrypted_password:
            raise ValueError("No encrypted password in database entry")

        password = decrypt_password(encrypted_password)
        username = get_mongo_username(user_id, database_id)
        db_name = get_mongo_db_name(user_id, database_id)

        base_uri = MONGO_URI if not MONGO_URI.endswith("/fastapi_platform_db") else MONGO_URI.replace("/fastapi_platform_db", "") + "/fastapi_platform_db"
        parsed = urlparse(base_uri)

        # URL-encode username and password for safety
        encoded_username = quote_plus(username)
        encoded_password = quote_plus(password)

        # Determine host:port
        hostname = parsed.hostname or "localhost"
        port = parsed.port or 27017

        # Build new URI with user credentials
        netloc = f"{encoded_username}:{encoded_password}@{hostname}:{port}"

        # Set authSource=admin (user is created in admin db)
        query_params = parse_qs(parsed.query)
        query_params['authSource'] = ['admin']
        query = urlencode(query_params, doseq=True)

        return urlunparse((
            parsed.scheme,
            netloc,
            f"/{db_name}",
            parsed.params,
            query,
            parsed.fragment
        ))
    except Exception as e:
        logger.error(f"Failed to build secure MongoDB URI for user {user_id} database {database_id}: {e}")
        return get_user_mongo_uri_legacy(user_id)


def create_or_update_resource(create_fn, patch_fn, name: str, body, resource_type: str):
    """
    Create a K8s resource, or patch if it already exists (409 conflict).

    Args:
        create_fn: Function to create the resource (called with namespace, body)
        patch_fn: Function to patch the resource (called with name, namespace, body)
        name: Resource name (used for patching and logging)
        body: Resource body/spec
        resource_type: Human-readable type for logging (e.g., "Deployment", "Service")
    """
    try:
        create_fn(namespace=PLATFORM_NAMESPACE, body=body)
        logger.info(f"Created {resource_type} {name}")
    except ApiException as e:
        if e.status == 409:
            patch_fn(name=name, namespace=PLATFORM_NAMESPACE, body=body)
            logger.info(f"Updated {resource_type} {name}")
        else:
            raise


def create_or_update_custom_object(name: str, body: dict, resource_type: str):
    """
    Create a Traefik IngressRoute custom object, or patch if it already exists.

    Args:
        name: Resource name
        body: Resource body/spec (dict)
        resource_type: Human-readable type for logging
    """
    try:
        custom_objects.create_namespaced_custom_object(
            group="traefik.io",
            version="v1alpha1",
            namespace=PLATFORM_NAMESPACE,
            plural="ingressroutes",
            body=body
        )
        logger.info(f"Created {resource_type} {name}")
    except ApiException as e:
        if e.status == 409:
            custom_objects.patch_namespaced_custom_object(
                group="traefik.io",
                version="v1alpha1",
                namespace=PLATFORM_NAMESPACE,
                plural="ingressroutes",
                name=name,
                body=body
            )
            logger.info(f"Updated {resource_type} {name}")
        else:
            raise
