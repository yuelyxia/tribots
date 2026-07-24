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

from collections import OrderedDict

from typing import Optional, Literal

TOKEN = os.getenv("TOKEN")
CLIENT = os.getenv("CLIENT")

# mongodb info
client = pymongo.MongoClient(CLIENT)
db = client["database"]
userscol = db["users"]
altscol = db["alts"]
invitescol = db["invites"]

# tri roles info
o5_role = 1372426616671834234
staff_role = 1373803879623430268
ticket_ping = 1449382692671193294
sr_role = 1375254710952661102
adm_role = 1375276457890287748

TRI_Archive = 1371673839695826974

members_role = 1373806415256223895
unverified_role = 1373806500396535889

NERU_LOGS = 1460858907491569816
PROOFS_CHANNEL = 1455055877034868769

PROOF_CACHE_SIZE = 1000
proof_cache = OrderedDict()

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
    profile = discord.Embed(colour=0xffffff, title=user.display_name.replace('||', '\\|\\|').replace('_', '\\_'))
    profile.description = f"`{user.id}`\n{user.mention}\n`{user.name}`\n\n"
    profile.description += f"<:tri_whitecross:1462774085737119828>　No alts logged for this user."
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
@tasks.loop(hours=24)
async def clear_proof_cache():
    proof_cache.clear()
    print("Proof cache cleared!")

@bot.event
async def on_ready():
    if not update_alts_count.is_running():
        update_alts_count.start()
    if not clear_proof_cache.is_running():
        clear_proof_cache.start()

async def autoverify(user_id: int):
    guild = bot.get_guild(TRI_Archive)
    if not guild:
        try:
            guild = await bot.fetch_guild(TRI_Archive)
        except (discord.NotFound, discord.HTTPException):
            return
    try:
        member = guild.get_member(user_id) or await guild.fetch_member(user_id)
    except (discord.NotFound, discord.HTTPException):
        return
    member_r = guild.get_role(members_role)
    unverified_r = guild.get_role(unverified_role)
    if member_r and member_r not in member.roles:
        try:
            await member.add_roles(member_r, reason="Alt account logged.")
        except discord.Forbidden:
            pass
    if unverified_r and unverified_r in member.roles:
        try:
            await member.remove_roles(unverified_r, reason="Alt account logged.")
        except discord.Forbidden:
            pass

@bot.event
async def on_message(message: discord.Message):
    neru_logs_channel = bot.get_channel(NERU_LOGS)
    if message.author.id == 703886990948565003:
        alt1_id = None
        alt2_id = None
        pattern1 = r"\((\d{17,20})\)\s*-\s*Main account\s*:\s*.*?\((\d{17,20})\)"
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
            if alt1_id and alt2_id and alt1_id != alt2_id:
                proof = f"{message.jump_url} – dc"
                formatted_proof = proof
                guild_id = None
                try:
                    parts = message.jump_url.split('/')
                    guild_id = int(parts[-3])
                    guild = await bot.fetch_guild(guild_id)
                    if guild:
                        server_name = guild.name
                        formatted_proof = proof + f" – {server_name}"
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
                                if not alt_info:
                                    continue
                                alt_info["alts"] += old_alts2
                                alt_info["alts"].append(alt2_id)
                                alt_info["proofs"] += old_proofs2
                                alt_info["proofs"].append(proof)
                                altscol.replace_one(alt_query, alt_info)
                            for alt in old_alts2:
                                alt_query = {"_id": alt}
                                alt_info = altscol.find_one(alt_query)
                                if not alt_info:
                                    continue
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
                                    f"`{alt1_id}` and `{alt2_id}` have been added as alts.\n{formatted_proof} \n`{alt2_id}` has been added to the report on `{alt1_id}`")
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
                                    f"`{alt2_id}` and `{alt1_id}` have been added as alts.\n{formatted_proof} \n`{alt1_id}` has been added to the report on `{alt2_id}`")
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
                                f"`{alt1_id}` and `{alt2_id}` have been added as alts.\n{formatted_proof} \n`{alt2_id}` has been added to the report on `{alt1_id}`")
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
                                f"`{alt2_id}` and `{alt1_id}` have been added as alts.\n{formatted_proof} \n`{alt1_id}` has been added to the report on `{alt2_id}`")
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
                            if not alt_info:
                                continue
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
                                f"`{alt1_id}` and `{alt2_id}` have been added as alts.\n{formatted_proof} \n`{alt2_id}` has been added to the report on `{alt1_id}`")
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
                                f"`{alt2_id}` and `{alt1_id}` have been added as alts.\n{formatted_proof} \n`{alt1_id}` has been added to the report on `{alt2_id}`")
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
                                f"`{alt1_id}` and `{alt2_id}` have been added as alts.\n{formatted_proof} \n`{alt2_id}` has been added to the report on `{alt1_id}`")
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
                                f"`{alt2_id}` and `{alt1_id}` have been added as alts.\n{formatted_proof} \n`{alt1_id}` has been added to the report on `{alt2_id}`")
                        else:
                            await neru_logs_channel.send(
                                f"`{alt1_id}` and `{alt2_id}` have been added as alts.\n{formatted_proof}")
                if guild_id == TRI_Archive or (message.guild and message.guild.id == TRI_Archive):
                    await autoverify(int(alt1_id))

    await bot.process_commands(message)

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

