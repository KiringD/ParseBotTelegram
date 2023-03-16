import json
from datetime import datetime

from aiogram import types, Bot
from aiogram.bot.api import TelegramAPIServer
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, MediaGroup, InputMediaPhoto, InputMediaVideo, \
    InputFile, InputMediaDocument, ReplyKeyboardMarkup, ReplyKeyboardRemove

from .main import start_menu, Form
from ...database.methods import table_execute
from ...misc import telegramcalendar, TgKeys, ConfigKeys
from ...misc.util import new_post, edit_saved_post, delete_conf_post, send_message_bot_chat

calendar_temp = {}
calendar_editing_temp = {}
calendar_editing_media_temp = {}
users_calendar_script_temp = {}
posts_set_date_temp = {}
posts_set_time_temp = {}
users_saved_post_editing_temp = {}

local_server = TelegramAPIServer.from_base(f'http://{ConfigKeys.telegram_host}:{ConfigKeys.telegram_port}')

bot = Bot(token=TgKeys.TOKEN, server=local_server, parse_mode='HTML')

# @dp.message_handler(lambda message: message.text.lower() == "вернуться", state="CALENDAR_STATE")
async def process_calendar_script_back_command(message: types.Message):
    await start_menu(message=message)
    try:
        calendar_temp.pop(message.from_user.id)
    except Exception:
        pass

# @dp.message_handler(state="CALENDAR_STATE")
async def process_calendar_script_command(message: types.Message):
    user_saved_posts = json.loads((await table_execute(f"SELECT SAVED_POSTS FROM USERS WHERE USER_ID = {message.from_user.id}",is_return=True))[0])
    if message.text.lower() in user_saved_posts.keys():
        markup = await telegramcalendar.create_calendar(posts_info=user_saved_posts[message.text.lower()])
        users_calendar_script_temp[message.from_user.id] = user_saved_posts[message.text.lower()]
        await message.answer(f"Календарь публикаций для сценария - {message.text.lower()}", reply_markup=markup)
    else:
        await message.answer("Для данного сценария нет запланированных публикаций")
    await Form.CALENDAR_STATE.set()

# @dp.callback_query_handler(state="CALENDAR_STATE")
async def callback_calendar(callback_query: types.CallbackQuery):
    print(callback_query.data)
    await bot.answer_callback_query(callback_query.id)

    (kind, _, _, _, _) = await telegramcalendar.separate_callback_data(callback_query.data)
    if kind == telegramcalendar.CALENDAR_CALLBACK:
        await inline_calendar_handler(callback_query)
#todo
async def inline_calendar_handler(callback_query: types.CallbackQuery):
    user_saved_posts = json.loads((await table_execute(f"SELECT SAVED_POSTS FROM USERS WHERE USER_ID = {callback_query.from_user.id}",is_return=True))[0])
    scripts_settings = json.loads((await table_execute(
        f"SELECT SCRIPTS_SETTINGS FROM USERS WHERE USER_ID = {callback_query.from_user.id}", is_return=True))[0])
    posts_info = users_calendar_script_temp[callback_query.from_user.id]
    selected,date = await telegramcalendar.process_calendar_selection(bot, callback_query, posts_info=posts_info)
    if selected:
        if date == "DENY":
            users_calendar_script_temp.pop(callback_query.from_user.id)
            await bot.delete_message(chat_id=callback_query.from_user.id,
                                        message_id=callback_query.message.message_id)
            return 0
        no_posts = True
        for key in user_saved_posts.keys():
            if user_saved_posts[key] == posts_info:
                channel_to_post = key
        for post in posts_info:
            if post['date_post'] == str(date):
                inline_markup = InlineKeyboardMarkup().row(
                    InlineKeyboardButton('Удалить',
                                         callback_data=f"delete {post['source']} {post['message_id']}"),
                    InlineKeyboardButton('Опубликовать',
                                         callback_data=f"post {post['source']} {post['message_id']}")).row(
                    InlineKeyboardButton('Специальные настройки',
                                         callback_data=f"set {post['source']} {post['message_id']}"),
                    InlineKeyboardButton('Редактировать',
                                         callback_data=f"edit {post['source']} {post['message_id']}")).row(
                    InlineKeyboardButton('Изменить дату публикации',
                                         callback_data=f"date {post['source']} {post['message_id']}"),
                    InlineKeyboardButton('Изменить время',
                                         callback_data=f"time {post['source']} {post['message_id']}"))

                calendar_temp[callback_query.from_user.id] = channel_to_post

                raw_text = post['raw_text']
                settings = post['settings']

                custom_author = settings.get('author', None)

                if custom_author is not None:
                    if custom_author:
                        raw_text += f"\n\nИсточник: {post['source']}"
                else:
                    if scripts_settings[channel_to_post]["author"]:
                        raw_text += f"\n\nИсточник: {post['source']}"

                await bot.send_message(chat_id=callback_query.from_user.id, text=f'Публикация от {post["source"]} в {channel_to_post}:')
                await send_message_bot_chat(source=post["source"], media=post["media"],
                                            raw_text=raw_text, chat_id=callback_query.from_user.id)
                await bot.send_message(chat_id=callback_query.from_user.id,
                                       text=f"*Публикация назначена на {post['date_post']} в {post['time_post']}*\nВыберите опцию",
                                       reply_markup=inline_markup, parse_mode="Markdown")

                no_posts = False
        if no_posts:
            users_calendar_script_temp.pop(callback_query.from_user.id)
            await bot.send_message(chat_id=callback_query.from_user.id, text="На этот день у вас нет запланированных публикаций по этому сценарию")
            return 0
        await bot.delete_message(chat_id=callback_query.from_user.id, message_id=callback_query.message.message_id)
        users_calendar_script_temp.pop(callback_query.from_user.id)
        await Form.CALENDAR_DAY_STATE.set()


# calendar day state

