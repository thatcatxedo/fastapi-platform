"""
Database stats routes for FastAPI Platform
"""
from fastapi import APIRouter, HTTPException, Depends
import logging

from models import DatabaseStatsResponse, CollectionStats
from auth import get_current_user
from database import client
from utils import error_payload

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/database", tags=["database"])


@router.get("/stats", response_model=DatabaseStatsResponse)
async def get_database_stats(user: dict = Depends(get_current_user)):
    """Get MongoDB statistics for the user's database"""
    user_id = str(user["_id"])
    db_name = f"user_{user_id}"

    try:
        user_db = client[db_name]
        collection_names = await user_db.list_collection_names()

        collections = []
        total_documents = 0
        total_size = 0

        for coll_name in collection_names:
            try:
                stats = await user_db.command("collStats", coll_name)
                doc_count = stats.get("count", 0)
                size = stats.get("size", 0)
                avg_size = stats.get("avgObjSize", 0)

                collections.append(CollectionStats(
                    name=coll_name,
                    document_count=doc_count,
                    size_bytes=size,
                    avg_doc_size=int(avg_size) if avg_size else None
                ))
                total_documents += doc_count
                total_size += size
            except Exception as coll_err:
                logger.warning(f"Error getting stats for collection {coll_name}: {coll_err}")
                collections.append(CollectionStats(
                    name=coll_name,
                    document_count=0,
                    size_bytes=0,
                    avg_doc_size=None
                ))

        collections.sort(key=lambda c: c.document_count, reverse=True)

        try:
            db_stats = await user_db.command("dbStats")
            total_size_bytes = db_stats.get("dataSize", total_size)
        except Exception:
            total_size_bytes = total_size

        return DatabaseStatsResponse(
            database_name=db_name,
            total_collections=len(collection_names),
            total_documents=total_documents,
            total_size_bytes=total_size_bytes,
            total_size_mb=round(total_size_bytes / (1024 * 1024), 2),
            collections=collections
        )
    except Exception as e:
        logger.error(f"Error fetching database stats for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail=error_payload("DB_STATS_FAILED", str(e)))
