import pymongo
from database import db_connect

# 🛍️ Packs disponibles permanentemente en la tienda
packs = [
    {
        "id": "starter",
        "name": "Starter Pack",
        "description": "Perfecto para comenzar tu colección.",
        "price": 500,
        "cards_per_open": 1,
        "rewards": {
            "Z": 0.0005,
            "S": 0.005,
            "A": 0.02,
            "B": 0.10,
            "C": 0.20,
            "D": 0.30,
            "E": 0.3745
        }
    },
    {
        "id": "advanced",
        "name": "Advanced Pack",
        "description": "Mayor riesgo, mayor recompensa.",
        "price": 3000,
        "cards_per_open": 1,
        "rewards": {
            "Z": 0.005,
            "S": 0.02,
            "A": 0.07,
            "B": 0.18,
            "C": 0.22,
            "D": 0.23,
            "E": 0.275
        }
    },
    {
        "id": "rankup",
        "name": "RankUp Pack",
        "description": "Sube de nivel con cartas de alto rango.",
        "price": 7500,
        "cards_per_open": 1,
        "rewards": {
            "Z": 0.015,
            "S": 0.045,
            "A": 0.20,
            "B": 0.25,
            "C": 0.25,
            "D": 0.10,
            "E": 0.14
        }
    },
    {
        "id": "luxury",
        "name": "Luxury Pack",
        "description": "Una experiencia exclusiva para los más poderosos.",
        "price": 16500,
        "cards_per_open": 1,
        "rewards": {
            "Z": 0.04,
            "S": 0.10,
            "A": 0.20,
            "B": 0.25,
            "C": 0.20,
            "D": 0.10,
            "E": 0.11
        }
    }
]

db = db_connect()
if db:
    shop_packs = db["shop_packs"]

    for pack in packs:
        if not shop_packs.find_one({"id": pack["id"]}):
            shop_packs.insert_one(pack)
            print(f"✅ Pack insertado: {pack['id']}")
        else:
            print(f"⚠️ El pack ya existe: {pack['id']}")
