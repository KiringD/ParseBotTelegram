import json

from aiogram import Dispatcher, types
from aiogram.dispatcher.filters.state import StatesGroup, State
from aiogram.types import ReplyKeyboardMarkup

from ...database.methods import create_account, table_execute


class Form(StatesGroup):
    START_STATE = State()
    MAIN_STATE = State()
    ACCOUNT_STATE = State()
    WAITING_POSTS_STATE = State()
    SCRIPTS_STATE = State()
    CALENDAR_STATE = State()
    DELETE_ACCOUNT_STATE = State()
    WAITING_POSTS_SET_DATE_STATE = State()
    WAITING_POSTS_SET_TIME_STATE = State()
    WAITING_POST_EDITING_STATE = State()
    WAITING_POST_EDITING_TEXT_STATE = State()
    WAITING_POST_EDITING_MEDIA_STATE = State()
    CREATE_SCRIPT_STATE = State()
    SCRIPT_CONFIG_STATE = State()
    SCRIPT_SETTINGS_STATE = State()
    SOURCES_CHANGE_STATE = State()
    ADD_SOURCE_STATE = State()
    MODE_STATE = State()
    CALENDAR_EDITING_STATE = State()
    CALENDAR_EDITING_TEXT_STATE = State()
    CALENDAR_EDITING_MEDIA_STATE = State()
    CALENDAR_POSTS_SET_DATE_STATE = State()
    CALENDAR_POSTS_SET_TIME_STATE = State()
    CALENDAR_DAY_STATE = State()
    VK_GET_TOKEN = State()
    ACCOUNT_CONNECT_VK_STATE = State()
    TEST_STATE = State()


