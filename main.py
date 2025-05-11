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
from discord import Interaction, Embed, Color, Message
from discord.ui import View, Button
import copy
import logging
import traceback
from discord.errors import HTTPException
import pymongo
from pymongo.errors import DuplicateKeyError
from pymongo import ASCENDING


# at top of your bot file
logger = logging.getLogger("discord")
logger.setLevel(logging.ERROR)
handler = logging.FileHandler(filename="bot_errors.log", encoding="utf-8", mode="a")
logger.addHandler(handler)

# Conexión a MongoDB y colecciones
db_collections = db_connect()
users = db_collections["users"]
core_cards = db_collections["core_cards"]
user_cards = db_collections["user_cards"]
shop_packs = db_collections["shop_packs"]
user_packs = db_collections["user_packs"]
user_formations = db_collections["user_formations"]
user_teams = db_collections["user_teams"]
pvp_queue = db_collections["pvp_queue"]

pvp_queue.create_index("timestamp", expireAfterSeconds=180)
pvp_queue.create_index([('createdAt', ASCENDING)])

def color_by_rank(rank):
    colors = {
        "Z": discord.Color.from_rgb(255, 0, 255),
        "S": discord.Color.red(),
        "A": discord.Color.orange(),
        "B": discord.Color.blue(),
        "C": discord.Color.green(),
        "D": discord.Color.dark_gray(),
        "E": discord.Color.light_gray()
    }
    return colors.get(rank.upper(), discord.Color.default())

def generate_card_embed(card, show_footer=True):
    embed = discord.Embed(
        color=color_by_rank(card["rank"]),
        description=(
            f"**📝 Name:** {card['name']}\n"
            f"**🎖️ Rank:** {card['rank']}\n"
            f"**🏷️ Class:** {card['class']}\n"
            f"**🎭 Role:** {card['role']}\n\n"
            f"**📊 Stats:** 🗡️ATK{card['stats']['atk']} | 🛡️DEF{card['stats']['def']} | ⚡VEL{card['stats']['vel']} | ❤️HP{card['stats']['hp']} | 🧠INT{card['stats']['int']}\n"
            f"**🔥 Overall:** {card['overall']}"
        )
    )
    embed.set_image(url=card["image"])
    if show_footer:
        embed.set_footer(text="A new presence joins your collection...")
    return embed

def add_user_card(user_id, card):
    user_data = user_cards.find_one({"discordID": user_id})
    if not user_data:
        user_cards.insert_one({"discordID": user_id, "cards": []})
        user_data = user_cards.find_one({"discordID": user_id})

    card_id = len(user_data["cards"]) + 1
    new = {
        "card_id": card_id,
        "core_id": card["id"],  # <- ¡clave!
        "name": card["name"],
        "class": card["class"],
        "role": card["role"],
        "rank": card["rank"],
        "image": card.get("image", ""),
        "obtained_at": datetime.utcnow().isoformat()
    }

    user_cards.update_one(
        {"discordID": user_id},
        {"$push": {"cards": new}}
    )

    users.update_one(
        {"discordID": user_id},
        {"$inc": {"card_count": 1}},
        upsert=True
    )

def choose_rank(probabilities):
    return random.choices(
        list(probabilities.keys()),
        weights=list(probabilities.values()),
        k=1
    )[0]

PHRASES_DAILY = [
    "🎁 The winds of destiny bring you a new ally.",
    "✨ An unknown energy manifests as a card.",
    "🔥 Your power grows, a legendary card has answered your call!",
    "🌙 A mysterious figure has been lured by your aura..."
]

