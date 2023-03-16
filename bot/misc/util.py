import asyncio
import json
import traceback
import urllib.request
import os
from datetime import datetime
import pytube
import requests

from aiogram import Bot, types

import psycopg2
from aiogram.bot.api import TelegramAPIServer
from aiogram.types import MediaGroup, InputMediaPhoto, InputMediaVideo, InputMediaDocument, InputFile
from aiogram.utils.exceptions import RetryAfter

from . import TgKeys

from ..database.methods import table_execute
from .configdata import ConfigKeys

local_server = TelegramAPIServer.from_base(f'http://{ConfigKeys.telegram_host}:{ConfigKeys.telegram_port}')

bot = Bot(token=TgKeys.TOKEN, server=local_server, parse_mode='HTML')


def start_all_scripts():

    con = psycopg2.connect(ConfigKeys.SQL_INFO)
    cur = con.cursor()
    cur.execute("SELECT USER_ID FROM USERS")
    try:
        users = [i[0] for i in cur.fetchall()]
    except Exception:
        print(traceback.format_exc())
        return 0
    for user in users:
        cur.execute(f"SELECT RUNNING_SCRIPTS FROM USERS WHERE USER_ID = {user}")
        try:
            loop = asyncio.get_event_loop()
            user_running_scripts = json.loads(list(cur.fetchone())[0])
            cur.execute(f"SELECT LINKS FROM USERS WHERE USER_ID = {user}")
            links = json.loads(cur.fetchone()[0])
            for script_key in links.keys():
                if script_key in user_running_scripts:
                    # проверка канала для публикации на валидность
                    if not is_channel_accessable(script_key):
                        user_running_scripts.remove(script_key)
                        cur.execute(
                            f"UPDATE USERS SET RUNNING_SCRIPTS = '{json.dumps(user_running_scripts)}' WHERE USER_ID = {user}")
                        con.commit()
                        continue

                    telegram_channels = []
                    vk_channels = []
                    yt_channels = []
                    dzen_channels = []
                    flag = True
                    for source in links[script_key][1]:
                        if not is_source_accessable(source):
                            flag = False
                        if source[0] == "@":
                            telegram_channels.append(source)
                        elif "vk.com" in source:
                            vk_channels.append(source)
                        elif "youtube.com" in source:
                            yt_channels.append(source)
                        elif "dzen.ru" in source:
                            dzen_channels.append(source)

                    # проверка источника на валидность
                    if flag == False:
                        user_running_scripts.remove(script_key)
                        cur.execute(
                            f"UPDATE USERS SET RUNNING_SCRIPTS = '{json.dumps(user_running_scripts)}' WHERE USER_ID = {user}")
                        con.commit()
                        continue

                    if len(telegram_channels) != 0:
                        loop.create_task(tgparser.start_handler(channels=telegram_channels))
                    if len(vk_channels) != 0:
                        cur.execute(f"SELECT VK_ACCESS_TOKEN FROM USERS WHERE USER_ID = {user}")
                        access_token = cur.fetchone()[0]
                        loop.create_task(
                            vkparser.start_handler(groups=vk_channels, access_token=access_token))
                    if len(yt_channels) != 0:
                        loop.create_task(ytparser.start_handler(channels=yt_channels))
                    if len(dzen_channels) != 0:
                        loop.create_task(dzenparser.start_handler(channels=dzen_channels))
        except Exception as e:
            print(traceback.format_exc())
    con.close()


def is_channel_accessable(channel_id):
    try:
        a = urllib.request.urlopen(
            f'https://api.telegram.org/bot{TgKeys.TOKEN}/getChat?chat_id={channel_id}')
        out = a.read().decode('utf-8')
        json_data = json.loads(out)['result']
        if not "invite_link" in json_data.keys():
            return False
    except Exception:
        return False
    return True


