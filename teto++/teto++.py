#  yuelyxia  ©  2025 – 2026

from dotenv import load_dotenv
import os
load_dotenv()

import pymongo

import asyncio
import aiohttp
import re
import datetime
import time

import discord
from discord import app_commands
from discord.ext import commands, tasks

TOKEN = os.getenv("TOKEN")
CLIENT = os.getenv("CLIENT")

# mongodb info
client = pymongo.MongoClient(CLIENT)
db = client["database"]
userscol = db["users"]
serverscol = db["servers"]
accountscol = db["accounts"]
trusteduserscol = db["trusted_users"]
trustedserverscol = db["trusted_servers"]
altscol = db["alts"]
invitescol = db["invites"]

# tri bots
tri_bots = [
    1450073025818136598, # teto
    1457249982104211467, # teto++
    1457382953293320304, # neru
    1457309787044839477, # miku
    1457009979817988241, # kafu
]

TRI_Archive = 1371673839695826974

USER_REPORTS_CHANNEL = 1375132097605406721
INVITE_LOGS_CHANNEL = 1523229932375900300

intents = discord.Intents.all()
bot = commands.Bot(command_prefix=',', help_command=None, intents=intents)

red_tags = ["Scammer", "Scam Server Owner", "Raider", "Plagiarist", "Fake Event Host", "Impersonator", "Vouch Scammer"]
yellow_tags = ["Suspect", "Service Ban", "Unprofessional MM", "Unprofessional Pilot", "Unprofessional IDV MM", "Unprofessional Staff", "Unprofessional Supervisor", "Improper Conduct"]

red_server_tags = ["Scam Server", "Impersonator Server", "Fake Vouch Server", "Fake Event Server"]
yellow_server_tags = ["Suspect Server"]

red_account_tags = ["Scammed Account", "Scammer Account", "Leeched Account"]
yellow_account_tags = ["Under Investigation", "Advertised by Scammer"]

# formatting functions

def default_user_profile(user):
    profile = discord.Embed(title=f"{user.display_name.replace('||', '\\|\\|')}")
    profile.set_thumbnail(url=f"{user.display_avatar}")
    profile.description = f"`{user.id}`\n{user.mention}\n`{user.name}`"
    profile.description += f"\n-# **Account Created** – <t:{round(int(user.created_at.timestamp()))}:D> (<t:{round(int(user.created_at.timestamp()))}:R>)" + '\n'
    profile.set_footer(text="✦　This user is unreported.")
    return profile
def default_server_profile(guild):
    profile = discord.Embed(title=f"{guild.name}")
    if guild.icon:
        profile.set_thumbnail(url=f"{guild.icon.url}")
    profile.description = f"`{guild.id}`"
    if guild.created_at:
        profile.description += f"\n-# **Server Created** – <t:{round(int(guild.created_at.timestamp()))}:D> (<t:{round(int(guild.created_at.timestamp()))}:R>)" + '\n'
    if guild.banner:
        profile.set_image(url=guild.banner.url)
    profile.set_footer(text="✦　This server is unreported.")
    return profile
def reported_user_profile(user, user_profile):
    r_profile_list = user_profile["r_profile_list"]
    no_of_cases = len(user_profile) - 2
    cases = []
    for i in range(1, no_of_cases + 1):
        cases.append(user_profile[str(i)])
    tags_strings = []
    all_tags_list = []
    for case in cases:
        tags_strings.append(case["tags"])
    for tags_string in tags_strings:
        tags_list = tags_string.split(", ")
        for tag in tags_list:
            all_tags_list.append(tag)
    all_tags_list = sort_user_tags(all_tags_list)
    title = all_tags_list[0]
    newest_case_tags = cases[-1]["tags"].split(", ")
    newest_case_title = newest_case_tags[0]
    r_profile = format_user_r_profile(user, r_profile_list, title)
    add_case = format_user_add_case(cases[-1], newest_case_title)
    add_case.set_footer(text=f"Page {len(cases)} of {no_of_cases}")
    embeds = [r_profile, add_case]
    return embeds
def reported_server_profile(guild, server_profile):
    r_profile_list = server_profile["r_profile_list"]
    no_of_cases = len(server_profile) - 2
    cases = []
    for i in range(1, no_of_cases + 1):
        cases.append(server_profile[str(i)])
    tags_strings = []
    all_tags_list = []
    for case in cases:
        tags_strings.append(case["tags"])
    for tags_string in tags_strings:
        tags_list = tags_string.split(", ")
        for tag in tags_list:
            all_tags_list.append(tag)
    all_tags_list = sort_server_tags(all_tags_list)
    title = all_tags_list[0]
    newest_case_tags = cases[-1]["tags"].split(", ")
    newest_case_title = newest_case_tags[0]
    r_profile = format_server_r_profile(guild, r_profile_list, title)
    if guild.banner:
        r_profile.set_image(url=guild.banner.url)
    add_case = format_server_add_case(cases[-1], newest_case_title)
    add_case.set_footer(text=f"Page {len(cases)} of {no_of_cases}")
    embeds = [r_profile, add_case]
    return embeds

def sort_user_tags(tags):
    sorted_tags = []
    for tag in tags:
        if tag == "Ex-offender":
            sorted_tags.append(tag)
    for tag_to_find in red_tags:
        for tag in tags:
            if tag == tag_to_find:
                sorted_tags.append(tag)
    for tag_to_find in yellow_tags:
        for tag in tags:
            if tag == tag_to_find:
                sorted_tags.append(tag)
    return sorted_tags
def sort_server_tags(tags):
    sorted_tags = []
    for tag_to_find in red_server_tags:
        for tag in tags:
            if tag == tag_to_find:
                sorted_tags.append(tag)
    for tag_to_find in yellow_server_tags:
        for tag in tags:
            if tag == tag_to_find:
                sorted_tags.append(tag)
    return sorted_tags

def selected_string(selected_list):
    string = ", ".join(selected_list)
    return string
def alts_string(alts_list):
    string = ""
    for alt in alts_list:
        string += f"{str(alt)}" + " "
    string = string[:-1]
    string = "`" + string + "`"
    return string
def image_links_to_embeds(image_links):
    image_embeds = []
    for url in image_links:
        embed = discord.Embed()
        embed.set_image(url=url)
        image_embeds.append(embed)
    return image_embeds
    # returns a list

def format_trusteduser_profile(user, trusteduser_profile):
    if trusteduser_profile["current_staff"] == 1:
        trusted_embed = discord.Embed(colour=0xbba8dd, title=f"{user.display_name.replace('||', '\\|\\|')}")
        title = "TRI Staff"
    elif trusteduser_profile["staff"] == 1:
        trusted_embed = discord.Embed(colour=0x9279b5, title=f"{user.display_name.replace('||', '\\|\\|')}")
        title = "Former TRI Staff"
    else:
        trusted_embed = discord.Embed(colour=0x9279b5, title=f"{user.display_name.replace('||', '\\|\\|')}")
        title = "Trusted User"
    trusted_embed.set_thumbnail(url=f"{user.display_avatar}")
    trusted_embed.description = f"```ansi\n\u001b[1m{title}\u001b[0m\n```"
    trusted_embed.description += f"`{user.id}`\n{user.mention}\n`{user.name}`"
    trusted_embed.description += "\n-# **Account Created** – " + f"<t:{round(int(user.created_at.timestamp()))}:D> (<t:{round(int(user.created_at.timestamp()))}:R>)" + '\n'
    trusted_embed.set_footer(text="✦　This user is trusted.")
    if trusteduser_profile["staff"] == 1:
        trusted_embed.description += "\n**Staff Info**"
        trusted_embed.description += f"\n> **Tickets** – {trusteduser_profile["tickets"]}"
        trusted_embed.description += f"\n> **Reports** – {trusteduser_profile["reports"]}"
        trusted_embed.description += f"\n> **Closes** – {trusteduser_profile["closes"]}"
        trusted_embed.description += f"\n> **Reviews** – {trusteduser_profile["reviews"]}"
        trusted_embed.description += f"\n> **Votes** – {trusteduser_profile["votes"]}"
        if trusteduser_profile["mm"] == 1 or trusteduser_profile["pilot"] == 1 or trusteduser_profile["trader"] == 1:
            trusted_embed.description += "\n"
    if trusteduser_profile["mm"] == 1:
        trusted_embed.description += "\n**Professional Middleman**"
    if trusteduser_profile["pilot"] == 1:
        trusted_embed.description += "\n**Professional Pilot**"
    if trusteduser_profile["trader"] == 1:
        trusted_embed.description += "\n**Trusted Trader**"
    return trusted_embed
def format_user_r_profile(user, r_profile_list, title):
    if title == "Ex-offender":
        r_profile = discord.Embed(colour=0xFFD643, title=f"{user.display_name.replace('||', '\\|\\|')}")
        colour = "\u001b[1;33m"
    elif title in red_tags:
        r_profile = discord.Embed(colour=0xFF0045, title=f"{user.display_name.replace('||', '\\|\\|')}")
        colour = "\u001b[1;31m"
    elif title in yellow_tags:
        r_profile = discord.Embed(colour=0xFFD643, title=f"{user.display_name.replace('||', '\\|\\|')}")
        colour = "\u001b[1;33m"
    else:
        r_profile = discord.Embed(title=f"{user.display_name.replace('||', '\\|\\|')}")
        colour = "\u001b[0m"
    r_profile.set_thumbnail(url=f"{user.display_avatar}")
    r_profile.description = f"```ansi\n{colour}{title}\u001b[0m\n```"
    r_profile.description += f"`{user.id}`\n{user.mention}\n`{user.name}`"
    r_profile.description += "\n-# **Account Created** – " + f"<t:{round(int(user.created_at.timestamp()))}:D> (<t:{round(int(user.created_at.timestamp()))}:R>)\n"
    r_profile.description += f"\n**Alt(s)** – {r_profile_list[0] or "None"}"
    r_profile.description += f"\n**Other Tag(s)** – {r_profile_list[1] or "None"}"
    return r_profile