# @dp.callback_query_handler(lambda c: c.data.startswith("set"), state="CALENDAR_DAY_STATE")
async def callback_calendar_settings_post(callback_query: types.CallbackQuery):
    await bot.answer_callback_query(callback_query.id)
    try:
        channel_message_id = int(callback_query.data.split()[2])
    except ValueError:
        channel_message_id = callback_query.data.split()[2]
    channel_source = callback_query.data.split()[1]
    channel_to_post = calendar_temp[callback_query.from_user.id]

    settings = (await edit_saved_post(user_id=callback_query.from_user.id, prev_channel_source=channel_source,
                                      prev_message_id=channel_message_id, channel_to_post=channel_to_post,
                                      type='none', to_return=["settings"]))['settings']

    script_settings = json.loads((await table_execute(
        f"SELECT SCRIPTS_SETTINGS FROM USERS WHERE USER_ID = {callback_query.from_user.id}", is_return=True))[0])
    global_author = "ON" if script_settings[channel_to_post]['author'] else "OFF"
    author = settings.get('author', None)
    if author is None:
        inline_markup = InlineKeyboardMarkup().add(
            InlineKeyboardButton(f"Указание авторства - ПО УМОЛЧАНИЮ ({global_author})", callback_data=f"author {channel_source} {channel_message_id}")).add(
            InlineKeyboardButton("Вернуться", callback_data=f"back {channel_source} {channel_message_id}"))
    else:
        if author:
            inline_markup = InlineKeyboardMarkup().add(
                InlineKeyboardButton("Указание авторства - ON", callback_data=f"author {channel_source} {channel_message_id}")).add(
                InlineKeyboardButton("Вернуться", callback_data=f"back {channel_source} {channel_message_id}"))
        else:
            inline_markup = InlineKeyboardMarkup().add(
                InlineKeyboardButton("Указание авторства - OFF", callback_data=f"author {channel_source} {channel_message_id}")).add(
                InlineKeyboardButton("Вернуться", callback_data=f"back {channel_source} {channel_message_id}"))

    await callback_query.message.edit_text(text="Специальные настройки для этой публикации", reply_markup=inline_markup)

# @dp.callback_query_handler(lambda c: c.data.startswith("author"), state="CALENDAR_DAY_STATE")
async def callback_calendar_settings_author_post(callback_query: types.CallbackQuery):
    await bot.answer_callback_query(callback_query.id)

    try:
        channel_message_id = int(callback_query.data.split()[2])
    except ValueError:
        channel_message_id = callback_query.data.split()[2]

    channel_source = callback_query.data.split()[1]
    channel_to_post = calendar_temp[callback_query.from_user.id]

    return_dict = await edit_saved_post(user_id=callback_query.from_user.id, prev_channel_source=channel_source,
                                      prev_message_id=channel_message_id, channel_to_post=channel_to_post,
                                      type='none', to_return=["settings","raw_text", "media"])
    settings = return_dict['settings']
    raw_text = return_dict['raw_text']
    media = return_dict['media']
    script_settings = json.loads((await table_execute(
        f"SELECT SCRIPTS_SETTINGS FROM USERS WHERE USER_ID = {callback_query.from_user.id}", is_return=True))[0])
    global_author = "ON" if script_settings[channel_to_post]['author'] else "OFF"
    author = settings.get('author', None)
    message_id_offset = 0
    if len(media.keys()) == 2:
        is_media = False
        message_id_offset += 1
    else:
        if isinstance(media, dict):
            if 'photo' in media.keys():
                for photo in media['photo']:
                    message_id_offset += 1
            if 'video' in media.keys():
                for video in media['video']:
                    message_id_offset += 1
            if 'doc' in media.keys():
                for doc in media['doc']:
                    message_id_offset += 1
        is_media = True

    if author is None:
        settings['author'] = True
        if global_author == "OFF":
            if is_media:
                print(message_id_offset)
                await bot.edit_message_caption(chat_id=callback_query.from_user.id,
                                               message_id=callback_query.message.message_id - message_id_offset,
                                               caption=raw_text + f"\n\nИсточник: {channel_source}")
            else:
                await bot.edit_message_text(text=raw_text + f"\n\nИсточник: {channel_source}",
                                            chat_id=callback_query.from_user.id,
                                            message_id=callback_query.message.message_id-1)
        inline_markup = InlineKeyboardMarkup().add(
            InlineKeyboardButton(f"Указание авторства - ON",
                                 callback_data=f"author {channel_source} {channel_message_id}")).add(
            InlineKeyboardButton("Вернуться", callback_data=f"back {channel_source} {channel_message_id}"))
    else:
        if author:
            settings['author'] = False
            if is_media:
                await bot.edit_message_caption(chat_id=callback_query.from_user.id,
                                               message_id=callback_query.message.message_id - message_id_offset,
                                               caption=raw_text)
            else:
                await bot.edit_message_text(text=raw_text,
                                            chat_id=callback_query.from_user.id,
                                            message_id=callback_query.message.message_id - 1)
            inline_markup = InlineKeyboardMarkup().add(
                InlineKeyboardButton("Указание авторства - OFF", callback_data=f"author {channel_source} {channel_message_id}")).add(
                InlineKeyboardButton("Вернуться", callback_data=f"back {channel_source} {channel_message_id}"))
        else:
            settings.pop('author')
            if global_author == "ON":
                if is_media:
                    await bot.edit_message_caption(chat_id=callback_query.from_user.id,
                                                   message_id=callback_query.message.message_id - message_id_offset,
                                                   caption=raw_text + f"\n\nИсточник: {channel_source}")
                else:
                    await bot.edit_message_text(text=raw_text + f"\n\nИсточник: {channel_source}",
                                                chat_id=callback_query.from_user.id,
                                                message_id=callback_query.message.message_id - 1)
            inline_markup = InlineKeyboardMarkup().add(
                InlineKeyboardButton(f"Указание авторства - ПО УМОЛЧАНИЮ ({global_author})",
                                     callback_data=f"author {channel_source} {channel_message_id}")).add(
                InlineKeyboardButton("Вернуться", callback_data=f"back {channel_source} {channel_message_id}"))
    await edit_saved_post(user_id=callback_query.from_user.id, prev_channel_source=channel_source,
                          prev_message_id=channel_message_id, channel_to_post=channel_to_post,
                          type='edit', settings=settings)
    await callback_query.message.edit_text(text="Специальные настройки для этой публикации", reply_markup=inline_markup)

