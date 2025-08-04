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

bot = commands.Bot(command_prefix="r?", intents=discord.Intents.all())

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


@bot.tree.command(name="ustawkanalzlogami",
                  description="Ustaw kanał do wysyłania logów bota (tylko dla administratorów)")
@app_commands.default_permissions(administrator=True)
@app_commands.describe(kanal="Kanał, do którego będą wysyłane logi")
async def set_log_channel(interaction: discord.Interaction, kanal: discord.TextChannel):
    config['log_channel_id'] = kanal.id
    save_config()
    await interaction.response.send_message(f"Kanał logów został pomyślnie ustawiony na {kanal.mention}.",
                                            ephemeral=True)


SUCCESS_MESSAGES_WYJEB = [
    "rzucił/a zaklęcie: Ryko i koko mute ci w oko!",
    "rzucił/a zaklęcie: Czary mary hokus poku {user} spierdala jak ford focus!",
    "wyjebał/a {user} na minutę z czatu! ❤️",
    "naprawił/a czat pozbywajac sie {user}!",
    "pozbył/a sie problemu na minute!",
    "zarchiwował/a {user} na minute",
    "dał/a kare {user} za uzywanie minta!",
    "przestraszył/a {user} kodem na minute",
    "dał/a kare {user} za zbyt mala ilosc wysylanego kodu!"
]
SUCCES_MUTE_MESSAGE = [
    "wyciszył/a {user}",
]
mod_role_id = 1203714318235992064
sigmamod_role_id = 1333189890447249429
mutes_file = 'users_mutes.json'
mute_levels = [30,60,180,720,1440,10080,30240] #Czasy podane w minutach

@bot.tree.command(name="wyjeb", description="Wyjeb wybranego użytkownika na 1 minutę z czatu")
@app_commands.default_permissions(moderate_members=True)
@app_commands.describe(uzytkownik="Użytkownik do wyciszenia na 1 minutę")
async def wyjeb(interaction: discord.Interaction, uzytkownik: discord.Member):
    member = uzytkownik
    if not member:
        await interaction.response.send_message("Nie znaleziono wskazanego użytkownika do wyjebania na tym serwerze!",
                                                ephemeral=True)
        return
    if member == interaction.guild.me:
        await interaction.response.send_message("Nie mogę wyjebać samego siebie!", ephemeral=True)
        return
    if member == interaction.user:
        await interaction.response.send_message("Nie możesz wyjebać samego siebie!", ephemeral=True)
        return
    if member.get_role(mod_role_id) and not interaction.user.get_role(sigmamod_role_id):
        await interaction.response.send_message("Nie możesz wyjebać moderatora!", ephemeral=True)
        return
    try:
        if not interaction.guild.me.guild_permissions.moderate_members or interaction.guild.me.top_role <= member.top_role:
            await interaction.response.send_message("Nie mam wystarczających uprawnień, aby wyjebać tego użytkownika!",
                                                    ephemeral=True)
            return

        await member.timeout(discord.utils.utcnow() + timedelta(minutes=1), reason=f"Wyjebany przez {interaction.user}")
        msg = random.choice(SUCCESS_MESSAGES_WYJEB).replace("{user}", member.mention)
        await interaction.response.send_message(f"{interaction.user.mention} {msg}", ephemeral=False)
    except discord.Forbidden:
        await interaction.response.send_message("Nie mam uprawnień do wypierdalania tego użytkownika!", ephemeral=True)
    except discord.HTTPException as e:
        await interaction.response.send_message(f"Wystąpił błąd HTTP: {e}", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"Wystąpił nieoczekiwany błąd: {e}", ephemeral=True)

def getMuteLevel(user_id):
    try:
        with open(mutes_file, 'r') as f:
            data = json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return 0
    return data.get(user_id, {}).get('mute_level', -1)

def getLastMute(user_id):
    try:
        with open(mutes_file, 'r') as f:
            data = json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return -1
    return data.get(user_id, {}).get('last_mute', -1)

def saveMute(user_id, user_name, mute_level):
    if os.path.exists(mutes_file):
        try:
            with open(mutes_file, 'r') as f:
                data = json.load(f)
        except json.JSONDecodeError:
            data = {}
    else:
        data = {}

    data[user_id] = {
        "name": user_name,
        "last_mute": datetime.datetime.now().isoformat(),
        "mute_level": mute_level
    }
    with open(mutes_file, 'w') as f:
        json.dump(data, f, indent=4)

