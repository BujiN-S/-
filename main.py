import os
import discord
import threading
import asyncio
from discord.ext import commands
from discord import app_commands
from flask import Flask
from db.database import db_connect, verify_user, register_user
from datetime import datetime, timedelta
import random

db_collections = db_connect()
cooldowns = {}

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

probabilidades = {
    "Z": 0.001,
    "S": 0.01,
    "A": 0.04,
    "B": 0.1,
    "C": 0.2,
    "D": 0.25,
    "E": 0.399  # Total 1.0
}

def elegir_rango():
    r = random.random()
    acumulado = 0
    for rango, prob in sorted(probabilidades.items(), key=lambda x: -x[1]):  # Mayor a menor
        acumulado += prob
        if r <= acumulado:
            return rango
    return "E"  # Fallback

def generar_recompensa_monedas():
    prob = random.random()
    if prob < 0.4:
        return random.randint(0, 300)
    elif prob < 0.7:
        return random.randint(300, 800)
    elif prob < 0.9:
        return random.randint(800, 1500)
    elif prob < 0.98:
        return random.randint(1500, 2500)
    else:
        return random.randint(2500, 4000)

@bot.tree.command(name="recompensa", description="Reclama tu recompensa diaria.")
async def recompensa(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    db_collections = db_connect()
    users = db_collections["users"]
    cards = db_collections["cards"]

    user_data = users.find_one({"discordID": user_id})
    if not user_data:
        await interaction.response.send_message("❌ No estás registrado. Usa `/start` para comenzar.", ephemeral=True)
        return

    now = datetime.utcnow()
    ultimo = user_data.get("ultimo_reclamo")

    if ultimo:
        diferencia = now - ultimo
        if diferencia < timedelta(hours=24):
            restante = timedelta(hours=24) - diferencia
            horas = restante.seconds // 3600
            minutos = (restante.seconds % 3600) // 60
            await interaction.response.send_message(
                f"⏳ Ya reclamaste tu recompensa.\nVuelve en {horas}h {minutos}min.",
                ephemeral=True
            )
            return

    # Monedas reducidas por carta
    recompensa_monedas = generar_recompensa_monedas()
    nueva_cantidad = user_data["monedas"] + recompensa_monedas

    # 🎴 Obtener carta aleatoria
    rango = elegir_rango()
    posibles_cartas = list(cards.find({"rank": rango}))
    if not posibles_cartas:
        await interaction.response.send_message("❌ No hay cartas disponibles para este rango.", ephemeral=True)
        return
    carta = random.choice(posibles_cartas)

    # 🎲 Agregamos la carta al inventario del usuario
    carta_id_unica = f"{carta['id']}_{random.randint(100000, 999999)}"
    nueva_carta = {
        "id_instancia": carta_id_unica,
        "id_carta": carta["id"],
        "nombre": carta["name"],
        "rank": carta["rank"],
        "fecha_obtenida": now
    }

    users.update_one(
        {"discordID": user_id},
        {
            "$set": {
                "monedas": nueva_cantidad,
                "ultimo_reclamo": now
            },
            "$push": {
                "cartas": nueva_carta
            }
        }
    )

    await interaction.response.send_message(
        f"🎁 Has recibido **{recompensa_monedas} monedas** y una carta:\n"
        f"**{carta['name']}** [{carta['rank']}]\n"
        f"🖼 {carta['image']}"
    )

# Conexión a la base de datos
db = db_connect()

if db:
    users = db["users"]
    core_cards = db["core_cards"]  # <- Asegurate de que la colección se llame así
else:
    print("❌ No se pudo conectar a la base de datos.")

# === Comando /cartarecompensa ===
@bot.tree.command(name="cartarecompensa", description="Reclama una carta gratis cada hora.")
async def cartarecompensa(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    user_data = users.find_one({"discordID": user_id})

    if not user_data:
        await interaction.response.send_message("❌ No estás registrado. Usa `/start` para comenzar.", ephemeral=True)
        return

    now = datetime.utcnow()
    ultimo = user_data.get("ultimo_reclamo_carta")

    if ultimo and now - ultimo < timedelta(hours=1):
        restante = timedelta(hours=1) - (now - ultimo)
        minutos = restante.seconds // 60
        await interaction.response.send_message(
            f"⏳ Ya reclamaste tu carta.\nVuelve en {minutos} minutos.",
            ephemeral=True
        )
        return

    # 🎲 Determinar rareza de la carta
    prob = random.random()
    if prob < 0.001:
        rank = "Z"
    elif prob < 0.04:
        rank = "S"
    elif prob < 0.10:
        rank = "A"
    elif prob < 0.25:
        rank = "B"
    elif prob < 0.45:
        rank = "C"
    elif prob < 0.70:
        rank = "D"
    else:
        rank = "E"

    # 📦 Buscar una carta aleatoria de esa rareza
    cartas_disponibles = list(core_cards.find({"rank": rank}))
    if not cartas_disponibles:
        await interaction.response.send_message("❌ No hay cartas disponibles de esta rareza.", ephemeral=True)
        return

    carta_obtenida = random.choice(cartas_disponibles)

    # 🆔 Crear carta única para el jugador
    carta_jugador = {
        "carta_id": carta_obtenida["id"],
        "instancia_id": str(random.getrandbits(64)),  # ID única
        "fecha_obtenida": now.isoformat()
    }

    users.update_one(
        {"discordID": user_id},
        {
            "$push": {"cartas": carta_jugador},
            "$set": {"ultimo_reclamo_carta": now}
        }
    )

    await interaction.response.send_message(
        f"🎴 Obtuviste la carta **{carta_obtenida['name']}** [**{rank}**]\n{carta_obtenida['image']}"
    )

@bot.tree.command(name="balance", description="Consulta cuántas monedas tienes.")
async def balance(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    user_name = interaction.user.name
    avatar_url = interaction.user.avatar.url if interaction.user.avatar else interaction.user.default_avatar.url

    user_data = users.find_one({"discordID": user_id})

    if not user_data:
        await interaction.response.send_message("❌ No estás registrado. Usa `/start` para comenzar.", ephemeral=True)
        return

    monedas = user_data.get("monedas", 0)

    embed = discord.Embed(
        title=f"💰 Balance de {user_name}",
        description=f"Tienes **{monedas} monedas** actualmente.",
        color=discord.Color.gold()
    )
    embed.set_thumbnail(url=avatar_url)
    embed.set_footer(text="¡Sigue jugando para ganar más monedas!")

    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="apostar", description="Apuesta una cantidad de monedas y pon a prueba tu suerte.")
@app_commands.describe(cantidad="Cantidad de monedas a apostar")
async def apostar(interaction: discord.Interaction, cantidad: int):
    user_id = str(interaction.user.id)
    user_name = interaction.user.name
    avatar_url = interaction.user.avatar.url if interaction.user.avatar else interaction.user.default_avatar.url

    # Validar cantidad
    if cantidad <= 0:
        await interaction.response.send_message("❌ La cantidad debe ser mayor que cero.", ephemeral=True)
        return

    user_data = users.find_one({"discordID": user_id})
    if not user_data:
        await interaction.response.send_message("❌ No estás registrado. Usa `/start` para comenzar.", ephemeral=True)
        return

    monedas_actuales = user_data.get("monedas", 0)
    if cantidad > monedas_actuales:
        await interaction.response.send_message("❌ No tienes suficientes monedas para apostar esa cantidad.", ephemeral=True)
        return

    # Generar resultado
    prob = random.random()
    if prob < 0.20:
        multiplicador = 0    # pierde todo
        resultado = "❌ Perdiste todo"
    elif prob < 0.50:
        multiplicador = 0.5  # pierde la mitad
        resultado = "⚠️ Perdiste la mitad"
    elif prob < 0.80:
        multiplicador = 1    # recupera
        resultado = "✅ Recuperaste tu apuesta"
    elif prob < 0.95:
        multiplicador = 2    # gana el doble
        resultado = "💰 ¡Ganaste el doble!"
    else:
        multiplicador = 3    # gana el triple
        resultado = "🔥 ¡CRÍTICO! ¡Ganaste el triple!"

    ganancia = int(cantidad * multiplicador)
    nuevas_monedas = monedas_actuales - cantidad + ganancia

    users.update_one(
        {"discordID": user_id},
        {"$set": {"monedas": nuevas_monedas}}
    )

    # Embed del resultado
    embed = discord.Embed(
        title="🎲 Resultado de la apuesta",
        description=f"{resultado}\n\n💸 Apostaste: **{cantidad} monedas**\n💰 Ganaste: **{ganancia} monedas**",
        color=discord.Color.orange()
    )
    embed.set_thumbnail(url=avatar_url)
    embed.set_footer(text=f"Nuevo balance: {nuevas_monedas} monedas")

    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="dar", description="Envía monedas a otro jugador.")
@app_commands.describe(usuario="Jugador que recibirá las monedas", cantidad="Cantidad a enviar")
async def dar(interaction: discord.Interaction, usuario: discord.User, cantidad: int):
    emisor_id = str(interaction.user.id)
    receptor_id = str(usuario.id)
    emisor_nombre = interaction.user.name
    avatar_url = interaction.user.avatar.url if interaction.user.avatar else interaction.user.default_avatar.url

    if cantidad <= 0:
        await interaction.response.send_message("❌ La cantidad debe ser mayor que cero.", ephemeral=True)
        return

    if emisor_id == receptor_id:
        await interaction.response.send_message("❌ No puedes darte monedas a ti mismo, genio.", ephemeral=True)
        return

    # Verificar que ambos estén registrados
    emisor = users.find_one({"discordID": emisor_id})
    receptor = users.find_one({"discordID": receptor_id})

    if not emisor:
        await interaction.response.send_message("❌ No estás registrado. Usa `/start` para comenzar.", ephemeral=True)
        return

    if not receptor:
        await interaction.response.send_message(f"❌ {usuario.name} no está registrado.", ephemeral=True)
        return

    saldo_emisor = emisor.get("monedas", 0)
    if saldo_emisor < cantidad:
        await interaction.response.send_message("❌ No tienes suficientes monedas para enviar esa cantidad.", ephemeral=True)
        return

    # Transferencia
    nuevo_emisor = saldo_emisor - cantidad
    nuevo_receptor = receptor.get("monedas", 0) + cantidad

    users.update_one({"discordID": emisor_id}, {"$set": {"monedas": nuevo_emisor}})
    users.update_one({"discordID": receptor_id}, {"$set": {"monedas": nuevo_receptor}})

    # Embed de confirmación
    embed = discord.Embed(
        title="💸 Transferencia completada",
        description=(
            f"Has enviado **{cantidad} monedas** a {usuario.mention}.\n"
            f"Tu nuevo saldo es de **{nuevo_emisor} monedas**."
        ),
        color=discord.Color.green()
    )
    embed.set_thumbnail(url=avatar_url)
    embed.set_footer(text="Gracias por compartir tus riquezas 💰")

    await interaction.response.send_message(embed=embed)

# === Ejecutar bot en segundo plano ===
def run_bot():
    asyncio.run(bot.start(TOKEN))

threading.Thread(target=run_bot).start()

# === Ejecutar app Flask ===
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)))