import os
import sys
from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context
from dotenv import load_dotenv
load_dotenv()

# 1) put project root onto path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# 2) import your Base
from recommender.models import Base
target_metadata = Base.metadata

# this `config` is Alembic’s Config object (parsed from alembic.ini)
config = context.config
print(os.getenv("DATABASE_URL"))

# 3) override the sqlalchemy.url from your env
config.set_main_option("sqlalchemy.url", os.getenv("DATABASE_URL"))

# set up logging exactly as in the generated template
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

def run_migrations_offline():
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url, target_metadata=target_metadata, literal_binds=True
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()