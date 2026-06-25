#  yuelyxia  ©  2025 – 2026

from dotenv import load_dotenv
import os
load_dotenv()

import pymongo

import asyncio
import re

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

intents = discord.Intents.all()
bot = commands.Bot(command_prefix=',', help_command=None, intents=intents)

red_tags = ["Scammer", "Scam Server Owner", "Raider", "Plagiarist", "Fake Event Host", "Impersonator", "Vouch Scammer"]
yellow_tags = ["Suspect", "Service Ban", "Unprofessional MM", "Unprofessional Pilot", "Unprofessional IDV MM", "Unprofessional Staff", "Unprofessional Supervisor", "Improper Conduct"]

red_server_tags = ["Scam Server", "Impersonator Server", "Fake Vouch Server", "Fake Event Server"]
yellow_server_tags = ["Suspect Server"]

red_account_tags = ["Scammed Account", "Leeched Account"]
yellow_account_tags = ["Under Investigation", "Advertised by Scammer"]

# formatting functions

def default_user_profile(user):
    profile = discord.Embed()
    profile.set_thumbnail(url=f"{user.display_avatar}")
    profile.description = f"{user.mention} {user.display_name}\n`{user.name}`\n`{user.id}`"
    profile.description += f"\n-# **Account Created** – <t:{round(int(user.created_at.timestamp()))}:D> (<t:{round(int(user.created_at.timestamp()))}:R>)" + '\n'
    profile.set_footer(text="✦　This user is unreported.")
    return profile
def default_server_profile(guild):
    profile = discord.Embed()
    if guild.icon:
        profile.set_thumbnail(url=f"{guild.icon.url}")
    profile.description = f"{guild.name}\n`{guild.id}`"
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
        tags_strings.append(case[2])
    for tags_string in tags_strings:
        tags_list = tags_string.split(", ")
        for tag in tags_list:
            all_tags_list.append(tag)
    all_tags_list = sort_user_tags(all_tags_list)
    title = all_tags_list[0]
    newest_case_tags = cases[-1][2].split(", ")
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
        tags_strings.append(case[1])
    for tags_string in tags_strings:
        tags_list = tags_string.split(", ")
        for tag in tags_list:
            all_tags_list.append(tag)
    all_tags_list = sort_server_tags(all_tags_list)
    title = all_tags_list[0]
    newest_case_tags = cases[-1][1].split(", ")
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
    for i in range(0, len(tags)):
        tag = tags[i]
        if tag == "Ex-offender":
            sorted_tags.append(tag)
    for tag_to_find in red_tags:
        for i in range(0, len(tags)):
            tag = tags[i]
            if tag == tag_to_find:
                sorted_tags.append(tag)
    for tag_to_find in yellow_tags:
        for i in range(0, len(tags)):
            tag = tags[i]
            if tag == tag_to_find:
                sorted_tags.append(tag)
    return sorted_tags
