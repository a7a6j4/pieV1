import os
from dotenv import load_dotenv
from pathlib import Path
from sqlalchemy import URL, create_engine
from sqlalchemy.orm import sessionmaker, Session
from typing import Annotated, Optional, Union
from fastapi import Depends
from .model import Base


# Ensure proper .env file path and load it
dotenv_path = Path(__file__).parent / '.env'
if dotenv_path.exists():
    load_dotenv(dotenv_path=dotenv_path, override=True)
else:
    # Try loading from current directory
    load_dotenv(override=True)

# Get environment variables with fallbacks
host = os.getenv('HOST', 'localhost')
port = int(os.getenv('PORT', '5432'))
username = os.getenv('USERNAME', 'postgres')
password = os.getenv('PASSWORD', '')
database = os.getenv('DATABASE', 'pie_app')
sslmode = os.getenv('SSLMODE', 'prefer')

db_url = URL.create(
    drivername="postgresql+psycopg2",
    username=username,
    password=password,
    host=host,
    port=port,
    database=database,
)

# connect_args = {"check_same_thread": False}
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