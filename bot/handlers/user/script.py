import json
import traceback
import urllib.request

import pytube
import requests
from aiogram import types, Bot
from aiogram.bot.api import TelegramAPIServer
from aiogram.dispatcher import FSMContext
from aiogram.types import ReplyKeyboardMarkup, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardRemove
from aiogram.utils.exceptions import ChatNotFound, BotKicked

from .main import start_menu, Form, process_scripts_command
from ...database.methods import table_execute
from ...misc import TgKeys, ConfigKeys
from ...misc.util import stop_telegram_script, start_telegram_script

local_server = TelegramAPIServer.from_base(f'http://{ConfigKeys.telegram_host}:{ConfigKeys.telegram_port}')

bot = Bot(token=TgKeys.TOKEN, server=local_server, parse_mode='HTML')


# Scripts state
# @dp.message_handler(lambda message: message.text and message.text.lower() == "вернуться", state="SCRIPTS_STATE")
async def process_return_from_scripts_command(message: types.Message):
    await start_menu(message=message)


# @dp.message_handler(lambda message: message.text and message.text.lower() == "создать сценарий", state="SCRIPTS_STATE")
async def process_create_script_command(message: types.Message):
    markup = ReplyKeyboardMarkup(resize_keyboard=True).add("1", "2").row("Отмена")
    await message.answer(
        "Чтобы создать новый скрипт выберите один из режимов работы скрипта:\n1 - Бот будет автоматически публиковать все посты из указанных вами источников в ваш телеграм канал\n2 - Бот будет присылать все посты из указанных вами источников в данный чат для вашей модерации и настройки",
        reply_markup=markup)
    await Form.CREATE_SCRIPT_STATE.set()


# @dp.message_handler(state="SCRIPTS_STATE")
async def process_scripts_config_command(message: types.Message | types.CallbackQuery, state: FSMContext):
    current_scripts = json.loads(
        (await table_execute(f"SELECT LINKS FROM USERS WHERE USER_ID = {message.from_user.id}", is_return=True))[0])
    running_scripts = json.loads((await table_execute(
        f"SELECT RUNNING_SCRIPTS FROM USERS WHERE USER_ID = {message.from_user.id}", is_return=True))[0])
    if message.text.lower() in current_scripts.keys():
        await state.update_data(current_script=message.text.lower())
        if message.text.lower() in running_scripts:
            markup = ReplyKeyboardMarkup(resize_keyboard=True).add("Вернуться", f"Удалить скрипт ").row(
                f"Редактировать скрипт", f"Настройки публикаций").row(
                f"Остановить скрипт {message.text.lower()}")
            if current_scripts[message.text.lower()][0] == 1:
                await bot.send_message(chat_id=message.from_user.id,
                                       text=f'Информация о скрипте *{message.text.lower()}*\nСтатус сценария - *Запущен*\nРежим работы сценария - *"Режим автоматической публикации"\n*Канал для публикации - *{message.text.lower()}*\nИсточники: {current_scripts[message.text.lower()][1]}',
                                       reply_markup=markup, parse_mode="Markdown")
            else:
                await bot.send_message(chat_id=message.from_user.id,
                                       text=f'Информация о скрипте *{message.text.lower()}*\nСтатус сценария - *Запущен*\nРежим работы сценария - *"Режим планирования"\n*Канал для публикации - *{message.text.lower()}*\nИсточники: {current_scripts[message.text.lower()][1]}',
                                       reply_markup=markup, parse_mode="Markdown")
        else:
            markup = ReplyKeyboardMarkup(resize_keyboard=True).add("Вернуться", f"Удалить скрипт {message.text.lower()}").row(
                f"Редактировать скрипт {message.text.lower()}", f"Настройки публикаций").row(
                f"Запустить скрипт {message.text.lower()}")
            if current_scripts[message.text.lower()][0] == 1:
                await bot.send_message(chat_id=message.from_user.id,
                                       text=f'Информация о скрипте *{message.text.lower()}*\nСтатус сценария - *Не запущен*\nРежим работы сценария - *"Режим автоматической публикации"*\nКанал для публикации - *{message.text.lower()}*\nИсточники: {current_scripts[message.text.lower()][1]}',
                                       reply_markup=markup, parse_mode="Markdown")
            else:
                await bot.send_message(chat_id=message.from_user.id,
                                       text=f'Информация о скрипте *{message.text.lower()}*\nСтатус сценария - *Не запущен*\nРежим работы сценария - *"Режим планирования"*\nКанал для публикации - *{message.text.lower()}*\nИсточники: {current_scripts[message.text.lower()][1]}',
                                       reply_markup=markup, parse_mode="Markdown")
        await Form.SCRIPT_CONFIG_STATE.set()


