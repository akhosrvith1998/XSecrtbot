import sqlite3
import telegram
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, InlineQueryResultArticle, InputTextMessageContent
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, InlineQueryHandler, CallbackQueryHandler, ContextTypes
import os
from datetime import datetime
import pytz
import asyncio
import traceback

# لاگ نسخه پکیج
print(f"python-telegram-bot version: {telegram.__version__}")

# تنظیمات اولیه
TOKEN = '7682323067:AAFcmkRvUZBQZJVQgCKgPqkaQb0TE2TPBPo'
BOT_USERNAME = '@XSecrtbot'
SPONSOR_CHANNEL = '@XSecrtyou'

# تنظیم Application
application = ApplicationBuilder().token(TOKEN).build()

# تنظیم پایگاه داده SQLite (استفاده از مسیر موقت)
DB_PATH = '/tmp/whisper_bot.db'

def init_db():
    try:
        conn = sqlite3.connect(DB_PATH)
        print("Database connected successfully")
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS users (
                     user_id INTEGER PRIMARY KEY, 
                     username TEXT, 
                     last_name TEXT,
                     started INTEGER DEFAULT 0)''')  # ستون جدید started
        c.execute('''CREATE TABLE IF NOT EXISTS whispers (
                     id INTEGER PRIMARY KEY AUTOINCREMENT,
                     sender_id INTEGER,
                     receiver_id INTEGER,
                     receiver_username TEXT,
                     receiver_last_name TEXT,
                     text TEXT,
                     view_count INTEGER DEFAULT 0,
                     view_time TEXT,
                     snoop_count INTEGER DEFAULT 0,
                     deleted INTEGER DEFAULT 0)''')
        c.execute('''CREATE TABLE IF NOT EXISTS past_receivers (
                     sender_id INTEGER,
                     receiver_id INTEGER,
                     receiver_username TEXT,
                     receiver_last_name TEXT)''')
        conn.commit()
    except Exception as e:
        print(f"Database init error: {e}")
    finally:
        conn.close()

init_db()

# بررسی عضویت در کانال اسپانسر
async def check_membership(update: telegram.Update, context: ContextTypes.DEFAULT_TYPE, user_id):
    try:
        member = await context.bot.get_chat_member(chat_id=SPONSOR_CHANNEL, user_id=user_id)
        return member.status in ['member', 'administrator', 'creator']
    except Exception as e:
        print(f"Membership check error: {e}")
        return False

# بررسی وضعیت کاربر (استارت کرده یا نه)
def check_user_started(user_id):
    conn = None
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('SELECT started FROM users WHERE user_id = ?', (user_id,))
        result = c.fetchone()
        return result and result[0] == 1
    except Exception as e:
        print(f"Check user started error: {e}")
        return False
    finally:
        if conn:
            conn.close()

# پیام خوشآمدگویی
async def start(update: telegram.Update, context: ContextTypes.DEFAULT_TYPE):
    print("Start command received")
    try:
        user = update.effective_user
        user_id = user.id
        last_name = user.last_name or user.first_name
        username = user.username

        # ذخیره یا به‌روزرسانی کاربر در پایگاه داده
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('INSERT OR REPLACE INTO users (user_id, username, last_name, started) VALUES (?, ?, ?, ?)', 
                  (user_id, username, last_name, 1))  # تنظیم started به 1
        conn.commit()
        conn.close()

        # بررسی عضویت
        is_member = await check_membership(update, context, user_id)
        welcome_text = f"سلام {last_name} خوش آمدی 💭\n\nبا من میتونی پیام هاتو توی گروه، بصورت مخفیانه بفرستی برای گیرنده مدنظرت تا فقط تو و اون بتونید پیام رو بخونید!\n\nدر چهار حالت میتونی از من استفاده کنی:\n\nحالت اول، من رو تایپ کن، یوزرنیم گیرنده رو تایپ کن، متن نجوات رو بنویس.\nمثال:\n{BOT_USERNAME} @username سلام چطوری؟ 😈\n\nحالت دوم، من رو تایپ کن، آیدی عددی گیرنده رو تایپ کن، متن نجوات رو بنویس.\nمثال:\n{BOT_USERNAME} 1234567890 سلام چطوری؟ 😈\n\nحالت سوم، من رو تایپ کن، روی یکی از پیام های گیرنده ریپلای کن، متن نجوات رو بنویس.\nمثال:\n{BOT_USERNAME} سلام چطوری؟ 😈\n\nحالت چهارم، اگر قبلا از طریق من به گیرنده مدنظرت نجوا دادی، وقتی من رو تایپ کنی، گزینه ارسال نجوا به اون کاربر بالای صفحه کیبوردت نشون داده میشه، درنتیجه بعد از تایپ یوزرنیم من، فقط کافیه متن نجوات رو بنویسی.\n\nضمنا یادت نره، در هر چهار حالت، بعد از اتمام تایپ متن نجوات، باید روی گزینه ارسال نجوا، کلیک کنی تا نجوات ساخته و ارسال بشه.\n\nلطفا توی کانال اسپانسر هم عضو شو 💜"

        keyboard = [[InlineKeyboardButton("XSecrtyou", url=f"https://t.me/{SPONSOR_CHANNEL[1:]}")]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(welcome_text, reply_markup=reply_markup)

        if is_member:
            await context.bot.send_message(chat_id=user_id, text="عضویتت هم تایید شد. ✅")
    except Exception as e:
        print(f"Start handler error: {e}")
        traceback.print_exc()

# پردازش Inline Query
async def inlinequery(update: telegram.Update, context: ContextTypes.DEFAULT_TYPE):
    print("Inline query received:", update.inline_query.query)
    try:
        query = update.inline_query.query.strip()
        user_id = update.inline_query.from_user.id
        last_name = update.inline_query.from_user.last_name or update.inline_query.from_user.first_name

        # بررسی عضویت و وضعیت استارت
        is_member = await check_membership(update, context, user_id)
        has_started = check_user_started(user_id)

        if not has_started or not is_member:
            results = [InlineQueryResultArticle(
                id='1',
                title="لطفا قبل از شروع، روی این پیام کلیک کن 🤌🏼",
                input_message_content=InputTextMessageContent(""),  # بدون پیام در گروه
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("شروع ربات", url="https://t.me/XSecrtbot?start=start")
                ]])
            )]
            await update.inline_query.answer(results)
            return

        # اگر چیزی تایپ نشده یا فقط یوزرنیم ربات تایپ شده
        if not query or query == "":
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute('SELECT DISTINCT receiver_id, receiver_username, receiver_last_name FROM past_receivers WHERE sender_id = ?', (user_id,))
            past_receivers = c.fetchall()
            conn.close()

            results = [
                InlineQueryResultArticle(id='1', title='یوزرنیم یا آیدی عددی رو وارد کن 💡', input_message_content=InputTextMessageContent('')),
                InlineQueryResultArticle(id='2', title='روی پیام کاربر ریپلای کن💡', input_message_content=InputTextMessageContent(''))
            ]
            for i, (rec_id, rec_username, rec_last_name) in enumerate(past_receivers[:8], 3):
                rec_display = rec_username if rec_username else str(rec_id)
                results.append(InlineQueryResultArticle(
                    id=str(i),
                    title=f"{rec_last_name} {rec_display}",
                    input_message_content=InputTextMessageContent(f"{rec_display} ")
                ))
            await update.inline_query.answer(results)
            return

        # پردازش فرمت‌ها
        parts = query.split(' ', 1)
        receiver = parts[0] if len(parts) > 1 else None
        text = parts[1] if len(parts) > 1 else parts[0]

        # فرمت سوم (ریپلای)
        if update.inline_query.message and update.inline_query.message.reply_to_message:
            receiver_id = update.inline_query.message.reply_to_message.from_user.id
            receiver_last_name = update.inline_query.message.reply_to_message.from_user.last_name or update.inline_query.message.reply_to_message.from_user.first_name
            receiver_username = update.inline_query.message.reply_to_message.from_user.username
            receiver_display = receiver_username if receiver_username else str(receiver_id)
            results = [InlineQueryResultArticle(
                id='1',
                title=f"{receiver_last_name} {receiver_display}",
                input_message_content=InputTextMessageContent(f"{receiver_display} {text}", parse_mode='Markdown'),
                reply_markup=build_keyboard(user_id, receiver_id, text, receiver_last_name, receiver_username)
            )]
            await update.inline_query.answer(results)
            return

        # اگر فقط گیرنده تایپ شده
        if receiver and not text:
            results = [InlineQueryResultArticle(id='1', title='حالا متن نجوا رو بنویس 💡', input_message_content=InputTextMessageContent(f"{receiver} "))]
            await update.inline_query.answer(results)
            return

        # پردازش گیرنده
        receiver_id = None
        receiver_username = None
        receiver_last_name = None
        if receiver.startswith('@'):
            receiver_username = receiver[1:]
            try:
                chat = await context.bot.get_chat(receiver_username)
                receiver_id = chat.id
                receiver_last_name = chat.last_name or chat.first_name
            except Exception as e:
                print(f"Error getting chat by username: {e}")
                receiver_last_name = "کاربر ناشناس"
        elif receiver.isdigit():
            receiver_id = int(receiver)
            try:
                chat = await context.bot.get_chat(receiver_id)
                receiver_last_name = chat.last_name or chat.first_name
                receiver_username = chat.username
            except Exception as e:
                print(f"Error getting chat by ID: {e}")
                receiver_last_name = "کاربر ناشناس"
        else:
            results = [InlineQueryResultArticle(id='1', title='یوزرنیم یا آیدی عددی رو وارد کن 💡', input_message_content=InputTextMessageContent(''))]
            await update.inline_query.answer(results)
            return

        # ذخیره گیرنده در تاریخچه
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('INSERT OR REPLACE INTO past_receivers (sender_id, receiver_id, receiver_username, receiver_last_name) VALUES (?, ?, ?, ?)',
                  (user_id, receiver_id, receiver_username, receiver_last_name))
        conn.commit()
        conn.close()

        receiver_display = receiver_username if receiver_username else str(receiver_id)
        results = [InlineQueryResultArticle(
            id='1',
            title=f"{receiver_last_name} {receiver_display}",
            input_message_content=InputTextMessageContent(f"{receiver_display} {text}", parse_mode='Markdown'),
            reply_markup=build_keyboard(user_id, receiver_id, text, receiver_last_name, receiver_username)
        )]
        await update.inline_query.answer(results)
    except Exception as e:
        print(f"Inline query error: {e}")
        traceback.print_exc()

# ساخت دکمه‌های Inline Keyboard
def build_keyboard(sender_id, receiver_id, text, receiver_last_name, receiver_username):
    conn = None
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('INSERT INTO whispers (sender_id, receiver_id, receiver_username, receiver_last_name, text) VALUES (?, ?, ?, ?, ?)',
                  (sender_id, receiver_id, receiver_username, receiver_last_name, text))
        whisper_id = c.lastrowid
        conn.commit()

        keyboard = [
            [InlineKeyboardButton("ببینم 🤔", callback_data=f"view_{whisper_id}"),
             InlineKeyboardButton("پاسخ 💭", callback_data=f"reply_{whisper_id}")],
            [InlineKeyboardButton("حذف 🤌🏼", callback_data=f"delete_{whisper_id}")]
        ]
        return InlineKeyboardMarkup(keyboard)
    except Exception as e:
        print(f"Build keyboard error: {e}")
        traceback.print_exc()
        return None
    finally:
        if conn:
            conn.close()

# پردازش Callback Query
async def button(update: telegram.Update, context: ContextTypes.DEFAULT_TYPE):
    print("Button callback received:", update.callback_query.data)
    conn = None
    try:
        query = update.callback_query
        user_id = query.from_user.id
        data = query.data

        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        whisper_id = int(data.split('_')[1])
        c.execute('SELECT id, sender_id, receiver_id, receiver_username, receiver_last_name, text, view_count, view_time, snoop_count, deleted FROM whispers WHERE id = ?', (whisper_id,))
        whisper = c.fetchone()
        if not whisper:
            await query.answer("این نجوا دیگر وجود ندارد!", show_alert=True)
            return

        id, sender_id, receiver_id, receiver_username, receiver_last_name, text, view_count, view_time, snoop_count, deleted = whisper

        if data.startswith('view_'):
            if user_id == receiver_id or user_id == sender_id:
                tehran_tz = pytz.timezone('Asia/Tehran')
                view_time = datetime.now(tehran_tz).strftime('%H:%M')
                c.execute('UPDATE whispers SET view_count = view_count + 1, view_time = ? WHERE id = ? AND receiver_id = ?', (view_time, whisper_id, receiver_id))
                conn.commit()
                await query.answer(text=f"{BOT_USERNAME}\n\nمتن نجوا:\n{text}", show_alert=True)
            else:
                c.execute('UPDATE whispers SET snoop_count = snoop_count + 1 WHERE id = ?', (whisper_id,))
                conn.commit()
                await query.answer(text="تو گیرنده این نجوا نیستی! 😛", show_alert=True)
            await update_inline_message(update, whisper_id)

        elif data.startswith('reply_'):
            receiver_display = receiver_username if receiver_username else str(receiver_id)
            await context.bot.send_message(chat_id=user_id, text=f"{receiver_display} ")
            await query.answer()

        elif data.startswith('delete_') and user_id == sender_id:
            c.execute('UPDATE whispers SET deleted = 1 WHERE id = ?', (whisper_id,))
            conn.commit()
            await update_inline_message(query, whisper_id)
            await query.answer()

    except Exception as e:
        print(f"Button handler error: {e}")
        traceback.print_exc()
    finally:
        if conn:
            conn.close()

# به‌روزرسانی Inline Message
async def update_inline_message(query, whisper_id):
    conn = None
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()

        # گرفتن اطلاعات نجوا
        c.execute('SELECT receiver_username, receiver_last_name, view_count, view_time, snoop_count, deleted FROM whispers WHERE id = ?', (whisper_id,))
        whisper = c.fetchone()
        if not whisper:
            return

        receiver_username, receiver_last_name, view_count, view_time, snoop_count, deleted = whisper

        # گرفتن اطلاعات کاربر فعلی
        current_user_id = query.from_user.id

        # بررسی اینکه این کاربر، دریافت‌کننده است
        c.execute('SELECT receiver_id FROM whispers WHERE id = ?', (whisper_id,))
        result = c.fetchone()
        if not result:
            return
        receiver_id = result[0]

        if current_user_id == receiver_id:
            # به‌روزرسانی view_count و view_time فقط اگر خود مخاطب بود
            new_view_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            c.execute('UPDATE whispers SET view_count = view_count + 1, view_time = ? WHERE id = ? AND receiver_id = ?', (new_view_time, whisper_id, receiver_id))
            conn.commit()

        if deleted:
            text = f"{receiver_last_name}\n\nاین نجوی توسط فرستنده پاک شده 💤"
            keyboard = [[InlineKeyboardButton("پاسخ 💫", callback_data=f"reply_{whisper_id}")]]
        else:
            if view_count == 0:
                text = f"{receiver_last_name}\n\nهنوز ندیده 😐\nتعداد فضولا: {snoop_count} نفر"
                keyboard = [
                    [InlineKeyboardButton("ببینم 🤔", callback_data=f"view_{whisper_id}"),
                     InlineKeyboardButton("پاسخ 💫", callback_data=f"reply_{whisper_id}")],
                    [InlineKeyboardButton("حذف 🤖", callback_data=f"delete_{whisper_id}")]
                ]
            else:
                snoop_text = f"تعداد فضولا: {snoop_count} نفر" if snoop_count > 0 else "تعداد فضولا"
                text = f"{receiver_last_name}\n\nنجوا رو {view_count} بار دیده 😈 {view_time}\n{snoop_text}"
                keyboard = [
                    [InlineKeyboardButton("ببینم 🤔", callback_data=f"view_{whisper_id}"),
                     InlineKeyboardButton("پاسخ 💫", callback_data=f"reply_{whisper_id}")],
                    [InlineKeyboardButton("حذف 🤖", callback_data=f"delete_{whisper_id}")]
                ]

        await query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup(keyboard))
    except Exception as e:
        print(f"Update inline message error: {e}")
        traceback.print_exc()
    finally:
        if conn:
            conn.close()

# تنظیم Handlerها
application.add_handler(CommandHandler("start", start))
application.add_handler(InlineQueryHandler(inlinequery))
application.add_handler(CallbackQueryHandler(button))

# اجرای ربات
if __name__ == "__main__":
    print("Starting bot...")
    application.run_polling()