@bot.tree.command(name="warn", description="Wycisz użytkownika na określony czas")
@app_commands.default_permissions(moderate_members=True)
@app_commands.describe(uzytkownik="Użytkownik do wyciszenia", powod="Powód wyciszenia (opcjonalnie)")
async def warn(interaction: discord.Interaction, uzytkownik: discord.Member, powod: str = "Brak powodu"):
    member = uzytkownik
    if not member:
        await interaction.response.send_message("Nie znaleziono wskazanego użytkownika do wyjebania na tym serwerze!",
                                                ephemeral=True)
        return
    if member == interaction.guild.me or member == interaction.user:
        await interaction.response.send_message("Nie możesz warnować samego siebie!", ephemeral=True)
        return
    if member.get_role(mod_role_id) and not interaction.user.get_role(sigmamod_role_id):
        await interaction.response.send_message("Nie możesz wyjebać moderatora!", ephemeral=True)
        return
    try:
        if not interaction.guild.me.guild_permissions.moderate_members or interaction.guild.me.top_role <= member.top_role:
            await interaction.response.send_message("Nie mam wystarczających uprawnień, aby wyjebać tego użytkownika!",
                                                    ephemeral=True)
            return

        target_user = uzytkownik or interaction.user
        user_id = str(target_user.id)
        currentMuteLevel = getMuteLevel(user_id)
        last_mute_str = getLastMute(user_id)

        if last_mute_str == -1:
            newMuteLevel = 1
        elif datetime.datetime.fromisoformat(last_mute_str) < datetime.datetime.now() - timedelta(days=7):
            newMuteLevel = 1
        else:
            newMuteLevel = currentMuteLevel + 1

        muteLevelIndex = min(newMuteLevel - 1, len(mute_levels) - 1)
        muteTime = mute_levels[muteLevelIndex]

        saveMute(user_id, target_user.name, newMuteLevel)
        msg = random.choice(SUCCES_MUTE_MESSAGE).replace("{user}", member.mention)
        if muteTime > 60 * 24:
            days = muteTime // (60 * 24)
            msg += f" na {days} dni"
        elif(muteTime > 60):
            minutes = muteTime // 60
            msg += f" na {minutes} godzin/e/y"
        else:
            msg += f" na {muteTime} minut"
        await member.timeout(discord.utils.utcnow() + timedelta(minutes=muteTime), reason=f"Wyjebany przez {interaction.user}")
        await interaction.response.send_message(f"{interaction.user.mention} {msg}", ephemeral=False)

    except discord.Forbidden:
        await interaction.response.send_message("Nie mam uprawnień do wypierdalania tego użytkownika!", ephemeral=True)
    except discord.HTTPException as e:
        await interaction.response.send_message(f"Wystąpił błąd HTTP: {e}", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"Wystąpił nieoczekiwany błąd: {e}", ephemeral=True)


@bot.tree.command(name="mute", description="Wycisz użytkownika na określony czas")
@app_commands.default_permissions(moderate_members=True)
@app_commands.describe(uzytkownik="Użytkownik do wyciszenia", czas="Czas wyciszenia, np. 1s, 30m, 2h, 3d",
                       powod="Powód wyciszenia (opcjonalnie)")
async def mute(interaction: discord.Interaction, uzytkownik: discord.Member, czas: str, powod: str = "Brak powodu"):
    def parse_time(time_str):
        units = {"s": 1, "m": 60, "h": 3600, "d": 86400}
        time_str = time_str.lower()
        num = ''
        total_seconds = 0
        for char in time_str:
            if char.isdigit():
                num += char
            elif char in units and num:
                total_seconds += int(num) * units[char]
                num = ''
            else:
                return None
        return total_seconds if total_seconds > 0 else None

    if not uzytkownik:
        await interaction.response.send_message("Nie znaleziono wskazanego użytkownika!", ephemeral=True)
        return
    if uzytkownik == interaction.guild.me:
        await interaction.response.send_message("Nie mogę wyciszyć samego siebie!", ephemeral=True)
        return
    if uzytkownik.top_role >= interaction.guild.me.top_role:
        await interaction.response.send_message("Nie mam uprawnień do wyciszenia tego użytkownika!", ephemeral=True)
        return

    seconds = parse_time(czas)
    if seconds is None or seconds < 1 or seconds > 28 * 24 * 3600:
        await interaction.response.send_message("Podaj poprawny czas wyciszenia (od 1s do 28d, np. 30m, 2h, 3d).",
                                                ephemeral=True)
        return

    try:
        await uzytkownik.timeout(discord.utils.utcnow() + timedelta(seconds=seconds),
                                 reason=f"{powod} (wyciszone przez {interaction.user})")
        await interaction.response.send_message(
            f"{uzytkownik.mention} został/a wyciszony/a na {czas}.\nPowód: {powod}",
            ephemeral=False
        )
    except discord.Forbidden:
        await interaction.response.send_message("Nie mam uprawnień do wyciszenia tego użytkownika!", ephemeral=True)
    except discord.HTTPException as e:
        await interaction.response.send_message(f"Wystąpił błąd HTTP: {e}", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"Wystąpił nieoczekiwany błąd: {e}", ephemeral=True)


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