# script config state
# @dp.message_handler(state="SCRIPT_CONFIG_STATE")
async def process_script_config_back_command(message: types.Message, state: FSMContext):
    running_scripts = json.loads((await table_execute(
        f"SELECT RUNNING_SCRIPTS FROM USERS WHERE USER_ID = {message.from_user.id}", is_return=True))[0])

    text = message.text.lower()
    script_name = (await state.get_data()).get('current_script')
    if text == "вернуться":
        async with state.proxy() as data:
            data.pop('current_script')
        await process_scripts_command(message=message)
    elif "остановить скрипт" in text:
        if script_name in running_scripts:
            await stop_telegram_script(user_id=message.from_user.id, script_name=script_name)
            await bot.send_message(chat_id=message.from_user.id, text="*Сценарий отключен*", parse_mode="Markdown")
            await Form.SCRIPTS_STATE.set()
            message.text = script_name
            await process_scripts_config_command(message=message, state=state)
    elif "запустить скрипт" in text:
        if script_name not in running_scripts:
            if await is_vk_in_sources(script_name=script_name, user_id=message.from_user.id) and not await is_vk_available(user_id=message.from_user.id):
                await bot.send_message(chat_id=message.from_user.id, text=
                    "*Ошибка*\nВаш сценарий содержит источники из Вконтакте. Для работы такого сценария вам необходимо авторизоваться через Вконтакте.\nЭто можно сделать во вкладке *Аккаунт*",
                    parse_mode="Markdown")
                return 0
            #проверка канала для публикации на валидность
            channel_info = await is_channel_accessable(channel_id=script_name)
            if channel_info is not True:
                await bot.send_message(chat_id=message.from_user.id, text=channel_info)
                return 0
            # проверка источника на валидность
            sources_list = (json.loads((await table_execute(f"SELECT LINKS FROM USERS WHERE USER_ID = {message.from_user.id}", is_return=True))[0])[script_name])[1]
            broken_sources_list = []
            for source in sources_list:
                if not (await is_source_accessable(source))[0]:
                    broken_sources_list.append(source)
            if len(broken_sources_list) != 0:
                for source in broken_sources_list:
                    await bot.send_message(chat_id=message.from_user.id,text=f"*Ошибка*\nИсточник {source} недоступен. Возможно он был удален или заблокирован.\nСценарий не будет запущен пока этот источник не будет удален или исправлен",
                                           parse_mode="Markdown")
                return 0
            await start_telegram_script(user_id=message.from_user.id, script_name=script_name)
            await bot.send_message(chat_id=message.from_user.id, text="*Сценарий запущен*", parse_mode="Markdown")
            await Form.SCRIPTS_STATE.set()
            message.text = script_name
            await process_scripts_config_command(message=message, state=state)
    elif "удалить скрипт" in text:
        if script_name in running_scripts:
            await stop_telegram_script(user_id=message.from_user.id, script_name=script_name)
        user_scripts = json.loads(
            (await table_execute(f"SELECT LINKS FROM USERS WHERE USER_ID = {message.from_user.id}", is_return=True))[0])
        user_scripts.pop(script_name)
        await table_execute(
            f"UPDATE USERS SET LINKS = '{json.dumps(user_scripts)}' WHERE USER_ID = {message.from_user.id}")
        await bot.send_message(chat_id=message.from_user.id, text="*Сценарий удален*", parse_mode="Markdown")
        await process_scripts_command(message=message)
    elif "редактировать скрипт" in text:
        inline_markup = InlineKeyboardMarkup().add(
            InlineKeyboardButton('Режим работы', callback_data=f'mode_change'),
            InlineKeyboardButton('Источники', callback_data=f'sources_change'),
            InlineKeyboardButton('Отмена', callback_data=f'deny_change'))
        await bot.send_message(chat_id=message.from_user.id, text="Редактирование сценария...",
                               reply_markup=ReplyKeyboardRemove())
        await bot.send_message(chat_id=message.from_user.id, text="Что вы хотите изменить?", reply_markup=inline_markup)
        # await message.answer(f"*Все источники для сценария - {text[12:]}*", parse_mode="Markdown")
    elif "настройки публикаций" in text:
        script_settings = json.loads((await table_execute(
            f"SELECT SCRIPTS_SETTINGS FROM USERS WHERE USER_ID = {message.from_user.id}", is_return=True))[0])
        if not script_settings[script_name]["author"]:
            inline_markup = InlineKeyboardMarkup().add(
                InlineKeyboardButton("Указание авторства - OFF", callback_data=f"author")).add(
                InlineKeyboardButton("Вернуться", callback_data=f"back"))
        else:
            inline_markup = InlineKeyboardMarkup().add(
                InlineKeyboardButton("Указание авторства - ON", callback_data=f"author")).add(
                InlineKeyboardButton("Вернуться", callback_data=f"back"))
        await message.answer("Перехожу в глобальные настройки...", reply_markup=ReplyKeyboardRemove())
        await message.answer(f"Стандартные настройки для каждой публикации в канал - {script_name}",
                             reply_markup=inline_markup)
        await Form.SCRIPT_SETTINGS_STATE.set()

