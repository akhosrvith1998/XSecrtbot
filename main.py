import logging
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InlineQueryResultArticle,
    InputTextMessageContent,
    BotCommand
)
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    InlineQueryHandler,
    CallbackQueryHandler,
    ChosenInlineResultHandler,
    MessageHandler,
    filters
)
from telegram.constants import ParseMode
import sqlite3
import datetime
import pytz

# تنظیمات اولیه
TOKEN = "7682323067:AAFcmkRvUZBQZJVQgCKgPqkaQb0TE2TPBPo"
BOT_USERNAME = "@XSecrtbot"
SPONSOR_CHANNEL = "@XSecrtyou"
ADMIN_ID = 0  # آیدی عددی ادمین برای دریافت گزارشات

# تنظیمات پایگاه داده
DB_NAME = "whisper_bot.db"

# تنظیم منطقه زمانی
tehran_tz = pytz.timezone("Asia/Tehran")

# راه‌اندازی لاگر
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- توابع پایگاه داده ---
def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # ایجاد جدول کاربران (بدون فیلد joined_sponsor)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        first_name TEXT,
        last_name TEXT,
        deep_link_used BOOLEAN DEFAULT 0
    )
    ''')
    
    # ایجاد جدول نجواها
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS whispers (
        whisper_id TEXT PRIMARY KEY,
        sender_id INTEGER,
        recipient_id INTEGER,
        message TEXT,
        sent_time DATETIME,
        view_count INTEGER DEFAULT 0,
        view_time DATETIME,
        unauthorized_views INTEGER DEFAULT 0,
        deleted BOOLEAN DEFAULT 0
    )
    ''')
    
    # ایجاد جدول تاریخچه گیرندگان
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS recipient_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sender_id INTEGER,
        recipient_id INTEGER,
        last_used DATETIME
    )
    ''')
    
    conn.commit()
    conn.close()

def get_user(user_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    user = cursor.fetchone()
    conn.close()
    return user

def add_user(user_id, username, first_name, last_name):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
    INSERT OR IGNORE INTO users (user_id, username, first_name, last_name)
    VALUES (?, ?, ?, ?)
    ''', (user_id, username, first_name, last_name))
    conn.commit()
    conn.close()