def register_user_handlers(dp: Dispatcher):
    dp.register_message_handler(callback=base_command)
    dp.register_message_handler(callback=process_start_command, state="*", commands=['start'])
    dp.register_message_handler(callback=process_help_command, state="*", commands=['help'])
    # dp.register_message_handler(callback=gg, state="*", commands=['gg'])
    # start state
    dp.register_message_handler(start_menu, lambda message: message.text.lower() == "возможности" or message.text.lower() == "начать работу",state=Form.START_STATE)
    # main state
    dp.register_message_handler(process_account_command, lambda message: message.text.lower() == "аккаунт", state=Form.MAIN_STATE)
    dp.register_message_handler(process_waiting_posts_command, lambda message: message.text.lower() == "ожидающие публикации", state=Form.MAIN_STATE)
    dp.register_message_handler(process_scripts_command, lambda message: message.text.lower() == "сценарии", state=Form.MAIN_STATE)
    dp.register_message_handler(process_calendar_command, lambda message: message.text.lower() == "календарь публикаций", state=Form.MAIN_STATE)
    # calendar state
    dp.register_message_handler(process_calendar_script_back_command, lambda message: message.text.lower() == "вернуться", state=[Form.CALENDAR_STATE, Form.CALENDAR_DAY_STATE, Form.CALENDAR_EDITING_STATE])
    dp.register_message_handler(callback=process_calendar_script_command, state=[Form.CALENDAR_STATE, Form.CALENDAR_DAY_STATE])
    dp.register_callback_query_handler(callback=callback_calendar, state=Form.CALENDAR_STATE)
    # calendar day state
    dp.register_callback_query_handler(callback_calendar_set_date_post, lambda c: c.data.startswith("date"), state=Form.CALENDAR_DAY_STATE)
    dp.register_callback_query_handler(callback_calendar_delete_post, lambda c:  c.data.startswith("delete"), state=Form.CALENDAR_DAY_STATE)
    dp.register_callback_query_handler(callback_calendar_to_post_post, lambda c:  c.data.startswith("post"), state=Form.CALENDAR_DAY_STATE)
    dp.register_callback_query_handler(callback_calendar_set_time_post, lambda c:  c.data.startswith("time"), state=Form.CALENDAR_DAY_STATE)
    dp.register_callback_query_handler(callback_calendar_settings_post, lambda c: c.data.startswith("set"), state=Form.CALENDAR_DAY_STATE)
    dp.register_callback_query_handler(callback_calendar_settings_back_post, lambda c: c.data.startswith("back"), state=Form.CALENDAR_DAY_STATE)
    dp.register_callback_query_handler(callback_calendar_settings_author_post, lambda c: c.data.startswith("author"), state=Form.CALENDAR_DAY_STATE)
    dp.register_callback_query_handler(callback_calendar_edit_post, lambda c: c.data.startswith("edit"), state=Form.CALENDAR_DAY_STATE)
    # calendar editing state
    dp.register_callback_query_handler(callback_calendar_edit_return, lambda c: c.data.startswith("return"), state=Form.CALENDAR_EDITING_STATE)
    dp.register_callback_query_handler(callback_calendar_edit_del_text, lambda c: c.data.startswith("del t"), state=Form.CALENDAR_EDITING_STATE)
    dp.register_callback_query_handler(callback_calendar_edit_del_media, lambda c: c.data.startswith("del m"), state=Form.CALENDAR_EDITING_STATE)
    dp.register_callback_query_handler(callback_calendar_edit_back, lambda c: c.data.startswith("back"), state=Form.CALENDAR_EDITING_STATE)
    dp.register_callback_query_handler(callback_calendar_edit_del_media_rm, lambda c: c.data.startswith("rm"), state=Form.CALENDAR_EDITING_STATE)
    dp.register_callback_query_handler(callback_calendar_edit_edit_text, lambda c: c.data.startswith("ed t"), state=Form.CALENDAR_EDITING_STATE)
    dp.register_callback_query_handler(callback_calendar_edit_edit_media, lambda c: c.data.startswith("ed m"), state=Form.CALENDAR_EDITING_STATE)
    # calendar editing text state
    dp.register_message_handler(calendar_edit_text, state=Form.CALENDAR_EDITING_TEXT_STATE)
    # calendar editing media state
    dp.register_message_handler(calendar_edit_media, content_types=types.ContentType.ANY, state=Form.CALENDAR_EDITING_MEDIA_STATE)
    # calendar set date state
    dp.register_callback_query_handler(callback=set_date_inline_calendar_handler, state=Form.CALENDAR_POSTS_SET_DATE_STATE)
    # calendar set time state
    dp.register_callback_query_handler(set_hour_inline_calendar_handler, lambda c: c.data.startswith("hour"), state=Form.CALENDAR_POSTS_SET_TIME_STATE)
    dp.register_callback_query_handler(set_minute_inline_calendar_handler, lambda c: c.data.startswith("minute"), state=Form.CALENDAR_POSTS_SET_TIME_STATE)
    # account state
    dp.register_message_handler(process_delete_account_command, lambda message: message.text.lower() == "удалить аккаунт", state=Form.ACCOUNT_STATE)
    dp.register_message_handler(process_return_from_account_command, lambda message: message.text.lower() == "вернуться", state=Form.ACCOUNT_STATE)
    dp.register_message_handler(process_subscription_command, lambda message: message.text.lower() == "оформить подписку", state=Form.ACCOUNT_STATE)
    dp.register_message_handler(process_connect_vk, lambda message: message.text.lower() == "подключить вконтакте", state=Form.ACCOUNT_STATE)
    dp.register_message_handler(process_unconnect_vk, lambda message: message.text.lower() == "отвязать вконтакте", state=Form.ACCOUNT_STATE)
    # delete account state
    dp.register_message_handler(account_deletion_confirm, lambda message: message.text.lower() == "удалить" or message.text.lower() == "отмена" or message.text.lower() == "совершенно точно удалить", state=Form.DELETE_ACCOUNT_STATE)
    # waiting_posts state
    dp.register_message_handler(process_waiting_posts_script_return_command, lambda message: message.text.lower() == "вернуться", state=[Form.WAITING_POSTS_STATE, Form.WAITING_POST_EDITING_STATE, Form.WAITING_POSTS_SET_TIME_STATE, Form.WAITING_POSTS_SET_DATE_STATE])
    dp.register_message_handler(process_waiting_posts_script_command, state=Form.WAITING_POSTS_STATE)
    dp.register_callback_query_handler(callback_set_date_post, lambda c: c.data.startswith("time"), state=Form.WAITING_POSTS_STATE)
    dp.register_callback_query_handler(callback_delete_post, lambda c: c.data.startswith("delete"), state=Form.WAITING_POSTS_STATE)
    dp.register_callback_query_handler(callback_to_post_post, lambda c: c.data.startswith("post"), state=Form.WAITING_POSTS_STATE)
    dp.register_callback_query_handler(callback_settings_post, lambda c: c.data.startswith("set"), state=Form.WAITING_POSTS_STATE)
    dp.register_callback_query_handler(callback_settings_back_post, lambda c: c.data.startswith("back"), state=Form.WAITING_POSTS_STATE)
    dp.register_callback_query_handler(callback_settings_author_post, lambda c: c.data.startswith("author"), state=Form.WAITING_POSTS_STATE)
    dp.register_callback_query_handler(callback_edit_post, lambda c: c.data.startswith("edit"), state=Form.WAITING_POSTS_STATE)
    dp.register_callback_query_handler(callback_continue_command, lambda c: c.data.startswith("cont"), state=Form.WAITING_POSTS_STATE)
    # Waiting posts set date state
    dp.register_callback_query_handler(callback_waiting_set_date_post, state=Form.WAITING_POSTS_SET_DATE_STATE)
    # waiting posts set time state
    dp.register_callback_query_handler(set_hour_inline_waiting_post_handler, lambda c: c.data.startswith("hour"), state=Form.WAITING_POSTS_SET_TIME_STATE)
    dp.register_callback_query_handler(set_minute_inline_waiting_post_handler, lambda c: c.data.startswith("minute"), state=Form.WAITING_POSTS_SET_TIME_STATE)
    # Waiting posts editing state
    dp.register_callback_query_handler(callback_edit_return_post, lambda c: c.data.startswith("return"), state=Form.WAITING_POST_EDITING_STATE)
    dp.register_callback_query_handler(callback_edit_del_text_post, lambda c: c.data.startswith("del t"), state=Form.WAITING_POST_EDITING_STATE)
    dp.register_callback_query_handler(callback_edit_del_media_post, lambda c: c.data.startswith("del m"), state=Form.WAITING_POST_EDITING_STATE)
    dp.register_callback_query_handler(callback_edit_edit_text_post, lambda c: c.data.startswith("ed t"), state=Form.WAITING_POST_EDITING_STATE)
    dp.register_callback_query_handler(callback_edit_edit_media_post, lambda c: c.data.startswith("ed m"), state=Form.WAITING_POST_EDITING_STATE)
    dp.register_callback_query_handler(callback_edit_back_post, lambda c: c.data.startswith("back"), state=Form.WAITING_POST_EDITING_STATE)
    dp.register_callback_query_handler(callback_edit_del_media_rm_post, lambda c: c.data.startswith("rm"), state=Form.WAITING_POST_EDITING_STATE)
    # Waiting post editing text state
    dp.register_message_handler(edit_text_post, state=Form.WAITING_POST_EDITING_TEXT_STATE)
    # Waiting post editing text state
    dp.register_message_handler(edit_media_post, content_types=types.ContentType.ANY, state=Form.WAITING_POST_EDITING_MEDIA_STATE)
    # Scripts state
    dp.register_message_handler(process_return_from_scripts_command, lambda message: message.text.lower() == "вернуться", state=Form.SCRIPTS_STATE)
    dp.register_message_handler(process_create_script_command, lambda message: message.text.lower() == "создать сценарий", state=Form.SCRIPTS_STATE)
    dp.register_message_handler(process_scripts_config_command, state=Form.SCRIPTS_STATE)
    # script settings state
    dp.register_callback_query_handler(callback_script_settings, state=Form.SCRIPT_SETTINGS_STATE)
    # script config state
    dp.register_message_handler(process_script_config_back_command, state=Form.SCRIPT_CONFIG_STATE)
    dp.register_callback_query_handler(callback_change_deny, lambda c: c.data.startswith("deny_change"), state=Form.SCRIPT_CONFIG_STATE)
    dp.register_callback_query_handler(callback_change_mode, lambda c: c.data.startswith("mode_change"), state=Form.SCRIPT_CONFIG_STATE)
    dp.register_callback_query_handler(callback_change_sources, lambda c: c.data.startswith("sources_change"), state=Form.SCRIPT_CONFIG_STATE)
    # Sources change state
    dp.register_callback_query_handler(callback_confirm_sources_change, lambda c: c.data.startswith("confirm_sources_change"), state=Form.SOURCES_CHANGE_STATE)
    dp.register_callback_query_handler(callback_delete_source, lambda c: c.data.startswith("delete"), state=Form.SOURCES_CHANGE_STATE)
    dp.register_callback_query_handler(callback_add_source, lambda c: c.data.startswith("add_source"), state=Form.SOURCES_CHANGE_STATE)
    # Add source state
    dp.register_message_handler(process_add_source_command, state=Form.ADD_SOURCE_STATE)
    # Create script state
    dp.register_message_handler(process_choose_script_mode_command, lambda message: message.text.lower() == "1" or message.text.lower() == "2", state=Form.CREATE_SCRIPT_STATE)
    dp.register_message_handler(process_cancel_command, lambda message: message.text.lower() == "отмена", state=[Form.CREATE_SCRIPT_STATE, Form.MODE_STATE])
    # Mode state
    dp.register_message_handler(process_end_script_creation_command, lambda message: message.text.lower() == "завершить создание скрипта", state=Form.MODE_STATE)
    dp.register_message_handler(process_channel_link_command, state=Form.MODE_STATE)
    # Vk get token state
    dp.register_message_handler(get_vk_token_command, lambda message: message.text.lower() == "позже" or message.text.lower() == "авторизоваться", state=Form.VK_GET_TOKEN)
    dp.register_message_handler(check_vk_token_command, lambda message: message.text.lower() == "отмена" or message.text.lower() == "готово", state=Form.VK_GET_TOKEN)
    # Account connect vk state
    dp.register_message_handler(process_connect_vk_confirm, lambda message: message.text.lower() == "отмена" or message.text.lower() == "готово", state=Form.ACCOUNT_CONNECT_VK_STATE)