async def is_vk_in_sources(script_name, user_id):
    user_scripts = json.loads(
        (await table_execute(f"SELECT LINKS FROM USERS WHERE USER_ID = {user_id}", is_return=True))[0])
    for source in user_scripts[script_name][1]:
        if source.startswith("vk.com/"):
            return True
    return False

async def is_vk_available(user_id):
    access_token = (await  table_execute(f"SELECT VK_ACCESS_TOKEN FROM USERS WHERE USER_ID = {user_id}", is_return=True))[0]
    if access_token is None:
        return False
    else:
        return True

async def is_channel_accessable(channel_id):
    try:
        chat_info = dict(await bot.get_chat(chat_id=channel_id))
        if not "invite_link" in chat_info.keys():
            return "Бот больше не администратор этого канала. Сделайте его вновь администратором прежде чем запустить сценарий"
    except BotKicked:
        return "Бот был удален из этого канала. Сначало вам необходимо добавить бота в этот канал как администратора. Сделайте это чтобы запустить сценарий"
    except Exception:
        return "Ошибка, что-то пошло не так"
    return True

async def is_source_accessable(source):
    if source.startswith('@'):
        try:
            channel_info = dict(await bot.get_chat(chat_id=source))
        except Exception:
            return (False, "*Ошиибка*\nДанный канал не доступен. Возможно он не существует, закрыт или был заблокирован")
    elif source.startswith("vk.com/"):
        try:
            group_info = json.loads((urllib.request.urlopen(
                'https://api.vk.com/method/groups.getById?group_id=' + source[
                                                                       7:] + '&v=5.131&access_token=' + ConfigKeys.LOCAL_VK_TOKEN)).read().decode(
                'utf-8'))
            if group_info['response'][0]['is_closed'] == 1:
                return (False, "*Ошиибка*\nДанная группа является закрытой")
        except Exception:
            return (False, "*Ошиибка*\nДанная группа недоступна. Возможно она была удалена или заблокирована")
    elif source.startswith("youtube.com/"):
        try:
            a = pytube.Channel(source).channel_id
        except Exception:

            return (False, "*Ошиибка*\nДанная канал недоступен. Возможно он был удален или заблокирован")
    elif source.startswith("dzen.ru/"):
        url = "https://" + source
        page = requests.get(url)
        if page.status_code != 200:
            return (False, "*Ошиибка*\nДанная канал недоступен. Возможно он был удален или заблокирован")
    return (True, "")

