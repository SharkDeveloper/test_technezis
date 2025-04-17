import re
import requests
from bs4 import BeautifulSoup
from lxml import html
import logging

def clean_price(price_str):
    """Clean price string and convert to float."""
    if not price_str:
        return None
    
    # Remove currency symbols and whitespace
    cleaned = re.sub(r'[^\d.,]', '', price_str)
    
    # Replace comma with dot for decimal point
    cleaned = cleaned.replace(',', '.')
    
    try:
        return float(cleaned)
    except ValueError:
        logging.error(f"Could not convert price string to float: {price_str}")
        return None

def parse_website(url, xpath):
    """Parse website and extract price using xpath."""
    try:
        # Add headers to mimic a browser request
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        # Parse HTML
        tree = html.fromstring(response.content)
        
        # Try to find price using xpath
        price_elements = tree.xpath(xpath)
        
        if not price_elements:
            logging.warning(f"No price element found for {url} using xpath: {xpath}")
            return None
        
        # Get the first matching element
        price_text