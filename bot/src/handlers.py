from aiogram import Dispatcher, types
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
import pandas as pd
import io
from datetime import datetime
from celery import Celery
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Celery
celery_app = Celery('bot',
                   broker='redis://redis:6379/0',
                   backend='redis://redis:6379/0')

def register_handlers(dp: Dispatcher):
    # Create keyboard
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Загрузить файл")]
        ],
        resize_keyboard=True
    )

    @dp.message(Command("start"))
    async def cmd_start(message: types.Message):
        await message.answer(
            "Привет! Я бот для парсинга цен с веб-сайтов.\n\n"
            "Я могу:\n"
            "1. Принимать Excel файлы с данными для парсинга\n\n"
            "Используйте кнопку ниже для загрузки файла.",
            reply_markup=keyboard
        )

    @dp.message(lambda message: message.text == "Загрузить файл")
    async def upload_file(message: types.Message):
        await message.answer(
            "Пожалуйста, отправьте Excel файл (.xlsx, .xls) со следующими колонками:\n"
            "- title: название сайта\n"
            "- url: ссылка на сайт\n"
            "- xpath: путь к элементу с ценой"
        )

    @dp.message(lambda message: message.document is not None)
    async def handle_file(message: types.Message):
        # Check if file is Excel
        if not message.document.file_name.endswith(('.xlsx', '.xls')):
            await message.answer("Пожалуйста, отправьте файл в формате Excel (.xlsx, .xls)")
            return

        try:
            # Download the file
            file = await message.bot.get_file(message.document.file_id)
            file_path = file.file_path
            downloaded_file = await message.bot.download_file(file_path)
            file_content = downloaded_file.read()
            
            # Read Excel file
            # Determine Excel engine based on file extension
            engine = 'openpyxl' if message.document.file_name.endswith('.xlsx') else 'xlrd'
            df = pd.read_excel(io.BytesIO(file_content), engine=engine)
            
            # Check required columns
            required_columns = ['title', 'url', 'xpath']
            missing_columns = [col for col in required_columns if col not in df.columns]
            
            if missing_columns:
                await message.answer(
                    f"Ошибка: В файле отсутствуют обязательные колонки: {', '.join(missing_columns)}\n"
                    "Требуемые колонки: title, url, xpath"
                )
                return

            # Save file with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"websites_{timestamp}.xlsx"
            df.to_excel(filename, index=False, engine='openpyxl')

            # Prepare response message
            response = "Содержимое файла:\n\n"
            for _, row in df.iterrows():
                response += f"Название: {row['title']}\n"
                response += f"URL: {row['url']}\n"
                response += f"XPath: {row['xpath']}\n"
                response += "-" * 30 + "\n"

            # Split response if it's too long
            max_length = 4096
            for i in range(0, len(response), max_length):
                chunk = response[i:i + max_length]
                await message.answer(chunk)

            await message.answer(
                f"Файл успешно обработан и сохранен как {filename}\n"
                "Начинаю парсинг сайтов..."
            )

            # Send websites data to worker
            websites_data = df.to_dict('records')
            task = celery_app.send_task('main.process_websites', args=[websites_data])
            results = task.get()

            # Send results to user
            for result in results:
                if result.get('success', False):
                    price = result.get('price')
                    if price:
                        # Format price with spaces for thousands
                        try:
                            price_int = int(price.replace(',', '.').replace(' ', ''))
                            formatted_price = f"{price_int:,}".replace(',', ' ')
                            price_text = f"Цена: {formatted_price} ₽"
                        except ValueError:
                            price_text = f"Цена: {price} ₽"
                    else:
                        price_text = "Цена не найдена"
                    
                    await message.answer(
                        f"✅ {result.get('title', 'Без названия')}\n"
                        f"{price_text}"
                    )
                else:
                    await message.answer(
                        f"❌ {result.get('title', 'Без названия')}\n"
                        f"Ошибка: {result.get('error', 'Неизвестная ошибка')}"
                    )

            # Получаем обновленную статистику после парсинга
            stats_task = celery_app.send_task('main.get_statistics')
            stats = stats_task.get(timeout=10)
            
            if stats:
                await message.answer(
                    "📊 Обновленная статистика после парсинга:\n\n"
                    f"Всего товаров: {stats.get('total_products', 0)}\n"
                    f"Товаров с ценами: {stats.get('products_with_price', 0)}\n"
                    f"Средняя цена: {stats.get('average_price', '0.00')} ₽"
                )
            
            await message.answer("Парсинг завершен!")

        except Exception as e:
            await message.answer(f"Произошла ошибка при обработке файла: {str(e)}") 