# Script Settings state
async def callback_script_settings(callback_query: types.CallbackQuery, state: FSMContext):
    await bot.answer_callback_query(callback_query.id)
    script_name = (await state.get_data()).get('current_script')
    if callback_query.data == "back":
        await callback_query.message.delete()
        callback_query.text = script_name
        await process_scripts_config_command(message=callback_query, state=state)
    elif callback_query.data == "author":
        scripts_settings = json.loads((await table_execute(
            f"SELECT SCRIPTS_SETTINGS FROM USERS WHERE USER_ID = {callback_query.from_user.id}", is_return=True))[0])
        if scripts_settings[script_name]["author"]:
            scripts_settings[script_name]["author"] = False
            inline_markup = InlineKeyboardMarkup().add(
                InlineKeyboardButton("Указание авторства - OFF", callback_data=f"author")).add(
                InlineKeyboardButton("Вернуться", callback_data=f"back"))
        else:
            scripts_settings[script_name]["author"] = True
            inline_markup = InlineKeyboardMarkup().add(
                InlineKeyboardButton("Указание авторства - ON", callback_data=f"author")).add(
                InlineKeyboardButton("Вернуться", callback_data=f"back"))
        await table_execute(f"UPDATE USERS SET SCRIPTS_SETTINGS = '{json.dumps(scripts_settings)}' WHERE USER_ID = {callback_query.from_user.id}")
        # await transform_post_to_settings(user_id=callback_query.from_user.id, script_name=script_name, type = "all")
        await callback_query.message.edit_reply_markup(inline_markup)


# @dp.callback_query_handler(lambda c: c.data and "deny_change" in c.data, state="SCRIPT_CONFIG_STATE")
async def callback_change_deny(callback_query: types.CallbackQuery, state: FSMContext):
    await bot.answer_callback_query(callback_query.id)
    script_name = (await state.get_data()).get('current_script')
    await bot.delete_message(chat_id=callback_query.from_user.id, message_id=callback_query.message.message_id)
    callback_query.text = script_name
    await process_scripts_config_command(message=callback_query, state=state)


# @dp.callback_query_handler(lambda c: c.data and "mode_change" in c.data, state="SCRIPT_CONFIG_STATE")
async def callback_change_mode(callback_query: types.CallbackQuery, state: FSMContext):
    await bot.answer_callback_query(callback_query.id)
    script_name = (await state.get_data()).get('current_script')
    user_scripts = json.loads(
        (await table_execute(f"SELECT LINKS FROM USERS WHERE USER_ID = {callback_query.from_user.id}", is_return=True))[
            0])
    if user_scripts[script_name][0] == 1:
        user_scripts[script_name][0] = 2
        await bot.send_message(chat_id=callback_query.from_user.id,
                               text='Режим работы сценария изменен на *"режим планирования"*', parse_mode="Markdown")
    elif user_scripts[script_name][0] == 2:
        user_scripts[script_name][0] = 1
        await bot.send_message(chat_id=callback_query.from_user.id,
                               text='Режим работы сценария изменен на *"режим автоматической публикации"*',
                               parse_mode="Markdown")
    await stop_telegram_script(script_name=script_name, user_id=callback_query.from_user.id)
    await table_execute(
        f"UPDATE USERS SET LINKS = '{json.dumps(user_scripts)}' WHERE USER_ID = {callback_query.from_user.id}")
    await start_telegram_script(script_name=script_name, user_id=callback_query.from_user.id)
    await bot.delete_message(chat_id=callback_query.from_user.id, message_id=callback_query.message.message_id)
    callback_query.text = script_name
    await process_scripts_config_command(message=callback_query, state=state)


