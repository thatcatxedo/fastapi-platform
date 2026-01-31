# Multi-Database Per User Architecture

This document details how to evolve the platform from single-database-per-user to supporting multiple isolated databases per user.

## Current Architecture

### Single Database Per User

Each user currently gets one MongoDB database named `user_{user_id}`:

```
user_6758f3c2a1b2c3d4e5f6g7h8
├── collection_1
├── collection_2
└── collection_n
```

**How it works today:**
1. User signs up → `create_mongo_user()` creates MongoDB user with `readWrite` role on `user_{user_id}`
2. Password stored encrypted in user document (`mongo_password_encrypted`)
3. Apps get `PLATFORM_MONGO_URI` injected at deploy time
4. URI format: `mongodb://user_{id}:{password}@{host}/user_{id}?authSource=admin`

**Key files:**
- `backend/migrations/mongo_users.py` - User creation, password encryption
- `backend/deployment/helpers.py` - URI generation (`get_user_mongo_uri_secure()`)
- `backend/deployment/apps.py` - Injects `PLATFORM_MONGO_URI` into pod env
- `backend/routers/database.py` - Stats endpoint for single database

---

## Proposed Architecture

### Multiple Databases Per User

Allow users to create multiple isolated databases:

```
user_6758f3c2a1b2c3d4e5f6g7h8_default     (created on signup)
user_6758f3c2a1b2c3d4e5f6g7h8_production  (user-created)
user_6758f3c2a1b2c3d4e5f6g7h8_staging     (user-created)
```

Each database has:
- Its own MongoDB user (for credential isolation)
- Its own password (independent rotation)
- User-friendly name + unique ID

---

## Schema Changes

### User Document

**Current:**
```python
{
    "_id": ObjectId,
    "username": str,
    "email": str,
    "password_hash": str,
    "created_at": datetime,
    "is_admin": bool,
    "mongo_password_encrypted": str  # Single password
}
```

**Proposed:**
```python
{
    "_id": ObjectId,
    "username": str,
    "email": str,
    "password_hash": str,
    "created_at": datetime,
    "is_admin": bool,

    # NEW: Multi-database support
    "databases": [
        {
            "id": str,                        # Unique ID (e.g., "default", UUID)
            "name": str,                      # User-friendly name
            "mongo_password_encrypted": str,  # Per-database password
            "created_at": datetime,
            "is_default": bool,               # Default for new apps
            "description": Optional[str]
        }
    ],
    "default_database_id": str,

    # DEPRECATED: Keep for backwards compatibility
    "mongo_password_encrypted": str
}
```

### App Document

**Add database association:**
```python
{
    "_id": ObjectId,
    "user_id": ObjectId,
    "app_id": str,
    "name": str,
    "database_id": Optional[str],  # NEW: Which database this app uses
                                   # If None, uses user's default
    # ... existing fields ...
}
```

---

## MongoDB User Strategy

### Recommended: One MongoDB User Per Database

Each database gets its own MongoDB user for complete isolation:

```javascript
// Database 1: user_xxx_default
db.createUser({
    user: "user_xxx_default",
    pwd: "password_for_default",
    roles: [{ role: "readWrite", db: "user_xxx_default" }]
})

// Database 2: user_xxx_production
db.createUser({
    user: "user_xxx_production",
    pwd: "password_for_production",
    roles: [{ role: "readWrite", db: "user_xxx_production" }]
})
```

**Benefits:**
- Independent password rotation per database
- Can revoke access to one database without affecting others
- Better security isolation
- Simpler mental model

**Trade-off:**
- More MongoDB users to manage (but automated)

---

## API Design

### New Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/databases` | List all user's databases |
| `POST` | `/api/databases` | Create new database |
| `GET` | `/api/databases/{id}` | Get database details + stats |
| `PATCH` | `/api/databases/{id}` | Update name, description, set as default |
| `DELETE` | `/api/databases/{id}` | Delete database (with safeguards) |
| `POST` | `/api/databases/{id}/rotate` | Rotate credentials |

### Create Database

```http
POST /api/databases
Content-Type: application/json

{
    "name": "production",
    "description": "Production database for live apps"
}
```

**Response:**
```json
{
    "id": "prod_a1b2c3",
    "name": "production",
    "mongo_database": "user_xxx_prod_a1b2c3",
    "is_default": false,
    "created_at": "2026-01-31T12:00:00Z"
}
```

### List Databases

```http
GET /api/databases
```

**Response:**
```json
{
    "databases": [
        {
            "id": "default",
            "name": "Default",
            "is_default": true,
            "total_collections": 5,
            "total_size_mb": 12.5,
            "created_at": "2026-01-01T00:00:00Z"
        },
        {
            "id": "prod_a1b2c3",
            "name": "production",
            "is_default": false,
            "total_collections": 3,
            "total_size_mb": 45.2,
            "created_at": "2026-01-31T12:00:00Z"
        }
    ],
    "total_size_mb": 57.7
}
```

