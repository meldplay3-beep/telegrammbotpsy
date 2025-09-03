{\rtf1\ansi\ansicpg1251\cocoartf2822
\cocoatextscaling0\cocoaplatform0{\fonttbl\f0\fswiss\fcharset0 Helvetica;}
{\colortbl;\red255\green255\blue255;}
{\*\expandedcolortbl;;}
\paperw11900\paperh16840\margl1440\margr1440\vieww11520\viewh8400\viewkind0
\pard\tx720\tx1440\tx2160\tx2880\tx3600\tx4320\tx5040\tx5760\tx6480\tx7200\tx7920\tx8640\pardirnatural\partightenfactor0

\f0\fs24 \cf0 import os\
import logging\
import random\
import sqlite3\
from datetime import datetime\
from dotenv import load_dotenv\
from telegram import Update\
from telegram.ext import (\
    ApplicationBuilder, CommandHandler, ContextTypes,\
    ConversationHandler, MessageHandler, filters\
)\
\
# Setup\
load_dotenv()\
TOKEN = os.getenv("TELEGRAM_TOKEN")\
if not TOKEN:\
    raise SystemExit("Please set TELEGRAM_TOKEN in .env")\
\
logging.basicConfig(\
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",\
    level=logging.INFO\
)\
logger = logging.getLogger(__name__)\
\
# Database setup\
DB_FILE = "database.db"\
\
def init_db():\
    conn = sqlite3.connect(DB_FILE)\
    cur = conn.cursor()\
    cur.execute("""\
        CREATE TABLE IF NOT EXISTS users (\
            user_id INTEGER PRIMARY KEY,\
            name TEXT\
        )\
    """)\
    cur.execute("""\
        CREATE TABLE IF NOT EXISTS reflections (\
            id INTEGER PRIMARY KEY AUTOINCREMENT,\
            user_id INTEGER,\
            situation TEXT,\
            feelings TEXT,\
            values TEXT,\
            created_at TEXT\
        )\
    """)\
    conn.commit()\
    conn.close()\
\
def get_user_name(user_id: int) -> str | None:\
    conn = sqlite3.connect(DB_FILE)\
    cur = conn.cursor()\
    cur.execute("SELECT name FROM users WHERE user_id = ?", (user_id,))\
    row = cur.fetchone()\
    conn.close()\
    return row[0] if row else None\
\
def set_user_name(user_id: int, name: str):\
    conn = sqlite3.connect(DB_FILE)\
    cur = conn.cursor()\
    cur.execute("INSERT INTO users (user_id, name) VALUES (?, ?) ON CONFLICT(user_id) DO UPDATE SET name = excluded.name", (user_id, name))\
    conn.commit()\
    conn.close()\
\
def save_reflection(user_id: int, situation: str, feelings: str, values: str):\
    conn = sqlite3.connect(DB_FILE)\
    cur = conn.cursor()\
    cur.execute(\
        "INSERT INTO reflections (user_id, situation, feelings, values, created_at) VALUES (?, ?, ?, ?, ?)",\
        (user_id, situation, feelings, values, datetime.now().isoformat())\
    )\
    conn.commit()\
    conn.close()\
\
# States\
ASK_NAME, CALM_TALK, REFLECT_Q1, REFLECT_Q2, REFLECT_Q3 = range(5)\
\
# Calming exercises and affirmations\
BREATHING_TIPS = [\
    "\uc0\u1057 \u1076 \u1077 \u1083 \u1072 \u1081  \u1075 \u1083 \u1091 \u1073 \u1086 \u1082 \u1080 \u1081  \u1074 \u1076 \u1086 \u1093  \u1085 \u1072  4 \u1089 \u1077 \u1082 \u1091 \u1085 \u1076 \u1099 ... \u1079 \u1072 \u1076 \u1077 \u1088 \u1078 \u1080  \u1076 \u1099 \u1093 \u1072 \u1085 \u1080 \u1077  \u1085 \u1072  4... \u1080  \u1084 \u1077 \u1076 \u1083 \u1077 \u1085 \u1085 \u1086  \u1074 \u1099 \u1076 \u1086 \u1093 \u1085 \u1080  \u1085 \u1072  6 \u55356 \u57132 ",\
    "\uc0\u1047 \u1072 \u1082 \u1088 \u1086 \u1081  \u1075 \u1083 \u1072 \u1079 \u1072  \u1080  \u1089 \u1076 \u1077 \u1083 \u1072 \u1081  3 \u1084 \u1077 \u1076 \u1083 \u1077 \u1085 \u1085 \u1099 \u1093  \u1075 \u1083 \u1091 \u1073 \u1086 \u1082 \u1080 \u1093  \u1074 \u1076 \u1086 \u1093 \u1072 . \u1055 \u1088 \u1077 \u1076 \u1089 \u1090 \u1072 \u1074 \u1100 , \u1095 \u1090 \u1086  \u1089  \u1082 \u1072 \u1078 \u1076 \u1099 \u1084  \u1074 \u1099 \u1076 \u1086 \u1093 \u1086 \u1084  \u1085 \u1072 \u1087 \u1088 \u1103 \u1078 \u1077 \u1085 \u1080 \u1077  \u1091 \u1093 \u1086 \u1076 \u1080 \u1090  \u55356 \u57151 ",\
    "\uc0\u1055 \u1086 \u1087 \u1088 \u1086 \u1073 \u1091 \u1081  \u1076 \u1099 \u1093 \u1072 \u1085 \u1080 \u1077  '\u1082 \u1086 \u1088 \u1086 \u1073 \u1086 \u1095 \u1082 \u1072 ': \u1074 \u1076 \u1086 \u1093  4 \u1089 \u1077 \u1082  \'97 \u1079 \u1072 \u1076 \u1077 \u1088 \u1078 \u1082 \u1072  4 \u1089 \u1077 \u1082  \'97 \u1074 \u1099 \u1076 \u1086 \u1093  4 \u1089 \u1077 \u1082  \'97 \u1079 \u1072 \u1076 \u1077 \u1088 \u1078 \u1082 \u1072  4 \u1089 \u1077 \u1082  \u55357 \u56626 "\
]\
\
AFFIRMATIONS = [\
    "\uc0\u1058 \u1099  \u1089 \u1080 \u1083 \u1100 \u1085 \u1077 \u1077 , \u1095 \u1077 \u1084  \u1076 \u1091 \u1084 \u1072 \u1077 \u1096 \u1100  \u55357 \u56473 ",\
    "\uc0\u1058 \u1099  \u1079 \u1072 \u1089 \u1083 \u1091 \u1078 \u1080 \u1074 \u1072 \u1077 \u1096 \u1100  \u1083 \u1102 \u1073 \u1074 \u1080  \u1080  \u1089 \u1087 \u1086 \u1082 \u1086 \u1081 \u1089 \u1090 \u1074 \u1080 \u1103  \u55356 \u57144 ",\
    "\uc0\u1058 \u1099  \u1089 \u1087 \u1088 \u1072 \u1074 \u1080 \u1096 \u1100 \u1089 \u1103 , \u1103  \u1088 \u1103 \u1076 \u1086 \u1084  \u55357 \u56911 ",\
    "\uc0\u1050 \u1072 \u1078 \u1076 \u1099 \u1081  \u1096 \u1072 \u1075  \u1082  \u1084 \u1080 \u1088 \u1091  \u1074 \u1072 \u1078 \u1077 \u1085  \u55356 \u57119 "\
]\
\
# Helper to get user's name or fallback\
def get_name_from_db(user_id: int) -> str:\
    name = get_user_name(user_id)\
    return name if name else "\uc0\u1076 \u1088 \u1091 \u1075 "\
\
# Handlers\
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:\
    user_id = update.effective_user.id\
    name = get_user_name(user_id)\
    if not name:\
        await update.message.reply_text("\uc0\u1055 \u1088 \u1080 \u1074 \u1077 \u1090  \u55356 \u57151  \u1071  \u1090 \u1074 \u1086 \u1081  \u1073 \u1086 \u1090 -\u1076 \u1088 \u1091 \u1075 . \u1050 \u1072 \u1082  \u1084 \u1085 \u1077  \u1082  \u1090 \u1077 \u1073 \u1077  \u1086 \u1073 \u1088 \u1072 \u1097 \u1072 \u1090 \u1100 \u1089 \u1103 ?")\
        return ASK_NAME\
    else:\
        await update.message.reply_text(\
            f"\uc0\u1057 \u1085 \u1086 \u1074 \u1072  \u1088 \u1072 \u1076  \u1090 \u1077 \u1073 \u1103  \u1074 \u1080 \u1076 \u1077 \u1090 \u1100 , \{name\} \u55357 \u56473 \\n"\
            "\uc0\u1071  \u1087 \u1086 \u1084 \u1086 \u1075 \u1091  \u1090 \u1077 \u1073 \u1077  \u1091 \u1089 \u1087 \u1086 \u1082 \u1086 \u1080 \u1090 \u1100 \u1089 \u1103  \u1087 \u1086 \u1089 \u1083 \u1077  \u1089 \u1089 \u1086 \u1088 \u1099  \u1080  \u1084 \u1103 \u1075 \u1082 \u1086  \u1088 \u1072 \u1079 \u1086 \u1073 \u1088 \u1072 \u1090 \u1100 \u1089 \u1103  \u1074  \u1095 \u1091 \u1074 \u1089 \u1090 \u1074 \u1072 \u1093 .\\n\\n"\
            "\uc0\u1050 \u1086 \u1084 \u1072 \u1085 \u1076 \u1099 :\\n"\
            "\'95 /calm \'97 \uc0\u1088 \u1077 \u1078 \u1080 \u1084  \u1091 \u1089 \u1087 \u1086 \u1082 \u1086 \u1077 \u1085 \u1080 \u1103 \\n"\
            "\'95 /reflect \'97 \uc0\u1084 \u1103 \u1075 \u1082 \u1080 \u1081  \u1088 \u1072 \u1079 \u1073 \u1086 \u1088  \u1089 \u1080 \u1090 \u1091 \u1072 \u1094 \u1080 \u1080 \\n"\
            "\'95 /setname \'97 \uc0\u1080 \u1079 \u1084 \u1077 \u1085 \u1080 \u1090 \u1100  \u1080 \u1084 \u1103 \\n"\
            "\'95 /cancel \'97 \uc0\u1087 \u1088 \u1077 \u1088 \u1074 \u1072 \u1090 \u1100  \u1088 \u1072 \u1079 \u1075 \u1086 \u1074 \u1086 \u1088 "\
        )\
        return ConversationHandler.END\
\
async def ask_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:\
    user_id = update.effective_user.id\
    name = update.message.text.strip()\
    set_user_name(user_id, name)\
    await update.message.reply_text(\
        f"\uc0\u1056 \u1072 \u1076  \u1087 \u1086 \u1079 \u1085 \u1072 \u1082 \u1086 \u1084 \u1080 \u1090 \u1100 \u1089 \u1103 , \{name\} \u55356 \u57144 \\n"\
        "\uc0\u1058 \u1077 \u1087 \u1077 \u1088 \u1100  \u1103  \u1073 \u1091 \u1076 \u1091  \u1086 \u1073 \u1088 \u1072 \u1097 \u1072 \u1090 \u1100 \u1089 \u1103  \u1082  \u1090 \u1077 \u1073 \u1077  \u1087 \u1086  \u1080 \u1084 \u1077 \u1085 \u1080 .\\n\\n"\
        "\uc0\u1050 \u1086 \u1084 \u1072 \u1085 \u1076 \u1099 :\\n"\
        "\'95 /calm \'97 \uc0\u1088 \u1077 \u1078 \u1080 \u1084  \u1091 \u1089 \u1087 \u1086 \u1082 \u1086 \u1077 \u1085 \u1080 \u1103 \\n"\
        "\'95 /reflect \'97 \uc0\u1084 \u1103 \u1075 \u1082 \u1080 \u1081  \u1088 \u1072 \u1079 \u1073 \u1086 \u1088  \u1089 \u1080 \u1090 \u1091 \u1072 \u1094 \u1080 \u1080 \\n"\
        "\'95 /setname \'97 \uc0\u1080 \u1079 \u1084 \u1077 \u1085 \u1080 \u1090 \u1100  \u1080 \u1084 \u1103 \\n"\
        "\'95 /cancel \'97 \uc0\u1087 \u1088 \u1077 \u1088 \u1074 \u1072 \u1090 \u1100  \u1088 \u1072 \u1079 \u1075 \u1086 \u1074 \u1086 \u1088 "\
    )\
    return ConversationHandler.END\
\
async def setname(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:\
    user_id = update.effective_user.id\
    await update.message.reply_text("\uc0\u1061 \u1086 \u1088 \u1086 \u1096 \u1086  \u55356 \u57151  \u1053 \u1072 \u1087 \u1080 \u1096 \u1080 , \u1082 \u1072 \u1082  \u1084 \u1085 \u1077  \u1082  \u1090 \u1077 \u1073 \u1077  \u1086 \u1073 \u1088 \u1072 \u1097 \u1072 \u1090 \u1100 \u1089 \u1103 .")\
    conn = sqlite3.connect(DB_FILE)\
    cur = conn.cursor()\
    cur.execute("DELETE FROM users WHERE user_id = ?", (user_id,))\
    conn.commit()\
    conn.close()\
\
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:\
    await update.message.reply_text("\uc0\u1061 \u1086 \u1088 \u1086 \u1096 \u1086 , \u1089 \u1076 \u1077 \u1083 \u1072 \u1077 \u1084  \u1087 \u1072 \u1091 \u1079 \u1091 . \u1071  \u1088 \u1103 \u1076 \u1086 \u1084 , \u1077 \u1089 \u1083 \u1080  \u1087 \u1086 \u1085 \u1072 \u1076 \u1086 \u1073 \u1080 \u1090 \u1089 \u1103  \u55356 \u57144 ")\
    return ConversationHandler.END\
\
# Calm Flow\
async def calm_entry(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:\
    user_id = update.effective_user.id\
    name = get_name_from_db(user_id)\
    await update.message.reply_text(\
        f"\uc0\u1071  \u1087 \u1086 \u1085 \u1080 \u1084 \u1072 \u1102 , \u1090 \u1077 \u1073 \u1077  \u1089 \u1077 \u1081 \u1095 \u1072 \u1089  \u1085 \u1077 \u1087 \u1088 \u1086 \u1089 \u1090 \u1086 , \{name\} \u55357 \u56473 \\n"\
        "\uc0\u1061 \u1086 \u1095 \u1077 \u1096 \u1100 , \u1087 \u1088 \u1086 \u1089 \u1090 \u1086  \u1088 \u1072 \u1089 \u1089 \u1082 \u1072 \u1078 \u1080 , \u1095 \u1090 \u1086  \u1091  \u1090 \u1077 \u1073 \u1103  \u1085 \u1072  \u1076 \u1091 \u1096 \u1077 . \u1071  \u1088 \u1103 \u1076 \u1086 \u1084  \u1080  \u1074 \u1099 \u1089 \u1083 \u1091 \u1096 \u1072 \u1102  \u55357 \u56911 "\
    )\
    return CALM_TALK\
\
async def calm_talk(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:\
    user_id = update.effective_user.id\
    name = get_name_from_db(user_id)\
    tip = random.choice(BREATHING_TIPS)\
    affirm = random.choice(AFFIRMATIONS)\
    await update.message.reply_text(\
        f"\uc0\u1057 \u1087 \u1072 \u1089 \u1080 \u1073 \u1086 , \u1095 \u1090 \u1086  \u1087 \u1086 \u1076 \u1077 \u1083 \u1080 \u1083 \u1089 \u1103 , \{name\} \u55356 \u57151  \u1071  \u1089 \u1083 \u1099 \u1096 \u1091  \u1090 \u1074 \u1086 \u1102  \u1073 \u1086 \u1083 \u1100 .\\n\\n"\
        f"\uc0\u1055 \u1086 \u1087 \u1088 \u1086 \u1073 \u1091 \u1081  \u1091 \u1087 \u1088 \u1072 \u1078 \u1085 \u1077 \u1085 \u1080 \u1077 :\\n\{tip\}\\n\\n"\
        f"\uc0\u1040  \u1077 \u1097 \u1105  \u1079 \u1072 \u1087 \u1086 \u1084 \u1085 \u1080 : \{affirm\}"\
    )\
    return ConversationHandler.END\
\
# Reflect Flow\
async def reflect_entry(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:\
    user_id = update.effective_user.id\
    name = get_name_from_db(user_id)\
    await update.message.reply_text(\
        f"\uc0\u1044 \u1072 \u1074 \u1072 \u1081  \u1087 \u1086 \u1087 \u1088 \u1086 \u1073 \u1091 \u1077 \u1084  \u1084 \u1103 \u1075 \u1082 \u1086  \u1088 \u1072 \u1079 \u1086 \u1073 \u1088 \u1072 \u1090 \u1100 \u1089 \u1103  \u1074  \u1089 \u1080 \u1090 \u1091 \u1072 \u1094 \u1080 \u1080 , \{name\} \u55357 \u56491 \\n\\n"\
        "1/3. \uc0\u1063 \u1090 \u1086  \u1080 \u1084 \u1077 \u1085 \u1085 \u1086  \u1087 \u1088 \u1086 \u1080 \u1079 \u1086 \u1096 \u1083 \u1086  \u1074  \u1089 \u1089 \u1086 \u1088 \u1077 ? \u1053 \u1072 \u1087 \u1080 \u1096 \u1080  \u1089 \u1074 \u1086 \u1080 \u1084 \u1080  \u1089 \u1083 \u1086 \u1074 \u1072 \u1084 \u1080 ."\
    )\
    return REFLECT_Q1\
\
async def reflect_q1(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:\
    context.user_data["situation"] = update.message.text\
    await update.message.reply_text("2/3. \uc0\u1063 \u1090 \u1086  \u1090 \u1099  \u1095 \u1091 \u1074 \u1089 \u1090 \u1074 \u1086 \u1074 \u1072 \u1083 (\u1072 ) \u1074  \u1101 \u1090 \u1086 \u1090  \u1084 \u1086 \u1084 \u1077 \u1085 \u1090 ? \u10084 \u65039 ")\
    return REFLECT_Q2\
\
async def reflect_q2(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:\
    context.user_data["feelings"] = update.message.text\
    await update.message.reply_text("3/3. \uc0\u1063 \u1090 \u1086  \u1093 \u1086 \u1088 \u1086 \u1096 \u1077 \u1075 \u1086  \u1090 \u1099  \u1094 \u1077 \u1085 \u1080 \u1096 \u1100  \u1074  \u1087 \u1072 \u1088 \u1090 \u1085 \u1105 \u1088 \u1077 , \u1085 \u1077 \u1089 \u1084 \u1086 \u1090 \u1088 \u1103  \u1085 \u1072  \u1089 \u1089 \u1086 \u1088 \u1091 ? \u55356 \u57144 ")\
    return REFLECT_Q3\
\
async def reflect_q3(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:\
    user_id = update.effective_user.id\
    name = get_name_from_db(user_id)\
    situation = context.user_data.get("situation", "")\
    feelings = context.user_data.get("feelings", "")\
    values = update.message.text\
    save_reflection(user_id, situation, feelings, values)\
    summary = (\
        f"\uc0\u1057 \u1087 \u1072 \u1089 \u1080 \u1073 \u1086 , \u1095 \u1090 \u1086  \u1087 \u1086 \u1076 \u1077 \u1083 \u1080 \u1083 \u1089 \u1103 , \{name\} \u55357 \u56473 \\n\\n"\
        f"\uc0\u1058 \u1099  \u1088 \u1072 \u1089 \u1089 \u1082 \u1072 \u1079 \u1072 \u1083 (\u1072 ):\\n"\
        f"\'95 \uc0\u1057 \u1080 \u1090 \u1091 \u1072 \u1094 \u1080 \u1103 : \{situation\}\\n"\
        f"\'95 \uc0\u1063 \u1091 \u1074 \u1089 \u1090 \u1074 \u1072 : \{feelings\}\\n"\
        f"\'95 \uc0\u1062 \u1077 \u1085 \u1085 \u1086 \u1089 \u1090 \u1100 : \{values\}\\n\\n"\
        "\uc0\u1069 \u1090 \u1086  \u1086 \u1095 \u1077 \u1085 \u1100  \u1074 \u1072 \u1078 \u1085 \u1086  \u55356 \u57151  \u1055 \u1086 \u1084 \u1085 \u1080 , \u1095 \u1090 \u1086  \u1091  \u1074 \u1072 \u1089  \u1077 \u1089 \u1090 \u1100  \u1080  \u1093 \u1086 \u1088 \u1086 \u1096 \u1080 \u1077  \u1084 \u1086 \u1084 \u1077 \u1085 \u1090 \u1099 , "\
        "\uc0\u1080  \u1086 \u1085 \u1080  \u1084 \u1086 \u1075 \u1091 \u1090  \u1087 \u1086 \u1084 \u1086 \u1095 \u1100  \u1074 \u1072 \u1084  \u1085 \u1072 \u1081 \u1090 \u1080  \u1087 \u1091 \u1090 \u1100  \u1082  \u1087 \u1088 \u1080 \u1084 \u1080 \u1088 \u1077 \u1085 \u1080 \u1102 .\\n"\
        "\uc0\u1055 \u1086 \u1087 \u1088 \u1086 \u1073 \u1091 \u1081  \u1087 \u1086 \u1079 \u1078 \u1077  \u1087 \u1086 \u1075 \u1086 \u1074 \u1086 \u1088 \u1080 \u1090 \u1100  \u1089 \u1087 \u1086 \u1082 \u1086 \u1081 \u1085 \u1086 , \u1085 \u1072 \u1095 \u1080 \u1085 \u1072 \u1103  \u1085 \u1077  \u1089  \u1086 \u1073 \u1074 \u1080 \u1085 \u1077 \u1085 \u1080 \u1081 , \u1072  \u1089  \u1090 \u1086 \u1075 \u1086 , \u1095 \u1090 \u1086  \u1090 \u1099  \u1095 \u1091 \u1074 \u1089 \u1090 \u1074 \u1091 \u1077 \u1096 \u1100  \u55357 \u56911 "\
    )\
    await update.message.reply_text(summary)\
    return ConversationHandler.END\
\
def main() -> None:\
    init_db()\
    app = ApplicationBuilder().token(TOKEN).build()\
\
    # Name collection\
    name_conv = ConversationHandler(\
        entry_points=[CommandHandler("start", start)],\
        states=\{ASK_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_name)]\},\
        fallbacks=[CommandHandler("cancel", cancel)]\
    )\
    app.add_handler(name_conv)\
    app.add_handler(CommandHandler("setname", setname))\
\
    # Calm flow\
    calm_conv = ConversationHandler(\
        entry_points=[CommandHandler("calm", calm_entry)],\
        states=\{CALM_TALK: [MessageHandler(filters.TEXT & ~filters.COMMAND, calm_talk)]\},\
        fallbacks=[CommandHandler("cancel", cancel)]\
    )\
    app.add_handler(calm_conv)\
\
    # Reflect flow\
    reflect_conv = ConversationHandler(\
        entry_points=[CommandHandler("reflect", reflect_entry)],\
        states=\{\
            REFLECT_Q1: [MessageHandler(filters.TEXT & ~filters.COMMAND, reflect_q1)],\
            REFLECT_Q2: [MessageHandler(filters.TEXT & ~filters.COMMAND, reflect_q2)],\
            REFLECT_Q3: [MessageHandler(filters.TEXT & ~filters.COMMAND, reflect_q3)],\
        \},\
        fallbacks=[CommandHandler("cancel", cancel)]\
    )\
    app.add_handler(reflect_conv)\
\
    # Cancel handler\
    app.add_handler(CommandHandler("cancel", cancel))\
\
    app.run_polling()\
\
if __name__ == "__main__":\
    main()}