import configparser

class ConfigKeys:
    config = configparser.ConfigParser()
    config.read("config.ini")

    TOKEN = config['Aiogram']['TOKEN']
    SQL_INFO = config['Aiogram']['SQL_INFO']


    api_id = config['Telegram']['api_id']
    api_hash = config['Telegram']['api_hash']
    username = config['Telegram']['username']
    trash_chat_id = config['Telegram']['trash_chat_id']

    http_host = config['Aiohttp']['http_host']
    http_port = config['Aiohttp']['http_port']

    LOCAL_VK_TOKEN = config['VK']['LOCAL_VK_TOKEN']
    VK_APPLICATION_KEY = config['VK']['VK_APPLICATION_KEY']
    VK_APPLICATION_ID = config['VK']['VK_APPLICATION_ID']
    VK_AUTH_DOMAIN = config['VK']['VK_AUTH_DOMAIN']

    telegram_host = config['Telegram_bot_api_server']['telegram_host']
    telegram_port = config['Telegram_bot_api_server']['telegram_port']