def format_user_add_case(add_case_list, case_title):
    if case_title == "Ex-offender":
        add_case = discord.Embed(colour=0xFFD643)
    elif case_title in red_tags:
        add_case = discord.Embed(colour=0xFF0045)
    elif case_title in yellow_tags:
        add_case = discord.Embed(colour=0xFFD643)
    else:
        add_case = discord.Embed()
    if add_case_list:
        add_case.description = f"**{add_case_list["tags"] or "TBC"}**\n"
        add_case.description += "-# **Date Added** – " + add_case_list["date_added"]
        add_case.description += "\n-# **Game(s)** – " + add_case_list["games"]
        add_case.description += f"\n\n**Reason** – {add_case_list["reason"]}\n\u200b"
        add_case.description += f"\n-# **Contributor** – {add_case_list["contributor"]}\n-# **TRI Staff** – {add_case_list["staff"]}\n-# **Accepted by** – {add_case_list["accepted_by"]}"
    return add_case
def format_trustedserver_profile(guild):
    if guild.id == TRI_Archive:
        trusted_embed = discord.Embed(colour=0xbba8dd, title=f"{guild.name}")
        title = "Trade Report Investigation Archive"
    else:
        trusted_embed = discord.Embed(colour=0x9279b5, title=f"{guild.name}")
        title = "Trusted Server"
    if guild.icon:
        trusted_embed.set_thumbnail(url=f"{guild.icon.url}")
    trusted_embed.description = f"```ansi\n\u001b[1m{title}\u001b[0m\n```"
    trusted_embed.description += f"`{guild.id}`"
    if guild.created_at:
        trusted_embed.description += "\n**Server Created** – " + f"<t:{round(int(guild.created_at.timestamp()))}:D> (<t:{round(int(guild.created_at.timestamp()))}:R>)" + '\n'
    if guild.banner:
        trusted_embed.set_image(url=guild.banner.url)
    return trusted_embed
def format_server_r_profile(guild, r_profile_list, title):
    if title in red_server_tags:
        r_profile = discord.Embed(colour=0xCF2D53, title=f"{guild.name}")
        colour = "\u001b[1;31m"
    elif title in yellow_server_tags:
        r_profile = discord.Embed(colour=0xd9b534, title=f"{guild.name}")
        colour = "\u001b[1;33m"
    else:
        r_profile = discord.Embed()
        colour = "\u001b[0m"
    if guild.icon:
        r_profile.set_thumbnail(url=f"{guild.icon.url}")
    r_profile.description = f"```ansi\n{colour}{title}\u001b[0m\n```"
    r_profile.description += f"`{guild.id}`"
    if guild.created_at:
        r_profile.description += "\n-# **Server Created** – " + f"<t:{round(int(guild.created_at.timestamp()))}:D> (<t:{round(int(guild.created_at.timestamp()))}:R>)\n"
    r_profile.description += f"\n**Owner** – {r_profile_list[0]}\n**Other Tag(s)** – {r_profile_list[1] or "None"}"
    if guild.banner:
        r_profile.set_image(url=guild.banner.url)
    return r_profile
def format_server_add_case(add_case_list, case_title):
    if case_title in red_server_tags:
        add_case = discord.Embed(colour=0xCF2D53)
    elif case_title in yellow_server_tags:
        add_case = discord.Embed(colour=0xd9b534)
    else:
        add_case = discord.Embed()
    add_case.description = f"**{add_case_list["tags"] or "TBC"}**\n"
    add_case.description += "-# **Date Added** – " + add_case_list["date_added"]
    add_case.description += f"\n\n**Reason** – {add_case_list["reason"]}\n\u200b"
    add_case.description += f"\n-# **Contributor** – {add_case_list["contributor"]}\n-# **TRI Staff** – {add_case_list["staff"]}\n-# **Accepted by** – {add_case_list["accepted_by"]}"
    return add_case

def format_game(game):
    if game.lower() in ["genshin", "gi", "genshin impact"]:
        game = "Genshin Impact"
    elif game.lower() in ["hsr", "honkai star rail", "honkai: star rail"]:
        game = "Honkai: Star Rail"
    elif game.lower() in ["wuwa", "wuthering waves"]:
        game = "Wuthering Waves"
    elif game.lower() in ["rblx", "roblox"]:
        game = "Roblox"
    elif game.lower() in ["zzz", "zenless zone zero"]:
        game = "Zenless Zone Zero"
    elif game.lower() in ["hi3", "honkai impact 3rd", "honkai impact"]:
        game = "Honkai Impact 3rd"
    elif game.lower() in ["project sekai", "prsk", "pjsk", "project sekai: colorful stage", "project sekai: colourful stage", "project sekai colorful stage", "project sekai colourful stage", "colorful stage", "colourful stage", "colorfulstage", "colourfulstage"]:
        game = "Project Sekai"
    elif game.lower() in ["crk", "cookie run kingdom", "cookie run: kingdom"]:
        game = "Cookie Run: Kingdom"
    elif game.lower() in ["idv", "identity v"]:
        game = "Identity V"
    elif game.lower() in ["valorant"]:
        game = "Valorant"
    else:
        return None
    return game
def get_game_icon(game):
    game = format_game(game)
    if game == "Genshin Impact":
        icon = "https://media.discordapp.net/attachments/1455055877034868769/1516025983076143174/genshin.png?ex=6a3124b8&is=6a2fd338&hm=5d671a96d68705e20bd54d9bd833497d9077cec2149d412eb9580ac943d4ebd6&=&format=webp&quality=lossless&width=1024&height=1024"
    elif game == "Honkai: Star Rail":
        icon = "https://media.discordapp.net/attachments/1455055877034868769/1516026005532446741/hsr.jpg?ex=6a3124be&is=6a2fd33e&hm=9678434ab7eaebc8fc09f9f3c336d95bd0f5cab888f7c36a58b31506a873f292&=&format=webp&width=1580&height=1580"
    elif game == "Wuthering Waves":
        icon = "https://media.discordapp.net/attachments/1455055877034868769/1516026232121069648/image.png?ex=6a3124f4&is=6a2fd374&hm=e6fd4759dd08d9fbdd8cb469219e887b284e20bb51ba5b43408c7bf2962f02ed&=&format=webp&quality=lossless&width=1580&height=1580"
    elif game == "Roblox":
        icon = "https://media.discordapp.net/attachments/1455055877034868769/1516270091681927218/500px-Roblox_28202529_28App_Icon29.svg.png?ex=6a320810&is=6a30b690&hm=bd89b113f822cdae762c07bfbd5692447bdcd13de4fe1ea3bd10e3a35bcba2c4&=&format=webp&quality=lossless&width=1000&height=1000"
    elif game == "Zenless Zone Zero":
        icon = "https://media.discordapp.net/attachments/1455055877034868769/1516027356777680926/image.png?ex=6a312600&is=6a2fd480&hm=2e375ceeb0a0dd8caec476d8ea106334dd6dcc9db99bbbe46cbdd5990fe169d0&=&format=webp&quality=lossless&width=700&height=700"
    elif game == "Honkai Impact 3rd":
        icon = "https://media.discordapp.net/attachments/1455055877034868769/1516027382153089054/rKiMpbQqkg-LUolGjtRvi3T-SEVL30hY_2A1PWK0jagN380TUXj0SHQu9fkmiDdEAtA_J4SHW8p_czxpAAbyYw.png?ex=6a312606&is=6a2fd486&hm=f9b5d4a6ebace2e076fdfff5f9da349b5799444476d65908cfcab8c37704d7b5&=&format=webp&quality=lossless&width=1024&height=1024"
    elif game == "Project Sekai":
        icon = "https://media.discordapp.net/attachments/1455055877034868769/1516270868807024691/pdv4ajv4O-ow2BVpWopiMy9XSHXTJSEzi1gjTeD-mg4V3bkM6dmu8qJv_-Poupg5mQ6wNXlhJRuXaH-8SE91.png?ex=6a3208ca&is=6a30b74a&hm=49f291eab7537e755e6b42023bf0dd7d64593fcd48e9382fb541ba78448774c5&=&format=webp&quality=lossless&width=1024&height=1024"
    elif game == "Cookie Run: Kingdom":
        icon = "https://media.discordapp.net/attachments/1455055877034868769/1516269434442874980/J1zzZf_Clyg51sikuBbfTMD_sGVK64Ki5vyVtn3MmkUUzQ-AxKWq2-WuVDnpkrpai6Icun3wXspttadNAxy4djI.png?ex=6a320774&is=6a30b5f4&hm=3f007a0828065da94c7b449d6ae2a1132a1c6f907cd86b32ef5e5255664eb7a5&=&format=webp&quality=lossless&width=700&height=700"
    elif game == "Identity V":
        icon = "https://media.discordapp.net/attachments/1455055877034868769/1516027416198516797/gP6SK4EnELXuvGQWstDib8kmu7IS_TtyxRPfATilagj1PFW7zDfbiU8qn5vaPEju5OUB_NwuaN8qtFZVpPUbng.png?ex=6a31260e&is=6a2fd48e&hm=0a51cab196a17826e467e8730f8460d66a32cd6c2dd8efa230fec7ef1dd5adb9&=&format=webp&quality=lossless&width=700&height=700"
    else:
        return None
    return icon