# @dp.callback_query_handler(lambda c: c.data.startswith("back"), state="CALENDAR_DAY_STATE")
async def callback_calendar_settings_back_post(callback_query: types.CallbackQuery):
    await bot.answer_callback_query(callback_query.id)

    try:
        channel_message_id = int(callback_query.data.split()[2])
    except ValueError:
        channel_message_id = callback_query.data.split()[2]

    channel_source = callback_query.data.split()[1]

    inline_markup = InlineKeyboardMarkup().row(
        InlineKeyboardButton('Удалить',
                             callback_data=f"delete {channel_source} {channel_message_id}"),
        InlineKeyboardButton('Опубликовать',
                             callback_data=f"post {channel_source} {channel_message_id}")).row(
        InlineKeyboardButton('Специальные настройки',
                             callback_data=f"set {channel_source} {channel_message_id}"),
        InlineKeyboardButton('Редактировать',
                             callback_data=f"edit {channel_source} {channel_message_id}")).row(
        InlineKeyboardButton('Изменить дату публикации',
                             callback_data=f"date {channel_source} {channel_message_id}"),
        InlineKeyboardButton('Изменить время',
                             callback_data=f"time {channel_source} {channel_message_id}"))

    await callback_query.message.edit_text(text="Выберите опцию", reply_markup=inline_markup)

async def callback_calendar_set_time_post(callback_query: types.CallbackQuery):
    await bot.answer_callback_query(callback_query.id)
    try:
        channel_message_id = int(callback_query.data.split()[2])
    except ValueError:
        channel_message_id = callback_query.data.split()[2]
    channel_source = callback_query.data.split()[1]
    channel_to_post = calendar_temp[callback_query.from_user.id]

    user_saved_posts = json.loads((await table_execute(
        f"SELECT SAVED_POSTS FROM USERS WHERE USER_ID = {callback_query.from_user.id}", is_return=True))[0])
    if channel_to_post in user_saved_posts.keys():
        for post in user_saved_posts[channel_to_post]:
            if post['source'] == channel_source and post['message_id'] == channel_message_id:
                date_post = post['date_post']
                time_post = post['time_post']

    posts_set_time_temp[callback_query.from_user.id] = [channel_to_post, channel_source, channel_message_id]

    keyboard = []
    row=[]
    current_datetime = datetime.now()
    current_date = current_datetime.strftime('%Y-%m-%d')
    for i in range(1,25):
        if date_post == current_date and i-1 < current_datetime.hour:
            row.append(InlineKeyboardButton("☓", callback_data=f"hour ☓ {date_post} {time_post}"))
        else:
            if i-1 < 10:
                row.append(InlineKeyboardButton(f"0{i-1}", callback_data=f"hour 0{i-1} {date_post} {time_post}"))
            else:
                row.append(InlineKeyboardButton(f"{i-1}", callback_data=f"hour {i-1} {date_post} {time_post}"))
        if i % 6 == 0:
            keyboard.append(row)
            row = []
    keyboard.append([InlineKeyboardButton("Отмена", callback_data=f"hour DENY {date_post} {time_post}")])
    inline_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)


    await bot.edit_message_text(chat_id=callback_query.from_user.id, message_id=callback_query.message.message_id, text=f"*Дата публикации этой записи* - {date_post} в {time_post}\nВыберете час в который вы хотите опубликовать этот пост:",
                               reply_markup=inline_markup, parse_mode="Markdown")

    await Form.CALENDAR_POSTS_SET_TIME_STATE.set()

async def callback_calendar_set_date_post(callback_query: types.CallbackQuery):
    await bot.answer_callback_query(callback_query.id)
    try:
        channel_message_id = int(callback_query.data.split()[2])
    except ValueError:
        channel_message_id = callback_query.data.split()[2]
    channel_source = callback_query.data.split()[1]
    channel_to_post = calendar_temp[callback_query.from_user.id]

    user_saved_posts = json.loads(
        (await table_execute(f"SELECT SAVED_POSTS FROM USERS WHERE USER_ID = {callback_query.from_user.id}", is_return=True))[0])

    if channel_to_post in user_saved_posts.keys():
        for post in user_saved_posts[channel_to_post]:
            if post['source'] == channel_source and post['message_id'] == channel_message_id:
                date_post = post['date_post']


    posts_set_date_temp[callback_query.from_user.id] = [channel_to_post, channel_source, channel_message_id, date_post, user_saved_posts[channel_to_post.lower()]]
    inline_markup = await telegramcalendar.create_calendar(posts_info=user_saved_posts[channel_to_post.lower()], remove_day=(int(date_post.split('-')[0]), int(date_post.split('-')[1]), int(date_post.split('-')[2])))
    await bot.edit_message_text(chat_id=callback_query.from_user.id, message_id=callback_query.message.message_id,
                                text="Выберите необходимую дату публикации", reply_markup=inline_markup)
    await Form.CALENDAR_POSTS_SET_DATE_STATE.set()

async def callback_calendar_delete_post(callback_query: types.CallbackQuery):
    await bot.answer_callback_query(callback_query.id)
    try:
        channel_message_id = int(callback_query.data.split()[2])
    except ValueError:
        channel_message_id = callback_query.data.split()[2]
    channel_source = callback_query.data.split()[1]
    channel_to_post = calendar_temp[callback_query.from_user.id]

    media = (await edit_saved_post(user_id=callback_query.from_user.id, prev_channel_source=channel_source,
                            prev_message_id=channel_message_id, channel_to_post=channel_to_post,
                            type="remove", to_return=['media']))['media']
    await delete_conf_post(message=callback_query, channel_source=channel_source, media=media)

# @dp.callback_query_handler(lambda c: c.data and "post" in c.data, state="CALENDAR_DAY_STATE")
async def callback_calendar_to_post_post(callback_query: types.CallbackQuery):
    await bot.answer_callback_query(callback_query.id)
    try:
        channel_message_id = int(callback_query.data.split()[2])
    except ValueError:
        channel_message_id = callback_query.data.split()[2]
    channel_to_post = calendar_temp[callback_query.from_user.id]
    channel_source = callback_query.data.split()[1]

    return_list = await edit_saved_post(user_id=callback_query.from_user.id, prev_channel_source=channel_source,
                                  prev_message_id=channel_message_id, channel_to_post=channel_to_post,
                                  type="remove", to_return=["media", "raw_text", "settings"])

    media = return_list['media']
    raw_text = return_list['raw_text']
    settings = return_list['settings']

    await new_post(user_id=callback_query.from_user.id, source=channel_source, channel_to_post=channel_to_post, media=media, raw_text=raw_text,
                   message_id=channel_message_id, settings=settings)
    await delete_conf_post(message=callback_query, channel_source=channel_source, media=media)

