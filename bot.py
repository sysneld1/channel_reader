"""
Main Telegram Bot - Handles user interactions and notifications
"""
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    MessageHandler,
    filters
)
from datetime import datetime
from database import SessionLocal, User, Subscription, UserSettings, ScrapedMessage
from config import BOT_TOKEN
from summarizer import summarizer

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    #level=logging.INFO
    level=logging.DEBUG
)
logger = logging.getLogger(__name__)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    user = update.effective_user
    
    db = SessionLocal()
    try:
        # Check if user exists
        db_user = db.query(User).filter(User.telegram_id == user.id).first()
        
        if not db_user:
            db_user = User(
                telegram_id=user.id,
                username=user.username
            )
            db.add(db_user)
            db.commit()
            
            # Create default settings
            settings = UserSettings(user_id=db_user.id)
            db.add(settings)
            db.commit()
            
            welcome_text = f"""
👋 Привет, {user.first_name}!

Я бот-агрегатор, который поможет тебе следить за сообщениями из Telegram-каналов.

📋 Мои возможности:
• Подписка на каналы
• Автоматический сбор сообщений
• Суммаризация важных новостей
• Ежедневные дайджесты

📌 Основные команды:
/channels - список ваших подписок
/all_channels - все доступные каналы в системе
/subscribe - добавить канал в отслеживание
/unsubscribe - отписаться от канала
/settings - настройки суммаризации
/digest - получить дайджест сейчас
"""
        else:
            welcome_text = f"С возвращением, {user.first_name}! 👋"
        
        await update.message.reply_text(welcome_text)
        
    except Exception as e:
        logger.error(f"Error in start command: {e}")
    finally:
        db.close()


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command"""
    help_text = """
📚 Справка по командам:

/start - Начать работу с ботом
/channels - Показать ваши подписки
/all_channels - Показать ВСЕ каналы из вашего Telegram
/subscribe - Подписаться на канал
/unsubscribe - Отписаться от канала
/settings - Настройки уведомлений

/digest - Получить дайджест сейчас
/help - Показать справку

💡 Как использовать:

1️⃣ Используйте /all_channels чтобы увидеть все ваши каналы
2️⃣ Скопируйте identifier из списка каналов
3️⃣ Вставьте в команду: /subscribe identifier

📱 Два типа каналов:

✅ КАНАЛЫ С USERNAME:
   Формат: @channel_name
   Пример: /subscribe @tproger

🔢 КАНАЛЫ БЕЗ USERNAME:
   Формат: channel_ID
   Пример: /subscribe channel_1315670121

💡 Команда /all_channels покажет все каналы в несколько сообщений
   (по 20 каналов в каждом сообщении)
"""
    await update.message.reply_text(help_text)


async def channels_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /channels command - show subscribed channels"""
    telegram_id = update.effective_user.id
    
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.telegram_id == telegram_id).first()
        if not user:
            await update.message.reply_text("❌ Используйте /start для начала")
            return
        
        subscriptions = db.query(Subscription).filter(
            Subscription.user_id == user.id,
            Subscription.is_active == True
        ).all()
        
        if not subscriptions:
            await update.message.reply_text(
                "📭 Вы ещё не подписаны ни на какие каналы.\n"
                "Используйте /subscribe @channel_name для подписки"
            )
            return
        
        text = "📋 Ваши подписки:\n\n"
        for sub in subscriptions:
            text += f"• {sub.channel_title or sub.channel_id}\n"
        
        await update.message.reply_text(text)
        
    except Exception as e:
        logger.error(f"Error in channels command: {e}")
    finally:
        db.close()


