#  yuelyxia  ©  2025 – 2026

from dotenv import load_dotenv
import os

from pymongo.errors import DuplicateKeyError

load_dotenv()

import pymongo

import asyncio
import re

import discord
from discord import app_commands
from discord.ext import commands, tasks

from typing import Optional, Literal

TOKEN = os.getenv("TOKEN")
CLIENT = os.getenv("CLIENT")

# mongodb info
client = pymongo.MongoClient(CLIENT)
db = client["database"]
userscol = db["users"]
altscol = db["alts"]

# tri roles info
o5_role = 1372426616671834234
staff_role = 1373803879623430268
ticket_ping = 1449382692671193294
sr_role = 1375254710952661102
adm_role = 1375276457890287748

NERU_LOGS = 1460858907491569816
PROOFS_CHANNEL = 1455055877034868769

intents = discord.Intents.all()
bot = commands.Bot(command_prefix=',', help_command=None, intents=intents)

def alts_string(alts_list):
    string = ""
    for alt in alts_list:
        string += f"{str(alt)}" + " "
    string = string[:-1]
    string = "`" + string + "`"
    return string
def default_no_alts(user):
    profile = discord.Embed(colour=0xffffff)
    profile.description = f"{user.name} `{user.id}`\n"
    profile.description += f"\nNo alts logged for this user."
    return profile

@tasks.loop(hours=1.0)
async def update_alts_count():
    alts_count = altscol.count_documents({})
    await bot.change_presence(
        status=discord.Status.idle,
        activity=discord.Activity(
                                  type=discord.ActivityType.watching,
                                  name=f"{alts_count} alts."
                              )
                              )

@bot.event
async def on_ready():
    update_alts_count.start()

