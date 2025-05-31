import logging
from telegram import (
    InlineKeyboardButton, InlineKeyboardMarkup, InlineQueryResultArticle,
    InputTextMessageContent, Update, InlineQueryResultCachedPhoto
)
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    InlineQueryHandler, ContextTypes, MessageHandler, filters
)
from datetime import datetime
import pytz
import asyncio

# تنظیمات اولیه
TOKEN = "7682323067:AAFcmkRvUZBQZJVQgCKgPqkaQb0TE2TPBPo"
BOT_USERNAME = "@XSecrtbot"
CHANNEL_ID = "@XSecrtyou"
ADMIN_ID = 1234567890  # جایگزین با ID ادمین
TIMEZONE = pytz.timezone("Asia/Tehran")

# پایگاه داده موقت (در حافظه)
user_data = {}  # {user_id: {history: [], ...}}
messages = {}  # {message_id: {sender: id, receiver: id, text: str, ...}}

# تنظیب لاگ‌گیری
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# توابع کمکی
def persian_time():
    return datetime.now(TIMEZONE).strftime("%H:%M")

def get_user_key(user):
    return f"{user.id}_{user.username or 'no_username'}"

async def check_membership(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id):
    try:
        member = await context.bot.get_chat_member(CHANNEL_ID, user_id)
        return member.status in ['member', 'administrator', 'creator']
    except Exception as e:
        logging.error(f"Error checking membership: {e}")
        return False

# دستور استارت
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat_id = update.effective_chat.id
    
    if not await check_membership(update, context, user.id):
        keyboard = [[
            InlineKeyboardButton("عضویت در کانال", url=f"https://t.me/{CHANNEL_ID[1:]}"),
        ]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            f"سلام {user.last_name or user.first_name}! لطفاً ابتدا در کانال ما عضو شوید:",
            reply_markup=reply_markup
        )
        return

    keyboard = [[
        InlineKeyboardButton("راهنما💡", callback_data="help"),
        InlineKeyboardButton("عضویت در کانال", url=f"https://t.me/{CHANNEL_ID[1:]}")
    ]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"سلام {user.last_name or user.first_name}! خوش آمدید 💭\n\n"
        "با من میتونی پیام هاتو توی گروه، بصورت مخفیانه بفرستی برای گیرنده مدنظرت...",
        reply_markup=reply_markup
    )

# منوی راهنما
async def help_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    help_text = (
        "در چهار حالت میتونی از من استفاده کنی:\n\n"
        "1️⃣ نجوا یوزرنیم:\n"
        "من رو تایپ کن، یوزرنیم گیرنده رو تایپ کن، متن نجوات رو بنویس.\n"
        "مثال: @XSecrtbot @username سلام چطوری؟ 😈\n\n"
        "2️⃣ نجوا عددی:\n"
        "من رو تایپ کن، آیدی عددی گیرنده رو تایپ کن، متن نجوات رو بنویس.\n"
        "مثال: @XSecrtbot 1234567890 سلام چطوری؟ 😈\n\n"
        "3️⃣ نجوا ریپلای:\n"
        "من رو تایپ کن، روی یکی از پیام های گیرنده ریپلای کن، متن نجوات رو بنویس.\n"
        "مثال: @XSecrtbot سلام چطوری؟ 😈\n\n"
        "4️⃣ نجوا تاریخچه:\n"
        "اگر قبلا به گیرنده مدنظرت نجوا دادی، وقتی من رو تایپ کنی، گزینه ارسال نجوا به اون کاربر بالای صفحه کیبوردت نشون داده میشه.\n\n"
        "⚠️ در هر حالت، بعد از اتمام تایپ متن نجوات، روی گزینه ارسال نجوا کلیک کن تا نجوات ساخته و ارسال بشه."
    )
    
    keyboard = [[
        InlineKeyboardButton("« بازگشت", callback_data="back_to_main")
    ]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        help_text,
        reply_markup=reply_markup
    )