def default_account_profile(game_uid):
    profile = discord.Embed()
    game, uid = game_uid.split("ㆍ")
    icon = get_game_icon(game)
    if icon: profile.set_thumbnail(url=f"{icon}")
    profile.description = f"**{game}**\n`{uid}`\n-# `{game_uid}`"
    profile.set_footer(text="✦　This account is unreported or invalid.")
    return profile
def reported_account_profile(game_uid, account_profile):
    r_profile_list = account_profile["r_profile_list"]
    no_of_cases = len(account_profile) - 2
    #
    cases = []
    for i in range(1, no_of_cases + 1):
        cases.append(account_profile[str(i)])
    latest_case = cases[-1]
    latest_tags = latest_case["tags"].split(", ")
    all_tags_list = []
    for case in cases:
        all_tags_list.extend(case["tags"].split(", "))
    all_tags_list = sort_account_tags(all_tags_list)
    if "Recovered Account" in latest_tags:
        title = "Recovered Account"
    else:
        title = all_tags_list[0]
    #
    newest_case_tags = cases[-1]["tags"].split(", ")
    newest_case_title = newest_case_tags[0]
    r_profile = format_account_r_profile(game_uid, r_profile_list, title)
    add_case = format_account_add_case(cases[-1], newest_case_title)
    add_case.set_footer(text=f"Page {len(cases)} of {no_of_cases}")
    embeds = [r_profile, add_case]
    return embeds
def sort_account_tags(tags):
    sorted_tags = []
    for tag_to_find in red_account_tags:
        for i in range(0, len(tags)):
            tag = tags[i]
            if tag == tag_to_find:
                sorted_tags.append(tag)
    for tag_to_find in yellow_account_tags:
        for i in range(0, len(tags)):
            tag = tags[i]
            if tag == tag_to_find:
                sorted_tags.append(tag)
    for i in range(0, len(tags)):
        tag = tags[i]
        if tag == "Recovered Account":
            sorted_tags.append(tag)
    return sorted_tags
def format_account_r_profile(game_uid, r_profile_list, title):
    if title == "Recovered Account":
        r_profile = discord.Embed(colour=0x1DCCA9)
        colour = "\u001b[1;32m"
    elif title in red_account_tags:
        r_profile = discord.Embed(colour=0xFF0045)
        colour = "\u001b[1;31m"
    elif title in yellow_account_tags:
        r_profile = discord.Embed(colour=0xFFD643)
        colour = "\u001b[1;33m"
    else:
        r_profile = discord.Embed()
        colour = "\u001b[0m"
    game, uid = game_uid.split("ㆍ")
    icon = get_game_icon(game)
    if icon: r_profile.set_thumbnail(url=f"{icon}")
    r_profile.description = (f"```ansi\n{colour}{title}\u001b[0m\n```")
    r_profile.description += f"**{game}**\n`{uid}`\n-# `{game_uid}`"
    links = []
    for link in r_profile_list[0]:
        game, uid = link.split("ㆍ")
        links.append(f"{game}ㆍ`{uid}`")
    r_profile.description += f"\n**Linked Account(s)**\n{"\n".join(links) or "None"}"
    r_profile.description += f"\n**Other Tag(s)** – {r_profile_list[1] or "None"}"
    return r_profile
def format_account_add_case(add_case_list, case_title):
    if case_title == "Recovered Account":
        add_case = discord.Embed(colour=0x1DCCA9)
    elif case_title in red_account_tags:
        add_case = discord.Embed(colour=0xFF0045)
    elif case_title in yellow_account_tags:
        add_case = discord.Embed(colour=0xFFD643)
    else:
        add_case = discord.Embed()
    if add_case_list:
        add_case.description = f"**{add_case_list["tags"] or "TBC"}**\n"
        add_case.description += "-# **Date Added** – " + add_case_list["date_added"]
        add_case.description += f"\n-# **Related User(s)** – {add_case_list["related_users"] or "None"}"
        add_case.description += f"\n\n**Reason** – {add_case_list["reason"]}\n\u200b"
        add_case.description += f"\n-# **Contributor** – {add_case_list["contributor"]}\n-# **TRI Staff** – {add_case_list["staff"]}\n-# **Accepted by** – {add_case_list["accepted_by"]}"
    return add_case
def format_game_uid(game, uid):
    game = format_game(game)
    if uid.lower().startswith("eu/na") or uid.lower().startswith("euna"):
        uid = uid.lower().replace("eu/na", "EU/NA").replace("euna", "EU/NA")
    elif uid.lower().startswith("asia"):
        uid = uid.lower().replace("asia", "Asia")
    elif uid.lower().startswith("jp"):
        uid = uid.lower().replace("jp", "JP")
    elif uid.lower().startswith("en"):
        uid = uid.lower().replace("en", "EN")
    elif uid.lower().startswith("tw"):
        uid = uid.lower().replace("tw", "TW")
    elif uid.lower().startswith("kr"):
        uid = uid.lower().replace("kr", "KR")
    game_uid = f"{game}ㆍ{uid}"
    return game_uid
def get_game_uid_list(text):
    unique_game_uids = set()
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        match = re.match(r"(.+?)\s+(\S+)$", line)
        if match:
            raw_game = match.group(1).strip()
            raw_uid = match.group(2).strip()
            formatted_result = format_game_uid(raw_game, raw_uid)
            if formatted_result:
                unique_game_uids.add(formatted_result)
    game_uid_list = list(unique_game_uids)
    return game_uid_list

class UnknownGuild:
    icon=None
    banner=None
    name="Unknown"
    created_at=None
    def __init__(self, id):
        self.id = id


@tasks.loop(hours=1.0)
async def update_reports_count():
    reports_count = userscol.count_documents({}) + serverscol.count_documents({}) + accountscol.count_documents({})
    await bot.change_presence(status=discord.Status.dnd,
                              activity=discord.Activity(
                                  type=discord.ActivityType.watching,
                                  name=f"{reports_count} reports."
                              )
                              )


def get_invite_priority_and_expiry(invite: discord.Invite):
    """
    Returns (priority_score, expires_at_timestamp)
    3: Permanent (max_age == 0)
    2: Vanity URL
    1: Temporary (max_age > 0)
    """
    is_vanity_url = False
    if hasattr(invite, 'is_vanity') and callable(invite.is_vanity):
        try:
            is_vanity_url = invite.is_vanity()
        except Exception:
            pass

    if not is_vanity_url and invite.guild and hasattr(invite.guild, 'vanity_url_code'):
        if invite.code == invite.guild.vanity_url_code:
            is_vanity_url = True

    if is_vanity_url:
        return 2, None

    expires_at_ts = None
    if invite.expires_at:
        expires_at_ts = int(invite.expires_at.timestamp())

    max_age = getattr(invite, 'max_age', 0) or 0

    if max_age == 0:
        return 3, None  # Permanent
    else:
        if not expires_at_ts and invite.created_at and max_age:
            expires_at_ts = int((invite.created_at + datetime.timedelta(seconds=max_age)).timestamp())
        return 1, expires_at_ts


@tasks.loop(hours=6.0)
async def process_invites():
    await bot.wait_until_ready()
    log_channel = bot.get_channel(INVITE_LOGS_CHANNEL)
    now_ts = int(discord.utils.utcnow().timestamp())

    all_stored = list(invitescol.find({}))
    for server_doc in all_stored:
        guild_id = server_doc["_id"]
        guild_name = ""
        stored_invites_data = server_doc.get("invites", [])
        valid_invites = []
        removed_invites = []

        for inv_entry in stored_invites_data:
            code = inv_entry if isinstance(inv_entry, str) else inv_entry.get("code")
            expires_at = None if isinstance(inv_entry, str) else inv_entry.get("expires_at")

            if expires_at and now_ts >= expires_at:
                removed_invites.append(code)
                continue
            try:
                invite = await bot.fetch_invite(code)
                if invite.guild and str(invite.guild.id) == guild_id:
                    guild_name = f"{invite.guild.name} "
                    priority, expiry = get_invite_priority_and_expiry(invite)
                    valid_invites.append({
                        "code": code,
                        "priority": priority,
                        "expires_at": expiry
                    })
                else:
                    removed_invites.append(code)
            except (discord.NotFound, discord.HTTPException):
                removed_invites.append(code)
        if removed_invites and log_channel:
            invitescol.update_one({"_id": guild_id}, {"$set": {"invites": valid_invites}})
            await log_channel.send(embed=discord.Embed(description=
                f"**Invites Updated** for {guild_name}`{guild_id}`\n"
                f"> **Removed** – {', '.join([f'`{c}`' for c in removed_invites])}"
            ))

    for guild in bot.guilds:
        await asyncio.sleep(1)
        guild_id_str = str(guild.id)
        stored = {doc["_id"]: doc for doc in all_stored}
        server_doc = stored.get(guild_id_str, {"_id": guild_id_str, "invites": []})
        current_invites = server_doc.get("invites", [])
        current_invites = [{"code": x, "priority": 1, "expires_at": None} if isinstance(x, str) else x for x in
                           current_invites]
        existing_codes = {x["code"] for x in current_invites}

        added_invites = []
        replaced_invites = []

        try:
            if len(current_invites) >= 5:
                continue
            guild_invites = await guild.invites()
            incoming_candidates = []
            for inv in guild_invites:
                if inv.code not in existing_codes:
                    p, exp = get_invite_priority_and_expiry(inv)
                    incoming_candidates.append({"code": inv.code, "priority": p, "expires_at": exp})

            incoming_candidates.sort(key=lambda x: x["priority"], reverse=True)

            for candidate in incoming_candidates:
                if len(current_invites) < 5:
                    current_invites.append(candidate)
                    added_invites.append(candidate["code"])
                else:
                    current_invites.sort(key=lambda x: (x["priority"], -(x["expires_at"] or 9999999999)))
                    lowest_saved = current_invites[0]
                    if candidate["priority"] > lowest_saved["priority"] or (
                            candidate["priority"] == lowest_saved["priority"] and
                            candidate["expires_at"] is not None and lowest_saved["expires_at"] is not None and
                            candidate["expires_at"] > lowest_saved["expires_at"]
                    ):
                        current_invites[0] = candidate
                        replaced_invites.append(f"`{lowest_saved['code']}` <:tri_whitearrow:1523377871480033301> `{candidate['code']}`")

            if len(current_invites) < 5 and guild.text_channels:
                try:
                    new_inv = await guild.text_channels[0].create_invite(max_age=0, max_uses=0, unique=True)
                    if new_inv.code not in {x["code"] for x in current_invites}:
                        p, exp = get_invite_priority_and_expiry(new_inv)
                        current_invites.append({"code": new_inv.code, "priority": p, "expires_at": exp})
                        added_invites.append(new_inv.code)
                except discord.Forbidden:
                    pass

        except discord.Forbidden:
            continue

        if added_invites or replaced_invites:
            invitescol.update_one({"_id": guild_id_str}, {"$set": {"invites": current_invites}}, upsert=True)
            if log_channel:
                msg = f"**Invites Updated** for {guild.name} `{guild_id_str}`\n"
                if added_invites:
                    msg += f"> **Added** – {', '.join([f'`{c}`' for c in added_invites])}\n"
                if replaced_invites:
                    msg += f"> **Replaced** – {', '.join(replaced_invites)}\n"
                await log_channel.send(embed=discord.Embed(description=msg))