def is_source_accessable(source):
    if source.startswith('@'):
        try:
            a = urllib.request.urlopen(
                f'https://api.telegram.org/bot{TgKeys.TOKEN}/getChat?chat_id={source}')
            out = a.read().decode('utf-8')
            json_data = json.loads(out)['result']
        except Exception:
            return False
    elif source.startswith("vk.com/"):
        try:
            group_info = json.loads((urllib.request.urlopen(
                'https://api.vk.com/method/groups.getById?group_id=' + source[
                                                                       7:] + '&v=5.131&access_token=' + ConfigKeys.LOCAL_VK_TOKEN)).read().decode(
                'utf-8'))
            if group_info['response'][0]['is_closed'] == 1:
                return False
        except Exception:
            return False
    elif source.startswith("youtube.com/"):
        try:
            a = pytube.Channel(source).channel_id
        except Exception:
            return False
    elif source.startswith("dzen.ru/"):
        url = "https://" + source
        page = requests.get(url)
        if page.status_code != 200:
            return False
    return True


async def get_file_id(file, file_type):
    while True:
        try:
            result = None
            if file_type == "photo":
                msg = await bot.send_photo(photo=file, chat_id=ConfigKeys.trash_chat_id)
                result = msg.photo[0].file_id
            elif file_type == "video":
                msg = await bot.send_video(video=file, chat_id=ConfigKeys.trash_chat_id)
                result = msg.video.file_id
            elif file_type == "doc":
                msg = await bot.send_document(document=file, chat_id=ConfigKeys.trash_chat_id)
                result = msg.document.file_id
        except RetryAfter:
            continue
        return result


