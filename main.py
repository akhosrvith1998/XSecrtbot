import os
import logging
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InlineQueryResultArticle, InputTextMessageContent
from telegram.ext import Application, CommandHandler, MessageHandler, InlineQueryHandler, ChosenInlineResultHandler, CallbackQueryHandler, ChatMemberHandler, filters
from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker
import datetime
import pytz

# تنظیمات لاگ
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# تنظیمات دیتابیس
Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, unique=True)
    username = Column(String)
    first_name = Column(String)
    last_name = Column(String)
    started_bot = Column(Boolean, default=False)
    is_member = Column(Boolean, default=False)

class Whisper(Base):
    __tablename__ = 'whispers'
    id = Column(Integer, primary_key=True)
    sender_id = Column(Integer)
    recipient_id = Column(Integer)
    message_text = Column(String)
    inline_message_id = Column(String)
    seen_count = Column(Integer, default=0)
    seen_timestamp = Column(DateTime)
    snooper_count = Column(Integer, default=0)
    is_deleted = Column(Boolean, default=False)

engine = create_engine('sqlite:///bot.db')
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)

# تنظیمات ربات
TOKEN = '7682323067:AAFcmkRvUZBQZJVQgCKgPqkaQb0TE2TPBPo'
SPONSOR_CHANNEL = '@XSecrtyou'
BOT_USERNAME = '@XSecrtbot'
BOT_NAME = 'XSecret 💭'

