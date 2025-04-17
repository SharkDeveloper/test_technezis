# Website Parser Bot

A robust Telegram bot for managing website parsing tasks with async support, task queues, and REST API.

## Features

- Upload Excel files with website information
- Asynchronous website parsing
- Task queue with Celery and RabbitMQ
- REST API for managing websites
- Price history tracking
- Docker support
- Database migrations with Alembic
- Redis for caching
- Modern async architecture

## Architecture

The project consists of several components:

1. **Telegram Bot** - Handles user interactions and file uploads
2. **REST API** - Provides programmatic access to the system
3. **Task Queue** - Manages asynchronous parsing tasks using Celery
4. **Database** - Stores website information and price history
5. **Cache** - Redis for caching frequently accessed data

## Tech Stack

- Python 3.11+
- aiogram 3.x
- FastAPI
- SQLAlchemy
- Alembic
- Redis
- RabbitMQ
- Celery
- Docker
- Poetry

## Setup

1. Clone the repository
2. Copy `.env.example` to `.env` and fill in your values:
   ```bash
   cp .env.example .env
   ```

3. Edit the `.env` file and set your Telegram bot token:
   ```
   BOT_TOKEN=your_telegram_bot_token_here
   ```

### Running with Docker Compose

1. Build and start all services:
   ```bash
   docker-compose up --build
   ```

2. The following services will be available:
   - Telegram Bot: Running and ready to receive messages
   - REST API: Available at http://localhost:8001
   - Celery Worker: Processing tasks in the background
   - Redis: Available at localhost:6379
   - RabbitMQ: Available at localhost:5672 (management interface at localhost:15672)
   - PostgreSQL: Available at localhost:5432

3. To stop all services:
   ```bash
   docker-compose down
   ```

## Excel File Format

The Excel file should contain the following columns:
- title: Website name
- url: Website URL
- xpath: XPath to the price element

## API Endpoints

- `POST /websites/` - Create a new website
- `GET /websites/` - List all websites
- `GET /websites/{website_id}` - Get website details
- `POST /websites/parse-all` - Trigger parsing for all websites

## Development

For local development without Docker:

1. Install dependencies:
   ```bash
   poetry install
   ```

2. Run database migrations:
   ```bash
   poetry run alembic upgrade head
   ```

3. Start the services:
   ```bash
   # Terminal 1 - Bot
   poetry run python -m app.bot.main

   # Terminal 2 - API
   poetry run uvicorn app.api.main:app --reload

   # Terminal 3 - Celery Worker
   poetry run celery -A app.worker.tasks worker --loglevel=info
   ```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request 