@bot.event
async def on_message(message: discord.Message):
    neru_logs_channel = bot.get_channel(NERU_LOGS)
    if message.author.id == 703886990948565003:
        pattern1 = r"\((\d{17,20})\)\s*-\s*Main account\s*:\s*<@\d{17,20}>\s*\((\d{17,20})\)"
        match1 = re.search(pattern1, message.content)
        match2 = False
        if message.embeds:
            embed = message.embeds[0]
            for field in embed.fields:
                if field.name.lower() == "alt account":
                    match = re.search(r"\((\d+)\)", field.value)
                    if match:
                        match2 = True
                        alt1_id = match.group(1)
                elif field.name.lower() == "main account":
                    match = re.search(r"\((\d+)\)", field.value)
                    if match:
                        alt2_id = match.group(1)
        if match1 or match2:
            if match1:
                alt1_id = match1.group(1)
                alt2_id = match1.group(2)
            if alt1_id != alt2_id:
                proof = f"{message.jump_url} ┈ dc"
                try:
                    parts = message.jump_url.split('/')
                    guild_id = int(parts[-3])
                    guild = await bot.fetch_guild(guild_id)
                    if guild:
                        server_name = guild.name
                        formatted_proof = proof + f" ┈ {server_name}"
                except Exception:
                    pass
                alt1_query = {"_id": alt1_id}
                alt1_info = altscol.find_one(alt1_query)
                alt2_query = {"_id": alt2_id}
                alt2_info = altscol.find_one(alt2_query)
                if alt1_info:  # alt 1 logged
                    if alt2_info:  # alt 2 also logged
                        if alt1_id in alt2_info["alts"] and alt2_id in alt1_info["alts"]:  # check if already exists
                            pass
                        else:
                            old_alts1 = alt1_info["alts"].copy()
                            old_alts2 = alt2_info["alts"].copy()
                            old_proofs1 = alt1_info["proofs"].copy()
                            old_proofs2 = alt2_info["proofs"].copy()
                            for alt in old_alts1:
                                alt_query = {"_id": alt}
                                alt_info = altscol.find_one(alt_query)
                                alt_info["alts"] += old_alts2
                                alt_info["alts"].append(alt2_id)
                                alt_info["proofs"] += old_proofs2
                                alt_info["proofs"].append(proof)
                                altscol.replace_one(alt_query, alt_info)
                            for alt in old_alts2:
                                alt_query = {"_id": alt}
                                alt_info = altscol.find_one(alt_query)
                                alt_info["alts"] += old_alts1
                                alt_info["alts"].append(alt1_id)
                                alt_info["proofs"] += old_proofs1
                                alt_info["proofs"].append(proof)
                                altscol.replace_one(alt_query, alt_info)
                            alt1_info["alts"] += old_alts2
                            alt1_info["alts"].append(alt2_id)
                            alt1_info["proofs"] += old_proofs2
                            alt1_info["proofs"].append(proof)
                            alt2_info["alts"] += old_alts1
                            alt2_info["alts"].append(alt1_id)
                            alt2_info["proofs"] += old_proofs1
                            alt2_info["proofs"].append(proof)
                            altscol.replace_one(alt1_query, alt1_info)
                            altscol.replace_one(alt2_query, alt2_info)
                            user1_query = {"_id": alt1_id}
                            user1_profile = userscol.find_one(user1_query)
                            user2_query = {"_id": alt2_id}
                            user2_profile = userscol.find_one(user2_query)
                            if user1_profile and user2_profile and len(user1_profile)>2 and len(user2_profile)>2:
                                await neru_logs_channel.send(
                                    f"`{alt1_id}` and `{alt2_id}` have been added as alts.\n{formatted_proof} \n<@&{sr_role}> Separate reports detected, use /merge to merge them.")
                            elif user1_profile and len(user1_profile)>2:  # user 1 reported, user 2 not reported
                                r_profile_list = user1_profile["r_profile_list"]
                                user1_alts = r_profile_list[0].strip("`").split()
                                if alt2_id not in user1_alts: user1_alts.append(alt2_id)
                                r_profile_list[0] = alts_string(user1_alts)
                                user1_profile["r_profile_list"] = r_profile_list
                                userscol.replace_one(user1_query, user1_profile)
                                new_user = {"_id": alt2_id, "main": alt1_id}
                                userscol.insert_one(new_user)
                                await neru_logs_channel.send(
                                    f"`{alt1_id}` and `{alt2_id}` have been added as alts.\n{formatted_proof} `{alt2_id}` has been added to the report on `{alt1_id}`")
                            elif user2_profile and len(user2_profile)>2:  # user 2 reported, user 1 not reported
                                r_profile_list = user2_profile["r_profile_list"]
                                user2_alts = r_profile_list[0].strip("`").split()
                                if alt1_id not in user2_alts: user2_alts.append(alt1_id)
                                r_profile_list[0] = alts_string(user2_alts)
                                user2_profile["r_profile_list"] = r_profile_list
                                userscol.replace_one(user2_query, user2_profile)
                                new_user = {"_id": alt1_id, "main": alt2_id}
                                userscol.insert_one(new_user)
                                await neru_logs_channel.send(
                                    f"`{alt2_id}` and `{alt1_id}` have been added as alts.\n{formatted_proof} `{alt1_id}` has been added to the report on `{alt2_id}`")
                            else:
                                await neru_logs_channel.send(
                                    f"`{alt1_id}` and `{alt2_id}` have been added as alts.\n{formatted_proof}")
                    else:  # alt 2 not logged
                        old_alts1 = alt1_info["alts"].copy()
                        old_proofs1 = alt1_info["proofs"].copy()
                        alt2_info = {"_id": alt2_id, "alts": old_alts1, "proofs": []}
                        alt2_info["alts"].append(alt1_id)
                        alt2_info["proofs"] = old_proofs1
                        alt2_info["proofs"].append(proof)
                        for alt in old_alts1:
                            alt_query = {"_id": alt}
                            alt_info = altscol.find_one(alt_query)
                            alt_info["alts"].append(alt2_id)
                            alt_info["proofs"].append(proof)
                            altscol.replace_one(alt_query, alt_info)
                        alt1_info["alts"].append(alt2_id)
                        alt1_info["proofs"].append(proof)
                        altscol.replace_one(alt1_query, alt1_info)
                        altscol.insert_one(alt2_info)
                        user1_query = {"_id": alt1_id}
                        user1_profile = userscol.find_one(user1_query)
                        user2_query = {"_id": alt2_id}
                        user2_profile = userscol.find_one(user2_query)
                        if user1_profile and user2_profile and len(user1_profile)>2 and len(user2_profile)>2:
                            await neru_logs_channel.send(
                                f"`{alt1_id}` and `{alt2_id}` have been added as alts.\n{formatted_proof} \n<@&{sr_role}> Separate reports detected, use /merge to merge them.")
                        elif user1_profile and len(user1_profile)>2:  # user 1 reported, user 2 not reported
                            r_profile_list = user1_profile["r_profile_list"]
                            user1_alts = r_profile_list[0].strip("`").split()
                            if alt2_id not in user1_alts: user1_alts.append(alt2_id)
                            r_profile_list[0] = alts_string(user1_alts)
                            user1_profile["r_profile_list"] = r_profile_list
                            userscol.replace_one(user1_query, user1_profile)
                            new_user = {"_id": alt2_id, "main": alt1_id}
                            userscol.insert_one(new_user)
                            await neru_logs_channel.send(
                                f"`{alt1_id}` and `{alt2_id}` have been added as alts.\n{formatted_proof} `{alt2_id}` has been added to the report on `{alt1_id}`")
                        elif user2_profile and len(user2_profile)>2:  # user 2 reported, user 1 not reported
                            r_profile_list = user2_profile["r_profile_list"]
                            user2_alts = r_profile_list[0].strip("`").split()
                            if alt1_id not in user2_alts: user2_alts.append(alt1_id)
                            r_profile_list[0] = alts_string(user2_alts)
                            user2_profile["r_profile_list"] = r_profile_list
                            userscol.replace_one(user2_query, user2_profile)
                            new_user = {"_id": alt1_id, "main": alt2_id}
                            userscol.insert_one(new_user)
                            await neru_logs_channel.send(
                                f"`{alt2_id}` and `{alt1_id}` have been added as alts.\n{formatted_proof} `{alt1_id}` has been added to the report on `{alt2_id}`")
                        else:
                            await neru_logs_channel.send(
                                f"`{alt1_id}` and `{alt2_id}` have been added as alts.\n{formatted_proof}")
                else:  # alt 1 not logged
                    if alt2_info:  # but alt 2 logged
                        old_alts2 = alt2_info["alts"].copy()
                        old_proofs2 = alt2_info["proofs"].copy()
                        alt1_info = {"_id": alt1_id, "alts": old_alts2, "proofs": []}
                        alt1_info["alts"].append(alt2_id)
                        alt1_info["proofs"] = old_proofs2
                        alt1_info["proofs"].append(proof)
                        for alt in old_alts2:
                            alt_query = {"_id": alt}
                            alt_info = altscol.find_one(alt_query)
                            alt_info["alts"].append(alt1_id)
                            alt_info["proofs"].append(proof)
                            altscol.replace_one(alt_query, alt_info)
                        alt2_info["alts"].append(alt1_id)
                        alt2_info["proofs"].append(proof)
                        altscol.replace_one(alt2_query, alt2_info)
                        altscol.insert_one(alt1_info)
                        user1_query = {"_id": alt1_id}
                        user1_profile = userscol.find_one(user1_query)
                        user2_query = {"_id": alt2_id}
                        user2_profile = userscol.find_one(user2_query)
                        if user1_profile and user2_profile and len(user1_profile)>2 and len(user2_profile)>2:
                            await neru_logs_channel.send(
                                f"`{alt1_id}` and `{alt2_id}` have been added as alts.\n{formatted_proof} \n<@&{sr_role}> Separate reports detected, use /merge to merge them.")
                        elif user1_profile and len(user1_profile)>2:  # user 1 reported, user 2 not reported
                            r_profile_list = user1_profile["r_profile_list"]
                            user1_alts = r_profile_list[0].strip("`").split()
                            if alt2_id not in user1_alts: user1_alts.append(alt2_id)
                            r_profile_list[0] = alts_string(user1_alts)
                            user1_profile["r_profile_list"] = r_profile_list
                            userscol.replace_one(user1_query, user1_profile)
                            new_user = {"_id": alt2_id, "main": alt1_id}
                            userscol.insert_one(new_user)
                            await neru_logs_channel.send(
                                f"`{alt1_id}` and `{alt2_id}` have been added as alts.\n{formatted_proof} `{alt2_id}` has been added to the report on `{alt1_id}`")
                        elif user2_profile and len(user2_profile)>2:  # user 2 reported, user 1 not reported
                            r_profile_list = user2_profile["r_profile_list"]
                            user2_alts = r_profile_list[0].strip("`").split()
                            if alt1_id not in user2_alts: user2_alts.append(alt1_id)
                            r_profile_list[0] = alts_string(user2_alts)
                            user2_profile["r_profile_list"] = r_profile_list
                            userscol.replace_one(user2_query, user2_profile)
                            new_user = {"_id": alt1_id, "main": alt2_id}
                            userscol.insert_one(new_user)
                            await neru_logs_channel.send(
                                f"`{alt2_id}` and `{alt1_id}` have been added as alts.\n{formatted_proof} `{alt1_id}` has been added to the report on `{alt2_id}`")
                        else:
                            await neru_logs_channel.send(
                                f"`{alt1_id}` and `{alt2_id}` have been added as alts.\n{formatted_proof}")
                    else:  # both alts not logged
                        alt1_info = {
                            "_id": alt1_id,
                            "alts": [alt2_id],
                            "proofs": [proof]
                        }
                        alt2_info = {
                            "_id": alt2_id,
                            "alts": [alt1_id],
                            "proofs": [proof]
                        }
                        #
                        altscol.insert_one(alt1_info)
                        altscol.insert_one(alt2_info)
                        #
                        user1_query = {"_id": alt1_id}
                        user1_profile = userscol.find_one(user1_query)
                        user2_query = {"_id": alt2_id}
                        user2_profile = userscol.find_one(user2_query)
                        if user1_profile and user2_profile and len(user1_profile)>2 and len(user2_profile)>2:
                            await neru_logs_channel.send(
                                f"`{alt1_id}` and `{alt2_id}` have been added as alts.\n{formatted_proof} \n<@&{sr_role}> Separate reports detected, use /merge to merge them.")
                        elif user1_profile and len(user1_profile)>2:  # user 1 reported, user 2 not reported
                            r_profile_list = user1_profile["r_profile_list"]
                            user1_alts = r_profile_list[0].strip("`").split()
                            if alt2_id not in user1_alts: user1_alts.append(alt2_id)
                            r_profile_list[0] = alts_string(user1_alts)
                            user1_profile["r_profile_list"] = r_profile_list
                            userscol.replace_one(user1_query, user1_profile)
                            new_user = {"_id": alt2_id, "main": alt1_id}
                            userscol.insert_one(new_user)
                            await neru_logs_channel.send(
                                f"`{alt1_id}` and `{alt2_id}` have been added as alts.\n{formatted_proof} `{alt2_id}` has been added to the report on `{alt1_id}`")
                        elif user2_profile and len(user2_profile)>2:  # user 2 reported, user 1 not reported
                            r_profile_list = user2_profile["r_profile_list"]
                            user2_alts = r_profile_list[0].strip("`").split()
                            if alt1_id not in user2_alts: user2_alts.append(alt1_id)
                            r_profile_list[0] = alts_string(user2_alts)
                            user2_profile["r_profile_list"] = r_profile_list
                            userscol.replace_one(user2_query, user2_profile)
                            new_user = {"_id": alt1_id, "main": alt2_id}
                            userscol.insert_one(new_user)
                            await neru_logs_channel.send(
                                f"`{alt2_id}` and `{alt1_id}` have been added as alts.\n{formatted_proof} `{alt1_id}` has been added to the report on `{alt2_id}`")
                        else:
                            await neru_logs_channel.send(
                                f"`{alt1_id}` and `{alt2_id}` have been added as alts.\n{formatted_proof}")

    await bot.process_commands(message)

