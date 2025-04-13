import discord
from discord.ext import commands
from discord import app_commands, Embed
from db.database import db_connect, verify_id, register_user

class General(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db_conn = db_connect()

    @app_commands.command(name="perfil", description="Muestra el perfil del jugador")
    async def perfil(self, interaction: discord.Interaction):
        """Comando para mostrar el perfil del jugador"""

        if not self.db_conn:
            await interaction.response.send_message("❌ No se pudo conectar a la base de datos.")
            return

        user_id = interaction.user.id
        user_name = interaction.user.name

        # Si el usuario no está registrado, lo registramos automáticamente
        if not verify_id(self.db_conn, user_id):
            register_user(self.db_conn, user_id, user_name)

        # Obtener datos actualizados del usuario
        db = self.db_conn["discord_server"]
        col = db["users"]
        user_data = col.find_one({"discordID": str(user_id)})

        # Embed de perfil
        avatar_url = interaction.user.avatar.url if interaction.user.avatar else interaction.user.default_avatar.url

        embed = Embed(
            title=f"👤 Perfil de {user_name}",
            description="Aquí tienes tu información como jugador:",
            color=discord.Color.blurple()
        )

        embed.set_thumbnail(url=avatar_url)
        embed.add_field(name="🆔 ID de Usuario", value=user_data['discordID'], inline=False)
        embed.add_field(name="💰 Monedas", value=user_data.get('monedas', 0), inline=True)
        embed.add_field(name="⚔️ Clase", value=user_data.get('clase', 'Sin clase'), inline=True)
        embed.add_field(name="🔝 Nivel", value=user_data.get('nivel', 1), inline=True)
        embed.add_field(name="🏠 Clan", value=user_data.get('clan', 'Sin clan'), inline=True)
        embed.add_field(name="💪 Poder Total", value=user_data.get('poder_total', 0), inline=True)

        await interaction.response.send_message(embed=embed)

async def setup(bot: commands.Bot):
    cog = General(bot)
    await bot.add_cog(cog)

    # ✅ Forzar registro global del comando
    if not bot.tree.get_command("perfil"):
        bot.tree.add_command(cog.perfil, guild=None)