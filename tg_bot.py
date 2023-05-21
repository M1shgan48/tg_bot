import logging
from datetime import date, datetime
from telegram.ext import Application, MessageHandler, filters, CommandHandler, ConversationHandler
from telegram import ReplyKeyboardMarkup
from bs4 import BeautifulSoup
import requests
import asyncio
import sqlite3



# Запускаем логгирование
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.DEBUG
)
logger = logging.getLogger(__name__)
back_post_id = None


# Фунция проверяющая наличие новых постов каждого пользователя в бд, и оповещающая его о наличиях.
async def news(update, context):
    global back_post_id
    con = sqlite3.connect("telegramm_bot.db")
    cur = con.cursor()
    # Открываем баззу данных и проверяем разрешает ли пользователь присылать ему сайт
    result = cur.execute("""SELECT * FROM people WHERE perm = 'TRUE'""").fetchall()
    try:
        for i in result:
            # Собираем с сайта пост для каждого человека по его интерусу
            url = f"https://www.playground.ru/news/{i[2]}"
            page = requests.get(url)
            soup = BeautifulSoup(page.content, "html.parser")

            post = soup.find("div", class_="post-flow-container", id=True)
            post = str(post)
            post = post.split("|")
            post = post[1].split('<div class="post-title">')
            post = post[1].strip('"')
            post = post.split('<a href="')
            post = post[1]
            post = str(post).split("</a>")
            post = post[0].split('">')
            who_people = int(i[0])
            spis_text = ["Вышел новый пост! Думаю вам понравится", "Ого! Это новый пост, прочитайте скорее",
                         "Я нашел для вас что-то интересное!", "Спешу вас обрадовать, по вашему итересу найден пост!"]
            if post[0] != i[-1]:  # Если вышел новый пост выкладываем пользователю и запоминаем его как последний
                cur.execute(f"""UPDATE people SET back_post = '{post[0]}'
                        WHERE people_id = '{str(i[0])}'""")
                await context.bot.send_message(chat_id=who_people, text='Вышел новый пост! Думаю вам понравится')
                news_paper = f"{post[1]}\n{post[0]}"
                await context.bot.send_message(chat_id=who_people, text=news_paper)
        await asyncio.sleep(1)
        asyncio.create_task(news(update, context))

        con.commit()
        con.close()

    except Exception:  # При возникновении ошибки, игнорируем ее
        con.commit()
        con.close()
        await asyncio.sleep(1)
        asyncio.create_task(news(update, context))


# Команда старт запускаяющая нашего бота.
async def start(update, context):
    """Отправляет сообщение когда получена команда /start"""
    user = update.effective_user
    await update.message.reply_html(
        rf"{user.mention_html()}! Здраствуйте! Я ваш личный бот, который будет показывать самые свежие новости"
        rf" от 'playground.ru'",
        reply_markup=markup)
    await update.message.reply_text("Что бы выбрать интерес нажмите кнопку - interests")
    asyncio.create_task(news(update, context))


# Команда помощи, кратко обьясняющая о боте.
async def help_command(update, context):
    """Отправляет сообщение когда получена команда /help"""
    await update.message.reply_text("Я бот, который уведомляет вас о самых новых постах по вашему интересу")
    await update.message.reply_text("Что бы выбрать интерес нажмите кнопку - interests")
    await update.message.reply_text("Что бы приостановить бота нажмите - stop")
    await update.message.reply_text("Что бы узнать время нажмите - time")
    await update.message.reply_text("Что бы узнать дату нажмите - date")
    await update.message.reply_text("По всем вопросам обращаться к @tot_samiy_na_bezdare")


# Функция показывающая время.
async def time_command(update, context):
    temp = datetime.now()
    await update.message.reply_text("Сейчас время - " + str(temp.hour) + ":" + str(temp.minute))


# Функция показывающая дату.
async def date_command(update, context):
    await update.message.reply_text("Сейчас дата -  " + str(date.today()))
# Создаём объект Application.
# Вместо слова "TOKEN" надо разместить полученный от @BotFather токен
application = Application.builder().token("5958500052:AAH_SH7ZLqCEm5Kvos64h7-PZmYiA6WeyCk").build()