# async def gg(message: types.Message):
#     await Form.TEST_STATE.set()

# base handler
# @dp.message_handler()
async def base_command(message: types.Message):
    if await create_account(message=message, is_return=True):
        await start_menu(message=message)
    else:
        await process_start_command(message=message)


# any state
# @dp.message_handler(state="*", commands=['start'])
async def process_start_command(message: types.Message):
    await create_account(message=message)
    markup = ReplyKeyboardMarkup(resize_keyboard=True).add("Возможности", "Начать работу")
    await message.answer("Привет!\nЯ помогу тебе с публикациями в твоих телеграм каналах.", reply_markup=markup)
    await Form.START_STATE.set()

# @dp.message_handler(state="*", commands=['help'])
async def process_help_command(message: types.Message):
    await message.answer(
        "Этот бот может работать в 2 режимах:\n1) Вы можете указать несколько источников из которых бот будет получать публикации и предоставлять их вам на модерацию, после чего публиковать в ваших каналах с указанными вами настройками.\n2) Вы можете указать несколько источников из которых бот будет получать публикации и автоматически публиковать их в ваших каналах\nПоддерживаемые соцсети: Telegram, Youtube, VK, Дзен")


# start_state
# @dp.message_handler(lambda message: message.text.lower() == "возможности" or message.text.lower() == "начать работу", state="START_STATE")
async def start_menu(message: types.Message):
    if message.text == "Возможности":
        markup = ReplyKeyboardMarkup(resize_keyboard=True).add("Начать работу")
        await message.answer(
            "Этот бот может работать в 2 режимах:\n1) Вы можете указать несколько источников из которых бот будет получатьпубликации и предоставлять их вам на модерацию, после чего публиковать в ваших каналах с указанными вами настройками.\n2) Вы можете указать несколько источников из которых бот будет получать публикации и автоматически публиковать их в ваших каналах\nПоддерживаемые соцсети: Telegram, Youtube, VK, Дзен",
            reply_markup=markup)
    else:
        markup = ReplyKeyboardMarkup(resize_keyboard=True).row("Сценарии", "Аккаунт").row("Ожидающие публикации",
                                                                                          "Календарь публикаций")
        await message.answer("Что вы хотите?", reply_markup=markup)
        await Form.MAIN_STATE.set()

