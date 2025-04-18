import pymongo
from db.database import db_connect

# 📦 Lista de 30 cartas distintas (rellená los campos)
cards = [
    {
        "id": "Z0001",
        "name": "Asia Argento",
        "rank": "Z",
        "class": "Beginbringer",
        "role": "Radiant Healer",
        "ability": "Benevolent Grace",
        "image": "https://i.imgur.com/Nthf6oF.png"
    },
    {
        "id": "C0001",
        "name": "Asia Argento",
        "rank": "C",
        "class": "Imouto",
        "role": "Aura",
        "image": "https://i.imgur.com/5DvoPHk.png"
    },
    {
        "id": "S0001",
        "name": "Irina Shidou",
        "rank": "S",
        "class": "Imouto",
        "role": "Duelist",
        "image": "https://i.imgur.com/HJrvuQ3.png"
    },
    {
        "id": "A0001",
        "name": "Irina Shidou",
        "rank": "A",
        "class": "Imouto",
        "role": "Berserker",
        "image": "https://i.imgur.com/VNLsOvj.png"
    },
    {
        "id": "B0001",
        "name": "Irina Shidou",
        "rank": "B",
        "class": "Imoutou",
        "role": "Deflector",
        "image": "https://i.imgur.com/tnqIL1y.png"
    },
    {
        "id": "A0002",
        "name": "Grayfia Lucifuge",
        "rank": "A",
        "class": "Mommy",
        "role": "Tank",
        "image": "https://i.imgur.com/NuRU8nf.png"
    },
    {
        "id": "C0002",
        "name": "Rias Gremory",
        "rank": "C",
        "class": "Onee-San",
        "role": "Deflector",
        "image": "https://i.imgur.com/jKSieeK.png"
    },
    {
        "id": "A0003",
        "name": "Rias Gremory",
        "rank": "A",
        "class": "Onee-San",
        "role": "Slayer",
        "image": "https://i.imgur.com/c1nVDwn.png"
    },
    {
        "id": "C0003",
        "name": "Irina Shidou",
        "rank": "C",
        "class": "Imouto",
        "role": "Avenger",
        "imagen": "https://i.imgur.com/RFF3yoJ.png"
    },
    {
        "id": "B0002",
        "name": "Asia Argento",
        "rank": "B",
        "class": "Imouto",
        "role": "Berserker",
        "image": "https://i.imgur.com/dYd8Nl8.png"
    },
    {
        "id": "B0003",
        "name": "Akeno Himejima",
        "rank": "B",
        "class": "Onee-San",
        "role": "Duelist",
        "image": "https://i.imgur.com/aMfleSN.png"
    },
    {
       "id": "B0004",
        "name": "Akeno Himejima",
        "rank": "B",
        "class": "Onee-San",
        "role": "Duelist",
        "image": "https://i.imgur.com/C6tMunG.png"
    },
    {
        "id": "C0004",
        "name": "Yuuma Amano",
        "rank": "C",
        "class": "Onee-San",
        "role": "Tank",
        "image": "https://i.imgur.com/m10Jf6K.png"
    },
    {
        "id": "S0002",
        "name": "Rias Gremory",
        "rank": "S",
        "class": "Onee-San",
        "role": "Berserker",
        "image": "https://i.imgur.com/q7yB634.png"
    },
    {
        "id": "S0003",
        "name": "Xenovia Quarto",
        "rank": "S",
        "class": "Baddie",
        "role": "Berserker",
        "image": "https://i.imgur.com/T1drEJ1.png"
    },
    {
        "id": "A0004",
        "name": "Rias Gremory",
        "rank": "A",
        "class": "Onee-San",
        "role": "Healer",
        "image": "https://i.imgur.com/8zE1s7J.png"
    },
    {
        "id": "C0005",
        "name": "Akeno Himejima",
        "rank": "C",
        "class": "Onee-San",
        "role": "Tank",
        "image": "https://i.imgur.com/jWsGdHa.png"
    },
    {
        "id": "A0005",
        "name": "Rossweisse",
        "rank": "A",
        "class": "Milf",
        "role": "Duelist",
        "image": "https://i.imgur.com/NdflAYY.png"
    },
    {
        "id": "A0006",
        "name": "Ravel Phoenix",
        "rank": "A",
        "class": "Tsundere",
        "role": "Duelist",
        "image": "https://i.imgur.com/I5eGWRZ.png"
    },
    {
        "id": "B0005",
        "name": "Ravel Phoenixx",
        "rank": "B",
        "class": "Tsundere",
        "role": "Healer",
        "image": "https://i.imgur.com/h22AFEF.png"
    },
    {
        "id": "A0007",
        "name": "Yasaka",
        "rank": "A",
        "class": "Milf",
        "role": "Tank",
        "image": "https://i.imgur.com/SPkhwbU.png"
    },
    {
        "id": "A0008",
        "name": "Serafall Leviathan",
        "rank": "A",
        "class": "Imouto",
        "role": "Deflector",
        "image": "https://i.imgur.com/bjnxEMI.png"
    },
    {
        "id": "S0004",
        "name": "Tsunade Senju",
        "rank": "S",
        "class": "Mommy",
        "role": "Healer",
        "image": "https://i.imgur.com/psKl7Jz.png"
    },
    {
        "id": "A0009",
        "name": "Tsunade Senju",
        "rank": "A",
        "class": "Mommy",
        "role": "Tank",
        "image": "https://i.imgur.com/p30vafK.png"
    },
    {
        "id": "A0010",
        "name": "Tsunade Senju",
        "rank": "A",
        "class": "Mommy",
        "role": "Berserker",
        "image": "https://i.imgur.com/Pc4QYJv.png"
    },
    {
        "id": "C0006",
        "name": "Xenovia Quarto",
        "rank": "C",
        "class": "Baddie",
        "role": "Aura",
        "image": "https://i.imgur.com/ImW0ZpI.png"
    },
    {
        "id": "C0007",
        "name": "Raynare",
        "rank": "C",
        "class": "Baddie",
        "role": "Aura",
        "image": "https://i.imgur.com/42WDygQ.png"
    },
    {
        "id": "A0011",
        "name": "Seekvaira Agares",
        "rank": "A",
        "class": "Onee-San",
        "role": "Foreseer",
        "image": "https://i.imgur.com/d0EF9Kt.png"
    },
    {
        "id": "B006",
        "name": "Raynare",
        "rank": "B",
        "class": "Baddie",
        "role": "Deflector",
        "image": "https://i.imgur.com/KA2WdLH.png"
    },
    {
        "id": "Z0002",
        "name": "Le Fay",
        "rank": "Z",
        "class": "Endbringer",
        "role": "Noble Aura",
        "image": "https://i.imgur.com/iZtAbkP.png"
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

