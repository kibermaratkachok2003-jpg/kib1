import logging
import datetime
import asyncio
import aiohttp
from typing import Optional
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes
)

# КЛЮЧИ и ссылки хардкодом (НЕ os.environ)
BOT_TOKEN = "8572568483:AAGDnh10VMr3W_o3OJOZ-6gxkfzgYYzOwuo"
CRM_URL = "https://kiberonevostochnoebiryulevo.s20.online/"
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

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

async def cleanup_old_leads():
    now = datetime.datetime.now()
    leads_storage[:] = [lead for lead in leads_storage if (now - lead['timestamp']).days < 3]

def mask_md(text):
    # Экранирует потенциально опасные символы под MarkdownV2, чтобы не ломать разметку
    escape_chars = r'_*[]()~`>#+-=|{}.!'
    return ''.join('\\' + c if c in escape_chars else c for c in str(text))

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await cleanup_old_leads()
    context.user_data.clear()
    keyboard = [
        [InlineKeyboardButton("📌 Записаться сейчас", callback_data="register")],
        [InlineKeyboardButton("❌ Нет, пусть в телефоне сидит", callback_data="cancel")]
    ]
    await update.message.reply_text(greeting_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
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

async def handle_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get('awaiting_phone'):
        return  # Не ждем телефон сейчас, значит, игнорировать
    phone = update.message.text.strip()
    # Простая проверка (только +7 и 11 цифр)
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
    #await send_to_crm(user_data) #когда будет работать, все остальное тоже заработает
    # Подставляем данные и экранируем для Markdown
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


async def get_alfa_crm_token() -> Optional[str]:
    """
    Асинхронно получает временный токен для работы с ALFA-CRM API

    Args:
        hostname (str): Доменное имя ALFA-CRM (например, 'demo.s20.online')
        email (str): Email пользователя с доступом к v2api
        api_key (str): API ключ пользователя

    Returns:
        Optional[str]: Токен авторизации или None в случае ошибки
    """

    # Формируем URL для авторизации
    auth_url = f"https://{CRM_URL}/v2api/auth/login"

    # Данные для авторизации
    auth_data = {
        "email": "dissonance96@yandex.ru",
        "api_key": "e1b5f46a4f69fa86088742749376e22a"
    }

    # Заголовки запроса
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json"
    }

    try:
        # Создаем асинхронную сессию и отправляем POST запрос
        async with aiohttp.ClientSession() as session:
            async with session.post(
                    auth_url,
                    data=json.dumps(auth_data),
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=30)
            ) as response:

                # Проверяем успешность запроса
                if response.status == 200:
                    # Парсим ответ
                    response_data = await response.json()
                    token = response_data.get('token')

                    if token:
                        print(f"Токен успешно получен. Срок жизни: 3600 секунд")
                        return token
                    else:
                        print("Ошибка: токен не найден в ответе")
                        return None

                else:
                    response_text = await response.text()
                    print(f"Ошибка авторизации: {response.status}")
                    print(f"Ответ сервера: {response_text}")
                    return None

    except aiohttp.ClientError as e:
        print(f"Ошибка при выполнении запроса: {e}")
        return None
    except json.JSONDecodeError as e:
        print(f"Ошибка при парсинге JSON ответа: {e}")
        return None
    except asyncio.TimeoutError:
        print("Таймаут при получении токена")
        return None
    except Exception as e:
        print(f"Неожиданная ошибка: {e}")
        return None


async def send_to_crm(lead_data):
    try:
        token = await get_alfa_crm_token()
        async with aiohttp.ClientSession() as session:
            data = {
                "key": CRM_KEY,
                "phone": lead_data['phone'],
                "user_id": str(lead_data['user_id']),
                "username": lead_data['username'],
                "first_name": lead_data['first_name'],
                "location": lead_data['location'],
                "age": lead_data['age'],
                "source": "telegram_bot",
                "timestamp": lead_data['timestamp'].isoformat()
            }
            async with session.post(f"{CRM_URL}api/1/lead/create?token={token}", json=data, timeout=10) as response:
                if response.status == 200:
                    logging.info("Lead sent to CRM")
                else:
                    logging.error(f"CRM error: {response.status}")
    except Exception as e:
        logging.error(f"Error sending to CRM: {e}")