async def all_channels_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /all_channels command - show all channels user is subscribed to in Telegram"""
    telegram_id = update.effective_user.id

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.telegram_id == telegram_id).first()
        if not user:
            await update.message.reply_text("❌ Используйте /start для начала")
            return

        # Get user's subscriptions in our system
        user_subscriptions = db.query(Subscription).filter(
            Subscription.user_id == user.id,
            Subscription.is_active == True
        ).all()

        user_channel_ids = {sub.channel_id for sub in user_subscriptions}

        # Get all channels from Telegram using Telethon
        try:
            from scheduler import get_scraper
            scraper = get_scraper()

            if not scraper:
                await update.message.reply_text(
                    "❌ Не удалось подключиться к Telegram. Попробуйте позже."
                )
                return

            await update.message.reply_text("🔍 Получаю список ваших каналов из Telegram...")

            # Get all channels user is subscribed to in Telegram
            telegram_channels = await scraper.get_user_channels()

            if not telegram_channels:
                await update.message.reply_text(
                    "📭 В вашем Telegram нет доступных каналов для отслеживания."
                )
                return

            # Format the response
            text = "📋 Ваши каналы в Telegram:\n\n"

            # Group channels
            subscribed_channels = []  # Channels already in our system
            other_channels = []  # Other channels

            for channel in telegram_channels:
                channel_id = f"@{channel['username']}" if channel['username'] else f"channel_{channel['id']}"
                channel_title = channel['title']

                if channel_id in user_channel_ids:
                    subscribed_channels.append((channel_id, channel_title, "✅"))
                else:
                    other_channels.append((channel_id, channel_title, "➕"))

            # Show subscribed channels first
            if subscribed_channels:
                text += "✅ Отслеживаемые каналы:\n"
                for channel_id, channel_title, status in subscribed_channels:
                    text += f"{status} {channel_title}\n"
                text += "\n"

            # Show other channels with usernames for easy copying - ALL CHANNELS
            if other_channels:
                # Send all channels in multiple messages (20 channels per message)
                channels_per_message = 20
                total_messages = (len(other_channels) + channels_per_message - 1) // channels_per_message

                await update.message.reply_text(
                    f"📋 Ваши каналы в Telegram ({len(other_channels)} каналов)\n"
                    f"📄 Будет отправлено {total_messages} сообщений"
                )

                for i in range(0, len(other_channels), channels_per_message):
                    chunk = other_channels[i:i + channels_per_message]
                    page_num = (i // channels_per_message) + 1

                    text = f"📋 Страница {page_num}/{total_messages}\n\n"
                    text += "➕ Доступные для отслеживания:\n"

                    for channel_id, channel_title, status in chunk:
                        # Format as: "Channel Name → @channel_name" for easy copying
                        text += f"{status} {channel_title} → {channel_id}\n"

                    text += "\n💡 Скопируйте @username и используйте: /subscribe @username"

                    # Small delay between messages to avoid rate limiting
                    if i > 0:
                        import asyncio
                        await asyncio.sleep(1)

                    await update.message.reply_text(text)
            else:
                await update.message.reply_text("🎉 Вы подписаны на все доступные каналы!")

        except Exception as e:
            logger.error(f"Error getting Telegram channels: {e}")
            await update.message.reply_text(
                "❌ Ошибка при получении списка каналов из Telegram. "
                "Убедитесь, что бот правильно настроен и подключен к Telegram API."
            )

    except Exception as e:
        logger.error(f"Error in all_channels command: {e}")
    finally:
        db.close()


async def subscribe_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /subscribe command"""
    args = context.args
    
    if not args:
        await update.message.reply_text(
            "❌ Укажите название канала или ID\n\n"
            "📱 Примеры:\n"
            "• /subscribe tproger (канал с username)\n"
            "• /subscribe channel_1315670121 (канал без username)\n\n"
            "💡 Используйте /all_channels чтобы увидеть все каналы"
        )
        return
    
    channel_input = args[0].lstrip('@')
    user_id = update.effective_user.id
    
    db = SessionLocal()
    try:
        # Get user
        user = db.query(User).filter(User.telegram_id == user_id).first()
        if not user:
            await update.message.reply_text("❌ Пользователь не найден. Используйте /start")
            return
        
        # Determine channel format
        if channel_input.startswith('channel_'):
            # Channel ID format
            channel_id = channel_input
            channel_title = channel_input.replace('channel_', 'Channel ')
        else:
            # Username format
            channel_id = f"@{channel_input}"
            channel_title = channel_input

        # Check if already subscribed
        existing = db.query(Subscription).filter(
            Subscription.user_id == user.id,
            Subscription.channel_id == channel_id
        ).first()
        
        if existing:
            await update.message.reply_text(f"✅ Вы уже подписаны на {channel_id}")
            return
        
        # Add subscription
        subscription = Subscription(
            user_id=user.id,
            channel_id=channel_id,
            channel_title=channel_title
        )
        db.add(subscription)
        db.commit()
        
        await update.message.reply_text(
            f"✅ Подписка на {channel_id} добавлена!\n\n"
            f"📢 Бот будет автоматически собирать и суммаризировать "
            f"сообщения из этого канала.\n"
            f"💡 Используйте /digest для получения дайджеста."
        )

    except Exception as e:
        logger.error(f"Error in subscribe command: {e}")
        await update.message.reply_text("❌ Ошибка при добавлении подписки")
    finally:
        db.close()