# هندلر اینلاین کوئری
async def inline_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.inline_query.query
    user_id = update.effective_user.id
    
    # بررسی عضویت در کانال
    if not await check_membership(update, context, user_id):
        results = [InlineQueryResultArticle(
            id="need_join",
            title="لطفا قبل از شروع عضو شوید",
            input_message_content=InputTextMessageContent(
                "لطفا قبل از شروع روی این پیام کلیک کن🤌🏼"
            ),
            description="عضویت در کانال مورد نیاز است",
            thumb_url="https://telegram.org/img/favicon.ico"
        )]
        await update.inline_query.answer(results)
        return

    # پردازش تاریخچه گیرندگان
    user_history = user_data.get(user_id, {}).get("history", [])
    
    results = []
    
    # گزینه اول: وارد کردن یوزرنیم/آیدی
    results.append(InlineQueryResultArticle(
        id="enter_username",
        title="یوزرنیم یا آیدی عددی رو وارد کن 💡",
        input_message_content=InputTextMessageContent(
            "لطفاً یوزرنیم یا آیدی عددی گیرنده رو وارد کنید"
        ),
        description="وارد کردن یوزرنیم یا آیدی عددی گیرنده"
    ))
    
    # گزینه دوم: ریپلای بر روی پیام
    results.append(InlineQueryResultArticle(
        id="reply_to_message",
        title="روی پیام کاربر ریپلای کن 💡",
        input_message_content=InputTextMessageContent(
            "لطفاً روی یکی از پیام های گیرنده ریپلای کنید"
        ),
        description="استخراج اطلاعات از طریق ریپلای"
    ))
    
    # گزینه سوم و بعدی: تاریخچه گیرندگان
    for i, (receiver_id, last_name) in enumerate(user_history[:10]):
        if i >= 8:  # حداکثر 8 گزینه تاریخچه
            break
        results.append(InlineQueryResultArticle(
            id=f"history_{i}",
            title=f"{last_name} ({receiver_id})",
            input_message_content=InputTextMessageContent(
                f"@XSecrtbot {receiver_id} "
            ),
            description=f"ارسال نجوا به {last_name}"
        ))
    
    await update.inline_query.answer(results)

