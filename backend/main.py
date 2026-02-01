"""
FastAPI Learning Platform API
Main application entry point
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from lifespan import lifespan
from database import client, templates_collection
from routers import auth, apps, viewer, database, databases, templates, admin, metrics, chat

app = FastAPI(title="FastAPI Learning Platform API", lifespan=lifespan)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(auth.router)
app.include_router(apps.router)
app.include_router(viewer.router)
app.include_router(database.router)
app.include_router(databases.router)
app.include_router(templates.router)
app.include_router(admin.router)
app.include_router(metrics.router)
app.include_router(chat.router)


@app.get("/")
async def root():
    return {"message": "FastAPI Learning Platform API", "version": "1.0.0"}


@app.get("/health")
async def health():
    try:
        await client.admin.command('ping')
        # Check that required templates exist
        template_count = await templates_collection.count_documents({"is_global": True})
        health_status = {
            "status": "healthy",
            "database": "connected",
            "templates": template_count
        }
        # Warn if templates are missing (but don't fail health check)
        if template_count < 2:
            health_status["warning"] = f"Only {template_count} global templates found (expected at least 2)"
        return health_status
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Database unhealthy: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
