from sqlalchemy import Column, Integer, String, Float, DateTime, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime

Base = declarative_base()

class Website(Base):
    __tablename__ = 'websites'

    id = Column(Integer, primary_key=True)
    title = Column(String, nullable=False)
    url = Column(String, nullable=False)
    xpath = Column(String, nullable=False)
    price = Column(Float, nullable=True)
    last_checked = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<Website(title='{self.title}', url='{self.url}', price={self.price})>"

# Create database engine and session
engine = create_engine('postgresql://user:password@db:5432/dbname')
Session = sessionmaker(bind=engine)

# Create tables
Base.metadata.create_all(engine) 