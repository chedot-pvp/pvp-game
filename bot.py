import random
import time
import sqlite3
from aiogram import Bot, Dispatcher, executor, types

TOKEN = "6561293568:AAGBnBqmU3Z_5R_3r3zHb51IoTM8YAXAeIU"

bot = Bot(token=TOKEN)
dp = Dispatcher(bot)

db = sqlite3.connect("game.db")
sql = db.cursor()

# ---------- БАЗА ДАННЫХ ----------
sql.execute("""
CREATE TABLE IF NOT EXISTS users (
    telegram_id INTEGER PRIMARY KEY,
    strength INTEGER,
    agility INTEGER,
    stamina INTEGER,
    coins INTEGER,
    last_fight REAL
)
""")

sql.execute("""
CREATE TABLE IF NOT EXISTS queue (
    telegram_id INTEGER UNIQUE,
    joined REAL
)
""")

db.commit()

# ---------- ВСПОМОГАТЕЛЬНОЕ ----------
def get_user(uid):
    sql.execute("SELECT * FROM users WHERE telegram_id=?", (uid,))
    return sql.fetchone()

def create_user(uid):
    sql.execute(
        "INSERT INTO users VALUES (?,?,?,?,?,?)",
        (uid, 1, 1, 1, 50, 0)
    )
    db.commit()

def stats(u):
    strength, agility, stamina = u[1], u[2], u[3]
    hp = 100 + stamina * 25
    dmg = strength * 4
    crit = agility * 0.6
    dodge = agility * 0.4
    return hp, dmg, crit, dodge

# ---------- БОЙ ----------
def fight(u1, u2):
    hp1, dmg1, crit1, dodge1 = stats(u1)
    hp2, dmg2, crit2, dodge2 = stats(u2)

    log = []

    while hp1 > 0 and hp2 > 0:
        if random.random() * 100 >= dodge2:
            hit = dmg1 * (2 if random.random() * 100 < crit1 else 1)
            hp2 -= hit
            log.append(f"Игрок {u1[0]} ударил на {hit}")
        else:
            log.append(f"Игрок {u2[0]} увернулся")

        if hp2 <= 0:
            return u1, u2, log

        if random.random() * 100 >= dodge1:
            hit = dmg2 * (2 if random.random() * 100 < crit2 else 1)
            hp1 -= hit
            log.append(f"Игрок {u2[0]} ударил на {hit}")
        else:
            log.append(f"Игрок {u1[0]} увернулся")

    return u2, u1, log

# ---------- КОМАНДЫ ----------
@dp.message_handler(commands=["start"])
async def start(msg: types.Message):
    if not get_user(msg.from_user.id):
        create_user(msg.from_user.id)

    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("🗡 В бой", "⚙ Прокачка", "👤 Профиль")
    await msg.answer("Добро пожаловать в PvP!", reply_markup=kb)

@dp.message_handler(lambda m: m.text == "👤 Профиль")
async def web_profile(msg: types.Message):
    kb = types.InlineKeyboardMarkup()
    kb.add(
        types.InlineKeyboardButton(
            text="👤 Открыть профиль",
            web_app=types.WebAppInfo(
                url="https://chedot-pvp.github.io/pvp-game/"
            )
        )
    )
    await msg.answer("Твой профиль:", reply_markup=kb)

@dp.message_handler(lambda m: m.text == "🗡 В бой")
async def battle(msg: types.Message):
    uid = msg.from_user.id
    now = time.time()

    sql.execute("SELECT last_fight FROM users WHERE telegram_id=?", (uid,))
    last = sql.fetchone()[0]

    if now - last < 30:
        await msg.answer("⏳ Подожди 30 секунд")
        return

    sql.execute("INSERT OR IGNORE INTO queue VALUES (?,?)", (uid, now))
    db.commit()

    sql.execute("SELECT telegram_id FROM queue WHERE telegram_id != ?", (uid,))
    enemy = sql.fetchone()

    if not enemy:
        await msg.answer("⌛ Ожидание соперника...")
        return

    enemy_id = enemy[0]

    sql.execute("DELETE FROM queue WHERE telegram_id IN (?,?)", (uid, enemy_id))
    db.commit()

    u1 = get_user(uid)
    u2 = get_user(enemy_id)

    winner, loser, log = fight(u1, u2)

    sql.execute("UPDATE users SET coins = coins + 15 WHERE telegram_id=?", (winner[0],))
    sql.execute("UPDATE users SET coins = coins + 5 WHERE telegram_id=?", (loser[0],))
    sql.execute("UPDATE users SET last_fight=? WHERE telegram_id IN (?,?)", (now, winner[0], loser[0]))
    db.commit()

    text = "⚔ БОЙ\n\n" + "\n".join(log[:10]) + f"\n\n🏆 Победитель: {winner[0]}"
    await bot.send_message(winner[0], text)
    await bot.send_message(loser[0], text)

@dp.message_handler(lambda m: m.text == "⚙ Прокачка")
async def upgrade(msg: types.Message):
    u = get_user(msg.from_user.id)
    cost = 50

    if u[4] < cost:
        await msg.answer("❌ Недостаточно монет")
        return

    sql.execute(
        "UPDATE users SET strength = strength + 1, coins = coins - ? WHERE telegram_id=?",
        (cost, msg.from_user.id)
    )
    db.commit()

    await msg.answer("✅ Сила увеличена!")


@dp.message_handler(commands=["game"])
async def open_game(msg: types.Message):
    kb = types.InlineKeyboardMarkup()
    kb.add(
        types.InlineKeyboardButton(
            text="🎮 Открыть игру",
            web_app=types.WebAppInfo(
                url="https://chedot-pvp.github.io/pvp-game/"
            )
        )
    )
    await msg.answer("Запуск игры:", reply_markup=kb)

# ---------- ЗАПУСК ----------
if __name__ == "__main__":
    executor.start_polling(dp)