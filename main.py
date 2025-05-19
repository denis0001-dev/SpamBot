# Imports
import asyncio
import logging
import re
import signal
import sys
import traceback
from typing import Optional

from telegram import Update, MessageOriginUser
from telegram.constants import ParseMode
from telegram.error import BadRequest, Forbidden
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, MessageHandler, filters, CallbackContext
# noinspection PyProtectedMember
from telegram.ext._utils.types import HandlerCallback, CCT, RT
from telegram.helpers import mention_html

from secrets import token, devIds
from utils import generate_long_string, escape

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
FORWARD_WAIT = "forward_wait"


# Utilities
def generate_messages(count: int):
    messages.clear()
    for _ in range(count):
        messages.append(generate_long_string())

def add_handler(command_name: str, function: CommandCallback):
    app.add_handler(CommandHandler(command_name, function))
    handlers[command_name] = function


# Bot commands
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print("/start called")
    await update.effective_message.reply_markdown_v2(
        """
Я *Spam Bot*\\!

Добавьте меня в канал или группу, а потом используйте одну из команд, чтобы начать атаку\\.
Используйте /help\\.
        """
    )

async def help(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
`/userid` \\- получить ID пользователя по пересланному сообщению
`/me` \\- Имя бота
`/creator` \\- Создатель бота
`/rights` \\- получить права бота в указанной группе или канале
`/editname` \\- изменить название группы или канала
`/editdesc` \\- изменить описание группы или канала
`/editpfp` \\- изменить фото профиля группы или канала
"""
    )

async def hack(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
            msgs = int(arguments[2])
        except IndexError: pass
    except IndexError:
        await update.effective_message.reply_markdown_v2("*Пожалуйста, укажите ID чата как аргумент к этой команде\\.*")
        return

    await update.effective_message.reply_markdown_v2("*_Начинаю атаку\\.\\.\\._*")

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
            except Forbidden as e:
                print(e)
                try:
                    sent_message = await update.get_bot().send_message(
                        chat_id=chat_id,
                        text=f"{message}512", parse_mode=ParseMode.MARKDOWN_V2
                    )
                    file.write(f"{sent_message.chat_id} {sent_message.message_id}\n")
                except Forbidden:
                    await update.effective_message.reply_markdown_v2(
                        "*Я не в этой группе или канале, пожалуйста, добавьте меня, чтобы продолжить\\!*"
                    )
                    return
        # noinspection PyUnboundLocalVariable
        if exiting: sys.exit()
        if should_stop:
            should_stop = False
            break
        signal.signal(signal.SIGINT, signal.SIG_DFL)
        await asyncio.sleep(1)  # Задержка между сообщениями в 2 секунды

    await update.effective_message.reply_markdown_v2("*_Атака завершена\\!_*")

async def delete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    arguments = update.effective_message.text.split(" ")
    all = False
    msg_chat_id = update.effective_message.chat_id
    if len(arguments) > 1:
        if arguments[1].lower() == "all":
            all = True
        elif re.search(r"^-?\d+$", arguments[1]):
            msg_chat_id = int(arguments[1])

    deleted = 0
    remaining = []
    with open("messages.txt", "r") as file:
        last_id = -1
        for msg in file.readlines():
            try:
                chat_id = int(msg.split(" ")[0])
                if chat_id == msg_chat_id or all:
                    message_id = int(msg.split(" ")[1])
                    await update.get_bot().delete_message(chat_id=chat_id, message_id=message_id)
                    deleted += 1
                    last_id = message_id
                else:
                    remaining.append(msg)
            except BadRequest as e:
                await update.effective_message.reply_markdown_v2(f"Ошибка при удалении сообщения: {e.message}")
                remaining.append(msg)
                pass
    with open("messages.txt", "w") as file:
        file.writelines(remaining)
    await update.effective_message.reply_markdown_v2(f"*{deleted} сообщений было успешно удалено\\!*")

async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global should_stop
    should_stop = True
    await update.effective_message.reply_markdown_v2(f"*Останавливаюсь\\!*")

async def chatid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.effective_message.reply_markdown_v2(f"{update.effective_message.chat_id}".replace("-", "\\-"))

async def debug(update: Update, context: ContextTypes.DEFAULT_TYPE):
    raise ZeroDivisionError()

async def userid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Устанавливаем состояние ожидания пересланного сообщения
    context.user_data['state'] = FORWARD_WAIT
    await update.message.reply_text("Пожалуйста, перешлите сообщение от нужного пользователя для получения его ID")

async def me(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_markdown_v2("Я @SPAM145226721BOT")

async def creator(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_markdown_v2(
        "Меня создал @denis0001\\_dev, программист, который знает большинство популярных языков программирования\\!"
    )

async def send(update: Update, context: ContextTypes.DEFAULT_TYPE):
    arguments = update.effective_message.text.split(" ")
    if len(arguments) < 2:
        await update.effective_message.reply_markdown_v2("*Пожалуйста, укажите ID чата как аргумент к этой команде\\.*")
        return

    chat_id = arguments[1]
    msgs = 1
    message = None
    if len(arguments) > 2:
        try:
            msgs = int(arguments[2])
            message = " ".join(arguments[3:])
        except ValueError as e:
            print(e)

    if message:
        await context.bot.send_message(chat_id=chat_id, text=message)
        await update.effective_message.reply_text("Сообщение отправлено!")
        return
    context.user_data['send_mode'] = True
    context.user_data['send_target_chat_id'] = chat_id
    context.user_data['send_count'] = msgs

    await update.effective_message.reply_text("Пожалуйста, отправьте сообщение, которое вы хотите переслать/отправить.")

async def rights(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = update.effective_message.text.split()
    if len(args) < 2:
        await update.effective_message.reply_text(
            "Пожалуйста, укажите ID или @username группы/канала как аргумент к этой команде.\nПример: /rights -1001234567890"
        )
        return
    chat_id = args[1]
    bot_id = context.bot.id
    try:
        member = await context.bot.get_chat_member(chat_id, bot_id)
        status = member.status
        rights = []
        if hasattr(member, 'can_change_info') and member.can_change_info:
            rights.append('can_change_info')
        if hasattr(member, 'can_post_messages') and member.can_post_messages:
            rights.append('can_post_messages')
        if hasattr(member, 'can_edit_messages') and member.can_edit_messages:
            rights.append('can_edit_messages')
        if hasattr(member, 'can_delete_messages') and member.can_delete_messages:
            rights.append('can_delete_messages')
        if hasattr(member, 'can_invite_users') and member.can_invite_users:
            rights.append('can_invite_users')
        if hasattr(member, 'can_restrict_members') and member.can_restrict_members:
            rights.append('can_restrict_members')
        if hasattr(member, 'can_pin_messages') and member.can_pin_messages:
            rights.append('can_pin_messages')
        if hasattr(member, 'can_promote_members') and member.can_promote_members:
            rights.append('can_promote_members')
        if hasattr(member, 'can_manage_chat') and member.can_manage_chat:
            rights.append('can_manage_chat')
        if hasattr(member, 'can_manage_video_chats') and member.can_manage_video_chats:
            rights.append('can_manage_video_chats')
        if hasattr(member, 'can_manage_topics') and member.can_manage_topics:
            rights.append('can_manage_topics')
        if hasattr(member, 'can_post_stories') and member.can_post_stories:
            rights.append('can_post_stories')
        if hasattr(member, 'can_edit_stories') and member.can_edit_stories:
            rights.append('can_edit_stories')
        if hasattr(member, 'can_delete_stories') and member.can_delete_stories:
            rights.append('can_delete_stories')
        rights_text = '\n'.join(rights) if rights else 'Нет специальных прав.'
        await update.effective_message.reply_text(
            f"Статус бота в чате: {status}\nПрава:\n{rights_text}"
        )
    except Forbidden:
        await update.effective_message.reply_text(
            "У меня нет доступа к этому чату или меня там нет."
        )
    except BadRequest as e:
        await update.effective_message.reply_text(
            f"Ошибка: {e.message}"
        )
    except Exception as e:
        await update.effective_message.reply_text(
            f"Произошла неизвестная ошибка: {e}"
        )

async def editname(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = update.effective_message.text.split()
    if len(args) < 3:
        await update.effective_message.reply_text(
            "Пожалуйста, укажите ID или @username группы/канала и новое имя.\nПример: /editname -1001234567890 НовоеИмя"
        )
        return
    chat_id = args[1]
    new_title = " ".join(args[2:])
    try:
        await context.bot.set_chat_title(chat_id, new_title)
        await update.effective_message.reply_text(f"Название чата {chat_id} изменено на: {new_title}")
    except Forbidden:
        await update.effective_message.reply_text("У меня нет прав для изменения названия этого чата.")
    except BadRequest as e:
        await update.effective_message.reply_text(f"Ошибка: {e.message}")
    except Exception as e:
        await update.effective_message.reply_text(f"Произошла неизвестная ошибка: {e}")

async def editdesc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = update.effective_message.text.split()
    if len(args) < 3:
        await update.effective_message.reply_text(
            "Пожалуйста, укажите ID или @username группы/канала и новое описание.\nПример: /editdesc -1001234567890 Новое описание группы"
        )
        return
    chat_id = args[1]
    new_desc = " ".join(args[2:])
    try:
        await context.bot.set_chat_description(chat_id, new_desc)
        await update.effective_message.reply_text(f"Описание чата {chat_id} изменено на: {new_desc}")
    except Forbidden:
        await update.effective_message.reply_text("У меня нет прав для изменения описания этого чата.")
    except BadRequest as e:
        await update.effective_message.reply_text(f"Ошибка: {e.message}")
    except Exception as e:
        await update.effective_message.reply_text(f"Произошла неизвестная ошибка: {e}")

async def editpfp(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = update.effective_message.text.split()
    if len(args) < 2:
        await update.effective_message.reply_text(
            "Пожалуйста, укажите ID или @username группы/канала как аргумент к этой команде.\nПример: /editpfp -1001234567890 (в ответ на фото)"
        )
        return
    chat_id = args[1]
    # Check if the message is a reply to a photo
    if not update.message.reply_to_message or not update.message.reply_to_message.photo:
        await update.effective_message.reply_text(
            "Пожалуйста, используйте эту команду в ответ на сообщение с фотографией."
        )
        return
    # Get the largest photo size
    photo = update.message.reply_to_message.photo[-1]
    try:
        file = await context.bot.get_file(photo.file_id)
        file_path = f"/tmp/{photo.file_id}.jpg"
        await file.download_to_drive(file_path)
        with open(file_path, "rb") as img:
            await context.bot.set_chat_photo(chat_id, img)
        await update.effective_message.reply_text(f"Фото профиля чата {chat_id} успешно изменено!")
    except Forbidden:
        await update.effective_message.reply_text("У меня нет прав для изменения фото этого чата.")
    except BadRequest as e:
        await update.effective_message.reply_text(f"Ошибка: {e.message}")
    except Exception as e:
        await update.effective_message.reply_text(f"Произошла неизвестная ошибка: {e}")

# Handlers
async def error(obj: object, context: CallbackContext):
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

    trace = escape("".join(traceback.format_tb(sys.exc_info()[2])))
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
    for dev_id in devIds:
        await context.bot.send_message(dev_id, text, parse_mode=ParseMode.HTML)
    raise

async def handle_forward(update: Update, context: CallbackContext):
    print("handler fired")
    # Проверяем, находится ли пользователь в состоянии ожидания
    if update.effective_message.forward_origin:
        print(context.user_data.get('state'))
        if context.user_data.get('state') == FORWARD_WAIT:
            print(update.message.forward_origin)
            orig: MessageOriginUser | None = update.message.forward_origin
            # Проверяем, что сообщение пересланное
            if orig:
                # Получаем ID оригинального отправителя
                user_id = orig.sender_user.id
                username = orig.sender_user.username

                # Формируем ответное сообщение
                response = f"ID пользователя: {user_id}\n"
                if username:
                    response += f"Имя пользователя: {username}"

                # Отправляем ответ
                await update.message.reply_text(response)
                # Очищаем состояние
                context.user_data.pop('state', None)
            else:
                await update.message.reply_text("Пожалуйста, перешлите именно сообщение от нужного пользователя")
    elif context.user_data.get('send_mode'):
        print("Send mode")
        chat_id = context.user_data.get('send_target_chat_id')
        msgs = context.user_data.get('send_count', 1)
        message = update.effective_message
        print(f"Sending to {chat_id} {msgs} times: {message.text}")

        if not update.effective_user.is_bot:
            for _ in range(msgs):
                if message.text:
                    await context.bot.send_message(chat_id=chat_id, text=message.text)
                elif message.photo:
                    await context.bot.send_photo(chat_id=chat_id, photo=message.photo[-1].file_id, caption=message.caption)
                elif message.document:
                    await context.bot.send_document(chat_id=chat_id, document=message.document.file_id,
                                                    caption=message.caption)
                elif message.sticker:
                    await context.bot.send_sticker(chat_id=chat_id, sticker=message.sticker.file_id)
                elif message.voice:
                    await context.bot.send_voice(chat_id=chat_id, voice=message.voice.file_id, caption=message.caption)
                elif message.audio:
                    await context.bot.send_audio(chat_id=chat_id, audio=message.audio.file_id, caption=message.caption)
                elif message.video:
                    await context.bot.send_video(chat_id=chat_id, video=message.video.file_id, caption=message.caption)
                else:
                    await update.effective_message.reply_text("Тип сообщения не поддерживается.")
                    context.user_data['send_mode'] = False
                    return

            await update.effective_message.reply_text("Сообщение отправлено.")
            context.user_data['send_mode'] = False


async def process_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    for i, cmd in enumerate(handlers):
        if update.effective_message.text.lower().startswith(f"/{cmd.lower()}"):
            await handlers[cmd](update, context)

async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = update.effective_message.text.split()
    if len(args) < 2:
        await update.effective_message.reply_text(
            "Пожалуйста, укажите ID или @username группы/канала как аргумент к этой команде.\nПример: /admin -1001234567890"
        )
        return
    chat_id = args[1]
    user_id = update.effective_user.id
    try:
        # Try to promote the user to admin with basic rights
        await context.bot.promote_chat_member(
            chat_id=chat_id,
            user_id=user_id,
            can_change_info=True,
            can_post_messages=True,
            can_edit_messages=True,
            can_delete_messages=True,
            can_invite_users=True,
            can_restrict_members=True,
            can_pin_messages=True,
            can_promote_members=False
        )
        await update.effective_message.reply_text(
            f"Пользователь {user_id} был назначен администратором в чате {chat_id} (если у меня есть права)."
        )
    except Forbidden:
        await update.effective_message.reply_text(
            "У меня нет прав для назначения администратора в этом чате."
        )
    except BadRequest as e:
        await update.effective_message.reply_text(
            f"Ошибка: {e.message}"
        )
    except Exception as e:
        await update.effective_message.reply_text(
            f"Произошла неизвестная ошибка: {e}"
        )

# Main bot
app = ApplicationBuilder().token(token).build()

# Command handlers
add_handler("hack", hack)
add_handler("start", start)
add_handler("help", help)
add_handler("delete", delete)
add_handler("stop", stop)
add_handler("attack", attack)
add_handler("chatid", chatid)
add_handler("debug", debug)
add_handler("userid", userid)
add_handler("me", me)
add_handler("creator", creator)
add_handler("send", send)
add_handler("admin", admin)
add_handler("rights", rights)
add_handler("editname", editname)
add_handler("editdesc", editdesc)
add_handler("editpfp", editpfp)

# Misc handlers
app.add_handler(MessageHandler(filters.TEXT & filters.COMMAND, process_command))
app.add_handler(MessageHandler(~filters.StatusUpdate.ALL, handle_forward))
app.add_error_handler(error)

app.run_polling()