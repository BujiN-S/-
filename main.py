import os
import discord
import threading
import asyncio
from discord.ext import commands
from flask import Flask
from db.database import db_connect, verify_user, register_user
from datetime import datetime, timedelta
import random

# === Configuración Flask ===
app = Flask(__name__)

@app.route('/')
def index():
    return "✅ Bot activo desde Render."

# === Configuración bot Discord ===
TOKEN = "MTM1MjQ5NTYxMjgxMzI1MDY0MA.G3LmNo.Y1xgmu5UznG3yitpLk8MOmRsHEpcLCliAkGN0k"
APP_ID = 1352495612813250640

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents, application_id=APP_ID)
users = db_connect()

@bot.event
async def on_ready():
    print(f"✅ Bot conectado como {bot.user}")
    synced = await bot.tree.sync()
    print(f"🔄 Comandos sincronizados: {[cmd.name for cmd in synced]}")

@bot.tree.command(name="start", description="Start your adventure!")
async def start(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    user_name = interaction.user.name

    if users.find_one({"discordID": user_id}):
        await interaction.response.send_message("✅ Ya estás registrado.", ephemeral=True)
    else:
        users.insert_one({
            "discordID": user_id,
            "userName": user_name,
            "monedas": 0,
            "clase": "Sin clase",
            "nivel": 1,
            "clan": "Sin clan",
            "poder_total": 0
        })
        await interaction.response.send_message("🎉 ¡Tu aventura ha comenzado!", ephemeral=True)

@bot.tree.command(name="perfil", description="Muestra el perfil del jugador")
async def perfil(interaction: discord.Interaction):
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

# === Comando /recompensa ===
cooldowns = {}

def generar_recompensa():
    prob = random.random()
    if prob < 0.4:
        return random.randint(0, 500)
    elif prob < 0.7:
        return random.randint(500, 1500)
    elif prob < 0.9:
        return random.randint(1500, 3000)
    elif prob < 0.98:
        return random.randint(3000, 7000)
    else:
        return random.randint(7000, 10000)

@bot.tree.command(name="recompensa", description="Reclama tu recompensa diaria.")
async def recompensa(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    user_data = users.find_one({"discordID": user_id})

    if not user_data:
        await interaction.response.send_message("❌ No estás registrado. Usa `/start` para comenzar.", ephemeral=True)
        return

    now = datetime.utcnow()
    cooldown = cooldowns.get(user_id)

    if cooldown and now < cooldown:
        restante = cooldown - now
        horas = int(restante.total_seconds() // 3600)
        minutos = int((restante.total_seconds() % 3600) // 60)
        await interaction.response.send_message(
            f"⏳ Ya reclamaste tu recompensa.\nVuelve en {horas}h {minutos}min.",
            ephemeral=True
        )
        return

    recompensa = generar_recompensa()
    nueva_cantidad = user_data["monedas"] + recompensa

    users.update_one(
        {"discordID": user_id},
        {"$set": {"monedas": nueva_cantidad}}
    )

    cooldowns[user_id] = now + timedelta(hours=24)

    await interaction.response.send_message(
        f"🎁 Has recibido **{recompensa} monedas**.\n💰 Ahora tienes **{nueva_cantidad} monedas**.",
        ephemeral=True
    )

# === Ejecutar bot en segundo plano ===
def run_bot():
    asyncio.run(bot.start(TOKEN))

threading.Thread(target=run_bot).start()

# === Ejecutar app Flask ===
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)))