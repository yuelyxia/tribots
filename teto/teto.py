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

import discord
from discord import app_commands
from discord.ext import commands, tasks
from discord.utils import get

from typing import Literal

TOKEN = os.getenv("TOKEN")
CLIENT = os.getenv("CLIENT")

# mongodb info
client = pymongo.MongoClient(CLIENT)
db = client["database"]
userscol = db["users"]
serverscol = db["servers"]
trusteduserscol = db["trusted_users"]
trustedserverscol = db["trusted_servers"]
staffweeklycol = db["staff_weekly"]
inprogresscol = db["in_progress"]

inprogresscol.create_index("user_id", unique=True)

# tri channels info
PROOFS_CHANNEL = 1455055877034868769
VOTE_CHANNEL = 1434537315791016210
USER_REPORTS_CHANNEL = 1375132097605406721
SERVER_REPORTS_CHANNEL = 1375184563675856916
TICKETS_CHANNEL = 1375261699111784478

# tri roles info
o5_role = 1372426616671834234
staff_role = 1373803879623430268
ticket_ping = 1449382692671193294
in_training = 1396701840321679391
sr_role = 1375254710952661102
adm_role = 1375276457890287748

new_user_report_ping = 1375275062185168957
updated_user_report_ping = 1459590866724323625
appealed_user_report_ping = 1459590865335877663
new_server_report_ping = 1375275002537971742
updated_server_report_ping = 1459590362703204405
appealed_server_report_ping = 1459590364292972776

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
               "Unprofessional Staff", "Unprofessional Supervisor", "Improper Conduct"]

red_server_tags = ["Scam Server", "Impersonator Server", "Fake Vouch Server", "Fake Event Server"]
yellow_server_tags = ["Suspect Server"]


# formatting functions

def default_user_profile(user):
    profile = discord.Embed()
    profile.set_thumbnail(url=f"{user.display_avatar}")
    profile.description = f"{user.name}\n`{user.id}`\n{user.mention}"
    profile.description += "\n**Account Created:** " + f"<t:{round(int(user.created_at.timestamp()))}:D> (<t:{round(int(user.created_at.timestamp()))}:R>)" + '\n'
    profile.set_footer(text="✦　This user is unreported.")
    return profile
def default_server_profile(guild):
    profile = discord.Embed()
    if guild.icon:
        profile.set_thumbnail(url=f"{guild.icon.url}")
    profile.description = f"{guild.name}\n`{guild.id}`"
    if guild.created_at:
        profile.description += "\n**Server Created:** " + f"<t:{round(int(guild.created_at.timestamp()))}:D> (<t:{round(int(guild.created_at.timestamp()))}:R>)" + '\n'
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
    for tag_to_find in yellow_server_tags:
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
    if trusteduser_profile["current_staff"] == "1":
        trusted_embed = discord.Embed(title="TRI Staff", colour=0xbba8dd)
    elif trusteduser_profile["staff"] == "1":
        trusted_embed = discord.Embed(title="Former TRI Staff", colour=0x9279b5)
    else:
        trusted_embed = discord.Embed(title="Trusted User", colour=0x9279b5)
    trusted_embed.set_thumbnail(url=f"{user.display_avatar}")
    trusted_embed.description = f"{user.name}\n`{user.id}`\n{user.mention}"
    trusted_embed.description += "\n**Account Created:** " + f"<t:{round(int(user.created_at.timestamp()))}:D> (<t:{round(int(user.created_at.timestamp()))}:R>)" + '\n'
    trusted_embed.set_footer(text="✦　This user is trusted.")
    if trusteduser_profile["staff"] == "1":
        trusted_embed.description += "### Staff Info"
        trusted_embed.description += f"\n**Reports:** {trusteduser_profile['reports']}"
        trusted_embed.description += f"\n**Reviews:** {trusteduser_profile['reviews']}"
        trusted_embed.description += f"\n**Votes:** {trusteduser_profile['votes']}"
        if trusteduser_profile["mm"] == "1" or trusteduser_profile["pilot"] == "1" or trusteduser_profile["trader"] == "1":
            trusted_embed.description += "\n"
    if trusteduser_profile["mm"] == "1":
        trusted_embed.description += "\nProfessional Middleman"
    if trusteduser_profile["pilot"] == "1":
        trusted_embed.description += "\nProfessional Pilot"
    if trusteduser_profile["trader"] == "1":
        trusted_embed.description += "\nTrusted Trader"
    return trusted_embed
def format_user_r_profile(user, r_profile_list, title):
    if title == "Ex-offender":
        r_profile = discord.Embed(title=title, colour=0xFFD643)
    elif title in red_tags:
        r_profile = discord.Embed(title=title, colour=0xFF0045)
    elif title in yellow_tags:
        r_profile = discord.Embed(title=title, colour=0xFFD643)
    else:
        r_profile = discord.Embed(title=title)
    r_profile.set_thumbnail(url=f"{user.display_avatar}")
    r_profile.description = f"{user.name}\n`{user.id}`\n{user.mention}"
    r_profile.description += "\n**Account Created:** " + f"<t:{round(int(user.created_at.timestamp()))}:D> (<t:{round(int(user.created_at.timestamp()))}:R>)\n"
    r_profile.description += "\n**Alts:** " + r_profile_list[0]
    r_profile.description += "\n**Other Tag(s):** " + r_profile_list[1]
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
        add_case.description = "**Date Added:** " + add_case_list[0]
        add_case.description += "\n**Game(s):** " + add_case_list[1]
        add_case.description += "\n**Tag(s):** " + add_case_list[2]
        add_case.description += "\n\n> **Reason:** " + add_case_list[3]
        add_case.description += "\n\n> **Contributor:** " + add_case_list[4]
        add_case.description += "\n> **TRI Staff:** " + add_case_list[5]
        add_case.description += "\n> **Accepted by:** " + add_case_list[6]
    return add_case
def format_trustedserver_profile(guild, trustedserver_profile):
    if guild.id == TRI_Archive:
        trusted_embed = discord.Embed(title="Trade Report Investigation Archive", colour=0xbba8dd)
    else:
        trusted_embed = discord.Embed(title="Trusted Server", colour=0x9279b5)
    if guild.icon:
        trusted_embed.set_thumbnail(url=f"{guild.icon.url}")
    trusted_embed.description = f"{guild.name}\n`{guild.id}`"
    if guild.created_at:
        trusted_embed.description += "\n**Server Created:** " + f"<t:{round(int(guild.created_at.timestamp()))}:D> (<t:{round(int(guild.created_at.timestamp()))}:R>)" + '\n'
    if guild.banner:
        trusted_embed.set_image(url=guild.banner.url)
    return trusted_embed
def format_server_r_profile(guild, r_profile_list, title):
    if title in red_server_tags:
        r_profile = discord.Embed(title=title, colour=0xCF2D53)
    elif title in yellow_server_tags:
        r_profile = discord.Embed(title=title, colour=0xd9b534)
    else:
        r_profile = discord.Embed(title=title)
    if guild.icon:
        r_profile.set_thumbnail(url=f"{guild.icon.url}")
    r_profile.description = f"{guild.name}\n`{guild.id}`\n**Owner:** {r_profile_list[0]}"
    if guild.created_at:
        r_profile.description += "\n**Server Created:** " + f"<t:{round(int(guild.created_at.timestamp()))}:D> (<t:{round(int(guild.created_at.timestamp()))}:R>)" + '\n'
    r_profile.description += "\n**Other Tag(s):** " + r_profile_list[1]
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
    add_case.description = "**Date Added:** " + add_case_list[0]
    add_case.description += "\n**Tag(s):** " + add_case_list[1]
    add_case.description += "\n\n> **Reason:** " + add_case_list[2]
    add_case.description += "\n\n> **Contributor:** " + add_case_list[3]
    add_case.description += "\n> **TRI Staff:** " + add_case_list[4]
    add_case.description += "\n> **Accepted by:** " + add_case_list[5]
    return add_case


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
    discord.SelectOption(label="Unprofessional Staff", value="Unprofessional Staff"),
    discord.SelectOption(label="Unprofessional Supervisor", value="Unprofessional Supervisor"),
    discord.SelectOption(label="Improper Conduct", value="Improper Conduct"),
]

