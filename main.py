import os
import logging
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

# تابع خوش‌آمدگویی با استارت
async def start(update: Update, context: CallbackContext) -> None:
    user = update.effective_user
    session = Session()
    db_user = session.query(User).filter_by(user_id=user.id).first()
    if not db_user:
        db_user = User(user_id=user.id, username=user.username, first_name=user.first_name, last_name=user.last_name, started_bot=True)
        session.add(db_user)
    else:
        db_user.started_bot = True
    session.commit()

    # بررسی وضعیت عضویت در کانال
    membership_text = ""
    try:
        member = await context.bot.get_chat_member(chat_id=SPONSOR_CHANNEL, user_id=user.id)
        if member.status in ['member', 'administrator', 'creator']:
            db_user.is_member = True
            membership_text = "عضویتت هم تایید شد. ✅"
        else:
            db_user.is_member = False
            membership_text = "لطفا عضو کانال اسپانسر شوید."
    except Exception as e:
        logger.error(f"Error checking membership: {e}")
        membership_text = "خطا در بررسی عضویت. لطفا بعدا تلاش کنید."

    session.commit()
    session.close()

    # مدیریت نام کاربر
    display_name = user.last_name or user.first_name or "کاربر"
    welcome_text = f"سلام {display_name} خوش آمدی 💭\n\nبا من میتونی پیام هاتو توی گروه، بصورت مخفیانه بفرستی برای گیرنده مدنظرت تا فقط تو و اون بتونید پیام رو بخونید!\n\nدر چهار حالت میتونی از من استفاده کنی:\n\n{membership_text}"
    keyboard = [
        [InlineKeyboardButton("نجوا یوزرنیم", callback_data='guide_username'),
         InlineKeyboardButton("نجوا عددی", callback_data='guide_userid')],
        [InlineKeyboardButton("نجوا ریپلای", callback_data='guide_reply'),
         InlineKeyboardButton("نجوا تاریخچه", callback_data='guide_history')],
        [InlineKeyboardButton("عضویت در کانال اسپانسر", url=f'https://t.me/{SPONSOR_CHANNEL[1:]}')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    message = await context.bot.send_message(chat_id=user.id, text=welcome_text, reply_markup=reply_markup)
    context.user_data['welcome_message_id'] = message.message_id  # ذخیره message_id

# توابع راهنمای جزئی با لاگ و ویرایش پیام
async def guide_username_callback(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    logger.info(f"Guide username callback triggered by user {query.from_user.id}")
    await query.answer()
    text = "حالت اول، من رو تایپ کن، یوزرنیم گیرنده رو تایپ کن، متن نجوات رو بنویس.\n\nمثال:\n@XSecrtbot @username سلام چطوری؟ 😈\n\nضمنا یادت نره، در هر چهار حالت، بعد از اتمام تایپ متن نجوات، باید روی گزینه ارسال نجوا، کلیک کنی تا نجوات ساخته و ارسال بشه."
    keyboard = [[InlineKeyboardButton("بازگشت", callback_data='back_to_menu')]]
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
        logger.error(f"Error editing message: {e}")
        await context.bot.send_message(chat_id=query.from_user.id, text=text, reply_markup=reply_markup)

async def guide_userid_callback(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    logger.info(f"Guide userid callback triggered by user {query.from_user.id}")
    await query.answer()
    text = "حالت دوم، من رو تایپ کن، آیدی عددی گیرنده رو تایپ کن، متن نجوات رو بنویس.\n\nمثال:\n@XSecrtbot 1234567890 سلام چطوری؟ 😈\n\nضمنا یادت نره، در هر چهار حالت، بعد از اتمام تایپ متن نجوات، باید روی گزینه ارسال نجوا، کلیک کنی تا نجوات ساخته و ارسال بشه."
    keyboard = [[InlineKeyboardButton("بازگشت", callback_data='back_to_menu')]]
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
        logger.error(f"Error editing message: {e}")
        await context.bot.send_message(chat_id=query.from_user.id, text=text, reply_markup=reply_markup)

async def guide_reply_callback(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    logger.info(f"Guide reply callback triggered by user {query.from_user.id}")
    await query.answer()
    text = "حالت سوم، من رو تایپ کن، روی یکی از پیام های گیرنده ریپلای کن، متن نجوات رو بنویس.\n\nمثال:\n@XSecrtbot سلام چطوری؟ 😈\n\nضمنا یادت نره، در هر چهار حالت، بعد از اتمام تایپ متن نجوات، باید روی گزینه ارسال نجوا، کلیک کنی تا نجوات ساخته و ارسال بشه."
    keyboard = [[InlineKeyboardButton("بازگشت", callback_data='back_to_menu')]]
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
        logger.error(f"Error editing message: {e}")
        await context.bot.send_message(chat_id=query.from_user.id, text=text, reply_markup=reply_markup)

async def guide_history_callback(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    logger.info(f"Guide history callback triggered by user {query.from_user.id}")
    await query.answer()
    text = "حالت چهارم، اگر قبلا از طریق من به گیرنده مدنظرت نجوا دادی، وقتی من رو تایپ کنی، گزینه ارسال نجوا به اون کاربر بالای صفحه کیبوردت نشون داده میشه، درنتیجه بعد از تایپ یوزرنیم من، فقط کافیه متن نجوات رو بنویسی.\n\nضمنا یادت نره، در هر چهار حالت، بعد از اتمام تایپ متن نجوات، باید روی گزینه ارسال نجوا، کلیک کنی تا نجوات ساخته و ارسال بشه."
    keyboard = [[InlineKeyboardButton("بازگشت", callback_data='back_to_menu')]]
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
        logger.error(f"Error editing message: {e}")
        await context.bot.send_message(chat_id=query.from_user.id, text=text, reply_markup=reply_markup)

# تابع بازگشت به منوی اصلی
async def back_to_menu_callback(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    await query.answer()
    display_name = query.from_user.last_name or query.from_user.first_name or "کاربر"
    welcome_text = f"سلام {display_name} خوش آمدی 💭\n\nبا من میتونی پیام هاتو توی گروه، بصورت مخفیانه بفرستی برای گیرنده مدنظرت تا فقط تو و اون بتونید پیام رو بخونید!\n\nدر چهار حالت میتونی از من استفاده کنی:"
    session = Session()
    user = session.query(User).filter_by(user_id=query.from_user.id).first()
    if user and user.is_member:
        welcome_text += "\n\nعضویتت هم تایید شد. ✅"
    else:
        welcome_text += "\n\nلطفا عضو کانال اسپانسر شوید."
    session.close()
    keyboard = [
        [InlineKeyboardButton("نجوا یوزرنیم", callback_data='guide_username'),
         InlineKeyboardButton("نجوا عددی", callback_data='guide_userid')],
        [InlineKeyboardButton("نجوا ریپلای", callback_data='guide_reply'),
         InlineKeyboardButton("نجوا تاریخچه", callback_data='guide_history')],
        [InlineKeyboardButton("عضویت در کانال اسپانسر", url=f'https://t.me/{SPONSOR_CHANNEL[1:]}')]
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
        logger.error(f"Error editing message: {e}")
        await context.bot.send_message(
            chat_id=query.from_user.id,
            text=welcome_text,
            reply_markup=reply_markup
        )

# تابع مدیریت عضویت در کانال
async def chat_member_update(update: Update, context: CallbackContext) -> None:
    chat_member = update.chat_member
    if chat_member.chat.username == SPONSOR_CHANNEL[1:]:
        user_id = chat_member.user.id
        session = Session()
        user = session.query(User).filter_by(user_id=user_id).first()
        try:
            if user and user.started_bot:
                if chat_member.new_chat_member.status in ['member', 'administrator', 'creator']:
                    user.is_member = True
                    membership_text = "عضویتت هم شد. ✅"
                else:
                    user.is_member = False
                    membership_text = "شما از کانال اسپانسر لفت دادی، لطفا برای استفاده از ربات، دوباره عضو کانال شوید."
                session.commit()
            # به‌روزرسانی پیام خوش‌آمدگویی
                display_name = chat_member.user.last_name or chat_member.user.first_name or "کاربر"
                welcome_text = f"سلام {display_name} خوش آمدی 💫\n\nبا من میتونی پیام هاتو توی گروه، بصورت مخفیانه بفرستی برای گیرنده مدنظرت تا فقط تو و اون بتونید پیام رو بخونید!\n\nدر چهار حالت میتونی از من استفاده کنی:\n\n{membership_text}"
                keyboard = [
                    [InlineKeyboardButton("نجوا یوزرنیم", callback_data='guide_username'),
                     InlineKeyboardButton("نجوا عددی", callback_data='guide_userid')],
                    [InlineKeyboardButton("نجوا ریپلای", callback_data='guide_reply'),
                     InlineKeyboardButton("نجوا تاریخچه", callback_data='guide_history')],
                    [InlineKeyboardButton("عضویت در کانال اسپانسر", url=f'https://t.me/{SPONSOR_CHANNEL[1:]}')]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                message_id = context.user_data.get('welcome_message_id')
                try:
                    await context.bot.edit_message_text(
                        chat_id=user_id,
                        message_id=message_id,
                        text=welcome_text,
                        reply_markup=reply_markup
                    )
                except Exception as e:
                    logger.error(f"Error editing message: {e}")
                    await context.bot.send_message(
                        chat_id=user_id,
                        text=welcome_text,
                        reply_markup=reply_markup
                    )
        finally:
            session.close()

# تابع دریافت گیرنده‌های سابق
def get_previous_recipients(user_id):
    session = Session()
    whispers = session.query(Whisper).filter_by(sender_id=user_id).distinct(Whisper.recipient_id).limit(10).all()
    recipient_ids = [w.recipient_id for w in whispers]
    recipients = session.query(User).filter_by(User.user_id.in_(recipient_ids)).all()
    session.close()
    return recipients

# تابع مدیریت Inline Query
async def inline_query(update: Update, context: CallbackContext) -> None:
    query = update.inline_query.query.strip()
    user_id = update.inline_query.from_user.id
    session = Session()
    user = session.query(User).filter_by(user_id=user_id).first()

    logger.info(f"Inline query by user {user_id}: '{query}'")

    try:
        if not user:
            logger.info(f"User {user_id} not found in database, creating new user")
            user = User(user_id=user_id, username=update.inline_query.from_user.username,
                               first_name=update.inline_query.from_user.first_name,
                               last_name=update.inline_query.from_user.last_name,
                               started_bot=True)
            session.add(user)
            session.commit()

        if not user.started_bot or not user.is_member:
            logger.info(f"User {user_id} not started or not member: started_bot={user.started_bot}, is_member={user.is_member}")
            results = [
                InlineQueryResultArticle(
                    id='start_bot',
                    title='لطفا قبل از شروع روی این پیام کلیک کن🤌🏼',
                    description='برای استفاده از ربات، ابتدا آن را استارت کنید.',
                    input_message_content=InputTextMessageContent('لطفا ربات را استارت کنید و عضو کانال اسپانسر شوید.'),
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("استارت ربات", url=f'https://t.me/XSecrtbot?start=start')]
                    ])
                )
            ]
        else:
            results = []
            if not query:
                logger.info(f"Empty query for user {user_id}")
                results.append(
                    InlineQueryResultArticle(
                        id='enter_id',
                        title='یوزرنیم یا آیدی عددی رو وارد کن 💡',
                        description='مثال: @XSecrtbot @username متن نجوا',
                        input_message_content=InputTextMessageContent('لطفا یوزرنیم یا آیدی عددی و متن نجوا را وارد کنید.')
                )
                results.append(
                    InlineQueryResultArticle(
                        id='reply',
                        title='روی پیام کاربر ریپلای کن 💡',
                        description='مثال: روی پیام ریپلای کن و @XSecrtbot متن نجوا را بنویس',
                        input_message_content=InputTextMessageContent('لطفا روی پیام کاربر ریپلای کنید و @XSecrtbot را تایپ کنید.')
                )
            for recipient in get_previous_recipients(user_id):
                identifier = f"@{recipient.username}" if recipient.username else str(recipient.user_id)
                results.append(
                    InlineQueryResultArticle(
                        id=f'recipient_{recipient.user_id}',
                        title=f'{recipient.last_name or "کاربر"} ({identifier})',
                        description=f'ارسال نجوا به {identifier}',
                        input_message_content=InputTextMessageContent(f'{BOT_USERNAME} {identifier}')
                    )
                )
        else:
            parts = query.split(' ', 1)
            logger.info(f"Query parts for user {user_id}: {parts}")
            if len(parts) == 2:
                identifier, text = parts
                recipient = None
                if identifier.startswith('@'):
                    username = identifier[1:]
                    recipient = session.query(User).filter_by(username=).first()
                    if not recipient:
                        logger.info(f"Recipient {username} not found, creating new recipient")
                        recipient = User(user_id=hash(username), username=username, started_bot=False)
                        session.add(recipient)
                        session.commit()
                elif identifier.isdigit():
                    recipient_id = int(identifier)
                    recipient = session.query(User).filter_by(user_id=recipient_id).first()
                    if not recipient:
                        logger.info(f"Recipient {recipient_id} not found, creating new recipient")
                        recipient = User(user_id=recipient_id, started_bot=False)
                        session.add(recipient)
                        session.commit()
                if recipient:
                    logger.info(f"Recipient {recipient.user_id} found or created for user {user_id}")
                    results.append(
                        InlineQueryResultArticle(
                            id=f'send_{recipient.user_id}',
                            title=f'ارسال نجوا به {recipient.last_name or "کاربر"} ({"@" + recipient.username if recipient.username else recipient.user_id})',
                            description=text,
                            input_message_content=InputTextMessageContent(f'در حال ارسال نجوا به {recipient.last_name or "کاربر"}...')
                        )
                    )
            elif len(parts) == 1:
                identifier = parts[0]
                if identifier.startswith('@') or identifier.isdigit():
                    results.append(
                        InlineQueryResultArticle(
                            id='write_text',
                            title='حالا متن نجوا رو بنویس 😈',
                            description='مثال: سلام چطور می‌توانم به شما کمک کنم؟',
                            input_message_content=InputTextMessageContent('لطفا متن نجوا را وارد کنید.')
                    )
        await update.inline_query.answer(results, cache_time=0)
    except Exception as e:
        logger.error(f"Error in inline_query: {e}")
    finally:
        session.close()

# تابع مدیریت پیام‌های ریپلای‌شده
async def handle_reply_message(update: Update, context: CallbackContext) -> None:
    message = update.message
    if message.reply_to_message and isinstance(message.text, str) and BOT_USERNAME in message.text:
        user_id = update.effective_user.id
        session = Session()
        try:
            user = session.query(User).filter_by(user_id=user_id).first()

            if not user or not user.started_bot or not user.is_member:
                await message.reply_text("لطفا ربات را استارت کنید و عضو کانال اسپانسر شوید.")
                return

            reply_user = message.reply_to_message.from_user
            recipient = session.query(User).filter_by(user_id=reply_user.id).first()
            if not recipient:
                logger.info(f"Reply recipient user {reply_user.id} not found, creating new recipient")
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
            if text:
                await message.reply_text("لطفا متن نجوا را وارد کنید.")
                return

            whisper = Whisper(sender_id=user_id, recipient_id=recipient.user_id, message_text=text)
            session.add(wisper)
            session.commit()
            keyboard = [
                [InlineKeyboardButton("ببینم 🤔", callback_data=f'see_{whisper.id}'),
                 InlineKeyboardButton("پاسخ 💪", callback_data=f'reply_{whisper.id}'),
                [InlineKeyboardButton("حذف 🤖", callback_data=f'delete_{whisper.id}')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await message.reply_text(
                text=f"{recipient.last_name or 'کاربر'}\n\nهنوز ندیده 😐\nتعداد فضول: 0",
                reply_markup=reply_markup
            )
            logger.info(f"Whisper sent via reply by user {user_id} to {recipient.user_id}")
        except Exception as e:
            logger.error(f"Error in handle_reply_message: {e}")
            await message.reply_text("خطا در ارسال نجوا. لطفا دوباره تلاش کنید.")
        finally:
            session.close()

# تابع مدیریت انتخاب گزینه Inline
async def chosen_inline_result(update: Update, context: CallbackContext) -> None:
    result = update.chosen_inline_result
    user_id = result.from_user.id
    inline_message_id = result.inline_message_id
    query = result.query.strip()
    session = Session()

    logger.info(f"Chosen inline result by user {user_id}: result_id={result.result_id}, query='{query}'")

    try:
        sender = session.query(User).filter_by(user_id=user_id).first()
        if sender and sender.is_member and sender.started_bot:
            if 'send_' in result.result_id:
                parts = query.split(' ', 1)
                if len(parts) != 2:
                    logger.error(f"Invalid query format in chosen_inline_result: {query}")
                    return
                identifier, text = parts
                recipient = None
                if identifier.startswith('@'):
                    recipient = session.query(User).filter_by(username=identifier[1:]).first()
                elif identifier.isdigit():
                    recipient = session.query(User).filter_by(user_id=int(identifier)).first()
                if recipient:
                    whisper = Whisper(sender_id=user_id, recipient_id=recipient.user_id, message_text=text, inline_message_id=inline_message_id)
                    session.add(whisper)
                    session.commit()
                    keyboard = [
                        [InlineKeyboardButton("ببینم 🤔", callback_data=f'see_{whisper.id}'),
                         InlineKeyboardButton("پاسخ 💪", callback_data=f'reply_{whisper.id}')],
                        [InlineKeyboardButton("حذف 🤖", callback_data=f'delete_{whisper.id}')]
                    ]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    await context.bot.edit_message_text(
                        inline_message_id=inline_message_id,
                        text=f"{recipient.last_name or 'کاربر'}\n\nهنوز ندیده 😐\nتعداد فضول: 0",
                        reply_markup=reply_markup
                    )
                    logger.info(f"Inline message edited successfully for whisper {whisper.id}")
    except Exception as e:
        logger.error(f"Error in chosen_inline_result: {e}")
        await context.bot.send_message(
            chat_id=user_id,
            text=f"خطا در ارسال نجوا. لطفا دوباره تلاش کنید."
        )
    finally:
        session.close()

# تابع مدیریت دکمه‌ها
async def button_handler(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    user_id = query.from_user.id
    data = query.data
    session = Session()

    try:
        if data.startswith('see_'):
            whisper_id = int(data.split('_')[1])
            whisper = session.query(Whisper).filter_by(id=whisper_id).first()
            if whisper:
                if user_id == whisper.sender_id or user_id == whisper.recipient_id:
                    if user_id == whisper.recipient_id and not whisper.is_deleted:
                        whisper.seen_count += 1
                        whisper.seen_timestamp = datetime.datetime.now(pytz.timezone('UTC'))
                        session.commit()
                    text = f"XSecret 💫 \n\n{whisper.message_text}" if not whisper.is_deleted else "اینIFIEDا توسط فرستنده، پاک شده 💤"
                    await query.answer(text=text, show_alert=True)
                else:
                    whisper.snooper_count += 1
                    session.commit()
                    await query.answer("شما مجاز به دیدن این نجوا نیستید!", show_alert=True)

                recipient = session.query(User).filter_by(user_id=whisper.recipient_id).first()
                if not whisper.is_deleted:
                    seen_text = f"نجوا را {whisper.seen_count} بار دیده 😈 ({whisper.seen_timestamp.strftime('%H:%M')})" if whisper.seen_count > 0 else "هنوز ندیده 😊"
                    snooper_text = f"تعداد فضول: {whisper.snooper_count}" if whisper.snooper_count <= 0 else f"تعداد فضول: {whisper.snooper_count} نفر"
                    message_text = f"{recipient.last_name or 'کاربر'}\n\n{seen_text}\n{snooper_text}"
                    keyboard = [
                        [InlineKeyboardButton("ببینم 🤔", callback_data=f'see_{whisper.id}'),
                         InlineKeyboardButton("پاسخ 💪", callback_data=f'reply_{whisper.id}')],
                        [InlineKeyboardButton("حذف 🤖", callback_data=f'delete_{whisper.id}')]
                    ]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                else:
                    message_text = f"{recipient.last_name or 'کاربر'}\n\nاین نجوا توسط فرستنده، پاک شده 💤"
                    keyboard = [[InlineKeyboardButton("پاسخ 💪", callback_data=f'reply_{whisper.id}')]]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                await context.bot.edit_message_text(
                    inline_message_id= אר                    inline_message_id=whisper.inline_message_id,
                    text=message_text,
                    reply_markup=reply_markup
                )
        elif data.startswith('reply_'):
            whisper_id = int(data.split('_')[1])
            whisper = session.query(Whisper).filter_by(id=whisper_id).first()
            if whisper:
                sender = session.query(User).filter_by(user_id=whisper.sender_id).first()
                identifier = f"@{sender.username}" if sender.username else f"{sender.user_id}"
                await query.answer()
                await context.bot.edit_message_reply_markup(
                    inline_message_id=query.inline_message_id,
                    reply_markup=query.message.reply_markup
                )
                await context.bot.send_message(
                    chat_id=query.from_user.id,
                    text=f"برای پاسخ، متن نجوا را وارد کنید:\n{BOT_USERNAME} {identifier} "
                )
        elif data.startswith('delete_'):
            whisper_id = int(data.split('_')[1])
            whisper = session.query(Whisper).filter_by(id=whisper_id).first()
            if whisper and user_id == whisper.sender_id:
                whisper.is_deleted = True
                session.commit()
                recipient = session.query(User).filter_by(user_id=whisper.recipient_id).first()
                keyboard = [[InlineKeyboardButton("پاسخ 💪", callback_data=f'reply_{whisper.id}')]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await context.bot.edit_message_text(
                    inline_message_id=whisper.inline_message_id,
                    text=f"{recipient.last_name or 'کاربر'}\n\nاین نجوا توسط فرستنده، پاک شده 💤",
                    reply_markup=reply_markup
                )
                await query.answer("نجوا با موفقیت حذف شد!", show_alert=True)
    except Exception as e:
        logger.error(f"Error in button_handler: {e}")
    finally:
        session.close()

# تابع اصلی
def main():
    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
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