def sort_server_tags(tags):
    sorted_tags = []
    for tag_to_find in red_server_tags:
        for i in range(0, len(tags)):
            tag = tags[i]
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
        trusted_embed = discord.Embed(title="TRI Staff", colour=0xbba8dd)
    elif trusteduser_profile["staff"] == 1:
        trusted_embed = discord.Embed(title="Former TRI Staff", colour=0x9279b5)
    else:
        trusted_embed = discord.Embed(title="Trusted User", colour=0x9279b5)
    trusted_embed.set_thumbnail(url=f"{user.display_avatar}")
    trusted_embed.description = f"{user.mention} {user.display_name}\n`{user.name}`\n`{user.id}`"
    trusted_embed.description += "\n-# **Account Created** – " + f"<t:{round(int(user.created_at.timestamp()))}:D> (<t:{round(int(user.created_at.timestamp()))}:R>)" + '\n'
    trusted_embed.set_footer(text="✦　This user is trusted.")
    if trusteduser_profile["staff"] == 1:
        trusted_embed.description += "### Staff Info"
        trusted_embed.description += f"\n**Reports** – {trusteduser_profile["reports"]}"
        trusted_embed.description += f"\n**Reviews** – {trusteduser_profile["reviews"]}"
        trusted_embed.description += f"\n**Votes** – {trusteduser_profile["votes"]}"
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
        r_profile = discord.Embed(colour=0xFFD643)
        colour = "\u001b[1;33m"
    elif title in red_tags:
        r_profile = discord.Embed(colour=0xFF0045)
        colour = "\u001b[1;31m"
    elif title in yellow_tags:
        r_profile = discord.Embed(colour=0xFFD643)
        colour = "\u001b[1;33m"
    else:
        r_profile = discord.Embed()
        colour = "\u001b[0m"
    r_profile.set_thumbnail(url=f"{user.display_avatar}")
    r_profile.description = (f"```ansi\n{colour}{title}\u001b[0m\n```")
    r_profile.description += f"{user.mention} {user.display_name}\n`{user.name}`\n`{user.id}`"
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
        add_case.description = f"**{add_case_list[2]}**\n"
        """
        tags_list = add_case_list[2].split(", ")
        tags_strings = []
        for tag in tags_list:
            if tag == "Ex-offender":
                colour = "\u001b[1;33m"
            elif tag in red_tags:
                colour = "\u001b[1;31m"
            elif tag in yellow_tags:
                colour = "\u001b[1;33m"
            else:
                colour = "\u001b[0m"
            tags_strings.append(f"{colour}{tag}\u001b[0m")
        tags_string = ", ".join(tags_strings)
        add_case.description = (f"```ansi\n{tags_string}\n```")
        """
        add_case.description += "-# **Date Added** – " + add_case_list[0]
        add_case.description += "\n-# **Game(s)** – " + add_case_list[1]
        #add_case.description += f"\n\n-# **Contributor** – {add_case_list[4]}"
        add_case.description += f"\n\n**Reason** – {add_case_list[3]}\n\u200b"
        #add_case.description += f"\n> **Contributor** – {add_case_list[4]}\n> **TRI Staff** – {add_case_list[5]}\n> **Accepted by** – {add_case_list[6]}"
        add_case.description += f"\n-# **Contributor** – {add_case_list[4]}\n-# **TRI Staff** – {add_case_list[5]}\n-# **Accepted by** – {add_case_list[6]}"
        """add_case.add_field(name="Contributor", value=f"-# {add_case_list[4]}")
        add_case.add_field(name="TRI Staff", value=f"-# {add_case_list[5]}")
        add_case.add_field(name="Accepted by", value=f"-# {add_case_list[6]}")"""

    return add_case
def format_trustedserver_profile(guild):
    if guild.id == TRI_Archive:
        trusted_embed = discord.Embed(title="Trade Report Investigation Archive", colour=0xbba8dd)
    else:
        trusted_embed = discord.Embed(title="Trusted Server", colour=0x9279b5)
    if guild.icon:
        trusted_embed.set_thumbnail(url=f"{guild.icon.url}")
    trusted_embed.description = f"{guild.name}\n`{guild.id}`"
    if guild.created_at:
        trusted_embed.description += "\n**Server Created** – " + f"<t:{round(int(guild.created_at.timestamp()))}:D> (<t:{round(int(guild.created_at.timestamp()))}:R>)" + '\n'
    if guild.banner:
        trusted_embed.set_image(url=guild.banner.url)
    return trusted_embed
