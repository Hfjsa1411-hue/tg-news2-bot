import os
import logging
import datetime
from dotenv import load_dotenv
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters
)
from parser import get_top_posts
from storage import load_data, save_data

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
YOUR_USER_ID = int(os.getenv("YOUR_USER_ID"))

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)


def get_main_menu():
    keyboard = [
        ["➕ Добавить канал", "➖ Удалить канал"],
        ["📋 Мои каналы", "🏆 Топ прямо сейчас"],
        ["⚙️ Настройки", "📅 Расписание"],
        ["📖 Справка"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def format_post(i: int, post: dict) -> str:
    views_str = f"{post['views']:,}".replace(",", " ")
    text = post["text"]
    if len(text) > 350:
        text = text[:350] + "..."
    medals = {1: "🥇", 2: "🥈", 3: "🥉"}
    medal = medals.get(i, f"#{i}")
    return (
        f"{medal} *{post['channel_title']}*\n"
        f"👁 {views_str} просмотров\n\n"
        f"{text}\n\n"
        f"[📲 Читать в Telegram]({post['url']})"
    )


async def send_digest(context):
    app = context.application
    data = load_data()
    if not data["channels"]:
        return
    try:
        await app.bot.send_message(YOUR_USER_ID, "📨 *Твой дайджест готов!*", parse_mode="Markdown")
        
        for channel in data["channels"]:
            posts = get_top_posts([channel], hours=data.get("hours", 24), top_n=data.get("top_count", 5))
            
            if not posts:
                await app.bot.send_message(
                    YOUR_USER_ID,
                    f"😔 Посты из {channel} не найдены."
                )
                continue
            
            channel_title = posts[0].get("channel_title", channel)
            await app.bot.send_message(
                YOUR_USER_ID,
                f"📺 *{channel_title}*",
                parse_mode="Markdown"
            )
            
            for i, post in enumerate(posts, 1):
                await app.bot.send_message(
                    YOUR_USER_ID,
                    format_post(i, post),
                    parse_mode="Markdown",
                    disable_web_page_preview=False
                )
            
            await app.bot.send_message(YOUR_USER_ID, "━" * 30)
    except Exception as e:
        print(f"Ошибка дайджеста: {e}")


async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 *Привет! Я твой новостной бот.*\n\n"
        "Выбери действие из меню ниже:",
        parse_mode="Markdown",
        reply_markup=get_main_menu()
    )


async def handle_menu(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    
    if text == "➕ Добавить канал":
        await update.message.reply_text(
            "📝 Отправь мне название канала:\n"
            "Примеры: @channelname или channelname"
        )
        ctx.user_data["action"] = "add_channel"
    
    elif text == "➖ Удалить канал":
        data = load_data()
        if not data["channels"]:
            await update.message.reply_text("📋 Нет добавленных каналов", reply_markup=get_main_menu())
            return
        
        keyboard = [[ch] for ch in data["channels"]]
        keyboard.append(["❌ Отмена"])
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        
        await update.message.reply_text("Выбери канал для удаления:", reply_markup=reply_markup)
        ctx.user_data["action"] = "remove_channel"
    
    elif text == "📋 Мои каналы":
        data = load_data()
        if not data["channels"]:
            text_msg = "📋 Список пуст.\nДобавь каналы через меню."
        else:
            text_msg = "📋 *Твои каналы:*\n" + "\n".join(f"• {c}" for c in data["channels"])
            text_msg += f"\n\n🕒 Период: {data.get('hours', 24)}ч\n🔢 Топ: {data.get('top_count', 5)} постов"
        
        await update.message.reply_text(text_msg, parse_mode="Markdown", reply_markup=get_main_menu())
    
    elif text == "🏆 Топ прямо сейчас":
        data = load_data()
        if not data["channels"]:
            await update.message.reply_text("Сначала добавь каналы в меню.", reply_markup=get_main_menu())
            return
        
        await update.message.reply_text("⏳ Собираю топ постов, подожди...")
        
        for channel in data["channels"]:
            posts = get_top_posts([channel], hours=data.get("hours", 24), top_n=data.get("top_count", 5))
            
            if not posts:
                await ctx.bot.send_message(
                    update.message.chat_id,
                    f"😔 Посты из {channel} не найдены."
                )
                continue
            
            channel_title = posts[0].get("channel_title", channel)
            await ctx.bot.send_message(
                update.message.chat_id,
                f"📺 *{channel_title}*",
                parse_mode="Markdown"
            )
            
            for i, post in enumerate(posts, 1):
                await ctx.bot.send_message(
                    update.message.chat_id,
                    format_post(i, post),
                    parse_mode="Markdown",
                    disable_web_page_preview=False
                )
            
            await ctx.bot.send_message(update.message.chat_id, "━" * 30)
        
        await ctx.bot.send_message(
            update.message.chat_id,
            "✅ Готово!",
            reply_markup=get_main_menu()
        )
    
    elif text == "⚙️ Настройки":
        data = load_data()
        text_msg = (
            f"⚙️ *Текущие настройки:*\n\n"
            f"🕒 Период: {data.get('hours', 24)} часов\n"
            f"🔢 Топ постов: {data.get('top_count', 5)}\n\n"
            f"Отправь: <часов> <кол-во постов>\n"
            f"Пример: 24 10"
        )
        
        await update.message.reply_text(text_msg, parse_mode="Markdown", reply_markup=get_main_menu())
        ctx.user_data["action"] = "settings"
    
    elif text == "📅 Расписание":
        data = load_data()
        schedule_text = data.get("schedule_time") or "не установлено"
        
        text_msg = f"📅 *Расписание:*\n\nТекущее время: {schedule_text}\n\nОтправь время в формате HH:MM\nПример: 09:00\n\nИли отправь: off"
        
        await update.message.reply_text(text_msg, parse_mode="Markdown", reply_markup=get_main_menu())
        ctx.user_data["action"] = "schedule"
    
    elif text == "📖 Справка":
        text_msg = (
            "📖 *Справка:*\n\n"
            "➕ Добавить канал\n"
            "➖ Удалить канал\n"
            "📋 Мои каналы\n"
            "🏆 Топ прямо сейчас\n"
            "⚙️ Настройки\n"
            "📅 Расписание\n\n"
            "⚠️ Работает только с публичными каналами!"
        )
        
        await update.message.reply_text(text_msg, parse_mode="Markdown", reply_markup=get_main_menu())
    
    elif text == "❌ Отмена":
        ctx.user_data["action"] = None
        await update.message.reply_text("Отменено", reply_markup=get_main_menu())
    
    else:
        action = ctx.user_data.get("action")
        
        if action == "add_channel":
            channel = text
            if not channel.startswith("@"):
                channel = "@" + channel
            
            data = load_data()
            if channel in data["channels"]:
                await update.message.reply_text(f"⚠️ Канал {channel} уже добавлен", reply_markup=get_main_menu())
            else:
                data["channels"].append(channel)
                save_data(data)
                await update.message.reply_text(f"✅ Добавлен: *{channel}*", parse_mode="Markdown", reply_markup=get_main_menu())
            
            ctx.user_data["action"] = None
        
        elif action == "remove_channel":
            channel = text
            data = load_data()
            if channel in data["channels"]:
                data["channels"].remove(channel)
                save_data(data)
                await update.message.reply_text(f"❌ Удалён: *{channel}*", parse_mode="Markdown", reply_markup=get_main_menu())
            else:
                await update.message.reply_text("Канал не найден", reply_markup=get_main_menu())
            
            ctx.user_data["action"] = None
        
        elif action == "settings":
            try:
                parts = text.split()
                hours = int(parts[0])
                top_n = int(parts[1]) if len(parts) > 1 else 5
                
                data = load_data()
                data["hours"] = max(1, min(168, hours))
                data["top_count"] = max(1, min(20, top_n))
                save_data(data)
                
                await update.message.reply_text(
                    f"✅ Обновлено:\n🕒 Период: {data['hours']} часов\n🔢 Топ: {data['top_count']} постов",
                    reply_markup=get_main_menu()
                )
            except:
                await update.message.reply_text("❌ Неверный формат. Пример: 24 10", reply_markup=get_main_menu())
            
            ctx.user_data["action"] = None
        
        elif action == "schedule":
            time_str = text.strip()
            
            if time_str.lower() == "off":
                ctx.job_queue.scheduler.remove_all_jobs()
                data = load_data()
                data["schedule_time"] = None
                save_data(data)
                await update.message.reply_text("⏹ Авторассылка отключена", reply_markup=get_main_menu())
            else:
                try:
                    hour, minute = map(int, time_str.split(":"))
                    assert 0 <= hour <= 23 and 0 <= minute <= 59
                    
                    ctx.job_queue.run_daily(
                        send_digest,
                        time=datetime.time(hour=hour, minute=minute),
                        name="daily_digest"
                    )

                    jobs = ctx.job_queue.get_jobs_by_name("daily_digest")
                    for job in jobs[:-1]:
                        job.schedule_removal()

                    data = load_data()
                    data["schedule_time"] = time_str
                    save_data(data)
                    
                    await update.message.reply_text(
                        f"✅ Дайджест будет приходить каждый день в *{time_str}* (МСК)",
                        parse_mode="Markdown",
                        reply_markup=get_main_menu()
                    )
                except:
                    await update.message.reply_text("❌ Неверный формат. Пример: 09:00", reply_markup=get_main_menu())
            
            ctx.user_data["action"] = None


async def post_init(app):
    data = load_data()
    schedule_time = data.get("schedule_time")
    
    if schedule_time:
        try:
            hour, minute = map(int, schedule_time.split(":"))
            app.job_queue.run_daily(
                send_digest,
                time=datetime.time(hour=hour, minute=minute),
                name="daily_digest"
            )
            print(f"📅 Расписание восстановлено: {schedule_time}")
        except:
            print("⚠️ Не удалось восстановить расписание")


def main():
    app = (
        ApplicationBuilder()
        .token(BOT_TOKEN)
        .post_init(post_init)
        .build()
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_menu))

    print("🤖 Бот запущен с клавиатурой! Нажми Ctrl+C для остановки.")
    app.run_polling()


if __name__ == "__main__":
    main()