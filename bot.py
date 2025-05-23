from apikeys import token
import discord
from discord import app_commands
from discord.ext import commands
from datetime import timedelta
import random
import json
import os
import datetime
import asyncio

bot = commands.Bot(command_prefix="!", intents=discord.Intents.all())

LEVELS_FILE = 'levels.json'
if os.path.exists(LEVELS_FILE):
    with open(LEVELS_FILE, 'r') as f:
        levels = json.load(f)
else:
    levels = {}

def save_levels():
    with open(LEVELS_FILE, 'w') as f:
        json.dump(levels, f)

CONFIG_FILE = 'config.json'
DEFAULT_CONFIG = {'log_channel_id': None}
config = {}

def load_config():
    global config
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f:
            try:
                config = json.load(f)
            except json.JSONDecodeError:
                print(f"Błąd podczas wczytywania {CONFIG_FILE}. Tworzę domyślny plik.")
                config = DEFAULT_CONFIG
                save_config()
    else:
        config = DEFAULT_CONFIG
        save_config()

def save_config():
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=4)


async def send_log_message(message_content: str):
    log_channel_id = config.get('log_channel_id')
    if log_channel_id is None:
        return

    log_channel = bot.get_channel(log_channel_id)
    if log_channel is None:
        try:
            log_channel = await bot.fetch_channel(log_channel_id)
        except (discord.NotFound, discord.Forbidden, discord.HTTPException):
            print(f"Nie znaleziono kanału logów lub brak uprawnień do niego (ID: {log_channel_id}).")
            return

    try:
        await log_channel.send(message_content)
    except discord.Forbidden:
        print(f"Brak uprawnień do wysyłania wiadomości w kanale logów (ID: {log_channel_id}).")
    except discord.HTTPException as e:
        print(f"Błąd HTTP podczas wysyłania logu do kanału (ID: {log_channel_id}): {e}")


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
    load_config()
    print(f'Zalogowano jako {bot.user.name} (ID: {bot.user.id})')
    print('------')
    try:
        synced = await bot.tree.sync()
        print(f"Zsynchronizowano {len(synced)} komend(y)")
    except Exception as e:
        print(f"Nie udało się zsynchronizować komend: {e}")


@bot.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return

    if random.random() <= 0.2:
        user_id = str(message.author.id)
        if user_id not in levels:
            levels[user_id] = {'xp': 0}

        old_level, _ = calculate_level(levels[user_id]['xp'])
        levels[user_id]['xp'] += random.randint(5, 15)
        new_level, _ = calculate_level(levels[user_id]['xp'])

        if new_level > old_level:
             if new_level > 1:
                  await message.channel.send(f"{message.author.mention} awansował/a na poziom {new_level}!")

        save_levels()

    await bot.process_commands(message)


@bot.event
async def on_message_delete(message: discord.Message):
    if message.author.bot:
        return

    if config.get('log_channel_id') is not None and message.channel.id == config['log_channel_id']:
        return

    channel = message.channel
    author = message.author
    content = message.content if message.content else "Brak treści"

    timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log_message = (
        f"[{timestamp}] 🗑️ Wiadomość usunięta w kanale {channel.mention}\n"
        f"Autor: {author.mention} (`{author.name}`)\n"
        f"Treść: ```{content}```"
    )
    await send_log_message(log_message)

@bot.event
async def on_member_update(before: discord.Member, after: discord.Member):
    timeout_before = before.timed_out_until
    timeout_after = after.timed_out_until

    if timeout_after and (not timeout_before or timeout_after > timeout_before):
        timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        end_time_str = timeout_after.strftime('%Y-%m-%d %H:%M:%S UTC')
        log_message = (
            f"[{timestamp}] 🔇 Użytkownik {after.mention} (`{after.name}`) został/a wyciszony/a (timeout) do {end_time_str}."
        )
        await send_log_message(log_message)
    elif timeout_before and not timeout_after:
        timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_message = (
            f"[{timestamp}] 🔊 Timeout użytkownika {after.mention} (`{after.name}`) został/a zakończony/a."
        )
        await send_log_message(log_message)

    roles_before = set(before.roles)
    roles_after = set(after.roles)

    roles_added = list(roles_after - roles_before)
    roles_removed = list(roles_before - roles_after)

    if roles_added or roles_removed:
        timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_message_parts = [f"[{timestamp}] 🎭 Zmiana ról dla użytkownika {after.mention} (`{after.name}`):"]

        if roles_added:
            added_mentions = [role.mention for role in roles_added]
            log_message_parts.append(f"  ➕ Dodano role: {', '.join(added_mentions)}")

        if roles_removed:
            removed_mentions = [role.mention for role in roles_removed]
            log_message_parts.append(f"  ➖ Usunięto role: {', '.join(removed_mentions)}")

        await send_log_message("\n".join(log_message_parts))