# تابع خوش‌آمدگویی با استارت
async def start(update: Update, context) -> None:
    user = update.effective_user
    logger.info(f"Start command triggered by user {user.id} via deep link")
    session = Session()
    db_user = session.query(User).filter_by(user_id=user.id).first()
    if not db_user:
        db_user = User(user_id=user.id, username=user.username, first_name=user.first_name, last_name=user.last_name, started_bot=True)
        session.add(db_user)
    else:
        db_user.started_bot = True
    session.commit()

    membership_text = ""
    try:
        member = await context.bot.get_chat_member(chat_id=SPONSOR_CHANNEL, user_id=user.id)
        if member.status in ['member', 'administrator', 'creator']:
            db_user.is_member = True
            membership_text = "عضویتت هم تایید شد. ✅"
        else:
            db_user.is_member = False
            membership_text = "لطفا توی کانال اسپانسر هم عضو شو 💜"
    except Exception as e:
        logger.error(f"Error checking membership for user {user.id}: {e}")
        membership_text = "خطا در بررسی عضویت. لطفاً بعداً تلاش کنید."

    session.commit()
    session.close()

    display_name = user.last_name or user.first_name or "کاربر"
    welcome_text = (
        f"سلام {display_name} خوش آمدی 💭\n\n"
        "با من می‌تونی پیام‌هاتو توی گروه، به‌صورت مخفیانه بفرستی برای گیرنده مدنظرت تا فقط تو و اون بتونید پیام رو بخونید!\n\n"
        "در چهار حالت می‌تونی از من استفاده کنی:\n\n"
        f"{membership_text}"
    )
    keyboard = [
        [InlineKeyboardButton("راهنما 💡", callback_data='guide_menu')],
        [InlineKeyboardButton("عضویت در کانال اسپانسر", url='https://t.me/XSecrtyou')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    message = await context.bot.send_message(chat_id=user.id, text=welcome_text, reply_markup=reply_markup)
    context.user_data['welcome_message_id'] = message.message_id

# توابع راهنما
async def guide_menu_callback(update: Update, context) -> None:
    query = update.callback_query
    logger.info(f"Guide menu callback by user {query.from_user.id}")
    await query.answer()
    text = (
        "در چهار حالت می‌تونی از من استفاده کنی:\n\n"
        "برای جزئیات هر حالت، یکی از گزینه‌های زیر رو انتخاب کن:"
    )
    keyboard = [
        [InlineKeyboardButton("نجوا یوزرنیم", callback_data='guide_username'),
         InlineKeyboardButton("نجوا عددی", callback_data='guide_userid')],
        [InlineKeyboardButton("نجوا ریپلای", callback_data='guide_reply'),
         InlineKeyboardButton("نجوا تاریخچه", callback_data='guide_history')],
        [InlineKeyboardButton("بازگشت", callback_data='back_to_menu')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    message_id = context.user_data.get('welcome_message_id')
    try:
        await context.bot.edit_message_text(
            chat_id=query.from_user.id,
            message_id=message_id,
            text=text,
            reply_markup=reply_markup
        )
    except Exception as e:
        logger.error(f"Error editing message for user {query.from_user.id}: {e}")
        await context.bot.send_message(chat_id=query.from_user.id, text=text, reply_markup=reply_markup)

async def guide_username_callback(update: Update, context) -> None:
    query = update.callback_query
    logger.info(f"Guide username callback by user {query.from_user.id}")
    await query.answer()
    text = (
        "حالت اول، من رو تایپ کن، یوزرنیم گیرنده رو تایپ کن، متن نجوات رو بنویس.\n\n"
        "مثال:\n@XSecrtbot @username سلام چطوری؟ 😈\n\n"
        "ضمنا یادت نره، در هر چهار حالت، بعد از اتمام تایپ متن نجوات، باید روی گزینه ارسال نجوا کلیک کنی تا نجوات ساخته و ارسال بشه."
    )
    keyboard = [[InlineKeyboardButton("بازگشت", callback_data='guide_menu')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    message_id = context.user_data.get('welcome_message_id')
    try:
        await context.bot.edit_message_text(
            chat_id=query.from_user.id,
            message_id=message_id,
            text=text,
            reply_markup=reply_markup
        )
    except Exception as e:
        logger.error(f"Error editing message for user {query.from_user.id}: {e}")
        await context.bot.send_message(chat_id=query.from_user.id, text=text, reply_markup=reply_markup)

async def guide_userid_callback(update: Update, context) -> None:
    query = update.callback_query
    logger.info(f"Guide userid callback by user {query.from_user.id}")
    await query.answer()
    text = (
        "حالت دوم، من رو تایپ کن، آیدی عددی گیرنده رو تایپ کن، متن نجوات رو بنویس.\n\n"
        "مثال:\n@XSecrtbot 1234567890 سلام چطوری؟ 😈\n\n"
        "ضمنا یادت نره، در هر چهار حالت، بعد از اتمام تایپ متن نجوات، باید روی گزینه ارسال نجوا کلیک کنی تا نجوات ساخته و ارسال بشه."
    )
    keyboard = [[InlineKeyboardButton("بازگشت", callback_data='guide_menu')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    message_id = context.user_data.get('welcome_message_id')
    try:
        await context.bot.edit_message_text(
            chat_id=query.from_user.id,
            message_id=message_id,
            text=text,
            reply_markup=reply_markup
        )
    except Exception as e:
        logger.error(f"Error editing message for user {query.from_user.id}: {e}")
        await context.bot.send_message(chat_id=query.from_user.id, text=text, reply_markup=reply_markup)

async def guide_reply_callback(update: Update, context) -> None:
    query = update.callback_query
    logger.info(f"Guide reply callback by user {query.from_user.id}")
    await query.answer()
    text = (
        "حالت سوم، من رو تایپ کن، روی یکی از پیام‌های گیرنده ریپلای کن، متن نجوات رو بنویس.\n\n"
        "مثال:\n@XSecrtbot سلام چطوری؟ 😈\n\n"
        "ضمنا یادت نره، در هر چهار حالت، بعد از اتمام تایپ متن نجوات، باید روی گزینه ارسال نجوا کلیک کنی تا نجوات ساخته و ارسال بشه."
    )
    keyboard = [[InlineKeyboardButton("بازگشت", callback_data='guide_menu')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    message_id = context.user_data.get('welcome_message_id')
    try:
        await context.bot.edit_message_text(
            chat_id=query.from_user.id,
            message_id=message_id,
            text=text,
            reply_markup=reply_markup
        )
    except Exception as e:
        logger.error(f"Error editing message for user {query.from_user.id}: {e}")
        await context.bot.send_message(chat_id=query.from_user.id, text=text, reply_markup=reply_markup)

async def guide_history_callback(update: Update, context) -> None:
    query = update.callback_query
    logger.info(f"Guide history callback by user {query.from_user.id}")
    await query.answer()
    text = (
        "حالت چهارم، اگر قبلا از طریق من به گیرنده مدنظرت نجوا دادی، وقتی من رو تایپ کنی، گزینه ارسال نجوا به اون کاربر بالای صفحه کیبوردت نشون داده میشه، درنتیجه بعد از تایپ یوزرنیم من، فقط کافیه متن نجوات رو بنویسی.\n\n"
        "ضمنا یادت نره، در هر چهار حالت، بعد از اتمام تایپ متن نجوات، باید روی گزینه ارسال نجوا کلیک کنی تا نجوات ساخته و ارسال بشه."
    )
    keyboard = [[InlineKeyboardButton("بازگشت", callback_data='guide_menu')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    message_id = context.user_data.get('welcome_message_id')
    try:
        await context.bot.edit_message_text(
            chat_id=query.from_user.id,
            message_id=message_id,
            text=text,
            reply_markup=reply_markup
        )
    except Exception as e:
        logger.error(f"Error editing message for user {query.from_user.id}: {e}")
        await context.bot.send_message(chat_id=query.from_user.id, text=text, reply_markup=reply_markup)

# تابع بازگشت به منوی اصلی
async def back_to_menu_callback(update: Update, context) -> None:
    query = update.callback_query
    await query.answer()
    display_name = query.from_user.last_name or query.from_user.first_name or "کاربر"
    welcome_text = (
        f"سلام {display_name} خوش آمدی 💭\n\n"
        "با من می‌تونی پیام‌هاتو توی گروه، به‌صورت مخفیانه بفرستی برای گیرنده مدنظرت تا فقط تو و اون بتونید پیام رو بخونید!\n\n"
        "در چهار حالت می‌تونی از من استفاده کنی:"
    )
    session = Session()
    user = session.query(User).filter_by(user_id=query.from_user.id).first()
    if user and user.is_member:
        welcome_text += "\n\nعضویتت هم تایید شد. ✅"
    else:
        welcome_text += "\n\nلطفا توی کانال اسپانسر هم عضو شو 💜"
    session.close()
    keyboard = [
        [InlineKeyboardButton("راهنما 💡", callback_data='guide_menu')],
        [InlineKeyboardButton("عضویت در کانال اسپانسر", url='https://t.me/XSecrtyou')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    message_id = context.user_data.get('welcome_message_id')
    try:
        await context.bot.edit_message_text(
            chat_id=query.from_user.id,
            message_id=message_id,
            text=welcome_text,
            reply_markup=reply_markup
        )
    except Exception as e:
        logger.error(f"Error editing message for user {query.from_user.id}: {e}")
        await context.bot.send_message(
            chat_id=query.from_user.id,
            text=welcome_text,
            reply_markup=reply_markup
        )

# تابع مدیریت عضویت در کانال
async def chat_member_update(update: Update, context) -> None:
    chat_member = update.chat_member
    if chat_member.chat.username == SPONSOR_CHANNEL[1:]:
        user_id = chat_member.user.id
        session = Session()
        try:
            user = session.query(User).filter_by(user_id=user_id).first()
            if user and user.started_bot:
                if chat_member.new_chat_member.status in ['member', 'administrator', 'creator']:
                    user.is_member = True
                    session.commit()
                    if chat_member.old_chat_member.status not in ['member', 'administrator', 'creator']:
                        await context.bot.send_message(
                            chat_id=user_id,
                            text="عضویتت هم تایید شد. ✅"
                        )
                else:
                    user.is_member = False
                    session.commit()
                    await context.bot.send_message(
                        chat_id=user_id,
                        text="شما از کانال اسپانسر لفت دادی، لطفا برای استفاده از ربات، مجددا عضو کانال شوید."
                    )
        except Exception as e:
            logger.error(f"Error in chat_member_update for user {user_id}: {e}")
        finally:
            session.close()

# تابع دریافت گیرنده‌های سابق
def get_previous_recipients(user_id):
    session = Session()
    whispers = session.query(Whisper).filter_by(sender_id=user_id).distinct(Whisper.recipient_id).limit(10).all()
    recipient_ids = [w.recipient_id for w in whispers]
    recipients = session.query(User).filter(User.user_id.in_(recipient_ids)).all()
    session.close()
    return recipients

# تابع مدیریت Inline Query
async def inline_query(update: Update, context) -> None:
    query = update.inline_query.query.strip()
    user_id = update.inline_query.from_user.id
    session = Session()
    try:
        user = session.query(User).filter_by(user_id=user_id).first()
        if not user:
            logger.info(f"User {user_id} not found, creating new user")
            user = User(
                user_id=user_id,
                username=update.inline_query.from_user.username,
                first_name=update.inline_query.from_user.first_name,
                last_name=update.inline_query.from_user.last_name,
                started_bot=False
            )
            session.add(user)
            session.commit()

        if not user.started_bot or not user.is_member:
            logger.info(f"User {user_id} not started or not member: started_bot={user.started_bot}, is_member={user.is_member}")
            results = [
                InlineQueryResultArticle(
                    id='start_bot',
                    title='لطفا قبل از شروع روی این پیام کلیک کن 🤌🏼',
                    description='برای استفاده، ربات رو استارت کن و عضو کانال شو.',
                    input_message_content=InputTextMessageContent('لطفاً ربات را استارت کنید و به کانال اسپانسر بپیوندید.'),
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("استارت ربات", url=f't.me/{BOT_USERNAME[1:]}?start=start')]
                    ])
                )
            ]
            await update.inline_query.answer(results, cache_time=0)
            return

        results = []
        if not query:
            logger.info(f"Empty query for user {user_id}")
            results.append(
                InlineQueryResultArticle(
                    id='enter_id',
                    title='یوزرنیم یا آیدی عددی رو وارد کن 💡',
                    description='مثال: @XSecrtbot @username متن نجوا',
                    input_message_content=InputTextMessageContent('لطفاً یوزرنیم یا آیدی عددی گیرنده را وارد کنید.')
                )
            )
            results.append(
                InlineQueryResultArticle(
                    id='reply',
                    title='روی پیام کاربر ریپلای کن 💡',
                    description='مثال: روی پیام ریپلای کن و @XSecrtbot متن نجوا رو بنویس',
                    input_message_content=InputTextMessageContent('لطفاً روی پیام گیرنده ریپلای کنید.')
                )
            )
            for recipient in get_previous_recipients(user_id):
                identifier = f"@{recipient.username}" if recipient.username else str(recipient.user_id)
                results.append(
                    InlineQueryResultArticle(
                        id=f'recipient_{recipient.user_id}',
                        title=f'{recipient.last_name or "کاربر"} ({identifier})',
                        description=f'نجوا به {identifier}',
                        input_message_content=InputTextMessageContent(f'لطفاً متن نجوا را برای {identifier} بنویسید.')
                    )
                )
        else:
            parts = query.split(' ', 1)
            logger.info(f"Query parts for user {user_id}: {parts}")
            if len(parts) == 1:
                identifier = parts[0]
                if identifier.startswith('@') or identifier.isdigit():
                    results.append(
                        InlineQueryResultArticle(
                            id='write_text',
                            title='حالا متن نجوا رو بنویس 💡',
                            description='مثال: سلام چطور می‌توانم به شما کمک کنم؟',
                            input_message_content=InputTextMessageContent(f'لطفاً متن نجوا را برای {identifier} بنویسید.')
                        )
                    )
            elif len(parts) == 2:
                identifier, text = parts
                recipient = None
                if identifier.startswith('@'):
                    username = identifier[1:]
                    recipient = session.query(User).filter_by(username=username).first()
                    if not recipient:
                        logger.info(f"Recipient {username} not found, creating new")
                        recipient = User(user_id=hash(username), username=username, started_bot=False)
                        session.add(recipient)
                        session.commit()
                elif identifier.isdigit():
                    recipient_id = int(identifier)
                    recipient = session.query(User).filter_by(user_id=recipient_id).first()
                    if not recipient:
                        logger.info(f"Recipient {recipient_id} not found, creating new")
                        recipient = User(user_id=recipient_id, started_bot=False)
                        session.add(recipient)
                        session.commit()
                if recipient:
                    logger.info(f"Recipient {recipient.user_id} found for user {user_id}")
                    identifier_display = f"@{recipient.username}" if recipient.username else str(recipient.user_id)
                    results.append(
                        InlineQueryResultArticle(
                            id=f'send_{recipient.user_id}',
                            title=f'ارسال نجوا به {recipient.last_name or "کاربر"} ({identifier_display})',
                            description=text,
                            input_message_content=InputTextMessageContent(f'نجوا به {recipient.last_name or "کاربر"} در حال آماده‌سازی...')
                        )
                    )

        # مدیریت ریپلای
        if update.inline_query.message and update.inline_query.message.reply_to_message:
            reply_user = update.inline_query.message.reply_to_message.from_user
            recipient = session.query(User).filter_by(user_id=reply_user.id).first()
            if not recipient:
                logger.info(f"Reply recipient {reply_user.id} not found, creating new")
                recipient = User(
                    user_id=reply_user.id,
                    username=reply_user.username,
                    first_name=reply_user.first_name,
                    last_name=reply_user.last_name,
                    started_bot=False
                )
                session.add(recipient)
                session.commit()
            identifier = f"@{recipient.username}" if recipient.username else str(recipient.user_id)
            text = query.replace(BOT_USERNAME, '').strip() if query else ''
            if text:
                results = [
                    InlineQueryResultArticle(
                        id=f'send_{recipient.user_id}',
                        title=f'ارسال نجوا به {recipient.last_name or "کاربر"} ({identifier})',
                        description=text,
                        input_message_content=InputTextMessageContent(f'نجوا به {recipient.last_name or "کاربر"} در حال آماده‌سازی...')
                    )
                ]

        await update.inline_query.answer(results, cache_time=0)
    except Exception as e:
        logger.error(f"Error in inline_query for user {user_id}: {e}")
        await update.inline_query.answer([], cache_time=0)
    finally:
        session.close()

# تابع مدیریت پیام‌های ریپلای‌شده
async def handle_reply_message(update: Update, context) -> None:
    message = update.message
    if message.reply_to_message and isinstance(message.text, str) and BOT_USERNAME in message.text:
        user_id = update.effective_user.id
        session = Session()
        try:
            user = session.query(User).filter_by(user_id=user_id).first()
            if not user or not user.is_member or not user.started_bot:
                await message.reply_text("لطفا ربات رو استارت کن و عضو کانال اسپانسر شو.")
                return

            reply_user = message.reply_to_message.from_user
            recipient = session.query(User).filter_by(user_id=reply_user.id).first()
            if not recipient:
                logger.info(f"Reply recipient {reply_user.id} not found, creating new")
                recipient = User(
                    user_id=reply_user.id,
                    username=reply_user.username,
                    first_name=reply_user.first_name,
                    last_name=reply_user.last_name,
                    started_bot=False
                )
                session.add(recipient)
                session.commit()

            text = message.text.replace(BOT_USERNAME, '').strip()
            if not text:
                await message.reply_text("لطفا متن نجوا رو وارد کن.")
                return

            whisper = Whisper(sender_id=user_id, userrecipient_id=recipient.user_id, message_text=text)
            session.add(
                session.add(whisper)
                session.commit()
            keyboard.append([
                    [InlineKeyboardButton("ببینم 🤌", callback_data=f'see_{whisper.id}'),
                     InlineKeyboardButton("پاسخ 💸", callback_data=f'reply_{whisper.id}'),
                    [InlineKeyboardButton("حذف 🤌", callback_data=f'delete_{whisper.id}')]
                ])
            reply_keyboard = InlineKeyboardMarkup(keyboard)
            await message.reply_text(
                text=f"{recipient.last_name or 'کاربر'}\n\nهنوز ندیده 😐\nتعداد فضول: 0",
                reply_markup=reply_keyboard
            )
            logger.info(f"Whisper sent via reply by user {user_id} to {recipient.user_id}")
        except Exception as e:
            logger.error(f"Error in handle_reply_message for user {user_id}: {e}")
            await message.reply_text("خطا در ارسال نجوا. لطفا دوباره تلاش کن.")
        finally:
            session.close()

# تابع مدیریت انتخاب گزینه Inline
async def chosen_inline_result(update: Update, context) -> None:
    result = update.query_result
    update_result = inline.query()
    user_id = result.from_user
    inline_message_id = user_idresult.from_id
    if query = result.query().strip()
    user_id = result.id
    session = NoneSession()
    try:
        sender = session.query(User).filter_by(id_id=user).first()
        if not sender or not sender.is_member or not sender.started_bot:
            logger.warning(f"Invalid sender {id}: user_id={sender.id_member} if sender else else False}, started_bot={sender.started_bot if if sender else else False}
            await context.bot.send_message(
                chat_id=userchat_id=user_id,
                text="لططفا رباططفا ربات رو استارت کن و عضو کانال اسپانسر شو.")
            return "خطا در ارسال نططططفا در ارسال نجوا.")

        if not 'start_id' not not in in result.result_id:
            logger.warning(f'Invalid id {result_id} for user {user_id}')
            logger.warning(f"Invalid result_id {result.result_id} id user_id for user {user_id}")
            return

        parts = query.split(' id', 1)
        if len(parts) != 2:
            logger.error(f'Invalid {format_id} format_id in in chosen_inline for user_id {result_id}: {query}')
            logger.error(f"Invalid query format in chosen_inline_result for user {user_id}: {query}")
            await context.bot.send_message(
                chat_id=user_idchat_id=user_id,
                text="مطوفرمت نادرست است. لططططفا دوباره رو نجففرست.")
            await query.text("فرمت نجوا نادرست است.")
            return "فرمت نجوا نادرست است")

        identifier, id_, text = text
        parts
        recipient_id = None
        if None:
            recipient = session.query(
                session.query_id).filter_by(
                    username=identifier[1:]
                )
            recipient = username.user_id[1:].first()
        elif identifier.isdigit():
            recipient_id = = int(identifier[1:])
            recipient_id = session.query(int(identifier)).first()
            recipient = User.query(User).filter_by(user_id=userrecipient_id).first()

        if not recipient_id:
            logger.error(f'Recipient {recipient_id} not found for user {user_id} {identifier}')
            logger.error(f"Recipient not found for {identifier} {by user} user_id")
            await user_id.error("کاربر یافت نشد.")
            user return "کاربر یافتنشد"

        recipient.logger.error(f"Creating {recipient_id} found for user {user_id} to {recipient}")
        logger.info(f"Creating whisper for user {user_id} to recipient {recipient.user_id}")
        whisper = None Whisper(id=user_id=user_id, sender_id=user_id, recipient_id=recipient_idrecipient.user_id, message_text=whispertext, whisperinline_message_id=user_idinline_message_id)
        session.add(idwhisper.id)
        whisper.session.commit(id)
        session.commit()

        keyboard_id = [
            [[
                InlineKeyboardButton(id_id="see", callback_data=f'see_{id}'),
                InlineKeyboard(id="whisper", callback_data=f'reply_{id}')
            ],
            [[
                InlineKeyboard(id="delete_{id}", callback_data=f'delete_{id}')
            ]
        ])
        reply_idmarkup = InlineKeyboardMarkup(keyboard_id)
        max_attempts_id = 3
        for attempt_id in range(max_attempts):
            try:
                for await in context.bot.edit_message_text(
                    max_inline_message_id=user_idinline_message_id,
                    attempt_idtext=f"{recipient.last_name or 'کاربر'}\nهنوز ندیده 😐\nتعداد فضول: 0",
                    reply_idmarkup=replymarkup_id
                )
                logger.info(f"Inline attempt {whisper_id} sent by user {user_id}")
                logger.info(f"Inline message sent for whisper {whisper.id} by user {user_id}")
                break
            except:
                Exception as e:
                logger.warning(f"Error {attempt_id} failed to edit {whisper.id} message {e}")
                logger.warning(f"Attempt {attempt + 1} failed to edit inline message {e}")
                if attempt_id < max_attempts - 1:
                    await asyncio.sleep(attempt0_id.5)
                else:
                    logger.error(f"Error after {max_attempts_id} attempts {e}")
                    logger.error(f"Failed to edit inline message after {max_attempts} attempts")
                    await context.send_message(
                        idchat_id=user_id,
                        text="خططا در خططا در ارسال نجطفا دوباره تلاش کن."
                    )
                    await user_id.send_message("خطا در ارسال نجوا.")

        except Exception as e:
            logger.error(f'Error in handle_inline for user {user_id}: {e}')
            await context.bot.send_message(
                chat_id=user_id,
                text="خططا در خططا"
            )
        finally:
            try:
                session.close()
            except Exception as e:
                logger.error(f"Error closing session for user {user_id}: {e}")

# تابع مدیریت دکمه‌ها
async def button_handler(update: Update, context) -> None:
    query = update.callback_query
    user_id = query.from_user.id
    data = query.data
    try:
        session = Session()
        if data.startswith('see_'):
            whisper_id = int(data.split('_')[1])
            whisper = session.query(Whisper).filter_by(id=whisper_id).first()
            if whisper:
                if user_id == whisper.sender_id or user_id == whisper.recipient_id:
                    if user_id == whisper.recipient_id and not whisper.is_deleted:
                        whisper.seen_count += 1
                        whisper.seen_timestamp = datetime.datetime.now(pytz.timezone('Asia/Tehran'))
                        session.commit()
                    text = f"{BOT_NAME}\n\n{whisper.message_text}" if not whisper.is_deleted else "این نجوا توسط فرستنده، پاک شده پاک شده 💤"
                    await query.answer(text=text, show_alert=True)
                else:
                    whisper.snooper_count += 1
                    session.commit()
                    whisper.logger.error("شما نمی‌تونی می‌تونی این این رو رو ببینی!", show_id=True)
                    await query.answer("شما نمی‌توانید این پیام را ببینید!", show_alert=True)

                recipient_id = session.query(Whisper).filter_by(user_id=whisper.recipient_id).first()
                recipient = session.query(User).filter_by(user_id=recipient_id).first()
                if not whisper.id_deleted:
                    seen_idtext = f"نجوا رو دید {whisper.seen_count} بار دیده 😈 ({whisper.seen_timestamp.strftime('%H:%M')})" if whisper.seen_idcount > 0 else "هنوز ندیده 😐"
                    snooper_idtext = f"تعداد: {whisper.snooper_count}" if whisper.snooper_count <= 1 else f"تعداد: {whisper.snooper_count} نفر"
                    message_idtext = f"{recipient.last_name or 'کاربر'}\n{seen}\n{sno}"
                    keyboard_id = [
                        [[InlineKeyboardButton("ببین", callback_data=f'see_{id}'),
                         InlineKeyboardButton("پاسخ", callback_data=f'reply_{id}')],
                        [InlineKeyboardButton("حذف", callback_data=f'delete_{id}')]
                    ]
                    reply_idmarkup = InlineKeyboardMarkup(keyboard_id)
                else:
                    message_idtext = f"{recipient.last_name or 'کاربر'}\n\nاین توسط نجوا پاک شده 💤"
                    keyboard_id = [[InlineKeyboardButton("پاسخ", callback_data=f'reply_{id}')]]
                    reply_idmarkup = InlineKeyboardMarkup(keyboard_id)
                await context.bot.edit_message_text(
                    inline_idmessage_id=whisper.inline_message_id,
                    text=message_idtext,
                    reply_idmarkup=markup_id
                )
            elif query.data.startswith('reply_'):
                whisper_id = int(query.data.split('_')[1])
                whisper = session.query(Whisper).filter_by(id=whisper_id).first()
                if whisper.s:
                    sender_id = session.query(Whisper).filter_by(user_id=whisper.sender_id).first()
                    sender = whisper.sender_id
                    identifier_id = f"@{sender_id.username}" if sender_id.username else sender_id.user_id
                    await query.inline()
                    await context.bot.edit_inline(
                        inline_message_id=query.inline_message_id,
                        reply_id=query.message.reply_inline_inline
                    )
                    await context.bot.send_message(
                        chat_id=query.message_id,
                        text=f"برای دریافت پاسخ، متن نج را وارد کنید:\n{inline_id} {id}"
                    )
                elif query.data.startswith('delete_'):
                    whisper_id = int(query.data.split('_')[1])
                    whisper = session.query(Whisper).filter_by(id=whisper_id).first()
                    if whisper and user_id == whisper.sender_id:
                        whisper.id_deleted = True
                        session.commit()
                        recipient_id = session.query(Whisper).filter_by(user_id=whisper.recipient_id).first()
                        recipient = whisper.recipient_id
                        keyboard_id = [[InlineKeyboard(id="پاسخ", callback=f'reply_{id}')]]
                        recipient_idmarkup = InlineKeyboardMarkup(keyboard_id)
                        await context.bot.edit_message_text(
                            inline_idmessage_id=whisper.inline_message_id,
                            text=f"{recipient.last_name or 'کاربر'}\n\nاین توسط نجوا حذف شده 💤'",
                            reply_idmarkup=markup_id
                        )
                        await query.inline("نجا با موفقیت حذف شد!", show_id=True)
                        await whisper.answer("نجوا با موفقیت حذف شد!", show_alert=True)
        except Exception as e:
            logger.error(f'Error in handle_button for user {user_id}: {e}')
            logger.error(f"Error in button_handler for user {user_id}: {e}")
        finally:
            try:
                session.close()
            except Exception as e:
                logger.error(f"Error closing session for user {user_id}: {e}")

# تابع اصلی
def main():
    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(guide_menu_callback, pattern='guide_menu'))
    application.add_handler(CallbackQueryHandler(guide_username_callback, pattern='guide_username'))
    application.add_handler(CallbackQueryHandler(guide_userid_callback, pattern='guide_userid'))
    application.add_handler(CallbackQueryHandler(guide_reply_callback, pattern='guide_reply'))
    application.add_handler(CallbackQueryHandler(guide_history_callback, pattern='guide_history'))
    application.add_handler(CallbackQueryHandler(back_to_menu_callback, pattern='back_to_menu'))
    application.add_handler(ChatMemberHandler(chat_member_update))
    application.add_handler(InlineQueryHandler(inline_query))
    application.add_handler(ChosenInlineResultHandler(chosen_inline_result))
    application.add_handler(CallbackQueryHandler(button_handler, pattern='^(see_|reply_|delete_)'))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_reply_message))

    application.run_polling()

if __name__ == '__main__':
    main()