from celery import Celery
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import aiohttp
from bs4 import BeautifulSoup
from models import Website
from config import Settings

settings = Settings()

# Initialize Celery
celery_app = Celery('worker',
                   broker=settings.REDIS_URL,
                   backend=settings.REDIS_URL)

# Configure Celery
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='Europe/Moscow',
    enable_utc=True,
)

def register_handlers():
    """Register Celery task handlers"""
    @celery_app.task
    async def parse_website(website_id: int):
        """
        Parse website and save results to database
        """
        try:
            # Get website info from database
            engine = create_engine(settings.DATABASE_URL)
            Session = sessionmaker(bind=engine)
            session = Session()
            
            website = session.query(Website).filter(Website.id == website_id).first()
            if not website:
                return {"error": f"Website with id {website_id} not found"}

            # Parse website
            async with aiohttp.ClientSession() as client:
                async with client.get(website.url) as response:
                    if response.status == 200:
                        html = await response.text()
                        soup = BeautifulSoup(html, 'lxml')
                        
                        # Extract price by XPath
                        price_element = soup.select_one(website.xpath)
                        if price_element:
                            price = float(price_element.text.strip().replace(' ', '').replace('₽', ''))
                            
                            # Save results
                            website.price = price
                            website.last_checked = datetime.utcnow()
                            session.commit()
                            
                            return {"success": True, "price": price}
                        else:
                            return {"error": "Price element not found"}
                    else:
                        return {"error": f"Failed to fetch website: {response.status}"}
        except Exception as e:
            return {"error": str(e)}
        finally:
            session.close()

    return celery_app 