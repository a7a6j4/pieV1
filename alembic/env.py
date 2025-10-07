from logging.config import fileConfig
import sys
import os
from config import settings

from sqlalchemy import engine_from_config, URL
from sqlalchemy import pool

from alembic import context

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load environment variables

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
import model
target_metadata = model.Base.metadata

def get_url():
    """Get database URL from environment variables"""
    host = settings.HOST
    port = int(os.getenv('PORT', '5432'))
    username = settings.USERNAME
    password = settings.PASSWORD
    database = settings.DATABASE
    
    return URL.create(
        drivername="postgresql+psycopg2",
        username=username,
        password=password,
        host=host,
        port=port,
        database=database,
    )

def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    # Create engine from URL
    from sqlalchemy import create_engine
    engine = create_engine(get_url(), pool_recycle=3600)
    
    with engine.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