# @dp.callback_query_handler(lambda c: c.data.startswith("edit"), state="CALENDAR_DAY_STATE")
async def callback_calendar_edit_post(callback_query: types.CallbackQuery):
    await bot.answer_callback_query(callback_query.id)

    try:
        channel_message_id = int(callback_query.data.split()[2])
    except ValueError:
        channel_message_id = callback_query.data.split()[2]
    channel_source = callback_query.data.split()[1]
    channel_to_post = calendar_temp[callback_query.from_user.id]

    inline_markup = InlineKeyboardMarkup().row(
        InlineKeyboardButton("Удалить медиа", callback_data=f"del m {channel_source} {channel_message_id}"),
        InlineKeyboardButton("Удалить текст", callback_data=f"del t {channel_source} {channel_message_id}")).row(
        InlineKeyboardButton("Изменить текст", callback_data=f"ed t {channel_source} {channel_message_id}"),
        InlineKeyboardButton("Добавить медиа", callback_data=f"ed m {channel_source} {channel_message_id}")).row(
        InlineKeyboardButton("Вернуться", callback_data=f"return {channel_source} {channel_message_id}"))

    return_dict = await edit_saved_post(user_id=callback_query.from_user.id, prev_channel_source=channel_source,
                                        prev_message_id=channel_message_id, channel_to_post=channel_to_post,
                                        type="none", to_return=["media", "source", "raw_text"])

    media = return_dict['media']
    source = return_dict['source']
    raw_text = return_dict['raw_text']

    await delete_conf_post(message=callback_query, channel_source=channel_source, media=media)

    await callback_query.message.answer(f'*Редактируемая публикация*:', parse_mode="Markdown")
    await send_message_bot_chat(source=source, media=media, raw_text=raw_text, chat_id=callback_query.from_user.id)
    await callback_query.message.answer(text="Выберите опцию", reply_markup=inline_markup)
    await Form.CALENDAR_EDITING_STATE.set()

# Calendar editing state

# @dp.callback_query_handler(lambda c: c.data and "return" in c.data, state="CALENDAR_EDITING_STATE")
async def callback_calendar_edit_return(callback_query: types.CallbackQuery):
    await bot.answer_callback_query(callback_query.id)

    try:
        channel_message_id = int(callback_query.data.split()[2])
    except ValueError:
        channel_message_id = callback_query.data.split()[2]
    channel_source = callback_query.data.split()[1]
    channel_to_post = calendar_temp[callback_query.from_user.id]

    inline_markup = InlineKeyboardMarkup().row(
        InlineKeyboardButton('Удалить',
                             callback_data=f"delete {channel_source} {channel_message_id}"),
        InlineKeyboardButton('Опубликовать',
                             callback_data=f"post {channel_source} {channel_message_id}")).row(
        InlineKeyboardButton('Специальные настройки',
                             callback_data=f"set {channel_source} {channel_message_id}"),
        InlineKeyboardButton('Редактировать',
                             callback_data=f"edit {channel_source} {channel_message_id}")).row(
        InlineKeyboardButton('Изменить дату публикации',
                             callback_data=f"date {channel_source} {channel_message_id}"),
        InlineKeyboardButton('Изменить время',
                             callback_data=f"time {channel_source} {channel_message_id}"))

    media = (await edit_saved_post(user_id=callback_query.from_user.id, prev_channel_source=channel_source,
                          prev_message_id=channel_message_id, channel_to_post=channel_to_post,
                          type="none", to_return=["media"]))['media']
    message_id_offset = 1
    if len(media.keys()) == 2:
        message_id_offset += 1
    else:
        if isinstance(media, dict):
            if 'photo' in media.keys():
                for photo in media['photo']:
                    message_id_offset += 1
            if 'video' in media.keys():
                for video in media['video']:
                    message_id_offset += 1
            if 'doc' in media.keys():
                for doc in media['doc']:
                    message_id_offset += 1
    await bot.edit_message_text(chat_id=callback_query.from_user.id, message_id=callback_query.message.message_id-message_id_offset,
                                text=f'Публикация от {channel_source} в {channel_to_post}:')
    await callback_query.message.edit_reply_markup(reply_markup=inline_markup)
    await Form.CALENDAR_DAY_STATE.set()

# @dp.callback_query_handler(lambda c: c.data and "del t" in c.data, state="CALENDAR_EDITING_STATE")
async def callback_calendar_edit_del_text(callback_query: types.CallbackQuery):
    await bot.answer_callback_query(callback_query.id)

    try:
        channel_message_id = int(callback_query.data.split()[3])
    except ValueError:
        channel_message_id = callback_query.data.split()[3]
    channel_source = callback_query.data.split()[2]
    channel_to_post = calendar_temp[callback_query.from_user.id]

    return_dict = await edit_saved_post(user_id=callback_query.from_user.id, prev_channel_source=channel_source,
                          prev_message_id=channel_message_id, channel_to_post=channel_to_post,
                          type="none", to_return=["media", "raw_text"])

    media = return_dict['media']
    raw_text = return_dict['raw_text']

    message_id_offset = 0
    if len(media.keys()) == 2:
        is_media = False
        message_id_offset += 1
    else:
        if isinstance(media, dict):
            if 'photo' in media.keys():
                for photo in media['photo']:
                    message_id_offset += 1
            if 'video' in media.keys():
                for video in media['video']:
                    message_id_offset += 1
            if 'doc' in media.keys():
                for doc in media['doc']:
                    message_id_offset += 1
        is_media = True

    # print(is_media)
    if raw_text != "" and is_media:
        if is_media:
            await bot.edit_message_caption(chat_id=callback_query.from_user.id,
                                           message_id=callback_query.message.message_id-message_id_offset,
                                           caption="")
        else:
            await bot.edit_message_text(chat_id=callback_query.from_user.id,
                                        message_id=callback_query.message.message_id - message_id_offset,
                                        text="")
        await edit_saved_post(user_id=callback_query.from_user.id, prev_channel_source=channel_source,
                              prev_message_id=channel_message_id, channel_to_post=channel_to_post,
                              type="edit", raw_text="")

