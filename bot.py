import os
import logging
from datetime import datetime

import pandas as pd
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from dotenv import load_dotenv
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)

# Initialize bot and dispatcher
bot = Bot(token=os.getenv("BOT_TOKEN"))
dp = Dispatcher()

# Database setup
Base = declarative_base()
engine = create_engine('sqlite:///websites.db')
Session = sessionmaker(bind=engine)

class Website(Base):
    __tablename__ = 'websites'
    
    id = Column(Integer, primary_key=True)
    title = Column(String)
    url = Column(String)
    xpath = Column(String)
    price = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

Base.metadata.create_all(engine)

def create_keyboard():
    builder = ReplyKeyboardBuilder()
    builder.add(types.KeyboardButton(text="Upload File"))
    builder.adjust(1)
    return builder.as_markup(resize_keyboard=True)

@dp.message(Command("start"))
async def cmd_start(message: Message):
    await message.answer(
        "Welcome! I can help you manage website parsing tasks. "
        "Click 'Upload File' to upload an Excel file with website information.",
        reply_markup=create_keyboard()
    )

@dp.message(F.text == "Upload File")
async def request_file(message: Message):
    await message.answer(
        "Please send me an Excel file with the following columns:\n"
        "- title: Website name\n"
        "- url: Website URL\n"
        "- xpath: XPath to the price element"
    )

@dp.message(F.document)
async def handle_file(message: Message):
    if not message.document.file_name.endswith(('.xlsx', '.xls')):
        await message.answer("Please send an Excel file (.xlsx or .xls)")
        return

    try:
        # Download the file
        file = await bot.get_file(message.document.file_id)
        file_path = file.file_path
        downloaded_file = await bot.download_file(file_path)
        
        # Save the file temporarily
        temp_path = f"temp_{message.document.file_name}"
        with open(temp_path, 'wb') as f:
            f.write(downloaded_file.read())
        
        # Read Excel file
        df = pd.read_excel(temp_path)
        
        # Validate columns
        required_columns = ['title', 'url', 'xpath']
        if not all(col in df.columns for col in required_columns):
            await message.answer("Error: File must contain 'title', 'url', and 'xpath' columns")
            return
        
        # Save to database
        session = Session()
        for _, row in df.iterrows():
            website = Website(
                title=row['title'],
                url=row['url'],
                xpath=row['xpath']
            )
            session.add(website)
        session.commit()
        session.close()
        
        # Show the data
        response = "File processed successfully!\n\nData from file:\n"
        response += df.to_string()
        await message.answer(response)
        
        # Clean up
        os.remove(temp_path)
        
    except Exception as e:
        logging.error(f"Error processing file: {e}")
        await message.answer(f"Error processing file: {str(e)}")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    import asyncio
    asyncio.run(main()) 