### Delete Database

```http
DELETE /api/databases/{id}
```

**Safeguards:**
- Cannot delete the last database
- Cannot delete the default database (must change default first)
- Option: Require confirmation if apps are using this database
- Option: Auto-migrate apps to default, or block deletion

---

## URI Generation Changes

### Current (`deployment/helpers.py`)

```python
def get_user_mongo_uri_secure(user_id: str, user: dict) -> str:
    # Returns URI for single database: user_{user_id}
```

### Proposed

```python
def get_user_mongo_uri_secure(
    user_id: str,
    user: dict,
    database_id: Optional[str] = None
) -> str:
    """
    Get MongoDB URI for a specific user database.

    Args:
        user_id: Platform user ID
        user: User document from MongoDB
        database_id: Specific database ID, or None for default

    Returns:
        MongoDB connection string for the specified database
    """
    # Find the database record
    if database_id is None:
        database_id = user.get("default_database_id", "default")

    databases = user.get("databases", [])

    # Backwards compatibility: no databases array
    if not databases:
        return get_user_mongo_uri_legacy(user_id, user)

    database = next(
        (db for db in databases if db["id"] == database_id),
        None
    )

    if not database:
        raise ValueError(f"Database {database_id} not found for user")

    # Build URI for this specific database
    mongo_username = f"user_{user_id}_{database_id}"
    mongo_password = decrypt_password(database["mongo_password_encrypted"])
    mongo_db_name = f"user_{user_id}_{database_id}"

    # Parse base URI for host/port
    parsed = urlparse(MONGO_URI)
    host = parsed.hostname
    port = parsed.port or 27017

    return f"mongodb://{mongo_username}:{quote_plus(mongo_password)}@{host}:{port}/{mongo_db_name}?authSource=admin"
```

### App Deployment Update

```python
# In deployment/apps.py
async def deploy_app(...):
    # Get the database this app should use
    app_database_id = app_doc.get("database_id")  # May be None

    # Generate URI for correct database
    mongo_uri = get_user_mongo_uri_secure(
        user_id,
        user,
        database_id=app_database_id
    )

    env_list = [
        k8s_client.V1EnvVar(name="CODE_PATH", value=code_path),
        k8s_client.V1EnvVar(name="PLATFORM_MONGO_URI", value=mongo_uri)
    ]
```

---

## Migration Strategy

### Phase 1: Schema Extension (Non-Breaking)

Add new fields without changing existing behavior:

```python
async def migrate_to_multi_db_schema():
    """Add databases array to users without breaking existing apps."""

    async for user in users_collection.find({"databases": {"$exists": False}}):
        # Create default database entry from existing password
        default_db = {
            "id": "default",
            "name": "Default",
            "mongo_password_encrypted": user.get("mongo_password_encrypted"),
            "created_at": user.get("created_at", datetime.utcnow()),
            "is_default": True,
            "description": "Original database"
        }

        await users_collection.update_one(
            {"_id": user["_id"]},
            {
                "$set": {
                    "databases": [default_db],
                    "default_database_id": "default"
                }
            }
        )
```

### Phase 2: MongoDB User Rename

Rename existing MongoDB users to new format:

```python
async def migrate_mongo_users():
    """Rename user_xxx to user_xxx_default in MongoDB."""

    async for user in users_collection.find({}):
        user_id = str(user["_id"])
        old_username = f"user_{user_id}"
        new_username = f"user_{user_id}_default"

        # Check if old user exists
        users_info = await admin_db.command("usersInfo", old_username)
        if not users_info.get("users"):
            continue

        # Get current password (need to reset since we can't read it)
        new_password = generate_mongo_password()

        # Create new user with new naming
        await admin_db.command(
            "createUser",
            new_username,
            pwd=new_password,
            roles=[{"role": "readWrite", "db": f"user_{user_id}_default"}]
        )

        # Update stored password
        await users_collection.update_one(
            {"_id": user["_id"]},
            {"$set": {"databases.0.mongo_password_encrypted": encrypt_password(new_password)}}
        )

        # Drop old user
        await admin_db.command("dropUser", old_username)

        # Rename database (MongoDB doesn't support this directly)
        # Option 1: Leave database name as-is, just change user
        # Option 2: Copy data to new database name (expensive)
```

**Note:** Database renaming in MongoDB requires copying all data. Consider keeping old database names (`user_{user_id}`) and only changing the username format for new databases.

### Phase 3: Update URI Generation

Make `get_user_mongo_uri_secure()` database-aware with backwards compatibility.

---