# @dp.callback_query_handler(lambda c: c.data and "del m" in c.data, state="CALENDAR_EDITING_STATE")
async def callback_calendar_edit_del_media(callback_query: types.CallbackQuery):
    await bot.answer_callback_query(callback_query.id)

    try:
        channel_message_id = int(callback_query.data.split()[3])
    except ValueError:
        channel_message_id = callback_query.data.split()[3]
    channel_source = callback_query.data.split()[2]
    channel_to_post = calendar_temp[callback_query.from_user.id]

    return_dict = await edit_saved_post(user_id=callback_query.from_user.id, prev_channel_source=channel_source,
                                        prev_message_id=channel_message_id, channel_to_post=channel_to_post,
                                        type="none", to_return=["media"])
    media = return_dict['media']
    inline_markup = InlineKeyboardMarkup()
    if 'photo' in media.keys() or 'video' in media.keys() or 'doc' in media.keys():
        if 'photo' in media.keys():
            photo_counter = 0
            for photo in media['photo']:
                inline_markup.row(InlineKeyboardButton(f"Удалить фото №{photo_counter+1}",
                                                       callback_data=f"rm p {photo_counter} {channel_source} {channel_message_id}"))
                photo_counter += 1
        if 'video' in media.keys():
            video_counter = 0
            for video in media['video']:
                inline_markup.row(InlineKeyboardButton(f"Удалить видео №{video_counter+1}",
                                                       callback_data=f"rm v {video_counter} {channel_source} {channel_message_id}"))
                video_counter += 1
        if 'doc' in media.keys():
            doc_counter = 0
            for doc in media['doc']:
                inline_markup.row(InlineKeyboardButton(f"Удалить документ №{doc_counter+1}",
                                                       callback_data=f"rm d {doc_counter} {channel_source} {channel_message_id}"))
                doc_counter += 1

        inline_markup.row(InlineKeyboardButton("Вернуться", callback_data=f"back {channel_source} {channel_message_id}"))

        await bot.edit_message_text(chat_id=callback_query.from_user.id, message_id=callback_query.message.message_id,
                                    text="Выберете какое медиа удалить", reply_markup=inline_markup)


# @dp.callback_query_handler(lambda c: c.data and "back" in c.data, state="CALENDAR_EDITING_STATE")
async def callback_calendar_edit_back(callback_query: types.CallbackQuery):
    await bot.answer_callback_query(callback_query.id)

    try:
        channel_message_id = int(callback_query.data.split()[2])
    except ValueError:
        channel_message_id = callback_query.data.split()[2]
    channel_source = callback_query.data.split()[1]

    inline_markup = InlineKeyboardMarkup().row(
        InlineKeyboardButton("Удалить медиа", callback_data=f"del m {channel_source} {channel_message_id}"),
        InlineKeyboardButton("Удалить текст", callback_data=f"del t {channel_source} {channel_message_id}")).row(
        InlineKeyboardButton("Изменить текст", callback_data=f"ed t {channel_source} {channel_message_id}"),
        InlineKeyboardButton("Добавить медиа", callback_data=f"ed m {channel_source} {channel_message_id}")).row(
        InlineKeyboardButton("Вернуться", callback_data=f"return {channel_source} {channel_message_id}"))

    await bot.edit_message_text(chat_id=callback_query.from_user.id, message_id=callback_query.message.message_id,
                                text="Выберите опцию", reply_markup=inline_markup)

# @dp.callback_query_handler(lambda c: c.data and "rm" in c.data, state="CALENDAR_EDITING_STATE")
async def callback_calendar_edit_del_media_rm(callback_query: types.CallbackQuery):
    await bot.answer_callback_query(callback_query.id)

    try:
        channel_message_id = int(callback_query.data.split()[4])
    except ValueError:
        channel_message_id = callback_query.data.split()[4]
    channel_source = callback_query.data.split()[3]
    channel_to_post = calendar_temp[callback_query.from_user.id]
    index_to_remove = int(callback_query.data.split()[2])

    media_type = None
    if callback_query.data.split()[1] == "p":
        media_type = "photo"
    elif callback_query.data.split()[1] == "v":
        media_type = "video"
    elif callback_query.data.split()[1] == "d":
        media_type = "doc"

    return_dict = await edit_saved_post(user_id=callback_query.from_user.id, prev_channel_source=channel_source,
                                        prev_message_id=channel_message_id, channel_to_post=channel_to_post,
                                        type="none", to_return=["media", "source", "raw_text"])
    media = return_dict['media']
    source = return_dict['source']
    raw_text = return_dict['raw_text']

    await delete_conf_post(message=callback_query, channel_source=channel_source, media=media)

    media[media_type].pop(index_to_remove)
    if len(media[media_type]) == 0:
        media.pop(media_type)

    inline_markup = InlineKeyboardMarkup()
    photo_counter = 0
    video_counter = 0
    doc_counter = 0
    if 'photo' in media.keys() or 'video' in media.keys() or 'doc' in media.keys():
        if 'photo' in media.keys():
            for photo in media['photo']:
                inline_markup.row(InlineKeyboardButton(f"Удалить фото №{photo_counter+1}",
                                                       callback_data=f"rm p {photo_counter} {channel_source} {channel_message_id}"))
                photo_counter += 1
        if 'video' in media.keys():
            for video in media['video']:
                inline_markup.row(InlineKeyboardButton(f"Удалить видео №{video_counter+1}",
                                                       callback_data=f"rm v {video_counter} {channel_source} {channel_message_id}"))
                video_counter += 1
        if 'doc' in media.keys():
            for doc in media['doc']:
                inline_markup.row(InlineKeyboardButton(f"Удалить документ №{doc_counter+1}",
                                                       callback_data=f"rm d {doc_counter} {channel_source} {channel_message_id}"))
                doc_counter += 1

        inline_markup.row(InlineKeyboardButton("Вернуться", callback_data=f"back {channel_source} {channel_message_id}"))

    if photo_counter + video_counter + doc_counter == 0 and raw_text == "":
        await edit_saved_post(user_id=callback_query.from_user.id, prev_channel_source=channel_source,
                              prev_message_id=channel_message_id, channel_to_post=channel_to_post,
                              type="remove")
        await Form.CALENDAR_DAY_STATE.set()
        return 0


    await callback_query.message.answer(f'*Редактируемая публикация*:', parse_mode="Markdown")
    await send_message_bot_chat(source=source, media=media, raw_text=raw_text, chat_id=callback_query.from_user.id)
    if photo_counter + video_counter + doc_counter == 0 and raw_text != "":
        message = await callback_query.message.answer(text="Выберете опцию")
        callback_query.data = f"back {channel_source} {channel_message_id}"
        callback_query.message.message_id = message.message_id
        await callback_calendar_edit_back(callback_query=callback_query)
    else:
        await callback_query.message.answer(text="Выберете какое медиа удалить", reply_markup=inline_markup)
    await edit_saved_post(user_id=callback_query.from_user.id, prev_channel_source=channel_source,
                          prev_message_id=channel_message_id, channel_to_post=channel_to_post,
                          type="edit", media=media)

