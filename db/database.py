import pymongo
from pymongo.errors import ConnectionError

# URI de conexión directa
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