games_options = [
    discord.SelectOption(label="Genshin Impact", value="Genshin Impact"),
    discord.SelectOption(label="Honkai: Star Rail", value="Honkai: Star Rail"),
    discord.SelectOption(label="Wuthering Waves", value="Wuthering Waves"),
    discord.SelectOption(label="Roblox", value="Roblox"),
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


@tasks.loop(hours=1.0)
async def update_reports_count():
    reports_count = userscol.count_documents({}) + serverscol.count_documents({})
    await bot.change_presence(status=discord.Status.dnd,
                              activity=discord.Activity(
                                  type=discord.ActivityType.watching,
                                  name=f"{reports_count} reports."
                              )
                              )

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


@bot.event
async def on_message(message):
    if message.channel.type == discord.ChannelType.news and message.author.id == bot.user.id:
        await publish_queue.put(message)
    await bot.process_commands(message)


# check

@bot.command(name='mc', help='Checks a list of users (max 200), leave a space between users.')
async def mc(ctx, *, to_check: str = None):
    if to_check != None:
        users = to_check.split()
        valid_users = []
        invalid_users = []
        embeds = []
        for user in users:
            try: user = await bot.fetch_user(int(user.strip('<@>')))
            except Exception: invalid_users.append(user)
            else:
                if user not in valid_users: valid_users.append(user)
        if valid_users and len(valid_users) <= 200:
            valid_users_grouped = [valid_users[i:i + 25] for i in range(0, len(valid_users), 25)]

            for group in valid_users_grouped:
                description = ""
                for user in group:
                    user_id = user.id
                    user_query = {"_id": str(user_id)}
                    trusteduser_profile = trusteduserscol.find_one(user_query)
                    if trusteduser_profile:
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

            await ctx.reply(embeds=embeds)
        else:
            if valid_users: await ctx.reply("Exceeded 200 users.")
            else: await ctx.reply("No valid users provided.")


@bot.command(name='c', help='Checks a user or server.')
async def c(ctx, *, to_check: str = None):
    requested_by = ctx.author
    if to_check == None:
        user = ctx.author
        user_id = user.id
        user_query = {"_id": str(user_id)}
        trusteduser_profile = trusteduserscol.find_one(user_query)
        if trusteduser_profile:
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
                    user_query = {"_id": str(user_id)}
                    trusteduser_profile = trusteduserscol.find_one(user_query)
                    if trusteduser_profile and (trusteduser_profile["current_staff"] == "1"
                                                and (get(ctx.guild.roles, id=ticket_ping) in ctx.author.roles
                                                     or get(ctx.guild.roles, id=in_training) in ctx.author.roles)):
                        await ctx.reply(f"User `{user_id}` is reported as alt of `{main}`.",
                                        embeds=reported_user_profile(main_user, main_user_profile),
                                        view=EditUserReportView(main_user, main_user_profile, requested_by,
                                                            len(main_user_profile) - 2))
                    else:
                        await ctx.reply(f"User `{user_id}` is reported as alt of `{main}`.",
                                        embeds=reported_user_profile(main_user, main_user_profile),
                                        view=ReportedUserView(main_user, main_user_profile, requested_by,
                                                              len(main_user_profile) - 2))
                #
                else:
                    #
                    user_query = {"_id": str(user_id)}
                    trusteduser_profile = trusteduserscol.find_one(user_query)
                    if trusteduser_profile and (trusteduser_profile["current_staff"] == "1"
                                                and (get(ctx.guild.roles, id=ticket_ping) in ctx.author.roles
                                                     or get(ctx.guild.roles, id=in_training) in ctx.author.roles)):
                        await ctx.reply(f"User is reported.",
                                        embeds=reported_user_profile(user, user_profile),
                                        view=EditUserReportView(user, user_profile, requested_by, len(user_profile) - 2))
                    else:
                        await ctx.reply(f"User is reported.",
                                        embeds=reported_user_profile(user, user_profile),
                                        view=ReportedUserView(user, user_profile, requested_by, len(user_profile) - 2))
            #
            else:
                profile = default_user_profile(user)
                #
                user_query = {"_id": str(user_id)}
                trusteduser_profile = trusteduserscol.find_one(user_query)
                if trusteduser_profile and (trusteduser_profile["current_staff"] == "1"
                                            and (get(ctx.guild.roles, id=ticket_ping) in ctx.author.roles
                                                 or get(ctx.guild.roles, id=in_training) in ctx.author.roles)):
                    await ctx.reply(embed=profile, view=NewUserReportView(user, requested_by))
                else:
                    await ctx.reply(embed=profile, view=MemberView())

    else:
        try:
            if int(to_check.strip('<@>')) in tri_bots:
                user = await bot.fetch_user(int(to_check.strip('<@>')))
                user_id = user.id
                profile = discord.Embed(colour=0xffffff)
                profile.set_thumbnail(url=f"{user.display_avatar.url}")
                profile.description = f"{user.name}\n`{user_id}`\n{user.mention}"
                profile.description += "\n**Account Created:** " + f"<t:{round(int(user.created_at.timestamp()))}:D> (<t:{round(int(user.created_at.timestamp()))}:R>)" + '\n'
                if user_id == 1450073025818136598:
                    profile.description += "\n**TETO** ┈ report bot for `/tri`"
                elif user_id == 1457249982104211467:
                    profile.description += "\n**TETO++** ┈ report bot for `/tri`"
                elif user_id == 1457382953293320304:
                    profile.description += "\n**NERU** ┈ alts bot for `/tri`"
                elif user_id == 1457309787044839477:
                    profile.description += "\n**MIKU** ┈ utils bot for `/tri`"
                elif user_id == 1457009979817988241:
                    profile.description += "\n**KAFU** ┈ tickets bot for `/tri`"
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
                trusted_embed = format_trustedserver_profile(UnknownGuild(int(to_check.strip('<@>'))), trustedserver_profile)
                await ctx.reply("Server is trusted.", embed=trusted_embed)
            else:
                server_profile = serverscol.find_one(server_query)
                if server_profile:  # reported server
                    await ctx.reply(f"Server is reported.",
                                        embeds=reported_server_profile(UnknownGuild(int(to_check.strip('<@>'))), server_profile),
                                        view=ReportedServerView(UnknownGuild(int(to_check.strip('<@>'))), server_profile, requested_by,
                                                                len(server_profile) - 2))
                else:  # unreported server
                    await ctx.reply("Please provide a valid user ID. To check servers, please provide a valid invite link.")

        except discord.HTTPException as e:
            await ctx.reply(f"An error occurred: {e}")
        except ValueError:
            try:
                invite = await bot.fetch_invite(to_check)
            except discord.NotFound:
                await ctx.reply("The invite link is **invalid** or **expired**.")
            except discord.Forbidden:
                await ctx.reply("Unable to access details of invite.")
            except Exception as e:
                await ctx.reply(f"An error occurred: {e}")
            else:
                guild = invite.guild
                guild_id = invite.guild.id
                server_query = {"_id": str(guild_id)}
                trustedserver_profile = trustedserverscol.find_one(server_query)
                if trustedserver_profile:
                    trusted_embed = format_trustedserver_profile(guild, trustedserver_profile)
                    await ctx.reply("Server is trusted.", embed=trusted_embed)
                else:
                    server_profile = serverscol.find_one(server_query)
                    if server_profile:  # reported server
                        #
                        user_query = {"_id": str(ctx.author.id)}
                        trusteduser_profile = trusteduserscol.find_one(user_query)
                        if trusteduser_profile and (trusteduser_profile["current_staff"] == "1"
                                                    and (get(ctx.guild.roles, id=ticket_ping) in ctx.author.roles
                                                         or get(ctx.guild.roles, id=in_training) in ctx.author.roles)):
                            await ctx.reply(f"Server is reported.",
                                            embeds=reported_server_profile(guild, server_profile),
                                            view=EditServerReportView(guild, server_profile, requested_by,
                                                                    len(server_profile) - 2))
                        else:
                            await ctx.reply(f"Server is reported.",
                                            embeds=reported_server_profile(guild, server_profile),
                                            view=ReportedServerView(guild, server_profile, requested_by,
                                                                  len(server_profile) - 2))
                    else:  # unreported server
                        profile = default_server_profile(guild)
                        #
                        user_query = {"_id": str(ctx.author.id)}
                        trusteduser_profile = trusteduserscol.find_one(user_query)
                        if trusteduser_profile and (trusteduser_profile["current_staff"] == "1"
                                                    and (get(ctx.guild.roles, id=ticket_ping) in ctx.author.roles
                                                         or get(ctx.guild.roles, id=in_training) in ctx.author.roles)):
                            await ctx.reply(embed=profile, view=NewServerReportView(guild, requested_by))
                        else:
                            await ctx.reply(embed=profile, view=MemberView())
        #
        else:
            user_id = user.id
            user_query = {"_id": str(user_id)}
            trusteduser_profile = trusteduserscol.find_one(user_query)
            if trusteduser_profile:
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
                        user_query = {"_id": str(ctx.author.id)}
                        trusteduser_profile = trusteduserscol.find_one(user_query)
                        if trusteduser_profile and (trusteduser_profile["current_staff"] == "1"
                                                    and (get(ctx.guild.roles, id=ticket_ping) in ctx.author.roles
                                                         or get(ctx.guild.roles, id=in_training) in ctx.author.roles)):
                            await ctx.reply(f"User `{user_id}` is reported as alt of `{main}`.",
                                            embeds=reported_user_profile(main_user, main_user_profile),
                                            view=EditUserReportView(main_user, main_user_profile, requested_by,
                                                                len(main_user_profile) - 2))
                        else:
                            await ctx.reply(
                                f"User `{user_id}` is reported as alt of `{main}`.",
                                embeds=reported_user_profile(main_user, main_user_profile),
                                view=ReportedUserView(main_user, main_user_profile, requested_by,
                                                      len(main_user_profile) - 2))
                    else:
                        #
                        user_query = {"_id": str(ctx.author.id)}
                        trusteduser_profile = trusteduserscol.find_one(user_query)
                        if trusteduser_profile and (trusteduser_profile["current_staff"] == "1"
                                                    and (get(ctx.guild.roles, id=ticket_ping) in ctx.author.roles
                                                         or get(ctx.guild.roles, id=in_training) in ctx.author.roles)):
                            await ctx.reply(f"User is reported.",
                                            embeds=reported_user_profile(user, user_profile),
                                            view=EditUserReportView(user, user_profile, requested_by,
                                                                len(user_profile) - 2))
                        else:
                            await ctx.reply(f"User is reported.",
                                            embeds=reported_user_profile(user, user_profile),
                                            view=ReportedUserView(user, user_profile, requested_by,
                                                                  len(user_profile) - 2))
                #
                else:
                    profile = default_user_profile(user)
                    #
                    user_query = {"_id": str(ctx.author.id)}
                    trusteduser_profile = trusteduserscol.find_one(user_query)
                    if trusteduser_profile and (trusteduser_profile["current_staff"] == "1"
                                                and (get(ctx.guild.roles, id=ticket_ping) in ctx.author.roles
                                                     or get(ctx.guild.roles, id=in_training) in ctx.author.roles)):
                        requested_by = ctx.author
                        await ctx.reply(embed=profile, view=NewUserReportView(user, requested_by))
                    else:
                        await ctx.reply(embed=profile, view=MemberView())


# reported user
class ReportedUserView(discord.ui.View):
    def __init__(self, user, user_profile, requested_by, current_case):
        super().__init__(timeout=None)
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
                tags_strings.append(case[2])
            for tags_string in tags_strings:
                tags_list = tags_string.split(", ")
                for tag in tags_list:
                    all_tags_list.append(tag)
            all_tags_list = sort_user_tags(all_tags_list)
            title = all_tags_list[0]
            if current_case != 1:
                prev_index = current_case - 2
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
        image_links = cases[current_case - 1][7]
        image_embeds = image_links_to_embeds(image_links)
        await interaction.followup.send(f"Proofs for `{user.id}`", embeds=image_embeds, ephemeral=True)

    @discord.ui.button(label="Alts Proofs", style=discord.ButtonStyle.grey, custom_id="reporteduser:altsproofs")
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
        super().__init__(timeout=None)
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
        image_links = cases[current_case - 1][6]
        image_embeds = image_links_to_embeds(image_links)
        await interaction.followup.send(f"Proofs for `{guild.id}`", embeds=image_embeds, ephemeral=True)

# member
class MemberView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(discord.ui.Button(label="Report", style=discord.ButtonStyle.grey,
                                        url="https://discord.com/channels/1371673839695826974/1375261699111784478"))

# new user
class NewUserReportView(discord.ui.View):
    def __init__(self, user, requested_by):
        super().__init__(timeout=None)
        self.user = user
        self.requested_by = requested_by

    @discord.ui.button(label="Report", style=discord.ButtonStyle.red, custom_id="newuserreport:report")
    async def report_button(self, interaction, button):
        #
        user = self.user
        requested_by = self.requested_by
        #
        await interaction.response.defer()
        ongoing_report = []
        tickets_channel = bot.get_channel(TICKETS_CHANNEL)
        active_threads = tickets_channel.threads
        for thread in active_threads:
            try:
                async for message in thread.history():
                    if message.content.startswith(f"Adding report on `{user.id}`") or \
                            message.content.startswith(f"Editing alts for `{user.id}`") or \
                            message.content.startswith(f"Appealing for `{user.id}`") or \
                            message.content.startswith(f"Initializing report on `{user.id}`") \
                            and message.author.id == bot.user.id:
                        ongoing_report.append(message.jump_url)
            except Exception:
                pass
        if ongoing_report:
            await interaction.followup.send(
                f"There already exists an ongoing report on `{user.id}`: {ongoing_report[0]}")
            return
        ongoing_vote = []
        vote_channel = bot.get_channel(VOTE_CHANNEL)
        active_threads = vote_channel.threads
        for thread in active_threads:
            if thread.name == f"{user.id}":
                ongoing_vote.append(thread.jump_url)
        if ongoing_vote:
            await interaction.followup.send(
                f"There already exists an ongoing vote on `{user.id}`: {ongoing_vote[0]}")
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
            add_case_list = [
                # [0] date added
                "",
                # [1] games
                "",
                # [2] tags
                "",
                # [3] reason
                "",
                # [4] contributor
                "",
                # [5] tri staff
                "",
                # [6] accepted by
                "",
                # [7] image_links
                [],
            ]
            add_case_list[
                0] = f"<t:{round(int(discord.utils.utcnow().timestamp()))}:D> (<t:{round(int(discord.utils.utcnow().timestamp()))}:R>)"
            add_case_list[5] = f"<@{interaction.user.id}>"
            channel_id = msg.channel.id
            message_id = msg.id
            r_profile = format_user_r_profile(user, r_profile_list, title)
            add_case = format_user_add_case(add_case_list, case_title)
            embeds = [r_profile, add_case]
            session = inprogresscol.find_one({"_id": message_id})
            if not session:
                inprogresscol.insert_one({"_id": message_id,
                                          "user_id": user.id,
                                          "requested_by": requested_by.id,
                                          "channel_id": channel_id,
                                          "r_profile_list": r_profile_list,
                                          "add_case_list": add_case_list,
                                          "title": title,
                                          "case_title": case_title
                                          })
            await msg.edit(embeds=embeds,
                           view=AltsView())
        elif any(role.id == ticket_ping for role in interaction.user.roles):
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
            message = await bot.get_channel(channel_id).fetch_message(message_id)
            if requested_by == interaction.user.id or any(role.id == sr_role for role in interaction.user.roles):
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
            if requested_by == interaction.user.id or any(role.id == sr_role for role in interaction.user.roles):
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
            message = await bot.get_channel(channel_id).fetch_message(message_id)
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
            message = await bot.get_channel(channel_id).fetch_message(message_id)
            if requested_by == interaction.user.id or any(role.id == sr_role for role in interaction.user.roles):
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
            message = await bot.get_channel(channel_id).fetch_message(message_id)
            if requested_by == interaction.user.id or any(role.id == sr_role for role in interaction.user.roles):
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
            message = await bot.get_channel(channel_id).fetch_message(message_id)
            if requested_by == interaction.user.id:
                sorted_tags = sort_user_tags(self.select_callback.values)
                case_title = sorted_tags[0]
                tags = selected_string(sorted_tags)
                add_case_list[2] = tags
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
            message = await bot.get_channel(channel_id).fetch_message(message_id)
            if requested_by == interaction.user.id or any(role.id == sr_role for role in interaction.user.roles):
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
            message = await bot.get_channel(channel_id).fetch_message(message_id)
            if requested_by == interaction.user.id or any(role.id == sr_role for role in interaction.user.roles):
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
            message = await bot.get_channel(channel_id).fetch_message(message_id)
            if requested_by == interaction.user.id:
                games = selected_string(self.select_callback.values)
                add_case_list[1] = games
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
            message = await bot.get_channel(channel_id).fetch_message(message_id)
            if requested_by == interaction.user.id or any(role.id == sr_role for role in interaction.user.roles):
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
            message = await bot.get_channel(channel_id).fetch_message(message_id)
            if requested_by == interaction.user.id or any(role.id == sr_role for role in interaction.user.roles):
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
                                  style=discord.TextStyle.short)

    def __init__(self):
        super().__init__(timeout=None)

    async def on_submit(self, interaction):
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
            message = await bot.get_channel(channel_id).fetch_message(message_id)
            add_case_list[3] = str(self.reason.value)
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
            message = await bot.get_channel(channel_id).fetch_message(message_id)
            if requested_by == interaction.user.id or any(role.id == sr_role for role in interaction.user.roles):
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
            message = await bot.get_channel(channel_id).fetch_message(message_id)
            if requested_by == interaction.user.id or any(role.id == sr_role for role in interaction.user.roles):
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
            message = await bot.get_channel(channel_id).fetch_message(message_id)
            contributor_input = self.contributor.value
            if contributor_input.lower() == "n":
                add_case_list[4] = "Anonymous"
            else:
                try:
                    contributor_id = await bot.fetch_user(int(contributor_input))
                except Exception:
                    add_case_list[4] = ""
                else:
                    add_case_list[4] = f"<@{contributor_id.id}>"
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
            message = await bot.get_channel(channel_id).fetch_message(message_id)
            if requested_by == interaction.user.id or any(role.id == sr_role for role in interaction.user.roles):
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
                add_case_list[7] = []
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
                                            add_case_list[7].append(new_image_url)
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
            if requested_by == interaction.user.id or any(role.id == sr_role for role in interaction.user.roles):
                image_embeds = image_links_to_embeds(add_case_list[7])
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
            if requested_by == interaction.user.id or any(role.id == sr_role for role in interaction.user.roles):
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
            inprogresscol.delete_one({"_id": interaction.message.id})
            message = await bot.get_channel(channel_id).fetch_message(message_id)
            if requested_by == interaction.user.id or any(role.id == sr_role for role in interaction.user.roles):
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
            message = await bot.get_channel(channel_id).fetch_message(message_id)
            if any(role.id == sr_role for role in interaction.user.roles) and interaction.user.id != requested_by:
                accepted_by = interaction.user
                add_case_list[6] = f"<@{interaction.user.id}>"
                #

                r_profile = format_user_r_profile(user, r_profile_list, title)
                add_case = format_user_add_case(add_case_list, case_title)
                embeds = [r_profile, add_case]
                #
                vote_channel = bot.get_channel(VOTE_CHANNEL)
                agree_users = []
                disagree_users = []
                alts_proofs_embeds = image_links_to_embeds(r_profile_list[2])
                proofs_embeds = image_links_to_embeds(add_case_list[7])
                new_report_message = await vote_channel.send(content=f"New report on `{user.id}`")
                new_report_thread = await new_report_message.create_thread(name=f"{user.id}")
                await new_report_thread.send(f"<@&{ticket_ping}>")
                vote_msg = await new_report_thread.send(
                    content=f"Report accepted by <@{accepted_by.id}>.\nLink to thread: <#{channel_id}>\n\nAgree: 0\nDisagree: 0",
                    embeds=embeds, view=UserVoteView())
                vote_channel_id = vote_msg.channel.id
                vote_message_id = vote_msg.id
                inprogresscol.delete_one({"_id": interaction.message.id})
                #
                try:
                    inprogresscol.insert_one({"_id": vote_message_id,
                                              "user_id": user.id,
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
                except DuplicateKeyError: pass
                await new_report_thread.send(content=f"Alt Proofs for `{user.id}`", embeds=alts_proofs_embeds)
                await new_report_thread.send(content=f"Proofs for `{user.id}`", embeds=proofs_embeds)
                await message.edit(content="Report has been submitted for voting.", embeds=embeds, view=None)
            else:
                await interaction.followup.send("You do not have permission to accept the report for voting.",
                                                ephemeral=True)


# edit user
class EditUserReportView(discord.ui.View):
    def __init__(self, user, user_profile, requested_by, current_case):
        super().__init__(timeout=None)
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
                tags_strings.append(case[2])
            for tags_string in tags_strings:
                tags_list = tags_string.split(", ")
                for tag in tags_list:
                    all_tags_list.append(tag)
            all_tags_list = sort_user_tags(all_tags_list)
            title = all_tags_list[0]
            if current_case != 1:
                prev_index = current_case - 2
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
        image_links = cases[current_case - 1][7]
        image_embeds = image_links_to_embeds(image_links)
        await interaction.followup.send(f"Proofs for `{user.id}`", embeds=image_embeds, ephemeral=True)

    @discord.ui.button(label="Alts Proofs", style=discord.ButtonStyle.grey, custom_id="edituserreport:altsproofs", row=0)
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
        ongoing_report = []
        tickets_channel = bot.get_channel(TICKETS_CHANNEL)
        active_threads = tickets_channel.threads
        for thread in active_threads:
            try:
                async for message in thread.history():
                    if message.content.startswith(f"Adding report on `{user.id}`") or \
                            message.content.startswith(f"Editing alts for `{user.id}`") or \
                            message.content.startswith(f"Appealing for `{user.id}`") or \
                            message.content.startswith(f"Initializing report on `{user.id}`") \
                            and message.author.id == bot.user.id:
                        ongoing_report.append(message.jump_url)
            except Exception:
                pass
        if ongoing_report:
            await interaction.followup.send(
                f"There already exists an ongoing report on `{user.id}`: {ongoing_report[0]}")
            return
        ongoing_vote = []
        vote_channel = bot.get_channel(VOTE_CHANNEL)
        active_threads = vote_channel.threads
        for thread in active_threads:
            if thread.name == f"{user.id}":
                ongoing_vote.append(thread.jump_url)
        if ongoing_vote:
            await interaction.followup.send(
                f"There already exists an ongoing vote on `{user.id}`: {ongoing_vote[0]}")
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
                tags_strings.append(case[2])
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
        elif any(role.id == ticket_ping for role in interaction.user.roles):
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
        ongoing_report = []
        tickets_channel = bot.get_channel(TICKETS_CHANNEL)
        active_threads = tickets_channel.threads
        for thread in active_threads:
            try:
                async for message in thread.history():
                    if message.content.startswith(f"Adding report on `{user.id}`") or \
                            message.content.startswith(f"Editing alts for `{user.id}`") or \
                            message.content.startswith(f"Appealing for `{user.id}`") or \
                            message.content.startswith(f"Initializing report on `{user.id}`") \
                            and message.author.id == bot.user.id:
                        ongoing_report.append(message.jump_url)
            except Exception:
                pass
        if ongoing_report:
            await interaction.followup.send(
                f"There already exists an ongoing report on `{user.id}`: {ongoing_report[0]}")
            return
        ongoing_vote = []
        vote_channel = bot.get_channel(VOTE_CHANNEL)
        active_threads = vote_channel.threads
        for thread in active_threads:
            if thread.name == f"{user.id}":
                ongoing_vote.append(thread.jump_url)
        if ongoing_vote:
            await interaction.followup.send(
                f"There already exists an ongoing vote on `{user.id}`: {ongoing_vote[0]}")
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
                tags_strings.append(case[2])
            for tags_string in tags_strings:
                tags_list = tags_string.split(", ")
                for tag in tags_list:
                    all_tags_list.append(tag)
            all_tags_list = sort_user_tags(all_tags_list)
            title = all_tags_list[0]
            #
            case_title = "TBC"
            add_case_list = [
                # [0] date added
                "",
                # [1] games
                "",
                # [2] tags
                "",
                # [3] reason
                "",
                # [4] contributor
                "",
                # [5] tri staff
                "",
                # [6] accepted by
                "",
                # [7] image_links
                [],
            ]
            add_case_list[
                0] = f"<t:{round(int(discord.utils.utcnow().timestamp()))}:D> (<t:{round(int(discord.utils.utcnow().timestamp()))}:R>)"
            add_case_list[5] = f"<@{interaction.user.id}>"
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
        elif any(role.id == ticket_ping for role in interaction.user.roles):
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
        ongoing_report = []
        tickets_channel = bot.get_channel(TICKETS_CHANNEL)
        active_threads = tickets_channel.threads
        for thread in active_threads:
            try:
                async for message in thread.history():
                    if message.content.startswith(f"Adding report on `{user.id}`") or \
                            message.content.startswith(f"Editing alts for `{user.id}`") or \
                            message.content.startswith(f"Appealing for `{user.id}`") or \
                            message.content.startswith(f"Initializing report on `{user.id}`") \
                            and message.author.id == bot.user.id:
                        ongoing_report.append(message.jump_url)
            except Exception:
                pass
        if ongoing_report:
            await interaction.followup.send(
                f"There already exists an ongoing report on `{user.id}`: {ongoing_report[0]}")
            return
        ongoing_vote = []
        vote_channel = bot.get_channel(VOTE_CHANNEL)
        active_threads = vote_channel.threads
        for thread in active_threads:
            if thread.name == f"{user.id}":
                ongoing_vote.append(thread.jump_url)
        if ongoing_vote:
            await interaction.followup.send(
                f"There already exists an ongoing vote on `{user.id}`: {ongoing_vote[0]}")
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
                tags_strings.append(case[2])
            for tags_string in tags_strings:
                tags_list = tags_string.split(", ")
                for tag in tags_list:
                    all_tags_list.append(tag)
            all_tags_list = sort_user_tags(all_tags_list)
            title = all_tags_list[0]
            current_index = current_case - 1
            add_case_list = user_profile[str(current_case)]
            case_tags = cases[current_index][2].split(", ")
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
        elif any(role.id == ticket_ping for role in interaction.user.roles):
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
            if requested_by == interaction.user.id or any(role.id == sr_role for role in interaction.user.roles):
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
            message = await bot.get_channel(channel_id).fetch_message(message_id)
            if requested_by == interaction.user.id or any(role.id == sr_role for role in interaction.user.roles):
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
            message = await bot.get_channel(channel_id).fetch_message(message_id)
            if any(role.id == sr_role for role in interaction.user.roles) and interaction.user.id != requested_by:
                accepted_by = interaction.user
                r_profile = format_user_r_profile(user, r_profile_list, title)
                #
                vote_channel = bot.get_channel(VOTE_CHANNEL)
                add_case_list = []
                case_title = ""
                agree_users = []
                disagree_users = []
                all_images_to_show = r_profile_list[2]
                image_embeds = image_links_to_embeds(all_images_to_show)
                new_report_message = await vote_channel.send(content=f"Alts edited for `{user.id}`")
                new_report_thread = await new_report_message.create_thread(name=f"{user.id}")
                await new_report_thread.send(f"<@&{ticket_ping}>")
                vote_msg = await new_report_thread.send(
                    content=f"Report accepted by <@{accepted_by.id}>.\nLink to thread: <#{channel_id}>\n\nAgree: 0\nDisagree: 0",
                    embed=r_profile, view=UserVoteView())
                vote_channel_id = vote_msg.channel.id
                vote_message_id = vote_msg.id
                inprogresscol.delete_one({"_id": interaction.message.id})
                #
                try:
                    inprogresscol.insert_one({"_id": vote_message_id,
                                              "user_id": user.id,
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
                except DuplicateKeyError: pass
                await new_report_thread.send(content=f"Alts Proofs for `{user.id}`", embeds=image_embeds)
                reason_embed = discord.Embed(title="Reason", description=reason)
                await new_report_thread.send(content=f"Reason for change(s)", embed=reason_embed)
                embeds = [r_profile, reason_embed]
                await message.edit(content="Report has been submitted for voting.", embeds=embeds, view=None)
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
            message = await bot.get_channel(channel_id).fetch_message(message_id)
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
            message = await bot.get_channel(channel_id).fetch_message(message_id)
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
            message = await bot.get_channel(channel_id).fetch_message(message_id)
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
            if requested_by == interaction.user.id or any(role.id == sr_role for role in interaction.user.roles):
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
            message = await bot.get_channel(channel_id).fetch_message(message_id)
            if requested_by == interaction.user.id or any(role.id == sr_role for role in interaction.user.roles):
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
            message = await bot.get_channel(channel_id).fetch_message(message_id)
            if any(role.id == sr_role for role in interaction.user.roles) and interaction.user.id != requested_by:
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
                proofs_embeds = image_links_to_embeds(add_case_list[7])
                add_case_list = [add_case_list]
                new_report_message = await vote_channel.send(content=f"Appeal on `{user.id}`")
                new_report_thread = await new_report_message.create_thread(name=f"{user.id}")
                await new_report_thread.send(f"<@&{ticket_ping}>")
                vote_msg = await new_report_thread.send(
                    content=f"Appeal accepted by <@{accepted_by.id}>.\nLink to thread: <#{channel_id}>\n\nAgree: 0\nDisagree: 0",
                    embeds=embeds, view=UserVoteView())
                vote_channel_id = vote_msg.channel.id
                vote_message_id = vote_msg.id
                inprogresscol.delete_one({"_id": interaction.message.id})
                #
                try:
                    inprogresscol.insert_one({"_id": vote_message_id,
                                              "user_id": user.id,
                                              "requested_by": requested_by,
                                              "channel_id": channel_id,
                                              "message_id": interaction.message.id,
                                              "r_profile_list": r_profile_list,
                                              "add_case_list": add_case_list,
                                              "title": title,
                                              "case_title": case_title,
                                              "reason": reason,
                                              "vote_channel_id": vote_channel_id,
                                              "vote_message_id": vote_message_id,
                                              "accepted_by": accepted_by.id,
                                              "agree_users": agree_users,
                                              "disagree_users": disagree_users,
                                              })
                except DuplicateKeyError: pass
                await new_report_thread.send(content=f"Alt Proofs for `{user.id}`", embeds=alts_proofs_embeds)
                await new_report_thread.send(content=f"Proofs for `{user.id}`", embeds=proofs_embeds)
                await message.edit(content="Appeal has been submitted for voting.", embeds=embeds, view=None)
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
            message = await bot.get_channel(channel_id).fetch_message(message_id)
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
            message = await bot.get_channel(channel_id).fetch_message(message_id)
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
            message = await bot.get_channel(channel_id).fetch_message(message_id)
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
            message = await bot.get_channel(channel_id).fetch_message(message_id)
            if requested_by == interaction.user.id or any(role.id == sr_role for role in interaction.user.roles):
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
            if requested_by == interaction.user.id or any(role.id == sr_role for role in interaction.user.roles):
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
            message = await bot.get_channel(channel_id).fetch_message(message_id)
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
            message = await bot.get_channel(channel_id).fetch_message(message_id)
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
            message = await bot.get_channel(channel_id).fetch_message(message_id)
            if requested_by == interaction.user.id or any(role.id == sr_role for role in interaction.user.roles):
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
            message = await bot.get_channel(channel_id).fetch_message(message_id)
            if requested_by == interaction.user.id or any(role.id == sr_role for role in interaction.user.roles):
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
            message = await bot.get_channel(channel_id).fetch_message(message_id)
            if requested_by == interaction.user.id:
                sorted_tags = sort_user_tags(self.select_callback.values)
                case_title = sorted_tags[0]
                tags = selected_string(sorted_tags)
                add_case_list[2] = tags
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
            message = await bot.get_channel(channel_id).fetch_message(message_id)
            if requested_by == interaction.user.id or any(role.id == sr_role for role in interaction.user.roles):
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
            message = await bot.get_channel(channel_id).fetch_message(message_id)
            if requested_by == interaction.user.id or any(role.id == sr_role for role in interaction.user.roles):
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
            message = await bot.get_channel(channel_id).fetch_message(message_id)
            if requested_by == interaction.user.id:
                games = selected_string(self.select_callback.values)
                add_case_list[1] = games
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
            message = await bot.get_channel(channel_id).fetch_message(message_id)
            if requested_by == interaction.user.id or any(role.id == sr_role for role in interaction.user.roles):
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
            message = await bot.get_channel(channel_id).fetch_message(message_id)
            if requested_by == interaction.user.id or any(role.id == sr_role for role in interaction.user.roles):
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
                                  style=discord.TextStyle.short)

    def __init__(self):
        super().__init__(timeout=None)

    async def on_submit(self, interaction):
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
            message = await bot.get_channel(channel_id).fetch_message(message_id)
            add_case_list[3] = str(self.reason.value)
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
            message = await bot.get_channel(channel_id).fetch_message(message_id)
            if requested_by == interaction.user.id or any(role.id == sr_role for role in interaction.user.roles):
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
            message = await bot.get_channel(channel_id).fetch_message(message_id)
            if requested_by == interaction.user.id or any(role.id == sr_role for role in interaction.user.roles):
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
            message = await bot.get_channel(channel_id).fetch_message(message_id)
            contributor_input = self.contributor.value
            if contributor_input.lower() == "n":
                add_case_list[4] = "Anonymous"
            else:
                try:
                    contributor_id = await bot.fetch_user(int(contributor_input))
                except Exception:
                    add_case_list[4] = ""
                else:
                    add_case_list[4] = f"<@{contributor_id.id}>"
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
            message = await bot.get_channel(channel_id).fetch_message(message_id)
            if requested_by == interaction.user.id or any(role.id == sr_role for role in interaction.user.roles):
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
                add_case_list[7] = []
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
                                            add_case_list[7].append(new_image_url)
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
            if requested_by == interaction.user.id or any(role.id == sr_role for role in interaction.user.roles):
                image_embeds = image_links_to_embeds(add_case_list[7])
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
            if requested_by == interaction.user.id or any(role.id == sr_role for role in interaction.user.roles):
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
            inprogresscol.delete_one({"_id": interaction.message.id})
            message = await bot.get_channel(channel_id).fetch_message(message_id)
            if requested_by == interaction.user.id or any(role.id == sr_role for role in interaction.user.roles):
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
            message = await bot.get_channel(channel_id).fetch_message(message_id)
            if any(role.id == sr_role for role in interaction.user.roles) and interaction.user.id != requested_by:
                accepted_by = interaction.user
                add_case_list[6] = f"<@{interaction.user.id}>"
                r_profile = format_user_r_profile(user, r_profile_list, title)
                add_case = format_user_add_case(add_case_list, case_title)
                embeds = [r_profile, add_case]
                #
                vote_channel = bot.get_channel(VOTE_CHANNEL)
                agree_users = []
                disagree_users = []
                alts_proofs_embeds = image_links_to_embeds(r_profile_list[2])
                proofs_embeds = image_links_to_embeds(add_case_list[7])
                new_report_message = await vote_channel.send(content=f"Report added on `{user.id}`")
                new_report_thread = await new_report_message.create_thread(name=f"{user.id}")
                await new_report_thread.send(f"<@&{ticket_ping}>")
                vote_msg = await new_report_thread.send(
                    content=f"Report accepted by <@{accepted_by.id}>.\nLink to thread: <#{channel_id}>\n\nAgree: 0\nDisagree: 0",
                    embeds=embeds, view=UserVoteView())
                vote_channel_id = vote_msg.channel.id
                vote_message_id = vote_msg.id
                inprogresscol.delete_one({"_id": interaction.message.id})
                #
                try:
                    inprogresscol.insert_one({"_id": vote_message_id,
                                              "user_id": user.id,
                                              "requested_by": requested_by,
                                              "channel_id": channel_id,
                                              "message_id": interaction.message.id,
                                              "r_profile_list": r_profile_list,
                                              "add_case_list": add_case_list,
                                              "title": title,
                                              "case_title": case_title,
                                              "vote_channel_id": vote_channel_id,
                                              "vote_message_id": vote_message_id,
                                              "accepted_by": accepted_by.id,
                                              "agree_users": agree_users,
                                              "disagree_users": disagree_users,
                                              })
                except DuplicateKeyError: pass
                await new_report_thread.send(content=f"Alt Proofs for `{user.id}`", embeds=alts_proofs_embeds)
                await new_report_thread.send(content=f"Proofs for `{user.id}`", embeds=proofs_embeds)
                await message.edit(content="Report has been submitted for voting.", embeds=embeds, view=None)
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
            add_case_list = session["add_case_list"]
            title = session["title"]
            case_title = session["case_title"]
            accepted_by = session["accepted_by"]
            reason = session.get("reason")
            user_id = session["user_id"]
            user = await bot.fetch_user(user_id)
            agree_users, disagree_users = await handle_vote(interaction, session, "agree")
            #
            r_profile = format_user_r_profile(user, r_profile_list, title)
            #
            if len(agree_users) >= 8:
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
                            userscol.insert_one(new_user)
                        for alt in removed_alts_list:
                            userscol.delete_one({"_id": alt})
                        update_operation = {'$set': {"r_profile_list": r_profile_list}}
                        userscol.update_one(user_query, update_operation)
                    #
                    if not add_case_list:  # only alts edited
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
                        r_profile = format_user_r_profile(user, r_profile_list, title)
                        user_reports_channel = bot.get_channel(USER_REPORTS_CHANNEL)
                        await user_reports_channel.send(content=f"<@&{updated_user_report_ping}>\nAlts edited for `{user.id}`",
                                                        embed=r_profile)
                        reason_embed = discord.Embed(title="Reason", description=reason)
                        await user_reports_channel.send(content=f"Reason for change(s)", embed=reason_embed)
                        await interaction.edit_original_response(
                            content=f"**Report has been published.** Report accepted by <@{accepted_by}>.\nLink to thread: <#{channel_id}>\n\nAgree: {len(agree_users)}\nDisagree: {len(disagree_users)}",
                            embeds=r_profile, view=None)
                        message = await bot.get_channel(channel_id).fetch_message(message_id)
                        await message.edit(
                            content=f"**Report has been published.** Report accepted by <@{accepted_by}>.")
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
                                tags_strings.append(case[2])
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
                        await interaction.edit_original_response(
                            content=f"**Appeal has been published.** Appeal accepted by <@{accepted_by}>.\nLink to thread: <#{channel_id}>\n\nAgree: {len(agree_users)}\nDisagree: {len(disagree_users)}",
                            embeds=embeds, view=None)
                        message = await bot.get_channel(channel_id).fetch_message(message_id)
                        await message.edit(
                            content=f"**Appeal has been published.** Appeal accepted by <@{accepted_by}>.")
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
                        serverscol.update_one(query_filter, update_operation)
                        update_operation = {'$set': {str(no_of_cases + 1): add_case_list}}
                        userscol.update_one(query_filter, update_operation)

                        user_reports_channel = bot.get_channel(USER_REPORTS_CHANNEL)
                        await user_reports_channel.send(content=f"<@&{updated_user_report_ping}>\nReport added on `{user.id}`",
                                                        embeds=embeds)
                        await interaction.edit_original_response(
                            content=f"**Report has been published.** Report accepted by <@{accepted_by}>.\nLink to thread: <#{channel_id}>\n\nAgree: {len(agree_users)}\nDisagree: {len(disagree_users)}",
                            embeds=embeds, view=None)
                        message = await bot.get_channel(channel_id).fetch_message(message_id)
                        await message.edit(
                            content=f"**Report has been published.** Report accepted by <@{accepted_by}>.")
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
                        new_user = {"_id": str(alt), "main": str(user.id)}
                        userscol.insert_one(new_user)

                    user_reports_channel = bot.get_channel(USER_REPORTS_CHANNEL)
                    await user_reports_channel.send(content=f"<@&{new_user_report_ping}>\nNew report on `{user.id}`",
                                                    embeds=embeds)
                    await interaction.edit_original_response(
                        content=f"**Report has been published.** Report accepted by <@{accepted_by}>.\nLink to thread: <#{channel_id}>\n\nAgree: {len(agree_users)}\nDisagree: {len(disagree_users)}",
                        embeds=embeds, view=None)
                    message = await bot.get_channel(channel_id).fetch_message(message_id)
                    await message.edit(
                        content=f"**Report has been published.** Report accepted by <@{accepted_by}>.")
                    await bot.get_channel(channel_id).send(
                        f"Report on `{user.id}` has been published. <@{requested_by}> <@{accepted_by}>")
                    inprogresscol.delete_one({"_id": interaction.message.id})

                voters = agree_users + disagree_users
                for voter in voters:
                    voter_query = {"_id": str(voter)}
                    voter_profile = trusteduserscol.find_one(voter_query)
                    if voter_profile:
                        voter_profile["votes"] = str(int(voter_profile["votes"]) + 1)
                        trusteduserscol.replace_one(voter_query, voter_profile)

                staff_query = {"_id": str(requested_by)}
                staff_profile = trusteduserscol.find_one(staff_query)
                staff_weekly_profile = staffweeklycol.find_one(staff_query)
                if staff_profile:
                    staff_profile["reports"] = str(int(staff_profile["reports"]) + 1)
                    trusteduserscol.replace_one(staff_query, staff_profile)
                if staff_weekly_profile:
                    staff_weekly_profile["weekly_reports"] = str(int(staff_weekly_profile["weekly_reports"]) + 1)
                    staffweeklycol.replace_one(staff_query, staff_weekly_profile)

                sr_query = {"_id": str(accepted_by)}
                sr_profile = trusteduserscol.find_one(sr_query)
                sr_weekly_profile = staffweeklycol.find_one(sr_query)
                if sr_profile:
                    sr_profile["reviews"] = str(int(sr_profile["reviews"]) + 1)
                    trusteduserscol.replace_one(sr_query, sr_profile)
                if sr_weekly_profile:
                    sr_weekly_profile["weekly_reviews"] = str(int(sr_weekly_profile["weekly_reviews"]) + 1)
                    staffweeklycol.replace_one(sr_query, sr_weekly_profile)

                new_name = f"p-{interaction.channel.name}"
                await interaction.channel.edit(name=new_name, archived=True)

            #
            if not add_case_list:  # only alts edited
                await interaction.edit_original_response(
                    content=f"Report accepted by <@{accepted_by}>.\nLink to thread: <#{channel_id}>\n\nAgree: {len(agree_users)}\nDisagree: {len(disagree_users)}",
                    embed=r_profile, view=UserVoteView())

            elif len(add_case_list) == 1:  # [[add_case_list]] case to appeal
                add_case_list = add_case_list[0]
                add_case = format_user_add_case(add_case_list, case_title)
                reason_embed = discord.Embed(title="Reason", colour=0x1DCCA9, description=reason)
                embeds = [r_profile, add_case, reason_embed]
                await interaction.edit_original_response(
                    content=f"Appeal accepted by <@{accepted_by}>.\nLink to thread: <#{channel_id}>\n\nAgree: {len(agree_users)}\nDisagree: {len(disagree_users)}",
                    embeds=embeds,
                    view=UserVoteView())

            else:  # new case exists
                add_case = format_user_add_case(add_case_list, case_title)
                embeds = [r_profile, add_case]
                await interaction.edit_original_response(
                    content=f"Report accepted by <@{accepted_by}>.\nLink to thread: <#{channel_id}>\n\nAgree: {len(agree_users)}\nDisagree: {len(disagree_users)}",
                    embeds=embeds,
                    view=UserVoteView())

    @discord.ui.button(label="Disagree", style=discord.ButtonStyle.red, custom_id="uservote:disagree")
    async def disagree_button(self, interaction, button):
        await interaction.response.defer()
        session = inprogresscol.find_one({"_id": interaction.message.id})
        if session:
            requested_by = session["requested_by"]
            channel_id = session["channel_id"]
            message_id = session["message_id"]
            r_profile_list = session["r_profile_list"]
            add_case_list = session["add_case_list"]
            title = session["title"]
            case_title = session["case_title"]
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
                            tags_strings.append(case[2])
                        for tags_string in tags_strings:
                            tags_list = tags_string.split(", ")
                            for tag in tags_list:
                                all_tags_list.append(tag)
                        all_tags_list = sort_user_tags(all_tags_list)
                        title = all_tags_list[0]
                        r_profile = format_user_r_profile(user, r_profile_list, title)
                        await interaction.edit_original_response(
                            content=f"**Report has been rejected.** Report accepted by <@{accepted_by}>.\nLink to thread: <#{channel_id}>\n\nAgree: {len(agree_users)}\nDisagree: {len(disagree_users)}",
                            embed=r_profile, view=None)
                        message = await bot.get_channel(channel_id).fetch_message(message_id)
                        await message.edit(
                            content=f"**Report has been rejected.** Report accepted by <@{accepted_by}>.")
                        await bot.get_channel(channel_id).send(
                            f"Report on `{user.id}` has been rejected. <@{requested_by}> <@{accepted_by}>")
                        inprogresscol.delete_one({"_id": interaction.message.id})

                    elif len(add_case_list) == 1:  # [[add_case_list]] case to appeal
                        add_case_list = add_case_list[0]
                        r_profile = format_user_r_profile(user, r_profile_list, title)
                        add_case = format_user_add_case(add_case_list, case_title)
                        embeds = [r_profile, add_case]
                        #
                        await interaction.edit_original_response(
                            content=f"**Appeal has been rejected.** Appeal accepted by <@{accepted_by}>.\nLink to thread: <#{channel_id}>\n\nAgree: {len(agree_users)}\nDisagree: {len(disagree_users)}",
                            embeds=embeds, view=None)
                        message = await bot.get_channel(channel_id).fetch_message(message_id)
                        await message.edit(
                            content=f"**Appeal has been rejected.** Appeal accepted by <@{accepted_by}>.")
                        await bot.get_channel(channel_id).send(
                            f"Appeal on `{user.id}` has been rejected. <@{requested_by}> <@{accepted_by}>")
                        inprogresscol.delete_one({"_id": interaction.message.id})

                    else:  # new case exists
                        r_profile = format_user_r_profile(user, r_profile_list, title)
                        add_case = format_user_add_case(add_case_list, case_title)
                        embeds = [r_profile, add_case]
                        await interaction.edit_original_response(
                            content=f"**Report has been rejected.** Report accepted by <@{accepted_by}>.\nLink to thread: <#{channel_id}>\n\nAgree: {len(agree_users)}\nDisagree: {len(disagree_users)}",
                            embeds=embeds, view=None)
                        message = await bot.get_channel(channel_id).fetch_message(message_id)
                        await message.edit(
                            content=f"**Report has been rejected.** Report accepted by <@{accepted_by}>.")
                        await bot.get_channel(channel_id).send(
                            f"Report on `{user.id}` has been rejected. <@{requested_by}> <@{accepted_by}>")
                        inprogresscol.delete_one({"_id": interaction.message.id})
                else:  # if new reported user
                    r_profile = format_user_r_profile(user, r_profile_list, title)
                    add_case = format_user_add_case(add_case_list, case_title)
                    embeds = [r_profile, add_case]
                    await interaction.edit_original_response(
                        content=f"**Report has been rejected.** Report accepted by <@{accepted_by}>.\nLink to thread: <#{channel_id}>\n\nAgree: {len(agree_users)}\nDisagree: {len(disagree_users)}",
                        embeds=embeds, view=None)
                    message = await bot.get_channel(channel_id).fetch_message(message_id)
                    await message.edit(
                        content=f"**Report has been rejected.** Report accepted by <@{accepted_by}>.")
                    await bot.get_channel(channel_id).send(
                        f"Report on `{user.id}` has been rejected. <@{requested_by}> <@{accepted_by}>")
                    inprogresscol.delete_one({"_id": interaction.message.id})
                voters = agree_users + disagree_users
                for voter in voters:
                    voter_query = {"_id": str(voter)}
                    voter_profile = trusteduserscol.find_one(voter_query)
                    if voter_profile:
                        voter_profile["votes"] = str(int(voter_profile["votes"]) + 1)
                        trusteduserscol.replace_one(voter_query, voter_profile)
                new_name = f"r-{interaction.channel.name}"
                await interaction.channel.edit(name=new_name, archived=True)
                return
            if not add_case_list:  # only alts edited
                await interaction.edit_original_response(
                    content=f"Report accepted by <@{accepted_by}>.\nLink to thread: <#{channel_id}>\n\nAgree: {len(agree_users)}\nDisagree: {len(disagree_users)}",
                    embed=r_profile, view=UserVoteView())
            elif len(add_case_list) == 1:  # [[add_case_list]] case to appeal
                add_case_list = add_case_list[0]
                add_case = format_user_add_case(add_case_list, case_title)
                reason_embed = discord.Embed(title="Reason", colour=0x1DCCA9, description=reason)
                embeds = [r_profile, add_case, reason_embed]
                await interaction.edit_original_response(
                    content=f"Appeal accepted by <@{accepted_by}>.\nLink to thread: <#{channel_id}>\n\nAgree: {len(agree_users)}\nDisagree: {len(disagree_users)}",
                    embeds=embeds, view=UserVoteView())
            else:  # new case exists
                add_case = format_user_add_case(add_case_list, case_title)
                embeds = [r_profile, add_case]
                await interaction.edit_original_response(
                    content=f"Report accepted by <@{accepted_by}>.\nLink to thread: <#{channel_id}>\n\nAgree: {len(agree_users)}\nDisagree: {len(disagree_users)}",
                    embeds=embeds, view=UserVoteView())

    @discord.ui.button(label="Remove Vote", style=discord.ButtonStyle.primary, custom_id="uservote:removevote")
    async def remove_vote_button(self, interaction, button):
        await interaction.response.defer()
        session = inprogresscol.find_one({"_id": interaction.message.id})
        if session:
            channel_id = session["channel_id"]
            r_profile_list = session["r_profile_list"]
            add_case_list = session["add_case_list"]
            title = session["title"]
            case_title = session["case_title"]
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
                await interaction.edit_original_response(
                    content=f"Report accepted by <@{accepted_by}>.\nLink to thread: <#{channel_id}>\n\nAgree: {len(agree_users)}\nDisagree: {len(disagree_users)}",
                    embeds=embeds, view=UserVoteView())
            elif len(add_case_list) == 1:  # [[add_case_list]] case to appeal
                add_case_list = add_case_list[0]
                add_case = format_user_add_case(add_case_list, case_title)
                reason_embed = discord.Embed(title="Reason", colour=0x1DCCA9, description=reason)
                embeds = [r_profile, add_case, reason_embed]
                await interaction.edit_original_response(
                    content=f"Appeal accepted by <@{accepted_by}>.\nLink to thread: <#{channel_id}>\n\nAgree: {len(agree_users)}\nDisagree: {len(disagree_users)}",
                    embeds=embeds, view=UserVoteView())
            else:
                add_case = format_user_add_case(add_case_list, case_title)
                embeds = [r_profile, add_case]
                await interaction.edit_original_response(
                    content=f"Report accepted by <@{accepted_by}>.\nLink to thread: <#{channel_id}>\n\nAgree: {len(agree_users)}\nDisagree: {len(disagree_users)}",
                    embeds=embeds, view=UserVoteView())

    @discord.ui.button(label="Publish", style=discord.ButtonStyle.grey, custom_id="uservote:publish")
    async def publish_button(self, interaction, button):
        await interaction.response.defer()
        session = inprogresscol.find_one({"_id": interaction.message.id})
        if session:
            requested_by = session["requested_by"]
            channel_id = session["channel_id"]
            message_id = session["message_id"]
            r_profile_list = session["r_profile_list"]
            add_case_list = session["add_case_list"]
            title = session["title"]
            case_title = session["case_title"]
            agree_users = session["agree_users"]
            disagree_users = session["disagree_users"]
            reason = session.get("reason")
            user_id = session["user_id"]
            user = await bot.fetch_user(user_id)
            o5_check = get(interaction.user.guild.roles, id=o5_role) in interaction.user.roles
            sr_check = any(role.id == sr_role for role in interaction.user.roles) and interaction.user.id != requested_by and len(
                agree_users) >= 4
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
                            userscol.insert_one(new_user)
                        for alt in removed_alts_list:
                            userscol.delete_one({"_id": alt})
                        update_operation = {'$set': {"r_profile_list": r_profile_list}}
                        userscol.update_one(user_query, update_operation)
                    if not add_case_list:  # only alts edited
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
                        r_profile = format_user_r_profile(user, r_profile_list, title)
                        user_reports_channel = bot.get_channel(USER_REPORTS_CHANNEL)
                        await user_reports_channel.send(content=f"<@&{updated_user_report_ping}>\nAlts edited for `{user.id}`",
                                                        embed=r_profile)
                        reason_embed = discord.Embed(title="Reason", description=reason)
                        await user_reports_channel.send(content=f"Reason for change(s)", embed=reason_embed)
                        await interaction.edit_original_response(
                            content=f"**Report has been published.** Report accepted by <@{accepted_by}>.\nLink to thread: <#{channel_id}>\n\nAgree: {len(agree_users)}\nDisagree: {len(disagree_users)}",
                            embed=r_profile, view=None)
                        message = await bot.get_channel(channel_id).fetch_message(message_id)
                        await message.edit(
                            content=f"**Report has been published.** Report accepted by <@{accepted_by}>.")
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
                                tags_strings.append(case[2])
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
                        await interaction.edit_original_response(
                            content=f"**Appeal has been published.** Appeal accepted by <@{accepted_by}>.\nLink to thread: <#{channel_id}>\n\nAgree: {len(agree_users)}\nDisagree: {len(disagree_users)}",
                            embeds=embeds, view=None)
                        message = await bot.get_channel(channel_id).fetch_message(message_id)
                        await message.edit(
                            content=f"**Appeal has been published.** Appeal accepted by <@{accepted_by}>.")
                        await bot.get_channel(channel_id).send(
                            f"Appeal on `{user.id}` has been published. <@{requested_by}> <@{accepted_by}>")
                        inprogresscol.delete_one({"_id": interaction.message.id})
                    else:  # new case exists
                        add_case_list[6] = f"{interaction.user.mention}"
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
                        serverscol.update_one(query_filter, update_operation)
                        update_operation = {'$set': {str(no_of_cases + 1): add_case_list}}
                        userscol.update_one(query_filter, update_operation)

                        user_reports_channel = bot.get_channel(USER_REPORTS_CHANNEL)
                        await user_reports_channel.send(content=f"<@&{updated_user_report_ping}>\nReport added on `{user.id}`",
                                                        embeds=embeds)
                        await interaction.edit_original_response(
                            content=f"**Report has been published.** Report accepted by <@{accepted_by}>.\nLink to thread: <#{channel_id}>\n\nAgree: {len(agree_users)}\nDisagree: {len(disagree_users)}",
                            embeds=embeds, view=None)
                        message = await bot.get_channel(channel_id).fetch_message(message_id)
                        await message.edit(
                            content=f"**Report has been published.** Report accepted by <@{accepted_by}>.")
                        await bot.get_channel(channel_id).send(
                            f"Report on `{user.id}` has been published. <@{requested_by}> <@{accepted_by}>")
                        inprogresscol.delete_one({"_id": interaction.message.id})
                else:  # if new reported user
                    add_case_list[6] = f"{interaction.user.mention}"
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
                        userscol.insert_one(new_user)

                    user_reports_channel = bot.get_channel(USER_REPORTS_CHANNEL)
                    await user_reports_channel.send(content=f"<@&{new_user_report_ping}>\nNew report on `{user.id}`",
                                                    embeds=embeds)
                    await interaction.edit_original_response(
                        content=f"**Report has been published.** Report accepted by <@{accepted_by}>.\nLink to thread: <#{channel_id}>\n\nAgree: {len(agree_users)}\nDisagree: {len(disagree_users)}",
                        embeds=embeds, view=None)
                    message = await bot.get_channel(channel_id).fetch_message(message_id)
                    await message.edit(
                        content=f"**Report has been published.** Report accepted by <@{accepted_by}>.")
                    await bot.get_channel(channel_id).send(
                        f"Report on `{user.id}` has been published. <@{requested_by}> <@{accepted_by}>")
                    inprogresscol.delete_one({"_id": interaction.message.id})
                voters = agree_users + disagree_users
                for voter in voters:
                    voter_query = {"_id": str(voter)}
                    voter_profile = trusteduserscol.find_one(voter_query)
                    if voter_profile:
                        voter_profile["votes"] = str(int(voter_profile["votes"]) + 1)
                        trusteduserscol.replace_one(voter_query, voter_profile)

                staff_query = {"_id": str(requested_by)}
                staff_profile = trusteduserscol.find_one(staff_query)
                staff_weekly_profile = staffweeklycol.find_one(staff_query)
                if staff_profile:
                    staff_profile["reports"] = str(int(staff_profile["reports"]) + 1)
                    trusteduserscol.replace_one(staff_query, staff_profile)
                if staff_weekly_profile:
                    staff_weekly_profile["weekly_reports"] = str(int(staff_weekly_profile["weekly_reports"]) + 1)
                    staffweeklycol.replace_one(staff_query, staff_weekly_profile)

                sr_query = {"_id": str(accepted_by)}
                sr_profile = trusteduserscol.find_one(sr_query)
                sr_weekly_profile = staffweeklycol.find_one(sr_query)
                if sr_profile:
                    sr_profile["reviews"] = str(int(sr_profile["reviews"]) + 1)
                    trusteduserscol.replace_one(sr_query, sr_profile)
                if sr_weekly_profile:
                    sr_weekly_profile["weekly_reviews"] = str(int(sr_weekly_profile["weekly_reviews"]) + 1)
                    staffweeklycol.replace_one(sr_query, sr_weekly_profile)

                new_name = f"p-{interaction.channel.name}"
                await interaction.channel.edit(name=new_name, archived=True)

            else:
                await interaction.followup.send("You do not have permission to publish the report.", ephemeral=True)


# new server
class NewServerReportView(discord.ui.View):
    def __init__(self, guild, requested_by):
        super().__init__(timeout=None)
        self.guild = guild
        self.requested_by = requested_by
    @discord.ui.button(label="Report", style=discord.ButtonStyle.red, custom_id="newserverreport:report")
    async def report_button(self, interaction, button):
        #
        guild = self.guild
        requested_by = self.requested_by
        #
        await interaction.response.defer()
        ongoing_report = []
        tickets_channel = bot.get_channel(TICKETS_CHANNEL)
        active_threads = tickets_channel.threads
        for thread in active_threads:
            try:
                async for message in thread.history():
                    if message.content.startswith(f"Adding report on `{guild.id}`") or \
                            message.content.startswith(f"Editing owner for `{guild.id}`") or \
                            message.content.startswith(f"Appealing for `{guild.id}`") or \
                            message.content.startswith(f"Initializing report on `{guild.id}`") \
                            and message.author.id == bot.user.id:
                        ongoing_report.append(message.jump_url)
            except Exception:
                pass
        if ongoing_report:
            await interaction.followup.send(
                f"There already exists an ongoing report on `{guild.id}`: {ongoing_report[0]}")
            return
        ongoing_vote = []
        vote_channel = bot.get_channel(VOTE_CHANNEL)
        active_threads = vote_channel.threads
        for thread in active_threads:
            if thread.name == f"server-{guild.id}":
                ongoing_vote.append(thread.jump_url)
        if ongoing_vote:
            await interaction.followup.send(
                f"There already exists an ongoing vote on `{guild.id}`: {ongoing_vote[0]}")
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
            add_case_list = [
                # [0] date added
                "",
                # [1] tags
                "",
                # [2] reason
                "",
                # [3] contributor
                "",
                # [4] tri staff
                "",
                # [5] accepted by
                "",
                # [6] image_links
                [],
            ]
            add_case_list[
                0] = f"<t:{round(int(discord.utils.utcnow().timestamp()))}:D> (<t:{round(int(discord.utils.utcnow().timestamp()))}:R>)"
            add_case_list[4] = f"{interaction.user.mention}"
            channel_id = msg.channel.id
            message_id = msg.id
            r_profile = format_server_r_profile(guild, r_profile_list, title)
            add_case = format_server_add_case(add_case_list, case_title)
            embeds = [r_profile, add_case]
            await msg.edit(embeds=embeds,
                           view=ServerOwnerView(guild, requested_by, channel_id, message_id, r_profile_list, add_case_list,
                                         title, case_title))
        elif any(role.id == ticket_ping for role in interaction.user.roles):
            await interaction.followup.send(
                f"This was requested by {requested_by.mention}, you cannot interact with this component.",
                ephemeral=True)
        else:
            await interaction.followup.send("You do not have permission to use this button.", ephemeral=True)

class ServerOwnerView(discord.ui.View):
    def __init__(self, guild, requested_by, channel_id, message_id, r_profile_list, add_case_list, title, case_title):
        super().__init__(timeout=None)
        self.guild = guild
        self.requested_by = requested_by
        self.channel_id = channel_id
        self.message_id = message_id
        self.r_profile_list = r_profile_list
        self.add_case_list = add_case_list
        self.title = title
        self.case_title = case_title

    @discord.ui.button(emoji="<:rightarrow:1458096774521553038>", style=discord.ButtonStyle.grey, custom_id="serverowner:next")
    async def next_button(self, interaction, button):
        await interaction.response.defer()
        #
        guild = self.guild
        requested_by = self.requested_by
        channel_id = self.channel_id
        message_id = self.message_id
        r_profile_list = self.r_profile_list
        add_case_list = self.add_case_list
        title = self.title
        case_title = self.case_title
        #
        message = await bot.get_channel(channel_id).fetch_message(message_id)
        if requested_by == interaction.user or any(role.id == sr_role for role in interaction.user.roles):
            r_profile = format_server_r_profile(guild, r_profile_list, title)
            add_case = format_server_add_case(add_case_list, case_title)
            embeds = [r_profile, add_case]
            await message.edit(embeds=embeds,
                               view=ServerTagsView(guild, requested_by, channel_id, message_id, r_profile_list,
                                                    add_case_list,
                                                    title, case_title))

    @discord.ui.button(label="Owner", style=discord.ButtonStyle.green, custom_id="serverowner:input")
    async def reason_button(self, interaction, button):
        #
        guild = self.guild
        requested_by = self.requested_by
        channel_id = self.channel_id
        message_id = self.message_id
        r_profile_list = self.r_profile_list
        add_case_list = self.add_case_list
        title = self.title
        case_title = self.case_title
        #
        if requested_by == interaction.user:
            await interaction.response.send_modal(
                ServerOwnerModal(guild, requested_by, channel_id, message_id, r_profile_list, add_case_list, title,
                            case_title))
class ServerOwnerModal(discord.ui.Modal, title="Owner"):
    owner = discord.ui.TextInput(label="Owner", placeholder="Input Server Owner ID here.", required=True,
                                  style=discord.TextStyle.short)

    def __init__(self, guild, requested_by, channel_id, message_id, r_profile_list, add_case_list, title, case_title):
        super().__init__(timeout=None)
        self.guild = guild
        self.requested_by = requested_by
        self.channel_id = channel_id
        self.message_id = message_id
        self.r_profile_list = r_profile_list
        self.add_case_list = add_case_list
        self.title = title
        self.case_title = case_title

    async def on_submit(self, interaction):
        await interaction.response.defer()
        #
        guild = self.guild
        requested_by = self.requested_by
        channel_id = self.channel_id
        message_id = self.message_id
        r_profile_list = self.r_profile_list
        add_case_list = self.add_case_list
        title = self.title
        case_title = self.case_title
        #
        message = await bot.get_channel(channel_id).fetch_message(message_id)
        try:
            valid_owner = await bot.fetch_user(int(self.owner.value))
        except Exception:
            pass
        else:
            if valid_owner:
                r_profile_list[0] = f"{valid_owner.mention}"
        #
        self.r_profile_list = r_profile_list
        #
        r_profile = format_server_r_profile(guild, r_profile_list, title)
        add_case = format_server_add_case(add_case_list, case_title)
        embeds = [r_profile, add_case]
        await message.edit(embeds=embeds,
                           view=ServerOwnerView(guild, requested_by, channel_id, message_id, r_profile_list, add_case_list,
                                           title, case_title))

class ServerTagsView(discord.ui.View):
    def __init__(self, guild, requested_by, channel_id, message_id, r_profile_list, add_case_list, title, case_title):
        super().__init__(timeout=None)
        self.guild = guild
        self.requested_by = requested_by
        self.channel_id = channel_id
        self.message_id = message_id
        self.r_profile_list = r_profile_list
        self.add_case_list = add_case_list
        self.title = title
        self.case_title = case_title

    @discord.ui.button(emoji="<:leftarrow:1458096658062770176>", style=discord.ButtonStyle.grey, custom_id="servertags:prev")
    async def prev_button(self, interaction, button):
        await interaction.response.defer()
        #
        guild = self.guild
        requested_by = self.requested_by
        channel_id = self.channel_id
        message_id = self.message_id
        r_profile_list = self.r_profile_list
        add_case_list = self.add_case_list
        title = self.title
        case_title = self.case_title
        #
        message = await bot.get_channel(channel_id).fetch_message(message_id)
        if requested_by == interaction.user or any(role.id == sr_role for role in interaction.user.roles):
            r_profile = format_server_r_profile(guild, r_profile_list, title)
            add_case = format_server_add_case(add_case_list, case_title)
            embeds = [r_profile, add_case]
            await message.edit(embeds=embeds,
                               view=ServerOwnerView(guild, requested_by, channel_id, message_id, r_profile_list,
                                                   add_case_list, title, case_title))

    @discord.ui.button(emoji="<:rightarrow:1458096774521553038>", style=discord.ButtonStyle.grey, custom_id="servertags:next")
    async def next_button(self, interaction, button):
        await interaction.response.defer()
        #
        guild = self.guild
        requested_by = self.requested_by
        channel_id = self.channel_id
        message_id = self.message_id
        r_profile_list = self.r_profile_list
        add_case_list = self.add_case_list
        title = self.title
        case_title = self.case_title
        #
        message = await bot.get_channel(channel_id).fetch_message(message_id)
        if requested_by == interaction.user or any(role.id == sr_role for role in interaction.user.roles):
            r_profile = format_server_r_profile(guild, r_profile_list, title)
            add_case = format_server_add_case(add_case_list, case_title)
            embeds = [r_profile, add_case]
            await message.edit(embeds=embeds,
                               view=ServerReasonView(guild, requested_by, channel_id, message_id, r_profile_list, add_case_list,
                                              title, case_title))

    @discord.ui.select(options=server_tags_options, placeholder="Select Tag(s)...", custom_id="servertags:select",
                       max_values=len(server_tags_options))
    async def select_callback(self, interaction, select):
        await interaction.response.defer()
        #
        guild = self.guild
        requested_by = self.requested_by
        channel_id = self.channel_id
        message_id = self.message_id
        r_profile_list = self.r_profile_list
        add_case_list = self.add_case_list
        title = self.title
        case_title = self.case_title
        #
        message = await bot.get_channel(channel_id).fetch_message(message_id)
        if requested_by == interaction.user:
            sorted_tags = sort_server_tags(self.select_callback.values)
            case_title = sorted_tags[0]
            tags = selected_string(sorted_tags)
            add_case_list[1] = tags
            title = sorted_tags[0]
            all_other_tags = selected_string(sorted_tags[1:])
            r_profile_list[1] = all_other_tags
            #
            self.r_profile_list = r_profile_list
            self.add_case_list = add_case_list
            self.title = title
            self.case_title = case_title
            #
            r_profile = format_server_r_profile(guild, r_profile_list, title)
            add_case = format_server_add_case(add_case_list, case_title)
            embeds = [r_profile, add_case]
            await message.edit(embeds=embeds)

class ServerReasonView(discord.ui.View):
    def __init__(self, guild, requested_by, channel_id, message_id, r_profile_list, add_case_list, title, case_title):
        super().__init__(timeout=None)
        self.guild = guild
        self.requested_by = requested_by
        self.channel_id = channel_id
        self.message_id = message_id
        self.r_profile_list = r_profile_list
        self.add_case_list = add_case_list
        self.title = title
        self.case_title = case_title

    @discord.ui.button(emoji="<:leftarrow:1458096658062770176>", style=discord.ButtonStyle.grey, custom_id="serverreason:prev")
    async def prev_button(self, interaction, button):
        await interaction.response.defer()
        #
        guild = self.guild
        requested_by = self.requested_by
        channel_id = self.channel_id
        message_id = self.message_id
        r_profile_list = self.r_profile_list
        add_case_list = self.add_case_list
        title = self.title
        case_title = self.case_title
        #
        message = await bot.get_channel(channel_id).fetch_message(message_id)
        if requested_by == interaction.user or any(role.id == sr_role for role in interaction.user.roles):
            r_profile = format_server_r_profile(guild, r_profile_list, title)
            add_case = format_server_add_case(add_case_list, case_title)
            embeds = [r_profile, add_case]
            await message.edit(embeds=embeds,
                               view=ServerTagsView(guild, requested_by, channel_id, message_id, r_profile_list, add_case_list,
                                              title, case_title))

    @discord.ui.button(emoji="<:rightarrow:1458096774521553038>", style=discord.ButtonStyle.grey, custom_id="serverreason:next")
    async def next_button(self, interaction, button):
        await interaction.response.defer()
        #
        guild = self.guild
        requested_by = self.requested_by
        channel_id = self.channel_id
        message_id = self.message_id
        r_profile_list = self.r_profile_list
        add_case_list = self.add_case_list
        title = self.title
        case_title = self.case_title
        #
        message = await bot.get_channel(channel_id).fetch_message(message_id)
        if requested_by == interaction.user or any(role.id == sr_role for role in interaction.user.roles):
            r_profile = format_server_r_profile(guild, r_profile_list, title)
            add_case = format_server_add_case(add_case_list, case_title)
            embeds = [r_profile, add_case]
            await message.edit(embeds=embeds,
                               view=ServerContributorView(guild, requested_by, channel_id, message_id, r_profile_list,
                                                    add_case_list,
                                                    title, case_title))

    @discord.ui.button(label="Reason", style=discord.ButtonStyle.green, custom_id="serverreason:input")
    async def reason_button(self, interaction, button):
        #
        guild = self.guild
        requested_by = self.requested_by
        channel_id = self.channel_id
        message_id = self.message_id
        r_profile_list = self.r_profile_list
        add_case_list = self.add_case_list
        title = self.title
        case_title = self.case_title
        #
        if requested_by == interaction.user:
            await interaction.response.send_modal(
                ServerReasonModal(guild, requested_by, channel_id, message_id, r_profile_list, add_case_list, title,
                            case_title))
class ServerReasonModal(discord.ui.Modal, title="Reason"):
    reason = discord.ui.TextInput(label="Reason", placeholder="Input reason here.", required=True,
                                  style=discord.TextStyle.short)

    def __init__(self, guild, requested_by, channel_id, message_id, r_profile_list, add_case_list, title, case_title):
        super().__init__(timeout=None)
        self.guild = guild
        self.requested_by = requested_by
        self.channel_id = channel_id
        self.message_id = message_id
        self.r_profile_list = r_profile_list
        self.add_case_list = add_case_list
        self.title = title
        self.case_title = case_title

    async def on_submit(self, interaction):
        await interaction.response.defer()
        #
        guild = self.guild
        requested_by = self.requested_by
        channel_id = self.channel_id
        message_id = self.message_id
        r_profile_list = self.r_profile_list
        add_case_list = self.add_case_list
        title = self.title
        case_title = self.case_title
        #
        message = await bot.get_channel(channel_id).fetch_message(message_id)
        add_case_list[2] = str(self.reason.value)
        #
        self.add_case_list = add_case_list
        #
        r_profile = format_server_r_profile(guild, r_profile_list, title)
        add_case = format_server_add_case(add_case_list, case_title)
        embeds = [r_profile, add_case]
        await message.edit(embeds=embeds,
                           view=ServerReasonView(guild, requested_by, channel_id, message_id, r_profile_list, add_case_list,
                                           title, case_title))

class ServerContributorView(discord.ui.View):
    def __init__(self, guild, requested_by, channel_id, message_id, r_profile_list, add_case_list, title, case_title):
        super().__init__(timeout=None)
        self.guild = guild
        self.requested_by = requested_by
        self.channel_id = channel_id
        self.message_id = message_id
        self.r_profile_list = r_profile_list
        self.add_case_list = add_case_list
        self.title = title
        self.case_title = case_title

    @discord.ui.button(emoji="<:leftarrow:1458096658062770176>", style=discord.ButtonStyle.grey,
                       custom_id="servercontributor:prev")
    async def prev_button(self, interaction, button):
        await interaction.response.defer()
        #
        guild = self.guild
        requested_by = self.requested_by
        channel_id = self.channel_id
        message_id = self.message_id
        r_profile_list = self.r_profile_list
        add_case_list = self.add_case_list
        title = self.title
        case_title = self.case_title
        #
        message = await bot.get_channel(channel_id).fetch_message(message_id)
        if requested_by == interaction.user or any(role.id == sr_role for role in interaction.user.roles):
            r_profile = format_server_r_profile(guild, r_profile_list, title)
            add_case = format_server_add_case(add_case_list, case_title)
            embeds = [r_profile, add_case]
            await message.edit(embeds=embeds,
                               view=ServerReasonView(guild, requested_by, channel_id, message_id, r_profile_list,
                                               add_case_list,
                                               title, case_title))

    @discord.ui.button(emoji="<:rightarrow:1458096774521553038>", style=discord.ButtonStyle.grey,
                       custom_id="servercontributor:next")
    async def next_button(self, interaction, button):
        await interaction.response.defer()
        #
        guild = self.guild
        requested_by = self.requested_by
        channel_id = self.channel_id
        message_id = self.message_id
        r_profile_list = self.r_profile_list
        add_case_list = self.add_case_list
        title = self.title
        case_title = self.case_title
        #
        message = await bot.get_channel(channel_id).fetch_message(message_id)
        if requested_by == interaction.user or any(role.id == sr_role for role in interaction.user.roles):
            r_profile = format_server_r_profile(guild, r_profile_list, title)
            add_case = format_server_add_case(add_case_list, case_title)
            embeds = [r_profile, add_case]
            await message.edit(embeds=embeds,
                               view=ServerProofsView(guild, requested_by, channel_id, message_id, r_profile_list,
                                               add_case_list,
                                               title, case_title))

    @discord.ui.button(label="Contributor", style=discord.ButtonStyle.green, custom_id="servercontributor:input")
    async def contributor_button(self, interaction, button):
        #
        guild = self.guild
        requested_by = self.requested_by
        channel_id = self.channel_id
        message_id = self.message_id
        r_profile_list = self.r_profile_list
        add_case_list = self.add_case_list
        title = self.title
        case_title = self.case_title
        #
        if requested_by == interaction.user:
            await interaction.response.send_modal(
                ServerContributorModal(guild, requested_by, channel_id, message_id, r_profile_list, add_case_list, title,
                                 case_title))
class ServerContributorModal(discord.ui.Modal, title="Contributor"):
    contributor = discord.ui.TextInput(label="Contributor",
                                       placeholder="User ID / n if Anonymous.", required=True,
                                       style=discord.TextStyle.short)

    def __init__(self, guild, requested_by, channel_id, message_id, r_profile_list, add_case_list, title, case_title):
        super().__init__(timeout=None)
        self.guild = guild
        self.requested_by = requested_by
        self.channel_id = channel_id
        self.message_id = message_id
        self.r_profile_list = r_profile_list
        self.add_case_list = add_case_list
        self.title = title
        self.case_title = case_title

    async def on_submit(self, interaction):
        await interaction.response.defer()
        #
        guild = self.guild
        requested_by = self.requested_by
        channel_id = self.channel_id
        message_id = self.message_id
        r_profile_list = self.r_profile_list
        add_case_list = self.add_case_list
        title = self.title
        case_title = self.case_title
        #
        message = await bot.get_channel(channel_id).fetch_message(message_id)
        contributor_input = self.contributor.value
        if contributor_input.lower() == "n":
            add_case_list[3] = "Anonymous"
        else:
            try:
                contributor_id = await bot.fetch_user(int(contributor_input))
            except Exception:
                add_case_list[3] = ""
            else:
                add_case_list[3] = f"<@{contributor_id.id}>"
        #
        self.add_case_list = add_case_list
        #
        r_profile = format_server_r_profile(guild, r_profile_list, title)
        add_case = format_server_add_case(add_case_list, case_title)
        embeds = [r_profile, add_case]
        await message.edit(embeds=embeds,
                           view=ServerContributorView(guild, requested_by, channel_id, message_id, r_profile_list,
                                                add_case_list, title, case_title))

class ServerProofsView(discord.ui.View):
    def __init__(self, guild, requested_by, channel_id, message_id, r_profile_list, add_case_list, title, case_title):
        super().__init__(timeout=None)
        self.guild = guild
        self.requested_by = requested_by
        self.channel_id = channel_id
        self.message_id = message_id
        self.r_profile_list = r_profile_list
        self.add_case_list = add_case_list
        self.title = title
        self.case_title = case_title

    @discord.ui.button(emoji="<:leftarrow:1458096658062770176>", style=discord.ButtonStyle.grey, custom_id="serverproofs:prev")
    async def prev_button(self, interaction, button):
        await interaction.response.defer()
        #
        guild = self.guild
        requested_by = self.requested_by
        channel_id = self.channel_id
        message_id = self.message_id
        r_profile_list = self.r_profile_list
        add_case_list = self.add_case_list
        title = self.title
        case_title = self.case_title
        #
        message = await bot.get_channel(channel_id).fetch_message(message_id)
        if requested_by == interaction.user or any(role.id == sr_role for role in interaction.user.roles):
            r_profile = format_server_r_profile(guild, r_profile_list, title)
            add_case = format_server_add_case(add_case_list, case_title)
            embeds = [r_profile, add_case]
            await message.edit(embeds=embeds,
                               view=ServerContributorView(guild, requested_by, channel_id, message_id, r_profile_list,
                                                    add_case_list, title, case_title))

    @discord.ui.button(label="Add Proofs", style=discord.ButtonStyle.green, custom_id="serverproofs:input")
    async def proofs_button(self, interaction, button):
        #
        guild = self.guild
        requested_by = self.requested_by
        channel_id = self.channel_id
        message_id = self.message_id
        r_profile_list = self.r_profile_list
        add_case_list = self.add_case_list
        title = self.title
        case_title = self.case_title
        #
        message = await bot.get_channel(channel_id).fetch_message(message_id)
        if requested_by == interaction.user:
            image_links = []
            add_case_list[6] = []
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
                                        add_case_list[6].append(new_image_url)
                        except Exception:
                            await msg.channel.send(f"An error occurred with file {attachment.filename}")
            #
            self.add_case_list = add_case_list
            #
            image_embeds = image_links_to_embeds(image_links)
            await interaction.followup.send(f"Images received from {interaction.user.mention}.",
                                            embeds=image_embeds)

    @discord.ui.button(label="Show Proofs", style=discord.ButtonStyle.grey, custom_id="serverproofs:showproofs")
    async def show_proofs_button(self, interaction, button):
        await interaction.response.defer()
        #
        guild = self.guild
        requested_by = self.requested_by
        channel_id = self.channel_id
        message_id = self.message_id
        r_profile_list = self.r_profile_list
        add_case_list = self.add_case_list
        title = self.title
        case_title = self.case_title
        #
        if requested_by == interaction.user or any(role.id == sr_role for role in interaction.user.roles):
            image_embeds = image_links_to_embeds(add_case_list[6])
            await interaction.followup.send(f"Proofs for `{guild.id}`",
                                            embeds=image_embeds, ephemeral=True)

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.grey, custom_id="serverproofs:cancel")
    async def cancel_button(self, interaction, button):
        await interaction.response.defer()
        #
        guild = self.guild
        requested_by = self.requested_by
        channel_id = self.channel_id
        message_id = self.message_id
        #
        message = await bot.get_channel(channel_id).fetch_message(message_id)
        if requested_by == interaction.user or any(role.id == sr_role for role in interaction.user.roles):
            await message.edit(content=f"**Cancelled by {interaction.user.mention}.**", view=None)

    @discord.ui.button(label="Accept", style=discord.ButtonStyle.grey, custom_id="serverproofs:accept")
    async def accept_button(self, interaction, button):
        await interaction.response.defer()
        #
        guild = self.guild
        requested_by = self.requested_by
        channel_id = self.channel_id
        message_id = self.message_id
        r_profile_list = self.r_profile_list
        add_case_list = self.add_case_list
        title = self.title
        case_title = self.case_title
        #
        message = await bot.get_channel(channel_id).fetch_message(message_id)
        if any(role.id == sr_role for role in interaction.user.roles) and interaction.user != requested_by:
            accepted_by = interaction.user
            add_case_list[5] = f"<@{interaction.user.id}>"
            #
            self.add_case_list = add_case_list
            #
            r_profile = format_server_r_profile(guild, r_profile_list, title)
            add_case = format_server_add_case(add_case_list, case_title)
            embeds = [r_profile, add_case]
            #
            vote_channel = bot.get_channel(VOTE_CHANNEL)
            agree_users = []
            disagree_users = []
            all_images_to_show = add_case_list[6]
            image_embeds = image_links_to_embeds(all_images_to_show)
            new_report_message = await vote_channel.send(content=f"New report on `{guild.id}`")
            new_report_thread = await new_report_message.create_thread(name=f"server-{guild.id}")
            await new_report_thread.send(f"<@&{ticket_ping}>")
            await new_report_thread.send(
                content=f"Report accepted by {accepted_by.mention}.\nLink to thread: <#{channel_id}>\n\nAgree: 0\nDisagree: 0",
                embeds=embeds,
                view=ServerVoteView(guild, requested_by, channel_id, message_id, r_profile_list, add_case_list, title,
                              case_title, accepted_by, agree_users, disagree_users))
            await new_report_thread.send(content=f"Proofs for `{guild.id}`", embeds=image_embeds)
            await message.edit(content="Report has been submitted for voting.", embeds=embeds, view=None)
        else:
            await interaction.followup.send("You do not have permission to accept the report for voting.",
                                            ephemeral=True)


# edit server
class EditServerReportView(discord.ui.View):
    def __init__(self, guild, server_profile, requested_by, current_case):
        super().__init__(timeout=None)
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
        image_links = cases[current_case - 1][6]
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
        ongoing_report = []
        tickets_channel = bot.get_channel(TICKETS_CHANNEL)
        active_threads = tickets_channel.threads
        for thread in active_threads:
            try:
                async for message in thread.history():
                    if message.content.startswith(f"Adding report on `{guild.id}`") or \
                            message.content.startswith(f"Editing owner for `{guild.id}`") or \
                            message.content.startswith(f"Appealing for `{guild.id}`") or \
                            message.content.startswith(f"Initializing report on `{guild.id}`") \
                            and message.author.id == bot.user.id:
                        ongoing_report.append(message.jump_url)
            except Exception:
                pass
        if ongoing_report:
            await interaction.followup.send(
                f"There already exists an ongoing report on `{guild.id}`: {ongoing_report[0]}")
            return
        ongoing_vote = []
        vote_channel = bot.get_channel(VOTE_CHANNEL)
        active_threads = vote_channel.threads
        for thread in active_threads:
            if thread.name == f"server-{guild.id}":
                ongoing_vote.append(thread.jump_url)
        if ongoing_vote:
            await interaction.followup.send(
                f"There already exists an ongoing vote on `{guild.id}`: {ongoing_vote[0]}")
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
                tags_strings.append(case[1])
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
            embeds = [r_profile, reason_embed]
            await msg.edit(embeds=embeds, view=EditOwnerOnlyView(guild, requested_by, channel_id, message_id,
                                                                r_profile_list, title, reason))
        elif any(role.id == ticket_ping for role in interaction.user.roles):
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
        current_case = self.current_case
        #
        await interaction.response.defer()
        ongoing_report = []
        tickets_channel = bot.get_channel(TICKETS_CHANNEL)
        active_threads = tickets_channel.threads
        for thread in active_threads:
            try:
                async for message in thread.history():
                    if message.content.startswith(f"Adding report on `{guild.id}`") or \
                            message.content.startswith(f"Editing owner for `{guild.id}`") or \
                            message.content.startswith(f"Appealing for `{guild.id}`") or \
                            message.content.startswith(f"Initializing report on `{guild.id}`") \
                            and message.author.id == bot.user.id:
                        ongoing_report.append(message.jump_url)
            except Exception:
                pass
        if ongoing_report:
            await interaction.followup.send(
                f"There already exists an ongoing report on `{guild.id}`: {ongoing_report[0]}")
            return
        ongoing_vote = []
        vote_channel = bot.get_channel(VOTE_CHANNEL)
        active_threads = vote_channel.threads
        for thread in active_threads:
            if thread.name == f"server-{guild.id}":
                ongoing_vote.append(thread.jump_url)
        if ongoing_vote:
            await interaction.followup.send(
                f"There already exists an ongoing vote on `{guild.id}`: {ongoing_vote[0]}")
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
                tags_strings.append(case[1])
            for tags_string in tags_strings:
                tags_list = tags_string.split(", ")
                for tag in tags_list:
                    all_tags_list.append(tag)
            all_tags_list = sort_server_tags(all_tags_list)
            title = all_tags_list[0]
            #
            case_title = "TBC"
            add_case_list = [
                # [0] date added
                "",
                # [1] tags
                "",
                # [2] reason
                "",
                # [3] contributor
                "",
                # [4] tri staff
                "",
                # [5] accepted by
                "",
                # [6] image_links
                [],
            ]
            add_case_list[
                0] = f"<t:{round(int(discord.utils.utcnow().timestamp()))}:D> (<t:{round(int(discord.utils.utcnow().timestamp()))}:R>)"
            add_case_list[4] = f"<@{interaction.user.id}>"
            channel_id = msg.channel.id
            message_id = msg.id
            r_profile = format_server_r_profile(guild, r_profile_list, title)
            add_case = format_server_add_case(add_case_list, case_title)
            embeds = [r_profile, add_case]
            await msg.edit(embeds=embeds, view=AddReportOwnerView(guild, requested_by, channel_id, message_id,
                                                                 r_profile_list, add_case_list, title, case_title))
        elif any(role.id == ticket_ping for role in interaction.user.roles):
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
        ongoing_report = []
        tickets_channel = bot.get_channel(TICKETS_CHANNEL)
        active_threads = tickets_channel.threads
        for thread in active_threads:
            try:
                async for message in thread.history():
                    if message.content.startswith(f"Adding report on `{guild.id}`") or \
                            message.content.startswith(f"Editing owner for `{guild.id}`") or \
                            message.content.startswith(f"Appealing for `{guild.id}`") or \
                            message.content.startswith(f"Initializing report on `{guild.id}`") \
                            and message.author.id == bot.user.id:
                        ongoing_report.append(message.jump_url)
            except Exception:
                pass
        if ongoing_report:
            await interaction.followup.send(
                f"There already exists an ongoing report on `{guild.id}`: {ongoing_report[0]}")
            return
        ongoing_vote = []
        vote_channel = bot.get_channel(VOTE_CHANNEL)
        active_threads = vote_channel.threads
        for thread in active_threads:
            if thread.name == f"server-{guild.id}":
                ongoing_vote.append(thread.jump_url)
        if ongoing_vote:
            await interaction.followup.send(
                f"There already exists an ongoing vote on `{guild.id}`: {ongoing_vote[0]}")
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
                tags_strings.append(case[1])
            for tags_string in tags_strings:
                tags_list = tags_string.split(", ")
                for tag in tags_list:
                    all_tags_list.append(tag)
            all_tags_list = sort_server_tags(all_tags_list)
            title = all_tags_list[0]
            current_index = current_case - 1
            add_case_list = server_profile[str(current_case)]
            case_tags = cases[current_index][1].split(", ")
            case_title = case_tags[0]
            channel_id = msg.channel.id
            message_id = msg.id
            r_profile = format_server_r_profile(guild, r_profile_list, title)
            reason = ""
            reason_embed = discord.Embed(title="Reason", colour=0x1dcca9, description=reason)
            add_case = format_server_add_case(add_case_list, case_title)
            embeds = [r_profile, add_case, reason_embed]
            await msg.edit(embeds=embeds, view=ServerAppealView(guild, requested_by, channel_id, message_id,
                                                          r_profile_list, add_case_list, title, case_title, reason))
        elif any(role.id == ticket_ping for role in interaction.user.roles):
            await interaction.followup.send(
                "This was requested by " + f"{requested_by.mention}, you cannot interact with this component.",
                ephemeral=True)
        else:
            await interaction.followup.send("You do not have permission to use this button.", ephemeral=True)


# edit owner only
class EditOwnerOnlyView(discord.ui.View):
    def __init__(self, guild, requested_by, channel_id, message_id, r_profile_list, title, reason):
        super().__init__(timeout=None)
        self.guild = guild
        self.requested_by = requested_by
        self.channel_id = channel_id
        self.message_id = message_id
        self.r_profile_list = r_profile_list
        self.title = title
        self.reason = reason

    @discord.ui.button(label="Edit Owner", style=discord.ButtonStyle.green, custom_id="editowneronly:editowner")
    async def edit_owner_button(self, interaction, button):
        #
        guild = self.guild
        requested_by = self.requested_by
        channel_id = self.channel_id
        message_id = self.message_id
        r_profile_list = self.r_profile_list
        title = self.title
        reason = self.reason
        #
        if requested_by == interaction.user:
            await interaction.response.send_modal(
                EditOwnerOnlyModal(guild, requested_by, channel_id, message_id, r_profile_list, title, reason))

    @discord.ui.button(label="Reason", style=discord.ButtonStyle.primary, custom_id="editowneronly:reason")
    async def reason_button(self, interaction, button):
        #
        guild = self.guild
        requested_by = self.requested_by
        channel_id = self.channel_id
        message_id = self.message_id
        r_profile_list = self.r_profile_list
        title = self.title
        reason = self.reason
        #
        if requested_by == interaction.user:
            await interaction.response.send_modal(
                OwnerReasonModal(guild, requested_by, channel_id, message_id, r_profile_list, title, reason))

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.grey, custom_id="editowneronly:cancel")
    async def cancel_button(self, interaction, button):
        await interaction.response.defer()
        #
        guild = self.guild
        requested_by = self.requested_by
        channel_id = self.channel_id
        message_id = self.message_id
        #
        message = await bot.get_channel(channel_id).fetch_message(message_id)
        if requested_by == interaction.user or any(role.id == sr_role for role in interaction.user.roles):
            await message.edit(content=f"**Cancelled by {interaction.user.mention}.**", view=None)

    @discord.ui.button(label="Accept", style=discord.ButtonStyle.grey, custom_id="editowneronly:accept")
    async def accept_button(self, interaction, button):
        await interaction.response.defer()
        #
        guild = self.guild
        requested_by = self.requested_by
        channel_id = self.channel_id
        message_id = self.message_id
        r_profile_list = self.r_profile_list
        title = self.title
        reason = self.reason
        #
        message = await bot.get_channel(channel_id).fetch_message(message_id)
        if any(role.id == sr_role for role in interaction.user.roles) and interaction.user != requested_by:
            accepted_by = interaction.user
            r_profile = format_server_r_profile(guild, r_profile_list, title)
            #
            vote_channel = bot.get_channel(VOTE_CHANNEL)
            add_case_list = []
            case_title = ""
            agree_users = []
            disagree_users = []
            new_report_message = await vote_channel.send(content=f"Owner edited for `{guild.id}`")
            new_report_thread = await new_report_message.create_thread(name=f"server-{guild.id}")
            await new_report_thread.send(f"<@&{ticket_ping}>")
            await new_report_thread.send(
                content=f"Report accepted by {accepted_by.mention}.\nLink to thread: <#{channel_id}>\n\nAgree: 0\nDisagree: 0",
                embed=r_profile,
                view=ServerVoteView(guild, requested_by, channel_id, message_id, r_profile_list, add_case_list, title,
                              case_title, accepted_by, agree_users, disagree_users, reason))
            reason_embed = discord.Embed(title="Reason", description=reason)
            await new_report_thread.send(content=f"Reason for change(s)", embed=reason_embed)
            embeds = [r_profile, reason_embed]
            await message.edit(content="Report has been submitted for voting.", embeds=embeds, view=None)
        else:
            await interaction.followup.send("You do not have permission to accept the report for voting.",
                                            ephemeral=True)
class EditOwnerOnlyModal(discord.ui.Modal, title="Edit Owner"):
    owner = discord.ui.TextInput(label="Edit Owner", placeholder="Input Server Owner ID here.", required=True,
                                 style=discord.TextStyle.short)

    def __init__(self, guild, requested_by, channel_id, message_id, r_profile_list, title, reason):
        super().__init__(timeout=None)
        self.guild = guild
        self.requested_by = requested_by
        self.channel_id = channel_id
        self.message_id = message_id
        self.r_profile_list = r_profile_list
        self.title = title
        self.reason = reason

    async def on_submit(self, interaction):
        await interaction.response.defer()
        #
        guild = self.guild
        requested_by = self.requested_by
        channel_id = self.channel_id
        message_id = self.message_id
        r_profile_list = self.r_profile_list
        title = self.title
        reason = self.reason
        #
        message = await bot.get_channel(channel_id).fetch_message(message_id)
        try:
            valid_owner = await bot.fetch_user(int(self.owner.value))
        except Exception:
            pass
        else:
            if valid_owner:
                r_profile_list[0] = f"{valid_owner.mention}"
        #
        self.r_profile_list = r_profile_list
        #
        r_profile = format_server_r_profile(guild, r_profile_list, title)
        reason_embed = discord.Embed(title="Reason", description=reason)
        embeds = [r_profile, reason_embed]
        await message.edit(embeds=embeds,
                           view=EditOwnerOnlyView(guild, requested_by, channel_id, message_id, r_profile_list, title,
                                                 reason))
class OwnerReasonModal(discord.ui.Modal, title="Reason"):
    reason_input = discord.ui.TextInput(label="Reason", placeholder="Please explain the change(s) you have made.",
                                        required=True, style=discord.TextStyle.long)

    def __init__(self, guild, requested_by, channel_id, message_id, r_profile_list, title, reason):
        super().__init__(timeout=None)
        self.guild = guild
        self.requested_by = requested_by
        self.channel_id = channel_id
        self.message_id = message_id
        self.r_profile_list = r_profile_list
        self.title = title
        self.reason = reason

    async def on_submit(self, interaction):
        await interaction.response.defer()
        #
        guild = self.guild
        requested_by = self.requested_by
        channel_id = self.channel_id
        message_id = self.message_id
        r_profile_list = self.r_profile_list
        title = self.title
        reason = self.reason
        #
        message = await bot.get_channel(channel_id).fetch_message(message_id)
        reason = str(self.reason_input.value)
        r_profile = format_server_r_profile(guild, r_profile_list, title)
        reason_embed = discord.Embed(title="Reason", description=reason)
        embeds = [r_profile, reason_embed]
        await message.edit(embeds=embeds,
                           view=EditOwnerOnlyView(guild, requested_by, channel_id, message_id, r_profile_list, title,
                                                 reason))


# server appeal
class ServerAppealView(discord.ui.View):
    def __init__(self, guild, requested_by, channel_id, message_id, r_profile_list, add_case_list, title, case_title,
                 reason):
        super().__init__(timeout=None)
        self.guild = guild
        self.requested_by = requested_by
        self.channel_id = channel_id
        self.message_id = message_id
        self.r_profile_list = r_profile_list
        self.add_case_list = add_case_list
        self.title = title
        self.case_title = case_title
        self.reason = reason

    @discord.ui.button(label="Edit Owner", style=discord.ButtonStyle.green, custom_id="serverappeal:editowner")
    async def edit_owner_button(self, interaction, button):
        #
        guild = self.guild
        requested_by = self.requested_by
        channel_id = self.channel_id
        message_id = self.message_id
        r_profile_list = self.r_profile_list
        add_case_list = self.add_case_list
        title = self.title
        case_title = self.case_title
        reason = self.reason
        #
        if requested_by == interaction.user:
            await interaction.response.send_modal(
                EditOwnerAppealModal(guild, requested_by, channel_id, message_id, r_profile_list, add_case_list, title,
                                   case_title, reason))


    @discord.ui.button(label="Reason", style=discord.ButtonStyle.primary, custom_id="serverappeal:reason")
    async def reason_button(self, interaction, button):
        #
        guild = self.guild
        requested_by = self.requested_by
        channel_id = self.channel_id
        message_id = self.message_id
        r_profile_list = self.r_profile_list
        add_case_list = self.add_case_list
        title = self.title
        case_title = self.case_title
        reason = self.reason
        #
        if requested_by == interaction.user:
            await interaction.response.send_modal(
                ServerAppealReasonModal(guild, requested_by, channel_id, message_id, r_profile_list, add_case_list, title,
                                  case_title, reason))

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.grey, custom_id="serverappeal:cancel")
    async def cancel_button(self, interaction, button):
        await interaction.response.defer()
        #
        guild = self.guild
        requested_by = self.requested_by
        channel_id = self.channel_id
        message_id = self.message_id
        #
        message = await bot.get_channel(channel_id).fetch_message(message_id)
        if requested_by == interaction.user or any(role.id == sr_role for role in interaction.user.roles):
            await message.edit(content=f"**Cancelled by {interaction.user.mention}.**", view=None)

    @discord.ui.button(label="Accept", style=discord.ButtonStyle.grey, custom_id="serverappeal:accept")
    async def accept_button(self, interaction, button):
        await interaction.response.defer()
        #
        guild = self.guild
        requested_by = self.requested_by
        channel_id = self.channel_id
        message_id = self.message_id
        r_profile_list = self.r_profile_list
        add_case_list = self.add_case_list
        title = self.title
        case_title = self.case_title
        reason = self.reason
        #
        message = await bot.get_channel(channel_id).fetch_message(message_id)
        if any(role.id == sr_role for role in interaction.user.roles) and interaction.user != requested_by:
            accepted_by = interaction.user
            r_profile = format_server_r_profile(guild, r_profile_list, title)
            add_case = format_server_add_case(add_case_list, case_title)
            reason_embed = discord.Embed(title="Reason", colour=0x1DCCA9, description=reason)
            embeds = [r_profile, add_case, reason_embed]
            #
            vote_channel = bot.get_channel(VOTE_CHANNEL)
            agree_users = []
            disagree_users = []
            image_embeds = image_links_to_embeds(add_case_list[6])
            add_case_list = [add_case_list]
            new_report_message = await vote_channel.send(content=f"Appeal on `{guild.id}`")
            new_report_thread = await new_report_message.create_thread(name=f"server-{guild.id}")
            await new_report_thread.send(f"<@&{ticket_ping}>")
            await new_report_thread.send(
                content=f"Appeal accepted by {accepted_by.mention}.\nLink to thread: <#{channel_id}>\n\nAgree: 0\nDisagree: 0",
                embeds=embeds,
                view=ServerVoteView(guild, requested_by, channel_id, message_id, r_profile_list, add_case_list, title,
                              case_title, accepted_by, agree_users, disagree_users, reason))
            await new_report_thread.send(content=f"Proofs for `{guild.id}`", embeds=image_embeds)
            await message.edit(content="Appeal has been submitted for voting.", embeds=embeds, view=None)
        else:
            await interaction.followup.send("You do not have permission to accept the report for voting.",
                                            ephemeral=True)