async def process_and_save_invite(invite: discord.Invite):
    if not invite.guild:
        return

    log_channel = bot.get_channel(INVITE_LOGS_CHANNEL)
    guild_id_str = str(invite.guild.id)
    server_doc = invitescol.find_one({"_id": guild_id_str}) or {"_id": guild_id_str, "invites": []}
    current_invites = server_doc.get("invites", [])

    current_invites = [{"code": x, "priority": 1, "expires_at": None} if isinstance(x, str) else x for x in
                       current_invites]

    if any(x["code"] == invite.code for x in current_invites):
        return

    try:
        p, exp = get_invite_priority_and_expiry(invite)
    except Exception:
        p, exp = 1, None

    candidate = {"code": invite.code, "priority": p, "expires_at": exp}

    added = False
    replaced_code = None

    if len(current_invites) < 5:
        current_invites.append(candidate)
        added = True
    else:
        current_invites.sort(key=lambda x: (x["priority"], -(x["expires_at"] or 9999999999)))
        lowest_saved = current_invites[0]

        if candidate["priority"] > lowest_saved["priority"] or (
                candidate["priority"] == lowest_saved["priority"] and
                candidate["expires_at"] is not None and lowest_saved["expires_at"] is not None and
                candidate["expires_at"] > lowest_saved["expires_at"]
        ):
            replaced_code = lowest_saved["code"]
            current_invites[0] = candidate
            added = True

    if added:
        invitescol.update_one({"_id": guild_id_str}, {"$set": {"invites": current_invites}}, upsert=True)
        if log_channel:
            msg = f"**Invites Updated** for {invite.guild.name} `{guild_id_str}`\n"
            if replaced_code:
                msg += f"> **Replaced** – `{replaced_code}` <:tri_whitearrow:1523377871480033301> `{invite.code}`"
            else:
                msg += f"> **Added** – `{invite.code}`"
            await log_channel.send(embed=discord.Embed(description=msg))


@bot.event
async def on_ready():
    if not update_reports_count.is_running():
        update_reports_count.start()
    if not update_scam_domains.is_running():
        update_scam_domains.start()
    if not process_invites.is_running():
        process_invites.start()


CHAINS = {
    "btc": "bitcoin",
    "bitcoin": "bitcoin",

    "ltc": "litecoin",
    "litecoin": "litecoin",

    "eth": "ethereum",
    "ethereum": "ethereum",

    "doge": "dogecoin",
    "dogecoin": "dogecoin",

    "bch": "bitcoin-cash",
    "bitcoincash": "bitcoin-cash",

    "dash": "dash",

    "xrp": "ripple",
    "ripple": "ripple",

    "trx": "tron",
    "tron": "tron",

    "matic": "polygon",
    "polygon": "polygon",

    "arb": "arbitrum",
    "arbitrum": "arbitrum",

    "op": "optimism",
    "optimism": "optimism",

    "base": "base",

    "avax": "avalanche",
    "avalanche": "avalanche",

    "bnb": "binance-smart-chain",
    "bsc": "binance-smart-chain",

    "sol": "solana",
    "solana": "solana"
}

COINGECKO_IDS = {
    "bitcoin": "bitcoin",
    "litecoin": "litecoin",
    "ethereum": "ethereum",
    "dogecoin": "dogecoin",
    "bitcoin-cash": "bitcoin-cash",
    "dash": "dash",
    "ripple": "ripple",
    "tron": "tron",
    "polygon": "matic-network",
    "arbitrum": "ethereum",
    "optimism": "ethereum",
    "base": "ethereum",
    "binance-smart-chain": "binancecoin",
    "avalanche": "avalanche-2",
    "solana": "solana"
}

SYMBOLS = {
    "bitcoin": "BTC",
    "litecoin": "LTC",
    "ethereum": "ETH",
    "dogecoin": "DOGE",
    "bitcoin-cash": "BCH",
    "dash": "DASH",
    "ripple": "XRP",
    "tron": "TRX",
    "polygon": "POL",
    "arbitrum": "ETH",
    "optimism": "ETH",
    "base": "ETH",
    "binance-smart-chain": "BNB",
    "avalanche": "AVAX",
    "solana": "SOL",
}

DECIMALS = {
    "bitcoin": 8,
    "litecoin": 8,
    "ethereum": 18,
    "dogecoin": 8,
    "bitcoin-cash": 8,
    "dash": 8,
    "ripple": 6,
    "tron": 6,
    "polygon": 18,
    "arbitrum": 18,
    "optimism": 18,
    "base": 18,
    "binance-smart-chain": 18,
    "avalanche": 18,
    "solana": 9,
}


@bot.command()
async def txid(ctx, chain: str, txid: str):
    chain = CHAINS.get(chain.lower())
    if chain is None:
        return await ctx.send("Unsupported cryptocurrency.")
    url = f"https://api.blockchair.com/{chain}/dashboards/transaction/{txid}"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status != 200:
                return await ctx.send("Transaction not found.")
            data = await resp.json()
    if "data" not in data or txid not in data["data"]:
        return await ctx.send("Transaction not found.")
    tx = data["data"][txid]
    transaction = tx["transaction"]

    inputs = tx.get("inputs", [])
    outputs = sorted(
        tx.get("outputs", []),
        key=lambda x: x.get("value", 0),
        reverse=True
    )
    senders = list(dict.fromkeys(
        i["recipient"]
        for i in inputs
        if i.get("recipient")
    ))
    recipients = []
    largest_value = outputs[0]["value"] if outputs else 0
    for o in outputs:
        if not o.get("recipient"):
            continue
        label = ""
        if o["value"] == largest_value:
            label = " <:tri_whitestar2:1525772163930390548>"
        recipients.append((o["recipient"], label))
    decimals = DECIMALS.get(chain, 18)
    symbol = SYMBOLS.get(chain, chain.upper())
    amount = transaction["output_total"] / (10 ** decimals)
    fee = transaction["fee"] / (10 ** decimals)
    block_time = transaction["time"]
    unix = int(datetime.datetime.fromisoformat(block_time).timestamp())

    historical_price = None
    current_price = None
    coin = COINGECKO_IDS.get(chain)
    if coin:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                        f"https://api.coingecko.com/api/v3/simple/price?ids={coin}&vs_currencies=usd"
                ) as r:
                    current = await r.json()
                    current_price = current[coin]["usd"]
                frm = unix - 1800
                to = unix + 1800
                async with session.get(
                        f"https://api.coingecko.com/api/v3/coins/{coin}/market_chart/range",
                        params={
                            "vs_currency": "usd",
                            "from": frm,
                            "to": to
                        }
                ) as r:
                    history = await r.json()
                    if history.get("prices"):
                        historical_price = history["prices"][0][1]
        except Exception:
            pass
    worth_then = (
        f"${amount * historical_price:,.2f}"
        if historical_price
        else "Unknown"
    )
    worth_now = (
        f"${amount * current_price:,.2f}"
        if current_price
        else "Unknown"
    )

    embed = discord.Embed(title=f"{symbol} Transaction", colour=0xffffff)
    embed.add_field(
        name="Hash",
        value=f"`{txid}`",
        inline=False
    )
    embed.add_field(
        name="Status",
        value="Confirmed" if transaction["block_id"] else "Unconfirmed",
        inline=True
    )
    embed.add_field(
        name="Confirmations",
        value=transaction.get("confirmations", "Unknown"),
        inline=True
    )
    embed.add_field(
        name="Block",
        value=transaction.get("block_id", "Pending"),
        inline=True
    )
    embed.add_field(
        name="Confirmed",
        value=f"<t:{unix}:F>",
        inline=True
    )
    embed.add_field(
        name="Amount",
        value=f"{amount:,.8f}".rstrip("0").rstrip(".") + f" {symbol}",
        inline=True
    )
    embed.add_field(
        name="Fee",
        value=f"{fee:,.8f}".rstrip("0").rstrip(".") + f" {symbol}",
        inline=True
    )
    embed.add_field(
        name="Worth Then",
        value=worth_then,
        inline=True
    )
    embed.add_field(
        name="Worth Now",
        value=worth_now,
        inline=True
    )
    embed.add_field(
        name="Sender(s)",
        value="\n".join(
            f"`{x}`"
            for x in senders[:5]
        ) or "Unknown",
        inline=False
    )
    embed.add_field(
        name="Recipient(s)",
        value="\n".join(
            f"`{addr}`{label}"
            for addr, label in recipients[:5]
        ) or "Unknown",
        inline=False
    )
    embed.add_field(
        name="Explorer",
        value=f"https://blockchair.com/{chain}/transaction/{txid}",
        inline=False
    )
    await ctx.reply(embed=embed)

