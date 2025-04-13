import os
import threading
import asyncio
import discord
from discord.ext import commands
from flask import Flask
from db.database import db_connect, verify_user, register_user, update_user  # ← Importamos las funciones útiles

# === Flask para keep-alive ===
app = Flask(__name__)

@app.route("/")
def index():
    return "Bot y servidor activos ✅"

# === Configuración de conexión ===
TOKEN = "MTM1MjQ5NTYxMjgxMzI1MDY0MA.G3LmNo.Y1xgmu5UznG3yitpLk8MOmRsHEpcLCliAkGN0k"
APP_ID = 1352495612813250640

# === Conexión MongoDB ===
users = db_connect()

# === Configuración del bot ===
intents = discord.Intents.all()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents, application_id=APP_ID)

# === Comando básico para iniciar el juego ===
@bot.tree.command(name="start", description="Start your adventure!")
async def start(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    user_name = interaction.user.name

    if verify_user(users, user_id):
        await interaction.response.send_message("Ya estás registrado. ✅", ephemeral=True)
    else:
        register_user(users, user_id, user_name)
        await interaction.response.send_message("¡Bienvenido al juego! 🎮", ephemeral=True)

# === Comando para mostrar el perfil del jugador ===
@bot.tree.command(name="perfil", description="Muestra el perfil del jugador")
async def perfil(interaction: discord.Interaction):
    if not users:
        await interaction.response.send_message("❌ No se pudo conectar a la base de datos.", ephemeral=True)
        return

    user_id = str(interaction.user.id)
    user_data = users.find_one({"discordID": user_id})
    if not user_data:
        await interaction.response.send_message("❌ No estás registrado. Usa `/start` para comenzar.", ephemeral=True)
        return

    avatar_url = interaction.user.avatar.url if interaction.user.avatar else interaction.user.default_avatar.url
    embed = discord.Embed(
        title=f"👤 Perfil de {interaction.user.name}",
        description="Aquí tienes tu información como jugador:",
        color=discord.Color.blurple()
    )
    embed.set_thumbnail(url=avatar_url)
    embed.add_field(name="🆔 ID de Usuario", value=user_data.get("discordID", "Desconocido"), inline=False)
    embed.add_field(name="💰 Monedas", value=user_data.get("monedas", 0), inline=True)
    embed.add_field(name="⚔️ Clase", value=user_data.get("clase", "Sin clase"), inline=True)
    embed.add_field(name="🔝 Nivel", value=user_data.get("nivel", 1), inline=True)
    embed.add_field(name="🏠 Clan", value=user_data.get("clan", "Sin clan"), inline=True)
    embed.add_field(name="💪 Poder Total", value=user_data.get("poder_total", 0), inline=True)

    await interaction.response.send_message(embed=embed)

# === Evento al iniciar el bot ===
@bot.event
async def on_ready():
    print(f"✅ Bot conectado como {bot.user}")
    synced = await bot.tree.sync()
    print(f"🔄 Comandos sincronizados globalmente: {[cmd.name for cmd in synced]}")

# === Iniciar el bot en segundo plano ===
def run_bot():
    asyncio.run(bot.start(TOKEN))

threading.Thread(target=run_bot).start()