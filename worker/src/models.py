from sqlalchemy import Column, Integer, String, DateTime, Float
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class Website(Base):
    __tablename__ = 'websites'

    id = Column(Integer, primary_key=True)
    title = Column(String, nullable=False)
    url = Column(String, nullable=False)
    xpath = Column(String, nullable=False)
    price = Column(Float, nullable=True)
    last_checked = Column(DateTime, nullable=True)

    def __repr__(self):
        return f"<Website(title={self.title}, url={self.url})>" 