def format_server_r_profile(guild, r_profile_list, title):
    if title in red_server_tags:
        r_profile = discord.Embed(colour=0xCF2D53)
        colour = "\u001b[1;31m"
    elif title in yellow_server_tags:
        r_profile = discord.Embed(colour=0xd9b534)
        colour = "\u001b[1;33m"
    else:
        r_profile = discord.Embed()
        colour = "\u001b[0m"
    if guild.icon:
        r_profile.set_thumbnail(url=f"{guild.icon.url}")
    r_profile.description = f"```ansi\n{colour}{title}\u001b[0m\n```"
    r_profile.description += f"{guild.name}\n`{guild.id}`"
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
    add_case.description = f"**{add_case_list[1]}**\n"
    """
    tags_list = add_case_list[1].split(", ")
    tags_strings = []
    for tag in tags_list:
        if tag in red_server_tags:
            colour = "\u001b[1;31m"
        elif tag in yellow_server_tags:
            colour = "\u001b[1;33m"
        else:
            colour = "\u001b[0m"
        tags_strings.append(f"{colour}{tag}\u001b[0m")
    tags_string = ", ".join(tags_strings)
    add_case.description = (f"```ansi\n{tags_string}\n```")
    """
    add_case.description += "-# **Date Added** – " + add_case_list[0]
    add_case.description += f"\n\n**Reason** – {add_case_list[2]}\n\u200b"
    add_case.description += f"\n-# **Contributor** – {add_case_list[3]}\n-# **TRI Staff** – {add_case_list[4]}\n-# **Accepted by** – {add_case_list[5]}"
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
    profile.description = f"**{game}**ㆍ`{uid}`"
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
    latest_tags = latest_case[2].split(", ")
    all_tags_list = []
    for case in cases:
        all_tags_list.extend(case[2].split(", "))
    all_tags_list = sort_account_tags(all_tags_list)
    if "Recovered Account" in latest_tags:
        title = "Recovered Account"
    else:
        title = all_tags_list[0]
    #
    newest_case_tags = cases[-1][2].split(", ")
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
    r_profile.description += f"**{game}**\n`{uid}`"
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
        add_case.description = f"**{add_case_list[2] or "TBC"}**\n"
        add_case.description += "-# **Date Added** – " + add_case_list[0]
        add_case.description += f"\n-# **Related User(s)** – {add_case_list[1] or "None"}"
        add_case.description += f"\n\n**Reason** – {add_case_list[3]}\n\u200b"
        add_case.description += f"\n-# **Contributor** – {add_case_list[4]}\n-# **TRI Staff** – {add_case_list[5]}\n-# **Accepted by** – {add_case_list[6]}"
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

@bot.event
async def on_ready():
    update_reports_count.start()


# check

