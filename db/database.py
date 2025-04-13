import pymongo

# URI de conexión directa
MONGO_URI = "mongodb+srv://TCG:ixR4AINjmD8HlCQa@cluster0.mriaxlf.mongodb.net/"

def db_connect():
    """Establece la conexión con la base de datos MongoDB."""
    try:
        client = pymongo.MongoClient(MONGO_URI)
        db = client["discord_server"]
        print("✅ Conexión exitosa a MongoDB Atlas.")
        return db["users"]
    except Exception as e:
        print(f"❌ Error al conectar con MongoDB: {e}")
        return None

def verify_user(users, discord_id):
    """Verifica si un usuario existe por su ID de Discord."""
    return users.find_one({"discordID": str(discord_id)}) is not None

def register_user(users, discord_id, user_name):
    """Registra un nuevo usuario con datos iniciales."""
    users.insert_one({
        "discordID": str(discord_id),
        "userName": str(user_name),
        "monedas": 0,
        "clase": "Sin clase",
        "nivel": 1,
        "clan": "Sin clan",
        "poder_total": 0
    })

def update_user(users, discord_id, field, value):
    """Actualiza un campo específico del usuario."""
    users.update_one({"discordID": str(discord_id)}, {"$set": {field: value}})