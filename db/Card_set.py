import pymongo
from database import db_connect

# 📦 Lista de 30 cartas distintas (rellená los campos)
cards = [
    {
        "id": "Z0001",
        "name": "Asia Argento",
        "class": "Beginbringer",
        "role": "Radiant Healer",
        "ability": "Benevolent Grace",
        "image": "https://i.imgur.com/Nthf6oF.png",
        "stats": {
            "atk": 13,
            "def": 14,
            "vel": 13,
            "hp": 15,
            "int": 13
        },
        "overall": 14,
        "rank": "Z"
    },
    {
        "id": "C0001",
        "name": "Asia Argento",
        "class": "Imouto",
        "role": "Aura",
        "image": "https://i.imgur.com/5DvoPHk.png",
        "stats": {
            "atk": 5,
            "def": 5,
            "vel": 5,
            "hp": 8,
            "int": 9
        },
        "overall": 6,
        "rank": "C"
    },
    {
        "id": "S0001",
        "name": "Irina Shidou",
        "class": "Imouto",
        "role": "Duelist",
        "image": "https://i.imgur.com/HJrvuQ3.png",
        "stats": {
            "atk": 15,
            "def": 11,
            "vel": 11,
            "hp": 10,
            "int": 8
        },
        "overall": 11,
        "rank": "S"
    },
    {
        "id": "A0001",
        "name": "Irina Shidou",
        "class": "Imouto",
        "role": "Berserker",
        "image": "https://i.imgur.com/VNLsOvj.png",
        "stats": {
            "atk": 15,
            "def": 4,
            "vel": 15,
            "hp": 7,
            "int": 7
        },
        "overall": 10,
        "rank": "A"
    },
    {
        "id": "B0001",
        "name": "Irina Shidou",
        "class": "Imoutou",
        "role": "Deflector",
        "image": "https://i.imgur.com/tnqIL1y.png",
        "stats": {
            "atk": 4,
            "def": 10,
            "vel": 5,
            "hp": 8,
            "int": 7
        },
        "overall": 7,
        "rank": "B"
    },
    {
        "id": "A0002",
        "name": "Grayfia Lucifuge",
        "class": "Mommy",
        "role": "Tank",
        "image": "https://i.imgur.com/NuRU8nf.png",
        "stats": {
            "atk": 5,
            "def": 15,
            "vel": 3,
            "hp": 15,
            "int": 8
        },
        "overall": 9,
        "rank": "A"
    },
    {
        "id": "C0002",
        "name": "Rias Gremory",
        "class": "Onee-San",
        "role": "Deflector",
        "image": "https://i.imgur.com/jKSieeK.png",
        "stats": {
            "atk": 8,
            "def": 5,
            "vel": 4,
            "hp": 9,
            "int": 4
        },
        "overall": 6,
        "rank": "C"
    },
    {
        "id": "A0003",
        "name": "Rias Gremory",
        "class": "Onee-San",
        "role": "Slayer",
        "image": "https://i.imgur.com/c1nVDwn.png",
        "stats": {
            "atk": 10,
            "def": 8,
            "vel": 14,
            "hp": 9,
            "int": 10
        },
        "overall": 10,
        "rank": "A"
    },
    {
        "id": "C0003",
        "name": "Irina Shidou",
        "class": "Imouto",
        "role": "Avenger",
        "image": "https://i.imgur.com/RFF3yoJ.png",
        "stats": {
            "atk": 8,
            "def": 5,
            "vel": 4,
            "hp": 5,
            "int": 3
        },
        "overall": 5,
        "rank": "C"
    },
    {
        "id": "B0002",
        "name": "Asia Argento",
        "class": "Imouto",
        "role": "Berserker",
        "image": "https://i.imgur.com/dYd8Nl8.png",
        "stats": {
            "atk": 14,
            "def": 5,
            "vel": 9,
            "hp": 10,
            "int": 3
        },
        "overall": 8,
        "rank": "B"
    },
    {
        "id": "B0003",
        "name": "Akeno Himejima",
        "class": "Onee-San",
        "role": "Duelist",
        "image": "https://i.imgur.com/aMfleSN.png",
        "stats": {
            "atk": 9,
            "def": 7,
            "vel": 6,
            "hp": 9,
            "int": 8
        },
        "overall": 8,
        "rank": "B"
    },
    {
       "id": "B0004",
        "name": "Akeno Himejima",
        "class": "Onee-San",
        "role": "Duelist",
        "image": "https://i.imgur.com/C6tMunG.png",
        "stats": {
            "atk": 10,
            "def": 8,
            "vel": 9,
            "hp": 7,
            "int": 8
        },
        "overall": 8,
        "rank": "B"
    },
    {
        "id": "C0004",
        "name": "Yuuma Amano",
        "class": "Onee-San",
        "role": "Tank",
        "image": "https://i.imgur.com/m10Jf6K.png",
        "stats": {
            "atk": 3,
            "def": 9,
            "vel": 5,
            "hp": 10,
            "int": 4
        },
        "overall": 6,
        "rank": "C"
    },
    {
        "id": "S0002",
        "name": "Rias Gremory",
        "class": "Onee-San",
        "role": "Berserker",
        "image": "https://i.imgur.com/q7yB634.png",
        "stats": {
            "atk": 15,
            "def": 8,
            "vel": 14,
            "hp": 12,
            "int": 7
        },
        "overall": 11,
        "rank": "S"
    },
    {
        "id": "S0003",
        "name": "Xenovia Quarto",
        "class": "Baddie",
        "role": "Berserker",
        "image": "https://i.imgur.com/T1drEJ1.png",
        "stats": {
            "atk": 15,
            "def": 8,
            "vel": 14,
            "hp": 14,
            "int": 6
        },
        "overall": 11,
        "rank": "S"
    },
    {
        "id": "A0004",
        "name": "Rias Gremory",
        "class": "Onee-San",
        "role": "Healer",
        "image": "https://i.imgur.com/8zE1s7J.png",
        "stats": {
            "atk": 7,
            "def": 13,
            "vel": 8,
            "hp": 15,
            "int": 7
        },
        "overall": 10,
        "rank": "A"
    },
    {
        "id": "C0005",
        "name": "Akeno Himejima",
        "class": "Onee-San",
        "role": "Tank",
        "image": "https://i.imgur.com/jWsGdHa.png",
        "stats": {
            "atk": 4,
            "def": 7,
            "vel": 3,
            "hp": 7,
            "int": 8
        },
        "overall": 6,
        "rank": "C"
    },
    {
        "id": "A0005",
        "name": "Rossweisse",
        "class": "Milf",
        "role": "Duelist",
        "image": "https://i.imgur.com/NdflAYY.png",
        "stats": {
            "atk": 9,
            "def": 10,
            "vel": 8,
            "hp": 12,
            "int": 8
        },
        "overall": 9,
        "rank": "A"
    },
    {
        "id": "A0006",
        "name": "Ravel Phoenix",
        "class": "Tsundere",
        "role": "Duelist",
        "image": "https://i.imgur.com/I5eGWRZ.png",
        "stats": {
            "atk": 9,
            "def": 10,
            "vel": 8,
            "hp": 12,
            "int": 8
        },
        "overall": 9,
        "rank": "A"
    },
    {
        "id": "B0005",
        "name": "Ravel Phoenixx",
        "class": "Tsundere",
        "role": "Healer",
        "image": "https://i.imgur.com/h22AFEF.png",
        "stats": {
            "atk": 3,
            "def": 10,
            "vel": 5,
            "hp": 12,
            "int": 6
        },
        "overall": 7,
        "rank": "B"
    },
    {
        "id": "A0007",
        "name": "Yasaka",
        "class": "Milf",
        "role": "Tank",
        "image": "https://i.imgur.com/SPkhwbU.png",
        "stats": {
            "atk": 5,
            "def": 13,
            "vel": 7,
            "hp": 12,
            "int": 7
        },
        "overall": 9,
        "rank": "A"
    },
    {
        "id": "A0008",
        "name": "Serafall Leviathan",
        "class": "Imouto",
        "role": "Deflector",
        "image": "https://i.imgur.com/bjnxEMI.png",
        "stats": {
            "atk": 6,
            "def": 14,
            "vel": 7,
            "hp": 15,
            "int": 7
        },
        "overall": 10,
        "rank": "A"
    },
    {
        "id": "S0004",
        "name": "Tsunade Senju",
        "class": "Mommy",
        "role": "Healer",
        "image": "https://i.imgur.com/psKl7Jz.png",
        "stats": {
            "atk": 9,
            "def": 15,
            "vel": 10,
            "hp": 15,
            "int": 13
        },
        "overall": 12,
        "rank": "S"
    },
    {
        "id": "A0009",
        "name": "Tsunade Senju",
        "class": "Mommy",
        "role": "Tank",
        "image": "https://i.imgur.com/p30vafK.png",
        "stats": {
            "atk": 5,
            "def": 15,
            "vel": 7,
            "hp": 15,
            "int": 8
        },
        "overall": 10,
        "rank": "A"
    },
    {
        "id": "A0010",
        "name": "Tsunade Senju",
        "class": "Mommy",
        "role": "Berserker",
        "image": "https://i.imgur.com/Pc4QYJv.png",
        "stats": {
            "atk": 13,
            "def": 5,
            "vel": 10,
            "hp": 10,
            "int": 8
        },
        "overall": 9,
        "rank": "A"
    },
    {
        "id": "C0006",
        "name": "Xenovia Quarta",
        "class": "Baddie",
        "role": "Aura",
        "image": "https://i.imgur.com/ImW0ZpI.png",
        "stats": {
            "atk": 7,
            "def": 5,
            "vel": 6,
            "hp": 7,
            "int": 5
        },
        "overall": 6,
        "rank": "C"
    },
    {
        "id": "C0007",
        "name": "Raynare",
        "class": "Baddie",
        "role": "Aura",
        "image": "https://i.imgur.com/42WDygQ.png",
        "stats": {
            "atk": 7,
            "def": 5,
            "vel": 6,
            "hp": 7,
            "int": 5
        },
        "overall": 6,
        "rank": "C"
    },
    {
        "id": "A0011",
        "name": "Seekvaira Agares",
        "class": "Onee-San",
        "role": "Foreseer",
        "image": "https://i.imgur.com/d0EF9Kt.png",
        "stats": {
            "atk": 7,
            "def": 5,
            "vel": 7,
            "hp": 10,
            "int": 15
        },
        "overall": 9,
        "rank": "A"
    },
    {
        "id": "B0006",
        "name": "Raynare",
        "class": "Baddie",
        "role": "Deflector",
        "image": "https://i.imgur.com/KA2WdLH.png",
        "stats": {
            "atk": 7,
            "def": 11,
            "vel": 6,
            "hp": 9,
            "int": 5
        },
        "overall": 8,
        "rank": "B"
    },
    {
        "id": "Z0002",
        "name": "Le Fay",
        "class": "Endbringer",
        "role": "Noble Aura",
        "image": "https://i.imgur.com/iZtAbkP.png",
        "stats": {
            "atk": 15,
            "def": 13,
            "vel": 14,
            "hp": 13,
            "int": 13
        },
        "overall": 14,
        "rank": "Z"
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

