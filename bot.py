from apikeys import token
import discord
from discord import app_commands
from discord.ext import commands
from datetime import timedelta
import random
import json
import os

bot = commands.Bot(command_prefix="!", intents=discord.Intents.all())

if os.path.exists('levels.json'):
    with open('levels.json', 'r') as f:
        levels = json.load(f)
else:
    levels = {}


def save_levels():
    with open('levels.json', 'w') as f:
        json.dump(levels, f)


def required_xp(level):
    return level * 100


def calculate_level(xp):
    level = 1
    while xp >= required_xp(level):
        xp -= required_xp(level)
        level += 1
    return level, xp


@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name} (ID: {bot.user.id})')
    print('------')
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} command(s)")
    except Exception as e:
        print(f"Failed to sync commands: {e}")


@bot.event
async def on_message(message):
    if message.author.bot:
        return

    if random.random() <= 0.2:
        user_id = str(message.author.id)
        if user_id not in levels:
            levels[user_id] = {'xp': 0}

        levels[user_id]['xp'] += random.randint(5, 15)
        level, remaining_xp = calculate_level(levels[user_id]['xp'])

        """
        if level > 1 and remaining_xp < required_xp(level - 1):
            await message.channel.send(f"{message.author.mention} awansował/a na poziom {level}!")
        """

        save_levels()

    await bot.process_commands(message)


@bot.tree.command(name="level", description="Sprawdź swój aktualny poziom i XP")
async def level(interaction: discord.Interaction, user: discord.User = None):
    target_user = user or interaction.user
    user_id = str(target_user.id)
    if user_id in levels:
        xp = levels[user_id]['xp']
        lvl, remaining_xp = calculate_level(xp)
        await interaction.response.send_message(f"{target_user.name} jest na poziomie {lvl} z {remaining_xp} XP.",
                                                ephemeral=False)
    else:
        await interaction.response.send_message(f"{target_user.name} nie ma jeszcze żadnego XP.", ephemeral=False)


@bot.tree.command(name="leaderboard", description="Pokaż 10 użytkowników z największą ilością XP")
async def leaderboard(interaction: discord.Interaction):
    sorted_users = sorted(levels.items(), key=lambda x: x[1]['xp'], reverse=True)[:10]
    if not sorted_users:
        await interaction.response.send_message("Brak danych w tabeli wyników.", ephemeral=False)
        return

    leaderboard_text = "**Tabela wyników:**\n"
    for index, (user_id, data) in enumerate(sorted_users, start=1):
        level, _ = calculate_level(data['xp'])
        user = await bot.fetch_user(int(user_id))
        leaderboard_text += f"{index}. {user.name} - Poziom {level}, {data['xp']} XP\n"

    await interaction.response.send_message(leaderboard_text, ephemeral=False)


@bot.tree.command(name="wyjebsimona", description="Wyjeb simona na 1 minutę z czatu")
@app_commands.default_permissions(moderate_members=True)
async def wyjebsimona(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.moderate_members:
        await interaction.response.send_message("Nie masz uprawnień do użycia tej komendy!", ephemeral=True)
        return

    id_simona = 1135927904702845039
    member = interaction.guild.get_member(id_simona)
    if not member:
        await interaction.response.send_message("Użytkownik nie został znaleziony na tym serwerze!", ephemeral=True)
        return

    try:
        await member.timeout(discord.utils.utcnow() + timedelta(minutes=1), reason="Wyjeb simona command")
        success_messages_simon = [
            "rzucił/a zaklęcie na simona: Ryko i koko mute ci w oko!",
            "rzucił/a zaklęcie na simona: Czary mary hokus poku simon spierdala jak ford focus!",
            "wyjebał/a simona na minutę z czatu! ❤️",
            "naprawił/a czat pozbywajac sie simona!",
            "pozbył/a sie problemu na minute!",
            "z archował/a simona na minute",
            "dał/a kare simonowi za uzywanie minta!"
        ]
        await interaction.response.send_message(f"{interaction.user.mention} {random.choice(success_messages_simon)}",
                                                ephemeral=False)
    except discord.Forbidden:
        await interaction.response.send_message("Nie mam uprawnień do timeoutowania tego użytkownika!", ephemeral=False)
    except discord.HTTPException as e:
        await interaction.response.send_message(f"Wystąpił błąd: {e}", ephemeral=False)

@bot.tree.command(name="wyjebmiska", description="Wyjeb miska na 1 minutę z czatu")
@app_commands.default_permissions(moderate_members=True)
async def wyjebmiska(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.moderate_members:
        await interaction.response.send_message("Nie masz uprawnień do użycia tej komendy!", ephemeral=True)
        return

    id_miska = 1103907600120156272
    member = interaction.guild.get_member(id_miska)
    if not member:
        await interaction.response.send_message("Użytkownik nie został znaleziony na tym serwerze!", ephemeral=True)
        return

    try:
        await member.timeout(discord.utils.utcnow() + timedelta(minutes=1), reason="Wyjeb miska command")
        success_messages = [
            "rzucił/a zaklęcie na miska: Ryko i koko mute ci w oko!",
            "rzucił/a zaklęcie na miska: Czary mary hokus poku placek spierdala jak ford focus!",
            "wyjebał/a miska na minutę z czatu! ❤️",
            "naprawił/a czat pozbywajac sie miska!",
            "pozbył/a sie problemu na minute!"
        ]
        await interaction.response.send_message(f"{interaction.user.mention} {random.choice(success_messages)}",
                                                ephemeral=False)
    except discord.Forbidden:
        await interaction.response.send_message("Nie mam uprawnień do timeoutowania tego użytkownika!", ephemeral=False)
    except discord.HTTPException as e:
        await interaction.response.send_message(f"Wystąpił błąd: {e}", ephemeral=False)


@bot.tree.command(name="mintdetected", description="I hate mint")
@app_commands.default_permissions(moderate_members=True)
async def mintDetected(interaction: discord.Interaction):
    if not interaction.user.guild_permissions.moderate_members:
        await interaction.response.send_message("Nie masz uprawnień do użycia tej komendy!", ephemeral=True)
        return

    try:
        await interaction.response.send_message("Mint detected\nopinion rejected",
                                                ephemeral=False)
    except discord.HTTPException as e:
        await interaction.response.send_message(f"Wystąpił błąd: {e}", ephemeral=False)
bot.run(token)