PHRASES_HOURLY = [
    "✨ A card has answered your call, traveler of destiny!",
    "🌟 A mystical whisper brings a new card into your hands.",
    "🔮 The tapestry of destiny grants you this symbolic card.",
    "⚔️ A warrior from another realm bursts into your collection..."
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

def choose_rank_threshold(probs: dict[str, float]) -> str:
    """
    Recibe un dict rank->prob (suman 1.0), 
    devuelve un rank usando random.random().
    """
    r = random.random()
    Accumulated = 0.0
    for rank, p in probs.items():
        Accumulated += p
        if r < Accumulated:
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
    bot.loop.create_task(pvp_matchmaker())
    synced = await bot.tree.sync()
    print(f"🔄 Comandos sincronizados: {[cmd.name for cmd in synced]}")
    bot.add_view(CatalogView([]))

@bot.tree.command(name="start", description="Start your adventure!")
async def start(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    user_name = interaction.user.name

    if users.find_one({"discordID": user_id}):
        await interaction.response.send_message("You're already registered, genius.", ephemeral=True)
    else:
        users.insert_one({
            "discordID": user_id,
            "userName": user_name,
            "coins": 0,
            "clan": "None",
            "card_count": 0
        })
        await interaction.response.send_message("🎉 Your adventure has begun!", ephemeral=True)

@bot.tree.command(name="profile", description="Show your profile")
async def profile(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    user_data = users.find_one({"discordID": user_id})

    if not user_data:
        await interaction.response.send_message("❌ You are not registered. Use '/start' to begin.", ephemeral=True)
        return

    avatar_url = interaction.user.avatar.url if interaction.user.avatar else interaction.user.default_avatar.url
    embed = discord.Embed(
        title=f"{interaction.user.name}'s Profile",
        description="Here is your information:",
        color=discord.Color.blurple()
    )
    embed.set_thumbnail(url=avatar_url)
    embed.add_field(name="🆔 User's ID", value=user_data.get("discordID", "Stranger"), inline=False)
    embed.add_field(name="💰 Coins", value=user_data.get("coins", 0), inline=True)
    embed.add_field(name="🏠 Clan", value=user_data.get("clan", "none"), inline=True)

    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="reward", description="Claim your daily reward.")
async def reward(interaction: discord.Interaction):
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
            f"⏳ You must wait {h}h {m}m {s}s.", ephemeral=True
        )

    # monedas + DB se escribirán sólo tras el send
    coins = random.randint(200, 700)

    # elegir carta
    rank = choose_rank_threshold(DAILY_PROBS)
    pool = list(core_cards.find({"rank": rank}))
    card = random.choice(pool) if pool else None

    phrase = random.choice(PHRASES_DAILY)
    if card:
        # guardo carta en tu colección
        add_user_card(user_id, card)
        # genero embed usando carta["image"]
        embed = discord.Embed(
            color=color_by_rank(card["rank"]),
            description=f"**{card['name']}** • {card['class']} – {card['role']}"
        )
        embed.set_image(url=card.get("image", ""))
        await interaction.response.send_message(
            content=f"{phrase}\n🎁 +{coins} coins",
            embed=embed,
        )
    else:
        await interaction.response.send_message(
            f"⚠️ I couldn't find a card of rank '{rank}'. But you won +{coins} coins."
        )

    # Sólo si llegaste aquí sin excepciones, actualizo BD:
    users.update_one(
        {"discordID": user_id},
        {"$inc": {"coins": coins}, "$set": {"last_daily": now}},
        upsert=True
    )

@bot.tree.command(name="rewardcard", description="Claim your hourly reward.")
async def rewardcard(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    user = users.find_one({"discordID": user_id}) or {}
    now = datetime.utcnow()

    # 1) Chequear cooldown
    last = user.get("last_hourly")
    if last and (now - last) < HOURLY_CD:
        rem = HOURLY_CD - (now - last)
        minutes = int(rem.total_seconds() // 60)
        return await interaction.response.send_message(
            f"🕒 You must wait {minutes}m.",
            ephemeral=True
        )

    # 2) Selección de rango y carta
    rank = choose_rank_threshold(HOURLY_PROBS)
    pool = list(core_cards.find({"rank": rank}))
    card = random.choice(pool) if pool else None
    phrase = random.choice(PHRASES_HOURLY)

    # 3) Intentar enviar respuesta y, si falla, informar
    try:
        if card:
            # a) Guardar carta en user_cards + card_count
            add_user_card(user_id, card)

            # b) Crear embed usando carta["image"]
            embed = discord.Embed(
                title=card["name"],
                description=f"Rank: {card['rank']} • Class: {card['class']} • Role: {card['role']}",
                color=color_by_rank(card["rank"])
            )
            embed.set_image(url=card["image"])
            embed.set_footer(text=phrase)

            # c) Enviar
            await interaction.response.send_message(
                embed=embed
            )
        else:
            await interaction.response.send_message(
                f"⚠️ I couldn't find a card of rank '{rank}'.",
                ephemeral=True
            )
    except Exception as e:
        # Log en consola para debugging
        print(f"[ERROR] /rewardcard falló: {e}", flush=True)
        # Informar al usuario
        return await interaction.response.send_message(
            "❌ An error occurred while claiming your card. Please try again later.",
            ephemeral=True
        )

    # 4) Sólo si todo salió bien, actualizar cooldown
    users.update_one(
        {"discordID": user_id},
        {"$set": {"last_hourly": now}},
        upsert=True
    )
        
@bot.tree.command(name="balance", description="Check how many coins you have.")
async def balance(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    user_name = interaction.user.name
    avatar_url = interaction.user.avatar.url if interaction.user.avatar else interaction.user.default_avatar.url

    user_data = users.find_one({"discordID": user_id})

    if not user_data:
        await interaction.response.send_message("❌ You are not registered. Use '/start' to begin.", ephemeral=True)
        return

    coins = user_data.get("coins", 0)

    embed = discord.Embed(
        title=f"{user_name}'s balance",
        description=f"Currently, you have **{coins} coins**.",
        color=discord.Color.gold()
    )
    embed.set_thumbnail(url=avatar_url)
    embed.set_footer(text="Keep playing to earn more coins!")

    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="bet", description="Bet some coins and see if luck's on your side!")
@app_commands.describe(amount="Bet amount")
async def bet(interaction: discord.Interaction, amount: int):
    user_id = str(interaction.user.id)
    user_name = interaction.user.name
    avatar_url = interaction.user.avatar.url if interaction.user.avatar else interaction.user.default_avatar.url

    # Validar cantidad
    if amount <= 0:
        await interaction.response.send_message("❌ The amount must be greater than zero.", ephemeral=True)
        return

    user_data = users.find_one({"discordID": user_id})
    if not user_data:
        await interaction.response.send_message("❌ You are not registered. Use '/start' to begin.", ephemeral=True)
        return

    current_coins = user_data.get("coins", 0)
    if amount > current_coins:
        await interaction.response.send_message("❌ Hold up—you're out of coins for that one!", ephemeral=True)
        return

    # Generar resultado
    prob = random.random()
    if prob < 0.20:
        multiplier = 0    # pierde todo
        result = "❌ You lost everything."
    elif prob < 0.50:
        multiplier = 0.5  # pierde la mitad
        result = "⚠️ You lost half."
    elif prob < 0.80:
        multiplier = 1    # recupera
        result = "✅ You recovered your bet."
    elif prob < 0.95:
        multiplier = 2    # gana el doble
        result = "💰 You won double!"
    else:
        multiplier = 3    # gana el triple
        result = "🔥 A critical surge of luck! You've earned triple the reward!"

    gain = int(amount * multiplier)
    new_coins = current_coins - amount + gain

    users.update_one(
        {"discordID": user_id},
        {"$set": {"coins": new_coins}}
    )

    # Embed del resultado
    embed = discord.Embed(
        title="🎲 Bet result",
        description=f"{result}\n\n💸 You bet: **{amount} coins**\n💰 You won: **{gain} coins**",
        color=discord.Color.orange()
    )
    embed.set_thumbnail(url=avatar_url)
    embed.set_footer(text=f"{user_name}'s new balance: {new_coins} coins")

    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="give", description="Send coins to another player.")
@app_commands.describe(user="Player who will receive the coins", amount="Amount")
async def give(interaction: discord.Interaction, user: discord.User, amount: int):
    transmitter_id = str(interaction.user.id)
    receiver_id = str(user.id)
    transmitter_name = interaction.user.name
    avatar_url = interaction.user.avatar.url if interaction.user.avatar else interaction.user.default_avatar.url

    if amount <= 0:
        await interaction.response.send_message("❌ The amount must be greater than zero.", ephemeral=True)
        return

    if transmitter_id == receiver_id:
        await interaction.response.send_message("❌ You can't give coins to yourself, genius.", ephemeral=True)
        return

    # Verificar que ambos estén registrados
    transmitter = users.find_one({"discordID": transmitter_id})
    receiver = users.find_one({"discordID": receiver_id})

    if not transmitter:
        await interaction.response.send_message("❌ You are not registered. Use '/start' to begin.", ephemeral=True)
        return

    if not receiver:
        await interaction.response.send_message(f"❌ {user.name} is not registered..", ephemeral=True)
        return

    transmitter_holdings = transmitter.get("coins", 0)
    if transmitter_holdings < amount:
        await interaction.response.send_message("❌ You don't have enough coins to send that amount.", ephemeral=True)
        return

    # Transferencia
    new_transmitter = transmitter_holdings - amount
    new_receiver = receiver.get("coins", 0) + amount

    users.update_one({"discordID": transmitter_id}, {"$set": {"coins": new_transmitter}})
    users.update_one({"discordID": receiver_id}, {"$set": {"coins": new_receiver}})

    # Embed de confirmación
    embed = discord.Embed(
        title="💸 Transfer completed",
        description=(
            f"You sent **{amount} coins** to {user.mention}.\n"
            f"Your new balance is **{new_transmitter} coins**."
        ),
        color=discord.Color.green()
    )
    embed.set_thumbnail(url=avatar_url)
    embed.set_footer(text="Your generosity knows no bounds—thanks for sharing your riches! 💰")

    await interaction.response.send_message(embed=embed)

class CatalogView(ui.View):
    def __init__(self, cards, per_page: int = 10):
        super().__init__(timeout=None)
        self.cards = cards
        self.per_page = per_page
        self.current = 0

        self.select = ui.Select(placeholder="Select a card to view details.", options=[])
        self.select.callback = self.on_select
        self.add_item(self.select)

        self.prev_button = ui.Button(label="⬅️ Back", style=ButtonStyle.secondary)
        self.next_button = ui.Button(label="➡️ Next", style=ButtonStyle.secondary)
        self.prev_button.callback = self.on_prev
        self.next_button.callback = self.on_next
        self.add_item(self.prev_button)
        self.add_item(self.next_button)

        self.update_select_options()

    def update_select_options(self):
        start = self.current * self.per_page
        end = start + self.per_page
        page = self.cards[start:end]

        self.select.options.clear()
        for c in page:
            self.select.append_option(discord.SelectOption(label=f"{c['name']} [{c['rank']}]",value=c['id']))

        self.prev_button.disabled = self.current == 0
        max_page = (len(self.cards) - 1) // self.per_page
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
        card_id = self.select.values[0]
        card = next((c for c in self.cards if c['id'] == card_id), None)
        if card:
            embed = generate_card_embed(card, show_footer=False)
            await interaction.response.send_message(embed=embed)
        else:
            await interaction.response.send_message("❌ Card not found.", ephemeral=True)

    def get_embed(self):
        start = self.current * self.per_page
        end = start + self.per_page
        page = self.cards[start:end]

        embed = discord.Embed(
            title=f"📚 Catalog (Page {self.current+1}/{(len(self.cards)-1)//self.per_page+1})",
            color=discord.Color.blurple()
        )
        for c in page:
            embed.add_field(
                name=f"{c['name']} [{c['rank']}]",
                value=f"Class: {c['class']} • Role: {c['role']}",
                inline=False
            )
        return embed

@bot.tree.command(name="catalog", description="Show all available cards.")
async def catalog(interaction: discord.Interaction):
    all_cards = list(core_cards.find())
    if not all_cards:
        await interaction.response.send_message("❌ No cards found in the database.", ephemeral=True)
        return

    view = CatalogView(all_cards, per_page=10)
    await interaction.response.send_message(embed=view.get_embed(), view=view)

@bot.tree.command(name="collection", description="Show all your owned cards.")
async def collection(interaction: discord.Interaction):
    uid = str(interaction.user.id)
    user_doc = user_cards.find_one({"discordID": uid})
    cards = user_doc.get("cards", []) if user_doc else []

    if not cards:
        return await interaction.response.send_message(
            "❌ Your collection is empty.", ephemeral=True
        )

    class Paginator(ui.View):
        def __init__(self, cards, per_page: int = 10):
            super().__init__(timeout=None)
            self.cards = cards
            self.per_page = per_page
            self.page = 0

            # crear botones manualmente
            self.prev_button = ui.Button(label="⬅", style=discord.ButtonStyle.secondary)
            self.next_button = ui.Button(label="➡", style=discord.ButtonStyle.secondary)

            self.prev_button.callback = self.prev_page
            self.next_button.callback = self.next_page

            self.add_item(self.prev_button)
            self.add_item(self.next_button)

            self.update_buttons()

        def update_buttons(self):
            self.prev_button.disabled = self.page == 0
            self.next_button.disabled = (self.page + 1) * self.per_page >= len(self.cards)

        def get_embed(self):
            start = self.page * self.per_page
            end = start + self.per_page
            chunk = self.cards[start:end]

            embed = discord.Embed(
                title=f"📖 Colección ({self.page+1}/{(len(self.cards)-1)//self.per_page+1})",
                color=discord.Color.blue()
            )
            for c in chunk:
                embed.add_field(
                    name=f"{c.get('name','?')} [{c.get('rank','?')}]",
                    value=f"ID: {c.get('card_id','?')} | Role: {c.get('role','?')} | Class: {c.get('class','?')}",
                    inline=False
                )
            return embed

        async def prev_page(self, interaction: discord.Interaction):
            self.page -= 1
            self.update_buttons()
            await interaction.response.edit_message(embed=self.get_embed(), view=self)

        async def next_page(self, interaction: discord.Interaction):
            self.page += 1
            self.update_buttons()
            await interaction.response.edit_message(embed=self.get_embed(), view=self)

    view = Paginator(cards)
    await interaction.response.send_message(embed=view.get_embed(), view=view)

@bot.tree.command(name="searchcard", description="Search for a card by name, class, role, or rank.")
@app_commands.describe(name="Name (opcional)", class_="Class (opcional)", role="Role (opcional)", rank="Rank (opcional)")
async def searchcard(interaction: discord.Interaction, name: str = None, class_: str = None, role: str = None, rank: str = None):
    if not any([name, class_, role, rank]):
        await interaction.response.send_message("❗ At least one search parameter is required.", ephemeral=True)
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

    cards = list(core_cards.find(filtros))

    if not cards:
        await interaction.response.send_message("❌ No matching cards found.", ephemeral=True)
        return

    if len(cards) == 1:
        embed = generate_card_embed(cards[0], con_footer=False)
        await interaction.response.send_message(embed=embed)
    else:
        view = CatalogView(cards, per_page=10)
        await interaction.response.send_message(embed=view.get_embed(), view=view)

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
        label = f"Buy {pack['name']}"
        super().__init__(label=label, style=discord.ButtonStyle.green, custom_id=pack_id)

    async def callback(self, interaction: Interaction):
        user_id = str(interaction.user.id)
        # 1) Verifico usuario
        user = users.find_one({"discordID": user_id})
        if not user:
            return await interaction.response.send_message("❌ You are not registered. Use '/start' to begin.", ephemeral=True)

        # 2) Re-leo pack desde BD (por si cambió)
        pack = shop_packs.find_one({"id": self.pack_id})
        if not pack:
            return await interaction.response.send_message("❌ This pack is no longer available.", ephemeral=True)

        price = pack["price"]
        if user.get("coins", 0) < price:
            return await interaction.response.send_message("❌ You don't have enough coins.", ephemeral=True)

        # 3) Transacción atómica: resto monedas
        users.update_one(
            {"discordID": user_id},
            {"$inc": {"coins": -price}}
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
            f"📦 You have purchased a **{pack['name']}** for {price} coins.",
            ephemeral=True
        )

# —————————————————————————————
# Comando /shop corregido
# —————————————————————————————
@bot.tree.command(name="store", description="View and buy packs in the store.")
async def store(interaction: Interaction):
    user_id = str(interaction.user.id)

    # Validar registro y saldo
    user = users.find_one({"discordID": user_id})
    if not user:
        return await interaction.response.send_message("❌ You are not registered. Use '/start' to begin.", ephemeral=True)

    packs = list(shop_packs.find())
    if not packs:
        return await interaction.response.send_message("🛒 The store is out of stock.", ephemeral=True)

    # Construyo embed
    embed = Embed(
        title="🛍️ Packs Store",
        description=f"💰 Coins: **{user.get('coins', 0)}**",
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
    await interaction.response.send_message(embed=embed, view=view)

class OpenPackView(ui.View):
    def __init__(self, uid: str, packs: list[dict]):
        super().__init__(timeout=None)
        self.uid = uid
        for pack in packs:
            self.add_item(OpenPackButton(pack["id"], pack["count"], uid))

class OpenPackButton(ui.Button):
    def __init__(self, pack_id: str, count: int, user_id: str):
        pack = shop_packs.find_one({"id": pack_id})
        label = f"Open {pack['name']} ({count})"
        super().__init__(label=label, style=ButtonStyle.blurple, custom_id=f"open_{pack_id}")
        self.pack_id = pack_id
        self.user_id = user_id

    async def callback(self, interaction: Interaction):
        if str(interaction.user.id) != self.user_id:
            return await interaction.response.send_message("❌ This button isn't meant for you.", ephemeral=True)

        await interaction.response.defer()

        # 1. Restar un pack
        result = user_packs.update_one(
            {"discordID": self.user_id, "packs.id": self.pack_id, "packs.count": {"$gt": 0}},
            {"$inc": {"packs.$.count": -1}}
        )
        if result.modified_count == 0:
            return await interaction.followup.send("❌ You don't have that pack anymore.", ephemeral=True)

        # 2. Limpiar los que quedaron en 0
        user_packs.update_one(
            {"discordID": self.user_id},
            {"$pull": {"packs": {"id": self.pack_id, "count": 0}}}
        )

        # 3. Elegir carta y agregarla
        pack = shop_packs.find_one({"id": self.pack_id})
        rank = choose_rank_threshold(pack["rewards"])
        pool = list(core_cards.find({"rank": rank}))
        card = random.choice(pool)
        add_user_card(self.user_id, card)

        # Mostrar solo la imagen de la carta
        card_embed = Embed(
            title=f"{card['name']} [{card['rank']}]",
            description=f"{card['class']} • {card['role']}",
            color=color_by_rank(card["rank"])
        )
        card_embed.set_image(url=card.get("image", ""))
        card_embed.set_footer(text=f"🎁 You opened a {pack['name']}")


        # 4. Mostrar packs restantes
        doc = user_packs.find_one({"discordID": self.user_id})
        current_packs = doc.get("packs", [])
        desc = "\n".join(
            f"{shop_packs.find_one({'id': p['id']})['name']} ({p['count']})"
            for p in current_packs
        ) or "You have no packs."

        embed_list = Embed(
            title="📦 Available packs",
            description=desc,
            color=Color.purple()
        )

        await interaction.followup.send(
            content=f"{interaction.user.mention} opened a pack!",
            embeds=[embed_list, card_embed],
            view=OpenPackView(self.user_id, current_packs)
        )

@bot.tree.command(name="open", description="Open one of your stored packs.")
async def open(interaction: Interaction):
    uid = str(interaction.user.id)
    doc = user_packs.find_one({"discordID": uid})
    if not doc or not doc.get("packs"):
        return await interaction.response.send_message("❌ You don't have any stored packs.", ephemeral=True)

    desc = "\n".join(
        f"{shop_packs.find_one({'id': p['id']})['name']} ({p['count']})"
        for p in doc["packs"]
    )
    embed = Embed(
        title="🎁 Your Packs",
        description=desc,
        color=Color.purple()
    )
    view = OpenPackView(uid, doc["packs"])
    await interaction.response.send_message(embed=embed, view=view)

@bot.tree.command(name="sell", description="Sell a card from your collection.")
@app_commands.describe(card_id="The ID of the card you want to sell")
async def sell(interaction: discord.Interaction, card_id: int):
    uid = str(interaction.user.id)
    try:
        # 1. Validar que el usuario tenga cartas
        user_data = user_cards.find_one({"discordID": uid})
        if not user_data or not user_data.get("cards"):
            return await interaction.response.send_message("❌ You have no cards to sell.", ephemeral=True)

        # 2. Buscar la carta
        card = next((c for c in user_data["cards"] if c["card_id"] == card_id), None)
        if not card:
            return await interaction.response.send_message("❌ No card with that ID was found in your collection.", ephemeral=True)

        # 3. Verificar si la carta está en el equipo (lista de IDs)
        # Comprobar si la carta está en el equipo
        team_data = user_teams.find_one({"discordID": uid})
        if team_data and "team" in team_data:
            if str(card_id) in team_data["team"]:
                return await interaction.response.send_message(
                    "❌ This card is part of your team and cannot be sold.", ephemeral=True
                )


        # 4. Valor de venta
        rank = card.get("rank", "E")
        sell_value = RANK_VALUE.get(rank, 0)

        # 5. Eliminar la carta
        user_cards.update_one(
            {"discordID": uid},
            {"$pull": {"cards": {"card_id": card_id}}}
        )

        # 6. Sumar monedas
        users.update_one(
            {"discordID": uid},
            {"$inc": {"coins": sell_value}}
        )

        # 7. Confirmación
        embed = discord.Embed(
            title="🪙 Card Sold",
            description=(
                f"You successfully sold **{card['name']}** [`{rank}`]\n"
                f"You earned **{sell_value} coins**."
            ),
            color=discord.Color.green()
        )
        embed.set_footer(text="Thank you for your contribution to the market!")
        await interaction.response.send_message(embed=embed)

    except Exception as e:
        # Agrega logging si quieres
        logging.error(f"[ERROR] /sell failed: {e}\n{traceback.format_exc()}")
        await interaction.response.send_message(
            "❌ An internal error occurred while trying to sell your card. Please try again later.",
            ephemeral=True
        )
        
@bot.tree.command(name="formation", description="Choose your battle formation.")
@app_commands.describe(option="Choose your formation.")
@app_commands.choices(
    option=[
        app_commands.Choice(name="🛡️ Defensive — 2 frontlines, 1 midline, 1 backline", value="defensive"),
        app_commands.Choice(name="🔥 Offensive — 1 frontline, 2 midlines, 1 backline", value="offensive"),
        app_commands.Choice(name="🔄 Versatile — 1 forntline, 1 midline, 2 backlines", value="versatile"),
    ]
)
async def formation(interaction: discord.Interaction, option: app_commands.Choice[str]):
    uid = str(interaction.user.id)

    formations = {
        "defensive": {
            "slots": ["frontline", "frontline", "midline", "backline"],
            "desc": "🛡️ 2 defenders up front, perfect for holding the line."
        },
        "offensive": {
            "slots": ["frontline", "midline", "midline", "backline"],
            "desc": "🔥 Emphasizes offense, concentrating power through the middle."
        },
        "versatile": {
            "slots": ["frontline", "midline", "backline", "backline"],
            "desc": "🔄 Stable formation with a fortified rear."
        },
    }

    formation = formations[option.value]
    user_formations.update_one(
        {"discordID": uid},
        {"$set": {"formation": formation["slots"]}},
        upsert=True
    )

    await interaction.response.send_message(
        f"✅ You chose the **{option.name.split('—')[0].strip()}** formation\n{formation['desc']}"
    )

@bot.tree.command(name="assign", description="Assign a card to a slot in your formation.")
@app_commands.describe(
    slot="Slot number (1 to 4) based on your formation",
    id="Card ID"
)
async def assign(interaction: Interaction, slot: int, id: str):
    uid = str(interaction.user.id)
    # 1) Formación
    fdoc = user_formations.find_one({"discordID": uid})
    if not fdoc or "formation" not in fdoc:
        return await interaction.response.send_message(
            "❌ Start by selecting your formation using '/formacion'.", ephemeral=True
        )
    slots = fdoc["formation"]
    if slot < 1 or slot > len(slots):
        return await interaction.response.send_message(
            f"❌ That slot doesn't exist! Pick a number from 1 to {len(slots)}.", ephemeral=True
        )

    # 2) Comprueba que tienes esa carta
    udoc = user_cards.find_one({"discordID": uid})
    your_cards = {str(c["card_id"]): c for c in udoc.get("cards", [])} if udoc else {}
    if id not in your_cards:
        return await interaction.response.send_message(
            f"❌ The card wasn't found in your collection.", ephemeral=True
        )

    # 3) Recupera o crea tu team
    tdoc = user_teams.find_one({"discordID": uid})
    if not tdoc or "team" not in tdoc:
        team = [""] * len(slots)
    else:
        team = tdoc["team"]

    # 4) Asigna y guarda
    team[slot-1] = id
    user_teams.update_one(
        {"discordID": uid},
        {"$set": {"team": team}},
        upsert=True
    )

    await interaction.response.send_message(
        f"✅ Card successfully assigned to the slot. {slot} ({slots[slot-1].capitalize()})."
    )

@bot.tree.command(name="team", description="Show your formation and assigned cards.")
async def team(interaction: Interaction):
    uid = str(interaction.user.id)
    fdoc = user_formations.find_one({"discordID": uid})
    if not fdoc or "formation" not in fdoc:
        return await interaction.response.send_message(
            "❌ Start by selecting your formation using '/formacion'.", ephemeral=True
        )
    slots = fdoc["formation"]

    tdoc = user_teams.find_one({"discordID": uid})
    team = tdoc.get("team", [""] * len(slots)) if tdoc else [""] * len(slots)

    # Prepara texto
    lines = []
    # para buscar datos de las cartas
    udoc = user_cards.find_one({"discordID": uid}) or {}
    your_cards = {str(c["card_id"]): c for c in udoc.get("cards", [])}
    for idx, role in enumerate(slots, start=1):
        cid = team[idx-1]
        if cid and cid in your_cards:
            c = your_cards[cid]
            lines.append(
                f"{idx}. {role.capitalize()} — {c['name']} [{c['rank']}]"
            )
        else:
            lines.append(f"{idx}. {role.capitalize()} — *(vacío)*")

    embed = Embed(
        title="📋 Your current lineup",
        description="\n".join(lines),
        color=Color.blue()
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="swap", description="Swap the positions of two cards in your team.")
@app_commands.describe(
    slot1="First slot you want to swap",
    slot2="Second slot you want to swap"
)
async def swap(interaction: discord.Interaction, slot1: int, slot2: int):
    uid = str(interaction.user.id)

    # Verificamos formación activa
    fdoc = user_formations.find_one({"discordID": uid})
    if not fdoc or "formation" not in fdoc:
        return await interaction.response.send_message(
            "❌ Start by selecting your formation using '/formacion'.", ephemeral=True
        )
    slots = fdoc["formation"]

    # Validamos números
    if slot1 < 1 or slot1 > len(slots) or slot2 < 1 or slot2 > len(slots):
        return await interaction.response.send_message(
            f"❌ That slot doesn't exist! Pick a number from 1 to {len(slots)}.", ephemeral=True
        )

    if slot1 == slot2:
        return await interaction.response.send_message(
            "❌ You can't swap the same slot.", ephemeral=True
        )

    # Cargamos el equipo
    tdoc = user_teams.find_one({"discordID": uid})
    if not tdoc or "team" not in tdoc:
        return await interaction.response.send_message(
            "❌ No cards have been assigned yet.", ephemeral=True
        )

    team = tdoc["team"]

    # Intercambiamos
    team[slot1-1], team[slot2-1] = team[slot2-1], team[slot1-1]

    # Guardamos
    user_teams.update_one(
        {"discordID": uid},
        {"$set": {"team": team}}
    )

    await interaction.response.send_message(
        f"✅ Cards in slot {slot1} and slot {slot2} have been swapped."
    )

@bot.tree.command(name="clearteam", description="Remove all cards from your current team.")
async def clearteam(interaction: discord.Interaction):
    uid = str(interaction.user.id)

    # Verificamos si el usuario tiene formación
    fdoc = user_formations.find_one({"discordID": uid})
    if not fdoc or "formation" not in fdoc:
        return await interaction.response.send_message(
            "❌ Start by selecting your formation using '/formacion'.", ephemeral=True
        )
    slots = fdoc["formation"]

    # Creamos un equipo vacío del mismo tamaño
    empty_team = [""] * len(slots)

    user_teams.update_one(
        {"discordID": uid},
        {"$set": {"team": empty_team}},
        upsert=True
    )

    await interaction.response.send_message(
        "✅ Successfully removed all cards from your team."
    )

@bot.tree.command(name="remove", description="Remove a card from a specific slot in your team.")
@app_commands.describe(slot="Choose a slot number (1 to 4) to clear.")
async def remove(interaction: discord.Interaction, slot: int):
    uid = str(interaction.user.id)

    # 1) Formación
    fdoc = user_formations.find_one({"discordID": uid})
    if not fdoc or "formation" not in fdoc:
        return await interaction.response.send_message(
            "❌ Start by selecting your formation using '/formacion'.", ephemeral=True
        )
    slots = fdoc["formation"]
    if slot < 1 or slot > len(slots):
        return await interaction.response.send_message(
            f"❌ That slot doesn't exist! Pick a number from 1 to {len(slots)}.", ephemeral=True
        )

    # 2) Recupera el team
    tdoc = user_teams.find_one({"discordID": uid})
    if not tdoc or "team" not in tdoc:
        return await interaction.response.send_message(
            "❌ No cards have been assigned yet.", ephemeral=True
        )
    team = tdoc["team"]

    if team[slot-1] == "":
        return await interaction.response.send_message(
            f"❌ Slot {slot} is already empty.", ephemeral=True
        )

    # 3) Remover carta
    removed_card = team[slot-1]
    team[slot-1] = ""

    # 4) Guardar cambios
    user_teams.update_one(
        {"discordID": uid},
        {"$set": {"team": team}}
    )

    await interaction.response.send_message(
        f"✅ Card '{removed_card}' removed from slot {slot} ({slots[slot-1].capitalize()})."
    )

# /pvp command
# ---------- Combat Simulation ----------

def simulate_battle(e1, e2):
    """
    Simulate a combat between two teams e1 and e2.
    Returns (winner, log) where winner is "Team 1", "Team 2" or "Draw".
    """
    MAX_ROUNDS = 7
    log = []
    current_round = 1

    # Deep copy to avoid mutating original stats
    cards1 = [copy.deepcopy(c) for c in e1]
    cards2 = [copy.deepcopy(c) for c in e2]

    round_phrases = [
        "A new round of battles begins.",
        "The cards are preparing for another fierce battle.",
        "A new round begins: every move could be decisive."
    ]

    try:
        while current_round <= MAX_ROUNDS:
            log.append(f"⚔️ Round {current_round}: {random.choice(round_phrases)}")

            # Initiative pool
            pool = [(c, 1) for c in cards1 if c['hp'] > 0] + [(c, 2) for c in cards2 if c['hp'] > 0]
            pool.sort(key=lambda x: x[0]['vel'] + random.randint(0, 3), reverse=True)

            for card, team in pool:
                if card['hp'] <= 0:
                    continue

                allies = cards1 if team == 1 else cards2
                enemies = cards2 if team == 1 else cards1
                alive_enemies = [c for c in enemies if c['hp'] > 0]

                # Check victory
                if not alive_enemies:
                    winner = "Team 1" if team == 1 else "Team 2"
                    log.append(f"🏁 {card['name']} delivers the final blow!")
                    return winner, log

                target = min(alive_enemies, key=lambda x: x['hp'])
                role = card['role'].lower().strip()

                # Support roles
                if role == "healer":
                    injured = [a for a in allies if 0 < a['hp'] < a['max_hp'] and a is not card]
                    if injured:
                        a = random.choice(injured)
                        amt = int(a['max_hp'] * 0.2 + card['int'] * 0.1)
                        a['hp'] = min(a['hp'] + amt, a['max_hp'])
                        phrase = random.choice([
                            "{card} restored {a}'s vitality, healing +{amt}HP.",
                            "{card} cast a healing spell on {a}, restoring +{amt}HP.",
                            "{card} tended to {a}'s wounds, healing +{amt}HP."
                        ])
                        log.append(phrase.format(card=card['name'], a=a['name'], amt=amt))
                    else:
                        dmg = max(1, card['atk'] - int(target['def'] * 0.5))
                        target['hp'] -= dmg
                        phrase = random.choice([
                            "{card} had no one to heal, so attacked {target} instead (-{dmg}HP).",
                            "{card} swung their staff at {target} (-{dmg}HP).",
                            "{card} resorted to combat and hit {target} (-{dmg}HP)."
                        ])
                        log.append(phrase.format(card=card['name'], target=target['name'], dmg=dmg))
                    continue

                if role == "radiant healer":
                    injured = [a for a in allies if 0 < a['hp'] < a['max_hp'] and a is not card]
                    if injured:
                        a = random.choice(injured)
                        amt = int(a['max_hp'] * 0.4 + card['int'] * 0.2)
                        a['hp'] = min(a['hp'] + amt, a['max_hp'])
                        phrase = random.choice([
                            "{card} summoned radiant energy over {a}, healing +{amt}HP.",
                            "{card} bathed {a} in a wave of healing light (+{amt}HP).",
                            "{card} shone healing light upon {a}'s wounds, bringing recovery +{amt}HP."
                        ])
                        log.append(phrase.format(card=card['name'], a=a['name'], amt=amt))
                    else:
                        dmg = max(1, card['atk'] - int(target['def'] * 0.5))
                        target['hp'] -= dmg
                        phrase = random.choice([
                            "{card} emitted a flash of light and struck {target} (-{dmg}HP).",
                            "{card} lashed out with divine fury at {target} (-{dmg}HP).",
                            "{card} found no one to heal and attacked {target} instead (-{dmg}HP)."
                        ])
                        log.append(phrase.format(card=card['name'], target=target['name'], dmg=dmg))
                    continue

                # Aura buffs
                if role in ["aura", "aura sparkling", "noble aura"]:
                    buffed = False
                    for a in allies:
                        if a is card: continue
                        if role == "aura":
                            a['atk'] += 1
                        elif role == "aura sparkling":
                            a['atk'] += 2
                        elif role == "noble aura":
                            a['atk'] += 2
                            a['def'] += 2
                        buffed = True
                    if buffed:
                        phrase = random.choice([
                            "{card} inspired their team, boosting their strength.",
                            "{card} empowered their allies with radiant energy.",
                            "{card} radiated power and inspired the entire team."
                        ])
                        log.append(phrase.format(card=card['name']))
                    else:
                        dmg = max(1, card['atk'] - int(target['def'] * 0.5))
                        target['hp'] -= dmg
                        phrase = random.choice([
                            "{card} had no one to empower and attacked {target} instead (-{dmg}HP).",
                            "{card} surged forward and struck {target} (-{dmg}HP).",
                            "{card} unleashed their own power against {target} (-{dmg}HP)."
                        ])
                        log.append(phrase.format(card=card['name'], target=target['name'], dmg=dmg))
                    continue

                # Offensive / defensive roles
                if role == "tank":
                    dmg = max(1, card['atk'] - int(target['def'] * 0.5))
                    target['hp'] -= dmg
                    phrase = random.choice([
                        "{card} resisted the strike and counterattacked {target} (-{dmg}HP).",
                        "{card} absorbed the damage and struck back at {target} (-{dmg}HP).",
                        "{card} shielded the team while punishing {target} (-{dmg}HP)."
                    ])
                    log.append(phrase.format(card=card['name'], target=target['name'], dmg=dmg))
                    continue

                if role == "deflector":
                    base, resist = card['atk'], target['def']
                    dmg = int((base ** 1.1) / (resist * 0.5 + 2)) + random.randint(-1, 1)
                    dmg = max(1, dmg)
                    if random.random() < 0.2:
                        reflect = int(dmg * 0.5)
                        card['hp'] -= reflect
                        phrase = random.choice([
                            "{card} partially deflected the attack, taking {reflect} damage.",
                            "{card} channeled the impact back but took {reflect} damage.",
                            "{card} reflected part of the blow, but was not unscathed ({reflect}HP)."
                        ])
                        log.append(phrase.format(card=card['name'], reflect=reflect))
                    else:
                        target['hp'] -= dmg
                        phrase = random.choice([
                            "{card} countered with precision, striking {target} (-{dmg}HP).",
                            "{card} spun gracefully and struck {target} (-{dmg}HP).",
                            "{card} took advantage of {target}'s lapse, striking for (-{dmg}HP)."
                        ])
                        log.append(phrase.format(card=card['name'], target=target['name'], dmg=dmg))
                    continue

                if role == "slayer":
                    base, resist = card['atk'], target['def']
                    dmg = int((base ** 1.1) / (resist * 0.5 + 2)) + random.randint(-1, 1)
                    dmg = max(1, dmg)
                    target['hp'] -= dmg
                    phrase = random.choice([
                        "{card} delivered an unyielding blow to {target} (-{dmg}HP).",
                        "{card} ruthlessly charged against {target} (-{dmg}HP).",
                        "{card} dealt a decisive blow to {target} (-{dmg}HP)."
                    ])
                    log.append(phrase.format(card=card['name'], target=target['name'], dmg=dmg))
                    continue

                if role == "berserker":
                    base, resist = card['atk'], target['def']
                    dmg = int((base ** 1.1) / (resist * 0.5 + 2)) + random.randint(-1, 1)
                    dmg = max(1, int(dmg * 1.2))
                    target['hp'] -= dmg
                    phrase = random.choice([
                        "{card} went into a frenzy and shattered {target} (-{dmg}HP).",
                        "{card} roared and unleashed a devastating attack on {target} (-{dmg}HP).",
                        "{card} unleashed their full fury against {target} (-{dmg}HP)."
                    ])
                    log.append(phrase.format(card=card['name'], target=target['name'], dmg=dmg))
                    continue

                if role == "duelist":
                    base, resist = card['atk'], target['def']
                    dmg = int((base ** 1.1) / (resist * 0.5 + 2)) + random.randint(-1, 1)
                    snd = random.random() < 0.3
                    if snd:
                        dmg *= 2
                        phrase = random.choice([
                            "{card} found {target}'s weak spot and delivered a critical strike (-{dmg}HP)!",
                            "{card} exploited an opening for a lethal blow to {target} (-{dmg}HP)!",
                            "{card} caught {target} off guard with a masterful strike (-{dmg}HP)!"
                        ])
                    else:
                        phrase = random.choice([
                            "{card} faced off with {target} and delivered a precise strike (-{dmg}HP).",
                            "{card} engaged in a quick duel with {target} (-{dmg}HP).",
                            "{card} struck {target} with style and technique (-{dmg}HP)."
                        ])
                    target['hp'] -= max(1, dmg)
                    log.append(phrase.format(card=card['name'], target=target['name'], dmg=dmg))
                    continue

                if role == "avenger":
                    deads = sum(1 for a in allies if a['hp'] <= 0)
                    base = card['atk'] + deads * 2
                    resist = target['def']
                    dmg = int((base ** 1.1) / (resist * 0.5 + 2)) + random.randint(-1, 1)
                    dmg = max(1, dmg)
                    target['hp'] -= dmg
                    phrase = random.choice([
                        "{card} unleashed their pent-up rage upon {target} (-{dmg}HP).",
                        "{card} avenged their allies by striking {target} (-{dmg}HP).",
                        "{card} struck {target} in the name of the fallen (-{dmg}HP)."
                    ])
                    log.append(phrase.format(card=card['name'], target=target['name'], dmg=dmg))
                    continue

                if role == "foressor":
                    dodge_chance = 0.3 + card['int'] * 0.02
                    if random.random() < dodge_chance:
                        phrase = random.choice([
                            "{card} foresaw the attack and dodged it gracefully.",
                            "{card} glimpsed the future and avoided danger in time.",
                            "{card} anticipated {target}'s move and emerged unscathed."
                        ])
                        log.append(phrase.format(card=card['name'], target=target['name']))
                        continue
                    base, resist = card['atk'], target['def']
                    dmg = int((base ** 1.1) / (resist * 0.5 + 2)) + random.randint(-1, 1)
                    dmg = max(1, dmg)
                    target['hp'] -= dmg
                    phrase = random.choice([
                        "{card} struck {target} with wisdom (-{dmg}HP).",
                        "{card} used a vision to strike {target} (-{dmg}HP).",
                        "{card} foresaw {target}'s weak spot and struck (-{dmg}HP)."
                    ])
                    log.append(phrase.format(card=card['name'], target=target['name'], dmg=dmg))
                    continue

            current_round += 1

        # Draw by limit
        log.append("⏳ The battle ended in a draw due to time limit.")
        return "Draw", log

    except Exception as e:
        log.append(f"❌ Internal error during battle: {e}")
        return "Draw", log


# --- PvP Matching ---
async def pvp_matchmaker():
    await bot.wait_until_ready()
    while True:
        try:
            docs = list(pvp_queue.find().sort("createdAt", ASCENDING).limit(2))
            print(f"[MATCHMAKER] Queue length: {len(docs)}")

            if len(docs) == 2:
                # Saca los usuarios de la cola
                ids = [d["_id"] for d in docs]
                pvp_queue.delete_many({"_id": {"$in": ids}})
                print(f"[MATCHMAKER] Removed IDs from queue: {ids}")

                p1, p2 = docs
                uid1, uid2 = p1["user_id"], p2["user_id"]
                print(f"[MATCHMAKER] Matched {uid1} vs {uid2}")

                # Obtiene usuarios y canales
                user1 = await bot.fetch_user(int(uid1))
                user2 = await bot.fetch_user(int(uid2))
                chan1 = bot.get_channel(p1["channel_id"])
                chan2 = bot.get_channel(p2["channel_id"])
                msg1 = await chan1.fetch_message(p1["message_id"])
                msg2 = await chan2.fetch_message(p2["message_id"])

                header = f"⚔️ {user1.display_name} vs {user2.display_name}\n\n"
                await msg1.edit(content=header + "🕐 The duel begins!")
                await msg2.edit(content=header + "🕐 The duel begins!")

                # Obtiene equipos
                team1, err1 = get_user_team(uid1)
                team2, err2 = get_user_team(uid2)
                if err1 or err2:
                    error_msg = err1 or err2
                    print(f"[MATCHMAKER] Error getting teams: {error_msg}")
                    await msg1.edit(content=header + error_msg)
                    await msg2.edit(content=header + error_msg)
                    continue
                print(f"[MATCHMAKER] Team1: {team1}")
                print(f"[MATCHMAKER] Team2: {team2}")

                # Simula batalla
                winner, log = await asyncio.to_thread(simulate_battle, team1, team2)
                print(f"[MATCHMAKER] Winner: {winner}")

                for entry in log:
                    await asyncio.sleep(1)
                    await msg1.edit(content=header + entry)
                    await msg2.edit(content=header + entry)

                await asyncio.sleep(1)
                result = (
                    "🤝 The duel ended in a draw!"
                    if winner == "Draw" else
                    f"🏆 **{user1.display_name if winner == 'Team 1' else user2.display_name}** wins!"
                )
                await msg1.edit(content=header + result)
                await msg2.edit(content=header + result)

        except Exception as e:
            print(f"[PVP DEBUG][ERROR] {e}")
            traceback.print_exc()
            await asyncio.sleep(5)


@bot.tree.command(name="pvp", description="Queue PvP against another player")
async def pvp(interaction: discord.Interaction):
    uid = str(interaction.user.id)

    # 1) Verificar que el usuario tenga un equipo completo
    team, err = get_user_team(uid)
    if err:
        return await interaction.response.send_message(f"⚠️ {err}", ephemeral=True)

    # 2) Informar al usuario que ha entrado en cola
    await interaction.response.send_message(
        "🌀 Te has apuntado a la cola de PvP. ¡Esperando oponente...", 
        ephemeral=False
    )
    msg = await interaction.original_response()

    # 3) Insertar correctamente en la colección (sin doble insert)
    try:
        pvp_queue.insert_one({
            "_id": uid,                  # Usamos el UID como _id para prevenir duplicados
            "user_id": uid,
            "channel_id": msg.channel.id,
            "message_id": msg.id,
            "createdAt": datetime.utcnow()
        })
    except pymongo.errors.DuplicateKeyError:
        # Si ya estaba en cola, solo lo notificamos
        return await interaction.followup.send(
            "⚠️ Ya estás en la cola de PvP. Por favor espera a ser emparejado.",
            ephemeral=True
        )

    # (Opcional) Log para debugging
    print(f"[PVP] {uid} añadido a la cola")


# --- Battle Simulation ---
# --- Assemble user team ---
def get_user_team(uid: str):
    frm = user_formations.find_one({"discordID": uid})
    tdoc = user_teams.find_one({"discordID": uid})
    if not frm or not tdoc:
        return None, "❌ No team formed yet."
    raw = tdoc.get("team", [])
    if any(not cid for cid in raw):
        return None, "❗ Empty slot in your team."
    team = []
    for cid in raw:
        inst = user_cards.find_one({"discordID": uid, "cards.card_id": int(cid)}, {"cards.$":1})
        if not inst: continue
        core = core_cards.find_one({"id": inst['cards'][0]['core_id']})
        if not core: continue
        team.append({
            "name": core['name'],
            "role": core['role'].lower(),
            "atk": core['stats']['atk'],
            "def": core['stats']['def'],
            "vel": core['stats']['vel'],
            "int": core['stats']['int'],
            "hp": core['stats']['hp'],
            "max_hp": core['stats']['hp']
        })
    if not team:
        return None, "⚠️ Failed to assemble your team."
    return team, None

@bot.tree.command(name="duel", description="Start a duel against another player")
async def duel(interaction: discord.Interaction, opponent: discord.User):
    uid1, uid2 = str(interaction.user.id), str(opponent.id)
    if uid1 == uid2:
        return await interaction.response.send_message("❌ You can't duel yourself!", ephemeral=True)
    await interaction.response.defer(ephemeral=False)
    team1, err1 = get_user_team(uid1)
    if err1: return await interaction.followup.send(f"⚠️ {err1}", ephemeral=False)
    team2, err2 = get_user_team(uid2)
    if err2: return await interaction.followup.send(f"⚠️ {err2}", ephemeral=False)
    title = f"⚔️ **{interaction.user.display_name}** vs **{opponent.display_name}**\n\n"
    msg = await interaction.followup.send(title + "🏁 The duel begins!", ephemeral=False)
    winner, log = await asyncio.to_thread(simulate_battle, team1, team2)
    for entry in log:
        await asyncio.sleep(2)
        await msg.edit(content=title + entry)
    await asyncio.sleep(1)
    if winner=="Draw":
        result = "🤝 The duel ended in a draw!"
    else:
        champ = interaction.user.display_name if winner=="Team 1" else opponent.display_name
        result = f"🏆 **{champ}** wins the duel!"
    await msg.edit(content=title + result)

def run_bot():
    asyncio.run(bot.start(TOKEN))

threading.Thread(target=run_bot).start()

# === Ejecutar app Flask ===
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 8080)))