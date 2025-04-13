import os
import threading
import asyncio
import discord
from discord.ext import commands
from flask import Flask
from pymongo import MongoClient

# === Flask para keep-alive ===
app = Flask(__name__)

@app.route("/")
def index():
    return "Bot y servidor activos ✅"

# === Configuración de conexión ===
TOKEN = "MTM1MjQ5NTYxMjgxMzI1MDY0MA.G3LmNo.Y1xgmu5UznG3yitpLk8MOmRsHEpcLCliAkGN0k"
APP_ID = 1352495612813250640
MONGO_URI = "mongodb+srv://TCG:ixR4AINjmD8HlCQa@cluster0.mriaxlf.mongodb.net/"

# === Conexión MongoDB ===
client = MongoClient(MONGO_URI)
db = client["discord_server"]
users = db["users"]

# === Configuración del bot ===
intents = discord.Intents.all()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents, application_id=APP_ID)

# === Comando básico para iniciar el juego ===
@bot.tree.command(name="start", description="Start your adventure!")
async def start(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    user_name = interaction.user.name

    if users.find_one({"discordID": user_id}):
        await interaction.response.send_message("Ya estás registrado. ✅", ephemeral=True)
    else:
        users.insert_one({"discordID": user_id, "userName": user_name})
        await interaction.response.send_message("¡Bienvenido al juego! 🎮", ephemeral=True)

# === Evento al iniciar el bot ===
@bot.event
async def on_ready():
    print(f"✅ Bot conectado como {bot.user}")

    # Cargar la extensión de comandos
    await bot.load_extension("general")

    # Esperar un momento para asegurar que los comandos del cog estén listos
    await asyncio.sleep(1)

    # Sincronizar comandos globales
    synced = await bot.tree.sync()
    print(f"🔄 Comandos sincronizados globalmente: {[cmd.name for cmd in synced]}")

# === Iniciar el bot en segundo plano ===
def run_bot():
    asyncio.run(bot.start(TOKEN))

threading.Thread(target=run_bot).start()