@bot.tree.command(name="level", description="Sprawdź swój aktualny poziom i XP")
async def level(interaction: discord.Interaction, user: discord.User = None):
    target_user = user or interaction.user
    user_id = str(target_user.id)
    if user_id in levels:
        xp = levels[user_id]['xp']
        lvl, remaining_xp = calculate_level(xp)
        required_for_next = required_xp(lvl)
        await interaction.response.send_message(
            f"{target_user.name} jest na poziomie {lvl} z {remaining_xp} XP. Do następnego poziomu brakuje {required_for_next - remaining_xp} XP.",
            ephemeral=False
        )
    else:
        await interaction.response.send_message(f"{target_user.name} nie ma jeszcze żadnego XP.", ephemeral=False)


@bot.tree.command(name="leaderboard", description="Pokaż 10 użytkowników z największą ilością XP")
async def leaderboard(interaction: discord.Interaction):
    sorted_users = sorted(levels.items(), key=lambda x: x[1]['xp'], reverse=True)[:10]
    if not sorted_users:
        await interaction.response.send_message("Brak danych w tabeli wyników.", ephemeral=False)
        return

    leaderboard_text = "**Tabela wyników:**\n"
    user_fetch_tasks = [bot.fetch_user(int(user_id)) for user_id, _ in sorted_users]
    fetched_users = await asyncio.gather(*user_fetch_tasks, return_exceptions=True)

    user_map = {str(user.id): user for user in fetched_users if isinstance(user, discord.User)}

    for index, (user_id, data) in enumerate(sorted_users, start=1):
        level, _ = calculate_level(data['xp'])
        user = user_map.get(user_id)
        user_display_name = user.name if user else f"Nieznany Użytkownik (ID: {user_id})"
        leaderboard_text += f"{index}. {user_display_name} - Poziom {level}, {data['xp']} XP\n"

    await interaction.response.send_message(leaderboard_text, ephemeral=False)


@bot.tree.command(name="ustawkanalzlogami", description="Ustaw kanał do wysyłania logów bota (tylko dla administratorów)")
@app_commands.default_permissions(administrator=True)
@app_commands.describe(kanal="Kanał, do którego będą wysyłane logi")
async def set_log_channel(interaction: discord.Interaction, kanal: discord.TextChannel):
    config['log_channel_id'] = kanal.id
    save_config()
    await interaction.response.send_message(f"Kanał logów został pomyślnie ustawiony na {kanal.mention}.", ephemeral=True)


@bot.tree.command(name="wyjebsimona", description="Wyjeb simona na 1 minutę z czatu")
@app_commands.default_permissions(moderate_members=True)
async def wyjebsimona(interaction: discord.Interaction):
    id_simona = 1135927904702845039
    member = interaction.guild.get_member(id_simona)
    if not member:
        await interaction.response.send_message("Użytkownik Simon nie został znaleziony na tym serwerze!", ephemeral=True)
        return

    try:
        if not interaction.guild.me.guild_permissions.moderate_members or interaction.guild.me.top_role <= member.top_role:
             await interaction.response.send_message("Nie mam wystarczających uprawnień, aby wyciszyć tego użytkownika!", ephemeral=False)
             return

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
        await interaction.response.send_message("Nie mam uprawnień do timeoutowania tego użytkownika (Discord Forbidden)!", ephemeral=False)
    except discord.HTTPException as e:
        await interaction.response.send_message(f"Wystąpił błąd HTTP: {e}", ephemeral=False)
    except Exception as e:
        await interaction.response.send_message(f"Wystąpił nieoczekiwany błąd: {e}", ephemeral=False)