@bot.command(name="ma", help="Checks a list of users (max 100) for logged alts, leave a space between users.")
async def ma(ctx, *, to_check: str = None):
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
        f"_Checking **{len(valid_users)}** users for alts..._")
    if not valid_users:
        await status_message.delete()
        if invalid_users:
            await ctx.send(f"Invalid: {' '.join([f'`{u}`' for u in invalid_users])}")
        return await ctx.reply("No valid user IDs provided.")

    processed_ids = set()
    message_batches = []
    current_content = []
    current_embeds = []
    current_embed_chars = 0

    for user in valid_users:
        current_id = str(user.id)

        if current_id in processed_ids:
            continue
        processed_ids.add(current_id)

        alts_info = altscol.find_one({"_id": current_id})

        if alts_info and alts_info.get("alts"):
            alts_list = alts_info.get("alts", [])
            alts_count = len(alts_list)
            raw_ids = " ".join(alt for alt in alts_list)
            current_content.append(
                f"<a:tri_whitealert:1496542298908000257> **`{current_id}` has {alts_count} logged alt(s).**")
            embed = discord.Embed(colour=0xffffff, title=user.display_name.replace('||', '\\|\\|').replace('_', '\\_'))
            embed.description = f"`{user.id}`\n{user.mention}\n`{user.name}`\n\n<a:tri_whitealert:1496542298908000257> **Alt(s)**\n`{raw_ids}`"
            embed_chars = len(embed.title or "") + len(embed.description or "")
            if len(current_embeds) == 10 or current_embed_chars + embed_chars > 6000:
                message_batches.append(("\n".join(current_content), current_embeds))
                current_content = []
                current_embeds = []
                current_embed_chars = 0
            current_embeds.append(embed)
            current_embed_chars += embed_chars
        else:
            current_content.append(f"<:tri_whitedot:1462907474947342567> `{current_id}` has no logged alts.")
            embed = discord.Embed(colour=0xffffff)
            embed.description = f"<:tri_whitecross:1462774085737119828>　No alts logged for `{current_id}`."
            embed_chars = len(embed.description)
            if len(current_embeds) == 10 or current_embed_chars + embed_chars > 6000:
                message_batches.append(("\n".join(current_content), current_embeds))
                current_content = []
                current_embeds = []
                current_embed_chars = 0
            current_embeds.append(embed)
            current_embed_chars += embed_chars

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