# check

async def fetch_worker(raw_user):
    user_id = re.sub(r"\D", "", raw_user)
    if not (17 <= len(user_id) <= 20):
        return None, None

    user_id_int = int(user_id)

    cached_user = bot.get_user(user_id_int)
    if cached_user:
        return cached_user, None

    try:
        fetched_user = await bot.fetch_user(user_id_int)
        return fetched_user, None
    except discord.NotFound:
        return None, raw_user
    except discord.HTTPException:
        return None, None

@bot.command(name="c", help="Checks a user or server.")
async def c(ctx, *, to_check: str = None):
    if ctx.guild.id == TRI_Archive:
        teto = ctx.guild.get_member(1450073025818136598)
        if not teto.status == discord.Status.offline:
            return

    requested_by = ctx.author
    game_input, uid_input, game = None, None, None
    has_space = to_check and " " in to_check.strip()
    log_channel = bot.get_channel(INVITE_LOGS_CHANNEL)

    if to_check:
        to_check = to_check.strip()
        match = re.match(r"(.+?)\s+(\S+)$", to_check)
        if match:
            game_input = match.group(1).strip()
            uid_input = match.group(2).strip()
            game = format_game(game_input)

    if game is not None and uid_input is not None:
        game_uid = format_game_uid(game, uid_input)
        account_profile = accountscol.find_one({"_id": str(game_uid)})

        if account_profile:
            if len(account_profile) == 2:
                main = account_profile['main']
                main_profile = accountscol.find_one({"_id": main})
                return await ctx.reply(
                    f"Account `{game_uid}` is linked to `{main}`.",
                    embeds=reported_account_profile(main, main_profile),
                    view=ReportedAccountView(main, main_profile, requested_by, len(main_profile) - 2)
                )
            else:
                return await ctx.reply(
                    "Account is reported.",
                    embeds=reported_account_profile(game_uid, account_profile),
                    view=ReportedAccountView(game_uid, account_profile, requested_by, len(account_profile) - 2)
                )
        else:
            return await ctx.reply(embed=default_account_profile(game_uid), view=MemberView())

    target_raw = to_check if to_check else str(ctx.author.id)

    fetched_invite_guild = None
    if not target_raw.strip().isdigit() and not (target_raw.startswith('<@') and target_raw.endswith('>')):
        try:
            invite_code = target_raw.strip()
            cleaned_url = re.sub(r'(https?://)?(www\.)?(discord\.gg|discord\.com/invite)/', '', invite_code).strip()
            if cleaned_url:
                invite_code = cleaned_url.split('/')[0]

            invite = await bot.fetch_invite(invite_code, with_counts=True)
            fetched_invite_guild = invite.guild

            await process_and_save_invite(invite)
        except Exception:
            pass

    clean_text = re.sub(r"<a?:\w+:\d+>", "", target_raw)

    tokens = clean_text.split()
    first_valid_id = None
    target_user = None
    is_reported_server_id = False

    for token in tokens:
        cleaned_token = re.sub(r"\D", "", token)
        if 17 <= len(cleaned_token) <= 20:

            fetched, _ = await fetch_worker(cleaned_token)
            if fetched:
                first_valid_id = cleaned_token
                target_user = fetched
                break

            if serverscol.find_one({"_id": cleaned_token}):
                first_valid_id = cleaned_token
                is_reported_server_id = True
                break

    if has_space and not first_valid_id:
        return await ctx.reply(f"The game {game_input} is **invalid** or **unsupported**.")

    worker_input = first_valid_id if first_valid_id else target_raw
    if not target_user and not is_reported_server_id:
        target_user, _ = await fetch_worker(worker_input)

    if target_user and target_user.id in tri_bots:
        profile = discord.Embed(colour=0xffffff, title=target_user.display_name)
        profile.set_thumbnail(url=f"{target_user.display_avatar.url}")
        profile.description = f"`{target_user.id}`\n{target_user.mention}\n`{target_user.name}`\n"
        profile.description += f"\n-# **Account Created** – <t:{round(target_user.created_at.timestamp())}:D> (<t:{round(target_user.created_at.timestamp())}:R>)\n"

        bot_desc = {
            1450073025818136598: "\n**TETO** ┈ report bot for `/tri`",
            1457249982104211467: "\n**TETO++** ┈ user check bot for `/tri`",
            1457382953293320304: "\n**NERU** ┈ alts check bot for `/tri`",
            1457309787044839477: "\n**MIKU** ┈ tickets bot for `/tri`"
        }
        profile.description += bot_desc.get(target_user.id, "")
        profile.set_footer(text="✦　TRI bot")
        return await ctx.reply(embed=profile)

    if is_reported_server_id or fetched_invite_guild or not target_user:
        server_id = worker_input.strip('<@>')
        guild = None

        if fetched_invite_guild:
            guild = fetched_invite_guild
            server_id = str(guild.id)
        elif not server_id.isdigit():
            try:
                invite_code = target_raw.strip()
                cleaned_url = re.sub(r'(https?://)?(www\.)?(discord\.gg|discord\.com/invite)/', '', invite_code).strip()
                if cleaned_url:
                    invite_code = cleaned_url.split('/')[0]

                invite = await bot.fetch_invite(invite_code, with_counts=True)
                guild = invite.guild
                server_id = str(guild.id)
                await process_and_save_invite(invite)
            except Exception:
                return await ctx.send("The invite link is **invalid** or **expired**.")
        else:
            server_doc = invitescol.find_one({"_id": server_id})
            if server_doc and server_doc.get("invites"):
                valid_invites = []
                removed_invites = []
                now_ts = int(discord.utils.utcnow().timestamp())

                for inv_entry in server_doc["invites"]:
                    code = inv_entry if isinstance(inv_entry, str) else inv_entry.get("code")
                    expires_at = None if isinstance(inv_entry, str) else inv_entry.get("expires_at")

                    if expires_at and now_ts >= expires_at:
                        removed_invites.append(code)
                        continue
                    try:
                        invite = await bot.fetch_invite(code, with_counts=True)
                        if invite.guild and str(invite.guild.id) == server_id:
                            p, exp = get_invite_priority_and_expiry(invite)
                            valid_invites.append({"code": code, "priority": p, "expires_at": exp})
                            if not guild:
                                guild = invite.guild
                        else:
                            removed_invites.append(code)
                    except (discord.NotFound, discord.HTTPException):
                        removed_invites.append(code)

                invitescol.update_one({"_id": server_id}, {"$set": {"invites": valid_invites}})
                guild_name = f"{guild.name} " if guild and not isinstance(guild, UnknownGuild) else ""
                if removed_invites and log_channel:
                    await log_channel.send(embed=discord.Embed(description=
                        f"**Invites Updated** for {guild_name}`{server_id}`\n"
                        f"> **Removed** – {', '.join([f'`{c}`' for c in removed_invites])}"
                    ))

            if not guild:
                guild = bot.get_guild(int(server_id)) or UnknownGuild(int(server_id))

        server_profile = serverscol.find_one({"_id": server_id})
        if trustedserverscol.find_one({"_id": server_id}):
            return await ctx.reply("Server is trusted.", embed=format_trustedserver_profile(guild))
        elif server_profile:
            return await ctx.reply(
                "Server is reported.",
                embeds=reported_server_profile(guild, server_profile),
                view=ReportedServerView(guild, server_profile, requested_by, len(server_profile) - 2)
            )
        else:
            if server_id.isdigit() and (not guild or isinstance(guild, UnknownGuild)):
                return await ctx.reply(
                    "Please provide a valid user ID. To check servers, please provide a valid invite link.")
            return await ctx.reply(embed=default_server_profile(guild), view=MemberView())

    user_id_str = str(target_user.id) if target_user else str(worker_input.strip('<@>'))
    trusteduser_profile = trusteduserscol.find_one({"_id": user_id_str})

    if trusteduser_profile and not (
            trusteduser_profile.get("current_staff", 0) == 0 and trusteduser_profile.get("staff", 0) == 0 and
            trusteduser_profile.get("mm", 0) == 0 and trusteduser_profile.get("pilot", 0) == 0 and
            trusteduser_profile.get("trader", 0) == 0):
        return await ctx.reply("User is trusted.", embed=format_trusteduser_profile(target_user, trusteduser_profile))

    user_profile = userscol.find_one({"_id": user_id_str})
    if user_profile:
        if len(user_profile) == 2:
            main = user_profile['main']
            main_user_profile = userscol.find_one({"_id": main})
            main_user, _ = await fetch_worker(main)
            if not main_user:
                try:
                    main_user = await bot.fetch_user(int(main))
                except Exception:
                    main_user = target_user

            return await ctx.reply(
                f"User `{user_id_str}` is reported as alt of `{main}`.",
                embeds=reported_user_profile(main_user, main_user_profile),
                view=ReportedUserView(main_user, main_user_profile, requested_by, len(main_user_profile) - 2)
            )
        else:
            return await ctx.reply(
                "User is reported.",
                embeds=reported_user_profile(target_user, user_profile),
                view=ReportedUserView(target_user, user_profile, requested_by, len(user_profile) - 2)
            )
    else:
        return await ctx.reply(embed=default_user_profile(target_user), view=MemberView())

