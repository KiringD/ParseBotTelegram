import psycopg2
from aiogram import types
import json

from ...misc import ConfigKeys

async def table_execute(command, is_return=False):
    con = psycopg2.connect(ConfigKeys.SQL_INFO)
    cur = con.cursor()
    cur.execute(command)
    if is_return:
        tmp=cur.fetchone()
    con.commit()
    con.close()
    if is_return:
        return tmp

def table_create():
    con = psycopg2.connect(ConfigKeys.SQL_INFO)
    cur = con.cursor()
    cur.execute('''
        CREATE TABLE IF NOT EXISTS USERS(
            USER_ID BIGINT,
            PAYED_FOR TIMESTAMP,
            SUBSCRIPTION BOOL,
            LINKS TEXT,
            SCRIPTS_SETTINGS TEXT,
            RUNNING_SCRIPTS TEXT,
            SAVED_POSTS TEXT,
            VK_ACCESS_TOKEN TEXT,
            VK_USER_ID BIGINT
        );''')
    con.commit()
    con.close()

async def create_account(message: types.Message, is_return=False):
    user = message.from_user.id
    con = psycopg2.connect(ConfigKeys.SQL_INFO)
    cur = con.cursor()
    cur.execute(f"SELECT * from USERS where USER_ID = {user};")
    if cur.fetchone() is None:
        cur.execute(f"INSERT INTO USERS (USER_ID, SUBSCRIPTION, LINKS, SCRIPTS_SETTINGS ,RUNNING_SCRIPTS, SAVED_POSTS) VALUES ({user}, false, '{json.dumps({})}', '{json.dumps({})}', '{json.dumps([])}', '{json.dumps({})}')")
        con.commit()
        if is_return:
            con.close()
            return False
    con.close()
    return True