# @dp.callback_query_handler(lambda c: c.data and "sources_change" in c.data, state="SCRIPT_CONFIG_STATE")
async def callback_change_sources(callback_query: types.CallbackQuery | types.Message, state: FSMContext):
    try:
        await bot.answer_callback_query(callback_query.id)
    except:
        pass
    script_name = (await state.get_data()).get('current_script')
    user_scripts = json.loads(
        (await table_execute(f"SELECT LINKS FROM USERS WHERE USER_ID = {callback_query.from_user.id}", is_return=True))[
            0])
    script_info = user_scripts[script_name]
    inline_markup = InlineKeyboardMarkup().row(
        InlineKeyboardButton('Готово..', callback_data=f'confirm_sources_change')).row(
        InlineKeyboardButton('Добавить источник..', callback_data=f'add_source'))
    for i in range(len(script_info[1])):
        inline_markup.row(InlineKeyboardButton("Удалить источник - " + script_info[1][i],
                                               callback_data=f'delete {i}'))
    try:
        await bot.delete_message(chat_id=callback_query.from_user.id, message_id=callback_query.message.message_id)
    except:
        pass
    await bot.send_message(chat_id=callback_query.from_user.id, text="Доступные действия с источниками:",
                           reply_markup=inline_markup)
    try:
        await stop_telegram_script(user_id=callback_query.from_user.id, script_name=script_name, update_db=False)
    except:
        pass
    await Form.SOURCES_CHANGE_STATE.set()


# Sources change state

# @dp.callback_query_handler(lambda c: c.data and "confirm_sources_change" in c.data, state="SOURCES_CHANGE_STATE")
async def callback_confirm_sources_change(callback_query: types.CallbackQuery, state: FSMContext):
    await bot.answer_callback_query(callback_query.id)
    script_name = (await state.get_data()).get('current_script')
    running_scripts = json.loads((await table_execute(
        f"SELECT RUNNING_SCRIPTS FROM USERS WHERE USER_ID = {callback_query.from_user.id}", is_return=True))[0])
    if script_name in running_scripts:
        if await is_vk_in_sources(script_name=script_name, user_id=callback_query.from_user.id) and not await is_vk_available(user_id=callback_query.from_user.id):
            running_scripts.remove(script_name)
            await table_execute(f"UPDATE USERS SET RUNNING_SCRIPTS = '{json.dumps(running_scripts)}' WHERE USER_ID = {callback_query.from_user.id}")
        else:
            await start_telegram_script(user_id=callback_query.from_user.id, script_name=script_name, update_db=False)
    await bot.delete_message(chat_id=callback_query.from_user.id, message_id=callback_query.message.message_id)
    callback_query.text = script_name
    await process_scripts_config_command(message=callback_query, state=state)


# @dp.callback_query_handler(lambda c: c.data and "d" in c.data, state="SOURCES_CHANGE_STATE")
async def callback_delete_source(callback_query: types.CallbackQuery, state: FSMContext):
    await bot.answer_callback_query(callback_query.id)
    script_name = (await state.get_data()).get('current_script')
    source_id = int(callback_query.data.split()[1])
    user_scripts = json.loads(
        (await table_execute(f"SELECT LINKS FROM USERS WHERE USER_ID = {callback_query.from_user.id}", is_return=True))[
            0])
    script_info = user_scripts[script_name]
    source = script_info[1][source_id]
    # print(source)
    user_scripts[script_name][1].remove(source)
    await table_execute(
        f"UPDATE USERS SET LINKS = '{json.dumps(user_scripts)}' WHERE USER_ID = {callback_query.from_user.id}")
    await callback_change_sources(callback_query=callback_query, state=state)


# @dp.callback_query_handler(lambda c: c.data and "add_source" in c.data, state="SOURCES_CHANGE_STATE")
async def callback_add_source(callback_query: types.CallbackQuery, state: FSMContext):
    await bot.answer_callback_query(callback_query.id)
    script_name = (await state.get_data()).get('current_script')
    await bot.delete_message(chat_id=callback_query.from_user.id, message_id=callback_query.message.message_id)
    markup = ReplyKeyboardMarkup(resize_keyboard=True).add("Отмена")
    await bot.send_message(chat_id=callback_query.from_user.id,
                           text=f"Добавление источника в сценарий {script_name}\n*Поддерживаемые соцсети: Telegram, Youtube, VK, Дзен*\nУкажите ссылку в одном из этих форматов:\n*Telegram* - @yourchannel\n*Вконтакте* - vk.com/anyyourgroup\n*Youtube* - youtube.com/с/anychannel\n*Дзен* - dzen.ru/anyname",
                           reply_markup=markup, parse_mode="Markdown")
    await Form.ADD_SOURCE_STATE.set()