async def new_post(source: str | list, raw_text: str, user_id: int = None, message_id=None, media=None,
                   channel_to_post=None, settings=None):
    if settings is None:
        settings = {}
    con = psycopg2.connect(ConfigKeys.SQL_INFO)
    cur = con.cursor()

    if channel_to_post is None:
        cur.execute("SELECT USER_ID FROM USERS")
        users = [i[0] for i in cur.fetchall()]
        con.close()

        for user in users:
            all_user_scripts = json.loads(
                (await table_execute(f"SELECT LINKS FROM USERS WHERE USER_ID = {user}", is_return=True))[0])
            running_user_scripts = json.loads(
                (await table_execute(f"SELECT RUNNING_SCRIPTS FROM USERS WHERE USER_ID = {user}", is_return=True))[0])
            scripts_settings = json.loads((await table_execute(
                f"SELECT SCRIPTS_SETTINGS FROM USERS WHERE USER_ID = {user}", is_return=True))[0])
            for script_name in all_user_scripts.keys():
                print(script_name)
                if source in all_user_scripts[script_name][1] and script_name in running_user_scripts:
                    if all_user_scripts[script_name][0] == 1:
                        media_group = MediaGroup()
                        first_flag = False
                        document_media = None
                        if scripts_settings[script_name]["author"]:
                            raw_text += f"\n\nИсточник: {source}"
                        if 'photo' in media.keys():
                            for photo in media['photo']:
                                if not first_flag:
                                    if len(media['text']) < 1024:
                                        media_group.attach_photo(InputMediaPhoto(media=photo, caption=raw_text), '')
                                    else:
                                        if scripts_settings[script_name]["author"]:
                                            media_group.attach_photo(InputMediaPhoto(media=photo, caption=f"\n\nИсточник: {source}"), '')
                                        else:
                                            media_group.attach_photo(photo, '')
                                    first_flag = True
                                else:
                                    media_group.attach_photo(photo, '')
                        if 'video' in media.keys():
                            for video in media['video']:
                                if not first_flag:
                                    if len(media['text']) < 1024:
                                        media_group.attach_video(InputMediaVideo(media=video, caption=raw_text), '')
                                    else:
                                        if scripts_settings[script_name]["author"]:
                                            media_group.attach_video(
                                                InputMediaVideo(media=video, caption=f"\n\nИсточник: {source}"), '')
                                        else:
                                            media_group.attach_video(video, '')
                                    first_flag = True
                                else:
                                    media_group.attach_video(video, "")
                        if 'doc' in media.keys():
                            document_media = MediaGroup()
                            for doc in media['doc']:
                                if not first_flag:
                                    if len(raw_text) < 1024:
                                        document_media.attach_document(InputMediaDocument(media=doc, caption=raw_text),
                                                                       '')
                                    else:
                                        if scripts_settings[script_name]["author"]:
                                            document_media.attach_document(
                                                InputMediaDocument(media=doc, caption=f"\n\nИсточник: {source}"), '')
                                        else:
                                            document_media.attach_document(doc, '')
                                    first_flag = True
                                else:
                                    document_media.attach_document(doc, "")
                        if 'text' in media.keys() and first_flag is False:
                            await bot.send_message(chat_id=script_name, text=raw_text)
                        if first_flag:
                            if document_media is not None:
                                if len(media_group.to_python()) == 0:
                                    await bot.send_media_group(chat_id=script_name, media=document_media)
                                else:
                                    await bot.send_media_group(chat_id=script_name, media=media_group)
                                    await bot.send_media_group(chat_id=script_name, media=document_media)
                            else:
                                await bot.send_media_group(chat_id=script_name, media=media_group)

                    elif all_user_scripts[script_name][0] == 2:
                        user_saved_posts = json.loads((await table_execute(
                            f"SELECT SAVED_POSTS FROM USERS WHERE USER_ID = {user}", is_return=True))[0])
                        if len(user_saved_posts) == 0:
                            user_saved_posts = {script_name: [
                                {"media": media, "source": source, "message_id": message_id, "raw_text": raw_text,
                                 "date_post": None, "time_post": None, "settings": {}}]}
                        else:
                            if script_name in user_saved_posts.keys():
                                user_saved_posts[script_name].append(
                                    {"media": media, "source": source, "message_id": message_id, "raw_text": raw_text,
                                     "date_post": None, "time_post": None, "settings": {}})
                            else:
                                user_saved_posts[script_name] = [
                                    {"media": media, "source": source, "message_id": message_id, "raw_text": raw_text,
                                     "date_post": None, "time_post": None, "settings": {}}]
                        await table_execute(
                            f"UPDATE USERS SET SAVED_POSTS = '{json.dumps(user_saved_posts)}' WHERE USER_ID = {user}")
    else:
        media_group = MediaGroup()
        first_flag = False
        document_media = None
        scripts_settings = json.loads((await table_execute(
            f"SELECT SCRIPTS_SETTINGS FROM USERS WHERE USER_ID = {user_id}", is_return=True))[0])
        custom_author = settings.get('author', None)

        if custom_author is not None:
            if custom_author:
                raw_text += f"\n\nИсточник: {source}"
        else:
            if scripts_settings[channel_to_post]["author"]:
                raw_text += f"\n\nИсточник: {source}"
        if 'photo' in media.keys():
            for photo in media['photo']:
                if not first_flag:
                    if len(media['text']) < 1024:
                        media_group.attach_photo(InputMediaPhoto(media=photo, caption=raw_text), '')
                    else:
                        if custom_author is not None:
                            if custom_author:
                                media_group.attach_photo(InputMediaPhoto(media=photo, caption=f"\n\nИсточник: {source}"), '')
                        elif scripts_settings[channel_to_post]["author"]:
                            media_group.attach_photo(InputMediaPhoto(media=photo, caption=f"\n\nИсточник: {source}"), '')
                        else:
                            media_group.attach_photo(photo, '')
                    first_flag = True
                else:
                    media_group.attach_photo(photo, '')
        if 'video' in media.keys():
            for video in media['video']:
                if not first_flag:
                    if len(media['text']) < 1024:
                        media_group.attach_video(InputMediaVideo(media=video, caption=raw_text), '')
                    else:
                        if custom_author is not None:
                            if custom_author:
                                media_group.attach_video(
                                    InputMediaVideo(media=video, caption=f"\n\nИсточник: {source}"), '')
                        elif scripts_settings[channel_to_post]["author"]:
                            media_group.attach_video(InputMediaVideo(media=video, caption=f"\n\nИсточник: {source}"),
                                                     '')
                        else:
                            media_group.attach_video(video, '')
                    first_flag = True
                else:
                    media_group.attach_video(video, "")
        if 'doc' in media.keys():
            document_media = MediaGroup()
            for doc in media['doc']:
                if not first_flag:
                    if len(raw_text) < 1024:
                        document_media.attach_document(InputMediaDocument(media=doc, caption=media['text']), '')
                    else:
                        if custom_author is not None:
                            if custom_author:
                                document_media.attach_document(
                                    InputMediaDocument(media=doc, caption=f"\n\nИсточник: {source}"), '')
                        elif scripts_settings[channel_to_post]["author"]:
                            document_media.attach_document(InputMediaDocument(media=doc, caption=f"\n\nИсточник: {source}"),
                                                     '')
                        else:
                            document_media.attach_document(doc, '')
                    first_flag = True
                else:
                    document_media.attach_document(doc, "")
        if 'text' in media.keys() and first_flag is False:
            await bot.send_message(chat_id=channel_to_post, text=raw_text)
        if first_flag:
            if document_media is not None:
                if len(media_group.to_python()) == 0:
                    await bot.send_media_group(chat_id=channel_to_post, media=document_media)
                else:
                    await bot.send_media_group(chat_id=channel_to_post, media=media_group)
                    await bot.send_media_group(chat_id=channel_to_post, media=document_media)
            else:
                await bot.send_media_group(chat_id=channel_to_post, media=media_group)

    # if source.startswith('vk.com'):
    #     await vk_new_post(user_id=user_id, source=source, raw_text=raw_text, message_id=message_id, media=media,
    #                       channel_to_post=channel_to_post, settings=settings)
    #     # await vk_new_post(source = source, raw_text = raw_text, media = media, channel_to_post = channel_to_post)
    # elif source.startswith('@'):
    #     await tg_new_post(user_id=user_id, source=source, raw_text=raw_text, message_id=message_id, media=media,
    #                       channel_to_post=channel_to_post, settings=settings)
    #
    # elif source.startswith('youtube.com'):
    #     await yt_new_post(user_id=user_id, source=source, raw_text=raw_text, message_id=message_id, media=media, channel_to_post=channel_to_post, settings=settings)


