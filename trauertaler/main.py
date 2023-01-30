from fastapi import FastAPI
from sqlalchemy import MetaData

from . import models, routes
from .database import engine

meta_data = MetaData()

app = FastAPI(root_path="/api")
app = FastAPI()
app.include_router(routes.login.router)
app.include_router(routes.admin.router, prefix="/admin", include_in_schema=False)
app.include_router(routes.ledger.router)


models.Base.metadata.create_all(bind=engine)
