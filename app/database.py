# In app/database.py

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from .config import settings # Your updated config import

# The f-string is gone! We just use the URL directly from settings.
SQLALCHEMY_DATABASE_URL = settings.database_url

engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# (The rest of your file, including get_db, remains the same)
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()