async def start_telegram_script(user_id, script_name, update_db=True):
    script_info = \
    json.loads((await table_execute(f"SELECT LINKS FROM USERS WHERE USER_ID = {user_id}", is_return=True))[0])[
        script_name]
    # print(all_user_scripts)
    # mode = script_info[0]
    telegram_channels = []
    vk_channels = []
    yt_channels = []
    dzen_channels = []
    for script in script_info[1]:
        if script[0] == "@":
            telegram_channels.append(script)
        elif "vk.com" in script:
            vk_channels.append(script)
        elif "youtube.com" in script:
            yt_channels.append(script)
        elif "dzen.ru" in script:
            dzen_channels.append(script)

    if len(telegram_channels) != 0:
        await tgparser.start_handler(channels=telegram_channels)
    if len(vk_channels) != 0:
        access_token = \
        (await  table_execute(f"SELECT VK_ACCESS_TOKEN FROM USERS WHERE USER_ID = {user_id}", is_return=True))[0]
        await vkparser.start_handler(groups=vk_channels, access_token=access_token)
    if len(yt_channels) != 0:
        await ytparser.start_handler(yt_channels)
    if len(dzen_channels) != 0:
        await dzenparser.start_handler(dzen_channels)

    if update_db:
        bd_running_names = json.loads(
            (await table_execute(f"SELECT RUNNING_SCRIPTS FROM USERS WHERE USER_ID = {user_id}", is_return=True))[0])
        if len(bd_running_names) == 0:
            bd_running_names = [script_name]
        elif not script_name in bd_running_names:
            bd_running_names.append(script_name)
        else:
            return 0
        final_info = json.dumps(bd_running_names)
        await table_execute(f"UPDATE USERS SET RUNNING_SCRIPTS = '{final_info}' WHERE USER_ID = {user_id}")