@bot.command(name="ma", help="Checks a list of users (max 100) for logged alts, leave a space between users.")
async def ma(ctx, *, to_check: str = None):
    if to_check != None:
        users = to_check.split()
        if len(users) > 100:
            return await ctx.reply("Exceeded 100 users.")
        estimated_seconds = round(len(users) * 0.35, 1)
        status_message = await ctx.reply(f"Checking **{len(users)}** users.\nEstimated time: **~{estimated_seconds}s**")
        valid_users = []
        invalid_users = []
        for raw_user in users:
            try:
                user_id = int(re.sub(r"\D", "", raw_user))
                fetched_user = await bot.fetch_user(user_id)
            except:
                invalid_users.append(raw_user)
            else:
                if fetched_user not in valid_users:
                    valid_users.append(fetched_user)
        if not valid_users:
            await status_message.delete()
            return await ctx.reply("No valid user IDs provided.")
        lines = []
        embeds = []
        for user in valid_users:
            user_id = str(user.id)
            alts_info = altscol.find_one({"_id": user_id})
            if not alts_info:
                lines.append(f"{user.mention} `{user.id}` ┈ No alts")
                continue
            else:
                alts_count = len(alts_info.get("alts", []))
                if alts_count > 0:
                    lines.append(f"**{user.mention} `{user.id}` ┈ {alts_count} alt(s)**")
                    continue
        line_groups = [lines[i:i + 25] for i in range(0, len(lines), 25)][:10]
        for group in line_groups:
            embed = discord.Embed(description="\n".join(group))
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
        await status_message.edit(content="Finished checking users.")

@bot.command(name="a", help="Checks a user for logged alts.")
async def a(ctx, *, to_check: str = None):
    if to_check is None:
        user = ctx.author
    else:
        try:
            user = await bot.fetch_user(int(to_check.strip('<@!>')))
        except:
            await ctx.send("Please provide a valid user ID.")
            return
    user_id = str(user.id)
    alts_info = altscol.find_one({"_id": user_id})
    if not alts_info:
        await ctx.reply(embed=default_no_alts(user))
        return
    alts = alts_info.get("alts", [])
    proofs = alts_info.get("proofs", [])
    lines_with_server = []
    lines_without_server = []
    for i, alt in enumerate(alts):
        base_proof = proofs[i] if i < len(proofs) else "No proof"
        proof_with_server = base_proof
        if isinstance(base_proof, str) and base_proof.endswith(" ┈ dc"):
            jump_url = base_proof[:-5]
            parts = jump_url.split("/")
            try:
                guild_id = int(parts[-3])
                guild = bot.get_guild(guild_id) or await bot.fetch_guild(guild_id)
                if guild:
                    proof_with_server = base_proof + f" ┈ {guild.name}"
            except Exception:
                pass
        lines_without_server.append(f"`{alt}` ┈ {base_proof}")
        lines_with_server.append(f"`{alt}` ┈ {proof_with_server}")
    LIMIT = 3900
    GLOBAL_LIMIT = 5800
    header = f"Alts for {user.name} `{user.id}`\n"
    def calculate_total_chars(lines_list):
        total_embed_chars = 0
        current_chunk = []
        for line in lines_list:
            if len(header) + len("\n".join(current_chunk + [line])) > LIMIT:
                total_embed_chars += len(header) + len("\n".join(current_chunk))
                current_chunk = [line]
            else:
                current_chunk.append(line)
        if current_chunk:
            total_embed_chars += len(header) + len("\n".join(current_chunk))
        return total_embed_chars
    if calculate_total_chars(lines_with_server) <= GLOBAL_LIMIT:
        chosen_lines = lines_with_server
    else:
        chosen_lines = lines_without_server
    embeds = []
    chunk = []
    for line in chosen_lines:
        test_chunk = "\n".join(chunk + [line])
        if len(header) + len(test_chunk) > LIMIT:
            embed = discord.Embed(colour=0xffffff)
            embed.description = header + "\n".join(chunk)
            embeds.append(embed)
            chunk = [line]
        else:
            chunk.append(line)
    if chunk:
        embed = discord.Embed(colour=0xffffff)
        embed.description = header + "\n".join(chunk)
        embeds.append(embed)
    await ctx.reply(embeds=embeds, view=RelatedIDsView(user_id, alts))

class RelatedIDsView(discord.ui.View):
    def __init__(self, user_id, alts):
        super().__init__(timeout=None)
        self.user_id = user_id
        self.alts = alts

    @discord.ui.button(label="Related IDs", style=discord.ButtonStyle.grey, custom_id="related_ids")
    async def related_ids_button(self, interaction, button):
        #
        user_id = self.user_id
        alts = self.alts
        string = user_id + " " + " ".join(alts)
        await interaction.response.send_message(f"`{string}`", ephemeral=True)

imports = app_commands.Group(name="import", description="Import Double Counter alt intrusions.")
bot.tree.add_command(imports)