async def unsubscribe_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /unsubscribe command"""
    args = context.args
    
    if not args:
        await update.message.reply_text(
            "❌ Укажите название канала или ID\n\n"
            "📱 Примеры:\n"
            "• /unsubscribe tproger (канал с username)\n"
            "• /unsubscribe channel_1315670121 (канал без username)\n\n"
            "💡 Используйте /channels чтобы увидеть ваши подписки"
        )
        return
    
    channel_input = args[0].lstrip('@')
    user_id = update.effective_user.id
    
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.telegram_id == user_id).first()
        if not user:
            await update.message.reply_text("❌ Пользователь не найден. Используйте /start")
            return
        
        # Determine channel format
        if channel_input.startswith('channel_'):
            # Channel ID format
            channel_id = channel_input
        else:
            # Username format
            channel_id = f"@{channel_input}"

        subscription = db.query(Subscription).filter(
            Subscription.user_id == user.id,
            Subscription.channel_id == channel_id
        ).first()
        
        if subscription:
            subscription.is_active = False
            db.commit()
            await update.message.reply_text(f"✅ Отписка от {channel_id} выполнена")
        else:
            await update.message.reply_text(f"❌ Вы не были подписаны на {channel_id}")

    except Exception as e:
        logger.error(f"Error in unsubscribe command: {e}")
    finally:
        db.close()


async def settings_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /settings command"""
    telegram_id = update.effective_user.id
    
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.telegram_id == telegram_id).first()
        if not user:
            await update.message.reply_text("❌ Используйте /start для начала")
            return
        
        settings = db.query(UserSettings).filter(
            UserSettings.user_id == user.id
        ).first()
        
        if not settings:
            await update.message.reply_text("❌ Настройки не найдены")
            return
        
        keyboard = [
            [
                InlineKeyboardButton("📝 Длина суммаризации", callback_data="setting_length"),
                InlineKeyboardButton("🖼️ Медиа", callback_data="setting_media")
            ],
            [
                InlineKeyboardButton("📅 Ежедневный дайджест", callback_data="setting_digest"),
                InlineKeyboardButton("🔔 Время уведомлений", callback_data="setting_time")
            ]
        ]
        
        settings_text = f"""
⚙️ Ваши настройки:

📏 Длина суммаризации: {settings.summary_length}
🖼️ Включать медиа: {'Да' if settings.include_media else 'Нет'}
📅 Ежедневный дайджест: {'Включен' if settings.daily_digest else 'Выключен'}
🔔 Время уведомлений: {settings.notification_time}
"""
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(settings_text, reply_markup=reply_markup)
        
    except Exception as e:
        logger.error(f"Error in settings command: {e}")
    finally:
        db.close()