@bot.command(name='c', help='Checks a user or server.')
async def c(ctx, *, to_check: str = None):
    if ctx.guild.id == TRI_Archive:
        return
    requested_by = ctx.author
    if to_check: to_check = to_check.strip()
    if to_check and " " in to_check:
        match = re.match(r"(.+?)\s+(\S+)$", to_check)
        if match:
            game_input = match.group(1).strip()
            uid_input = match.group(2).strip()
            game = format_game(game_input)
            if game is None:
                return await ctx.reply(f"The game {game_input} is **invalid** or **unsupported**.")
            game_uid = format_game_uid(game, uid_input)
            account_query = {"_id": str(game_uid)}
            account_profile = accountscol.find_one(account_query)
            if account_profile:
                if len(account_profile) == 2:
                    main = account_profile['main']
                    account_query = {"_id": main}
                    main_profile = accountscol.find_one(account_query)
                    await ctx.reply(
                            f"Account `{game_uid}` is linked to `{main}`.",
                            embeds=reported_account_profile(main, main_profile),
                            view=ReportedAccountView(main, main_profile, requested_by,
                                                     len(main_profile) - 2))
                else:
                    await ctx.reply(f"Account is reported.",
                                    embeds=reported_account_profile(game_uid, account_profile),
                                    view=ReportedAccountView(game_uid, account_profile, requested_by,
                                                             len(account_profile) - 2))
            #
            else:
                profile = default_account_profile(game_uid)
                await ctx.reply(embed=profile, view=MemberView())
    else:
        if to_check == None:
            user = ctx.author
            user_id = user.id
            user_query = {"_id": str(user_id)}
            trusteduser_profile = trusteduserscol.find_one(user_query)
            if trusteduser_profile and not (
                    trusteduser_profile["current_staff"] == 0 and trusteduser_profile["staff"] == 0 and trusteduser_profile["mm"] == 0 and trusteduser_profile["pilot"] == 0 and trusteduser_profile[
                        "trader"] == 0):
                trusted_embed = format_trusteduser_profile(user, trusteduser_profile)
                await ctx.reply("User is trusted.", embed=trusted_embed)
            #
            else:
                user_profile = userscol.find_one(user_query)
                if user_profile:
                    if len(user_profile) == 2:
                        main = user_profile['main']
                        user_query = {"_id": main}
                        main_user_profile = userscol.find_one(user_query)
                        main_user = await bot.fetch_user(int(main))
                        #
                        await ctx.reply(f"User `{user.id}` is reported as alt of `{main}`.",
                                            embeds=reported_user_profile(main_user, main_user_profile),
                                            view=ReportedUserView(main_user, main_user_profile, requested_by,
                                                                  len(main_user_profile) - 2))
                    #
                    else:
                        await ctx.reply(f"User is reported.",
                                            embeds=reported_user_profile(user, user_profile),
                                            view=ReportedUserView(user, user_profile, requested_by, len(user_profile) - 2))
                #
                else:
                    profile = default_user_profile(user)
                    await ctx.reply(embed=profile, view=MemberView())

        else:
            try:
                if int(to_check.strip('<@>')) in tri_bots:
                    user = await bot.fetch_user(int(to_check.strip('<@>')))
                    profile = discord.Embed(colour=0xffffff)
                    profile.set_thumbnail(url=f"{user.display_avatar.url}")
                    profile.description = f"{user.mention} {user.display_name}\n`{user.name}`\n`{user.id}`{user.mention} {user.display_name}\n`{user.name}`\n`{user.id}`"
                    profile.description += "\n-# **Account Created** – " + f"<t:{round(int(user.created_at.timestamp()))}:D> (<t:{round(int(user.created_at.timestamp()))}:R>)" + '\n'
                    if user.id == 1450073025818136598:
                        profile.description += "\n**TETO** ┈ report bot for `/tri`"
                    elif user.id == 1457249982104211467:
                        profile.description += "\n**TETO++** ┈ user check bot for `/tri`"
                    elif user.id == 1457382953293320304:
                        profile.description += "\n**NERU** ┈ alts check bot for `/tri`"
                    elif user.id == 1457309787044839477:
                        profile.description += "\n**MIKU** ┈ tickets bot for `/tri`"
                    profile.set_footer(text="✦　TRI bot")
                    await ctx.reply(embed=profile)
                    return
            except Exception: pass
            try:
                user = await bot.fetch_user(int(to_check.strip('<@>')))
            except discord.NotFound:
                server_query = {"_id": to_check.strip('<@>')}
                trustedserver_profile = trustedserverscol.find_one(server_query)
                if trustedserver_profile:
                    trusted_embed = format_trustedserver_profile(UnknownGuild(int(to_check.strip('<@>'))))
                    await ctx.reply("Server is trusted.", embed=trusted_embed)
                else:
                    server_profile = serverscol.find_one(server_query)
                    if server_profile:  # reported server
                        await ctx.reply(f"Server is reported.",
                                        embeds=reported_server_profile(UnknownGuild(int(to_check.strip('<@>'))),
                                                                       server_profile),
                                        view=ReportedServerView(UnknownGuild(int(to_check.strip('<@>'))), server_profile,
                                                                requested_by,
                                                                len(server_profile) - 2))
                    else:  # unreported server
                        await ctx.reply(
                            "Please provide a valid user ID. To check servers, please provide a valid invite link.")

            except discord.HTTPException as e:
                await ctx.send(f"An error occurred: {e}")
            except ValueError:
                try:
                    invite = await bot.fetch_invite(to_check)
                except discord.NotFound:
                    await ctx.send("The invite link is **invalid** or **expired**.")
                except discord.Forbidden:
                    await ctx.send("Unable to access details of invite.")
                except Exception as e:
                    await ctx.send(f"An error occurred: {e}")
                else:
                    guild = invite.guild
                    guild_id = invite.guild.id
                    server_query = {"_id": str(guild_id)}
                    trustedserver_profile = trustedserverscol.find_one(server_query)
                    if trustedserver_profile:
                        trusted_embed = format_trustedserver_profile(guild)
                        await ctx.reply("Server is trusted.", embed=trusted_embed)
                    else:
                        server_profile = serverscol.find_one(server_query)
                        if server_profile:  # reported server
                            #
                            await ctx.reply(f"Server is reported.",
                                                embeds=reported_server_profile(guild, server_profile),
                                                view=ReportedServerView(guild, server_profile, requested_by,
                                                                      len(server_profile) - 2))
                        else:  # unreported server
                            profile = default_server_profile(guild)
                            #
                            await ctx.reply(embed=profile, view=MemberView())
            #
            else:
                user_id = user.id
                user_query = {"_id": str(user_id)}
                trusteduser_profile = trusteduserscol.find_one(user_query)
                if trusteduser_profile and not (
                        trusteduser_profile["current_staff"] == 0 and trusteduser_profile["staff"] == 0 and
                        trusteduser_profile["mm"] == 0 and trusteduser_profile["pilot"] == 0 and trusteduser_profile[
                            "trader"] == 0):
                    trusted_embed = format_trusteduser_profile(user, trusteduser_profile)
                    await ctx.reply("User is trusted.", embed=trusted_embed)
                else:
                    user_profile = userscol.find_one(user_query)
                    if user_profile:
                        if len(user_profile) == 2:
                            main = user_profile['main']
                            user_query = {"_id": main}
                            main_user_profile = userscol.find_one(user_query)
                            main_user = await bot.fetch_user(int(main))
                            #
                            await ctx.reply(
                                    f"User `{user.id}` is reported as alt of `{main}`.",
                                    embeds=reported_user_profile(main_user, main_user_profile),
                                    view=ReportedUserView(main_user, main_user_profile, requested_by,
                                                          len(main_user_profile) - 2))
                        else:
                            await ctx.reply(f"User is reported.",
                                                embeds=reported_user_profile(user, user_profile),
                                                view=ReportedUserView(user, user_profile, requested_by,
                                                                      len(user_profile) - 2))
                    #
                    else:
                        profile = default_user_profile(user)
                        await ctx.reply(embed=profile, view=MemberView())