@bot.command(name="ca", help="Checks a user’s alts and profile data.")
async def ca(ctx, *, to_check: str = None):
    if ctx.guild.id == TRI_Archive:
        teto = ctx.guild.get_member(1450073025818136598)
        if not teto.status == discord.Status.offline:
            return

    requested_by = ctx.author

    target_user = None
    if to_check:
        clean_text = re.sub(r"<a?:\w+:\d+>", "", to_check.strip())
        cleaned_token = re.sub(r"\D", "", clean_text)

        if 17 <= len(cleaned_token) <= 20:
            target_user, _ = await fetch_worker(cleaned_token)
            user_id_str = cleaned_token
        else:
            user_id_str = clean_text
    else:
        target_user = ctx.author
        user_id_str = str(ctx.author.id)

    if not target_user and user_id_str.isdigit():
        try:
            target_user = await bot.fetch_user(int(user_id_str))
        except Exception:
            pass

    if not target_user:
        return await ctx.reply("Please provide a valid user ID or mention.")

    alts_info = altscol.find_one({"_id": user_id_str})
    alts_embed = discord.Embed(colour=0xffffff)
    if alts_info and alts_info.get("alts"):
        raw_ids = " ".join(alt for alt in alts_info.get("alts", []))
        alts_embed.description = f"<a:tri_whitealert:1496542298908000257> **Alt(s)** of `{target_user.id}`\n\n`{raw_ids}`"
    else:
        alts_embed.description = "<:tri_whitecross:1462774085737119828>　No alts logged for this user."

    await ctx.reply(embed=alts_embed)

    trusteduser_profile = trusteduserscol.find_one({"_id": user_id_str})
    if trusteduser_profile and not (
            trusteduser_profile.get("current_staff", 0) == 0 and trusteduser_profile.get("staff", 0) == 0 and
            trusteduser_profile.get("mm", 0) == 0 and trusteduser_profile.get("pilot", 0) == 0 and
            trusteduser_profile.get("trader", 0) == 0):
        return await ctx.send("User is trusted.", embed=format_trusteduser_profile(target_user, trusteduser_profile))

    user_profile = userscol.find_one({"_id": user_id_str})
    if user_profile:
        if len(user_profile) == 2:
            main = user_profile['main']
            main_user_profile = userscol.find_one({"_id": main})
            main_user, _ = await fetch_worker(main)
            if not main_user:
                try:
                    main_user = await bot.fetch_user(int(main))
                except Exception:
                    main_user = target_user

            msg = f"User `{user_id_str}` is reported as alt of `{main}`."
            view = ReportedUserView(main_user, main_user_profile, requested_by, len(main_user_profile) - 2)
            return await ctx.send(msg, embeds=reported_user_profile(main_user, main_user_profile), view=view)
        else:
            view = ReportedUserView(target_user, user_profile, requested_by, len(user_profile) - 2)
            return await ctx.send("User is reported.", embeds=reported_user_profile(target_user, user_profile),
                                   view=view)

    else:
        profile = default_user_profile(target_user)
        view = MemberView()
        return await ctx.send(embed=profile, view=view)


@bot.command(name='mc', help='Checks a list of users (max 100), leave a space between users.')
async def mc(ctx, *, to_check: str = None):
    if to_check is None:
        return

    if ctx.guild.id == TRI_Archive:
        teto = ctx.guild.get_member(1450073025818136598)
        if not teto.status == discord.Status.offline:
            return

    users = to_check.split()
    valid_users = []
    invalid_users = []

    results = await asyncio.gather(*(fetch_worker(u) for u in users))

    for fetched_user, invalid_raw in results:
        if fetched_user and fetched_user not in valid_users:
            valid_users.append(fetched_user)
        if invalid_raw and invalid_raw not in invalid_users:
            invalid_users.append(invalid_raw)

    if len(valid_users) + len(invalid_users) > 100:
        return await ctx.reply("Exceeded 100 users.")

    status_message = await ctx.reply(
        f"_Checking **{len(valid_users)}** users..._")
    if not valid_users:
        await status_message.delete()
        if invalid_users:
            await ctx.send(f"Invalid: {' '.join([f'`{u}`' for u in invalid_users])}")
        return await ctx.reply("No valid user IDs provided.")

    processed_ids = set()
    processed_mains = set()

    message_batches = []
    current_content = []
    current_embeds = []

    for user in valid_users:
        current_id = str(user.id)

        if current_id in processed_ids:
            continue
        processed_ids.add(current_id)

        if len(current_embeds) == 10 or len(current_content) == 10:
            message_batches.append(("\n".join(current_content), current_embeds))
            current_content = []
            current_embeds = []

        user_query = {"_id": current_id}
        trusteduser_profile = trusteduserscol.find_one(user_query)

        if trusteduser_profile and not (
                trusteduser_profile["current_staff"] == 0 and trusteduser_profile["staff"] == 0 and
                trusteduser_profile["mm"] == 0 and trusteduser_profile["pilot"] == 0 and
                trusteduser_profile["trader"] == 0):

            trusted_embed = format_trusteduser_profile(user, trusteduser_profile)
            current_embeds.append(trusted_embed)
            current_content.append(f"<:tri_whiteheart:1434538078747365507> `{current_id}` is trusted.")
        else:
            user_profile = userscol.find_one(user_query)
            if user_profile:
                is_alt = len(user_profile) == 2
                target_profile = user_profile
                main_id_str = ""
                already_processed_embed = False

                if is_alt:
                    main = user_profile['main']
                    if main in processed_mains:
                        already_processed_embed = True
                    else:
                        processed_mains.add(main)

                    target_profile = userscol.find_one({"_id": main}) or {}
                    try:
                        main_user = await bot.fetch_user(int(main))
                        user = main_user
                        main_id_str = str(main_user.id)
                    except discord.HTTPException:
                        main_id_str = str(main)

                no_of_cases = len(target_profile) - 2 if target_profile else 0

                all_tags_list = []
                for i in range(1, no_of_cases + 1):
                    case = target_profile.get(str(i))
                    if case and len(case) > 2:
                        all_tags_list.extend(case["tags"].split(", "))

                all_tags_list = sort_user_tags(all_tags_list)
                all_unique_tags = list(dict.fromkeys(all_tags_list))

                if is_alt:
                    current_content.append(
                        f"<a:tri_whitealert:1496542298908000257> **`{current_id}` (alt of `{main_id_str}`) is reported as {selected_string(all_unique_tags)}.**")
                else:
                    current_content.append(
                        f"<a:tri_whitealert:1496542298908000257> **`{current_id}` is reported as {selected_string(all_unique_tags)}.**")

                if already_processed_embed:
                    continue

                r_profile_list = target_profile.get("r_profile_list", [])
                title = all_unique_tags[0] if all_unique_tags else "Reported"
                r_profile = format_user_r_profile(user, r_profile_list, title)
                current_embeds.append(r_profile)
            else:
                profile = default_user_profile(user)
                current_embeds.append(profile)
                current_content.append(f"<:tri_whitedot:1462907474947342567> `{current_id}` is unreported.")

    if current_content or current_embeds:
        message_batches.append(("\n".join(current_content), current_embeds))

    for idx, (content, embeds_chunk) in enumerate(message_batches):
        if idx == 0:
            await status_message.edit(content=content, embeds=embeds_chunk)
        else:
            await ctx.send(content=content, embeds=embeds_chunk)

    if invalid_users:
        invalid_formatted = " ".join([f"`{user}`" for user in invalid_users])
        await ctx.send(content=f"Invalid: {invalid_formatted}")

