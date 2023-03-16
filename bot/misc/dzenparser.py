from bs4 import BeautifulSoup
from requests_html import AsyncHTMLSession

import asyncio


from bot.misc.util import new_post


async def start_handler(channels: str | list):
    loop = asyncio.get_event_loop()
    all_tasks = []
    for i in asyncio.all_tasks():
        all_tasks.append(i.get_name())

    if isinstance(channels, list):
        for channel in channels:
            if channel not in all_tasks:
                loop.create_task(dzen_handler(channel=channel), name=channel)
                all_tasks.append(channel)
    else:
        if channels not in all_tasks:
            loop.create_task(dzen_handler(channel=channels), name=channels)

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

async def get_html(session,URL):
    r = await session.get(URL)
    return r
    
async def dzen_handler(channel: str):
    print(channel)

    # print(driver.page_source)
    session = AsyncHTMLSession()

    request = await get_html(session,"https://" + channel)
    await request.html.arender(sleep=1)


    soup = BeautifulSoup(request.html.html, "html.parser")
    await session.close()

    main_script = str(soup.find('body').find('script'))
    i = 0
    prev_posts_ids = []
    for b in range(6):
        location = main_script.find('"shareLink":"https://dzen.ru/', i)
        if location == -1:
            break
        default_str_size = 29
        while True:
            if main_script[location + default_str_size] != '"':
                default_str_size += 1
            else:
                break
        prev_posts_ids.append(main_script[location+29:location + default_str_size])
        i = location + default_str_size

    while True:
        await asyncio.sleep(60)

        session = AsyncHTMLSession()

        request = request = await get_html(session,"https://" + channel)
        await request.html.arender(sleep=1)
        # print(driver.page_source)

        soup = BeautifulSoup(request.html.html, "html.parser")
        await session.close()


        posts_ids = []
        new_posts_count = 0

        main_script = str(soup.find('body').find('script'))
        i = 0
        for b in range(6):
            location = main_script.find('"shareLink":"https://dzen.ru/', i)
            if location == -1:
                break
            default_str_size = 29
            while True:
                if main_script[location + default_str_size] != '"':
                    default_str_size += 1
                else:
                    break
            posts_ids.append(main_script[location + 29:location + default_str_size])
            i = location + default_str_size

        for post_id in posts_ids:
            if post_id not in prev_posts_ids:
                new_posts_count+=1
        if new_posts_count != 0:
            prev_posts_ids = posts_ids


            all_cooked = []

            rows = soup.findAll('div', {'class': 'feed__row'})
            for news_offset in range(new_posts_count):
                cooked = {}
                news = rows[news_offset]
                # print(news)
                statia = news.find('a', {'class': 'card-image-compact-view__clickable'}, href=True)
                video = news.find('a', {'class': 'card-video-2-view__clickable'}, href=True)
                picture = news.findAll('span', {'class': 'zen-ui-rich-text__text _color_primary'})
                # print(picture)
                text = ""
                if statia is not None:
                    text = statia.get('aria-label')
                if video is not None:
                    text = video.get('aria-label')
                if len(picture) != 0:
                    strii = ""
                    for label in picture:
                        strii += label.text
                    text = strii

                cooked['text'] = f"{text}\n\nhttps://dzen.ru/{prev_posts_ids[news_offset]}"
                if prev_posts_ids[news_offset].startswith("video"):
                    cooked['message_id'] = prev_posts_ids[news_offset][12:12+11]
                else:
                    cooked['message_id'] = prev_posts_ids[news_offset][2:2 + 11]
                all_cooked.append(cooked)

            for cooked in all_cooked:
                await new_post(source=channel, message_id=cooked['message_id'], raw_text=cooked["text"], media=cooked)
