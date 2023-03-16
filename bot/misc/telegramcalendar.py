#!/usr/bin/env python3
#
# A library that allows to create an inline calendar keyboard.
# grcanosa https://github.com/grcanosa
#
"""
Base methods for calendar keyboard creation and processing.
"""


from aiogram.types import ReplyKeyboardRemove, \
    ReplyKeyboardMarkup, KeyboardButton, \
    InlineKeyboardMarkup, InlineKeyboardButton
import datetime
import calendar
import asyncio

CALENDAR_CALLBACK = "CALENDAR"

start_message = "Hey {}! I am calender bot \n \n Please type /calendar or /jcalendar to view my power"

calendar_message = "Please select a date: "

calendar_response_message = "You selected %s"

async def separate_callback_data(data):
    """ Separate the callback data"""
    return data.split(";")

async def create_callback_data(action,year,month,day):
    """ Create the callback data associated to each button"""
    return CALENDAR_CALLBACK + ";" + ";".join([action,str(year),str(month),str(day)])


async def create_calendar(year=None,month=None, posts_info=None, remove_day=(None)):
    """
    Create an inline keyboard with the provided year and month
    :param int year: Year to use in the calendar, if None the current year is used.
    :param int month: Month to use in the calendar, if None the current month is used.
    :return: Returns the InlineKeyboardMarkup object with the calendar.
    """

    posts_dates = []
    if posts_info is not None:
        for post_date in posts_info:
            if post_date['date_post'] is not None:
                posts_dates.append(tuple(map(int, post_date['date_post'].split('-'))))

    # print(posts_dates)

    now = datetime.datetime.now()
    if year == None: year = now.year
    if month == None: month = now.month
    data_ignore = await create_callback_data("IGNORE", year, month, 0)
    data_deny = await create_callback_data("DENY", year, month, 0)
    keyboard = []
    #First row - Month and Year
    row=[]
    row.append(InlineKeyboardButton(calendar.month_name[month]+" "+str(year),callback_data=data_ignore))
    keyboard.append(row)
    #Second row - Week Days
    row=[]
    for day in ["Mo","Tu","We","Th","Fr","Sa","Su"]:
        row.append(InlineKeyboardButton(day,callback_data=data_ignore))
    keyboard.append(row)

    my_calendar = calendar.monthcalendar(year, month)
    for week in my_calendar:
        row=[]
        for day in week:
            if(day==0):
                row.append(InlineKeyboardButton(" ",callback_data=data_ignore))
            else:
                # print((year, month, day), remove_day)
                if (year, month, day) == remove_day:
                    row.append(InlineKeyboardButton("☓", callback_data=data_ignore))
                elif (year, month, day) in posts_dates:
                    row.append(InlineKeyboardButton(str(day)+' ●',callback_data=await create_callback_data("DAY",year,month,day)))
                elif int(day)<int(now.day) and int(month) == int(now.month) and int(year) == int(now.year):
                    row.append(InlineKeyboardButton("☓",callback_data=data_ignore))
                else:
                    row.append(InlineKeyboardButton(str(day),callback_data=await create_callback_data("DAY",year,month,day)))
        keyboard.append(row)
    #Last row - Buttons
    row=[]
    if int(year) != int(now.year) or int(month) != int(now.month):
        row.append(InlineKeyboardButton("<",callback_data=await create_callback_data("PREV-MONTH",year,month,day)))
    else:
        row.append(InlineKeyboardButton(" ",callback_data=data_ignore))
    row.append(InlineKeyboardButton("Отмена",callback_data=data_deny))
    row.append(InlineKeyboardButton(">",callback_data=await create_callback_data("NEXT-MONTH",year,month,day)))
    keyboard.append(row)
    # print(InlineKeyboardMarkup(inline_keyboard=keyboard))

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


async def process_calendar_selection(bot, callback_query, posts_info=None, remove_day=(None)):
    """
    Process the callback_query. This method generates a new calendar if forward or
    backward is pressed. This method should be called inside a CallbackQueryHandler.
    :param telegram.Bot bot: The bot, as provided by the CallbackQueryHandler
    :param telegram.Update update: The update, as provided by the CallbackQueryHandler
    :return: Returns a tuple (Boolean,datetime.datetime), indicating if a date is selected
                and returning the date if so.
    """
    ret_data = (False,None)
    # print(query)
    (_,action,year,month,day) = await separate_callback_data(callback_query.data)
    curr = datetime.datetime(int(year), int(month), 1)
    if action == "IGNORE":
        await bot.answer_callback_query(callback_query.id)
    elif action == "DENY":
        ret_data = True, "DENY"
    elif action == "DAY":
        await bot.edit_message_text(text=callback_query.message.text,
            chat_id=callback_query.message.chat.id,
            message_id=callback_query.message.message_id
            )
        ret_data = True,datetime.date(int(year),int(month),int(day))
    elif action == "PREV-MONTH":
        pre = curr - datetime.timedelta(days=1)
        if posts_info is None:
            await bot.edit_message_text(text=callback_query.message.text,
                chat_id=callback_query.message.chat.id,
                message_id=callback_query.message.message_id,
                reply_markup=await create_calendar(int(pre.year),int(pre.month)))
        else:
            await bot.edit_message_text(text=callback_query.message.text,
                chat_id=callback_query.message.chat.id,
                message_id=callback_query.message.message_id,
                reply_markup=await create_calendar(int(pre.year),int(pre.month),posts_info=posts_info, remove_day=remove_day))
    elif action == "NEXT-MONTH":
        ne = curr + datetime.timedelta(days=31)
        if posts_info is None:
            await bot.edit_message_text(text=callback_query.message.text,
                chat_id=callback_query.message.chat.id,
                message_id=callback_query.message.message_id,
                reply_markup=await create_calendar(int(ne.year),int(ne.month)))
        else:
            await bot.edit_message_text(text=callback_query.message.text,
                chat_id=callback_query.message.chat.id,
                message_id=callback_query.message.message_id,
                reply_markup=await create_calendar(int(ne.year),int(ne.month),posts_info=posts_info, remove_day=remove_day))
    else:
        bot.answer_callback_query(callback_query_id= callback_query.id, text="Something went wrong!")
        # UNKNOWN
    return ret_data