class EditOwnerAppealModal(discord.ui.Modal, title="Edit Owner"):
    owner = discord.ui.TextInput(label="Edit Owner", placeholder="Input Server Owner ID here.",
                                required=True, style=discord.TextStyle.short)

    def __init__(self, guild, requested_by, channel_id, message_id, r_profile_list, add_case_list, title, case_title,
                 reason):
        super().__init__(timeout=None)
        self.guild = guild
        self.requested_by = requested_by
        self.channel_id = channel_id
        self.message_id = message_id
        self.r_profile_list = r_profile_list
        self.add_case_list = add_case_list
        self.title = title
        self.case_title = case_title
        self.reason = reason

    async def on_submit(self, interaction):
        await interaction.response.defer()
        #
        guild = self.guild
        requested_by = self.requested_by
        channel_id = self.channel_id
        message_id = self.message_id
        r_profile_list = self.r_profile_list
        add_case_list = self.add_case_list
        title = self.title
        case_title = self.case_title
        reason = self.reason
        #
        message = await bot.get_channel(channel_id).fetch_message(message_id)
        try:
            valid_owner = await bot.fetch_user(int(self.owner.value))
        except Exception:
            pass
        else:
            if valid_owner:
                r_profile_list[0] = f"{valid_owner.mention}"
        #
        self.r_profile_list = r_profile_list
        #
        r_profile = format_server_r_profile(guild, r_profile_list, title)
        reason_embed = discord.Embed(title="Reason", colour=0x1DCCA9, description=reason)
        add_case = format_server_add_case(add_case_list, case_title)
        embeds = [r_profile, add_case, reason_embed]
        await message.edit(embeds=embeds,
                           view=ServerAppealView(guild, requested_by, channel_id, message_id, r_profile_list, add_case_list,
                                           title, case_title, reason))