@bot.command(name="a", help="Checks a user for logged alts.")
async def a(ctx, *, to_check: str = None):
    status_message = await ctx.reply("_Checking user for alts..._")
    if to_check is None:
        user = ctx.author
    else:
        user, _ = await fetch_worker(to_check)
        if not user:
            await ctx.send("Please provide a valid user ID.")
            return
    user_id = str(user.id)
    alts_info = altscol.find_one({"_id": user_id})
    if not alts_info:
        await status_message.edit(content=None, embed=default_no_alts(user))
        return
    alts = alts_info.get("alts", [])
    proofs = alts_info.get("proofs", [])
    chosen_lines = []
    for i, alt in enumerate(alts):
        base_proof = proofs[i] if i < len(proofs) else "No proof"
        if isinstance(base_proof, dict):
            key = (base_proof["channel_id"], base_proof["message_id"])

            cached = proof_cache.get(key)
            if cached is not None:
                proof_cache.move_to_end(key)
                base_proof = cached
            else:
                try:
                    channel = bot.get_channel(base_proof["channel_id"])
                    if channel is None:
                        channel = await bot.fetch_channel(base_proof["channel_id"])
                    message = await channel.fetch_message(base_proof["message_id"])
                    if message.attachments:
                        base_proof = f"{message.attachments[0].proxy_url} – added by <@{base_proof['added_by']}>"
                    else:
                        base_proof = f"Proof unavailable – added by <@{base_proof['added_by']}>"
                except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                    base_proof = f"Proof unavailable – added by <@{base_proof['added_by']}>"
                proof_cache[key] = base_proof
                proof_cache.move_to_end(key)
                if len(proof_cache) > PROOF_CACHE_SIZE:
                    proof_cache.popitem(last=False)
        proof_with_server = base_proof
        if isinstance(base_proof, str) and base_proof.endswith(" – dc"):
            jump_url = base_proof[:-5]
            parts = jump_url.split("/")
            try:
                guild_id = int(parts[-3])
                guild = bot.get_guild(guild_id)
                server_name = None
                if not guild:
                    try:
                        guild = await bot.fetch_guild(guild_id)
                    except (discord.NotFound, discord.HTTPException, discord.Forbidden):
                        guild = None

                if guild:
                    server_name = guild.name
                else:
                    server_doc = invitescol.find_one({"_id": str(guild_id)})
                    if server_doc and server_doc.get("invites"):
                        for inv_entry in server_doc["invites"]:
                            code = inv_entry if isinstance(inv_entry, str) else inv_entry.get("code")
                            if not code:
                                continue
                            try:
                                invite = await bot.fetch_invite(code)
                                if invite and invite.guild:
                                    server_name = invite.guild.name
                                    break
                            except (discord.NotFound, discord.HTTPException, discord.Forbidden):
                                continue
                if server_name:
                    proof_with_server = f"[{server_name}]({jump_url}) – dc"
            except Exception:
                pass
        if isinstance(base_proof, str) and base_proof.endswith(">"):
            parts = base_proof.split(" – ")
            proof_with_server = f"[image]({parts[0]}) – {parts[1]}"
        chosen_lines.append(f"ㆍ `{alt}` – {proof_with_server}")
    LIMIT = 3800
    header = f"`{user.id}`\n{user.mention}\n`{user.name}`\n\n<a:tri_whitealert:1496542298908000257> **Alt(s)**\n"
    embeds = []
    chunk = []
    for line in chosen_lines:
        test_chunk = "\n".join(chunk + [line])
        if len(header) + len(test_chunk) > LIMIT:
            embed = discord.Embed(colour=0xffffff, title=user.display_name.replace('||', '\\|\\|').replace('_', '\\_').replace("_", "\\_"))
            embed.description = header + "\n".join(chunk)
            embeds.append(embed)
            chunk = [line]
        else:
            chunk.append(line)
    if chunk:
        embed = discord.Embed(colour=0xffffff, title=user.display_name.replace('||', '\\|\\|').replace('_', '\\_'))
        embed.description = header + "\n".join(chunk)
        embeds.append(embed)
    for idx, embed in enumerate(embeds):
        if idx == 0:
            if len(embeds) == 1:
                await status_message.edit(content=None, embed=embed, view=RelatedIDsView(user_id, alts))
            else:
                await status_message.edit(content=None, embed=embed)
        else:
            if idx == len(embeds) - 1:
                await ctx.send(embed=embed, view=RelatedIDsView(user_id, alts))
            else:
                await ctx.send(embed=embed)

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
                pattern = r"\((\d{17,20})\)\s*-\s*Main account\s*:\s*.*?\((\d{17,20})\)"
                match = re.search(pattern, message.content)
                if match:
                    alt1_id, alt2_id = match.group(1), match.group(2)
                if not alt1_id or not alt2_id:
                    continue
                if alt1_id == alt2_id:
                    continue
                proof = f"{message.jump_url} – dc"
                formatted_proof = proof
                try:
                    parts = message.jump_url.split('/')
                    guild_id = int(parts[-3])
                    guild = await bot.fetch_guild(guild_id)
                    if guild:
                        server_name = guild.name
                        formatted_proof = proof + f" – {server_name}"
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
                                if not alt_info:
                                    continue
                                alt_info["alts"] += old_alts2
                                alt_info["alts"].append(alt2_id)
                                alt_info["proofs"] += old_proofs2
                                alt_info["proofs"].append(proof)
                                altscol.replace_one(alt_query, alt_info)
                            for alt in old_alts2:
                                alt_query = {"_id": alt}
                                alt_info = altscol.find_one(alt_query)
                                if not alt_info:
                                    continue
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
                                    f"`{alt1_id}` and `{alt2_id}` have been added as alts.\n{formatted_proof} \n`{alt2_id}` has been added to the report on `{alt1_id}`")
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
                                    f"`{alt2_id}` and `{alt1_id}` have been added as alts.\n{formatted_proof} \n`{alt1_id}` has been added to the report on `{alt2_id}`")
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
                                f"`{alt1_id}` and `{alt2_id}` have been added as alts.\n{formatted_proof} \n`{alt2_id}` has been added to the report on `{alt1_id}`")
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
                                f"`{alt2_id}` and `{alt1_id}` have been added as alts.\n{formatted_proof} \n`{alt1_id}` has been added to the report on `{alt2_id}`")
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
                            if not alt_info:
                                continue
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
                                f"`{alt1_id}` and `{alt2_id}` have been added as alts.\n{formatted_proof} \n`{alt2_id}` has been added to the report on `{alt1_id}`")
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
                                f"`{alt2_id}` and `{alt1_id}` have been added as alts.\n{formatted_proof} \n`{alt1_id}` has been added to the report on `{alt2_id}`")
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
                                f"`{alt1_id}` and `{alt2_id}` have been added as alts.\n{formatted_proof} \n`{alt2_id}` has been added to the report on `{alt1_id}`")
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
                                f"`{alt2_id}` and `{alt1_id}` have been added as alts.\n{formatted_proof} \n`{alt1_id}` has been added to the report on `{alt2_id}`")
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
                pattern = r"\((\d{17,20})\)\s*-\s*Main account\s*:\s*.*?\((\d{17,20})\)"
                match = re.search(pattern, message.content)
                if match:
                    alt1_id, alt2_id = match.group(1), match.group(2)
                if not alt1_id or not alt2_id:
                    continue
                if alt1_id == alt2_id:
                    continue
                proof = f"{message.jump_url} – dc"
                formatted_proof = proof
                try:
                    parts = message.jump_url.split('/')
                    guild_id = int(parts[-3])
                    guild = await bot.fetch_guild(guild_id)
                    if guild:
                        server_name = guild.name
                        formatted_proof = proof + f" – {server_name}"
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
                                if not alt_info:
                                    continue
                                alt_info["alts"] += old_alts2
                                alt_info["alts"].append(alt2_id)
                                alt_info["proofs"] += old_proofs2
                                alt_info["proofs"].append(proof)
                                altscol.replace_one(alt_query, alt_info)
                            for alt in old_alts2:
                                alt_query = {"_id": alt}
                                alt_info = altscol.find_one(alt_query)
                                if not alt_info:
                                    continue
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
                                    f"`{alt1_id}` and `{alt2_id}` have been added as alts.\n{formatted_proof} \n`{alt2_id}` has been added to the report on `{alt1_id}`")
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
                                    f"`{alt2_id}` and `{alt1_id}` have been added as alts.\n{formatted_proof} \n`{alt1_id}` has been added to the report on `{alt2_id}`")
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
                                f"`{alt1_id}` and `{alt2_id}` have been added as alts.\n{formatted_proof} \n`{alt2_id}` has been added to the report on `{alt1_id}`")
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
                                f"`{alt2_id}` and `{alt1_id}` have been added as alts.\n{formatted_proof} \n`{alt1_id}` has been added to the report on `{alt2_id}`")
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
                            if not alt_info:
                                continue
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
                                f"`{alt1_id}` and `{alt2_id}` have been added as alts.\n{formatted_proof} \n`{alt2_id}` has been added to the report on `{alt1_id}`")
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
                                f"`{alt2_id}` and `{alt1_id}` have been added as alts.\n{formatted_proof} \n`{alt1_id}` has been added to the report on `{alt2_id}`")
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
                                f"`{alt1_id}` and `{alt2_id}` have been added as alts.\n{formatted_proof} \n`{alt2_id}` has been added to the report on `{alt1_id}`")
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
                                f"`{alt2_id}` and `{alt1_id}` have been added as alts.\n{formatted_proof} \n`{alt1_id}` has been added to the report on `{alt2_id}`")
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
    if interaction.channel.id != NERU_LOGS:
        return await interaction.followup.send("This command can only be used in the NERU logs channel.", ephemeral=True)
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
        return sent.id if sent.attachments else None
    sent_id = await upload_attachment(image)
    if not sent_id:
        return await interaction.followup.send("Please provide a valid image.", ephemeral=True)
    proof = {
        "channel_id": PROOFS_CHANNEL,
        "message_id": sent_id,
        "added_by": interaction.user.id
    }
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
                        return await interaction.followup.send(f"`{alt1_id}` and `{alt2_id}` have already been logged.", ephemeral=True)
                    else:
                        old_alts1 = alt1_info["alts"].copy()
                        old_alts2 = alt2_info["alts"].copy()
                        old_proofs1 = alt1_info["proofs"].copy()
                        old_proofs2 = alt2_info["proofs"].copy()
                        for alt in old_alts1:
                            alt_query = {"_id": alt}
                            alt_info = altscol.find_one(alt_query)
                            if not alt_info:
                                continue
                            alt_info["alts"] += old_alts2
                            alt_info["alts"].append(alt2_id)
                            alt_info["proofs"] += old_proofs2
                            alt_info["proofs"].append(proof)
                            altscol.replace_one(alt_query, alt_info)
                        for alt in old_alts2:
                            alt_query = {"_id": alt}
                            alt_info = altscol.find_one(alt_query)
                            if not alt_info:
                                continue
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
                        if user1_profile and user2_profile and len(user1_profile or "")>2 and len(user2_profile or "")>2:
                            await interaction.followup.send(
                                f"`{alt1_id}` and `{alt2_id}` have been added as alts. Separate reports detected, use /merge to merge them.")
                        elif user1_profile and len(user1_profile)>2 and not user2_profile: # user 1 reported, user 2 not reported
                            await interaction.followup.send(
                                f"`{alt1_id}` and `{alt2_id}` have been added as alts. `{alt1_id}` is reported but not `{alt2_id}`. Please update the report accordingly.")
                        elif user2_profile and len(user2_profile)>2 and not user1_profile: # user 2 reported, user 1 not reported
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
                    if user1_profile and user2_profile and len(user1_profile or "")>2 and len(user2_profile or "")>2:
                        await interaction.followup.send(
                            f"`{alt1_id}` and `{alt2_id}` have been added as alts. Separate reports detected, use /merge to merge them.")
                    elif user1_profile and len(user1_profile)>2 and not user2_profile:  # user 1 reported, user 2 not reported
                        await interaction.followup.send(
                            f"`{alt1_id}` and `{alt2_id}` have been added as alts. `{alt1_id}` is reported but not `{alt2_id}`. Please update the report accordingly.")
                    elif user2_profile and len(user2_profile)>2 and not user1_profile:  # user 2 reported, user 1 not reported
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
                        if not alt_info:
                            continue
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
                    if user1_profile and user2_profile and len(user1_profile or "")>2 and len(user2_profile or "")>2:
                        await interaction.followup.send(
                            f"`{alt1_id}` and `{alt2_id}` have been added as alts. Separate reports detected, use /merge to merge them.")
                    elif user1_profile and len(user1_profile)>2 and not user2_profile:  # user 1 reported, user 2 not reported
                        await interaction.followup.send(
                            f"`{alt1_id}` and `{alt2_id}` have been added as alts. `{alt1_id}` is reported but not `{alt2_id}`. Please update the report accordingly.")
                    elif user2_profile and len(user2_profile)>2 and not user1_profile:  # user 2 reported, user 1 not reported
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
                    if user1_profile and user2_profile and len(user1_profile or "")>2 and len(user2_profile or "")>2:
                        await interaction.followup.send(
                            f"`{alt1_id}` and `{alt2_id}` have been added as alts. Separate reports detected, use /merge to merge them.")
                    elif user1_profile and len(user1_profile)>2 and not user2_profile:  # user 1 reported, user 2 not reported
                        await interaction.followup.send(
                            f"`{alt1_id}` and `{alt2_id}` have been added as alts. `{alt1_id}` is reported but not `{alt2_id}`. Please update the report accordingly.")
                    elif user2_profile and len(user2_profile)>2 and not user1_profile:  # user 2 reported, user 1 not reported
                        await interaction.followup.send(
                            f"`{alt1_id}` and `{alt2_id}` have been added as alts. `{alt2_id}` is reported but not `{alt1_id}`. Please update the report accordingly.")
                    else:  # none reported
                        await interaction.followup.send(f"`{alt1_id}` and `{alt2_id}` have been added as alts.")

