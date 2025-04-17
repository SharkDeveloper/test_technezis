from celery import Celery
from sqlalchemy import create_engine, Column, Integer, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import aiohttp
from bs4 import BeautifulSoup
import asyncio
from typing import List, Dict
import os
from dotenv import load_dotenv
from pydantic_settings import BaseSettings
from handlers import register_handlers

load_dotenv()

class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql://user:password@db:5432/dbname"
    REDIS_URL: str = "redis://redis:6379/0"

settings = Settings()

# Celery setup
celery_app = Celery('worker', broker=settings.REDIS_URL, backend=settings.REDIS_URL)

# Database setup
engine = create_engine(settings.DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class Website(Base):
    __tablename__ = "websites"

    id = Column(Integer, primary_key=True, index=True)
    url = Column(String, unique=True, index=True)
    title = Column(String)
    description = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

Base.metadata.create_all(bind=engine)

async def parse_website(session: aiohttp.ClientSession, url: str) -> Dict:
    try:
        async with session.get(url) as response:
            if response.status == 200:
                html = await response.text()
                soup = BeautifulSoup(html, 'lxml')
                return {
                    'url': url,
                    'title': soup.title.string if soup.title else '',
                    'description': soup.find('meta', {'name': 'description'})['content'] if soup.find('meta', {'name': 'description'}) else ''
                }
    except Exception as e:
        print(f"Error parsing {url}: {str(e)}")
        return None

@celery_app.task
def process_urls(urls: List[str]):
    db = SessionLocal()
    try:
        async def process_all():
            async with aiohttp.ClientSession() as session:
                tasks = [parse_website(session, url) for url in urls]
                results = await asyncio.gather(*tasks)
                
                for result in results:
                    if result:
                        website = Website(
                            url=result['url'],
                            title=result['title'],
                            description=result['description']
                        )
                        db.add(website)
                
                db.commit()
        
        asyncio.run(process_all())
    except Exception as e:
        print(f"Error processing URLs: {str(e)}")
        db.rollback()
    finally:
        db.close()

@celery_app.task
def get_statistics():
    """Get statistics about parsed websites"""
    session = SessionLocal()
    try:
        total_sites = session.query(Website).count()
        sites_with_price = session.query(Website).filter(Website.price.isnot(None)).count()
        latest_check = session.query(Website).order_by(Website.last_checked.desc()).first()
        
        stats = {
            'total_sites': total_sites,
            'sites_with_price': sites_with_price,
            'latest_check': latest_check.last_checked.isoformat() if latest_check else None,
            'latest_prices': []
        }
        
        # Get latest prices
        latest_prices = session.query(Website).order_by(Website.last_checked.desc()).limit(5).all()
        for site in latest_prices:
            stats['latest_prices'].append({
                'title': site.title,
                'price': site.price,
                'last_checked': site.last_checked.isoformat()
            })
        
        return stats
    finally:
        session.close()

if __name__ == '__main__':
    celery_app = register_handlers()
    celery_app.start() 