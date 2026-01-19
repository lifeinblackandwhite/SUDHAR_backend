from fastapi import FastAPI, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.database import get_db, engine, Base
from app.db import models
from app.db.schemas import *
from app.api.routes.issue_routes import router as issue_router
from app.db.database import engine
from app.api.routes.verification_routes import router as verification_router

from app.api.routes.community_feed import router as community_feed_router
from app.api.ws.community_ws import router as community_ws_router

from app.api.routes.community_feed import router as community_feed_router


app = FastAPI()

app.include_router(community_feed_router)
app.include_router(community_ws_router)


app.include_router(verification_router)

@app.on_event("startup")
async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
async def startup():
    async with engine.begin() as conn:
        await conn.run_sync(models.Base.metadata.create_all)

@app.get("/")
def home():
    return {"message": "Backend running 🚀"}

@app.get("/db-test")
async def db_test(db: AsyncSession = Depends(get_db)):
    result = await db.execute("SELECT 1;")
    value = result.scalar()
    return {"db_connected": value == 1}

app.include_router(issue_router)
