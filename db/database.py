import pymongo

# Usar la URI directamente aquí
db_uri = "mongodb+srv://TCG:ixR4AINjmD8HlCQa@cluster0.mriaxlf.mongodb.net/"  # Directamente aquí

def db_connect():
    try:
        connection = pymongo.MongoClient(db_uri)
        # Intentar hacer una consulta simple para verificar la conexión
        connection.admin.command('ping')
        print("✅ Conexión a MongoDB exitosa!")
        return connection
    except pymongo.errors.ConnectionError as e:
        print(f"❌ Error de conexión: {e}")
    except Exception as e:
        print(f"❌ Error desconocido: {e}")
    return None

def register(conn, ctx):
    print(f"✅ Registro iniciado para {ctx.author.id} ({ctx.author.name})")
    database = conn["discord_server"]
    collection = database["users"]
    
    # Crear un documento con el discordID y el userName
    doc = {"discordID": str(ctx.author.id), "userName": str(ctx.author.name)}
    
    # Insertar el documento en la colección
    collection.insert_one(doc)
    print(f"✅ {ctx.author.name} registrado correctamente.")

def verify_id(conn, discord_id):
    print(f"✅ Verificando si el ID {discord_id} existe en la base de datos.")
    database = conn["discord_server"]
    collection = database["users"]
    
    # Buscar un documento con el discordID
    doc = collection.find_one({"discordID": discord_id})
    if doc:
        print(f"✅ ID {discord_id} encontrado.")
        return True
    else:
        print(f"❌ ID {discord_id} no encontrado.")
        return False