async def digest_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /digest command - get immediate digest"""
    telegram_id = update.effective_user.id
    logger.info(f"User {telegram_id} requested /digest command")

    db = SessionLocal()
    try:
        # Get user by telegram_id first
        user = db.query(User).filter(User.telegram_id == telegram_id).first()
        
        if not user:
            await update.message.reply_text("❌ Используйте /start для начала")
            return
        
        subscriptions = db.query(Subscription).filter(
            Subscription.user_id == user.id,
            Subscription.is_active == True
        ).all()
        
        logger.info(f"User has {len(subscriptions)} active subscriptions")

        if not subscriptions:
            await update.message.reply_text("📭 Нет активных подписок")
            return
        
        # Debug: check total messages in DB
        total_messages = db.query(ScrapedMessage).count()
        logger.info(f"Total messages in DB: {total_messages}")

        digest_text = "📰 Срочный дайджест:\n\n"
        total_messages = 0
        channels_with_messages = 0

        for sub in subscriptions:
            messages = db.query(ScrapedMessage).filter(
                ScrapedMessage.subscription_id == sub.id
            ).order_by(ScrapedMessage.timestamp.desc()).limit(5).all()
            
            logger.debug(f"Channel '{sub.channel_title}' (sub_id={sub.id}): {len(messages)} messages found")

            for msg in messages:
                logger.debug(f"  - ID={msg.id}, message_id={msg.message_id}, timestamp={msg.timestamp}")

            if messages:
                channels_with_messages += 1
                total_messages += len(messages)
                digest_text += f"📌 {sub.channel_title}:\n"
                for msg in messages:
                    summary = msg.summary or msg.processed_text or msg.text
                    digest_text += f"• {summary[:100]}...\n"
                digest_text += "\n"
        
        logger.info(f"Found {total_messages} messages in {channels_with_messages} channels")

        if not channels_with_messages:
            await update.message.reply_text("📭 Нет новых сообщений для отображения")
            return

        await update.message.reply_text(digest_text)
        
    except Exception as e:
        logger.error(f"Error in digest command: {e}")
    finally:
        db.close()


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle callback queries from inline keyboards"""
    query = update.callback_query
    await query.answer()
    
    callback_data = query.data
    
    # Get user from database
    telegram_id = query.from_user.id
    db = SessionLocal()
    
    try:
        user = db.query(User).filter(User.telegram_id == telegram_id).first()
        if not user:
            await query.edit_message_text("❌ Используйте /start для начала")
            return
        
        settings = db.query(UserSettings).filter(UserSettings.user_id == user.id).first()
        if not settings:
            await query.edit_message_text("❌ Настройки не найдены")
            return
        
        # Handle length selection
        if callback_data.startswith("len_"):
            length = callback_data.replace("len_", "")
            settings.summary_length = length
            db.commit()
            await query.edit_message_text(f"✅ Длина суммаризации: {length}")
            return
        
        # Handle media toggle
        if callback_data == "setting_media":
            settings.include_media = not settings.include_media
            db.commit()
            await query.edit_message_text(f"✅ Медиа: {'включено' if settings.include_media else 'выключено'}")
            return
        
        # Handle digest toggle
        if callback_data == "setting_digest":
            settings.daily_digest = not settings.daily_digest
            db.commit()
            await query.edit_message_text(f"✅ Ежедневный дайджест: {'включен' if settings.daily_digest else 'выключен'}")
            return
        
        # Show main settings menu
        if callback_data == "setting_length":
            await query.edit_message_text(
                text="📏 Выберите длину суммаризации:",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("Короткая", callback_data="len_short")],
                    [InlineKeyboardButton("Средняя", callback_data="len_medium")],
                    [InlineKeyboardButton("Длинная", callback_data="len_long")],
                    [InlineKeyboardButton("🔙 Назад", callback_data="settings_back")]
                ])
            )
            return
        
        # Back to main menu
        if callback_data == "settings_back":
            keyboard = [
                [
                    InlineKeyboardButton("📝 Длина суммаризации", callback_data="setting_length"),
                    InlineKeyboardButton("🖼️ Медиа", callback_data="setting_media")
                ],
                [
                    InlineKeyboardButton("📅 Ежедневный дайджест", callback_data="setting_digest"),
                    InlineKeyboardButton("🔔 Время уведомлений", callback_data="setting_time")
                ]
            ]
            
            settings_text = f"""
⚙️ Ваши настройки:

📏 Длина суммаризации: {settings.summary_length}
🖼️ Включать медиа: {'Да' if settings.include_media else 'Нет'}
📅 Ежедневный дайджест: {'Включен' if settings.daily_digest else 'Выключен'}
🔔 Время уведомлений: {settings.notification_time}
"""
            await query.edit_message_text(settings_text, reply_markup=InlineKeyboardMarkup(keyboard))
            return
        
        # Handle notification time setting
        if callback_data == "setting_time":
            keyboard = [
                [
                    InlineKeyboardButton("08:00", callback_data="time_08:00"),
                    InlineKeyboardButton("09:00", callback_data="time_09:00"),
                    InlineKeyboardButton("10:00", callback_data="time_10:00")
                ],
                [
                    InlineKeyboardButton("12:00", callback_data="time_12:00"),
                    InlineKeyboardButton("18:00", callback_data="time_18:00"),
                    InlineKeyboardButton("21:00", callback_data="time_21:00")
                ],
                [InlineKeyboardButton("🔙 Назад", callback_data="settings_back")]
            ]
            await query.edit_message_text(
                text="⏰ Выберите время уведомлений:",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return
        
        # Handle time input (format: HH:MM)
        if callback_data.startswith("time_"):
            time_value = callback_data.replace("time_", "")
            # Validate time format
            try:
                from datetime import datetime
                datetime.strptime(time_value, "%H:%M")
                settings.notification_time = time_value
                db.commit()
                await query.edit_message_text(f"✅ Время уведомлений: {time_value}")
                return
            except ValueError:
                pass
        
    except Exception as e:
        logger.error(f"Error in handle_callback: {e}")
    finally:
        db.close()


async def send_summary(bot, user_id: int, channel_title: str, message_text: str, link: str):
    """
    Send summarized message to user
    
    Args:
        bot: Telegram bot instance
        user_id: User Telegram ID
        channel_title: Name of the channel
        message_text: Original message text
        link: Link to original message
    """
    try:
        # Generate summary
        summary = summarizer.summarize_text(message_text)
        
        # Format message
        formatted_msg = f"""
📌 {channel_title}
🕒 {datetime.now().strftime('%H:%M')}

📝 Краткое содержание:
"{summary}"

🔗 Исходное сообщение: {link}
"""
        
        await bot.send_message(chat_id=user_id, text=formatted_msg)
        
    except Exception as e:
        logger.error(f"Error sending summary: {e}")


def main():
    """Main function to run the bot"""
    application = ApplicationBuilder().token(BOT_TOKEN).build()
    
    # Add handlers
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('help', help_command))
    application.add_handler(CommandHandler('channels', channels_command))
    application.add_handler(CommandHandler('all_channels', all_channels_command))
    application.add_handler(CommandHandler('subscribe', subscribe_command))
    application.add_handler(CommandHandler('unsubscribe', unsubscribe_command))
    application.add_handler(CommandHandler('settings', settings_command))
    application.add_handler(CommandHandler('digest', digest_command))
    application.add_handler(CallbackQueryHandler(handle_callback))
    
    # Start the bot
    application.run_polling(poll_interval=10)


if __name__ == "__main__":
    main()