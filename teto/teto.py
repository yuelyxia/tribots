#  yuelyxia  ©  2025 – 2026

from dotenv import load_dotenv
import os
load_dotenv()

import pymongo
from pymongo.errors import DuplicateKeyError

import io
import aiohttp
import asyncio
import re
import datetime
import copy

import discord
from discord import app_commands
from discord.ext import commands, tasks
from discord.utils import get

from typing import Literal, Union

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
staffweeklycol = db["staff_weekly"]
inprogresscol = db["in_progress"]
altscol = db["alts"]
invitescol = db["invites"]

inprogresscol.create_index("user_id", unique=True, sparse=True)
inprogresscol.create_index("guild_id", unique=True, sparse=True)

# tri channels info
PROOFS_CHANNEL = 1455055877034868769
VOTE_CHANNEL = 1434537315791016210
USER_REPORTS_CHANNEL = 1375132097605406721
SERVER_REPORTS_CHANNEL = 1375184563675856916
ACCOUNT_REPORTS_CHANNEL = 1515531623045533716
TICKETS_CHANNEL = 1375261699111784478
INVITE_LOGS_CHANNEL = 1523229932375900300

# tri roles info
o5_role = 1372426616671834234
staff_role = 1373803879623430268
ticket_ping = 1449382692671193294
t_role = 1396701840321679391
sr_ping = 1375254710952661102
adm_ping = 1375276457890287748

new_user_report_ping = 1375275062185168957
updated_user_report_ping = 1459590866724323625
appealed_user_report_ping = 1459590865335877663
new_server_report_ping = 1375275002537971742
updated_server_report_ping = 1459590362703204405
appealed_server_report_ping = 1459590364292972776
new_account_report_ping = 1515589534438395914
updated_account_report_ping = 1515589535059284148
appealed_account_report_ping = 1515589539069169844

# tri bots
tri_bots = [
    1450073025818136598, # teto
    1457249982104211467, # teto++
    1457382953293320304, # neru
    1457309787044839477, # miku
    1457009979817988241, # kafu
]

TRI_Archive = 1371673839695826974

intents = discord.Intents.all()
bot = commands.Bot(command_prefix=',', help_command=None, intents=intents)

red_tags = ["Scammer", "Scam Server Owner", "Raider", "Plagiarist", "Fake Event Host", "Impersonator", "Vouch Scammer"]
yellow_tags = ["Suspect", "Service Ban", "Unprofessional MM", "Unprofessional Pilot", "Unprofessional IDV MM",
               "Unprofessional Supervisor", "Improper Conduct"]

red_server_tags = ["Scam Server", "Impersonator Server", "Fake Vouch Server", "Fake Event Server"]
yellow_server_tags = ["Suspect Server"]

red_account_tags = ["Scammed Account", "Scammer Account", "Leeched Account"]
yellow_account_tags = ["Suspicious Account", "Advertised by Scammer"]

games_list = ["Genshin Impact", "Honkai: Star Rail", "Wuthering Waves", "Roblox", "Zenless Zone Zero", "Honkai Impact 3rd", "Project Sekai", "Cookie Run: Kingdom", "Identity V", "Valorant", "Others", "N/A"]

def is_sr(user):
    return any(role.id in (sr_ping, adm_ping) for role in user.roles)

def is_active_staff(user):
    return any(role.id in (ticket_ping, adm_ping) for role in user.roles)

# formatting functions

def default_user_profile(user):
    profile = discord.Embed(title=f"{user.display_name.replace('||', '\\|\\|').replace('_', '\\_')}")
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
        trusted_embed = discord.Embed(colour=0xbba8dd, title=f"{user.display_name.replace('||', '\\|\\|').replace('_', '\\_')}")
        title = "TRI Staff"
    elif trusteduser_profile["staff"] == 1:
        trusted_embed = discord.Embed(colour=0x9279b5, title=f"{user.display_name.replace('||', '\\|\\|').replace('_', '\\_')}")
        title = "Former TRI Staff"
    else:
        trusted_embed = discord.Embed(colour=0x9279b5, title=f"{user.display_name.replace('||', '\\|\\|').replace('_', '\\_')}")
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
        r_profile = discord.Embed(colour=0xFFD643, title=f"{user.display_name.replace('||', '\\|\\|').replace('_', '\\_')}")
        colour = "\u001b[1;33m"
    elif title in red_tags:
        r_profile = discord.Embed(colour=0xFF0045, title=f"{user.display_name.replace('||', '\\|\\|').replace('_', '\\_')}")
        colour = "\u001b[1;31m"
    elif title in yellow_tags:
        r_profile = discord.Embed(colour=0xFFD643, title=f"{user.display_name.replace('||', '\\|\\|').replace('_', '\\_')}")
        colour = "\u001b[1;33m"
    else:
        r_profile = discord.Embed(title=f"{user.display_name.replace('||', '\\|\\|').replace('_', '\\_')}")
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
        r_profile = discord.Embed(title=f"{guild.name}")
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
def reconstruct_server_r_profile(guild_data, r_profile_list, title):
    guild_id = guild_data["id"]
    guild_name = guild_data["name"]
    guild_icon = guild_data["icon"]
    guild_created_at = guild_data["created_at"]
    guild_banner = guild_data["banner"]
    if title in red_server_tags:
        r_profile = discord.Embed(colour=0xCF2D53, title=f"{guild_name}")
        colour = "\u001b[1;31m"
    elif title in yellow_server_tags:
        r_profile = discord.Embed(colour=0xd9b534, title=f"{guild_name}")
        colour = "\u001b[1;33m"
    else:
        r_profile = discord.Embed(title=f"{guild_name}")
        colour = "\u001b[0m"
    if guild_icon:
        r_profile.set_thumbnail(url=guild_icon)
    r_profile.description = (f"```ansi\n{colour}{title}\u001b[0m\n```")
    r_profile.description += f"`{guild_id}`"
    if guild_created_at:
        ts = int(guild_created_at)
        r_profile.description += (
            f"\n-# **Server Created** – "
            f"<t:{ts}:D> (<t:{ts}:R>)\n"
        )
    r_profile.description += f"\n**Owner** – {r_profile_list[0]}\n**Other Tag(s)** – {r_profile_list[1] or "None"}"
    if guild_banner:
        r_profile.set_image(url=guild_banner)
    return r_profile


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
    game, uid = game_uid.split("ㆍ", 1)
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
        for tag in tags:
            if tag == tag_to_find:
                sorted_tags.append(tag)
    for tag_to_find in yellow_account_tags:
        for tag in tags:
            if tag == tag_to_find:
                sorted_tags.append(tag)
    for tag in tags:
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
    game, uid = game_uid.split("ㆍ", 1)
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


# dropdown options

user_tags_options = [
    discord.SelectOption(label="Scammer", value="Scammer"),
    discord.SelectOption(label="Scam Server Owner", value="Scam Server Owner"),
    discord.SelectOption(label="Raider", value="Raider"),
    discord.SelectOption(label="Plagiarist", value="Plagiarist"),
    discord.SelectOption(label="Fake Event Host", value="Fake Event Host"),
    discord.SelectOption(label="Impersonator", value="Impersonator"),
    discord.SelectOption(label="Vouch Scammer", value="Vouch Scammer"),
    discord.SelectOption(label="Suspect", value="Suspect"),
    discord.SelectOption(label="Ex-offender", value="Ex-offender"),
    discord.SelectOption(label="Service Ban", value="Service Ban"),
    discord.SelectOption(label="Unprofessional MM", value="Unprofessional MM"),
    discord.SelectOption(label="Unprofessional Pilot", value="Unprofessional Pilot"),
    discord.SelectOption(label="Unprofessional IDV MM", value="Unprofessional IDV MM"),
    discord.SelectOption(label="Unprofessional Supervisor", value="Unprofessional Supervisor"),
    discord.SelectOption(label="Improper Conduct", value="Improper Conduct"),
]

games_options = [
    discord.SelectOption(label="Genshin Impact", value="Genshin Impact"),
    discord.SelectOption(label="Honkai: Star Rail", value="Honkai: Star Rail"),
    discord.SelectOption(label="Wuthering Waves", value="Wuthering Waves"),
    discord.SelectOption(label="Roblox", value="Roblox"),
    discord.SelectOption(label="Zenless Zone Zero", value="Zenless Zone Zero"),
    discord.SelectOption(label="Honkai Impact 3rd", value="Honkai Impact 3rd"),
    discord.SelectOption(label="Project Sekai", value="Project Sekai"),
    discord.SelectOption(label="Cookie Run: Kingdom", value="Cookie Run: Kingdom"),
    discord.SelectOption(label="Identity V", value="Identity V"),
    discord.SelectOption(label="Valorant", value="Valorant"),
    discord.SelectOption(label="Others", value="Others"),
    discord.SelectOption(label="N/A", value="N/A"),
]

server_tags_options = [
    discord.SelectOption(label="Scam Server", value="Scam Server"),
    discord.SelectOption(label="Impersonator Server", value="Impersonator Server"),
    discord.SelectOption(label="Fake Vouch Server", value="Fake Vouch Server"),
    discord.SelectOption(label="Fake Event Server", value="Fake Event Server"),
    discord.SelectOption(label="Suspect Server", value="Suspect Server"),
]

account_tag_options = [
    discord.SelectOption(label="Scammed Account", value="Scammed Account"),
    discord.SelectOption(label="Scammer Account", value="Scammer Account"),
    discord.SelectOption(label="Leeched Account", value="Leeched Account"),
    discord.SelectOption(label="Suspicious Account", value="Suspicious Account"),
    discord.SelectOption(label="Advertised by Scammer", value="Advertised by Scammer"),
    discord.SelectOption(label="Recovered Account", value="Recovered Account"),
]

@tasks.loop(hours=1.0)
async def update_reports_count():
    reports_count = userscol.count_documents({}) + serverscol.count_documents({}) + accountscol.count_documents({})
    await bot.change_presence(status=discord.Status.dnd,
                              activity=discord.Activity(
                                  type=discord.ActivityType.watching,
                                  name=f"{reports_count} reports."
                              )
                              )

# edit queue

old_message_edit_queue = asyncio.Queue()

async def old_message_edit_worker():
    while True:
        message, kwargs = await old_message_edit_queue.get()
        try:
            await message.edit(**kwargs)
        except discord.HTTPException as e:
            if e.code == 30046:
                await asyncio.sleep(5)
                await old_message_edit_queue.put((message, kwargs))
            elif e.code in [50083]:
                try:
                    thread = message.channel
                    await thread.edit(archived=False, locked=False)
                    await asyncio.sleep(1)
                    await message.edit(**kwargs)
                    await asyncio.sleep(1)
                    await thread.edit(archived=True, locked=True)
                except Exception as inner_e:
                    print(inner_e)
            else:
                print(e)
        await asyncio.sleep(5)

# publish queue

publish_queue = asyncio.Queue()

@tasks.loop(seconds=1.0)
async def publish_worker():
    # Only run if there is something in the queue
    if not publish_queue.empty():
        message = await publish_queue.get()
        try:
            await message.publish()
        except discord.HTTPException as e:
            if e.status == 429:
                await asyncio.sleep(e.retry_after)
                await publish_queue.put(message) # Re-queue
        publish_queue.task_done()


# on ready

@bot.event
async def on_ready():
    update_reports_count.start()
    publish_worker.start()
    bot.loop.create_task(old_message_edit_worker())
    #
    bot.add_view(AltsView())
    bot.add_view(UserTagsView())
    bot.add_view(GamesView())
    bot.add_view(UserReasonView())
    bot.add_view(UserContributorView())
    bot.add_view(UserProofsView())
    bot.add_view(EditAltsOnlyView())
    bot.add_view(UserAppealView())
    bot.add_view(AddReportAltsView())
    bot.add_view(AddReportUserTagsView())
    bot.add_view(AddReportGamesView())
    bot.add_view(AddReportUserReasonView())
    bot.add_view(AddReportUserContributorView())
    bot.add_view(AddReportUserProofsView())
    bot.add_view(UserVoteView())
    bot.add_view(ServerOwnerView())
    bot.add_view(ServerTagsView())
    bot.add_view(ServerReasonView())
    bot.add_view(ServerContributorView())
    bot.add_view(ServerProofsView())
    bot.add_view(EditOwnerOnlyView())
    bot.add_view(ServerAppealView())
    bot.add_view(AddReportOwnerView())
    bot.add_view(AddReportServerTagsView())
    bot.add_view(AddReportServerReasonView())
    bot.add_view(AddReportServerContributorView())
    bot.add_view(AddReportServerProofsView())
    bot.add_view(ServerVoteView())
    bot.add_view(LinksView())
    bot.add_view(AccountTagsView())
    bot.add_view(RelatedUsersView())
    bot.add_view(AccountReasonView())
    bot.add_view(AccountContributorView())
    bot.add_view(AccountProofsView())
    bot.add_view(EditLinksOnlyView())
    bot.add_view(AccountAppealView())
    bot.add_view(AddReportLinksView())
    bot.add_view(AddReportAccountTagsView())
    bot.add_view(AddReportRelatedUsersView())
    bot.add_view(AddReportAccountReasonView())
    bot.add_view(AddReportAccountContributorView())
    bot.add_view(AddReportAccountProofsView())
    bot.add_view(AccountVoteView())


@bot.event
async def on_message(message):
    if message.channel.type == discord.ChannelType.news and message.author.id == bot.user.id:
        await publish_queue.put(message)
    await bot.process_commands(message)


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
                msg += f"> **Replaced** – `{replaced_code}` <:whitearrow4:1523377871480033301> `{invite.code}`"
            else:
                msg += f"> **Added** – `{invite.code}`"
            await log_channel.send(embed=discord.Embed(description=msg))


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

@bot.command(name='mc', help='Checks a list of users (max 100), leave a space between users.')
async def mc(ctx, *, to_check: str = None):
    if to_check is None:
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
                        f"<a:whitealert:1496542298908000257> **`{current_id}` (alt of `{main_id_str}`) is reported as {selected_string(all_unique_tags)}.**")
                else:
                    current_content.append(
                        f"<a:whitealert:1496542298908000257> **`{current_id}` is reported as {selected_string(all_unique_tags)}.**")

                if already_processed_embed:
                    continue

                r_profile_list = target_profile.get("r_profile_list", [])
                title = all_unique_tags[0] if all_unique_tags else "Reported"
                r_profile = format_user_r_profile(user, r_profile_list, title)
                current_embeds.append(r_profile)
            else:
                profile = default_user_profile(user)
                current_embeds.append(profile)
                current_content.append(f"<:whitedot:1462907474947342567> `{current_id}` is unreported.")

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


@bot.command(name="c", help="Checks a user, server or account.")
async def c(ctx, *, to_check: str = None):
    requested_by = ctx.author

    author_query = {"_id": str(ctx.author.id)}
    trusted_author = trusteduserscol.find_one(author_query)
    is_staff = bool(
        trusted_author and
        trusted_author.get("current_staff") == 1 and
        (is_active_staff(ctx.author) or get(ctx.guild.roles, id=t_role) in ctx.author.roles)
    )

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
                msg = f"Account `{game_uid}` is linked to `{main}`."
                view = EditAccountReportView(main, main_profile, requested_by,
                                             len(main_profile) - 2) if is_staff else ReportedAccountView(main,
                                                                                                         main_profile,
                                                                                                         requested_by,
                                                                                                         len(main_profile) - 2)
                return await ctx.reply(msg, embeds=reported_account_profile(main, main_profile), view=view)
            else:
                msg = "Account is reported."
                view = EditAccountReportView(game_uid, account_profile, requested_by,
                                             len(account_profile) - 2) if is_staff else ReportedAccountView(game_uid,
                                                                                                            account_profile,
                                                                                                            requested_by,
                                                                                                            len(account_profile) - 2)
                return await ctx.reply(msg, embeds=reported_account_profile(game_uid, account_profile), view=view)
        else:
            view = NewAccountReportView(game_uid, requested_by) if is_staff else MemberView()
            return await ctx.reply(embed=default_account_profile(game_uid), view=view)

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
            1457249982104211467: "\n**TETO++** ┈ report bot for `/tri`",
            1457382953293320304: "\n**NERU** ┈ alts bot for `/tri`",
            1457309787044839477: "\n**MIKU** ┈ utils bot for `/tri`",
            1457009979817988241: "\n**KAFU** ┈ utils bot for **trading** & tickets bot for `/tri`"
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
        trusted_server = trustedserverscol.find_one({"_id": server_id})

        if trusted_server:
            return await ctx.reply("Server is trusted.", embed=format_trustedserver_profile(guild))
        elif server_profile:
            view = EditServerReportView(guild, server_profile, requested_by,
                                        len(server_profile) - 2) if is_staff else ReportedServerView(guild,
                                                                                                     server_profile,
                                                                                                     requested_by,
                                                                                                     len(server_profile) - 2)
            return await ctx.reply("Server is reported.", embeds=reported_server_profile(guild, server_profile),
                                   view=view)
        else:
            if server_id.isdigit() and (not guild or isinstance(guild, UnknownGuild)):
                return await ctx.reply(
                    "Please provide a valid user ID. To check servers, please provide a valid invite link.")
            view = NewServerReportView(guild, requested_by) if is_staff else MemberView()
            return await ctx.reply(embed=default_server_profile(guild), view=view)

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

            msg = f"User `{user_id_str}` is reported as alt of `{main}`."
            view = EditUserReportView(main_user, main_user_profile, requested_by,
                                      len(main_user_profile) - 2) if is_staff else ReportedUserView(main_user,
                                                                                                    main_user_profile,
                                                                                                    requested_by,
                                                                                                    len(main_user_profile) - 2)
            return await ctx.reply(msg, embeds=reported_user_profile(main_user, main_user_profile), view=view)
        else:
            view = EditUserReportView(target_user, user_profile, requested_by,
                                      len(user_profile) - 2) if is_staff else ReportedUserView(target_user,
                                                                                               user_profile,
                                                                                               requested_by,
                                                                                               len(user_profile) - 2)
            return await ctx.reply("User is reported.", embeds=reported_user_profile(target_user, user_profile),
                                   view=view)
    else:
        profile = default_user_profile(target_user)
        view = NewUserReportView(target_user, requested_by) if is_staff else MemberView()
        return await ctx.reply(embed=profile, view=view)

@bot.command(name="ca", help="Checks a user and for their alts.")
async def ca(ctx, *, to_check: str = None):
    requested_by = ctx.author

    author_query = {"_id": str(ctx.author.id)}
    trusted_author = trusteduserscol.find_one(author_query)
    is_staff = bool(
        trusted_author and
        trusted_author.get("current_staff") == 1 and
        (is_active_staff(ctx.author) or get(ctx.guild.roles, id=t_role) in ctx.author.roles)
    )

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
        alts_embed.description = f"<a:whitealert:1496542298908000257> **Alt(s)** of `{target_user.id}`\n\n`{raw_ids}`"
    else:
        alts_embed.description = "<:whitecross:1462774085737119828>　No alts logged for this user."

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
            view = EditUserReportView(main_user, main_user_profile, requested_by,
                                      len(main_user_profile) - 2) if is_staff else ReportedUserView(main_user,
                                                                                                    main_user_profile,
                                                                                                    requested_by,
                                                                                                    len(main_user_profile) - 2)
            return await ctx.send(msg, embeds=reported_user_profile(main_user, main_user_profile), view=view)
        else:
            view = EditUserReportView(target_user, user_profile, requested_by,
                                      len(user_profile) - 2) if is_staff else ReportedUserView(target_user, user_profile,
                                                                                               requested_by,
                                                                                               len(user_profile) - 2)
            return await ctx.send("User is reported.", embeds=reported_user_profile(target_user, user_profile),
                                   view=view)

    else:
        profile = default_user_profile(target_user)
        view = NewUserReportView(target_user, requested_by) if is_staff else MemberView()
        return await ctx.send(embed=profile, view=view)


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


# reported user
class ReportedUserView(discord.ui.View):
    def __init__(self, user, user_profile, requested_by, current_case):
        super().__init__(timeout=3600)
        self.user = user
        self.user_profile = user_profile
        self.requested_by = requested_by
        self.current_case = current_case

    @discord.ui.button(emoji="<:leftarrow:1458096658062770176>", style=discord.ButtonStyle.grey, custom_id="reporteduser:prev")
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
                prev_index = current_case - 2
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

    @discord.ui.button(emoji="<:rightarrow:1458096774521553038>", style=discord.ButtonStyle.grey, custom_id="reporteduser:next")
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

    @discord.ui.button(label="Proofs", style=discord.ButtonStyle.grey, custom_id="reporteduser:proofs")
    async def proofs_button(self, interaction, button):
        await interaction.response.defer()
        #
        user = self.user
        user_profile = self.user_profile
        current_case = self.current_case
        #
        no_of_cases = len(user_profile) - 2
        cases = []
        for i in range(1, no_of_cases + 1):
            cases.append(user_profile[str(i)])
        image_links = cases[current_case - 1]["proofs"]
        image_embeds = image_links_to_embeds(image_links)
        await interaction.followup.send(f"Proofs for `{user.id}`", embeds=image_embeds, ephemeral=True)


    @discord.ui.button(label="Alts", style=discord.ButtonStyle.grey, custom_id="reporteduser:altsproofs")
    async def alts_proofs_button(self, interaction, button):
        await interaction.response.defer()
        #
        user = self.user
        user_profile = self.user_profile
        #
        r_profile_list = user_profile["r_profile_list"]
        image_links = r_profile_list[2]
        image_embeds = image_links_to_embeds(image_links)
        await interaction.followup.send(f"Alts Proofs for `{user.id}`", embeds=image_embeds, ephemeral=True)

# reported server
class ReportedServerView(discord.ui.View):
    def __init__(self, guild, server_profile, requested_by, current_case):
        super().__init__(timeout=3600)
        self.guild = guild
        self.server_profile = server_profile
        self.requested_by = requested_by
        self.current_case = current_case

    @discord.ui.button(emoji="<:leftarrow:1458096658062770176>", style=discord.ButtonStyle.grey, custom_id="reportedserver:prev")
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

    @discord.ui.button(emoji="<:rightarrow:1458096774521553038>", style=discord.ButtonStyle.grey, custom_id="reportedserver:next")
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

    @discord.ui.button(label="Proofs", style=discord.ButtonStyle.grey, custom_id="reportedserver:proofs")
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


# member
class MemberView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(discord.ui.Button(label="Report", style=discord.ButtonStyle.grey,
                                        url="https://discord.com/channels/1371673839695826974/1375261699111784478"))

# new user
class NewUserReportView(discord.ui.View):
    def __init__(self, user, requested_by):
        super().__init__(timeout=3600)
        self.user = user
        self.requested_by = requested_by

    @discord.ui.button(label="Report", style=discord.ButtonStyle.red, custom_id="newuserreport:report")
    async def report_button(self, interaction, button):
        #
        user = self.user
        requested_by = self.requested_by
        #
        await interaction.response.defer()
        existing_entry = inprogresscol.find_one({"user_id": user.id})
        if existing_entry:
            # ongoing vote
            if "vote_channel_id" in existing_entry:
                vote_channel_id = existing_entry["vote_channel_id"]
                vote_message_id = existing_entry["_id"]
                vote_channel = bot.get_channel(vote_channel_id)
                if not vote_channel:
                    vote_channel = await bot.fetch_channel(vote_channel_id)
                try:
                    vote_message = await vote_channel.fetch_message(vote_message_id)
                except discord.NotFound:
                    return await interaction.followup.send(
                        "This message could not be found. It may have been deleted.", ephemeral=True)
                await interaction.followup.send(f"There already exists an ongoing vote on `{user.id}`: {vote_message.jump_url}")
            # ongoing report
            else:
                channel_id = existing_entry["channel_id"]
                message_id = existing_entry["_id"]
                thread = await bot.fetch_channel(channel_id)
                try:
                    message = await thread.fetch_message(message_id)
                except discord.NotFound:
                    return await interaction.followup.send(
                        "This message could not be found. It may have been deleted.", ephemeral=True)
                await interaction.followup.send(
                        f"There already exists an ongoing report on `{user.id}`: {message.jump_url}")
            return
        if requested_by == interaction.user:
            await interaction.edit_original_response(view=None)
            msg = await interaction.followup.send(f"Initializing report on `{user.id}`...", wait=True)
            title = "TBC"
            case_title = "TBC"
            r_profile_list = [
                # [0] alts
                "",
                # [1] other tags
                "",
                # [2] alts_image_links
                [],
            ]
            add_case_list = {
                "date_added": f"<t:{round(int(discord.utils.utcnow().timestamp()))}:D> (<t:{round(int(discord.utils.utcnow().timestamp()))}:R>)",
                "games": "", "tags": "", "reason": "", "contributor": "", "staff": f"{interaction.user.mention}",
                "accepted_by": "", "proofs": []}
            channel_id = msg.channel.id
            message_id = msg.id
            r_profile = format_user_r_profile(user, r_profile_list, title)
            add_case = format_user_add_case(add_case_list, case_title)
            embeds = [r_profile, add_case]
            try:
                inprogresscol.insert_one({"_id": message_id,
                                          "user_id": user.id,
                                          "requested_by": requested_by.id,
                                          "channel_id": channel_id,
                                          "r_profile_list": r_profile_list,
                                          "add_case_list": add_case_list,
                                          "title": title,
                                          "case_title": case_title
                                          })
            except DuplicateKeyError: pass
            await msg.edit(embeds=embeds, view=AltsView())
        elif is_active_staff(interaction.user):
            await interaction.followup.send(
                "This was requested by " + f"{requested_by.mention}, you cannot interact with this component.",
                ephemeral=True)
        else:
            await interaction.followup.send("You do not have permission to use this button.", ephemeral=True)

class AltsView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(emoji="<:rightarrow:1458096774521553038>", style=discord.ButtonStyle.grey, custom_id="alts:next")
    async def next_button(self, interaction, button):
        await interaction.response.defer()
        #
        session = inprogresscol.find_one({"_id": interaction.message.id})
        if session:
            requested_by = session["requested_by"]
            channel_id = session["channel_id"]
            message_id = interaction.message.id
            r_profile_list = session["r_profile_list"]
            add_case_list = session["add_case_list"]
            title = session["title"]
            case_title = session["case_title"]
            user_id = session["user_id"]
            user = await bot.fetch_user(user_id)
            #
            thread = await bot.fetch_channel(channel_id)
            message = await thread.fetch_message(message_id)
            if requested_by == interaction.user.id or is_sr(interaction.user):
                r_profile = format_user_r_profile(user, r_profile_list, title)
                add_case = format_user_add_case(add_case_list, case_title)
                embeds = [r_profile, add_case]
                await message.edit(embeds=embeds, view=UserTagsView())

    @discord.ui.button(label="Alts", style=discord.ButtonStyle.green, custom_id="alts:input")
    async def alts_button(self, interaction, button):
        session = inprogresscol.find_one({"_id": interaction.message.id})
        if session:
            requested_by = session["requested_by"]
            #
            if requested_by == interaction.user.id:
                await interaction.response.send_modal(AltsModal())

    @discord.ui.button(label="Add Alts Proofs", style=discord.ButtonStyle.green, custom_id="alts:altsproofs")
    async def alts_proofs_button(self, interaction, button):
        #
        session = inprogresscol.find_one({"_id": interaction.message.id})
        if session:
            requested_by = session["requested_by"]
            r_profile_list = session["r_profile_list"]
            #
            if requested_by == interaction.user.id:
                image_links = []
                r_profile_list[2] = []
                await interaction.response.send_message(
                    "Please send the images you would like to upload (max 10). **All images previously uploaded in this session have been removed.**",
                    ephemeral=True)

                # Wait for a follow-up message from the user in the same channel
                def check(m):
                    # Check if the message is from the same user, in the same channel, and has an attachment
                    return m.author == interaction.user and m.channel == interaction.channel

                try:
                    msg = await bot.wait_for('message', check=check, timeout=120.0)
                except asyncio.TimeoutError:
                    await interaction.followup.send("You took too long to upload an image.", ephemeral=True)
                    return
                if msg.attachments:
                    for attachment in msg.attachments:
                        # Ensure the attachment is an image (optional check)
                        if attachment.content_type and attachment.content_type.startswith('image/'):
                            try:
                                # 1. Download the file data using aiohttp
                                async with aiohttp.ClientSession() as http_session:
                                    async with http_session.get(attachment.url) as resp:
                                        # For this example, we just send back the image URL and filename
                                        data = io.BytesIO(await resp.read())
                                        file = discord.File(data, filename=attachment.filename)
                                        channel_to_send = bot.get_channel(PROOFS_CHANNEL)
                                        sent_message = await channel_to_send.send(file=file)
                                        if sent_message.attachments:
                                            new_image_url = sent_message.attachments[0].url
                                            image_links.append(new_image_url)
                                            r_profile_list[2].append(new_image_url)
                            except Exception:
                                await msg.channel.send(f"An error occurred with file {attachment.filename}")
                #
                inprogresscol.update_one(
                    {"_id": interaction.message.id},
                    {"$set": {"r_profile_list": r_profile_list}}
                )
                #
                image_embeds = image_links_to_embeds(image_links)
                await interaction.followup.send(f"Images received from {interaction.user.mention}.",
                                                embeds=image_embeds)

    @discord.ui.button(label="Show Alts Proofs", style=discord.ButtonStyle.grey, custom_id="alts:showaltsproofs")
    async def show_alts_proofs_button(self, interaction, button):
        await interaction.response.defer()
        #
        session = inprogresscol.find_one({"_id": interaction.message.id})
        if session:
            requested_by = session["requested_by"]
            r_profile_list = session["r_profile_list"]
            user_id = session["user_id"]
            user = await bot.fetch_user(user_id)
            #
            if requested_by == interaction.user.id or is_sr(interaction.user):
                image_embeds = image_links_to_embeds(r_profile_list[2])
                await interaction.followup.send(f"Alts Proofs for `{user.id}`",
                                                embeds=image_embeds, ephemeral=True)
class AltsModal(discord.ui.Modal, title="Alts"):
    alts = discord.ui.TextInput(label="Alts", placeholder="List alts here and leave a space between IDs.",
                                required=True, style=discord.TextStyle.short)

    def __init__(self):
        super().__init__(timeout=None)

    async def on_submit(self, interaction):
        await interaction.response.defer()
        #
        session = inprogresscol.find_one({"_id": interaction.message.id})
        if session:
            channel_id = session["channel_id"]
            message_id = interaction.message.id
            r_profile_list = session["r_profile_list"]
            add_case_list = session["add_case_list"]
            title = session["title"]
            case_title = session["case_title"]
            user_id = session["user_id"]
            user = await bot.fetch_user(user_id)
            #
            thread = await bot.fetch_channel(channel_id)
            message = await thread.fetch_message(message_id)
            alts_input = self.alts.value
            alts_list = alts_input.split()
            valid_alts = []
            for alt in alts_list:
                try:
                    alt_id = await bot.fetch_user(int(alt))
                except Exception:
                    pass
                else:
                    if alt_id.id not in valid_alts and alt_id != user:
                        valid_alts.append(alt_id.id)
            if len(valid_alts) != 0:
                r_profile_list[0] = alts_string(valid_alts)
            else:
                r_profile_list[0] = ""
            #
            inprogresscol.update_one(
                {"_id": interaction.message.id},
                {"$set": {"r_profile_list": r_profile_list}}
            )
            #
            r_profile = format_user_r_profile(user, r_profile_list, title)
            add_case = format_user_add_case(add_case_list, case_title)
            embeds = [r_profile, add_case]
            await message.edit(embeds=embeds,
                               view=AltsView())

class UserTagsView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(emoji="<:leftarrow:1458096658062770176>", style=discord.ButtonStyle.grey, custom_id="usertags:prev")
    async def prev_button(self, interaction, button):
        await interaction.response.defer()
        #
        session = inprogresscol.find_one({"_id": interaction.message.id})
        if session:
            requested_by = session["requested_by"]
            channel_id = session["channel_id"]
            message_id = interaction.message.id
            r_profile_list = session["r_profile_list"]
            add_case_list = session["add_case_list"]
            title = session["title"]
            case_title = session["case_title"]
            user_id = session["user_id"]
            user = await bot.fetch_user(user_id)
            #
            thread = await bot.fetch_channel(channel_id)
            message = await thread.fetch_message(message_id)
            if requested_by == interaction.user.id or is_sr(interaction.user):
                r_profile = format_user_r_profile(user, r_profile_list, title)
                add_case = format_user_add_case(add_case_list, case_title)
                embeds = [r_profile, add_case]
                await message.edit(embeds=embeds,
                                   view=AltsView())

    @discord.ui.button(emoji="<:rightarrow:1458096774521553038>", style=discord.ButtonStyle.grey, custom_id="usertags:next")
    async def next_button(self, interaction, button):
        await interaction.response.defer()
        #
        session = inprogresscol.find_one({"_id": interaction.message.id})
        if session:
            requested_by = session["requested_by"]
            channel_id = session["channel_id"]
            message_id = interaction.message.id
            r_profile_list = session["r_profile_list"]
            add_case_list = session["add_case_list"]
            title = session["title"]
            case_title = session["case_title"]
            user_id = session["user_id"]
            user = await bot.fetch_user(user_id)
            #
            thread = await bot.fetch_channel(channel_id)
            message = await thread.fetch_message(message_id)
            if requested_by == interaction.user.id or is_sr(interaction.user):
                r_profile = format_user_r_profile(user, r_profile_list, title)
                add_case = format_user_add_case(add_case_list, case_title)
                embeds = [r_profile, add_case]
                await message.edit(embeds=embeds, view=GamesView())

    @discord.ui.select(options=user_tags_options, placeholder="Select Tag(s)...", custom_id="usertags:select",
                       max_values=len(user_tags_options))
    async def select_callback(self, interaction, select):
        await interaction.response.defer()
        #
        session = inprogresscol.find_one({"_id": interaction.message.id})
        if session:
            requested_by = session["requested_by"]
            channel_id = session["channel_id"]
            message_id = interaction.message.id
            r_profile_list = session["r_profile_list"]
            add_case_list = session["add_case_list"]
            user_id = session["user_id"]
            user = await bot.fetch_user(user_id)
            #
            thread = await bot.fetch_channel(channel_id)
            message = await thread.fetch_message(message_id)
            if requested_by == interaction.user.id:
                sorted_tags = sort_user_tags(self.select_callback.values)
                case_title = sorted_tags[0]
                tags = selected_string(sorted_tags)
                add_case_list["tags"] = tags
                title = sorted_tags[0]
                all_other_tags = selected_string(sorted_tags[1:])
                r_profile_list[1] = all_other_tags
                #
                inprogresscol.update_one(
                    {"_id": interaction.message.id},
                    {"$set": {
                        "r_profile_list": r_profile_list,
                        "add_case_list": add_case_list,
                        "title": title,
                        "case_title": case_title, }
                    })
                #
                r_profile = format_user_r_profile(user, r_profile_list, title)
                add_case = format_user_add_case(add_case_list, case_title)
                embeds = [r_profile, add_case]
                await message.edit(embeds=embeds)

class GamesView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(emoji="<:leftarrow:1458096658062770176>", style=discord.ButtonStyle.grey, custom_id="games:prev")
    async def prev_button(self, interaction, button):
        await interaction.response.defer()
        #
        session = inprogresscol.find_one({"_id": interaction.message.id})
        if session:
            requested_by = session["requested_by"]
            channel_id = session["channel_id"]
            message_id = interaction.message.id
            r_profile_list = session["r_profile_list"]
            add_case_list = session["add_case_list"]
            title = session["title"]
            case_title = session["case_title"]
            user_id = session["user_id"]
            user = await bot.fetch_user(user_id)
            #
            thread = await bot.fetch_channel(channel_id)
            message = await thread.fetch_message(message_id)
            if requested_by == interaction.user.id or is_sr(interaction.user):
                r_profile = format_user_r_profile(user, r_profile_list, title)
                add_case = format_user_add_case(add_case_list, case_title)
                embeds = [r_profile, add_case]
                await message.edit(embeds=embeds,
                                   view=UserTagsView())

    @discord.ui.button(emoji="<:rightarrow:1458096774521553038>", style=discord.ButtonStyle.grey, custom_id="games:next")
    async def next_button(self, interaction, button):
        await interaction.response.defer()
        #
        session = inprogresscol.find_one({"_id": interaction.message.id})
        if session:
            requested_by = session["requested_by"]
            channel_id = session["channel_id"]
            message_id = interaction.message.id
            r_profile_list = session["r_profile_list"]
            add_case_list = session["add_case_list"]
            title = session["title"]
            case_title = session["case_title"]
            user_id = session["user_id"]
            user = await bot.fetch_user(user_id)
            #
            thread = await bot.fetch_channel(channel_id)
            message = await thread.fetch_message(message_id)
            if requested_by == interaction.user.id or is_sr(interaction.user):
                r_profile = format_user_r_profile(user, r_profile_list, title)
                add_case = format_user_add_case(add_case_list, case_title)
                embeds = [r_profile, add_case]
                await message.edit(embeds=embeds, view=UserReasonView())

    @discord.ui.select(options=games_options, placeholder="Select Game(s)...", custom_id="games:select",
                       max_values=len(games_options))
    async def select_callback(self, interaction, select):
        await interaction.response.defer()
        #
        session = inprogresscol.find_one({"_id": interaction.message.id})
        if session:
            requested_by = session["requested_by"]
            channel_id = session["channel_id"]
            message_id = interaction.message.id
            r_profile_list = session["r_profile_list"]
            add_case_list = session["add_case_list"]
            title = session["title"]
            case_title = session["case_title"]
            user_id = session["user_id"]
            user = await bot.fetch_user(user_id)
            #
            thread = await bot.fetch_channel(channel_id)
            message = await thread.fetch_message(message_id)
            if requested_by == interaction.user.id:
                games = selected_string(self.select_callback.values)
                add_case_list["games"] = games
                #
                inprogresscol.update_one(
                    {"_id": interaction.message.id},
                    {"$set": {
                        "r_profile_list": r_profile_list,
                        "add_case_list": add_case_list,
                        "title": title,
                        "case_title": case_title, }
                    })
                #
                r_profile = format_user_r_profile(user, r_profile_list, title)
                add_case = format_user_add_case(add_case_list, case_title)
                embeds = [r_profile, add_case]
                await message.edit(embeds=embeds)

class UserReasonView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(emoji="<:leftarrow:1458096658062770176>", style=discord.ButtonStyle.grey, custom_id="userreason:prev")
    async def prev_button(self, interaction, button):
        await interaction.response.defer()
        #
        session = inprogresscol.find_one({"_id": interaction.message.id})
        if session:
            requested_by = session["requested_by"]
            channel_id = session["channel_id"]
            message_id = interaction.message.id
            r_profile_list = session["r_profile_list"]
            add_case_list = session["add_case_list"]
            title = session["title"]
            case_title = session["case_title"]
            user_id = session["user_id"]
            user = await bot.fetch_user(user_id)
            #
            thread = await bot.fetch_channel(channel_id)
            message = await thread.fetch_message(message_id)
            if requested_by == interaction.user.id or is_sr(interaction.user):
                r_profile = format_user_r_profile(user, r_profile_list, title)
                add_case = format_user_add_case(add_case_list, case_title)
                embeds = [r_profile, add_case]
                await message.edit(embeds=embeds, view=GamesView())

    @discord.ui.button(emoji="<:rightarrow:1458096774521553038>", style=discord.ButtonStyle.grey, custom_id="userreason:next")
    async def next_button(self, interaction, button):
        await interaction.response.defer()
        #
        session = inprogresscol.find_one({"_id": interaction.message.id})
        if session:
            requested_by = session["requested_by"]
            channel_id = session["channel_id"]
            message_id = interaction.message.id
            r_profile_list = session["r_profile_list"]
            add_case_list = session["add_case_list"]
            title = session["title"]
            case_title = session["case_title"]
            user_id = session["user_id"]
            user = await bot.fetch_user(user_id)
            #
            thread = await bot.fetch_channel(channel_id)
            message = await thread.fetch_message(message_id)
            if requested_by == interaction.user.id or is_sr(interaction.user):
                r_profile = format_user_r_profile(user, r_profile_list, title)
                add_case = format_user_add_case(add_case_list, case_title)
                embeds = [r_profile, add_case]
                await message.edit(embeds=embeds, view=UserContributorView())

    @discord.ui.button(label="Reason", style=discord.ButtonStyle.green, custom_id="userreason:input")
    async def reason_button(self, interaction, button):
        #
        session = inprogresscol.find_one({"_id": interaction.message.id})
        if session:
            requested_by = session["requested_by"]
            if requested_by == interaction.user.id:
                await interaction.response.send_modal(UserReasonModal())
class UserReasonModal(discord.ui.Modal, title="Reason"):
    reason = discord.ui.TextInput(label="Reason", placeholder="Input reason here.", required=True,
                                  style=discord.TextStyle.long)

    def __init__(self):
        super().__init__(timeout=None)

    async def on_submit(self, interaction):
        await interaction.response.defer()
        #
        session = inprogresscol.find_one({"_id": interaction.message.id})
        if session:
            channel_id = session["channel_id"]
            message_id = interaction.message.id
            r_profile_list = session["r_profile_list"]
            add_case_list = session["add_case_list"]
            title = session["title"]
            case_title = session["case_title"]
            user_id = session["user_id"]
            user = await bot.fetch_user(user_id)
            #
            thread = await bot.fetch_channel(channel_id)
            message = await thread.fetch_message(message_id)
            reason = re.sub(r"\s+", " ", self.reason.value)
            add_case_list["reason"] = reason
            #
            inprogresscol.update_one(
                {"_id": interaction.message.id},
                {"$set": {"add_case_list": add_case_list}},
            )
            #
            r_profile = format_user_r_profile(user, r_profile_list, title)
            add_case = format_user_add_case(add_case_list, case_title)
            embeds = [r_profile, add_case]
            await message.edit(embeds=embeds,
                               view=UserReasonView())

class UserContributorView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(emoji="<:leftarrow:1458096658062770176>", style=discord.ButtonStyle.grey,
                       custom_id="usercontributor:prev")
    async def prev_button(self, interaction, button):
        await interaction.response.defer()
        #
        session = inprogresscol.find_one({"_id": interaction.message.id})
        if session:
            requested_by = session["requested_by"]
            channel_id = session["channel_id"]
            message_id = interaction.message.id
            r_profile_list = session["r_profile_list"]
            add_case_list = session["add_case_list"]
            title = session["title"]
            case_title = session["case_title"]
            user_id = session["user_id"]
            user = await bot.fetch_user(user_id)
            #
            thread = await bot.fetch_channel(channel_id)
            message = await thread.fetch_message(message_id)
            if requested_by == interaction.user.id or is_sr(interaction.user):
                r_profile = format_user_r_profile(user, r_profile_list, title)
                add_case = format_user_add_case(add_case_list, case_title)
                embeds = [r_profile, add_case]
                await message.edit(embeds=embeds, view=UserReasonView())

    @discord.ui.button(emoji="<:rightarrow:1458096774521553038>", style=discord.ButtonStyle.grey,
                       custom_id="usercontributor:next")
    async def next_button(self, interaction, button):
        await interaction.response.defer()
        #
        session = inprogresscol.find_one({"_id": interaction.message.id})
        if session:
            requested_by = session["requested_by"]
            channel_id = session["channel_id"]
            message_id = interaction.message.id
            r_profile_list = session["r_profile_list"]
            add_case_list = session["add_case_list"]
            title = session["title"]
            case_title = session["case_title"]
            user_id = session["user_id"]
            user = await bot.fetch_user(user_id)
            #
            thread = await bot.fetch_channel(channel_id)
            message = await thread.fetch_message(message_id)
            if requested_by == interaction.user.id or is_sr(interaction.user):
                r_profile = format_user_r_profile(user, r_profile_list, title)
                add_case = format_user_add_case(add_case_list, case_title)
                embeds = [r_profile, add_case]
                await message.edit(embeds=embeds, view=UserProofsView())

    @discord.ui.button(label="Contributor", style=discord.ButtonStyle.green, custom_id="usercontributor:input")
    async def contributor_button(self, interaction, button):
        #
        session = inprogresscol.find_one({"_id": interaction.message.id})
        if session:
            requested_by = session["requested_by"]
            #
            if requested_by == interaction.user.id:
                await interaction.response.send_modal(UserContributorModal())
class UserContributorModal(discord.ui.Modal, title="Contributor"):
    contributor = discord.ui.TextInput(label="Contributor",
                                       placeholder="User ID / n if Anonymous.", required=True,
                                       style=discord.TextStyle.short)

    def __init__(self):
        super().__init__(timeout=None)

    async def on_submit(self, interaction):
        await interaction.response.defer()
        #
        session = inprogresscol.find_one({"_id": interaction.message.id})
        if session:
            channel_id = session["channel_id"]
            message_id = interaction.message.id
            r_profile_list = session["r_profile_list"]
            add_case_list = session["add_case_list"]
            title = session["title"]
            case_title = session["case_title"]
            user_id = session["user_id"]
            user = await bot.fetch_user(user_id)
            #
            thread = await bot.fetch_channel(channel_id)
            message = await thread.fetch_message(message_id)
            contributor_input = self.contributor.value
            if contributor_input.lower() == "n":
                add_case_list["contributor"] = "Anonymous"
            else:
                try:
                    contributor_id = await bot.fetch_user(int(contributor_input))
                except Exception:
                    add_case_list["contributor"] = ""
                else:
                    add_case_list["contributor"] = f"<@{contributor_id.id}>"
            #
            inprogresscol.update_one(
                {"_id": interaction.message.id},
                {"$set": {"add_case_list": add_case_list}},
            )
            #
            r_profile = format_user_r_profile(user, r_profile_list, title)
            add_case = format_user_add_case(add_case_list, case_title)
            embeds = [r_profile, add_case]
            await message.edit(embeds=embeds, view=UserContributorView())

class UserProofsView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(emoji="<:leftarrow:1458096658062770176>", style=discord.ButtonStyle.grey, custom_id="userproofs:prev")
    async def prev_button(self, interaction, button):
        await interaction.response.defer()
        #
        session = inprogresscol.find_one({"_id": interaction.message.id})
        if session:
            requested_by = session["requested_by"]
            channel_id = session["channel_id"]
            message_id = interaction.message.id
            r_profile_list = session["r_profile_list"]
            add_case_list = session["add_case_list"]
            title = session["title"]
            case_title = session["case_title"]
            user_id = session["user_id"]
            user = await bot.fetch_user(user_id)
            #
            thread = await bot.fetch_channel(channel_id)
            message = await thread.fetch_message(message_id)
            if requested_by == interaction.user.id or is_sr(interaction.user):
                r_profile = format_user_r_profile(user, r_profile_list, title)
                add_case = format_user_add_case(add_case_list, case_title)
                embeds = [r_profile, add_case]
                await message.edit(embeds=embeds, view=UserContributorView())

    @discord.ui.button(label="Add Proofs", style=discord.ButtonStyle.green, custom_id="userproofs:input")
    async def proofs_button(self, interaction, button):
        #
        session = inprogresscol.find_one({"_id": interaction.message.id})
        if session:
            requested_by = session["requested_by"]
            add_case_list = session["add_case_list"]
            #
            if requested_by == interaction.user.id:
                image_links = []
                add_case_list["proofs"] = []
                await interaction.response.send_message(
                    "Please send the images you would like to upload (max 10). **All images previously uploaded in this session have been removed.**",
                    ephemeral=True)

                # Wait for a follow-up message from the user in the same channel
                def check(m):
                    # Check if the message is from the same user, in the same channel, and has an attachment
                    return m.author == interaction.user and m.channel == interaction.channel

                try:
                    msg = await bot.wait_for('message', check=check, timeout=120.0)
                except asyncio.TimeoutError:
                    await interaction.followup.send("You took too long to upload an image.", ephemeral=True)
                    return
                if msg.attachments:
                    for attachment in msg.attachments:
                        # Ensure the attachment is an image (optional check)
                        if attachment.content_type and attachment.content_type.startswith('image/'):
                            try:
                                # 1. Download the file data using aiohttp
                                async with aiohttp.ClientSession() as http_session:
                                    async with http_session.get(attachment.url) as resp:
                                        # For this example, we just send back the image URL and filename
                                        data = io.BytesIO(await resp.read())
                                        file = discord.File(data, filename=attachment.filename)
                                        channel_to_send = bot.get_channel(PROOFS_CHANNEL)
                                        sent_message = await channel_to_send.send(file=file)
                                        if sent_message.attachments:
                                            new_image_url = sent_message.attachments[0].url
                                            image_links.append(new_image_url)
                                            add_case_list["proofs"].append(new_image_url)
                            except Exception:
                                await msg.channel.send(f"An error occurred with file {attachment.filename}")
                #
                inprogresscol.update_one(
                    {"_id": interaction.message.id},
                    {"$set": {"add_case_list": add_case_list}},
                )
                #
                image_embeds = image_links_to_embeds(image_links)
                await interaction.followup.send(f"Images received from {interaction.user.mention}.",
                                                embeds=image_embeds)

    @discord.ui.button(label="Show Proofs", style=discord.ButtonStyle.grey, custom_id="userproofs:showproofs")
    async def show_proofs_button(self, interaction, button):
        await interaction.response.defer()
        #
        session = inprogresscol.find_one({"_id": interaction.message.id})
        if session:
            requested_by = session["requested_by"]
            add_case_list = session["add_case_list"]
            user_id = session["user_id"]
            user = await bot.fetch_user(user_id)
            #
            if requested_by == interaction.user.id or is_sr(interaction.user):
                image_embeds = image_links_to_embeds(add_case_list["proofs"])
                await interaction.followup.send(f"Proofs for `{user.id}`",
                                                embeds=image_embeds, ephemeral=True)

    @discord.ui.button(label="Show Alts Proofs", style=discord.ButtonStyle.grey, custom_id="userproofs:showaltsproofs")
    async def show_alts_proofs_button(self, interaction, button):
        await interaction.response.defer()
        #
        session = inprogresscol.find_one({"_id": interaction.message.id})
        if session:
            requested_by = session["requested_by"]
            r_profile_list = session["r_profile_list"]
            user_id = session["user_id"]
            user = await bot.fetch_user(user_id)
            #
            if requested_by == interaction.user.id or is_sr(interaction.user):
                image_embeds = image_links_to_embeds(r_profile_list[2])
                await interaction.followup.send(f"Alts Proofs for `{user.id}`",
                                                embeds=image_embeds, ephemeral=True)

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.grey, custom_id="userproofs:cancel")
    async def cancel_button(self, interaction, button):
        await interaction.response.defer()
        #
        session = inprogresscol.find_one({"_id": interaction.message.id})
        if session:
            requested_by = session["requested_by"]
            channel_id = session["channel_id"]
            message_id = interaction.message.id
            #
            thread = await bot.fetch_channel(channel_id)
            message = await thread.fetch_message(message_id)
            if requested_by == interaction.user.id or is_sr(interaction.user):
                inprogresscol.delete_one({"_id": interaction.message.id})
                await message.edit(content=f"**Cancelled by {interaction.user.mention}.**", view=None)

    @discord.ui.button(label="Accept", style=discord.ButtonStyle.grey, custom_id="userproofs:accept")
    async def accept_button(self, interaction, button):
        await interaction.response.defer()
        #
        session = inprogresscol.find_one({"_id": interaction.message.id})
        if session:
            requested_by = session["requested_by"]
            channel_id = session["channel_id"]
            message_id = interaction.message.id
            r_profile_list = session["r_profile_list"]
            add_case_list = session["add_case_list"]
            title = session["title"]
            case_title = session["case_title"]
            user_id = session["user_id"]
            user = await bot.fetch_user(user_id)
            #
            thread = await bot.fetch_channel(channel_id)
            message = await thread.fetch_message(message_id)
            if is_sr(interaction.user) and interaction.user.id != requested_by:
                accepted_by = interaction.user
                add_case_list["accepted_by"] = f"<@{interaction.user.id}>"
                #
                r_profile = format_user_r_profile(user, r_profile_list, title)
                add_case = format_user_add_case(add_case_list, case_title)
                embeds = [r_profile, add_case]
                #
                vote_channel = bot.get_channel(VOTE_CHANNEL)
                agree_users = []
                disagree_users = []
                alts_proofs_embeds = image_links_to_embeds(r_profile_list[2])
                proofs_embeds = image_links_to_embeds(add_case_list["proofs"])
                new_report_message = await vote_channel.send(content=f"New report on `{user.id}`")
                new_report_thread = await new_report_message.create_thread(name=f"{user.id}")
                await new_report_thread.send(f"<@&{ticket_ping}>")
                vote_msg = await new_report_thread.send(
                    content=f"Report accepted by {accepted_by.mention}.\nLink to thread: <#{channel_id}>\n\nAgree: 0\nDisagree: 0",
                    embeds=embeds, view=UserVoteView())
                vote_channel_id = vote_msg.channel.id
                vote_message_id = vote_msg.id
                old_session = inprogresscol.find_one({"user_id": user_id})
                if old_session:
                    inprogresscol.delete_one({"_id": old_session["_id"]})
                inprogresscol.insert_one({
                    "_id": vote_message_id,
                    "user_id": user_id,
                    "requested_by": requested_by,
                    "channel_id": channel_id,
                    "message_id": interaction.message.id,
                    "r_profile_list": r_profile_list,
                    "add_case_list": add_case_list,
                    "title": title,
                    "case_title": case_title,
                    "vote_channel_id": vote_channel_id,
                    "accepted_by": accepted_by.id,
                    "agree_users": agree_users,
                    "disagree_users": disagree_users,
                })
                await new_report_thread.send(content=f"Alts Proofs for `{user.id}`", embeds=alts_proofs_embeds)
                await new_report_thread.send(content=f"Proofs for `{user.id}`", embeds=proofs_embeds)
                await old_message_edit_queue.put(
                    (message, {"content": "Report has been submitted for voting.", "embeds": embeds, "view": None}))
            else:
                await interaction.followup.send("You do not have permission to accept the report for voting.",
                                                ephemeral=True)


# edit user
class EditUserReportView(discord.ui.View):
    def __init__(self, user, user_profile, requested_by, current_case):
        super().__init__(timeout=3600)
        self.user = user
        self.user_profile = user_profile
        self.requested_by = requested_by
        self.current_case = current_case

    @discord.ui.button(emoji="<:leftarrow:1458096658062770176>", style=discord.ButtonStyle.grey, custom_id="edituserreport:prev",
                       row=0)
    async def prev_button(self, interaction, button):
        await interaction.response.defer()
        #
        user = self.user
        user_profile = self.user_profile
        requested_by = self.requested_by
        current_case = self.current_case
        #
        no_of_cases = len(user_profile) - 2
        #
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
                prev_index = current_case - 2
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
                                                             view=EditUserReportView(user, user_profile, requested_by,
                                                                                   current_case))

    @discord.ui.button(emoji="<:rightarrow:1458096774521553038>", style=discord.ButtonStyle.grey, custom_id="edituserreport:next",
                       row=0)
    async def next_button(self, interaction, button):
        await interaction.response.defer()
        #
        user = self.user
        user_profile = self.user_profile
        requested_by = self.requested_by
        current_case = self.current_case
        #
        no_of_cases = len(user_profile) - 2
        #
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
                                                         view=EditUserReportView(user, user_profile, requested_by,
                                                                               current_case))

    @discord.ui.button(label="Proofs", style=discord.ButtonStyle.grey, custom_id="edituserreport:proofs", row=0)
    async def proofs_button(self, interaction, button):
        await interaction.response.defer()
        #
        user = self.user
        user_profile = self.user_profile
        current_case = self.current_case
        #
        no_of_cases = len(user_profile) - 2
        cases = []
        for i in range(1, no_of_cases + 1):
            cases.append(user_profile[str(i)])
        image_links = cases[current_case - 1]["proofs"]
        image_embeds = image_links_to_embeds(image_links)
        await interaction.followup.send(f"Proofs for `{user.id}`", embeds=image_embeds, ephemeral=True)

    @discord.ui.button(label="Alts", style=discord.ButtonStyle.grey, custom_id="edituserreport:altsproofs", row=0)
    async def alts_proofs_button(self, interaction, button):
        await interaction.response.defer()
        #
        user = self.user
        user_profile = self.user_profile
        #
        r_profile_list = user_profile["r_profile_list"]
        image_links = r_profile_list[2]
        image_embeds = image_links_to_embeds(image_links)
        await interaction.followup.send(f"Alts Proofs for `{user.id}`", embeds=image_embeds, ephemeral=True)

    @discord.ui.button(label="Edit Alts", style=discord.ButtonStyle.primary, custom_id="edituserreport:editalts", row=1)
    async def edit_alts_button(self, interaction, button):
        #
        user = self.user
        user_profile = self.user_profile
        requested_by = self.requested_by
        #
        await interaction.response.defer()
        existing_entry = inprogresscol.find_one({"user_id": user.id})
        if existing_entry:
            # ongoing vote
            if "vote_channel_id" in existing_entry:
                vote_channel_id = existing_entry["vote_channel_id"]
                vote_message_id = existing_entry["_id"]
                vote_channel = bot.get_channel(vote_channel_id)
                if not vote_channel:
                    vote_channel = await bot.fetch_channel(vote_channel_id)
                try:
                    vote_message = await vote_channel.fetch_message(vote_message_id)
                except discord.NotFound:
                    return await interaction.followup.send(
                        "This message could not be found. It may have been deleted.", ephemeral=True)
                await interaction.followup.send(
                    f"There already exists an ongoing vote on `{user.id}`: {vote_message.jump_url}")
            # ongoing report
            else:
                channel_id = existing_entry["channel_id"]
                message_id = existing_entry["_id"]
                thread = await bot.fetch_channel(channel_id)
                try:
                    message = await thread.fetch_message(message_id)
                except discord.NotFound:
                    return await interaction.followup.send(
                        "This message could not be found. It may have been deleted.", ephemeral=True)
                await interaction.followup.send(
                    f"There already exists an ongoing report on `{user.id}`: {message.jump_url}")
            return
        if requested_by == interaction.user:
            await interaction.edit_original_response(view=None)
            msg = await interaction.followup.send(f"Editing alts for `{user.id}`...", wait=True)
            r_profile_list = user_profile["r_profile_list"]
            cases = []
            no_of_cases = len(user_profile) - 2
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
            channel_id = msg.channel.id
            message_id = msg.id
            r_profile = format_user_r_profile(user, r_profile_list, title)
            reason = ""
            reason_embed = discord.Embed(title="Reason", description=reason)
            try:
                inprogresscol.insert_one({"_id": message_id,
                                          "user_id": user.id,
                                          "requested_by": requested_by.id,
                                          "channel_id": channel_id,
                                          "r_profile_list": r_profile_list,
                                          "title": title,
                                          "reason": reason,
                                          })
            except DuplicateKeyError:
                pass
            embeds = [r_profile, reason_embed]
            await msg.edit(embeds=embeds, view=EditAltsOnlyView())
        elif is_active_staff(interaction.user):
            await interaction.followup.send(
                "This was requested by " + f"{requested_by.mention}, you cannot interact with this component.",
                ephemeral=True)
        else:
            await interaction.followup.send("You do not have permission to use this button.", ephemeral=True)

    @discord.ui.button(label="Add Report", style=discord.ButtonStyle.red, custom_id="edituserreport:addreport", row=1)
    async def add_report_button(self, interaction, button):
        #
        user = self.user
        user_profile = self.user_profile
        requested_by = self.requested_by
        current_case = self.current_case
        #
        await interaction.response.defer()
        existing_entry = inprogresscol.find_one({"user_id": user.id})
        if existing_entry:
            # ongoing vote
            if "vote_channel_id" in existing_entry:
                vote_channel_id = existing_entry["vote_channel_id"]
                vote_message_id = existing_entry["_id"]
                vote_channel = bot.get_channel(vote_channel_id)
                if not vote_channel:
                    vote_channel = await bot.fetch_channel(vote_channel_id)
                try:
                    vote_message = await vote_channel.fetch_message(vote_message_id)
                except discord.NotFound:
                    return await interaction.followup.send(
                        "This message could not be found. It may have been deleted.", ephemeral=True)
                await interaction.followup.send(
                    f"There already exists an ongoing vote on `{user.id}`: {vote_message.jump_url}")
            # ongoing report
            else:
                channel_id = existing_entry["channel_id"]
                message_id = existing_entry["_id"]
                thread = await bot.fetch_channel(channel_id)
                try:
                    message = await thread.fetch_message(message_id)
                except discord.NotFound:
                    return await interaction.followup.send(
                        "This message could not be found. It may have been deleted.", ephemeral=True)
                await interaction.followup.send(
                    f"There already exists an ongoing report on `{user.id}`: {message.jump_url}")
            return
        if requested_by == interaction.user:
            await interaction.edit_original_response(view=None)
            msg = await interaction.followup.send(f"Adding report on `{user.id}`...", wait=True)
            r_profile_list = user_profile["r_profile_list"]
            cases = []
            no_of_cases = len(user_profile) - 2
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
            #
            case_title = "TBC"
            add_case_list = {
                "date_added": f"<t:{round(int(discord.utils.utcnow().timestamp()))}:D> (<t:{round(int(discord.utils.utcnow().timestamp()))}:R>)",
                "games": "", "tags": "", "reason": "", "contributor": "", "staff": f"{interaction.user.mention}",
                "accepted_by": "", "proofs": []}
            channel_id = msg.channel.id
            message_id = msg.id
            try:
                inprogresscol.insert_one({"_id": message_id,
                                          "user_id": user.id,
                                          "requested_by": requested_by.id,
                                          "channel_id": channel_id,
                                          "r_profile_list": r_profile_list,
                                          "add_case_list": add_case_list,
                                          "title": title,
                                          "case_title": case_title
                                          })
            except DuplicateKeyError:
                pass
            r_profile = format_user_r_profile(user, r_profile_list, title)
            add_case = format_user_add_case(add_case_list, case_title)
            embeds = [r_profile, add_case]
            await msg.edit(embeds=embeds, view=AddReportAltsView())
        elif is_active_staff(interaction.user):
            await interaction.followup.send(
                "This was requested by " + f"{requested_by.mention}, you cannot interact with this component.",
                ephemeral=True)
        else:
            await interaction.followup.send("You do not have permission to use this button.", ephemeral=True)

    @discord.ui.button(label="Appeal", style=discord.ButtonStyle.green, custom_id="edituserreport:appeal", row=1)
    async def appeal_button(self, interaction, button):
        #
        user = self.user
        user_profile = self.user_profile
        requested_by = self.requested_by
        current_case = self.current_case
        #
        await interaction.response.defer()
        existing_entry = inprogresscol.find_one({"user_id": user.id})
        if existing_entry:
            # ongoing vote
            if "vote_channel_id" in existing_entry:
                vote_channel_id = existing_entry["vote_channel_id"]
                vote_message_id = existing_entry["_id"]
                vote_channel = bot.get_channel(vote_channel_id)
                if not vote_channel:
                    vote_channel = await bot.fetch_channel(vote_channel_id)
                try:
                    vote_message = await vote_channel.fetch_message(vote_message_id)
                except discord.NotFound:
                    return await interaction.followup.send(
                        "This message could not be found. It may have been deleted.", ephemeral=True)
                await interaction.followup.send(
                    f"There already exists an ongoing vote on `{user.id}`: {vote_message.jump_url}")
            # ongoing report
            else:
                channel_id = existing_entry["channel_id"]
                message_id = existing_entry["_id"]
                thread = await bot.fetch_channel(channel_id)
                try:
                    message = await thread.fetch_message(message_id)
                except discord.NotFound:
                    return await interaction.followup.send(
                        "This message could not be found. It may have been deleted.", ephemeral=True)
                await interaction.followup.send(
                    f"There already exists an ongoing report on `{user.id}`: {message.jump_url}")
            return
        if requested_by == interaction.user:
            await interaction.edit_original_response(view=None)
            msg = await interaction.followup.send(f"Appealing for `{user.id}`...", wait=True)
            r_profile_list = user_profile["r_profile_list"]
            cases = []
            no_of_cases = len(user_profile) - 2
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
            current_index = current_case - 1
            add_case_list = user_profile[str(current_case)]
            case_tags = cases[current_index]["tags"].split(", ")
            case_title = case_tags[0]
            channel_id = msg.channel.id
            message_id = msg.id
            r_profile = format_user_r_profile(user, r_profile_list, title)
            reason = ""
            reason_embed = discord.Embed(title="Reason", colour=0x1dcca9, description=reason)
            try:
                inprogresscol.insert_one({"_id": message_id,
                                          "user_id": user.id,
                                          "requested_by": requested_by.id,
                                          "channel_id": channel_id,
                                          "r_profile_list": r_profile_list,
                                          "add_case_list": add_case_list,
                                          "title": title,
                                          "case_title": case_title,
                                          "reason": reason
                                          })
            except DuplicateKeyError:
                pass
            add_case = format_user_add_case(add_case_list, case_title)
            embeds = [r_profile, add_case, reason_embed]
            await msg.edit(embeds=embeds, view=UserAppealView())
        elif is_active_staff(interaction.user):
            await interaction.followup.send(
                "This was requested by " + f"{requested_by.mention}, you cannot interact with this component.",
                ephemeral=True)
        else:
            await interaction.followup.send("You do not have permission to use this button.", ephemeral=True)


# edit alts only
class EditAltsOnlyView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
    @discord.ui.button(label="Add Alts", style=discord.ButtonStyle.green, custom_id="editaltsonly:addalts")
    async def add_alts_button(self, interaction, button):
        session = inprogresscol.find_one({"_id": interaction.message.id})
        if session:
            requested_by = session["requested_by"]
            if requested_by == interaction.user.id:
                await interaction.response.send_modal(AddAltsOnlyModal())

    @discord.ui.button(label="Remove Alts", style=discord.ButtonStyle.red, custom_id="editaltsonly:removealts")
    async def remove_alts_button(self, interaction, button):
        session = inprogresscol.find_one({"_id": interaction.message.id})
        if session:
            requested_by = session["requested_by"]
            if requested_by == interaction.user.id:
                await interaction.response.send_modal(RemoveAltsOnlyModal())

    @discord.ui.button(label="Add Alts Proofs", style=discord.ButtonStyle.green, custom_id="editaltsonly:addaltsproofs")
    async def add_alts_proofs_button(self, interaction, button):
        session = inprogresscol.find_one({"_id": interaction.message.id})
        if session:
            requested_by = session["requested_by"]
            r_profile_list = session["r_profile_list"]
            if requested_by == interaction.user.id:
                image_links = []
                original_image_links = r_profile_list[2].copy()
                await interaction.response.send_message(
                    f"Please send the images you would like to upload (max {10 - len(r_profile_list[2])}).",
                    ephemeral=True)
                def check(m):
                    return m.author == interaction.user and m.channel == interaction.channel

                try:
                    msg = await bot.wait_for('message', check=check, timeout=120.0)
                except asyncio.TimeoutError:
                    await interaction.followup.send("You took too long to upload an image.", ephemeral=True)
                    return
                if msg.attachments:
                    for attachment in msg.attachments:
                        # Ensure the attachment is an image (optional check)
                        if attachment.content_type and attachment.content_type.startswith('image/'):
                            try:
                                # 1. Download the file data using aiohttp
                                async with aiohttp.ClientSession() as http_session:
                                    async with http_session.get(attachment.url) as resp:
                                        # For this example, we just send back the image URL and filename
                                        data = io.BytesIO(await resp.read())
                                        file = discord.File(data, filename=attachment.filename)
                                        channel_to_send = bot.get_channel(PROOFS_CHANNEL)
                                        sent_message = await channel_to_send.send(file=file)
                                        if sent_message.attachments:
                                            new_image_url = sent_message.attachments[0].url
                                            image_links.append(new_image_url)
                                            r_profile_list[2].append(new_image_url)
                            except Exception:
                                await msg.channel.send(f"An error occurred with file {attachment.filename}")
                if len(r_profile_list[2]) > 10:
                    await interaction.followup.send(
                        f"There are a total of {len(r_profile_list[2])} images, exceeding the max limit of 10. Please try again.")
                    r_profile_list[2] = original_image_links
                else:
                    inprogresscol.update_one(
                        {"_id": interaction.message.id},
                        {"$set": {"r_profile_list": r_profile_list}}
                    )
                    #
                    image_embeds = image_links_to_embeds(image_links)
                    await interaction.followup.send(f"Images received from {interaction.user.mention}.",
                                                    embeds=image_embeds)

    @discord.ui.button(label="Remove Alts Proofs", style=discord.ButtonStyle.red, custom_id="editaltsonly:removealtsproofs")
    async def remove_alts_proofs_button(self, interaction, button):
        session = inprogresscol.find_one({"_id": interaction.message.id})
        if session:
            requested_by = session["requested_by"]
            r_profile_list = session["r_profile_list"]
            if requested_by == interaction.user.id:
                await interaction.response.send_message(
                    f"Please list image(s) you would like to remove, from 1 to {len(r_profile_list[2])}, with a space between each number.",
                    ephemeral=True)
                def check(m):
                    return m.author == interaction.user and m.channel == interaction.channel

                try:
                    msg = await bot.wait_for('message', check=check, timeout=120.0)
                except asyncio.TimeoutError:
                    await interaction.followup.send("You took too long to respond.", ephemeral=True)
                    return
                try:
                    to_remove = msg.content.split()
                    indices_to_remove = []
                    for i in to_remove:
                        indices_to_remove.append(int(i) - 1)
                    indices_to_remove = set(indices_to_remove)
                except Exception:
                    await interaction.followup.send("Invalid response. Please try again.", ephemeral=True)
                else:
                    images_removed = []
                    for i in indices_to_remove:
                        if 0 <= i < len(r_profile_list[2]):
                            images_removed.append(r_profile_list[2][i])
                    r_profile_list[2] = [value for index, value in enumerate(r_profile_list[2]) if
                                         index not in indices_to_remove]
                    inprogresscol.update_one(
                        {"_id": interaction.message.id},
                        {"$set": {"r_profile_list": r_profile_list}}
                    )
                    #
                    image_embeds = image_links_to_embeds(images_removed)
                    await interaction.followup.send(f"Images removed by {interaction.user.mention}.",
                                                    embeds=image_embeds)

    @discord.ui.button(label="Show Alts Proofs", style=discord.ButtonStyle.grey, custom_id="editaltsonly:showaltsproofs")
    async def show_alts_proofs_button(self, interaction, button):
        await interaction.response.defer()
        session = inprogresscol.find_one({"_id": interaction.message.id})
        if session:
            requested_by = session["requested_by"]
            r_profile_list = session["r_profile_list"]
            user_id = session["user_id"]
            user = await bot.fetch_user(user_id)
            if requested_by == interaction.user.id or is_sr(interaction.user):
                image_embeds = image_links_to_embeds(r_profile_list[2])
                await interaction.followup.send(f"Alts Proofs for `{user.id}`",
                                                embeds=image_embeds, ephemeral=True)

    @discord.ui.button(label="Reason", style=discord.ButtonStyle.primary, custom_id="editaltsonly:reason")
    async def reason_button(self, interaction, button):
        #
        session = inprogresscol.find_one({"_id": interaction.message.id})
        if session:
            requested_by = session["requested_by"]
            if requested_by == interaction.user.id:
                await interaction.response.send_modal(AltsReasonModal())

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.grey, custom_id="editaltsonly:cancel")
    async def cancel_button(self, interaction, button):
        await interaction.response.defer()
        session = inprogresscol.find_one({"_id": interaction.message.id})
        if session:
            requested_by = session["requested_by"]
            channel_id = session["channel_id"]
            message_id = interaction.message.id
            thread = await bot.fetch_channel(channel_id)
            message = await thread.fetch_message(message_id)
            if requested_by == interaction.user.id or is_sr(interaction.user):
                inprogresscol.delete_one({"_id": interaction.message.id})
                await message.edit(content=f"**Cancelled by {interaction.user.mention}.**", view=None)

    @discord.ui.button(label="Accept", style=discord.ButtonStyle.grey, custom_id="editaltsonly:accept")
    async def accept_button(self, interaction, button):
        await interaction.response.defer()
        #
        session = inprogresscol.find_one({"_id": interaction.message.id})
        if session:
            requested_by = session["requested_by"]
            channel_id = session["channel_id"]
            message_id = interaction.message.id
            r_profile_list = session["r_profile_list"]
            title = session["title"]
            reason = session["reason"]
            user_id = session["user_id"]
            user = await bot.fetch_user(user_id)
            thread = await bot.fetch_channel(channel_id)
            message = await thread.fetch_message(message_id)
            if is_sr(interaction.user) and interaction.user.id != requested_by:
                accepted_by = interaction.user
                r_profile = format_user_r_profile(user, r_profile_list, title)
                #
                vote_channel = bot.get_channel(VOTE_CHANNEL)
                agree_users = []
                disagree_users = []
                all_images_to_show = r_profile_list[2]
                image_embeds = image_links_to_embeds(all_images_to_show)
                new_report_message = await vote_channel.send(content=f"Edited alts for `{user.id}`")
                new_report_thread = await new_report_message.create_thread(name=f"{user.id}")
                await new_report_thread.send(f"<@&{ticket_ping}>")
                vote_msg = await new_report_thread.send(
                    content=f"Report accepted by {accepted_by.mention}.\nLink to thread: <#{channel_id}>\n\nAgree: 0\nDisagree: 0",
                    embed=r_profile, view=UserVoteView())
                vote_channel_id = vote_msg.channel.id
                vote_message_id = vote_msg.id
                old_session = inprogresscol.find_one({"user_id": user_id})
                if old_session:
                    inprogresscol.delete_one({"_id": old_session["_id"]})
                inprogresscol.insert_one({
                    "_id": vote_message_id,
                    "user_id": user_id,
                    "requested_by": requested_by,
                    "channel_id": channel_id,
                    "message_id": interaction.message.id,
                    "r_profile_list": r_profile_list,
                    "title": title,
                    "reason": reason,
                    "vote_channel_id": vote_channel_id,
                    "accepted_by": accepted_by.id,
                    "agree_users": agree_users,
                    "disagree_users": disagree_users,
                })
                await new_report_thread.send(content=f"Alts Proofs for `{user.id}`", embeds=image_embeds)
                reason_embed = discord.Embed(title="Reason", description=reason)
                await new_report_thread.send(content=f"Reason for change(s)", embed=reason_embed)
                embeds = [r_profile, reason_embed]
                await old_message_edit_queue.put(
                    (message, {"content": "Report has been submitted for voting.", "embeds": embeds, "view": None}))
            else:
                await interaction.followup.send("You do not have permission to accept the report for voting.",
                                                ephemeral=True)
class AddAltsOnlyModal(discord.ui.Modal, title="Add Alts"):
    alts = discord.ui.TextInput(label="Add Alts", placeholder="List alts here and leave a space between IDs.",
                                required=True, style=discord.TextStyle.short)
    def __init__(self):
        super().__init__(timeout=None)
    async def on_submit(self, interaction):
        await interaction.response.defer()
        session = inprogresscol.find_one({"_id": interaction.message.id})
        if session:
            channel_id = session["channel_id"]
            message_id = interaction.message.id
            r_profile_list = session["r_profile_list"]
            title = session["title"]
            reason = session["reason"]
            user_id = session["user_id"]
            user = await bot.fetch_user(user_id)
            #
            original_alts = r_profile_list[0].strip("`").split() if r_profile_list[0] else []
            thread = await bot.fetch_channel(channel_id)
            message = await thread.fetch_message(message_id)
            alts_input = self.alts.value
            alts_list = alts_input.split()
            valid_alts = []
            for alt in alts_list:
                try:
                    alt_id = await bot.fetch_user(int(alt))
                except Exception:
                    pass
                else:
                    if alt_id.id not in valid_alts and str(alt_id.id) not in original_alts and alt_id != user:
                        valid_alts.append(alt_id.id)
            if len(valid_alts) != 0:
                r_profile_list[0] = alts_string(original_alts + valid_alts)
            inprogresscol.update_one(
                {"_id": interaction.message.id},
                {"$set": {"r_profile_list": r_profile_list}}
            )
            r_profile = format_user_r_profile(user, r_profile_list, title)
            reason_embed = discord.Embed(title="Reason", description=reason)
            embeds = [r_profile, reason_embed]
            await message.edit(embeds=embeds, view=EditAltsOnlyView())
class RemoveAltsOnlyModal(discord.ui.Modal, title="Remove Alts"):
    alts = discord.ui.TextInput(label="Remove Alts", placeholder="List alts here and leave a space between IDs.",
                                required=True, style=discord.TextStyle.short)
    def __init__(self):
        super().__init__(timeout=None)
    async def on_submit(self, interaction):
        await interaction.response.defer()
        session = inprogresscol.find_one({"_id": interaction.message.id})
        if session:
            channel_id = session["channel_id"]
            message_id = interaction.message.id
            r_profile_list = session["r_profile_list"]
            title = session["title"]
            reason = session["reason"]
            user_id = session["user_id"]
            user = await bot.fetch_user(user_id)
            #
            original_alts = r_profile_list[0].strip("`").split() if r_profile_list[0] else []
            thread = await bot.fetch_channel(channel_id)
            message = await thread.fetch_message(message_id)
            alts_input = self.alts.value
            alts_list = alts_input.split()
            valid_alts = []
            for alt in alts_list:
                try:
                    alt_id = await bot.fetch_user(int(alt))
                except Exception:
                    pass
                else:
                    if alt_id.id not in valid_alts and str(alt_id.id) in original_alts:
                        valid_alts.append(str(alt_id.id))
            if len(valid_alts) != 0:
                remaining_alts = [element for element in original_alts if element not in set(valid_alts)]
                if len(remaining_alts) != 0:
                    r_profile_list[0] = alts_string(remaining_alts)
                else:
                    r_profile_list[0] = ""
            #
            inprogresscol.update_one(
                {"_id": interaction.message.id},
                {"$set": {"r_profile_list": r_profile_list}}
            )
            r_profile = format_user_r_profile(user, r_profile_list, title)
            reason_embed = discord.Embed(title="Reason", description=reason)
            embeds = [r_profile, reason_embed]
            await message.edit(embeds=embeds, view=EditAltsOnlyView())
class AltsReasonModal(discord.ui.Modal, title="Reason"):
    reason_input = discord.ui.TextInput(label="Reason", placeholder="Please explain the change(s) you have made.",
                                        required=True, style=discord.TextStyle.long)

    def __init__(self):
        super().__init__(timeout=None)

    async def on_submit(self, interaction):
        await interaction.response.defer()
        session = inprogresscol.find_one({"_id": interaction.message.id})
        if session:
            channel_id = session["channel_id"]
            message_id = interaction.message.id
            r_profile_list = session["r_profile_list"]
            title = session["title"]
            reason = session["reason"]
            user_id = session["user_id"]
            user = await bot.fetch_user(user_id)
            thread = await bot.fetch_channel(channel_id)
            message = await thread.fetch_message(message_id)
            reason = str(self.reason_input.value)
            inprogresscol.update_one(
                {"_id": interaction.message.id},
                {"$set": {"reason": reason}}
            )
            r_profile = format_user_r_profile(user, r_profile_list, title)
            reason_embed = discord.Embed(title="Reason", description=reason)
            embeds = [r_profile, reason_embed]
            await message.edit(embeds=embeds, view=EditAltsOnlyView())


# user appeal
class UserAppealView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Add Alts", style=discord.ButtonStyle.green, custom_id="userappeal:addalts")
    async def add_alts_button(self, interaction, button):
        session = inprogresscol.find_one({"_id": interaction.message.id})
        if session:
            requested_by = session["requested_by"]
            if requested_by == interaction.user.id:
                await interaction.response.send_modal(AddAltsAppealModal())

    @discord.ui.button(label="Remove Alts", style=discord.ButtonStyle.red, custom_id="userappeal:removealts")
    async def remove_alts_button(self, interaction, button):
        session = inprogresscol.find_one({"_id": interaction.message.id})
        if session:
            requested_by = session["requested_by"]
            if requested_by == interaction.user.id:
                await interaction.response.send_modal(RemoveAltsAppealModal())

    @discord.ui.button(label="Add Alts Proofs", style=discord.ButtonStyle.green, custom_id="userappeal:addaltsproofs")
    async def add_alts_proofs_button(self, interaction, button):
        session = inprogresscol.find_one({"_id": interaction.message.id})
        if session:
            requested_by = session["requested_by"]
            r_profile_list = session["r_profile_list"]
            if requested_by == interaction.user.id:
                image_links = []
                original_image_links = r_profile_list[2].copy()
                await interaction.response.send_message(
                    f"Please send the images you would like to upload (max {10 - len(r_profile_list[2])}).",
                    ephemeral=True)
                def check(m):
                    return m.author == interaction.user and m.channel == interaction.channel
                try:
                    msg = await bot.wait_for('message', check=check, timeout=120.0)
                except asyncio.TimeoutError:
                    await interaction.followup.send("You took too long to upload an image.", ephemeral=True)
                    return
                if msg.attachments:
                    for attachment in msg.attachments:
                        # Ensure the attachment is an image (optional check)
                        if attachment.content_type and attachment.content_type.startswith('image/'):
                            try:
                                # 1. Download the file data using aiohttp
                                async with aiohttp.ClientSession() as http_session:
                                    async with http_session.get(attachment.url) as resp:
                                        # For this example, we just send back the image URL and filename
                                        data = io.BytesIO(await resp.read())
                                        file = discord.File(data, filename=attachment.filename)
                                        channel_to_send = bot.get_channel(PROOFS_CHANNEL)
                                        sent_message = await channel_to_send.send(file=file)
                                        if sent_message.attachments:
                                            new_image_url = sent_message.attachments[0].url
                                            image_links.append(new_image_url)
                                            r_profile_list[2].append(new_image_url)
                            except Exception:
                                await msg.channel.send(f"An error occurred with file {attachment.filename}")
                if len(r_profile_list[2]) > 10:
                    await interaction.followup.send(
                        f"There are a total of {len(r_profile_list[2])} images, exceeding the max limit of 10. Please try again.")
                    r_profile_list[2] = original_image_links
                else:
                    inprogresscol.update_one(
                        {"_id": interaction.message.id},
                        {"$set": {"r_profile_list": r_profile_list}}
                    )
                    image_embeds = image_links_to_embeds(image_links)
                    await interaction.followup.send(f"Images received from {interaction.user.mention}.",
                                                    embeds=image_embeds)

    @discord.ui.button(label="Remove Alts Proofs", style=discord.ButtonStyle.red, custom_id="userappeal:removealtsproofs")
    async def remove_alts_proofs_button(self, interaction, button):
        session = inprogresscol.find_one({"_id": interaction.message.id})
        if session:
            requested_by = session["requested_by"]
            r_profile_list = session["r_profile_list"]
            if requested_by == interaction.user.id:
                await interaction.response.send_message(
                    f"Please list image(s) you would like to remove, from 1 to {len(r_profile_list[2])}, with a space between each number.",
                    ephemeral=True)
                # Wait for a follow-up message from the user in the same channel
                def check(m):
                    # Check if the message is from the same user, in the same channel
                    return m.author == interaction.user and m.channel == interaction.channel
                try:
                    msg = await bot.wait_for('message', check=check, timeout=120.0)
                except asyncio.TimeoutError:
                    await interaction.followup.send("You took too long to respond.", ephemeral=True)
                    return
                try:
                    to_remove = msg.content.split()
                    indices_to_remove = []
                    for i in to_remove:
                        indices_to_remove.append(int(i) - 1)
                    indices_to_remove = set(indices_to_remove)
                except Exception:
                    await interaction.followup.send("Invalid response. Please try again.", ephemeral=True)
                else:
                    images_removed = []
                    for i in indices_to_remove:
                        if 0 <= i < len(r_profile_list[2]):
                            images_removed.append(r_profile_list[2][i])
                    r_profile_list[2] = [value for index, value in enumerate(r_profile_list[2]) if
                                         index not in indices_to_remove]
                    inprogresscol.update_one(
                        {"_id": interaction.message.id},
                        {"$set": {"r_profile_list": r_profile_list}}
                    )
                    image_embeds = image_links_to_embeds(images_removed)
                    await interaction.followup.send(f"Images removed by {interaction.user.mention}.",
                                                    embeds=image_embeds)

    @discord.ui.button(label="Show Alts Proofs", style=discord.ButtonStyle.grey, custom_id="userappeal:showaltsproofs")
    async def show_alts_proofs_button(self, interaction, button):
        await interaction.response.defer()
        #
        session = inprogresscol.find_one({"_id": interaction.message.id})
        if session:
            requested_by = session["requested_by"]
            r_profile_list = session["r_profile_list"]
            user_id = session["user_id"]
            user = await bot.fetch_user(user_id)
        #
            if requested_by == interaction.user.id or is_sr(interaction.user):
                image_embeds = image_links_to_embeds(r_profile_list[2])
                await interaction.followup.send(f"Alts Proofs for `{user.id}`",
                                                embeds=image_embeds, ephemeral=True)

    @discord.ui.button(label="Reason", style=discord.ButtonStyle.primary, custom_id="userappeal:reason")
    async def reason_button(self, interaction, button):
        #
        session = inprogresscol.find_one({"_id": interaction.message.id})
        if session:
            requested_by = session["requested_by"]
            #
            if requested_by == interaction.user.id:
                await interaction.response.send_modal(UserAppealReasonModal())

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.grey, custom_id="userappeal:cancel")
    async def cancel_button(self, interaction, button):
        await interaction.response.defer()
        session = inprogresscol.find_one({"_id": interaction.message.id})
        if session:
            requested_by = session["requested_by"]
            channel_id = session["channel_id"]
            message_id = interaction.message.id
            thread = await bot.fetch_channel(channel_id)
            message = await thread.fetch_message(message_id)
            if requested_by == interaction.user.id or is_sr(interaction.user):
                inprogresscol.delete_one({"_id": interaction.message.id})
                await message.edit(content=f"**Cancelled by {interaction.user.mention}.**", view=None)

    @discord.ui.button(label="Accept", style=discord.ButtonStyle.grey, custom_id="userappeal:accept")
    async def accept_button(self, interaction, button):
        await interaction.response.defer()
        #
        session = inprogresscol.find_one({"_id": interaction.message.id})
        if session:
            requested_by = session["requested_by"]
            channel_id = session["channel_id"]
            message_id = interaction.message.id
            r_profile_list = session["r_profile_list"]
            add_case_list = session["add_case_list"]
            title = session["title"]
            case_title = session["case_title"]
            reason = session["reason"]
            user_id = session["user_id"]
            user = await bot.fetch_user(user_id)
            thread = await bot.fetch_channel(channel_id)
            message = await thread.fetch_message(message_id)
            if is_sr(interaction.user) and interaction.user.id != requested_by:
                accepted_by = interaction.user
                r_profile = format_user_r_profile(user, r_profile_list, title)
                add_case = format_user_add_case(add_case_list, case_title)
                reason_embed = discord.Embed(title="Reason", colour=0x1DCCA9, description=reason)
                embeds = [r_profile, add_case, reason_embed]
                #
                vote_channel = bot.get_channel(VOTE_CHANNEL)
                agree_users = []
                disagree_users = []
                alts_proofs_embeds = image_links_to_embeds(r_profile_list[2])
                proofs_embeds = image_links_to_embeds(add_case_list["proofs"])
                add_case_list = [add_case_list]
                new_report_message = await vote_channel.send(content=f"Appeal on `{user.id}`")
                new_report_thread = await new_report_message.create_thread(name=f"{user.id}")
                await new_report_thread.send(f"<@&{ticket_ping}>")
                vote_msg = await new_report_thread.send(
                    content=f"Appeal accepted by <@{accepted_by.id}>.\nLink to thread: <#{channel_id}>\n\nAgree: 0\nDisagree: 0",
                    embeds=embeds, view=UserVoteView())
                vote_channel_id = vote_msg.channel.id
                vote_message_id = vote_msg.id
                old_session = inprogresscol.find_one({"user_id": user_id})
                if old_session:
                    inprogresscol.delete_one({"_id": old_session["_id"]})
                inprogresscol.insert_one({
                    "_id": vote_message_id,
                    "user_id": user_id,
                    "requested_by": requested_by,
                    "channel_id": channel_id,
                    "message_id": interaction.message.id,
                    "r_profile_list": r_profile_list,
                    "add_case_list": add_case_list,
                    "title": title,
                    "case_title": case_title,
                    "reason": reason,
                    "vote_channel_id": vote_channel_id,
                    "accepted_by": accepted_by.id,
                    "agree_users": agree_users,
                    "disagree_users": disagree_users,
                })
                await new_report_thread.send(content=f"Alts Proofs for `{user.id}`", embeds=alts_proofs_embeds)
                await new_report_thread.send(content=f"Proofs for `{user.id}`", embeds=proofs_embeds)
                await old_message_edit_queue.put(
                    (message, {"content": "Appeal has been submitted for voting.", "embeds": embeds, "view": None}))
            else:
                await interaction.followup.send("You do not have permission to accept the report for voting.",
                                                ephemeral=True)
class AddAltsAppealModal(discord.ui.Modal, title="Add Alts"):
    alts = discord.ui.TextInput(label="Add Alts", placeholder="List alts here and leave a space between IDs.",
                                required=True, style=discord.TextStyle.short)

    def __init__(self):
        super().__init__(timeout=None)

    async def on_submit(self, interaction):
        await interaction.response.defer()
        #
        session = inprogresscol.find_one({"_id": interaction.message.id})
        if session:
            channel_id = session["channel_id"]
            message_id = interaction.message.id
            r_profile_list = session["r_profile_list"]
            add_case_list = session["add_case_list"]
            title = session["title"]
            case_title = session["case_title"]
            reason = session["reason"]
            user_id = session["user_id"]
            user = await bot.fetch_user(user_id)
            #
            original_alts = r_profile_list[0].strip("`").split() if r_profile_list[0] else []
            thread = await bot.fetch_channel(channel_id)
            message = await thread.fetch_message(message_id)
            alts_input = self.alts.value
            alts_list = alts_input.split()
            valid_alts = []
            for alt in alts_list:
                try:
                    alt_id = await bot.fetch_user(int(alt))
                except Exception:
                    pass
                else:
                    if alt_id.id not in valid_alts and str(alt_id.id) not in original_alts and alt_id != user:
                        valid_alts.append(alt_id.id)
            if len(valid_alts) != 0:
                r_profile_list[0] = alts_string(original_alts + valid_alts)
            #
            inprogresscol.update_one(
                {"_id": interaction.message.id},
                {"$set": {"r_profile_list": r_profile_list}}
            )
            #
            r_profile = format_user_r_profile(user, r_profile_list, title)
            reason_embed = discord.Embed(title="Reason", colour=0x1DCCA9, description=reason)
            add_case = format_user_add_case(add_case_list, case_title)
            embeds = [r_profile, add_case, reason_embed]
            await message.edit(embeds=embeds, view=UserAppealView())
class RemoveAltsAppealModal(discord.ui.Modal, title="Remove Alts"):
    alts = discord.ui.TextInput(label="Remove Alts", placeholder="List alts here and leave a space between IDs.",
                                required=True, style=discord.TextStyle.short)

    def __init__(self):
        super().__init__(timeout=None)

    async def on_submit(self, interaction):
        await interaction.response.defer()
        #
        session = inprogresscol.find_one({"_id": interaction.message.id})
        if session:
            channel_id = session["channel_id"]
            message_id = interaction.message.id
            r_profile_list = session["r_profile_list"]
            add_case_list = session["add_case_list"]
            title = session["title"]
            case_title = session["case_title"]
            reason = session["reason"]
            user_id = session["user_id"]
            user = await bot.fetch_user(user_id)
            #
            original_alts = r_profile_list[0].strip("`").split() if r_profile_list[0] else []
            thread = await bot.fetch_channel(channel_id)
            message = await thread.fetch_message(message_id)
            alts_input = self.alts.value
            alts_list = alts_input.split()
            valid_alts = []
            for alt in alts_list:
                try:
                    alt_id = await bot.fetch_user(int(alt))
                except Exception:
                    pass
                else:
                    if alt_id.id not in valid_alts and str(alt_id.id) in original_alts:
                        valid_alts.append(str(alt_id.id))
            if len(valid_alts) != 0:
                remaining_alts = [element for element in original_alts if element not in set(valid_alts)]
                if len(remaining_alts) != 0:
                    r_profile_list[0] = alts_string(remaining_alts)
                else:
                    r_profile_list[0] = ""
            #
            inprogresscol.update_one(
                {"_id": interaction.message.id},
                {"$set": {"r_profile_list": r_profile_list}}
            )
            #
            r_profile = format_user_r_profile(user, r_profile_list, title)
            reason_embed = discord.Embed(title="Reason", colour=0x1DCCA9, description=reason)
            add_case = format_user_add_case(add_case_list, case_title)
            embeds = [r_profile, add_case, reason_embed]
            await message.edit(embeds=embeds, view=UserAppealView())
class UserAppealReasonModal(discord.ui.Modal, title="Reason"):
    reason_input = discord.ui.TextInput(label="Reason", placeholder="Please explain the appeal you have made.",
                                        required=True, style=discord.TextStyle.long)

    def __init__(self):
        super().__init__(timeout=None)

    async def on_submit(self, interaction):
        await interaction.response.defer()
        #
        session = inprogresscol.find_one({"_id": interaction.message.id})
        if session:
            channel_id = session["channel_id"]
            message_id = interaction.message.id
            r_profile_list = session["r_profile_list"]
            add_case_list = session["add_case_list"]
            title = session["title"]
            case_title = session["case_title"]
            user_id = session["user_id"]
            user = await bot.fetch_user(user_id)
            #
            thread = await bot.fetch_channel(channel_id)
            message = await thread.fetch_message(message_id)
            reason = str(self.reason_input.value)
            inprogresscol.update_one(
                {"_id": interaction.message.id},
                {"$set": {"reason": reason}}
            )
            r_profile = format_user_r_profile(user, r_profile_list, title)
            reason_embed = discord.Embed(title="Reason", colour=0x1DCCA9, description=reason)
            add_case = format_user_add_case(add_case_list, case_title)
            embeds = [r_profile, add_case, reason_embed]
            await message.edit(embeds=embeds, view=UserAppealView())


# user add report
class AddReportAltsView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(emoji="<:rightarrow:1458096774521553038>", style=discord.ButtonStyle.grey, custom_id="addreportalts:next")
    async def next_button(self, interaction, button):
        await interaction.response.defer()
        #
        session = inprogresscol.find_one({"_id": interaction.message.id})
        if session:
            requested_by = session["requested_by"]
            channel_id = session["channel_id"]
            message_id = interaction.message.id
            r_profile_list = session["r_profile_list"]
            add_case_list = session["add_case_list"]
            title = session["title"]
            case_title = session["case_title"]
            user_id = session["user_id"]
            user = await bot.fetch_user(user_id)
            #
            thread = await bot.fetch_channel(channel_id)
            message = await thread.fetch_message(message_id)
            if requested_by == interaction.user.id or is_sr(interaction.user):
                r_profile = format_user_r_profile(user, r_profile_list, title)
                add_case = format_user_add_case(add_case_list, case_title)
                embeds = [r_profile, add_case]
                await message.edit(embeds=embeds, view=AddReportUserTagsView())

    @discord.ui.button(label="Add Alts", style=discord.ButtonStyle.green, custom_id="addreportalts:addalts")
    async def add_alts_button(self, interaction, button):
        #
        session = inprogresscol.find_one({"_id": interaction.message.id})
        if session:
            requested_by = session["requested_by"]
            #
            if requested_by == interaction.user.id:
                await interaction.response.send_modal(AddAltsModal())

    @discord.ui.button(label="Remove Alts", style=discord.ButtonStyle.red, custom_id="addreportalts:removealts")
    async def remove_alts_button(self, interaction, button):
        #
        session = inprogresscol.find_one({"_id": interaction.message.id})
        if session:
            requested_by = session["requested_by"]
            #
            if requested_by == interaction.user.id:
                await interaction.response.send_modal(RemoveAltsModal())

    @discord.ui.button(label="Add Alts Proofs", style=discord.ButtonStyle.green, custom_id="addreportalts:addaltsproofs")
    async def add_alts_proofs_button(self, interaction, button):
        #
        session = inprogresscol.find_one({"_id": interaction.message.id})
        if session:
            requested_by = session["requested_by"]
            r_profile_list = session["r_profile_list"]
            #
            if requested_by == interaction.user.id:
                image_links = []
                original_image_links = r_profile_list[2].copy()
                await interaction.response.send_message(
                    f"Please send the images you would like to upload (max {10 - len(r_profile_list[2])}).",
                    ephemeral=True)

                # Wait for a follow-up message from the user in the same channel
                def check(m):
                    # Check if the message is from the same user, in the same channel, and has an attachment
                    return m.author == interaction.user and m.channel == interaction.channel

                try:
                    msg = await bot.wait_for('message', check=check, timeout=120.0)
                except asyncio.TimeoutError:
                    await interaction.followup.send("You took too long to upload an image.", ephemeral=True)
                    return
                if msg.attachments:
                    for attachment in msg.attachments:
                        # Ensure the attachment is an image (optional check)
                        if attachment.content_type and attachment.content_type.startswith('image/'):
                            try:
                                # 1. Download the file data using aiohttp
                                async with aiohttp.ClientSession() as http_session:
                                    async with http_session.get(attachment.url) as resp:
                                        # For this example, we just send back the image URL and filename
                                        data = io.BytesIO(await resp.read())
                                        file = discord.File(data, filename=attachment.filename)
                                        channel_to_send = bot.get_channel(PROOFS_CHANNEL)
                                        sent_message = await channel_to_send.send(file=file)
                                        if sent_message.attachments:
                                            new_image_url = sent_message.attachments[0].url
                                            image_links.append(new_image_url)
                                            r_profile_list[2].append(new_image_url)
                            except Exception:
                                await msg.channel.send(f"An error occurred with file {attachment.filename}")
                if len(r_profile_list[2]) > 10:
                    await interaction.followup.send(
                        f"There are a total of {len(r_profile_list[2])} images, exceeding the max limit of 10. Please try again.")
                    r_profile_list[2] = original_image_links
                else:
                    #
                    inprogresscol.update_one(
                        {"_id": interaction.message.id},
                        {"$set": {"r_profile_list": r_profile_list}}
                    )
                    #
                    image_embeds = image_links_to_embeds(image_links)
                    await interaction.followup.send(f"Images received from {interaction.user.mention}.",
                                                    embeds=image_embeds)

    @discord.ui.button(label="Remove Alts Proofs", style=discord.ButtonStyle.red, custom_id="addreportalts:removealtsproofs")
    async def remove_alts_proofs_button(self, interaction, button):
        #
        session = inprogresscol.find_one({"_id": interaction.message.id})
        if session:
            requested_by = session["requested_by"]
            r_profile_list = session["r_profile_list"]
            #
            if requested_by == interaction.user.id:
                await interaction.response.send_message(
                    f"Please list image(s) you would like to remove, from 1 to {len(r_profile_list[2])}, with a space between each number.",
                    ephemeral=True)

                # Wait for a follow-up message from the user in the same channel
                def check(m):
                    # Check if the message is from the same user, in the same channel
                    return m.author == interaction.user and m.channel == interaction.channel

                try:
                    msg = await bot.wait_for('message', check=check, timeout=120.0)
                except asyncio.TimeoutError:
                    await interaction.followup.send("You took too long to respond.", ephemeral=True)
                    return
                try:
                    to_remove = msg.content.split()
                    indices_to_remove = []
                    for i in to_remove:
                        indices_to_remove.append(int(i) - 1)
                    indices_to_remove = set(indices_to_remove)
                except Exception:
                    await interaction.followup.send("Invalid response. Please try again.", ephemeral=True)
                else:
                    images_removed = []
                    for i in indices_to_remove:
                        if 0 <= i < len(r_profile_list[2]):
                            images_removed.append(r_profile_list[2][i])
                    r_profile_list[2] = [value for index, value in enumerate(r_profile_list[2]) if
                                         index not in indices_to_remove]
                    #
                    inprogresscol.update_one(
                        {"_id": interaction.message.id},
                        {"$set": {"r_profile_list": r_profile_list}}
                    )
                    #
                    image_embeds = image_links_to_embeds(images_removed)
                    await interaction.followup.send(f"Images removed by {interaction.user.mention}.",
                                                    embeds=image_embeds)

    @discord.ui.button(label="Show Alts Proofs", style=discord.ButtonStyle.grey, custom_id="addreportalts:showaltsproofs")
    async def show_alts_proofs_button(self, interaction, button):
        await interaction.response.defer()
        #
        session = inprogresscol.find_one({"_id": interaction.message.id})
        if session:
            requested_by = session["requested_by"]
            r_profile_list = session["r_profile_list"]
            user_id = session["user_id"]
            user = await bot.fetch_user(user_id)
            #
            if requested_by == interaction.user.id or is_sr(interaction.user):
                image_embeds = image_links_to_embeds(r_profile_list[2])
                await interaction.followup.send(f"Alts Proofs for `{user.id}`",
                                                embeds=image_embeds, ephemeral=True)
class AddAltsModal(discord.ui.Modal, title="Add Alts"):
    alts = discord.ui.TextInput(label="Add Alts", placeholder="List alts here and leave a space between IDs.",
                                required=True, style=discord.TextStyle.short)

    def __init__(self):
        super().__init__(timeout=None)

    async def on_submit(self, interaction):
        await interaction.response.defer()
        #
        session = inprogresscol.find_one({"_id": interaction.message.id})
        if session:
            channel_id = session["channel_id"]
            message_id = interaction.message.id
            r_profile_list = session["r_profile_list"]
            add_case_list = session["add_case_list"]
            title = session["title"]
            case_title = session["case_title"]
            user_id = session["user_id"]
            user = await bot.fetch_user(user_id)
            #
            original_alts = r_profile_list[0].strip("`").split() if r_profile_list[0] else []
            thread = await bot.fetch_channel(channel_id)
            message = await thread.fetch_message(message_id)
            alts_input = self.alts.value
            alts_list = alts_input.split()
            valid_alts = []
            for alt in alts_list:
                try:
                    alt_id = await bot.fetch_user(int(alt))
                except Exception:
                    pass
                else:
                    if alt_id.id not in valid_alts and str(alt_id.id) not in original_alts and alt_id != user:
                        valid_alts.append(alt_id.id)
            if len(valid_alts) != 0:
                r_profile_list[0] = alts_string(original_alts + valid_alts)
            #
            inprogresscol.update_one(
                {"_id": interaction.message.id},
                {"$set": {"r_profile_list": r_profile_list}}
            )
            #
            r_profile = format_user_r_profile(user, r_profile_list, title)
            add_case = format_user_add_case(add_case_list, case_title)
            embeds = [r_profile, add_case]
            await message.edit(embeds=embeds, view=AddReportAltsView())
class RemoveAltsModal(discord.ui.Modal, title="Remove Alts"):
    alts = discord.ui.TextInput(label="Remove Alts", placeholder="List alts here and leave a space between IDs.",
                                required=True, style=discord.TextStyle.short)

    def __init__(self):
        super().__init__(timeout=None)

    async def on_submit(self, interaction):
        await interaction.response.defer()
        #
        session = inprogresscol.find_one({"_id": interaction.message.id})
        if session:
            channel_id = session["channel_id"]
            message_id = interaction.message.id
            r_profile_list = session["r_profile_list"]
            add_case_list = session["add_case_list"]
            title = session["title"]
            case_title = session["case_title"]
            user_id = session["user_id"]
            user = await bot.fetch_user(user_id)
            #
            original_alts = r_profile_list[0].strip("`").split() if r_profile_list[0] else []
            thread = await bot.fetch_channel(channel_id)
            message = await thread.fetch_message(message_id)
            alts_input = self.alts.value
            alts_list = alts_input.split()
            valid_alts = []
            for alt in alts_list:
                try:
                    alt_id = await bot.fetch_user(int(alt))
                except Exception:
                    pass
                else:
                    if alt_id.id not in valid_alts and str(alt_id.id) in original_alts:
                        valid_alts.append(str(alt_id.id))
            if len(valid_alts) != 0:
                remaining_alts = [element for element in original_alts if element not in set(valid_alts)]
                if len(remaining_alts) != 0:
                    r_profile_list[0] = alts_string(remaining_alts)
                else:
                    r_profile_list[0] = ""
            #
            inprogresscol.update_one(
                {"_id": interaction.message.id},
                {"$set": {"r_profile_list": r_profile_list}}
            )
            #
            r_profile = format_user_r_profile(user, r_profile_list, title)
            add_case = format_user_add_case(add_case_list, case_title)
            embeds = [r_profile, add_case]
            await message.edit(embeds=embeds, view=AddReportAltsView())

class AddReportUserTagsView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(emoji="<:leftarrow:1458096658062770176>", style=discord.ButtonStyle.grey, custom_id="addreportusertags:prev")
    async def prev_button(self, interaction, button):
        await interaction.response.defer()
        #
        session = inprogresscol.find_one({"_id": interaction.message.id})
        if session:
            requested_by = session["requested_by"]
            channel_id = session["channel_id"]
            message_id = interaction.message.id
            r_profile_list = session["r_profile_list"]
            add_case_list = session["add_case_list"]
            title = session["title"]
            case_title = session["case_title"]
            user_id = session["user_id"]
            user = await bot.fetch_user(user_id)
            #
            thread = await bot.fetch_channel(channel_id)
            message = await thread.fetch_message(message_id)
            if requested_by == interaction.user.id or is_sr(interaction.user):
                r_profile = format_user_r_profile(user, r_profile_list, title)
                add_case = format_user_add_case(add_case_list, case_title)
                embeds = [r_profile, add_case]
                await message.edit(embeds=embeds, view=AddReportAltsView())

    @discord.ui.button(emoji="<:rightarrow:1458096774521553038>", style=discord.ButtonStyle.grey, custom_id="addreportusertags:next")
    async def next_button(self, interaction, button):
        await interaction.response.defer()
        #
        session = inprogresscol.find_one({"_id": interaction.message.id})
        if session:
            requested_by = session["requested_by"]
            channel_id = session["channel_id"]
            message_id = interaction.message.id
            r_profile_list = session["r_profile_list"]
            add_case_list = session["add_case_list"]
            title = session["title"]
            case_title = session["case_title"]
            user_id = session["user_id"]
            user = await bot.fetch_user(user_id)
            #
            thread = await bot.fetch_channel(channel_id)
            message = await thread.fetch_message(message_id)
            if requested_by == interaction.user.id or is_sr(interaction.user):
                r_profile = format_user_r_profile(user, r_profile_list, title)
                add_case = format_user_add_case(add_case_list, case_title)
                embeds = [r_profile, add_case]
                await message.edit(embeds=embeds, view=AddReportGamesView())

    @discord.ui.select(options=user_tags_options, placeholder="Select Tag(s)...", custom_id="addreportusertags:select",
                       max_values=len(user_tags_options))
    async def select_callback(self, interaction, select):
        await interaction.response.defer()
        #
        session = inprogresscol.find_one({"_id": interaction.message.id})
        if session:
            requested_by = session["requested_by"]
            channel_id = session["channel_id"]
            message_id = interaction.message.id
            r_profile_list = session["r_profile_list"]
            add_case_list = session["add_case_list"]
            title = session["title"]
            user_id = session["user_id"]
            user = await bot.fetch_user(user_id)
            #
            thread = await bot.fetch_channel(channel_id)
            message = await thread.fetch_message(message_id)
            if requested_by == interaction.user.id:
                sorted_tags = sort_user_tags(self.select_callback.values)
                case_title = sorted_tags[0]
                tags = selected_string(sorted_tags)
                add_case_list["tags"] = tags
                #
                user_id = user.id
                user_query = {"_id": str(user_id)}
                user_profile = userscol.find_one(user_query)
                old_r_profile_list = user_profile["r_profile_list"]
                #
                existing_tags_list = old_r_profile_list[1].split(", ")
                existing_tags_list.insert(0, title)
                for tag in sorted_tags:
                    if tag not in existing_tags_list:
                        existing_tags_list.append(tag)
                sorted_tags = sort_user_tags(existing_tags_list)
                #
                title = sorted_tags[0]
                all_other_tags = selected_string(sorted_tags[1:])
                r_profile_list[1] = all_other_tags
                #
                inprogresscol.update_one(
                    {"_id": interaction.message.id},
                    {"$set": {
                        "r_profile_list": r_profile_list,
                        "add_case_list": add_case_list,
                        "title": title,
                        "case_title": case_title, }
                    })
                #
                r_profile = format_user_r_profile(user, r_profile_list, title)
                add_case = format_user_add_case(add_case_list, case_title)
                embeds = [r_profile, add_case]
                await message.edit(embeds=embeds)

class AddReportGamesView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(emoji="<:leftarrow:1458096658062770176>", style=discord.ButtonStyle.grey, custom_id="addreportgames:prev")
    async def prev_button(self, interaction, button):
        await interaction.response.defer()
        #
        session = inprogresscol.find_one({"_id": interaction.message.id})
        if session:
            requested_by = session["requested_by"]
            channel_id = session["channel_id"]
            message_id = interaction.message.id
            r_profile_list = session["r_profile_list"]
            add_case_list = session["add_case_list"]
            title = session["title"]
            case_title = session["case_title"]
            user_id = session["user_id"]
            user = await bot.fetch_user(user_id)
            #
            thread = await bot.fetch_channel(channel_id)
            message = await thread.fetch_message(message_id)
            if requested_by == interaction.user.id or is_sr(interaction.user):
                r_profile = format_user_r_profile(user, r_profile_list, title)
                add_case = format_user_add_case(add_case_list, case_title)
                embeds = [r_profile, add_case]
                await message.edit(embeds=embeds, view=AddReportUserTagsView())

    @discord.ui.button(emoji="<:rightarrow:1458096774521553038>", style=discord.ButtonStyle.grey, custom_id="addreportgames:next")
    async def next_button(self, interaction, button):
        await interaction.response.defer()
        #
        session = inprogresscol.find_one({"_id": interaction.message.id})
        if session:
            requested_by = session["requested_by"]
            channel_id = session["channel_id"]
            message_id = interaction.message.id
            r_profile_list = session["r_profile_list"]
            add_case_list = session["add_case_list"]
            title = session["title"]
            case_title = session["case_title"]
            user_id = session["user_id"]
            user = await bot.fetch_user(user_id)
            #
            thread = await bot.fetch_channel(channel_id)
            message = await thread.fetch_message(message_id)
            if requested_by == interaction.user.id or is_sr(interaction.user):
                r_profile = format_user_r_profile(user, r_profile_list, title)
                add_case = format_user_add_case(add_case_list, case_title)
                embeds = [r_profile, add_case]
                await message.edit(embeds=embeds, view=AddReportUserReasonView())

    @discord.ui.select(options=games_options, placeholder="Select Game(s)...", custom_id="addreportgames:select",
                       max_values=len(games_options))
    async def select_callback(self, interaction, select):
        await interaction.response.defer()
        #
        session = inprogresscol.find_one({"_id": interaction.message.id})
        if session:
            requested_by = session["requested_by"]
            channel_id = session["channel_id"]
            message_id = interaction.message.id
            r_profile_list = session["r_profile_list"]
            add_case_list = session["add_case_list"]
            title = session["title"]
            case_title = session["case_title"]
            user_id = session["user_id"]
            user = await bot.fetch_user(user_id)
            #
            thread = await bot.fetch_channel(channel_id)
            message = await thread.fetch_message(message_id)
            if requested_by == interaction.user.id:
                games = selected_string(self.select_callback.values)
                add_case_list["games"] = games
                #
                inprogresscol.update_one(
                    {"_id": interaction.message.id},
                    {"$set": {
                        "r_profile_list": r_profile_list,
                        "add_case_list": add_case_list,
                        "title": title,
                        "case_title": case_title, }
                    })
                #
                r_profile = format_user_r_profile(user, r_profile_list, title)
                add_case = format_user_add_case(add_case_list, case_title)
                embeds = [r_profile, add_case]
                await message.edit(embeds=embeds)

class AddReportUserReasonView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(emoji="<:leftarrow:1458096658062770176>", style=discord.ButtonStyle.grey, custom_id="addreportuserreason:prev")
    async def prev_button(self, interaction, button):
        await interaction.response.defer()
        #
        session = inprogresscol.find_one({"_id": interaction.message.id})
        if session:
            requested_by = session["requested_by"]
            channel_id = session["channel_id"]
            message_id = interaction.message.id
            r_profile_list = session["r_profile_list"]
            add_case_list = session["add_case_list"]
            title = session["title"]
            case_title = session["case_title"]
            user_id = session["user_id"]
            user = await bot.fetch_user(user_id)
            #
            thread = await bot.fetch_channel(channel_id)
            message = await thread.fetch_message(message_id)
            if requested_by == interaction.user.id or is_sr(interaction.user):
                r_profile = format_user_r_profile(user, r_profile_list, title)
                add_case = format_user_add_case(add_case_list, case_title)
                embeds = [r_profile, add_case]
                await message.edit(embeds=embeds, view=AddReportGamesView())

    @discord.ui.button(emoji="<:rightarrow:1458096774521553038>", style=discord.ButtonStyle.grey, custom_id="addreportuserreason:next")
    async def next_button(self, interaction, button):
        await interaction.response.defer()
        #
        session = inprogresscol.find_one({"_id": interaction.message.id})
        if session:
            requested_by = session["requested_by"]
            channel_id = session["channel_id"]
            message_id = interaction.message.id
            r_profile_list = session["r_profile_list"]
            add_case_list = session["add_case_list"]
            title = session["title"]
            case_title = session["case_title"]
            user_id = session["user_id"]
            user = await bot.fetch_user(user_id)
            #
            thread = await bot.fetch_channel(channel_id)
            message = await thread.fetch_message(message_id)
            if requested_by == interaction.user.id or is_sr(interaction.user):
                r_profile = format_user_r_profile(user, r_profile_list, title)
                add_case = format_user_add_case(add_case_list, case_title)
                embeds = [r_profile, add_case]
                await message.edit(embeds=embeds, view=AddReportUserContributorView())

    @discord.ui.button(label="Reason", style=discord.ButtonStyle.green, custom_id="addreportuserreason:input")
    async def reason_button(self, interaction, button):
        #
        session = inprogresscol.find_one({"_id": interaction.message.id})
        if session:
            requested_by = session["requested_by"]
            #
            if requested_by == interaction.user.id:
                await interaction.response.send_modal(AddReportUserReasonModal())
class AddReportUserReasonModal(discord.ui.Modal, title="Reason"):
    reason = discord.ui.TextInput(label="Reason", placeholder="Input reason here.", required=True,
                                  style=discord.TextStyle.long)

    def __init__(self):
        super().__init__(timeout=None)

    async def on_submit(self, interaction):
        await interaction.response.defer()
        #
        session = inprogresscol.find_one({"_id": interaction.message.id})
        if session:
            channel_id = session["channel_id"]
            message_id = interaction.message.id
            r_profile_list = session["r_profile_list"]
            add_case_list = session["add_case_list"]
            title = session["title"]
            case_title = session["case_title"]
            user_id = session["user_id"]
            user = await bot.fetch_user(user_id)
            #
            thread = await bot.fetch_channel(channel_id)
            message = await thread.fetch_message(message_id)
            reason = re.sub(r"\s+", " ", self.reason.value)
            add_case_list["reason"] = reason
            #
            inprogresscol.update_one(
                {"_id": interaction.message.id},
                {"$set": {"add_case_list": add_case_list}},
            )
            #
            r_profile = format_user_r_profile(user, r_profile_list, title)
            add_case = format_user_add_case(add_case_list, case_title)
            embeds = [r_profile, add_case]
            await message.edit(embeds=embeds, view=AddReportUserReasonView())

class AddReportUserContributorView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(emoji="<:leftarrow:1458096658062770176>", style=discord.ButtonStyle.grey,
                       custom_id="addreportusercontributor:prev")
    async def prev_button(self, interaction, button):
        await interaction.response.defer()
        #
        session = inprogresscol.find_one({"_id": interaction.message.id})
        if session:
            requested_by = session["requested_by"]
            channel_id = session["channel_id"]
            message_id = interaction.message.id
            r_profile_list = session["r_profile_list"]
            add_case_list = session["add_case_list"]
            title = session["title"]
            case_title = session["case_title"]
            user_id = session["user_id"]
            user = await bot.fetch_user(user_id)
            #
            thread = await bot.fetch_channel(channel_id)
            message = await thread.fetch_message(message_id)
            if requested_by == interaction.user.id or is_sr(interaction.user):
                r_profile = format_user_r_profile(user, r_profile_list, title)
                add_case = format_user_add_case(add_case_list, case_title)
                embeds = [r_profile, add_case]
                await message.edit(embeds=embeds, view=AddReportUserReasonView())

    @discord.ui.button(emoji="<:rightarrow:1458096774521553038>", style=discord.ButtonStyle.grey,
                       custom_id="addreportusercontributor:next")
    async def next_button(self, interaction, button):
        await interaction.response.defer()
        #
        session = inprogresscol.find_one({"_id": interaction.message.id})
        if session:
            requested_by = session["requested_by"]
            channel_id = session["channel_id"]
            message_id = interaction.message.id
            r_profile_list = session["r_profile_list"]
            add_case_list = session["add_case_list"]
            title = session["title"]
            case_title = session["case_title"]
            user_id = session["user_id"]
            user = await bot.fetch_user(user_id)
            #
            thread = await bot.fetch_channel(channel_id)
            message = await thread.fetch_message(message_id)
            if requested_by == interaction.user.id or is_sr(interaction.user):
                r_profile = format_user_r_profile(user, r_profile_list, title)
                add_case = format_user_add_case(add_case_list, case_title)
                embeds = [r_profile, add_case]
                await message.edit(embeds=embeds, view=AddReportUserProofsView())

    @discord.ui.button(label="Contributor", style=discord.ButtonStyle.green, custom_id="addreportusercontributor:input")
    async def contributor_button(self, interaction, button):
        #
        session = inprogresscol.find_one({"_id": interaction.message.id})
        if session:
            requested_by = session["requested_by"]
            #
            if requested_by == interaction.user.id:
                await interaction.response.send_modal(AddReportUserContributorModal())
class AddReportUserContributorModal(discord.ui.Modal, title="Contributor"):
    contributor = discord.ui.TextInput(label="Contributor",
                                       placeholder="User ID / n if Anonymous.", required=True,
                                       style=discord.TextStyle.short)

    def __init__(self):
        super().__init__(timeout=None)

    async def on_submit(self, interaction):
        await interaction.response.defer()
        #
        session = inprogresscol.find_one({"_id": interaction.message.id})
        if session:
            channel_id = session["channel_id"]
            message_id = interaction.message.id
            r_profile_list = session["r_profile_list"]
            add_case_list = session["add_case_list"]
            title = session["title"]
            case_title = session["case_title"]
            user_id = session["user_id"]
            user = await bot.fetch_user(user_id)
            #
            thread = await bot.fetch_channel(channel_id)
            message = await thread.fetch_message(message_id)
            contributor_input = self.contributor.value
            if contributor_input.lower() == "n":
                add_case_list["contributor"] = "Anonymous"
            else:
                try:
                    contributor_id = await bot.fetch_user(int(contributor_input))
                except Exception:
                    add_case_list["contributor"] = ""
                else:
                    add_case_list["contributor"] = f"<@{contributor_id.id}>"
            #
            inprogresscol.update_one(
                {"_id": interaction.message.id},
                {"$set": {"add_case_list": add_case_list}},
            )
            #
            r_profile = format_user_r_profile(user, r_profile_list, title)
            add_case = format_user_add_case(add_case_list, case_title)
            embeds = [r_profile, add_case]
            await message.edit(embeds=embeds,
                               view=AddReportUserContributorView())

class AddReportUserProofsView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(emoji="<:leftarrow:1458096658062770176>", style=discord.ButtonStyle.grey, custom_id="addreportuserproofs:prev")
    async def prev_button(self, interaction, button):
        await interaction.response.defer()
        #
        session = inprogresscol.find_one({"_id": interaction.message.id})
        if session:
            requested_by = session["requested_by"]
            channel_id = session["channel_id"]
            message_id = interaction.message.id
            r_profile_list = session["r_profile_list"]
            add_case_list = session["add_case_list"]
            title = session["title"]
            case_title = session["case_title"]
            user_id = session["user_id"]
            user = await bot.fetch_user(user_id)
            #
            thread = await bot.fetch_channel(channel_id)
            message = await thread.fetch_message(message_id)
            if requested_by == interaction.user.id or is_sr(interaction.user):
                r_profile = format_user_r_profile(user, r_profile_list, title)
                add_case = format_user_add_case(add_case_list, case_title)
                embeds = [r_profile, add_case]
                await message.edit(embeds=embeds, view=AddReportUserContributorView())

    @discord.ui.button(label="Add Proofs", style=discord.ButtonStyle.green, custom_id="addreportuserproofs:input")
    async def proofs_button(self, interaction, button):
        #
        session = inprogresscol.find_one({"_id": interaction.message.id})
        if session:
            requested_by = session["requested_by"]
            add_case_list = session["add_case_list"]
            #
            if requested_by == interaction.user.id:
                image_links = []
                add_case_list["proofs"] = []
                await interaction.response.send_message(
                    "Please send the images you would like to upload (max 10). **All images previously uploaded in this session have been removed.**",
                    ephemeral=True)

                def check(m):
                    return m.author == interaction.user and m.channel == interaction.channel

                try:
                    msg = await bot.wait_for('message', check=check, timeout=120.0)
                except asyncio.TimeoutError:
                    await interaction.followup.send("You took too long to upload an image.", ephemeral=True)
                    return
                if msg.attachments:
                    for attachment in msg.attachments:
                        # Ensure the attachment is an image (optional check)
                        if attachment.content_type and attachment.content_type.startswith('image/'):
                            try:
                                # 1. Download the file data using aiohttp
                                async with aiohttp.ClientSession() as http_session:
                                    async with http_session.get(attachment.url) as resp:
                                        # For this example, we just send back the image URL and filename
                                        data = io.BytesIO(await resp.read())
                                        file = discord.File(data, filename=attachment.filename)
                                        channel_to_send = bot.get_channel(PROOFS_CHANNEL)
                                        sent_message = await channel_to_send.send(file=file)
                                        if sent_message.attachments:
                                            new_image_url = sent_message.attachments[0].url
                                            image_links.append(new_image_url)
                                            add_case_list["proofs"].append(new_image_url)
                            except Exception:
                                await msg.channel.send(f"An error occurred with file {attachment.filename}")
                #
                inprogresscol.update_one(
                    {"_id": interaction.message.id},
                    {"$set": {"add_case_list": add_case_list}},
                )
                #
                image_embeds = image_links_to_embeds(image_links)
                await interaction.followup.send(f"Images received from {interaction.user.mention}.",
                                                embeds=image_embeds)

    @discord.ui.button(label="Show Proofs", style=discord.ButtonStyle.grey, custom_id="addreportuserproofs:showproofs")
    async def show_proofs_button(self, interaction, button):
        await interaction.response.defer()
        #
        session = inprogresscol.find_one({"_id": interaction.message.id})
        if session:
            requested_by = session["requested_by"]
            add_case_list = session["add_case_list"]
            user_id = session["user_id"]
            user = await bot.fetch_user(user_id)
            #
            if requested_by == interaction.user.id or is_sr(interaction.user):
                image_embeds = image_links_to_embeds(add_case_list["proofs"])
                await interaction.followup.send(f"Proofs for `{user.id}`",
                                                embeds=image_embeds, ephemeral=True)

    @discord.ui.button(label="Show Alts Proofs", style=discord.ButtonStyle.grey, custom_id="addreportuserproofs:showaltsproofs")
    async def show_alts_proofs_button(self, interaction, button):
        await interaction.response.defer()
        #
        session = inprogresscol.find_one({"_id": interaction.message.id})
        if session:
            requested_by = session["requested_by"]
            r_profile_list = session["r_profile_list"]
            user_id = session["user_id"]
            user = await bot.fetch_user(user_id)
            #
            if requested_by == interaction.user.id or is_sr(interaction.user):
                image_embeds = image_links_to_embeds(r_profile_list[2])
                await interaction.followup.send(f"Alts Proofs for `{user.id}`",
                                                embeds=image_embeds, ephemeral=True)

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.grey, custom_id="addreportuserproofs:cancel")
    async def cancel_button(self, interaction, button):
        await interaction.response.defer()
        #
        session = inprogresscol.find_one({"_id": interaction.message.id})
        if session:
            requested_by = session["requested_by"]
            channel_id = session["channel_id"]
            message_id = interaction.message.id
            #
            thread = await bot.fetch_channel(channel_id)
            message = await thread.fetch_message(message_id)
            if requested_by == interaction.user.id or is_sr(interaction.user):
                inprogresscol.delete_one({"_id": interaction.message.id})
                await message.edit(content=f"**Cancelled by {interaction.user.mention}.**", view=None)

    @discord.ui.button(label="Accept", style=discord.ButtonStyle.grey, custom_id="addreportuserproofs:accept")
    async def accept_button(self, interaction, button):
        await interaction.response.defer()
        #
        session = inprogresscol.find_one({"_id": interaction.message.id})
        if session:
            requested_by = session["requested_by"]
            channel_id = session["channel_id"]
            message_id = interaction.message.id
            r_profile_list = session["r_profile_list"]
            add_case_list = session["add_case_list"]
            title = session["title"]
            case_title = session["case_title"]
            user_id = session["user_id"]
            user = await bot.fetch_user(user_id)
            #
            thread = await bot.fetch_channel(channel_id)
            message = await thread.fetch_message(message_id)
            if is_sr(interaction.user) and interaction.user.id != requested_by:
                accepted_by = interaction.user
                add_case_list["accepted_by"] = f"<@{interaction.user.id}>"
                r_profile = format_user_r_profile(user, r_profile_list, title)
                add_case = format_user_add_case(add_case_list, case_title)
                embeds = [r_profile, add_case]
                #
                vote_channel = bot.get_channel(VOTE_CHANNEL)
                agree_users = []
                disagree_users = []
                alts_proofs_embeds = image_links_to_embeds(r_profile_list[2])
                proofs_embeds = image_links_to_embeds(add_case_list["proofs"])
                new_report_message = await vote_channel.send(content=f"Added report on `{user.id}`")
                new_report_thread = await new_report_message.create_thread(name=f"{user.id}")
                await new_report_thread.send(f"<@&{ticket_ping}>")
                vote_msg = await new_report_thread.send(
                    content=f"Report accepted by {accepted_by.mention}.\nLink to thread: <#{channel_id}>\n\nAgree: 0\nDisagree: 0",
                    embeds=embeds, view=UserVoteView())
                vote_channel_id = vote_msg.channel.id
                vote_message_id = vote_msg.id
                old_session = inprogresscol.find_one({"user_id": user_id})
                if old_session:
                    inprogresscol.delete_one({"_id": old_session["_id"]})
                inprogresscol.insert_one({
                    "_id": vote_message_id,
                    "user_id": user_id,
                    "requested_by": requested_by,
                    "channel_id": channel_id,
                    "message_id": interaction.message.id,
                    "r_profile_list": r_profile_list,
                    "add_case_list": add_case_list,
                    "title": title,
                    "case_title": case_title,
                    "vote_channel_id": vote_channel_id,
                    "accepted_by": accepted_by.id,
                    "agree_users": agree_users,
                    "disagree_users": disagree_users,
                })
                await new_report_thread.send(content=f"Alts Proofs for `{user.id}`", embeds=alts_proofs_embeds)
                await new_report_thread.send(content=f"Proofs for `{user.id}`", embeds=proofs_embeds)
                await old_message_edit_queue.put(
                    (message, {"content": "Report has been submitted for voting.", "embeds": embeds, "view": None}))
            else:
                await interaction.followup.send("You do not have permission to accept the report for voting.",
                                                ephemeral=True)

async def handle_vote(interaction, session, vote_type):
    agree_users = session.get("agree_users", [])
    disagree_users = session.get("disagree_users", [])
    user_id = interaction.user.id
    message = None
    if vote_type == "remove":
        if user_id in agree_users:
            agree_users.remove(user_id)
            message = "You have removed your vote."
        elif user_id in disagree_users:
            disagree_users.remove(user_id)
            message = "You have removed your vote."
        else:
            message = "You have not voted."
    elif vote_type == "agree":
        if user_id not in agree_users and user_id not in disagree_users:
            agree_users.append(user_id)
            message = "You have voted Agree."
        elif user_id in disagree_users:
            disagree_users.remove(user_id)
            agree_users.append(user_id)
            message = "You have changed your vote from Disagree to Agree."
        else:
            message = "You have already voted Agree."
    elif vote_type == "disagree":
        if user_id not in disagree_users and user_id not in agree_users:
            disagree_users.append(user_id)
            message = "You have voted Disagree."
        elif user_id in agree_users:
            agree_users.remove(user_id)
            disagree_users.append(user_id)
            message = "You have changed your vote from Agree to Disagree."
        else:
            message = "You have already voted Disagree."
    session["agree_users"] = agree_users
    session["disagree_users"] = disagree_users
    inprogresscol.update_one({"_id": interaction.message.id},
                             {"$set": {"agree_users": agree_users, "disagree_users": disagree_users}})
    await interaction.followup.send(message, ephemeral=True)
    return agree_users, disagree_users

# user voting
class UserVoteView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Agree", style=discord.ButtonStyle.green, custom_id="uservote:agree")
    async def agree_button(self, interaction, button):
        await interaction.response.defer()
        session = inprogresscol.find_one({"_id": interaction.message.id})
        if session:
            requested_by = session["requested_by"]
            channel_id = session["channel_id"]
            message_id = session["message_id"]
            r_profile_list = session["r_profile_list"]
            add_case_list = session.get("add_case_list")
            title = session["title"]
            case_title = session.get("case_title")
            accepted_by = session["accepted_by"]
            reason = session.get("reason")
            user_id = session["user_id"]
            user = await bot.fetch_user(user_id)
            agree_users, disagree_users = await handle_vote(interaction, session, "agree")
            #
            r_profile = format_user_r_profile(user, r_profile_list, title)
            #
            if len(agree_users) >= 8 and len(agree_users) > len(disagree_users):
                user_id = user.id
                user_query = {"_id": str(user_id)}
                user_profile = userscol.find_one(user_query)
                if user_profile:  # if editing existing reported user
                    old_r_profile_list = user_profile["r_profile_list"]
                    cases = []
                    no_of_cases = len(user_profile) - 2
                    for i in range(1, no_of_cases + 1):
                        cases.append(user_profile[str(i)])
                    #
                    if old_r_profile_list[0] != r_profile_list[0]:  # comparing alts
                        old_alts_list = old_r_profile_list[0].strip("`").split()
                        new_alts_list = r_profile_list[0].strip("`").split()
                        added_alts_list = set(new_alts_list) - set(old_alts_list)
                        removed_alts_list = set(old_alts_list) - set(new_alts_list)
                        for alt in added_alts_list:
                            userscol.update_one(
                                {"_id": str(alt)},
                                {"$set": {"main": str(user.id)}},
                                upsert=True
                            )
                        for alt in removed_alts_list:
                            userscol.delete_one({"_id": alt})
                        update_operation = {'$set': {"r_profile_list": r_profile_list}}
                        userscol.update_one(user_query, update_operation)
                    if not add_case_list:  # only alts edited
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
                        r_profile = format_user_r_profile(user, r_profile_list, title)
                        user_reports_channel = bot.get_channel(USER_REPORTS_CHANNEL)
                        await user_reports_channel.send(content=f"<@&{updated_user_report_ping}>\nEdited alts for `{user.id}`",
                                                        embed=r_profile)
                        reason_embed = discord.Embed(title="Reason", description=reason)
                        await user_reports_channel.send(content=f"Reason for change(s)", embed=reason_embed)
                        await old_message_edit_queue.put((interaction.message, {"content": f"**Report has been published.** Report accepted by <@{accepted_by}>.\nLink to thread: <#{channel_id}>\n\nAgree: {len(agree_users)}\nDisagree: {len(disagree_users)}",
                            "embeds": [r_profile], "view": None}))
                        thread = await bot.fetch_channel(channel_id)
                        message = await thread.fetch_message(message_id)
                        await old_message_edit_queue.put((message, {
                            "content": f"**Report has been published.** Report accepted by <@{accepted_by}>.",
                            "view": None}))
                        await bot.get_channel(channel_id).send(
                            f"Report on `{user.id}` has been published. <@{requested_by}> <@{accepted_by}>")
                        inprogresscol.delete_one({"_id": interaction.message.id})
                    elif len(add_case_list) == 1:  # [[add_case_list]] case to appeal
                        add_case_list = add_case_list[0]
                        appeal_case_number = next((k for k, v in user_profile.items() if v == add_case_list), None)
                        query_filter = {"_id": str(user.id)}
                        update_operation = {"$unset": {appeal_case_number: ""}}
                        userscol.update_one(query_filter, update_operation)
                        #
                        user_query = {"_id": str(user_id)}
                        user_profile = userscol.find_one(user_query)
                        alts = r_profile_list[0].strip("`").split() if r_profile_list[0] else []
                        if len(user_profile) == 2:
                            userscol.delete_one(user_query)
                            for alt in alts:
                                user_query = {"_id": alt}
                                userscol.delete_one(user_query)
                        else:
                            no_of_cases = len(user_profile) - 2
                            for i in range(int(appeal_case_number), no_of_cases + 1):
                                user_profile[appeal_case_number] = user_profile.pop(str(int(appeal_case_number) + 1))
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
                            all_tags_list = list(dict.fromkeys(all_tags_list))
                            title = all_tags_list[0]
                            all_other_tags = selected_string(all_tags_list[1:])
                            r_profile_list = user_profile["r_profile_list"]
                            r_profile_list[1] = all_other_tags
                            user_profile["r_profile_list"] = r_profile_list
                            query_filter = {"_id": str(user.id)}
                            userscol.replace_one(query_filter, user_profile)
                        #
                        r_profile = format_user_r_profile(user, r_profile_list, title)
                        add_case = format_user_add_case(add_case_list, case_title)
                        reason_embed = discord.Embed(title="Reason", colour=0x1DCCA9, description=reason)
                        embeds = [r_profile, add_case]
                        #
                        user_reports_channel = bot.get_channel(USER_REPORTS_CHANNEL)
                        await user_reports_channel.send(content=f"<@&{appealed_user_report_ping}>\nAppeal on `{user.id}`",
                                                        embeds=embeds)
                        await user_reports_channel.send(content=f"Reason for appeal", embed=reason_embed)
                        await old_message_edit_queue.put((interaction.message, {"content": f"**Appeal has been published.** Appeal accepted by <@{accepted_by}>.\nLink to thread: <#{channel_id}>\n\nAgree: {len(agree_users)}\nDisagree: {len(disagree_users)}",
                            "view": None, "embeds": embeds}))
                        thread = await bot.fetch_channel(channel_id)
                        message = await thread.fetch_message(message_id)
                        await old_message_edit_queue.put((message, {
                            "content": f"**Appeal has been published.** Appeal accepted by <@{accepted_by}>.",
                            "view": None}))
                        await bot.get_channel(channel_id).send(
                            f"Appeal on `{user.id}` has been published. <@{requested_by}> <@{accepted_by}>")
                        inprogresscol.delete_one({"_id": interaction.message.id})
                    else:  # new case exists
                        #
                        r_profile = format_user_r_profile(user, r_profile_list, title)
                        add_case = format_user_add_case(add_case_list, case_title)
                        embeds = [r_profile, add_case]

                        query_filter = {"_id": str(user.id)}
                        update_operation = {'$set': {"r_profile_list": r_profile_list}}
                        userscol.update_one(query_filter, update_operation)
                        update_operation = {'$set': {str(no_of_cases + 1): add_case_list}}
                        userscol.update_one(query_filter, update_operation)

                        user_reports_channel = bot.get_channel(USER_REPORTS_CHANNEL)
                        await user_reports_channel.send(content=f"<@&{updated_user_report_ping}>\nAdded report on `{user.id}`",
                                                        embeds=embeds)
                        await old_message_edit_queue.put((interaction.message, {"content": f"**Report has been published.** Report accepted by <@{accepted_by}>.\nLink to thread: <#{channel_id}>\n\nAgree: {len(agree_users)}\nDisagree: {len(disagree_users)}",
                            "view": None, "embeds": embeds}))
                        thread = await bot.fetch_channel(channel_id)
                        message = await thread.fetch_message(message_id)
                        await old_message_edit_queue.put((message, {
                            "content": f"**Report has been published.** Report accepted by <@{accepted_by}>.",
                            "view": None}))
                        await bot.get_channel(channel_id).send(
                            f"Report on `{user.id}` has been published. <@{requested_by}> <@{accepted_by}>")
                        inprogresscol.delete_one({"_id": interaction.message.id})
                else:  # if new reported user
                    r_profile = format_user_r_profile(user, r_profile_list, title)
                    add_case = format_user_add_case(add_case_list, case_title)
                    embeds = [r_profile, add_case]
                    new_user = {"_id": str(user.id), "r_profile_list": r_profile_list,
                                "1": add_case_list}
                    userscol.insert_one(new_user)
                    alts_list = r_profile_list[0].strip("`").split() if r_profile_list[0] else []
                    for alt in alts_list:
                        userscol.update_one(
                            {"_id": str(alt)},
                            {"$set": {"main": str(user.id)}},
                            upsert=True
                        )
                    user_reports_channel = bot.get_channel(USER_REPORTS_CHANNEL)
                    await user_reports_channel.send(content=f"<@&{new_user_report_ping}>\nNew report on `{user.id}`",
                                                    embeds=embeds)
                    await old_message_edit_queue.put((interaction.message, {"content": f"**Report has been published.** Report accepted by <@{accepted_by}>.\nLink to thread: <#{channel_id}>\n\nAgree: {len(agree_users)}\nDisagree: {len(disagree_users)}",
                        "view": None, "embeds": embeds}))
                    thread = await bot.fetch_channel(channel_id)
                    message = await thread.fetch_message(message_id)
                    await old_message_edit_queue.put((message, {
                        "content": f"**Report has been published.** Report accepted by <@{accepted_by}>.",
                        "view": None}))
                    await bot.get_channel(channel_id).send(
                        f"Report on `{user.id}` has been published. <@{requested_by}> <@{accepted_by}>")
                    inprogresscol.delete_one({"_id": interaction.message.id})
                try:
                    voters = agree_users + disagree_users
                    for voter in voters:
                        voter_query = {"_id": str(voter)}
                        voter_profile = trusteduserscol.find_one(voter_query)
                        if voter_profile:
                            trusteduserscol.update_one(
                                voter_query,
                                {"$inc": {"votes": 1}}
                            )

                    staff_query = {"_id": str(requested_by)}
                    if trusteduserscol.find_one(staff_query):
                        trusteduserscol.update_one(
                            staff_query,
                            {"$inc": {"reports": 1}}
                        )
                    if staffweeklycol.find_one(staff_query):
                        staffweeklycol.update_one(
                            staff_query,
                            {"$inc": {"weekly_reports": 1}}
                        )
                    sr_query = {"_id": str(accepted_by)}
                    if trusteduserscol.find_one(sr_query):
                        trusteduserscol.update_one(
                            {"_id": str(accepted_by)},
                            {"$inc": {"reviews": 1}}
                        )
                    if staffweeklycol.find_one(sr_query):
                        staffweeklycol.update_one(
                            {"_id": str(accepted_by)},
                            {"$inc": {"weekly_reviews": 1}}
                        )
                except Exception as e:
                    print(f"{e}")
                current_name = interaction.channel.name
                new_name = current_name if current_name.startswith("p-") else f"p-{current_name}"
                await asyncio.sleep(2)
                await interaction.channel.edit(name=new_name, archived=True, locked=True)
                return
            #
            if not add_case_list:  # only alts edited
                await old_message_edit_queue.put((interaction.message, {"content": f"Report accepted by <@{accepted_by}>.\nLink to thread: <#{channel_id}>\n\nAgree: {len(agree_users)}\nDisagree: {len(disagree_users)}",
                    "embeds": [r_profile], "view": UserVoteView()}))
            elif len(add_case_list) == 1:  # [[add_case_list]] case to appeal
                add_case_list = add_case_list[0]
                add_case = format_user_add_case(add_case_list, case_title)
                reason_embed = discord.Embed(title="Reason", colour=0x1DCCA9, description=reason)
                embeds = [r_profile, add_case, reason_embed]
                await old_message_edit_queue.put((interaction.message, {"content": f"Appeal accepted by <@{accepted_by}>.\nLink to thread: <#{channel_id}>\n\nAgree: {len(agree_users)}\nDisagree: {len(disagree_users)}",
                    "embeds": embeds, "view": UserVoteView()}))
            else:  # new case exists
                add_case = format_user_add_case(add_case_list, case_title)
                embeds = [r_profile, add_case]
                await old_message_edit_queue.put((interaction.message, {"content": f"Report accepted by <@{accepted_by}>.\nLink to thread: <#{channel_id}>\n\nAgree: {len(agree_users)}\nDisagree: {len(disagree_users)}",
                    "embeds": embeds, "view": UserVoteView()}))

    @discord.ui.button(label="Disagree", style=discord.ButtonStyle.red, custom_id="uservote:disagree")
    async def disagree_button(self, interaction, button):
        await interaction.response.defer()
        session = inprogresscol.find_one({"_id": interaction.message.id})
        if session:
            requested_by = session["requested_by"]
            channel_id = session["channel_id"]
            message_id = session["message_id"]
            r_profile_list = session["r_profile_list"]
            add_case_list = session.get("add_case_list")
            title = session["title"]
            case_title = session.get("case_title")
            accepted_by = session["accepted_by"]
            reason = session.get("reason")
            user_id = session["user_id"]
            user = await bot.fetch_user(user_id)
            agree_users, disagree_users = await handle_vote(interaction, session, "disagree")
            #
            r_profile = format_user_r_profile(user, r_profile_list, title)
            #
            if len(disagree_users) >= 12:
                user_id = user.id
                user_query = {"_id": str(user_id)}
                user_profile = userscol.find_one(user_query)
                if user_profile:  # if editing existing reported user
                    if not add_case_list:  # only alts edited
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
                        r_profile = format_user_r_profile(user, r_profile_list, title)
                        await old_message_edit_queue.put((interaction.message, {"content": f"**Report has been rejected.** Report accepted by <@{accepted_by}>.\nLink to thread: <#{channel_id}>\n\nAgree: {len(agree_users)}\nDisagree: {len(disagree_users)}",
                            "embeds": [r_profile], "view": None}))
                        thread = await bot.fetch_channel(channel_id)
                        message = await thread.fetch_message(message_id)
                        await old_message_edit_queue.put((message, {
                            "content": f"**Report has been rejected.** Report accepted by <@{accepted_by}>.",
                            "view": None}))
                        await bot.get_channel(channel_id).send(
                            f"Report on `{user.id}` has been rejected. <@{requested_by}> <@{accepted_by}>")
                        inprogresscol.delete_one({"_id": interaction.message.id})

                    elif len(add_case_list) == 1:  # [[add_case_list]] case to appeal
                        add_case_list = add_case_list[0]
                        r_profile = format_user_r_profile(user, r_profile_list, title)
                        add_case = format_user_add_case(add_case_list, case_title)
                        embeds = [r_profile, add_case]
                        #
                        await old_message_edit_queue.put((interaction.message, {"content": f"**Appeal has been rejected.** Appeal accepted by <@{accepted_by}>.\nLink to thread: <#{channel_id}>\n\nAgree: {len(agree_users)}\nDisagree: {len(disagree_users)}",
                            "view": None, "embeds": embeds}))
                        thread = await bot.fetch_channel(channel_id)
                        message = await thread.fetch_message(message_id)
                        await old_message_edit_queue.put((message, {
                            "content": f"**Appeal has been rejected.** Appeal accepted by <@{accepted_by}>.",
                            "view": None}))
                        await bot.get_channel(channel_id).send(
                            f"Appeal on `{user.id}` has been rejected. <@{requested_by}> <@{accepted_by}>")
                        inprogresscol.delete_one({"_id": interaction.message.id})

                    else:  # new case exists
                        r_profile = format_user_r_profile(user, r_profile_list, title)
                        add_case = format_user_add_case(add_case_list, case_title)
                        embeds = [r_profile, add_case]
                        await old_message_edit_queue.put((interaction.message, {"content": f"**Report has been rejected.** Report accepted by <@{accepted_by}>.\nLink to thread: <#{channel_id}>\n\nAgree: {len(agree_users)}\nDisagree: {len(disagree_users)}",
                            "view": None, "embeds": embeds}))
                        thread = await bot.fetch_channel(channel_id)
                        message = await thread.fetch_message(message_id)
                        await old_message_edit_queue.put((message, {
                            "content": f"**Report has been rejected.** Report accepted by <@{accepted_by}>.",
                            "view": None}))
                        await bot.get_channel(channel_id).send(
                            f"Report on `{user.id}` has been rejected. <@{requested_by}> <@{accepted_by}>")
                        inprogresscol.delete_one({"_id": interaction.message.id})
                else:  # if new reported user
                    r_profile = format_user_r_profile(user, r_profile_list, title)
                    add_case = format_user_add_case(add_case_list, case_title)
                    embeds = [r_profile, add_case]
                    await old_message_edit_queue.put((interaction.message, {"content": f"**Report has been rejected.** Report accepted by <@{accepted_by}>.\nLink to thread: <#{channel_id}>\n\nAgree: {len(agree_users)}\nDisagree: {len(disagree_users)}",
                        "view": None, "embeds": embeds}))
                    thread = await bot.fetch_channel(channel_id)
                    message = await thread.fetch_message(message_id)
                    await old_message_edit_queue.put((message, {
                        "content": f"**Report has been rejected.** Report accepted by <@{accepted_by}>.",
                        "view": None}))
                    await bot.get_channel(channel_id).send(
                        f"Report on `{user.id}` has been rejected. <@{requested_by}> <@{accepted_by}>")
                    inprogresscol.delete_one({"_id": interaction.message.id})
                try:
                    voters = agree_users + disagree_users
                    for voter in voters:
                        voter_query = {"_id": str(voter)}
                        voter_profile = trusteduserscol.find_one(voter_query)
                        if voter_profile:
                            trusteduserscol.update_one(
                                voter_query,
                                {"$inc": {"votes": 1}}
                            )
                except Exception as e:
                    print(f"{e}")
                current_name = interaction.channel.name
                new_name = current_name if current_name.startswith("r-") else f"r-{current_name}"
                await asyncio.sleep(2)
                await interaction.channel.edit(name=new_name, archived=True, locked=True)
                return
            if not add_case_list:  # only alts edited
                await old_message_edit_queue.put((interaction.message, {"content": f"Report accepted by <@{accepted_by}>.\nLink to thread: <#{channel_id}>\n\nAgree: {len(agree_users)}\nDisagree: {len(disagree_users)}",
                    "embeds": [r_profile], "view": UserVoteView()}))
            elif len(add_case_list) == 1:  # [[add_case_list]] case to appeal
                add_case_list = add_case_list[0]
                add_case = format_user_add_case(add_case_list, case_title)
                reason_embed = discord.Embed(title="Reason", colour=0x1DCCA9, description=reason)
                embeds = [r_profile, add_case, reason_embed]
                await old_message_edit_queue.put((interaction.message, {"content": f"Appeal accepted by <@{accepted_by}>.\nLink to thread: <#{channel_id}>\n\nAgree: {len(agree_users)}\nDisagree: {len(disagree_users)}",
                    "embeds": embeds, "view": UserVoteView()}))
            else:  # new case exists
                add_case = format_user_add_case(add_case_list, case_title)
                embeds = [r_profile, add_case]
                await old_message_edit_queue.put((interaction.message, {"content": f"Report accepted by <@{accepted_by}>.\nLink to thread: <#{channel_id}>\n\nAgree: {len(agree_users)}\nDisagree: {len(disagree_users)}",
                    "embeds": embeds, "view": UserVoteView()}))

    @discord.ui.button(label="Remove Vote", style=discord.ButtonStyle.primary, custom_id="uservote:removevote")
    async def remove_vote_button(self, interaction, button):
        await interaction.response.defer()
        session = inprogresscol.find_one({"_id": interaction.message.id})
        if session:
            channel_id = session["channel_id"]
            r_profile_list = session["r_profile_list"]
            add_case_list = session.get("add_case_list")
            title = session["title"]
            case_title = session.get("case_title")
            accepted_by = session["accepted_by"]
            reason = session.get("reason")
            user_id = session["user_id"]
            user = await bot.fetch_user(user_id)
            agree_users, disagree_users = await handle_vote(interaction, session, "remove")
            #
            r_profile = format_user_r_profile(user, r_profile_list, title)
            if not add_case_list:
                reason_embed = discord.Embed(title="Reason", description=reason)
                embeds = [r_profile, reason_embed]
                await old_message_edit_queue.put((interaction.message, {"content": f"Report accepted by <@{accepted_by}>.\nLink to thread: <#{channel_id}>\n\nAgree: {len(agree_users)}\nDisagree: {len(disagree_users)}",
                    "embeds": embeds, "view": UserVoteView()}))
            elif len(add_case_list) == 1:  # [[add_case_list]] case to appeal
                add_case_list = add_case_list[0]
                add_case = format_user_add_case(add_case_list, case_title)
                reason_embed = discord.Embed(title="Reason", colour=0x1DCCA9, description=reason)
                embeds = [r_profile, add_case, reason_embed]
                await old_message_edit_queue.put((interaction.message, {"content": f"Appeal accepted by <@{accepted_by}>.\nLink to thread: <#{channel_id}>\n\nAgree: {len(agree_users)}\nDisagree: {len(disagree_users)}",
                    "embeds": embeds, "view": UserVoteView()}))
            else:
                add_case = format_user_add_case(add_case_list, case_title)
                embeds = [r_profile, add_case]
                await old_message_edit_queue.put((interaction.message, {"content": f"Report accepted by <@{accepted_by}>.\nLink to thread: <#{channel_id}>\n\nAgree: {len(agree_users)}\nDisagree: {len(disagree_users)}",
                    "embeds": embeds, "view": UserVoteView()}))

    @discord.ui.button(label="Publish", style=discord.ButtonStyle.grey, custom_id="uservote:publish")
    async def publish_button(self, interaction, button):
        await interaction.response.defer(thinking=True)
        session = inprogresscol.find_one({"_id": interaction.message.id})
        if session:
            requested_by = session["requested_by"]
            channel_id = session["channel_id"]
            message_id = session["message_id"]
            r_profile_list = session["r_profile_list"]
            add_case_list = session.get("add_case_list")
            title = session["title"]
            case_title = session.get("case_title")
            agree_users = session["agree_users"]
            disagree_users = session["disagree_users"]
            reason = session.get("reason")
            user_id = session["user_id"]
            user = await bot.fetch_user(user_id)
            o5_check = get(interaction.user.guild.roles, id=o5_role) in interaction.user.roles and len(
                agree_users) >= 5 and len(agree_users) > len(disagree_users)
            sr_check = is_sr(interaction.user) and interaction.user.id != requested_by and len(
                agree_users) >= 5 and len(agree_users) > len(disagree_users)
            if o5_check or sr_check:
                accepted_by = interaction.user.id
                user_id = user.id
                user_query = {"_id": str(user_id)}
                user_profile = userscol.find_one(user_query)
                if user_profile:  # if editing existing reported user
                    old_r_profile_list = user_profile["r_profile_list"]
                    cases = []
                    no_of_cases = len(user_profile) - 2
                    for i in range(1, no_of_cases + 1):
                        cases.append(user_profile[str(i)])
                    #
                    if old_r_profile_list[0] != r_profile_list[0]:  # comparing alts
                        old_alts_list = old_r_profile_list[0].strip("`").split()
                        new_alts_list = r_profile_list[0].strip("`").split()
                        added_alts_list = set(new_alts_list) - set(old_alts_list)
                        removed_alts_list = set(old_alts_list) - set(new_alts_list)
                        for alt in added_alts_list:
                            new_user = {"_id": str(alt), "main": str(user.id)}
                            try:
                                userscol.insert_one(new_user)
                            except DuplicateKeyError:
                                existing = userscol.find_one({"_id": str(alt)})
                                if existing and "r_profile_list" in existing:
                                    await interaction.channel.send(f"User `{user.id}` was reported with alt `{alt}` which already exists as a reported user. <@&{sr_ping}> Separate reports detected, use /merge to merge them.")
                        for alt in removed_alts_list:
                            userscol.delete_one({"_id": alt})
                        update_operation = {'$set': {"r_profile_list": r_profile_list}}
                        userscol.update_one(user_query, update_operation)
                    if not add_case_list:  # only alts edited
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
                        r_profile = format_user_r_profile(user, r_profile_list, title)
                        user_reports_channel = bot.get_channel(USER_REPORTS_CHANNEL)
                        await user_reports_channel.send(content=f"<@&{updated_user_report_ping}>\nEdited alts for `{user.id}`",
                                                        embed=r_profile)
                        reason_embed = discord.Embed(title="Reason", description=reason)
                        await user_reports_channel.send(content=f"Reason for change(s)", embed=reason_embed)
                        await old_message_edit_queue.put((interaction.message, {"content": f"**Report has been published.** Report accepted by <@{accepted_by}>.\nLink to thread: <#{channel_id}>\n\nAgree: {len(agree_users)}\nDisagree: {len(disagree_users)}",
                            "embeds": [r_profile], "view": None}))
                        thread = await bot.fetch_channel(channel_id)
                        message = await thread.fetch_message(message_id)
                        await old_message_edit_queue.put((message, {
                            "content": f"**Report has been published.** Report accepted by <@{accepted_by}>.",
                            "view": None}))
                        await bot.get_channel(channel_id).send(
                            f"Report on `{user.id}` has been published. <@{requested_by}> <@{accepted_by}>")
                        inprogresscol.delete_one({"_id": interaction.message.id})
                    elif len(add_case_list) == 1:  # [[add_case_list]] case to appeal
                        add_case_list = add_case_list[0]
                        appeal_case_number = next((k for k, v in user_profile.items() if v == add_case_list), None)
                        query_filter = {"_id": str(user.id)}
                        update_operation = {"$unset": {appeal_case_number: ""}}
                        userscol.update_one(query_filter, update_operation)
                        #
                        user_query = {"_id": str(user_id)}
                        user_profile = userscol.find_one(user_query)
                        alts = r_profile_list[0].strip("`").split() if r_profile_list[0] else []
                        if len(user_profile) == 2:
                            userscol.delete_one(user_query)
                            for alt in alts:
                                user_query = {"_id": alt}
                                userscol.delete_one(user_query)
                        else:
                            no_of_cases = len(user_profile) - 2
                            for i in range(int(appeal_case_number), no_of_cases + 1):
                                user_profile[appeal_case_number] = user_profile.pop(str(int(appeal_case_number) + 1))
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
                            all_tags_list = list(dict.fromkeys(all_tags_list))
                            title = all_tags_list[0]
                            all_other_tags = selected_string(all_tags_list[1:])
                            r_profile_list = user_profile["r_profile_list"]
                            r_profile_list[1] = all_other_tags
                            user_profile["r_profile_list"] = r_profile_list
                            query_filter = {"_id": str(user.id)}
                            userscol.replace_one(query_filter, user_profile)
                        #
                        r_profile = format_user_r_profile(user, r_profile_list, title)
                        add_case = format_user_add_case(add_case_list, case_title)
                        reason_embed = discord.Embed(title="Reason", colour=0x1DCCA9, description=reason)
                        embeds = [r_profile, add_case]
                        #
                        user_reports_channel = bot.get_channel(USER_REPORTS_CHANNEL)
                        await user_reports_channel.send(content=f"<@&{appealed_user_report_ping}>\nAppeal on `{user.id}`",
                                                        embeds=embeds)
                        await user_reports_channel.send(content=f"Reason for appeal", embed=reason_embed)
                        await old_message_edit_queue.put((interaction.message, {"content": f"**Appeal has been published.** Appeal accepted by <@{accepted_by}>.\nLink to thread: <#{channel_id}>\n\nAgree: {len(agree_users)}\nDisagree: {len(disagree_users)}",
                            "view": None, "embeds": embeds}))
                        thread = await bot.fetch_channel(channel_id)
                        message = await thread.fetch_message(message_id)
                        await old_message_edit_queue.put((message, {
                            "content": f"**Appeal has been published.** Appeal accepted by <@{accepted_by}>.",
                            "view": None}))
                        await bot.get_channel(channel_id).send(
                            f"Appeal on `{user.id}` has been published. <@{requested_by}> <@{accepted_by}>")
                        inprogresscol.delete_one({"_id": interaction.message.id})
                    else:  # new case exists
                        add_case_list["accepted_by"] = f"{interaction.user.mention}"
                        inprogresscol.update_one(
                            {"_id": interaction.message.id},
                            {"$set": {"add_case_list": add_case_list}},
                        )
                        #
                        r_profile = format_user_r_profile(user, r_profile_list, title)
                        add_case = format_user_add_case(add_case_list, case_title)
                        embeds = [r_profile, add_case]

                        query_filter = {"_id": str(user.id)}
                        update_operation = {'$set': {"r_profile_list": r_profile_list}}
                        userscol.update_one(query_filter, update_operation)
                        update_operation = {'$set': {str(no_of_cases + 1): add_case_list}}
                        userscol.update_one(query_filter, update_operation)

                        user_reports_channel = bot.get_channel(USER_REPORTS_CHANNEL)
                        await user_reports_channel.send(content=f"<@&{updated_user_report_ping}>\nAdded report on `{user.id}`",
                                                        embeds=embeds)
                        await old_message_edit_queue.put((interaction.message, {"content": f"**Report has been published.** Report accepted by <@{accepted_by}>.\nLink to thread: <#{channel_id}>\n\nAgree: {len(agree_users)}\nDisagree: {len(disagree_users)}",
                            "view": None, "embeds": embeds}))
                        thread = await bot.fetch_channel(channel_id)
                        message = await thread.fetch_message(message_id)
                        await old_message_edit_queue.put((message, {
                            "content": f"**Report has been published.** Report accepted by <@{accepted_by}>.",
                            "view": None}))
                        await bot.get_channel(channel_id).send(
                            f"Report on `{user.id}` has been published. <@{requested_by}> <@{accepted_by}>")
                        inprogresscol.delete_one({"_id": interaction.message.id})
                else:  # if new reported user
                    add_case_list["accepted_by"] = interaction.user.mention
                    inprogresscol.update_one(
                        {"_id": interaction.message.id},
                        {"$set": {"add_case_list": add_case_list}},
                    )
                    #
                    r_profile = format_user_r_profile(user, r_profile_list, title)
                    add_case = format_user_add_case(add_case_list, case_title)
                    embeds = [r_profile, add_case]
                    new_user = {"_id": str(user.id), "r_profile_list": r_profile_list,
                                "1": add_case_list}
                    userscol.insert_one(new_user)
                    alts_list = r_profile_list[0].strip("`").split() if r_profile_list[0] else []
                    for alt in alts_list:
                        new_user = {"_id": str(alt), "main": str(user.id)}
                        try:
                            userscol.insert_one(new_user)
                        except DuplicateKeyError:
                            existing = userscol.find_one({"_id": str(alt)})
                            if existing and "r_profile_list" in existing:
                                await interaction.channel.send(
                                    f"User `{user.id}` was reported with alt `{alt}` which already exists as a reported user. <@&{sr_ping}> Separate reports detected, use /merge to merge them.")
                    user_reports_channel = bot.get_channel(USER_REPORTS_CHANNEL)
                    await user_reports_channel.send(content=f"<@&{new_user_report_ping}>\nNew report on `{user.id}`",
                                                    embeds=embeds)
                    await old_message_edit_queue.put((interaction.message, {"content": f"**Report has been published.** Report accepted by <@{accepted_by}>.\nLink to thread: <#{channel_id}>\n\nAgree: {len(agree_users)}\nDisagree: {len(disagree_users)}",
                        "view": None, "embeds": embeds}))
                    thread = await bot.fetch_channel(channel_id)
                    message = await thread.fetch_message(message_id)
                    await old_message_edit_queue.put((message, {
                        "content": f"**Report has been published.** Report accepted by <@{accepted_by}>.",
                        "view": None}))
                    await bot.get_channel(channel_id).send(
                        f"Report on `{user.id}` has been published. <@{requested_by}> <@{accepted_by}>")
                    inprogresscol.delete_one({"_id": interaction.message.id})
                try:
                    voters = agree_users + disagree_users
                    for voter in voters:
                        voter_query = {"_id": str(voter)}
                        voter_profile = trusteduserscol.find_one(voter_query)
                        if voter_profile:
                            trusteduserscol.update_one(
                                voter_query,
                                {"$inc": {"votes": 1}}
                            )

                    staff_query = {"_id": str(requested_by)}
                    if trusteduserscol.find_one(staff_query):
                        trusteduserscol.update_one(
                            staff_query,
                            {"$inc": {"reports": 1}}
                        )
                    if staffweeklycol.find_one(staff_query):
                        staffweeklycol.update_one(
                            staff_query,
                            {"$inc": {"weekly_reports": 1}}
                        )

                    sr_query = {"_id": str(accepted_by)}
                    if trusteduserscol.find_one(sr_query):
                        trusteduserscol.update_one(
                            {"_id": str(accepted_by)},
                            {"$inc": {"reviews": 1}}
                        )
                    if staffweeklycol.find_one(sr_query):
                        staffweeklycol.update_one(
                            {"_id": str(accepted_by)},
                            {"$inc": {"weekly_reviews": 1}}
                        )
                except Exception as e:
                    print(f"{e}")
                current_name = interaction.channel.name
                new_name = current_name if current_name.startswith("p-") else f"p-{current_name}"
                await asyncio.sleep(2)
                await interaction.channel.edit(name=new_name, archived=True, locked=True)
            else:
                await interaction.followup.send("You do not have permission to publish the report.", ephemeral=True)


# new server
class NewServerReportView(discord.ui.View):
    def __init__(self, guild, requested_by):
        super().__init__(timeout=3600)
        self.guild = guild
        self.requested_by = requested_by
    @discord.ui.button(label="Report", style=discord.ButtonStyle.red, custom_id="newserverreport:report")
    async def report_button(self, interaction, button):
        #
        guild = self.guild
        requested_by = self.requested_by
        #
        await interaction.response.defer()
        existing_entry = inprogresscol.find_one({"guild_id": guild.id})
        if existing_entry:
            # ongoing vote
            if "vote_channel_id" in existing_entry:
                vote_channel_id = existing_entry["vote_channel_id"]
                vote_message_id = existing_entry["_id"]
                vote_channel = bot.get_channel(vote_channel_id)
                if not vote_channel:
                    vote_channel = await bot.fetch_channel(vote_channel_id)
                try:
                    vote_message = await vote_channel.fetch_message(vote_message_id)
                except discord.NotFound:
                    return await interaction.followup.send(
                        "This message could not be found. It may have been deleted.", ephemeral=True)
                await interaction.followup.send(
                    f"There already exists an ongoing vote on `{guild.id}`: {vote_message.jump_url}")
            # ongoing report
            else:
                channel_id = existing_entry["channel_id"]
                message_id = existing_entry["_id"]
                thread = await bot.fetch_channel(channel_id)
                try:
                    message = await thread.fetch_message(message_id)
                except discord.NotFound:
                    return await interaction.followup.send(
                        "This message could not be found. It may have been deleted.", ephemeral=True)
                await interaction.followup.send(
                    f"There already exists an ongoing report on `{guild.id}`: {message.jump_url}")
            return
        if requested_by == interaction.user:
            await interaction.edit_original_response(view=None)
            msg = await interaction.followup.send(f"Initializing report on `{guild.id}`...", wait=True)
            title = "TBC"
            case_title = "TBC"
            r_profile_list = [
                # [0] owner
                "",
                # [1] other tags
                "",
            ]
            add_case_list = {
                "date_added": f"<t:{round(int(discord.utils.utcnow().timestamp()))}:D> (<t:{round(int(discord.utils.utcnow().timestamp()))}:R>)",
                "tags": "",
                "reason": "",
                "contributor": "",
                "staff": f"{interaction.user.mention}",
                "accepted_by": "",
                "proofs": [],
            }
            channel_id = msg.channel.id
            message_id = msg.id
            r_profile = format_server_r_profile(guild, r_profile_list, title)
            add_case = format_server_add_case(add_case_list, case_title)
            embeds = [r_profile, add_case]
            try:
                inprogresscol.insert_one({"_id": message_id,
                                          "guild_id": guild.id,
                                          "guild_data": {
                                                "id": guild.id,
                                                "name": guild.name,
                                                "icon": guild.icon.url if guild.icon else None,
                                                "banner": guild.banner.url if guild.banner else None,
                                                "created_at": int(guild.created_at.timestamp()) if interaction.guild.created_at else None
                                            },
                                          "requested_by": requested_by.id,
                                          "channel_id": channel_id,
                                          "r_profile_list": r_profile_list,
                                          "add_case_list": add_case_list,
                                          "title": title,
                                          "case_title": case_title
                                          })
            except DuplicateKeyError: pass
            await msg.edit(embeds=embeds, view=ServerOwnerView())
        elif is_active_staff(interaction.user):
            await interaction.followup.send(
                f"This was requested by {requested_by.mention}, you cannot interact with this component.",
                ephemeral=True)
        else:
            await interaction.followup.send("You do not have permission to use this button.", ephemeral=True)

class ServerOwnerView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(emoji="<:rightarrow:1458096774521553038>", style=discord.ButtonStyle.grey, custom_id="serverowner:next")
    async def next_button(self, interaction, button):
        await interaction.response.defer()
        #
        session = inprogresscol.find_one({"_id": interaction.message.id})
        if session:
            guild_data = session["guild_data"]
            requested_by = session["requested_by"]
            channel_id = session["channel_id"]
            message_id = interaction.message.id
            r_profile_list = session["r_profile_list"]
            add_case_list = session["add_case_list"]
            title = session["title"]
            case_title = session["case_title"]
            thread = await bot.fetch_channel(channel_id)
            message = await thread.fetch_message(message_id)
            if requested_by == interaction.user.id or is_sr(interaction.user):
                r_profile = reconstruct_server_r_profile(guild_data, r_profile_list, title)
                add_case = format_server_add_case(add_case_list, case_title)
                embeds = [r_profile, add_case]
                await message.edit(embeds=embeds, view=ServerTagsView())

    @discord.ui.button(label="Owner", style=discord.ButtonStyle.green, custom_id="serverowner:input")
    async def owner_button(self, interaction, button):
        session = inprogresscol.find_one({"_id": interaction.message.id})
        if session:
            requested_by = session["requested_by"]
            if requested_by == interaction.user.id:
                await interaction.response.send_modal(ServerOwnerModal())
class ServerOwnerModal(discord.ui.Modal, title="Owner"):
    owner = discord.ui.TextInput(label="Owner", placeholder="Input Server Owner ID here.", required=True,
                                  style=discord.TextStyle.short)
    def __init__(self):
        super().__init__(timeout=None)
    async def on_submit(self, interaction):
        await interaction.response.defer()
        #
        session = inprogresscol.find_one({"_id": interaction.message.id})
        if session:
            guild_data = session["guild_data"]
            channel_id = session["channel_id"]
            message_id = interaction.message.id
            r_profile_list = session["r_profile_list"]
            add_case_list = session["add_case_list"]
            title = session["title"]
            case_title = session["case_title"]
            thread = await bot.fetch_channel(channel_id)
            message = await thread.fetch_message(message_id)
            try:
                valid_owner = await bot.fetch_user(int(self.owner.value))
            except Exception:
                pass
            else:
                if valid_owner:
                    r_profile_list[0] = f"{valid_owner.mention}"
            #
            inprogresscol.update_one(
                {"_id": interaction.message.id},
                {"$set": {"r_profile_list": r_profile_list}
                })
            #
            r_profile = reconstruct_server_r_profile(guild_data, r_profile_list, title)
            add_case = format_server_add_case(add_case_list, case_title)
            embeds = [r_profile, add_case]
            await message.edit(embeds=embeds, view=ServerOwnerView())

class ServerTagsView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
    @discord.ui.button(emoji="<:leftarrow:1458096658062770176>", style=discord.ButtonStyle.grey, custom_id="servertags:prev")
    async def prev_button(self, interaction, button):
        await interaction.response.defer()
        #
        session = inprogresscol.find_one({"_id": interaction.message.id})
        if session:
            guild_data = session["guild_data"]
            requested_by = session["requested_by"]
            channel_id = session["channel_id"]
            message_id = interaction.message.id
            r_profile_list = session["r_profile_list"]
            add_case_list = session["add_case_list"]
            title = session["title"]
            case_title = session["case_title"]
            thread = await bot.fetch_channel(channel_id)
            message = await thread.fetch_message(message_id)
            if requested_by == interaction.user.id or is_sr(interaction.user):
                r_profile = reconstruct_server_r_profile(guild_data, r_profile_list, title)
                add_case = format_server_add_case(add_case_list, case_title)
                embeds = [r_profile, add_case]
                await message.edit(embeds=embeds, view=ServerOwnerView())

    @discord.ui.button(emoji="<:rightarrow:1458096774521553038>", style=discord.ButtonStyle.grey, custom_id="servertags:next")
    async def next_button(self, interaction, button):
        await interaction.response.defer()
        #
        session = inprogresscol.find_one({"_id": interaction.message.id})
        if session:
            guild_data = session["guild_data"]
            requested_by = session["requested_by"]
            channel_id = session["channel_id"]
            message_id = interaction.message.id
            r_profile_list = session["r_profile_list"]
            add_case_list = session["add_case_list"]
            title = session["title"]
            case_title = session["case_title"]
            thread = await bot.fetch_channel(channel_id)
            message = await thread.fetch_message(message_id)
            if requested_by == interaction.user.id or is_sr(interaction.user):
                r_profile = reconstruct_server_r_profile(guild_data, r_profile_list, title)
                add_case = format_server_add_case(add_case_list, case_title)
                embeds = [r_profile, add_case]
                await message.edit(embeds=embeds, view=ServerReasonView())

    @discord.ui.select(options=server_tags_options, placeholder="Select Tag(s)...", custom_id="servertags:select",
                       max_values=len(server_tags_options))
    async def select_callback(self, interaction, select):
        await interaction.response.defer()
        #
        session = inprogresscol.find_one({"_id": interaction.message.id})
        if session:
            guild_data = session["guild_data"]
            requested_by = session["requested_by"]
            channel_id = session["channel_id"]
            message_id = interaction.message.id
            r_profile_list = session["r_profile_list"]
            add_case_list = session["add_case_list"]
            title = session["title"]
            case_title = session["case_title"]
            thread = await bot.fetch_channel(channel_id)
            message = await thread.fetch_message(message_id)
            if requested_by == interaction.user.id:
                sorted_tags = sort_server_tags(self.select_callback.values)
                case_title = sorted_tags[0]
                tags = selected_string(sorted_tags)
                add_case_list["tags"] = tags
                title = sorted_tags[0]
                all_other_tags = selected_string(sorted_tags[1:])
                r_profile_list[1] = all_other_tags
                #
                inprogresscol.update_one(
                    {"_id": interaction.message.id},
                    {"$set": {
                        "r_profile_list": r_profile_list,
                        "add_case_list": add_case_list,
                        "title": title,
                        "case_title": case_title, }
                    })
                #
                r_profile = reconstruct_server_r_profile(guild_data, r_profile_list, title)
                add_case = format_server_add_case(add_case_list, case_title)
                embeds = [r_profile, add_case]
                await message.edit(embeds=embeds)

class ServerReasonView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(emoji="<:leftarrow:1458096658062770176>", style=discord.ButtonStyle.grey, custom_id="serverreason:prev")
    async def prev_button(self, interaction, button):
        await interaction.response.defer()
        #
        session = inprogresscol.find_one({"_id": interaction.message.id})
        if session:
            guild_data = session["guild_data"]
            requested_by = session["requested_by"]
            channel_id = session["channel_id"]
            message_id = interaction.message.id
            r_profile_list = session["r_profile_list"]
            add_case_list = session["add_case_list"]
            title = session["title"]
            case_title = session["case_title"]
            thread = await bot.fetch_channel(channel_id)
            message = await thread.fetch_message(message_id)
            if requested_by == interaction.user.id or is_sr(interaction.user):
                r_profile = reconstruct_server_r_profile(guild_data, r_profile_list, title)
                add_case = format_server_add_case(add_case_list, case_title)
                embeds = [r_profile, add_case]
                await message.edit(embeds=embeds, view=ServerTagsView())

    @discord.ui.button(emoji="<:rightarrow:1458096774521553038>", style=discord.ButtonStyle.grey, custom_id="serverreason:next")
    async def next_button(self, interaction, button):
        await interaction.response.defer()
        #
        session = inprogresscol.find_one({"_id": interaction.message.id})
        if session:
            guild_data = session["guild_data"]
            requested_by = session["requested_by"]
            channel_id = session["channel_id"]
            message_id = interaction.message.id
            r_profile_list = session["r_profile_list"]
            add_case_list = session["add_case_list"]
            title = session["title"]
            case_title = session["case_title"]
            thread = await bot.fetch_channel(channel_id)
            message = await thread.fetch_message(message_id)
            if requested_by == interaction.user.id or is_sr(interaction.user):
                r_profile = reconstruct_server_r_profile(guild_data, r_profile_list, title)
                add_case = format_server_add_case(add_case_list, case_title)
                embeds = [r_profile, add_case]
                await message.edit(embeds=embeds, view=ServerContributorView())

    @discord.ui.button(label="Reason", style=discord.ButtonStyle.green, custom_id="serverreason:input")
    async def reason_button(self, interaction, button):
        #
        session = inprogresscol.find_one({"_id": interaction.message.id})
        if session:
            requested_by = session["requested_by"]
            if requested_by == interaction.user.id:
                await interaction.response.send_modal(ServerReasonModal())
class ServerReasonModal(discord.ui.Modal, title="Reason"):
    reason = discord.ui.TextInput(label="Reason", placeholder="Input reason here.", required=True,
                                  style=discord.TextStyle.long)

    def __init__(self):
        super().__init__(timeout=None)

    async def on_submit(self, interaction):
        await interaction.response.defer()
        #
        session = inprogresscol.find_one({"_id": interaction.message.id})
        if session:
            guild_data = session["guild_data"]
            channel_id = session["channel_id"]
            message_id = interaction.message.id
            r_profile_list = session["r_profile_list"]
            add_case_list = session["add_case_list"]
            title = session["title"]
            case_title = session["case_title"]
            thread = await bot.fetch_channel(channel_id)
            message = await thread.fetch_message(message_id)
            reason = re.sub(r"\s+", " ", self.reason.value)
            add_case_list["reason"] = reason
            #
            inprogresscol.update_one(
                {"_id": interaction.message.id},
                {"$set": {"add_case_list": add_case_list}
                })
            #
            r_profile = reconstruct_server_r_profile(guild_data, r_profile_list, title)
            add_case = format_server_add_case(add_case_list, case_title)
            embeds = [r_profile, add_case]
            await message.edit(embeds=embeds, view=ServerReasonView())

class ServerContributorView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(emoji="<:leftarrow:1458096658062770176>", style=discord.ButtonStyle.grey,
                       custom_id="servercontributor:prev")
    async def prev_button(self, interaction, button):
        await interaction.response.defer()
        #
        session = inprogresscol.find_one({"_id": interaction.message.id})
        if session:
            guild_data = session["guild_data"]
            requested_by = session["requested_by"]
            channel_id = session["channel_id"]
            message_id = interaction.message.id
            r_profile_list = session["r_profile_list"]
            add_case_list = session["add_case_list"]
            title = session["title"]
            case_title = session["case_title"]
            thread = await bot.fetch_channel(channel_id)
            message = await thread.fetch_message(message_id)
            if requested_by == interaction.user.id or is_sr(interaction.user):
                r_profile = reconstruct_server_r_profile(guild_data, r_profile_list, title)
                add_case = format_server_add_case(add_case_list, case_title)
                embeds = [r_profile, add_case]
                await message.edit(embeds=embeds, view=ServerReasonView())

    @discord.ui.button(emoji="<:rightarrow:1458096774521553038>", style=discord.ButtonStyle.grey,
                       custom_id="servercontributor:next")
    async def next_button(self, interaction, button):
        await interaction.response.defer()
        #
        session = inprogresscol.find_one({"_id": interaction.message.id})
        if session:
            guild_data = session["guild_data"]
            requested_by = session["requested_by"]
            channel_id = session["channel_id"]
            message_id = interaction.message.id
            r_profile_list = session["r_profile_list"]
            add_case_list = session["add_case_list"]
            title = session["title"]
            case_title = session["case_title"]
            thread = await bot.fetch_channel(channel_id)
            message = await thread.fetch_message(message_id)
            if requested_by == interaction.user.id or is_sr(interaction.user):
                r_profile = reconstruct_server_r_profile(guild_data, r_profile_list, title)
                add_case = format_server_add_case(add_case_list, case_title)
                embeds = [r_profile, add_case]
                await message.edit(embeds=embeds, view=ServerProofsView())

    @discord.ui.button(label="Contributor", style=discord.ButtonStyle.green, custom_id="servercontributor:input")
    async def contributor_button(self, interaction, button):
        #
        session = inprogresscol.find_one({"_id": interaction.message.id})
        if session:
            requested_by = session["requested_by"]
            if requested_by == interaction.user.id:
                await interaction.response.send_modal(ServerContributorModal())
class ServerContributorModal(discord.ui.Modal, title="Contributor"):
    contributor = discord.ui.TextInput(label="Contributor",
                                       placeholder="User ID / n if Anonymous.", required=True,
                                       style=discord.TextStyle.short)

    def __init__(self):
        super().__init__(timeout=None)

    async def on_submit(self, interaction):
        await interaction.response.defer()
        #
        session = inprogresscol.find_one({"_id": interaction.message.id})
        if session:
            guild_data = session["guild_data"]
            channel_id = session["channel_id"]
            message_id = interaction.message.id
            r_profile_list = session["r_profile_list"]
            add_case_list = session["add_case_list"]
            title = session["title"]
            case_title = session["case_title"]
        #
            thread = await bot.fetch_channel(channel_id)
            message = await thread.fetch_message(message_id)
            contributor_input = self.contributor.value
            if contributor_input.lower() == "n":
                add_case_list["contributor"] = "Anonymous"
            else:
                try:
                    contributor_id = await bot.fetch_user(int(contributor_input))
                except Exception:
                    add_case_list["contributor"] = ""
                else:
                    add_case_list["contributor"] = f"<@{contributor_id.id}>"
            #
            inprogresscol.update_one(
                {"_id": interaction.message.id},
                {"$set": {"add_case_list": add_case_list}
                })
            #
            r_profile = reconstruct_server_r_profile(guild_data, r_profile_list, title)
            add_case = format_server_add_case(add_case_list, case_title)
            embeds = [r_profile, add_case]
            await message.edit(embeds=embeds, view=ServerContributorView())

class ServerProofsView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(emoji="<:leftarrow:1458096658062770176>", style=discord.ButtonStyle.grey, custom_id="serverproofs:prev")
    async def prev_button(self, interaction, button):
        await interaction.response.defer()
        #
        session = inprogresscol.find_one({"_id": interaction.message.id})
        if session:
            guild_data = session["guild_data"]
            requested_by = session["requested_by"]
            channel_id = session["channel_id"]
            message_id = interaction.message.id
            r_profile_list = session["r_profile_list"]
            add_case_list = session["add_case_list"]
            title = session["title"]
            case_title = session["case_title"]
            thread = await bot.fetch_channel(channel_id)
            message = await thread.fetch_message(message_id)
            if requested_by == interaction.user.id or is_sr(interaction.user):
                r_profile = reconstruct_server_r_profile(guild_data, r_profile_list, title)
                add_case = format_server_add_case(add_case_list, case_title)
                embeds = [r_profile, add_case]
                await message.edit(embeds=embeds, view=ServerContributorView())

    @discord.ui.button(label="Add Proofs", style=discord.ButtonStyle.green, custom_id="serverproofs:input")
    async def proofs_button(self, interaction, button):
        #
        session = inprogresscol.find_one({"_id": interaction.message.id})
        if session:
            requested_by = session["requested_by"]
            add_case_list = session["add_case_list"]
            #
            if requested_by == interaction.user.id:
                image_links = []
                add_case_list["proofs"] = []
                await interaction.response.send_message(
                    "Please send the images you would like to upload (max 10). **All images previously uploaded in this session have been removed.**",
                    ephemeral=True)

                def check(m):
                    return m.author == interaction.user and m.channel == interaction.channel

                try:
                    msg = await bot.wait_for('message', check=check, timeout=120.0)
                except asyncio.TimeoutError:
                    await interaction.followup.send("You took too long to upload an image.", ephemeral=True)
                    return
                if msg.attachments:
                    for attachment in msg.attachments:
                        # Ensure the attachment is an image (optional check)
                        if attachment.content_type and attachment.content_type.startswith('image/'):
                            try:
                                # 1. Download the file data using aiohttp
                                async with aiohttp.ClientSession() as http_session:
                                    async with http_session.get(attachment.url) as resp:
                                        # For this example, we just send back the image URL and filename
                                        data = io.BytesIO(await resp.read())
                                        file = discord.File(data, filename=attachment.filename)
                                        channel_to_send = bot.get_channel(PROOFS_CHANNEL)
                                        sent_message = await channel_to_send.send(file=file)
                                        if sent_message.attachments:
                                            new_image_url = sent_message.attachments[0].url
                                            image_links.append(new_image_url)
                                            add_case_list["proofs"].append(new_image_url)
                            except Exception:
                                await msg.channel.send(f"An error occurred with file {attachment.filename}")
                #
                inprogresscol.update_one(
                    {"_id": interaction.message.id},
                    {"$set": {"add_case_list": add_case_list}
                     })
                #
                image_embeds = image_links_to_embeds(image_links)
                await interaction.followup.send(f"Images received from {interaction.user.mention}.",
                                                embeds=image_embeds)

    @discord.ui.button(label="Show Proofs", style=discord.ButtonStyle.grey, custom_id="serverproofs:showproofs")
    async def show_proofs_button(self, interaction, button):
        await interaction.response.defer()
        #
        session = inprogresscol.find_one({"_id": interaction.message.id})
        if session:
            guild_data = session["guild_data"]
            requested_by = session["requested_by"]
            add_case_list = session["add_case_list"]
            guild_id = session["guild_id"]
            #
            if requested_by == interaction.user.id or is_sr(interaction.user):
                image_embeds = image_links_to_embeds(add_case_list["proofs"])
                await interaction.followup.send(f"Proofs for `{guild_id}`",
                                                embeds=image_embeds, ephemeral=True)

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.grey, custom_id="serverproofs:cancel")
    async def cancel_button(self, interaction, button):
        await interaction.response.defer()
        #
        session = inprogresscol.find_one({"_id": interaction.message.id})
        if session:
            requested_by = session["requested_by"]
            channel_id = session["channel_id"]
            message_id = interaction.message.id
            #
            thread = await bot.fetch_channel(channel_id)
            message = await thread.fetch_message(message_id)
            if requested_by == interaction.user.id or is_sr(interaction.user):
                inprogresscol.delete_one({"_id": interaction.message.id})
                await message.edit(content=f"**Cancelled by {interaction.user.mention}.**", view=None)

    @discord.ui.button(label="Accept", style=discord.ButtonStyle.grey, custom_id="serverproofs:accept")
    async def accept_button(self, interaction, button):
        await interaction.response.defer()
        #
        session = inprogresscol.find_one({"_id": interaction.message.id})
        if session:
            guild_data = session["guild_data"]
            requested_by = session["requested_by"]
            channel_id = session["channel_id"]
            message_id = interaction.message.id
            r_profile_list = session["r_profile_list"]
            add_case_list = session["add_case_list"]
            title = session["title"]
            case_title = session["case_title"]
            guild_id = guild_data["id"]
            #
            thread = await bot.fetch_channel(channel_id)
            message = await thread.fetch_message(message_id)
            if is_sr(interaction.user) and interaction.user.id != requested_by:
                accepted_by = interaction.user
                add_case_list["accepted_by"] = f"<@{interaction.user.id}>"
                #
                r_profile = reconstruct_server_r_profile(guild_data, r_profile_list, title)
                add_case = format_server_add_case(add_case_list, case_title)
                embeds = [r_profile, add_case]
                #
                vote_channel = bot.get_channel(VOTE_CHANNEL)
                agree_users = []
                disagree_users = []
                all_images_to_show = add_case_list["proofs"]
                image_embeds = image_links_to_embeds(all_images_to_show)
                new_report_message = await vote_channel.send(content=f"New report on `{guild_id}`")
                new_report_thread = await new_report_message.create_thread(name=f"server-{guild_id}")
                await new_report_thread.send(f"<@&{ticket_ping}>")
                vote_msg = await new_report_thread.send(
                    content=f"Report accepted by {accepted_by.mention}.\nLink to thread: <#{channel_id}>\n\nAgree: 0\nDisagree: 0",
                    embeds=embeds, view=ServerVoteView())
                vote_channel_id = vote_msg.channel.id
                vote_message_id = vote_msg.id
                old_session = inprogresscol.find_one({"guild_id": guild_id})
                if old_session:
                    inprogresscol.delete_one({"_id": old_session["_id"]})
                inprogresscol.insert_one({
                    "_id": vote_message_id,
                    "guild_id": guild_id,
                    "guild_data": guild_data,
                    "requested_by": requested_by,
                    "channel_id": channel_id,
                    "message_id": interaction.message.id,
                    "r_profile_list": r_profile_list,
                    "add_case_list": add_case_list,
                    "title": title,
                    "case_title": case_title,
                    "vote_channel_id": vote_channel_id,
                    "accepted_by": accepted_by.id,
                    "agree_users": agree_users,
                    "disagree_users": disagree_users,
                })
                await new_report_thread.send(content=f"Proofs for `{guild_id}`", embeds=image_embeds)
                await old_message_edit_queue.put((message, {"content": "Report has been submitted for voting.", "view": None}))
            else:
                await interaction.followup.send("You do not have permission to accept the report for voting.",
                                                ephemeral=True)


# edit server
class EditServerReportView(discord.ui.View):
    def __init__(self, guild, server_profile, requested_by, current_case):
        super().__init__(timeout=3600)
        self.guild = guild
        self.server_profile = server_profile
        self.requested_by = requested_by
        self.current_case = current_case

    @discord.ui.button(emoji="<:leftarrow:1458096658062770176>", style=discord.ButtonStyle.grey, custom_id="editserverreport:prev")
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
                                                         view=EditServerReportView(guild, server_profile, requested_by,
                                                                                 current_case))

    @discord.ui.button(emoji="<:rightarrow:1458096774521553038>", style=discord.ButtonStyle.grey, custom_id="editserverreport:next")
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
                                                         view=EditServerReportView(guild, server_profile, requested_by,
                                                                                 current_case))

    @discord.ui.button(label="Proofs", style=discord.ButtonStyle.grey, custom_id="editserverreport:seeproofs")
    async def proofs_button(self, interaction, button):
        await interaction.response.defer()
        #
        guild = self.guild
        server_profile = self.server_profile
        requested_by = self.requested_by
        current_case = self.current_case
        #
        r_profile_list = server_profile["r_profile_list"]
        no_of_cases = len(server_profile) - 2
        cases = []
        for i in range(1, no_of_cases + 1):
            cases.append(server_profile[str(i)])
        image_links = cases[current_case - 1]["proofs"]
        image_embeds = image_links_to_embeds(image_links)
        await interaction.followup.send(f"Proofs for `{guild.id}`", embeds=image_embeds, ephemeral=True)

    @discord.ui.button(label="Edit Owner", style=discord.ButtonStyle.primary, custom_id="editserverreport:editowner", row=1)
    async def edit_owner_button(self, interaction, button):
        #
        guild = self.guild
        server_profile = self.server_profile
        requested_by = self.requested_by
        current_case = self.current_case
        #
        await interaction.response.defer()
        existing_entry = inprogresscol.find_one({"guild_id": guild.id})
        if existing_entry:
            # ongoing vote
            if "vote_channel_id" in existing_entry:
                vote_channel_id = existing_entry["vote_channel_id"]
                vote_message_id = existing_entry["_id"]
                vote_channel = bot.get_channel(vote_channel_id)
                if not vote_channel:
                    vote_channel = await bot.fetch_channel(vote_channel_id)
                try:
                    vote_message = await vote_channel.fetch_message(vote_message_id)
                except discord.NotFound:
                    return await interaction.followup.send(
                        "This message could not be found. It may have been deleted.", ephemeral=True)
                await interaction.followup.send(
                    f"There already exists an ongoing vote on `{guild.id}`: {vote_message.jump_url}")
            # ongoing report
            else:
                channel_id = existing_entry["channel_id"]
                message_id = existing_entry["_id"]
                thread = await bot.fetch_channel(channel_id)
                try:
                    message = await thread.fetch_message(message_id)
                except discord.NotFound:
                    return await interaction.followup.send(
                        "This message could not be found. It may have been deleted.", ephemeral=True)
                await interaction.followup.send(
                    f"There already exists an ongoing report on `{guild.id}`: {message.jump_url}")
            return
        if requested_by == interaction.user:
            await interaction.edit_original_response(view=None)
            msg = await interaction.followup.send(f"Editing owner for `{guild.id}`...", wait=True)
            r_profile_list = server_profile["r_profile_list"]
            cases = []
            no_of_cases = len(server_profile) - 2
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
            channel_id = msg.channel.id
            message_id = msg.id
            r_profile = format_server_r_profile(guild, r_profile_list, title)
            reason = ""
            reason_embed = discord.Embed(title="Reason", description=reason)
            try:
                inprogresscol.insert_one({"_id": message_id,
                                          "guild_id": guild.id,
                                          "guild_data": {
                                              "id": guild.id,
                                              "name": guild.name,
                                              "icon": guild.icon.url if guild.icon else None,
                                              "banner": guild.banner.url if guild.banner else None,
                                              "created_at": int(
                                                  guild.created_at.timestamp()) if interaction.guild.created_at else None
                                          },
                                          "requested_by": requested_by.id,
                                          "channel_id": channel_id,
                                          "r_profile_list": r_profile_list,
                                          "title": title,
                                          "reason": reason,
                                          })
            except DuplicateKeyError:
                pass
            embeds = [r_profile, reason_embed]
            await msg.edit(embeds=embeds, view=EditOwnerOnlyView())
        elif is_active_staff(interaction.user):
            await interaction.followup.send(
                "This was requested by " + f"{requested_by.mention}, you cannot interact with this component.",
                ephemeral=True)
        else:
            await interaction.followup.send("You do not have permission to use this button.", ephemeral=True)

    @discord.ui.button(label="Add Report", style=discord.ButtonStyle.red, custom_id="editserverreport:addreport", row=1)
    async def add_report_button(self, interaction, button):
        #
        guild = self.guild
        server_profile = self.server_profile
        requested_by = self.requested_by
        #
        await interaction.response.defer()
        existing_entry = inprogresscol.find_one({"guild_id": guild.id})
        if existing_entry:
            # ongoing vote
            if "vote_channel_id" in existing_entry:
                vote_channel_id = existing_entry["vote_channel_id"]
                vote_message_id = existing_entry["_id"]
                vote_channel = bot.get_channel(vote_channel_id)
                if not vote_channel:
                    vote_channel = await bot.fetch_channel(vote_channel_id)
                try:
                    vote_message = await vote_channel.fetch_message(vote_message_id)
                except discord.NotFound:
                    return await interaction.followup.send(
                        "This message could not be found. It may have been deleted.", ephemeral=True)
                await interaction.followup.send(
                    f"There already exists an ongoing vote on `{guild.id}`: {vote_message.jump_url}")
            # ongoing report
            else:
                channel_id = existing_entry["channel_id"]
                message_id = existing_entry["_id"]
                thread = await bot.fetch_channel(channel_id)
                try:
                    message = await thread.fetch_message(message_id)
                except discord.NotFound:
                    return await interaction.followup.send(
                        "This message could not be found. It may have been deleted.", ephemeral=True)
                await interaction.followup.send(
                    f"There already exists an ongoing report on `{guild.id}`: {message.jump_url}")
            return
        if requested_by == interaction.user:
            await interaction.edit_original_response(view=None)
            msg = await interaction.followup.send(f"Adding report on `{guild.id}`...", wait=True)
            r_profile_list = server_profile["r_profile_list"]
            cases = []
            no_of_cases = len(server_profile) - 2
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
            #
            case_title = "TBC"
            add_case_list = {
                                "date_added": f"<t:{round(int(discord.utils.utcnow().timestamp()))}:D> (<t:{round(int(discord.utils.utcnow().timestamp()))}:R>)",
                                "tags": "",
                                "reason": "",
                                "contributor": "",
                                "staff": f"{interaction.user.mention}",
                                "accepted_by": "",
                                "proofs": [],
                            }
            channel_id = msg.channel.id
            message_id = msg.id
            try:
                inprogresscol.insert_one({"_id": message_id,
                                          "guild_id": guild.id,
                                          "guild_data": {
                                              "id": guild.id,
                                              "name": guild.name,
                                              "icon": guild.icon.url if guild.icon else None,
                                              "banner": guild.banner.url if guild.banner else None,
                                              "created_at": int(
                                                  guild.created_at.timestamp()) if interaction.guild.created_at else None
                                          },
                                          "requested_by": requested_by.id,
                                          "channel_id": channel_id,
                                          "r_profile_list": r_profile_list,
                                          "add_case_list": add_case_list,
                                          "title": title,
                                          "case_title": case_title
                                          })
            except DuplicateKeyError:
                pass
            r_profile = format_server_r_profile(guild, r_profile_list, title)
            add_case = format_server_add_case(add_case_list, case_title)
            embeds = [r_profile, add_case]
            await msg.edit(embeds=embeds, view=AddReportOwnerView())
        elif is_active_staff(interaction.user):
            await interaction.followup.send(
                "This was requested by " + f"{requested_by.mention}, you cannot interact with this component.",
                ephemeral=True)
        else:
            await interaction.followup.send("You do not have permission to use this button.", ephemeral=True)

    @discord.ui.button(label="Appeal", style=discord.ButtonStyle.green, custom_id="editserverreport:appeal", row=1)
    async def appeal_button(self, interaction, button):
        #
        guild = self.guild
        server_profile = self.server_profile
        requested_by = self.requested_by
        current_case = self.current_case
        #
        await interaction.response.defer()
        existing_entry = inprogresscol.find_one({"guild_id": guild.id})
        if existing_entry:
            # ongoing vote
            if "vote_channel_id" in existing_entry:
                vote_channel_id = existing_entry["vote_channel_id"]
                vote_message_id = existing_entry["_id"]
                vote_channel = bot.get_channel(vote_channel_id)
                if not vote_channel:
                    vote_channel = await bot.fetch_channel(vote_channel_id)
                try:
                    vote_message = await vote_channel.fetch_message(vote_message_id)
                except discord.NotFound:
                    return await interaction.followup.send(
                        "This message could not be found. It may have been deleted.", ephemeral=True)
                await interaction.followup.send(
                    f"There already exists an ongoing vote on `{guild.id}`: {vote_message.jump_url}")
            # ongoing report
            else:
                channel_id = existing_entry["channel_id"]
                message_id = existing_entry["_id"]
                thread = await bot.fetch_channel(channel_id)
                try:
                    message = await thread.fetch_message(message_id)
                except discord.NotFound:
                    return await interaction.followup.send(
                        "This message could not be found. It may have been deleted.", ephemeral=True)
                await interaction.followup.send(
                    f"There already exists an ongoing report on `{guild.id}`: {message.jump_url}")
            return
        if requested_by == interaction.user:
            await interaction.edit_original_response(view=None)
            msg = await interaction.followup.send(f"Appealing for `{guild.id}`...", wait=True)
            r_profile_list = server_profile["r_profile_list"]
            cases = []
            no_of_cases = len(server_profile) - 2
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
            current_index = current_case - 1
            add_case_list = server_profile[str(current_case)]
            case_tags = cases[current_index]["tags"].split(", ")
            case_title = case_tags[0]
            channel_id = msg.channel.id
            message_id = msg.id
            r_profile = format_server_r_profile(guild, r_profile_list, title)
            reason = ""
            reason_embed = discord.Embed(title="Reason", colour=0x1dcca9, description=reason)
            try:
                inprogresscol.insert_one({"_id": message_id,
                                          "guild_id": guild.id,
                                          "guild_data": {
                                              "id": guild.id,
                                              "name": guild.name,
                                              "icon": guild.icon.url if guild.icon else None,
                                              "banner": guild.banner.url if guild.banner else None,
                                              "created_at": int(
                                                  guild.created_at.timestamp()) if interaction.guild.created_at else None
                                          },
                                          "requested_by": requested_by.id,
                                          "channel_id": channel_id,
                                          "r_profile_list": r_profile_list,
                                          "add_case_list": add_case_list,
                                          "title": title,
                                          "case_title": case_title,
                                          "reason": reason
                                          })
            except DuplicateKeyError:
                pass
            add_case = format_server_add_case(add_case_list, case_title)
            embeds = [r_profile, add_case, reason_embed]
            await msg.edit(embeds=embeds, view=ServerAppealView())
        elif is_active_staff(interaction.user):
            await interaction.followup.send(
                "This was requested by " + f"{requested_by.mention}, you cannot interact with this component.",
                ephemeral=True)
        else:
            await interaction.followup.send("You do not have permission to use this button.", ephemeral=True)


# edit owner only
class EditOwnerOnlyView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Edit Owner", style=discord.ButtonStyle.green, custom_id="editowneronly:editowner")
    async def edit_owner_button(self, interaction, button):
        #
        session = inprogresscol.find_one({"_id": interaction.message.id})
        if session:
            requested_by = session["requested_by"]
            if requested_by == interaction.user.id:
                await interaction.response.send_modal(EditOwnerOnlyModal())

    @discord.ui.button(label="Reason", style=discord.ButtonStyle.primary, custom_id="editowneronly:reason")
    async def reason_button(self, interaction, button):
        #
        session = inprogresscol.find_one({"_id": interaction.message.id})
        if session:
            requested_by = session["requested_by"]
            if requested_by == interaction.user.id:
                await interaction.response.send_modal(OwnerReasonModal())

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.grey, custom_id="editowneronly:cancel")
    async def cancel_button(self, interaction, button):
        await interaction.response.defer()
        #
        session = inprogresscol.find_one({"_id": interaction.message.id})
        if session:
            requested_by = session["requested_by"]
            channel_id = session["channel_id"]
            message_id = interaction.message.id
            #
            thread = await bot.fetch_channel(channel_id)
            message = await thread.fetch_message(message_id)
            if requested_by == interaction.user.id or is_sr(interaction.user):
                inprogresscol.delete_one({"_id": interaction.message.id})
                await message.edit(content=f"**Cancelled by {interaction.user.mention}.**", view=None)

    @discord.ui.button(label="Accept", style=discord.ButtonStyle.grey, custom_id="editowneronly:accept")
    async def accept_button(self, interaction, button):
        await interaction.response.defer()
        #
        session = inprogresscol.find_one({"_id": interaction.message.id})
        if session:
            guild_data = session["guild_data"]
            requested_by = session["requested_by"]
            channel_id = session["channel_id"]
            message_id = interaction.message.id
            r_profile_list = session["r_profile_list"]
            title = session["title"]
            reason = session["reason"]
            guild_id = session["guild_id"]
            #
            thread = await bot.fetch_channel(channel_id)
            message = await thread.fetch_message(message_id)
            if is_sr(interaction.user) and interaction.user.id != requested_by:
                accepted_by = interaction.user
                r_profile = reconstruct_server_r_profile(guild_data, r_profile_list, title)
                #
                vote_channel = bot.get_channel(VOTE_CHANNEL)
                agree_users = []
                disagree_users = []
                new_report_message = await vote_channel.send(content=f"Owner edited for `{guild_id}`")
                new_report_thread = await new_report_message.create_thread(name=f"server-{guild_id}")
                await new_report_thread.send(f"<@&{ticket_ping}>")
                vote_msg = await new_report_thread.send(
                    content=f"Report accepted by {accepted_by.mention}.\nLink to thread: <#{channel_id}>\n\nAgree: 0\nDisagree: 0",
                    embed=r_profile, view=ServerVoteView())
                vote_channel_id = vote_msg.channel.id
                vote_message_id = vote_msg.id
                old_session = inprogresscol.find_one({"guild_id": guild_id})
                if old_session:
                    inprogresscol.delete_one({"_id": old_session["_id"]})
                inprogresscol.insert_one({
                    "_id": vote_message_id,
                    "guild_id": guild_id,
                    "guild_data": guild_data,
                    "requested_by": requested_by,
                    "channel_id": channel_id,
                    "message_id": interaction.message.id,
                    "r_profile_list": r_profile_list,
                    "title": title,
                    "reason": reason,
                    "vote_channel_id": vote_channel_id,
                    "accepted_by": accepted_by.id,
                    "agree_users": agree_users,
                    "disagree_users": disagree_users,
                })
                reason_embed = discord.Embed(title="Reason", description=reason)
                await new_report_thread.send(content=f"Reason for change(s)", embed=reason_embed)
                await old_message_edit_queue.put((message, {"content": "Report has been submitted for voting.", "view": None}))
            else:
                await interaction.followup.send("You do not have permission to accept the report for voting.",
                                                ephemeral=True)
class EditOwnerOnlyModal(discord.ui.Modal, title="Edit Owner"):
    owner = discord.ui.TextInput(label="Edit Owner", placeholder="Input Server Owner ID here.", required=True,
                                 style=discord.TextStyle.short)

    def __init__(self):
        super().__init__(timeout=None)

    async def on_submit(self, interaction):
        await interaction.response.defer()
        #
        session = inprogresscol.find_one({"_id": interaction.message.id})
        if session:
            guild_data = session["guild_data"]
            channel_id = session["channel_id"]
            message_id = interaction.message.id
            r_profile_list = session["r_profile_list"]
            title = session["title"]
            reason = session["reason"]
            #
            thread = await bot.fetch_channel(channel_id)
            message = await thread.fetch_message(message_id)
            try:
                valid_owner = await bot.fetch_user(int(self.owner.value))
            except Exception:
                pass
            else:
                if valid_owner:
                    r_profile_list[0] = f"{valid_owner.mention}"
            #
            inprogresscol.update_one(
                {"_id": interaction.message.id},
                {"$set": {"r_profile_list": r_profile_list}
                })
            #
            r_profile = reconstruct_server_r_profile(guild_data, r_profile_list, title)
            reason_embed = discord.Embed(title="Reason", description=reason)
            embeds = [r_profile, reason_embed]
            await message.edit(embeds=embeds, view=EditOwnerOnlyView())
class OwnerReasonModal(discord.ui.Modal, title="Reason"):
    reason_input = discord.ui.TextInput(label="Reason", placeholder="Please explain the change(s) you have made.",
                                        required=True, style=discord.TextStyle.long)
    def __init__(self):
        super().__init__(timeout=None)
    async def on_submit(self, interaction):
        await interaction.response.defer()
        session = inprogresscol.find_one({"_id": interaction.message.id})
        if session:
            guild_data = session["guild_data"]
            channel_id = session["channel_id"]
            message_id = interaction.message.id
            r_profile_list = session["r_profile_list"]
            title = session["title"]
            #
            thread = await bot.fetch_channel(channel_id)
            message = await thread.fetch_message(message_id)
            reason = str(self.reason_input.value)
            inprogresscol.update_one(
                {"_id": interaction.message.id},
                {"$set": {"reason": reason}}
            )
            r_profile = reconstruct_server_r_profile(guild_data, r_profile_list, title)
            reason_embed = discord.Embed(title="Reason", description=reason)
            embeds = [r_profile, reason_embed]
            await message.edit(embeds=embeds, view=EditOwnerOnlyView())


# server appeal
class ServerAppealView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Edit Owner", style=discord.ButtonStyle.green, custom_id="serverappeal:editowner")
    async def edit_owner_button(self, interaction, button):
        #
        session = inprogresscol.find_one({"_id": interaction.message.id})
        if session:
            requested_by = session["requested_by"]
            #
            if requested_by == interaction.user.id:
                await interaction.response.send_modal(EditOwnerAppealModal())


    @discord.ui.button(label="Reason", style=discord.ButtonStyle.primary, custom_id="serverappeal:reason")
    async def reason_button(self, interaction, button):
        #
        session = inprogresscol.find_one({"_id": interaction.message.id})
        if session:
            requested_by = session["requested_by"]
            #
            if requested_by == interaction.user.id:
                await interaction.response.send_modal(
                    ServerAppealReasonModal())

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.grey, custom_id="serverappeal:cancel")
    async def cancel_button(self, interaction, button):
        await interaction.response.defer()
        #
        session = inprogresscol.find_one({"_id": interaction.message.id})
        if session:
            requested_by = session["requested_by"]
            channel_id = session["channel_id"]
            message_id = interaction.message.id
            #
            thread = await bot.fetch_channel(channel_id)
            message = await thread.fetch_message(message_id)
            if requested_by == interaction.user.id or is_sr(interaction.user):
                inprogresscol.delete_one({"_id": interaction.message.id})
                await message.edit(content=f"**Cancelled by {interaction.user.mention}.**", view=None)

    @discord.ui.button(label="Accept", style=discord.ButtonStyle.grey, custom_id="serverappeal:accept")
    async def accept_button(self, interaction, button):
        await interaction.response.defer()
        #
        session = inprogresscol.find_one({"_id": interaction.message.id})
        if session:
            guild_data = session["guild_data"]
            requested_by = session["requested_by"]
            channel_id = session["channel_id"]
            message_id = interaction.message.id
            r_profile_list = session["r_profile_list"]
            add_case_list = session["add_case_list"]
            title = session["title"]
            case_title = session["case_title"]
            guild_id = session["guild_id"]
            reason = session["reason"]
            #
            thread = await bot.fetch_channel(channel_id)
            message = await thread.fetch_message(message_id)
            if is_sr(interaction.user) and interaction.user.id != requested_by:
                accepted_by = interaction.user
                r_profile = reconstruct_server_r_profile(guild_data, r_profile_list, title)
                add_case = format_server_add_case(add_case_list, case_title)
                reason_embed = discord.Embed(title="Reason", colour=0x1DCCA9, description=reason)
                embeds = [r_profile, add_case, reason_embed]
                #
                vote_channel = bot.get_channel(VOTE_CHANNEL)
                agree_users = []
                disagree_users = []
                image_embeds = image_links_to_embeds(add_case_list["proofs"])
                add_case_list = [add_case_list]
                new_report_message = await vote_channel.send(content=f"Appeal on `{guild_id}`")
                new_report_thread = await new_report_message.create_thread(name=f"server-{guild_id}")
                await new_report_thread.send(f"<@&{ticket_ping}>")
                vote_msg = await new_report_thread.send(
                    content=f"Appeal accepted by <@{accepted_by}>.\nLink to thread: <#{channel_id}>\n\nAgree: 0\nDisagree: 0",
                    embeds=embeds, view=ServerVoteView())
                vote_channel_id = vote_msg.channel.id
                vote_message_id = vote_msg.id
                old_session = inprogresscol.find_one({"guild_id": guild_id})
                if old_session:
                    inprogresscol.delete_one({"_id": old_session["_id"]})
                inprogresscol.insert_one({
                    "_id": vote_message_id,
                    "guild_id": guild_id,
                    "guild_data": guild_data,
                    "requested_by": requested_by,
                    "channel_id": channel_id,
                    "message_id": interaction.message.id,
                    "r_profile_list": r_profile_list,
                    "add_case_list": add_case_list,
                    "title": title,
                    "case_title": case_title,
                    "reason": reason,
                    "vote_channel_id": vote_channel_id,
                    "accepted_by": accepted_by.id,
                    "agree_users": agree_users,
                    "disagree_users": disagree_users,
                })
                await new_report_thread.send(content=f"Proofs for `{guild_id}`", embeds=image_embeds)
                await old_message_edit_queue.put((message, {"content": "Appeal has been submitted for voting.", "view": None}))
            else:
                await interaction.followup.send("You do not have permission to accept the report for voting.",
                                                ephemeral=True)
class EditOwnerAppealModal(discord.ui.Modal, title="Edit Owner"):
    owner = discord.ui.TextInput(label="Edit Owner", placeholder="Input Server Owner ID here.",
                                required=True, style=discord.TextStyle.short)

    def __init__(self):
        super().__init__(timeout=None)

    async def on_submit(self, interaction):
        await interaction.response.defer()
        #
        session = inprogresscol.find_one({"_id": interaction.message.id})
        if session:
            guild_data = session["guild_data"]
            channel_id = session["channel_id"]
            message_id = interaction.message.id
            r_profile_list = session["r_profile_list"]
            add_case_list = session["add_case_list"]
            title = session["title"]
            case_title = session["case_title"]
            reason = session["reason"]
            #
            thread = await bot.fetch_channel(channel_id)
            message = await thread.fetch_message(message_id)
            try:
                valid_owner = await bot.fetch_user(int(self.owner.value))
            except Exception:
                pass
            else:
                if valid_owner:
                    r_profile_list[0] = f"{valid_owner.mention}"
            #
            inprogresscol.update_one(
                {"_id": interaction.message.id},
                {"$set": {
                    "r_profile_list": r_profile_list}
                })
            #
            r_profile = reconstruct_server_r_profile(guild_data, r_profile_list, title)
            reason_embed = discord.Embed(title="Reason", colour=0x1DCCA9, description=reason)
            add_case = format_server_add_case(add_case_list, case_title)
            embeds = [r_profile, add_case, reason_embed]
            await message.edit(embeds=embeds, view=ServerAppealView())
class ServerAppealReasonModal(discord.ui.Modal, title="Reason"):
    reason_input = discord.ui.TextInput(label="Reason", placeholder="Please explain the appeal you have made.",
                                        required=True, style=discord.TextStyle.long)

    def __init__(self):
        super().__init__(timeout=None)
    async def on_submit(self, interaction):
        await interaction.response.defer()
        #
        session = inprogresscol.find_one({"_id": interaction.message.id})
        if session:
            guild_data = session["guild_data"]
            channel_id = session["channel_id"]
            message_id = interaction.message.id
            r_profile_list = session["r_profile_list"]
            add_case_list = session["add_case_list"]
            title = session["title"]
            case_title = session["case_title"]
            #
            thread = await bot.fetch_channel(channel_id)
            message = await thread.fetch_message(message_id)
            reason = str(self.reason_input.value)
            inprogresscol.update_one(
                {"_id": interaction.message.id},
                {"$set": {"reason": reason}}
            )
            r_profile = reconstruct_server_r_profile(guild_data, r_profile_list, title)
            reason_embed = discord.Embed(title="Reason", colour=0x1DCCA9, description=reason)
            add_case = format_server_add_case(add_case_list, case_title)
            embeds = [r_profile, add_case, reason_embed]
            await message.edit(embeds=embeds, view=ServerAppealView())


# server add report
class AddReportOwnerView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(emoji="<:rightarrow:1458096774521553038>", style=discord.ButtonStyle.grey, custom_id="addreportowner:next")
    async def next_button(self, interaction, button):
        await interaction.response.defer()
        #
        session = inprogresscol.find_one({"_id": interaction.message.id})
        if session:
            guild_data = session["guild_data"]
            requested_by = session["requested_by"]
            channel_id = session["channel_id"]
            message_id = interaction.message.id
            r_profile_list = session["r_profile_list"]
            add_case_list = session["add_case_list"]
            title = session["title"]
            case_title = session["case_title"]
            #
            thread = await bot.fetch_channel(channel_id)
            message = await thread.fetch_message(message_id)
            if requested_by == interaction.user.id or is_sr(interaction.user):
                r_profile = reconstruct_server_r_profile(guild_data, r_profile_list, title)
                add_case = format_server_add_case(add_case_list, case_title)
                embeds = [r_profile, add_case]
                await message.edit(embeds=embeds, view=AddReportServerTagsView())

    @discord.ui.button(label="Edit Owner", style=discord.ButtonStyle.green, custom_id="addreportowner:editowner")
    async def edit_owner_button(self, interaction, button):
        #
        session = inprogresscol.find_one({"_id": interaction.message.id})
        if session:
            requested_by = session["requested_by"]
            #
            if requested_by == interaction.user.id:
                await interaction.response.send_modal(EditOwnerModal())

class EditOwnerModal(discord.ui.Modal, title="Edit Owner"):
    owner = discord.ui.TextInput(label="Edit Owner", placeholder="Input Server Owner ID here.",
                                required=True, style=discord.TextStyle.short)

    def __init__(self):
        super().__init__(timeout=None)

    async def on_submit(self, interaction):
        await interaction.response.defer()
        #
        session = inprogresscol.find_one({"_id": interaction.message.id})
        if session:
            guild_data = session["guild_data"]
            channel_id = session["channel_id"]
            message_id = interaction.message.id
            r_profile_list = session["r_profile_list"]
            add_case_list = session["add_case_list"]
            title = session["title"]
            case_title = session["case_title"]
            #
            thread = await bot.fetch_channel(channel_id)
            message = await thread.fetch_message(message_id)
            try:
                valid_owner = await bot.fetch_user(int(self.owner.value))
            except Exception:
                pass
            else:
                if valid_owner:
                    r_profile_list[0] = f"{valid_owner.mention}"
            #
            inprogresscol.update_one(
                {"_id": interaction.message.id},
                {"$set": {
                    "r_profile_list": r_profile_list}
                })
            #
            r_profile = reconstruct_server_r_profile(guild_data, r_profile_list, title)
            add_case = format_server_add_case(add_case_list, case_title)
            embeds = [r_profile, add_case]
            await message.edit(embeds=embeds, view=AddReportOwnerView())

class AddReportServerTagsView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(emoji="<:leftarrow:1458096658062770176>", style=discord.ButtonStyle.grey, custom_id="addreportservertags:prev")
    async def prev_button(self, interaction, button):
        await interaction.response.defer()
        #
        session = inprogresscol.find_one({"_id": interaction.message.id})
        if session:
            guild_data = session["guild_data"]
            requested_by = session["requested_by"]
            channel_id = session["channel_id"]
            message_id = interaction.message.id
            r_profile_list = session["r_profile_list"]
            add_case_list = session["add_case_list"]
            title = session["title"]
            case_title = session["case_title"]
            #
            thread = await bot.fetch_channel(channel_id)
            message = await thread.fetch_message(message_id)
            if requested_by == interaction.user.id or is_sr(interaction.user):
                r_profile = reconstruct_server_r_profile(guild_data, r_profile_list, title)
                add_case = format_server_add_case(add_case_list, case_title)
                embeds = [r_profile, add_case]
                await message.edit(embeds=embeds, view=AddReportOwnerView())

    @discord.ui.button(emoji="<:rightarrow:1458096774521553038>", style=discord.ButtonStyle.grey, custom_id="addreportservertags:next")
    async def next_button(self, interaction, button):
        await interaction.response.defer()
        #
        session = inprogresscol.find_one({"_id": interaction.message.id})
        if session:
            guild_data = session["guild_data"]
            requested_by = session["requested_by"]
            channel_id = session["channel_id"]
            message_id = interaction.message.id
            r_profile_list = session["r_profile_list"]
            add_case_list = session["add_case_list"]
            title = session["title"]
            case_title = session["case_title"]
            #
            thread = await bot.fetch_channel(channel_id)
            message = await thread.fetch_message(message_id)
            if requested_by == interaction.user.id or is_sr(interaction.user):
                r_profile = reconstruct_server_r_profile(guild_data, r_profile_list, title)
                add_case = format_server_add_case(add_case_list, case_title)
                embeds = [r_profile, add_case]
                await message.edit(embeds=embeds, view=AddReportServerReasonView())

    @discord.ui.select(options=server_tags_options, placeholder="Select Tag(s)...", custom_id="addreportservertags:select",
                       max_values=len(server_tags_options))
    async def select_callback(self, interaction, select):
        await interaction.response.defer()
        #
        session = inprogresscol.find_one({"_id": interaction.message.id})
        if session:
            guild_data = session["guild_data"]
            requested_by = session["requested_by"]
            channel_id = session["channel_id"]
            message_id = interaction.message.id
            r_profile_list = session["r_profile_list"]
            add_case_list = session["add_case_list"]
            title = session["title"]
            guild_id = session["guild_id"]
            #
            thread = await bot.fetch_channel(channel_id)
            message = await thread.fetch_message(message_id)
            if requested_by == interaction.user.id:
                sorted_tags = sort_server_tags(self.select_callback.values)
                case_title = sorted_tags[0]
                tags = selected_string(sorted_tags)
                add_case_list["tags"] = tags
                #
                server_query = {"_id": str(guild_id)}
                server_profile = serverscol.find_one(server_query)
                old_r_profile_list = server_profile["r_profile_list"]
                #
                existing_tags_list = old_r_profile_list[1].split(", ")
                existing_tags_list.insert(0, title)
                for tag in sorted_tags:
                    if tag not in existing_tags_list:
                        existing_tags_list.append(tag)
                sorted_tags = sort_server_tags(existing_tags_list)
                #
                title = sorted_tags[0]
                all_other_tags = selected_string(sorted_tags[1:])
                r_profile_list[1] = all_other_tags
                #
                inprogresscol.update_one(
                    {"_id": interaction.message.id},
                    {"$set": {
                        "r_profile_list": r_profile_list,
                        "add_case_list": add_case_list,
                        "title": title,
                        "case_title": case_title}
                    })
                #
                r_profile = reconstruct_server_r_profile(guild_data, r_profile_list, title)
                add_case = format_server_add_case(add_case_list, case_title)
                embeds = [r_profile, add_case]
                await message.edit(embeds=embeds)

class AddReportServerReasonView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(emoji="<:leftarrow:1458096658062770176>", style=discord.ButtonStyle.grey, custom_id="addreportserverreason:prev")
    async def prev_button(self, interaction, button):
        await interaction.response.defer()
        #
        session = inprogresscol.find_one({"_id": interaction.message.id})
        if session:
            guild_data = session["guild_data"]
            requested_by = session["requested_by"]
            channel_id = session["channel_id"]
            message_id = interaction.message.id
            r_profile_list = session["r_profile_list"]
            add_case_list = session["add_case_list"]
            title = session["title"]
            case_title = session["case_title"]
            #
            thread = await bot.fetch_channel(channel_id)
            message = await thread.fetch_message(message_id)
            if requested_by == interaction.user.id or is_sr(interaction.user):
                r_profile = reconstruct_server_r_profile(guild_data, r_profile_list, title)
                add_case = format_server_add_case(add_case_list, case_title)
                embeds = [r_profile, add_case]
                await message.edit(embeds=embeds, view=AddReportServerTagsView())

    @discord.ui.button(emoji="<:rightarrow:1458096774521553038>", style=discord.ButtonStyle.grey, custom_id="addreportserverreason:next")
    async def next_button(self, interaction, button):
        await interaction.response.defer()
        #
        session = inprogresscol.find_one({"_id": interaction.message.id})
        if session:
            guild_data = session["guild_data"]
            requested_by = session["requested_by"]
            channel_id = session["channel_id"]
            message_id = interaction.message.id
            r_profile_list = session["r_profile_list"]
            add_case_list = session["add_case_list"]
            title = session["title"]
            case_title = session["case_title"]
            #
            thread = await bot.fetch_channel(channel_id)
            message = await thread.fetch_message(message_id)
            if requested_by == interaction.user.id or is_sr(interaction.user):
                r_profile = reconstruct_server_r_profile(guild_data, r_profile_list, title)
                add_case = format_server_add_case(add_case_list, case_title)
                embeds = [r_profile, add_case]
                await message.edit(embeds=embeds, view=AddReportServerContributorView())

    @discord.ui.button(label="Reason", style=discord.ButtonStyle.green, custom_id="addreportserverreason:reason")
    async def reason_button(self, interaction, button):
        #
        session = inprogresscol.find_one({"_id": interaction.message.id})
        if session:
            requested_by = session["requested_by"]
            #
            if requested_by == interaction.user.id:
                await interaction.response.send_modal(AddReportServerReasonModal())
class AddReportServerReasonModal(discord.ui.Modal, title="Reason"):
    reason = discord.ui.TextInput(label="Reason", placeholder="Input reason here.", required=True,
                                  style=discord.TextStyle.long)
    def __init__(self):
        super().__init__(timeout=None)

    async def on_submit(self, interaction):
        await interaction.response.defer()
        #
        session = inprogresscol.find_one({"_id": interaction.message.id})
        if session:
            guild_data = session["guild_data"]
            channel_id = session["channel_id"]
            message_id = interaction.message.id
            r_profile_list = session["r_profile_list"]
            add_case_list = session["add_case_list"]
            title = session["title"]
            case_title = session["case_title"]
            #
            thread = await bot.fetch_channel(channel_id)
            message = await thread.fetch_message(message_id)
            reason = re.sub(r"\s+", " ", self.reason.value)
            add_case_list["reason"] = reason
            #
            inprogresscol.update_one(
                {"_id": interaction.message.id},
                {"$set": {
                    "add_case_list": add_case_list}
                })
            #
            r_profile = reconstruct_server_r_profile(guild_data, r_profile_list, title)
            add_case = format_server_add_case(add_case_list, case_title)
            embeds = [r_profile, add_case]
            await message.edit(embeds=embeds, view=AddReportServerReasonView())

class AddReportServerContributorView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(emoji="<:leftarrow:1458096658062770176>", style=discord.ButtonStyle.grey,
                       custom_id="addreportservercontributor:prev")
    async def prev_button(self, interaction, button):
        await interaction.response.defer()
        #
        session = inprogresscol.find_one({"_id": interaction.message.id})
        if session:
            guild_data = session["guild_data"]
            requested_by = session["requested_by"]
            channel_id = session["channel_id"]
            message_id = interaction.message.id
            r_profile_list = session["r_profile_list"]
            add_case_list = session["add_case_list"]
            title = session["title"]
            case_title = session["case_title"]
            #
            thread = await bot.fetch_channel(channel_id)
            message = await thread.fetch_message(message_id)
            if requested_by == interaction.user.id or is_sr(interaction.user):
                r_profile = reconstruct_server_r_profile(guild_data, r_profile_list, title)
                add_case = format_server_add_case(add_case_list, case_title)
                embeds = [r_profile, add_case]
                await message.edit(embeds=embeds, view=AddReportServerReasonView())

    @discord.ui.button(emoji="<:rightarrow:1458096774521553038>", style=discord.ButtonStyle.grey,
                       custom_id="addreportservercontributor:next")
    async def next_button(self, interaction, button):
        await interaction.response.defer()
        #
        session = inprogresscol.find_one({"_id": interaction.message.id})
        if session:
            guild_data = session["guild_data"]
            requested_by = session["requested_by"]
            channel_id = session["channel_id"]
            message_id = interaction.message.id
            r_profile_list = session["r_profile_list"]
            add_case_list = session["add_case_list"]
            title = session["title"]
            case_title = session["case_title"]
            #
            thread = await bot.fetch_channel(channel_id)
            message = await thread.fetch_message(message_id)
            if requested_by == interaction.user.id or is_sr(interaction.user):
                r_profile = reconstruct_server_r_profile(guild_data, r_profile_list, title)
                add_case = format_server_add_case(add_case_list, case_title)
                embeds = [r_profile, add_case]
                await message.edit(embeds=embeds, view=AddReportServerProofsView())

    @discord.ui.button(label="Contributor", style=discord.ButtonStyle.green, custom_id="addreportservercontributor:input")
    async def contributor_button(self, interaction, button):
        #
        session = inprogresscol.find_one({"_id": interaction.message.id})
        if session:
            requested_by = session["requested_by"]
            #
            if requested_by == interaction.user.id:
                await interaction.response.send_modal(AddReportServerContributorModal())
class AddReportServerContributorModal(discord.ui.Modal, title="Contributor"):
    contributor = discord.ui.TextInput(label="Contributor",
                                       placeholder="User ID / n if Anonymous.", required=True,
                                       style=discord.TextStyle.short)
    def __init__(self):
        super().__init__(timeout=None)
    async def on_submit(self, interaction):
        await interaction.response.defer()
        #
        session = inprogresscol.find_one({"_id": interaction.message.id})
        if session:
            guild_data = session["guild_data"]
            channel_id = session["channel_id"]
            message_id = interaction.message.id
            r_profile_list = session["r_profile_list"]
            add_case_list = session["add_case_list"]
            title = session["title"]
            case_title = session["case_title"]
            #
            thread = await bot.fetch_channel(channel_id)
            message = await thread.fetch_message(message_id)
            contributor_input = self.contributor.value
            if contributor_input.lower() == "n":
                add_case_list["contributor"] = "Anonymous"
            else:
                try:
                    contributor_id = await bot.fetch_user(int(contributor_input))
                except Exception:
                    add_case_list["contributor"] = ""
                else:
                    add_case_list["contributor"] = f"<@{contributor_id.id}>"
            #
            inprogresscol.update_one(
                {"_id": interaction.message.id},
                {"$set": {"add_case_list": add_case_list}},
            )
            #
            r_profile = reconstruct_server_r_profile(guild_data, r_profile_list, title)
            add_case = format_server_add_case(add_case_list, case_title)
            embeds = [r_profile, add_case]
            await message.edit(embeds=embeds, view=AddReportServerContributorView())

class AddReportServerProofsView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(emoji="<:leftarrow:1458096658062770176>", style=discord.ButtonStyle.grey, custom_id="addreportserverproofs:prev")
    async def prev_button(self, interaction, button):
        await interaction.response.defer()
        #
        session = inprogresscol.find_one({"_id": interaction.message.id})
        if session:
            guild_data = session["guild_data"]
            requested_by = session["requested_by"]
            channel_id = session["channel_id"]
            message_id = interaction.message.id
            r_profile_list = session["r_profile_list"]
            add_case_list = session["add_case_list"]
            title = session["title"]
            case_title = session["case_title"]
            #
            thread = await bot.fetch_channel(channel_id)
            message = await thread.fetch_message(message_id)
            if requested_by == interaction.user.id or is_sr(interaction.user):
                r_profile = reconstruct_server_r_profile(guild_data, r_profile_list, title)
                add_case = format_server_add_case(add_case_list, case_title)
                embeds = [r_profile, add_case]
                await message.edit(embeds=embeds, view=ServerContributorView())

    @discord.ui.button(label="Add Proofs", style=discord.ButtonStyle.green, custom_id="addreportserverproofs:input")
    async def proofs_button(self, interaction, button):
        #
        session = inprogresscol.find_one({"_id": interaction.message.id})
        if session:
            requested_by = session["requested_by"]
            add_case_list = session["add_case_list"]
            #
            if requested_by == interaction.user.id:
                image_links = []
                add_case_list["proofs"] = []
                await interaction.response.send_message(
                    "Please send the images you would like to upload (max 10). **All images previously uploaded in this session have been removed.**",
                    ephemeral=True)
                def check(m):
                    return m.author == interaction.user and m.channel == interaction.channel
                try:
                    msg = await bot.wait_for('message', check=check, timeout=120.0)
                except asyncio.TimeoutError:
                    await interaction.followup.send("You took too long to upload an image.", ephemeral=True)
                    return
                if msg.attachments:
                    for attachment in msg.attachments:
                        if attachment.content_type and attachment.content_type.startswith('image/'):
                            try:
                                async with aiohttp.ClientSession() as http_session:
                                    async with http_session.get(attachment.url) as resp:
                                        data = io.BytesIO(await resp.read())
                                        file = discord.File(data, filename=attachment.filename)
                                        channel_to_send = bot.get_channel(PROOFS_CHANNEL)
                                        sent_message = await channel_to_send.send(file=file)
                                        if sent_message.attachments:
                                            new_image_url = sent_message.attachments[0].url
                                            image_links.append(new_image_url)
                                            add_case_list["proofs"].append(new_image_url)
                            except Exception:
                                await msg.channel.send(f"An error occurred with file {attachment.filename}")
                #
                inprogresscol.update_one(
                    {"_id": interaction.message.id},
                    {"$set": {"add_case_list": add_case_list}},
                )
                #
                image_embeds = image_links_to_embeds(image_links)
                await interaction.followup.send(f"Images received from {interaction.user.mention}.",
                                                embeds=image_embeds)

    @discord.ui.button(label="Show Proofs", style=discord.ButtonStyle.grey, custom_id="addreportserverproofs:showproofs")
    async def show_proofs_button(self, interaction, button):
        await interaction.response.defer()
        #
        session = inprogresscol.find_one({"_id": interaction.message.id})
        if session:
            requested_by = session["requested_by"]
            add_case_list = session["add_case_list"]
            guild_id = session["guild_id"]
            #
            if requested_by == interaction.user.id or is_sr(interaction.user):
                image_embeds = image_links_to_embeds(add_case_list["proofs"])
                await interaction.followup.send(f"Proofs for `{guild_id}`",
                                                embeds=image_embeds, ephemeral=True)

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.grey, custom_id="addreportserverproofs:cancel")
    async def cancel_button(self, interaction, button):
        await interaction.response.defer()
        #
        session = inprogresscol.find_one({"_id": interaction.message.id})
        if session:
            requested_by = session["requested_by"]
            channel_id = session["channel_id"]
            message_id = interaction.message.id
            #
            thread = await bot.fetch_channel(channel_id)
            message = await thread.fetch_message(message_id)
            if requested_by == interaction.user.id or is_sr(interaction.user):
                inprogresscol.delete_one({"_id": interaction.message.id})
                await message.edit(content=f"**Cancelled by {interaction.user.mention}.**", view=None)

    @discord.ui.button(label="Accept", style=discord.ButtonStyle.grey, custom_id="addreportserverproofs:accept")
    async def accept_button(self, interaction, button):
        await interaction.response.defer()
        #
        session = inprogresscol.find_one({"_id": interaction.message.id})
        if session:
            guild_data = session["guild_data"]
            requested_by = session["requested_by"]
            channel_id = session["channel_id"]
            message_id = interaction.message.id
            r_profile_list = session["r_profile_list"]
            add_case_list = session["add_case_list"]
            title = session["title"]
            case_title = session["case_title"]
            guild_id = session["guild_id"]
            #
            thread = await bot.fetch_channel(channel_id)
            message = await thread.fetch_message(message_id)
            if is_sr(interaction.user) and interaction.user.id != requested_by:
                accepted_by = interaction.user
                add_case_list["accepted_by"] = f"<@{interaction.user.id}>"
                #
                inprogresscol.update_one(
                    {"_id": interaction.message.id},
                    {"$set": {"add_case_list": add_case_list}},
                )
                #
                r_profile = reconstruct_server_r_profile(guild_data, r_profile_list, title)
                add_case = format_server_add_case(add_case_list, case_title)
                embeds = [r_profile, add_case]
                #
                vote_channel = bot.get_channel(VOTE_CHANNEL)
                agree_users = []
                disagree_users = []
                all_images_to_show = add_case_list["proofs"]
                image_embeds = image_links_to_embeds(all_images_to_show)
                new_report_message = await vote_channel.send(content=f"Added report on `{guild_id}`")
                new_report_thread = await new_report_message.create_thread(name=f"server-{guild_id}")
                await new_report_thread.send(f"<@&{ticket_ping}>")
                vote_msg = await new_report_thread.send(
                    content=f"Report accepted by {accepted_by.mention}.\nLink to thread: <#{channel_id}>\n\nAgree: 0\nDisagree: 0",
                    embeds=embeds, view=ServerVoteView())
                vote_channel_id = vote_msg.channel.id
                vote_message_id = vote_msg.id
                old_session = inprogresscol.find_one({"guild_id": guild_id})
                if old_session:
                    inprogresscol.delete_one({"_id": old_session["_id"]})
                inprogresscol.insert_one({
                    "_id": vote_message_id,
                    "guild_id": guild_id,
                    "guild_data": guild_data,
                    "requested_by": requested_by,
                    "channel_id": channel_id,
                    "message_id": interaction.message.id,
                    "r_profile_list": r_profile_list,
                    "add_case_list": add_case_list,
                    "title": title,
                    "case_title": case_title,
                    "vote_channel_id": vote_channel_id,
                    "accepted_by": accepted_by.id,
                    "agree_users": agree_users,
                    "disagree_users": disagree_users,
                })
                await new_report_thread.send(content=f"Proofs for `{guild_id}`", embeds=image_embeds)
                await old_message_edit_queue.put((message, {"content": "Report has been submitted for voting.", "view": None}))
            else:
                await interaction.followup.send("You do not have permission to accept the report for voting.",
                                                ephemeral=True)


# server voting
class ServerVoteView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Agree", style=discord.ButtonStyle.green, custom_id="servervote:agree")
    async def agree_button(self, interaction, button):
        await interaction.response.defer()
        #
        session = inprogresscol.find_one({"_id": interaction.message.id})
        if session:
            guild_data = session["guild_data"]
            requested_by = session["requested_by"]
            channel_id = session["channel_id"]
            message_id = session["message_id"]
            r_profile_list = session["r_profile_list"]
            add_case_list = session.get("add_case_list")
            title = session["title"]
            case_title = session.get("case_title")
            accepted_by = session["accepted_by"]
            reason = session.get("reason")
            guild_id = session["guild_id"]
            agree_users, disagree_users = await handle_vote(interaction, session, "agree")
            #
            r_profile = reconstruct_server_r_profile(guild_data, r_profile_list, title)
            #
            if len(agree_users) >= 8 and len(agree_users) > len(disagree_users):
                server_query = {"_id": str(guild_id)}
                server_profile = serverscol.find_one(server_query)
                if server_profile:  # if editing existing reported user
                    cases = []
                    no_of_cases = len(server_profile) - 2
                    for i in range(1, no_of_cases + 1):
                        cases.append(server_profile[str(i)])
                    query_filter = {"_id": str(guild_id)}
                    update_operation = {'$set': {"r_profile_list": r_profile_list}}
                    serverscol.update_one(query_filter, update_operation)
                    if not add_case_list:  # only owner edited
                        r_profile = reconstruct_server_r_profile(guild_data, r_profile_list, title)
                        server_reports_channel = bot.get_channel(SERVER_REPORTS_CHANNEL)
                        await server_reports_channel.send(
                            content=f"<@&{updated_server_report_ping}>\nServer Owner edited for `{guild_id}`",
                            embed=r_profile)
                        reason_embed = discord.Embed(title="Reason", description=reason)
                        await server_reports_channel.send(content=f"Reason for change(s)", embed=reason_embed)
                        embeds = [r_profile, reason_embed]
                        await old_message_edit_queue.put((interaction.message, {"content": f"**Report has been published.** Report accepted by <@{accepted_by}>.\nLink to thread: <#{channel_id}>\n\nAgree: {len(agree_users)}\nDisagree: {len(disagree_users)}",
                                                                                "view": None,
                                                                                "embeds": embeds}))
                        thread = await bot.fetch_channel(channel_id)
                        message = await thread.fetch_message(message_id)
                        await old_message_edit_queue.put(
                            (message, {"content": f"**Report has been published.** Report accepted by <@{accepted_by}>.", "view": None}))
                        await bot.get_channel(channel_id).send(
                            f"Report on `{guild_id}` has been published. <@{requested_by}> <@{accepted_by}>")
                        inprogresscol.delete_one({"_id": interaction.message.id})

                    elif len(add_case_list) == 1:  # [[add_case_list]] case to appeal
                        add_case_list = add_case_list[0]
                        appeal_case_number = next((k for k, v in server_profile.items() if v == add_case_list), None)
                        query_filter = {"_id": str(guild_id)}
                        update_operation = {"$unset": {appeal_case_number: ""}}
                        serverscol.update_one(query_filter, update_operation)
                        #
                        server_query = {"_id": str(guild_id)}
                        server_profile = serverscol.find_one(server_query)

                        if len(server_profile) == 2:
                            serverscol.delete_one(server_query)
                        else:
                            no_of_cases = len(server_profile) - 2
                            for i in range(int(appeal_case_number), no_of_cases + 1):
                                server_profile[appeal_case_number] = server_profile.pop(str(int(appeal_case_number) + 1))
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
                            all_tags_list = list(dict.fromkeys(all_tags_list))
                            title = all_tags_list[0]
                            all_other_tags = selected_string(all_tags_list[1:])
                            r_profile_list = server_profile["r_profile_list"]
                            r_profile_list[1] = all_other_tags
                            server_profile["r_profile_list"] = r_profile_list
                            query_filter = {"_id": str(guild_id)}
                            serverscol.replace_one(query_filter, server_profile)
                        #
                        r_profile = reconstruct_server_r_profile(guild_data, r_profile_list, title)
                        add_case = format_server_add_case(add_case_list, case_title)
                        reason_embed = discord.Embed(title="Reason", colour=0x1DCCA9, description=reason)
                        embeds = [r_profile, add_case]
                        #
                        server_reports_channel = bot.get_channel(SERVER_REPORTS_CHANNEL)
                        await server_reports_channel.send(content=f"<@&{appealed_server_report_ping}>\nAppeal on `{guild_id}`",
                                                          embeds=embeds)
                        await server_reports_channel.send(content=f"Reason for appeal", embed=reason_embed)
                        await old_message_edit_queue.put((interaction.message, {"content": f"**Appeal has been published.** Appeal accepted by <@{accepted_by}>.\nLink to thread: <#{channel_id}>\n\nAgree: {len(agree_users)}\nDisagree: {len(disagree_users)}",
                                                                                "view": None,
                                                                                "embeds": embeds}))
                        thread = await bot.fetch_channel(channel_id)
                        message = await thread.fetch_message(message_id)
                        await old_message_edit_queue.put(
                            (message,
                             {"content": f"**Appeal has been published.** Appeal accepted by <@{accepted_by}>.",
                              "view": None}))
                        await bot.get_channel(channel_id).send(
                            f"Appeal on `{guild_id}` has been published. <@{requested_by}> <@{accepted_by}>")
                        inprogresscol.delete_one({"_id": interaction.message.id})

                    else:  # new case exists
                        r_profile = reconstruct_server_r_profile(guild_data, r_profile_list, title)
                        add_case = format_server_add_case(add_case_list, case_title)
                        embeds = [r_profile, add_case]

                        query_filter = {"_id": str(guild_id)}
                        update_operation = {'$set': {"r_profile_list": r_profile_list}}
                        serverscol.update_one(query_filter, update_operation)
                        update_operation = {'$set': {str(no_of_cases + 1): add_case_list}}
                        serverscol.update_one(query_filter, update_operation)

                        server_reports_channel = bot.get_channel(SERVER_REPORTS_CHANNEL)
                        await server_reports_channel.send(content=f"<@&{updated_server_report_ping}>\nAdded report on `{guild_id}`",
                                                          embeds=embeds)
                        await old_message_edit_queue.put((interaction.message, {"content": f"**Report has been published.** Report accepted by <@{accepted_by}>.\nLink to thread: <#{channel_id}>\n\nAgree: {len(agree_users)}\nDisagree: {len(disagree_users)}",
                                                                                "view": None,
                                                                                "embeds": embeds}))
                        thread = await bot.fetch_channel(channel_id)
                        message = await thread.fetch_message(message_id)
                        await old_message_edit_queue.put(
                            (message,
                             {"content": f"**Report has been published.** Report accepted by <@{accepted_by}>.",
                              "view": None}))
                        await bot.get_channel(channel_id).send(
                            f"Report on `{guild_id}` has been published. <@{requested_by}> <@{accepted_by}>")
                        inprogresscol.delete_one({"_id": interaction.message.id})

                else:  # if new reported server
                    r_profile = reconstruct_server_r_profile(guild_data, r_profile_list, title)
                    add_case = format_server_add_case(add_case_list, case_title)
                    embeds = [r_profile, add_case]

                    new_server = {"_id": str(guild_id), "r_profile_list": r_profile_list,
                                  "1": add_case_list}
                    serverscol.insert_one(new_server)

                    server_reports_channel = bot.get_channel(SERVER_REPORTS_CHANNEL)
                    await server_reports_channel.send(content=f"<@&{new_server_report_ping}>\nNew report on `{guild_id}`",
                                                      embeds=embeds)
                    await old_message_edit_queue.put((interaction.message, {"content": f"**Report has been published.** Report accepted by <@{accepted_by}>.\nLink to thread: <#{channel_id}>\n\nAgree: {len(agree_users)}\nDisagree: {len(disagree_users)}",
                                                                            "view": None,
                                                                            "embeds": embeds}))
                    thread = await bot.fetch_channel(channel_id)
                    message = await thread.fetch_message(message_id)
                    await old_message_edit_queue.put(
                        (message, {"content": f"**Report has been published.** Report accepted by <@{accepted_by}>.",
                                   "view": None}))
                    await bot.get_channel(channel_id).send(
                        f"Report on `{guild_id}` has been published. <@{requested_by}> <@{accepted_by}>")
                    inprogresscol.delete_one({"_id": interaction.message.id})
                try:
                    voters = agree_users + disagree_users
                    for voter in voters:
                        voter_query = {"_id": str(voter)}
                        voter_profile = trusteduserscol.find_one(voter_query)
                        if voter_profile:
                            trusteduserscol.update_one(
                                voter_query,
                                {"$inc": {"votes": 1}}
                            )

                    staff_query = {"_id": str(requested_by)}
                    if trusteduserscol.find_one(staff_query):
                        trusteduserscol.update_one(
                            staff_query,
                            {"$inc": {"reports": 1}}
                        )
                    if staffweeklycol.find_one(staff_query):
                        staffweeklycol.update_one(
                            staff_query,
                            {"$inc": {"weekly_reports": 1}}
                        )
                    sr_query = {"_id": str(accepted_by)}
                    if trusteduserscol.find_one(sr_query):
                        trusteduserscol.update_one(
                            {"_id": str(accepted_by)},
                            {"$inc": {"reviews": 1}}
                        )
                    if staffweeklycol.find_one(sr_query):
                        staffweeklycol.update_one(
                            {"_id": str(accepted_by)},
                            {"$inc": {"weekly_reviews": 1}}
                        )
                except Exception as e:
                    print(f"{e}")
                current_name = interaction.channel.name
                new_name = current_name if current_name.startswith("p-") else f"p-{current_name}"
                await asyncio.sleep(2)
                await interaction.channel.edit(name=new_name, archived=True, locked=True)
                return
            #
            if add_case_list == []:  # only owner edited
                await old_message_edit_queue.put((interaction.message, {"content": f"Report accepted by <@{accepted_by}>.\nLink to thread: <#{channel_id}>\n\nAgree: {len(agree_users)}\nDisagree: {len(disagree_users)}",
                    "embeds": [r_profile], "view": ServerVoteView()}))
            elif len(add_case_list) == 1:  # [[add_case_list]] case to appeal
                add_case_list = add_case_list[0]
                add_case = format_server_add_case(add_case_list, case_title)
                reason_embed = discord.Embed(title="Reason", colour=0x1DCCA9, description=reason)
                embeds = [r_profile, add_case, reason_embed]
                add_case_list = [add_case_list]
                await old_message_edit_queue.put((interaction.message, {"content": f"Appeal accepted by <@{accepted_by}>.\nLink to thread: <#{channel_id}>\n\nAgree: {len(agree_users)}\nDisagree: {len(disagree_users)}",
                    "embeds": embeds, "view": ServerVoteView()}))
            else:  # new case exists
                add_case = format_server_add_case(add_case_list, case_title)
                embeds = [r_profile, add_case]
                await old_message_edit_queue.put((interaction.message, {"content": f"Report accepted by <@{accepted_by}>.\nLink to thread: <#{channel_id}>\n\nAgree: {len(agree_users)}\nDisagree: {len(disagree_users)}",
                    "embeds": embeds, "view": ServerVoteView()}))

    @discord.ui.button(label="Disagree", style=discord.ButtonStyle.red, custom_id="servervote:disagree")
    async def disagree_button(self, interaction, button):
        await interaction.response.defer()
        session = inprogresscol.find_one({"_id": interaction.message.id})
        if session:
            guild_data = session["guild_data"]
            requested_by = session["requested_by"]
            channel_id = session["channel_id"]
            message_id = session["message_id"]
            r_profile_list = session["r_profile_list"]
            add_case_list = session.get("add_case_list")
            title = session["title"]
            case_title = session.get("case_title")
            accepted_by = session["accepted_by"]
            reason = session.get("reason")
            guild_id = session["guild_id"]
            agree_users, disagree_users = await handle_vote(interaction, session, "disagree")
            #
            r_profile = reconstruct_server_r_profile(guild_data, r_profile_list, title)
            #
            if len(disagree_users) >= 12:
                server_query = {"_id": str(guild_id)}
                server_profile = serverscol.find_one(server_query)
                if server_profile:  # if editing existing reported user
                    cases = []
                    no_of_cases = len(server_profile) - 2
                    for i in range(1, no_of_cases + 1):
                        cases.append(server_profile[str(i)])
                    if not add_case_list:  # only owner edited
                        r_profile = reconstruct_server_r_profile(guild_data, r_profile_list, title)
                        reason_embed = discord.Embed(title="Reason", description=reason)
                        embeds = [r_profile, reason_embed]
                        await old_message_edit_queue.put((interaction.message, {"content": f"**Report has been rejected.** Report accepted by <@{accepted_by}>.\nLink to thread: <#{channel_id}>\n\nAgree: {len(agree_users)}\nDisagree: {len(disagree_users)}",
                            "view": None, "embeds": embeds}))
                        thread = await bot.fetch_channel(channel_id)
                        message = await thread.fetch_message(message_id)
                        await old_message_edit_queue.put(
                            (message, {"content": f"**Report has been rejected.** Report accepted by <@{accepted_by}>.",
                              "view": None}))
                        await bot.get_channel(channel_id).send(
                            f"Report on server `{guild_id}` has been rejected. <@{requested_by}> <@{accepted_by}>")
                        inprogresscol.delete_one({"_id": interaction.message.id})
                    elif len(add_case_list) == 1:  # [[add_case_list]] case to appeal
                        add_case_list = add_case_list[0]
                        r_profile = reconstruct_server_r_profile(guild_data, r_profile_list, title)
                        add_case = format_server_add_case(add_case_list, case_title)
                        reason_embed = discord.Embed(title="Reason", colour=0x1DCCA9, description=reason)
                        embeds = [r_profile, add_case]
                        #
                        await old_message_edit_queue.put((interaction.message, {"content": f"**Appeal has been rejected.** Appeal accepted by <@{accepted_by}>.\nLink to thread: <#{channel_id}>\n\nAgree: {len(agree_users)}\nDisagree: {len(disagree_users)}",
                            "view": None, "embeds": embeds}))
                        thread = await bot.fetch_channel(channel_id)
                        message = await thread.fetch_message(message_id)
                        await old_message_edit_queue.put(
                            (message,
                             {"content": f"**Appeal has been rejected.** Appeal accepted by <@{accepted_by}>.",
                              "view": None}))
                        await bot.get_channel(channel_id).send(
                            f"Appeal on server `{guild_id}` has been rejected. <@{requested_by}> <@{accepted_by}>")
                        inprogresscol.delete_one({"_id": interaction.message.id})
                    else:  # new case exists
                        #
                        r_profile = reconstruct_server_r_profile(guild_data, r_profile_list, title)
                        add_case = format_server_add_case(add_case_list, case_title)
                        embeds = [r_profile, add_case]

                        await old_message_edit_queue.put((interaction.message, {"content": f"**Report has been rejected.** Report accepted by <@{accepted_by}>.\nLink to thread: <#{channel_id}>\n\nAgree: {len(agree_users)}\nDisagree: {len(disagree_users)}",
                            "view": None, "embeds": embeds}))
                        thread = await bot.fetch_channel(channel_id)
                        message = await thread.fetch_message(message_id)
                        await old_message_edit_queue.put(
                            (message,
                             {"content": f"**Report has been rejected.** Report accepted by <@{accepted_by}>.",
                              "view": None}))
                        await bot.get_channel(channel_id).send(
                            f"Report on server `{guild_id}` has been rejected. <@{requested_by}> <@{accepted_by}>")
                        inprogresscol.delete_one({"_id": interaction.message.id})
                else:  # if new reported server
                    #
                    r_profile = reconstruct_server_r_profile(guild_data, r_profile_list, title)
                    add_case = format_server_add_case(add_case_list, case_title)
                    embeds = [r_profile, add_case]
                    await old_message_edit_queue.put((interaction.message, {"content": f"**Report has been rejected.** Report accepted by <@{accepted_by}>.\nLink to thread: <#{channel_id}>\n\nAgree: {len(agree_users)}\nDisagree: {len(disagree_users)}",
                        "view": None, "embeds": embeds}))
                    thread = await bot.fetch_channel(channel_id)
                    message = await thread.fetch_message(message_id)
                    await old_message_edit_queue.put(
                        (message, {"content": f"**Report has been rejected.** Report accepted by <@{accepted_by}>.",
                          "view": None}))
                    await bot.get_channel(channel_id).send(
                        f"Report on server `{guild_id}` has been rejected. <@{requested_by}> <@{accepted_by}>")
                    inprogresscol.delete_one({"_id": interaction.message.id})
                try:
                    voters = agree_users + disagree_users
                    for voter in voters:
                        voter_query = {"_id": str(voter)}
                        voter_profile = trusteduserscol.find_one(voter_query)
                        if voter_profile:
                            trusteduserscol.update_one(
                                voter_query,
                                {"$inc": {"votes": 1}}
                            )
                except Exception as e:
                    print(f"{e}")
                current_name = interaction.channel.name
                new_name = current_name if current_name.startswith("r-") else f"r-{current_name}"
                await asyncio.sleep(2)
                await interaction.channel.edit(name=new_name, archived=True, locked=True)
                return
            #
            if not add_case_list:  # only owner edited
                await old_message_edit_queue.put((interaction.message, {"content": f"Report accepted by <@{accepted_by}>.\nLink to thread: <#{channel_id}>\n\nAgree: {len(agree_users)}\nDisagree: {len(disagree_users)}",
                    "embeds": [r_profile], "view": ServerVoteView()}))

            elif len(add_case_list) == 1:  # [[add_case_list]] case to appeal
                add_case_list = add_case_list[0]
                add_case = format_server_add_case(add_case_list, case_title)
                reason_embed = discord.Embed(title="Reason", colour=0x1DCCA9, description=reason)
                embeds = [r_profile, add_case, reason_embed]
                add_case_list = [add_case_list]
                await old_message_edit_queue.put((interaction.message, {"content": f"Appeal accepted by <@{accepted_by}>.\nLink to thread: <#{channel_id}>\n\nAgree: {len(agree_users)}\nDisagree: {len(disagree_users)}",
                    "embeds": embeds, "view": ServerVoteView()}))

            else:  # new case exists
                add_case = format_server_add_case(add_case_list, case_title)
                embeds = [r_profile, add_case]
                await old_message_edit_queue.put((interaction.message, {"content": f"Report accepted by <@{accepted_by}>.\nLink to thread: <#{channel_id}>\n\nAgree: {len(agree_users)}\nDisagree: {len(disagree_users)}",
                    "embeds": embeds, "view": ServerVoteView()}))

    @discord.ui.button(label="Remove Vote", style=discord.ButtonStyle.primary, custom_id="servervote:removevote")
    async def remove_vote_button(self, interaction, button):
        await interaction.response.defer()
        #
        session = inprogresscol.find_one({"_id": interaction.message.id})
        if session:
            guild_data = session["guild_data"]
            channel_id = session["channel_id"]
            r_profile_list = session["r_profile_list"]
            add_case_list = session.get("add_case_list")
            title = session["title"]
            case_title = session.get("case_title")
            accepted_by = session["accepted_by"]
            reason = session.get("reason")
            agree_users, disagree_users = await handle_vote(interaction, session, "remove")
            #
            r_profile = reconstruct_server_r_profile(guild_data, r_profile_list, title)
            if not add_case_list:
                reason_embed = discord.Embed(title="Reason", description=reason)
                embeds = [r_profile, reason_embed]
                await old_message_edit_queue.put((interaction.message, {"content": f"Report accepted by <@{accepted_by}>.\nLink to thread: <#{channel_id}>\n\nAgree: {len(agree_users)}\nDisagree: {len(disagree_users)}",
                    "embeds": embeds, "view": ServerVoteView()}))

            elif len(add_case_list) == 1:  # [[add_case_list]] case to appeal
                add_case_list = add_case_list[0]
                add_case = format_server_add_case(add_case_list, case_title)
                reason_embed = discord.Embed(title="Reason", colour=0x1DCCA9, description=reason)
                embeds = [r_profile, add_case, reason_embed]
                add_case_list = [add_case_list]
                await old_message_edit_queue.put((interaction.message, {"content": f"Appeal accepted by <@{accepted_by}>.\nLink to thread: <#{channel_id}>\n\nAgree: {len(agree_users)}\nDisagree: {len(disagree_users)}",
                    "embeds": embeds, "view": ServerVoteView()}))

            else:
                add_case = format_server_add_case(add_case_list, case_title)
                embeds = [r_profile, add_case]
                await old_message_edit_queue.put((interaction.message, {"content": f"Report accepted by <@{accepted_by}>.\nLink to thread: <#{channel_id}>\n\nAgree: {len(agree_users)}\nDisagree: {len(disagree_users)}",
                    "embeds": embeds, "view": ServerVoteView()}))

    @discord.ui.button(label="Publish", style=discord.ButtonStyle.grey, custom_id="servervote:publish")
    async def publish_button(self, interaction, button):
        await interaction.response.defer()
        #
        session = inprogresscol.find_one({"_id": interaction.message.id})
        if session:
            guild_data = session["guild_data"]
            requested_by = session["requested_by"]
            channel_id = session["channel_id"]
            message_id = session["message_id"]
            r_profile_list = session["r_profile_list"]
            add_case_list = session.get("add_case_list")
            title = session["title"]
            case_title = session.get("case_title")
            agree_users = session["agree_users"]
            disagree_users = session["disagree_users"]
            reason = session.get("reason")
            guild_id = session["guild_id"]
            #
            o5_check = get(interaction.user.guild.roles, id=o5_role) in interaction.user.roles and len(
                agree_users) >= 5 and len(agree_users) > len(disagree_users)
            sr_check = is_sr(interaction.user) and interaction.user.id != requested_by and len(
                agree_users) >= 5 and len(agree_users) > len(disagree_users)
            if o5_check or sr_check:
                accepted_by = interaction.user.id
                server_query = {"_id": str(guild_id)}
                server_profile = serverscol.find_one(server_query)
                if server_profile:  # if editing existing reported user
                    cases = []
                    no_of_cases = len(server_profile) - 2
                    for i in range(1, no_of_cases + 1):
                        cases.append(server_profile[str(i)])
                    query_filter = {"_id": str(guild_id)}
                    update_operation = {'$set': {"r_profile_list": r_profile_list}}
                    serverscol.update_one(query_filter, update_operation)
                    if not add_case_list:  # only owner edited
                        r_profile = reconstruct_server_r_profile(guild_data, r_profile_list, title)
                        server_reports_channel = bot.get_channel(SERVER_REPORTS_CHANNEL)
                        await server_reports_channel.send(content=f"<@&{updated_server_report_ping}>\nServer Owner edited for `{guild_id}`",
                                                        embed=r_profile)
                        reason_embed = discord.Embed(title="Reason", description=reason)
                        await server_reports_channel.send(content=f"Reason for change(s)", embed=reason_embed)
                        embeds = [r_profile, reason_embed]
                        await old_message_edit_queue.put((interaction.message, {"content": f"**Report has been published.** Report accepted by <@{accepted_by}>.\nLink to thread: <#{channel_id}>\n\nAgree: {len(agree_users)}\nDisagree: {len(disagree_users)}",
                            "view": None, "embeds": embeds}))
                        thread = await bot.fetch_channel(channel_id)
                        message = await thread.fetch_message(message_id)
                        await old_message_edit_queue.put(
                            (message, {"content": f"**Report has been published.** Report accepted by <@{accepted_by}>.",
                              "view": None}))
                        await bot.get_channel(channel_id).send(
                            f"Report on `{guild_id}` has been published. <@{requested_by}> <@{accepted_by}>")
                        inprogresscol.delete_one({"_id": interaction.message.id})
                    elif len(add_case_list) == 1:  # [[add_case_list]] case to appeal
                        add_case_list = add_case_list[0]
                        appeal_case_number = next((k for k, v in server_profile.items() if v == add_case_list), None)
                        query_filter = {"_id": str(guild_id)}
                        update_operation = {"$unset": {appeal_case_number: ""}}
                        serverscol.update_one(query_filter, update_operation)
                        #
                        server_query = {"_id": str(guild_id)}
                        server_profile = serverscol.find_one(server_query)
                        if len(server_profile) == 2:
                            serverscol.delete_one(server_query)
                        else:
                            no_of_cases = len(server_profile) - 2
                            for i in range(int(appeal_case_number), no_of_cases + 1):
                                server_profile[appeal_case_number] = server_profile.pop(str(int(appeal_case_number) + 1))
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
                            all_tags_list = list(dict.fromkeys(all_tags_list))
                            title = all_tags_list[0]
                            all_other_tags = selected_string(all_tags_list[1:])
                            r_profile_list = server_profile["r_profile_list"]
                            r_profile_list[1] = all_other_tags
                            server_profile["r_profile_list"] = r_profile_list
                            query_filter = {"_id": str(guild_id)}
                            serverscol.replace_one(query_filter, server_profile)
                        #
                        r_profile = reconstruct_server_r_profile(guild_data, r_profile_list, title)
                        add_case = format_server_add_case(add_case_list, case_title)
                        reason_embed = discord.Embed(title="Reason", colour=0x1DCCA9, description=reason)
                        embeds = [r_profile, add_case]
                        #
                        server_reports_channel = bot.get_channel(SERVER_REPORTS_CHANNEL)
                        await server_reports_channel.send(content=f"<@&{appealed_server_report_ping}>\nAppeal on `{guild_id}`",
                                                        embeds=embeds)
                        await server_reports_channel.send(content=f"Reason for appeal", embed=reason_embed)
                        await old_message_edit_queue.put((interaction.message, {"content": f"**Appeal has been published.** Appeal accepted by <@{accepted_by}>.\nLink to thread: <#{channel_id}>\n\nAgree: {len(agree_users)}\nDisagree: {len(disagree_users)}",
                            "view": None, "embeds": embeds}))
                        thread = await bot.fetch_channel(channel_id)
                        message = await thread.fetch_message(message_id)
                        await old_message_edit_queue.put(
                            (message,
                             {"content": f"**Appeal has been published.** Appeal accepted by <@{accepted_by}>.",
                              "view": None}))
                        await bot.get_channel(channel_id).send(
                            f"Appeal on `{guild_id}` has been published. <@{requested_by}> <@{accepted_by}>")
                        inprogresscol.delete_one({"_id": interaction.message.id})
                    else:  # new case exists
                        add_case_list["accepted_by"] = f"{interaction.user.mention}"
                        inprogresscol.update_one(
                            {"_id": interaction.message.id},
                            {"$set": {"add_case_list": add_case_list}},
                        )
                        #
                        r_profile = reconstruct_server_r_profile(guild_data, r_profile_list, title)
                        add_case = format_server_add_case(add_case_list, case_title)
                        embeds = [r_profile, add_case]

                        query_filter = {"_id": str(guild_id)}
                        update_operation = {'$set': {"r_profile_list": r_profile_list}}
                        serverscol.update_one(query_filter, update_operation)
                        update_operation = {'$set': {str(no_of_cases + 1): add_case_list}}
                        serverscol.update_one(query_filter, update_operation)

                        server_reports_channel = bot.get_channel(SERVER_REPORTS_CHANNEL)
                        await server_reports_channel.send(content=f"<@&{updated_server_report_ping}>\nAdded report on `{guild_id}`",
                                                        embeds=embeds)
                        await old_message_edit_queue.put((interaction.message, {"content": f"**Report has been published.** Report accepted by <@{accepted_by}>.\nLink to thread: <#{channel_id}>\n\nAgree: {len(agree_users)}\nDisagree: {len(disagree_users)}",
                            "view": None, "embeds": embeds}))
                        thread = await bot.fetch_channel(channel_id)
                        message = await thread.fetch_message(message_id)
                        await old_message_edit_queue.put(
                            (message,
                             {"content": f"**Report has been published.** Report accepted by <@{accepted_by}>.",
                              "view": None}))
                        await bot.get_channel(channel_id).send(
                            f"Report on `{guild_id}` has been published. <@{requested_by}> <@{accepted_by}>")
                        inprogresscol.delete_one({"_id": interaction.message.id})
                else:  # if new reported server
                    add_case_list["accepted_by"] = f"{interaction.user.mention}"
                    inprogresscol.update_one(
                        {"_id": interaction.message.id},
                        {"$set": {"add_case_list": add_case_list}},
                    )
                    #
                    r_profile = reconstruct_server_r_profile(guild_data, r_profile_list, title)
                    add_case = format_server_add_case(add_case_list, case_title)
                    embeds = [r_profile, add_case]

                    new_server = {"_id": str(guild_id), "r_profile_list": r_profile_list,
                                "1": add_case_list}
                    serverscol.insert_one(new_server)

                    server_reports_channel = bot.get_channel(SERVER_REPORTS_CHANNEL)
                    await server_reports_channel.send(content=f"<@&{new_server_report_ping}>\nNew report on `{guild_id}`",
                                                    embeds=embeds)
                    await old_message_edit_queue.put((interaction.message, {"content": f"**Report has been published.** Report accepted by <@{accepted_by}>.\nLink to thread: <#{channel_id}>\n\nAgree: {len(agree_users)}\nDisagree: {len(disagree_users)}",
                        "view": None, "embeds": embeds}))
                    thread = await bot.fetch_channel(channel_id)
                    message = await thread.fetch_message(message_id)
                    await old_message_edit_queue.put(
                        (message,
                         {"content": f"**Report has been published.** Report accepted by <@{accepted_by}>.",
                          "view": None}))
                    await bot.get_channel(channel_id).send(
                        f"Report on `{guild_id}` has been published. <@{requested_by}> <@{accepted_by}>")
                    inprogresscol.delete_one({"_id": interaction.message.id})
                try:
                    voters = agree_users + disagree_users
                    for voter in voters:
                        voter_query = {"_id": str(voter)}
                        voter_profile = trusteduserscol.find_one(voter_query)
                        if voter_profile:
                            trusteduserscol.update_one(
                                voter_query,
                                {"$inc": {"votes": 1}}
                            )
                    staff_query = {"_id": str(requested_by)}
                    if trusteduserscol.find_one(staff_query):
                        trusteduserscol.update_one(
                            staff_query,
                            {"$inc": {"reports": 1}}
                        )
                    if staffweeklycol.find_one(staff_query):
                        staffweeklycol.update_one(
                            staff_query,
                            {"$inc": {"weekly_reports": 1}}
                        )
                    sr_query = {"_id": str(accepted_by)}
                    if trusteduserscol.find_one(sr_query):
                        trusteduserscol.update_one(
                            {"_id": str(accepted_by)},
                            {"$inc": {"reviews": 1}}
                        )
                    if staffweeklycol.find_one(sr_query):
                        staffweeklycol.update_one(
                            {"_id": str(accepted_by)},
                            {"$inc": {"weekly_reviews": 1}}
                        )
                except Exception as e:
                    print(f"{e}")
                current_name = interaction.channel.name
                new_name = current_name if current_name.startswith("p-") else f"p-{current_name}"
                await asyncio.sleep(2)
                await interaction.channel.edit(name=new_name, archived=True, locked=True)
            else:
                await interaction.followup.send("You do not have permission to publish the report.", ephemeral=True)


# new account
class NewAccountReportView(discord.ui.View):
    def __init__(self, game_uid, requested_by):
        super().__init__(timeout=3600)
        self.game_uid = game_uid
        self.requested_by = requested_by

    @discord.ui.button(label="Report", style=discord.ButtonStyle.red, custom_id="newaccountreport:report")
    async def report_button(self, interaction, button):
        #
        game_uid = self.game_uid
        requested_by = self.requested_by
        #
        await interaction.response.defer()
        existing_entry = inprogresscol.find_one({"account_id": game_uid})
        if existing_entry:
            # ongoing vote
            if "vote_channel_id" in existing_entry:
                vote_channel_id = existing_entry["vote_channel_id"]
                vote_message_id = existing_entry["_id"]
                vote_channel = bot.get_channel(vote_channel_id)
                if not vote_channel:
                    vote_channel = await bot.fetch_channel(vote_channel_id)
                try:
                    vote_message = await vote_channel.fetch_message(vote_message_id)
                except discord.NotFound:
                    return await interaction.followup.send(
                        "This message could not be found. It may have been deleted.", ephemeral=True)
                await interaction.followup.send(f"There already exists an ongoing vote on `{game_uid}`: {vote_message.jump_url}")
            # ongoing report
            else:
                channel_id = existing_entry["channel_id"]
                message_id = existing_entry["_id"]
                thread = await bot.fetch_channel(channel_id)
                try:
                    message = await thread.fetch_message(message_id)
                except discord.NotFound:
                    return await interaction.followup.send(
                        "This message could not be found. It may have been deleted.", ephemeral=True)
                await interaction.followup.send(
                        f"There already exists an ongoing report on `{game_uid}`: {message.jump_url}")
            return
        if requested_by == interaction.user:
            await interaction.edit_original_response(view=None)
            msg = await interaction.followup.send(f"Initializing report on `{game_uid}`...", wait=True)
            title = "TBC"
            case_title = "TBC"
            r_profile_list = [
                # [0] links
                "",
                # [1] other tags
                "",
                # [2] links_image_links
                [],
            ]
            add_case_list = {
                "date_added": f"<t:{round(int(discord.utils.utcnow().timestamp()))}:D> (<t:{round(int(discord.utils.utcnow().timestamp()))}:R>)",
                "related_users": "", "tags": "", "reason": "", "contributor": "", "staff": f"{interaction.user.mention}",
                "accepted_by": "", "proofs": []}
            channel_id = msg.channel.id
            message_id = msg.id
            r_profile = format_account_r_profile(game_uid, r_profile_list, title)
            add_case = format_account_add_case(add_case_list, case_title)
            embeds = [r_profile, add_case]
            try:
                inprogresscol.insert_one({"_id": message_id,
                                          "account_id": game_uid,
                                          "requested_by": requested_by.id,
                                          "channel_id": channel_id,
                                          "r_profile_list": r_profile_list,
                                          "add_case_list": add_case_list,
                                          "title": title,
                                          "case_title": case_title
                                          })
            except DuplicateKeyError: pass
            await msg.edit(embeds=embeds, view=LinksView())
        elif is_active_staff(interaction.user):
            await interaction.followup.send(
                "This was requested by " + f"{requested_by.mention}, you cannot interact with this component.",
                ephemeral=True)
        else:
            await interaction.followup.send("You do not have permission to use this button.", ephemeral=True)

class LinksView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(emoji="<:rightarrow:1458096774521553038>", style=discord.ButtonStyle.grey, custom_id="links:next")
    async def next_button(self, interaction, button):
        await interaction.response.defer()
        #
        session = inprogresscol.find_one({"_id": interaction.message.id})
        if session:
            requested_by = session["requested_by"]
            channel_id = session["channel_id"]
            message_id = interaction.message.id
            r_profile_list = session["r_profile_list"]
            add_case_list = session["add_case_list"]
            title = session["title"]
            case_title = session["case_title"]
            game_uid = session["account_id"]
            #
            thread = await bot.fetch_channel(channel_id)
            message = await thread.fetch_message(message_id)
            if requested_by == interaction.user.id or is_sr(interaction.user):
                r_profile = format_account_r_profile(game_uid, r_profile_list, title)
                add_case = format_account_add_case(add_case_list, case_title)
                embeds = [r_profile, add_case]
                await message.edit(embeds=embeds, view=AccountTagsView())

    @discord.ui.button(label="Links", style=discord.ButtonStyle.green, custom_id="links:input")
    async def links_button(self, interaction, button):
        session = inprogresscol.find_one({"_id": interaction.message.id})
        if session:
            requested_by = session["requested_by"]
            #
            if requested_by == interaction.user.id:
                await interaction.response.send_modal(LinksModal())

    @discord.ui.button(label="Add Links Proofs", style=discord.ButtonStyle.green, custom_id="links:linksproofs")
    async def links_proofs_button(self, interaction, button):
        #
        session = inprogresscol.find_one({"_id": interaction.message.id})
        if session:
            requested_by = session["requested_by"]
            r_profile_list = session["r_profile_list"]
            #
            if requested_by == interaction.user.id:
                image_links = []
                r_profile_list[2] = []
                await interaction.response.send_message(
                    "Please send the images you would like to upload (max 10). **All images previously uploaded in this session have been removed.**",
                    ephemeral=True)

                # Wait for a follow-up message from the user in the same channel
                def check(m):
                    # Check if the message is from the same user, in the same channel, and has an attachment
                    return m.author == interaction.user and m.channel == interaction.channel

                try:
                    msg = await bot.wait_for('message', check=check, timeout=120.0)
                except asyncio.TimeoutError:
                    await interaction.followup.send("You took too long to upload an image.", ephemeral=True)
                    return
                if msg.attachments:
                    for attachment in msg.attachments:
                        # Ensure the attachment is an image (optional check)
                        if attachment.content_type and attachment.content_type.startswith('image/'):
                            try:
                                # 1. Download the file data using aiohttp
                                async with aiohttp.ClientSession() as http_session:
                                    async with http_session.get(attachment.url) as resp:
                                        # For this example, we just send back the image URL and filename
                                        data = io.BytesIO(await resp.read())
                                        file = discord.File(data, filename=attachment.filename)
                                        channel_to_send = bot.get_channel(PROOFS_CHANNEL)
                                        sent_message = await channel_to_send.send(file=file)
                                        if sent_message.attachments:
                                            new_image_url = sent_message.attachments[0].url
                                            image_links.append(new_image_url)
                                            r_profile_list[2].append(new_image_url)
                            except Exception:
                                await msg.channel.send(f"An error occurred with file {attachment.filename}")
                #
                inprogresscol.update_one(
                    {"_id": interaction.message.id},
                    {"$set": {"r_profile_list": r_profile_list}}
                )
                #
                image_embeds = image_links_to_embeds(image_links)
                await interaction.followup.send(f"Images received from {interaction.user.mention}.",
                                                embeds=image_embeds)

    @discord.ui.button(label="Show Links Proofs", style=discord.ButtonStyle.grey, custom_id="links:showlinksproofs")
    async def show_links_proofs_button(self, interaction, button):
        await interaction.response.defer()
        #
        session = inprogresscol.find_one({"_id": interaction.message.id})
        if session:
            requested_by = session["requested_by"]
            r_profile_list = session["r_profile_list"]
            game_uid = session["account_id"]
            #
            if requested_by == interaction.user.id or is_sr(interaction.user):
                image_embeds = image_links_to_embeds(r_profile_list[2])
                await interaction.followup.send(f"Links Proofs for `{game_uid}`",
                                                embeds=image_embeds, ephemeral=True)
class LinksModal(discord.ui.Modal, title="Links"):
    links = discord.ui.TextInput(label="Links", placeholder="List links here and leave a newline between game UIDs.",
                                required=True, style=discord.TextStyle.long)

    def __init__(self):
        super().__init__(timeout=None)

    async def on_submit(self, interaction):
        await interaction.response.defer()
        #
        session = inprogresscol.find_one({"_id": interaction.message.id})
        if session:
            channel_id = session["channel_id"]
            message_id = interaction.message.id
            r_profile_list = session["r_profile_list"]
            add_case_list = session["add_case_list"]
            title = session["title"]
            case_title = session["case_title"]
            game_uid = session["account_id"]
            #
            thread = await bot.fetch_channel(channel_id)
            message = await thread.fetch_message(message_id)
            links_input = self.links.value
            game_uid_list = get_game_uid_list(links_input)
            r_profile_list[0] = game_uid_list or []
            #
            inprogresscol.update_one(
                {"_id": interaction.message.id},
                {"$set": {"r_profile_list": r_profile_list}}
            )
            #
            r_profile = format_account_r_profile(game_uid, r_profile_list, title)
            add_case = format_account_add_case(add_case_list, case_title)
            embeds = [r_profile, add_case]
            await message.edit(embeds=embeds, view=LinksView())

class AccountTagsView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(emoji="<:leftarrow:1458096658062770176>", style=discord.ButtonStyle.grey, custom_id="accounttags:prev")
    async def prev_button(self, interaction, button):
        await interaction.response.defer()
        #
        session = inprogresscol.find_one({"_id": interaction.message.id})
        if session:
            requested_by = session["requested_by"]
            channel_id = session["channel_id"]
            message_id = interaction.message.id
            r_profile_list = session["r_profile_list"]
            add_case_list = session["add_case_list"]
            title = session["title"]
            case_title = session["case_title"]
            game_uid = session["account_id"]
            #
            thread = await bot.fetch_channel(channel_id)
            message = await thread.fetch_message(message_id)
            if requested_by == interaction.user.id or is_sr(interaction.user):
                r_profile = format_account_r_profile(game_uid, r_profile_list, title)
                add_case = format_account_add_case(add_case_list, case_title)
                embeds = [r_profile, add_case]
                await message.edit(embeds=embeds, view=LinksView())

    @discord.ui.button(emoji="<:rightarrow:1458096774521553038>", style=discord.ButtonStyle.grey, custom_id="accounttags:next")
    async def next_button(self, interaction, button):
        await interaction.response.defer()
        #
        session = inprogresscol.find_one({"_id": interaction.message.id})
        if session:
            requested_by = session["requested_by"]
            channel_id = session["channel_id"]
            message_id = interaction.message.id
            r_profile_list = session["r_profile_list"]
            add_case_list = session["add_case_list"]
            title = session["title"]
            case_title = session["case_title"]
            game_uid = session["account_id"]
            #
            thread = await bot.fetch_channel(channel_id)
            message = await thread.fetch_message(message_id)
            if requested_by == interaction.user.id or is_sr(interaction.user):
                r_profile = format_account_r_profile(game_uid, r_profile_list, title)
                add_case = format_account_add_case(add_case_list, case_title)
                embeds = [r_profile, add_case]
                await message.edit(embeds=embeds, view=RelatedUsersView())

    @discord.ui.select(options=account_tag_options, placeholder="Select Tag(s)...", custom_id="accounttags:select",
                       max_values=len(account_tag_options))
    async def select_callback(self, interaction, select):
        await interaction.response.defer()
        #
        session = inprogresscol.find_one({"_id": interaction.message.id})
        if session:
            requested_by = session["requested_by"]
            channel_id = session["channel_id"]
            message_id = interaction.message.id
            r_profile_list = session["r_profile_list"]
            add_case_list = session["add_case_list"]
            game_uid = session["account_id"]
            #
            thread = await bot.fetch_channel(channel_id)
            message = await thread.fetch_message(message_id)
            if requested_by == interaction.user.id:
                sorted_tags = sort_account_tags(self.select_callback.values)
                case_title = sorted_tags[0]
                tags = selected_string(sorted_tags)
                add_case_list["tags"] = tags
                if "Recovered Account" in tags:
                    title = "Recovered Account"
                    all_other_tags = selected_string([tag for tag in sorted_tags if tag != "Recovered Account"])
                else:
                    title = sorted_tags[0]
                    all_other_tags = selected_string(sorted_tags[1:])
                r_profile_list[1] = all_other_tags
                #
                inprogresscol.update_one(
                    {"_id": interaction.message.id},
                    {"$set": {
                        "r_profile_list": r_profile_list,
                        "add_case_list": add_case_list,
                        "title": title,
                        "case_title": case_title, }
                    })
                #
                r_profile = format_account_r_profile(game_uid, r_profile_list, title)
                add_case = format_account_add_case(add_case_list, case_title)
                embeds = [r_profile, add_case]
                await message.edit(embeds=embeds)

def related_users_string(user_ids):
    return " ".join(f"`{user_id}`" for user_id in user_ids)

class RelatedUsersView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(emoji="<:leftarrow:1458096658062770176>", style=discord.ButtonStyle.grey, custom_id="relatedusers:prev")
    async def prev_button(self, interaction, button):
        await interaction.response.defer()
        #
        session = inprogresscol.find_one({"_id": interaction.message.id})
        if session:
            requested_by = session["requested_by"]
            channel_id = session["channel_id"]
            message_id = interaction.message.id
            r_profile_list = session["r_profile_list"]
            add_case_list = session["add_case_list"]
            title = session["title"]
            case_title = session["case_title"]
            game_uid = session["account_id"]
            #
            thread = await bot.fetch_channel(channel_id)
            message = await thread.fetch_message(message_id)
            if requested_by == interaction.user.id or is_sr(interaction.user):
                r_profile = format_account_r_profile(game_uid, r_profile_list, title)
                add_case = format_account_add_case(add_case_list, case_title)
                embeds = [r_profile, add_case]
                await message.edit(embeds=embeds, view=AccountTagsView())

    @discord.ui.button(emoji="<:rightarrow:1458096774521553038>", style=discord.ButtonStyle.grey,
                       custom_id="relatedusers:next")
    async def next_button(self, interaction, button):
        await interaction.response.defer()
        #
        session = inprogresscol.find_one({"_id": interaction.message.id})
        if session:
            requested_by = session["requested_by"]
            channel_id = session["channel_id"]
            message_id = interaction.message.id
            r_profile_list = session["r_profile_list"]
            add_case_list = session["add_case_list"]
            title = session["title"]
            case_title = session["case_title"]
            game_uid = session["account_id"]
            #
            thread = await bot.fetch_channel(channel_id)
            message = await thread.fetch_message(message_id)
            if requested_by == interaction.user.id or is_sr(interaction.user):
                r_profile = format_account_r_profile(game_uid, r_profile_list, title)
                add_case = format_account_add_case(add_case_list, case_title)
                embeds = [r_profile, add_case]
                await message.edit(embeds=embeds, view=AccountReasonView())

    @discord.ui.button(
        label="Related Users",
        style=discord.ButtonStyle.green,
        custom_id="relatedusers:input"
    )
    async def related_users_button(self, interaction, button):
        session = inprogresscol.find_one({"_id": interaction.message.id})
        if session and session["requested_by"] == interaction.user.id:
            await interaction.response.send_modal(RelatedUsersModal())

class RelatedUsersModal(
    discord.ui.Modal,
    title="Related Users"
):
    related_users = discord.ui.TextInput(
        label="Related Users",
        placeholder="List user IDs separated by spaces.",
        required=True,
        style=discord.TextStyle.paragraph
    )

    def __init__(self):
        super().__init__(timeout=None)

    async def on_submit(self, interaction):
        await interaction.response.defer()
        session = inprogresscol.find_one({"_id": interaction.message.id})
        if session:
            add_case_list = session["add_case_list"]
            title = session["title"]
            case_title = session["case_title"]
            game_uid = session["account_id"]
            thread = await bot.fetch_channel(session["channel_id"])
            message = await thread.fetch_message(interaction.message.id)
            ids = self.related_users.value.split()
            valid_users = []
            for id in ids:
                try:
                    fetched = await bot.fetch_user(int(id))
                except Exception:
                    continue
                if fetched.id not in valid_users:
                    valid_users.append(fetched.id)
            r_profile_list = session["r_profile_list"]
            if len(valid_users):
                add_case_list["related_users"] = related_users_string(valid_users)
            else:
                add_case_list["related_users"] = ""
            inprogresscol.update_one(
                {"_id": interaction.message.id},
                {"$set": {"add_case_list": add_case_list}}
            )
            r_profile = format_account_r_profile(game_uid, r_profile_list, title)
            add_case = format_account_add_case(add_case_list, case_title)
            embeds = [r_profile, add_case]
            await message.edit(embeds=embeds, view=RelatedUsersView())

class AccountReasonView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(emoji="<:leftarrow:1458096658062770176>", style=discord.ButtonStyle.grey, custom_id="accountreason:prev")
    async def prev_button(self, interaction, button):
        await interaction.response.defer()
        #
        session = inprogresscol.find_one({"_id": interaction.message.id})
        if session:
            requested_by = session["requested_by"]
            channel_id = session["channel_id"]
            message_id = interaction.message.id
            r_profile_list = session["r_profile_list"]
            add_case_list = session["add_case_list"]
            title = session["title"]
            case_title = session["case_title"]
            game_uid = session["account_id"]
            #
            thread = await bot.fetch_channel(channel_id)
            message = await thread.fetch_message(message_id)
            if requested_by == interaction.user.id or is_sr(interaction.user):
                r_profile = format_account_r_profile(game_uid, r_profile_list, title)
                add_case = format_account_add_case(add_case_list, case_title)
                embeds = [r_profile, add_case]
                await message.edit(embeds=embeds, view=RelatedUsersView())

    @discord.ui.button(emoji="<:rightarrow:1458096774521553038>", style=discord.ButtonStyle.grey, custom_id="accountreason:next")
    async def next_button(self, interaction, button):
        await interaction.response.defer()
        #
        session = inprogresscol.find_one({"_id": interaction.message.id})
        if session:
            requested_by = session["requested_by"]
            channel_id = session["channel_id"]
            message_id = interaction.message.id
            r_profile_list = session["r_profile_list"]
            add_case_list = session["add_case_list"]
            title = session["title"]
            case_title = session["case_title"]
            game_uid = session["account_id"]
            #
            thread = await bot.fetch_channel(channel_id)
            message = await thread.fetch_message(message_id)
            if requested_by == interaction.user.id or is_sr(interaction.user):
                r_profile = format_account_r_profile(game_uid, r_profile_list, title)
                add_case = format_account_add_case(add_case_list, case_title)
                embeds = [r_profile, add_case]
                await message.edit(embeds=embeds, view=AccountContributorView())

    @discord.ui.button(label="Reason", style=discord.ButtonStyle.green, custom_id="accountreason:input")
    async def reason_button(self, interaction, button):
        #
        session = inprogresscol.find_one({"_id": interaction.message.id})
        if session:
            requested_by = session["requested_by"]
            if requested_by == interaction.user.id:
                await interaction.response.send_modal(AccountReasonModal())
class AccountReasonModal(discord.ui.Modal, title="Reason"):
    reason = discord.ui.TextInput(label="Reason", placeholder="Input reason here.", required=True,
                                  style=discord.TextStyle.long)

    def __init__(self):
        super().__init__(timeout=None)

    async def on_submit(self, interaction):
        await interaction.response.defer()
        #
        session = inprogresscol.find_one({"_id": interaction.message.id})
        if session:
            channel_id = session["channel_id"]
            message_id = interaction.message.id
            r_profile_list = session["r_profile_list"]
            add_case_list = session["add_case_list"]
            title = session["title"]
            case_title = session["case_title"]
            game_uid = session["account_id"]
            #
            thread = await bot.fetch_channel(channel_id)
            message = await thread.fetch_message(message_id)
            reason = re.sub(r"\s+", " ", self.reason.value)
            add_case_list["reason"] = reason
            #
            inprogresscol.update_one(
                {"_id": interaction.message.id},
                {"$set": {"add_case_list": add_case_list}},
            )
            #
            r_profile = format_account_r_profile(game_uid, r_profile_list, title)
            add_case = format_account_add_case(add_case_list, case_title)
            embeds = [r_profile, add_case]
            await message.edit(embeds=embeds, view=AccountReasonView())

class AccountContributorView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(emoji="<:leftarrow:1458096658062770176>", style=discord.ButtonStyle.grey,
                       custom_id="accountcontributor:prev")
    async def prev_button(self, interaction, button):
        await interaction.response.defer()
        #
        session = inprogresscol.find_one({"_id": interaction.message.id})
        if session:
            requested_by = session["requested_by"]
            channel_id = session["channel_id"]
            message_id = interaction.message.id
            r_profile_list = session["r_profile_list"]
            add_case_list = session["add_case_list"]
            title = session["title"]
            case_title = session["case_title"]
            game_uid = session["account_id"]
            #
            thread = await bot.fetch_channel(channel_id)
            message = await thread.fetch_message(message_id)
            if requested_by == interaction.user.id or is_sr(interaction.user):
                r_profile = format_account_r_profile(game_uid, r_profile_list, title)
                add_case = format_account_add_case(add_case_list, case_title)
                embeds = [r_profile, add_case]
                await message.edit(embeds=embeds, view=AccountReasonView())

    @discord.ui.button(emoji="<:rightarrow:1458096774521553038>", style=discord.ButtonStyle.grey,
                       custom_id="accountcontributor:next")
    async def next_button(self, interaction, button):
        await interaction.response.defer()
        #
        session = inprogresscol.find_one({"_id": interaction.message.id})
        if session:
            requested_by = session["requested_by"]
            channel_id = session["channel_id"]
            message_id = interaction.message.id
            r_profile_list = session["r_profile_list"]
            add_case_list = session["add_case_list"]
            title = session["title"]
            case_title = session["case_title"]
            game_uid = session["account_id"]
            #
            thread = await bot.fetch_channel(channel_id)
            message = await thread.fetch_message(message_id)
            if requested_by == interaction.user.id or is_sr(interaction.user):
                r_profile = format_account_r_profile(game_uid, r_profile_list, title)
                add_case = format_account_add_case(add_case_list, case_title)
                embeds = [r_profile, add_case]
                await message.edit(embeds=embeds, view=AccountProofsView())

    @discord.ui.button(label="Contributor", style=discord.ButtonStyle.green, custom_id="accountcontributor:input")
    async def contributor_button(self, interaction, button):
        #
        session = inprogresscol.find_one({"_id": interaction.message.id})
        if session:
            requested_by = session["requested_by"]
            #
            if requested_by == interaction.user.id:
                await interaction.response.send_modal(AccountContributorModal())
class AccountContributorModal(discord.ui.Modal, title="Contributor"):
    contributor = discord.ui.TextInput(label="Contributor",
                                       placeholder="Account ID / n if Anonymous.", required=True,
                                       style=discord.TextStyle.short)

    def __init__(self):
        super().__init__(timeout=None)

    async def on_submit(self, interaction):
        await interaction.response.defer()
        #
        session = inprogresscol.find_one({"_id": interaction.message.id})
        if session:
            channel_id = session["channel_id"]
            message_id = interaction.message.id
            r_profile_list = session["r_profile_list"]
            add_case_list = session["add_case_list"]
            title = session["title"]
            case_title = session["case_title"]
            game_uid = session["account_id"]
            #
            thread = await bot.fetch_channel(channel_id)
            message = await thread.fetch_message(message_id)
            contributor_input = self.contributor.value
            if contributor_input.lower() == "n":
                add_case_list["contributor"] = "Anonymous"
            else:
                try:
                    contributor_id = await bot.fetch_user(int(contributor_input))
                except Exception:
                    add_case_list["contributor"] = ""
                else:
                    add_case_list["contributor"] = f"<@{contributor_id.id}>"
            #
            inprogresscol.update_one(
                {"_id": interaction.message.id},
                {"$set": {"add_case_list": add_case_list}},
            )
            #
            r_profile = format_account_r_profile(game_uid, r_profile_list, title)
            add_case = format_account_add_case(add_case_list, case_title)
            embeds = [r_profile, add_case]
            await message.edit(embeds=embeds, view=AccountContributorView())

class AccountProofsView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(emoji="<:leftarrow:1458096658062770176>", style=discord.ButtonStyle.grey, custom_id="accountproofs:prev")
    async def prev_button(self, interaction, button):
        await interaction.response.defer()
        #
        session = inprogresscol.find_one({"_id": interaction.message.id})
        if session:
            requested_by = session["requested_by"]
            channel_id = session["channel_id"]
            message_id = interaction.message.id
            r_profile_list = session["r_profile_list"]
            add_case_list = session["add_case_list"]
            title = session["title"]
            case_title = session["case_title"]
            game_uid = session["account_id"]
            #
            thread = await bot.fetch_channel(channel_id)
            message = await thread.fetch_message(message_id)
            if requested_by == interaction.user.id or is_sr(interaction.user):
                r_profile = format_account_r_profile(game_uid, r_profile_list, title)
                add_case = format_account_add_case(add_case_list, case_title)
                embeds = [r_profile, add_case]
                await message.edit(embeds=embeds, view=AccountContributorView())

    @discord.ui.button(label="Add Proofs", style=discord.ButtonStyle.green, custom_id="accountproofs:input")
    async def proofs_button(self, interaction, button):
        #
        session = inprogresscol.find_one({"_id": interaction.message.id})
        if session:
            requested_by = session["requested_by"]
            add_case_list = session["add_case_list"]
            #
            if requested_by == interaction.user.id:
                image_links = []
                add_case_list["proofs"] = []
                await interaction.response.send_message(
                    "Please send the images you would like to upload (max 10). **All images previously uploaded in this session have been removed.**",
                    ephemeral=True)

                # Wait for a follow-up message from the user in the same channel
                def check(m):
                    # Check if the message is from the same user, in the same channel, and has an attachment
                    return m.author == interaction.user and m.channel == interaction.channel

                try:
                    msg = await bot.wait_for('message', check=check, timeout=120.0)
                except asyncio.TimeoutError:
                    await interaction.followup.send("You took too long to upload an image.", ephemeral=True)
                    return
                if msg.attachments:
                    for attachment in msg.attachments:
                        # Ensure the attachment is an image (optional check)
                        if attachment.content_type and attachment.content_type.startswith('image/'):
                            try:
                                # 1. Download the file data using aiohttp
                                async with aiohttp.ClientSession() as http_session:
                                    async with http_session.get(attachment.url) as resp:
                                        # For this example, we just send back the image URL and filename
                                        data = io.BytesIO(await resp.read())
                                        file = discord.File(data, filename=attachment.filename)
                                        channel_to_send = bot.get_channel(PROOFS_CHANNEL)
                                        sent_message = await channel_to_send.send(file=file)
                                        if sent_message.attachments:
                                            new_image_url = sent_message.attachments[0].url
                                            image_links.append(new_image_url)
                                            add_case_list["proofs"].append(new_image_url)
                            except Exception:
                                await msg.channel.send(f"An error occurred with file {attachment.filename}")
                #
                inprogresscol.update_one(
                    {"_id": interaction.message.id},
                    {"$set": {"add_case_list": add_case_list}},
                )
                #
                image_embeds = image_links_to_embeds(image_links)
                await interaction.followup.send(f"Images received from {interaction.user.mention}.",
                                                embeds=image_embeds)

    @discord.ui.button(label="Show Proofs", style=discord.ButtonStyle.grey, custom_id="accountproofs:showproofs")
    async def show_proofs_button(self, interaction, button):
        await interaction.response.defer()
        #
        session = inprogresscol.find_one({"_id": interaction.message.id})
        if session:
            requested_by = session["requested_by"]
            add_case_list = session["add_case_list"]
            game_uid = session["account_id"]
            #
            if requested_by == interaction.user.id or is_sr(interaction.user):
                image_embeds = image_links_to_embeds(add_case_list["proofs"])
                await interaction.followup.send(f"Proofs for `{game_uid}`",
                                                embeds=image_embeds, ephemeral=True)

    @discord.ui.button(label="Show Links Proofs", style=discord.ButtonStyle.grey, custom_id="accountproofs:showlinksproofs")
    async def show_links_proofs_button(self, interaction, button):
        await interaction.response.defer()
        #
        session = inprogresscol.find_one({"_id": interaction.message.id})
        if session:
            requested_by = session["requested_by"]
            r_profile_list = session["r_profile_list"]
            game_uid = session["account_id"]
            #
            if requested_by == interaction.user.id or is_sr(interaction.user):
                image_embeds = image_links_to_embeds(r_profile_list[2])
                await interaction.followup.send(f"Links Proofs for `{game_uid}`",
                                                embeds=image_embeds, ephemeral=True)

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.grey, custom_id="accountproofs:cancel")
    async def cancel_button(self, interaction, button):
        await interaction.response.defer()
        #
        session = inprogresscol.find_one({"_id": interaction.message.id})
        if session:
            requested_by = session["requested_by"]
            channel_id = session["channel_id"]
            message_id = interaction.message.id
            #
            thread = await bot.fetch_channel(channel_id)
            message = await thread.fetch_message(message_id)
            if requested_by == interaction.user.id or is_sr(interaction.user):
                inprogresscol.delete_one({"_id": interaction.message.id})
                await message.edit(content=f"**Cancelled by {interaction.user.mention}.**", view=None)

    @discord.ui.button(label="Accept", style=discord.ButtonStyle.grey, custom_id="accountproofs:accept")
    async def accept_button(self, interaction, button):
        await interaction.response.defer()
        #
        session = inprogresscol.find_one({"_id": interaction.message.id})
        if session:
            requested_by = session["requested_by"]
            channel_id = session["channel_id"]
            message_id = interaction.message.id
            r_profile_list = session["r_profile_list"]
            add_case_list = session["add_case_list"]
            title = session["title"]
            case_title = session["case_title"]
            game_uid = session["account_id"]
            #
            thread = await bot.fetch_channel(channel_id)
            message = await thread.fetch_message(message_id)
            if is_sr(interaction.user) and interaction.user.id != requested_by:
                accepted_by = interaction.user
                add_case_list["accepted_by"] = f"<@{interaction.user.id}>"
                #
                r_profile = format_account_r_profile(game_uid, r_profile_list, title)
                add_case = format_account_add_case(add_case_list, case_title)
                embeds = [r_profile, add_case]
                #
                vote_channel = bot.get_channel(VOTE_CHANNEL)
                agree_users = []
                disagree_users = []
                links_proofs_embeds = image_links_to_embeds(r_profile_list[2])
                proofs_embeds = image_links_to_embeds(add_case_list["proofs"])
                new_report_message = await vote_channel.send(content=f"New report on `{game_uid}`")
                new_report_thread = await new_report_message.create_thread(name=f"{game_uid}")
                await new_report_thread.send(f"<@&{ticket_ping}>")
                vote_msg = await new_report_thread.send(
                    content=f"Report accepted by {accepted_by.mention}.\nLink to thread: <#{channel_id}>\n\nAgree: 0\nDisagree: 0",
                    embeds=embeds, view=AccountVoteView())
                vote_channel_id = vote_msg.channel.id
                vote_message_id = vote_msg.id
                old_session = inprogresscol.find_one({"account_id": game_uid})
                if old_session:
                    inprogresscol.delete_one({"_id": old_session["_id"]})
                inprogresscol.insert_one({
                    "_id": vote_message_id,
                    "account_id": game_uid,
                    "requested_by": requested_by,
                    "channel_id": channel_id,
                    "message_id": interaction.message.id,
                    "r_profile_list": r_profile_list,
                    "add_case_list": add_case_list,
                    "title": title,
                    "case_title": case_title,
                    "vote_channel_id": vote_channel_id,
                    "accepted_by": accepted_by.id,
                    "agree_users": agree_users,
                    "disagree_users": disagree_users,
                })
                await new_report_thread.send(content=f"Links Proofs for `{game_uid}`", embeds=links_proofs_embeds)
                await new_report_thread.send(content=f"Proofs for `{game_uid}`", embeds=proofs_embeds)
                await old_message_edit_queue.put(
                    (message, {"content": "Report has been submitted for voting.", "embeds": embeds, "view": None}))
            else:
                await interaction.followup.send("You do not have permission to accept the report for voting.",
                                                ephemeral=True)


# edit account
class EditAccountReportView(discord.ui.View):
    def __init__(self, game_uid, account_profile, requested_by, current_case):
        super().__init__(timeout=3600)
        self.game_uid = game_uid
        self.account_profile = account_profile
        self.requested_by = requested_by
        self.current_case = current_case

    @discord.ui.button(emoji="<:leftarrow:1458096658062770176>", style=discord.ButtonStyle.grey, custom_id="editaccountreport:prev",
                       row=0)
    async def prev_button(self, interaction, button):
        await interaction.response.defer()
        #
        game_uid = self.game_uid
        account_profile = self.account_profile
        requested_by = self.requested_by
        current_case = self.current_case
        #
        no_of_cases = len(account_profile) - 2
        #
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
                                                             view=EditAccountReportView(game_uid, account_profile, requested_by,
                                                                                   current_case))

    @discord.ui.button(emoji="<:rightarrow:1458096774521553038>", style=discord.ButtonStyle.grey, custom_id="editaccountreport:next",
                       row=0)
    async def next_button(self, interaction, button):
        await interaction.response.defer()
        #
        game_uid = self.game_uid
        account_profile = self.account_profile
        requested_by = self.requested_by
        current_case = self.current_case
        #
        no_of_cases = len(account_profile) - 2
        #
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
                                                         view=EditAccountReportView(game_uid, account_profile, requested_by,
                                                                               current_case))

    @discord.ui.button(label="Proofs", style=discord.ButtonStyle.grey, custom_id="editaccountreport:proofs", row=0)
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

    @discord.ui.button(label="Links", style=discord.ButtonStyle.grey, custom_id="editaccountreport:linksproofs", row=0)
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

    @discord.ui.button(label="Edit Links", style=discord.ButtonStyle.primary, custom_id="editaccountreport:editlinks", row=1)
    async def edit_links_button(self, interaction, button):
        #
        game_uid = self.game_uid
        account_profile = self.account_profile
        requested_by = self.requested_by
        #
        await interaction.response.defer()
        existing_entry = inprogresscol.find_one({"account_id": game_uid})
        if existing_entry:
            # ongoing vote
            if "vote_channel_id" in existing_entry:
                vote_channel_id = existing_entry["vote_channel_id"]
                vote_message_id = existing_entry["_id"]
                vote_channel = bot.get_channel(vote_channel_id)
                if not vote_channel:
                    vote_channel = await bot.fetch_channel(vote_channel_id)
                try:
                    vote_message = await vote_channel.fetch_message(vote_message_id)
                except discord.NotFound:
                    return await interaction.followup.send(
                        "This message could not be found. It may have been deleted.", ephemeral=True)
                await interaction.followup.send(
                    f"There already exists an ongoing vote on `{game_uid}`: {vote_message.jump_url}")
            # ongoing report
            else:
                channel_id = existing_entry["channel_id"]
                message_id = existing_entry["_id"]
                thread = await bot.fetch_channel(channel_id)
                try:
                    message = await thread.fetch_message(message_id)
                except discord.NotFound:
                    return await interaction.followup.send(
                        "This message could not be found. It may have been deleted.", ephemeral=True)
                await interaction.followup.send(
                    f"There already exists an ongoing report on `{game_uid}`: {message.jump_url}")
            return
        if requested_by == interaction.user:
            await interaction.edit_original_response(view=None)
            msg = await interaction.followup.send(f"Editing links for `{game_uid}`...", wait=True)
            r_profile_list = account_profile["r_profile_list"]
            cases = []
            no_of_cases = len(account_profile) - 2
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
            channel_id = msg.channel.id
            message_id = msg.id
            r_profile = format_account_r_profile(game_uid, r_profile_list, title)
            reason = ""
            reason_embed = discord.Embed(title="Reason", description=reason)
            try:
                inprogresscol.insert_one({"_id": message_id,
                                          "account_id": game_uid,
                                          "requested_by": requested_by.id,
                                          "channel_id": channel_id,
                                          "r_profile_list": r_profile_list,
                                          "title": title,
                                          "reason": reason,
                                          })
            except DuplicateKeyError:
                pass
            embeds = [r_profile, reason_embed]
            await msg.edit(embeds=embeds, view=EditLinksOnlyView())
        elif is_active_staff(interaction.user):
            await interaction.followup.send(
                "This was requested by " + f"{requested_by.mention}, you cannot interact with this component.",
                ephemeral=True)
        else:
            await interaction.followup.send("You do not have permission to use this button.", ephemeral=True)

    @discord.ui.button(label="Add Report", style=discord.ButtonStyle.red, custom_id="editaccountreport:addreport", row=1)
    async def add_report_button(self, interaction, button):
        #
        game_uid = self.game_uid
        account_profile = self.account_profile
        requested_by = self.requested_by
        current_case = self.current_case
        #
        await interaction.response.defer()
        existing_entry = inprogresscol.find_one({"account_id": game_uid})
        if existing_entry:
            # ongoing vote
            if "vote_channel_id" in existing_entry:
                vote_channel_id = existing_entry["vote_channel_id"]
                vote_message_id = existing_entry["_id"]
                vote_channel = bot.get_channel(vote_channel_id)
                if not vote_channel:
                    vote_channel = await bot.fetch_channel(vote_channel_id)
                try:
                    vote_message = await vote_channel.fetch_message(vote_message_id)
                except discord.NotFound:
                    return await interaction.followup.send(
                        "This message could not be found. It may have been deleted.", ephemeral=True)
                await interaction.followup.send(
                    f"There already exists an ongoing vote on `{game_uid}`: {vote_message.jump_url}")
            # ongoing report
            else:
                channel_id = existing_entry["channel_id"]
                message_id = existing_entry["_id"]
                thread = await bot.fetch_channel(channel_id)
                try:
                    message = await thread.fetch_message(message_id)
                except discord.NotFound:
                    return await interaction.followup.send(
                        "This message could not be found. It may have been deleted.", ephemeral=True)
                await interaction.followup.send(
                    f"There already exists an ongoing report on `{game_uid}`: {message.jump_url}")
            return
        if requested_by == interaction.user:
            await interaction.edit_original_response(view=None)
            msg = await interaction.followup.send(f"Adding report on `{game_uid}`...", wait=True)
            r_profile_list = account_profile["r_profile_list"]
            cases = []
            no_of_cases = len(account_profile) - 2
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
            case_title = "TBC"
            add_case_list = {
                "date_added": f"<t:{round(int(discord.utils.utcnow().timestamp()))}:D> (<t:{round(int(discord.utils.utcnow().timestamp()))}:R>)",
                "related_users": "", "tags": "", "reason": "", "contributor": "", "staff": f"{interaction.user.mention}",
                "accepted_by": "", "proofs": []}
            channel_id = msg.channel.id
            message_id = msg.id
            try:
                inprogresscol.insert_one({"_id": message_id,
                                          "account_id": game_uid,
                                          "requested_by": requested_by.id,
                                          "channel_id": channel_id,
                                          "r_profile_list": r_profile_list,
                                          "add_case_list": add_case_list,
                                          "title": title,
                                          "case_title": case_title
                                          })
            except DuplicateKeyError:
                pass
            r_profile = format_account_r_profile(game_uid, r_profile_list, title)
            add_case = format_account_add_case(add_case_list, case_title)
            embeds = [r_profile, add_case]
            await msg.edit(embeds=embeds, view=AddReportLinksView())
        elif is_active_staff(interaction.user):
            await interaction.followup.send(
                "This was requested by " + f"{requested_by.mention}, you cannot interact with this component.",
                ephemeral=True)
        else:
            await interaction.followup.send("You do not have permission to use this button.", ephemeral=True)

    @discord.ui.button(label="Appeal", style=discord.ButtonStyle.green, custom_id="editaccountreport:appeal", row=1)
    async def appeal_button(self, interaction, button):
        #
        game_uid = self.game_uid
        account_profile = self.account_profile
        requested_by = self.requested_by
        current_case = self.current_case
        #
        await interaction.response.defer()
        existing_entry = inprogresscol.find_one({"account_id": game_uid})
        if existing_entry:
            # ongoing vote
            if "vote_channel_id" in existing_entry:
                vote_channel_id = existing_entry["vote_channel_id"]
                vote_message_id = existing_entry["_id"]
                vote_channel = bot.get_channel(vote_channel_id)
                if not vote_channel:
                    vote_channel = await bot.fetch_channel(vote_channel_id)
                try:
                    vote_message = await vote_channel.fetch_message(vote_message_id)
                except discord.NotFound:
                    return await interaction.followup.send(
                        "This message could not be found. It may have been deleted.", ephemeral=True)
                await interaction.followup.send(
                    f"There already exists an ongoing vote on `{game_uid}`: {vote_message.jump_url}")
            # ongoing report
            else:
                channel_id = existing_entry["channel_id"]
                message_id = existing_entry["_id"]
                thread = await bot.fetch_channel(channel_id)
                try:
                    message = await thread.fetch_message(message_id)
                except discord.NotFound:
                    return await interaction.followup.send(
                        "This message could not be found. It may have been deleted.", ephemeral=True)
                await interaction.followup.send(
                    f"There already exists an ongoing report on `{game_uid}`: {message.jump_url}")
            return
        if requested_by == interaction.user:
            await interaction.edit_original_response(view=None)
            msg = await interaction.followup.send(f"Appealing for `{game_uid}`...", wait=True)
            r_profile_list = account_profile["r_profile_list"]
            cases = []
            no_of_cases = len(account_profile) - 2
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
            current_index = current_case - 1
            add_case_list = account_profile[str(current_case)]
            case_tags = cases[current_index]["tags"].split(", ")
            case_title = case_tags[0]
            channel_id = msg.channel.id
            message_id = msg.id
            r_profile = format_account_r_profile(game_uid, r_profile_list, title)
            reason = ""
            reason_embed = discord.Embed(title="Reason", colour=0x1dcca9, description=reason)
            try:
                inprogresscol.insert_one({"_id": message_id,
                                          "account_id": game_uid,
                                          "requested_by": requested_by.id,
                                          "channel_id": channel_id,
                                          "r_profile_list": r_profile_list,
                                          "add_case_list": add_case_list,
                                          "title": title,
                                          "case_title": case_title,
                                          "reason": reason
                                          })
            except DuplicateKeyError:
                pass
            add_case = format_account_add_case(add_case_list, case_title)
            embeds = [r_profile, add_case, reason_embed]
            await msg.edit(embeds=embeds, view=AccountAppealView())
        elif is_active_staff(interaction.user):
            await interaction.followup.send(
                "This was requested by " + f"{requested_by.mention}, you cannot interact with this component.",
                ephemeral=True)
        else:
            await interaction.followup.send("You do not have permission to use this button.", ephemeral=True)


# edit links only
class EditLinksOnlyView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
    @discord.ui.button(label="Add Links", style=discord.ButtonStyle.green, custom_id="editlinksonly:addlinks")
    async def add_links_button(self, interaction, button):
        session = inprogresscol.find_one({"_id": interaction.message.id})
        if session:
            requested_by = session["requested_by"]
            if requested_by == interaction.user.id:
                await interaction.response.send_modal(AddLinksOnlyModal())

    @discord.ui.button(label="Remove Links", style=discord.ButtonStyle.red, custom_id="editlinksonly:removelinks")
    async def remove_links_button(self, interaction, button):
        session = inprogresscol.find_one({"_id": interaction.message.id})
        if session:
            requested_by = session["requested_by"]
            if requested_by == interaction.user.id:
                await interaction.response.send_modal(RemoveLinksOnlyModal())

    @discord.ui.button(label="Add Links Proofs", style=discord.ButtonStyle.green, custom_id="editlinksonly:addlinksproofs")
    async def add_links_proofs_button(self, interaction, button):
        session = inprogresscol.find_one({"_id": interaction.message.id})
        if session:
            requested_by = session["requested_by"]
            r_profile_list = session["r_profile_list"]
            if requested_by == interaction.user.id:
                image_links = []
                original_image_links = r_profile_list[2].copy()
                await interaction.response.send_message(
                    f"Please send the images you would like to upload (max {10 - len(r_profile_list[2])}).",
                    ephemeral=True)
                def check(m):
                    return m.author == interaction.user and m.channel == interaction.channel

                try:
                    msg = await bot.wait_for('message', check=check, timeout=120.0)
                except asyncio.TimeoutError:
                    await interaction.followup.send("You took too long to upload an image.", ephemeral=True)
                    return
                if msg.attachments:
                    for attachment in msg.attachments:
                        # Ensure the attachment is an image (optional check)
                        if attachment.content_type and attachment.content_type.startswith('image/'):
                            try:
                                # 1. Download the file data using aiohttp
                                async with aiohttp.ClientSession() as http_session:
                                    async with http_session.get(attachment.url) as resp:
                                        # For this example, we just send back the image URL and filename
                                        data = io.BytesIO(await resp.read())
                                        file = discord.File(data, filename=attachment.filename)
                                        channel_to_send = bot.get_channel(PROOFS_CHANNEL)
                                        sent_message = await channel_to_send.send(file=file)
                                        if sent_message.attachments:
                                            new_image_url = sent_message.attachments[0].url
                                            image_links.append(new_image_url)
                                            r_profile_list[2].append(new_image_url)
                            except Exception:
                                await msg.channel.send(f"An error occurred with file {attachment.filename}")
                if len(r_profile_list[2]) > 10:
                    await interaction.followup.send(
                        f"There are a total of {len(r_profile_list[2])} images, exceeding the max limit of 10. Please try again.")
                    r_profile_list[2] = original_image_links
                else:
                    inprogresscol.update_one(
                        {"_id": interaction.message.id},
                        {"$set": {"r_profile_list": r_profile_list}}
                    )
                    #
                    image_embeds = image_links_to_embeds(image_links)
                    await interaction.followup.send(f"Images received from {interaction.user.mention}.",
                                                    embeds=image_embeds)

    @discord.ui.button(label="Remove Links Proofs", style=discord.ButtonStyle.red, custom_id="editlinksonly:removelinksproofs")
    async def remove_links_proofs_button(self, interaction, button):
        session = inprogresscol.find_one({"_id": interaction.message.id})
        if session:
            requested_by = session["requested_by"]
            r_profile_list = session["r_profile_list"]
            if requested_by == interaction.user.id:
                await interaction.response.send_message(
                    f"Please list image(s) you would like to remove, from 1 to {len(r_profile_list[2])}, with a space between each number.",
                    ephemeral=True)
                def check(m):
                    return m.author == interaction.user and m.channel == interaction.channel

                try:
                    msg = await bot.wait_for('message', check=check, timeout=120.0)
                except asyncio.TimeoutError:
                    await interaction.followup.send("You took too long to respond.", ephemeral=True)
                    return
                try:
                    to_remove = msg.content.split()
                    indices_to_remove = []
                    for i in to_remove:
                        indices_to_remove.append(int(i) - 1)
                    indices_to_remove = set(indices_to_remove)
                except Exception:
                    await interaction.followup.send("Invalid response. Please try again.", ephemeral=True)
                else:
                    images_removed = []
                    for i in indices_to_remove:
                        if 0 <= i < len(r_profile_list[2]):
                            images_removed.append(r_profile_list[2][i])
                    r_profile_list[2] = [value for index, value in enumerate(r_profile_list[2]) if
                                         index not in indices_to_remove]
                    inprogresscol.update_one(
                        {"_id": interaction.message.id},
                        {"$set": {"r_profile_list": r_profile_list}}
                    )
                    #
                    image_embeds = image_links_to_embeds(images_removed)
                    await interaction.followup.send(f"Images removed by {interaction.user.mention}.",
                                                    embeds=image_embeds)

    @discord.ui.button(label="Show Links Proofs", style=discord.ButtonStyle.grey, custom_id="editlinksonly:showlinksproofs")
    async def show_links_proofs_button(self, interaction, button):
        await interaction.response.defer()
        session = inprogresscol.find_one({"_id": interaction.message.id})
        if session:
            requested_by = session["requested_by"]
            r_profile_list = session["r_profile_list"]
            game_uid = session["account_id"]
            if requested_by == interaction.user.id or is_sr(interaction.user):
                image_embeds = image_links_to_embeds(r_profile_list[2])
                await interaction.followup.send(f"Links Proofs for `{game_uid}`",
                                                embeds=image_embeds, ephemeral=True)

    @discord.ui.button(label="Reason", style=discord.ButtonStyle.primary, custom_id="editlinksonly:reason")
    async def reason_button(self, interaction, button):
        #
        session = inprogresscol.find_one({"_id": interaction.message.id})
        if session:
            requested_by = session["requested_by"]
            if requested_by == interaction.user.id:
                await interaction.response.send_modal(LinksReasonModal())

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.grey, custom_id="editlinksonly:cancel")
    async def cancel_button(self, interaction, button):
        await interaction.response.defer()
        session = inprogresscol.find_one({"_id": interaction.message.id})
        if session:
            requested_by = session["requested_by"]
            channel_id = session["channel_id"]
            message_id = interaction.message.id
            thread = await bot.fetch_channel(channel_id)
            message = await thread.fetch_message(message_id)
            if requested_by == interaction.user.id or is_sr(interaction.user):
                inprogresscol.delete_one({"_id": interaction.message.id})
                await message.edit(content=f"**Cancelled by {interaction.user.mention}.**", view=None)

    @discord.ui.button(label="Accept", style=discord.ButtonStyle.grey, custom_id="editlinksonly:accept")
    async def accept_button(self, interaction, button):
        await interaction.response.defer()
        #
        session = inprogresscol.find_one({"_id": interaction.message.id})
        if session:
            requested_by = session["requested_by"]
            channel_id = session["channel_id"]
            message_id = interaction.message.id
            r_profile_list = session["r_profile_list"]
            title = session["title"]
            reason = session["reason"]
            game_uid = session["account_id"]
            thread = await bot.fetch_channel(channel_id)
            message = await thread.fetch_message(message_id)
            if is_sr(interaction.user) and interaction.user.id != requested_by:
                accepted_by = interaction.user
                r_profile = format_account_r_profile(game_uid, r_profile_list, title)
                #
                vote_channel = bot.get_channel(VOTE_CHANNEL)
                agree_users = []
                disagree_users = []
                all_images_to_show = r_profile_list[2]
                image_embeds = image_links_to_embeds(all_images_to_show)
                new_report_message = await vote_channel.send(content=f"Links edited for `{game_uid}`")
                new_report_thread = await new_report_message.create_thread(name=f"{game_uid}")
                await new_report_thread.send(f"<@&{ticket_ping}>")
                vote_msg = await new_report_thread.send(
                    content=f"Report accepted by {accepted_by.mention}.\nLink to thread: <#{channel_id}>\n\nAgree: 0\nDisagree: 0",
                    embed=r_profile, view=AccountVoteView())
                vote_channel_id = vote_msg.channel.id
                vote_message_id = vote_msg.id
                old_session = inprogresscol.find_one({"account_id": game_uid})
                if old_session:
                    inprogresscol.delete_one({"_id": old_session["_id"]})
                inprogresscol.insert_one({
                    "_id": vote_message_id,
                    "account_id": game_uid,
                    "requested_by": requested_by,
                    "channel_id": channel_id,
                    "message_id": interaction.message.id,
                    "r_profile_list": r_profile_list,
                    "title": title,
                    "reason": reason,
                    "vote_channel_id": vote_channel_id,
                    "accepted_by": accepted_by.id,
                    "agree_users": agree_users,
                    "disagree_users": disagree_users,
                })
                await new_report_thread.send(content=f"Links Proofs for `{game_uid}`", embeds=image_embeds)
                reason_embed = discord.Embed(title="Reason", description=reason)
                await new_report_thread.send(content=f"Reason for change(s)", embed=reason_embed)
                embeds = [r_profile, reason_embed]
                await old_message_edit_queue.put(
                    (message, {"content": "Report has been submitted for voting.", "embeds": embeds, "view": None}))
            else:
                await interaction.followup.send("You do not have permission to accept the report for voting.",
                                                ephemeral=True)
class AddLinksOnlyModal(discord.ui.Modal, title="Add Links"):
    links = discord.ui.TextInput(label="Add Links", placeholder="List links here and leave a newline between game UIDs.",
                                required=True, style=discord.TextStyle.long)
    def __init__(self):
        super().__init__(timeout=None)
    async def on_submit(self, interaction):
        await interaction.response.defer()
        session = inprogresscol.find_one({"_id": interaction.message.id})
        if session:
            channel_id = session["channel_id"]
            message_id = interaction.message.id
            r_profile_list = session["r_profile_list"]
            title = session["title"]
            reason = session["reason"]
            game_uid = session["account_id"]
            #
            original_links = r_profile_list[0] if r_profile_list[0] else []
            thread = await bot.fetch_channel(channel_id)
            message = await thread.fetch_message(message_id)
            links_input = self.links.value
            links_list = get_game_uid_list(links_input)
            valid_links = []
            for link in links_list:
                if link not in valid_links and link not in original_links and link != game_uid:
                    valid_links.append(link)
            if len(valid_links) != 0:
                r_profile_list[0] = original_links + valid_links
            inprogresscol.update_one(
                {"_id": interaction.message.id},
                {"$set": {"r_profile_list": r_profile_list}}
            )
            r_profile = format_account_r_profile(game_uid, r_profile_list, title)
            reason_embed = discord.Embed(title="Reason", description=reason)
            embeds = [r_profile, reason_embed]
            await message.edit(embeds=embeds, view=EditLinksOnlyView())
class RemoveLinksOnlyModal(discord.ui.Modal, title="Remove Links"):
    links = discord.ui.TextInput(label="Remove Links", placeholder="List links here and leave a newline between game UIDs.",
                                required=True, style=discord.TextStyle.long)
    def __init__(self):
        super().__init__(timeout=None)
    async def on_submit(self, interaction):
        await interaction.response.defer()
        session = inprogresscol.find_one({"_id": interaction.message.id})
        if session:
            channel_id = session["channel_id"]
            message_id = interaction.message.id
            r_profile_list = session["r_profile_list"]
            title = session["title"]
            reason = session["reason"]
            game_uid = session["account_id"]
            #
            original_links = r_profile_list[0] if r_profile_list[0] else []
            thread = await bot.fetch_channel(channel_id)
            message = await thread.fetch_message(message_id)
            links_input = self.links.value
            links_list = get_game_uid_list(links_input)
            valid_links = []
            for link in links_list:
                if link not in valid_links and link in original_links and link != game_uid:
                    valid_links.append(link)
            if len(valid_links) != 0:
                remaining_links = [element for element in original_links if element not in set(valid_links)]
                if len(remaining_links) != 0:
                    r_profile_list[0] = remaining_links
                else:
                    r_profile_list[0] = []
            #
            inprogresscol.update_one(
                {"_id": interaction.message.id},
                {"$set": {"r_profile_list": r_profile_list}}
            )
            r_profile = format_account_r_profile(game_uid, r_profile_list, title)
            reason_embed = discord.Embed(title="Reason", description=reason)
            embeds = [r_profile, reason_embed]
            await message.edit(embeds=embeds, view=EditLinksOnlyView())
class LinksReasonModal(discord.ui.Modal, title="Reason"):
    reason_input = discord.ui.TextInput(label="Reason", placeholder="Please explain the change(s) you have made.",
                                        required=True, style=discord.TextStyle.long)

    def __init__(self):
        super().__init__(timeout=None)

    async def on_submit(self, interaction):
        await interaction.response.defer()
        session = inprogresscol.find_one({"_id": interaction.message.id})
        if session:
            channel_id = session["channel_id"]
            message_id = interaction.message.id
            r_profile_list = session["r_profile_list"]
            title = session["title"]
            reason = session["reason"]
            game_uid = session["account_id"]
            thread = await bot.fetch_channel(channel_id)
            message = await thread.fetch_message(message_id)
            reason = str(self.reason_input.value)
            inprogresscol.update_one(
                {"_id": interaction.message.id},
                {"$set": {"reason": reason}}
            )
            r_profile = format_account_r_profile(game_uid, r_profile_list, title)
            reason_embed = discord.Embed(title="Reason", description=reason)
            embeds = [r_profile, reason_embed]
            await message.edit(embeds=embeds, view=EditLinksOnlyView())


# account appeal
class AccountAppealView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Add Links", style=discord.ButtonStyle.green, custom_id="accountappeal:addlinks")
    async def add_links_button(self, interaction, button):
        session = inprogresscol.find_one({"_id": interaction.message.id})
        if session:
            requested_by = session["requested_by"]
            if requested_by == interaction.user.id:
                await interaction.response.send_modal(AddLinksAppealModal())

    @discord.ui.button(label="Remove Links", style=discord.ButtonStyle.red, custom_id="accountappeal:removelinks")
    async def remove_links_button(self, interaction, button):
        session = inprogresscol.find_one({"_id": interaction.message.id})
        if session:
            requested_by = session["requested_by"]
            if requested_by == interaction.user.id:
                await interaction.response.send_modal(RemoveLinksAppealModal())

    @discord.ui.button(label="Add Links Proofs", style=discord.ButtonStyle.green, custom_id="accountappeal:addlinksproofs")
    async def add_links_proofs_button(self, interaction, button):
        session = inprogresscol.find_one({"_id": interaction.message.id})
        if session:
            requested_by = session["requested_by"]
            r_profile_list = session["r_profile_list"]
            if requested_by == interaction.user.id:
                image_links = []
                original_image_links = r_profile_list[2].copy()
                await interaction.response.send_message(
                    f"Please send the images you would like to upload (max {10 - len(r_profile_list[2])}).",
                    ephemeral=True)
                def check(m):
                    return m.author == interaction.user and m.channel == interaction.channel
                try:
                    msg = await bot.wait_for('message', check=check, timeout=120.0)
                except asyncio.TimeoutError:
                    await interaction.followup.send("You took too long to upload an image.", ephemeral=True)
                    return
                if msg.attachments:
                    for attachment in msg.attachments:
                        # Ensure the attachment is an image (optional check)
                        if attachment.content_type and attachment.content_type.startswith('image/'):
                            try:
                                # 1. Download the file data using aiohttp
                                async with aiohttp.ClientSession() as http_session:
                                    async with http_session.get(attachment.url) as resp:
                                        # For this example, we just send back the image URL and filename
                                        data = io.BytesIO(await resp.read())
                                        file = discord.File(data, filename=attachment.filename)
                                        channel_to_send = bot.get_channel(PROOFS_CHANNEL)
                                        sent_message = await channel_to_send.send(file=file)
                                        if sent_message.attachments:
                                            new_image_url = sent_message.attachments[0].url
                                            image_links.append(new_image_url)
                                            r_profile_list[2].append(new_image_url)
                            except Exception:
                                await msg.channel.send(f"An error occurred with file {attachment.filename}")
                if len(r_profile_list[2]) > 10:
                    await interaction.followup.send(
                        f"There are a total of {len(r_profile_list[2])} images, exceeding the max limit of 10. Please try again.")
                    r_profile_list[2] = original_image_links
                else:
                    inprogresscol.update_one(
                        {"_id": interaction.message.id},
                        {"$set": {"r_profile_list": r_profile_list}}
                    )
                    image_embeds = image_links_to_embeds(image_links)
                    await interaction.followup.send(f"Images received from {interaction.user.mention}.",
                                                    embeds=image_embeds)

    @discord.ui.button(label="Remove Links Proofs", style=discord.ButtonStyle.red, custom_id="accountappeal:removelinksproofs")
    async def remove_links_proofs_button(self, interaction, button):
        session = inprogresscol.find_one({"_id": interaction.message.id})
        if session:
            requested_by = session["requested_by"]
            r_profile_list = session["r_profile_list"]
            if requested_by == interaction.user.id:
                await interaction.response.send_message(
                    f"Please list image(s) you would like to remove, from 1 to {len(r_profile_list[2])}, with a space between each number.",
                    ephemeral=True)
                # Wait for a follow-up message from the user in the same channel
                def check(m):
                    # Check if the message is from the same user, in the same channel
                    return m.author == interaction.user and m.channel == interaction.channel
                try:
                    msg = await bot.wait_for('message', check=check, timeout=120.0)
                except asyncio.TimeoutError:
                    await interaction.followup.send("You took too long to respond.", ephemeral=True)
                    return
                try:
                    to_remove = msg.content.split()
                    indices_to_remove = []
                    for i in to_remove:
                        indices_to_remove.append(int(i) - 1)
                    indices_to_remove = set(indices_to_remove)
                except Exception:
                    await interaction.followup.send("Invalid response. Please try again.", ephemeral=True)
                else:
                    images_removed = []
                    for i in indices_to_remove:
                        if 0 <= i < len(r_profile_list[2]):
                            images_removed.append(r_profile_list[2][i])
                    r_profile_list[2] = [value for index, value in enumerate(r_profile_list[2]) if
                                         index not in indices_to_remove]
                    inprogresscol.update_one(
                        {"_id": interaction.message.id},
                        {"$set": {"r_profile_list": r_profile_list}}
                    )
                    image_embeds = image_links_to_embeds(images_removed)
                    await interaction.followup.send(f"Images removed by {interaction.user.mention}.",
                                                    embeds=image_embeds)

    @discord.ui.button(label="Show Links Proofs", style=discord.ButtonStyle.grey, custom_id="accountappeal:showlinksproofs")
    async def show_links_proofs_button(self, interaction, button):
        await interaction.response.defer()
        #
        session = inprogresscol.find_one({"_id": interaction.message.id})
        if session:
            requested_by = session["requested_by"]
            r_profile_list = session["r_profile_list"]
            game_uid = session["account_id"]
        #
            if requested_by == interaction.user.id or is_sr(interaction.user):
                image_embeds = image_links_to_embeds(r_profile_list[2])
                await interaction.followup.send(f"Links Proofs for `{game_uid}`",
                                                embeds=image_embeds, ephemeral=True)

    @discord.ui.button(label="Reason", style=discord.ButtonStyle.primary, custom_id="accountappeal:reason")
    async def reason_button(self, interaction, button):
        #
        session = inprogresscol.find_one({"_id": interaction.message.id})
        if session:
            requested_by = session["requested_by"]
            #
            if requested_by == interaction.user.id:
                await interaction.response.send_modal(AccountAppealReasonModal())

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.grey, custom_id="accountappeal:cancel")
    async def cancel_button(self, interaction, button):
        await interaction.response.defer()
        session = inprogresscol.find_one({"_id": interaction.message.id})
        if session:
            requested_by = session["requested_by"]
            channel_id = session["channel_id"]
            message_id = interaction.message.id
            thread = await bot.fetch_channel(channel_id)
            message = await thread.fetch_message(message_id)
            if requested_by == interaction.user.id or is_sr(interaction.user):
                inprogresscol.delete_one({"_id": interaction.message.id})
                await message.edit(content=f"**Cancelled by {interaction.user.mention}.**", view=None)

    @discord.ui.button(label="Accept", style=discord.ButtonStyle.grey, custom_id="accountappeal:accept")
    async def accept_button(self, interaction, button):
        await interaction.response.defer()
        #
        session = inprogresscol.find_one({"_id": interaction.message.id})
        if session:
            requested_by = session["requested_by"]
            channel_id = session["channel_id"]
            message_id = interaction.message.id
            r_profile_list = session["r_profile_list"]
            add_case_list = session["add_case_list"]
            title = session["title"]
            case_title = session["case_title"]
            reason = session["reason"]
            game_uid = session["account_id"]
            thread = await bot.fetch_channel(channel_id)
            message = await thread.fetch_message(message_id)
            if is_sr(interaction.user) and interaction.user.id != requested_by:
                accepted_by = interaction.user
                r_profile = format_account_r_profile(game_uid, r_profile_list, title)
                add_case = format_account_add_case(add_case_list, case_title)
                reason_embed = discord.Embed(title="Reason", colour=0x1DCCA9, description=reason)
                embeds = [r_profile, add_case, reason_embed]
                #
                vote_channel = bot.get_channel(VOTE_CHANNEL)
                agree_users = []
                disagree_users = []
                links_proofs_embeds = image_links_to_embeds(r_profile_list[2])
                proofs_embeds = image_links_to_embeds(add_case_list["proofs"])
                add_case_list = [add_case_list]
                new_report_message = await vote_channel.send(content=f"Appeal on `{game_uid}`")
                new_report_thread = await new_report_message.create_thread(name=f"{game_uid}")
                await new_report_thread.send(f"<@&{ticket_ping}>")
                vote_msg = await new_report_thread.send(
                    content=f"Appeal accepted by <@{accepted_by.id}>.\nLink to thread: <#{channel_id}>\n\nAgree: 0\nDisagree: 0",
                    embeds=embeds, view=AccountVoteView())
                vote_channel_id = vote_msg.channel.id
                vote_message_id = vote_msg.id
                old_session = inprogresscol.find_one({"account_id": game_uid})
                if old_session:
                    inprogresscol.delete_one({"_id": old_session["_id"]})
                inprogresscol.insert_one({
                    "_id": vote_message_id,
                    "account_id": game_uid,
                    "requested_by": requested_by,
                    "channel_id": channel_id,
                    "message_id": interaction.message.id,
                    "r_profile_list": r_profile_list,
                    "add_case_list": add_case_list,
                    "title": title,
                    "case_title": case_title,
                    "reason": reason,
                    "vote_channel_id": vote_channel_id,
                    "accepted_by": accepted_by.id,
                    "agree_users": agree_users,
                    "disagree_users": disagree_users,
                })
                await new_report_thread.send(content=f"Links Proofs for `{game_uid}`", embeds=links_proofs_embeds)
                await new_report_thread.send(content=f"Proofs for `{game_uid}`", embeds=proofs_embeds)
                await old_message_edit_queue.put(
                    (message, {"content": "Appeal has been submitted for voting.", "embeds": embeds, "view": None}))
            else:
                await interaction.followup.send("You do not have permission to accept the report for voting.",
                                                ephemeral=True)
class AddLinksAppealModal(discord.ui.Modal, title="Add Links"):
    links = discord.ui.TextInput(label="Add Links", placeholder="List links here and leave a newline between game UIDs.",
                                required=True, style=discord.TextStyle.long)

    def __init__(self):
        super().__init__(timeout=None)

    async def on_submit(self, interaction):
        await interaction.response.defer()
        #
        session = inprogresscol.find_one({"_id": interaction.message.id})
        if session:
            channel_id = session["channel_id"]
            message_id = interaction.message.id
            r_profile_list = session["r_profile_list"]
            add_case_list = session["add_case_list"]
            title = session["title"]
            case_title = session["case_title"]
            reason = session["reason"]
            game_uid = session["account_id"]
            #
            original_links = r_profile_list[0] if r_profile_list[0] else []
            thread = await bot.fetch_channel(channel_id)
            message = await thread.fetch_message(message_id)
            links_input = self.links.value
            links_list = get_game_uid_list(links_input)
            valid_links = []
            for link in links_list:
                if link not in valid_links and link not in original_links and link != game_uid:
                    valid_links.append(link)
            if len(valid_links) != 0:
                r_profile_list[0] = original_links + valid_links
            #
            inprogresscol.update_one(
                {"_id": interaction.message.id},
                {"$set": {"r_profile_list": r_profile_list}}
            )
            #
            r_profile = format_account_r_profile(game_uid, r_profile_list, title)
            reason_embed = discord.Embed(title="Reason", colour=0x1DCCA9, description=reason)
            add_case = format_account_add_case(add_case_list, case_title)
            embeds = [r_profile, add_case, reason_embed]
            await message.edit(embeds=embeds, view=AccountAppealView())
class RemoveLinksAppealModal(discord.ui.Modal, title="Remove Links"):
    links = discord.ui.TextInput(label="Remove Links", placeholder="List links here and leave a newline between game UIDs.",
                                required=True, style=discord.TextStyle.long)

    def __init__(self):
        super().__init__(timeout=None)

    async def on_submit(self, interaction):
        await interaction.response.defer()
        #
        session = inprogresscol.find_one({"_id": interaction.message.id})
        if session:
            channel_id = session["channel_id"]
            message_id = interaction.message.id
            r_profile_list = session["r_profile_list"]
            add_case_list = session["add_case_list"]
            title = session["title"]
            case_title = session["case_title"]
            reason = session["reason"]
            game_uid = session["account_id"]
            #
            original_links = r_profile_list[0] if r_profile_list[0] else []
            thread = await bot.fetch_channel(channel_id)
            message = await thread.fetch_message(message_id)
            links_input = self.links.value
            links_list = get_game_uid_list(links_input)
            valid_links = []
            for link in links_list:
                if link not in valid_links and link in original_links and link != game_uid:
                    valid_links.append(link)
            if len(valid_links) != 0:
                remaining_links = [element for element in original_links if element not in set(valid_links)]
                if len(remaining_links) != 0:
                    r_profile_list[0] = remaining_links
                else:
                    r_profile_list[0] = []
            #
            inprogresscol.update_one(
                {"_id": interaction.message.id},
                {"$set": {"r_profile_list": r_profile_list}}
            )
            #
            r_profile = format_account_r_profile(game_uid, r_profile_list, title)
            reason_embed = discord.Embed(title="Reason", colour=0x1DCCA9, description=reason)
            add_case = format_account_add_case(add_case_list, case_title)
            embeds = [r_profile, add_case, reason_embed]
            await message.edit(embeds=embeds, view=AccountAppealView())
class AccountAppealReasonModal(discord.ui.Modal, title="Reason"):
    reason_input = discord.ui.TextInput(label="Reason", placeholder="Please explain the appeal you have made.",
                                        required=True, style=discord.TextStyle.long)

    def __init__(self):
        super().__init__(timeout=None)

    async def on_submit(self, interaction):
        await interaction.response.defer()
        #
        session = inprogresscol.find_one({"_id": interaction.message.id})
        if session:
            channel_id = session["channel_id"]
            message_id = interaction.message.id
            r_profile_list = session["r_profile_list"]
            add_case_list = session["add_case_list"]
            title = session["title"]
            case_title = session["case_title"]
            game_uid = session["account_id"]
            #
            thread = await bot.fetch_channel(channel_id)
            message = await thread.fetch_message(message_id)
            reason = str(self.reason_input.value)
            inprogresscol.update_one(
                {"_id": interaction.message.id},
                {"$set": {"reason": reason}}
            )
            r_profile = format_account_r_profile(game_uid, r_profile_list, title)
            reason_embed = discord.Embed(title="Reason", colour=0x1DCCA9, description=reason)
            add_case = format_account_add_case(add_case_list, case_title)
            embeds = [r_profile, add_case, reason_embed]
            await message.edit(embeds=embeds, view=AccountAppealView())


# account add report
class AddReportLinksView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(emoji="<:rightarrow:1458096774521553038>", style=discord.ButtonStyle.grey, custom_id="addreportlinks:next")
    async def next_button(self, interaction, button):
        await interaction.response.defer()
        #
        session = inprogresscol.find_one({"_id": interaction.message.id})
        if session:
            requested_by = session["requested_by"]
            channel_id = session["channel_id"]
            message_id = interaction.message.id
            r_profile_list = session["r_profile_list"]
            add_case_list = session["add_case_list"]
            title = session["title"]
            case_title = session["case_title"]
            game_uid = session["account_id"]
            #
            thread = await bot.fetch_channel(channel_id)
            message = await thread.fetch_message(message_id)
            if requested_by == interaction.user.id or is_sr(interaction.user):
                r_profile = format_account_r_profile(game_uid, r_profile_list, title)
                add_case = format_account_add_case(add_case_list, case_title)
                embeds = [r_profile, add_case]
                await message.edit(embeds=embeds, view=AddReportAccountTagsView())

    @discord.ui.button(label="Add Links", style=discord.ButtonStyle.green, custom_id="addreportlinks:addlinks")
    async def add_links_button(self, interaction, button):
        #
        session = inprogresscol.find_one({"_id": interaction.message.id})
        if session:
            requested_by = session["requested_by"]
            #
            if requested_by == interaction.user.id:
                await interaction.response.send_modal(AddLinksModal())

    @discord.ui.button(label="Remove Links", style=discord.ButtonStyle.red, custom_id="addreportlinks:removelinks")
    async def remove_links_button(self, interaction, button):
        #
        session = inprogresscol.find_one({"_id": interaction.message.id})
        if session:
            requested_by = session["requested_by"]
            #
            if requested_by == interaction.user.id:
                await interaction.response.send_modal(RemoveLinksModal())

    @discord.ui.button(label="Add Links Proofs", style=discord.ButtonStyle.green, custom_id="addreportlinks:addlinksproofs")
    async def add_links_proofs_button(self, interaction, button):
        #
        session = inprogresscol.find_one({"_id": interaction.message.id})
        if session:
            requested_by = session["requested_by"]
            r_profile_list = session["r_profile_list"]
            #
            if requested_by == interaction.user.id:
                image_links = []
                original_image_links = r_profile_list[2].copy()
                await interaction.response.send_message(
                    f"Please send the images you would like to upload (max {10 - len(r_profile_list[2])}).",
                    ephemeral=True)

                # Wait for a follow-up message from the user in the same channel
                def check(m):
                    # Check if the message is from the same user, in the same channel, and has an attachment
                    return m.author == interaction.user and m.channel == interaction.channel

                try:
                    msg = await bot.wait_for('message', check=check, timeout=120.0)
                except asyncio.TimeoutError:
                    await interaction.followup.send("You took too long to upload an image.", ephemeral=True)
                    return
                if msg.attachments:
                    for attachment in msg.attachments:
                        # Ensure the attachment is an image (optional check)
                        if attachment.content_type and attachment.content_type.startswith('image/'):
                            try:
                                # 1. Download the file data using aiohttp
                                async with aiohttp.ClientSession() as http_session:
                                    async with http_session.get(attachment.url) as resp:
                                        # For this example, we just send back the image URL and filename
                                        data = io.BytesIO(await resp.read())
                                        file = discord.File(data, filename=attachment.filename)
                                        channel_to_send = bot.get_channel(PROOFS_CHANNEL)
                                        sent_message = await channel_to_send.send(file=file)
                                        if sent_message.attachments:
                                            new_image_url = sent_message.attachments[0].url
                                            image_links.append(new_image_url)
                                            r_profile_list[2].append(new_image_url)
                            except Exception:
                                await msg.channel.send(f"An error occurred with file {attachment.filename}")
                if len(r_profile_list[2]) > 10:
                    await interaction.followup.send(
                        f"There are a total of {len(r_profile_list[2])} images, exceeding the max limit of 10. Please try again.")
                    r_profile_list[2] = original_image_links
                else:
                    #
                    inprogresscol.update_one(
                        {"_id": interaction.message.id},
                        {"$set": {"r_profile_list": r_profile_list}}
                    )
                    #
                    image_embeds = image_links_to_embeds(image_links)
                    await interaction.followup.send(f"Images received from {interaction.user.mention}.",
                                                    embeds=image_embeds)

    @discord.ui.button(label="Remove Links Proofs", style=discord.ButtonStyle.red, custom_id="addreportlinks:removelinksproofs")
    async def remove_links_proofs_button(self, interaction, button):
        #
        session = inprogresscol.find_one({"_id": interaction.message.id})
        if session:
            requested_by = session["requested_by"]
            r_profile_list = session["r_profile_list"]
            #
            if requested_by == interaction.user.id:
                await interaction.response.send_message(
                    f"Please list image(s) you would like to remove, from 1 to {len(r_profile_list[2])}, with a space between each number.",
                    ephemeral=True)

                # Wait for a follow-up message from the user in the same channel
                def check(m):
                    # Check if the message is from the same user, in the same channel
                    return m.author == interaction.user and m.channel == interaction.channel

                try:
                    msg = await bot.wait_for('message', check=check, timeout=120.0)
                except asyncio.TimeoutError:
                    await interaction.followup.send("You took too long to respond.", ephemeral=True)
                    return
                try:
                    to_remove = msg.content.split()
                    indices_to_remove = []
                    for i in to_remove:
                        indices_to_remove.append(int(i) - 1)
                    indices_to_remove = set(indices_to_remove)
                except Exception:
                    await interaction.followup.send("Invalid response. Please try again.", ephemeral=True)
                else:
                    images_removed = []
                    for i in indices_to_remove:
                        if 0 <= i < len(r_profile_list[2]):
                            images_removed.append(r_profile_list[2][i])
                    r_profile_list[2] = [value for index, value in enumerate(r_profile_list[2]) if
                                         index not in indices_to_remove]
                    #
                    inprogresscol.update_one(
                        {"_id": interaction.message.id},
                        {"$set": {"r_profile_list": r_profile_list}}
                    )
                    #
                    image_embeds = image_links_to_embeds(images_removed)
                    await interaction.followup.send(f"Images removed by {interaction.user.mention}.",
                                                    embeds=image_embeds)

    @discord.ui.button(label="Show Links Proofs", style=discord.ButtonStyle.grey, custom_id="addreportlinks:showlinksproofs")
    async def show_links_proofs_button(self, interaction, button):
        await interaction.response.defer()
        #
        session = inprogresscol.find_one({"_id": interaction.message.id})
        if session:
            requested_by = session["requested_by"]
            r_profile_list = session["r_profile_list"]
            game_uid = session["account_id"]
            #
            if requested_by == interaction.user.id or is_sr(interaction.user):
                image_embeds = image_links_to_embeds(r_profile_list[2])
                await interaction.followup.send(f"Links Proofs for `{game_uid}`",
                                                embeds=image_embeds, ephemeral=True)
class AddLinksModal(discord.ui.Modal, title="Add Links"):
    links = discord.ui.TextInput(label="Add Links", placeholder="List links here and leave a newline between game UIDs.",
                                required=True, style=discord.TextStyle.long)

    def __init__(self):
        super().__init__(timeout=None)

    async def on_submit(self, interaction):
        await interaction.response.defer()
        #
        session = inprogresscol.find_one({"_id": interaction.message.id})
        if session:
            channel_id = session["channel_id"]
            message_id = interaction.message.id
            r_profile_list = session["r_profile_list"]
            add_case_list = session["add_case_list"]
            title = session["title"]
            case_title = session["case_title"]
            game_uid = session["account_id"]
            #
            original_links = r_profile_list[0] if r_profile_list[0] else []
            thread = await bot.fetch_channel(channel_id)
            message = await thread.fetch_message(message_id)
            links_input = self.links.value
            links_list = get_game_uid_list(links_input)
            valid_links = []
            for link in links_list:
                if link not in valid_links and link not in original_links and link != game_uid:
                    valid_links.append(link)
            if len(valid_links) != 0:
                r_profile_list[0] = original_links + valid_links
            #
            inprogresscol.update_one(
                {"_id": interaction.message.id},
                {"$set": {"r_profile_list": r_profile_list}}
            )
            #
            r_profile = format_account_r_profile(game_uid, r_profile_list, title)
            add_case = format_account_add_case(add_case_list, case_title)
            embeds = [r_profile, add_case]
            await message.edit(embeds=embeds, view=AddReportLinksView())
class RemoveLinksModal(discord.ui.Modal, title="Remove Links"):
    links = discord.ui.TextInput(label="Remove Links", placeholder="List links here and leave a newline between game UIDs.",
                                required=True, style=discord.TextStyle.long)

    def __init__(self):
        super().__init__(timeout=None)

    async def on_submit(self, interaction):
        await interaction.response.defer()
        #
        session = inprogresscol.find_one({"_id": interaction.message.id})
        if session:
            channel_id = session["channel_id"]
            message_id = interaction.message.id
            r_profile_list = session["r_profile_list"]
            add_case_list = session["add_case_list"]
            title = session["title"]
            case_title = session["case_title"]
            game_uid = session["account_id"]
            #
            original_links = r_profile_list[0] if r_profile_list[0] else []
            thread = await bot.fetch_channel(channel_id)
            message = await thread.fetch_message(message_id)
            links_input = self.links.value
            links_list = get_game_uid_list(links_input)
            valid_links = []
            for link in links_list:
                if link not in valid_links and link in original_links and link != game_uid:
                    valid_links.append(link)
            if len(valid_links) != 0:
                remaining_links = [element for element in original_links if element not in set(valid_links)]
                if len(remaining_links) != 0:
                    r_profile_list[0] = remaining_links
                else:
                    r_profile_list[0] = []
            #
            inprogresscol.update_one(
                {"_id": interaction.message.id},
                {"$set": {"r_profile_list": r_profile_list}}
            )
            #
            r_profile = format_account_r_profile(game_uid, r_profile_list, title)
            add_case = format_account_add_case(add_case_list, case_title)
            embeds = [r_profile, add_case]
            await message.edit(embeds=embeds, view=AddReportLinksView())

class AddReportAccountTagsView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(emoji="<:leftarrow:1458096658062770176>", style=discord.ButtonStyle.grey, custom_id="addreportaccounttags:prev")
    async def prev_button(self, interaction, button):
        await interaction.response.defer()
        #
        session = inprogresscol.find_one({"_id": interaction.message.id})
        if session:
            requested_by = session["requested_by"]
            channel_id = session["channel_id"]
            message_id = interaction.message.id
            r_profile_list = session["r_profile_list"]
            add_case_list = session["add_case_list"]
            title = session["title"]
            case_title = session["case_title"]
            game_uid = session["account_id"]
            #
            thread = await bot.fetch_channel(channel_id)
            message = await thread.fetch_message(message_id)
            if requested_by == interaction.user.id or is_sr(interaction.user):
                r_profile = format_account_r_profile(game_uid, r_profile_list, title)
                add_case = format_account_add_case(add_case_list, case_title)
                embeds = [r_profile, add_case]
                await message.edit(embeds=embeds, view=AddReportLinksView())

    @discord.ui.button(emoji="<:rightarrow:1458096774521553038>", style=discord.ButtonStyle.grey, custom_id="addreportaccounttags:next")
    async def next_button(self, interaction, button):
        await interaction.response.defer()
        #
        session = inprogresscol.find_one({"_id": interaction.message.id})
        if session:
            requested_by = session["requested_by"]
            channel_id = session["channel_id"]
            message_id = interaction.message.id
            r_profile_list = session["r_profile_list"]
            add_case_list = session["add_case_list"]
            title = session["title"]
            case_title = session["case_title"]
            game_uid = session["account_id"]
            #
            thread = await bot.fetch_channel(channel_id)
            message = await thread.fetch_message(message_id)
            if requested_by == interaction.user.id or is_sr(interaction.user):
                r_profile = format_account_r_profile(game_uid, r_profile_list, title)
                add_case = format_account_add_case(add_case_list, case_title)
                embeds = [r_profile, add_case]
                await message.edit(embeds=embeds, view=AddReportRelatedUsersView())

    @discord.ui.select(options=account_tag_options, placeholder="Select Tag(s)...", custom_id="addreportaccounttags:select",
                       max_values=len(account_tag_options))
    async def select_callback(self, interaction, select):
        await interaction.response.defer()
        #
        session = inprogresscol.find_one({"_id": interaction.message.id})
        if session:
            requested_by = session["requested_by"]
            channel_id = session["channel_id"]
            message_id = interaction.message.id
            r_profile_list = session["r_profile_list"]
            add_case_list = session["add_case_list"]
            title = session["title"]
            game_uid = session["account_id"]
            #
            thread = await bot.fetch_channel(channel_id)
            message = await thread.fetch_message(message_id)
            if requested_by == interaction.user.id:
                sorted_tags = sort_account_tags(self.select_callback.values)
                case_title = sorted_tags[0]
                tags = selected_string(sorted_tags)
                add_case_list["tags"] = tags
                #
                account_query = {"_id": str(game_uid)}
                account_profile = accountscol.find_one(account_query)
                old_r_profile_list = account_profile["r_profile_list"]
                #
                existing_tags_list = old_r_profile_list[1].split(", ")
                existing_tags_list.insert(0, title)
                for tag in sorted_tags:
                    if tag not in existing_tags_list:
                        existing_tags_list.append(tag)
                sorted_tags = sort_account_tags(existing_tags_list)
                #
                if "Recovered Account" in tags:
                    title = "Recovered Account"
                    all_other_tags = selected_string([tag for tag in sorted_tags if tag != "Recovered Account"])
                else:
                    title = sorted_tags[0]
                    all_other_tags = selected_string(sorted_tags[1:])
                r_profile_list[1] = all_other_tags
                #
                inprogresscol.update_one(
                    {"_id": interaction.message.id},
                    {"$set": {
                        "r_profile_list": r_profile_list,
                        "add_case_list": add_case_list,
                        "title": title,
                        "case_title": case_title, }
                    })
                #
                r_profile = format_account_r_profile(game_uid, r_profile_list, title)
                add_case = format_account_add_case(add_case_list, case_title)
                embeds = [r_profile, add_case]
                await message.edit(embeds=embeds)

class AddReportRelatedUsersView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(emoji="<:leftarrow:1458096658062770176>", style=discord.ButtonStyle.grey, custom_id="addreportrelatedusers:prev")
    async def prev_button(self, interaction, button):
        await interaction.response.defer()
        #
        session = inprogresscol.find_one({"_id": interaction.message.id})
        if session:
            requested_by = session["requested_by"]
            channel_id = session["channel_id"]
            message_id = interaction.message.id
            r_profile_list = session["r_profile_list"]
            add_case_list = session["add_case_list"]
            title = session["title"]
            case_title = session["case_title"]
            game_uid = session["account_id"]
            #
            thread = await bot.fetch_channel(channel_id)
            message = await thread.fetch_message(message_id)
            if requested_by == interaction.user.id or is_sr(interaction.user):
                r_profile = format_account_r_profile(game_uid, r_profile_list, title)
                add_case = format_account_add_case(add_case_list, case_title)
                embeds = [r_profile, add_case]
                await message.edit(embeds=embeds, view=AddReportAccountTagsView())

    @discord.ui.button(emoji="<:rightarrow:1458096774521553038>", style=discord.ButtonStyle.grey, custom_id="addreportrelatedusers:next")
    async def next_button(self, interaction, button):
        await interaction.response.defer()
        #
        session = inprogresscol.find_one({"_id": interaction.message.id})
        if session:
            requested_by = session["requested_by"]
            channel_id = session["channel_id"]
            message_id = interaction.message.id
            r_profile_list = session["r_profile_list"]
            add_case_list = session["add_case_list"]
            title = session["title"]
            case_title = session["case_title"]
            game_uid = session["account_id"]
            #
            thread = await bot.fetch_channel(channel_id)
            message = await thread.fetch_message(message_id)
            if requested_by == interaction.user.id or is_sr(interaction.user):
                r_profile = format_account_r_profile(game_uid, r_profile_list, title)
                add_case = format_account_add_case(add_case_list, case_title)
                embeds = [r_profile, add_case]
                await message.edit(embeds=embeds, view=AddReportAccountReasonView())
    @discord.ui.button(
        label="Related Users",
        style=discord.ButtonStyle.green,
        custom_id="addreportrelatedusers:input"
    )
    async def related_users_button(self, interaction, button):
        session = inprogresscol.find_one({"_id": interaction.message.id})
        if session and session["requested_by"] == interaction.user.id:
            await interaction.response.send_modal(AddReportRelatedUsersModal())


class AddReportRelatedUsersModal(
    discord.ui.Modal,
    title="Related Users"
):
    related_users = discord.ui.TextInput(
        label="Related Users",
        placeholder="List user IDs separated by spaces.",
        required=True,
        style=discord.TextStyle.paragraph
    )

    def __init__(self):
        super().__init__(timeout=None)

    async def on_submit(self, interaction):
        await interaction.response.defer()
        session = inprogresscol.find_one({"_id": interaction.message.id})
        if session:
            requested_by = session["requested_by"]
            channel_id = session["channel_id"]
            message_id = interaction.message.id
            r_profile_list = session["r_profile_list"]
            add_case_list = session["add_case_list"]
            title = session["title"]
            case_title = session["case_title"]
            game_uid = session["account_id"]
            thread = await bot.fetch_channel(session["channel_id"])
            message = await thread.fetch_message(interaction.message.id)
            ids = self.related_users.value.split()
            valid_users = []
            for id in ids:
                try:
                    fetched = await bot.fetch_user(int(id))
                except Exception:
                    continue
                if fetched.id not in valid_users:
                    valid_users.append(fetched.id)
            r_profile_list = session["r_profile_list"]
            if len(valid_users):
                add_case_list["related_users"] = related_users_string(valid_users)
            else:
                add_case_list["related_users"] = ""
            inprogresscol.update_one(
                {"_id": interaction.message.id},
                {"$set": {"add_case_list": add_case_list}}
            )
            r_profile = format_account_r_profile(game_uid, r_profile_list, title)
            add_case = format_account_add_case(add_case_list, case_title)
            embeds = [r_profile, add_case]
            await message.edit(embeds=embeds, view=AddReportRelatedUsersView())

class AddReportAccountReasonView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(emoji="<:leftarrow:1458096658062770176>", style=discord.ButtonStyle.grey, custom_id="addreportaccountreason:prev")
    async def prev_button(self, interaction, button):
        await interaction.response.defer()
        #
        session = inprogresscol.find_one({"_id": interaction.message.id})
        if session:
            requested_by = session["requested_by"]
            channel_id = session["channel_id"]
            message_id = interaction.message.id
            r_profile_list = session["r_profile_list"]
            add_case_list = session["add_case_list"]
            title = session["title"]
            case_title = session["case_title"]
            game_uid = session["account_id"]
            #
            thread = await bot.fetch_channel(channel_id)
            message = await thread.fetch_message(message_id)
            if requested_by == interaction.user.id or is_sr(interaction.user):
                r_profile = format_account_r_profile(game_uid, r_profile_list, title)
                add_case = format_account_add_case(add_case_list, case_title)
                embeds = [r_profile, add_case]
                await message.edit(embeds=embeds, view=AddReportRelatedUsersView())

    @discord.ui.button(emoji="<:rightarrow:1458096774521553038>", style=discord.ButtonStyle.grey, custom_id="addreportaccountreason:next")
    async def next_button(self, interaction, button):
        await interaction.response.defer()
        #
        session = inprogresscol.find_one({"_id": interaction.message.id})
        if session:
            requested_by = session["requested_by"]
            channel_id = session["channel_id"]
            message_id = interaction.message.id
            r_profile_list = session["r_profile_list"]
            add_case_list = session["add_case_list"]
            title = session["title"]
            case_title = session["case_title"]
            game_uid = session["account_id"]
            #
            thread = await bot.fetch_channel(channel_id)
            message = await thread.fetch_message(message_id)
            if requested_by == interaction.user.id or is_sr(interaction.user):
                r_profile = format_account_r_profile(game_uid, r_profile_list, title)
                add_case = format_account_add_case(add_case_list, case_title)
                embeds = [r_profile, add_case]
                await message.edit(embeds=embeds, view=AddReportAccountContributorView())

    @discord.ui.button(label="Reason", style=discord.ButtonStyle.green, custom_id="addreportaccountreason:input")
    async def reason_button(self, interaction, button):
        #
        session = inprogresscol.find_one({"_id": interaction.message.id})
        if session:
            requested_by = session["requested_by"]
            #
            if requested_by == interaction.user.id:
                await interaction.response.send_modal(AddReportAccountReasonModal())
class AddReportAccountReasonModal(discord.ui.Modal, title="Reason"):
    reason = discord.ui.TextInput(label="Reason", placeholder="Input reason here.", required=True,
                                  style=discord.TextStyle.long)

    def __init__(self):
        super().__init__(timeout=None)

    async def on_submit(self, interaction):
        await interaction.response.defer()
        #
        session = inprogresscol.find_one({"_id": interaction.message.id})
        if session:
            channel_id = session["channel_id"]
            message_id = interaction.message.id
            r_profile_list = session["r_profile_list"]
            add_case_list = session["add_case_list"]
            title = session["title"]
            case_title = session["case_title"]
            game_uid = session["account_id"]
            #
            thread = await bot.fetch_channel(channel_id)
            message = await thread.fetch_message(message_id)
            reason = re.sub(r"\s+", " ", self.reason.value)
            add_case_list["reason"] = reason
            #
            inprogresscol.update_one(
                {"_id": interaction.message.id},
                {"$set": {"add_case_list": add_case_list}},
            )
            #
            r_profile = format_account_r_profile(game_uid, r_profile_list, title)
            add_case = format_account_add_case(add_case_list, case_title)
            embeds = [r_profile, add_case]
            await message.edit(embeds=embeds, view=AddReportAccountReasonView())

class AddReportAccountContributorView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(emoji="<:leftarrow:1458096658062770176>", style=discord.ButtonStyle.grey,
                       custom_id="addreportaccountcontributor:prev")
    async def prev_button(self, interaction, button):
        await interaction.response.defer()
        #
        session = inprogresscol.find_one({"_id": interaction.message.id})
        if session:
            requested_by = session["requested_by"]
            channel_id = session["channel_id"]
            message_id = interaction.message.id
            r_profile_list = session["r_profile_list"]
            add_case_list = session["add_case_list"]
            title = session["title"]
            case_title = session["case_title"]
            game_uid = session["account_id"]
            #
            thread = await bot.fetch_channel(channel_id)
            message = await thread.fetch_message(message_id)
            if requested_by == interaction.user.id or is_sr(interaction.user):
                r_profile = format_account_r_profile(game_uid, r_profile_list, title)
                add_case = format_account_add_case(add_case_list, case_title)
                embeds = [r_profile, add_case]
                await message.edit(embeds=embeds, view=AddReportAccountReasonView())

    @discord.ui.button(emoji="<:rightarrow:1458096774521553038>", style=discord.ButtonStyle.grey,
                       custom_id="addreportaccountcontributor:next")
    async def next_button(self, interaction, button):
        await interaction.response.defer()
        #
        session = inprogresscol.find_one({"_id": interaction.message.id})
        if session:
            requested_by = session["requested_by"]
            channel_id = session["channel_id"]
            message_id = interaction.message.id
            r_profile_list = session["r_profile_list"]
            add_case_list = session["add_case_list"]
            title = session["title"]
            case_title = session["case_title"]
            game_uid = session["account_id"]
            #
            thread = await bot.fetch_channel(channel_id)
            message = await thread.fetch_message(message_id)
            if requested_by == interaction.user.id or is_sr(interaction.user):
                r_profile = format_account_r_profile(game_uid, r_profile_list, title)
                add_case = format_account_add_case(add_case_list, case_title)
                embeds = [r_profile, add_case]
                await message.edit(embeds=embeds, view=AddReportAccountProofsView())

    @discord.ui.button(label="Contributor", style=discord.ButtonStyle.green, custom_id="addreportaccountcontributor:input")
    async def contributor_button(self, interaction, button):
        #
        session = inprogresscol.find_one({"_id": interaction.message.id})
        if session:
            requested_by = session["requested_by"]
            #
            if requested_by == interaction.user.id:
                await interaction.response.send_modal(AddReportAccountContributorModal())
class AddReportAccountContributorModal(discord.ui.Modal, title="Contributor"):
    contributor = discord.ui.TextInput(label="Contributor",
                                       placeholder="Account ID / n if Anonymous.", required=True,
                                       style=discord.TextStyle.short)

    def __init__(self):
        super().__init__(timeout=None)

    async def on_submit(self, interaction):
        await interaction.response.defer()
        #
        session = inprogresscol.find_one({"_id": interaction.message.id})
        if session:
            channel_id = session["channel_id"]
            message_id = interaction.message.id
            r_profile_list = session["r_profile_list"]
            add_case_list = session["add_case_list"]
            title = session["title"]
            case_title = session["case_title"]
            game_uid = session["account_id"]
            #
            thread = await bot.fetch_channel(channel_id)
            message = await thread.fetch_message(message_id)
            contributor_input = self.contributor.value
            if contributor_input.lower() == "n":
                add_case_list["contributor"] = "Anonymous"
            else:
                try:
                    contributor_id = await bot.fetch_user(int(contributor_input))
                except Exception:
                    add_case_list["contributor"] = ""
                else:
                    add_case_list["contributor"] = f"<@{contributor_id.id}>"
            #
            inprogresscol.update_one(
                {"_id": interaction.message.id},
                {"$set": {"add_case_list": add_case_list}},
            )
            #
            r_profile = format_account_r_profile(game_uid, r_profile_list, title)
            add_case = format_account_add_case(add_case_list, case_title)
            embeds = [r_profile, add_case]
            await message.edit(embeds=embeds,
                               view=AddReportAccountContributorView())

class AddReportAccountProofsView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(emoji="<:leftarrow:1458096658062770176>", style=discord.ButtonStyle.grey, custom_id="addreportaccountproofs:prev")
    async def prev_button(self, interaction, button):
        await interaction.response.defer()
        #
        session = inprogresscol.find_one({"_id": interaction.message.id})
        if session:
            requested_by = session["requested_by"]
            channel_id = session["channel_id"]
            message_id = interaction.message.id
            r_profile_list = session["r_profile_list"]
            add_case_list = session["add_case_list"]
            title = session["title"]
            case_title = session["case_title"]
            game_uid = session["account_id"]
            #
            thread = await bot.fetch_channel(channel_id)
            message = await thread.fetch_message(message_id)
            if requested_by == interaction.user.id or is_sr(interaction.user):
                r_profile = format_account_r_profile(game_uid, r_profile_list, title)
                add_case = format_account_add_case(add_case_list, case_title)
                embeds = [r_profile, add_case]
                await message.edit(embeds=embeds, view=AddReportAccountContributorView())

    @discord.ui.button(label="Add Proofs", style=discord.ButtonStyle.green, custom_id="addreportaccountproofs:input")
    async def proofs_button(self, interaction, button):
        #
        session = inprogresscol.find_one({"_id": interaction.message.id})
        if session:
            requested_by = session["requested_by"]
            add_case_list = session["add_case_list"]
            #
            if requested_by == interaction.user.id:
                image_links = []
                add_case_list["proofs"] = []
                await interaction.response.send_message(
                    "Please send the images you would like to upload (max 10). **All images previously uploaded in this session have been removed.**",
                    ephemeral=True)

                def check(m):
                    return m.author == interaction.user and m.channel == interaction.channel

                try:
                    msg = await bot.wait_for('message', check=check, timeout=120.0)
                except asyncio.TimeoutError:
                    await interaction.followup.send("You took too long to upload an image.", ephemeral=True)
                    return
                if msg.attachments:
                    for attachment in msg.attachments:
                        # Ensure the attachment is an image (optional check)
                        if attachment.content_type and attachment.content_type.startswith('image/'):
                            try:
                                # 1. Download the file data using aiohttp
                                async with aiohttp.ClientSession() as http_session:
                                    async with http_session.get(attachment.url) as resp:
                                        # For this example, we just send back the image URL and filename
                                        data = io.BytesIO(await resp.read())
                                        file = discord.File(data, filename=attachment.filename)
                                        channel_to_send = bot.get_channel(PROOFS_CHANNEL)
                                        sent_message = await channel_to_send.send(file=file)
                                        if sent_message.attachments:
                                            new_image_url = sent_message.attachments[0].url
                                            image_links.append(new_image_url)
                                            add_case_list["proofs"].append(new_image_url)
                            except Exception:
                                await msg.channel.send(f"An error occurred with file {attachment.filename}")
                #
                inprogresscol.update_one(
                    {"_id": interaction.message.id},
                    {"$set": {"add_case_list": add_case_list}},
                )
                #
                image_embeds = image_links_to_embeds(image_links)
                await interaction.followup.send(f"Images received from {interaction.user.mention}.",
                                                embeds=image_embeds)

    @discord.ui.button(label="Show Proofs", style=discord.ButtonStyle.grey, custom_id="addreportaccountproofs:showproofs")
    async def show_proofs_button(self, interaction, button):
        await interaction.response.defer()
        #
        session = inprogresscol.find_one({"_id": interaction.message.id})
        if session:
            requested_by = session["requested_by"]
            add_case_list = session["add_case_list"]
            game_uid = session["account_id"]
            #
            if requested_by == interaction.user.id or is_sr(interaction.user):
                image_embeds = image_links_to_embeds(add_case_list["proofs"])
                await interaction.followup.send(f"Proofs for `{game_uid}`",
                                                embeds=image_embeds, ephemeral=True)

    @discord.ui.button(label="Show Links Proofs", style=discord.ButtonStyle.grey, custom_id="addreportaccountproofs:showlinksproofs")
    async def show_links_proofs_button(self, interaction, button):
        await interaction.response.defer()
        #
        session = inprogresscol.find_one({"_id": interaction.message.id})
        if session:
            requested_by = session["requested_by"]
            r_profile_list = session["r_profile_list"]
            game_uid = session["account_id"]
            #
            if requested_by == interaction.user.id or is_sr(interaction.user):
                image_embeds = image_links_to_embeds(r_profile_list[2])
                await interaction.followup.send(f"Links Proofs for `{game_uid}`",
                                                embeds=image_embeds, ephemeral=True)

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.grey, custom_id="addreportaccountproofs:cancel")
    async def cancel_button(self, interaction, button):
        await interaction.response.defer()
        #
        session = inprogresscol.find_one({"_id": interaction.message.id})
        if session:
            requested_by = session["requested_by"]
            channel_id = session["channel_id"]
            message_id = interaction.message.id
            #
            thread = await bot.fetch_channel(channel_id)
            message = await thread.fetch_message(message_id)
            if requested_by == interaction.user.id or is_sr(interaction.user):
                inprogresscol.delete_one({"_id": interaction.message.id})
                await message.edit(content=f"**Cancelled by {interaction.user.mention}.**", view=None)

    @discord.ui.button(label="Accept", style=discord.ButtonStyle.grey, custom_id="addreportaccountproofs:accept")
    async def accept_button(self, interaction, button):
        await interaction.response.defer()
        #
        session = inprogresscol.find_one({"_id": interaction.message.id})
        if session:
            requested_by = session["requested_by"]
            channel_id = session["channel_id"]
            message_id = interaction.message.id
            r_profile_list = session["r_profile_list"]
            add_case_list = session["add_case_list"]
            title = session["title"]
            case_title = session["case_title"]
            game_uid = session["account_id"]
            #
            thread = await bot.fetch_channel(channel_id)
            message = await thread.fetch_message(message_id)
            if is_sr(interaction.user) and interaction.user.id != requested_by:
                accepted_by = interaction.user
                add_case_list["accepted_by"] = f"<@{interaction.user.id}>"
                r_profile = format_account_r_profile(game_uid, r_profile_list, title)
                add_case = format_account_add_case(add_case_list, case_title)
                embeds = [r_profile, add_case]
                #
                vote_channel = bot.get_channel(VOTE_CHANNEL)
                agree_users = []
                disagree_users = []
                links_proofs_embeds = image_links_to_embeds(r_profile_list[2])
                proofs_embeds = image_links_to_embeds(add_case_list["proofs"])
                new_report_message = await vote_channel.send(content=f"Added report on `{game_uid}`")
                new_report_thread = await new_report_message.create_thread(name=f"{game_uid}")
                await new_report_thread.send(f"<@&{ticket_ping}>")
                vote_msg = await new_report_thread.send(
                    content=f"Report accepted by {accepted_by.mention}.\nLink to thread: <#{channel_id}>\n\nAgree: 0\nDisagree: 0",
                    embeds=embeds, view=AccountVoteView())
                vote_channel_id = vote_msg.channel.id
                vote_message_id = vote_msg.id
                old_session = inprogresscol.find_one({"account_id": game_uid})
                if old_session:
                    inprogresscol.delete_one({"_id": old_session["_id"]})
                inprogresscol.insert_one({
                    "_id": vote_message_id,
                    "account_id": game_uid,
                    "requested_by": requested_by,
                    "channel_id": channel_id,
                    "message_id": interaction.message.id,
                    "r_profile_list": r_profile_list,
                    "add_case_list": add_case_list,
                    "title": title,
                    "case_title": case_title,
                    "vote_channel_id": vote_channel_id,
                    "accepted_by": accepted_by.id,
                    "agree_users": agree_users,
                    "disagree_users": disagree_users,
                })
                await new_report_thread.send(content=f"Links Proofs for `{game_uid}`", embeds=links_proofs_embeds)
                await new_report_thread.send(content=f"Proofs for `{game_uid}`", embeds=proofs_embeds)
                await old_message_edit_queue.put(
                    (message, {"content": "Report has been submitted for voting.", "embeds": embeds, "view": None}))
            else:
                await interaction.followup.send("You do not have permission to accept the report for voting.",
                                                ephemeral=True)


# user voting
class AccountVoteView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Agree", style=discord.ButtonStyle.green, custom_id="accountvote:agree")
    async def agree_button(self, interaction, button):
        await interaction.response.defer()
        session = inprogresscol.find_one({"_id": interaction.message.id})
        if session:
            requested_by = session["requested_by"]
            channel_id = session["channel_id"]
            message_id = session["message_id"]
            r_profile_list = session["r_profile_list"]
            add_case_list = session.get("add_case_list")
            title = session["title"]
            case_title = session.get("case_title")
            accepted_by = session["accepted_by"]
            reason = session.get("reason")
            game_uid = session["account_id"]
            agree_users, disagree_users = await handle_vote(interaction, session, "agree")
            #
            r_profile = format_account_r_profile(game_uid, r_profile_list, title)
            #
            if len(agree_users) >= 8 and len(agree_users) > len(disagree_users):
                account_query = {"_id": game_uid}
                account_profile = accountscol.find_one(account_query)
                if account_profile:  # if editing existing reported user
                    old_r_profile_list = account_profile["r_profile_list"]
                    cases = []
                    no_of_cases = len(account_profile) - 2
                    for i in range(1, no_of_cases + 1):
                        cases.append(account_profile[str(i)])
                    #
                    if old_r_profile_list[0] != r_profile_list[0]:  # comparing links
                        old_links_list = old_r_profile_list[0]
                        new_links_list = r_profile_list[0]
                        added_links_list = set(new_links_list) - set(old_links_list)
                        removed_links_list = set(old_links_list) - set(new_links_list)
                        for link in added_links_list:
                            new_account = {"_id": str(link), "main": game_uid}
                            accountscol.insert_one(new_account)
                        for link in removed_links_list:
                            accountscol.delete_one({"_id": link})
                        update_operation = {'$set': {"r_profile_list": r_profile_list}}
                        accountscol.update_one(account_query, update_operation)
                    if not add_case_list:  # only links edited
                        tags_strings = []
                        all_tags_list = []
                        for case in cases:
                            tags_strings.append(case["tags"])
                        for tags_string in tags_strings:
                            tags_list = tags_string.split(", ")
                            for tag in tags_list:
                                all_tags_list.append(tag)
                        all_tags_list = sort_account_tags(all_tags_list)
                        title = all_tags_list[0]
                        r_profile = format_account_r_profile(game_uid, r_profile_list, title)
                        account_reports_channel = bot.get_channel(ACCOUNT_REPORTS_CHANNEL)
                        await account_reports_channel.send(content=f"<@&{updated_account_report_ping}>\nLinks edited for `{game_uid}`",
                                                        embed=r_profile)
                        reason_embed = discord.Embed(title="Reason", description=reason)
                        await account_reports_channel.send(content=f"Reason for change(s)", embed=reason_embed)
                        await old_message_edit_queue.put((interaction.message, {"content": f"**Report has been published.** Report accepted by <@{accepted_by}>.\nLink to thread: <#{channel_id}>\n\nAgree: {len(agree_users)}\nDisagree: {len(disagree_users)}",
                            "embeds": [r_profile], "view": None}))
                        thread = await bot.fetch_channel(channel_id)
                        message = await thread.fetch_message(message_id)
                        await old_message_edit_queue.put((message, {
                            "content": f"**Report has been published.** Report accepted by <@{accepted_by}>.",
                            "view": None}))
                        await bot.get_channel(channel_id).send(
                            f"Report on `{game_uid}` has been published. <@{requested_by}> <@{accepted_by}>")
                        inprogresscol.delete_one({"_id": interaction.message.id})
                    elif len(add_case_list) == 1:  # [[add_case_list]] case to appeal
                        add_case_list = add_case_list[0]
                        appeal_case_number = next((k for k, v in account_profile.items() if v == add_case_list), None)
                        query_filter = {"_id": game_uid}
                        update_operation = {"$unset": {appeal_case_number: ""}}
                        accountscol.update_one(query_filter, update_operation)
                        #
                        account_query = {"_id": game_uid}
                        account_profile = accountscol.find_one(account_query)
                        links = r_profile_list[0] if r_profile_list[0] else []
                        if len(account_profile) == 2:
                            accountscol.delete_one(account_query)
                            for link in links:
                                account_query = {"_id": link}
                                accountscol.delete_one(account_query)
                        else:
                            no_of_cases = len(account_profile) - 2
                            for i in range(int(appeal_case_number), no_of_cases + 1):
                                account_profile[appeal_case_number] = account_profile.pop(str(int(appeal_case_number) + 1))
                            cases = []
                            for i in range(1, no_of_cases + 1):
                                cases.append(account_profile[str(i)])
                            latest_tags = add_case_list["tags"].split(", ")
                            all_tags_list = []
                            for case in cases:
                                all_tags_list.extend(case["tags"].split(", "))
                            all_tags_list = sort_account_tags(all_tags_list)
                            if "Recovered Account" in latest_tags:
                                title = "Recovered Account"
                                all_other_tags = selected_string([tag for tag in all_tags_list if tag != "Recovered Account"])
                            else:
                                title = all_tags_list[0]
                                all_other_tags = selected_string(all_tags_list[1:])
                            r_profile_list = account_profile["r_profile_list"]
                            r_profile_list[1] = all_other_tags
                            account_profile["r_profile_list"] = r_profile_list
                            query_filter = {"_id": game_uid}
                            accountscol.replace_one(query_filter, account_profile)
                        #
                        r_profile = format_account_r_profile(game_uid, r_profile_list, title)
                        add_case = format_account_add_case(add_case_list, case_title)
                        reason_embed = discord.Embed(title="Reason", colour=0x1DCCA9, description=reason)
                        embeds = [r_profile, add_case]
                        #
                        account_reports_channel = bot.get_channel(ACCOUNT_REPORTS_CHANNEL)
                        await account_reports_channel.send(content=f"<@&{appealed_account_report_ping}>\nAppeal on `{game_uid}`",
                                                        embeds=embeds)
                        await account_reports_channel.send(content=f"Reason for appeal", embed=reason_embed)
                        await old_message_edit_queue.put((interaction.message, {"content": f"**Appeal has been published.** Appeal accepted by <@{accepted_by}>.\nLink to thread: <#{channel_id}>\n\nAgree: {len(agree_users)}\nDisagree: {len(disagree_users)}",
                            "view": None, "embeds": embeds}))
                        thread = await bot.fetch_channel(channel_id)
                        message = await thread.fetch_message(message_id)
                        await old_message_edit_queue.put((message, {
                            "content": f"**Appeal has been published.** Appeal accepted by <@{accepted_by}>.",
                            "view": None}))
                        await bot.get_channel(channel_id).send(
                            f"Appeal on `{game_uid}` has been published. <@{requested_by}> <@{accepted_by}>")
                        inprogresscol.delete_one({"_id": interaction.message.id})
                    else:  # new case exists
                        #
                        r_profile = format_account_r_profile(game_uid, r_profile_list, title)
                        add_case = format_account_add_case(add_case_list, case_title)
                        embeds = [r_profile, add_case]

                        query_filter = {"_id": game_uid}
                        update_operation = {'$set': {"r_profile_list": r_profile_list}}
                        accountscol.update_one(query_filter, update_operation)
                        update_operation = {'$set': {str(no_of_cases + 1): add_case_list}}
                        accountscol.update_one(query_filter, update_operation)

                        account_reports_channel = bot.get_channel(ACCOUNT_REPORTS_CHANNEL)
                        await account_reports_channel.send(content=f"<@&{updated_account_report_ping}>\nAdded report on `{game_uid}`",
                                                        embeds=embeds)
                        await old_message_edit_queue.put((interaction.message, {"content": f"**Report has been published.** Report accepted by <@{accepted_by}>.\nLink to thread: <#{channel_id}>\n\nAgree: {len(agree_users)}\nDisagree: {len(disagree_users)}",
                            "view": None, "embeds": embeds}))
                        thread = await bot.fetch_channel(channel_id)
                        message = await thread.fetch_message(message_id)
                        await old_message_edit_queue.put((message, {
                            "content": f"**Report has been published.** Report accepted by <@{accepted_by}>.",
                            "view": None}))
                        await bot.get_channel(channel_id).send(
                            f"Report on `{game_uid}` has been published. <@{requested_by}> <@{accepted_by}>")
                        inprogresscol.delete_one({"_id": interaction.message.id})
                else:  # if new reported account
                    r_profile = format_account_r_profile(game_uid, r_profile_list, title)
                    add_case = format_account_add_case(add_case_list, case_title)
                    embeds = [r_profile, add_case]
                    new_account = {"_id": game_uid, "r_profile_list": r_profile_list,
                                "1": add_case_list}
                    accountscol.insert_one(new_account)
                    links_list = r_profile_list[0] if r_profile_list[0] else []
                    for link in links_list:
                        new_account = {"_id": str(link), "main": game_uid}
                        accountscol.insert_one(new_account)
                    account_reports_channel = bot.get_channel(ACCOUNT_REPORTS_CHANNEL)
                    await account_reports_channel.send(content=f"<@&{new_account_report_ping}>\nNew report on `{game_uid}`",
                                                    embeds=embeds)
                    await old_message_edit_queue.put((interaction.message, {"content": f"**Report has been published.** Report accepted by <@{accepted_by}>.\nLink to thread: <#{channel_id}>\n\nAgree: {len(agree_users)}\nDisagree: {len(disagree_users)}",
                        "view": None, "embeds": embeds}))
                    thread = await bot.fetch_channel(channel_id)
                    message = await thread.fetch_message(message_id)
                    await old_message_edit_queue.put((message, {
                        "content": f"**Report has been published.** Report accepted by <@{accepted_by}>.",
                        "view": None}))
                    await bot.get_channel(channel_id).send(
                        f"Report on `{game_uid}` has been published. <@{requested_by}> <@{accepted_by}>")
                    inprogresscol.delete_one({"_id": interaction.message.id})
                try:
                    voters = agree_users + disagree_users
                    for voter in voters:
                        voter_query = {"_id": str(voter)}
                        voter_profile = trusteduserscol.find_one(voter_query)
                        if voter_profile:
                            trusteduserscol.update_one(
                                voter_query,
                                {"$inc": {"votes": 1}}
                            )

                    staff_query = {"_id": str(requested_by)}
                    if trusteduserscol.find_one(staff_query):
                        trusteduserscol.update_one(
                            staff_query,
                            {"$inc": {"reports": 1}}
                        )
                    if staffweeklycol.find_one(staff_query):
                        staffweeklycol.update_one(
                            staff_query,
                            {"$inc": {"weekly_reports": 1}}
                        )
                    sr_query = {"_id": str(accepted_by)}
                    if trusteduserscol.find_one(sr_query):
                        trusteduserscol.update_one(
                            {"_id": str(accepted_by)},
                            {"$inc": {"reviews": 1}}
                        )
                    if staffweeklycol.find_one(sr_query):
                        staffweeklycol.update_one(
                            {"_id": str(accepted_by)},
                            {"$inc": {"weekly_reviews": 1}}
                        )
                except Exception as e:
                    print(f"{e}")
                current_name = interaction.channel.name
                new_name = current_name if current_name.startswith("p-") else f"p-{current_name}"
                await asyncio.sleep(2)
                await interaction.channel.edit(name=new_name, archived=True, locked=True)
                return
            #
            if not add_case_list:  # only links edited
                await old_message_edit_queue.put((interaction.message, {"content": f"Report accepted by <@{accepted_by}>.\nLink to thread: <#{channel_id}>\n\nAgree: {len(agree_users)}\nDisagree: {len(disagree_users)}",
                    "embeds": [r_profile], "view": AccountVoteView()}))
            elif len(add_case_list) == 1:  # [[add_case_list]] case to appeal
                add_case_list = add_case_list[0]
                add_case = format_account_add_case(add_case_list, case_title)
                reason_embed = discord.Embed(title="Reason", colour=0x1DCCA9, description=reason)
                embeds = [r_profile, add_case, reason_embed]
                await old_message_edit_queue.put((interaction.message, {"content": f"Appeal accepted by <@{accepted_by}>.\nLink to thread: <#{channel_id}>\n\nAgree: {len(agree_users)}\nDisagree: {len(disagree_users)}",
                    "embeds": embeds, "view": AccountVoteView()}))
            else:  # new case exists
                add_case = format_account_add_case(add_case_list, case_title)
                embeds = [r_profile, add_case]
                await old_message_edit_queue.put((interaction.message, {"content": f"Report accepted by <@{accepted_by}>.\nLink to thread: <#{channel_id}>\n\nAgree: {len(agree_users)}\nDisagree: {len(disagree_users)}",
                    "embeds": embeds, "view": AccountVoteView()}))

    @discord.ui.button(label="Disagree", style=discord.ButtonStyle.red, custom_id="accountvote:disagree")
    async def disagree_button(self, interaction, button):
        await interaction.response.defer()
        session = inprogresscol.find_one({"_id": interaction.message.id})
        if session:
            requested_by = session["requested_by"]
            channel_id = session["channel_id"]
            message_id = session["message_id"]
            r_profile_list = session["r_profile_list"]
            add_case_list = session.get("add_case_list")
            title = session["title"]
            case_title = session.get("case_title")
            accepted_by = session["accepted_by"]
            reason = session.get("reason")
            game_uid = session["account_id"]
            agree_users, disagree_users = await handle_vote(interaction, session, "disagree")
            #
            r_profile = format_account_r_profile(game_uid, r_profile_list, title)
            #
            if len(disagree_users) >= 12:
                account_query = {"_id": game_uid}
                account_profile = accountscol.find_one(account_query)
                if account_profile:  # if editing existing reported account
                    if not add_case_list:  # only links edited
                        no_of_cases = len(account_profile) - 2
                        cases = []
                        for i in range(1, no_of_cases + 1):
                            cases.append(account_profile[str(i)])
                        latest_tags = add_case_list["tags"].split(", ")
                        all_tags_list = []
                        for case in cases:
                            all_tags_list.extend(case["tags"].split(", "))
                        all_tags_list = sort_account_tags(all_tags_list)
                        if "Recovered Account" in latest_tags:
                            title = "Recovered Account"
                        else:
                            title = all_tags_list[0]
                        r_profile = format_account_r_profile(game_uid, r_profile_list, title)
                        await old_message_edit_queue.put((interaction.message, {"content": f"**Report has been rejected.** Report accepted by <@{accepted_by}>.\nLink to thread: <#{channel_id}>\n\nAgree: {len(agree_users)}\nDisagree: {len(disagree_users)}",
                            "embeds": [r_profile], "view": None}))
                        thread = await bot.fetch_channel(channel_id)
                        message = await thread.fetch_message(message_id)
                        await old_message_edit_queue.put((message, {
                            "content": f"**Report has been rejected.** Report accepted by <@{accepted_by}>.",
                            "view": None}))
                        await bot.get_channel(channel_id).send(
                            f"Report on `{game_uid}` has been rejected. <@{requested_by}> <@{accepted_by}>")
                        inprogresscol.delete_one({"_id": interaction.message.id})

                    elif len(add_case_list) == 1:  # [[add_case_list]] case to appeal
                        add_case_list = add_case_list[0]
                        r_profile = format_account_r_profile(game_uid, r_profile_list, title)
                        add_case = format_account_add_case(add_case_list, case_title)
                        embeds = [r_profile, add_case]
                        #
                        await old_message_edit_queue.put((interaction.message, {"content": f"**Appeal has been rejected.** Appeal accepted by <@{accepted_by}>.\nLink to thread: <#{channel_id}>\n\nAgree: {len(agree_users)}\nDisagree: {len(disagree_users)}",
                            "view": None, "embeds": embeds}))
                        thread = await bot.fetch_channel(channel_id)
                        message = await thread.fetch_message(message_id)
                        await old_message_edit_queue.put((message, {
                            "content": f"**Appeal has been rejected.** Appeal accepted by <@{accepted_by}>.",
                            "view": None}))
                        await bot.get_channel(channel_id).send(
                            f"Appeal on `{game_uid}` has been rejected. <@{requested_by}> <@{accepted_by}>")
                        inprogresscol.delete_one({"_id": interaction.message.id})

                    else:  # new case exists
                        r_profile = format_account_r_profile(game_uid, r_profile_list, title)
                        add_case = format_account_add_case(add_case_list, case_title)
                        embeds = [r_profile, add_case]
                        await old_message_edit_queue.put((interaction.message, {"content": f"**Report has been rejected.** Report accepted by <@{accepted_by}>.\nLink to thread: <#{channel_id}>\n\nAgree: {len(agree_users)}\nDisagree: {len(disagree_users)}",
                            "view": None, "embeds": embeds}))
                        thread = await bot.fetch_channel(channel_id)
                        message = await thread.fetch_message(message_id)
                        await old_message_edit_queue.put((message, {
                            "content": f"**Report has been rejected.** Report accepted by <@{accepted_by}>.",
                            "view": None}))
                        await bot.get_channel(channel_id).send(
                            f"Report on `{game_uid}` has been rejected. <@{requested_by}> <@{accepted_by}>")
                        inprogresscol.delete_one({"_id": interaction.message.id})
                else:  # if new reported account
                    r_profile = format_account_r_profile(game_uid, r_profile_list, title)
                    add_case = format_account_add_case(add_case_list, case_title)
                    embeds = [r_profile, add_case]
                    await old_message_edit_queue.put((interaction.message, {"content": f"**Report has been rejected.** Report accepted by <@{accepted_by}>.\nLink to thread: <#{channel_id}>\n\nAgree: {len(agree_users)}\nDisagree: {len(disagree_users)}",
                        "view": None, "embeds": embeds}))
                    thread = await bot.fetch_channel(channel_id)
                    message = await thread.fetch_message(message_id)
                    await old_message_edit_queue.put((message, {
                        "content": f"**Report has been rejected.** Report accepted by <@{accepted_by}>.",
                        "view": None}))
                    await bot.get_channel(channel_id).send(
                        f"Report on `{game_uid}` has been rejected. <@{requested_by}> <@{accepted_by}>")
                    inprogresscol.delete_one({"_id": interaction.message.id})
                try:
                    voters = agree_users + disagree_users
                    for voter in voters:
                        voter_query = {"_id": str(voter)}
                        voter_profile = trusteduserscol.find_one(voter_query)
                        if voter_profile:
                            trusteduserscol.update_one(
                                voter_query,
                                {"$inc": {"votes": 1}}
                            )
                except Exception as e:
                    print(f"{e}")
                current_name = interaction.channel.name
                new_name = current_name if current_name.startswith("r-") else f"r-{current_name}"
                await asyncio.sleep(2)
                await interaction.channel.edit(name=new_name, archived=True, locked=True)
                return
            if not add_case_list:  # only links edited
                await old_message_edit_queue.put((interaction.message, {"content": f"Report accepted by <@{accepted_by}>.\nLink to thread: <#{channel_id}>\n\nAgree: {len(agree_users)}\nDisagree: {len(disagree_users)}",
                    "embeds": [r_profile], "view": AccountVoteView()}))
            elif len(add_case_list) == 1:  # [[add_case_list]] case to appeal
                add_case_list = add_case_list[0]
                add_case = format_account_add_case(add_case_list, case_title)
                reason_embed = discord.Embed(title="Reason", colour=0x1DCCA9, description=reason)
                embeds = [r_profile, add_case, reason_embed]
                await old_message_edit_queue.put((interaction.message, {"content": f"Appeal accepted by <@{accepted_by}>.\nLink to thread: <#{channel_id}>\n\nAgree: {len(agree_users)}\nDisagree: {len(disagree_users)}",
                    "embeds": embeds, "view": AccountVoteView()}))
            else:  # new case exists
                add_case = format_account_add_case(add_case_list, case_title)
                embeds = [r_profile, add_case]
                await old_message_edit_queue.put((interaction.message, {"content": f"Report accepted by <@{accepted_by}>.\nLink to thread: <#{channel_id}>\n\nAgree: {len(agree_users)}\nDisagree: {len(disagree_users)}",
                    "embeds": embeds, "view": AccountVoteView()}))

    @discord.ui.button(label="Remove Vote", style=discord.ButtonStyle.primary, custom_id="accountvote:removevote")
    async def remove_vote_button(self, interaction, button):
        await interaction.response.defer()
        session = inprogresscol.find_one({"_id": interaction.message.id})
        if session:
            channel_id = session["channel_id"]
            r_profile_list = session["r_profile_list"]
            add_case_list = session.get("add_case_list")
            title = session["title"]
            case_title = session.get("case_title")
            accepted_by = session["accepted_by"]
            reason = session.get("reason")
            game_uid = session["account_id"]
            agree_users, disagree_users = await handle_vote(interaction, session, "remove")
            #
            r_profile = format_account_r_profile(game_uid, r_profile_list, title)
            if not add_case_list:
                reason_embed = discord.Embed(title="Reason", description=reason)
                embeds = [r_profile, reason_embed]
                await old_message_edit_queue.put((interaction.message, {"content": f"Report accepted by <@{accepted_by}>.\nLink to thread: <#{channel_id}>\n\nAgree: {len(agree_users)}\nDisagree: {len(disagree_users)}",
                    "embeds": embeds, "view": AccountVoteView()}))
            elif len(add_case_list) == 1:  # [[add_case_list]] case to appeal
                add_case_list = add_case_list[0]
                add_case = format_account_add_case(add_case_list, case_title)
                reason_embed = discord.Embed(title="Reason", colour=0x1DCCA9, description=reason)
                embeds = [r_profile, add_case, reason_embed]
                await old_message_edit_queue.put((interaction.message, {"content": f"Appeal accepted by <@{accepted_by}>.\nLink to thread: <#{channel_id}>\n\nAgree: {len(agree_users)}\nDisagree: {len(disagree_users)}",
                    "embeds": embeds, "view": AccountVoteView()}))
            else:
                add_case = format_account_add_case(add_case_list, case_title)
                embeds = [r_profile, add_case]
                await old_message_edit_queue.put((interaction.message, {"content": f"Report accepted by <@{accepted_by}>.\nLink to thread: <#{channel_id}>\n\nAgree: {len(agree_users)}\nDisagree: {len(disagree_users)}",
                    "embeds": embeds, "view": AccountVoteView()}))

    @discord.ui.button(label="Publish", style=discord.ButtonStyle.grey, custom_id="accountvote:publish")
    async def publish_button(self, interaction, button):
        await interaction.response.defer(thinking=True)
        session = inprogresscol.find_one({"_id": interaction.message.id})
        if session:
            requested_by = session["requested_by"]
            channel_id = session["channel_id"]
            message_id = session["message_id"]
            r_profile_list = session["r_profile_list"]
            add_case_list = session.get("add_case_list")
            title = session["title"]
            case_title = session.get("case_title")
            agree_users = session["agree_users"]
            disagree_users = session["disagree_users"]
            reason = session.get("reason")
            game_uid = session["account_id"]
            o5_check = get(interaction.user.guild.roles, id=o5_role) in interaction.user.roles and len(
                agree_users) >= 5 and len(agree_users) > len(disagree_users)
            sr_check = is_sr(interaction.user) and interaction.user.id != requested_by and len(
                agree_users) >= 5 and len(agree_users) > len(disagree_users)
            if o5_check or sr_check:
                accepted_by = interaction.user.id
                account_query = {"_id": game_uid}
                account_profile = accountscol.find_one(account_query)
                if account_profile:  # if editing existing reported user
                    old_r_profile_list = account_profile["r_profile_list"]
                    cases = []
                    no_of_cases = len(account_profile) - 2
                    for i in range(1, no_of_cases + 1):
                        cases.append(account_profile[str(i)])
                    #
                    if old_r_profile_list[0] != r_profile_list[0]:  # comparing links
                        old_links_list = old_r_profile_list[0]
                        new_links_list = r_profile_list[0]
                        added_links_list = set(new_links_list) - set(old_links_list)
                        removed_links_list = set(old_links_list) - set(new_links_list)
                        for link in added_links_list:
                            new_account = {"_id": str(link), "main": game_uid}
                            accountscol.insert_one(new_account)
                        for link in removed_links_list:
                            accountscol.delete_one({"_id": link})
                        update_operation = {'$set': {"r_profile_list": r_profile_list}}
                        accountscol.update_one(account_query, update_operation)
                    if not add_case_list:  # only links edited
                        tags_strings = []
                        all_tags_list = []
                        for case in cases:
                            tags_strings.append(case["tags"])
                        for tags_string in tags_strings:
                            tags_list = tags_string.split(", ")
                            for tag in tags_list:
                                all_tags_list.append(tag)
                        all_tags_list = sort_account_tags(all_tags_list)
                        title = all_tags_list[0]
                        r_profile = format_account_r_profile(game_uid, r_profile_list, title)
                        account_reports_channel = bot.get_channel(ACCOUNT_REPORTS_CHANNEL)
                        await account_reports_channel.send(content=f"<@&{updated_account_report_ping}>\nLinks edited for `{game_uid}`",
                                                        embed=r_profile)
                        reason_embed = discord.Embed(title="Reason", description=reason)
                        await account_reports_channel.send(content=f"Reason for change(s)", embed=reason_embed)
                        await old_message_edit_queue.put((interaction.message, {"content": f"**Report has been published.** Report accepted by <@{accepted_by}>.\nLink to thread: <#{channel_id}>\n\nAgree: {len(agree_users)}\nDisagree: {len(disagree_users)}",
                            "embeds": [r_profile], "view": None}))
                        thread = await bot.fetch_channel(channel_id)
                        message = await thread.fetch_message(message_id)
                        await old_message_edit_queue.put((message, {
                            "content": f"**Report has been published.** Report accepted by <@{accepted_by}>.",
                            "view": None}))
                        await bot.get_channel(channel_id).send(
                            f"Report on `{game_uid}` has been published. <@{requested_by}> <@{accepted_by}>")
                        inprogresscol.delete_one({"_id": interaction.message.id})
                    elif len(add_case_list) == 1:  # [[add_case_list]] case to appeal
                        add_case_list = add_case_list[0]
                        appeal_case_number = next((k for k, v in account_profile.items() if v == add_case_list), None)
                        query_filter = {"_id": game_uid}
                        update_operation = {"$unset": {appeal_case_number: ""}}
                        accountscol.update_one(query_filter, update_operation)
                        #
                        account_query = {"_id": game_uid}
                        account_profile = accountscol.find_one(account_query)
                        links = r_profile_list[0] if r_profile_list[0] else []
                        if len(account_profile) == 2:
                            accountscol.delete_one(account_query)
                            for link in links:
                                account_query = {"_id": link}
                                accountscol.delete_one(account_query)
                        else:
                            no_of_cases = len(account_profile) - 2
                            for i in range(int(appeal_case_number), no_of_cases + 1):
                                account_profile[appeal_case_number] = account_profile.pop(str(int(appeal_case_number) + 1))
                            cases = []
                            for i in range(1, no_of_cases + 1):
                                cases.append(account_profile[str(i)])
                            latest_tags = add_case_list["tags"].split(", ")
                            all_tags_list = []
                            for case in cases:
                                all_tags_list.extend(case["tags"].split(", "))
                            all_tags_list = sort_account_tags(all_tags_list)
                            if "Recovered Account" in latest_tags:
                                title = "Recovered Account"
                                all_other_tags = selected_string([tag for tag in all_tags_list if tag != "Recovered Account"])
                            else:
                                title = all_tags_list[0]
                                all_other_tags = selected_string(all_tags_list[1:])
                            r_profile_list = account_profile["r_profile_list"]
                            r_profile_list[1] = all_other_tags
                            account_profile["r_profile_list"] = r_profile_list
                            query_filter = {"_id": game_uid}
                            accountscol.replace_one(query_filter, account_profile)
                        #
                        r_profile = format_account_r_profile(game_uid, r_profile_list, title)
                        add_case = format_account_add_case(add_case_list, case_title)
                        reason_embed = discord.Embed(title="Reason", colour=0x1DCCA9, description=reason)
                        embeds = [r_profile, add_case]
                        #
                        account_reports_channel = bot.get_channel(ACCOUNT_REPORTS_CHANNEL)
                        await account_reports_channel.send(content=f"<@&{appealed_account_report_ping}>\nAppeal on `{game_uid}`",
                                                        embeds=embeds)
                        await account_reports_channel.send(content=f"Reason for appeal", embed=reason_embed)
                        await old_message_edit_queue.put((interaction.message, {"content": f"**Appeal has been published.** Appeal accepted by <@{accepted_by}>.\nLink to thread: <#{channel_id}>\n\nAgree: {len(agree_users)}\nDisagree: {len(disagree_users)}",
                            "view": None, "embeds": embeds}))
                        thread = await bot.fetch_channel(channel_id)
                        message = await thread.fetch_message(message_id)
                        await old_message_edit_queue.put((message, {
                            "content": f"**Appeal has been published.** Appeal accepted by <@{accepted_by}>.",
                            "view": None}))
                        await bot.get_channel(channel_id).send(
                            f"Appeal on `{game_uid}` has been published. <@{requested_by}> <@{accepted_by}>")
                        inprogresscol.delete_one({"_id": interaction.message.id})
                    else:  # new case exists
                        add_case_list["accepted_by"] = f"{interaction.user.mention}"
                        inprogresscol.update_one(
                            {"_id": interaction.message.id},
                            {"$set": {"add_case_list": add_case_list}},
                        )
                        #
                        r_profile = format_account_r_profile(game_uid, r_profile_list, title)
                        add_case = format_account_add_case(add_case_list, case_title)
                        embeds = [r_profile, add_case]

                        query_filter = {"_id": game_uid}
                        update_operation = {'$set': {"r_profile_list": r_profile_list}}
                        accountscol.update_one(query_filter, update_operation)
                        update_operation = {'$set': {str(no_of_cases + 1): add_case_list}}
                        accountscol.update_one(query_filter, update_operation)

                        account_reports_channel = bot.get_channel(ACCOUNT_REPORTS_CHANNEL)
                        await account_reports_channel.send(content=f"<@&{updated_account_report_ping}>\nAdded report on `{game_uid}`",
                                                        embeds=embeds)
                        await old_message_edit_queue.put((interaction.message, {"content": f"**Report has been published.** Report accepted by <@{accepted_by}>.\nLink to thread: <#{channel_id}>\n\nAgree: {len(agree_users)}\nDisagree: {len(disagree_users)}",
                            "view": None, "embeds": embeds}))
                        thread = await bot.fetch_channel(channel_id)
                        message = await thread.fetch_message(message_id)
                        await old_message_edit_queue.put((message, {
                            "content": f"**Report has been published.** Report accepted by <@{accepted_by}>.",
                            "view": None}))
                        await bot.get_channel(channel_id).send(
                            f"Report on `{game_uid}` has been published. <@{requested_by}> <@{accepted_by}>")
                        inprogresscol.delete_one({"_id": interaction.message.id})
                else:  # if new reported account
                    add_case_list["accepted_by"] = interaction.user.mention
                    inprogresscol.update_one(
                        {"_id": interaction.message.id},
                        {"$set": {"add_case_list": add_case_list}},
                    )
                    #
                    r_profile = format_account_r_profile(game_uid, r_profile_list, title)
                    add_case = format_account_add_case(add_case_list, case_title)
                    embeds = [r_profile, add_case]
                    new_account = {"_id": game_uid, "r_profile_list": r_profile_list,
                                "1": add_case_list}
                    accountscol.insert_one(new_account)
                    links_list = r_profile_list[0] if r_profile_list[0] else []
                    for link in links_list:
                        accountscol.update_one(
                            {"_id": str(link)},
                            {"$set": {"main": game_uid}},
                            upsert=True
                        )
                    account_reports_channel = bot.get_channel(ACCOUNT_REPORTS_CHANNEL)
                    await account_reports_channel.send(content=f"<@&{new_account_report_ping}>\nNew report on `{game_uid}`",
                                                    embeds=embeds)
                    await old_message_edit_queue.put((interaction.message, {"content": f"**Report has been published.** Report accepted by <@{accepted_by}>.\nLink to thread: <#{channel_id}>\n\nAgree: {len(agree_users)}\nDisagree: {len(disagree_users)}",
                        "view": None, "embeds": embeds}))
                    thread = await bot.fetch_channel(channel_id)
                    message = await thread.fetch_message(message_id)
                    await old_message_edit_queue.put((message, {
                        "content": f"**Report has been published.** Report accepted by <@{accepted_by}>.",
                        "view": None}))
                    await bot.get_channel(channel_id).send(
                        f"Report on `{game_uid}` has been published. <@{requested_by}> <@{accepted_by}>")
                    inprogresscol.delete_one({"_id": interaction.message.id})
                try:
                    voters = agree_users + disagree_users
                    for voter in voters:
                        voter_query = {"_id": str(voter)}
                        voter_profile = trusteduserscol.find_one(voter_query)
                        if voter_profile:
                            trusteduserscol.update_one(
                                voter_query,
                                {"$inc": {"votes": 1}}
                            )

                    staff_query = {"_id": str(requested_by)}
                    if trusteduserscol.find_one(staff_query):
                        trusteduserscol.update_one(
                            staff_query,
                            {"$inc": {"reports": 1}}
                        )
                    if staffweeklycol.find_one(staff_query):
                        staffweeklycol.update_one(
                            staff_query,
                            {"$inc": {"weekly_reports": 1}}
                        )

                    sr_query = {"_id": str(accepted_by)}
                    if trusteduserscol.find_one(sr_query):
                        trusteduserscol.update_one(
                            {"_id": str(accepted_by)},
                            {"$inc": {"reviews": 1}}
                        )
                    if staffweeklycol.find_one(sr_query):
                        staffweeklycol.update_one(
                            {"_id": str(accepted_by)},
                            {"$inc": {"weekly_reviews": 1}}
                        )
                except Exception as e:
                    print(f"{e}")
                current_name = interaction.channel.name
                new_name = current_name if current_name.startswith("p-") else f"p-{current_name}"
                await asyncio.sleep(2)
                await interaction.channel.edit(name=new_name, archived=True, locked=True)
            else:
                await interaction.followup.send("You do not have permission to publish the report.", ephemeral=True)


edit = app_commands.Group(name="edit", description="Edit.")
bot.tree.add_command(edit)

@edit.command(name="report", description="Edit an ongoing report.")
@app_commands.describe(
    id="User ID, Guild ID or GameㆍUID",
    alts="New Alt(s) (user report only).",
    alts_proofs="Input anything. Note this overrides ALL alts proofs.",
    owner="New Owner (server report only).",
    links="New Link(s) (account report only). Separate with newlines or `\\n`",
    links_proofs="Input anything. Note this overrides ALL links proofs.",
    tags="New Tag(s).",
    games="New Game(s).",
    related_users="Related User(s) (account report only).",
    reason="New Reason.",
    contributor="New Contributor.",
    proofs="Input anything."
)
async def edit_report(interaction: discord.Interaction, id: str, alts: str = None, alts_proofs: str = None, owner: str = None, links: str = None, links_proofs: str = None, tags: str = None, games: str = None, related_users: str = None, reason: str = None, contributor: str = None, proofs: str = None):
    await interaction.response.defer(ephemeral=True)
    if sum(bool(x) for x in [alts_proofs, links_proofs, proofs]) >= 2:
        return await interaction.followup.send("Please edit only one proof field at a time.", ephemeral=True)

    id = id.strip("<@>")
    query = []
    try:
        numeric_id = int(id)
        query.append({"user_id": numeric_id})
        query.append({"guild_id": numeric_id})
    except ValueError:
        pass
    query.append({"account_id": id})
    session = inprogresscol.find_one({"$or": query})

    if not session:
        return await interaction.followup.send("Unable to find ongoing report.", ephemeral=True)
    if interaction.user.id != session.get("requested_by"):
        return await interaction.followup.send("You are not authorised to edit this report.", ephemeral=True)
    try:
        channel = interaction.channel
        message = await channel.fetch_message(session["_id"])
    except:
        return await interaction.followup.send("Report not found in this channel.", ephemeral=True)
    restricted_flow = False
    if message and message.content:
        restricted_flow = (
                message.content.startswith("Editing alts for") or
                message.content.startswith("Editing owner for") or
                message.content.startswith("Appealing for")
        )
    is_user_report = "user_id" in session
    is_server_report = "guild_id" in session
    is_account_report = "account_id" in session
    is_edit_or_appeal = "reason" in session
    edited_fields = []
    title = session.get("title")
    case_title = session.get("case_title")
    r_profile_list = session.get("r_profile_list", [])
    add_case_list = session.get("add_case_list", {})
    if restricted_flow:
        if alts and is_user_report:
            if len(add_case_list) >= 2:
                return await interaction.followup.send("This report does not contain an editable case.", ephemeral=True)
            alt_ids = []
            for alt in alts.split():
                try:
                    alt_user = await bot.fetch_user(int(alt.strip("<@>")))
                    alt_ids.append(alt_user.id)
                except:
                    pass
            r_profile_list[0] = alts_string(alt_ids) if alt_ids else ""
            edited_fields.append(f"alts　–　{r_profile_list[0]}")
        if alts_proofs and is_user_report:
            if len(add_case_list) >= 2:
                return await interaction.followup.send("This report does not contain an editable case.", ephemeral=True)
            image_links = []
            await interaction.followup.send(
                "Please send the images you would like to upload (max 10). **All images previously uploaded in this session have been removed.**",
                ephemeral=True)

            def check(m):
                return m.author == interaction.user and m.channel == interaction.channel

            try:
                msg = await bot.wait_for('message', check=check, timeout=120.0)
            except asyncio.TimeoutError:
                await interaction.followup.send("You took too long to upload an image.", ephemeral=True)
                return
            if msg.attachments:
                for attachment in msg.attachments:
                    if attachment.content_type and attachment.content_type.startswith('image/'):
                        try:
                            async with aiohttp.ClientSession() as http_session:
                                async with http_session.get(attachment.url) as resp:
                                    data = io.BytesIO(await resp.read())
                                    file = discord.File(data, filename=attachment.filename)
                                    channel_to_send = bot.get_channel(PROOFS_CHANNEL)
                                    sent_message = await channel_to_send.send(file=file)
                                    if sent_message.attachments:
                                        new_image_url = sent_message.attachments[0].url
                                        image_links.append(new_image_url)
                        except Exception:
                            pass
            r_profile_list[2] = image_links
            edited_fields.append(f"alts proofs　–　{len(image_links)} uploaded")
            image_embeds = image_links_to_embeds(image_links)
            await message.reply(content=f"Images received from {interaction.user.mention}.", embeds=image_embeds)
        if owner and is_server_report:
            if len(add_case_list) >= 2:
                return await interaction.followup.send("This report does not contain an editable case.", ephemeral=True)
            try:
                owner_user = await bot.fetch_user(int(owner.strip("<@>")))
                r_profile_list[0] = owner_user.mention
                edited_fields.append(f"owner　–　{owner_user.mention}")
            except:
                pass
        if links and is_account_report:
            if len(add_case_list) >= 2:
                return await interaction.followup.send("This report does not contain an editable case.", ephemeral=True)
            links = links.replace("\\n", "\n")
            game_uid_list = get_game_uid_list(links)
            r_profile_list[0] = game_uid_list or []
            edited_fields.append(f"links\n{'\n'.join(r_profile_list[0])}")
        if links_proofs and is_account_report:
            if len(add_case_list) >= 2:
                return await interaction.followup.send("This report does not contain an editable case.", ephemeral=True)
            image_links = []
            await interaction.followup.send(
                "Please send the images you would like to upload (max 10). **All images previously uploaded in this session have been removed.**",
                ephemeral=True)

            def check(m):
                return m.author == interaction.user and m.channel == interaction.channel

            try:
                msg = await bot.wait_for('message', check=check, timeout=120.0)
            except asyncio.TimeoutError:
                await interaction.followup.send("You took too long to upload an image.", ephemeral=True)
                return
            if msg.attachments:
                for attachment in msg.attachments:
                    if attachment.content_type and attachment.content_type.startswith('image/'):
                        try:
                            async with aiohttp.ClientSession() as http_session:
                                async with http_session.get(attachment.url) as resp:
                                    data = io.BytesIO(await resp.read())
                                    file = discord.File(data, filename=attachment.filename)
                                    channel_to_send = bot.get_channel(PROOFS_CHANNEL)
                                    sent_message = await channel_to_send.send(file=file)
                                    if sent_message.attachments:
                                        new_image_url = sent_message.attachments[0].url
                                        image_links.append(new_image_url)
                        except Exception:
                            pass
            r_profile_list[2] = image_links
            edited_fields.append(f"links proofs　–　{len(image_links)} uploaded")
            image_embeds = image_links_to_embeds(image_links)
            await message.reply(content=f"Images received from {interaction.user.mention}.", embeds=image_embeds)
        if reason:
            if is_edit_or_appeal:
                session["reason"] = reason
                await message.reply(embed=discord.Embed(title="Reason", colour=0xffffff, description=reason))
                edited_fields.append("reason updated")

        update_data = {"r_profile_list": r_profile_list, "title": title}
        if reason is not None:
            update_data["reason"] = reason

        inprogresscol.update_one(
            {"_id": session["_id"]},
            {"$set": update_data}
        )
        embeds = []
        if is_user_report:
            user = await bot.fetch_user(session["user_id"])
            r_profile = format_user_r_profile(user, r_profile_list, title)
            embeds = [r_profile]
            if add_case_list and len(add_case_list) >= 2:
                add_case = format_user_add_case(add_case_list, case_title)
                embeds.append(add_case)
        elif is_server_report:
            guild_data = session["guild_data"]
            r_profile = reconstruct_server_r_profile(guild_data, r_profile_list, title)
            embeds = [r_profile]
            if add_case_list and len(add_case_list) >= 2:
                add_case = format_server_add_case(add_case_list, case_title)
                embeds.append(add_case)
        elif is_account_report:
            game_uid = session["account_id"]
            r_profile = format_account_r_profile(game_uid, r_profile_list, title)
            embeds = [r_profile]
            if add_case_list and len(add_case_list) >= 2:
                add_case = format_account_add_case(add_case_list, case_title)
                embeds.append(add_case)
        if not embeds:
            return
        vote_message = None
        ticket_message = None
        vote_channel_id = session.get("vote_channel_id")
        if vote_channel_id:
            try:
                vote_channel = await bot.fetch_channel(vote_channel_id)
                vote_message = await vote_channel.fetch_message(session["_id"])
            except:
                vote_message = None
        if not vote_message:
            try:
                thread = await bot.fetch_channel(session["channel_id"])
                ticket_message = await thread.fetch_message(session["_id"])
            except:
                ticket_message = None
        if vote_message:
            await old_message_edit_queue.put((vote_message, {"embeds": embeds}))
            await interaction.followup.send("Edited successfully.", ephemeral=True)
            if edited_fields:
                edit_embed = discord.Embed(
                    title=f"Edited {id}",
                    description="\n".join(
                        f"<:reply:1459162938303578213>　{x}" for x in edited_fields), colour=0xffffff)
                edit_embed.set_footer(text=f"Edited by {interaction.user}", icon_url=interaction.user.display_avatar)
                await vote_message.reply(embed=edit_embed)
        elif ticket_message:
            if add_case_list and len(add_case_list) < 2:
                reason_embed = discord.Embed(title="Reason", description=reason)
            else:
                reason_embed = discord.Embed(title="Reason", colour=0x1dcca9, description=reason)
            embeds.append(reason_embed)
            await old_message_edit_queue.put((ticket_message, {"embeds": embeds}))
            if edited_fields:
                edit_embed = discord.Embed(
                    title=f"Edited {id}",
                    description="\n".join(
                        f"<:reply:1459162938303578213>　{x}" for x in edited_fields), colour=0xffffff)
                edit_embed.set_footer(text=f"Edited by {interaction.user}", icon_url=interaction.user.display_avatar)
                await ticket_message.reply(embed=edit_embed)
        return

    if alts and is_user_report:
        alt_ids = []
        for alt in alts.split():
            try:
                alt_user = await bot.fetch_user(int(alt.strip("<@>")))
                alt_ids.append(alt_user.id)
            except:
                pass
        r_profile_list[0] = alts_string(alt_ids) if alt_ids else ""
        edited_fields.append(f"alts　–　{r_profile_list[0]}")
    if alts_proofs and is_user_report:
        image_links = []
        await interaction.followup.send(
            "Please send the images you would like to upload (max 10). **All images previously uploaded in this session have been removed.**",
            ephemeral=True)
        def check(m):
            return m.author == interaction.user and m.channel == interaction.channel
        try:
            msg = await bot.wait_for('message', check=check, timeout=120.0)
        except asyncio.TimeoutError:
            await interaction.followup.send("You took too long to upload an image.", ephemeral=True)
            return
        if msg.attachments:
            for attachment in msg.attachments:
                if attachment.content_type and attachment.content_type.startswith('image/'):
                    try:
                        async with aiohttp.ClientSession() as http_session:
                            async with http_session.get(attachment.url) as resp:
                                data = io.BytesIO(await resp.read())
                                file = discord.File(data, filename=attachment.filename)
                                channel_to_send = bot.get_channel(PROOFS_CHANNEL)
                                sent_message = await channel_to_send.send(file=file)
                                if sent_message.attachments:
                                    new_image_url = sent_message.attachments[0].url
                                    image_links.append(new_image_url)
                    except Exception:
                        pass
        r_profile_list[2] = image_links
        edited_fields.append(f"alts proofs　–　{len(image_links)} uploaded")
        image_embeds = image_links_to_embeds(image_links)
        await message.reply(content=f"Images received from {interaction.user.mention}.", embeds=image_embeds)
    if owner and is_server_report:
        try:
            owner_user = await bot.fetch_user(int(owner.strip("<@>")))
            r_profile_list[0] = owner_user.mention
            edited_fields.append(f"owner　–　{owner_user.mention}")
        except:
            pass
    if links and is_account_report:
        links = links.replace("\\n", "\n")
        game_uid_list = get_game_uid_list(links)
        r_profile_list[0] = game_uid_list or []
        edited_fields.append(f"links\n{'\n'.join(r_profile_list[0])}")
    if links_proofs and is_account_report:
        image_links = []
        await interaction.followup.send(
            "Please send the images you would like to upload (max 10). **All images previously uploaded in this session have been removed.**",
            ephemeral=True)
        def check(m):
            return m.author == interaction.user and m.channel == interaction.channel
        try:
            msg = await bot.wait_for('message', check=check, timeout=120.0)
        except asyncio.TimeoutError:
            await interaction.followup.send("You took too long to upload an image.", ephemeral=True)
            return
        if msg.attachments:
            for attachment in msg.attachments:
                if attachment.content_type and attachment.content_type.startswith('image/'):
                    try:
                        async with aiohttp.ClientSession() as http_session:
                            async with http_session.get(attachment.url) as resp:
                                data = io.BytesIO(await resp.read())
                                file = discord.File(data, filename=attachment.filename)
                                channel_to_send = bot.get_channel(PROOFS_CHANNEL)
                                sent_message = await channel_to_send.send(file=file)
                                if sent_message.attachments:
                                    new_image_url = sent_message.attachments[0].url
                                    image_links.append(new_image_url)
                    except Exception:
                        pass
        r_profile_list[2] = image_links
        edited_fields.append(f"links proofs　–　{len(image_links)} uploaded")
        image_embeds = image_links_to_embeds(image_links)
        await message.reply(content=f"Images received from {interaction.user.mention}.", embeds=image_embeds)
    if tags:
        tag_list = [x.strip().title() for x in tags.split(",") if x.strip()]
        if is_user_report:
            sorted_tags = sort_user_tags(tag_list)
        elif is_server_report:
            sorted_tags = sort_server_tags(tag_list)
        else:
            sorted_tags = sort_account_tags(tag_list)
        if sorted_tags:
            case_title = sorted_tags[0]
            if is_user_report:
                add_case_list["tags"] = ", ".join(sorted_tags)
            elif is_server_report:
                add_case_list["tags"] = ", ".join(sorted_tags)
            elif is_account_report:
                add_case_list["tags"] = ", ".join(sorted_tags)
            edited_fields.append(f"tags　–　{', '.join(sorted_tags)}")
            profile = None
            if is_user_report:
                profile = userscol.find_one({"_id": str(id)})
            elif is_server_report:
                profile = serverscol.find_one({"_id": str(id)})
            elif is_account_report:
                profile = accountscol.find_one({"_id": str(id)})
            cases = []
            if profile:
                no_of_cases = len(profile) - 2
                for i in range(1, no_of_cases + 1):
                    cases.append(profile[str(i)])
            tags_strings = []
            all_tags_list = []
            if is_account_report:
                latest_tags = add_case_list["tags"].split(", ")
                all_tags_list = []
                for case in cases:
                    all_tags_list.extend(case["tags"].split(", "))
                all_tags_list.extend(latest_tags)
                all_tags_list = list(dict.fromkeys(all_tags_list))
                all_tags_list = sort_account_tags(all_tags_list)
                if "Recovered Account" in latest_tags:
                    title = "Recovered Account"
                    all_other_tags = selected_string([tag for tag in all_tags_list if tag != "Recovered Account"])
                else:
                    title = all_tags_list[0] if all_tags_list else "TBC"
                    all_other_tags = selected_string(all_tags_list[1:])
            else:
                for case in cases:
                    tags_strings.append(case["tags"]) if is_user_report else tags_strings.append(case["tags"])
                for tags_string in tags_strings:
                    tags_list = tags_string.split(", ")
                    for tag in tags_list:
                        all_tags_list.append(tag)
                all_tags_list += tag_list
                all_tags_list = list(dict.fromkeys(all_tags_list))
                all_tags_list = sort_user_tags(all_tags_list) if is_user_report else sort_server_tags(all_tags_list)
                title = all_tags_list[0] if all_tags_list else "TBC"
                all_other_tags = selected_string(all_tags_list[1:])
            r_profile_list[1] = all_other_tags
    if games is not None and is_user_report:
        games_map = {g.lower(): g for g in games_list}
        filtered_games = []
        for g in games.split(","):
            key = g.strip().lower()
            if key in games_map and games_map[key] not in filtered_games:
                filtered_games.append(games_map[key])
        games_string = ", ".join(filtered_games) if filtered_games else "N/A"
        add_case_list["games"] = games_string
        edited_fields.append(f"games　–　{games_string}")
    if related_users and is_account_report:
        valid_users = []
        for user_id in related_users.split():
            try:
                fetched = await bot.fetch_user(int(user_id))
            except Exception:
                continue
            if fetched.id not in valid_users:
                valid_users.append(fetched.id)
        if len(valid_users):
            add_case_list["related_users"] = related_users_string(valid_users)
        else:
            add_case_list["related_users"] = ""
        edited_fields.append(f"related users　–　{related_users_string(valid_users)}")
    if reason:
        if is_user_report:
            add_case_list["reason"] = reason
        elif is_server_report:
            add_case_list["reason"] = reason
        elif is_account_report:
            add_case_list["reason"] = reason
        edited_fields.append("reason updated")
    if contributor:
        contributor_value = None
        if contributor == "n":
            contributor_value = "Anonymous"
        else:
            try:
                contributor_user = await bot.fetch_user(int(contributor.strip("<@>")))
                contributor_value = contributor_user.mention
            except:
                pass
        if is_user_report and contributor_value:
            add_case_list["contributor"] = contributor_value
            edited_fields.append(f"contributor　–　{contributor_value}")
        elif is_server_report and contributor_value:
            add_case_list["contributor"] = contributor_value
            edited_fields.append(f"contributor　–　{contributor_value}")
        elif is_account_report and contributor_value:
            add_case_list["contributor"] = contributor_value
            edited_fields.append(f"contributor　–　{contributor_value}")
    if proofs:
        await interaction.followup.send("Send proofs to be attached to this report.", ephemeral=True)
        def check(m):
            return m.author == interaction.user and m.channel == interaction.channel
        try:
            msg = await bot.wait_for("message", check=check, timeout=120)
        except asyncio.TimeoutError:
            return await interaction.followup.send("You took too long to upload proofs.", ephemeral=True)
        image_links = []
        if msg.attachments:
            for attachment in msg.attachments:
                if attachment.content_type and attachment.content_type.startswith("image/"):
                    try:
                        async with aiohttp.ClientSession() as http_session:
                            async with http_session.get(attachment.url) as resp:
                                data = io.BytesIO(await resp.read())
                                file = discord.File(data, filename=attachment.filename)
                                channel_to_send = bot.get_channel(PROOFS_CHANNEL)
                                sent_message = await channel_to_send.send(file=file)
                                if sent_message.attachments:
                                    new_image_url = sent_message.attachments[0].url
                                    image_links.append(new_image_url)
                    except Exception:
                        pass
        if is_user_report:
            add_case_list["proofs"] = image_links
            edited_fields.append(f"proofs　–　{len(image_links)} uploaded")
        elif is_server_report:
            add_case_list["proofs"] = image_links
            edited_fields.append(f"proofs　–　{len(image_links)} uploaded")
        elif is_account_report:
            add_case_list["proofs"] = image_links
            edited_fields.append(f"proofs　–　{len(image_links)} uploaded")
        image_embeds = image_links_to_embeds(image_links)
        await message.reply(content=f"Images received from {interaction.user.mention}.", embeds=image_embeds)

    update_data = {"r_profile_list": r_profile_list, "add_case_list": add_case_list, "title": title,
                   "case_title": case_title}
    inprogresscol.update_one(
        {"_id": session["_id"]},
        {"$set": update_data}
    )

    if is_user_report:
        user = await bot.fetch_user(session["user_id"])
        r_profile = format_user_r_profile(user, r_profile_list, title)
        embeds = [r_profile]
        if add_case_list:
            add_case = format_user_add_case(add_case_list, case_title)
            embeds.append(add_case)
    elif is_server_report:
        guild_data = session["guild_data"]
        r_profile = reconstruct_server_r_profile(guild_data, r_profile_list, title)
        embeds = [r_profile]
        if add_case_list:
            add_case = format_server_add_case(add_case_list, case_title)
            embeds.append(add_case)
    elif is_account_report:
        game_uid = session["account_id"]
        r_profile = format_account_r_profile(game_uid, r_profile_list, title)
        embeds = [r_profile]
        if add_case_list:
            add_case = format_account_add_case(add_case_list, case_title)
            embeds.append(add_case)
    if not embeds:
        return
    vote_message = None
    ticket_message = None
    vote_channel_id = session.get("vote_channel_id")
    if vote_channel_id:
        try:
            vote_channel = await bot.fetch_channel(vote_channel_id)
            vote_message = await vote_channel.fetch_message(session["_id"])
        except:
            vote_message = None
    if not vote_message:
        try:
            thread = await bot.fetch_channel(session["channel_id"])
            ticket_message = await thread.fetch_message(session["_id"])
        except:
            ticket_message = None
    target = vote_message or ticket_message
    if target:
        await old_message_edit_queue.put((target, {"embeds": embeds}))
        await interaction.followup.send("Edited successfully.", ephemeral=True)
        if edited_fields:
            edit_embed = discord.Embed(
                title=f"Edited {id}",
                description="\n".join(
                    f"<:reply:1459162938303578213>　{x}" for x in edited_fields), colour=0xffffff)
            edit_embed.set_footer(text=f"Edited by {interaction.user}", icon_url=interaction.user.display_avatar)
            await target.reply(embed=edit_embed)


# staff utils

@bot.command(name="ar", help="Sends jump urls to all active reports in the thread.")
@commands.has_any_role(staff_role)
async def ar(ctx):
    if isinstance(ctx.channel, discord.Thread):
        thread = ctx.channel
        active_reports = []
        db_reports = list(inprogresscol.find({"channel_id": thread.id, "vote_channel_id": {"$exists": False}}))
        for r in db_reports:
            message_id = r.get("_id")
            if message_id:
                active_reports.append(f"https://discord.com/channels/{ctx.guild.id}/{thread.id}/{message_id}")
        if active_reports:
            embed = discord.Embed(description="\n\n".join(active_reports))
        else:
            embed = discord.Embed(description="No active reports.")
        await ctx.reply(f"{len(active_reports)} active reports in this thread.", embed=embed)
    else:
        await ctx.reply("This command can only be used in a thread.")

@bot.command(name="vr", help="Sends a list of all reports in voting in the thread.")
@commands.has_any_role(staff_role)
async def vr(ctx):
    if isinstance(ctx.channel, discord.Thread):
        thread = ctx.channel
        voting_reports = []
        db_reports = list(inprogresscol.find({"channel_id": thread.id, "vote_channel_id": {"$exists": True}}))
        for r in db_reports:
            vote_channel_id = r.get("vote_channel_id")
            message_id = r.get("_id")
            if vote_channel_id and message_id:
                voting_reports.append(f"https://discord.com/channels/{ctx.guild.id}/{vote_channel_id}/{message_id}")
        if voting_reports:
            embed = discord.Embed(description="\n\n".join(voting_reports))
        else:
            embed = discord.Embed(description="No reports in voting.")
        await ctx.reply(f"{len(voting_reports)} reports in voting in this thread.", embed=embed)
    else:
        await ctx.reply("This command can only be used in a thread.")


@bot.command(name="pr", help="Sends a list of all published reports in the thread.")
@commands.has_any_role(staff_role)
async def pr(ctx):
    if isinstance(ctx.channel, discord.Thread):
        thread = ctx.channel
        published_reports = []
        try:
            async for message in thread.history(oldest_first=True, limit=None):
                if "published. " in message.content and message.author.id == bot.user.id:
                    match = re.search(r'`([^`]+)`', message.content)
                    if match:
                        published_reports.append(match.group(1))
        except Exception: pass
        if published_reports:
            embed = discord.Embed(description=f"`{" ".join(published_reports)}`")
        else: embed = discord.Embed(description="No published reports.")
        await ctx.reply(f"{len(published_reports)} published reports in this thread.", embed=embed)
    else:
        await ctx.reply("This command can only be used in a thread.")

@bot.command(name="sr", help="Pings sr+.")
@commands.has_any_role(staff_role)
async def sr(ctx):
    await ctx.reply(f"<@&{sr_ping}>")

@bot.command(name="adm", help="Pings adm+.")
@commands.has_any_role(staff_role)
async def adm(ctx):
    await ctx.reply(f"<@&{adm_ping}>")

@bot.command(name="tp", help="Pings ticket ping.")
@commands.has_any_role(staff_role)
async def tp(ctx):
    await ctx.reply(f"<@&{ticket_ping}>")


# slash cmds

@bot.tree.command(name="report", description="Create a report directly (staff only)")
@app_commands.describe(
    user="User to report",
    alts="Alts",
    alt_proof1="Alts proof image 1",
    alt_proof2="Alts proof image 2",
    alt_proof3="Alts proof image 3",
    alt_proof4="Alts proof image 4",
    alt_proof5="Alts proof image 5",
    tags="Tag(s)",
    games="Game(s)",
    reason="Reason",
    contributor="Contributor (optional)",
    proof1="Proof image 1",
    proof2="Proof image 2",
    proof3="Proof image 3",
    proof4="Proof image 4",
    proof5="Proof image 5",
    proof6="Proof image 6",
    proof7="Proof image 7",
    proof8="Proof image 8",
    proof9="Proof image 9",
    proof10="Proof image 10",
)
@app_commands.checks.has_any_role(adm_ping, sr_ping, ticket_ping)
async def report(
    interaction: discord.Interaction,
    user: discord.User,
    tags: str,
    games: str,
    reason: str,
    alts: str = None,
    contributor: discord.User = None,
    alt_proof1: discord.Attachment = None,
    alt_proof2: discord.Attachment = None,
    alt_proof3: discord.Attachment = None,
    alt_proof4: discord.Attachment = None,
    alt_proof5: discord.Attachment = None,
    proof1: discord.Attachment = None,
    proof2: discord.Attachment = None,
    proof3: discord.Attachment = None,
    proof4: discord.Attachment = None,
    proof5: discord.Attachment = None,
    proof6: discord.Attachment = None,
    proof7: discord.Attachment = None,
    proof8: discord.Attachment = None,
    proof9: discord.Attachment = None,
    proof10: discord.Attachment = None,
):
    await interaction.response.defer()
    user_id = user.id
    if user.id in tri_bots:
        await interaction.followup.send(f"You cannot report a TRI bot.", ephemeral=True)
        return
    existing = userscol.find_one({"_id": str(user_id)})
    trusted = trusteduserscol.find_one({"_id": str(user_id)})
    if existing:
        await interaction.followup.send(
            f"`{user_id}` is reported. Use ,c to add on a report.", ephemeral=True)
        return
    if trusted:
        await interaction.followup.send(
            f"`{user_id}` is trusted. Ask adm+ to dismiss them before using ,c to report.", ephemeral=True)
        return
    existing_entry = inprogresscol.find_one({"user_id": user.id})
    if existing_entry:
        # ongoing vote
        if "vote_channel_id" in existing_entry:
            vote_channel_id = existing_entry["vote_channel_id"]
            vote_message_id = existing_entry["_id"]
            vote_channel = bot.get_channel(vote_channel_id)
            if not vote_channel:
                vote_channel = await bot.fetch_channel(vote_channel_id)
            try:
                vote_message = await vote_channel.fetch_message(vote_message_id)
            except discord.NotFound:
                return await interaction.followup.send(
                    "This message could not be found. It may have been deleted.", ephemeral=True)
            await interaction.followup.send(
                f"There already exists an ongoing vote on `{user.id}`: {vote_message.jump_url}")
        # ongoing report
        else:
            channel_id = existing_entry["channel_id"]
            message_id = existing_entry["_id"]
            thread = await bot.fetch_channel(channel_id)
            try:
                message = await thread.fetch_message(message_id)
            except discord.NotFound:
                return await interaction.followup.send(
                    "This message could not be found. It may have been deleted.", ephemeral=True)
            await interaction.followup.send(
                f"There already exists an ongoing report on `{user.id}`: {message.jump_url}")
        return
    async def upload_attachment(att):
        if not att:
            return None
        if not att.content_type.startswith("image/"):
            return None
        channel = bot.get_channel(PROOFS_CHANNEL)
        sent = await channel.send(file=await att.to_file())
        return sent.attachments[0].url if sent.attachments else None
    alt_proofs_raw = [alt_proof1, alt_proof2, alt_proof3, alt_proof4, alt_proof5]
    alt_proof_links = []
    for att in alt_proofs_raw:
        url = await upload_attachment(att)
        if url:
            alt_proof_links.append(url)
    proof_raw = [proof1, proof2, proof3, proof4, proof5, proof6, proof7, proof8, proof9, proof10]
    proof_links = []
    for att in proof_raw:
        url = await upload_attachment(att)
        if url:
            proof_links.append(url)
    alt_ids = []
    if alts:
        for alt in alts.split():
            try:
                alt_user = await bot.fetch_user(int(alt.strip("<@>")))
                alt_ids.append(alt_user.id)
            except:
                pass
    alt_string = alts_string(alt_ids) if alt_ids else ""
    if contributor:
        contributor_value = f"<@{contributor.id}>"
    else:
        contributor_value = "Anonymous"
    r_profile_list = [
        alt_string,                    # [0] alts
        "",                            # [1] other tags (auto below)
        alt_proof_links               # [2] alts proofs
    ]
    sorted_tags = sort_user_tags(tags.title().split(", "))
    case_title = sorted_tags[0]
    r_profile_list[1] = selected_string(sorted_tags[1:])
    games_map = {g.lower(): g for g in games_list}
    filtered_games = []
    if games:
        for g in games.split(","):
            key = g.strip().lower()
            if key in games_map and games_map[key] not in filtered_games:
                filtered_games.append(games_map[key])
    games_string = ", ".join(filtered_games) if filtered_games else "N/A"
    add_case_list = {
        "date_added": f"<t:{round(int(discord.utils.utcnow().timestamp()))}:D> (<t:{round(int(discord.utils.utcnow().timestamp()))}:R>)",
        "games": games_string,
        "tags": selected_string(sorted_tags),
        "reason": reason,
        "contributor": contributor_value,
        "staff": f"<@{interaction.user.id}>",
        "accepted_by": "",
        "proofs": proof_links
    }
    r_profile = format_user_r_profile(user, r_profile_list, case_title)
    add_case = format_user_add_case(add_case_list, case_title)
    embeds = [r_profile, add_case]
    msg = await interaction.followup.send(
        content=f"Initializing report on `{user_id}`...",
        embeds=embeds,
        view=UserProofsView()
    )
    inprogresscol.insert_one({
        "_id": msg.id,
        "user_id": user_id,
        "requested_by": interaction.user.id,
        "channel_id": interaction.channel.id,
        "r_profile_list": r_profile_list,
        "add_case_list": add_case_list,
        "title": case_title,
        "case_title": case_title
    })
    if alt_proof_links:
        image_embeds = image_links_to_embeds(r_profile_list[2])
        await interaction.followup.send(f"Alts Proofs for `{user.id}`", embeds=image_embeds)
    if proof_links:
        image_embeds = image_links_to_embeds(add_case_list["proofs"])
        await interaction.followup.send(f"Proofs for `{user.id}`", embeds=image_embeds)

@bot.tree.command(name="merge", description="Merges the reports of two users. This action is irreversible.")
@app_commands.describe(main="Main", alt="Alt")
@app_commands.checks.has_any_role(adm_ping, sr_ping)
async def merge_reports(interaction: discord.Interaction, main: str, alt: str):
    await interaction.response.defer()
    try:
        main_id = int(main.strip().replace("<@", "").replace(">", ""))
        main = bot.get_user(main_id) or await bot.fetch_user(main_id)
    except Exception:
        return await interaction.followup.send("Please provide a valid main user id.")
    try:
        alt_id = int(alt.strip().replace("<@", "").replace(">", ""))
        alt = bot.get_user(alt_id) or await bot.fetch_user(alt_id)
    except Exception:
        return await interaction.followup.send("Please provide a valid alt user id.")

    if main.id == alt.id:
        return await interaction.followup.send("You cannot merge a user into themselves.")

    main_query = {"_id": str(main.id)}
    main_profile = userscol.find_one(main_query)
    alt_query = {"_id": str(alt.id)}
    alt_profile = userscol.find_one(alt_query)

    if not main_profile and not alt_profile:
        return await interaction.followup.send("Neither user has a reported profile.")
    if not main_profile:
        return await interaction.followup.send(f"Report on main user `{main.id}` not found.")
    if not alt_profile:
        return await interaction.followup.send(f"Report on alt user `{alt.id}` not found.")

    try:
        r_profile_list1 = main_profile.get("r_profile_list", ["", "", []])
        r_profile_list2 = alt_profile.get("r_profile_list", ["", "", []])

        main_alts = r_profile_list1[0].strip("`").split() if r_profile_list1[0] else []
        alt_alts = r_profile_list2[0].strip("`").split() if r_profile_list2[0] else []

        all_alts = list(set(main_alts + alt_alts))
        if str(alt.id) not in all_alts:
            all_alts.append(str(alt.id))
        if str(main.id) in all_alts:
            all_alts.remove(str(main.id))

        merged_alts_string = alts_string(all_alts) if all_alts else ""

        proofs1 = r_profile_list1[2] if isinstance(r_profile_list1[2], list) else []
        proofs2 = r_profile_list2[2] if isinstance(r_profile_list2[2], list) else []
        merged_alts_proofs = proofs1 + proofs2

        merged_tags_list = []
        raw_cases = []

        no_of_cases1 = len(main_profile) - 2
        for i in range(1, no_of_cases1 + 1):
            case = main_profile.get(str(i))
            if case:
                raw_cases.append(case)
                if "tags" in case and case["tags"]:
                    for tag in case["tags"].split(", "):
                        merged_tags_list.append(tag)
        no_of_cases2 = len(alt_profile) - 2
        for i in range(1, no_of_cases2 + 1):
            case = alt_profile.get(str(i))
            if case:
                raw_cases.append(case)
                if "tags" in case and case["tags"]:
                    for tag in case["tags"].split(", "):
                        merged_tags_list.append(tag)

        def get_case_timestamp(case_dict):
            date_str = case_dict.get("date_added", "")
            match = re.search(r"<t:(\d+)", date_str)
            return int(match.group(1)) if match else 0

        merged_cases = sorted(raw_cases, key=get_case_timestamp)
        unique_tags = list(set(merged_tags_list))
        merged_tags_list = sort_user_tags(unique_tags)
        all_other_tags = selected_string(merged_tags_list[1:]) if len(merged_tags_list) > 1 else ""

        merged_r_profile_list = [
            merged_alts_string,
            all_other_tags,
            merged_alts_proofs
        ]

        merged_profile = {
            "_id": str(main.id),
            "r_profile_list": merged_r_profile_list
        }

        for i, case in enumerate(merged_cases, start=1):
            merged_profile[str(i)] = case

        main_backup = copy.deepcopy(main_profile)
        alt_backup = copy.deepcopy(alt_profile)
        alt_backups = {}

        for alt_id in alt_alts:
            doc = userscol.find_one({"_id": alt_id})
            if doc:
                alt_backups[alt_id] = copy.deepcopy(doc)

        try:
            userscol.replace_one(main_query, merged_profile, upsert=True)

            userscol.replace_one(alt_query, {"_id": str(alt.id), "main": str(main.id)}, upsert=True)

            for alt_id in alt_alts:
                userscol.replace_one(
                    {"_id": alt_id},
                    {"_id": alt_id, "main": str(main.id)},
                    upsert=True
                )
        except Exception:
            userscol.replace_one(main_query, main_backup, upsert=True)
            userscol.replace_one(alt_query, alt_backup, upsert=True)
            for alt_id, doc in alt_backups.items():
                userscol.replace_one({"_id": alt_id}, doc, upsert=True)
            raise

        await interaction.followup.send(f"Successfully merged `{alt.id}` into `{main.id}`.")

    except Exception as e:
        await interaction.followup.send(f"An unexpected error occurred: {e}")

disable = app_commands.Group(name="disable", description="Disable.")
bot.tree.add_command(disable)

@disable.command(
    name="vote",
    description="Disables an active staff vote."
)
@app_commands.describe(
    user_id="User ID",
    guild_id="Server ID",
    account_id="Game UID"
)
@app_commands.checks.has_role(adm_ping)
async def disable_vote(
    interaction: discord.Interaction,
    user_id: str | None = None,
    guild_id: str | None = None,
    account_id: str | None = None,
):
    provided = sum(x is not None for x in (user_id, guild_id, account_id))
    if provided != 1:
        return await interaction.response.send_message(
            "Please provide exactly one of `user_id`, `guild_id`, or `account_id`.", ephemeral=True)
    if user_id is not None:
        session = inprogresscol.find_one({"user_id": int(user_id), "vote_channel_id": {"$exists": True}})
        entity = f"user `{user_id}`"
    elif guild_id is not None:
        session = inprogresscol.find_one({"guild_id": int(guild_id), "vote_channel_id": {"$exists": True}})
        entity = f"server `{guild_id}`"
    else:
        session = inprogresscol.find_one({"account_id": account_id, "vote_channel_id": {"$exists": True}})
        entity = f"account `{account_id}`"
    if session is None:
        return await interaction.response.send_message(f"No active vote found for {entity}.", ephemeral=True)
    try:
        vote_channel = await bot.fetch_channel(session["vote_channel_id"])
        vote_message = await vote_channel.fetch_message(session["_id"])
    except discord.NotFound:
        inprogresscol.delete_one({"_id": session["_id"]})
        return await interaction.response.send_message(
            "The vote message no longer exists. The stale session has been removed.", ephemeral=True)
    await vote_message.edit(view=None)
    try:
        report_thread = await bot.fetch_channel(session["channel_id"])
        report_message = await report_thread.fetch_message(session["message_id"])
        await report_message.edit(content=f"**Disabled by {interaction.user.mention}.**", view=None)
    except Exception:
        pass
    inprogresscol.delete_one({"_id": session["_id"]})
    thread = vote_message.channel
    try:
        await thread.edit(
            name=f"d-{thread.name}",
            archived=True,
            locked=True
        )
    except Exception:
        pass
    await interaction.response.send_message(f"Disabled active vote for {entity}.")

@disable.command(
    name="report",
    description="Disables an active report or appeal."
)
@app_commands.describe(
    user_id="User ID",
    guild_id="Server ID",
    account_id="Game UID"
)
@app_commands.checks.has_any_role(adm_ping, sr_ping)
async def disable_report(
    interaction: discord.Interaction,
    user_id: str | None = None,
    guild_id: str | None = None,
    account_id: str | None = None,
):
    provided = sum(x is not None for x in (user_id, guild_id, account_id))
    if provided != 1:
        await interaction.response.send_message(
            "Please provide exactly one of `user_id`, `guild_id`, or `account_id`.", ephemeral=True)
        return
    if user_id is not None:
        session = inprogresscol.find_one({"user_id": int(user_id)})
        entity = f"user `{user_id}`"
    elif guild_id is not None:
        session = inprogresscol.find_one({"guild_id": int(guild_id)})
        entity = f"server `{guild_id}`"
    else:
        session = inprogresscol.find_one({"account_id": account_id})
        entity = f"account `{account_id}`"
    if session is None:
        return await interaction.response.send_message(
            f"No active report or appeal found for {entity}.", ephemeral=True)
    try:
        channel = await bot.fetch_channel(session["channel_id"])
        message = await channel.fetch_message(session["_id"])
    except discord.NotFound:
        inprogresscol.delete_one({"_id": session["_id"]})
        return await interaction.response.send_message(
            "The report message no longer exists. The stale session has been removed.", ephemeral=True)
    await message.edit(
        content=f"**Disabled by {interaction.user.mention}.**", view=None)
    inprogresscol.delete_one({"_id": session["_id"]})
    await interaction.response.send_message(
        f"Disabled active report for {entity}.")

def is_int(value):
    try:
        int(value)
        return True
    except (ValueError, TypeError):
        return False

settings = app_commands.Group(name="set", description="Set.")
bot.tree.add_command(settings)

@settings.command(name="credits", description="Set credits to a certain value.")
@app_commands.checks.has_role(adm_ping)
async def set_credits(interaction: discord.Interaction, user: str, category: Literal["reports", "tickets", "reviews", "closes", "votes"], timeframe: Literal["weekly", "alltime"], value: int):
    try:
        user = await bot.fetch_user(int(user.strip("<@>")))
    except Exception:
        pass
    else:
        user_id = user.id
        user_query = {"_id": str(user_id)}
        trusteduser_profile = trusteduserscol.find_one(user_query)
        if trusteduser_profile:
            member = interaction.guild.get_member(int(user_id))
            if not member:
                await interaction.response.send_message("User not in server.", ephemeral=True)
                return
            staff_weekly = staffweeklycol.find_one(user_query)
            if not staff_weekly:
                await interaction.response.send_message("User not appointed as current TRI Staff.", ephemeral=True)
                return
            if category == "reports":
                if timeframe == "weekly":
                    staff_weekly["weekly_reports"] = value
                    staffweeklycol.replace_one(user_query, staff_weekly)
                if timeframe == "alltime":
                    trusteduser_profile["reports"] = value
                    trusteduserscol.replace_one(user_query, trusteduser_profile)
            if category == "tickets":
                if timeframe == "weekly":
                    staff_weekly["weekly_tickets"] = value
                    staffweeklycol.replace_one(user_query, staff_weekly)
                if timeframe == "alltime":
                    trusteduser_profile["tickets"] = value
                    trusteduserscol.replace_one(user_query, trusteduser_profile)
            if category == "reviews":
                if timeframe == "weekly":
                    staff_weekly["weekly_reviews"] = value
                    staffweeklycol.replace_one(user_query, staff_weekly)
                if timeframe == "alltime":
                    trusteduser_profile["reviews"] = value
                    trusteduserscol.replace_one(user_query, trusteduser_profile)
            if category == "closes":
                if timeframe == "weekly":
                    staff_weekly["weekly_closes"] = value
                    staffweeklycol.replace_one(user_query, staff_weekly)
                if timeframe == "alltime":
                    trusteduser_profile["closes"] = value
                    trusteduserscol.replace_one(user_query, trusteduser_profile)
            if category == "votes":
                if timeframe == "alltime":
                    trusteduser_profile["votes"] = value
                    trusteduserscol.replace_one(user_query, trusteduser_profile)
            await interaction.response.send_message(f"`{user_id}`’s **{timeframe} {category}** has been set to **{value}**.", ephemeral=True)

@bot.tree.command(name="appoint", description="Appoint a staff/trusted user.")
@app_commands.describe(user="User to appoint", category="staff/mm/pilot/trader")
@app_commands.checks.has_role(adm_ping)
async def appoint(interaction: discord.Interaction, user: str, category: Literal["staff", "mm", "pilot", "trader"]):
    try:
        user = await bot.fetch_user(int(user.strip("<@>")))
    except Exception:
        pass
    else:
        user_id = user.id
        user_query = {"_id": str(user_id)}
        trusteduser_profile = trusteduserscol.find_one(user_query)
        if trusteduser_profile:
            if category == "staff":
                member = interaction.guild.get_member(int(user_id))
                if not member: return
                trusteduser_profile["current_staff"] = 1
                trusteduser_profile["staff"] = 1
                trusteduserscol.replace_one(user_query, trusteduser_profile)
                if not staffweeklycol.find_one(user_query):
                    new_staff = {
                        "_id": str(user.id),
                        "weekly_reports": 0,
                        "weekly_tickets": 0,
                        "weekly_reviews": 0,
                        "weekly_closes": 0,
                    }
                    staffweeklycol.insert_one(new_staff)
                await interaction.response.send_message(f"`{user.id}` has been appointed as current TRI Staff.")
            elif category == "mm":
                trusteduser_profile["mm"] = 1
                trusteduserscol.replace_one(user_query, trusteduser_profile)
                await interaction.response.send_message(f"`{user.id}` has been appointed as Professional MM.")
            elif category == "pilot":
                trusteduser_profile["pilot"] = 1
                trusteduserscol.replace_one(user_query, trusteduser_profile)
                await interaction.response.send_message(f"`{user.id}` has been appointed as Professional Pilot.")
            elif category == "trader":
                trusteduser_profile["trader"] = 1
                trusteduserscol.replace_one(user_query, trusteduser_profile)
                await interaction.response.send_message(f"`{user.id}` has been appointed as Trusted Trader.")
            else:
                await interaction.response.send_message(f"Please enter a valid role.", ephemeral=True)
        else:
            if category == "staff":
                member = interaction.guild.get_member(int(user_id))
                if not member: return
                new_user = {
                    "_id": str(user.id),
                    "current_staff": 1,
                    "staff": 1,
                    "mm": 0,
                    "pilot": 0,
                    "trader": 0,
                    "reports": 0,
                    "tickets": 0,
                    "reviews": 0,
                    "closes": 0,
                    "votes": 0,
                }
                trusteduserscol.insert_one(new_user)
                new_staff = {
                    "_id": str(user.id),
                    "weekly_reports": 0,
                    "weekly_tickets": 0,
                    "weekly_reviews": 0,
                    "weekly_closes": 0,
                }
                staffweeklycol.insert_one(new_staff)
                await interaction.response.send_message(f"`{user.id}` has been appointed as current TRI Staff.")
            elif category == "mm":
                new_user = {
                    "_id": str(user.id),
                    "current_staff": 0,
                    "staff": 0,
                    "mm": 1,
                    "pilot": 0,
                    "trader": 0,
                    "reports": 0,
                    "tickets": 0,
                    "reviews": 0,
                    "closes": 0,
                    "votes": 0,
                }
                trusteduserscol.insert_one(new_user)
                await interaction.response.send_message(f"`{user.id}` has been appointed as Professional MM.")
            elif category == "pilot":
                new_user = {
                    "_id": str(user.id),
                    "current_staff": 0,
                    "staff": 0,
                    "mm": 0,
                    "pilot": 1,
                    "trader": 0,
                    "reports": 0,
                    "tickets": 0,
                    "reviews": 0,
                    "closes": 0,
                    "votes": 0,
                }
                trusteduserscol.insert_one(new_user)
                await interaction.response.send_message(f"`{user.id}` has been appointed as Professional Pilot.")
            elif category == "trader":
                new_user = {
                    "_id": str(user.id),
                    "current_staff": 0,
                    "staff": 0,
                    "mm": 0,
                    "pilot": 0,
                    "trader": 1,
                    "reports": 0,
                    "tickets": 0,
                    "reviews": 0,
                    "closes": 0,
                    "votes": 0,
                }
                trusteduserscol.insert_one(new_user)
                await interaction.response.send_message(f"`{user.id}` has been appointed as Trusted Trader.")
            else:
                await interaction.response.send_message(f"Please enter a valid role.", ephemeral=True)

@bot.tree.command(name="dismiss", description="Dismiss a staff/trusted user.")
@app_commands.describe(user="User to dismiss", category="staff/mm/pilot/trader")
@app_commands.checks.has_role(adm_ping)
async def dismiss(interaction: discord.Interaction, user: str, category: Literal["staff", "mm", "pilot", "trader"]):
    try:
        user = await bot.fetch_user(int(user.strip("<@>")))
    except Exception:
        pass
    else:
        user_id = user.id
        user_query = {"_id": str(user_id)}
        trusteduser_profile = trusteduserscol.find_one(user_query)
        if trusteduser_profile:
            if category == "staff":
                if trusteduser_profile["current_staff"] == 1:
                    trusteduser_profile["current_staff"] = 0
                    staffweeklycol.delete_one(user_query)
                elif trusteduser_profile["current_staff"] == 0:
                    trusteduser_profile["staff"] = 0
                trusteduserscol.replace_one(user_query, trusteduser_profile)
                await interaction.response.send_message(f"`{user.id}` has been dismissed as TRI Staff.")
            elif category == "mm":
                trusteduser_profile["mm"] = 0
                trusteduserscol.replace_one(user_query, trusteduser_profile)
                await interaction.response.send_message(f"`{user.id}` has been dismissed as Professional MM.")
            elif category == "pilot":
                trusteduser_profile["pilot"] = 0
                trusteduserscol.replace_one(user_query, trusteduser_profile)
                await interaction.response.send_message(f"`{user.id}` has been dismissed as Professional Pilot.")
            elif category == "trader":
                trusteduser_profile["trader"] = 0
                trusteduserscol.replace_one(user_query, trusteduser_profile)
                await interaction.response.send_message(f"`{user.id}` has been dismissed as Trusted Trader.")
            else:
                await interaction.response.send_message(f"Please enter a valid role.", ephemeral=True)
            trusteduser_profile = trusteduserscol.find_one(user_query)
            if (
                    trusteduser_profile["staff"] == 0
                    and trusteduser_profile["mm"] == 0
                    and trusteduser_profile["pilot"] == 0
                    and trusteduser_profile["trader"] == 0
                    and not trusteduser_profile.get("reports")
                    and not trusteduser_profile.get("reviews")
                    and not trusteduser_profile.get("votes")
            ):
                trusteduserscol.delete_one(user_query)

trusted = app_commands.Group(name="trusted", description="Manage trusted servers.")
bot.tree.add_command(trusted)

@trusted.command(name="add", description="Add a server as trusted.")
@app_commands.describe(server="Server invite")
@app_commands.checks.has_role(o5_role)
async def trusted_add(interaction: discord.Interaction, server: str):
    try:
        invite = await bot.fetch_invite(server)
    except discord.NotFound:
        await interaction.response.send_message("The invite link is **invalid** or **expired**.", ephemeral=True)
    except discord.Forbidden:
        await interaction.response.send_message("Unable to access details of invite.", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"An error occurred: {e}", ephemeral=True)
    else:
        guild_id = invite.guild.id
        server_query = {"_id": str(guild_id)}
        trustedserver_profile = trustedserverscol.find_one(server_query)
        if trustedserver_profile:
            await interaction.response.send_message(f"`{guild_id}` is already in Trusted Servers.")
        else:
            trustedserverscol.insert_one(server_query)
            await interaction.response.send_message(f"`{guild_id}` has been added to Trusted Servers.")

@trusted.command(name="remove", description="Remove a server from Trusted Servers.")
@app_commands.describe(server="Server invite or ID")
@app_commands.checks.has_role(o5_role)
async def trusted_remove(interaction: discord.Interaction, server: str):
    server_query = {"_id": server}
    trustedserver_profile = trustedserverscol.find_one(server_query)
    if trustedserver_profile:
        trustedserverscol.delete_one(server_query)
    else:
        try:
            invite = await bot.fetch_invite(server)
        except discord.NotFound:
            await interaction.response.send_message("The invite link is **invalid** or **expired**.", ephemeral=True)
        except discord.Forbidden:
            await interaction.response.send_message("Unable to access details of invite.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"An error occurred: {e}", ephemeral=True)
        else:
            guild_id = invite.guild.id
            server_query = {"_id": str(guild_id)}
            trustedserver_profile = trustedserverscol.find_one(server_query)
            if trustedserver_profile:
                trustedserverscol.delete_one(server_query)
                await interaction.response.send_message(f"`{guild_id}` has been removed from Trusted Servers.")
            else:
                await interaction.response.send_message(f"`{guild_id}` is not in Trusted Servers.")

# sync
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