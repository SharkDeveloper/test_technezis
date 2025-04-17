from celery import Celery
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
import aiohttp
import asyncio
from typing import Dict, List
import logging
import os
from dotenv import load_dotenv
from bs4 import BeautifulSoup
import re
from datetime import datetime

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create Celery app
celery_app = Celery('tasks', broker='redis://redis:6379/0', backend='redis://redis:6379/0')

# Database configuration
DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://postgres:postgres@db:5432/postgres')
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Website model
class Website(Base):
    __tablename__ = "websites"
    
    id = Column(Integer, primary_key=True, index=True)
    row_id = Column(String, unique=True, index=True)  # Уникальный идентификатор строки из файла
    url = Column(String, index=True)
    title = Column(String)
    description = Column(String)
    keywords = Column(String)
    status = Column(String)
    price = Column(String)  # Добавляем поле для хранения цены

# Создаем таблицу, если она не существует
Base.metadata.create_all(bind=engine)

def extract_title(html):
    """Extract title from HTML."""
    soup = BeautifulSoup(html, 'lxml')
    if soup.title:
        return soup.title.string
    return ""

def extract_description(html):
    """Extract description from HTML."""
    soup = BeautifulSoup(html, 'lxml')
    meta_desc = soup.find('meta', {'name': 'description'})
    if meta_desc and 'content' in meta_desc.attrs:
        return meta_desc['content']
    return ""

def extract_keywords(html):
    """Extract keywords from HTML."""
    soup = BeautifulSoup(html, 'lxml')
    meta_keywords = soup.find('meta', {'name': 'keywords'})
    if meta_keywords and 'content' in meta_keywords.attrs:
        return meta_keywords['content']
    return ""

def extract_price(html, xpath):
    """Extract price from HTML using XPath."""
    try:
        soup = BeautifulSoup(html, 'lxml')
        
        # Handle XPath format
        if xpath.startswith('//*[@id="'):
            # Extract ID from XPath
            id_match = re.search(r'@id="([^"]+)"', xpath)
            if id_match:
                element_id = id_match.group(1)
                element = soup.find(id=element_id)
                if element:
                    # Try to find price in the element
                    price_text = element.text.strip()
                    # Look for price with currency symbol
                    price_match = re.search(r'(\d+(?:\s*\d+)*(?:,\d+)?(?:\.\d+)?)\s*₽', price_text)
                    if price_match:
                        # Clean up the price (remove spaces)
                        price = price_match.group(1).replace(' ', '')
                        return price
        
        # Fallback: try to find any price-like text with currency symbol
        price_elements = soup.find_all(text=re.compile(r'\d+(?:\s*\d+)*(?:,\d+)?(?:\.\d+)?\s*₽'))
        if price_elements:
            for price_text in price_elements:
                price_match = re.search(r'(\d+(?:\s*\d+)*(?:,\d+)?(?:\.\d+)?)\s*₽', price_text.strip())
                if price_match:
                    # Clean up the price (remove spaces)
                    price = price_match.group(1).replace(' ', '')
                    return price
        
        # If no price with currency symbol found, try to find any number that looks like a price
        price_elements = soup.find_all(text=re.compile(r'\d+(?:\s*\d+)*(?:,\d+)?(?:\.\d+)?'))
        if price_elements:
            for price_text in price_elements:
                # Check if the text is in a price-like context
                parent = price_text.parent
                if parent and ('price' in parent.get('class', []) or 'price' in parent.get('id', '')):
                    price_match = re.search(r'(\d+(?:\s*\d+)*(?:,\d+)?(?:\.\d+)?)', price_text.strip())
                    if price_match:
                        # Clean up the price (remove spaces)
                        price = price_match.group(1).replace('', '')
                        return price
        
        return None
    except Exception as e:
        logger.error(f"Error extracting price: {str(e)}")
        return None