class ServerAppealReasonModal(discord.ui.Modal, title="Reason"):
    reason_input = discord.ui.TextInput(label="Reason", placeholder="Please explain the appeal you have made.",
                                        required=True, style=discord.TextStyle.long)

    def __init__(self, guild, requested_by, channel_id, message_id, r_profile_list, add_case_list, title, case_title,
                 reason):
        super().__init__(timeout=None)
        self.guild = guild
        self.requested_by = requested_by
        self.channel_id = channel_id
        self.message_id = message_id
        self.r_profile_list = r_profile_list
        self.add_case_list = add_case_list
        self.title = title
        self.case_title = case_title
        self.reason = reason

    async def on_submit(self, interaction):
        await interaction.response.defer()
        #
        guild = self.guild
        requested_by = self.requested_by
        channel_id = self.channel_id
        message_id = self.message_id
        r_profile_list = self.r_profile_list
        add_case_list = self.add_case_list
        title = self.title
        case_title = self.case_title
        reason = self.reason
        #
        message = await bot.get_channel(channel_id).fetch_message(message_id)
        reason = str(self.reason_input.value)
        r_profile = format_server_r_profile(guild, r_profile_list, title)
        reason_embed = discord.Embed(title="Reason", colour=0x1DCCA9, description=reason)
        add_case = format_server_add_case(add_case_list, case_title)
        embeds = [r_profile, add_case, reason_embed]
        await message.edit(embeds=embeds,
                           view=ServerAppealView(guild, requested_by, channel_id, message_id, r_profile_list, add_case_list,
                                           title, case_title, reason))