@bot.tree.command(name="wyjebpieczarka", description="Wyjeb pieczarka na 1 minutę z czatu")
@app_commands.default_permissions(moderate_members=True)
async def wyjebpieczarka(interaction: discord.Interaction):
    id_pieczarka = 1090356556589174794
    member = interaction.guild.get_member(id_pieczarka)
    if not member:
        await interaction.response.send_message("Użytkownik Pieczarek nie został znaleziony na tym serwerze!", ephemeral=True)
        return

    try:
        if not interaction.guild.me.guild_permissions.moderate_members or interaction.guild.me.top_role <= member.top_role:
             await interaction.response.send_message("Nie mam wystarczających uprawnień, aby wyciszyć tego użytkownika!", ephemeral=False)
             return

        await member.timeout(discord.utils.utcnow() + timedelta(minutes=1), reason="Wyjeb pieczarka command")
        success_messages_pieczarek = [
            "rzucił/a zaklęcie na pieczarka: Ryko i koko mute ci w oko!",
            #"rzucił/a zaklęcie na pieczarka: Czary mary hokus poku pieczarek spierdala jak ford focus!",
            "wywalił/a pieczarka na minutę z czatu! ❤️",
            "naprawił/a czat pozbywajac sie pieczarka!",
            "pozbył/a sie problemu na minute!",
            "przestraszył/a pieczarka kodem na minute",
            "dał/a kare pieczarkowi za zbyt mala ilosc wysylanego koduu na <#1232674301493383229>"
        ]
        await interaction.response.send_message(f"{interaction.user.mention} {random.choice(success_messages_pieczarek)}",
                                                ephemeral=False)
    except discord.Forbidden:
        await interaction.response.send_message("Nie mam uprawnień do timeoutowania tego użytkownika (Discord Forbidden)!", ephemeral=False)
    except discord.HTTPException as e:
        await interaction.response.send_message(f"Wystąpił błąd HTTP: {e}", ephemeral=False)
    except Exception as e:
        await interaction.response.send_message(f"Wystąpił nieoczekiwany błąd: {e}", ephemeral=False)


@bot.tree.command(name="wyjebmiska", description="Wyjeb miska na 1 minutę z czatu")
@app_commands.default_permissions(moderate_members=True)
async def wyjebmiska(interaction: discord.Interaction):
    id_miska = 1103907600120156272
    member = interaction.guild.get_member(id_miska)
    if not member:
        await interaction.response.send_message("Użytkownik Miska nie został znaleziony na tym serwerze!", ephemeral=True)
        return

    try:
        if not interaction.guild.me.guild_permissions.moderate_members or interaction.guild.me.top_role <= member.top_role:
             await interaction.response.send_message("Nie mam wystarczających uprawnień, aby wyciszyć tego użytkownika!", ephemeral=False)
             return

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
        await interaction.response.send_message("Nie mam uprawnień do timeoutowania tego użytkownika (Discord Forbidden)!", ephemeral=False)
    except discord.HTTPException as e:
        await interaction.response.send_message(f"Wystąpił błąd HTTP: {e}", ephemeral=False)
    except Exception as e:
        await interaction.response.send_message(f"Wystąpił nieoczekiwany błąd: {e}", ephemeral=False)


@bot.tree.command(name="mintdetected", description="I hate mint")
@app_commands.default_permissions(moderate_members=True)
async def mintDetected(interaction: discord.Interaction):
    try:
        await interaction.response.send_message("Mint detected\nopinion rejected", ephemeral=False)
    except discord.HTTPException as e:
        await interaction.response.send_message(f"Wystąpił błąd: {e}", ephemeral=False)
    except Exception as e:
        await interaction.response.send_message(f"Wystąpił nieoczekiwany błąd: {e}", ephemeral=False)


load_config()


bot.run(token)