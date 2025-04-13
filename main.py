import asyncio
import os
import threading
import discord
from discord.ext import commands
from pymongo import MongoClient
from flask import Flask

# === FLASK KEEP-ALIVE SERVER ===
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot activo ✅"

# === CONFIGURACIÓN DEL BOT ===
TOKEN = "MTM1MjQ5NTYxMjgxMzI1MDY0MA.G3LmNo.Y1xgmu5UznG3yitpLk8MOmRsHEpcLCliAkGN0k"
APP_ID = 1352495612813250640

# === CONEXIÓN A MONGODB ===
MONGO_URI = "mongodb+srv://TCG:ixR4AINjmD8HlCQa@cluster0.mriaxlf.mongodb.net/"
client = MongoClient(MONGO_URI)
db = client["discord_server"]
col = db["users"]

# === DISCORD SETUP ===
intents = discord.Intents.all()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents, application_id=APP_ID)

@bot.tree.command(name="start", description="Start your adventure!")
async def start(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    user_name = interaction.user.name

    if col.find_one({"discordID": user_id}):
        await interaction.response.send_message("Ya estás registrado. ✅", ephemeral=True)
    else:
        col.insert_one({"discordID": user_id, "userName": user_name})
        await interaction.response.send_message("¡Bienvenido al juego! 🎮", ephemeral=True)

@bot.event
async def on_ready():
    print(f"✅ Bot conectado como {bot.user}")
    await bot.tree.sync()

# === EJECUCIÓN DEL BOT ===
async def main():
    async with bot:
        await bot.start(TOKEN)

# === Lanzar Flask y Bot (en hilo separado) ===
def run_all():
    def run_bot():
        asyncio.run(main())

    # Arrancar el bot en un hilo nuevo
    threading.Thread(target=run_bot).start()

    # Correr Flask
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

# Solo se ejecuta en entorno local
if __name__ == "__main__":
    run_all()

# Exportar app para gunicorn (Render lo necesita)
# Esto hace que Flask arranque y con él el bot.
run_all()

    
