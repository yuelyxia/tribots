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
altscol = db["alts"]

# tri roles info
o5_role = 1372426616671834234
staff_role = 1373803879623430268
ticket_ping = 1449382692671193294
sr_role = 1375254710952661102
adm_role = 1375276457890287748

NERU_LOGS = 1460858907491569816

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
        pattern1 = r"\((\d{17,20})\)\s*-\s*Main account\s*:\s*<@(\d{17,20})>"
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
                                if not alt_info:
                                    print(f"[WARNING] Missing alt: {alt}")
                                    continue
                                alt_info["alts"] += old_alts2
                                alt_info["alts"].append(alt2_id)
                                alt_info["proofs"] += old_proofs2
                                alt_info["proof"].append(proof)
                                altscol.replace_one(alt_query, alt_info)
                            for alt in old_alts2:
                                alt_query = {"_id": alt}
                                alt_info = altscol.find_one(alt_query)
                                if not alt_info:
                                    print(f"[WARNING] Missing alt: {alt}")
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
                            if not alt_info:
                                print(f"[WARNING] Missing alt: {alt}")
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
                            if not alt_info:
                                print(f"[WARNING] Missing alt: {alt}")
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

@bot.command(name='a', help='Checks a user for logged alts.')
async def a(ctx, *, to_check: str = None):
    if to_check is None:
        user = ctx.author
        user_id = str(user.id)
        alts_query = {"_id": user_id}
        alts_info = altscol.find_one(alts_query)
        if alts_info:
            profile = discord.Embed(colour=0xffffff)
            profile.description = f"Alts for {user.name} `{user.id}`\n"
            for alt, proof in zip(alts_info["alts"], alts_info["proofs"]):
                if proof[-5:] == " ┈ dc":
                    jump_url = proof[:-5]
                    parts = jump_url.split('/')
                    guild_id = int(parts[-3])
                    guild = await bot.fetch_guild(guild_id)
                    if guild:
                        server_name = guild.name
                        formatted_proof = proof + f" ┈ {server_name}"
                        profile.description += f"\n`{alt}` ┈ {formatted_proof}"
                else:
                    profile.description += f"\n`{alt}` ┈ {proof}"
            await ctx.reply(embed=profile, view=RelatedIDsView(user_id, alts_info["alts"]))
        else:
            profile = default_no_alts(user)
            await ctx.reply(embed=profile)

    else:
        try:
            user = await bot.fetch_user(int(to_check.strip('<@>')))
        except discord.NotFound:
            await ctx.send("Please provide a valid user ID.")
        else:
            user_id = str(user.id)
            alts_query = {"_id": user_id}
            alts_info = altscol.find_one(alts_query)
            if alts_info:
                profile = discord.Embed(colour=0xffffff)
                profile.description = f"Alts for {user.name} `{user.id}`\n"
                for alt, proof in zip(alts_info["alts"], alts_info["proofs"]):
                    if proof[-5:] == " ┈ dc":
                        jump_url = proof[:-5]
                        parts = jump_url.split('/')
                        guild_id = int(parts[-3])
                        guild = await bot.fetch_guild(guild_id)
                        if guild:
                            server_name = guild.name
                            formatted_proof = proof + f" ┈ {server_name}"
                            profile.description += f"\n`{alt}` ┈ {formatted_proof}"
                    else:
                        profile.description += f"\n`{alt}` ┈ {proof}"
                await ctx.reply(embed=profile, view=RelatedIDsView(user_id, alts_info["alts"]))
            else:
                profile = default_no_alts(user)
                await ctx.reply(embed=profile)

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


@bot.tree.command(name="cleanup", description="Cleanup alts database.")
async def cleanup(interaction: discord.Interaction):
    if interaction.user.id != 1303291812282372137:  # replace with your admin ID
        await interaction.response.send_message("Unauthorized.", ephemeral=True)
        return
    await interaction.response.send_message("Repairing database...", ephemeral=True)
    def repair_job():
        id_pattern = re.compile(r"^\d{17,20}$")
        all_docs = list(altscol.find({}))
        fixed_count = 0
        for doc in all_docs:
            user_id = doc["_id"]

            alts = doc.get("alts", [])
            proofs = doc.get("proofs", [])

            clean_alts = []
            clean_proofs = proofs.copy()

            # Separate corrupted entries
            for item in alts:
                if isinstance(item, str) and id_pattern.match(item):
                    clean_alts.append(item)
                else:
                    clean_proofs.append(item)

            clean_alts = list(set(clean_alts))
            clean_proofs = list(set(clean_proofs))

            if user_id in clean_alts:
                clean_alts.remove(user_id)

            new_doc = {
                "_id": user_id,
                "alts": clean_alts,
                "proofs": clean_proofs
            }

            altscol.replace_one({"_id": user_id}, new_doc)
            fixed_count += 1

        all_docs = list(altscol.find({}))

        for doc in all_docs:
            user_id = doc["_id"]
            for alt in doc["alts"]:
                alt_doc = altscol.find_one({"_id": alt})

                if not alt_doc:
                    # create missing node
                    alt_doc = {"_id": alt, "alts": [], "proofs": []}

                if user_id not in alt_doc["alts"]:
                    alt_doc["alts"].append(user_id)

                altscol.replace_one({"_id": alt}, alt_doc, upsert=True)

    fixed_count = await asyncio.to_thread(repair_job)

    await interaction.followup.send(
        f"Cleanup complete. Processed {fixed_count} documents.",
        ephemeral=True
    )

