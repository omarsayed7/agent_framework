from fastapi import FastAPI
from services import router

app = FastAPI(
    title="Shared Router API",
    description="An example FastAPI application using a shared router with Swagger documentation.",
    version="1.0.0",
)


@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok"}


from services.agent import *

# Include the shared router
app.include_router(router)