# Add source state
# @dp.message_handler(state="ADD_SOURCE_STATE")
async def process_add_source_command(message: types.Message, state: FSMContext):
    if message.text.lower() == "отмена":
        script_name = (await state.get_data()).get('current_script')
        await message.answer("Отмена...", reply_markup=ReplyKeyboardRemove())
    else:
        if message.text.startswith('https://www.'):
            message.text = message.text[12:]
        elif message.text.startswith('https://'):
            message.text = message.text[8:]
        if not (message.text.startswith('@') or message.text.startswith("vk.com/") or message.text.startswith(
                "youtube.com/") or message.text.startswith("dzen.ru/")):
            await  message.answer(
                f"Неверный формат ссылки - {message.text}. Укажите ссылку в одном из этих форматов:\n*Telegram* - @yourchannel\n*Вконтакте* - vk.com/anyyourgroup\n*Youtube* - youtube.com/с/anychannel\n*Дзен* - dzen.ru/anyname",
                parse_mode="Markdown")
            return 0
        #проверка источника на валидность
        result = await is_source_accessable(message.text)
        if not result[0]:
            await message.answer(text=result[1], parse_mode="Markdown")
            return 0
        user_scripts = json.loads(
            (await table_execute(f"SELECT LINKS FROM USERS WHERE USER_ID = {message.from_user.id}", is_return=True))[0])
        script_name = (await state.get_data()).get('current_script')
        user_scripts[script_name][1].append(message.text)
        await table_execute(
            f"UPDATE USERS SET LINKS = '{json.dumps(user_scripts)}' WHERE USER_ID = {message.from_user.id}")
        await message.answer("Источник добавлен", reply_markup=ReplyKeyboardRemove())
    message.data = f"sources_change"
    await callback_change_sources(callback_query=message, state=state)


# Create script state
# @dp.message_handler(lambda message: message.text and (message.text.lower() == "1" or message.text.lower() == "2"), state="CREATE_SCRIPT_STATE")
async def process_choose_script_mode_command(message: types.Message, state: FSMContext):
    await state.update_data(new_script_mode=int(message.text))
    markup = ReplyKeyboardMarkup(resize_keyboard=True).add("Отмена")
    await message.answer("Укажите телеграм канал в который вы хотите постить желаемые посты\n*Формат* - @yourchannel",
                         reply_markup=markup, parse_mode="Markdown")
    await Form.MODE_STATE.set()


# @dp.message_handler(lambda message: message.text and message.text.lower() == "отмена", state=["CREATE_SCRIPT_STATE", "MODE_STATE"])
async def process_cancel_command(message: types.Message, state: FSMContext):
    try:
        async with state.proxy() as data:
            data.pop('new_script_mode')
            data.pop('new_script_sources')
            data.pop('new_script_destination')

    except Exception:
        print(traceback.format_exc())
    await process_scripts_command(message=message)