@bot.command(name="mc", help="Checks a list of users (max 100), leave a space between users.")
async def mc(ctx, *, to_check: str = None):
    if ctx.guild.id == TRI_Archive:
        return
    if to_check != None:
        users = to_check.split()
        if len(users) > 100:
            return await ctx.reply("Exceeded 100 users.")
        estimated_seconds = round(len(users) * 0.5, 1)
        status_message = await ctx.reply(f"Checking **{len(users)}** users.\nEstimated time: **~{estimated_seconds}s**")
        valid_users = []
        invalid_users = []
        embeds = []
        for raw_user in users:
            try:
                user_id = int(re.sub(r"\D", "", raw_user))
                fetched_user = await bot.fetch_user(user_id)
            except:
                invalid_users.append(raw_user)
            else:
                if fetched_user not in valid_users:
                    valid_users.append(fetched_user)
        if valid_users:
            valid_users_grouped = [valid_users[i:i + 25] for i in range(0, len(valid_users), 25)]
            for group in valid_users_grouped:
                description = ""
                for user in group:
                    user_id = user.id
                    user_query = {"_id": str(user_id)}
                    trusteduser_profile = trusteduserscol.find_one(user_query)
                    if trusteduser_profile and not(trusteduser_profile["current_staff"] == 0 and trusteduser_profile["staff"] == 0 and \
                            trusteduser_profile["mm"] == 0 and trusteduser_profile["pilot"] == 0 and trusteduser_profile["trader"] == 0):
                        description += f"\n{user.mention} `{user.id}` is trusted.\n"
                    else:
                        user_profile = userscol.find_one(user_query)
                        if user_profile:
                            if len(user_profile) == 2:
                                main = user_profile['main']
                                user_query = {"_id": main}
                                main_user_profile = userscol.find_one(user_query)
                                main_user = await bot.fetch_user(int(main))
                                r_profile_list = main_user_profile["r_profile_list"]
                                no_of_cases = len(main_user_profile) - 2
                                cases = []
                                for i in range(1, no_of_cases + 1):
                                    cases.append(main_user_profile[str(i)])
                                tags_strings = []
                                all_tags_list = []
                                for case in cases:
                                    tags_strings.append(case[2])
                                for tags_string in tags_strings:
                                    tags_list = tags_string.split(", ")
                                    for tag in tags_list:
                                        all_tags_list.append(tag)
                                all_tags_list = sort_user_tags(all_tags_list)
                                all_unique_tags = list(dict.fromkeys(all_tags_list))
                                description += f"\n**{user.mention} `{user.id}` is reported as alt of {main_user.mention} `{main_user.id}` ({selected_string(all_unique_tags)}).**\n"
                            else:
                                r_profile_list = user_profile["r_profile_list"]
                                no_of_cases = len(user_profile) - 2
                                cases = []
                                for i in range(1, no_of_cases + 1):
                                    cases.append(user_profile[str(i)])
                                tags_strings = []
                                all_tags_list = []
                                for case in cases:
                                    tags_strings.append(case[2])
                                for tags_string in tags_strings:
                                    tags_list = tags_string.split(", ")
                                    for tag in tags_list:
                                        all_tags_list.append(tag)
                                all_tags_list = sort_user_tags(all_tags_list)
                                all_unique_tags = list(dict.fromkeys(all_tags_list))
                                description += f"\n**{user.mention} `{user.id}` is reported as {selected_string(all_unique_tags)}.**\n"
                        else: description += f"\n{user.mention} `{user.id}` is unreported.\n"
                embed = discord.Embed(description=description)
                embeds.append(embed)
            if invalid_users:
                invalid_users_grouped = [invalid_users[i:i + 25] for i in range(0, len(invalid_users), 25)]
                if len(invalid_users) <= 50:
                    for group in invalid_users_grouped:
                        description = ""
                        for user in group:
                            description += f"\n`{user}` is invalid.\n"
                        invalid_embed = discord.Embed(description=description)
                        embeds.append(invalid_embed)
                elif len(invalid_users) > 50:
                    description = ""
                    for user in invalid_users_grouped[0]:
                        description += f"\n`{user}` is invalid.\n"
                    invalid_embed = discord.Embed(description=description)
                    embeds.append(invalid_embed)
                    for user in invalid_users_grouped[1]:
                        description += f"\n`{user}` is invalid.\n"
                    description += f"\nThere are more than 50 invalid users.\n"
                    invalid_embed = discord.Embed(description=description)
                    embeds.append(invalid_embed)
            await status_message.edit(content=None, embeds=embeds)
        else:
            await ctx.reply("No valid users provided.")