# @dp.callback_query_handler(lambda c: c.data and "ed t" in c.data, state="CALENDAR_EDITING_STATE")
async def callback_calendar_edit_edit_text(callback_query: types.CallbackQuery):
    await bot.answer_callback_query(callback_query.id)

    try:
        channel_message_id = int(callback_query.data.split()[3])
    except ValueError:
        channel_message_id = callback_query.data.split()[3]
    channel_source = callback_query.data.split()[2]
    channel_to_post = calendar_temp[callback_query.from_user.id]

    calendar_editing_temp[callback_query.from_user.id] = [channel_source, channel_message_id, channel_to_post, callback_query.message.message_id]

    await callback_query.message.answer("Введите новый текст для публикации", reply_markup=ReplyKeyboardRemove())

    await Form.CALENDAR_EDITING_TEXT_STATE.set()


# @dp.callback_query_handler(lambda c: c.data and "ed m" in c.data, state="CALENDAR_EDITING_STATE")
async def callback_calendar_edit_edit_media(callback_query: types.CallbackQuery):
    await bot.answer_callback_query(callback_query.id)
    print(calendar_editing_temp)

    try:
        channel_message_id = int(callback_query.data.split()[3])
    except ValueError:
        channel_message_id = callback_query.data.split()[3]
    channel_source = callback_query.data.split()[2]
    channel_to_post = calendar_temp[callback_query.from_user.id]

    calendar_editing_temp[callback_query.from_user.id] = [channel_source, channel_message_id, channel_to_post, callback_query.message.message_id]

    markup = ReplyKeyboardMarkup(resize_keyboard=True).row("Отмена", "Сохранить")
    await callback_query.message.answer("Отправьте новые файлы для публикации", reply_markup=markup)

    await Form.CALENDAR_EDITING_MEDIA_STATE.set()

# Calendar editing text state

# @dp.message_handler(state="CALENDAR_EDITING_TEXT_STATE")
async def calendar_edit_text(message: types.Message):
    channel_source = calendar_editing_temp[message.from_user.id][0]
    channel_message_id = calendar_editing_temp[message.from_user.id][1]
    channel_to_post = calendar_editing_temp[message.from_user.id][2]
    editing_post_message_id = calendar_editing_temp[message.from_user.id][3]


    return_dict = await edit_saved_post(user_id=message.from_user.id, prev_channel_source=channel_source,
                                        prev_message_id=channel_message_id, channel_to_post=channel_to_post,
                                        type="none", to_return=["media","raw_text"])

    media = return_dict['media']
    raw_text = return_dict['raw_text']

    message_id_offset = 0
    if len(media.keys()) == 2:
        is_media = False
        message_id_offset += 1
    else:
        if isinstance(media, dict):
            if 'photo' in media.keys():
                for photo in media['photo']:
                    message_id_offset += 1
            if 'video' in media.keys():
                for video in media['video']:
                    message_id_offset += 1
            if 'doc' in media.keys():
                for doc in media['doc']:
                    message_id_offset += 1
        is_media = True

    if is_media:
        if len(message.text) >= 1024:
            await message.answer("*Ошибка*\nЕсли в посте есть медиа длина текста не может превышать 1024 символов",
                                 parse_mode="Markdown")
            return 0
        if raw_text != message.text:
            await bot.edit_message_caption(chat_id=message.from_user.id,
                                           message_id=editing_post_message_id - message_id_offset,
                                           caption=message.text)
    else:
        if len(message.text) >= 4096:
            await message.answer("*Ошибка*\nДлина сообщения не может превышать 4096 символов", parse_mode="Markdown")
            return 0
        if raw_text != message.text:
            await bot.edit_message_text(chat_id=message.from_user.id,
                                        message_id=editing_post_message_id - message_id_offset,
                                        text=message.text)

    for i in range(message.message_id, editing_post_message_id, -1):
        try:
            await bot.delete_message(chat_id=message.from_user.id, message_id=i)
        except Exception:
            pass
    if raw_text != message.text:
        await edit_saved_post(user_id=message.from_user.id, prev_channel_source=channel_source,
                              prev_message_id=channel_message_id, channel_to_post=channel_to_post,
                              type="edit", raw_text=message.text)

    user_saved_posts = json.loads(
        (await table_execute(f"SELECT SAVED_POSTS FROM USERS WHERE USER_ID = {message.from_user.id}", is_return=True))[
            0])
    unconfigured_posts = {}
    for key in user_saved_posts.keys():
        for post in user_saved_posts[key]:
            if post['date_post'] == None:
                if key in unconfigured_posts:
                    unconfigured_posts[key].append(post)
                else:
                    unconfigured_posts[key] = [post]

    markup = ReplyKeyboardMarkup(resize_keyboard=True).row("Вернуться")
    for script in unconfigured_posts.keys():
        markup.row(script)
    await message.answer("Сохранено!", reply_markup=markup)

    calendar_editing_temp.pop(message.from_user.id)
    await Form.CALENDAR_EDITING_STATE.set()

# Calendar editing media state

