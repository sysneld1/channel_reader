"""
Main entry point for the Telegram Aggregator Bot
"""
import asyncio
import logging
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler
from database import init_db
from config import BOT_TOKEN
import sys

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

async def init_bot(application):
    """Initialize bot and scheduler"""
    logger.info("Initializing database...")
    init_db()
    
    # Import handler functions
    from bot import (
        start, help_command, channels_command, all_channels_command,
        subscribe_command, unsubscribe_command,
        settings_command, digest_command, handle_callback
    )
    
    # Add command handlers
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('help', help_command))
    application.add_handler(CommandHandler('channels', channels_command))
    application.add_handler(CommandHandler('all_channels', all_channels_command))
    application.add_handler(CommandHandler('subscribe', subscribe_command))
    application.add_handler(CommandHandler('unsubscribe', unsubscribe_command))
    application.add_handler(CommandHandler('settings', settings_command))
    application.add_handler(CommandHandler('digest', digest_command))
    application.add_handler(CallbackQueryHandler(handle_callback))
    
    # Connect scraper and start scheduler
    from scraper import ChannelScraper
    from scheduler import start_scheduler, set_bot_instance, set_scraper

    logger.info("Connecting to Telegram...")
    scraper = ChannelScraper()
    await scraper.connect()
    logger.info("Telegram connection established")

    set_bot_instance(application.bot)
    set_scraper(scraper)
    start_scheduler()
    
    logger.info("Bot initialized successfully")

def main():
    """Main entry point"""
    application = (
        ApplicationBuilder()
        .token(BOT_TOKEN)
        .concurrent_updates(False)
        .build()
    )
    
    # Run initialization
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(init_bot(application))
    
    logger.info("Starting polling...")
    
    # Use run_polling with post_shutdown_stop=False
    try:
        application.run_polling(drop_pending_updates=True, close_loop=False, poll_interval=10)
    except KeyboardInterrupt:
        logger.info("Application stopped")
        sys.exit(0)

if __name__ == "__main__":
    main()