class ReportedUserView(discord.ui.View):
    def __init__(self, user, user_profile, requested_by, current_case):
        super().__init__(timeout=None)
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
                tags_strings.append(case[2])
            for tags_string in tags_strings:
                tags_list = tags_string.split(", ")
                for tag in tags_list:
                    all_tags_list.append(tag)
            all_tags_list = sort_user_tags(all_tags_list)
            title = all_tags_list[0]
            if current_case != 1:
                prev_index = current_case-2
            try:
                prev_case_tags = cases[prev_index][2].split(", ")
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
                tags_strings.append(case[2])
            for tags_string in tags_strings:
                tags_list = tags_string.split(", ")
                for tag in tags_list:
                    all_tags_list.append(tag)
            all_tags_list = sort_user_tags(all_tags_list)
            title = all_tags_list[0]
            next_index = current_case
            try:
                next_case_tags = cases[next_index][2].split(", ")
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

    @discord.ui.button(label="𝘱𝘳𝘰𝘰𝘧𝘴", style=discord.ButtonStyle.grey, custom_id="see_proofs")
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
            image_links = cases[current_case-1][7]
            image_embeds = image_links_to_embeds(image_links)
            await interaction.followup.send(f"Proofs for `{user.id}`", embeds=image_embeds, ephemeral=True)

    @discord.ui.button(label="𝘢𝘭𝘵𝘴 𝘱𝘳𝘰𝘰𝘧𝘴", style=discord.ButtonStyle.grey, custom_id="see_alts_proofs")
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
            image_links = r_profile_list[6]
            image_embeds = image_links_to_embeds(image_links)
            await interaction.followup.send(f"Alts Proofs for `{user.id}`", embeds=image_embeds, ephemeral=True)

