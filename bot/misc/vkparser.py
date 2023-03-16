import urllib.request
import json
import os

from aiogram.types import InputFile

import yt_dlp
import asyncio

from .util import new_post, get_file_id

ydl_opts = {
    'format': 'best',
    'quiet': True,
    'outtmpl': 'vkMedia/videos/%(id)s.mp4',
    'ignoreerrors': True,
}


async def start_handler(groups: str | list, access_token: str):
    loop = asyncio.get_event_loop()
    all_tasks = []
    for i in asyncio.all_tasks():
        all_tasks.append(i.get_name())

    if isinstance(groups, list):
        for group in groups:
            if group not in all_tasks:
                group_url = group[7:]
                loop.create_task(vk_handler(group_url=group_url, access_token=access_token), name=group)
                all_tasks.append(group)
    else:
        if groups not in all_tasks:
            group_url = groups[7:]
            loop.create_task(vk_handler(group_url=group_url, access_token=access_token), name=groups)

async def stop_handler(groups: str | list):
    loop = asyncio.get_event_loop()
    if isinstance(groups, list):
        for i in asyncio.all_tasks():
            if i.get_name() in groups:
                i.cancel()
    else:
        for i in asyncio.all_tasks():
            if i.get_name() == groups:
                i.cancel()


async def vk_handler(group_url: str, access_token: str):
    group_id_raw = json.loads((urllib.request.urlopen(
        'https://api.vk.com/method/utils.resolveScreenName?screen_name=' + group_url + '&v=5.131&access_token=' + access_token)).read().decode(
        'utf-8'))

    try:
        while int(group_id_raw['error']['error_code']) == 6:
            await  asyncio.sleep(3)
            group_id_raw = json.loads((urllib.request.urlopen(
                'https://api.vk.com/method/utils.resolveScreenName?screen_name=' + group_url + '&v=5.131&access_token=' + access_token)).read().decode(
                'utf-8'))
    except Exception:
        pass
    group_id = str(group_id_raw['response']['object_id'])

    a = urllib.request.urlopen(
        'https://api.vk.com/method/wall.get?owner_id=-' + group_id + '&filter=owner&count=2&offset=' + "0" + '&v=5.131&access_token=' + access_token)
    out = a.read().decode('utf-8')
    json_data = json.loads(out)
    try:
        while int(json_data['error']['error_code']) == 6:
            await  asyncio.sleep(3)
            a = urllib.request.urlopen(
                'https://api.vk.com/method/wall.get?owner_id=-' + group_id + '&filter=owner&count=2&offset=' + "0" + '&v=5.131&access_token=' + access_token)
            out = a.read().decode('utf-8')
            json_data = json.loads(out)
    except Exception:
        pass
    if int(json_data['response']['items'][1]['id']) > int(json_data['response']['items'][0]['id']):
        last_post_id = int(json_data['response']['items'][1]['id'])
    else:
        last_post_id = int(json_data['response']['items'][0]['id'])
    while True:
        await asyncio.sleep(60)
        a = urllib.request.urlopen(
            'https://api.vk.com/method/wall.get?owner_id=-' + group_id + '&filter=owner&count=2&offset=' + "0" + '&v=5.131&access_token=' + access_token)
        out = a.read().decode('utf-8')
        json_data = json.loads(out)

        try:
            while int(json_data['error']['error_code']) == 6:
                await asyncio.sleep(3)
                a = urllib.request.urlopen(
                    'https://api.vk.com/method/wall.get?owner_id=-' + group_id + '&filter=owner&count=2&offset=' + "0" + '&v=5.131&access_token=' + access_token)
                out = a.read().decode('utf-8')
                json_data = json.loads(out)
        except Exception:
            pass

        if int(json_data['response']['items'][1]['id']) > int(json_data['response']['items'][0]['id']):
            if int(json_data['response']['items'][1]['id']) > last_post_id:
                posts_diff = int(json_data['response']['items'][1]['id']) - last_post_id
                last_post_id = int(json_data['response']['items'][1]['id'])
                cooked = await get_post_info(json_data['response']['items'][1], posts_diff=posts_diff,
                                             last_post_id=last_post_id, access_token=access_token)
                cooked.reverse()
                for post in cooked:
                    if not (len(post.keys()) == 2 and post['text'] == ''):
                        await new_post(source=f'vk.com/{group_url}', raw_text=post['text'], media=post,
                                       message_id=post['message_id'])
        else:
            if int(json_data['response']['items'][0]['id']) > last_post_id:
                posts_diff = int(json_data['response']['items'][0]['id']) - last_post_id
                last_post_id = int(json_data['response']['items'][0]['id'])
                cooked = await get_post_info(json_data['response']['items'][0], posts_diff=posts_diff,
                                             last_post_id=last_post_id, access_token=access_token)
                cooked.reverse()
                for post in cooked:
                    if not (len(post.keys()) == 2 and post['text'] == ''):
                        await new_post(source=f'vk.com/{group_url}', raw_text=post['text'], media=post,
                                       message_id=post['message_id'])