class ReportedUserView(discord.ui.View):
    def __init__(self, user, user_profile, requested_by, current_case):
        super().__init__(timeout=3600)
        self.user = user
        self.user_profile = user_profile
        self.requested_by = requested_by
        self.current_case = current_case

    @discord.ui.button(emoji="<:leftarrow:1457259860050706505>", style=discord.ButtonStyle.grey, custom_id="prev")
    async def prev_button(self, interaction, button):
        await interaction.response.defer()
        #
        user = self.user
        user_profile = self.user_profile
        requested_by = self.requested_by
        current_case = self.current_case
        #
        no_of_cases = len(user_profile) - 2
        if requested_by == interaction.user:
            r_profile_list = user_profile["r_profile_list"]
            cases = []
            for i in range(1, no_of_cases + 1):
                cases.append(user_profile[str(i)])
            tags_strings = []
            all_tags_list = []
            for case in cases:
                tags_strings.append(case["tags"])
            for tags_string in tags_strings:
                tags_list = tags_string.split(", ")
                for tag in tags_list:
                    all_tags_list.append(tag)
            all_tags_list = sort_user_tags(all_tags_list)
            title = all_tags_list[0]
            if current_case != 1:
                prev_index = current_case-2
            try:
                prev_case_tags = cases[prev_index]["tags"].split(", ")
            except Exception:
                pass
            else:
                prev_case_title = prev_case_tags[0]
                r_profile = format_user_r_profile(user, r_profile_list, title)
                add_case = format_user_add_case(cases[prev_index], prev_case_title)
                #
                current_case -= 1
                self.current_case = current_case
                add_case.set_footer(text=f"Page {current_case} of {no_of_cases}")
                embeds = [r_profile, add_case]
                await interaction.edit_original_response(content="User is reported.", embeds=embeds,
                                                   view=ReportedUserView(user, user_profile, requested_by,
                                                                       current_case))

    @discord.ui.button(emoji="<:rightarrow:1457259988048412815>", style=discord.ButtonStyle.grey, custom_id="next")
    async def next_button(self, interaction, button):
        await interaction.response.defer()
        #
        user = self.user
        user_profile = self.user_profile
        requested_by = self.requested_by
        current_case = self.current_case
        #
        no_of_cases = len(user_profile) - 2
        if requested_by == interaction.user:
            r_profile_list = user_profile["r_profile_list"]
            cases = []
            for i in range(1, no_of_cases + 1):
                cases.append(user_profile[str(i)])
            tags_strings = []
            all_tags_list = []
            for case in cases:
                tags_strings.append(case["tags"])
            for tags_string in tags_strings:
                tags_list = tags_string.split(", ")
                for tag in tags_list:
                    all_tags_list.append(tag)
            all_tags_list = sort_user_tags(all_tags_list)
            title = all_tags_list[0]
            next_index = current_case
            try:
                next_case_tags = cases[next_index]["tags"].split(", ")
            except Exception:
                pass
            else:
                next_case_title = next_case_tags[0]
                r_profile = format_user_r_profile(user, r_profile_list, title)
                add_case = format_user_add_case(cases[next_index], next_case_title)
                #
                current_case += 1
                self.current_case = current_case
                add_case.set_footer(text=f"Page {current_case} of {no_of_cases}")
                embeds = [r_profile, add_case]
                await interaction.edit_original_response(content="User is reported.", embeds=embeds,
                                                   view=ReportedUserView(user, user_profile, requested_by,
                                                                  current_case))

    @discord.ui.button(label="Proofs", style=discord.ButtonStyle.grey, custom_id="see_proofs")
    async def proofs_button(self, interaction, button):
        await interaction.response.defer()
        #
        user = self.user
        user_profile = self.user_profile
        requested_by = self.requested_by
        current_case = self.current_case
        #
        if requested_by == interaction.user:
            r_profile_list = user_profile["r_profile_list"]
            no_of_cases = len(user_profile) - 2
            cases = []
            for i in range(1, no_of_cases + 1):
                cases.append(user_profile[str(i)])
            image_links = cases[current_case-1]["proofs"]
            image_embeds = image_links_to_embeds(image_links)
            await interaction.followup.send(f"Proofs for `{user.id}`", embeds=image_embeds, ephemeral=True)

    @discord.ui.button(label="Alts", style=discord.ButtonStyle.grey, custom_id="see_alts_proofs")
    async def alts_proofs_button(self, interaction, button):
        await interaction.response.defer()
        #
        user = self.user
        user_profile = self.user_profile
        requested_by = self.requested_by
        current_case = self.current_case
        #
        if requested_by == interaction.user:
            r_profile_list = user_profile["r_profile_list"]
            image_links = r_profile_list[2]
            image_embeds = image_links_to_embeds(image_links)
            await interaction.followup.send(f"Alts Proofs for `{user.id}`", embeds=image_embeds, ephemeral=True)

class ReportedServerView(discord.ui.View):
    def __init__(self, guild, server_profile, requested_by, current_case):
        super().__init__(timeout=3600)
        self.guild = guild
        self.server_profile = server_profile
        self.requested_by = requested_by
        self.current_case = current_case

    @discord.ui.button(emoji="<:leftarrow:1458096658062770176>", style=discord.ButtonStyle.grey, custom_id="prev")
    async def prev_button(self, interaction, button):
        await interaction.response.defer()
        #
        guild = self.guild
        server_profile = self.server_profile
        requested_by = self.requested_by
        current_case = self.current_case
        #
        no_of_cases = len(server_profile) - 2
        if requested_by == interaction.user:
            r_profile_list = server_profile["r_profile_list"]
            cases = []
            for i in range(1, no_of_cases + 1):
                cases.append(server_profile[str(i)])
            tags_strings = []
            all_tags_list = []
            for case in cases:
                tags_strings.append(case["tags"])
            for tags_string in tags_strings:
                tags_list = tags_string.split(", ")
                for tag in tags_list:
                    all_tags_list.append(tag)
            all_tags_list = sort_server_tags(all_tags_list)
            title = all_tags_list[0]
            if current_case != 1:
                prev_index = current_case - 2
            try:
                prev_case_tags = cases[prev_index]["tags"].split(", ")
            except Exception:
                pass
            else:
                prev_case_title = prev_case_tags[0]
                r_profile = format_server_r_profile(guild, r_profile_list, title)
                add_case = format_server_add_case(cases[prev_index], prev_case_title)
                #
                current_case -= 1
                self.current_case = current_case
                add_case.set_footer(text=f"Page {current_case} of {no_of_cases}")
                embeds = [r_profile, add_case]
                await interaction.edit_original_response(content="Server is reported.", embeds=embeds,
                                                         view=ReportedServerView(guild, server_profile, requested_by,
                                                                               current_case))

    @discord.ui.button(emoji="<:rightarrow:1458096774521553038>", style=discord.ButtonStyle.grey, custom_id="next")
    async def next_button(self, interaction, button):
        await interaction.response.defer()
        #
        guild = self.guild
        server_profile = self.server_profile
        requested_by = self.requested_by
        current_case = self.current_case
        #
        no_of_cases = len(server_profile) - 2
        if requested_by == interaction.user:
            r_profile_list = server_profile["r_profile_list"]
            cases = []
            for i in range(1, no_of_cases + 1):
                cases.append(server_profile[str(i)])
            tags_strings = []
            all_tags_list = []
            for case in cases:
                tags_strings.append(case["tags"])
            for tags_string in tags_strings:
                tags_list = tags_string.split(", ")
                for tag in tags_list:
                    all_tags_list.append(tag)
            all_tags_list = sort_server_tags(all_tags_list)
            title = all_tags_list[0]
            next_index = current_case
            try:
                next_case_tags = cases[next_index]["tags"].split(", ")
            except Exception:
                pass
            else:
                next_case_title = next_case_tags[0]
                r_profile = format_server_r_profile(guild, r_profile_list, title)
                add_case = format_server_add_case(cases[next_index], next_case_title)
                #
                current_case += 1
                self.current_case = current_case
                add_case.set_footer(text=f"Page {current_case} of {no_of_cases}")
                embeds = [r_profile, add_case]
                await interaction.edit_original_response(content="Server is reported.", embeds=embeds,
                                                         view=ReportedServerView(guild, server_profile, requested_by,
                                                                               current_case))

    @discord.ui.button(label="Proofs", style=discord.ButtonStyle.grey, custom_id="see_proofs")
    async def proofs_button(self, interaction, button):
        await interaction.response.defer()
        #
        guild = self.guild
        server_profile = self.server_profile
        current_case = self.current_case
        #
        no_of_cases = len(server_profile) - 2
        cases = []
        for i in range(1, no_of_cases + 1):
            cases.append(server_profile[str(i)])
        image_links = cases[current_case - 1]["proofs"]
        image_embeds = image_links_to_embeds(image_links)
        await interaction.followup.send(f"Proofs for `{guild.id}`", embeds=image_embeds, ephemeral=True)

