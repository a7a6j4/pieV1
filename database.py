import os
from dotenv import load_dotenv
from pathlib import Path
from sqlalchemy import URL, create_engine
from sqlalchemy.orm import sessionmaker, Session
from typing import Annotated, Optional, Union
from fastapi import Depends
from model import Base
from config import settings


# Get environment variables with fallbacks
host = settings.HOST
port = settings.PORT
username = settings.USERNAME
password = settings.PASSWORD
database = settings.DATABASE
sslmode = settings.SSLMODE
drivername = settings.DB_DRIVER

db_url = URL.create(
    drivername=drivername,
    username=username,
    password=password,
    host=host,
    port=port,
    database=database,
)

engine = create_engine(db_url, pool_recycle=3600)

async def get_session():
    with Session(engine) as session:
        yield session

async def create_db_and_tables():
    try:
        Base.metadata.create_all(engine)
        # SQLModel.metadata.create_all(engine)
    except Exception as e:
        print(f"Error creating database and tables: {e}")

db = Annotated[Session, Depends(get_session)]

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)