@bot.tree.command(name="import_dc", description="Import Double Counter alt intrusions from recent 200 messages.")
async def import_dc(interaction: discord.Interaction):
    neru_logs_channel = bot.get_channel(NERU_LOGS)
    channel = interaction.channel
    if channel:
        msg = await channel.send("Checking recent 200 messages for Double Counter alt intrusions...")
        await interaction.response.defer(ephemeral=True)
        count=0
        async for message in channel.history(limit=200):
            if message.author.id == 703886990948565003:
                pattern1 = r"\((\d{17,20})\)\s*-\s*Main account\s*:\s*<@(\d{17,20})>"
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
                                    count+=1
                                    old_alts1 = alt1_info["alts"].copy()
                                    old_alts2 = alt2_info["alts"].copy()
                                    old_proofs1 = alt1_info["proofs"].copy()
                                    old_proofs2 = alt2_info["proofs"].copy()
                                    for alt in old_alts1:
                                        alt_query = {"_id": alt}
                                        alt_info = altscol.find_one(alt_query)
                                        if not alt_info:
                                            print(f"[WARNING] Missing alt: {alt}")
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
                                            print(f"[WARNING] Missing alt: {alt}")
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
                                        print(f"[WARNING] Missing alt: {alt}")
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
                            count+=1
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
                                        print(f"[WARNING] Missing alt: {alt}")
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
        if count == 0:
            await interaction.followup.send("No new alt intrusions imported.", ephemeral=True)
        else:
            await interaction.followup.send(f"Success!", ephemeral=True)
        await msg.edit(content=f"Successfully imported {count} alt intrusions.")

@bot.tree.command(name="import_all", description="Import Double Counter alt intrusions from all messages.")
async def import_dc(interaction: discord.Interaction):
    if interaction.user.id != 1303291812282372137:
        return
    neru_logs_channel = bot.get_channel(NERU_LOGS)
    channel = interaction.channel
    if channel:
        msg = await channel.send("Checking all messages for Double Counter alt intrusions...")
        await interaction.response.defer(ephemeral=True)
        count=0
        async for message in channel.history(limit=None):
            if message.author.id == 703886990948565003:
                pattern1 = r"\((\d{17,20})\)\s*-\s*Main account\s*:\s*<@(\d{17,20})>"
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
                                    count+=1
                                    old_alts1 = alt1_info["alts"].copy()
                                    old_alts2 = alt2_info["alts"].copy()
                                    old_proofs1 = alt1_info["proofs"].copy()
                                    old_proofs2 = alt2_info["proofs"].copy()
                                    for alt in old_alts1:
                                        alt_query = {"_id": alt}
                                        alt_info = altscol.find_one(alt_query)
                                        if not alt_info:
                                            print(f"[WARNING] Missing alt: {alt}")
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
                                            print(f"[WARNING] Missing alt: {alt}")
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
                                        print(f"[WARNING] Missing alt: {alt}")
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
                            count+=1
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
                                        print(f"[WARNING] Missing alt: {alt}")
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
        if count == 0:
            await interaction.followup.send("No new alt intrusions imported.", ephemeral=True)
        else:
            await interaction.followup.send(f"Success!", ephemeral=True)
        await msg.edit(content=f"Successfully imported {count} alt intrusions.")

