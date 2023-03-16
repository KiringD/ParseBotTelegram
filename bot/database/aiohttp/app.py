import asyncio
import requests
from aiohttp import web

from ..methods import table_execute
from ...misc import ConfigKeys


async def handle(request):
    query = request.query
    code = query["code"]
    user_id = query["state"]
    url = f"https://oauth.vk.com/access_token?client_id={ConfigKeys.VK_APPLICATION_ID}&client_secret={ConfigKeys.VK_APPLICATION_KEY}&redirect_uri=https://botovbot.ru/vk&code={code}"
    response = requests.get(url)
    access_token = response.json()["access_token"]
    vk_user_id = response.json()["user_id"]
    await table_execute(f"UPDATE USERS SET VK_ACCESS_TOKEN='{access_token}' WHERE USER_ID={user_id}")
    await table_execute(f"UPDATE USERS SET VK_USER_ID={vk_user_id} WHERE USER_ID={user_id}")
    return web.Response(text="Вы успешно авторизовались! Вы можете закрыть эту вкладку браузера")


app = web.Application()
app.add_routes([web.get('/vk', handle)])


def start_aiohttp_server():
    loop = asyncio.get_event_loop()
    loop.create_task(web._run_app(app, host=ConfigKeys.http_host, port=ConfigKeys.http_port))
