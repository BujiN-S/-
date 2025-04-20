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

# Conexión a MongoDB y colecciones
db_collections = db_connect()
users = db_collections["users"]
core_cards = db_collections["core_cards"]
user_cards = db_collections["user_cards"]

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
    embed.set_image(url=carta["image_url"])
    if mostrar_footer:
        embed.set_footer(text="Una nueva presencia se une a tu colección...")
    return embed

def agregar_carta_usuario(user_id, carta):
    user_cards_data = user_cards.find_one({"discordID": user_id})
    if not user_cards_data:
        user_cards.insert_one({"discordID": user_id, "cards": []})
        user_cards_data = user_cards.find_one({"discordID": user_id})
    card_id = len(user_cards_data["cards"]) + 1
    nueva = {
        "card_id": card_id,
        "name": carta["name"],
        "class": carta["class"],
        "role": carta["role"],
        "rank": carta["rank"],
        "image_url": carta["image_url"],
        "obtained_at": datetime.utcnow().isoformat()
    }
    user_cards.update_one({"discordID": user_id}, {"$push": {"cards": nueva}})

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
    "Z": 0.001,
    "S": 0.01,
    "A": 0.07,
    "B": 0.15,
    "C": 0.21,
    "D": 0.26,
    "E": 0.29
}

HOURLY_PROBS = {
    "Z": 0.001,
    "S": 0.039,
    "A": 0.06,
    "B": 0.15,
    "C": 0.20,
    "D": 0.25,
    "E": 0.30
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

    # 1) Verificar cooldown
    last = user.get("last_daily")
    if last and now - last < DAILY_CD:
        rem = DAILY_CD - (now - last)
        h, resto = divmod(int(rem.total_seconds()), 3600)
        m, s = divmod(resto, 60)
        return await interaction.response.send_message(
            f"⏳ Debes esperar {h}h {m}m {s}s para tu siguiente diaria.",
            ephemeral=True
        )

    # 2) Recompensa de monedas
    monedas = random.randint(200, 700)
    users.update_one(
        {"discordID": user_id},
        {"$inc": {"monedas": monedas}, "$set": {"last_daily": now}},
        upsert=True
    )

    # 3) Seleccionar carta
    rank = elegir_rank_threshold(DAILY_PROBS)
    pool = list(core_cards.find({"rank": rank}))
    carta = random.choice(pool) if pool else None

    # 4) Responder
    phrase = random.choice(PHRASES_DAILY)
    if carta:
        agregar_carta_usuario(user_id, carta)
        embed = generar_embed_carta(carta)
        await interaction.response.send_message(
            content=f"{phrase}\n🎁 **+{monedas} monedas**",
            embed=embed,
            ephemeral=True
        )
    else:
        await interaction.response.send_message(
            f"⚠️ No encontré carta de rango `{rank}`, pero ganaste **{monedas} monedas**.",
            ephemeral=True
        )

@bot.tree.command(name="cartarecompensa", description="Reclama una carta bonus (1h cooldown).")
async def cartarecompensa(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    user = users.find_one({"discordID": user_id}) or {}
    now = datetime.utcnow()

    # 1) Verificar cooldown
    last = user.get("last_hourly")
    if last and now - last < HOURLY_CD:
        rem = HOURLY_CD - (now - last)
        m = int(rem.total_seconds() // 60)
        return await interaction.response.send_message(
            f"🕒 Aún debes esperar {m} minutos para tu carta bonus.",
            ephemeral=True
        )

    users.update_one(
        {"discordID": user_id},
        {"$set": {"last_hourly": now}},
        upsert=True
    )

    # 2) Seleccionar carta
    rank = elegir_rank_threshold(HOURLY_PROBS)
    pool = list(core_cards.find({"rank": rank}))
    carta = random.choice(pool) if pool else None

    # 3) Responder
    phrase = random.choice(PHRASES_HOURLY)
    if carta:
        agregar_carta_usuario(user_id, carta)
        embed = generar_embed_carta(carta)
        await interaction.response.send_message(
            content=phrase,
            embed=embed,
            ephemeral=True
        )
    else:
        await interaction.response.send_message(
            f"⚠️ No encontré carta de rango `{rank}`.",
            ephemeral=True
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

@bot.tree.command(name="collection", description="Muestra tus cartas obtenidas.")
async def collection(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    user_cards = db_collections["user_cards"]

    # Obtener los datos del usuario
    user_cards_data = user_cards.find_one({"discordID": user_id})

    if not user_cards_data or not user_cards_data.get("cards"):
        await interaction.response.send_message("❌ No tienes cartas en tu colección.", ephemeral=True)
        return

    cards = user_cards_data["cards"]

    # Si hay muchas cartas, implementamos paginación
    page_size = 5
    total_pages = (len(cards) // page_size) + (1 if len(cards) % page_size > 0 else 0)

    # Página actual por defecto
    page = 1

    # Generamos el embed inicial
    embed = discord.Embed(
        title=f"🔮 Tu colección de cartas ({len(cards)} total)",
        description=f"Página {page}/{total_pages}",
        color=discord.Color.blue()
    )

    # Mostramos las cartas de la página actual
    start_index = (page - 1) * page_size
    end_index = start_index + page_size
    current_page_cards = cards[start_index:end_index]

    for carta in current_page_cards:
        embed.add_field(
            name=carta["name"],
            value=f"**Rango**: {carta['rank']}\n**Clase**: {carta['class']}\n**Rol**: {carta['role']}",
            inline=False
        )
        embed.set_image(url=carta["image_url"])

    # Enviar el embed con las cartas de la página
    message = await interaction.response.send_message(embed=embed, ephemeral=True)

    # Si hay más de una página, agregar botones para navegar
    if total_pages > 1:
        await message.add_reaction("⬅️")  # Botón de página anterior
        await message.add_reaction("➡️")  # Botón de siguiente página

        # Esperar reacciones y manejar la paginación
        def check(reaction, user):
            return user == interaction.user and str(reaction.emoji) in ["⬅️", "➡️"]

        try:
            reaction, user = await bot.wait_for("reaction_add", check=check, timeout=60.0)
            
            if str(reaction.emoji) == "➡️" and page < total_pages:
                page += 1
            elif str(reaction.emoji) == "⬅️" and page > 1:
                page -= 1

            # Rehacer el embed con la nueva página
            embed.description = f"Página {page}/{total_pages}"

            current_page_cards = cards[(page - 1) * page_size: page * page_size]
            embed.clear_fields()

            for carta in current_page_cards:
                embed.add_field(
                    name=carta["name"],
                    value=f"**Rango**: {carta['rank']}\n**Clase**: {carta['class']}\n**Rol**: {carta['role']}",
                    inline=False
                )
                embed.set_image(url=carta["image_url"])

            # Actualizar el mensaje con la nueva página de cartas
            await message.edit(embed=embed)
            await message.remove_reaction(reaction, user)
        except asyncio.TimeoutError:
            await message.clear_reactions()

# === Ejecutar bot en segundo plano ===
def run_bot():
    asyncio.run(bot.start(TOKEN))

threading.Thread(target=run_bot).start()

# === Ejecutar app Flask ===
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080))) 