@bot.tree.command(name="add_alts", description="Adds a pair of users as alts.")
@app_commands.describe(user1="User 1", user2="User 2", reason="Reason/Proof")
@app_commands.checks.has_role(adm_role)
async def add_alts(interaction: discord.Interaction, user1: str, user2: str, reason: str):
    if interaction.channel.id != NERU_LOGS:
        await interaction.response.send_message("This command does not work here.", ephemeral=True)
        return
    proof = f"{reason} ┈ added by {interaction.user.mention}"
    if user1.strip("<@>") != user2.strip("<@>"):
        try:
            alt1 = await bot.fetch_user(int(user1.strip("<@>")))
            alt2 = await bot.fetch_user(int(user2.strip("<@>")))
        except discord.NotFound:
            await interaction.response.send_message(f"Please provide valid User IDs.", ephemeral=True)
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
                        await interaction.response.send_message(f"`{alt1_id}` and `{alt2_id}` have already been logged.", ephemeral=True)
                    else:
                        old_alts1 = alt1_info["alts"].copy()
                        old_alts2 = alt2_info["alts"].copy()
                        old_proofs1 = alt1_info["proofs"].copy()
                        old_proofs2 = alt2_info["proofs"].copy()
                        for alt in old_alts1:
                            alt_query = {"_id": alt}
                            alt_info = altscol.find_one(alt_query)
                            if not alt_info:
                                print(f"[WARNING] Missing alt: {alt}")
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
                                print(f"[WARNING] Missing alt: {alt}")
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
                            await interaction.response.send_message(
                                f"`{alt1_id}` and `{alt2_id}` have been added as alts. Separate reports detected, use /merge to merge them.")
                        elif user1_profile and len(user1_profile)>2: # user 1 reported, user 2 not reported
                            await interaction.response.send_message(
                                f"`{alt1_id}` and `{alt2_id}` have been added as alts. `{alt1_id}` is reported but not `{alt2_id}`. Please update the report accordingly.")
                        elif user2_profile and len(user2_profile)>2: # user 2 reported, user 1 not reported
                            await interaction.response.send_message(
                                f"`{alt1_id}` and `{alt2_id}` have been added as alts. `{alt2_id}` is reported but not `{alt1_id}`. Please update the report accordingly.")
                        else: # none reported
                            await interaction.response.send_message(f"`{alt1_id}` and `{alt2_id}` have been added as alts.")

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
                            print(f"[WARNING] Missing alt: {alt}")
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
                        await interaction.response.send_message(
                            f"`{alt1_id}` and `{alt2_id}` have been added as alts. Separate reports detected, use /merge to merge them.")
                    elif user1_profile and len(user1_profile)>2:  # user 1 reported, user 2 not reported
                        await interaction.response.send_message(
                            f"`{alt1_id}` and `{alt2_id}` have been added as alts. `{alt1_id}` is reported but not `{alt2_id}`. Please update the report accordingly.")
                    elif user2_profile and len(user2_profile)>2:  # user 2 reported, user 1 not reported
                        await interaction.response.send_message(
                            f"`{alt1_id}` and `{alt2_id}` have been added as alts. `{alt2_id}` is reported but not `{alt1_id}`. Please update the report accordingly.")
                    else:  # none reported
                        await interaction.response.send_message(f"`{alt1_id}` and `{alt2_id}` have been added as alts.")

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
                            print(f"[WARNING] Missing alt: {alt}")
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
                        await interaction.response.send_message(
                            f"`{alt1_id}` and `{alt2_id}` have been added as alts. Separate reports detected, use /merge to merge them.")
                    elif user1_profile and len(user1_profile)>2:  # user 1 reported, user 2 not reported
                        await interaction.response.send_message(
                            f"`{alt1_id}` and `{alt2_id}` have been added as alts. `{alt1_id}` is reported but not `{alt2_id}`. Please update the report accordingly.")
                    elif user2_profile and len(user2_profile)>2:  # user 2 reported, user 1 not reported
                        await interaction.response.send_message(
                            f"`{alt1_id}` and `{alt2_id}` have been added as alts. `{alt2_id}` is reported but not `{alt1_id}`. Please update the report accordingly.")
                    else:  # none reported
                        await interaction.response.send_message(f"`{alt1_id}` and `{alt2_id}` have been added as alts.")

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
                        await interaction.response.send_message(
                            f"`{alt1_id}` and `{alt2_id}` have been added as alts. Separate reports detected, use /merge to merge them.")
                    elif user1_profile and len(user1_profile)>2:  # user 1 reported, user 2 not reported
                        await interaction.response.send_message(
                            f"`{alt1_id}` and `{alt2_id}` have been added as alts. `{alt1_id}` is reported but not `{alt2_id}`. Please update the report accordingly.")
                    elif user2_profile and len(user2_profile)>2:  # user 2 reported, user 1 not reported
                        await interaction.response.send_message(
                            f"`{alt1_id}` and `{alt2_id}` have been added as alts. `{alt2_id}` is reported but not `{alt1_id}`. Please update the report accordingly.")
                    else:  # none reported
                        await interaction.response.send_message(f"`{alt1_id}` and `{alt2_id}` have been added as alts.")

@bot.command()
async def sync(ctx: commands.Context):
    await bot.tree.sync()
    alts_count = altscol.count_documents({})
    await bot.change_presence(
        status=discord.Status.idle,
        activity=discord.Activity(type=discord.ActivityType.watching, name=f"{alts_count} alts.")
    )

bot.run(TOKEN)