# main state
# @dp.message_handler(lambda message: message.text.lower() == "аккаунт", state="MAIN_STATE")
async def process_account_command(message: types.Message):
    sub = await table_execute(f"SELECT SUBSCRIPTION FROM USERS WHERE USER_ID = {message.from_user.id}",is_return=True)
    payed_for = await table_execute(f"SELECT PAYED_FOR FROM USERS WHERE USER_ID = {message.from_user.id}",is_return=True)
    vk_token = await table_execute(f"SELECT VK_ACCESS_TOKEN FROM USERS WHERE USER_ID = {message.from_user.id}",is_return=True)
    vk_user_id = await table_execute(f"SELECT VK_USER_ID FROM USERS WHERE USER_ID = {message.from_user.id}",is_return=True)
    if payed_for[0] is None:
        payed_status = "Подписка не активна"
    elif not sub[0]:
        date = payed_for[0].strftime("%m/%d/%Y")
        payed_status = f"Подписка не активна\nПремиум функции будут доступны до {date}"
    else:
        date = payed_for[0].strftime("%m/%d/%Y")
        payed_status = f"Подписка активна\nДата следующего списания - {date}"

    if vk_token[0] is None:
        vk_token_status =  "Вы не авторизованы через Вконтакте"
        markup = ReplyKeyboardMarkup(resize_keyboard=True).add("Вернуться", "Подключить Вконтакте", "Удалить аккаунт").row("Оформить подписку")
    else:
        vk_token_status = f"Вы авторизованы через аккаунт - vk.com/id{vk_user_id[0]}"
        markup = ReplyKeyboardMarkup(resize_keyboard=True).add("Вернуться", "Отвязать Вконтакте", "Удалить аккаунт").row("Оформить подписку")

    await message.answer(f"Имя пользователя: *{message.from_user.full_name}*\nId: *{message.from_user.id}*\nСтатус премиум подписки: *{payed_status}*\nСтатус привязки Вконтакте: *{vk_token_status}*",
                         reply_markup=markup, parse_mode="Markdown")
    await Form.ACCOUNT_STATE.set()