# server add report
class AddReportOwnerView(discord.ui.View):
    def __init__(self, guild, requested_by, channel_id, message_id, r_profile_list, add_case_list, title, case_title):
        super().__init__(timeout=None)
        self.guild = guild
        self.requested_by = requested_by
        self.channel_id = channel_id
        self.message_id = message_id
        self.r_profile_list = r_profile_list
        self.add_case_list = add_case_list
        self.title = title
        self.case_title = case_title

    @discord.ui.button(emoji="<:rightarrow:1458096774521553038>", style=discord.ButtonStyle.grey, custom_id="addreportowner:next")
    async def next_button(self, interaction, button):
        await interaction.response.defer()
        #
        guild = self.guild
        requested_by = self.requested_by
        channel_id = self.channel_id
        message_id = self.message_id
        r_profile_list = self.r_profile_list
        add_case_list = self.add_case_list
        title = self.title
        case_title = self.case_title
        #
        message = await bot.get_channel(channel_id).fetch_message(message_id)
        if requested_by == interaction.user or any(role.id == sr_role for role in interaction.user.roles):
            r_profile = format_server_r_profile(guild, r_profile_list, title)
            add_case = format_server_add_case(add_case_list, case_title)
            embeds = [r_profile, add_case]
            await message.edit(embeds=embeds,
                               view=AddReportServerTagsView(guild, requested_by, channel_id, message_id, r_profile_list,
                                                            add_case_list, title, case_title))

    @discord.ui.button(label="Edit Owner", style=discord.ButtonStyle.green, custom_id="addreportowner:editowner")
    async def edit_owner_button(self, interaction, button):
        #
        guild = self.guild
        requested_by = self.requested_by
        channel_id = self.channel_id
        message_id = self.message_id
        r_profile_list = self.r_profile_list
        add_case_list = self.add_case_list
        title = self.title
        case_title = self.case_title
        #
        if requested_by == interaction.user:
            await interaction.response.send_modal(
                EditOwnerModal(guild, requested_by, channel_id, message_id, r_profile_list, add_case_list, title,
                             case_title))

