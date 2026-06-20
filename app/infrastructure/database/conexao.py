from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.config import config

engine = create_engine(
    config.database_url,
    connect_args={"check_same_thread": False},  # necessário para SQLite
    echo=False,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def obter_sessao():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