@imports.command(name="recent", description="Import Double Counter alt intrusions from recent 200 messages.")
async def import_recent(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    neru_logs_channel = bot.get_channel(NERU_LOGS)
    channel = interaction.channel
    if channel:
        msg = await channel.send("Checking recent 200 messages in this channel for Double Counter alt intrusions...")
        count=0
        async for message in channel.history(limit=200):
            alt1_id = None
            alt2_id = None
            if message.author.id == 703886990948565003:
                if message.embeds:
                    embed = message.embeds[0]
                    for field in embed.fields:
                        name = field.name.lower()
                        if name == "alt account":
                            m = re.search(r"\((\d{17,20})\)", field.value)
                            if m:
                                alt1_id = m.group(1)
                        elif name == "main account":
                            m = re.search(r"\((\d{17,20})\)", field.value)
                            if m:
                                alt2_id = m.group(1)
                pattern = r"\((\d{17,20})\)\s*-\s*Main account\s*:\s*<@\d{17,20}>\s*\((\d{17,20})\)"
                match = re.search(pattern, message.content)
                if match:
                    alt1_id, alt2_id = match.group(1), match.group(2)
                if not alt1_id or not alt2_id:
                    continue
                if alt1_id == alt2_id:
                    continue
                proof = f"{message.jump_url} ┈ dc"
                formatted_proof = proof
                try:
                    parts = message.jump_url.split('/')
                    guild_id = int(parts[-3])
                    guild = await bot.fetch_guild(guild_id)
                    if guild:
                        server_name = guild.name
                        formatted_proof = proof + f" ┈ {server_name}"
                except Exception:
                    pass
                alt1_query = {"_id": alt1_id}
                alt1_info = altscol.find_one(alt1_query)
                alt2_query = {"_id": alt2_id}
                alt2_info = altscol.find_one(alt2_query)
                if alt1_info:  # alt 1 logged
                    if alt2_info:  # alt 2 also logged
                        if alt1_id in alt2_info["alts"] and alt2_id in alt1_info[
                            "alts"]:  # check if already exists
                            continue
                        else:
                            count += 1
                            old_alts1 = alt1_info["alts"].copy()
                            old_alts2 = alt2_info["alts"].copy()
                            old_proofs1 = alt1_info["proofs"].copy()
                            old_proofs2 = alt2_info["proofs"].copy()
                            for alt in old_alts1:
                                alt_query = {"_id": alt}
                                alt_info = altscol.find_one(alt_query)
                                alt_info["alts"] += old_alts2
                                alt_info["alts"].append(alt2_id)
                                alt_info["proofs"] += old_proofs2
                                alt_info["proofs"].append(proof)
                                altscol.replace_one(alt_query, alt_info)
                            for alt in old_alts2:
                                alt_query = {"_id": alt}
                                alt_info = altscol.find_one(alt_query)
                                alt_info["alts"] += old_alts1
                                alt_info["alts"].append(alt1_id)
                                alt_info["proofs"] += old_proofs1
                                alt_info["proofs"].append(proof)
                                altscol.replace_one(alt_query, alt_info)
                            alt1_info["alts"] += old_alts2
                            alt1_info["alts"].append(alt2_id)
                            alt1_info["proofs"] += old_proofs2
                            alt1_info["proofs"].append(proof)
                            alt2_info["alts"] += old_alts1
                            alt2_info["alts"].append(alt1_id)
                            alt2_info["proofs"] += old_proofs1
                            alt2_info["proofs"].append(proof)
                            altscol.replace_one(alt1_query, alt1_info)
                            altscol.replace_one(alt2_query, alt2_info)
                            user1_query = {"_id": alt1_id}
                            user1_profile = userscol.find_one(user1_query)
                            user2_query = {"_id": alt2_id}
                            user2_profile = userscol.find_one(user2_query)
                            if user1_profile and user2_profile and len(user1_profile) > 2 and len(
                                    user2_profile) > 2:
                                await neru_logs_channel.send(
                                    f"`{alt1_id}` and `{alt2_id}` have been added as alts.\n{formatted_proof} \n<@&{sr_role}> Separate reports detected, use /merge to merge them.")
                            elif user1_profile and len(
                                    user1_profile) > 2:  # user 1 reported, user 2 not reported
                                r_profile_list = user1_profile["r_profile_list"]
                                user1_alts = r_profile_list[0].strip("`").split()
                                if alt2_id not in user1_alts: user1_alts.append(alt2_id)
                                r_profile_list[0] = alts_string(user1_alts)
                                user1_profile["r_profile_list"] = r_profile_list
                                userscol.replace_one(user1_query, user1_profile)
                                new_user = {"_id": alt2_id, "main": alt1_id}
                                try:
                                    userscol.insert_one(new_user)
                                except DuplicateKeyError:
                                    continue
                                await neru_logs_channel.send(
                                    f"`{alt1_id}` and `{alt2_id}` have been added as alts.\n{formatted_proof} `{alt2_id}` has been added to the report on `{alt1_id}`")
                            elif user2_profile and len(
                                    user2_profile) > 2:  # user 2 reported, user 1 not reported
                                r_profile_list = user2_profile["r_profile_list"]
                                user2_alts = r_profile_list[0].strip("`").split()
                                if alt1_id not in user2_alts: user2_alts.append(alt1_id)
                                r_profile_list[0] = alts_string(user2_alts)
                                user2_profile["r_profile_list"] = r_profile_list
                                userscol.replace_one(user2_query, user2_profile)
                                new_user = {"_id": alt1_id, "main": alt2_id}
                                try:
                                    userscol.insert_one(new_user)
                                except DuplicateKeyError:
                                    continue
                                await neru_logs_channel.send(
                                    f"`{alt2_id}` and `{alt1_id}` have been added as alts.\n{formatted_proof} `{alt1_id}` has been added to the report on `{alt2_id}`")
                            else:
                                await neru_logs_channel.send(
                                    f"`{alt1_id}` and `{alt2_id}` have been added as alts.\n{formatted_proof}")
                    else:  # alt 2 not logged
                        count += 1
                        old_alts1 = alt1_info["alts"].copy()
                        old_proofs1 = alt1_info["proofs"].copy()
                        alt2_info = {"_id": alt2_id, "alts": old_alts1, "proofs": []}
                        alt2_info["alts"].append(alt1_id)
                        alt2_info["proofs"] = old_proofs1
                        alt2_info["proofs"].append(proof)
                        for alt in old_alts1:
                            alt_query = {"_id": alt}
                            alt_info = altscol.find_one(alt_query)
                            alt_info["alts"].append(alt2_id)
                            alt_info["proofs"].append(proof)
                            altscol.replace_one(alt_query, alt_info)
                        alt1_info["alts"].append(alt2_id)
                        alt1_info["proofs"].append(proof)
                        altscol.replace_one(alt1_query, alt1_info)
                        altscol.insert_one(alt2_info)
                        user1_query = {"_id": alt1_id}
                        user1_profile = userscol.find_one(user1_query)
                        user2_query = {"_id": alt2_id}
                        user2_profile = userscol.find_one(user2_query)
                        if user1_profile and user2_profile and len(user1_profile) > 2 and len(
                                user2_profile) > 2:
                            await neru_logs_channel.send(
                                f"`{alt1_id}` and `{alt2_id}` have been added as alts.\n{formatted_proof} \n<@&{sr_role}> Separate reports detected, use /merge to merge them.")
                        elif user1_profile and len(user1_profile) > 2:  # user 1 reported, user 2 not reported
                            r_profile_list = user1_profile["r_profile_list"]
                            user1_alts = r_profile_list[0].strip("`").split()
                            if alt2_id not in user1_alts: user1_alts.append(alt2_id)
                            r_profile_list[0] = alts_string(user1_alts)
                            user1_profile["r_profile_list"] = r_profile_list
                            userscol.replace_one(user1_query, user1_profile)
                            new_user = {"_id": alt2_id, "main": alt1_id}
                            try:
                                userscol.insert_one(new_user)
                            except DuplicateKeyError:
                                continue
                            await neru_logs_channel.send(
                                f"`{alt1_id}` and `{alt2_id}` have been added as alts.\n{formatted_proof} `{alt2_id}` has been added to the report on `{alt1_id}`")
                        elif user2_profile and len(user2_profile) > 2:  # user 2 reported, user 1 not reported
                            r_profile_list = user2_profile["r_profile_list"]
                            user2_alts = r_profile_list[0].strip("`").split()
                            if alt1_id not in user2_alts: user2_alts.append(alt1_id)
                            r_profile_list[0] = alts_string(user2_alts)
                            user2_profile["r_profile_list"] = r_profile_list
                            userscol.replace_one(user2_query, user2_profile)
                            new_user = {"_id": alt1_id, "main": alt2_id}
                            try:
                                userscol.insert_one(new_user)
                            except DuplicateKeyError:
                                continue
                            await neru_logs_channel.send(
                                f"`{alt2_id}` and `{alt1_id}` have been added as alts.\n{formatted_proof} `{alt1_id}` has been added to the report on `{alt2_id}`")
                        else:
                            await neru_logs_channel.send(
                                f"`{alt1_id}` and `{alt2_id}` have been added as alts.\n{formatted_proof}")
                else:  # alt 1 not logged
                    if alt2_info:  # but alt 2 logged
                        count += 1
                        old_alts2 = alt2_info["alts"].copy()
                        old_proofs2 = alt2_info["proofs"].copy()
                        alt1_info = {"_id": alt1_id, "alts": old_alts2, "proofs": []}
                        alt1_info["alts"].append(alt2_id)
                        alt1_info["proofs"] = old_proofs2
                        alt1_info["proofs"].append(proof)
                        for alt in old_alts2:
                            alt_query = {"_id": alt}
                            alt_info = altscol.find_one(alt_query)
                            alt_info["alts"].append(alt1_id)
                            alt_info["proofs"].append(proof)
                            altscol.replace_one(alt_query, alt_info)
                        alt2_info["alts"].append(alt1_id)
                        alt2_info["proofs"].append(proof)
                        altscol.replace_one(alt2_query, alt2_info)
                        altscol.insert_one(alt1_info)
                        user1_query = {"_id": alt1_id}
                        user1_profile = userscol.find_one(user1_query)
                        user2_query = {"_id": alt2_id}
                        user2_profile = userscol.find_one(user2_query)
                        if user1_profile and user2_profile and len(user1_profile) > 2 and len(
                                user2_profile) > 2:
                            await neru_logs_channel.send(
                                f"`{alt1_id}` and `{alt2_id}` have been added as alts.\n{formatted_proof} \n<@&{sr_role}> Separate reports detected, use /merge to merge them.")
                        elif user1_profile and len(user1_profile) > 2:  # user 1 reported, user 2 not reported
                            r_profile_list = user1_profile["r_profile_list"]
                            user1_alts = r_profile_list[0].strip("`").split()
                            if alt2_id not in user1_alts: user1_alts.append(alt2_id)
                            r_profile_list[0] = alts_string(user1_alts)
                            user1_profile["r_profile_list"] = r_profile_list
                            userscol.replace_one(user1_query, user1_profile)
                            new_user = {"_id": alt2_id, "main": alt1_id}
                            try:
                                userscol.insert_one(new_user)
                            except DuplicateKeyError:
                                continue
                            await neru_logs_channel.send(
                                f"`{alt1_id}` and `{alt2_id}` have been added as alts.\n{formatted_proof} `{alt2_id}` has been added to the report on `{alt1_id}`")
                        elif user2_profile and len(user2_profile) > 2:  # user 2 reported, user 1 not reported
                            r_profile_list = user2_profile["r_profile_list"]
                            user2_alts = r_profile_list[0].strip("`").split()
                            if alt1_id not in user2_alts: user2_alts.append(alt1_id)
                            r_profile_list[0] = alts_string(user2_alts)
                            user2_profile["r_profile_list"] = r_profile_list
                            userscol.replace_one(user2_query, user2_profile)
                            new_user = {"_id": alt1_id, "main": alt2_id}
                            try:
                                userscol.insert_one(new_user)
                            except DuplicateKeyError:
                                continue
                            await neru_logs_channel.send(
                                f"`{alt2_id}` and `{alt1_id}` have been added as alts.\n{formatted_proof} `{alt1_id}` has been added to the report on `{alt2_id}`")
                        else:
                            await neru_logs_channel.send(
                                f"`{alt1_id}` and `{alt2_id}` have been added as alts.\n{formatted_proof}")
                    else:  # both alts not logged
                        count += 1
                        alt1_info = {
                            "_id": alt1_id,
                            "alts": [alt2_id],
                            "proofs": [proof]
                        }
                        alt2_info = {
                            "_id": alt2_id,
                            "alts": [alt1_id],
                            "proofs": [proof]
                        }
                        #
                        altscol.insert_one(alt1_info)
                        altscol.insert_one(alt2_info)
                        #
                        user1_query = {"_id": alt1_id}
                        user1_profile = userscol.find_one(user1_query)
                        user2_query = {"_id": alt2_id}
                        user2_profile = userscol.find_one(user2_query)
                        if user1_profile and user2_profile and len(user1_profile) > 2 and len(
                                user2_profile) > 2:
                            await neru_logs_channel.send(
                                f"`{alt1_id}` and `{alt2_id}` have been added as alts.\n{formatted_proof} \n<@&{sr_role}> Separate reports detected, use /merge to merge them.")
                        elif user1_profile and len(user1_profile) > 2:  # user 1 reported, user 2 not reported
                            r_profile_list = user1_profile["r_profile_list"]
                            user1_alts = r_profile_list[0].strip("`").split()
                            if alt2_id not in user1_alts: user1_alts.append(alt2_id)
                            r_profile_list[0] = alts_string(user1_alts)
                            user1_profile["r_profile_list"] = r_profile_list
                            userscol.replace_one(user1_query, user1_profile)
                            new_user = {"_id": alt2_id, "main": alt1_id}
                            try:
                                userscol.insert_one(new_user)
                            except DuplicateKeyError:
                                continue
                            await neru_logs_channel.send(
                                f"`{alt1_id}` and `{alt2_id}` have been added as alts.\n{formatted_proof} `{alt2_id}` has been added to the report on `{alt1_id}`")
                        elif user2_profile and len(user2_profile) > 2:  # user 2 reported, user 1 not reported
                            r_profile_list = user2_profile["r_profile_list"]
                            user2_alts = r_profile_list[0].strip("`").split()
                            if alt1_id not in user2_alts: user2_alts.append(alt1_id)
                            r_profile_list[0] = alts_string(user2_alts)
                            user2_profile["r_profile_list"] = r_profile_list
                            userscol.replace_one(user2_query, user2_profile)
                            new_user = {"_id": alt1_id, "main": alt2_id}
                            try:
                                userscol.insert_one(new_user)
                            except DuplicateKeyError:
                                continue
                            await neru_logs_channel.send(
                                f"`{alt2_id}` and `{alt1_id}` have been added as alts.\n{formatted_proof} `{alt1_id}` has been added to the report on `{alt2_id}`")
                        else:
                            await neru_logs_channel.send(
                                f"`{alt1_id}` and `{alt2_id}` have been added as alts.\n{formatted_proof}")
        if count == 0:
            await interaction.followup.send("No new alt intrusions imported.", ephemeral=True)
        else:
            await interaction.followup.send(f"Success!", ephemeral=True)
        await msg.edit(content=f"Successfully imported {count} alt intrusions.")

@imports.command(name="all", description="Import Double Counter alt intrusions from all messages in this channel.")
async def import_all(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    neru_logs_channel = bot.get_channel(NERU_LOGS)
    channel = interaction.channel
    if channel:
        msg = await channel.send("Checking all messages in this channel for Double Counter alt intrusions...")
        count = 0
        async for message in channel.history(limit=None):
            alt1_id = None
            alt2_id = None
            if message.author.id == 703886990948565003:
                if message.embeds:
                    embed = message.embeds[0]
                    for field in embed.fields:
                        name = field.name.lower()
                        if name == "alt account":
                            m = re.search(r"\((\d{17,20})\)", field.value)
                            if m:
                                alt1_id = m.group(1)
                        elif name == "main account":
                            m = re.search(r"\((\d{17,20})\)", field.value)
                            if m:
                                alt2_id = m.group(1)
                pattern = r"\((\d{17,20})\)\s*-\s*Main account\s*:\s*<@\d{17,20}>\s*\((\d{17,20})\)"
                match = re.search(pattern, message.content)
                if match:
                    alt1_id, alt2_id = match.group(1), match.group(2)
                if not alt1_id or not alt2_id:
                    continue
                if alt1_id == alt2_id:
                    continue
                proof = f"{message.jump_url} ┈ dc"
                formatted_proof = proof
                try:
                    parts = message.jump_url.split('/')
                    guild_id = int(parts[-3])
                    guild = await bot.fetch_guild(guild_id)
                    if guild:
                        server_name = guild.name
                        formatted_proof = proof + f" ┈ {server_name}"
                except Exception:
                    pass
                alt1_query = {"_id": alt1_id}
                alt1_info = altscol.find_one(alt1_query)
                alt2_query = {"_id": alt2_id}
                alt2_info = altscol.find_one(alt2_query)
                if alt1_info:  # alt 1 logged
                    if alt2_info:  # alt 2 also logged
                        if alt1_id in alt2_info["alts"] and alt2_id in alt1_info[
                            "alts"]:  # check if already exists
                            continue
                        else:
                            count += 1
                            old_alts1 = alt1_info["alts"].copy()
                            old_alts2 = alt2_info["alts"].copy()
                            old_proofs1 = alt1_info["proofs"].copy()
                            old_proofs2 = alt2_info["proofs"].copy()
                            for alt in old_alts1:
                                alt_query = {"_id": alt}
                                alt_info = altscol.find_one(alt_query)
                                alt_info["alts"] += old_alts2
                                alt_info["alts"].append(alt2_id)
                                alt_info["proofs"] += old_proofs2
                                alt_info["proofs"].append(proof)
                                altscol.replace_one(alt_query, alt_info)
                            for alt in old_alts2:
                                alt_query = {"_id": alt}
                                alt_info = altscol.find_one(alt_query)
                                alt_info["alts"] += old_alts1
                                alt_info["alts"].append(alt1_id)
                                alt_info["proofs"] += old_proofs1
                                alt_info["proofs"].append(proof)
                                altscol.replace_one(alt_query, alt_info)
                            alt1_info["alts"] += old_alts2
                            alt1_info["alts"].append(alt2_id)
                            alt1_info["proofs"] += old_proofs2
                            alt1_info["proofs"].append(proof)
                            alt2_info["alts"] += old_alts1
                            alt2_info["alts"].append(alt1_id)
                            alt2_info["proofs"] += old_proofs1
                            alt2_info["proofs"].append(proof)
                            altscol.replace_one(alt1_query, alt1_info)
                            altscol.replace_one(alt2_query, alt2_info)
                            user1_query = {"_id": alt1_id}
                            user1_profile = userscol.find_one(user1_query)
                            user2_query = {"_id": alt2_id}
                            user2_profile = userscol.find_one(user2_query)
                            if user1_profile and user2_profile and len(user1_profile) > 2 and len(
                                    user2_profile) > 2:
                                await neru_logs_channel.send(
                                    f"`{alt1_id}` and `{alt2_id}` have been added as alts.\n{formatted_proof} \n<@&{sr_role}> Separate reports detected, use /merge to merge them.")
                            elif user1_profile and len(
                                    user1_profile) > 2:  # user 1 reported, user 2 not reported
                                r_profile_list = user1_profile["r_profile_list"]
                                user1_alts = r_profile_list[0].strip("`").split()
                                if alt2_id not in user1_alts: user1_alts.append(alt2_id)
                                r_profile_list[0] = alts_string(user1_alts)
                                user1_profile["r_profile_list"] = r_profile_list
                                userscol.replace_one(user1_query, user1_profile)
                                new_user = {"_id": alt2_id, "main": alt1_id}
                                try:
                                    userscol.insert_one(new_user)
                                except DuplicateKeyError:
                                    continue
                                await neru_logs_channel.send(
                                    f"`{alt1_id}` and `{alt2_id}` have been added as alts.\n{formatted_proof} `{alt2_id}` has been added to the report on `{alt1_id}`")
                            elif user2_profile and len(
                                    user2_profile) > 2:  # user 2 reported, user 1 not reported
                                r_profile_list = user2_profile["r_profile_list"]
                                user2_alts = r_profile_list[0].strip("`").split()
                                if alt1_id not in user2_alts: user2_alts.append(alt1_id)
                                r_profile_list[0] = alts_string(user2_alts)
                                user2_profile["r_profile_list"] = r_profile_list
                                userscol.replace_one(user2_query, user2_profile)
                                new_user = {"_id": alt1_id, "main": alt2_id}
                                try:
                                    userscol.insert_one(new_user)
                                except DuplicateKeyError:
                                    continue
                                await neru_logs_channel.send(
                                    f"`{alt2_id}` and `{alt1_id}` have been added as alts.\n{formatted_proof} `{alt1_id}` has been added to the report on `{alt2_id}`")
                            else:
                                await neru_logs_channel.send(
                                    f"`{alt1_id}` and `{alt2_id}` have been added as alts.\n{formatted_proof}")
                    else:  # alt 2 not logged
                        count += 1
                        old_alts1 = alt1_info["alts"].copy()
                        old_proofs1 = alt1_info["proofs"].copy()
                        alt2_info = {"_id": alt2_id, "alts": old_alts1, "proofs": []}
                        alt2_info["alts"].append(alt1_id)
                        alt2_info["proofs"] = old_proofs1
                        alt2_info["proofs"].append(proof)
                        for alt in old_alts1:
                            alt_query = {"_id": alt}
                            alt_info = altscol.find_one(alt_query)
                            alt_info["alts"].append(alt2_id)
                            alt_info["proofs"].append(proof)
                            altscol.replace_one(alt_query, alt_info)
                        alt1_info["alts"].append(alt2_id)
                        alt1_info["proofs"].append(proof)
                        altscol.replace_one(alt1_query, alt1_info)
                        altscol.insert_one(alt2_info)
                        user1_query = {"_id": alt1_id}
                        user1_profile = userscol.find_one(user1_query)
                        user2_query = {"_id": alt2_id}
                        user2_profile = userscol.find_one(user2_query)
                        if user1_profile and user2_profile and len(user1_profile) > 2 and len(
                                user2_profile) > 2:
                            await neru_logs_channel.send(
                                f"`{alt1_id}` and `{alt2_id}` have been added as alts.\n{formatted_proof} \n<@&{sr_role}> Separate reports detected, use /merge to merge them.")
                        elif user1_profile and len(user1_profile) > 2:  # user 1 reported, user 2 not reported
                            r_profile_list = user1_profile["r_profile_list"]
                            user1_alts = r_profile_list[0].strip("`").split()
                            if alt2_id not in user1_alts: user1_alts.append(alt2_id)
                            r_profile_list[0] = alts_string(user1_alts)
                            user1_profile["r_profile_list"] = r_profile_list
                            userscol.replace_one(user1_query, user1_profile)
                            new_user = {"_id": alt2_id, "main": alt1_id}
                            try:
                                userscol.insert_one(new_user)
                            except DuplicateKeyError:
                                continue
                            await neru_logs_channel.send(
                                f"`{alt1_id}` and `{alt2_id}` have been added as alts.\n{formatted_proof} `{alt2_id}` has been added to the report on `{alt1_id}`")
                        elif user2_profile and len(user2_profile) > 2:  # user 2 reported, user 1 not reported
                            r_profile_list = user2_profile["r_profile_list"]
                            user2_alts = r_profile_list[0].strip("`").split()
                            if alt1_id not in user2_alts: user2_alts.append(alt1_id)
                            r_profile_list[0] = alts_string(user2_alts)
                            user2_profile["r_profile_list"] = r_profile_list
                            userscol.replace_one(user2_query, user2_profile)
                            new_user = {"_id": alt1_id, "main": alt2_id}
                            try:
                                userscol.insert_one(new_user)
                            except DuplicateKeyError:
                                continue
                            await neru_logs_channel.send(
                                f"`{alt2_id}` and `{alt1_id}` have been added as alts.\n{formatted_proof} `{alt1_id}` has been added to the report on `{alt2_id}`")
                        else:
                            await neru_logs_channel.send(
                                f"`{alt1_id}` and `{alt2_id}` have been added as alts.\n{formatted_proof}")
                else:  # alt 1 not logged
                    if alt2_info:  # but alt 2 logged
                        count += 1
                        old_alts2 = alt2_info["alts"].copy()
                        old_proofs2 = alt2_info["proofs"].copy()
                        alt1_info = {"_id": alt1_id, "alts": old_alts2, "proofs": []}
                        alt1_info["alts"].append(alt2_id)
                        alt1_info["proofs"] = old_proofs2
                        alt1_info["proofs"].append(proof)
                        for alt in old_alts2:
                            alt_query = {"_id": alt}
                            alt_info = altscol.find_one(alt_query)
                            alt_info["alts"].append(alt1_id)
                            alt_info["proofs"].append(proof)
                            altscol.replace_one(alt_query, alt_info)
                        alt2_info["alts"].append(alt1_id)
                        alt2_info["proofs"].append(proof)
                        altscol.replace_one(alt2_query, alt2_info)
                        altscol.insert_one(alt1_info)
                        user1_query = {"_id": alt1_id}
                        user1_profile = userscol.find_one(user1_query)
                        user2_query = {"_id": alt2_id}
                        user2_profile = userscol.find_one(user2_query)
                        if user1_profile and user2_profile and len(user1_profile) > 2 and len(
                                user2_profile) > 2:
                            await neru_logs_channel.send(
                                f"`{alt1_id}` and `{alt2_id}` have been added as alts.\n{formatted_proof} \n<@&{sr_role}> Separate reports detected, use /merge to merge them.")
                        elif user1_profile and len(user1_profile) > 2:  # user 1 reported, user 2 not reported
                            r_profile_list = user1_profile["r_profile_list"]
                            user1_alts = r_profile_list[0].strip("`").split()
                            if alt2_id not in user1_alts: user1_alts.append(alt2_id)
                            r_profile_list[0] = alts_string(user1_alts)
                            user1_profile["r_profile_list"] = r_profile_list
                            userscol.replace_one(user1_query, user1_profile)
                            new_user = {"_id": alt2_id, "main": alt1_id}
                            try:
                                userscol.insert_one(new_user)
                            except DuplicateKeyError:
                                continue
                            await neru_logs_channel.send(
                                f"`{alt1_id}` and `{alt2_id}` have been added as alts.\n{formatted_proof} `{alt2_id}` has been added to the report on `{alt1_id}`")
                        elif user2_profile and len(user2_profile) > 2:  # user 2 reported, user 1 not reported
                            r_profile_list = user2_profile["r_profile_list"]
                            user2_alts = r_profile_list[0].strip("`").split()
                            if alt1_id not in user2_alts: user2_alts.append(alt1_id)
                            r_profile_list[0] = alts_string(user2_alts)
                            user2_profile["r_profile_list"] = r_profile_list
                            userscol.replace_one(user2_query, user2_profile)
                            new_user = {"_id": alt1_id, "main": alt2_id}
                            try:
                                userscol.insert_one(new_user)
                            except DuplicateKeyError:
                                continue
                            await neru_logs_channel.send(
                                f"`{alt2_id}` and `{alt1_id}` have been added as alts.\n{formatted_proof} `{alt1_id}` has been added to the report on `{alt2_id}`")
                        else:
                            await neru_logs_channel.send(
                                f"`{alt1_id}` and `{alt2_id}` have been added as alts.\n{formatted_proof}")
                    else:  # both alts not logged
                        count += 1
                        alt1_info = {
                            "_id": alt1_id,
                            "alts": [alt2_id],
                            "proofs": [proof]
                        }
                        alt2_info = {
                            "_id": alt2_id,
                            "alts": [alt1_id],
                            "proofs": [proof]
                        }
                        #
                        altscol.insert_one(alt1_info)
                        altscol.insert_one(alt2_info)
                        #
                        user1_query = {"_id": alt1_id}
                        user1_profile = userscol.find_one(user1_query)
                        user2_query = {"_id": alt2_id}
                        user2_profile = userscol.find_one(user2_query)
                        if user1_profile and user2_profile and len(user1_profile) > 2 and len(
                                user2_profile) > 2:
                            await neru_logs_channel.send(
                                f"`{alt1_id}` and `{alt2_id}` have been added as alts.\n{formatted_proof} \n<@&{sr_role}> Separate reports detected, use /merge to merge them.")
                        elif user1_profile and len(user1_profile) > 2:  # user 1 reported, user 2 not reported
                            r_profile_list = user1_profile["r_profile_list"]
                            user1_alts = r_profile_list[0].strip("`").split()
                            if alt2_id not in user1_alts: user1_alts.append(alt2_id)
                            r_profile_list[0] = alts_string(user1_alts)
                            user1_profile["r_profile_list"] = r_profile_list
                            userscol.replace_one(user1_query, user1_profile)
                            new_user = {"_id": alt2_id, "main": alt1_id}
                            try:
                                userscol.insert_one(new_user)
                            except DuplicateKeyError:
                                continue
                            await neru_logs_channel.send(
                                f"`{alt1_id}` and `{alt2_id}` have been added as alts.\n{formatted_proof} `{alt2_id}` has been added to the report on `{alt1_id}`")
                        elif user2_profile and len(user2_profile) > 2:  # user 2 reported, user 1 not reported
                            r_profile_list = user2_profile["r_profile_list"]
                            user2_alts = r_profile_list[0].strip("`").split()
                            if alt1_id not in user2_alts: user2_alts.append(alt1_id)
                            r_profile_list[0] = alts_string(user2_alts)
                            user2_profile["r_profile_list"] = r_profile_list
                            userscol.replace_one(user2_query, user2_profile)
                            new_user = {"_id": alt1_id, "main": alt2_id}
                            try:
                                userscol.insert_one(new_user)
                            except DuplicateKeyError:
                                continue
                            await neru_logs_channel.send(
                                f"`{alt2_id}` and `{alt1_id}` have been added as alts.\n{formatted_proof} `{alt1_id}` has been added to the report on `{alt2_id}`")
                        else:
                            await neru_logs_channel.send(
                                f"`{alt1_id}` and `{alt2_id}` have been added as alts.\n{formatted_proof}")
        if count == 0:
            await interaction.followup.send("No new alt intrusions imported.", ephemeral=True)
        else:
            await interaction.followup.send(f"Success!", ephemeral=True)
        await msg.edit(content=f"Successfully imported {count} alt intrusions.")

alts = app_commands.Group(name="alts", description="Add/remove alts.")
bot.tree.add_command(alts)

@alts.command(name="add", description="Adds a pair of users as alts.")
@app_commands.describe(user1="User 1", user2="User 2", image="Image")
@app_commands.checks.has_role(adm_role)
async def alts_add(interaction: discord.Interaction, user1: str, user2: str, image: discord.Attachment):
    await interaction.response.defer()
    if user1 == user2:
        return await interaction.followup.send(
            "You cannot add the user as alt of themselves.",
            ephemeral=True
        )
    async def upload_attachment(att):
        if not att:
            return None
        if not att.content_type.startswith("image/"):
            return None
        channel = bot.get_channel(PROOFS_CHANNEL)
        sent = await channel.send(file=await att.to_file())
        return sent.attachments[0].url if sent.attachments else None
    url = await upload_attachment(image)
    if not url:
        return await interaction.followup.send("Please provide a valid image.")
    proof = f"{url} ┈ added by {interaction.user.mention}"
    if user1.strip("<@>") != user2.strip("<@>"):
        try:
            alt1 = await bot.fetch_user(int(user1.strip("<@>")))
            alt2 = await bot.fetch_user(int(user2.strip("<@>")))
        except discord.NotFound:
            await interaction.followup.send(f"Please provide valid User IDs.", ephemeral=True)
        else:
            alt1_id = str(alt1.id)
            alt2_id = str(alt2.id)
            alt1_query = {"_id": alt1_id}
            alt1_info = altscol.find_one(alt1_query)
            alt2_query = {"_id": alt2_id}
            alt2_info = altscol.find_one(alt2_query)
            if alt1_info: # alt 1 logged
                if alt2_info: # alt 2 also logged
                    if alt1_id in alt2_info["alts"] and alt2_id in alt1_info["alts"]: # check if already exists
                        await interaction.followup.send(f"`{alt1_id}` and `{alt2_id}` have already been logged.", ephemeral=True)
                    else:
                        old_alts1 = alt1_info["alts"].copy()
                        old_alts2 = alt2_info["alts"].copy()
                        old_proofs1 = alt1_info["proofs"].copy()
                        old_proofs2 = alt2_info["proofs"].copy()
                        for alt in old_alts1:
                            alt_query = {"_id": alt}
                            alt_info = altscol.find_one(alt_query)
                            alt_info["alts"] += old_alts2
                            alt_info["alts"].append(alt2_id)
                            alt_info["proofs"] += old_proofs2
                            alt_info["proofs"].append(proof)
                            altscol.replace_one(alt_query, alt_info)
                        for alt in old_alts2:
                            alt_query = {"_id": alt}
                            alt_info = altscol.find_one(alt_query)
                            alt_info["alts"] += old_alts1
                            alt_info["alts"].append(alt1_id)
                            alt_info["proofs"] += old_proofs1
                            alt_info["proofs"].append(proof)
                            altscol.replace_one(alt_query, alt_info)
                        alt1_info["alts"] += old_alts2
                        alt1_info["alts"].append(alt2_id)
                        alt1_info["proofs"] += old_proofs2
                        alt1_info["proofs"].append(proof)
                        alt2_info["alts"] += old_alts1
                        alt2_info["alts"].append(alt1_id)
                        alt2_info["proofs"] += old_proofs1
                        alt2_info["proofs"].append(proof)
                        altscol.replace_one(alt1_query, alt1_info)
                        altscol.replace_one(alt2_query, alt2_info)
                        user1_query = {"_id": alt1_id}
                        user1_profile = userscol.find_one(user1_query)
                        user2_query = {"_id": alt2_id}
                        user2_profile = userscol.find_one(user2_query)
                        if user1_profile and user2_profile and len(user1_profile)>2 and len(user2_profile)>2:
                            await interaction.followup.send(
                                f"`{alt1_id}` and `{alt2_id}` have been added as alts. Separate reports detected, use /merge to merge them.")
                        elif user1_profile and len(user1_profile)>2: # user 1 reported, user 2 not reported
                            await interaction.followup.send(
                                f"`{alt1_id}` and `{alt2_id}` have been added as alts. `{alt1_id}` is reported but not `{alt2_id}`. Please update the report accordingly.")
                        elif user2_profile and len(user2_profile)>2: # user 2 reported, user 1 not reported
                            await interaction.followup.send(
                                f"`{alt1_id}` and `{alt2_id}` have been added as alts. `{alt2_id}` is reported but not `{alt1_id}`. Please update the report accordingly.")
                        else: # none reported
                            await interaction.followup.send(f"`{alt1_id}` and `{alt2_id}` have been added as alts.")

                else: # alt 2 not logged
                    old_alts1 = alt1_info["alts"].copy()
                    old_proofs1 = alt1_info["proofs"].copy()
                    alt2_info = {"_id": alt2_id, "alts": old_alts1, "proofs": []}
                    alt2_info["alts"].append(alt1_id)
                    alt2_info["proofs"] = old_proofs1
                    alt2_info["proofs"].append(proof)
                    for alt in old_alts1:
                        alt_query = {"_id": alt}
                        alt_info = altscol.find_one(alt_query)
                        if not alt_info:
                            continue
                        alt_info["alts"].append(alt2_id)
                        alt_info["proofs"].append(proof)
                        altscol.replace_one(alt_query, alt_info)
                    alt1_info["alts"].append(alt2_id)
                    alt1_info["proofs"].append(proof)
                    altscol.replace_one(alt1_query, alt1_info)
                    altscol.insert_one(alt2_info)
                    user1_query = {"_id": alt1_id}
                    user1_profile = userscol.find_one(user1_query)
                    user2_query = {"_id": alt2_id}
                    user2_profile = userscol.find_one(user2_query)
                    if user1_profile and user2_profile and len(user1_profile)>2 and len(user2_profile)>2:
                        await interaction.followup.send(
                            f"`{alt1_id}` and `{alt2_id}` have been added as alts. Separate reports detected, use /merge to merge them.")
                    elif user1_profile and len(user1_profile)>2:  # user 1 reported, user 2 not reported
                        await interaction.followup.send(
                            f"`{alt1_id}` and `{alt2_id}` have been added as alts. `{alt1_id}` is reported but not `{alt2_id}`. Please update the report accordingly.")
                    elif user2_profile and len(user2_profile)>2:  # user 2 reported, user 1 not reported
                        await interaction.followup.send(
                            f"`{alt1_id}` and `{alt2_id}` have been added as alts. `{alt2_id}` is reported but not `{alt1_id}`. Please update the report accordingly.")
                    else:  # none reported
                        await interaction.followup.send(f"`{alt1_id}` and `{alt2_id}` have been added as alts.")

            else: # alt 1 not logged
                if alt2_info: # but alt 2 logged
                    old_alts2 = alt2_info["alts"].copy()
                    old_proofs2 = alt2_info["proofs"].copy()
                    alt1_info = {"_id": alt1_id, "alts": old_alts2, "proofs": []}
                    alt1_info["alts"].append(alt2_id)
                    alt1_info["proofs"] = old_proofs2
                    alt1_info["proofs"].append(proof)
                    for alt in old_alts2:
                        alt_query = {"_id": alt}
                        alt_info = altscol.find_one(alt_query)
                        alt_info["alts"].append(alt1_id)
                        alt_info["proofs"].append(proof)
                        altscol.replace_one(alt_query, alt_info)
                    alt2_info["alts"].append(alt1_id)
                    alt2_info["proofs"].append(proof)
                    altscol.replace_one(alt2_query, alt2_info)
                    altscol.insert_one(alt1_info)
                    user1_query = {"_id": alt1_id}
                    user1_profile = userscol.find_one(user1_query)
                    user2_query = {"_id": alt2_id}
                    user2_profile = userscol.find_one(user2_query)
                    if user1_profile and user2_profile and len(user1_profile)>2 and len(user2_profile)>2:
                        await interaction.followup.send(
                            f"`{alt1_id}` and `{alt2_id}` have been added as alts. Separate reports detected, use /merge to merge them.")
                    elif user1_profile and len(user1_profile)>2:  # user 1 reported, user 2 not reported
                        await interaction.followup.send(
                            f"`{alt1_id}` and `{alt2_id}` have been added as alts. `{alt1_id}` is reported but not `{alt2_id}`. Please update the report accordingly.")
                    elif user2_profile and len(user2_profile)>2:  # user 2 reported, user 1 not reported
                        await interaction.followup.send(
                            f"`{alt1_id}` and `{alt2_id}` have been added as alts. `{alt2_id}` is reported but not `{alt1_id}`. Please update the report accordingly.")
                    else:  # none reported
                        await interaction.followup.send(f"`{alt1_id}` and `{alt2_id}` have been added as alts.")

                else: # both alts not logged
                    alt1_info = {
                        "_id": alt1_id,
                        "alts": [alt2_id],
                        "proofs": [proof]
                    }
                    alt2_info = {
                        "_id": alt2_id,
                        "alts": [alt1_id],
                        "proofs": [proof]
                    }
                    #
                    altscol.insert_one(alt1_info)
                    altscol.insert_one(alt2_info)
                    #
                    user1_query = {"_id": alt1_id}
                    user1_profile = userscol.find_one(user1_query)
                    user2_query = {"_id": alt2_id}
                    user2_profile = userscol.find_one(user2_query)
                    if user1_profile and user2_profile and len(user1_profile)>2 and len(user2_profile)>2:
                        await interaction.followup.send(
                            f"`{alt1_id}` and `{alt2_id}` have been added as alts. Separate reports detected, use /merge to merge them.")
                    elif user1_profile and len(user1_profile)>2:  # user 1 reported, user 2 not reported
                        await interaction.followup.send(
                            f"`{alt1_id}` and `{alt2_id}` have been added as alts. `{alt1_id}` is reported but not `{alt2_id}`. Please update the report accordingly.")
                    elif user2_profile and len(user2_profile)>2:  # user 2 reported, user 1 not reported
                        await interaction.followup.send(
                            f"`{alt1_id}` and `{alt2_id}` have been added as alts. `{alt2_id}` is reported but not `{alt1_id}`. Please update the report accordingly.")
                    else:  # none reported
                        await interaction.followup.send(f"`{alt1_id}` and `{alt2_id}` have been added as alts.")

@alts.command(name="remove", description="Removes a pair of users as alts.")
@app_commands.describe(user1="User 1", user2="User 2")
@app_commands.checks.has_role(adm_role)
async def alts_remove(interaction: discord.Interaction, user1: str, user2: str):
    await interaction.response.defer()
    def parse_id(u: str):
        return u.strip("<@!>")
    alt1_id = parse_id(user1)
    alt2_id = parse_id(user2)
    if alt1_id == alt2_id:
        return await interaction.followup.send(
            "You cannot remove the user as alt of themselves.",
            ephemeral=True
        )
    doc1 = altscol.find_one({"_id": alt1_id})
    doc2 = altscol.find_one({"_id": alt2_id})
    if not doc1 and not doc2:
        return await interaction.followup.send(
            "Neither user is logged as an alt.",
            ephemeral=True
        )
    def remove_pair(doc, target_id):
        if not doc:
            return doc
        alts = doc.get("alts", [])
        proofs = doc.get("proofs", [])
        new_alts = []
        new_proofs = []
        for i in range(len(alts)):
            if alts[i] != target_id:
                new_alts.append(alts[i])
                if i < len(proofs):
                    new_proofs.append(proofs[i])
        doc["alts"] = new_alts
        doc["proofs"] = new_proofs
        return doc
    if doc1:
        doc1 = remove_pair(doc1, alt2_id)
        altscol.replace_one({"_id": alt1_id}, doc1)
    if doc2:
        doc2 = remove_pair(doc2, alt1_id)
        altscol.replace_one({"_id": alt2_id}, doc2)
    return await interaction.followup.send(
        f"`{alt1_id}` and `{alt2_id}` have been removed as alts."
    )

@bot.command()
async def sync(ctx: commands.Context):
    await bot.tree.sync()
    alts_count = altscol.count_documents({})
    await bot.change_presence(
        status=discord.Status.idle,
        activity=discord.Activity(type=discord.ActivityType.watching, name=f"{alts_count} alts.")
    )

bot.run(TOKEN)