async def admin_login(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args or []
    if not args:
        await update.message.reply_text(
            "🔐 *Введите пароль администратора после команды /admin:*\n\nПример: `/admin cyber2024`", parse_mode='Markdown')
        return
    password = args[0]
    if password in ADMIN_PASSWORDS:
        admin_sessions.add(update.effective_user.id)
        await cleanup_old_leads()
        today = datetime.datetime.now().date()
        today_leads = len([lead for lead in leads_storage if lead['timestamp'].date() == today])
        admin_message = (
            f"✅ *Бот работает исправно!*\n\n"
            f"📊 Статистика за сегодня:\n• Новых лидов: {today_leads}\n• Всего в памяти: {len(leads_storage)}\n\n"
            f"⚙ *Команды администратора:*\n"
            f"/stats - Показать статистику\n"
            f"/today_leads - Показать сегодняшние лиды\n"
            f"/edit_greeting - Изменить приветствие\n"
            f"/edit_success - Изменить текст успешной записи"
        )
        await update.message.reply_text(admin_message, parse_mode='Markdown')
    else:
        await update.message.reply_text("❌ Неверный пароль!")

async def edit_greeting(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in admin_sessions:
        await update.message.reply_text("❌ Доступ запрещён! Используйте /admin для входа.")
        return
    text = ' '.join(context.args)
    if not text:
        await update.message.reply_text("📝 Введите новый текст приветствия после команды.")
        return
    global greeting_text
    greeting_text = text
    await update.message.reply_text("✅ Текст приветствия обновлён!")

async def edit_success(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in admin_sessions:
        await update.message.reply_text("❌ Доступ запрещён! Используйте /admin для входа.")
        return
    text = ' '.join(context.args)
    if not text:
        await update.message.reply_text("📝 Введите новый текст успешной записи после команды.")
        return
    global success_text
    success_text = text
    await update.message.reply_text("✅ Текст успеха обновлён!")

async def show_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in admin_sessions:
        await update.message.reply_text("❌ Доступ запрещён! Используйте /admin для входа.")
        return
    await cleanup_old_leads()
    today = datetime.datetime.now().date()
    today_leads = len([lead for lead in leads_storage if lead['timestamp'].date() == today])
    stats_text = (
        f"📊 *Статистика лидов:*\n"
        f"• Лидов за сегодня: {today_leads}\n"
        f"• Всего в памяти: {len(leads_storage)}\n"
        f"• Сессий админов: {len(admin_sessions)}"
    )
    await update.message.reply_text(stats_text, parse_mode='Markdown')

async def show_today_leads(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in admin_sessions:
        await update.message.reply_text("❌ Доступ запрещён! Используйте /admin для входа.")
        return
    await cleanup_old_leads()
    today = datetime.datetime.now().date()
    today_leads = [lead for lead in leads_storage if lead['timestamp'].date() == today]
    if not today_leads:
        await update.message.reply_text("📊 *Лидов за сегодня нет*", parse_mode='Markdown')
        return
    leads_msg = "📊 *Лиды за сегодня:*\n\n"
    for i, lead in enumerate(today_leads, start=1):
        leads_msg += (
            f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"👤 *Лид #{i}*\n"
            f"├─ Имя: {mask_md(lead['first_name'])}\n"
            f"├─ Username: @{mask_md(lead['username'])}\n"
            f"├─ Телефон: {mask_md(lead['phone'])}\n"
            f"├─ Возраст: {mask_md(lead['age'])}\n"
            f"├─ Локация: {mask_md(lead['location'])}\n"
            f"└─ Время: {lead['timestamp'].strftime('%H:%M')}\n\n"
        )
    chunks = [leads_msg[i:i+4000] for i in range(0, len(leads_msg), 4000)]
    for c in chunks:
        await update.message.reply_text(c, parse_mode='MarkdownV2')

async def reminder_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(reminder_text, parse_mode='Markdown')

def main():
    application = Application.builder().token(BOT_TOKEN).read_timeout(30).write_timeout(30).connect_timeout(30).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_phone))
    application.add_handler(CommandHandler("admin", admin_login))
    application.add_handler(CommandHandler("edit_greeting", edit_greeting))
    application.add_handler(CommandHandler("edit_success", edit_success))
    application.add_handler(CommandHandler("stats", show_stats))
    application.add_handler(CommandHandler("today_leads", show_today_leads))
    application.add_handler(CommandHandler("reminder", reminder_command))
    logging.info("Bot started!")
    print("✅ Бот запущен! Проверьте Telegram...")
    application.run_polling(poll_interval=1.0, timeout=30, drop_pending_updates=True)

if __name__ == '__main__':
    main()