@alts.command(name="massadd", description="Adds multiple alts to a main user.")
@app_commands.describe(main="Main", alts="Alts, leave a space between IDs.", image="Image")
@app_commands.checks.has_role(adm_role)
async def alts_massadd(interaction: discord.Interaction, main: str, alts: str, image: discord.Attachment):
    await interaction.response.defer(ephemeral=True)
    if interaction.channel.id != NERU_LOGS:
        return await interaction.followup.send("This command can only be used in the NERU logs channel.",
                                               ephemeral=True)
    neru_logs_channel = bot.get_channel(NERU_LOGS)
    def clean_id(u: str):
        return u.strip("<@!>")
    main_id = clean_id(main)
    raw_alts = alts.split()

    async def upload_attachment(att):
        if not att:
            return None
        if not att.content_type.startswith("image/"):
            return None
        channel = bot.get_channel(PROOFS_CHANNEL)
        sent = await channel.send(file=await att.to_file())
        return sent.id if sent.attachments else None

    sent_id = await upload_attachment(image)
    if not sent_id:
        return await interaction.followup.send("Please provide a valid image.", ephemeral=True)
    proof = {
        "channel_id": PROOFS_CHANNEL,
        "message_id": sent_id,
        "added_by": interaction.user.id
    }
    if not main_id.isdigit():
        return await interaction.followup.send("Invalid main ID.", ephemeral=True)
    try:
        await bot.fetch_user(int(main_id))
    except discord.NotFound:
        return await interaction.followup.send("Main user not found.", ephemeral=True)

    valid_alts = []
    invalid_alts = []
    for uid in raw_alts:
        cid = clean_id(uid)
        if not cid.isdigit():
            invalid_alts.append(uid)
            continue
        try:
            await bot.fetch_user(int(cid))
            if cid != main_id and cid not in valid_alts:
                valid_alts.append(cid)
        except discord.NotFound:
            invalid_alts.append(cid)
    if not valid_alts:
        return await interaction.followup.send("No valid alt IDs provided.", ephemeral=True)

    linked = 0
    for alt_id in valid_alts:
        if alt_id == main_id:
            continue
        alt1_id = main_id
        alt2_id = alt_id
        alt1_query = {"_id": alt1_id}
        alt1_info = altscol.find_one(alt1_query)
        alt2_query = {"_id": alt2_id}
        alt2_info = altscol.find_one(alt2_query)
        if alt1_info:  # alt 1 logged
            if alt2_info:  # alt 2 also logged
                if alt1_id in alt2_info["alts"] and alt2_id in alt1_info["alts"]:  # check if already exists
                    await neru_logs_channel.send(f"`{alt1_id}` and `{alt2_id}` have already been logged.")
                    continue
                else:
                    old_alts1 = alt1_info["alts"].copy()
                    old_alts2 = alt2_info["alts"].copy()
                    old_proofs1 = alt1_info["proofs"].copy()
                    old_proofs2 = alt2_info["proofs"].copy()
                    for alt in old_alts1:
                        alt_query = {"_id": alt}
                        alt_info = altscol.find_one(alt_query)
                        if not alt_info:
                            continue
                        alt_info["alts"] += old_alts2
                        alt_info["alts"].append(alt2_id)
                        alt_info["proofs"] += old_proofs2
                        alt_info["proofs"].append(proof)
                        altscol.replace_one(alt_query, alt_info)
                    for alt in old_alts2:
                        alt_query = {"_id": alt}
                        alt_info = altscol.find_one(alt_query)
                        if not alt_info:
                            continue
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
                    if user1_profile and user2_profile and len(user1_profile or "") > 2 and len(
                            user2_profile or "") > 2:
                        await neru_logs_channel.send(
                            f"`{alt1_id}` and `{alt2_id}` have been added as alts. Separate reports detected, use /merge to merge them.")
                    elif user1_profile and len(
                            user1_profile) > 2 and not user2_profile:  # user 1 reported, user 2 not reported
                        await neru_logs_channel.send(
                            f"`{alt1_id}` and `{alt2_id}` have been added as alts. `{alt1_id}` is reported but not `{alt2_id}`. Please update the report accordingly.")
                    elif user2_profile and len(
                            user2_profile) > 2 and not user1_profile:  # user 2 reported, user 1 not reported
                        await neru_logs_channel.send(
                            f"`{alt1_id}` and `{alt2_id}` have been added as alts. `{alt2_id}` is reported but not `{alt1_id}`. Please update the report accordingly.")
                    else:  # none reported
                        await neru_logs_channel.send(f"`{alt1_id}` and `{alt2_id}` have been added as alts.")
                    linked += 1
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
                if user1_profile and user2_profile and len(user1_profile or "") > 2 and len(user2_profile or "") > 2:
                    await neru_logs_channel.send(
                        f"`{alt1_id}` and `{alt2_id}` have been added as alts. Separate reports detected, use /merge to merge them.")
                elif user1_profile and len(
                        user1_profile) > 2 and not user2_profile:  # user 1 reported, user 2 not reported
                    await neru_logs_channel.send(
                        f"`{alt1_id}` and `{alt2_id}` have been added as alts. `{alt1_id}` is reported but not `{alt2_id}`. Please update the report accordingly.")
                elif user2_profile and len(
                        user2_profile) > 2 and not user1_profile:  # user 2 reported, user 1 not reported
                    await neru_logs_channel.send(
                        f"`{alt1_id}` and `{alt2_id}` have been added as alts. `{alt2_id}` is reported but not `{alt1_id}`. Please update the report accordingly.")
                else:  # none reported
                    await neru_logs_channel.send(f"`{alt1_id}` and `{alt2_id}` have been added as alts.")
                linked += 1
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
                    if not alt_info:
                        continue
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
                if user1_profile and user2_profile and len(user1_profile or "") > 2 and len(user2_profile or "") > 2:
                    await neru_logs_channel.send(
                        f"`{alt1_id}` and `{alt2_id}` have been added as alts. Separate reports detected, use /merge to merge them.")
                elif user1_profile and len(
                        user1_profile) > 2 and not user2_profile:  # user 1 reported, user 2 not reported
                    await neru_logs_channel.send(
                        f"`{alt1_id}` and `{alt2_id}` have been added as alts. `{alt1_id}` is reported but not `{alt2_id}`. Please update the report accordingly.")
                elif user2_profile and len(
                        user2_profile) > 2 and not user1_profile:  # user 2 reported, user 1 not reported
                    await neru_logs_channel.send(
                        f"`{alt1_id}` and `{alt2_id}` have been added as alts. `{alt2_id}` is reported but not `{alt1_id}`. Please update the report accordingly.")
                else:  # none reported
                    await neru_logs_channel.send(f"`{alt1_id}` and `{alt2_id}` have been added as alts.")
                linked += 1
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
                if user1_profile and user2_profile and len(user1_profile or "") > 2 and len(user2_profile or "") > 2:
                    await neru_logs_channel.send(
                        f"`{alt1_id}` and `{alt2_id}` have been added as alts. Separate reports detected, use /merge to merge them.")
                elif user1_profile and len(
                        user1_profile) > 2 and not user2_profile:  # user 1 reported, user 2 not reported
                    await neru_logs_channel.send(
                        f"`{alt1_id}` and `{alt2_id}` have been added as alts. `{alt1_id}` is reported but not `{alt2_id}`. Please update the report accordingly.")
                elif user2_profile and len(
                        user2_profile) > 2 and not user1_profile:  # user 2 reported, user 1 not reported
                    await neru_logs_channel.send(
                        f"`{alt1_id}` and `{alt2_id}` have been added as alts. `{alt2_id}` is reported but not `{alt1_id}`. Please update the report accordingly.")
                else:  # none reported
                    await neru_logs_channel.send(f"`{alt1_id}` and `{alt2_id}` have been added as alts.")
                linked += 1
    await interaction.followup.send(
        f"Mass add successful.\nLinked **{linked}** alts to main `{main_id}`.\nInvalid: {f"`{' '.join(invalid_alts)}`" if invalid_alts else "None"}",
        ephemeral=True
    )

@alts.command(name="remove", description="Removes a pair of users as alts.")
@app_commands.describe(user1="User 1", user2="User 2")
@app_commands.checks.has_role(adm_role)
async def alts_remove(interaction: discord.Interaction, user1: str, user2: str):
    await interaction.response.defer()
    if interaction.channel.id != NERU_LOGS:
        return await interaction.followup.send("This command can only be used in the NERU logs channel.", ephemeral=True)
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