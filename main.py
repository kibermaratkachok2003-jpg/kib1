import logging
import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes
)

# Простая настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

BOT_TOKEN = "8572568483:AAGDnh10VMr3W_o3OJOZ-6gxkfzgYYzOwuo"
ADMIN_PASSWORDS = {"cyber2024", "admin123", "kiberone"}

admin_sessions = set()
leads_storage = []

# Тексты
greeting_text = """🌟 *Здравствуйте! Добро пожаловать в KIBERone!* 🌟

Я — ваш цифровой помощник из международной кибершколы будущего."""

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        keyboard = [
            [InlineKeyboardButton("📌 Записаться сейчас", callback_data="register")],
            [InlineKeyboardButton("❌ Отмена", callback_data="cancel")]
        ]
        await update.message.reply_text(
            greeting_text, 
            reply_markup=InlineKeyboardMarkup(keyboard), 
            parse_mode='Markdown'
        )
        print(f"✅ Start command handled for user {update.effective_user.id}")
    except Exception as e:
        print(f"❌ Error in start: {e}")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        query = update.callback_query
        await query.answer()
        
        if query.data == "register":
            await query.edit_message_text("✅ Для записи введите номер телефона:")
            context.user_data['awaiting_phone'] = True
        elif query.data == "cancel":
            await query.edit_message_text("😔 Жаль! Если передумаете - нажмите /start")
            
    except Exception as e:
        print(f"❌ Error in button_handler: {e}")

async def handle_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if not context.user_data.get('awaiting_phone'):
            return
            
        phone = update.message.text.strip()
        print(f"📞 Phone received: {phone}")
        
        # Простая проверка номера
        if not phone.startswith('+7') or len(phone) != 12:
            await update.message.reply_text("❌ Введите номер в формате +7XXXXXXXXXX")
            return
            
        # Сохраняем заявку
        lead_data = {
            'user_id': update.effective_user.id,
            'phone': phone,
            'timestamp': datetime.datetime.now(),
            'name': update.effective_user.first_name or "Не указано"
        }
        leads_storage.append(lead_data)
        
        await update.message.reply_text(
            f"🎉 Спасибо, {update.effective_user.first_name}! Ваша заявка принята!\n"
            f"📞 Телефон: {phone}\n\n"
            f"Мы свяжемся с вами в ближайшее время!"
        )
        context.user_data.clear()
        print(f"✅ Lead saved: {lead_data}")
        
    except Exception as e:
        print(f"❌ Error in handle_phone: {e}")

async def admin_login(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        args = context.args or []
        if not args:
            await update.message.reply_text("🔐 Введите пароль: /admin пароль")
            return
            
        if args[0] in ADMIN_PASSWORDS:
            admin_sessions.add(update.effective_user.id)
            await update.message.reply_text("✅ Вы вошли как администратор!")
        else:
            await update.message.reply_text("❌ Неверный пароль!")
    except Exception as e:
        print(f"❌ Error in admin_login: {e}")

async def show_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if update.effective_user.id not in admin_sessions:
            await update.message.reply_text("❌ Нет доступа!")
            return
            
        today_count = len([
            lead for lead in leads_storage 
            if lead['timestamp'].date() == datetime.datetime.now().date()
        ])
        
        await update.message.reply_text(
            f"📊 Статистика:\n"
            f"• Лидов сегодня: {today_count}\n"
            f"• Всего лидов: {len(leads_storage)}"
        )
    except Exception as e:
        print(f"❌ Error in show_stats: {e}")

def main():
    print("🚀 Запуск бота...")
    
    try:
        # Создаем приложение
        application = Application.builder().token(BOT_TOKEN).build()
        
        # Добавляем обработчики
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CallbackQueryHandler(button_handler))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_phone))
        application.add_handler(CommandHandler("admin", admin_login))
        application.add_handler(CommandHandler("stats", show_stats))
        
        # Запускаем бота
        print("✅ Бот запущен!")
        application.run_polling()
        
    except Exception as e:
        print(f"💥 КРИТИЧЕСКАЯ ОШИБКА: {e}")

if __name__ == '__main__':
    main()
