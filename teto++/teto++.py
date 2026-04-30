#  yuelyxia  ©  2025 – 2026

from dotenv import load_dotenv
import os
load_dotenv()

import pymongo

import asyncio

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


@tasks.loop(hours=1.0)
async def update_reports_count():
    reports_count = userscol.count_documents({}) + serverscol.count_documents({})
    await bot.change_presence(status=discord.Status.dnd,
                              activity=discord.Activity(
                                  type=discord.ActivityType.watching,
                                  name=f"{reports_count} reports."
                              )
                              )

@bot.event
async def on_ready():
    update_reports_count.start()

"""
@bot.event
async def on_message(message):
    if message.channel.id == USER_REPORTS_CHANNEL and message.author.id == 1450073025818136598:
        if message.embeds:
            embed = message.embeds[0]
            text_to_search = embed.description or ""
            match = re.search(r'`(.+?)`', text_to_search)
            if match:
                user_id = int(match.group(1))
                for guild in bot.guilds:
                    try:
                        await guild.fetch_member(user_id)
                    except Exception: pass
                    else:


    await bot.process_commands(message)
"""


# check

@bot.command(name='c', help='Checks a user or server.')
async def c(ctx, *, to_check: str = None):
    if ctx.guild.id == TRI_Archive:
        return
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
                profile.description = f"{user.name}\n`{user.id}`\n{user.mention}"
                profile.description += "\n**Account Created:** " + f"<t:{round(int(user.created_at.timestamp()))}:D> (<t:{round(int(user.created_at.timestamp()))}:R>)" + '\n'
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
                trusted_embed = format_trustedserver_profile(UnknownGuild(int(to_check.strip('<@>'))),
                                                             trustedserver_profile)
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
                    trusted_embed = format_trustedserver_profile(guild, trustedserver_profile)
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

@bot.command(name='mc', help='Checks a list of users (max 200), leave a space between users.')
async def mc(ctx, *, to_check: str = None):
    if ctx.guild.id == TRI_Archive:
        return
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
            image_links = cases[current_case-1][7]
            image_embeds = image_links_to_embeds(image_links)
            await interaction.followup.send(f"Proofs for `{user.id}`", embeds=image_embeds, ephemeral=True)

    @discord.ui.button(label="Alts Proofs", style=discord.ButtonStyle.grey, custom_id="see_alts_proofs")
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
        image_links = cases[current_case - 1][6]
        image_embeds = image_links_to_embeds(image_links)
        await interaction.followup.send(f"Proofs for `{guild.id}`", embeds=image_embeds, ephemeral=True)

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
    reports_count = userscol.count_documents({}) + serverscol.count_documents({})
    await bot.change_presence(status=discord.Status.dnd,
        activity=discord.Activity(
            type=discord.ActivityType.watching,
            name=f"{reports_count} reports."
        )
    )







bot.run(TOKEN)