class ReportedServerView(discord.ui.View):
    def __init__(self, guild, server_profile, requested_by, current_case):
        super().__init__(timeout=None)
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
                tags_strings.append(case[1])
            for tags_string in tags_strings:
                tags_list = tags_string.split(", ")
                for tag in tags_list:
                    all_tags_list.append(tag)
            all_tags_list = sort_server_tags(all_tags_list)
            title = all_tags_list[0]
            if current_case != 1:
                prev_index = current_case - 2
            try:
                prev_case_tags = cases[prev_index][1].split(", ")
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
                tags_strings.append(case[1])
            for tags_string in tags_strings:
                tags_list = tags_string.split(", ")
                for tag in tags_list:
                    all_tags_list.append(tag)
            all_tags_list = sort_server_tags(all_tags_list)
            title = all_tags_list[0]
            next_index = current_case
            try:
                next_case_tags = cases[next_index][1].split(", ")
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

    @discord.ui.button(label="𝘱𝘳𝘰𝘰𝘧𝘴", style=discord.ButtonStyle.grey, custom_id="see_proofs")
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
        image_links = cases[current_case - 1][6]
        image_embeds = image_links_to_embeds(image_links)
        await interaction.followup.send(f"Proofs for `{guild.id}`", embeds=image_embeds, ephemeral=True)

# reported account
class ReportedAccountView(discord.ui.View):
    def __init__(self, game_uid, account_profile, requested_by, current_case):
        super().__init__(timeout=1440)
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
            latest_tags = latest_case[2].split(", ")
            all_tags_list = []
            for case in cases:
                all_tags_list.extend(case[2].split(", "))
            all_tags_list = sort_account_tags(all_tags_list)
            if "Recovered Account" in latest_tags:
                title = "Recovered Account"
            else:
                title = all_tags_list[0]
            if current_case != 1:
                prev_index = current_case - 2
                try:
                    prev_case_tags = cases[prev_index][2].split(", ")
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
            latest_tags = latest_case[2].split(", ")
            all_tags_list = []
            for case in cases:
                all_tags_list.extend(case[2].split(", "))
            all_tags_list = sort_account_tags(all_tags_list)
            if "Recovered Account" in latest_tags:
                title = "Recovered Account"
            else:
                title = all_tags_list[0]
            next_index = current_case
            try:
                next_case_tags = cases[next_index][2].split(", ")
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

    @discord.ui.button(label="𝘱𝘳𝘰𝘰𝘧𝘴", style=discord.ButtonStyle.grey, custom_id="reportedaccount:proofs")
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
        image_links = cases[current_case - 1][7]
        image_embeds = image_links_to_embeds(image_links)
        await interaction.followup.send(f"Proofs for `{game_uid}`", embeds=image_embeds, ephemeral=True)


    @discord.ui.button(label="𝘭𝘪𝘯𝘬𝘴 𝘱𝘳𝘰𝘰𝘧𝘴", style=discord.ButtonStyle.grey, custom_id="reportedaccount:linksproofs")
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

@check.command(name="all", description="Check all users in the server for bannable report(s).")
@commands.has_permissions(administrator=True)
async def check_all(interaction: discord.Interaction):
    if interaction.guild is None:
        return
    await interaction.response.send_message(f"Checking {interaction.guild.member_count} users for bannable report(s).", ephemeral=True)
    ban_users = []
    for idx, member in enumerate(interaction.guild.members):
        if idx % 50 == 0:
            await asyncio.sleep(0)
        user_profile = await asyncio.to_thread(userscol.find_one, {"_id": str(member.id)})
        if not user_profile:
            continue
        if len(user_profile) == 2:
            main = user_profile["main"]
            main_user_profile = await asyncio.to_thread(userscol.find_one, {"_id": main})
            profile = main_user_profile
        else:
            profile = user_profile
        no_of_cases = len(profile) - 2
        all_tags_list = []
        for i in range(1, no_of_cases + 1):
            tags = profile[str(i)][2].split(", ")
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
        await interaction.followup.send(f"{len(ban_users)} users with bannable report(s) were found.", embeds=embeds)
    elif ban_users and len(ban_users) > 1000:
        embeds = []
        ban_users_grouped = [ban_users[i:i + 100] for i in range(0, 1001, 100)]
        for group in ban_users_grouped:
            embed = discord.Embed(description=f"`{" ".join(group)}`")
            embeds.append(embed)
        await interaction.followup.send(f"{len(ban_users)} users with bannable report(s) were found, which exceeds the limit of 1000 users that can be shown.", embeds=embeds)
    else:
        await interaction.followup.send("No users with bannable report(s) were found!")


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