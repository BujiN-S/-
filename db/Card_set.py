import pymongo
from database import db_connect

# 📦 Lista de 30 cartas distintas (rellená los campos)
cards = [
    {
        "id": "D0001",
        "name": "Elizabeth",
        "class": "Baddie",
        "role": "Slayer",
        "image": "https://i.imgur.com/LwnNg6g.png",
        "stats": {
            "atk": 3,
            "def": 4,
            "vel": 5,
            "hp": 3,
            "int": 5
        },
        "overall": 4,
        "rank": "D"
    },
    {
        "id": "D0002",
        "name": "Orihime Inoue",
        "class": "Baddie",
        "role": "Aura",
        "image": "https://i.imgur.com/v5XV7wZ.png",
        "stats": {
            "atk": 3,
            "def": 4,
            "vel": 4,
            "hp": 3,
            "int": 5
        },
        "overall": 4,
        "rank": "D"
    },
    {
        "id": "E0001",
        "name": "Mitsuri Kanroji",
        "class": "Baddie",
        "role": "Avenger",
        "image": "https://i.imgur.com/aDQ7wbf.png",
        "stats": {
            "atk": 2,
            "def": 1,
            "vel": 2,
            "hp": 1,
            "int": 2
        },
        "overall": 2,
        "rank": "E"
    },
    {
        "id": "E0002",
        "name": "Elizabeth",
        "class": "Baddie",
        "role": "Foresser",
        "image": "https://i.imgur.com/XoYnRNc.png",
        "stats": {
            "atk": 3,
            "def": 4,
            "vel": 5,
            "hp": 3,
            "int": 5
        },
        "overall": 2,
        "rank": "E"
    },
    {
        "id": "D0003",
        "name": "Momo Yaoyorozu",
        "class": "Baddie",
        "role": "Tank",
        "image": "https://i.imgur.com/cuLO953.png",
        "stats": {
            "atk": 3,
            "def": 5,
            "vel": 3,
            "hp": 5,
            "int": 4
        },
        "overall": 4,
        "rank": "D"
    },
    {
        "id": "D0004",
        "name": "Hinata Hyuuga",
        "class": "Baddie",
        "role": "Berserker",
        "image": "https://i.imgur.com/hWGqbXp.png",
        "stats": {
            "atk": 5,
            "def": 4,
            "vel": 3,
            "hp": 5,
            "int": 3
        },
        "overall": 4,
        "rank": "D"
    },
    {
        "id": "E0003",
        "name": "Asuna Yuuki",
        "class": "Senpai",
        "role": "Slayer",
        "image": "https://i.imgur.com/xMIMI5D.png",
        "stats": {
            "atk": 3,
            "def": 2,
            "vel": 3,
            "hp": 2,
            "int": 1
        },
        "overall": 2,
        "rank": "E"
    },
    {
        "id": "E0004",
        "name": "Nami",
        "class": "Baddie",
        "role": "Duelist",
        "image": "https://i.imgur.com/38L7OKa.png",
        "stats": {
            "atk": 3,
            "def": 2,
            "vel": 3,
            "hp": 1,
            "int": 1
        },
        "overall": 2,
        "rank": "E"
    },
    {
        "id": "E0005",
        "name": "Nico Robin",
        "class": "Baddie",
        "role": "Foresser",
        "image": "https://i.imgur.com/xqigkj1.png",
        "stats": {
            "atk": 1,
            "def": 2,
            "vel": 3,
            "hp": 1,
            "int": 3
        },
        "overall": 2,
        "rank": "E"
    },
    {
        "id": "S0005",
        "name": "Ochako Uraraka",
        "class": "Kouhai Sparkle",
        "role": "Aura Sparkling",
        "image": "https://i.imgur.com/raweJUE.png",
        "stats": {
            "atk": 7,
            "def": 11,
            "vel": 12,
            "hp": 8,
            "int": 15
        },
        "overall": 11,
        "rank": "S"
    },
]

db = db_connect()
if db:
    core_cards = db["cards"]

    for card in cards:
        if not core_cards.find_one({"id": card["id"]}):
            core_cards.insert_one(card)
            print(f"✅ Insertada: {card['id']}")
        else:
            print(f"⚠️ Ya existe: {card['id']}")