# @dp.message_handler(state="CALENDAR_EDITING_MEDIA_STATE")
async def calendar_edit_media(message: types.Message):
    channel_source = calendar_editing_temp[message.from_user.id][0]
    channel_message_id = calendar_editing_temp[message.from_user.id][1]
    channel_to_post = calendar_editing_temp[message.from_user.id][2]
    editing_post_message_id = calendar_editing_temp[message.from_user.id][3]
    if message.text is not None:
        if message.text.lower() == "отмена":
            try:
                calendar_editing_temp.pop(message.from_user.id)
                calendar_editing_media_temp.pop(message.from_user.id)
            except Exception:
                pass
            user_saved_posts = json.loads((await table_execute(
                f"SELECT SAVED_POSTS FROM USERS WHERE USER_ID = {message.from_user.id}", is_return=True))[0])
            unconfigured_posts = {}
            for key in user_saved_posts.keys():
                for post in user_saved_posts[key]:
                    if post['date_post'] == None:
                        if key in unconfigured_posts:
                            unconfigured_posts[key].append(post)
                        else:
                            unconfigured_posts[key] = [post]
            markup = ReplyKeyboardMarkup(resize_keyboard=True).row("Вернуться")
            for script in unconfigured_posts.keys():
                markup.row(script)
            for i in range(message.message_id, editing_post_message_id, -1):
                try:
                    await bot.delete_message(chat_id=message.from_user.id, message_id=i)
                except Exception:
                    pass
            await message.answer("Отмена...", reply_markup=markup)
            await Form.CALENDAR_EDITING_STATE.set()
            return 0

        if message.text.lower() == "сохранить":
            user_saved_posts = json.loads((await table_execute(
                f"SELECT SAVED_POSTS FROM USERS WHERE USER_ID = {message.from_user.id}", is_return=True))[0])
            unconfigured_posts = {}
            for key in user_saved_posts.keys():
                for post in user_saved_posts[key]:
                    if post['date_post'] == None:
                        if key in unconfigured_posts:
                            unconfigured_posts[key].append(post)
                        else:
                            unconfigured_posts[key] = [post]
            markup = ReplyKeyboardMarkup(resize_keyboard=True).row("Вернуться")
            for script in unconfigured_posts.keys():
                markup.row(script)
            inline_markup = InlineKeyboardMarkup().row(
                InlineKeyboardButton("Удалить медиа", callback_data=f"del m {channel_source} {channel_message_id}"),
                InlineKeyboardButton("Удалить текст",
                                     callback_data=f"del t {channel_source} {channel_message_id}")).row(
                InlineKeyboardButton("Изменить текст", callback_data=f"ed t {channel_source} {channel_message_id}"),
                InlineKeyboardButton("Добавить медиа",
                                     callback_data=f"ed m {channel_source} {channel_message_id}")).row(
                InlineKeyboardButton("Вернуться", callback_data=f"return {channel_source} {channel_message_id}"))

            for i in range(message.message_id, editing_post_message_id, -1):
                try:
                    await bot.delete_message(chat_id=message.from_user.id, message_id=i)
                except Exception:
                    pass

            await message.answer('Сохраняю...', reply_markup=markup)
            print(calendar_editing_media_temp.keys())
            if message.from_user.id in calendar_editing_media_temp.keys():

                media = calendar_editing_media_temp[message.from_user.id]

                delete_message = message
                delete_message.message_id = editing_post_message_id
                await delete_conf_post(message=delete_message, channel_source=channel_source, media=media)

                raw_text = (await edit_saved_post(user_id=message.from_user.id, prev_channel_source=channel_source,
                                                    prev_message_id=channel_message_id, channel_to_post=channel_to_post,
                                                    type="edit", to_return=["raw_text"], media=media))['raw_text']
                await message.answer('*Редактируемая публикация*:', parse_mode="Markdown")
                await send_message_bot_chat(source=channel_source, media=media, raw_text=raw_text, chat_id=message.from_user.id)
                await message.answer("Выберите опцию", reply_markup=inline_markup)

            await Form.CALENDAR_EDITING_STATE.set()

            try:
                print(calendar_editing_temp)
                calendar_editing_temp.pop(message.from_user.id)
                print(calendar_editing_temp)
                calendar_editing_media_temp.pop(message.from_user.id)
            except Exception:
                pass
            return 0

    if not message.from_user.id in calendar_editing_media_temp.keys():
        return_dict = await edit_saved_post(user_id=message.from_user.id, prev_channel_source=channel_source,
                                            prev_message_id=channel_message_id, channel_to_post=channel_to_post,
                                            type="none", to_return=["media"])

        media = return_dict['media']
    else:
        media = calendar_editing_media_temp[message.from_user.id]

    media_count = 0

    if 'photo' in media.keys():
        for photo in media['photo']:
            media_count += 1
    if 'video' in media.keys():
        for video in media['video']:
            media_count += 1
    if 'doc' in media.keys():
        for doc in media['doc']:
            media_count += 1
    if media_count < 10:
        if 'photo' in message:
            if 'photo' in media.keys():
                media['photo'].append(message.photo[0].file_id)
            else:
                media['photo'] = [message.photo[0].file_id]
        if 'video' in message:
            if 'video' in media.keys():
                media['video'].append(message.video.file_id)
            else:
                media['video'] = [message.video.file_id]
        if 'document' in message:
            if 'doc' in media.keys():
                media['doc'].append(message.document.file_id)
            else:
                media['doc'] = [message.document.file_id]

    else:
        await message.answer("*Ошибка*\nВы не можете прикрепить к публикации больше 10 файлов", parse_mode="Markdown")
    print(media)
    calendar_editing_media_temp[message.from_user.id] = media


# Calendar set date state
# @dp.callback_query_handler(state="CALENDAR_SET_DATE_STATE")
async def set_date_inline_calendar_handler(callback_query: types.CallbackQuery):
    date_post = posts_set_date_temp[callback_query.from_user.id][3]
    posts_info = posts_set_date_temp[callback_query.from_user.id][4]
    selected, date = await telegramcalendar.process_calendar_selection(bot, callback_query, posts_info=posts_info,
                                                                       remove_day=(int(date_post.split('-')[0]), int(date_post.split('-')[1]), int(date_post.split('-')[2])))
    if selected:
        user_saved_posts = json.loads((await table_execute(
            f"SELECT SAVED_POSTS FROM USERS WHERE USER_ID = {callback_query.from_user.id}", is_return=True))[0])
        channel_message_id = posts_set_date_temp[callback_query.from_user.id][2]
        channel_to_post = posts_set_date_temp[callback_query.from_user.id][0]
        channel_source = posts_set_date_temp[callback_query.from_user.id][1]

        if channel_to_post in user_saved_posts.keys():
            for post in user_saved_posts[channel_to_post]:
                if post['source'] == channel_source and post['message_id'] == channel_message_id:
                    date_post = post['date_post']
                    time_post = post['time_post']

            if date == "DENY":
                inline_markup = InlineKeyboardMarkup().row(
                    InlineKeyboardButton('Удалить',
                                         callback_data=f"delete {channel_source} {channel_message_id}"),
                    InlineKeyboardButton('Опубликовать',
                                         callback_data=f"post {channel_source} {channel_message_id}")).row(
                    InlineKeyboardButton('Специальные настройки',
                                         callback_data=f"set {channel_source} {channel_message_id}"),
                    InlineKeyboardButton('Редактировать',
                                         callback_data=f"edit {channel_source} {channel_message_id}")).row(
                    InlineKeyboardButton('Изменить дату публикации',
                                         callback_data=f"date {channel_source} {channel_message_id}"),
                    InlineKeyboardButton('Изменить время',
                                         callback_data=f"time {channel_source} {channel_message_id}"))

                await bot.edit_message_text(chat_id=callback_query.from_user.id,
                                            message_id=callback_query.message.message_id,
                                            text=f"*Публикация назначена на {date_post} в {time_post}*\nВыберите опцию",
                                            reply_markup=inline_markup, parse_mode="Markdown")
                posts_set_date_temp.pop(callback_query.from_user.id)
                await Form.CALENDAR_DAY_STATE.set()
                return 0

            media = (await edit_saved_post(user_id=callback_query.from_user.id, prev_channel_source=channel_source,
                                          prev_message_id=channel_message_id, channel_to_post=channel_to_post,
                                          type="edit", to_return=["media"], date_post=str(date)))["media"]
            await delete_conf_post(message=callback_query, channel_source=channel_source, media=media)
        posts_set_date_temp.pop(callback_query.from_user.id)
        await Form.CALENDAR_DAY_STATE.set()