# Функция, если пользователь не хочет получать рассылку.
async def stop(update, context):
    con = sqlite3.connect("telegramm_bot.db")
    cur = con.cursor()
    user_id = update.effective_message.chat_id
    cur.execute(f"""UPDATE people SET perm = 'FALSE' WHERE people_id = '{str(user_id)}'""")
    con.commit()
    con.close()
    await update.message.reply_text("К сожалению, вы отказались от моей работы, надеюсь еще увидимся!")
    return ConversationHandler.END

# Фунция где пользователь выбирает по какому интресу ему надо искать новости.
async def interest(update, context):
    global counter
    # Кнопки со всеми типами новостей
    con = sqlite3.connect("telegramm_bot.db")
    cur = con.cursor()
    interesting = update.message.text
    # Словарь где находятся новости как они записаны на сайте.
    spis = {"Все": "news", "VR": "vr", "Анонсы": "announces",
            "Железо": "hardware", "Индустрия": "industry", "Кино и сериалы": "movies",
            "Консоли": "consoles", "Мероприятия": "events", "Мобильные": "mobile",
            "Новости сайта": "site", "Обновления": "updates", "ПК": "pc",
            "Производительность": "performance", "Раздача и скидки": "freebies",
            "Релизы": "releases", "Скриншоты": "screenshots", "Слухи": "rumors",
            "Софт": "software", "Технологии": "tech", "Трейлеры": "trailers"}
    user_id = update.effective_message.chat_id
    context.user_data["interesting"] = spis[interesting]
    query = f"""SELECT people_id FROM people WHERE people_id = '{str(user_id)}'"""
    result = cur.execute(query).fetchall()
    if len(result) == 0:  # Если пользователь новый мы его добавляем в бд с его интересом.
        cur.execute(f"""INSERT INTO people VALUES('{str(user_id)}', 'TRUE',
         '{context.user_data['interesting']}', '0', '0')""")
    else:  # Если пользователь старый, то меням ему только интерес.
        cur.execute(f"""UPDATE people SET interest = '{context.user_data["interesting"]}'
         WHERE people_id = {str(user_id)}""")
    await update.message.reply_text(f"Отлично, теперь я буду оповещать вас о последних новостях в разделе "
                                    f"{interesting}", reply_markup=markup)
    cur.execute(f"""UPDATE people SET perm = 'TRUE'
            WHERE people_id = {str(user_id)}""")
    con.commit()
    con.close() 
    return ConversationHandler.END


async def interest2(update, context):
    await update.message.reply_text("Выберите, по какому интересу я должен отслеживать сайт",
                                    reply_markup=markup_inline)
    return 1


# После регистрации обработчика в приложении
# эти асинхронная функция будет вызываться при получении сообщения
# с типом "текст", т. е. текстовых сообщений.
# Регистрируем обработчик в приложении.)

application.add_handler(CommandHandler("help", help_command))
application.add_handler(CommandHandler("time", time_command))
application.add_handler(CommandHandler("date", date_command))
application.add_handler(CommandHandler("stop", stop))
application.add_handler(CommandHandler("news", news))
application.add_handler(CommandHandler("start", start))
# Состояние внутри диалога.
# Вариант с двумя обработчиками, фильтрующими текстовые сообщения.
conv_handler = ConversationHandler(
    entry_points=[CommandHandler('interests', interest2)],
    states={
        # Функция читает ответ на первый вопрос и задаёт второй.
        1: [MessageHandler(filters.TEXT & ~filters.COMMAND, interest)]
    },

    # Точка прерывания диалога. В данном случае — команда /stop.
    fallbacks=[CommandHandler('stop', stop)]
)


application.add_handler(conv_handler)

#keyboard
reply_keyboard = [["/help"], ["/time"],
                  ["/date"], ["/stop"],
                  ["/interests"]]

markup = ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=False)

items2 = [["Все"], ["VR"], ["Анонсы"],
         ["Железо"], ["Индустрия"], ["Кино и сериалы"],
         ["Консоли"], ["Мероприятия"], ["Мобильные"],
         ["Новости сайта"], ["Обновления"], ["ПК"],
         ["Производительность"], ["Раздача и скидки"], ["Релизы"],
         ["Скриншоты"], ["Слухи"], ["Софт"],
         ["Технологии"], ["Трейлеры"]]

markup_inline = ReplyKeyboardMarkup(items2, one_time_keyboard=True)

# Запускаем приложение.
application.run_polling()
