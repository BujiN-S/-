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
from discord import ui, ButtonStyle
from discord import Interaction, Embed, Color

# Conexión a MongoDB y colecciones
db_collections = db_connect()
users = db_collections["users"]
core_cards = db_collections["core_cards"]
user_cards = db_collections["user_cards"]
shop_packs = db_collections["shop_packs"]
user_packs = db_collections["user_packs"]
user_formations = db_collections["user_formations"]
user_teams = db_collections["user_teams"]

def color_por_rango(rango):
    colores = {
        "Z": discord.Color.from_rgb(255, 0, 255),
        "S": discord.Color.red(),
        "A": discord.Color.orange(),
        "B": discord.Color.blue(),
        "C": discord.Color.green(),
        "D": discord.Color.dark_gray(),
        "E": discord.Color.light_gray()
    }
    return colores.get(rango.upper(), discord.Color.default())

def generar_embed_carta(carta, mostrar_footer=True):
    embed = discord.Embed(
        color=color_por_rango(carta["rank"]),
        description=(
            f"**📝 Name:** {carta['name']}\n"
            f"**🎖️ Rank:** {carta['rank']}\n"
            f"**🏷️ Class:** {carta['class']}\n"
            f"**🎭 Role:** {carta['role']}\n\n"
            f"**📊 Stats:** 🗡️ATK{carta['stats']['atk']} | 🛡️DEF{carta['stats']['def']} | ⚡VEL{carta['stats']['vel']} | ❤️HP{carta['stats']['hp']} | 🧠INT{carta['stats']['int']}\n"
            f"**🔥 Overall:** {carta['overall']}"
        )
    )
    embed.set_image(url=carta["image"])
    if mostrar_footer:
        embed.set_footer(text="Una nueva presencia se une a tu colección...")
    return embed

def agregar_carta_usuario(user_id, carta):
    user_data = user_cards.find_one({"discordID": user_id})
    if not user_data:
        user_cards.insert_one({"discordID": user_id, "cards": []})
        user_data = user_cards.find_one({"discordID": user_id})

    card_id = len(user_data["cards"]) + 1
    nueva = {
        "card_id": card_id,
        "core_id": carta["id"],  # <- ¡clave!
        "name": carta["name"],
        "class": carta["class"],
        "role": carta["role"],
        "rank": carta["rank"],
        "image": carta.get("image", ""),
        "obtained_at": datetime.utcnow().isoformat()
    }

    user_cards.update_one(
        {"discordID": user_id},
        {"$push": {"cards": nueva}}
    )

    users.update_one(
        {"discordID": user_id},
        {"$inc": {"card_count": 1}},
        upsert=True
    )

def elegir_rank(probabilidades):
    return random.choices(
        list(probabilidades.keys()),
        weights=list(probabilidades.values()),
        k=1
    )[0]

PHRASES_DAILY = [
    "🎁 Los vientos del destino te traen una nueva aliada.",
    "✨ Una energía desconocida se manifiesta en forma de carta.",
    "🔥 ¡Tu poder crece, una carta legendaria ha respondido a tu llamado!",
    "🌙 Una figura misteriosa ha sido atraída por tu aura..."
]

PHRASES_HOURLY = [
    "✨ ¡Una carta ha respondido a tu llamado, viajero del destino!",
    "🌟 Un susurro místico trae una nueva carta a tus manos.",
    "🔮 El tapiz del destino te concede esta carta simbólica.",
    "⚔️ Una guerrera de otro plano irrumpe en tu colección..."
]

DAILY_CD = timedelta(hours=24)
HOURLY_CD = timedelta(hours=1)

DAILY_PROBS = {
    "Z": 0.01,
    "S": 0.07,
    "A": 0.13,
    "B": 0.22,
    "C": 0.25,
    "D": 0.17,
    "E": 0.15
}

HOURLY_PROBS = {
    "Z": 0.001,
    "S": 0.039,
    "A": 0.06,
    "B": 0.17,
    "C": 0.23,
    "D": 0.25,
    "E": 0.25
}

RANK_VALUE = {
    "E": 250,
    "D": 900,
    "C": 1750,
    "B": 4000,
    "A": 6500,
    "S": 11250,
    "Z": 20000
}

