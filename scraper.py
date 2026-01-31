from telethon import TelegramClient
from telethon.errors import FloodWaitError, RPCError
from telethon.tl.types import Channel, Chat
from datetime import datetime, timedelta, timezone
import asyncio
import logging
from typing import List, Dict, Optional
from database import SessionLocal, ScrapedMessage, Subscription
from config import API_ID, API_HASH, SESSION_NAME

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ChannelScraper:
    """Class for scraping messages from Telegram channels using Telethon"""
    
    def __init__(self):
        self.client = TelegramClient(SESSION_NAME, API_ID, API_HASH)
        self.last_check_time = {}
    
    async def connect(self):
        """Connect to Telegram using Telethon"""
        logger.info("Connecting to Telegram...")
        try:
            await self.client.connect()
            logger.info("Telegram client connected")

            if not await self.client.is_user_authorized():
                logger.warning("Session not authorized, authorization required")
                phone = input('Enter phone number (e.g., +79991234567): ')
                await self.client.send_code_request(phone)
                code = input('Enter code from Telegram: ')
                await self.client.sign_in(phone, code)
                logger.info("Authorization successful")
            else:
                logger.info("Session already authorized")
        except Exception as e:
            logger.error(f"Connection error: {e}")
            raise
    
    async def get_user_channels(self) -> List[Dict]:
        """
        Get all channels the user has access to
        
        Returns:
            List of channel dictionaries with id, title, access_hash
        """
        try:
            dialogs = await self.client.get_dialogs()
            channels = []
            
            for dialog in dialogs:
                entity = dialog.entity
                if isinstance(entity, Channel):
                    channels.append({
                        'id': entity.id,
                        'title': entity.title,
                        'username': entity.username,
                        'access_hash': entity.access_hash if hasattr(entity, 'access_hash') else None
                    })
            
            return channels
        except Exception as e:
            logger.error(f"Error getting channels: {e}")
            return []
    
    async def get_channel_messages(
        self, 
        channel_id: str,
        limit: int = 100,
        since_hours: int = 24
    ) -> List[Dict]:
        """
        Get messages from a specific channel
        
        Args:
            channel_id: Channel identifier (either username like '@channel' or ID like 'channel_123456')
            limit: Maximum number of messages to retrieve
            since_hours: How far back to look for messages
            
        Returns:
            List of message dictionaries
        """
        messages = []
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=since_hours)

        logger.info(f"Reading channel {channel_id}, limit={limit}, since_hours={since_hours}")

        try:
            # Handle different channel ID formats
            if channel_id.startswith('@'):
                # Username format: @channel_name
                entity = await self.client.get_entity(channel_id)
            elif channel_id.startswith('channel_'):
                # ID format: channel_123456789
                channel_numeric_id = int(channel_id.replace('channel_', ''))
                # For private channels, we need to use the numeric ID
                entity = await self.client.get_entity(channel_numeric_id)
            else:
                logger.error(f"Invalid channel ID format: {channel_id}")
                return []

            logger.info(f"Channel entity retrieved: {entity.title} (@{entity.username})")

            msg_count = 0
            async for message in self.client.iter_messages(
                entity, 
                limit=limit
            ):
                # Filter messages by cutoff time manually
                if message.date >= cutoff_time:
                    # Create link based on channel type
                    link = None
                    if entity.username:
                        link = f"https://t.me/{entity.username}/{message.id}"
                    elif hasattr(entity, 'id'):
                        # For private channels without username, link will be None
                        # We can still provide message ID for reference
                        pass

                    msg_dict = {
                        'message_id': message.id,
                        'text': message.text or "",
                        'date': message.date,
                        'sender_id': message.sender_id,
                        'media': message.media,
                        'link': link
                    }
                    messages.append(msg_dict)
                    msg_count += 1
                elif message.date < cutoff_time:
                    # Messages are ordered by date descending, so we can break early
                    break

            logger.info(f"Retrieved {msg_count} messages from {entity.title}")
            return messages
        except FloodWaitError as e:
            logger.warning(f"Flood wait: {e.seconds} seconds")
            await asyncio.sleep(e.seconds)
            return []
        except RPCError as e:
            logger.error(f"RPC error: {e}")
            return []
        except Exception as e:
            logger.error(f"Error getting messages from channel {channel_id}: {e}")
            return []
    
    async def check_new_messages(self) -> Dict[str, List[Dict]]:
        """
        Check all subscribed channels for new messages
        
        Returns:
            Dictionary mapping channel_id to list of new messages
        """
        db = SessionLocal()
        new_messages = {}
        
        try:
            # Get all active subscriptions
            subscriptions = db.query(Subscription).filter(
                Subscription.is_active == True
            ).all()
            
            logger.info(f"Checking {len(subscriptions)} subscribed channels for new messages")

            for sub in subscriptions:
                logger.info(f"Checking channel: {sub.channel_title} (ID: {sub.channel_id})")

                channel_messages = await self.get_channel_messages(
                    sub.channel_id,
                    limit=50,
                    since_hours=1
                )
                
                if channel_messages:
                    new_messages[sub.channel_id] = channel_messages
                    logger.info(f"Found {len(channel_messages)} new messages in {sub.channel_title}")
                else:
                    logger.info(f"No new messages in {sub.channel_title}")

        except Exception as e:
            logger.error(f"Error checking messages: {e}")
        finally:
            db.close()
        
        logger.info(f"Total channels with new messages: {len(new_messages)}")
        return new_messages
    
    async def disconnect(self):
        """Disconnect from Telegram"""
        await self.client.disconnect()


async def main():
    """Main function for testing the scraper"""
    scraper = ChannelScraper()
    
    try:
        await scraper.connect()
        channels = await scraper.get_user_channels()
        print(f"Found {len(channels)} channels:")
        for ch in channels:
            print(f"  - {ch['title']} (ID: {ch['id']})")
    finally:
        await scraper.disconnect()


if __name__ == "__main__":
    asyncio.run(main())

# python -c "from scraper import ChannelScraper; import asyncio; asyncio.run(ChannelScraper().connect())"