#account state
import json
import traceback

from aiogram import types, Bot
from aiogram.bot.api import TelegramAPIServer
from aiogram.dispatcher import FSMContext
from aiogram.types import ReplyKeyboardMarkup

from .main import start_menu, process_account_command, Form
from ...database.methods import table_execute
from ...misc import TgKeys, ConfigKeys
from ...misc.util import stop_telegram_script

local_server = TelegramAPIServer.from_base(f'http://{ConfigKeys.telegram_host}:{ConfigKeys.telegram_port}')

bot = Bot(token=TgKeys.TOKEN, server=local_server, parse_mode='HTML')

# @dp.message_handler(lambda message: message.text.lower() == "удалить аккаунт", state="ACCOUNT_STATE")
async def process_delete_account_command(message: types.Message):
    markup = ReplyKeyboardMarkup(resize_keyboard=True).add("Отмена", "Удалить")
    await message.answer("Вы точно хотите удалить этот аккаунт?\n*ПРЕДУПРЕЖДЕНИЕ*\nПосле удаления аккаунта вы потеряете абсолютно все сценарии, а также оставшиеся дни премиум подписки!!", reply_markup=markup, parse_mode= "Markdown")
    await Form.DELETE_ACCOUNT_STATE.set()

# @dp.message_handler(lambda message: message.text.lower() == "вернуться", state="ACCOUNT_STATE")
async def process_return_from_account_command(message: types.Message):
    await start_menu(message=message)

# todo
# @dp.message_handler(lambda message: message.text.lower() == "оформить подписку", state="ACCOUNT_STATE")
async def process_subscription_command(message: types.Message):
    await message.answer("*#TODO* Ссылка на оплату подписки", parse_mode= "Markdown")

# @dp.message_handler(lambda message: message.text.lower() == "отвязать вконтакте", state="ACCOUNT_STATE")
async def process_unconnect_vk(message: types.Message):
    await table_execute(f"UPDATE users SET vk_access_token=null WHERE user_id={message.from_user.id}")
    await table_execute(f"UPDATE users SET vk_user_id=null WHERE user_id={message.from_user.id}")
    running_scripts = json.loads((await table_execute(f"SELECT running_scripts FROM USERS WHERE USER_ID = {message.from_user.id}", is_return=True))[0])
    user_scripts = json.loads((await table_execute(f"SELECT LINKS FROM USERS WHERE USER_ID = {message.from_user.id}", is_return=True))[0])
    for script_key in user_scripts.keys():
        if script_key in running_scripts:
            vk_channels = []
            for source in user_scripts[script_key][1]:
                if "vk.com" in source:
                    vk_channels.append(source)
                    break

            if len(vk_channels) != 0:
                await stop_telegram_script(user_id=message.from_user.id, script_name=script_key)
    await message.answer(
        "Вы успешно отвязали Вконтакте\n*Внимание*\nНе забудьте, что все ваши сценарии содержашие источники из Вконтакте перестанут работать",
        parse_mode="Markdown")
    await process_account_command(message=message)


# @dp.message_handler(lambda message: message.text.lower() == "подключить вконтакте", state="ACCOUNT_STATE")
async def process_connect_vk(message: types.Message):
    markup = ReplyKeyboardMarkup(resize_keyboard=True).add("Отмена", "Готово")
    await message.answer(
        f"Для авторизации в Вконтакте перейдите по ссылке - https://oauth.vk.com/authorize?client_id={ConfigKeys.VK_APPLICATION_ID}&redirect_uri=https://botovbot.ru/vk&display=page&response_type=code&scope=466964&state={message.from_user.id}\nПосле того, как вы получите сообщение об успешной авторизации, нажмите - 'Готово'",
        reply_markup=markup)
    await Form.ACCOUNT_CONNECT_VK_STATE.set()


# account connect vk state

# @dp.message_handler(lambda message: message.text.lower() == "отмена" or message.text.lower() == "готово", state="ACCOUNT_CONNECT_VK_STATE")
async def process_connect_vk_confirm(message: types.Message):
    if message.text.lower() == "отмена":
        await process_account_command(message=message)
    elif message.text.lower() == "готово":
        vk_access_token = (
            await table_execute(f"SELECT VK_ACCESS_TOKEN FROM USERS WHERE USER_ID = {message.from_user.id}", is_return=True))[0]
        if vk_access_token is not None:
            await message.answer(
                "*Вы успешно авторизовались в Вконтакте*",
                parse_mode="Markdown")
            await process_account_command(message=message)
        else:
            await message.answer(
                "*Что-то пошло не так*\nВыполните действия по ссылке еще раз или повторите попытку позже",
                parse_mode="Markdown")

# delete account state
# @dp.message_handler(lambda message: message.text.lower() == "удалить" or message.text.lower() == "отмена" or message.text.lower() == "совершенно точно удалить", state="DELETE_ACCOUNT_STATE")
async def account_deletion_confirm(message: types.Message, state: FSMContext):
    text = message.text.lower()
    if text == "удалить":
        markup = ReplyKeyboardMarkup(resize_keyboard=True).add("Отмена", "Совершенно точно удалить")
        await message.answer("Вы совершенно точно хотите удалить аккаунт?\n*ЭТО ДЕЙСТВИЕ НЕЛЬЗЯ БУДЕТ ОТМЕНИТЬ*",reply_markup=markup, parse_mode= "Markdown")
    elif text == "совершенно точно удалить":
        try:
            running_scripts = json.loads((await table_execute(f"SELECT RUNNING_SCRIPTS FROM USERS WHERE USER_ID = {message.from_user.id}",is_return=True))[0])
            for script_name in running_scripts:
                await stop_telegram_script(user_id=message.from_user.id, script_name=script_name)
        except Exception as e:
            print(traceback.format_exc())
        await table_execute(f"DELETE FROM USERS WHERE USER_ID = {message.from_user.id}")
        markup = ReplyKeyboardMarkup(resize_keyboard=True).add("/start")
        await message.answer("Аккаунт полностью удален",reply_markup=markup)
        await state.finish()
    elif text == "отмена":
        await process_account_command(message=message)