# Calendar set time state
# @dp.callback_query_handler(lambda c: c.data and "hour" in c.data, state="CALENDAR_SET_TIME_STATE")
async def set_hour_inline_calendar_handler(callback_query: types.CallbackQuery):
    await bot.answer_callback_query(callback_query.id)
    if callback_query.data.split()[1] == "DENY":
        date_post = callback_query.data.split()[2]
        time_post = callback_query.data.split()[3]
        channel_message_id = posts_set_time_temp[callback_query.from_user.id][2]
        channel_to_post = posts_set_time_temp[callback_query.from_user.id][0]
        channel_source = posts_set_time_temp[callback_query.from_user.id][1]

        inline_markup = InlineKeyboardMarkup().row(
            InlineKeyboardButton('Удалить',
                                 callback_data=f"delete {channel_source} {channel_message_id}"),
            InlineKeyboardButton('Изменить дату публикации',
                                 callback_data=f"date {channel_source} {channel_message_id}")).row(
            InlineKeyboardButton('Изменить время',
                                 callback_data=f"time {channel_source} {channel_message_id}"),
            InlineKeyboardButton('Специальные настройки',
                                 callback_data=f"set {channel_source} {channel_message_id}")).row(
            InlineKeyboardButton('Опубликовать',
                                 callback_data=f"post {channel_source} {channel_message_id}"),
            InlineKeyboardButton('Редактировать',
                                 callback_data=f"edit {channel_source} {channel_message_id}"))

        await bot.edit_message_text(chat_id=callback_query.from_user.id, message_id=callback_query.message.message_id,
                                    text=f"*Публикация назначена на {date_post} в {time_post}*\nВыберите опцию",
                                    reply_markup=inline_markup, parse_mode="Markdown")

        await Form.CALENDAR_DAY_STATE.set()
        return 0
    hour = callback_query.data.split()[1]
    if hour != "☓":
        date_post = callback_query.data.split()[2]
        time_post = callback_query.data.split()[3]
        current_datetime = datetime.now()
        current_date = current_datetime.strftime('%Y-%m-%d')
        current_hour = current_datetime.strftime('%H')

        keyboard = []
        row = []
        for i in range(1, 61, 10):
            if date_post == current_date and hour == current_hour and i-1 <= current_datetime.minute:
                row.append(InlineKeyboardButton("☓", callback_data=f"minute ☓ {hour}"))
            else:
                if i-1 == 0:
                    row.append(InlineKeyboardButton("00", callback_data=f"minute 00 {hour}"))
                else:
                    row.append(InlineKeyboardButton(f"{i-1}", callback_data=f"minute {i-1} {hour}"))
        keyboard.append(row)
        keyboard.append([InlineKeyboardButton("Отмена", callback_data=f"minute DENY {date_post} {time_post}")])
        inline_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)

        await bot.edit_message_text(chat_id=callback_query.from_user.id, message_id=callback_query.message.message_id,
                                    text=f"*Вы выбрали час публикации - {hour}*\nТеперь укажите минуты в которые должен быть опубликован пост:",
                                    reply_markup=inline_markup, parse_mode="Markdown")

# @dp.callback_query_handler(lambda c: c.data and "minute" in c.data, state="CALENDAR_SET_TIME_STATE")
async def set_minute_inline_calendar_handler(callback_query: types.CallbackQuery):
    await bot.answer_callback_query(callback_query.id)
    channel_message_id = posts_set_time_temp[callback_query.from_user.id][2]
    channel_to_post = posts_set_time_temp[callback_query.from_user.id][0]
    channel_source = posts_set_time_temp[callback_query.from_user.id][1]

    inline_markup = InlineKeyboardMarkup().row(
        InlineKeyboardButton('Удалить',
                             callback_data=f"delete {channel_source} {channel_message_id}"),
        InlineKeyboardButton('Опубликовать',
                             callback_data=f"post {channel_source} {channel_message_id}")).row(
        InlineKeyboardButton('Специальные настройки',
                             callback_data=f"set {channel_source} {channel_message_id}"),
        InlineKeyboardButton('Редактировать',
                             callback_data=f"edit {channel_source} {channel_message_id}")).row(
        InlineKeyboardButton('Изменить дату публикации',
                             callback_data=f"date {channel_source} {channel_message_id}"),
        InlineKeyboardButton('Изменить время',
                             callback_data=f"time {channel_source} {channel_message_id}"))
    if callback_query.data.split()[1] == "DENY":
        date_post = callback_query.data.split()[2]
        time_post = callback_query.data.split()[3]

        await bot.edit_message_text(chat_id=callback_query.from_user.id, message_id=callback_query.message.message_id,
                                    text=f"*Публикация назначена на {date_post} в {time_post}*\nВыберите опцию",
                                    reply_markup=inline_markup, parse_mode="Markdown")

        await Form.CALENDAR_DAY_STATE.set()
        return 0
    minute = callback_query.data.split()[1]
    hour = callback_query.data.split()[2]
    if minute != "☓":
        date_post = (await edit_saved_post(user_id=callback_query.from_user.id, prev_channel_source=channel_source,
                                      prev_message_id=channel_message_id, channel_to_post=channel_to_post,
                                      type="edit", to_return=["date_post"], time_post=f"{hour}:{minute}"))["date_post"]

        await bot.edit_message_text(chat_id=callback_query.from_user.id, message_id=callback_query.message.message_id,
                                   text=f"*Публикация назначена на {date_post} в {hour}:{minute}*\nВыберите опцию",
                                   reply_markup=inline_markup, parse_mode="Markdown")

        await Form.CALENDAR_DAY_STATE.set()