def update_user_deep_link(user_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET deep_link_used = 1 WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()

def add_whisper(whisper_id, sender_id, recipient_id, message):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    sent_time = datetime.datetime.now(tehran_tz)
    cursor.execute('''
    INSERT INTO whispers (whisper_id, sender_id, recipient_id, message, sent_time)
    VALUES (?, ?, ?, ?, ?)
    ''', (whisper_id, sender_id, recipient_id, message, sent_time))
    conn.commit()
    conn.close()

def get_whisper(whisper_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM whispers WHERE whisper_id = ?", (whisper_id,))
    whisper = cursor.fetchone()
    conn.close()
    return whisper

def update_whisper_view(whisper_id, unauthorized=False):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    view_time = datetime.datetime.now(tehran_tz)
    
    if unauthorized:
        cursor.execute('''
        UPDATE whispers 
        SET unauthorized_views = unauthorized_views + 1 
        WHERE whisper_id = ?
        ''', (whisper_id,))
    else:
        cursor.execute('''
        UPDATE whispers 
        SET view_count = view_count + 1, 
            view_time = ? 
        WHERE whisper_id = ? AND view_count = 0
        ''', (view_time, whisper_id))
    
    conn.commit()
    conn.close()

def delete_whisper(whisper_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("UPDATE whispers SET deleted = 1 WHERE whisper_id = ?", (whisper_id,))
    conn.commit()
    conn.close()

def add_recipient_history(sender_id, recipient_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    last_used = datetime.datetime.now(tehran_tz)
    
    # بررسی وجود رکورد
    cursor.execute('''
    SELECT id FROM recipient_history 
    WHERE sender_id = ? AND recipient_id = ?
    ''', (sender_id, recipient_id))
    exists = cursor.fetchone()
    
    if exists:
        cursor.execute('''
        UPDATE recipient_history 
        SET last_used = ? 
        WHERE id = ?
        ''', (last_used, exists[0]))
    else:
        cursor.execute('''
        INSERT INTO recipient_history (sender_id, recipient_id, last_used)
        VALUES (?, ?, ?)
        ''', (sender_id, recipient_id, last_used))
    
    conn.commit()
    conn.close()

def get_recipient_history(sender_id, limit=8):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
    SELECT u.user_id, u.username, u.first_name, u.last_name 
    FROM recipient_history rh
    JOIN users u ON rh.recipient_id = u.user_id
    WHERE rh.sender_id = ?
    ORDER BY rh.last_used DESC
    LIMIT ?
    ''', (sender_id, limit))
    history = cursor.fetchall()
    conn.close()
    return history

# --- توابع اصلی ربات ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    add_user(user.id, user.username, user.first_name, user.last_name)
    update_user_deep_link(user.id)
    
    # ایجاد دکمه‌ها
    keyboard = [
        [InlineKeyboardButton("راهنما💡", callback_data="help_main")],
        [InlineKeyboardButton("عضویت در کانال اسپانسر", url=f"https://t.me/{SPONSOR_CHANNEL[1:]}")]
    ]
    
    # ارسال پیام خوش‌آمد
    welcome_message = (
        f"سلام {user.last_name or user.first_name} خوش آمدی 💭\n\n"
        "با من میتونی پیام هاتو توی گروه، بصورت مخفیانه بفرستی برای گیرنده مدنظرت تا فقط تو و اون بتونید پیام رو بخونید!\n\n"
        "برای شروع راهنما رو مطالعه کن 👇"
    )
    
    await update.message.reply_text(
        welcome_message,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def help_main(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    help_buttons = [
        [
            InlineKeyboardButton("نجوا یوزرنیم", callback_data="help_username"),
            InlineKeyboardButton("نجوا عددی", callback_data="help_numeric")
        ],
        [
            InlineKeyboardButton("نجوا ریپلای", callback_data="help_reply"),
            InlineKeyboardButton("نجوا تاریخچه", callback_data="help_history")
        ]
    ]
    
    help_text = (
        "📚 راهنمای استفاده از ربات:\n\n"
        "1. نجوا یوزرنیم: من رو تایپ کن، یوزرنیم گیرنده رو تایپ کن، متن نجوات رو بنویس\n"
        "مثال: @XSecrtbot @username سلام چطوری؟ 😈\n\n"
        "2. نجوا عددی: من رو تایپ کن، آیدی عددی گیرنده رو تایپ کن، متن نجوات رو بنویس\n"
        "مثال: @XSecrtbot 1234567890 سلام چطوری؟ 😈\n\n"
        "3. نجوا ریپلای: من رو تایپ کن، روی یکی از پیام های گیرنده ریپلای کن، متن نجوات رو بنویس\n"
        "مثال: @XSecrtbot سلام چطوری؟ 😈\n\n"
        "4. نجوا تاریخچه: اگر قبلا به کاربری نجوا فرستادی، با تایپ من در گروه، گزینه ارسال مجدد به اون کاربر نمایش داده میشه\n\n"
        "⚠️ توجه: در هر چهار حالت، بعد از اتمام تایپ متن نجوا، باید روی گزینه ارسال نجوا کلیک کنی."
    )
    
    await query.edit_message_text(
        help_text,
        reply_markup=InlineKeyboardMarkup(help_buttons)
    )

async def help_section(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    section = query.data
    text = ""
    
    if section == "help_username":
        text = (
            "📝 نجوا یوزرنیم:\n"
            "1. در گروه یا چت، @XSecrtbot رو تایپ کن\n"
            "2. بعد از یوزرنیم ربات، یوزرنیم گیرنده رو با @ وارد کن\n"
            "3. متن پیام نجوا رو بنویس\n"
            "4. از لیست نتایج، گزینه ارسال رو انتخاب کن\n\n"
            "مثال:\n"
            "@XSecrtbot @username سلام چطوری؟ 😈"
        )
    elif section == "help_numeric":
        text = (
            "🔢 نجوا عددی:\n"
            "1. در گروه یا چت، @XSecrtbot رو تایپ کن\n"
            "2. بعد از یوزرنیم ربات، آیدی عددی گیرنده رو وارد کن\n"
            "3. متن پیام نجوا رو بنویس\n"
            "4. از لیست نتایج، گزینه ارسال رو انتخاب کن\n\n"
            "مثال:\n"
            "@XSecrtbot 1234567890 سلام چطوری؟ 😈"
        )
    elif section == "help_reply":
        text = (
            "↩️ نجوا ریپلای:\n"
            "1. در گروه، روی پیام کاربر مورد نظر ریپلای کن\n"
            "2. @XSecrtbot رو تایپ کن\n"
            "3. متن پیام نجوا رو بنویس\n"
            "4. از لیست نتایج، گزینه ارسال رو انتخاب کن\n\n"
            "مثال:\n"
            "@XSecrtbot سلام چطوری؟ 😈"
        )
    elif section == "help_history":
        text = (
            "🕒 نجوا تاریخچه:\n"
            "1. در گروه یا چت، فقط @XSecrtbot رو تایپ کن\n"
            "2. لیست گیرنده‌های قبلی نمایش داده میشه\n"
            "3. گیرنده مورد نظرت رو انتخاب کن\n"
            "4. متن پیام نجوا رو بنویس\n"
            "5. از لیست نتایج، گزینه ارسال رو انتخاب کن\n\n"
            "⚠️ توجه: این قابلیت برای کاربرانی که قبلا بهشون نجوا فرستادی فعال میشه"
        )
    
    back_button = [[InlineKeyboardButton("بازگشت", callback_data="help_main")]]
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(back_button)
    )

async def handle_inline_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.inline_query.query.strip()
    user = update.inline_query.from_user
    
    # بررسی عضویت در کانال در لحظه
    try:
        member = await context.bot.get_chat_member(SPONSOR_CHANNEL, user.id)
        if member.status not in ["member", "administrator", "creator"]:
            results = [InlineQueryResultArticle(
                id="join_sponsor",
                title="لطفا قبل از شروع روی این پیام کلیک کن🤌🏼",
                input_message_content=InputTextMessageContent(
                    "برای استفاده از ربات باید در کانال اسپانسر عضو باشید.\n"
                    f"لطفا در کانال @{SPONSOR_CHANNEL[1:]} عضو شوید و سپس دوباره تلاش کنید."
                ),
                description="عضویت در کانال اجباری است"
            )]
            await update.inline_query.answer(results)
            return
    except Exception as e:
        logger.error(f"Channel check error: {e}")
        results = [InlineQueryResultArticle(
            id="error",
            title="خطا در بررسی عضویت",
            input_message_content=InputTextMessageContent(
                "خطا در بررسی عضویت شما در کانال. لطفا بعدا تلاش کنید."
            )
        )]
        await update.inline_query.answer(results)
        return
    
    # حالت‌های مختلف کوئری
    parts = query.split()
    results = []
    
    # حالت خالی: نمایش تاریخچه و گزینه‌های پایه
    if not query:
        # گزینه اول: وارد کردن یوزرنیم/آیدی
        results.append(InlineQueryResultArticle(
            id="input_user",
            title="یوزرنیم یا آیدی عددی رو وارد کن 💡",
            input_message_content=InputTextMessageContent(
                f"{BOT_USERNAME} [یوزرنیم یا آیدی] [متن پیام]"
            ),
            description="ارسال نجوا با یوزرنیم یا آیدی عددی"
        ))
        
        # گزینه دوم: ریپلای روی پیام
        results.append(InlineQueryResultArticle(
            id="reply_help",
            title="روی پیام کاربر ریپلای کن💡",
            input_message_content=InputTextMessageContent(
                f"{BOT_USERNAME} [متن پیام] (با ریپلای روی پیام کاربر)"
            ),
            description="ارسال نجوا با ریپلای"
        ))
        
        # گزینه‌های تاریخچه
        history = get_recipient_history(user.id)
        for idx, recipient in enumerate(history[:8]):
            rec_id, rec_username, rec_first, rec_last = recipient
            display_name = rec_last or rec_first or rec_username
            results.append(InlineQueryResultArticle(
                id=f"history_{idx}",
                title=f"{display_name} ({rec_username or rec_id})",
                input_message_content=InputTextMessageContent(
                    f"{BOT_USERNAME} {rec_username or rec_id} "
                ),
                description=f"ارسال مجدد به {display_name}"
            ))
        
        await update.inline_query.answer(results)
        return
    
    # حالت تشخیص گیرنده و متن
    if len(parts) > 1:
        # شناسایی گیرنده (یوزرنیم یا آیدی عددی)
        recipient_id = None
        recipient_username = None
        
        # بررسی یوزرنیم
        if parts[1].startswith('@'):
            recipient_username = parts[1][1:]
            recipient_text = parts[1]
        # بررسی آیدی عددی
        elif parts[1].isdigit():
            recipient_id = int(parts[1])
            recipient_text = parts[1]
        else:
            # حالت ریپلای
            message_text = " ".join(parts[1:])
            results.append(InlineQueryResultArticle(
                id="write_text",
                title="حالا متن نجوا رو بنویس 💡",
                input_message_content=InputTextMessageContent(
                    f"{BOT_USERNAME} {message_text}"
                ),
                description="متن پیام خود را وارد کنید"
            ))
            await update.inline_query.answer(results)
            return
        
        # ساخت گزینه ارسال
        message_text = " ".join(parts[2:]) if len(parts) > 2 else ""
        whisper_id = f"whisper_{recipient_id or recipient_username}_{datetime.datetime.now().timestamp()}"
        results.append(InlineQueryResultArticle(
            id=whisper_id,
            title=f"ارسال نجوا به {recipient_text}",
            input_message_content=InputTextMessageContent(
                f"✉️ یک نجوا برای شما ارسال شد!"
            ),
            description=f"متن: {message_text[:30] + '...' if len(message_text) > 30 else message_text}",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton(
                    "مشاهده نجوا",
                    callback_data=f"view_{whisper_id}"
                )
            ]])
        ))
        
        # ذخیره در دیتابیس
        if recipient_id or recipient_username:
            add_whisper(
                whisper_id=whisper_id,
                sender_id=user.id,
                recipient_id=recipient_id or recipient_username,
                message=message_text
            )
            add_recipient_history(user.id, recipient_id or recipient_username)
    
    await update.inline_query.answer(results)

async def handle_chosen_inline_result(update: Update, context: ContextTypes.DEFAULT_TYPE):
    result = update.chosen_inline_result
    whisper_id = result.result_id
    
    # اگر نجوا ذخیره شده بود، اطلاعات اضافه می‌شود
    if whisper_id.startswith("whisper_"):
        # استخراج اطلاعات از آیدی
        _, recipient, timestamp = whisper_id.split("_")
        # به‌روزرسانی اطلاعات نجوا
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("UPDATE whispers SET whisper_id = ? WHERE whisper_id = ?", (result.result_id, whisper_id))
        conn.commit()
        conn.close()

async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    
    if data.startswith("view_"):
        # استخراج شناسه نجوا
        whisper_id = data.split("_", 1)[1]
        whisper = get_whisper(whisper_id)
        
        if not whisper:
            await query.answer("این نجوا وجود ندارد یا حذف شده است", show_alert=True)
            return
        
        # بررسی مجاز بودن کاربر
        if query.from_user.id == whisper[2]:  # recipient_id
            update_whisper_view(whisper_id)
            await query.answer(whisper[4], show_alert=True)  # نمایش متن نجوا
            
            # به‌روزرسانی پیام
            view_time = datetime.datetime.now(tehran_tz).strftime("%H:%M")
            new_text = (
                f"{query.from_user.last_name or query.from_user.first_name}\n\n"
                f"نجوا رو 1 بار دیده 😈 {view_time}\n"
                f"تعداد فضول ها {whisper[7]} نفر"
            )
            
            keyboard = [
                [InlineKeyboardButton("پاسخ 💭", callback_data=f"reply_{whisper_id}")],
                [InlineKeyboardButton("حذف 🤌🏼", callback_data=f"delete_{whisper_id}")]
            ]
            
            await query.edit_message_text(
                new_text,
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        else:
            update_whisper_view(whisper_id, unauthorized=True)
            await query.answer("فقط گیرنده می‌تواند این نجوا را مشاهده کند", show_alert=True)
    
    elif data.startswith("reply_"):
        # آماده‌سازی پاسخ
        whisper_id = data.split("_", 1)[1]
        whisper = get_whisper(whisper_id)
        
        if whisper:
            sender_id = whisper[1]  # sender_id
            await query.answer()
            await context.bot.send_message(
                chat_id=query.from_user.id,
                text=f"برای پاسخ به این نجوا، پیام خود را در قالب زیر ارسال کنید:\n"
                     f"{BOT_USERNAME} {sender_id} [متن پیام]"
            )
    
    elif data.startswith("delete_"):
        whisper_id = data.split("_", 1)[1]
        whisper = get_whisper(whisper_id)
        
        if whisper and query.from_user.id == whisper[1]:  # sender_id
            delete_whisper(whisper_id)
            await query.answer("نجوا با موفقیت حذف شد", show_alert=True)
            # به‌روزرسانی پیام اینلاین
            await query.edit_message_text(
                "✅ این نجوا توسط فرستنده پاک شده است",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("پاسخ 💭", callback_data=f"reply_{whisper_id}")
                ]])
            )
        else:
            await query.answer("شما مجوز حذف این نجوا را ندارید", show_alert=True)
    
    await query.answer()

# --- تنظیمات و اجرای ربات ---
def main():
    # راه‌اندازی پایگاه داده
    init_db()
    
    # ایجاد اپلیکیشن
    application = Application.builder().token(TOKEN).build()
    
    # ثبت هندلرها
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(help_main, pattern="help_main"))
    application.add_handler(CallbackQueryHandler(help_section, pattern="help_"))
    application.add_handler(InlineQueryHandler(handle_inline_query))
    application.add_handler(ChosenInlineResultHandler(handle_chosen_inline_result))
    application.add_handler(CallbackQueryHandler(button_click))
    
    # اجرای ربات
    application.run_polling()

if __name__ == "__main__":
    main()