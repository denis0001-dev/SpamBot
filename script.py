import asyncio
import random
import signal
import string
import sys

from telegram import Update
from telegram.constants import ParseMode
from telegram.error import BadRequest, Forbidden
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters
# noinspection PyProtectedMember
from telegram.ext._utils.types import HandlerCallback, CCT, RT

messages = []
exiting = False
should_stop = False

def generate_long_string(length=1000):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

def generate_messages(count: int):
    messages.clear()
    for _ in range(count):
        messages.append(generate_long_string())

# Функция для отправки сообщений с задержкой
# noinspection PyUnusedLocal
async def send_messages(update, context):
    global should_stop

    generate_messages(10)
    for message in messages:
        def ignore_interrupt(_, __):
            global exiting
            exiting = True
            print("Interrupt received, exiting...")

        signal.signal(signal.SIGINT, ignore_interrupt)
        with open("messages.txt", "a") as file:
            sent_message = await update.effective_message.reply_text(f"{message}512")
            file.write(f"{sent_message.chat_id} {sent_message.message_id}\n")
        # noinspection PyUnboundLocalVariable
        if exiting: sys.exit()
        if should_stop:
            should_stop = False
            break
        signal.signal(signal.SIGINT, signal.SIG_DFL)
        await asyncio.sleep(1)  # Задержка между сообщениями в 2 секунды

# Обработчик команды hack
async def hack(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await send_messages(update, context)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    print("/start called")
    await update.effective_message.reply_markdown_v2(
        "\n".join([
            "Я *Spam Bot*\\!",
            "",
            "Добавьте меня в канал или группу, а потом используйте одну из команд, чтобы начать атаку\\.",
            "Используйте /help\\."
        ])
    )

async def help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.effective_message.reply_markdown_v2(
        "\n".join([
            "*Мои команды*",
            "",
            "`/start` \\- запустить бота *\\(только в ЛС\\)*",
            "`/hack` \\- начать атаку *\\(в нужном чате\\)*",
            "`/attack <chat>` \\- атаковать чат по @username или Chat ID",
            "`/delete` \\- удалить все сообщения, связанные с атакой",
            "`/stop` \\- остановить атаку",
            "`/chatid` \\- получить ID текущего чата",
            "`/help` \\- помощь"
        ])
    )

CommandCallback = HandlerCallback[Update, CCT, RT]

handlers: dict[str, CommandCallback] = {}

def add_handler(command_name: str, function: CommandCallback):
    app.add_handler(CommandHandler(command_name, function))
    handlers[command_name] = function

# Обработчик простого сообщения "хак"
async def process_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    for i, cmd in enumerate(handlers):
        if update.effective_message.text.lower().startswith(f"/{cmd.lower()}"):
            await handlers[cmd](update, context)

async def delete(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    deleted = 0
    with open("messages.txt", "r") as file:
        last_id = -1
        for msg in file.readlines():
            try:
                chat_id = int(msg.split(" ")[0])
                if chat_id == update.effective_message.chat_id:
                    message_id = int(msg.split(" ")[1])
                    await update.get_bot().delete_message(chat_id=chat_id, message_id=message_id)
                    deleted += 1
                    last_id = message_id
            except BadRequest: pass
    with open("messages.txt", "w") as file:
        file.write("")
    await update.effective_message.reply_markdown_v2(f"*{deleted} messages were successfully deleted\\!*")

async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    global should_stop
    print("stopping!!!")
    should_stop = True
    await update.effective_message.reply_markdown_v2(f"*Stopping\\!*")

# Функция для отправки сообщений с задержкой
# noinspection PyUnusedLocal
async def attack(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global should_stop

    arguments = update.effective_message.text.split(" ")
    chat_id = "-1"
    msgs = 10
    try:
        chat_id = arguments[1]
        try:
            msgs = arguments[2]
        except IndexError: pass
    except IndexError:
        await update.effective_message.reply_markdown_v2("*Please provide the Chat ID as an argument to this command\\.*")
        return

    await update.effective_message.reply_markdown_v2("*_Starting attack\\.\\.\\._*")

    generate_messages(msgs)
    for message in messages:
        def ignore_interrupt(_, __):
            global exiting
            exiting = True
            print("Interrupt received, exiting...")

        signal.signal(signal.SIGINT, ignore_interrupt)
        with open("messages.txt", "a") as file:
            try:
                sent_message = await (await update.get_bot().get_chat(chat_id)).send_message(
                    f"{message}512", parse_mode=ParseMode.MARKDOWN_V2
                )
                file.write(f"{sent_message.chat_id} {sent_message.message_id}\n")
            except Forbidden:
                await update.effective_message.reply_markdown_v2("*I'm not in this group or channel, please add me to continue\\!*")
                return
        # noinspection PyUnboundLocalVariable
        if exiting: sys.exit()
        if should_stop:
            should_stop = False
            break
        signal.signal(signal.SIGINT, signal.SIG_DFL)
        await asyncio.sleep(1)  # Задержка между сообщениями в 2 секунды

    await update.effective_message.reply_markdown_v2("*_Attack complete\\!_*")

async def chatid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.effective_message.reply_markdown_v2(f"{update.effective_message.chat_id}".replace("-", "\\-"))

# Основной код бота
app = ApplicationBuilder().token("7679458537:AAFfZYDUDRmeZjniAIL7a1p8BNW-0xdzH4k").build()

add_handler("hack", hack)
add_handler("start", start)
add_handler("help", help)
add_handler("delete", delete)
add_handler("stop", stop)
add_handler("attack", attack)
add_handler("chatid", chatid)

app.add_handler(MessageHandler(filters.TEXT & filters.COMMAND, process_command))

app.run_polling()