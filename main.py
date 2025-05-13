# Imports
import asyncio
import logging
import signal
import sys
import traceback

from typing import Optional
from telegram import Update
from telegram.constants import ParseMode
from telegram.error import BadRequest, Forbidden
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters, CallbackContext
# noinspection PyProtectedMember
from telegram.ext._utils.types import HandlerCallback, CCT, RT
from telegram.helpers import mention_html

from secrets import token
from utils import generate_long_string

# Set up logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

# Variables
messages = []
exiting = False
should_stop = False
CommandCallback = HandlerCallback[Update, CCT, RT]
handlers: dict[str, CommandCallback] = {}


# Utilities
def generate_messages(count: int):
    messages.clear()
    for _ in range(count):
        messages.append(generate_long_string())

def add_handler(command_name: str, function: CommandCallback):
    app.add_handler(CommandHandler(command_name, function))
    handlers[command_name] = function

async def process_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    for i, cmd in enumerate(handlers):
        if update.effective_message.text.lower().startswith(f"/{cmd.lower()}"):
            await handlers[cmd](update, context)


# Bot commands
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    print("/start called")
    await update.effective_message.reply_markdown_v2(
        """
Я *Spam Bot*\\!

Добавьте меня в канал или группу, а потом используйте одну из команд, чтобы начать атаку\\.
Используйте /help\\.
        """
    )

async def help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.effective_message.reply_markdown_v2(
"""
*Мои команды*

`/start` \\- запустить бота *\\(только в ЛС\\)*
`/hack` \\- начать атаку *\\(в нужном чате\\)*
`/attack <chat>` \\- атаковать чат по @username или Chat ID
`/delete` \\- удалить все сообщения, связанные с атакой
`/stop` \\- остановить атаку
`/chatid` \\- получить ID текущего чата
`/help` \\- помощь
"""
    )

async def hack(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
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

async def chatid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.effective_message.reply_markdown_v2(f"{update.effective_message.chat_id}".replace("-", "\\-"))

async def debug(update: Update, context: ContextTypes.DEFAULT_TYPE):
    raise ZeroDivisionError()

# Error handler
async def error(obj: object, context: CallbackContext):
    devs = [-1002472077168]
    print(obj)

    update: Optional[Update] = None

    if obj is Update or isinstance(obj, Update):
        # noinspection PyTypeChecker
        update = obj

    if update and update.effective_message:
        await update.effective_message.reply_markdown_v2(
            "Sorry, there was an error\\. Please try again or contact @denis0001\\_dev for support\\."
        )

    print(sys.exc_info()[0].__name__)

    trace = "".join(traceback.format_tb(sys.exc_info()[2]))
    payload = []

    if update and update.effective_user:
        bad_user = mention_html(update.effective_user.id, update.effective_user.first_name)
        payload.append(f' с пользователем {bad_user}')
    if update and update.effective_chat:
        payload.append(f' внутри чата <i>{update.effective_chat.title}</i>')
        if update.effective_chat.username:
            payload.append(f' (@{update.effective_chat.username})')
    if update and update.poll:
        payload.append(f' с id опроса {update.poll.id}.')
    text = f"Ошибка <code>{sys.exc_info()[0].__name__}</code> случилась{''.join(payload)}. " \
           f"Полная трассировка:\n\n<code>{trace}</code>"
    print(text)
    for dev_id in devs:
        await context.bot.send_message(dev_id, text, parse_mode=ParseMode.HTML)
    raise

app = ApplicationBuilder().token(token).build()

add_handler("hack", hack)
add_handler("start", start)
add_handler("help", help)
add_handler("delete", delete)
add_handler("stop", stop)
add_handler("attack", attack)
add_handler("chatid", chatid)
add_handler("debug", debug)

app.add_handler(MessageHandler(filters.TEXT & filters.COMMAND, process_command))
app.add_error_handler(error)

app.run_polling()