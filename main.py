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
from urllib.parse import quote

# تنظیمات اولیه
TOKEN = "7682323067:AAFcmkRvUZBQZJVQgCKgPqkaQb0TE2TPBPo"
BOT_USERNAME = "@XSecrtbot"
SPONSOR_CHANNEL = "@XSecrtyou"
ADMIN_ID = 0  # آیدی عددی ادمین برای دریافت گزارشات

# تنظیمات پایگاه داده
DB_NAME = "whisper_bot.db"

# تنظیم منطقه زمانی تهران
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
    
    # جدول کاربران
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        username TEXT,
        first_name TEXT,
        last_name TEXT,
        deep_link_used BOOLEAN DEFAULT 0,
        joined_date DATETIME
    )
    ''')
    
    # جدول نجواها
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
    
    # جدول تاریخچه گیرندگان
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
    now = datetime.datetime.now(tehran_tz)
    cursor.execute('''
    INSERT OR REPLACE INTO users (user_id, username, first_name, last_name, joined_date)
    VALUES (?, ?, ?, ?, ?)
    ''', (user_id, username, first_name, last_name, now))
    conn.commit()
    conn.close()

def update_user_deep_link(user_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET deep_link_used = 1 WHERE user_id = ?", (user_id,))
    conn.commit()
    conn.close()

# --- توابع کمکی ---
async def check_channel_membership(bot, user_id):
    try:
        member = await bot.get_chat_member(SPONSOR_CHANNEL, user_id)
        return member.status in ["member", "administrator", "creator"]
    except:
        return False

def create_deep_link(bot_username, payload):
    return f"https://t.me/{bot_username}?start={quote(payload)}"

# --- هندلرهای اصلی ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    deep_link = context.args[0] if context.args else None
    
    # ذخیره اطلاعات کاربر
    add_user(user.id, user.username, user.first_name, user.last_name)
    if deep_link:
        update_user_deep_link(user.id)
    
    # بررسی عضویت در کانال
    is_member = await check_channel_membership(context.bot, user.id)
    
    # ساخت دکمه‌ها
    keyboard = []
    if not is_member:
        keyboard.append([
            InlineKeyboardButton(
                "عضویت در کانال اسپانسر 💜",
                url=f"https://t.me/{SPONSOR_CHANNEL[1:]}"
            )
        ])
    keyboard.append([InlineKeyboardButton("راهنما 💡", callback_data="help_main")])
    
    # پیام خوش‌آمد
    welcome_text = (
        f"سلام {user.last_name or user.first_name} خوش آمدی 💭\n\n"
        "با من میتونی پیام هاتو توی گروه، بصورت مخفیانه بفرستی برای گیرنده مدنظرت "
        "تا فقط تو و اون بتونید پیام رو بخونید!\n\n"
    )
    
    if not is_member:
        welcome_text += "لطفا اول در کانال اسپانسر عضو شو 💜"
    else:
        welcome_text += "برای شروع از راهنما استفاده کن 👇"
    
    await update.message.reply_text(
        welcome_text,
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
    section = query.data
    
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
    else:  # help_history
        text = (
            "🕒 نجوا تاریخچه:\n"
            "1. در گروه یا چت، فقط @XSecrtbot رو تایپ کن\n"
            "2. لیست گیرنده‌های قبلی نمایش داده میشه\n"
            "3. گیرنده مورد نظرت رو انتخاب کن\n"
            "4. متن پیام نجوا رو بنویس\n"
            "5. از لیست نتایج، گزینه ارسال رو انتخاب کن"
        )
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("بازگشت", callback_data="help_main")
        ]])
    )

async def handle_inline_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.inline_query.query.strip()
    user = update.inline_query.from_user
    
    # بررسی عضویت در کانال
    if not await check_channel_membership(context.bot, user.id):
        deep_link = create_deep_link(BOT_USERNAME[1:], f"start_user_{user.id}")
        return await update.inline_query.answer([
            InlineQueryResultArticle(
                id="join_channel",
                title="لطفا قبل از شروع روی این پیام کلیک کن🤌🏼",
                input_message_content=InputTextMessageContent(
                    "برای استفاده از ربات باید در کانال اسپانسر عضو باشید.\n"
                    f"لطفا در کانال {SPONSOR_CHANNEL} عضو شوید."
                ),
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton(
                        "عضویت در کانال 💜",
                        url=f"https://t.me/{SPONSOR_CHANNEL[1:]}"
                    )
                ]])
            )
        ])
    
    results = []
    
    # حالت خالی - نمایش گزینه‌های اصلی
    if not query:
        results.extend([
            InlineQueryResultArticle(
                id="input_guide",
                title="یوزرنیم یا آیدی عددی رو وارد کن 💡",
                input_message_content=InputTextMessageContent(
                    f"{BOT_USERNAME} [یوزرنیم یا آیدی] [متن پیام]"
                ),
                description="ارسال نجوا با یوزرنیم یا آیدی عددی"
            ),
            InlineQueryResultArticle(
                id="reply_guide",
                title="روی پیام کاربر ریپلای کن💡",
                input_message_content=InputTextMessageContent(
                    f"{BOT_USERNAME} [متن پیام] (با ریپلای روی پیام کاربر)"
                ),
                description="ارسال نجوا با ریپلای"
            )
        ])
        
        # افزودن گزینه‌های تاریخچه
        history = get_recipient_history(user.id)
        for idx, recipient in enumerate(history[:8]):
            rec_id, rec_username, rec_first, rec_last = recipient
            display_name = rec_last or rec_first or rec_username or rec_id
            results.append(InlineQueryResultArticle(
                id=f"history_{idx}",
                title=f"ارسال به {display_name}",
                description=f"{rec_username or rec_id}",
                input_message_content=InputTextMessageContent(
                    f"{BOT_USERNAME} {rec_username or rec_id} "
                )
            ))
    
    # حالت ورود متن
    else:
        parts = query.split(maxsplit=1)
        
        # فقط گیرنده وارد شده
        if len(parts) == 1:
            target = parts[0]
            if target.startswith('@') or target.isdigit():
                results.append(InlineQueryResultArticle(
                    id="write_message",
                    title="حالا متن نجوا رو بنویس 💡",
                    input_message_content=InputTextMessageContent(
                        f"{BOT_USERNAME} {target} "
                    ),
                    description="متن پیام خود را وارد کنید"
                ))
        
        # گیرنده و متن وارد شده
        else:
            target, message = parts
            if target.startswith('@') or target.isdigit():
                whisper_id = f"w_{user.id}_{int(datetime.datetime.now().timestamp())}"
                
                results.append(InlineQueryResultArticle(
                    id=whisper_id,
                    title=f"ارسال نجوا به {target}",
                    input_message_content=InputTextMessageContent(
                        f"{target}\n\nهنوز ندیده 😐\n"
                        f"تعداد فضول ها 0 نفر"
                    ),
                    description=message[:30] + ("..." if len(message) > 30 else ""),
                    reply_markup=InlineKeyboardMarkup([
                        [
                            InlineKeyboardButton("ببینم 🤔", callback_data=f"view_{whisper_id}"),
                            InlineKeyboardButton("پاسخ 💭", callback_data=f"reply_{whisper_id}")
                        ],
                        [InlineKeyboardButton("حذف 🤌🏼", callback_data=f"delete_{whisper_id}")]
                    ])
                ))
                
                # ذخیره نجوا
                recipient_id = target[1:] if target.startswith('@') else target
                add_whisper(whisper_id, user.id, recipient_id, message)
    
    await update.inline_query.answer(results)

async def handle_chosen_inline_result(update: Update, context: ContextTypes.DEFAULT_TYPE):
    result = update.chosen_inline_result
    whisper_id = result.result_id
    
    if whisper_id.startswith("w_"):
        # به‌روزرسانی اطلاعات نجوا در صورت نیاز
        pass

async def handle_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    
    if data.startswith("view_"):
        whisper_id = data.split("_", 1)[1]
        whisper = get_whisper(whisper_id)
        
        if not whisper or whisper[8]:  # deleted
            await query.answer("این نجوا وجود ندارد یا حذف شده است", show_alert=True)
            return
        
        if str(query.from_user.id) == str(whisper[2]):  # recipient
            # نمایش متن نجوا
            await query.answer(f"XSecret 💭\n\n{whisper[3]}", show_alert=True)
            
            # به‌روزرسانی وضعیت مشاهده
            update_whisper_view(whisper_id)
            view_time = datetime.datetime.now(tehran_tz).strftime("%H:%M")
            
            # به‌روزرسانی پیام
            new_text = (
                f"{query.from_user.last_name or query.from_user.first_name}\n\n"
                f"نجوا رو {whisper[5]} بار دیده 😈 {view_time}\n"
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
            await query.answer(
                "فقط گیرنده می‌تواند این نجوا را مشاهده کند",
                show_alert=True
            )
    
    elif data.startswith("reply_"):
        whisper_id = data.split("_", 1)[1]
        whisper = get_whisper(whisper_id)
        
        if whisper:
            sender_id = whisper[1]
            await query.answer()
            await context.bot.send_message(
                chat_id=query.from_user.id,
                text=(
                    "برای پاسخ به این نجوا، پیام خود را به این شکل ارسال کنید:\n"
                    f"{BOT_USERNAME} {sender_id} [متن پیام]"
                )
            )
    
    elif data.startswith("delete_"):
        whisper_id = data.split("_", 1)[1]
        whisper = get_whisper(whisper_id)
        
        if whisper and str(query.from_user.id) == str(whisper[1]):  # sender
            delete_whisper(whisper_id)
            await query.answer("نجوا با موفقیت حذف شد", show_alert=True)
            
            await query.edit_message_text(
                "این نجوا توسط فرستنده پاک شده 💤",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("پاسخ 💭", callback_data=f"reply_{whisper_id}")
                ]])
            )
        else:
            await query.answer("شما مجوز حذف این نجوا را ندارید", show_alert=True)

def main():
    # راه‌اندازی پایگاه داده
    init_db()
    
    # ایجاد اپلیکیشن
    application = Application.builder().token(TOKEN).build()
    
    # تنظیم هندلرها
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(help_main, pattern="^help_main$"))
    application.add_handler(CallbackQueryHandler(help_section, pattern="^help_"))
    application.add_handler(InlineQueryHandler(handle_inline_query))
    application.add_handler(ChosenInlineResultHandler(handle_chosen_inline_result))
    application.add_handler(CallbackQueryHandler(handle_callback_query))
    
    # اجرای ربات
    application.run_polling()

if __name__ == "__main__":
    main()