# هندلر پیام
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # پردازش پیام‌های معمولی
    if update.message.text.startswith(BOT_USERNAME):
        # پردازش فرمت‌های ارسال نجوا
        parts = update.message.text.split()
        if len(parts) < 3:
            await update.message.reply_text("فرمت اشتباه! لطفاً دستور العمل‌ها را دوباره بخوانید.")
            return
            
        # تشخیص نوع فرمت
        target = parts[1]
        message_text = " ".join(parts[2:])
        
        # تشخیص گیرنده
        if target.startswith('@'):
            # فرمت یوزرنیم
            receiver_id = await get_user_id_by_username(target)
        elif target.isdigit():
            # فرمت عددی
            receiver_id = int(target)
        else:
            await update.message.reply_text("فرمت اشتباه! لطفاً یوزرنیم یا آیدی عددی را به درستی وارد کنید.")
            return
            
        if not receiver_id:
            await update.message.reply_text("کاربر مورد نظر پیدا نشد!")
            return
            
        # ذخیره تاریخچه
        user_key = get_user_key(update.effective_user)
        if user_key not in user_data:
            user_data[user_key] = {"history": []}
            
        # اضافه کردن به تاریخچه
        if (receiver_id, update.effective_user.last_name) not in user_data[user_key]["history"]:
            user_data[user_key]["history"].insert(0, (receiver_id, update.effective_user.last_name))
            # حداکثر 10 مورد را نگه دارید
            user_data[user_key]["history"] = user_data[user_key]["history"][:10]
        
        # ارسال پیام اینلاین
        message_id = f"{update.effective_user.id}_{receiver_id}_{len(messages)+1}"
        messages[message_id] = {
            "sender": update.effective_user.id,
            "receiver": receiver_id,
            "text": message_text,
            "sent_time": persian_time(),
            "views": [],
            "snoops": []
        }
        
        # ایجاد دکمه‌ها
        keyboard = [
            [InlineKeyboardButton("ببینم 🤔", callback_data=f"view_{message_id}"),
             InlineKeyboardButton("پاسخ 💭", callback_data=f"reply_{message_id}")],
            [InlineKeyboardButton("حذف 🤌🏼", callback_data=f"delete_{message_id}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # ارسال پیام به گیرنده
        try:
            await context.bot.send_message(
                chat_id=receiver_id,
                text=f"نام شما: {update.effective_user.last_name}\n"
                     f"هنوز ندیده 😐\n"
                     f"تعداد فضول ها: 0",
                reply_markup=reply_markup
            )
            await update.message.reply_text("نجوا با موفقیت ارسال شد!")
        except Exception as e:
            await update.message.reply_text("متاسفانه نمی‌تونم نجوا رو ارسال کنم.")

# هندلر کلیک روی دکمه‌ها
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data.split('_')
    action = data[0]
    message_id = '_'.join(data[1:])
    
    if message_id not in messages:
        await query.edit_message_text("این نجوا دیگه وجود نداره!")
        return
    
    msg_data = messages[message_id]
    user_id = query.from_user.id
    
    if action == "view":
        if user_id == msg_data["receiver"]:
            # مشاهده نجوا توسط گیرنده
            msg_data["views"].append({
                "user": user_id,
                "time": persian_time()
            })
            
            # به‌روزرسانی متن نجوا
            view_count = len(msg_data["views"])
            snooper_count = len(msg_data["snoops"])
            
            new_text = f"{query.from_user.last_name}\n"
            new_text += f"نجوا رو {view_count} بار دیده 😈 {msg_data['views'][0]['time']}\n"
            new_text += f"تعداد فضول ها: {snooper_count}"
            
            await query.edit_message_text(
                new_text,
                reply_markup=query.message.reply_markup
            )
            
            # نمایش متن نجوا در پاپ‌آپ
            await query.answer(
                text=f"نویسنده: {msg_data['sender']}\n"
                     f"متن نجوا: {msg_data['text']}"
            )
        else:
            # تلاش غیرمجاز برای مشاهده
            msg_data["snoops"].append({
                "user": user_id,
                "time": persian_time()
            })
            await query.answer("شما اجازه مشاهده این نجوا رو ندارید!", show_alert=True)
    
    elif action == "delete":
        if user_id == msg_data["sender"]:
            # حذف نجوا
            new_text = f"{query.from_user.last_name}\n"
            new_text += "این نجوا توسط فرستنده، پاک شده 💤"
            
            # تغییر دکمه‌ها
            keyboard = [[
                InlineKeyboardButton("پاسخ 💭", callback_data=f"reply_{message_id}")
            ]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                new_text,
                reply_markup=reply_markup
            )
        else:
            await query.answer("فقط فرستنده می‌تونه نجوا رو حذف کنه!", show_alert=True)
    
    elif action == "reply":
        # پاسخ به نجوا
        if user_id == msg_data["receiver"]:
            # فعال کردن حالت پاسخ
            context.user_data["reply_to"] = msg_data["sender"]
            await query.message.reply_text("لطفاً متن پاسخ خود را بنویسید:")
        else:
            await query.answer("فقط گیرنده می‌تونه پاسخ بده!", show_alert=True)

# هندلر عضویت در کانال
async def channel_member_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_member = update.my_chat_member
    user_id = chat_member.from_user.id
    
    if chat_member.new_chat_member.status == 'left':
        # کاربر از کانال خارج شده
        try:
            await context.bot.send_message(
                chat_id=user_id,
                text="شما از کانال اسپانسر لفت دادی، لطفا برای استفاده از ربات، مجددا عضو کانال شوید."
            )
        except:
            pass  # اگر کاربر ربات رو بلاک کرده باشد

# هندلر پیام‌های متنی
async def text_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if "reply_to" in context.user_data:
        # در حالت پاسخ دادن
        reply_to_id = context.user_data["reply_to"]
        message_text = update.message.text
        
        # ارسال پیام پاسخ
        try:
            await context.bot.send_message(
                chat_id=reply_to_id,
                text=f"پاسخ از {update.effective_user.last_name}:\n{message_text}"
            )
            await update.message.reply_text("پاسخ با موفقیت ارسال شد!")
            context.user_data.pop("reply_to")
        except Exception as e:
            await update.message.reply_text("متاسفانه نمی‌تونم پاسخ رو ارسال کنم.")

def main():
    application = Application.builder().token(TOKEN).build()
    
    # اضافه کردن هندلرها
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(help_menu, pattern="help"))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(InlineQueryHandler(inline_query))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_message_handler))
    application.add_handler(MessageHandler(filters.StatusUpdate.CHAT_MEMBER, channel_member_handler))
    
    # شروع ربات
    application.run_polling()

if __name__ == '__main__':
    main()