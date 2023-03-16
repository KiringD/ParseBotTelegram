from youtubesearchpython import Playlist, playlist_from_channel_id

from aiogram.types import InputFile
import os
import asyncio
import pytube
import yt_dlp

from bot.misc.util import new_post, get_file_id

ydl_opts = {
    'format': 'bestvideo+bestaudio',
    'quiet': True,
    'outtmpl': 'ytMedia/%(id)s',
    'ignoreerrors': True,
    'merge_output_format': 'mp4',
}

async def start_handler(channels: str | list):
    loop = asyncio.get_event_loop()
    all_tasks = []
    for i in asyncio.all_tasks():
        all_tasks.append(i.get_name())

    if isinstance(channels, list):
        for channel in channels:
            if channel not in all_tasks:
                loop.create_task(yt_handler(channel=channel), name=channel)
                all_tasks.append(channel)
    else:
        if channels not in all_tasks:
            loop.create_task(yt_handler(channel=channels), name=channels)

async def stop_handler(channels: str | list):
    loop = asyncio.get_event_loop()
    if isinstance(channels, list):
        for i in asyncio.all_tasks():
            if i.get_name() in channels:
                i.cancel()
    else:
        for i in asyncio.all_tasks():
            if i.get_name() == channels:
                i.cancel()


async def yt_handler(channel: str):
    print(channel)
    channel_id = pytube.Channel(channel).channel_id
    print(channel_id)

    playlist = Playlist(playlist_from_channel_id(channel_id))

    print(f'Videos Retrieved: {len(playlist.videos)}')
    prev_videos_ids = []
    for video in playlist.videos:
        prev_videos_ids.append((video['id'], video['title']))

    while True:
        await asyncio.sleep(60)

        playlist = Playlist(playlist_from_channel_id(channel_id))
        
        videos_ids = []
        new_videos = []
        for video in playlist.videos:
            videos_ids.append((video['id'], video['title']))
        for video_id in videos_ids:
            if video_id not in prev_videos_ids:
                new_videos.append(video_id)
        if len(new_videos) != 0:
            new_videos.reverse()
            prev_videos_ids = videos_ids
            print(new_videos)

            all_cooked = []
            loop = asyncio.get_event_loop()
            for video in new_videos:
                cooked = {}
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    await loop.run_in_executor(None, lambda: ydl.download('https://www.youtube.com/watch?v=' + video[0]))
                try:
                    video_path = f'ytMedia/{video[0]}.mp4'
                    stats = os.stat(video_path)
                    size = stats.st_size
                except Exception:
                    prev_videos_ids.remove(video)
                    continue

                if size < 2086666240:
                    video_file = InputFile(video_path, filename=video_path)
                    # print(i["video"])
                    file_id = await get_file_id(video_file, "video")
                    video_title = video[1]
                    cooked["text"] = video_title
                    cooked["video"] = [file_id]
                    cooked["message_id"] = video[0]

                os.remove(video_path)
                all_cooked.append(cooked)

            for cooked in all_cooked:
                await new_post(source=channel, message_id=cooked['message_id'], raw_text=cooked["text"], media=cooked)