# reported account
class ReportedAccountView(discord.ui.View):
    def __init__(self, game_uid, account_profile, requested_by, current_case):
        super().__init__(timeout=3600)
        self.game_uid = game_uid
        self.account_profile = account_profile
        self.requested_by = requested_by
        self.current_case = current_case

    @discord.ui.button(emoji="<:leftarrow:1458096658062770176>", style=discord.ButtonStyle.grey, custom_id="reportedaccount:prev")
    async def prev_button(self, interaction, button):
        await interaction.response.defer()
        #
        game_uid = self.game_uid
        account_profile = self.account_profile
        requested_by = self.requested_by
        current_case = self.current_case
        #
        no_of_cases = len(account_profile) - 2
        if requested_by == interaction.user:
            r_profile_list = account_profile["r_profile_list"]
            cases = []
            for i in range(1, no_of_cases + 1):
                cases.append(account_profile[str(i)])
            latest_case = cases[-1]
            latest_tags = latest_case["tags"].split(", ")
            all_tags_list = []
            for case in cases:
                all_tags_list.extend(case["tags"].split(", "))
            all_tags_list = sort_account_tags(all_tags_list)
            if "Recovered Account" in latest_tags:
                title = "Recovered Account"
            else:
                title = all_tags_list[0]
            if current_case != 1:
                prev_index = current_case - 2
                try:
                    prev_case_tags = cases[prev_index]["tags"].split(", ")
                except Exception:
                    pass
                else:
                    prev_case_title = prev_case_tags[0]
                    r_profile = format_account_r_profile(game_uid, r_profile_list, title)
                    add_case = format_account_add_case(cases[prev_index], prev_case_title)
                    #
                    current_case -= 1
                    self.current_case = current_case
                    add_case.set_footer(text=f"Page {current_case} of {no_of_cases}")
                    embeds = [r_profile, add_case]
                    await interaction.edit_original_response(content="Account is reported.", embeds=embeds,
                                                             view=ReportedAccountView(game_uid, account_profile, requested_by,
                                                                                   current_case))

    @discord.ui.button(emoji="<:rightarrow:1458096774521553038>", style=discord.ButtonStyle.grey, custom_id="reportedaccount:next")
    async def next_button(self, interaction, button):
        await interaction.response.defer()
        #
        game_uid = self.game_uid
        account_profile = self.account_profile
        requested_by = self.requested_by
        current_case = self.current_case
        #
        no_of_cases = len(account_profile) - 2
        if requested_by == interaction.user:
            r_profile_list = account_profile["r_profile_list"]
            cases = []
            for i in range(1, no_of_cases + 1):
                cases.append(account_profile[str(i)])
            latest_case = cases[-1]
            latest_tags = latest_case["tags"].split(", ")
            all_tags_list = []
            for case in cases:
                all_tags_list.extend(case["tags"].split(", "))
            all_tags_list = sort_account_tags(all_tags_list)
            if "Recovered Account" in latest_tags:
                title = "Recovered Account"
            else:
                title = all_tags_list[0]
            next_index = current_case
            try:
                next_case_tags = cases[next_index]["tags"].split(", ")
            except Exception:
                pass
            else:
                next_case_title = next_case_tags[0]
                r_profile = format_account_r_profile(game_uid, r_profile_list, title)
                add_case = format_account_add_case(cases[next_index], next_case_title)
                #
                current_case += 1
                self.current_case = current_case
                add_case.set_footer(text=f"Page {current_case} of {no_of_cases}")
                embeds = [r_profile, add_case]
                await interaction.edit_original_response(content="Account is reported.", embeds=embeds,
                                                         view=ReportedAccountView(game_uid, account_profile, requested_by,
                                                                               current_case))

    @discord.ui.button(label="Proofs", style=discord.ButtonStyle.grey, custom_id="reportedaccount:proofs")
    async def proofs_button(self, interaction, button):
        await interaction.response.defer()
        #
        game_uid = self.game_uid
        account_profile = self.account_profile
        current_case = self.current_case
        #
        no_of_cases = len(account_profile) - 2
        cases = []
        for i in range(1, no_of_cases + 1):
            cases.append(account_profile[str(i)])
        image_links = cases[current_case - 1]["proofs"]
        image_embeds = image_links_to_embeds(image_links)
        await interaction.followup.send(f"Proofs for `{game_uid}`", embeds=image_embeds, ephemeral=True)


    @discord.ui.button(label="Links", style=discord.ButtonStyle.grey, custom_id="reportedaccount:linksproofs")
    async def links_proofs_button(self, interaction, button):
        await interaction.response.defer()
        #
        game_uid = self.game_uid
        account_profile = self.account_profile
        #
        r_profile_list = account_profile["r_profile_list"]
        image_links = r_profile_list[2]
        image_embeds = image_links_to_embeds(image_links)
        await interaction.followup.send(f"Links Proofs for `{game_uid}`", embeds=image_embeds, ephemeral=True)

class MemberView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(discord.ui.Button(label="Report", style=discord.ButtonStyle.grey, url="https://discord.com/channels/1371673839695826974/1375261699111784478"))

check = app_commands.Group(name="check", description="Check.")
bot.tree.add_command(check)

RAW_LIST_URL = "https://raw.githubusercontent.com/Discord-AntiScam/scam-links/main/list.txt"
scam_domains = set()

@tasks.loop(hours=12)
async def update_scam_domains():
    global scam_domains
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(RAW_LIST_URL) as response:
                if response.status == 200:
                    text = await response.text()
                    new_domains = {
                        line.strip().lower()
                        for line in text.splitlines()
                        if line.strip() and not line.strip().startswith("#")
                    }
                    if new_domains:
                        scam_domains = new_domains
                        print(f"Updated {len(scam_domains)} domains.")
    except Exception as e:
        print(f"Cache refresh failed: {e}")

def defang_url(match: re.Match[str]) -> str:
    url = match.group(0)
    url = url.replace("https://", "hxxps://").replace("http://", "hxxp://")
    parts = url.split(".")
    if len(parts) > 1:
        return "[-]".join(parts[:-1]) + f"[{parts[-2][-1] if parts[-1] else ''}]" + parts[-1]
    return f"{url}"

@check.command(name="link", description="Checks a text or link for known malicious domains.")
@app_commands.describe(text="The text or link you want to check.")
async def check_link(interaction: discord.Interaction, text: str):
    extracted_urls = re.findall(r'(?:https?://)?(?:www\.)?([a-zA-Z0-9-]+(?:\.[a-zA-Z0-9-]+)+)', text)
    if not extracted_urls:
        return await interaction.response.send_message(
            "No URLs or domains detected in your input.",
            ephemeral=True
        )

    flagged_domains = []
    for domain in extracted_urls:
        cleaned_domain = domain.lower()

        if cleaned_domain in scam_domains:
            flagged_domains.append(cleaned_domain)
        else:
            parts = cleaned_domain.split('.')
            if len(parts) > 2:
                root_domain = ".".join(parts[-2:])
                if root_domain in scam_domains:
                    flagged_domains.append(cleaned_domain)

    ephemeral_embed = discord.Embed(colour=0xffffff)

    if flagged_domains:
        unique_flags = list(set(flagged_domains))
        formatted_list = "\n".join(f"- `{d}`" for d in unique_flags)
        ephemeral_embed.description = f"<a:tri_whitealert:1496542298908000257> **Malicious link(s) identified.**\n\n{formatted_list}"
        ephemeral_embed.set_footer(text="The public copy has been safely censored.")

        await interaction.response.send_message(embed=ephemeral_embed, ephemeral=True)

        safe_text = text
        for bad_domain in unique_flags:
            escaped_domain = re.escape(bad_domain)
            safe_text = re.sub(rf'(https?://)?(www\.)?{escaped_domain}', defang_url, safe_text, flags=re.IGNORECASE)

        public_embed = discord.Embed(description=f"{safe_text}", colour=0xffffff)
        public_embed.set_footer(text="The malicious link(s) have been safely censored.")
        await interaction.channel.send(content=f"<a:tri_whitealert:1496542298908000257> **{interaction.user.mention} checked a text containing the following malicious link(s)**", embed=public_embed)

    else:
        ephemeral_embed.description = "No known malicious domains detected.\n-# **This does not mean the link is guaranteed to be safe.**"
        await interaction.response.send_message(embed=ephemeral_embed, ephemeral=True)


@check.command(name="all", description="Check all users in the server for bannable report(s).")
@commands.has_permissions(administrator=True)
async def check_all(interaction: discord.Interaction):
    await interaction.response.send_message(f"Checking {interaction.guild.member_count:,} users for bannable report(s).", ephemeral=True)
    if interaction.guild is None:
        return
    start = time.perf_counter()
    status = await interaction.channel.send(content=f"Checking {interaction.guild.member_count:,} users for bannable report(s)...")
    total = interaction.guild.member_count
    ban_users = []
    for idx, member in enumerate(interaction.guild.members, start=1):
        if idx % 50 == 0:
            await asyncio.sleep(0)
        if idx % 100 == 0:
            elapsed = time.perf_counter() - start
            rate = idx / elapsed
            eta = (total - idx) / rate if rate else 0
            remaining = int(eta)
            minutes, seconds = divmod(remaining, 60)
            eta_text = (
                f"{minutes}m {seconds}s"
                if minutes
                else f"{seconds}s"
            )
            await status.edit(
                content=(
                    f"Checking {total:,} users for bannable report(s)...\n"
                    f"Progress: {idx:,}/{total:,} ({idx / total:.1%})\n"
                    f"ETA: {eta_text}"
                )
            )
        user_profile = await asyncio.to_thread(userscol.find_one, {"_id": str(member.id)})
        if not user_profile:
            continue
        if len(user_profile) == 2:
            main = user_profile["main"]
            profile = await asyncio.to_thread(userscol.find_one, {"_id": main})
            if profile is None:
                continue
        else:
            profile = user_profile
        no_of_cases = len(profile) - 2
        all_tags_list = []
        for i in range(1, no_of_cases + 1):
            tags = profile[str(i)]["tags"].split(", ")
            all_tags_list.extend(tags)
        all_tags_list = sort_user_tags(all_tags_list)
        if all_tags_list and all_tags_list[0] in red_tags:
            ban_users.append(str(member.id))
    if ban_users and len(ban_users) <= 1000:
        embeds = []
        ban_users_grouped = [ban_users[i:i + 100] for i in range(0, len(ban_users), 100)]
        for group in ban_users_grouped:
            embed = discord.Embed(description=f"`{" ".join(group)}`")
            embeds.append(embed)
        await interaction.channel.send(f"{len(ban_users)} users with bannable report(s) were found.", embeds=embeds)
    elif ban_users and len(ban_users) > 1000:
        embeds = []
        ban_users_grouped = [ban_users[i:i + 100] for i in range(0, 1001, 100)]
        for group in ban_users_grouped:
            embed = discord.Embed(description=f"`{" ".join(group)}`")
            embeds.append(embed)
        await interaction.channel.send(f"{len(ban_users)} users with bannable report(s) were found, which exceeds the limit of 1000 users that can be shown.", embeds=embeds)
    else:
        await interaction.channel.send("No users with bannable report(s) were found!")
    for doc in userscol.find({"main": {"$exists": True}}):
        if userscol.find_one({"_id": doc["main"]}) is None:
            print("Orphan alt:", doc["_id"], "->", doc["main"])


@bot.command()
async def sync(ctx: commands.Context):
    await bot.tree.sync()
    reports_count = userscol.count_documents({}) + serverscol.count_documents({}) + accountscol.count_documents({})
    await bot.change_presence(status=discord.Status.dnd,
        activity=discord.Activity(
            type=discord.ActivityType.watching,
            name=f"{reports_count} reports."
        )
    )


bot.run(TOKEN)