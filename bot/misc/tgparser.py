import asyncio
import os

from .configdata import ConfigKeys

from aiogram.types import InputFile

from telethon.sync import TelegramClient
from telethon import events
from telethon.utils import pack_bot_file_id

# классы для работы с каналами
from telethon.tl.functions.channels import JoinChannelRequest
from telethon.tl.types import MessageMediaPhoto, MessageMediaDocument, DocumentAttributeFilename


from .util import new_post, get_file_id

# Присваиваем значения внутренним переменным
api_id   = ConfigKeys.api_id
api_hash = ConfigKeys.api_hash
username = ConfigKeys.username

waiting_media_group = {}
waiting_media_group_counter = {}


client = TelegramClient(username, api_id, api_hash)

client.start()

running_handlers=[]

async def start_handler(channels):
	print(channels)
	with open("subscribed_channels.txt", "r") as file:
		old_file = file.read()
		tg_subsribed_channels = old_file.split()
	if isinstance(channels, str):
		if channels not in tg_subsribed_channels:
			with open("subscribed_channels.txt", "w") as file:
				file.write(old_file + " " + channels)
			await client(JoinChannelRequest(channels))
		running_handlers.append(channels)
		clear_running_handlers = list(set(running_handlers))
		client.remove_event_handler(tghandler)
		client.add_event_handler(tghandler, events.NewMessage(chats=clear_running_handlers))

	elif isinstance(channels, list):
		new_channels = ""
		for chat in channels:
			if chat not in tg_subsribed_channels:
				new_channels += " " + chat
				await client(JoinChannelRequest(chat))
			with open("subscribed_channels.txt", "w") as file:
				file.write(old_file + new_channels)
			running_handlers.append(chat)
		clear_running_handlers = list(set(running_handlers))
		client.remove_event_handler(tghandler)
		client.add_event_handler(tghandler, events.NewMessage(chats=clear_running_handlers))

	print(client.list_event_handlers())
async def stop_handler(channels):
	try:
		if isinstance(channels, str):
			running_handlers.remove(channels)
			clear_running_handlers = list(set(running_handlers))
			client.remove_event_handler(tghandler)
			client.add_event_handler(tghandler, events.NewMessage(chats=clear_running_handlers))

		elif isinstance(channels, list):
			for chat in channels:
				running_handlers.remove(chat)
			clear_running_handlers = list(set(running_handlers))
			client.remove_event_handler(tghandler)
			client.add_event_handler(tghandler, events.NewMessage(chats=clear_running_handlers))
	except Exception:
		pass


async def tghandler(event):
	chat = await event.get_chat()
	username = chat.username
	if username is None:
		username = chat.usernames[0].username
	    
	source = '@' + username

	media_type = None

	if event.message.grouped_id is not None:
		if event.message.grouped_id not in waiting_media_group.keys():
			waiting_media_group[event.message.grouped_id] = {"photo": [], "video": [], "doc": []}
			waiting_media_group_counter[event.message.grouped_id] = 0
			if isinstance(event.media, MessageMediaPhoto):
				media_type = "photo"
			elif isinstance(event.media, MessageMediaDocument):
				if event.media.to_dict()["document"]["mime_type"] == "video/mp4" \
					or event.media.to_dict()["document"]["mime_type"] == "video/webm" \
					or event.media.to_dict()["document"]["mime_type"] == "video/quicktime":
					media_type = "video"
				else:
					media_type = "doc"
			if media_type == "doc":
				doc_id = event.document.id
				doc_attrs = event.document.attributes
				file_name = ""
				for attr in doc_attrs:
					if isinstance(attr, DocumentAttributeFilename):
						file_name = attr.to_dict()["file_name"]
				await event.download_media(file=f'tgMedia/docs/{doc_id}.temp')
				doc_file = InputFile(f'tgMedia/docs/{doc_id}.temp', filename=file_name)
				file_id = await get_file_id(doc_file, media_type)
				os.remove(f'tgMedia/docs/{doc_id}.temp')

			else:
				file_id = await get_file_id(f'https://t.me/{source[1:]}/{event.message.id}', media_type)
			waiting_media_group[event.message.grouped_id][media_type].append(file_id)
			await asyncio.sleep(2)
			while waiting_media_group_counter[event.message.grouped_id] != 0:
				await asyncio.sleep(2)
			waiting_media_group_counter.pop(event.message.grouped_id)
		else:
			waiting_media_group_counter[event.message.grouped_id] += 1
			if isinstance(event.media, MessageMediaPhoto):
				media_type = "photo"
			elif isinstance(event.media, MessageMediaDocument):
				if event.media.to_dict()["document"]["mime_type"] == "video/mp4" \
					or event.media.to_dict()["document"]["mime_type"] == "video/webm" \
					or event.media.to_dict()["document"]["mime_type"] == "video/quicktime":
					media_type = "video"
				else:
					media_type = "doc"

			if media_type == "doc":
				doc_id = event.document.id
				doc_attrs = event.document.attributes
				file_name = ""
				for attr in doc_attrs:
					if isinstance(attr, DocumentAttributeFilename):
						file_name = attr.to_dict()["file_name"]
				await event.download_media(file=f'tgMedia/docs/{doc_id}.temp')
				doc_file = InputFile(f'tgMedia/docs/{doc_id}.temp', filename=file_name)
				file_id = await get_file_id(doc_file, media_type)
				os.remove(f'tgMedia/docs/{doc_id}.temp')
			else:
				file_id = await get_file_id(f'https://t.me/{source[1:]}/{event.message.id}', media_type)
			waiting_media_group[event.message.grouped_id][media_type].append(file_id)
			waiting_media_group_counter[event.message.grouped_id] -= 1
			return 0

		media = waiting_media_group[event.message.grouped_id]
		if len(waiting_media_group[event.message.grouped_id]['photo']) == 0:
			media.pop('photo')
		if len(waiting_media_group[event.message.grouped_id]['video']) == 0:
			media.pop('video')
		if len(waiting_media_group[event.message.grouped_id]['doc']) == 0:
			media.pop('doc')

		waiting_media_group.pop(event.message.grouped_id)
	else:
		if event.media is not None:
			if isinstance(event.media, MessageMediaPhoto):
				media_type = "photo"
			elif isinstance(event.media, MessageMediaDocument):
				if event.media.to_dict()["document"]["mime_type"] == "video/mp4" \
					or event.media.to_dict()["document"]["mime_type"] == "video/webm" \
					or event.media.to_dict()["document"]["mime_type"] == "video/quicktime":
					media_type = "video"
				else:
					media_type = "doc"
		if media_type == "doc":
				doc_id = event.document.id
				doc_attrs = event.document.attributes
				file_name = ""
				for attr in doc_attrs:
					if isinstance(attr, DocumentAttributeFilename):
						file_name = attr.to_dict()["file_name"]
				await event.download_media(file=f'tgMedia/docs/{doc_id}.temp')
				doc_file = InputFile(f'tgMedia/docs/{doc_id}.temp', filename=file_name)
				file_id = await get_file_id(doc_file, media_type)
				os.remove(f'tgMedia/docs/{doc_id}.temp')
		elif media_type is not None:
			file_id = await get_file_id(f'https://t.me/{source[1:]}/{event.message.id}', media_type)

		if media_type is None:
			media = {}
		else:
			media = {media_type: [file_id]}

	raw_text = event.raw_text
	message_id = event.message.id

	media["text"] = raw_text
	media["message_id"] = message_id
	await new_post(source = source, media = media, raw_text = raw_text, message_id = message_id)
