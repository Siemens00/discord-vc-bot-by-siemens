import discord
from discord.ext import commands
import os
import json
import asyncio
from datetime import datetime
from flask import Flask

# Konfiguracja Flask
app = Flask(__name__)

# Flask route (potrzebne dla uptimebota)
@app.route('/')
def home():
    return 'Bot działa!'

# Ustawienia bota
intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix='/', intents=intents)
top_message = None

DATA_FILE = "voice_data.json"
CHANNEL_ID_TO_POST = 1370339487561027605

voice_times = {}
active_users = {}

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

async def update_voice_top():
    await bot.wait_until_ready()
    channel = bot.get_channel(CHANNEL_ID_TO_POST)
    global top_message

    while not bot.is_closed():
        try:
            with open(DATA_FILE, "r") as f:
                data = json.load(f)

            now = datetime.now()
            combined_data = data.copy()

            for user_id, start_time_str in active_users.items():
                start_time = datetime.strptime(str(start_time_str), '%Y-%m-%d %H:%M:%S.%f')
                session_minutes = (now - start_time).total_seconds() / 60
                if user_id in combined_data:
                    combined_data[user_id] += session_minutes
                else:
                    combined_data[user_id] = session_minutes

            if not combined_data:
                content = "Brak danych."
            else:
                sorted_data = sorted(combined_data.items(), key=lambda x: x[1], reverse=True)
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

        await asyncio.sleep(60)

# Komenda do wyświetlania rankingu czasu na VC
@bot.command(name="voice_top")
async def voice_top(ctx):
    try:
        with open(DATA_FILE, "r") as f:
            data = json.load(f)
    except:
        await ctx.send("Brak danych.")
        return

    now = datetime.now()
    combined_data = data.copy()

    for user_id, start_time_str in active_users.items():
        start_time = datetime.strptime(str(start_time_str), '%Y-%m-%d %H:%M:%S.%f')
        session_minutes = (now - start_time).total_seconds() / 60
        if user_id in combined_data:
            combined_data[user_id] += session_minutes
        else:
            combined_data[user_id] = session_minutes

    sorted_data = sorted(combined_data.items(), key=lambda x: x[1], reverse=True)
    msg = "**TOP czasu spędzonego na VC all time:**\n"
    for i, (user_id, minutes) in enumerate(sorted_data[:10], 1):
        user = await bot.fetch_user(int(user_id))
        hours = minutes / 60
        msg += f"{i}. {user.name} - {hours:.2f}h\n"

    await ctx.send(msg)

@bot.event
async def on_ready():
    print(f'Bot is ready as {bot.user}')
    load_data()
    bot.loop.create_task(update_voice_top())

@bot.event
async def on_voice_state_update(member, before, after):
    user_id = str(member.id)

    if before.channel is None and after.channel is not None and not after.self_deaf:
        active_users[user_id] = datetime.now()

    elif before.channel is not None and after.channel is None:
        if user_id in active_users:
            start_time = active_users[user_id]
            duration = (datetime.now() - start_time).total_seconds() / 60
            if user_id not in voice_times:
                voice_times[user_id] = 0
            voice_times[user_id] += duration
            save_data()
            del active_users[user_id]

    elif before.self_deaf != after.self_deaf:
        if after.self_deaf:
            if user_id in active_users:
                start_time = active_users[user_id]
                duration = (datetime.now() - start_time).total_seconds() / 60
                if user_id not in voice_times:
                    voice_times[user_id] = 0
                voice_times[user_id] += duration
                save_data()
                del active_users[user_id]
        else:
            active_users[user_id] = datetime.now()

# Uruchomienie bota oraz aplikacji Flask
if __name__ == "__main__":
    # Uruchomienie aplikacji Flask w tle
    from threading import Thread
    def run_flask():
        app.run(host='0.0.0.0', port=8080)

    flask_thread = Thread(target=run_flask)
    flask_thread.start()

    # Uruchomienie bota
    bot.run(os.environ['DISCORD_TOKEN'])