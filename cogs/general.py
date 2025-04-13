import discord
from discord.ext import commands
from discord import app_commands, Embed
from db.database import db_connect, verify_id

class General(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db_conn = db_connect()

    @app_commands.command(name="perfil", description="Muestra el perfil del usuario")
    async def perfil(self, interaction: discord.Interaction):
        """Comando Slash para mostrar el perfil del usuario."""
        
        if not self.db_conn:
            await interaction.response.send_message("❌ No se pudo conectar a la base de datos.")
            return
        
        # Verificar si el usuario está registrado
        if not verify_id(self.db_conn, interaction.user.id):
            await interaction.response.send_message(f"❌ El usuario {interaction.user.name} no está registrado en la base de datos.")
            return
        
        # Obtener los datos del usuario (esto depende de cómo tengas la estructura de datos)
        db = self.db_conn["discord_server"]
        col = db["users"]
        user_data = col.find_one({"discordID": str(interaction.user.id)})

        # Datos iniciales del usuario si no existen
        user_data = user_data or {
            'discordID': str(interaction.user.id),
            'userName': interaction.user.name,
            'monedas': 0,
            'clase': 'Sin clase',
            'nivel': 1,
            'clan': 'Sin clan',
            'poder_total': 0
        }

        # Crear el embed
        avatar_url = interaction.user.avatar.url
        embed = Embed(
            title=f"Perfil de {interaction.user.name}",
            description=f"Bienvenido, {interaction.user.mention}! Aquí tienes tu perfil:",
            color=discord.Color.blue()
        )
        
        embed.set_thumbnail(url=avatar_url)
        embed.add_field(name="🆔 ID de Usuario", value=user_data['discordID'], inline=False)
        embed.add_field(name="💰 Monedas", value=user_data['monedas'], inline=False)
        embed.add_field(name="⚔️ Clase", value=user_data['clase'], inline=True)
        embed.add_field(name="🔝 Nivel", value=user_data['nivel'], inline=True)
        embed.add_field(name="🏰 Clan", value=user_data['clan'], inline=True)
        embed.add_field(name="💪 Poder Total", value=user_data['poder_total'], inline=True)

        # Enviar el embed
        await interaction.response.send_message(embed=embed)

async def setup(bot: commands.Bot):
    general = General(bot)
    # Registramos los comandos Slash del bot tree
    await bot.add_cog(general)
    # Sincronizamos los comandos con la API de Discord
    await bot.tree.sync()

