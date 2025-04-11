import asyncio
import discord
from discord.ext import commands
import pymongo
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
from flask import Flask
from threading import Thread

# === FLASK KEEP ALIVE ===
app = Flask('')

@app.route('/')
def home():
    return "El bot está vivo 🟢"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()

# === CONFIG ===
TOKEN = "MTM1MjQ5NTYxMjgxMzI1MDY0MA.G3LmNo.Y1xgmu5UznG3yitpLk8MOmRsHEpcLCliAkGN0k"  # Reemplaza con tu token de Discord
APP_ID = 1352495612813250640  # Reemplaza con tu ID de aplicación de Discord

# === MONGO ===
db_uri = "mongodb+srv://TCG:ixR4AINjmD8HlCQa@cluster0.mriaxlf.mongodb.net/"

def db_connect():
    """Establece la conexión con la base de datos MongoDB."""
    try:
        # Intentar la conexión
        client = pymongo.MongoClient(db_uri)
        print("✅ Conexión exitosa a MongoDB Atlas.")
        return client
    except ConnectionError as e:
        print(f"❌ Error de conexión a MongoDB: {e}")
        return None
    except Exception as e:
        print(f"❌ Error desconocido: {e}")
        return None

def register_user(conn, discord_id, discord_name):
    """Registra un usuario en la base de datos."""
    try:
        db = conn["discord_server"]
        col = db["users"]
        doc = {"discordID": str(discord_id), "userName": str(discord_name)}
        
        # Insertar el documento
        result = col.insert_one(doc)
        print(f"✅ Usuario {discord_name} registrado con ID: {result.inserted_id}")
    except Exception as e:
        print(f"❌ ERROR al insertar usuario en MongoDB: {e}")

def verify_id(conn, discord_id):
    """Verifica si el usuario ya está registrado en la base de datos."""
    try:
        db = conn["discord_server"]
        col = db["users"]
        
        # Buscar el usuario por su discordID
        user = col.find_one({"discordID": str(discord_id)})
        
        if user:
            print(f"✅ El usuario con ID {discord_id} ya existe.")
            return True
        else:
            print(f"❌ El usuario con ID {discord_id} no existe.")
            return False
    except Exception as e:
        print(f"❌ Error al verificar el ID: {e}")
        return False


# === CONEXIÓN A LA BASE DE DATOS ===
conn = db_connect()
if not conn:
    exit()  # Si no se puede conectar, se termina la ejecución

# === DISCORD BOT ===
intents = discord.Intents.all()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents, application_id=APP_ID)

# === COMANDO START ===
@bot.tree.command(name="start", description="Start your adventure!")
async def start(interaction: discord.Interaction):
    print(f"🟡 /start ejecutado por {interaction.user.name} ({interaction.user.id})")
    user_id = str(interaction.user.id)
    
    if verify_id(conn, user_id):
        print("🟢 Usuario ya registrado.")
        await interaction.response.send_message("Ya estás registrado.", ephemeral=True)
    else:
        print("🔵 Usuario nuevo. Registrando...")
        register_user(conn, user_id, interaction.user.name)
        await interaction.response.send_message("¡Bienvenido al juego! 🎮", ephemeral=True)

# === READY EVENT ===
@bot.event
async def on_ready():
    print(f"✅ Bot conectado como {bot.user}")
    await bot.tree.sync()

# === EJECUTAR BOT ===
async def main():
    async with bot:
        await bot.start(TOKEN)

keep_alive()
asyncio.run(main())