async def stop_telegram_script(user_id, script_name, update_db=True):
    script_info = \
    json.loads((await table_execute(f"SELECT LINKS FROM USERS WHERE USER_ID = {user_id}", is_return=True))[0])[
        script_name]
    telegram_channels = []
    vk_channels = []
    yt_channels = []
    dzen_channels = []
    for script in script_info[1]:
        if script[0] == "@":
            telegram_channels.append(script)
        elif "vk.com" in script:
            vk_channels.append(script)
        elif "youtube.com" in script:
            yt_channels.append(script)
        elif "dzen.ru" in script:
            dzen_channels.append(script)

    if len(telegram_channels) != 0:
        await tgparser.stop_handler(channels=telegram_channels)
    if len(vk_channels) != 0:
        await vkparser.stop_handler(groups=vk_channels)
    if len(yt_channels) != 0:
        await ytparser.stop_handler(channels=yt_channels)
    if len(dzen_channels) != 0:
        await dzenparser.stop_handler(channels=dzen_channels)

    if update_db:
        running_scripts = json.loads(
            (await table_execute(f"SELECT RUNNING_SCRIPTS FROM USERS WHERE USER_ID = {user_id}", is_return=True))[0])
        if script_name in running_scripts:
            running_scripts.remove(script_name)
        else:
            return 0
        await table_execute(
            f"UPDATE USERS SET RUNNING_SCRIPTS = '{json.dumps(running_scripts)}' WHERE USER_ID = {user_id}")


async def post_calendar_service():
    while True:
        try:
            con = psycopg2.connect(ConfigKeys.SQL_INFO)
            cur = con.cursor()
            cur.execute("SELECT USER_ID FROM USERS")
            users = list(cur.fetchall()[0])
            con.close()

            for user in users:
                user_saved_posts = json.loads(
                    (await table_execute(f"SELECT SAVED_POSTS FROM USERS WHERE USER_ID = {user}", is_return=True))[0])
                for channel_to_post in user_saved_posts.keys():
                    for post in user_saved_posts[channel_to_post]:
                        if post['date_post'] is not None:
                            current_datetime = datetime.now()
                            current_date = current_datetime.strftime('%Y-%m-%d')
                            current_time = current_datetime.strftime('%H:%M')

                            if post['date_post'] < current_date or (
                                    post['date_post'] == current_date and post['time_post'] <= current_time):
                                # print(post[4] < current_date, (post[4] == current_date and post[5] <= current_time), post[5], current_time)
                                media = post['media']
                                channel_source = post['source']
                                channel_message_id = post['message_id']
                                raw_text = post['raw_text']
                                date_post = post['date_post']
                                time_post = post['time_post']
                                settings = post['settings']
                                if {"media": media, "source": channel_source, "message_id": channel_message_id,
                                    "raw_text": raw_text, "date_post": date_post, "time_post": time_post,
                                    "settings": settings} in user_saved_posts[channel_to_post]:
                                    user_saved_posts[channel_to_post].remove(
                                        {"media": media, "source": channel_source, "message_id": channel_message_id,
                                         "raw_text": raw_text, "date_post": date_post, "time_post": time_post,
                                         "settings": settings})
                                    if len(user_saved_posts[channel_to_post]) == 0:
                                        user_saved_posts.pop(channel_to_post)
                                    await table_execute(
                                        f"UPDATE USERS SET SAVED_POSTS = '{json.dumps(user_saved_posts)}' WHERE USER_ID = {user}")
                                await new_post(user_id=user, source=channel_source, channel_to_post=channel_to_post,
                                               media=media,
                                               raw_text=raw_text,
                                               message_id=channel_message_id, settings=settings)
        except Exception:
            pass
        await asyncio.sleep(1 * 60)


def start_post_calendar_service():
    loop = asyncio.get_event_loop()
    loop.create_task(post_calendar_service())


