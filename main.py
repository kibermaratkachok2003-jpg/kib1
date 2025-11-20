import logging
import datetime
import asyncio
import aiohttp
import json  # Добавьте этот импорт
import traceback  # Добавьте для детальных ошибок
from typing import Optional
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes
)

# Настройка подробного логирования
logging.basicConfig(
    level=logging.DEBUG,  # Измените на DEBUG для подробных логов
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),  # Вывод в консоль
        logging.FileHandler('bot_errors.log')  # Запись в файл
    ]
)

# КЛЮЧИ и ссылки хардкодом
BOT_TOKEN = "8572568483:AAGDnh10VMr3W_o3OJOZ-6gxkfzgYYzOwuo"
CRM_URL = "https://kiberonevostochnoebiryulevo.s20.online/"  # Уберите слеш в конце
CRM_KEY = "8f513ee3-4afb-11ee-8939-3cecef7ebd64"
ADMIN_PASSWORDS = {"cyber2024", "admin123", "kiberone"}

admin_sessions = set()
leads_storage = []

# ---- Тексты ----
greeting_text = """🌟 *Здравствуйте! Добро пожаловать в KIBERone!* 🌟

Я — ваш цифровой помощник из международной кибершколы будущего.
KIBERone - это не просто кружок, а уверенный шаг к тому, чтобы ваш ребёнок вошёл в 1% самых успешных людей планеты! 🚀

🎯 *Наша программа признана ЮНЕСКО лучшей в мире*
• Дети создают свои чат-боты, сайты, приложения и многое другое
• Учатся управлять нейросетями и делать реальные проекты
• Развивают мышление предпринимателя и уверенность в себе

✨ *Хотите попробовать?* Приходите на ДЕМО занятие и ваш ребёнок создаст своего нейро-героя в Roblox! 🎮

📌 *Готовы записаться?* Жмите кнопку ниже! 👇"""
success_text = """🎉 *Поздравляем! Запись успешно создана!* 🎉

Ваш ребёнок сделал первый шаг в будущее технологий!
Мы свяжемся с вами в ближайшее время для подтверждения демо-занятия.

🌟 *Ждём вас в KIBERone* - месте, где рождаются гении!"""
reminder_text = """📢 *Напоминаем!*
Вы можете записаться на демо-занятие в любое время - просто введите /start 🚀"""

async def cleanup_old_leads():
    try:
        now = datetime.datetime.now()
        leads_storage[:] = [lead for lead in leads_storage if (now - lead['timestamp']).days < 3]
    except Exception as e:
        logging.error(f"Error in cleanup_old_leads: {e}")