# Mode state
# @dp.message_handler(lambda message: message.text and message.text.lower() == "завершить создание скрипта", state="MODE_STATE")
async def process_end_script_creation_command(message: types.Message, state: FSMContext):
    current_scripts = json.loads(
        (await table_execute(f"SELECT LINKS FROM USERS WHERE USER_ID = {message.from_user.id}", is_return=True))[0])
    scripts_settings = json.loads((await table_execute(
        f"SELECT SCRIPTS_SETTINGS FROM USERS WHERE USER_ID = {message.from_user.id}", is_return=True))[0])
    sources = (await state.get_data()).get('new_script_sources')
    if len(current_scripts) == 0:
        current_scripts = {(await state.get_data()).get('new_script_destination'): [(await state.get_data()).get('new_script_mode'), sources]}
        scripts_settings = {(await state.get_data()).get('new_script_destination'): {"author": False}}
    elif not (await state.get_data()).get('new_script_destination') in current_scripts.keys():
        current_scripts[(await state.get_data()).get('new_script_destination')] = [(await state.get_data()).get('new_script_mode'),
                                                                       sources]
        scripts_settings[(await state.get_data()).get('new_script_destination')] = {"author": False}
    else:
        await message.answer("*Ошибка*\nТакой сценарий уже существует", parse_mode="Markdown")
        await process_scripts_command(message=message)
        async with state.proxy() as data:
            data.pop('new_script_mode')
            data.pop('new_script_sources')
            data.pop('new_script_destination')
        return 0

    final_info = json.dumps(current_scripts)
    await table_execute(f"UPDATE USERS SET LINKS = '{final_info}' WHERE USER_ID = {message.from_user.id}")
    await table_execute(f"UPDATE USERS SET SCRIPTS_SETTINGS = '{json.dumps(scripts_settings)}' WHERE USER_ID = {message.from_user.id}")
    await message.answer("Сценарий успешно добавлен")
    vk_flag = False
    for source in sources:
        if source.startswith("vk.com"):
            vk_flag = True
            break

    if vk_flag:
        vk_access_token = (await table_execute(f"SELECT VK_ACCESS_TOKEN FROM USERS WHERE USER_ID = {message.from_user.id}", is_return=True))[0]
        if vk_access_token is None:
            markup = ReplyKeyboardMarkup(resize_keyboard=True).add("Позже", "Авторизоваться")
            await message.answer(
                "*ВНИМАНИЕ*\nДля получение публикаций из Вконтакте требуется авторизироваться.\nВаш сценарий не будет работать до тех пор, пока вы этого не сделаете",
                parse_mode="Markdown", reply_markup=markup)
            await Form.VK_GET_TOKEN.set()
        else:
            await start_telegram_script(user_id=message.from_user.id, script_name=(await state.get_data()).get('new_script_destination'))
            await process_scripts_command(message=message)
            async with state.proxy() as data:
                data.pop('new_script_mode')
                data.pop('new_script_sources')
                data.pop('new_script_destination')
    else:
        await start_telegram_script(user_id=message.from_user.id, script_name=(await state.get_data()).get('new_script_destination'))
        await process_scripts_command(message=message)
        async with state.proxy() as data:
            data.pop('new_script_mode')
            data.pop('new_script_sources')
            data.pop('new_script_destination')