FORMATION_TEMPLATES = {
    "f1": {"label": "Formation 1: 2 Frontline, 1 Midline, 1 Backline",
           "frontline": 2, "midline": 1, "backline": 1},
    "f2": {"label": "Formation 2: 1 Frontline, 2 Midline, 1 Backline",
           "frontline": 1, "midline": 2, "backline": 1},
    "f3": {"label": "Formation 3: 1 Frontline, 1 Midline, 2 Backline",
           "frontline": 1, "midline": 1, "backline": 2},
}

def elegir_rank_threshold(probs: dict[str, float]) -> str:
    """
    Recibe un dict rank->prob (suman 1.0), 
    devuelve un rank usando random.random().
    """
    r = random.random()
    acumulado = 0.0
    for rank, p in probs.items():
        acumulado += p
        if r < acumulado:
            return rank
    # por si acaso, devolvemos el último
    return list(probs.keys())[-1]

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

@bot.event
async def on_ready():
    print(f"✅ Bot conectado como {bot.user}")
    synced = await bot.tree.sync()
    print(f"🔄 Comandos sincronizados: {[cmd.name for cmd in synced]}")
    bot.add_view(CatalogView([]))

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
            "poder_total": 0,
            "card_count": 0
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

@bot.tree.command(name="recompensa", description="Reclama tu recompensa diaria.")
async def recompensa(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    user = users.find_one({"discordID": user_id}) or {}
    now = datetime.utcnow()

    # cooldown
    last = user.get("last_daily")
    if last and (now - last) < DAILY_CD:
        rem = DAILY_CD - (now - last)
        h, resto = divmod(int(rem.total_seconds()), 3600)
        m, s = divmod(resto, 60)
        return await interaction.response.send_message(
            f"⏳ Debes esperar {h}h {m}m {s}s.", ephemeral=True
        )

    # monedas + DB se escribirán sólo tras el send
    monedas = random.randint(200, 700)

    # elegir carta
    rank = elegir_rank_threshold(DAILY_PROBS)
    pool = list(core_cards.find({"rank": rank}))
    carta = random.choice(pool) if pool else None

    phrase = random.choice(PHRASES_DAILY)
    if carta:
        # guardo carta en tu colección
        agregar_carta_usuario(user_id, carta)
        # genero embed usando carta["image"]
        embed = discord.Embed(
            color=color_por_rango(carta["rank"]),
            description=f"**{carta['name']}** • {carta['class']} – {carta['role']}"
        )
        embed.set_image(url=carta.get("image", ""))
        await interaction.response.send_message(
            content=f"{phrase}\n🎁 +{monedas} monedas",
            embed=embed,
            ephemeral=True
        )
    else:
        await interaction.response.send_message(
            f"⚠️ No encontré carta de rango `{rank}`. Pero ganaste +{monedas} monedas.",
            ephemeral=True
        )

    # Sólo si llegaste aquí sin excepciones, actualizo BD:
    users.update_one(
        {"discordID": user_id},
        {"$inc": {"monedas": monedas}, "$set": {"last_daily": now}},
        upsert=True
    )

@bot.tree.command(name="cartarecompensa", description="Reclama una carta bonus (1h cooldown).")
async def cartarecompensa(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    user = users.find_one({"discordID": user_id}) or {}
    now = datetime.utcnow()

    # 1) Chequear cooldown
    last = user.get("last_hourly")
    if last and (now - last) < HOURLY_CD:
        rem = HOURLY_CD - (now - last)
        minutes = int(rem.total_seconds() // 60)
        return await interaction.response.send_message(
            f"🕒 Aún debes esperar {minutes} minutos para tu carta bonus.",
            ephemeral=True
        )

    # 2) Selección de rango y carta
    rank = elegir_rank_threshold(HOURLY_PROBS)
    pool = list(core_cards.find({"rank": rank}))
    carta = random.choice(pool) if pool else None
    phrase = random.choice(PHRASES_HOURLY)

    # 3) Intentar enviar respuesta y, si falla, informar
    try:
        if carta:
            # a) Guardar carta en user_cards + card_count
            agregar_carta_usuario(user_id, carta)

            # b) Crear embed usando carta["image"]
            embed = discord.Embed(
                title=carta["name"],
                description=f"Rank: {carta['rank']} • Class: {carta['class']} • Role: {carta['role']}",
                color=color_por_rango(carta["rank"])
            )
            embed.set_image(url=carta["image"])
            embed.set_footer(text=phrase)

            # c) Enviar
            await interaction.response.send_message(
                embed=embed,
                ephemeral=True
            )
        else:
            await interaction.response.send_message(
                f"⚠️ No encontré carta de rango `{rank}`.",
                ephemeral=True
            )
    except Exception as e:
        # Log en consola para debugging
        print(f"[ERROR] /cartarecompensa falló: {e}", flush=True)
        # Informar al usuario
        return await interaction.response.send_message(
            "❌ Ocurrió un error al reclamar tu carta. Intenta de nuevo en un rato.",
            ephemeral=True
        )

    # 4) Sólo si todo salió bien, actualizar cooldown
    users.update_one(
        {"discordID": user_id},
        {"$set": {"last_hourly": now}},
        upsert=True
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

class CatalogView(ui.View):
    def __init__(self, cartas, per_page: int = 10):
        super().__init__(timeout=None)
        self.cartas = cartas
        self.per_page = per_page
        self.current = 0

        self.select = ui.Select(placeholder="Selecciona una carta para ver detalles", options=[])
        self.select.callback = self.on_select
        self.add_item(self.select)

        self.prev_button = ui.Button(label="⬅️ Atrás", style=ButtonStyle.secondary)
        self.next_button = ui.Button(label="➡️ Siguiente", style=ButtonStyle.secondary)
        self.prev_button.callback = self.on_prev
        self.next_button.callback = self.on_next
        self.add_item(self.prev_button)
        self.add_item(self.next_button)

        self.update_select_options()

    def update_select_options(self):
        start = self.current * self.per_page
        end = start + self.per_page
        page = self.cartas[start:end]

        self.select.options.clear()
        for c in page:
            self.select.append_option(discord.SelectOption(label=f"{c['name']} [{c['rank']}]",value=c['id']))

        self.prev_button.disabled = self.current == 0
        max_page = (len(self.cartas) - 1) // self.per_page
        self.next_button.disabled = self.current >= max_page

    async def on_prev(self, interaction: discord.Interaction):
        await interaction.response.defer()
        self.current -= 1
        self.update_select_options()
        await interaction.response.edit_message(embed=self.get_embed(), view=self)

    async def on_next(self, interaction: discord.Interaction):
        self.current += 1
        self.update_select_options()
        await interaction.response.edit_message(embed=self.get_embed(), view=self)

    async def on_select(self, interaction: discord.Interaction):
        carta_id = self.select.values[0]
        carta = next((c for c in self.cartas if c['id'] == carta_id), None)
        if carta:
            embed = generar_embed_carta(carta, mostrar_footer=False)
            await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            await interaction.response.send_message("❌ No se encontró la carta.", ephemeral=True)

    def get_embed(self):
        start = self.current * self.per_page
        end = start + self.per_page
        page = self.cartas[start:end]

        embed = discord.Embed(
            title=f"📚 Catálogo (Página {self.current+1}/{(len(self.cartas)-1)//self.per_page+1})",
            color=discord.Color.blurple()
        )
        for c in page:
            embed.add_field(
                name=f"{c['name']} [{c['rank']}]",
                value=f"Class: {c['class']} • Role: {c['role']}",
                inline=False
            )
        return embed

@bot.tree.command(name="catalog", description="Muestra todas las cartas con navegación y opción de ver detalles.")
async def catalog(interaction: discord.Interaction):
    all_cards = list(core_cards.find())
    if not all_cards:
        await interaction.response.send_message("❌ No hay cartas en la base de datos.", ephemeral=True)
        return

    view = CatalogView(all_cards, per_page=10)
    await interaction.response.send_message(embed=view.get_embed(), view=view)

@bot.tree.command(name="collection", description="Prueba básica: lista tus primeras 10 cartas.")
async def collection(interaction: Interaction):
    uid = str(interaction.user.id)
    user_doc = user_cards.find_one({"discordID": uid})
    cards = user_doc.get("cards", []) if user_doc else []

    if not cards:
        return await interaction.response.send_message(
            "❌ No tienes cartas en tu colección.", ephemeral=True
        )

    # Solo listamos nombre, rango e ID de las primeras 10 cartas
    lines = [
        f"{uc.get('name','?')} [{uc.get('rank','?')}] — ID:{uc.get('card_id','?')}"
        for uc in cards[:10]
    ]
    embed = discord.Embed(
        title="🔍 Tus primeras 10 cartas",
        description="\n".join(lines),
        color=discord.Color.blue()
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="buscarcarta", description="Busca una carta por nombre, clase, rol o rango.")
@app_commands.describe(name="Name (opcional)", class_="Class (opcional)", role="Role (opcional)", rank="Rank (opcional)")
async def buscarcarta(interaction: discord.Interaction, name: str = None, class_: str = None, role: str = None, rank: str = None):
    if not any([name, class_, role, rank]):
        await interaction.response.send_message("❗ Debes especificar al menos un criterio para buscar.", ephemeral=True)
        return

    filtros = {}
    if name:
        filtros["name"] = {"$regex": name, "$options": "i"}
    if class_:
        filtros["class"] = {"$regex": class_, "$options": "i"}
    if role:
        filtros["role"] = {"$regex": role, "$options": "i"}
    if rank:
        filtros["rank"] = rank.upper()

    cartas = list(core_cards.find(filtros))

    if not cartas:
        await interaction.response.send_message("❌ No se encontraron cartas con los criterios dados.", ephemeral=True)
        return

    if len(cartas) == 1:
        embed = generar_embed_carta(cartas[0], con_footer=False)
        await interaction.response.send_message(embed=embed, ephemeral=True)
    else:
        view = CatalogView(cartas, per_page=10)
        await interaction.response.send_message(embed=view.get_embed(), view=view, ephemeral=True)

# —————————————————————————————
# ShopView y ShopButton revisados
# —————————————————————————————
class ShopView(ui.View):
    def __init__(self, packs):
        super().__init__(timeout=None)
        for pack in packs:
            # cada botón lleva su propio pack_id en custom_id
            self.add_item(ShopButton(str(pack["id"])))

class ShopButton(ui.Button):
    def __init__(self, pack_id: str):
        self.pack_id = pack_id
        # llamamos a la BD para obtener nombre / precio
        pack = shop_packs.find_one({"id": pack_id})
        label = f"Comprar {pack['name']}"
        super().__init__(label=label, style=discord.ButtonStyle.green, custom_id=pack_id)

    async def callback(self, interaction: Interaction):
        user_id = str(interaction.user.id)
        # 1) Verifico usuario
        user = users.find_one({"discordID": user_id})
        if not user:
            return await interaction.response.send_message("❌ No estás registrado. Usa `/start`.", ephemeral=True)

        # 2) Re-leo pack desde BD (por si cambió)
        pack = shop_packs.find_one({"id": self.pack_id})
        if not pack:
            return await interaction.response.send_message("❌ Este pack ya no existe.", ephemeral=True)

        price = pack["price"]
        if user.get("monedas", 0) < price:
            return await interaction.response.send_message("❌ No tienes suficientes monedas.", ephemeral=True)

        # 3) Transacción atómica: resto monedas
        users.update_one(
            {"discordID": user_id},
            {"$inc": {"monedas": -price}}
        )

        # 4) Sumar pack al inventario con $inc o $push atómico
        res = user_packs.update_one(
            {"discordID": user_id, "packs.id": self.pack_id},
            {"$inc": {"packs.$.count": 1}}
        )
        if res.matched_count == 0:
            # no existía, lo creamos
            user_packs.update_one(
                {"discordID": user_id},
                {"$push": {"packs": {"id": self.pack_id, "count": 1}}},
                upsert=True
            )

        # 5) Confirmación al usuario
        await interaction.response.send_message(
            f"📦 Has comprado un **{pack['name']}** por {price} monedas.",
            ephemeral=True
        )

# —————————————————————————————
# Comando /shop corregido
# —————————————————————————————
@bot.tree.command(name="shop", description="Mira y compra packs en la tienda.")
async def shop(interaction: Interaction):
    user_id = str(interaction.user.id)

    # Validar registro y saldo
    user = users.find_one({"discordID": user_id})
    if not user:
        return await interaction.response.send_message("❌ No estás registrado. Usa `/start`.", ephemeral=True)

    packs = list(shop_packs.find())
    if not packs:
        return await interaction.response.send_message("🛒 La tienda está vacía.", ephemeral=True)

    # Construyo embed
    embed = Embed(
        title="🛍️ Tienda de Packs",
        description=f"💰 Monedas: **{user.get('monedas', 0)}**",
        color=discord.Color.gold()
    )
    for p in packs:
        embed.add_field(
            name=f"{p['name']} — 💰 {p['price']}",
            value=f"_{p['description']}_\nZ: {p['rewards']['Z']*100:.2f}% • S: {p['rewards']['S']*100:.2f}%",
            inline=False
        )

    # Muestro botones
    view = ShopView(packs)
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

class AbrirPackView(ui.View):
    def __init__(self, uid: str, packs: list[dict]):
        super().__init__(timeout=None)
        self.uid = uid
        for pack in packs:
            self.add_item(AbrirPackButton(pack["id"], pack["count"], uid))

class AbrirPackButton(ui.Button):
    def __init__(self, pack_id: str, count: int, user_id: str):
        pack = shop_packs.find_one({"id": pack_id})
        label = f"Abrir {pack['name']} ({count})"
        super().__init__(label=label, style=ButtonStyle.blurple, custom_id=f"abrir_{pack_id}")
        self.pack_id = pack_id
        self.user_id = user_id

    async def callback(self, interaction: Interaction):
        if str(interaction.user.id) != self.user_id:
            return await interaction.response.send_message("❌ Este botón no es para ti.", ephemeral=True)

        await interaction.response.defer()

        # 1. Restar un pack
        result = user_packs.update_one(
            {"discordID": self.user_id, "packs.id": self.pack_id, "packs.count": {"$gt": 0}},
            {"$inc": {"packs.$.count": -1}}
        )
        if result.modified_count == 0:
            return await interaction.followup.send("❌ Ya no te queda ese pack.", ephemeral=True)

        # 2. Limpiar los que quedaron en 0
        user_packs.update_one(
            {"discordID": self.user_id},
            {"$pull": {"packs": {"id": self.pack_id, "count": 0}}}
        )

        # 3. Elegir carta y agregarla
        pack = shop_packs.find_one({"id": self.pack_id})
        rank = elegir_rank_threshold(pack["rewards"])
        pool = list(core_cards.find({"rank": rank}))
        carta = random.choice(pool)
        agregar_carta_usuario(self.user_id, carta)

        # Mostrar solo la imagen de la carta
        carta_embed = Embed(color=color_por_rango(carta["rank"]))
        carta_embed.set_image(url=carta.get("image", ""))
        carta_embed.set_footer(text=f"🎁 Abriste un {pack['name']}")


        # 4. Mostrar packs restantes
        doc = user_packs.find_one({"discordID": self.user_id})
        packs_actuales = doc.get("packs", [])
        desc = "\n".join(
            f"{shop_packs.find_one({'id': p['id']})['name']} ({p['count']})"
            for p in packs_actuales
        ) or "No tienes packs."

        lista_embed = Embed(
            title="📦 Packs disponibles",
            description=desc,
            color=Color.purple()
        )

        await interaction.followup.send(
            content=f"{interaction.user.mention} abrió un pack!",
            embeds=[lista_embed, carta_embed],
            view=AbrirPackView(self.user_id, packs_actuales)
        )

@bot.tree.command(name="abrir", description="Abre uno de tus packs guardados.")
async def abrir(interaction: Interaction):
    uid = str(interaction.user.id)
    doc = user_packs.find_one({"discordID": uid})
    if not doc or not doc.get("packs"):
        return await interaction.response.send_message("❌ No tienes packs guardados.", ephemeral=True)

    desc = "\n".join(
        f"{shop_packs.find_one({'id': p['id']})['name']} ({p['count']})"
        for p in doc["packs"]
    )
    embed = Embed(
        title="🎁 Tus Packs",
        description=desc,
        color=Color.purple()
    )
    view = AbrirPackView(uid, doc["packs"])
    await interaction.response.send_message(embed=embed, view=view)

@bot.tree.command(name="vender", description="Vende una carta que poseas usando su ID único.")
@app_commands.describe(id="ID de la carta que deseas vender")
async def vender(interaction: Interaction, id: str):
    uid = str(interaction.user.id)

    # 1️⃣ Comprobar si la carta está en el equipo activo
    team_doc = user_teams.find_one({"discordID": uid})
    if team_doc and "team" in team_doc:
        used_ids = []
        for zone in ("frontline", "midline", "backline"):
            # extraemos los IDs como strings
            used_ids += [str(cid) for cid in team_doc["team"].get(zone, [])]
        if id in used_ids:
            return await interaction.response.send_message(
                "❌ No puedes vender una carta que está en tu equipo activo.", 
                ephemeral=True
            )

    # 2️⃣ Recuperar la carta por su card_id de tu colección
    doc = user_cards.find_one({"discordID": uid})
    if not doc or "cards" not in doc:
        return await interaction.response.send_message("❌ No tienes cartas.", ephemeral=True)

    carta = next((c for c in doc["cards"] if str(c.get("card_id")) == id), None)
    if not carta:
        return await interaction.response.send_message(
            "❌ No se encontró ninguna carta con ese ID.", 
            ephemeral=True
        )

    # 3️⃣ Determinar valor de venta según rango
    rango = carta.get("rank", "E")
    valor = RANK_VALUE.get(rango, 0)

    # 4️⃣ Eliminar la carta de tu colección
    user_cards.update_one(
        {"discordID": uid},
        {"$pull": {"cards": {"card_id": carta["card_id"]}}}
    )

    # 5️⃣ Otorgar las monedas
    users.update_one(
        {"discordID": uid},
        {"$inc": {"monedas": valor}}
    )

    # 6️⃣ Confirmación al usuario
    embed = Embed(
        title="💰 Carta vendida",
        description=(
            f"Vendiste **{carta['name']}** [{rango}]\n"
            f"Ganaste **{valor} monedas**."
        ),
        color=Color.gold()
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)

# Asumimos colecciones MongoDB inicializadas:
# user_formations, user_teams, user_cards

# 1️⃣ /formacion: eliges directamente la plantilla por nombre
@bot.tree.command(name="formacion", description="Elige tu plantilla de formación 4v4.")
@app_commands.choices(
    plantilla=[
        app_commands.Choice(name="2 Frontline, 1 Midline, 1 Backline", value="f1"),
        app_commands.Choice(name="1 Frontline, 2 Midline, 1 Backline", value="f2"),
        app_commands.Choice(name="1 Frontline, 1 Midline, 2 Backline", value="f3"),
    ]
)
async def formacion(
    interaction: discord.Interaction,
    plantilla: app_commands.Choice[str],
):
    # Guardar la plantilla elegida (solo la key: f1, f2 o f3)
    user_formations.update_one(
        {"user_id": str(interaction.user.id)},
        {"$set": {"template_key": plantilla.value}},
        upsert=True
    )
    await interaction.response.send_message(
        f"✔️ Has seleccionado la plantilla **{plantilla.name}**.",
        ephemeral=True
    )

# 2️⃣ /equipo: rellenas la plantilla pasando IDs en orden
@bot.tree.command(name="equipo", description="Rellena tu plantilla con los IDs de tus cartas.")
@app_commands.describe(
    frontline1="ID carta Frontline #1",
    frontline2="ID carta Frontline #2 (si tu plantilla pide 2)",
    midline1="ID carta Midline #1",
    midline2="ID carta Midline #2 (si tu plantilla pide 2)",
    backline1="ID carta Backline #1",
    backline2="ID carta Backline #2 (si tu plantilla pide 2)",
)
async def equipo(
    interaction: discord.Interaction,
    frontline1: str,
    frontline2: str = None,
    midline1: str = None,
    midline2: str = None,
    backline1: str = None,
    backline2: str = None,
):
    # 1. Recuperar plantilla
    record = user_formations.find_one({"user_id": str(interaction.user.id)})
    if not record or "template_key" not in record:
        return await interaction.response.send_message(
            "❌ Primero elige tu plantilla con `/formacion`.",
            ephemeral=True
        )
    tpl = FORMATION_TEMPLATES[record["template_key"]]

    # 2. Construir listas según la plantilla
    zones = {
        "frontline": [frontline1, frontline2],
        "midline":   [midline1,   midline2],
        "backline":  [backline1,  backline2],
    }
    selected = {}
    for zone, needed in tpl.items():
        # filtra None y valida longitud
        ids = [i for i in zones[zone] if i]
        if len(ids) != needed:
            return await interaction.response.send_message(
                f"❌ Tu plantilla requiere {needed} IDs en **{zone}**, "
                f"pero diste {len(ids)}.",
                ephemeral=True
            )
        selected[zone] = ids

    # 3. Guardar en DB
    user_teams.update_one(
        {"user_id": str(interaction.user.id)},
        {"$set": {"team": selected}},
        upsert=True
    )

    # 4. Responder con un mensaje sencillo
    texto = "✅ Formación guardada:\n"
    for zone, ids in selected.items():
        texto += f"**{zone.title()}**: {', '.join(ids)}\n"

    await interaction.response.send_message(texto, ephemeral=True)


def run_bot():
    asyncio.run(bot.start(TOKEN))

threading.Thread(target=run_bot).start()

# === Ejecutar app Flask ===
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)))