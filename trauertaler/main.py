from fastapi import FastAPI

from . import models, routes
from .database import engine

app = FastAPI()
app.include_router(routes.login.router)
app.include_router(routes.admin.router, prefix="/admin", include_in_schema=True)
app.include_router(routes.ledger.router)


models.Base.metadata.create_all(bind=engine)