async def edit_saved_post(user_id, prev_channel_source, prev_message_id, channel_to_post, type, to_return=None,
                          media=None, source=None, message_id=None,
                          raw_text=None, date_post=None, time_post=None, settings=None):
    # types - remove, edit, none
    input = {"media": media, "source": source, "message_id": message_id, "raw_text": raw_text, "date_post": date_post,
             "time_post": time_post, "settings": settings}
    new = {}
    for key in input.keys():
        if input[key] is not None:
            new[key] = input[key]

    user_saved_posts = json.loads((await table_execute(
        f"SELECT SAVED_POSTS FROM USERS WHERE USER_ID = {user_id}", is_return=True))[0])
    if channel_to_post in user_saved_posts.keys():
        for post in user_saved_posts[channel_to_post]:
            if post['source'] == prev_channel_source and post['message_id'] == prev_message_id:
                media = post['media']
                raw_text = post['raw_text']
                date_post = post['date_post']
                time_post = post['time_post']
                settings = post['settings']

                raw_post = {"media": media, "source": prev_channel_source, "message_id": prev_message_id,
                            "raw_text": raw_text, "date_post": date_post, "time_post": time_post, "settings": settings}

                if raw_post in user_saved_posts[channel_to_post]:
                    index = user_saved_posts[channel_to_post].index(raw_post)
                    if type != 'none':
                        user_saved_posts[channel_to_post].remove(raw_post)
                        if type == 'edit':
                            # print(new)
                            for key in raw_post.keys():
                                if key in new.keys():
                                    raw_post[key] = new[key]
                            print(raw_post)

                            user_saved_posts[channel_to_post].insert(index, raw_post)
                        if len(user_saved_posts[channel_to_post]) == 0:
                            user_saved_posts.pop(channel_to_post)
                        await table_execute(
                            f"UPDATE USERS SET SAVED_POSTS = '{json.dumps(user_saved_posts)}' WHERE USER_ID = {user_id}")
    if to_return is not None:
        dict_to_return = {}
        for item in to_return:
            try:
                dict_to_return[item] = raw_post[item]
            except Exception:
                pass
        return dict_to_return


async def delete_conf_post(message: types.CallbackQuery | types.Message, channel_source, media):
    if isinstance(message, types.CallbackQuery):
        my_message_id = message.message.message_id
    else:
        my_message_id = message.message_id

    try:
        counter = 0
        for key in media.keys():
            if isinstance(media[key], list):
                for item in media[key]:
                    counter += 1
            else:
                counter += 1
        if counter == 2:
            counter = 3
        for i in range(counter):
            await bot.delete_message(chat_id=message.from_user.id,
                                     message_id=my_message_id - i)
    except Exception:
        pass
        # traceback.print_exc()


async def send_message_bot_chat(source, media, raw_text, chat_id):
    media_group = MediaGroup()
    first_flag = False
    document_media = None

    if 'photo' in media.keys():
        for photo in media['photo']:
            if first_flag is False:
                if len(raw_text) < 1024:
                    media_group.attach_photo(InputMediaPhoto(media=photo, caption=raw_text), '')
                else:
                    media_group.attach_photo(photo, '')
                first_flag = True
            else:
                media_group.attach_photo(photo, '')
    if 'video' in media.keys():
        for video in media['video']:
            if first_flag is False:
                if len(raw_text) < 1024:
                    media_group.attach_video(InputMediaVideo(media=video, caption=raw_text), '')
                else:
                    media_group.attach_video(video, '')
                first_flag = True
            else:
                media_group.attach_video(InputMediaVideo(media=video), "")
    if 'doc' in media.keys():
        document_media = MediaGroup()
        for doc in media['doc']:
            if first_flag is False:
                if len(raw_text) < 1024:
                    document_media.attach_document(InputMediaDocument(media=doc, caption=raw_text), '')
                else:
                    document_media.attach_document(doc, '')
                first_flag = True
            else:
                document_media.attach_document(InputMediaDocument(media=doc), "")
    if 'text' in media.keys() and first_flag is False:
        await bot.send_message(chat_id=chat_id, text=raw_text)
    if first_flag:
        if document_media is not None:
            if len(media_group.to_python()) == 0:
                await bot.send_media_group(chat_id=chat_id, media=document_media)
            else:
                await bot.send_media_group(chat_id=chat_id, media=media_group)
                await bot.send_media_group(chat_id=chat_id, media=document_media)
        else:
            await bot.send_media_group(chat_id=chat_id, media=media_group)

from . import tgparser, vkparser, ytparser, dzenparser