async def get_post_info(json_data, posts_diff: int, last_post_id: int, access_token: str):
    group_id = str(json_data['owner_id'])[1:]
    posts = []
    print("Post_diff = ", posts_diff)
    if posts_diff != 1:
        for i in range(posts_diff):
            post_id = '-' + str(group_id) + '_' + str(last_post_id - i)
            a = urllib.request.urlopen(
                'https://api.vk.com/method/wall.getById?posts=' + post_id + '&v=5.131&access_token=' + access_token)
            out = a.read().decode('utf-8')
            json_data = json.loads(out)
            try:
                while int(json_data['error']['error_code']) == 6:
                    await  asyncio.sleep(3)
                    a = urllib.request.urlopen(
                        'https://api.vk.com/method/wall.getById?posts=' + post_id + '&v=5.131&access_token=' + access_token)
                    out = a.read().decode('utf-8')
                    json_data = json.loads(out)
            except Exception as e:
                pass
            is_deleted = False
            try:
                is_deleted = json_data['response'][0]['is_deleted']
            except IndexError:
                is_deleted = True
            except Exception:
                pass

            if not is_deleted:
                posts.append(json_data['response'][0])
    else:
        posts.append(json_data)

    all_cooked = []
    for post in posts:
        cooked = {}

        text = post['text']
        # убираем html требуху
        text = text.replace('<br>', '\n')
        text = text.replace('&amp', '&')
        text = text.replace('&quot', '"')
        text = text.replace('&apos', "'")
        text = text.replace('&gt', '>')
        text = text.replace('&lt', '<')

        if len(text) < 4096:
            cooked['text'] = text
        else:
            cooked['text'] = ""

        message_id = post['id']
        cooked['message_id'] = message_id

        # на случай встречи с медиафайлами
        try:
            media = post['attachments']

            photo_arr = []
            video_arr = []
            doc_arr = []
            for i in media:
                # print(i)
                if "photo" in i:
                    width = i["photo"]["sizes"][0]["width"]
                    for size in i["photo"]["sizes"]:
                        new_width = size["width"]
                        if new_width > width:
                            width = new_width
                            url = size["url"]

                    # print(url)
                    # photo_arr.append('https://vk.com/photo' + str(i['photo']['owner_id']) + '_' + str(i['photo']['id']))
                    file_id = await get_file_id(url, "photo")
                    photo_arr.append(file_id)
                    cooked['photo'] = photo_arr
                if "video" in i:
                    a = urllib.request.urlopen(
                        'https://api.vk.com/method/video.get?owner_id=-' + group_id + '&videos=' + str(
                            i["video"]["owner_id"]) + "_" + str(i["video"]["id"]) + '&count=1&offset=' + "0" + '&filter=owner&v=5.131&extended=0&access_token=' + access_token)
                    out = a.read().decode('utf-8')
                    json_video_data = json.loads(out)

                    try:
                        while int(json_data['error']['error_code']) == 6:
                            await  asyncio.sleep(3)
                            a = urllib.request.urlopen(
                                'https://api.vk.com/method/video.get?owner_id=-' + group_id + '&videos=' + str(
                                    i["video"]["owner_id"]) + "_" + str(i["video"][ "id"]) + '&count=1&offset=' + "0" + '&filter=owner&v=5.131&extended=0&access_token=' + access_token)
                            out = a.read().decode('utf-8')
                            json_video_data = json.loads(out)
                    except Exception:
                        pass
                    # print(json_data)
                    player_url = json_video_data["response"]["items"][0]["player"]
                    print(player_url)
                    loop = asyncio.get_event_loop()
                    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                        await loop.run_in_executor(None, lambda: ydl.download([player_url]))
                    video_path = f'vkMedia/videos/{json_video_data["response"]["items"][0]["owner_id"]}_{json_video_data["response"]["items"][0]["id"]}.mp4'
                    stats = os.stat(video_path)
                    size = stats.st_size
                    # print(size)

                    if size < 2086666240:
                        video_file = InputFile(video_path, filename=video_path)
                        # print(i["video"])
                        file_id = await get_file_id(video_file, "video")
                        video_arr.append(file_id)
                        # print(video_arr)
                        cooked['video'] = video_arr

                    os.remove(video_path)

                if "doc" in i:
                    title = i['doc']['title']
                    owner_id = i['doc']['owner_id']
                    doc_id = i['doc']['id']
                    size = i['doc']['size']

                    if size < 2086666240:
                        if not os.path.isfile(f"vkMedia/docs/{owner_id}_{doc_id}_{title}"):
                            urllib.request.urlretrieve(i['doc']['url'],
                                                       f"vkMedia/docs/{owner_id}_{doc_id}_{title}")
                        doc_file = InputFile(f"vkMedia/docs/{owner_id}_{doc_id}_{title}", filename=title)
                        file_id = await get_file_id(doc_file, "doc")
                        doc_arr.append(file_id)

                        cooked['doc'] = doc_arr
                        os.remove(f"vkMedia/docs/{owner_id}_{doc_id}_{title}")

        except Exception as e:
            pass
        # print(traceback.format_exc())
        all_cooked.append(cooked)
    print(all_cooked)
    return all_cooked

