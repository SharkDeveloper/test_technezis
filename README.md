# Website Parser Bot

Telegram bot for managing website parsing tasks. Users can upload Excel files containing website information for parsing prices.

## Features

- Upload Excel files with website information
- Store website data in SQLite database
- Parse prices from specified websites
- Calculate average prices per website

## Setup

1. Clone the repository
2. Create a `.env` file with your Telegram bot token:
   ```
   BOT_TOKEN=your_bot_token_here
   ```

### Using Docker

1. Build the Docker image:
   ```bash
   docker build -t parser-bot .
   ```

2. Run the container:
   ```bash
   docker run -d --env-file .env parser-bot
   ```

### Manual Setup

1. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Run the bot:
   ```bash
   python bot.py
   ```

## Excel File Format

The Excel file should contain the following columns:
- title: Website name
- url: Website URL
- xpath: XPath to the price element

## Usage

1. Start the bot in Telegram
2. Click the "Upload File" button
3. Send an Excel file with website information
4. The bot will process the file and show the results 