# @dp.message_handler(lambda message: message.text.lower() == "ожидающие публикации", state="MAIN_STATE")
async def process_waiting_posts_command(message: types.Message):
    user_saved_posts = json.loads((await table_execute(f"SELECT SAVED_POSTS FROM USERS WHERE USER_ID = {message.from_user.id}",is_return=True))[0])
    unconfigured_posts = {}
    for key in user_saved_posts.keys():
        for post in user_saved_posts[key]:
            if post['date_post'] == None:
                if key in unconfigured_posts:
                    unconfigured_posts[key].append(post)
                else:
                    unconfigured_posts[key] = [post]

    if len(unconfigured_posts.keys()) == 0:
        markup = ReplyKeyboardMarkup(resize_keyboard=True).row("Сценарии", "Аккаунт").row("Ожидающие публикации", "Календарь публикаций")
        await message.answer("У вас нет ожидающих публикаций", reply_markup=markup)
    else:
        markup = ReplyKeyboardMarkup(resize_keyboard=True).row("Вернуться")
        for script in unconfigured_posts.keys():
            markup.row(script)
        await message.answer("Выберите канал для которого хотите посмотреть ожидающие публикации" ,reply_markup=markup)
        await Form.WAITING_POSTS_STATE.set()

# @dp.message_handler(lambda message: message.text.lower() == "сценарии", state="MAIN_STATE")
async def process_scripts_command(message: types.Message):
    markup = ReplyKeyboardMarkup(resize_keyboard=True).add("Вернуться", "Создать сценарий")
    current_scripts = json.loads((await table_execute(f"SELECT LINKS FROM USERS WHERE USER_ID = {message.from_user.id}",is_return=True))[0])
    for key in current_scripts.keys():
        markup.row(key)

    # print(await table_execute(f"SELECT LINKS FROM USERS WHERE USER_ID = {message.from_user.id}",is_return=True))
    await message.answer("Ваши сценарии:",reply_markup=markup)
    await Form.SCRIPTS_STATE.set()

