import discord
from discord.ext import commands
import os
import json
import asyncio
from datetime import datetime
from flask import Flask

# Konfiguracja Flask
app = Flask(__name__)

@app.route('/')
def home():
    return 'Bot działa!'

# Intents
intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix='/', intents=intents)

DATA_FILE = "voice_data.json"
CHANNEL_ID_TO_POST = 1370339487561027605

top_message = None
voice_times = {}  # user_id -> minutes
active_users = {}  # user_id -> datetime

def save_data():
    with open(DATA_FILE, 'w') as f:
        json.dump(voice_times, f)

def load_data():
    global voice_times
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r') as f:
            voice_times = json.load(f)
    else:
        voice_times = {}
        save_data()

@bot.event
async def on_ready():
    print(f'Bot is ready as {bot.user}')
    load_data()
    bot.loop.create_task(update_voice_top())

@bot.event
async def on_voice_state_update(member, before, after):
    user_id = str(member.id)
    now = datetime.now()

    def update_duration():
        if user_id in active_users:
            start_time = active_users[user_id]
            duration = (now - start_time).total_seconds() / 60
            voice_times[user_id] = voice_times.get(user_id, 0) + duration
            del active_users[user_id]
            save_data()

    # Dołączył na VC i nie jest zmutowany
    if before.channel is None and after.channel is not None and not after.self_deaf:
        active_users[user_id] = now

    # Opuścił VC
    elif before.channel is not None and after.channel is None:
        update_duration()

    # Zmutował/odmutował się
    elif before.self_deaf != after.self_deaf:
        if after.self_deaf:
            update_duration()
        else:
            active_users[user_id] = now

@bot.command(name="voice_top")
async def voice_top(ctx):
    now = datetime.now()
    combined_data = voice_times.copy()

    # Dodaj aktualne sesje
    for user_id, start_time_str in active_users.items():
        session_minutes = (now - start_time_str).total_seconds() / 60
        combined_data[user_id] = combined_data.get(user_id, 0) + session_minutes

    sorted_data = sorted(combined_data.items(), key=lambda x: x[1], reverse=True)
    if not sorted_data:
        await ctx.send("Brak danych.")
        return

    msg = "**TOP czasu spędzonego na VC all time:**\n"
    for i, (user_id, minutes) in enumerate(sorted_data[:10], 1):
        user = await bot.fetch_user(int(user_id))
        hours = minutes / 60
        msg += f"{i}. {user.name} - {hours:.2f}h\n"

    await ctx.send(msg)

async def update_voice_top():
    await bot.wait_until_ready()
    global top_message
    channel = bot.get_channel(CHANNEL_ID_TO_POST)

    while not bot.is_closed():
        try:
            now = datetime.now()
            combined_data = voice_times.copy()

            for user_id, start_time in active_users.items():
                session_minutes = (now - start_time).total_seconds() / 60
                combined_data[user_id] = combined_data.get(user_id, 0) + session_minutes

            sorted_data = sorted(combined_data.items(), key=lambda x: x[1], reverse=True)
            if not sorted_data:
                content = "Brak danych."
            else:
                content = "**TOP czasu spędzonego na VC all time:**\n"
                for i, (user_id, minutes) in enumerate(sorted_data[:10], 1):
                    user = await bot.fetch_user(int(user_id))
                    hours = minutes / 60
                    content += f"{i}. {user.name} - {hours:.2f}h\n"

            if top_message is not None:
                await top_message.delete()
            top_message = await channel.send(content)

        except Exception as e:
            print(f"Błąd podczas aktualizacji topki: {e}")

        await asyncio.sleep(600)  # 10 minut

# Uruchomienie Flask i bota
if __name__ == "__main__":
    from threading import Thread
    def run_flask():
        app.run(host='0.0.0.0', port=8080)

    flask_thread = Thread(target=run_flask)
    flask_thread.start()

    bot.run(os.environ['DISCORD_TOKEN'])