# @dp.message_handler(state="MODE_STATE")
async def process_channel_link_command(message: types.Message, state: FSMContext):
    markup = ReplyKeyboardMarkup(resize_keyboard=True).add("Отмена", "Завершить создание скрипта")
    if message.text.startswith('https://www.'):
        message.text = message.text[12:]
    elif message.text.startswith('https://'):
        message.text = message.text[8:]
    if (await state.get_data()).get("new_script_destination", -1) == -1 and not message.text.startswith('@'):
        markup = ReplyKeyboardMarkup(resize_keyboard=True).add("Отмена")
        await  message.answer(
            f"Неверный формат ссылки - {message.text}. Укажите канал в этом формате:\n*Формат* - @yourchannel",
            reply_markup=markup, parse_mode="Markdown")
        return 0

    if not (message.text.startswith('@') or message.text.startswith("vk.com/") or message.text.startswith("youtube.com/") or message.text.startswith("dzen.ru/")):
        await  message.answer(
            f"Неверный формат ссылки - {message.text}. Укажите ссылку в одном из этих форматов:\n*Telegram* - @yourchannel\n*Вконтакте* - vk.com/anyyourgroup\n*Youtube* - youtube.com/anychannel\n*Дзен* - dzen.ru/anyname",
            reply_markup=markup, parse_mode="Markdown")
        return 0

    # Проверка источника на валидность
    if (await state.get_data()).get('new_script_destination', -1) != -1:
        result = await is_source_accessable(message.text)
        if not result[0]:
            await message.answer(text=result[1], parse_mode="Markdown")
            return 0



    # Проверка канала для публикации на валидность
    if (await state.get_data()).get('new_script_destination', -1) == -1:
        try:
            chat_info = dict(await bot.get_chat(chat_id=message.text))
            if not "invite_link" in chat_info.keys():
                await message.answer("Сначало вам необходимо добавить бота в этот канал как администратора. Сделайте это чтоб продолжить создание сценария")
                return 0
        except ChatNotFound:
            await message.answer("Такого канала не существует. Проверьте правильность написания ссылки и повторите попытку")
            return 0
        except BotKicked:
            await message.answer("Бот был удален из этого канала. Сначало вам необходимо добавить бота в этот канал как администратора. Сделайте это чтоб продолжить создание сценария")
            return 0
        except Exception:
            await message.answer("Ошибка, что-то пошло не так")
            return 0


    if (await state.get_data()).get('new_script_destination', -1) == -1:
        await state.update_data(new_script_destination=message.text)
        await message.answer(
            "Хорошо!\nА теперь отправте ссылки на все источники с которых вы хотите получать публикации.\n*Поддерживаемые соцсети: Telegram, Youtube, VK, Дзен*\nФормат ссылок:\n*Telegram* - @yourchannel\n*Вконтакте* - vk.com/anyyourgroup\n*Youtube* - youtube.com/anychannel\n*Дзен* - dzen.ru/anyname\n*Отправляйте по 1 ссылке в одном сообщении! По завершению добавления источников нажмите кнопку завершения создания скрипта*",
            reply_markup=markup, parse_mode="Markdown")
    else:
        if (await state.get_data()).get('new_script_sources', -1) == -1:
            await state.update_data(new_script_sources=[message.text])
        else:
            async with state.proxy() as data:
                data['new_script_sources'].append(message.text)

# vk get token state

# @dp.message_handler(lambda message: message.text.lower() == "Позже" or message.text.lower() == "Авторизоваться", state="VK_GET_TOKEN")
async def get_vk_token_command(message: types.Message, state: FSMContext):
    if message.text.lower() == "позже":
        await process_scripts_command(message=message)
        async with state.proxy() as data:
            data.pop('new_script_mode')
            data.pop('new_script_sources')
            data.pop('new_script_destination')
    elif message.text.lower() == "авторизоваться":
        markup = ReplyKeyboardMarkup(resize_keyboard=True).add("Отмена", "Готово")
        await message.answer(
            f"Для авторизации в Вконтакте перейдите по ссылке - https://oauth.vk.com/authorize?client_id={ConfigKeys.VK_APPLICATION_ID}&redirect_uri=https://{ConfigKeys.VK_AUTH_DOMAIN}/vk&display=page&response_type=code&scope=466964&state={message.from_user.id}\nПосле того, как вы получите сообщение об успешной авторизации, нажмите - 'Готово'",
            reply_markup=markup)



# @dp.message_handler(lambda message: message.text.lower() == "отмена" or message.text.lower() == "готово", state="VK_GET_TOKEN")
async def check_vk_token_command(message: types.Message, state: FSMContext):
    if message.text.lower() == "отмена":
        await process_scripts_command(message=message)
        async with state.proxy() as data:
            data.pop('new_script_mode')
            data.pop('new_script_sources')
            data.pop('new_script_destination')
    elif message.text.lower() == "готово":
        vk_access_token = (
            await table_execute(f"SELECT VK_ACCESS_TOKEN FROM USERS WHERE USER_ID = {message.from_user.id}", is_return=True))[0]
        if vk_access_token is not None:
            await message.answer(
                "*Вы успешно авторизовались в Вконтакте*\nВы можете изменить это в настройках аккаунта",
                parse_mode="Markdown")
            await start_telegram_script(user_id=message.from_user.id,
                                        script_name=(await state.get_data()).get('new_script_destination'))
            await process_scripts_command(message=message)
            async with state.proxy() as data:
                data.pop('new_script_mode')
                data.pop('new_script_sources')
                data.pop('new_script_destination')
        else:
            await message.answer(
                "*Что-то пошло не так*\nВыполните действия по ссылке еще раз или повторите попытку позже",
                parse_mode="Markdown")
