import pymongo

MONGO_URI = "mongodb+srv://TCG:ixR4AINjmD8HlCQa@cluster0.mriaxlf.mongodb.net/"

def db_connect():
    try:
        client = pymongo.MongoClient(MONGO_URI)
        db = client["discord_server"]
        print("✅ Conexión exitosa a MongoDB Atlas.")
        return {
            "users": db["users"],
            "core_cards": db["core_cards"],
            "user_cards": db["user_cards"],
            "shop_packs": db["shop_packs"],
            "user_packs": db["user_packs"]
        }
    except Exception as e:
        print(f"❌ Error al conectar con MongoDB: {e}")
        return None

# Tus funciones para usuarios siguen igual
def verify_user(users, discord_id):
    return users.find_one({"discordID": str(discord_id)}) is not None

def register_user(users, discord_id, user_name):
    users.insert_one({
        "discordID": str(discord_id),
        "userName": str(user_name),
        "monedas": 0,
        "clan": "Sin clan",
        "poder_total": 0,
        "card_count": 0
    })

def update_user(users, discord_id, field, value):
    users.update_one({"discordID": str(discord_id)}, {"$set": {field: value}})