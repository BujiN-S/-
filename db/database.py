import pymongo

# URI de conexión directa
db_uri = "mongodb+srv://TCG:ixR4AINjmD8HlCQa@cluster0.mriaxlf.mongodb.net/"

def db_connect():
    """Establece la conexión con la base de datos MongoDB."""
    try:
        client = pymongo.MongoClient(db_uri)
        print("✅ Conexión exitosa a MongoDB Atlas.")
        return client
    except Exception as e:
        print(f"❌ Error al conectar con MongoDB: {e}")
        return None

def register_user(conn, discord_id, discord_name):
    """Registra un usuario en la base de datos con datos iniciales."""
    try:
        db = conn["discord_server"]
        col = db["users"]
        doc = {
            "discordID": str(discord_id),
            "userName": str(discord_name),
            "monedas": 0,
            "clase": "Sin clase",
            "nivel": 1,
            "clan": "Sin clan",
            "poder_total": 0
        }
        result = col.insert_one(doc)
        print(f"✅ Usuario {discord_name} registrado con ID: {result.inserted_id}")
    except Exception as e:
        print(f"❌ ERROR al insertar usuario en MongoDB: {e}")

def verify_id(conn, discord_id):
    """Verifica si el usuario ya está registrado en la base de datos."""
    try:
        db = conn["discord_server"]
        col = db["users"]
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

def update_user_data(conn, discord_id, field, value):
    """Actualiza los datos de un usuario en la base de datos."""
    try:
        db = conn["discord_server"]
        col = db["users"]
        update = {"$set": {field: value}}
        result = col.update_one({"discordID": str(discord_id)}, update)
        if result.modified_count > 0:
            print(f"✅ {field} actualizado exitosamente para el usuario {discord_id}.")
        else:
            print(f"❌ No se pudo actualizar {field} para el usuario {discord_id}.")
    except Exception as e:
        print(f"❌ Error al actualizar datos del usuario: {e}")