def mask_md(text):
    try:
        escape_chars = r'_*[]()~`>#+-=|{}.!'
        return ''.join('\\' + c if c in escape_chars else c for c in str(text))
    except Exception as e:
        logging.error(f"Error in mask_md: {e}")
        return str(text)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        await cleanup_old_leads()
        context.user_data.clear()
        keyboard = [
            [InlineKeyboardButton("📌 Записаться сейчас", callback_data="register")],
            [InlineKeyboardButton("❌ Нет, пусть в телефоне сидит", callback_data="cancel")]
        ]
        await update.message.reply_text(greeting_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        logging.info(f"Start command handled for user {update.effective_user.id}")
    except Exception as e:
        logging.error(f"Error in start: {e}\n{traceback.format_exc()}")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        query = update.callback_query
        await query.answer()
        logging.info(f"Button pressed: {query.data} by user {query.from_user.id}")
        
        if query.data == "register":
            consent_text = "✅ *Важно! Перед записью нужно ваше согласие:*\n\n✔ Я соглашаюсь на обработку персональных данных и получение полезных сообщений от KIBERone."
            keyboard = [[InlineKeyboardButton("📌 Согласен", callback_data="consent_given")]]
            await query.edit_message_text(consent_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        elif query.data == "consent_given":
            context.user_data.update({
                'username': query.from_user.username or query.from_user.first_name or "Не указано",
                'first_name': query.from_user.first_name or "Не указано"
            })
            location_text = "📍 *Выберите удобную локацию:*"
            keyboard = [
                [InlineKeyboardButton("• 6-ая Радиальная 3к11, ЖК Царицыно", callback_data="location_1")],
                [InlineKeyboardButton("• Липецкая 54/21 стр.2 (Библиотека 140)", callback_data="location_2")]
            ]
            await query.edit_message_text(location_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        elif query.data in ["location_1", "location_2"]:
            context.user_data['location'] = "6-ая Радиальная 3к11, ЖК Царицыно" if query.data == "location_1" else "Липецкая 54/21 стр.2 (Библиотека 140)"
            age_text = "👶 *Выберите возраст ребенка:*"
            keyboard = [
                [InlineKeyboardButton("• 6-8 лет", callback_data="age_6_8")],
                [InlineKeyboardButton("• 9-11 лет", callback_data="age_9_11")],
                [InlineKeyboardButton("• 12-15 лет", callback_data="age_12_15")]
            ]
            await query.edit_message_text(age_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        elif query.data.startswith("age_"):
            age_map = {"age_6_8": "6-8 лет", "age_9_11": "9-11 лет", "age_12_15": "12-15 лет"}
            context.user_data['age'] = age_map.get(query.data, "Не выбрано")
            phone_request = "📞 *Для завершения записи введите ваш номер телефона:*\n\nФормат: +7XXXXXXXXXX"
            context.user_data['awaiting_phone'] = True
            await query.edit_message_text(phone_request, parse_mode='Markdown')
        elif query.data == "cancel":
            context.user_data.clear()
            await query.edit_message_text("😔 Жаль, но мы всегда ждём вас! Если передумаете - нажмите /start")
            
    except Exception as e:
        logging.error(f"Error in button_handler: {e}\n{traceback.format_exc()}")

async def handle_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if not context.user_data.get('awaiting_phone'):
            return
        
        phone = update.message.text.strip()
        logging.info(f"Phone received: {phone} from user {update.effective_user.id}")
        
        if not (phone.startswith('+7') and len(phone) == 12 and phone[1:].isdigit()):
            await update.message.reply_text("❌ Пожалуйста, введите номер в формате +7XXXXXXXXXX")
            return
            
        user_data = {
            'user_id': update.effective_user.id,
            'phone': phone,
            'timestamp': datetime.datetime.now(),
            'username': context.user_data.get('username', update.effective_user.username or 'Не указано'),
            'first_name': context.user_data.get('first_name', update.effective_user.first_name or 'Не указано'),
            'location': context.user_data.get('location', 'Не выбрано'),
            'age': context.user_data.get('age', 'Не выбрано')
        }
        
        leads_storage.append(user_data)
        context.user_data['awaiting_phone'] = False
        await cleanup_old_leads()
        
        # Временно отключаем CRM для тестирования
        # await send_to_crm(user_data)
        
        msg = (
            f"🎊✨ ВЕЛИКОЛЕПНО! ВАША ЗАЯВКА ПРИНЯТА! ✨🎊\n\n"
            f"🎉 {mask_md(user_data['first_name'])}, вы сделали важный шаг в будущее вашего ребенка!\n\n"
            f"👨‍👩‍👧‍👦 *Данные вашей заявки:*\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"👤 Имя: {mask_md(user_data['first_name'])}\n"
            f"🎂 Возраст ребенка: {mask_md(user_data['age'])}\n"
            f"📍 Локация: {mask_md(user_data['location'])}\n"
            f"📞 Телефон: {mask_md(user_data['phone'])}\n\n"
            f"🚀 Ждем вас на увлекательном пробном занятии!\n\n"
            f"⏰ Мы свяжемся с вами в ближайшее время для подтверждения записи и согласования удобного времени.\n\n"
            f"💫 KIBERone - шаг в успешное будущее вашего ребенка!"
        )
        await update.message.reply_text(msg, parse_mode='MarkdownV2')
        context.user_data.clear()
        logging.info(f"Lead created successfully for user {update.effective_user.id}")
        
    except Exception as e:
        logging.error(f"Error in handle_phone: {e}\n{traceback.format_exc()}")
        await update.message.reply_text("❌ Произошла ошибка при обработке заявки. Попробуйте позже.")

# ВРЕМЕННО ОТКЛЮЧИМ CRM ФУНКЦИИ ДЛЯ ТЕСТИРОВАНИЯ
"""
async def get_alfa_crm_token() -> Optional[str]:
    try:
        # Исправленный URL - убираем https:// в начале
        crm_domain = CRM_URL.replace('https://', '').replace('/', '')
        auth_url = f"https://{crm_domain}/v2api/auth/login"
        
        logging.info(f"Trying to get CRM token from: {auth_url}")
        
        auth_data = {
            "email": "dissonance96@yandex.ru", 
            "api_key": "e1b5f46a4f69fa86088742749376e22a"
        }

        headers = {"Content-Type": "application/json"}

        async with aiohttp.ClientSession() as session:
            async with session.post(auth_url, json=auth_data, headers=headers, timeout=30) as response:
                logging.info(f"CRM auth response status: {response.status}")
                
                if response.status == 200:
                    response_data = await response.json()
                    token = response_data.get('token')
                    if token:
                        logging.info("CRM token received successfully")
                        return token
                    else:
                        logging.error("No token in CRM response")
                        return None
                else:
                    response_text = await response.text()
                    logging.error(f"CRM auth failed: {response.status} - {response_text}")
                    return None
                    
    except Exception as e:
        logging.error(f"Error getting CRM token: {e}\n{traceback.format_exc()}")
        return None

async def send_to_crm(lead_data):
    try:
        logging.info("Attempting to send lead to CRM")
        token = await get_alfa_crm_token()
        if not token:
            logging.error("No CRM token available")
            return
            
        crm_domain = CRM_URL.replace('https://', '').replace('/', '')
        create_url = f"https://{crm_domain}/v2api/1/lead/create"
        
        data = {
            "phone": lead_data['phone'],
            "name": lead_data['first_name'],
            "custom_fields": {
                "user_id": str(lead_data['user_id']),
                "username": lead_data['username'],
                "location": lead_data['location'], 
                "age": lead_data['age'],
                "source": "telegram_bot"
            }
        }
        
        headers = {
            "X-ALFACRM-TOKEN": token,
            "Content-Type": "application/json"
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(create_url, json=data, headers=headers, timeout=10) as response:
                logging.info(f"CRM create lead response: {response.status}")
                if response.status == 200:
                    logging.info("Lead sent to CRM successfully")
                else:
                    response_text = await response.text()
                    logging.error(f"CRM create lead error: {response.status} - {response_text}")
                    
    except Exception as e:
        logging.error(f"Error sending to CRM: {e}\n{traceback.format_exc()}")
"""

# ... остальные функции (admin_login, edit_greeting и т.д.) остаются без изменений

def main():
    try:
        logging.info("Starting bot initialization...")
        
        # Создаем application с таймаутами
        application = Application.builder().token(BOT_TOKEN).build()
        
        # Добавляем обработчики
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CallbackQueryHandler(button_handler))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_phone))
        application.add_handler(CommandHandler("admin", admin_login))
        application.add_handler(CommandHandler("edit_greeting", edit_greeting))
        application.add_handler(CommandHandler("edit_success", edit_success))
        application.add_handler(CommandHandler("stats", show_stats))
        application.add_handler(CommandHandler("today_leads", show_today_leads))
        application.add_handler(CommandHandler("reminder", reminder_command))
        
        logging.info("Bot started successfully!")
        print("✅ Бот запущен! Проверьте Telegram...")
        
        # Запускаем бота
        application.run_polling()
        
    except Exception as e:
        logging.error(f"Failed to start bot: {e}\n{traceback.format_exc()}")
        print(f"❌ Критическая ошибка запуска бота: {e}")

if __name__ == '__main__':
    main()