# @dp.message_handler(lambda message: message.text.lower() == "календарь публикаций", state="MAIN_STATE")
async def process_calendar_command(message: types.Message):
    all_user_scripts = json.loads((await table_execute(f"SELECT LINKS FROM USERS WHERE USER_ID = {message.from_user.id}",is_return=True))[0])
    if len(all_user_scripts) == 0:
        markup = ReplyKeyboardMarkup(resize_keyboard=True).row("Сценарии", "Аккаунт").row("Ожидающие публикации", "Календарь публикаций")
        await message.answer("У вас еще нет ни одного сценария", reply_markup=markup)
    else:
        markup = ReplyKeyboardMarkup(resize_keyboard=True).row("Вернуться")
        for script in all_user_scripts.keys():
            markup.row(script)
        await message.answer("Выберите канал для которого хотите посмотреть ожидающие публикации" ,reply_markup=markup)
        await Form.CALENDAR_STATE.set()

from .account import process_delete_account_command, process_return_from_account_command, process_subscription_command, \
    account_deletion_confirm, process_connect_vk, process_unconnect_vk, process_connect_vk_confirm
from .calendar import process_calendar_script_command, callback_calendar, \
    set_date_inline_calendar_handler, callback_calendar_set_date_post, callback_calendar_delete_post, \
    callback_calendar_to_post_post, callback_calendar_set_time_post, set_hour_inline_calendar_handler, \
    set_minute_inline_calendar_handler, callback_calendar_settings_post, callback_calendar_settings_back_post, \
    callback_calendar_settings_author_post, callback_calendar_edit_post, callback_calendar_edit_return, \
    callback_calendar_edit_del_text, callback_calendar_edit_del_media, callback_calendar_edit_back, \
    callback_calendar_edit_del_media_rm, callback_calendar_edit_edit_text, callback_calendar_edit_edit_media, \
    calendar_edit_text, calendar_edit_media, process_calendar_script_back_command
from .script import process_return_from_scripts_command, process_create_script_command, process_scripts_config_command, \
    process_script_config_back_command, callback_change_deny, callback_change_mode, callback_change_sources, \
    callback_confirm_sources_change, callback_delete_source, callback_add_source, process_add_source_command, \
    process_choose_script_mode_command, process_cancel_command, process_end_script_creation_command, \
    process_channel_link_command, check_vk_token_command, callback_script_settings
from .waiting_posts import process_waiting_posts_script_command, callback_set_date_post, callback_delete_post, \
    callback_to_post_post, callback_edit_post, callback_waiting_set_date_post, set_hour_inline_waiting_post_handler, \
    set_minute_inline_waiting_post_handler, callback_settings_post, callback_settings_back_post, \
    callback_settings_author_post, callback_edit_return_post, callback_edit_del_text_post, \
    process_waiting_posts_script_return_command, callback_edit_del_media_post, callback_edit_back_post, \
    callback_edit_del_media_rm_post, edit_text_post, \
    callback_edit_edit_text_post, callback_edit_edit_media_post, edit_media_post, callback_continue_command
from .script import get_vk_token_command