async def fetch_website_data(session: aiohttp.ClientSession, website_data: Dict) -> Dict:
    """Fetch website data asynchronously."""
    url = website_data.get('url', '')
    title = website_data.get('title', '')
    xpath = website_data.get('xpath', '')
    
    try:
        async with session.get(url) as response:
            if response.status == 200:
                html = await response.text()
                price = extract_price(html, xpath)
                
                return {
                    'url': url,
                    'title': title,
                    'description': extract_description(html),
                    'keywords': extract_keywords(html),
                    'status': 'success',
                    'success': True,
                    'price': price
                }
            return {
                'url': url,
                'title': title,
                'status': f'error: HTTP {response.status}',
                'success': False,
                'error': f'HTTP {response.status}'
            }
    except Exception as e:
        logger.error(f"Error fetching {url}: {str(e)}")
        return {
            'url': url,
            'title': title,
            'status': f'error: {str(e)}',
            'success': False,
            'error': str(e)
        }

@celery_app.task
def process_websites(websites_data: List[Dict]) -> List[Dict]:
    """Process a list of websites and store results in the database."""
    try:
        # Create database session
        db = SessionLocal()
        
        # Create aiohttp session
        async def process_urls():
            async with aiohttp.ClientSession() as session:
                tasks = [fetch_website_data(session, website) for website in websites_data]
                results = await asyncio.gather(*tasks)
                return results
        
        # Run async processing
        results = asyncio.run(process_urls())
        
        # Store results in database
        for i, result in enumerate(results):
            # Generate a unique identifier for the row
            row_id = f"row_{i}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
            
            # Check if website already exists
            existing_website = db.query(Website).filter(Website.row_id == row_id).first()
            
            if existing_website:
                # Update existing website
                existing_website.title = result['title']
                existing_website.description = result.get('description', '')
                existing_website.keywords = result.get('keywords', '')
                existing_website.status = result['status']
                existing_website.price = result.get('price', '')
                logger.info(f"Updated existing product: {result['title']}")
            else:
                # Create new website
                website = Website(
                    row_id=row_id,  # Use row_id as unique identifier
                    url=result['url'],
                    title=result['title'],
                    description=result.get('description', ''),
                    keywords=result.get('keywords', ''),
                    status=result['status'],
                    price=result.get('price', '')
                )
                db.add(website)
                logger.info(f"Added new product: {result['title']}")
        
        db.commit()
        db.close()
        
        return results
    except Exception as e:
        logger.error(f"Error processing websites: {str(e)}")
        return [{'success': False, 'error': str(e)}]

@celery_app.task
def get_statistics():
    """Get statistics about parsed websites."""
    db = SessionLocal()
    try:
        # Get all websites
        all_websites = db.query(Website).all()
        
        # Count total products (each website is a product)
        total_products = len(all_websites)
        
        # Count successful products and collect prices
        successful_products = []
        prices = []
        
        for site in all_websites:
            if site.status == 'success':
                successful_products.append(site)
                # Получаем цену напрямую из поля price
                if site.price:
                    try:
                        # Очищаем строку цены от пробелов и заменяем запятую на точку
                        price_str = site.price.replace(' ', '').replace(',', '.')
                        # Удаляем символ рубля и любые другие нечисловые символы
                        price_str = ''.join(c for c in price_str if c.isdigit() or c == '.')
                        if price_str:
                            price = float(price_str)
                            prices.append(price)
                    except (ValueError, TypeError) as e:
                        logger.error(f"Error converting price '{site.price}' to float: {str(e)}")
                        continue
        
        products_with_price = len(prices)  # Считаем только те товары, у которых удалось получить цену
        
        # Вычисляем среднюю арифметическую цену только если есть товары с ценами
        if products_with_price > 0:
            avg_price = sum(prices) / products_with_price
            avg_price_str = f"{avg_price:,.2f}"
        else:
            avg_price_str = None
        
        return {
            'total_products': total_products,
            'products_with_price': products_with_price,
            'average_price': avg_price_str
        }
    finally:
        db.close() 