"""
Scheduler for periodic message checking using asyncio
"""
import asyncio
from datetime import datetime, timezone, timedelta
from database import SessionLocal, Subscription, ScrapedMessage
from config import CHECK_INTERVAL_SECONDS
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global bot instance and scraper
_bot_instance = None
_scraper = None
_scheduler_task = None

def set_bot_instance(bot):
    """Set the bot instance for sending messages"""
    global _bot_instance
    _bot_instance = bot

def set_scraper(scraper):
    """Set the shared scraper instance"""
    global _scraper
    _scraper = scraper

def get_scraper():
    """Get the shared scraper instance"""
    global _scraper
    return _scraper


async def send_summary(user_id: int, channel_title: str, message_text: str, link: str):
    """Send summarized message to user"""
    global _bot_instance
    if not _bot_instance:
        logger.error("Bot instance not set")
        return
    
    try:
        from summarizer import summarizer
        summary = summarizer.summarize_text(message_text)
        
        formatted_msg = f"""
📌 {channel_title}
🕒 {datetime.now(timezone.utc).strftime('%H:%M')}

📝 Краткое содержание:
"{summary}"

🔗 Исходное сообщение: {link}
"""
        
        await _bot_instance.send_message(chat_id=user_id, text=formatted_msg)
    except Exception as e:
        logger.error(f"Error sending summary: {e}")


async def check_and_notify():
    """
    Main task: check channels for new messages and send summaries
    """
    global _scraper

    if not _scraper:
        logger.error("Scraper instance not set")
        return

    logger.info("Starting scheduled check...")
    
    db = SessionLocal()

    try:
        subscriptions = db.query(Subscription).filter(
            Subscription.is_active == True
        ).all()
        
        for sub in subscriptions:
            try:
                messages = await _scraper.get_channel_messages(
                    sub.channel_id,
                    limit=20,
                    since_hours=1
                )
                
                if not messages:
                    continue
                
                from database import User
                user = db.query(User).filter(User.id == sub.user_id).first()
                
                if not user:
                    continue
                
                for msg in messages:
                    logger.debug(f"Checking message ID={msg['message_id']} from channel {sub.channel_id}")

                    existing = db.query(ScrapedMessage).filter(
                        ScrapedMessage.message_id == msg['message_id'],
                        ScrapedMessage.channel_id == str(sub.channel_id)
                    ).first()
                    
                    if existing:
                        logger.debug(f"Message {msg['message_id']} already exists, skipping")
                        continue
                    
                    logger.info(f"Saving new message ID={msg['message_id']} from {sub.channel_title}: {msg['text'][:50]}...")

                    scraped_msg = ScrapedMessage(
                        subscription_id=sub.id,
                        channel_id=str(sub.channel_id),
                        channel_title=sub.channel_title,
                        message_id=msg['message_id'],
                        text=msg['text'],
                        link=msg['link'] or "",
                        timestamp=msg['date'],
                        processed_at=datetime.now(timezone.utc)
                    )
                    db.add(scraped_msg)
                    db.commit()
                    
                    await send_summary(
                        user.telegram_id,
                        sub.channel_title,
                        msg['text'],
                        msg['link'] or ""
                    )
                
                logger.info(f"Processed {len(messages)} messages from {sub.channel_title}")
                
            except Exception as e:
                logger.error(f"Error processing channel {sub.channel_id}: {e}")
                continue
    
    except Exception as e:
        logger.error(f"Error in scheduled check: {e}")
    finally:
        db.close()


async def scheduler_loop():
    """Main scheduler loop"""
    logger.info("Scheduler loop started")
    
    while True:
        try:
            await check_and_notify()
        except Exception as e:
            logger.error(f"Error in scheduler loop: {e}")
        
        # Wait for next check interval
        await asyncio.sleep(CHECK_INTERVAL_SECONDS)


def start_scheduler():
    """Start the scheduler in the current event loop"""
    global _scheduler_task
    _scheduler_task = asyncio.create_task(scheduler_loop())
    logger.info(f"Scheduler started (check every {CHECK_INTERVAL_SECONDS} seconds)")


def stop_scheduler():
    """Stop the scheduler"""
    global _scheduler_task
    if _scheduler_task:
        _scheduler_task.cancel()
        logger.info("Scheduler stopped")


if __name__ == "__main__":
    start_scheduler()
    try:
        asyncio.get_event_loop().run_forever()
    except KeyboardInterrupt:
        stop_scheduler()