class EditOwnerModal(discord.ui.Modal, title="Edit Owner"):
    owner = discord.ui.TextInput(label="Edit Owner", placeholder="Input Server Owner ID here.",
                                required=True, style=discord.TextStyle.short)

    def __init__(self, guild, requested_by, channel_id, message_id, r_profile_list, add_case_list, title, case_title):
        super().__init__(timeout=None)
        self.guild = guild
        self.requested_by = requested_by
        self.channel_id = channel_id
        self.message_id = message_id
        self.r_profile_list = r_profile_list
        self.add_case_list = add_case_list
        self.title = title
        self.case_title = case_title

    async def on_submit(self, interaction):
        await interaction.response.defer()
        #
        guild = self.guild
        requested_by = self.requested_by
        channel_id = self.channel_id
        message_id = self.message_id
        r_profile_list = self.r_profile_list
        add_case_list = self.add_case_list
        title = self.title
        case_title = self.case_title
        #
        message = await bot.get_channel(channel_id).fetch_message(message_id)
        try:
            valid_owner = await bot.fetch_user(int(self.owner.value))
        except Exception:
            pass
        else:
            if valid_owner:
                r_profile_list[0] = f"{valid_owner.mention}"
        #
        self.r_profile_list = r_profile_list
        #
        r_profile = format_server_r_profile(guild, r_profile_list, title)
        add_case = format_server_add_case(add_case_list, case_title)
        embeds = [r_profile, add_case]
        await message.edit(embeds=embeds,
                           view=AddReportOwnerView(guild, requested_by, channel_id, message_id, r_profile_list,
                                                   add_case_list, title, case_title))

class AddReportServerTagsView(discord.ui.View):
    def __init__(self, guild, requested_by, channel_id, message_id, r_profile_list, add_case_list, title, case_title):
        super().__init__(timeout=None)
        self.guild = guild
        self.requested_by = requested_by
        self.channel_id = channel_id
        self.message_id = message_id
        self.r_profile_list = r_profile_list
        self.add_case_list = add_case_list
        self.title = title
        self.case_title = case_title

    @discord.ui.button(emoji="<:leftarrow:1458096658062770176>", style=discord.ButtonStyle.grey, custom_id="addreportservertags:prev")
    async def prev_button(self, interaction, button):
        await interaction.response.defer()
        #
        guild = self.guild
        requested_by = self.requested_by
        channel_id = self.channel_id
        message_id = self.message_id
        r_profile_list = self.r_profile_list
        add_case_list = self.add_case_list
        title = self.title
        case_title = self.case_title
        #
        message = await bot.get_channel(channel_id).fetch_message(message_id)
        if requested_by == interaction.user or any(role.id == sr_role for role in interaction.user.roles):
            r_profile = format_server_r_profile(guild, r_profile_list, title)
            add_case = format_server_add_case(add_case_list, case_title)
            embeds = [r_profile, add_case]
            await message.edit(embeds=embeds,
                               view=AddReportOwnerView(guild, requested_by, channel_id, message_id, r_profile_list, add_case_list,
                                             title, case_title))

    @discord.ui.button(emoji="<:rightarrow:1458096774521553038>", style=discord.ButtonStyle.grey, custom_id="addreportservertags:next")
    async def next_button(self, interaction, button):
        await interaction.response.defer()
        #
        guild = self.guild
        requested_by = self.requested_by
        channel_id = self.channel_id
        message_id = self.message_id
        r_profile_list = self.r_profile_list
        add_case_list = self.add_case_list
        title = self.title
        case_title = self.case_title
        #
        message = await bot.get_channel(channel_id).fetch_message(message_id)
        if requested_by == interaction.user or any(role.id == sr_role for role in interaction.user.roles):
            r_profile = format_server_r_profile(guild, r_profile_list, title)
            add_case = format_server_add_case(add_case_list, case_title)
            embeds = [r_profile, add_case]
            await message.edit(embeds=embeds,
                               view=AddReportServerReasonView(guild, requested_by, channel_id, message_id,
                                                              r_profile_list, add_case_list, title, case_title))

    @discord.ui.select(options=server_tags_options, placeholder="Select Tag(s)...", custom_id="addreportservertags:select",
                       max_values=len(server_tags_options))
    async def select_callback(self, interaction, select):
        await interaction.response.defer()
        #
        guild = self.guild
        requested_by = self.requested_by
        channel_id = self.channel_id
        message_id = self.message_id
        r_profile_list = self.r_profile_list
        add_case_list = self.add_case_list
        title = self.title
        case_title = self.case_title
        #
        message = await bot.get_channel(channel_id).fetch_message(message_id)
        if requested_by == interaction.user:
            sorted_tags = sort_server_tags(self.select_callback.values)
            case_title = sorted_tags[0]
            tags = selected_string(sorted_tags)
            add_case_list[1] = tags
            #
            server_query = {"_id": str(guild.id)}
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
            self.r_profile_list = r_profile_list
            self.add_case_list = add_case_list
            self.title = title
            self.case_title = case_title
            #
            r_profile = format_server_r_profile(guild, r_profile_list, title)
            add_case = format_server_add_case(add_case_list, case_title)
            embeds = [r_profile, add_case]
            await message.edit(embeds=embeds)

class AddReportServerReasonView(discord.ui.View):
    def __init__(self, guild, requested_by, channel_id, message_id, r_profile_list, add_case_list, title, case_title):
        super().__init__(timeout=None)
        self.guild = guild
        self.requested_by = requested_by
        self.channel_id = channel_id
        self.message_id = message_id
        self.r_profile_list = r_profile_list
        self.add_case_list = add_case_list
        self.title = title
        self.case_title = case_title

    @discord.ui.button(emoji="<:leftarrow:1458096658062770176>", style=discord.ButtonStyle.grey, custom_id="addreportserverreason:prev")
    async def prev_button(self, interaction, button):
        await interaction.response.defer()
        #
        guild = self.guild
        requested_by = self.requested_by
        channel_id = self.channel_id
        message_id = self.message_id
        r_profile_list = self.r_profile_list
        add_case_list = self.add_case_list
        title = self.title
        case_title = self.case_title
        #
        message = await bot.get_channel(channel_id).fetch_message(message_id)
        if requested_by == interaction.user or any(role.id == sr_role for role in interaction.user.roles):
            r_profile = format_server_r_profile(guild, r_profile_list, title)
            add_case = format_server_add_case(add_case_list, case_title)
            embeds = [r_profile, add_case]
            await message.edit(embeds=embeds,
                               view=AddReportServerTagsView(guild, requested_by, channel_id, message_id, r_profile_list, add_case_list,
                                              title, case_title))

    @discord.ui.button(emoji="<:rightarrow:1458096774521553038>", style=discord.ButtonStyle.grey, custom_id="addreportserverreason:next")
    async def next_button(self, interaction, button):
        await interaction.response.defer()
        #
        guild = self.guild
        requested_by = self.requested_by
        channel_id = self.channel_id
        message_id = self.message_id
        r_profile_list = self.r_profile_list
        add_case_list = self.add_case_list
        title = self.title
        case_title = self.case_title
        #
        message = await bot.get_channel(channel_id).fetch_message(message_id)
        if requested_by == interaction.user or any(role.id == sr_role for role in interaction.user.roles):
            r_profile = format_server_r_profile(guild, r_profile_list, title)
            add_case = format_server_add_case(add_case_list, case_title)
            embeds = [r_profile, add_case]
            await message.edit(embeds=embeds,
                               view=AddReportServerContributorView(guild, requested_by, channel_id, message_id, r_profile_list,
                                                    add_case_list,
                                                    title, case_title))

    @discord.ui.button(label="Reason", style=discord.ButtonStyle.green, custom_id="addreportserverreason:reason")
    async def reason_button(self, interaction, button):
        #
        guild = self.guild
        requested_by = self.requested_by
        channel_id = self.channel_id
        message_id = self.message_id
        r_profile_list = self.r_profile_list
        add_case_list = self.add_case_list
        title = self.title
        case_title = self.case_title
        #
        if requested_by == interaction.user:
            await interaction.response.send_modal(
                AddReportServerReasonModal(guild, requested_by, channel_id, message_id, r_profile_list, add_case_list, title,
                            case_title))
class AddReportServerReasonModal(discord.ui.Modal, title="Reason"):
    reason = discord.ui.TextInput(label="Reason", placeholder="Input reason here.", required=True,
                                  style=discord.TextStyle.short)

    def __init__(self, guild, requested_by, channel_id, message_id, r_profile_list, add_case_list, title, case_title):
        super().__init__(timeout=None)
        self.guild = guild
        self.requested_by = requested_by
        self.channel_id = channel_id
        self.message_id = message_id
        self.r_profile_list = r_profile_list
        self.add_case_list = add_case_list
        self.title = title
        self.case_title = case_title

    async def on_submit(self, interaction):
        await interaction.response.defer()
        #
        guild = self.guild
        requested_by = self.requested_by
        channel_id = self.channel_id
        message_id = self.message_id
        r_profile_list = self.r_profile_list
        add_case_list = self.add_case_list
        title = self.title
        case_title = self.case_title
        #
        message = await bot.get_channel(channel_id).fetch_message(message_id)
        add_case_list[2] = str(self.reason.value)
        #
        self.add_case_list = add_case_list
        #
        r_profile = format_server_r_profile(guild, r_profile_list, title)
        add_case = format_server_add_case(add_case_list, case_title)
        embeds = [r_profile, add_case]
        await message.edit(embeds=embeds,
                           view=AddReportServerReasonView(guild, requested_by, channel_id, message_id, r_profile_list, add_case_list,
                                           title, case_title))

class AddReportServerContributorView(discord.ui.View):
    def __init__(self, guild, requested_by, channel_id, message_id, r_profile_list, add_case_list, title, case_title):
        super().__init__(timeout=None)
        self.guild = guild
        self.requested_by = requested_by
        self.channel_id = channel_id
        self.message_id = message_id
        self.r_profile_list = r_profile_list
        self.add_case_list = add_case_list
        self.title = title
        self.case_title = case_title

    @discord.ui.button(emoji="<:leftarrow:1458096658062770176>", style=discord.ButtonStyle.grey,
                       custom_id="addreportservercontributor:prev")
    async def prev_button(self, interaction, button):
        await interaction.response.defer()
        #
        guild = self.guild
        requested_by = self.requested_by
        channel_id = self.channel_id
        message_id = self.message_id
        r_profile_list = self.r_profile_list
        add_case_list = self.add_case_list
        title = self.title
        case_title = self.case_title
        #
        message = await bot.get_channel(channel_id).fetch_message(message_id)
        if requested_by == interaction.user or any(role.id == sr_role for role in interaction.user.roles):
            r_profile = format_server_r_profile(guild, r_profile_list, title)
            add_case = format_server_add_case(add_case_list, case_title)
            embeds = [r_profile, add_case]
            await message.edit(embeds=embeds,
                               view=AddReportServerReasonView(guild, requested_by, channel_id, message_id, r_profile_list,
                                               add_case_list,
                                               title, case_title))

    @discord.ui.button(emoji="<:rightarrow:1458096774521553038>", style=discord.ButtonStyle.grey,
                       custom_id="addreportservercontributor:next")
    async def next_button(self, interaction, button):
        await interaction.response.defer()
        #
        guild = self.guild
        requested_by = self.requested_by
        channel_id = self.channel_id
        message_id = self.message_id
        r_profile_list = self.r_profile_list
        add_case_list = self.add_case_list
        title = self.title
        case_title = self.case_title
        #
        message = await bot.get_channel(channel_id).fetch_message(message_id)
        if requested_by == interaction.user or any(role.id == sr_role for role in interaction.user.roles):
            r_profile = format_server_r_profile(guild, r_profile_list, title)
            add_case = format_server_add_case(add_case_list, case_title)
            embeds = [r_profile, add_case]
            await message.edit(embeds=embeds,
                               view=AddReportServerProofsView(guild, requested_by, channel_id, message_id, r_profile_list,
                                               add_case_list,
                                               title, case_title))

    @discord.ui.button(label="Contributor", style=discord.ButtonStyle.green, custom_id="addreportservercontributor:input")
    async def contributor_button(self, interaction, button):
        #
        guild = self.guild
        requested_by = self.requested_by
        channel_id = self.channel_id
        message_id = self.message_id
        r_profile_list = self.r_profile_list
        add_case_list = self.add_case_list
        title = self.title
        case_title = self.case_title
        #
        if requested_by == interaction.user:
            await interaction.response.send_modal(
                AddReportServerContributorModal(guild, requested_by, channel_id, message_id, r_profile_list, add_case_list, title,
                                 case_title))
class AddReportServerContributorModal(discord.ui.Modal, title="Contributor"):
    contributor = discord.ui.TextInput(label="Contributor",
                                       placeholder="User ID / n if Anonymous.", required=True,
                                       style=discord.TextStyle.short)

    def __init__(self, guild, requested_by, channel_id, message_id, r_profile_list, add_case_list, title, case_title):
        super().__init__(timeout=None)
        self.guild = guild
        self.requested_by = requested_by
        self.channel_id = channel_id
        self.message_id = message_id
        self.r_profile_list = r_profile_list
        self.add_case_list = add_case_list
        self.title = title
        self.case_title = case_title

    async def on_submit(self, interaction):
        await interaction.response.defer()
        #
        guild = self.guild
        requested_by = self.requested_by
        channel_id = self.channel_id
        message_id = self.message_id
        r_profile_list = self.r_profile_list
        add_case_list = self.add_case_list
        title = self.title
        case_title = self.case_title
        #
        message = await bot.get_channel(channel_id).fetch_message(message_id)
        contributor_input = self.contributor.value
        if contributor_input.lower() == "n":
            add_case_list[3] = "Anonymous"
        else:
            try:
                contributor_id = await bot.fetch_user(int(contributor_input))
            except Exception:
                add_case_list[3] = ""
            else:
                add_case_list[3] = f"<@{contributor_id.id}>"
        #
        self.add_case_list = add_case_list
        #
        r_profile = format_server_r_profile(guild, r_profile_list, title)
        add_case = format_server_add_case(add_case_list, case_title)
        embeds = [r_profile, add_case]
        await message.edit(embeds=embeds,
                           view=AddReportServerContributorView(guild, requested_by, channel_id, message_id, r_profile_list,
                                                add_case_list, title, case_title))

class AddReportServerProofsView(discord.ui.View):
    def __init__(self, guild, requested_by, channel_id, message_id, r_profile_list, add_case_list, title, case_title):
        super().__init__(timeout=None)
        self.guild = guild
        self.requested_by = requested_by
        self.channel_id = channel_id
        self.message_id = message_id
        self.r_profile_list = r_profile_list
        self.add_case_list = add_case_list
        self.title = title
        self.case_title = case_title

    @discord.ui.button(emoji="<:leftarrow:1458096658062770176>", style=discord.ButtonStyle.grey, custom_id="addreportserverproofs:prev")
    async def prev_button(self, interaction, button):
        await interaction.response.defer()
        #
        guild = self.guild
        requested_by = self.requested_by
        channel_id = self.channel_id
        message_id = self.message_id
        r_profile_list = self.r_profile_list
        add_case_list = self.add_case_list
        title = self.title
        case_title = self.case_title
        #
        message = await bot.get_channel(channel_id).fetch_message(message_id)
        if requested_by == interaction.user or any(role.id == sr_role for role in interaction.user.roles):
            r_profile = format_server_r_profile(guild, r_profile_list, title)
            add_case = format_server_add_case(add_case_list, case_title)
            embeds = [r_profile, add_case]
            await message.edit(embeds=embeds,
                               view=ServerContributorView(guild, requested_by, channel_id, message_id, r_profile_list,
                                                    add_case_list, title, case_title))

    @discord.ui.button(label="Add Proofs", style=discord.ButtonStyle.green, custom_id="addreportserverproofs:input")
    async def proofs_button(self, interaction, button):
        #
        guild = self.guild
        requested_by = self.requested_by
        channel_id = self.channel_id
        message_id = self.message_id
        r_profile_list = self.r_profile_list
        add_case_list = self.add_case_list
        title = self.title
        case_title = self.case_title
        #
        message = await bot.get_channel(channel_id).fetch_message(message_id)
        if requested_by == interaction.user:
            image_links = []
            add_case_list[6] = []
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
                                        add_case_list[6].append(new_image_url)
                        except Exception:
                            await msg.channel.send(f"An error occurred with file {attachment.filename}")
            #
            self.add_case_list = add_case_list
            #
            image_embeds = image_links_to_embeds(image_links)
            await interaction.followup.send(f"Images received from {interaction.user.mention}.",
                                            embeds=image_embeds)

    @discord.ui.button(label="Show Proofs", style=discord.ButtonStyle.grey, custom_id="addreportserverproofs:showproofs")
    async def show_proofs_button(self, interaction, button):
        await interaction.response.defer()
        #
        guild = self.guild
        requested_by = self.requested_by
        channel_id = self.channel_id
        message_id = self.message_id
        r_profile_list = self.r_profile_list
        add_case_list = self.add_case_list
        title = self.title
        case_title = self.case_title
        #
        if requested_by == interaction.user or any(role.id == sr_role for role in interaction.user.roles):
            image_embeds = image_links_to_embeds(add_case_list[6])
            await interaction.followup.send(f"Proofs for `{guild.id}`",
                                            embeds=image_embeds, ephemeral=True)

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.grey, custom_id="addreportserverproofs:cancel")
    async def cancel_button(self, interaction, button):
        await interaction.response.defer()
        #
        guild = self.guild
        requested_by = self.requested_by
        channel_id = self.channel_id
        message_id = self.message_id
        #
        message = await bot.get_channel(channel_id).fetch_message(message_id)
        if requested_by == interaction.user or any(role.id == sr_role for role in interaction.user.roles):
            await message.edit(content=f"**Cancelled by {interaction.user.mention}.**", view=None)

    @discord.ui.button(label="Accept", style=discord.ButtonStyle.grey, custom_id="addreportserverproofs:accept")
    async def accept_button(self, interaction, button):
        await interaction.response.defer()
        #
        guild = self.guild
        requested_by = self.requested_by
        channel_id = self.channel_id
        message_id = self.message_id
        r_profile_list = self.r_profile_list
        add_case_list = self.add_case_list
        title = self.title
        case_title = self.case_title
        #
        message = await bot.get_channel(channel_id).fetch_message(message_id)
        if any(role.id == sr_role for role in interaction.user.roles) and interaction.user != requested_by:
            accepted_by = interaction.user
            add_case_list[5] = f"<@{interaction.user.id}>"
            #
            self.add_case_list = add_case_list
            #
            r_profile = format_server_r_profile(guild, r_profile_list, title)
            add_case = format_server_add_case(add_case_list, case_title)
            embeds = [r_profile, add_case]
            #
            vote_channel = bot.get_channel(VOTE_CHANNEL)
            agree_users = []
            disagree_users = []
            all_images_to_show = add_case_list[6]
            image_embeds = image_links_to_embeds(all_images_to_show)
            new_report_message = await vote_channel.send(content=f"Report added on `{guild.id}`")
            new_report_thread = await new_report_message.create_thread(name=f"server-{guild.id}")
            await new_report_thread.send(f"<@&{ticket_ping}>")
            await new_report_thread.send(
                content=f"Report accepted by {accepted_by.mention}.\nLink to thread: <#{channel_id}>\n\nAgree: 0\nDisagree: 0",
                embeds=embeds,
                view=ServerVoteView(guild, requested_by, channel_id, message_id, r_profile_list, add_case_list, title,
                              case_title, accepted_by, agree_users, disagree_users))
            await new_report_thread.send(content=f"Proofs for `{guild.id}`", embeds=image_embeds)
            await message.edit(content="Report has been submitted for voting.", embeds=embeds, view=None)
        else:
            await interaction.followup.send("You do not have permission to accept the report for voting.",
                                            ephemeral=True)