## Frontend UI

### Database Management Page (`/databases`)

```
┌─────────────────────────────────────────────────────────────┐
│  Your Databases                            [+ New Database] │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ ★ Default                                    12.5 MB │   │
│  │   5 collections · 1,234 documents                    │   │
│  │   Used by: 3 apps                                    │   │
│  │   [View] [Credentials] [Set Default]                 │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │   Production                                 45.2 MB │   │
│  │   8 collections · 15,678 documents                   │   │
│  │   Used by: 2 apps                                    │   │
│  │   [View] [Credentials] [Delete]                      │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  Total Storage: 57.7 MB                                     │
└─────────────────────────────────────────────────────────────┘
```

### App Settings - Database Selection

In the editor's app settings panel:

```
┌─────────────────────────────────────────┐
│ App Settings                            │
├─────────────────────────────────────────┤
│                                         │
│ Database:                               │
│ ┌─────────────────────────────────────┐ │
│ │ ★ Default (12.5 MB)              ▼ │ │
│ └─────────────────────────────────────┘ │
│   ○ Default (12.5 MB)                   │
│   ○ Production (45.2 MB)                │
│   ○ Staging (2.1 MB)                    │
│                                         │
│ [Save Settings]                         │
└─────────────────────────────────────────┘
```

---

## Quota Considerations

With multiple databases, quotas become more important:

### Per-Database Limits
```python
{
    "id": "prod_a1b2c3",
    "name": "production",
    "quota_mb": 1000,           # 1GB limit
    "quota_collections": 50,    # Max collections
    "current_size_mb": 45.2
}
```

### Per-User Total Limits
```python
{
    "user_id": "xxx",
    "total_quota_mb": 5000,     # 5GB across all databases
    "max_databases": 10,        # Max databases per user
    "current_total_mb": 57.7
}
```

### Enforcement Points
1. **On write** - Check quota before allowing insert/update
2. **On database create** - Check max_databases limit
3. **Periodic job** - Flag users over quota, disable writes

---

## Implementation Checklist

### Critical Path

- [ ] User schema: Add `databases` array and `default_database_id`
- [ ] App schema: Add `database_id` field
- [ ] Migration: Convert existing users to multi-db schema
- [ ] `POST /api/databases` - Create new database
- [ ] `GET /api/databases` - List databases
- [ ] `DELETE /api/databases/{id}` - Delete database
- [ ] Update `get_user_mongo_uri_secure()` for database selection
- [ ] Update app deployment to use per-app database
- [ ] Frontend: Database management page
- [ ] Frontend: Database selector in app settings

### Nice-to-Have

- [ ] `PATCH /api/databases/{id}` - Update name/description
- [ ] `POST /api/databases/{id}/rotate` - Rotate credentials
- [ ] Per-database quota enforcement
- [ ] Database usage analytics
- [ ] Export/import database

---

## Cluster Foundation Requirements

The multi-database feature requires the platform's MongoDB user to have specific roles:

```javascript
// In fastapi-platform-cluster-foundation/infrastructure/mongodb/statefulset.yaml
db.createUser({
    user: "platform",
    pwd: "platformpass456",
    roles: [
        {role: "readWrite", db: "platform"},
        {role: "readWrite", db: "fastapi_platform_db"},
        {role: "readWriteAnyDatabase", db: "admin"},
        {role: "userAdminAnyDatabase", db: "admin"}  // Required for multi-database
    ]
})
```

**Critical:** The `userAdminAnyDatabase` role is required for the platform to create per-user MongoDB users. Without this role, database creation will fail with "not authorized" errors.

If you're upgrading an existing cluster, grant the role manually:
```bash
MONGO_PASSWORD=$(kubectl get secret -n mongodb mongodb-secret -o jsonpath='{.data.root-password}' | base64 -d)
kubectl exec -n mongodb mongodb-0 -- mongosh -u root -p "$MONGO_PASSWORD" --authenticationDatabase admin --eval '
db.getSiblingDB("platform").grantRolesToUser("platform", [
  { role: "userAdminAnyDatabase", db: "admin" }
])
'
```

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Breaking existing apps | Backwards-compatible schema, fallback to legacy URI |
| MongoDB user explosion | One user per database is manageable, automated cleanup |
| Password rotation complexity | Independent passwords per database is actually simpler |
| Migration failures | Run migration in dry-run mode first, add rollback |
| Quota tracking overhead | Async background job, cached stats |

---

## Open Questions

1. **Database naming:** Allow user-provided slugs or auto-generate?
2. **Default handling:** What happens when deleting a database with apps?
3. **Sharing:** Future support for sharing databases between users?
4. **Backup:** Per-database backup/restore functionality?
5. **MongoDB viewer:** Support viewing multiple databases in mongo-express?