# server voting
class ServerVoteView(discord.ui.View):
    def __init__(self, guild, requested_by, channel_id, message_id, r_profile_list, add_case_list, title, case_title,
                 accepted_by, agree_users, disagree_users, reason=None):
        super().__init__(timeout=None)
        self.guild = guild
        self.requested_by = requested_by
        self.channel_id = channel_id
        self.message_id = message_id
        self.r_profile_list = r_profile_list
        self.add_case_list = add_case_list
        self.title = title
        self.case_title = case_title
        self.accepted_by = accepted_by
        self.agree_users = agree_users
        self.disagree_users = disagree_users
        self.reason = reason

    @discord.ui.button(label="Agree", style=discord.ButtonStyle.green, custom_id="servervote:agree")
    async def agree_button(self, interaction, button):
        await interaction.response.defer()
        #
        guild = self.guild
        requested_by = self.requested_by
        channel_id = self.channel_id
        message_id = self.message_id
        r_profile_list = self.r_profile_list
        add_case_list = self.add_case_list
        title = self.title
        case_title = self.case_title
        accepted_by = self.accepted_by
        agree_users = self.agree_users
        disagree_users = self.disagree_users
        reason = self.reason
        #
        if interaction.user not in agree_users:
            if interaction.user not in disagree_users:
                agree_users.append(interaction.user)
                await interaction.followup.send("You have voted Agree.", ephemeral=True)
            elif interaction.user in disagree_users:
                disagree_users.remove(interaction.user)
                agree_users.append(interaction.user)
                await interaction.followup.send("You have changed your vote from Disagree to Agree.", ephemeral=True)
        elif interaction.user in agree_users:
            await interaction.followup.send("You have already voted Agree.", ephemeral=True)
        #
        self.agree_users = agree_users
        self.disagree_users = disagree_users
        #
        r_profile = format_server_r_profile(guild, r_profile_list, title)
        #
        if len(agree_users) >= 8:
            server_query = {"_id": str(guild.id)}
            server_profile = serverscol.find_one(server_query)
            if server_profile:  # if editing existing reported user
                cases = []
                no_of_cases = len(server_profile) - 2
                for i in range(1, no_of_cases + 1):
                    cases.append(server_profile[str(i)])
                query_filter = {"_id": str(guild.id)}
                update_operation = {'$set': {"r_profile_list": r_profile_list}}
                serverscol.update_one(query_filter, update_operation)
                if add_case_list == []:  # only owner edited
                    r_profile = format_server_r_profile(guild, r_profile_list, title)
                    server_reports_channel = bot.get_channel(SERVER_REPORTS_CHANNEL)
                    await server_reports_channel.send(
                        content=f"<@&{updated_server_report_ping}>\nServer Owner edited for `{guild.id}`",
                        embed=r_profile)
                    reason_embed = discord.Embed(title="Reason", description=reason)
                    await server_reports_channel.send(content=f"Reason for change(s)", embed=reason_embed)
                    embeds = [r_profile, reason_embed]
                    await interaction.edit_original_response(
                        content=f"**Report has been published.** Report accepted by {accepted_by.mention}.\nLink to thread: <#{channel_id}>\n\nAgree: {len(agree_users)}\nDisagree: {len(disagree_users)}",
                        embeds=embeds, view=None)
                    message = await bot.get_channel(channel_id).fetch_message(message_id)
                    await message.edit(
                        content=f"**Report has been published.** Report accepted by {accepted_by.mention}.")
                    await bot.get_channel(channel_id).send(
                        f"Report on `{guild.id}` has been published. {requested_by.mention} {accepted_by.mention}")

                elif len(add_case_list) == 1:  # [[add_case_list]] case to appeal
                    add_case_list = add_case_list[0]
                    appeal_case_number = next((k for k, v in server_profile.items() if v == add_case_list), None)
                    query_filter = {"_id": str(guild.id)}
                    update_operation = {"$unset": {appeal_case_number: ""}}
                    serverscol.update_one(query_filter, update_operation)
                    #
                    server_query = {"_id": str(guild.id)}
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
                            tags_strings.append(case[1])
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
                        query_filter = {"_id": str(guild.id)}
                        serverscol.replace_one(query_filter, server_profile)
                    #
                    r_profile = format_server_r_profile(guild, r_profile_list, title)
                    add_case = format_server_add_case(add_case_list, case_title)
                    reason_embed = discord.Embed(title="Reason", colour=0x1DCCA9, description=reason)
                    embeds = [r_profile, add_case]
                    #
                    server_reports_channel = bot.get_channel(SERVER_REPORTS_CHANNEL)
                    await server_reports_channel.send(content=f"<@&{appealed_server_report_ping}>\nAppeal on `{guild.id}`",
                                                      embeds=embeds)
                    await server_reports_channel.send(content=f"Reason for appeal", embed=reason_embed)
                    await interaction.edit_original_response(
                        content=f"**Appeal has been published.** Appeal accepted by {accepted_by.mention}.\nLink to thread: <#{channel_id}>\n\nAgree: {len(agree_users)}\nDisagree: {len(disagree_users)}",
                        embeds=embeds, view=None)
                    message = await bot.get_channel(channel_id).fetch_message(message_id)
                    await message.edit(
                        content=f"**Appeal has been published.** Appeal accepted by {accepted_by.mention}.")
                    await bot.get_channel(channel_id).send(
                        f"Appeal on `{guild.id}` has been published. {requested_by.mention} {accepted_by.mention}")

                else:  # new case exists
                    self.add_case_list = add_case_list
                    #
                    r_profile = format_server_r_profile(guild, r_profile_list, title)
                    add_case = format_server_add_case(add_case_list, case_title)
                    embeds = [r_profile, add_case]

                    query_filter = {"_id": str(guild.id)}
                    update_operation = {'$set': {"r_profile_list": r_profile_list}}
                    serverscol.update_one(query_filter, update_operation)
                    update_operation = {'$set': {str(no_of_cases + 1): add_case_list}}
                    serverscol.update_one(query_filter, update_operation)

                    server_reports_channel = bot.get_channel(SERVER_REPORTS_CHANNEL)
                    await server_reports_channel.send(content=f"<@&{updated_server_report_ping}>\nReport added on `{guild.id}`",
                                                      embeds=embeds)
                    await interaction.edit_original_response(
                        content=f"**Report has been published.** Report accepted by {accepted_by.mention}.\nLink to thread: <#{channel_id}>\n\nAgree: {len(agree_users)}\nDisagree: {len(disagree_users)}",
                        embeds=embeds, view=None)
                    message = await bot.get_channel(channel_id).fetch_message(message_id)
                    await message.edit(
                        content=f"**Report has been published.** Report accepted by {accepted_by.mention}.")
                    await bot.get_channel(channel_id).send(
                        f"Report on `{guild.id}` has been published. {requested_by.mention} {accepted_by.mention}")

            else:  # if new reported server
                #
                self.add_case_list = add_case_list
                #
                r_profile = format_server_r_profile(guild, r_profile_list, title)
                add_case = format_server_add_case(add_case_list, case_title)
                embeds = [r_profile, add_case]

                new_server = {"_id": str(guild.id), "r_profile_list": r_profile_list,
                              "1": add_case_list}
                serverscol.insert_one(new_server)

                server_reports_channel = bot.get_channel(SERVER_REPORTS_CHANNEL)
                await server_reports_channel.send(content=f"<@&{new_server_report_ping}>\nNew report on `{guild.id}`",
                                                  embeds=embeds)
                await interaction.edit_original_response(
                    content=f"**Report has been published.** Report accepted by {accepted_by.mention}.\nLink to thread: <#{channel_id}>\n\nAgree: {len(agree_users)}\nDisagree: {len(disagree_users)}",
                    embeds=embeds, view=None)
                message = await bot.get_channel(channel_id).fetch_message(message_id)
                await message.edit(
                    content=f"**Report has been published.** Report accepted by {accepted_by.mention}.")
                await bot.get_channel(channel_id).send(
                    f"Report on `{guild.id}` has been published. {requested_by.mention} {accepted_by.mention}")

            voters = agree_users + disagree_users
            for voter in voters:
                voter_query = {"_id": str(voter.id)}
                voter_profile = trusteduserscol.find_one(voter_query)
                if voter_profile:
                    voter_profile["votes"] = str(int(voter_profile["votes"]) + 1)
                    trusteduserscol.replace_one(voter_query, voter_profile)

            staff_query = {"_id": str(requested_by.id)}
            staff_profile = trusteduserscol.find_one(staff_query)
            staff_weekly_profile = staffweeklycol.find_one(staff_query)
            if staff_profile:
                staff_profile["reports"] = str(int(staff_profile["reports"]) + 1)
                trusteduserscol.replace_one(staff_query, staff_profile)
            if staff_weekly_profile:
                staff_weekly_profile["weekly_reports"] = str(int(staff_weekly_profile["weekly_reports"]) + 1)
                staffweeklycol.replace_one(staff_query, staff_weekly_profile)

            sr_query = {"_id": str(accepted_by.id)}
            sr_profile = trusteduserscol.find_one(sr_query)
            sr_weekly_profile = staffweeklycol.find_one(sr_query)
            if sr_profile:
                sr_profile["reviews"] = str(int(sr_profile["reviews"]) + 1)
                trusteduserscol.replace_one(sr_query, sr_profile)
            if sr_weekly_profile:
                sr_weekly_profile["weekly_reviews"] = str(int(sr_weekly_profile["weekly_reviews"]) + 1)
                staffweeklycol.replace_one(sr_query, sr_weekly_profile)

            new_name = f"p-{interaction.channel.name}"
            await interaction.channel.edit(name=new_name, archived=True)

            return

        #
        if add_case_list == []:  # only alts edited
            await interaction.edit_original_response(
                content=f"Report accepted by {accepted_by.mention}.\nLink to thread: <#{channel_id}>\n\nAgree: {len(agree_users)}\nDisagree: {len(disagree_users)}",
                embed=r_profile, view=ServerVoteView(guild, requested_by, channel_id, message_id, r_profile_list, add_case_list, title,
                                    case_title, accepted_by, agree_users, disagree_users, reason))

        elif len(add_case_list) == 1:  # [[add_case_list]] case to appeal
            add_case_list = add_case_list[0]
            add_case = format_server_add_case(add_case_list, case_title)
            reason_embed = discord.Embed(title="Reason", colour=0x1DCCA9, description=reason)
            embeds = [r_profile, add_case, reason_embed]
            add_case_list = [add_case_list]
            await interaction.edit_original_response(
                content=f"Appeal accepted by {accepted_by.mention}.\nLink to thread: <#{channel_id}>\n\nAgree: {len(agree_users)}\nDisagree: {len(disagree_users)}",
                embeds=embeds,
                view=ServerVoteView(guild, requested_by, channel_id, message_id, r_profile_list, add_case_list, title,
                              case_title, accepted_by, agree_users, disagree_users, reason))

        else:  # new case exists
            add_case = format_server_add_case(add_case_list, case_title)
            embeds = [r_profile, add_case]
            await interaction.edit_original_response(
                content=f"Report accepted by {accepted_by.mention}.\nLink to thread: <#{channel_id}>\n\nAgree: {len(agree_users)}\nDisagree: {len(disagree_users)}",
                embeds=embeds,
                view=ServerVoteView(guild, requested_by, channel_id, message_id, r_profile_list, add_case_list, title,
                                  case_title, accepted_by, agree_users, disagree_users))

    @discord.ui.button(label="Disagree", style=discord.ButtonStyle.red, custom_id="servervote:disagree")
    async def disagree_button(self, interaction, button):
        await interaction.response.defer()
        #
        guild = self.guild
        requested_by = self.requested_by
        channel_id = self.channel_id
        message_id = self.message_id
        r_profile_list = self.r_profile_list
        add_case_list = self.add_case_list
        title = self.title
        case_title = self.case_title
        accepted_by = self.accepted_by
        agree_users = self.agree_users
        disagree_users = self.disagree_users
        reason = self.reason
        #
        if interaction.user not in disagree_users:
            if interaction.user not in agree_users:
                disagree_users.append(interaction.user)
                await interaction.followup.send("You have voted Disagree.", ephemeral=True)
            elif interaction.user in agree_users:
                agree_users.remove(interaction.user)
                disagree_users.append(interaction.user)
                await interaction.followup.send("You have changed your vote from Agree to Disagree.", ephemeral=True)
        elif interaction.user in disagree_users:
            await interaction.followup.send("You have already voted Disagree.", ephemeral=True)
        #
        self.agree_users = agree_users
        self.disagree_users = disagree_users
        #
        r_profile = format_server_r_profile(guild, r_profile_list, title)
        #
        if len(disagree_users) >= 12:
            server_query = {"_id": str(guild.id)}
            server_profile = serverscol.find_one(server_query)
            if server_profile:  # if editing existing reported user
                cases = []
                no_of_cases = len(server_profile) - 2
                for i in range(1, no_of_cases + 1):
                    cases.append(server_profile[str(i)])
                if not add_case_list:  # only owner edited
                    r_profile = format_server_r_profile(guild, r_profile_list, title)
                    reason_embed = discord.Embed(title="Reason", description=reason)
                    embeds = [r_profile, reason_embed]
                    await interaction.edit_original_response(
                        content=f"**Report has been rejected.** Report accepted by {accepted_by.mention}.\nLink to thread: <#{channel_id}>\n\nAgree: {len(agree_users)}\nDisagree: {len(disagree_users)}",
                        embeds=embeds, view=None)
                    message = await bot.get_channel(channel_id).fetch_message(message_id)
                    await message.edit(
                        content=f"**Report has been rejected.** Report accepted by {accepted_by.mention}.")
                    await bot.get_channel(channel_id).send(
                        f"Report on server `{guild.id}` has been rejected. {requested_by.mention} {accepted_by.mention}")

                elif len(add_case_list) == 1:  # [[add_case_list]] case to appeal
                    add_case_list = add_case_list[0]
                    r_profile = format_server_r_profile(guild, r_profile_list, title)
                    add_case = format_server_add_case(add_case_list, case_title)
                    reason_embed = discord.Embed(title="Reason", colour=0x1DCCA9, description=reason)
                    embeds = [r_profile, add_case]
                    #
                    await interaction.edit_original_response(
                        content=f"**Appeal has been rejected.** Appeal accepted by {accepted_by.mention}.\nLink to thread: <#{channel_id}>\n\nAgree: {len(agree_users)}\nDisagree: {len(disagree_users)}",
                        embeds=embeds, view=None)
                    message = await bot.get_channel(channel_id).fetch_message(message_id)
                    await message.edit(
                        content=f"**Appeal has been rejected.** Appeal accepted by {accepted_by.mention}.")
                    await bot.get_channel(channel_id).send(
                        f"Appeal on server `{guild.id}` has been rejected. {requested_by.mention} {accepted_by.mention}")

                else:  # new case exists
                    #
                    self.add_case_list = add_case_list
                    #
                    r_profile = format_server_r_profile(guild, r_profile_list, title)
                    add_case = format_server_add_case(add_case_list, case_title)
                    embeds = [r_profile, add_case]

                    await interaction.edit_original_response(
                        content=f"**Report has been rejected.** Report accepted by {accepted_by.mention}.\nLink to thread: <#{channel_id}>\n\nAgree: {len(agree_users)}\nDisagree: {len(disagree_users)}",
                        embeds=embeds, view=None)
                    message = await bot.get_channel(channel_id).fetch_message(message_id)
                    await message.edit(
                        content=f"**Report has been rejected.** Report accepted by {accepted_by.mention}.")
                    await bot.get_channel(channel_id).send(
                        f"Report on server `{guild.id}` has been rejected. {requested_by.mention} {accepted_by.mention}")

            else:  # if new reported server
                #
                self.add_case_list = add_case_list
                #
                r_profile = format_server_r_profile(guild, r_profile_list, title)
                add_case = format_server_add_case(add_case_list, case_title)
                embeds = [r_profile, add_case]
                await interaction.edit_original_response(
                    content=f"**Report has been rejected.** Report accepted by {accepted_by.mention}.\nLink to thread: <#{channel_id}>\n\nAgree: {len(agree_users)}\nDisagree: {len(disagree_users)}",
                    embeds=embeds, view=None)
                message = await bot.get_channel(channel_id).fetch_message(message_id)
                await message.edit(
                    content=f"**Report has been rejected.** Report accepted by {accepted_by.mention}.")
                await bot.get_channel(channel_id).send(
                    f"Report on server `{guild.id}` has been rejected. {requested_by.mention} {accepted_by.mention}")

            voters = agree_users + disagree_users
            for voter in voters:
                voter_query = {"_id": str(voter.id)}
                voter_profile = trusteduserscol.find_one(voter_query)
                if voter_profile:
                    voter_profile["votes"] = str(int(voter_profile["votes"]) + 1)
                    trusteduserscol.replace_one(voter_query, voter_profile)

            new_name = f"r-{interaction.channel.name}"
            await interaction.channel.edit(name=new_name, archived=True)

            return
        #
        if not add_case_list:  # only alts edited
            await interaction.edit_original_response(
                content=f"Report accepted by {accepted_by.mention}.\nLink to thread: <#{channel_id}>\n\nAgree: {len(agree_users)}\nDisagree: {len(disagree_users)}",
                embed=r_profile, view=ServerVoteView(guild, requested_by, channel_id, message_id, r_profile_list, add_case_list, title,
                              case_title,
                              accepted_by, agree_users, disagree_users, reason))

        elif len(add_case_list) == 1:  # [[add_case_list]] case to appeal
            add_case_list = add_case_list[0]
            add_case = format_server_add_case(add_case_list, case_title)
            reason_embed = discord.Embed(title="Reason", colour=0x1DCCA9, description=reason)
            embeds = [r_profile, add_case, reason_embed]
            add_case_list = [add_case_list]
            await interaction.edit_original_response(
                content=f"Appeal accepted by {accepted_by.mention}.\nLink to thread: <#{channel_id}>\n\nAgree: {len(agree_users)}\nDisagree: {len(disagree_users)}",
                embeds=embeds,
                view=ServerVoteView(guild, requested_by, channel_id, message_id, r_profile_list, add_case_list, title,
                              case_title, accepted_by, agree_users, disagree_users, reason))

        else:  # new case exists
            add_case = format_server_add_case(add_case_list, case_title)
            embeds = [r_profile, add_case]
            await interaction.edit_original_response(
                content=f"Report accepted by {accepted_by.mention}.\nLink to thread: <#{channel_id}>\n\nAgree: {len(agree_users)}\nDisagree: {len(disagree_users)}",
                embeds=embeds,
                view=ServerVoteView(guild, requested_by, channel_id, message_id, r_profile_list, add_case_list, title,
                                    case_title, accepted_by, agree_users, disagree_users))

    @discord.ui.button(label="Remove Vote", style=discord.ButtonStyle.primary, custom_id="servervote:removevote")
    async def remove_vote_button(self, interaction, button):
        await interaction.response.defer()
        #
        guild = self.guild
        requested_by = self.requested_by
        channel_id = self.channel_id
        message_id = self.message_id
        r_profile_list = self.r_profile_list
        add_case_list = self.add_case_list
        title = self.title
        case_title = self.case_title
        accepted_by = self.accepted_by
        agree_users = self.agree_users
        disagree_users = self.disagree_users
        reason = self.reason
        #
        if interaction.user in agree_users:
            agree_users.remove(interaction.user)
            await interaction.followup.send("You have removed your vote.", ephemeral=True)
        elif interaction.user in disagree_users:
            disagree_users.remove(interaction.user)
            await interaction.followup.send("You have removed your vote.", ephemeral=True)
        else:
            await interaction.followup.send("You have not voted.", ephemeral=True)
        #
        self.agree_users = agree_users
        self.disagree_users = disagree_users
        #
        r_profile = format_server_r_profile(guild, r_profile_list, title)
        if not add_case_list:
            reason_embed = discord.Embed(title="Reason", description=reason)
            embeds = [r_profile, reason_embed]
            await interaction.edit_original_response(
                content=f"Report accepted by {accepted_by.mention}.\nLink to thread: <#{channel_id}>\n\nAgree: {len(agree_users)}\nDisagree: {len(disagree_users)}",
                embeds=embeds,
                view=ServerVoteView(guild, requested_by, channel_id, message_id, r_profile_list, add_case_list, title,
                              case_title,
                              accepted_by, agree_users, disagree_users, reason))

        elif len(add_case_list) == 1:  # [[add_case_list]] case to appeal
            add_case_list = add_case_list[0]
            add_case = format_server_add_case(add_case_list, case_title)
            reason_embed = discord.Embed(title="Reason", colour=0x1DCCA9, description=reason)
            embeds = [r_profile, add_case, reason_embed]
            add_case_list = [add_case_list]
            await interaction.edit_original_response(
                content=f"Appeal accepted by {accepted_by.mention}.\nLink to thread: <#{channel_id}>\n\nAgree: {len(agree_users)}\nDisagree: {len(disagree_users)}",
                embeds=embeds,
                view=ServerVoteView(guild, requested_by, channel_id, message_id, r_profile_list, add_case_list, title,
                              case_title, accepted_by, agree_users, disagree_users, reason))

        else:
            add_case = format_server_add_case(add_case_list, case_title)
            embeds = [r_profile, add_case]
            await interaction.edit_original_response(
                content=f"Report accepted by {accepted_by.mention}.\nLink to thread: <#{channel_id}>\n\nAgree: {len(agree_users)}\nDisagree: {len(disagree_users)}",
                embeds=embeds,
                view=ServerVoteView(guild, requested_by, channel_id, message_id, r_profile_list, add_case_list, title,
                                    case_title, accepted_by, agree_users, disagree_users))

    @discord.ui.button(label="Publish", style=discord.ButtonStyle.grey, custom_id="servervote:publish")
    async def publish_button(self, interaction, button):
        await interaction.response.defer()
        #
        guild = self.guild
        requested_by = self.requested_by
        channel_id = self.channel_id
        message_id = self.message_id
        r_profile_list = self.r_profile_list
        add_case_list = self.add_case_list
        title = self.title
        case_title = self.case_title
        accepted_by = self.accepted_by
        agree_users = self.agree_users
        disagree_users = self.disagree_users
        reason = self.reason
        #
        o5_check = get(interaction.user.guild.roles, id=o5_role) in interaction.user.roles
        sr_check = get(interaction.user.guild.roles,
                       id=sr_role) in interaction.user.roles and interaction.user != requested_by and len(
            agree_users) >= 4
        if o5_check or sr_check:
            accepted_by = interaction.user
            server_query = {"_id": str(guild.id)}
            server_profile = serverscol.find_one(server_query)
            if server_profile:  # if editing existing reported user
                cases = []
                no_of_cases = len(server_profile) - 2
                for i in range(1, no_of_cases + 1):
                    cases.append(server_profile[str(i)])
                query_filter = {"_id": str(guild.id)}
                update_operation = {'$set': {"r_profile_list": r_profile_list}}
                serverscol.update_one(query_filter, update_operation)
                if add_case_list == []:  # only owner edited
                    r_profile = format_server_r_profile(guild, r_profile_list, title)
                    server_reports_channel = bot.get_channel(SERVER_REPORTS_CHANNEL)
                    await server_reports_channel.send(content=f"<@&{updated_server_report_ping}>\nServer Owner edited for `{guild.id}`",
                                                    embed=r_profile)
                    reason_embed = discord.Embed(title="Reason", description=reason)
                    await server_reports_channel.send(content=f"Reason for change(s)", embed=reason_embed)
                    embeds = [r_profile, reason_embed]
                    await interaction.edit_original_response(
                        content=f"**Report has been published.** Report accepted by {accepted_by.mention}.\nLink to thread: <#{channel_id}>\n\nAgree: {len(agree_users)}\nDisagree: {len(disagree_users)}",
                        embeds=embeds, view=None)
                    message = await bot.get_channel(channel_id).fetch_message(message_id)
                    await message.edit(
                        content=f"**Report has been published.** Report accepted by {accepted_by.mention}.")
                    await bot.get_channel(channel_id).send(
                        f"Report on `{guild.id}` has been published. {requested_by.mention} {accepted_by.mention}")

                elif len(add_case_list) == 1:  # [[add_case_list]] case to appeal
                    add_case_list = add_case_list[0]
                    appeal_case_number = next((k for k, v in server_profile.items() if v == add_case_list), None)
                    query_filter = {"_id": str(guild.id)}
                    update_operation = {"$unset": {appeal_case_number: ""}}
                    serverscol.update_one(query_filter, update_operation)
                    #
                    server_query = {"_id": str(guild.id)}
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
                            tags_strings.append(case[1])
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
                        query_filter = {"_id": str(guild.id)}
                        serverscol.replace_one(query_filter, server_profile)
                    #
                    r_profile = format_server_r_profile(guild, r_profile_list, title)
                    add_case = format_server_add_case(add_case_list, case_title)
                    reason_embed = discord.Embed(title="Reason", colour=0x1DCCA9, description=reason)
                    embeds = [r_profile, add_case]
                    #
                    server_reports_channel = bot.get_channel(SERVER_REPORTS_CHANNEL)
                    await server_reports_channel.send(content=f"<@&{appealed_server_report_ping}>\nAppeal on `{guild.id}`",
                                                    embeds=embeds)
                    await server_reports_channel.send(content=f"Reason for appeal", embed=reason_embed)
                    await interaction.edit_original_response(
                        content=f"**Appeal has been published.** Appeal accepted by {accepted_by.mention}.\nLink to thread: <#{channel_id}>\n\nAgree: {len(agree_users)}\nDisagree: {len(disagree_users)}",
                        embeds=embeds, view=None)
                    message = await bot.get_channel(channel_id).fetch_message(message_id)
                    await message.edit(
                        content=f"**Appeal has been published.** Appeal accepted by {accepted_by.mention}.")
                    await bot.get_channel(channel_id).send(
                        f"Appeal on `{guild.id}` has been published. {requested_by.mention} {accepted_by.mention}")

                else:  # new case exists
                    add_case_list[5] = f"{interaction.user.mention}"
                    #
                    self.add_case_list = add_case_list
                    #
                    r_profile = format_server_r_profile(guild, r_profile_list, title)
                    add_case = format_server_add_case(add_case_list, case_title)
                    embeds = [r_profile, add_case]

                    query_filter = {"_id": str(guild.id)}
                    update_operation = {'$set': {"r_profile_list": r_profile_list}}
                    serverscol.update_one(query_filter, update_operation)
                    update_operation = {'$set': {str(no_of_cases + 1): add_case_list}}
                    serverscol.update_one(query_filter, update_operation)

                    server_reports_channel = bot.get_channel(SERVER_REPORTS_CHANNEL)
                    await server_reports_channel.send(content=f"<@&{updated_server_report_ping}>\nReport added on `{guild.id}`",
                                                    embeds=embeds)
                    await interaction.edit_original_response(
                        content=f"**Report has been published.** Report accepted by {accepted_by.mention}.\nLink to thread: <#{channel_id}>\n\nAgree: {len(agree_users)}\nDisagree: {len(disagree_users)}",
                        embeds=embeds, view=None)
                    message = await bot.get_channel(channel_id).fetch_message(message_id)
                    await message.edit(
                        content=f"**Report has been published.** Report accepted by {accepted_by.mention}.")
                    await bot.get_channel(channel_id).send(
                        f"Report on `{guild.id}` has been published. {requested_by.mention} {accepted_by.mention}")

            else:  # if new reported server
                add_case_list[5] = f"{interaction.user.mention}"
                #
                self.add_case_list = add_case_list
                #
                r_profile = format_server_r_profile(guild, r_profile_list, title)
                add_case = format_server_add_case(add_case_list, case_title)
                embeds = [r_profile, add_case]

                new_server = {"_id": str(guild.id), "r_profile_list": r_profile_list,
                            "1": add_case_list}
                serverscol.insert_one(new_server)

                server_reports_channel = bot.get_channel(SERVER_REPORTS_CHANNEL)
                await server_reports_channel.send(content=f"<@&{new_server_report_ping}>\nNew report on `{guild.id}`",
                                                embeds=embeds)
                await interaction.edit_original_response(
                    content=f"**Report has been published.** Report accepted by {accepted_by.mention}.\nLink to thread: <#{channel_id}>\n\nAgree: {len(agree_users)}\nDisagree: {len(disagree_users)}",
                    embeds=embeds, view=None)
                message = await bot.get_channel(channel_id).fetch_message(message_id)
                await message.edit(
                    content=f"**Report has been published.** Report accepted by {accepted_by.mention}.")
                await bot.get_channel(channel_id).send(
                    f"Report on `{guild.id}` has been published. {requested_by.mention} {accepted_by.mention}")

            voters = agree_users + disagree_users
            for voter in voters:
                voter_query = {"_id": str(voter.id)}
                voter_profile = trusteduserscol.find_one(voter_query)
                if voter_profile:
                    voter_profile["votes"] = str(int(voter_profile["votes"]) + 1)
                    trusteduserscol.replace_one(voter_query, voter_profile)

            staff_query = {"_id": str(requested_by.id)}
            staff_profile = trusteduserscol.find_one(staff_query)
            staff_weekly_profile = staffweeklycol.find_one(staff_query)
            if staff_profile:
                staff_profile["reports"] = str(int(staff_profile["reports"]) + 1)
                trusteduserscol.replace_one(staff_query, staff_profile)
            if staff_weekly_profile:
                staff_weekly_profile["weekly_reports"] = str(int(staff_weekly_profile["weekly_reports"]) + 1)
                staffweeklycol.replace_one(staff_query, staff_weekly_profile)

            sr_query = {"_id": str(accepted_by.id)}
            sr_profile = trusteduserscol.find_one(sr_query)
            sr_weekly_profile = staffweeklycol.find_one(sr_query)
            if sr_profile:
                sr_profile["reviews"] = str(int(sr_profile["reviews"]) + 1)
                trusteduserscol.replace_one(sr_query, sr_profile)
            if sr_weekly_profile:
                sr_weekly_profile["weekly_reviews"] = str(int(sr_weekly_profile["weekly_reviews"]) + 1)
                staffweeklycol.replace_one(sr_query, sr_weekly_profile)

            new_name = f"p-{interaction.channel.name}"
            await interaction.channel.edit(name=new_name, archived=True)

        else:
            await interaction.followup.send("You do not have permission to publish the report.", ephemeral=True)


# staff utils

@bot.command(name='ar', help="Sends jump urls to all active reports in the thread.")
@commands.has_any_role(staff_role)
async def ar(ctx):
    if isinstance(ctx.channel, discord.Thread):
        thread = ctx.channel
        active_reports = []
        try:
            async for message in thread.history(oldest_first=True, limit=None):
                if message.content.startswith(f"Adding report on") or \
                        message.content.startswith(f"Editing alts for") or \
                        message.content.startswith(f"Editing owner for") or \
                        message.content.startswith(f"Appealing for") or \
                        message.content.startswith(f"Initializing report on") \
                        and message.author.id == bot.user.id:
                    active_reports.append(message.jump_url)
        except Exception:
            pass
        if active_reports:
            embed = discord.Embed(description="\n\n".join(active_reports))
        else: embed = discord.Embed(description="No active reports.")
        await ctx.reply(f"{len(active_reports)} active reports in this thread.", embed=embed)
    else:
        await ctx.reply("This command can only be used in a thread.")

@bot.command(name='vr', help="Sends a list of all reports in voting in the thread.")
@commands.has_any_role(staff_role)
async def vr(ctx):
    if isinstance(ctx.channel, discord.Thread):
        thread = ctx.channel
        voting_reports = []
        try:
            async for message in thread.history(oldest_first=True, limit=None):
                if "has been submitted for voting." in message.content and message.embeds and message.author.id == bot.user.id:
                    voting_reports.append(message.jump_url)
        except Exception: pass
        if voting_reports:
            embed = discord.Embed(description=f"{"\n\n".join(voting_reports)}")
        else: embed = discord.Embed(description="No reports in voting.")
        await ctx.reply(f"{len(voting_reports)} reports in voting in this thread.", embed=embed)
    else:
        await ctx.reply("This command can only be used in a thread.")

@bot.command(name='pr', help="Sends a list of all published reports in the thread.")
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
    await ctx.reply(f"<@&{sr_role}>")

@bot.command(name="adm", help="Pings adm+.")
@commands.has_any_role(staff_role)
async def adm(ctx):
    await ctx.reply(f"<@&{adm_role}>")

@bot.command(name="tp", help="Pings ticket ping.")
@commands.has_any_role(staff_role)
async def tp(ctx):
    await ctx.reply(f"<@&{ticket_ping}>")


# slash cmds

@bot.tree.command(name='merge', description='Merges the reports of two users. This action is irreversible.')
@app_commands.describe(user1="Main", user2="Alt")
@app_commands.checks.has_role(sr_role)
async def merge_reports(interaction: discord.Interaction, user1: str, user2: str):
    if user1.strip("<@>") != user2.strip("<@>"):
        try:
            user1 = await bot.fetch_user(int(user1.strip("<@>")))
            user2 = await bot.fetch_user(int(user2.strip("<@>")))
        except discord.NotFound:
            await interaction.response.send_message(f"Please provide valid User IDs.", ephemeral=True)
        else:
            user1_query = {"_id": str(user1.id)}
            user1_profile = userscol.find_one(user1_query)
            user2_query = {"_id": str(user2.id)}
            user2_profile = userscol.find_one(user2_query)
            if user1_profile and user2_profile:
                r_profile_list1 = user1_profile["r_profile_list"]
                r_profile_list2 = user2_profile["r_profile_list"]
                user1_alts = r_profile_list1[0].strip("`").split()
                user2_alts = r_profile_list2[0].strip("`").split()
                all_alts = user1_alts + user2_alts
                all_alts.append(str(user2.id))
                if len(all_alts) != 0:
                    merged_alts_string = alts_string(all_alts)
                else: merged_alts_string = ""
                merged_alts_proofs = r_profile_list1[2] + r_profile_list2[2]
                merged_tags_list = []
                no_of_cases1 = len(user1_profile) - 2
                cases1 = []
                for i in range(1, no_of_cases1 + 1):
                    cases1.append(user1_profile[str(i)])
                tags_strings1 = []
                for case in cases1:
                    tags_strings1.append(case[2])
                for tags_string in tags_strings1:
                    tags_list = tags_string.split(", ")
                    for tag in tags_list:
                        merged_tags_list.append(tag)
                no_of_cases2 = len(user2_profile) - 2
                cases2 = []
                for i in range(1, no_of_cases2 + 1):
                    cases2.append(user2_profile[str(i)])
                tags_strings1 = []
                tags_strings2 = []
                for case in cases2:
                    tags_strings2.append(case[2])
                for tags_string in tags_strings2:
                    tags_list = tags_string.split(", ")
                    for tag in tags_list:
                        merged_tags_list.append(tag)
                merged_tags_list = sort_user_tags(merged_tags_list)
                all_other_tags = selected_string(merged_tags_list[1:])
                merged_r_profile_list = [
                    merged_alts_string,
                    all_other_tags,
                    merged_alts_proofs
                ]
                merged_cases = cases1 + cases2
                merged_cases.sort(key=lambda x: int(x[0][3:13]))
                #
                merged_profile = {
                    "_id": str(user1.id),
                    "r_profile_list": merged_r_profile_list,
                }
                i=0
                for case in merged_cases:
                    i+=1
                    merged_profile[str(i)] = case
                for alt in user2_alts:
                    alts_query = {"_id": alt}
                    alt_profile = {"_id": alt, "main": str(user1.id)}
                    userscol.replace_one(alts_query, alt_profile)
                new_user2_profile = {"_id": str(user2.id), "main": str(user1.id)}
                userscol.replace_one(user2_query, new_user2_profile)
                userscol.replace_one(user1_query, merged_profile)
                await interaction.response.send_message(f"`{user2.id}` successfully merged into `{user1.id}`.")
            elif user1_profile:
                await interaction.response.send_message(f"Report on `{user2.id}` not found.")
            elif user2_profile:
                await interaction.response.send_message(f"Report on `{user1.id}` not found.")
            else:
                await interaction.response.send_message(f"Neither user reported.")

@bot.tree.command(name='disable_vote', description='Disables a staff vote.')
@app_commands.describe(message_id="Message ID of vote")
@app_commands.checks.has_role(adm_role)
async def disable_vote(interaction: discord.Interaction, message_id: str):
    try:
        message = await interaction.channel.fetch_message(int(message_id))
    except discord.NotFound:
        await interaction.response.send_message("Message not found in this channel.", ephemeral=True)
    else:
        if "accepted by" in message.content and "Link to thread" in message.content and "Agree:" in message.content \
                and "Disagree:" in message.content and "has been published." not in message.content \
                and message.author.id == bot.user.id:
            await message.edit(view=None)
            inprogresscol.delete_one({"_id": message.id})
            thread = message.channel
            new_name = f"r-{thread.name}"
            await interaction.response.send_message(f"Vote has been disabled by {interaction.user.mention}.")
            await thread.edit(name=new_name, archived=True)
        else:
            await interaction.response.send_message("That is not a valid staff vote. Please try again.", ephemeral=True)

@bot.tree.command(name='disable', description='Disables a report/appeal.')
@app_commands.describe(message_id="Message ID of report/appeal")
@app_commands.checks.has_role(sr_role)
async def disable(interaction: discord.Interaction, message_id: str):
    try:
        message = await interaction.channel.fetch_message(int(message_id))
    except discord.NotFound:
        await interaction.response.send_message("Message not found in this channel.", ephemeral=True)
    else:
        if message.content.startswith(f"Adding report on") or \
                    message.content.startswith(f"Editing alts for") or \
                    message.content.startswith(f"Editing owner for") or \
                    message.content.startswith(f"Appealing for") or \
                    message.content.startswith(f"Initializing report on") \
                    and message.author.id == bot.user.id:
            await message.edit(content=f"**Disabled by {interaction.user.mention}.**", view=None)
            inprogresscol.delete_one({"_id": message.id})
            await interaction.response.send_message("Report/appeal disabled.")
        else:
            await interaction.response.send_message("That is not a valid report/appeal. Please try again.", ephemeral=True)

@bot.tree.command(name="appoint", description="Appoint a staff/trusted user.")
@app_commands.describe(user="User to appoint", category="staff/mm/pilot/trader")
@app_commands.checks.has_role(adm_role)
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
                trusteduser_profile["current_staff"] = "1"
                trusteduser_profile["staff"] = "1"
                trusteduserscol.replace_one(user_query, trusteduser_profile)
                if not staffweeklycol.find_one(user_query):
                    new_staff = {
                        "_id": str(user.id),
                        "weekly_reports": "0",
                        "weekly_reviews": "0",
                    }
                    staffweeklycol.insert_one(new_staff)
                await interaction.response.send_message(f"`{user.id}` has been appointed as current TRI Staff.")
            elif category == "mm":
                trusteduser_profile["mm"] = "1"
                trusteduserscol.replace_one(user_query, trusteduser_profile)
                await interaction.response.send_message(f"`{user.id}` has been appointed as Professional MM.")
            elif category == "pilot":
                trusteduser_profile["pilot"] = "1"
                trusteduserscol.replace_one(user_query, trusteduser_profile)
                await interaction.response.send_message(f"`{user.id}` has been appointed as Professional Pilot.")
            elif category == "trader":
                trusteduser_profile["trader"] = "1"
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
                    "current_staff": "1",
                    "staff": "1",
                    "mm": "0",
                    "pilot": "0",
                    "trader": "0",
                    "reports": "0",
                    "reviews": "0",
                    "votes": "0",
                }
                trusteduserscol.insert_one(new_user)
                new_staff = {
                    "_id": str(user.id),
                    "weekly_reports": "0",
                    "weekly_reviews": "0",
                }
                staffweeklycol.insert_one(new_staff)
                await interaction.response.send_message(f"`{user.id}` has been appointed as current TRI Staff.")
            elif category == "mm":
                new_user = {
                    "_id": str(user.id),
                    "current_staff": "0",
                    "staff": "0",
                    "mm": "1",
                    "pilot": "0",
                    "trader": "0",
                    "reports": "0",
                    "reviews": "0",
                    "votes": "0",
                }
                trusteduserscol.insert_one(new_user)
                await interaction.response.send_message(f"`{user.id}` has been appointed as Professional MM.")
            elif category == "pilot":
                new_user = {
                    "_id": str(user.id),
                    "current_staff": "0",
                    "staff": "0",
                    "mm": "0",
                    "pilot": "1",
                    "trader": "0",
                    "reports": "0",
                    "reviews": "0",
                }
                trusteduserscol.insert_one(new_user)
                await interaction.response.send_message(f"`{user.id}` has been appointed as Professional Pilot.")
            elif category == "trader":
                new_user = {
                    "_id": str(user.id),
                    "current_staff": "0",
                    "staff": "0",
                    "mm": "0",
                    "pilot": "0",
                    "trader": "1",
                    "reports": "0",
                    "reviews": "0",
                    "votes": "0",
                }
                trusteduserscol.insert_one(new_user)
                await interaction.response.send_message(f"`{user.id}` has been appointed as Trusted Trader.")
            else:
                await interaction.response.send_message(f"Please enter a valid role.", ephemeral=True)

@bot.tree.command(name="dismiss", description="Dismiss a staff/trusted user.")
@app_commands.describe(user="User to dismiss", category="staff/mm/pilot/trader")
@app_commands.checks.has_role(adm_role)
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
                if trusteduser_profile["current_staff"] == "1":
                    trusteduser_profile["current_staff"] = "0"
                    staffweeklycol.delete_one(user_query)
                elif trusteduser_profile["current_staff"] == "0":
                    trusteduser_profile["staff"] = "0"
                trusteduserscol.replace_one(user_query, trusteduser_profile)
                await interaction.response.send_message(f"`{user.id}` has been dismissed as TRI Staff.")
            elif category == "mm":
                trusteduser_profile["mm"] = "0"
                trusteduserscol.replace_one(user_query, trusteduser_profile)
                await interaction.response.send_message(f"`{user.id}` has been dismissed as Professional MM.")
            elif category == "pilot":
                trusteduser_profile["pilot"] = "0"
                trusteduserscol.replace_one(user_query, trusteduser_profile)
                await interaction.response.send_message(f"`{user.id}` has been dismissed as Professional Pilot.")
            elif category == "trader":
                trusteduser_profile["trader"] = "0"
                trusteduserscol.replace_one(user_query, trusteduser_profile)
                await interaction.response.send_message(f"`{user.id}` has been dismissed as Trusted Trader.")
            else:
                await interaction.response.send_message(f"Please enter a valid role.", ephemeral=True)
            trusteduser_profile = trusteduserscol.find_one(user_query)
            if trusteduser_profile["current_staff"] == "0" and trusteduser_profile["staff"] == "0" and \
                    trusteduser_profile["mm"] == "0" and trusteduser_profile["pilot"] == "0" and trusteduser_profile[
                "trader"] == "0":
                trusteduserscol.delete_one(user_query)

@bot.tree.command(name="add_trusted", description="Add a server as trusted.")
@app_commands.describe(server="Server invite")
@app_commands.checks.has_role(o5_role)
async def add_trusted(interaction: discord.Interaction, server: str):
    try:
        invite = await bot.fetch_invite(server)
    except discord.NotFound:
        await interaction.response.send_message("The invite link is **invalid** or **expired**.", ephemeral=True)
    except discord.Forbidden:
        await interaction.response.send_message("Unable to access details of invite.", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"An error occurred: {e}", ephemeral=True)
    else:
        guild = invite.guild
        guild_id = invite.guild.id
        server_query = {"_id": str(guild_id)}
        trustedserver_profile = trustedserverscol.find_one(server_query)
        if trustedserver_profile:
            await interaction.response.send_message(f"`{guild_id}` is already in Trusted Servers.")
        else:
            trustedserverscol.insert_one(server_query)
            await interaction.response.send_message(f"`{guild_id}` has been added to Trusted Servers.")

@bot.tree.command(name="remove_trusted", description="Remove a server from Trusted Servers.")
@app_commands.describe(server="Server invite or ID")
@app_commands.checks.has_role(o5_role)
async def remove_trusted(interaction: discord.Interaction, server: str):
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
            guild = invite.guild
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
    reports_count = userscol.count_documents({}) + serverscol.count_documents({})
    await bot.change_presence(status=discord.Status.dnd,
                              activity=discord.Activity(
                                  type=discord.ActivityType.watching,
                                  name=f"{reports_count} reports."
                              )
                              )

bot.run(TOKEN)