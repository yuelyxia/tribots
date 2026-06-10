#  yuelyxia  ©  2025 – 2026

from dotenv import load_dotenv
import os
load_dotenv()

import pymongo

import io
import aiohttp
import asyncio
import re

import datetime

import discord
from discord import app_commands
from discord.ext import commands, tasks
from discord.utils import get

from typing import Optional, Literal

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
filescol = db["files"]

intents = discord.Intents.all()
bot = commands.Bot(command_prefix=',', help_command=None, intents=intents)

LB_CHANNEL = 1375271142092308582
CMDS_CHANNEL = 1375260303817838694
VERIFY_CHANNEL = 1375260857772150804
TRAINING_CHANNEL = 1375271729680748635
TICKET_CHANNEL = 1375261699111784478
QUOTA_CHANNEL = 1505563131655749712

# tri roles info
staff_role = 1373803879623430268
ticket_ping = 1449382692671193294
o5_role = 1372426616671834234
adm_role = 1372426657335345163
tadm_role = 1373517323914448906
adm_ping = 1375276457890287748
sr_of_the_month = 1498909625263722537
sr_role = 1372426698242658324
tsr_role = 1372426698242658324
sr_ping = 1375254710952661102
reporter_of_the_month = 1447056456401551410
rep_role = 1372426736205303808
tr_role = 1372426794585817088
t_role = 1396701840321679391
ban_perms = 1373517806921973900
files_access = 1459594433371705575
defender = 1374364037818617856
staff_trainer = 1498599499893837874
full_break = 1505568168880636014
half_break = 1505568134617235546
tri_supporter = 1465630182462460040
archived_staff = 1505062096336064552

STAFF_ROLES = [ban_perms, files_access, defender, sr_of_the_month, sr_role, tsr_role, staff_trainer, sr_ping,
               reporter_of_the_month, rep_role, tr_role, t_role]

TRI_Archive = 1371673839695826974

#tethys roles info
tethys_adm_role = 1435570385960833024
tethys_staff_role = 1434809295953854475
tethys_tri_supporter = 1465634056015450270
tethys_ban_perms = 1465576138226139220
professional_pilot_role = 1435205527452778597
professional_mm_role = 1435205320300302396

tethys = 1434471275723493388


banned_words = ["backshot", "blackie", "blowjob", "boob", "boobies", "boobs", "breedable", "ching chong", "clit", "cock", "cunt", "dick", "dih", "dihh", "facist", "faggot", "fatass", "footjob", "gooner", "gooning", "hanime", "hentai", "hitler", "kill yourself", "kys", "masturbate", "ngger", "ngro", "nazi", "ngga", "nigga", "nigger", "nigro", "penis", "pervert", "porn", "prostitute", "rape", "retard", "retarted", "schlong", "semen", "shlong", "skibidi", "sperm", "suicide", "testes", "testicle", "testis", "tranny", "vagina", "whitey", "whore"]

# events

@bot.event
async def on_message(message):
    if message.channel.id == CMDS_CHANNEL:
        if message.author.bot:
            return
        if not message.content.startswith(","):
            try: await message.delete()
            except Exception: pass
    await bot.process_commands(message)


@bot.event
async def on_member_join(member):
    if member.guild.id == TRI_Archive:
        channel = bot.get_channel(VERIFY_CHANNEL)
        await channel.send(f"Welcome to TRI Archive, {member.mention}! Please verify.", delete_after=0)

@bot.event
async def on_member_update(before, after):
    if before.guild.id == TRI_Archive:
        source_role = discord.utils.get(after.guild.roles, id=tri_supporter)
        if source_role in after.roles and source_role not in before.roles:
            tethys_guild = bot.get_guild(tethys)
            try:
                target_member = await tethys_guild.fetch_member(after.id)
            except Exception: pass
            else:
                target_role = discord.utils.get(tethys_guild.roles, id=tethys_tri_supporter)
                try:
                    await target_member.add_roles(target_role, reason="tri supporter role synced from TRI Archive.")
                except Exception: pass

@bot.event
async def on_ready():
    bot.add_view(StaffGuideView())
    bot.add_view(StaffRulesView())
    bot.add_view(ClosingView())
    bot.add_view(TagsView())
    bot.add_view(FileView())
    bot.add_view(TRLogView())
    weekly_quota.start()
    await bot.tree.sync()

# loop tasks

async def send_low_performance_dm(member, rratio, vratio=None):
    try:
        embed = discord.Embed(
            title="Performance Warning",
            description=(
                "Your recent staff activity is below expected quota levels.\n\n"
                f"8-week average **reports** quota completion: **{rratio:.2f}**\n"
            ),
            colour=0xffffff
        )
        if rratio < 0.6:
            embed.title = "CRITICAL Performance Warning"
        if vratio:
            embed.description+=f"8-week average **reviews** quota completion: **{vratio:.2f}**\n"
            if vratio < 0.6:
                embed.title = "CRITICAL Performance Warning"
        embed.description+="\nPlease improve your activity. Thank you."
        await member.send(embed=embed)
    except:
        pass

async def send_incomplete_quota_dm(member, weekly, q, r, type=None):
    try:
        embed = discord.Embed(title="Incomplete Quota", colour=0xffffff)
        if type is not None and type == "reviews":
            embed.description = f"Required reviews: **{q}**\nCompleted reviews: **{weekly}**\nRatio: **{r:.2f}**"
        if type is not None and type == "reports":
            embed.description = f"Required reports: **{q}**\nCompleted reports: **{weekly}**\nRatio: **{r:.2f}**"
        if type is None:
            embed.description = f"Required reports: **{q}**\nCompleted reports: **{weekly}**\nRatio: **{r:.2f}**"
        await member.send(embed=embed)
    except:
        pass

def get_quota_config():
    return staffweeklycol.find_one({"_id": "global"}) or {
        "reports_quota": 0,
        "sr_reports_quota": 0,
        "sr_reviews_quota": 0
    }
# helpers
def apply_break(quota, member):
    if get(member.guild.roles, id=full_break) in member.roles:
        return -1
    if get(member.guild.roles, id=half_break) in member.roles:
        return max(1, quota // 2)
    return quota

@tasks.loop(time=datetime.time(hour=0, minute=0))
async def weekly_quota():
    guild = bot.get_guild(TRI_Archive)
    if not guild:
        return
    if datetime.datetime.now(datetime.timezone.utc).weekday() != 0:
        return
    lb_channel = bot.get_channel(LB_CHANNEL)
    if not lb_channel:
        return
    reviews_role_categories = {
        o5_role: ("overseers", []),
        adm_role: ("admins", []),
        sr_role: ("senior reporters", [])
    }
    reports_role_categories = {
        o5_role: ("overseers", []),
        adm_role: ("admins", []),
        sr_role: ("senior reporters", []),
        rep_role: ("reporters", []),
        tr_role: ("trial reporters", [])
    }
    sr_not_met_quota = []
    not_met_quota = []
    sr_demotion_list = []
    demotion_list = []
    total_reviews = 0
    total_reports = 0
    o5_r = get(guild.roles, id=o5_role)
    adm_r = get(guild.roles, id=adm_role)
    sr_r = get(guild.roles, id=sr_role)
    rep_r = get(guild.roles, id=rep_role)
    tr_r = get(guild.roles, id=tr_role)
    full_break_r = get(guild.roles, id=full_break)
    half_break_r = get(guild.roles, id=half_break)
    def apply_breakbal(member, weekly_profile):
        bal = weekly_profile.get("breakbal", 12)
        if full_break_role in member.roles:
            bal -= 1
        elif half_break_role in member.roles:
            bal -= 0.5
        else:
            bal += 0.125
        return max(bal, 0)
    def ratio(done, quota):
        if quota in (-1, 0):
            return -1 if quota == -1 else 1
        return round(min(done / quota, 1), 3)
    config = staffweeklycol.find_one({"_id": "global"}) or {
        "reports_quota": 0,
        "sr_reports_quota": 0,
        "sr_reviews_quota": 0
    }
    staff_members = set(o5_r.members + adm_r.members + sr_r.members + rep_r.members + tr_r.members + full_break_r.members + half_break_r.members)
    for member in staff_members:
        staff_id = str(member.id)
        full_break_role = guild.get_role(full_break)
        half_break_role = guild.get_role(half_break)
        ticket_ping_role = guild.get_role(ticket_ping)
        staff_profile = trusteduserscol.find_one({"_id": staff_id}) or {}
        weekly_profile = staffweeklycol.find_one({"_id": staff_id}) or {}
        weekly_profile["breakbal"] = apply_breakbal(member, weekly_profile)
        if weekly_profile["breakbal"] <= 0:
            remove_roles = []
            if member.get_role(full_break):
                remove_roles.append(full_break_role)
            if member.get_role(half_break):
                remove_roles.append(half_break_role)
            await member.remove_roles(*remove_roles)
            restore_roles = []
            for rid in weekly_profile.get("saved_roles", []):
                role = guild.get_role(rid)
                if role:
                    restore_roles.append(role)
            restore_roles.append(ticket_ping_role)
            await member.add_roles(*restore_roles)
            weekly_profile["saved_roles"] = []
            staffweeklycol.replace_one({"_id": str(member.id)}, weekly_profile, upsert=True)
        weekly_reviews = int(weekly_profile.get("weekly_reviews", 0))
        weekly_reports = int(weekly_profile.get("weekly_reports", 0))
        is_sr = any(role.id in (sr_ping, adm_ping) for role in member.roles)
        if is_sr:
            rq = config["sr_reports_quota"]
        else:
            rq = config["reports_quota"]
        rq = apply_break(rq, member)
        rr = ratio(weekly_reports, rq)
        weekly_profile.setdefault("reports_quota_list", [])
        weekly_profile["reports_quota_list"].append([weekly_reports, rq, rr])
        weekly_profile["reports_quota_list"] = weekly_profile["reports_quota_list"][-8:]
        if is_sr:
            vq = config["sr_reviews_quota"]
            vq = apply_break(vq, member)
            vr = ratio(weekly_reviews, vq)
            weekly_profile.setdefault("reviews_quota_list", [])
            weekly_profile["reviews_quota_list"].append([weekly_reviews, vq, vr])
            weekly_profile["reviews_quota_list"] = weekly_profile["reviews_quota_list"][-8:]
            if vq != -1 and vr != -1 and vr < 1:
                sr_not_met_quota.append([staff_id, "reviews", weekly_reviews, vq, vr])
                await send_incomplete_quota_dm(member, weekly_reviews, vq, vr, "reviews")
            if rq != -1 and rr != -1 and rr < 1:
                sr_not_met_quota.append([staff_id, "reports", weekly_reports, rq, rr])
                await send_incomplete_quota_dm(member, weekly_reports, rq, rr, "reports")
        else:
            if rq != -1 and rr != -1 and rr < 1:
                not_met_quota.append([staff_id, weekly_reports, rq, rr])
                await send_incomplete_quota_dm(member, weekly_reports, rq, rr)
        staffweeklycol.replace_one({"_id": staff_id}, weekly_profile, upsert=True)
        rratios = [x[2] for x in weekly_profile["reports_quota_list"] if x[2] != -1]
        if is_sr:
            vratios = [x[2] for x in weekly_profile["reviews_quota_list"] if x[2] != -1]
            ravg = sum(rratios) / len(rratios) if rratios else None
            vavg = sum(vratios) / len(vratios) if vratios else None
            if (ravg is not None and ravg < 0.5 and len(weekly_profile.get("reports_quota_list", [])) > 7) or (vavg is not None and vavg < 0.5 and len(weekly_profile.get("reviews_quota_list", [])) > 7):
                sr_demotion_list.append([staff_id, round(ravg, 3), round(vavg, 3)])
            if (ravg is not None and ravg < 0.8 and len(weekly_profile.get("reports_quota_list", [])) > 2) or (vavg is not None and vavg < 0.8 and len(weekly_profile.get("reviews_quota_list", [])) > 2):
                member = guild.get_member(int(staff_id))
                if member:
                    await send_low_performance_dm(member, vavg, ravg)
        else:
            if rratios:
                ravg = sum(rratios) / len(rratios)
                if ravg is not None and ravg < 0.5 and len(weekly_profile.get("reports_quota_list", [])) > 7:
                    demotion_list.append([staff_id, round(ravg, 3)])
                if ravg is not None and ravg < 0.8 and len(weekly_profile.get("reports_quota_list", [])) > 2:
                    member = guild.get_member(int(staff_id))
                    if member:
                        await send_low_performance_dm(member, ravg)

        matched_role = None
        for role_id in reports_role_categories:
            if get(member.roles, id=role_id):
                matched_role = role_id
                break
        if not matched_role:
            continue
        reports = staff_profile.get("reports", 0)
        weekly_reports = weekly_profile.get("weekly_reports", 0)
        reports_role_categories[matched_role][1].append((member, reports, weekly_reports))

        matched_role = None
        for rid in reviews_role_categories:
            if get(member.roles, id=rid):
                matched_role = rid
                break
        if not matched_role:
            continue
        reviews = staff_profile.get("reviews", 0)
        weekly_reviews = weekly_profile.get("weekly_reviews", 0)
        reviews_role_categories[matched_role][1].append((member, reviews, weekly_reviews))

    # reviews
    embeds = []
    for role_id, (title, staff_list) in reviews_role_categories.items():
        embed = discord.Embed(colour=0xffffff)
        embed.description = f"**✦　　┈　　{title}**"
        staff_list.sort(key=lambda x: x[2], reverse=True)
        for i, (member, reviews, weekly_reviews) in enumerate(staff_list, start=1):
            total_reviews += weekly_reviews
            embed.description += (
                f"\n-# {i}ㆍ　"
                f"{member.mention}　–　"
                f"**{reviews}** all ㆍ **{weekly_reviews}** week")
        embeds.append(embed)
    await lb_channel.send(f"## _ _　　　weekly leaderboards .ᐟ\n_ _　　　　　　||<@&{staff_role}>||")
    await lb_channel.send("## _ _　　　reviews leaderboard", embeds=embeds)
    # reports
    embeds = []
    for role_id, (title, staff_list) in reports_role_categories.items():
        embed = discord.Embed(colour=0xffffff)
        embed.description = f"**✦　　┈　　{title}**"
        # optional sorting
        staff_list.sort(key=lambda x: x[2], reverse=True)
        for i, (member, reports, weekly_reports) in enumerate(staff_list, start=1):
            total_reports += weekly_reports
            embed.description += (
                f"\n-# {i}ㆍ　"
                f"{member.mention}　–　"
                f"**{reports}** all ㆍ **{weekly_reports}** week")
        embeds.append(embed)
    await lb_channel.send("## _ _　　　reports leaderboard", embeds=embeds)
    summary = discord.Embed(colour=0xffffff)
    summary.description = (
        f"✦　　┈　　total reviews　　┈　　**{total_reviews}**\n"
        f"✦　　┈　　total reports　　┈　　**{total_reports}**"
    )
    await lb_channel.send("## _ _　　　weekly summary", embed=summary)

    sr_nmq_embed = discord.Embed(
        title="sr+ weekly quota summary",
        colour=0xffffff
    )
    if not sr_not_met_quota:
        sr_nmq_embed.description = "All staff met their weekly quota <a:pinkconfetti:1505564994731905065>"
    else:
        desc = ""
        for user, qtype, done, quota, ratio in sorted(sr_not_met_quota, key=lambda x: x[4]):
            member = guild.get_member(int(user))
            mention = member.mention if member else f"`{user}`"
            desc += (
                f"\n-# ㆍ　{mention}　–　{qtype}: "
                f"**{done}** / {quota}　({ratio:.2f})"
            )
        sr_nmq_embed.description = desc[:4000]
    nmq_embed = discord.Embed(
        title="staff weekly quota summary",
        colour=0xffffff
    )
    if not not_met_quota:
        nmq_embed.description = "All staff met their weekly quota <a:pinkconfetti:1505564994731905065>"
    else:
        desc = ""
        for user, done, quota, ratio in sorted(not_met_quota, key=lambda x: x[3]):
            member = guild.get_member(int(user))
            mention = member.mention if member else f"`{user}`"
            desc += (
                f"\n-# ㆍ　{mention}　–　**{done}** / {quota}　"
                f"({ratio:.2f})"
            )
        nmq_embed.description = desc[:4000]
    quota_channel = bot.get_channel(QUOTA_CHANNEL)
    await quota_channel.send(embed=sr_nmq_embed)
    await quota_channel.send(embed=nmq_embed)
    if sr_demotion_list:
        sr_demotion_embed = discord.Embed(
            title="sr+ demotion candidates",
            colour=0x992D22
        )
        desc = ""
        for staff_id, ravg, vavg in sr_demotion_list:
            member = guild.get_member(int(staff_id))
            mention = member.mention if member else f"`{staff_id}`"
            desc += f"\n-# ㆍ　{mention}　–　reports: `{ravg:.2f}`　ㆍ　reviews: `{vavg:.2f}`"
        sr_demotion_embed.description = desc
        if desc:
            await quota_channel.send(embed=sr_demotion_embed)
    if demotion_list:
        demotion_embed = discord.Embed(
            title="Demotion Candidates",
            colour=0xE74C3C
        )
        desc = ""
        for staff_id, avg in demotion_list:
            member = guild.get_member(int(staff_id))
            mention = member.mention if member else f"`{staff_id}`"
            desc += f"\n-# ㆍ　{mention}　–　reports: `{avg:.2f}`"
        demotion_embed.description = desc
        if desc:
            await quota_channel.send(embed=demotion_embed)

    staffweeklycol.update_many(
        {},
        {"$set": {"weekly_reports": 0, "weekly_reviews": 0}}
    )

settings = app_commands.Group(name="set", description="Set.")
bot.tree.add_command(settings)

@settings.command(name="breakbal", description="Set break balance for a staff or all staff.")
@app_commands.checks.has_role(adm_ping)
async def set_breakbal(interaction: discord.Interaction, user: str, value: float):
    await interaction.response.defer(ephemeral=True)
    if value < 0:
        return await interaction.followup.send("Break balance cannot be negative.", ephemeral=True)
    if value.is_integer():
        value = int(value)
    if user.lower() == "all":
        result = staffweeklycol.update_many({}, {"$set": {"breakbal": value}})
        return await interaction.followup.send(f"Set break balance to **{value}** for **{result.modified_count}** users.", ephemeral=True)
    try:
        user_id = int(user.strip("<@!>"))
    except ValueError:
        return await interaction.followup.send("Invalid user.", ephemeral=True)
    member = interaction.guild.get_member(user_id)
    if not member:
        return await interaction.followup.send("User not in server.", ephemeral=True)
    profile = staffweeklycol.find_one({"_id": str(user_id)})
    if profile:
        profile["breakbal"] = value
        staffweeklycol.replace_one({"_id": str(user_id)}, profile, upsert=True)
        await interaction.followup.send(f"`{user_id}`’s break balance has been set to **{value}**.", ephemeral=True)

@settings.command(name="quota", description="Set weekly report quota for staff")
@app_commands.describe(quota="Weekly report quota")
@app_commands.checks.has_role(adm_ping)
async def set_quota(interaction: discord.Interaction, quota: int):
    if quota < 0:
        return await interaction.response.send_message("Quota must be at least 0.", ephemeral=True)
    staffweeklycol.update_one(
        {"_id": "global"},
        {"$set": {"reports_quota": quota}},
        upsert=True
    )
    await interaction.response.send_message(
        f"Reporters report quota set to **{quota}**.",
        ephemeral=True
    )

@settings.command(name="srquota", description="Set weekly quota for SR+")
@app_commands.describe(quota="Weekly report quota", type="Reports/Reviews")
@app_commands.checks.has_role(adm_ping)
async def set_srquota(interaction: discord.Interaction, quota: int, type: Literal["reports", "reviews"]):
    if quota < 1:
        return await interaction.response.send_message(
            "Quota must be at least 1.",
            ephemeral=True
        )
    if type == "reports":
        field = "sr_reports_quota"
    elif type == "reviews":
        field = "sr_reviews_quota"
    staffweeklycol.update_one(
        {"_id": "global"},
        {"$set": {field: quota}},
        upsert=True
    )
    await interaction.response.send_message(
        f"SR+ {type} quota set to **{quota}**.",
        ephemeral=True
    )

# text commands

def get_staff_rank(member):
    if get(member.guild.roles, id=o5_role) in member.roles:
        return "Overseer"
    elif get(member.guild.roles, id=adm_role) in member.roles:
        return "Admin"
    elif get(member.guild.roles, id=tadm_role) in member.roles:
        return "Trial Admin"
    elif get(member.guild.roles, id=sr_role) in member.roles:
        return "Senior Reporter"
    elif get(member.guild.roles, id=tsr_role) in member.roles:
        return "Trial Senior Reporter"
    elif get(member.guild.roles, id=rep_role) in member.roles:
        return "Reporter"
    elif get(member.guild.roles, id=tr_role) in member.roles:
        return "Trial Reporter"
    return "Staff"

@bot.command(name="q")
async def quota(ctx, member: discord.Member = None):
    if not member: member = ctx.author
    staff_id = str(member.id)
    weekly_profile = staffweeklycol.find_one({"_id": staff_id})
    if not weekly_profile:
        return await ctx.send("No quota history found for this user.")
    t_r = get(ctx.guild.roles, id=t_role)
    in_training = set(t_r.members)
    if member in in_training:
        return await ctx.send("This staff is still in training.")
    embeds = []
    rank = get_staff_rank(member)
    profile = discord.Embed(colour=0xffffff)
    profile.set_thumbnail(url=f"{member.display_avatar}")
    profile.description = f"{member.name}\n`{member.id}`\n{member.mention}\n**Rank:** {rank}"
    embeds.append(profile)
    embed = discord.Embed(title="quota progress", colour=0xffffff, description="")
    is_sr = any(role.id in (sr_ping, adm_ping) for role in member.roles)
    if is_sr:
        current_reviews = weekly_profile.get("weekly_reviews", 0)
        current_reviews_quota = (
            get_quota_config().get("sr_reviews_quota", 0)
        )
        current_reviews_quota = apply_break(current_reviews_quota, member)
        current_reviews_ratio = (
            round(min(current_reviews / current_reviews_quota, 1), 2)
            if current_reviews_quota >= 0 else -1
        )
        quota_display = "FULL BREAK" if current_reviews_quota == -1 else str(current_reviews_quota)
        ratio_display = "N/A" if current_reviews_ratio == -1 else f"{current_reviews_ratio:.2f}"
        embed.description += f"\nreviews　–　**{current_reviews}** / {quota_display}　–　`{ratio_display}`"
        if ratio_display == "1.00": embed.description += "　<a:pinkconfetti:1505564994731905065>"
    current_reports = weekly_profile.get("weekly_reports", 0)
    if is_sr:
        current_reports_quota = get_quota_config().get("sr_reports_quota", 0)
    else:
        current_reports_quota = get_quota_config().get("reports_quota", 0)
    current_reports_quota = apply_break(current_reports_quota, member)
    current_reports_ratio = round(min(current_reports / current_reports_quota, 1), 2) if current_reports_quota >= 0 else -1
    quota_display = "FULL BREAK" if current_reports_quota == -1 else str(current_reports_quota)
    ratio_display = "N/A" if current_reports_ratio == -1 else f"{current_reports_ratio:.2f}"
    embed.description += f"\nreports　–　**{current_reports}** / {quota_display}　–　`{ratio_display}`"
    if ratio_display == "1.00": embed.description += "　<a:pinkconfetti:1505564994731905065>"
    await ctx.reply(embeds=[profile, embed])

@bot.command(name="qh")
async def quota_history(ctx, member: discord.Member=None):
    if not member: member = ctx.author
    staff_id = str(member.id)
    weekly_profile = staffweeklycol.find_one({"_id": staff_id})
    if not weekly_profile:
        return await ctx.send("No quota history found for this user.")
    t_r = get(ctx.guild.roles, id=t_role)
    in_training = set(t_r.members)
    if member in in_training:
        return await ctx.send("This staff is still in training.")
    embeds = []
    rank = get_staff_rank(member)
    profile = discord.Embed(colour=0xffffff)
    profile.set_thumbnail(url=f"{member.display_avatar}")
    profile.description = f"{member.name}\n`{member.id}`\n{member.mention}\n**Rank:** {rank}"
    embeds.append(profile)
    is_sr = any(role.id in (sr_ping, adm_ping) for role in member.roles)
    if is_sr:
        reviews_history = weekly_profile.get("reviews_quota_list", [])
        reviews_embed = discord.Embed(title="reviews quota history", colour=0xffffff)
        desc = ""
        for i, entry in enumerate(reviews_history[-7:], start=1):
            done, quota, ratio = entry
            quota_display = "FULL BREAK" if quota == -1 else str(quota)
            ratio_display = "N/A" if ratio == -1 else f"{ratio:.2f}"
            desc += (
                f"\nWeek {i}　–　**{done}** / {quota_display}　–　`{ratio_display}`")
        reviews_embed.description = desc
        current_reviews = weekly_profile.get("weekly_reviews", 0)
        current_reviews_quota = (
            get_quota_config().get("sr_reviews_quota", 0)
        )
        current_reviews_quota = apply_break(current_reviews_quota, member)
        current_reviews_ratio = (
            round(min(current_reviews / current_reviews_quota, 1), 2)
            if current_reviews_quota >= 0 else -1
        )
        quota_display = "FULL BREAK" if current_reviews_quota == -1 else str(current_reviews_quota)
        ratio_display = "N/A" if current_reviews_ratio == -1 else f"{current_reviews_ratio:.2f}"
        reviews_embed.description+= f"\nCurrent Week　–　**{current_reviews}** / {quota_display}　–　`{ratio_display}`"
        historical_reviews_ratios = [
            x[2]
            for x in reviews_history[-7:]
            if x[2] != -1
        ]
        if current_reviews_ratio != -1:
            historical_reviews_ratios.append(current_reviews_ratio)
        overall_reviews_ratio = (
            round(sum(historical_reviews_ratios) / len(historical_reviews_ratios), 3)
            if historical_reviews_ratios else 0
        )
        reviews_embed.description+=f"\n\n**Overall Ratio**　ㆍ　`{overall_reviews_ratio:.2f}`"
        embeds.append(reviews_embed)
    reports_history = weekly_profile.get("reports_quota_list", [])
    reports_embed = discord.Embed(
        title="reports quota history", colour=0xffffff
    )
    desc = ""
    for i, entry in enumerate(reports_history[-7:], start=1):
        done, quota, ratio = entry
        quota_display = "FULL BREAK" if quota == -1 else str(quota)
        ratio_display = "N/A" if ratio == -1 else f"{ratio:.2f}"
        desc += (
            f"\nWeek {i}　–　**{done}** / {quota_display}　–　`{ratio_display}`")
    reports_embed.description = desc
    current_reports = weekly_profile.get("weekly_reports", 0)
    if is_sr:
        current_reports_quota = (
            get_quota_config().get("sr_reports_quota", 0)
        )
    else:
        current_reports_quota = (
            get_quota_config().get("reports_quota", 0)
        )
    current_reports_quota = apply_break(current_reports_quota, member)
    current_reports_ratio = (
        round(min(current_reports / current_reports_quota, 1), 2)
        if current_reports_quota >= 0 else -1
    )
    quota_display = "FULL BREAK" if current_reports_quota == -1 else str(current_reports_quota)
    ratio_display = "N/A" if current_reports_ratio == -1 else f"{current_reports_ratio:.2f}"
    reports_embed.description += f"\nCurrent Week　–　**{current_reports}** / {quota_display}　–　`{ratio_display}`"
    historical_reports_ratios = [
        x[2]
        for x in reports_history[-7:]
        if x[2] != -1
    ]
    if current_reports_ratio != -1:
        historical_reports_ratios.append(current_reports_ratio)
    overall_reports_ratio = (
        round(sum(historical_reports_ratios) / len(historical_reports_ratios), 3)
        if historical_reports_ratios else 0
    )
    reports_embed.description+=f"\n\n**Overall Ratio**　ㆍ　`{overall_reports_ratio:.2f}`"
    embeds.append(reports_embed)
    await ctx.reply(embeds=embeds)

@bot.command(name="bb")
async def bb(ctx, member: discord.Member=None):
    if not member: member = ctx.author
    t_r = get(ctx.guild.roles, id=t_role)
    in_training = set(t_r.members)
    if member in in_training:
        return await ctx.send("This staff is still in training.")
    embeds = []
    rank = get_staff_rank(member)
    profile = discord.Embed(colour=0xffffff)
    profile.set_thumbnail(url=f"{member.display_avatar}")
    profile.description = f"{member.name}\n`{member.id}`\n{member.mention}\n**Rank:** {rank}"
    embeds.append(profile)
    staff_id = str(member.id)
    weekly_profile = staffweeklycol.find_one({"_id": staff_id}) or {}
    full_break_r = ctx.guild.get_role(full_break)
    half_break_r = ctx.guild.get_role(half_break)
    bal = weekly_profile.get("breakbal", 12)
    is_full = full_break_r in member.roles
    is_half = half_break_r in member.roles
    is_sr = any(role.id in (sr_ping, adm_ping) for role in member.roles)
    if is_sr:
        sr_reviews_quota = get_quota_config().get("sr_reviews_quota", 0)
        sr_reports_quota = get_quota_config().get("sr_reports_quota", 0)
        sr_reviews_quota = apply_break(sr_reviews_quota, member)
        sr_reports_quota = apply_break(sr_reports_quota, member)
        met_reviews = weekly_profile.get("weekly_reviews", 0) >= sr_reviews_quota
        met_reports = weekly_profile.get("weekly_reports", 0) >= sr_reports_quota
        met_quota = met_reviews and met_reports
    else:
        reports_quota = get_quota_config().get("reports_quota", 0)
        reports_quota = apply_break(reports_quota, member)
        met_quota = weekly_profile.get("weekly_reports", 0) >= reports_quota
    if is_full:
        preview = bal - 1
        state = "full break"
    elif is_half:
        preview = bal - 0.5
        state = "half break"
    else:
        if met_quota:
            preview = bal + 0.125
            state = "active (+0.125)"
        else:
            preview = bal
            state = "active (+0)"
    preview = max(0, round(preview, 3))
    bal = round(bal, 3)
    embed = discord.Embed(
        title="break balance",
        colour=0xffffff
    )
    embed.description = (
        f"status　–　{state}\n"
        f"current balance　–　**{bal}**\n"
    )
    if "active" not in state:
        embed.description += f"after deduction　–　**{preview}**\n"
    else:
        embed.description += f"after quota check　–　**{preview}**"

    if preview < 0.5:
        embed.description += "\n\nYou will be unable to go on break soon."
    embeds.append(embed)
    await ctx.reply(embeds=embeds)

@bot.command()
async def help(ctx):
    if ctx.guild.id == TRI_Archive:
        embed = discord.Embed(title="TRI bots commands", colour=0xffffff)
        # Add fields for each command/category
        embed.description = """
-# *Prefix:* `,`
### checks
`c`　┈　Checks a user or server.
`mc`　┈　Checks a list of users (max 100), leave a space between users.
`a`　┈　Checks a user for logged alts.
`ma`　┈　Checks a list of users (max 100) for logged alts, leave a space between users.
### utils
`ar`　┈　Sends jump urls to all active reports in the thread.
`vr`　┈　Sends a list of all reports in voting in the thread.
`pr`　┈　Sends a list of all published reports in the thread.
`fm`　┈　Sends a jump url to the first message in the thread.
`rn`　┈　Renames the current thread to the new name provided.
`getids`　┈　Extracts valid user IDs from the string provided.
### autoresponders
`sr`　┈　Pings sr+.
`adm`　┈　Pings adm+.
`tp`　┈　Pings ticket ping.
`ban`　┈　Pings ban perms.
`cl`　┈　Sends closing guide.
`tags`　┈　Sends tags descriptions.
### quota
`q`　┈　Sends quota progress for this week.
`qh`　┈　Sends quota history for the past 8 weeks.
`bb`　┈　Sends break balance.
### leaderboard
`lb`　┈　Sends the current week’s reports leaderboard.
`lbr`　┈　Sends the current week’s reviews leaderboard.
        """
        await ctx.send(embed=embed)

tags_options = [
    discord.SelectOption(emoji="<:whiteheart:1434538078747365507>", label="scammer", value="scammer"),
    discord.SelectOption(emoji="<:whiteheart:1434538078747365507>", label="scam server owner", value="scam server owner"),
    discord.SelectOption(emoji="<:whiteheart:1434538078747365507>", label="raider", value="raider"),
    discord.SelectOption(emoji="<:whiteheart:1434538078747365507>", label="plagiarist", value="plagiarist"),
    discord.SelectOption(emoji="<:whiteheart:1434538078747365507>", label="fake event host", value="fake event host"),
    discord.SelectOption(emoji="<:whiteheart:1434538078747365507>", label="impersonator", value="impersonator"),
    discord.SelectOption(emoji="<:whiteheart:1434538078747365507>", label="vouch scammer", value="vouch scammer"),
    discord.SelectOption(emoji="<:whiteheart:1434538078747365507>", label="suspect", value="suspect"),
    discord.SelectOption(emoji="<:whiteheart:1434538078747365507>", label="unprofessional mm", value="unprofessional mm"),
    discord.SelectOption(emoji="<:whiteheart:1434538078747365507>", label="unprofessional pilot", value="unprofessional pilot"),
    discord.SelectOption(emoji="<:whiteheart:1434538078747365507>", label="unprofessional idv mm", value="unprofessional idv mm"),
    discord.SelectOption(emoji="<:whiteheart:1434538078747365507>", label="unprofessional supervisor", value="unprofessional supervisor"),
    discord.SelectOption(emoji="<:whiteheart:1434538078747365507>", label="unprofessional staff", value="unprofessional staff"),
    discord.SelectOption(emoji="<:whiteheart:1434538078747365507>", label="ex-offender", value="ex-offender"),
    discord.SelectOption(emoji="<:whiteheart:1434538078747365507>", label="improper conduct", value="improper conduct"),
    discord.SelectOption(emoji="<:whiteheart:1434538078747365507>", label="service ban", value="service ban"),
    discord.SelectOption(emoji="<:whiteheart:1434538078747365507>", label="scam server", value="scam server"),
    discord.SelectOption(emoji="<:whiteheart:1434538078747365507>", label="impersonator server", value="impersonator server"),
    discord.SelectOption(emoji="<:whiteheart:1434538078747365507>", label="fake vouch server", value="fake vouch server"),
    discord.SelectOption(emoji="<:whiteheart:1434538078747365507>", label="fake event server", value="fake event server"),
    discord.SelectOption(emoji="<:whiteheart:1434538078747365507>", label="suspect server", value="suspect server"),
]

@bot.command(name="tags", help="Sends the descriptions of demerit tags.")
async def tags(ctx, *, tag: str = None):
    await ctx.reply(embed=discord.Embed(colour=0xffffff, title = "demerit　tags　⸝⸝.ᐟ", description="""
　　use the dropdown to select a tag and view its description.
    """), view=TagsView())

class TagsView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(discord.ui.Button(label="Legal Codex", style=discord.ButtonStyle.grey,
                                        url="https://docs.google.com/document/d/1ef3bb0l1EdXELcAbLDT7QOXFwbQco-600G-4HE6E7KM/"))

    @discord.ui.select(options=tags_options, placeholder="‎　　Select a demerit tag . . .　　　", custom_id="tags",
                       max_values=1)
    async def select_callback(self, interaction, select):
        if self.select_callback.values[0] == "scammer":
            embed = discord.Embed(colour=0xFF0045, description="""
## <a:redarrow:1388148121242177726>　　　　　scammer
　　**__definition__**

> users who have shown the **intention to, have attempted to, have admitted to, and/or have scammed**.
> 　⤷　applies __regardless__ of **whether the scam succeeded, and whether victim was able to recover the scammed possessions**.

　　**__examples__**

> - gaining control of victim’s account (directly or via MM) and ghosting/blocking without completing the trade.
> - sending malicious links (e.g. beam links) to steal accounts, items, or information.
> - providing a different account/item than agreed and refusing to refund or trade back.
> - faking account details (e.g. edited or stolen screenshots).
> - retrieving an account or filing chargebacks after a completed trade to reclaim money or assets.
> - causing damage to others’ account or items, especially with malicious intent.

　　**__notes__**

> - **admitting to scamming:** only reportable with proof (e.g., hit logs). claims alone aren’t enough.
> - **scam backs:** open a ticket before attempting a scam back to avoid being reported. please provide proof of original ownership and proof of the scam.

-# **confrontation is __strongly preferred__ and in some cases, required.** do be polite as much as possible. if ghosted/blocked upon confrontation, it is considered reportable.
""")
            await interaction.response.send_message(embed=embed, ephemeral=True)
        if self.select_callback.values[0] == "scam server owner":
            embed = discord.Embed(colour=0xFF0045, description="""
## <a:redarrow:1388148121242177726>　　　　　scam server owner
　　**__definition__**

> users who **own scam servers** or have owned scam servers in the past.

　　**__examples__**

> - owner of shop server, using the server to scam.
> - guild ownership holder of hitter server.

　　**__notes__**

> - screenshots of **vencord** or **serverinfo bot command** are preferred. If you do not have vencord, ask another staff for help.
> - the scam server owner may only be appealed if the scam server has been appealed.
""")
            await interaction.response.send_message(embed=embed, ephemeral=True)
        if self.select_callback.values[0] == "raider":
            embed = discord.Embed(colour=0xFF0045, description="""
## <a:redarrow:1388148121242177726>　　　　　raider
　　**__definition__**

> users who have **raided server(s)**.
> 　⤷　raiding is defined as: mass-banning server members, mass-deleting channels, spamming messages in server channels or server members’ dms, etc.

　　**__examples__**

> - participating in, coordinating, or assisting a raid, regardless of success or scale.
> - supplying raid tools, bots, or scripts to others for the purpose of raiding.

-# **confrontation is __strongly preferred__ and in some cases, required.** do be polite as much as possible. if ghosted/blocked upon confrontation, it is considered reportable.
""")
            await interaction.response.send_message(embed=embed, ephemeral=True)
        if self.select_callback.values[0] == "plagiarist":
            embed = discord.Embed(colour=0xFF0045, description="""
## <a:redarrow:1388148121242177726>　　　　　plagiarist
　　**__definition__**

> users who have claimed others’ creative works as their own, or have shared/used such works without the rightful owner’s permission.
> 　⤷　includes audio, visual, written works etc.

　　**__examples__**

> - claiming others’ creative works as one’s own.
> - heavily referencing, copying, or tracing another person’s artwork and claiming it as original.
> - failing to disclose significant references, tracing, or use of another’s work when offering the artwork for sale.

-# **confrontation is __required__.** do be polite as much as possible. if ghosted/blocked upon confrontation, it is considered reportable.
""")
            await interaction.response.send_message(embed=embed, ephemeral=True)
        if self.select_callback.values[0] == "fake event host":
            embed = discord.Embed(colour=0xFF0045, description="""
## <a:redarrow:1388148121242177726>　　　　　fake event host
　　**__definition__**

> users who have hosted events and refused to or repeatedly delayed giving the participant their prize/reward provided that the participant had followed all rules strictly.
> 　⤷　e.g. giveaways, invite rewards.

-# **confrontation is __required__.** do be polite as much as possible. if ghosted/blocked upon confrontation, it is considered reportable.
""")
            await interaction.response.send_message(embed=embed, ephemeral=True)
        if self.select_callback.values[0] == "impersonator":
            embed = discord.Embed(colour=0xFF0045, description="""
## <a:redarrow:1388148121242177726>　　　　　impersonator
　　**__definition__**

> users who deliberately imitate or copy the profile, name, layout and/or description of another user without the real user’s permission, with the intent of deception
> 　⤷　use of another’s identity with malicious intent.

-# **confrontation is __required__.** do be polite as much as possible. if ghosted/blocked upon confrontation, it is considered reportable.
""")
            await interaction.response.send_message(embed=embed, ephemeral=True)
        if self.select_callback.values[0] == "vouch scammer":
            embed = discord.Embed(colour=0xFF0045, description="""
## <a:redarrow:1388148121242177726>　　　　　vouch scammer
　　**__definition__**

> users who use spammed (often botted) vouches or stolen proofs/vouches, with the intent of deceiving others.
> 　⤷　show evidence of vouches left by ≥4 users with similar account creation dates.

　　**__notes__**

> - a server owner may be reported as vouch scammer for allowing spammed vouches in a trading server.
> - neither the vouched user nor voucher are reportable unless there is evidence of them scamming/attempting to scam.

-# **confrontation is __strongly preferred__ and in some cases, required.** do be polite as much as possible. if ghosted/blocked upon confrontation, it is considered reportable.
""")
            await interaction.response.send_message(embed=embed, ephemeral=True)
        if self.select_callback.values[0] == "suspect":
            embed = discord.Embed(colour=0xFFD643, description="""
## <a:yellowarrow:1509836964453548133>　　　　　suspect
　　**__definition__**

> users who have exhibited suspicious behaviour.

　　**__examples__**

> - refusing to use mm or ghosting/blocking after mm is mentioned, especially mms from trusted servers.
> - insisting on using a “personal” mm; insisting on trading via a mm in a group chat.
> - suggesting scam server(s) **and** refusing to use trusted servers or ghosting/blocking when asked to use trusted servers.
> - offering and insisting to mm/pilot without mm/pilot roles in any trading servers.
> - owning a server that is suspected of having scam activity (suspect server).

　　**__notes__**

> - trade must have been agreed to.
> - it is not reportable if
>   - the user unknowingly suggested scam server(s).
>   - the user ghosts or blocks due to the contributor being rude towards them, or due to not being interested in the trade anymore.

-# **confrontation is __strongly preferred__ and in some cases, required.** do be polite as much as possible. if ghosted/blocked upon confrontation, it is considered reportable.
""")
            await interaction.response.send_message(embed=embed, ephemeral=True)
        if self.select_callback.values[0] == "unprofessional mm":
            embed = discord.Embed(colour=0xFFD643, description="""
## <a:yellowarrow:1509836964453548133>　　　　　unprofessional mm
　　**__definition__**

> mm is deemed unprofessional if they have proven to be irresponsible in their service.
> this tag is for mming of lower-risked games, e.g. genshin, hsr, wuwa, hi3, zzz, prsk, roblox accounts or items. 
> 　⤷　usually excludes idv, unless irreversible damage was done to an account due to lack of basic knowledge of the game.

　　**__examples__**

> - items or accounts were put at **preventable, unnecessary and unreasonable** risks
>   - not checking the validity of every receipt sent
>   - not checking basic account details carefully before the account is given to the other trader.
>   - knowingly breaking reasonable service rules of a trading server in which they are a mm, especially rules set in place to ensure the mm’s and traders’ safety.
> - items or accounts were lost, damaged and/or retrieved (i.e. scammed) in a preventable situation
>   - knowingly mming for a scammer, which led to the items/accounts getting lost, damaged and/or retrieved.
>   - incorrectly securing an account, which led to the items/accounts getting lost, damaged and/or retrieved.
>   - altering the state of the account(s) without both traders’ permissions.
> - account was lost, damaged and/or retrieved (i.e. scammed) in an unpreventable situation but the trader was **not** informed of the risks beforehand.
> - mm lost an account in an unpreventable situation but did not attempt to offer any compensation whatsoever.
> - not sending compulsory mm screenshots into the ticket and unable to provide them when needed.
> - not following important steps of the full mm procedure within a trading server in which they are a mm
>   - not sending login and/or logout screenshots within the ticket, unless mm is unable to due to special circumstances.
>   - traders fail to complete mm forms accurately, which creates ambiguity between the accounts/items described and the accounts/items actually secured and traded, and mm failed to resolve the discrepany before proceeding. not reportable if mm is able to prove traders agreed to such changes before proceeding.

　　**__notes__**

> - it is not reportable if
>   - mm lost an account in an unpreventable situation and offered compensation that the trader was satisfied with, or continually attempted to offer compensation, subject to limitations such as the mm’s financial ability.
>   - account was retrieved in an unpreventable situation and the trader consented to the risks beforehand.
>   - low or moderate preventable risks were taken but no harm was done to the account in the end.

""")
            await interaction.response.send_message(embed=embed, ephemeral=True)


closing_options = [
    discord.SelectOption(emoji="<:whiteheart:1434538078747365507>", label="ㆍㆍReport", value="report"),
    discord.SelectOption(emoji="<:whiteheart:1434538078747365507>", label="ㆍㆍAppeal", value="appeal"),
    discord.SelectOption(emoji="<:whiteheart:1434538078747365507>", label="ㆍㆍVerify", value="verify"),
    discord.SelectOption(emoji="<:whiteheart:1434538078747365507>", label="ㆍㆍOthers", value="others"),
    discord.SelectOption(emoji="<:whiteheart:1434538078747365507>", label="ㆍㆍsr+", value="sr+"),
]

@bot.command(name="cl", help="Sends closing guide.")
async def cl(ctx, *, string: str = None):
    if ctx.guild.id == TRI_Archive:
        await ctx.reply(embed=discord.Embed(colour=0xffffff, title = "closing　guide　⸝⸝.ᐟ", description="""
- rename ticket　┈　`,rn 𝐧𝐚𝐦𝐞 tbc`
- ping sr+　┈　`,sr`
- see format for closing statements using the dropdown below.
- please merge identical reasons.
- for mass reports, you may wish to use `,pr` after reports are published to retrieve IDs easily.
        """), view=ClosingView())

class ClosingView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.select(options=closing_options, placeholder="‎　　Select a closing type . . .　　　", custom_id="closing",
                       max_values=1)
    async def select_callback(self, interaction, select):
        if self.select_callback.values[0] == "report":
            await interaction.response.send_message(embed=discord.Embed(description="""
- new report
  - `new report on 𝐢𝐝 as 𝐭𝐚𝐠`
  - `new report on 𝐢𝐝 (alt 𝐢𝐝) as 𝐭𝐚𝐠, 𝐭𝐚𝐠`
- added report
  - `added report on 𝐢𝐝 as 𝐭𝐚𝐠`
- edited alts only
  - `edited alts for 𝐢𝐝 - added 𝐢𝐝 𝐢𝐝, removed 𝐢𝐝`
- edited server owner
  - `server owner edited for 𝐢𝐝`
- insufficient proof
  - `no report on 𝐢𝐝 // insufficient proof`
- deleted user
  - `no report on 𝐢𝐝 // deleted user`
- issue resolved
  - `no report on 𝐢𝐝 // issue resolved`
- unresponsive contributor
  - `no report on 𝐢𝐝 // unresponsive contributor`
- contributor left server
  - `no report on 𝐢𝐝 // contributor left server`
"""), ephemeral=True)
        if self.select_callback.values[0] == "appeal":
            await interaction.response.send_message(embed=discord.Embed(description="""
- accepted appeal
  - `accepted appeal on 𝐢𝐝 as 𝐭𝐚𝐠`
- rejected appeal
  - `no appeal on 𝐢𝐝 // invalid reason`
- insufficient proof
  - `no appeal on 𝐢𝐝 // insufficient proof`
- unresponsive contributor
  - `no appeal on 𝐢𝐝 // unresponsive contributor`
- contributor left server
  - `no appeal on 𝐢𝐝 // contributor left server`
"""), ephemeral=True)
        if self.select_callback.values[0] == "verify":
            await interaction.response.send_message(embed=discord.Embed(description="""
- successful manual verification
  - `𝐢𝐝 manually verified`
- unresponsive contributor
  - `unresponsive contributor`
- contributor left server
  - `contributor left server`
"""), ephemeral=True)
        if self.select_callback.values[0] == "others":
            await interaction.response.send_message(embed=discord.Embed(description="""
- answered question(s)
  - `query answered`
- banned user(s)
  - `no report // banned 𝐢𝐝 for 𝐫𝐞𝐚𝐬𝐨𝐧`
- duplicate/troll ticket
  - `no report`
"""), ephemeral=True)
        if self.select_callback.values[0] == "sr+":
            await interaction.response.send_message(embed=discord.Embed(description="""
- rename ticket
  - `,rn 𝐧𝐚𝐦𝐞 tbc 𝐬𝐫 𝐧𝐚𝐦𝐞`
- check active reports and give feedback
  - `,ar`
- if done correctly, accept reports for voting in order.
- check reports in voting
  - `,vr`
- wait until 5 agree votes before you can publish. 8 agree votes = auto-publish, 12 disagree votes = auto-reject.
- check published reports
  - `,pr` and `,c 𝐢𝐝` or `,mc 𝐢𝐝 𝐢𝐝 𝐢𝐝`
- ask reporter for closing
- `,close` to give ticket credit(s)
- `/close` or click the `Close with Reason` button to close the ticket; input closing as the reason.
"""), ephemeral=True)

@bot.command(name="getids", help="Extracts valid user IDs from the string provided.")
async def getids(ctx, *, string: str = None):
    if string:
        digit_strings = re.findall(r'\d+', string)
        digit_ints = [int(x) for x in digit_strings]
        valid_users = []
        for integer in digit_ints:
            try: user = await bot.fetch_user(integer)
            except Exception: pass
            else:
                valid_users.append(str(user.id))
        if valid_users:
            await ctx.reply(embed=discord.Embed(description=f"`{" ".join(valid_users)}`"))
        else:
            await ctx.reply(f"No valid user IDs found.")

@bot.command(name="ban", help="Pings ban perms.")
@commands.has_any_role(staff_role, tethys_staff_role, professional_mm_role, professional_pilot_role)
async def ban(ctx):
    if ctx.guild.id == TRI_Archive:
        await ctx.reply(f"<@&{ban_perms}>")
    elif ctx.guild.id == tethys:
        await ctx.reply(f"<@&{tethys_ban_perms}>")

@bot.command(name="rn")
@commands.cooldown(2, 600, commands.BucketType.channel)
@commands.has_any_role(staff_role, tethys_staff_role)
async def rn(ctx, *, new_name: str):
    if isinstance(ctx.channel, discord.Thread):
        if ctx.channel.parent_id != TICKET_CHANNEL and ctx.channel.parent_id != TRAINING_CHANNEL:
            return
        try:
            await ctx.channel.edit(name=new_name)
        except Exception as e:
            await ctx.send(f"Renaming failed due to an error: {e}")
    else:
        await ctx.send("This command can only be used in a thread.")
@rn.error
async def rn_error(ctx, error):
    if isinstance(error, commands.CommandOnCooldown):
        remaining = error.retry_after  # cooldown time in seconds
        return await ctx.send(f"This command is on cooldown. Retry in {round(remaining)} seconds.")
    raise error

@bot.command(name='fm', help="Sends a jump url to the first message in the thread.")
@commands.has_any_role(staff_role, tethys_staff_role)
async def fm(ctx):
    if isinstance(ctx.channel, discord.Thread):
        thread = ctx.channel
        first_message = [msg async for msg in thread.history(limit=1, oldest_first=True)]
        if first_message:
            msg = first_message[0]
            embed = discord.Embed(title="First message", description=f"[Jump]({msg.jump_url})", colour=0xffffff)
            await ctx.reply(embed=embed)
    else:
        await ctx.reply("This command can only be used in a thread.")

@bot.command(name="lb", help="Sends the current week’s reports leaderboard.")
@commands.has_any_role(staff_role)
async def lb(ctx, *args):
    if args:
        return
    role_categories = {
        o5_role: ("overseers", []),
        adm_role: ("admins", []),
        sr_role: ("senior reporters", []),
        rep_role: ("reporters", []),
        tr_role: ("trial reporters", [])
    }
    staff_ids = []
    member_map = {}
    for member in ctx.guild.members:
        matched_role = None
        for role_id in role_categories:
            if any(r.id == role_id for r in member.roles):
                matched_role = role_id
                break
        if not matched_role:
            continue
        staff_ids.append(str(member.id))
        member_map[member.id] = (member, matched_role)
    profiles = trusteduserscol.find({"_id": {"$in": staff_ids}})
    weekly_profiles = staffweeklycol.find({"_id": {"$in": staff_ids}})
    profile_map = {p["_id"]: p for p in profiles}
    weekly_map = {p["_id"]: p for p in weekly_profiles}
    for staff_id in staff_ids:
        member, matched_role = member_map[int(staff_id)]
        staff_profile = profile_map.get(staff_id, {})
        weekly_profile = weekly_map.get(staff_id, {})
        reports = staff_profile.get("reports", 0)
        weekly_reports = weekly_profile.get("weekly_reports", 0)
        role_categories[matched_role][1].append(
            (member, reports, weekly_reports)
        )
    embed = discord.Embed(colour=0xffffff, description="")
    for role_id, (title, staff_list) in role_categories.items():
        embed.description += f"\n\n**✦　　┈　　{title}**"
        # optional sorting
        staff_list.sort(key=lambda x: x[2], reverse=True)
        for i, (member, reports, weekly_reports) in enumerate(staff_list, start=1):
            embed.description += (
                f"\n-# {i}ㆍ　"
                f"{member.mention}　–　"
                f"**{reports}** all ㆍ **{weekly_reports}** week")
    await ctx.reply("## _ _　　　reports leaderboard", embed=embed)

@bot.command(name="lbr", help="Sends the current week’s reviews leaderboard.")
@commands.has_any_role(staff_role)
async def lbr(ctx):
    role_categories = {
        o5_role: ("overseers", []),
        adm_role: ("admins", []),
        sr_role: ("senior reporters", [])
    }
    staff_ids = []
    member_map = {}
    for member in ctx.guild.members:
        matched_role = None
        for role_id in role_categories:
            if any(r.id == role_id for r in member.roles):
                matched_role = role_id
                break
        if not matched_role:
            continue
        staff_ids.append(str(member.id))
        member_map[member.id] = (member, matched_role)
    profiles = trusteduserscol.find({"_id": {"$in": staff_ids}})
    weekly_profiles = staffweeklycol.find({"_id": {"$in": staff_ids}})
    profile_map = {p["_id"]: p for p in profiles}
    weekly_map = {p["_id"]: p for p in weekly_profiles}
    for staff_id in staff_ids:
        member, matched_role = member_map[int(staff_id)]
        staff_profile = profile_map.get(staff_id, {})
        weekly_profile = weekly_map.get(staff_id, {})
        reviews = staff_profile.get("reviews", 0)
        weekly_reviews = weekly_profile.get("weekly_reviews", 0)
        role_categories[matched_role][1].append(
            (member, reviews, weekly_reviews)
        )
    embed = discord.Embed(colour=0xffffff, description="")
    for role_id, (title, staff_list) in role_categories.items():
        embed.description += f"\n\n**✦　　┈　　{title}**"
        staff_list.sort(key=lambda x: x[2], reverse=True)
        for i, (member, reviews, weekly_reviews) in enumerate(staff_list, start=1):
            embed.description += (
                f"\n-# {i}ㆍ　"
                f"{member.mention}　–　"
                f"**{reviews}** all ㆍ **{weekly_reviews}** week")
    await ctx.reply("## _ _　　　reviews leaderboard", embed=embed)


@bot.tree.command(name="break", description="Toggle full or half break.")
@app_commands.checks.has_role(staff_role)
async def break_command(interaction: discord.Interaction, type: Literal["full", "half"]):
    await interaction.response.defer()
    member = interaction.user
    guild = interaction.guild
    if get(member.roles, id=t_role):
        return await interaction.followup.send("In training staff cannot go on break.")
    profile = staffweeklycol.find_one({"_id": str(member.id)})
    if profile:
        profile.setdefault("breakbal", 12)
        profile.setdefault("saved_roles", [])
        breakbal = profile["breakbal"]
        cost = 1 if type == "full" else 0.5
        if breakbal - cost < 0:
            return await interaction.followup.send(
                f"You do not have enough break balance.\nCurrent balance: **{breakbal}**")
        full_break_role = guild.get_role(full_break)
        half_break_role = guild.get_role(half_break)
        archived_staff_role = guild.get_role(archived_staff)
        ticket_ping_role = guild.get_role(ticket_ping)
        current_break = None
        if member.get_role(full_break):
            current_break = "full"
        elif member.get_role(half_break):
            current_break = "half"
        if current_break == type:
            remove_roles = [archived_staff_role]
            if member.get_role(full_break):
                remove_roles.append(full_break_role)
            if member.get_role(half_break):
                remove_roles.append(half_break_role)
            await member.remove_roles(*remove_roles)
            restore_roles = []
            for rid in profile.get("saved_roles", []):
                role = guild.get_role(rid)
                if role:
                    restore_roles.append(role)
            restore_roles.append(ticket_ping_role)
            await member.add_roles(*restore_roles)
            profile["saved_roles"] = []
            staffweeklycol.replace_one({"_id": str(member.id)}, profile, upsert=True)
            return await interaction.followup.send("You are now off break.")
        elif current_break:
            if current_break == "full":
                remove_roles = [full_break_role, archived_staff_role]
                await member.remove_roles(*remove_roles)
                restore_roles = []
                for rid in profile.get("saved_roles", []):
                    role = guild.get_role(rid)
                    if role:
                        restore_roles.append(role)
                restore_roles.append(ticket_ping_role)
                await member.add_roles(*restore_roles)
                profile["saved_roles"] = []
                staffweeklycol.replace_one({"_id": str(member.id)}, profile, upsert=True)
                await member.add_roles(half_break_role)
            elif current_break == "half":
                await member.remove_roles(half_break_role)
                await member.add_roles(full_break_role)
                saved_roles = []
                remove_roles = []
                for rid in STAFF_ROLES:
                    role = guild.get_role(rid)
                    if role and member.get_role(rid):
                        saved_roles.append(rid)
                        remove_roles.append(role)
                if member.get_role(ticket_ping):
                    remove_roles.append(ticket_ping_role)
                if remove_roles:
                    await member.remove_roles(*remove_roles)
                profile["saved_roles"] = saved_roles
                staffweeklycol.replace_one({"_id": str(member.id)}, profile, upsert=True)
            return await interaction.followup.send(f"Changed break status to **{type} break**.")
        else:
            if type == "full":
                await member.add_roles(full_break_role)
                saved_roles = []
                remove_roles = []
                for rid in STAFF_ROLES:
                    role = guild.get_role(rid)
                    if role and member.get_role(rid):
                        saved_roles.append(rid)
                        remove_roles.append(role)
                if member.get_role(ticket_ping):
                    remove_roles.append(ticket_ping_role)
                if remove_roles:
                    await member.remove_roles(*remove_roles)
                profile["saved_roles"] = saved_roles
                staffweeklycol.replace_one({"_id": str(member.id)}, profile, upsert=True)
            if type == "half":
                await member.add_roles(half_break_role)
            await interaction.followup.send(f"You are now on **{type} break**.")
    else:
        return await interaction.followup.send("User not appointed as current TRI Staff.")

# slash commands

staff = app_commands.Group(name="staff", description="Staff.")
bot.tree.add_command(staff)

@staff.command(name="accepted", description="Assigns trainee roles to accepted staff.")
@app_commands.checks.has_role(adm_ping)
@app_commands.describe(user="User to assign roles.")
async def staff_accepted(interaction: discord.Interaction, user: discord.Member):
    try:
        await user.add_roles(interaction.guild.get_role(int(t_role)), interaction.guild.get_role(int(staff_role)))
        await user.edit(nick=f"tㆍ{user.display_name}")
    except:
        return await interaction.response.send_message("Unable to assign trainee roles to the user.")
    else:
        await interaction.response.send_message("Successfully assigned trainee roles to the user.")

send = app_commands.Group(name="send", description="Send embeds/rules/guides.")
bot.tree.add_command(send)

class StaffRulesView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(discord.ui.Button(label="Staff Legal Codex", style=discord.ButtonStyle.grey,
                                        url="https://docs.google.com/document/d/18GPfRrvzJ4b1d6cJ_yLyd1HELJbE4y9PqBH5-FVQktc/"))

staff_guide_options = [
    discord.SelectOption(emoji="<:whiteheart:1434538078747365507>", label="ㆍㆍTrial", value="trial"),
    discord.SelectOption(emoji="<:whiteheart:1434538078747365507>", label="ㆍㆍBreaks", value="breaks"),
    discord.SelectOption(emoji="<:whiteheart:1434538078747365507>", label="ㆍㆍQuota", value="quota"),
    discord.SelectOption(emoji="<:whiteheart:1434538078747365507>", label="ㆍㆍTickets", value="tickets"),
    discord.SelectOption(emoji="<:whiteheart:1434538078747365507>", label="ㆍㆍAutoresponders", value="autoresponders"),
]

class StaffGuideView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.select(options=staff_guide_options, placeholder="‎　　Select a guide topic . . .　　　", custom_id="guide",
                       max_values=1)
    async def select_callback(self, interaction, select):
        if self.select_callback.values[0] == "trial":
            await interaction.response.send_message(embed=discord.Embed(description="""
### Trial Period
- **14–90 days**
- Exceeding 90 days results in an **unappealable demotion** (you may reapply)
- **Asking questions is encouraged** and will not affect your status
- **No breaks in the first 14 days** unless it’s an emergency
### Promotion Requirements
- **2 weeks of quota** (not necessarily consecutive)
- **10 non-hitter report tickets**
- **1 appeal ticket**
- **20 votes**
            """), ephemeral=True)
        if self.select_callback.values[0] == "breaks":
            await interaction.response.send_message(embed=discord.Embed(description="""
### Break Types
- **Half Break** — weekly quota is **halved (rounded down)**
- **Full Break** — weekly quota is **not counted**
### Break Rules
- Staff **cannot earn Annual Leave** while on break
- **1 Full Break** may be split into **2 Half Breaks**
### Annual Leave
- Includes **all types of leave**
- Basic entitlement: **12 Full Breaks**
- **1/8 Full Break** for each **week of completed quota**
            """), ephemeral=True)
        if self.select_callback.values[0] == "quota":
            await interaction.response.send_message(embed=discord.Embed(description="""
### Quota Basics
- Weekly quota ranges between **5–10 reports/appeals**
- Only **successfully published** reports/appeals are counted
- Hitter reports count toward quota but have **low promotion value**
### Strikes
- Each week of **incomplete quota** while **not on a Full Break = 1 strike**
### Consequences for Incomplete Quota
- **Demotion in rank:**
  - 2 consecutive strikes with **no breaks taken**
  - 3 consecutive strikes with **≤ 1 Full Break** taken in total
  - 4 or more strikes (not necessarily consecutive) within the **past 8 weeks**
- **Demotion from Staff:**
  - Average activity of **below 50%** over the **past 8 weeks**
  - Full Break weeks are **excluded** from calculation, but Half Break weeks are **included**
  - Activity is measured by **quota fulfilled**, capped at **100% per week**
            """), ephemeral=True)
        if self.select_callback.values[0] == "tickets":
            await interaction.response.send_message(embed=discord.Embed(description="""
### Ticket Claiming
- The **first Staff** to send a proper greeting (e.g. hi) handles the ticket
- If multiple greetings are sent, **reload Discord** to see who was first
- Other Staff must **delete their messages**
### Ticket Handling
- Only **one Staff** may handle a ticket at a time
- A **Defender** may assist if required
- Only **one Senior Reporter** may review when requested
- After acceptance for voting, the **sr+ who publishes** the report is responsible for **closing the ticket**
### Ticket Priority
- Handle **older tickets first**
- Do not skip tickets because they seem difficult
### Ticket Limits
- **Trial Reporter** — 1 active, 2 on-hold, 1 self ticket
- **Reporter** — 2 active, 2 on-hold, 1 self ticket
- If an on-hold ticket becomes active and exceeds your limit, you must **open one active ticket to other Staff**
### On-Hold
- Staff may place **their own tickets** on hold when necessary
- Common reasons include:
  - Waiting for Defendant response
  - Waiting for Contributor response
- Abuse of on-hold may result in **warnings or demotion**
### Ticket Closure
- If the Contributor does not reply within **12 hours**, you may request closure
- If no meaningful proof is provided within **4 hours**, you may request closure
            """), ephemeral=True)
        if self.select_callback.values[0] == "autoresponders":
            await interaction.response.send_message(embed=discord.Embed(description="""
### ,adm
- Pings adm+.
### ,sr
- Pings sr+.
### ,tp
- Pings ticket ping, e.g. when you want open a ticket to other Staff.
### ,ban
- Pings ban perms.
### ,cl
- Sends closing guide.
### ,tags
- Sends tags descriptions.
                """), ephemeral=True)

@send.command(name="staffrules", description="Sends staff rules.")
@app_commands.checks.has_role(adm_ping)
async def send_staffrules(interaction: discord.Interaction):
    await interaction.channel.send(embed=discord.Embed(colour=0xffffff, description="""
## <:2paperclip:1449650494044639335>　　staff　　rules　　ꫂ᭪
### Follow Server Rules
- Adhere to all [server rules](https://discord.com/channels/1371673839695826974/1371674470611161160)
- Particular focus on **No Discrimination**, **No Hate or Threats**, and **No NSFW Content**
### Confidentiality
- Follow the Non-Disclosure Agreement (NDA)
- Violation may result in immediate removal from Staff, a report as Unprofessional Staff, and/or a server ban depending on severity
### Ticket Protocol
- Only one Staff should handle a ticket at a time, unless a Defender is required
- Do not hijack tickets assigned to others
- Avoid tickets where you are related to the Defendant
- Keep communication on-topic and case-related; no side-chatting
- When handling multiple reports in a ticket, address one at a time in order
### Professionalism
- Reports on Staff may result in quarantine and demotion if accepted
- Speaking negatively about ticket participants or Staff (current or former) is Unprofessional and will be addressed
### Respect
- Remain respectful, even toward those you dislike
- Personal feelings are not an excuse for rudeness or unprofessional behavior
### No Inappropriate Jokes
- Jokes about ||suicide||, ||self-harm||, or ||body shaming|| (e.g., "||kys||", "||fat||", "||keep yourself safe||") are strictly prohibited
- Even if said without ill-intention, these are not acceptable as they may make others uncomfortable
### No Drama
- Keep personal conflicts out of the server
- Resolve issues privately and respectfully, or seek proper mediation
### No Favouritism
- Do not excessively praise, defend, or favour specific individuals
- Favoritism that undermines neutrality, decision-making, or report handling is prohibited
"""), view=StaffRulesView())
    await interaction.response.send_message("Staff Rules have been sent.", ephemeral=True)

@send.command(name="staffguide", description="Sends staff guide.")
@app_commands.checks.has_role(adm_ping)
async def send_staffguide(interaction: discord.Interaction):
    await interaction.channel.send(embed=discord.Embed(colour=0xffffff, description="""
## <:whitebow:1388714593211125971>　　staff　　guide　　ꫂ᭪
　　`,help` for list of TRI bots commands.
"""), view=StaffGuideView())
    await interaction.response.send_message("Staff Guide has been sent.", ephemeral=True)

@send.command(name="rules", description="Sends server rules.")
@app_commands.checks.has_role(adm_ping)
async def send_rules(interaction: discord.Interaction, colour: str=None, image: discord.Attachment=None):
    await interaction.response.defer(ephemeral=True)
    colour = discord.Colour(int(colour.strip("#"), 16)) if colour else 0xffffff
    if image:
        image_embed = discord.Embed(colour=colour)
        image_embed.set_image(url=image.url)
        await interaction.channel.send("_ _", embed=image_embed)
    embed1 = discord.Embed(colour=colour, title="_ _　　✦，　〝　general　guidelines　◝", description="""
**　⸝⸝⊹　follow discord [tos](https://discord.com/terms) and [gls](https://discord.com/guidelines)ㆍ**
╴read discord terms of service & guidelines fully to ensure you don’t break them.

**　⊹⸝⸝　be respectful﹐strictly no hateㆍ**
╴be civil, any form of harassment, discrimination, bullying, etc will not be tolerated.

**　⸝⸝⊹　do not reveal or ask for personal infoㆍ**
╴this includes other’s info and your own, please do not share too much for your own and others' safety.

**　⊹⸝⸝　no plagiarismㆍ**
╴inspiration is allowed but do not plagiarise any content, please give proper credits.

**　⊹⸝⸝　respect the staff﹐open a ticket for help ／ concernsㆍ**
╴listen to staff and respect them, do not block them as they are here to help you. if you have concerns, need help or would like to report someone who broke the rules please open a ticket and do not deal with the problem yourself.

**　⸝⸝⊹　no ads ／ self - promo﹙includes dms﹚ㆍ**
╴any form of self promotion is strictly __prohibited__.
    """)
    await interaction.channel.send("_ _", embed=embed1)
    embed2 = discord.Embed(colour=colour, title="_ _　　✦，　〝　language　etiquette　◝", description="""
**　⸝⸝⊹　nsfw is strictly prohibitedㆍ**
╴includes both images and nsfw text, this is a public server and minors are present.

**　⊹⸝⸝　no excessive swearing﹐or slursㆍ**
╴swearing is alright, as long as it isn’t unnecessarily excessive or targeted towards someone in a serious matter. slurs will strictly result in an immediate ban, even if it is reclaimable by you.

**　⸝⸝⊹ 　do not spam anything for any reasonㆍ**
╴this includes text, images, pings, etc..
    """)
    await interaction.channel.send("_ _", embed=embed2)
    embed3 = discord.Embed(colour=colour, title="_ _　　✦，　〝　reporting　don’ts　◝", description="""
**　⸝⸝⊹　no false reportsㆍ**
╴falsely reporting someone and producing fake evidence will result in a ban.

**　⸝⸝⊹　no briberyㆍ**
╴any attempt to bribe someone or any attempt to take a bribe, is strictly prohibited.
    """)
    await interaction.channel.send("_ _", embed=embed3)
    embed4 = discord.Embed(colour=colour, description="""
**　ㆍ<:whitebow:1388714593211125971>　full version of rules [here](https://docs.google.com/document/d/1ef3bb0l1EdXELcAbLDT7QOXFwbQco-600G-4HE6E7KM/edit?pli=1&tab=t.0#heading=h.1qtqm2f0dk9x)　♪**
    """)
    await interaction.channel.send("_ _", embed=embed4)
    await interaction.followup.send("Sent!")


@send.command(name="reactroles", description="Sends react roles embeds.")
@app_commands.checks.has_role(adm_ping)
async def send_reactroles(interaction: discord.Interaction, colour: str=None, image: discord.Attachment=None):
    await interaction.response.defer(ephemeral=True)
    colour = discord.Colour(int(colour.strip("#"), 16)) if colour else 0xffffff
    if image:
        image_embed = discord.Embed(colour=colour)
        image_embed.set_image(url=image.url)
        await interaction.channel.send("_ _", embed=image_embed)
    await interaction.channel.send("""
_ _
_ _　　<:cutie:1388714793585606656>ㆍ**claim  roles  here** ㆍㆍ
-# <:greyreply:1448474301673115748>　click  for  the  role ,  click  again  to  remove .
""")
    embed1 = discord.Embed(colour=colour, title="★．．　age　range　⊹⁺₊", description="""  
-# _ _
　❜ <:whiteheart:1434538078747365507> ㆍ18 +　︵
　 <:whitebow:1388714593211125971> ㆍ16 — 17　❜
　❜ <:whitestar:1388147381152911381> ㆍ13 — 15　︵
""")
    msg1 = await interaction.channel.send("_ _", embed=embed1)
    embed2 = discord.Embed(colour=colour, title="★．．　pronouns　⊹⁺₊", description="""  
-# _ _
　┅ <:whitebutterfly:1459750881611354237> ㆍhe 　❀
　 <:whitepaperclip:1449650494044639335> ㆍ she 　┅
　┅ <:whitestar:1388147381152911381> ㆍthey 　❀
　 <:whitebowheart:1459750975710691410> ㆍ ask 　┅
    """)
    msg2 = await interaction.channel.send("_ _", embed=embed2)
    embed3 = discord.Embed(colour=colour, title="★．．　pings　⊹⁺₊", description="""  
-# _ _
　∿ <:whitestar:1388147381152911381> ㆍnew user report　⿻
　 <:whitebow:1388714593211125971> ㆍupdated user report　∿
　∿ <:whitepaperclip:1449650494044639335> ㆍappealed user report　⿻
　 <:whiteheart:1434538078747365507> ㆍnew server report　∿
　∿ <:whitebutterfly:1459750881611354237> ㆍupdated server report　⿻
　 <:whitebowheart:1459750975710691410> ㆍappealed server report　∿
""")
    msg3 = await interaction.channel.send("_ _", embed=embed3)
    embed4 = discord.Embed(colour=colour, description="""  
-# _ _
　⬩ <:whitebutterfly:1459750881611354237> ㆍnews　✿
　 <:whitebow:1388714593211125971> ㆍticket status　⬩
    """)
    msg4 = await interaction.channel.send("_ _", embed=embed4)
    await interaction.followup.send("Sent!")
    await interaction.followup.send(f"""
Use the following commands to add react roles:

`!rr addmany {interaction.channel.id} {msg1.id}
<:whiteheart:1434538078747365507> 1375276990096998440 
<:whitebow:1388714593211125971> 1375277014679818332 
<:whitestar:1388147381152911381> 1375277046204203148`

`!rr addmany {interaction.channel.id} {msg2.id}
<:whitebutterfly:1459750881611354237> 1375274759507411034
<:whitepaperclip:1449650494044639335> 1375274745616011355
<:whitestar:1388147381152911381> 1375274890894250045
<:whitebowheart:1459750975710691410> 1375274908275445780`

`!rr addmany {interaction.channel.id} {msg3.id}
<:whitestar:1388147381152911381> 1375275062185168957
<:whitebow:1388714593211125971> 1459590866724323625
<:whitepaperclip:1449650494044639335> 1459590865335877663
<:whiteheart:1434538078747365507> 1375275002537971742
<:whitebutterfly:1459750881611354237> 1459590362703204405 
<:whitebowheart:1459750975710691410> 1459590364292972776`

`!rr addmany {interaction.channel.id} {msg4.id}
<:whitebutterfly:1459750881611354237> 1375276744956706916
<:whitebow:1388714593211125971> 1459594319110602833`

""", ephemeral=True)


@send.command(name="faq", description="Sends faq.")
@app_commands.checks.has_role(adm_ping)
async def send_faq(interaction: discord.Interaction, colour: str=None, image: discord.Attachment=None):
    await interaction.response.defer(ephemeral=True)
    colour = discord.Colour(int(colour.strip("#"), 16)) if colour else 0xffffff
    if image:
        image_embed = discord.Embed(colour=0xffffff)
        image_embed.set_image(url=image.url)
        await interaction.channel.send("_ _", embed=image_embed)
    embed1 = discord.Embed(colour=colour, description="""
### <:blank:1383116055550890095>–　what is tri?

> - trade report investigation archive (**tri archive**) est. may 2025 is a server dedicated to **spreading awareness on dangerous, unlawful, or suspicious activity**, while also **commending outstanding mms/pilots and trusted traders** for upholding integrity and professionalism.
> - we also aim to **hold unprofessional behaviour accountable**, especially among staff members entrusted with positions of responsibility within the trading community.

　　**__why tri?__**

> - we have over 20 tags to report users and servers as accurately as possible.
> - we accept a wide range of reports, not only on scammers and suspects but also on dangerous or blacklisted individuals such as raiders, plagiarists or unprofessional staff. when in doubt, feel free to open a ticket to ask.
""")
    msg1 = await interaction.channel.send("_ _", embed=embed1)
    embed2 = discord.Embed(colour=colour, description="""
### <:blank:1383116055550890095>–　how to check users or servers?

> - `,c` to check; `,c [user id]` or `,c [invite]`
> - how to obtain user id? guide [here](https://support.discord.com/hc/en-us/articles/206346498-Where-can-I-find-my-User-Server-Message-ID).

　　**__examples__**

> - `,c 1450073025818136598`
> - `,c` <@1450073025818136598>
> - `,c tri`
> - `,c https://discord.gg/tri`

""")
    msg2 = await interaction.channel.send("_ _", embed=embed2)
    embed3 = discord.Embed(colour=colour, description="""
### <:blank:1383116055550890095>–　how to stay updated with tri’s reports?

> - follow tri’s report announcement channels <#1375132097605406721> and <#1375184563675856916> to receive updates in your own server.
> - how to follow a channel? guide [here](https://support.discord.com/hc/en-us/articles/360028384531-Channel-Following-FAQ).

> - add tri’s bot <@1457249982104211467> to your server by clicking **add app** on the bot’s profile, or click [here](https://discord.com/oauth2/authorize?client_id=1457249982104211467).
> - `,c` to check users or servers using <@1457249982104211467>.
> - `/check all` to check your server for users with bannable reports.
""")
    msg3 = await interaction.channel.send("_ _", embed=embed3)
    embed4 = discord.Embed(colour=colour, description=f"""
### <:blank:1383116055550890095>–　how to make a report?

> - <#1375261699111784478> to make a report.
> - please ensure you have the accused user id or server invite. how to obtain user id? guide [here](https://support.discord.com/hc/en-us/articles/206346498-Where-can-I-find-my-User-Server-Message-ID).
> - please also check if the accused has been reported recently (within the past 6 months) for similar reasons.
> - provide **uncropped**, **unedited** screenshots or screen recordings from **top to bottom** as far as possible.
> - [how to check users or servers?]({msg2.jump_url})

""")
    msg4 = await interaction.channel.send("_ _", embed=embed4)
    embed5 = discord.Embed(colour=colour, description=f"""
### <:blank:1383116055550890095>–　how to make an appeal?

> - <#1375261699111784478> to make an appeal if you believe your report is inaccurate or unfair, or if you have served minimum report period (mrp) as stated in [legal codex](https://docs.google.com/document/d/1ef3bb0l1EdXELcAbLDT7QOXFwbQco-600G-4HE6E7KM/).
> - note that appeals based on mrp are not guaranteed and will be reviewed on a case by case basis.
> - please provide all relevant information that may prove your report to be inaccurate or unfair.
> - you may request for a staff to be your defender i.e. argue in favour of your appeal. however, defenders will remain unbiased, and appeals will still be judged based on the facts and evidence presented.
""")
    msg5 = await interaction.channel.send("_ _", embed=embed5)
    embed6 = discord.Embed(colour=colour, description=f"""
### <:blank:1383116055550890095>–　what is tri’s tos, server rules and ban policy?
> - our terms of service may be found [here](https://docs.google.com/document/d/1ef3bb0l1EdXELcAbLDT7QOXFwbQco-600G-4HE6E7KM/edit?tab=t.0#heading=h.d0k3z1hwlns).
> - please read through [server rules](https://discord.com/channels/1371673839695826974/1371674470611161160) carefully. not following rules may result in warns or bans.

　　**__ban policy__**

> - we do not ban scammers so that they may make an appeal.
> **what do we ban?**
> - not following discord [tos](https://discord.com/terms) or [guidelines](https://discord.com/guidelines).
> - racist, sexist, homophobic, xenophobic, or similar slurs and sentiments
> - targeted hate, threats of violence, doxxing, or sharing private info.
> - false or malicious reports. this includes editing proofs.
> - advertising products, services, events, or servers.
> - attempting to bribe or gain favors from staff, even outside the server.
> - nsfw material, even if mentioned as a joke.

""")
    msg6 = await interaction.channel.send("_ _", embed=embed6)
    embed = discord.Embed(colour=colour, description=f"""
<:blank:1383116055550890095>–　[what is tri?]({msg1.jump_url})
-# <:blank:1383116055550890095>
<:blank:1383116055550890095>–　[how to check users or servers?]({msg2.jump_url})
-# <:blank:1383116055550890095>
<:blank:1383116055550890095>–　[how to stay updated with tri’s reports?]({msg3.jump_url})
-# <:blank:1383116055550890095>
<:blank:1383116055550890095>–　[how to make a report?]({msg4.jump_url})
-# <:blank:1383116055550890095>
<:blank:1383116055550890095>–　[how to make an appeal?]({msg5.jump_url})
-# <:blank:1383116055550890095>
<:blank:1383116055550890095>–　[what is tri’s tos, rules and ban policy?]({msg6.jump_url})
""")
    await interaction.channel.send("_ _", embed=embed)
    await interaction.followup.send("Sent!", ephemeral=True)

@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@app_commands.user_install()
@app_commands.guild_install()
class AnonGroup(app_commands.Group):
    def __init__(self):
        super().__init__(name="anon", description="Do something anonymously.")

anon = AnonGroup()
bot.tree.add_command(anon)

@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@app_commands.user_install()
@app_commands.guild_install()
@anon.command(name="say", description="MIKU will speak on your behalf.")
@app_commands.checks.cooldown(1, 5)
@app_commands.describe(message="Your message", image1="Image 1 (optional)", image2="Image 2 (optional)", image3="Image 3 (optional)", image4="Image 4 (optional)", image5="Image 5 (optional)", image6="Image 6 (optional)", image7="Image 7 (optional)", image8="Image 8 (optional)", image9="Image 9 (optional)", image10="Image 10 (optional)")
async def anon_say(interaction: discord.Interaction, message: str, image1: Optional[discord.Attachment], image2: Optional[discord.Attachment], image3: Optional[discord.Attachment], image4: Optional[discord.Attachment], image5: Optional[discord.Attachment], image6: Optional[discord.Attachment], image7: Optional[discord.Attachment], image8: Optional[discord.Attachment], image9: Optional[discord.Attachment], image10: Optional[discord.Attachment]):
    await interaction.response.defer(ephemeral=True)
    if interaction.guild and interaction.guild.id == TRI_Archive and not any(role.id in (staff_role, tethys_adm_role) for role in interaction.user.roles):
        return await interaction.followup.send("You are unauthorised to use this command.")
    try:
        images = [img for img in [image1, image2, image3, image4, image5, image6, image7, image8, image9, image10]
                  if img is not None]
        files_to_send = []
        async with aiohttp.ClientSession() as session:
            for img in images:
                if img.content_type and img.content_type.startswith('image/'):
                    async with session.get(img.url) as resp:
                        if resp.status == 200:
                            data = io.BytesIO(await resp.read())
                            files_to_send.append(discord.File(data, filename=img.filename))
        message = message.replace("\\n", "\n")
        if not interaction.guild or interaction.guild.id != TRI_Archive:
            await interaction.followup.send("Your message has been sent.", ephemeral=True)
            return await interaction.followup.send(content=message, files=files_to_send, ephemeral=False)
        elif get(interaction.user.guild.roles, id=adm_ping) in interaction.user.roles or get(interaction.user.guild.roles, id=tethys_adm_role) in interaction.user.roles:
            if files_to_send:
                await interaction.channel.send(content=message, files=files_to_send)
            else:
                await interaction.channel.send(message)
        else:
            for word in banned_words:
                message = message.replace(word, "*" * len(word))
            if files_to_send:
                await interaction.channel.send(content=message, files=files_to_send, allowed_mentions=discord.AllowedMentions(everyone=False, roles=False))
            else:
                await interaction.channel.send(message, allowed_mentions=discord.AllowedMentions(everyone=False, roles=False))
        print(f"{interaction.user.name}: {message}")
        await interaction.followup.send("Your message has been sent.", ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f"Unable to send message: {e}", ephemeral=True)

@anon.error
async def anon_error(interaction: discord.Interaction, error):
    if isinstance(error, app_commands.CommandOnCooldown):
        remaining = round(error.retry_after)
        if interaction.response.is_done():
            await interaction.followup.send(f"This command is on cooldown. Retry in {remaining} seconds.", ephemeral=True)
        else:
            await interaction.response.send_message(f"This command is on cooldown. Retry in {remaining} seconds.", ephemeral=True)
        return
    raise error

@anon.command(name="edit", description="Edit MIKU’s message.")
@app_commands.checks.cooldown(2, 5)
@app_commands.describe(message_id="The message to edit", message="Your message", image1="Image 1 (optional)", image2="Image 2 (optional)", image3="Image 3 (optional)", image4="Image 4 (optional)", image5="Image 5 (optional)", image6="Image 6 (optional)", image7="Image 7 (optional)", image8="Image 8 (optional)", image9="Image 9 (optional)", image10="Image 10 (optional)")
async def anon_edit(interaction: discord.Interaction, message_id: str, message: str, image1: Optional[discord.Attachment] = None, image2: Optional[discord.Attachment] = None, image3: Optional[discord.Attachment] = None, image4: Optional[discord.Attachment] = None, image5: Optional[discord.Attachment] = None, image6: Optional[discord.Attachment] = None, image7: Optional[discord.Attachment] = None, image8: Optional[discord.Attachment] = None, image9: Optional[discord.Attachment] = None, image10: Optional[discord.Attachment] = None):
    await interaction.response.defer(ephemeral=True)
    if interaction.guild and not any(role.id in (adm_ping, tethys_adm_role) for role in interaction.user.roles):
        return await interaction.followup.send("You are unauthorised to use this command.")
    if not interaction.guild and interaction.channel_id is None:
        return await interaction.followup.send("Discord limitations prevent editing old messages in DMs.")
    try:
        target_message = await interaction.channel.fetch_message(int(message_id))
        if target_message.author.id != bot.user.id:
            await interaction.followup.send("I can only edit messages sent by the bot.", ephemeral=True)
            return
        images = [img for img in [image1, image2, image3, image4, image5, image6, image7, image8, image9, image10]
                  if img is not None]
        files_to_send = []
        async with aiohttp.ClientSession() as session:
            for img in images:
                if img.content_type and img.content_type.startswith("image/"):
                    async with session.get(img.url) as resp:
                        if resp.status == 200:
                            data = io.BytesIO(await resp.read())
                            files_to_send.append(discord.File(data, filename=img.filename))
        message = message.replace("\\n", "\n")
        allowed_mentions = discord.AllowedMentions.all()
        if files_to_send:
            await target_message.edit(content=message, attachments=files_to_send, allowed_mentions=allowed_mentions)
        else:
            await target_message.edit(content=message, allowed_mentions=allowed_mentions)
        await interaction.followup.send("Message edited successfully.", ephemeral=True)
    except discord.NotFound:
        await interaction.followup.send("Message not found.", ephemeral=True)
    except discord.Forbidden:
        await interaction.followup.send("Missing permissions to edit message.", ephemeral=True)
    except Exception as e:
        await interaction.followup.send(f"Unable to edit message.\n```{e}```", ephemeral=True)

create = app_commands.Group(name="create", description="Create.")
bot.tree.add_command(create)

@create.command(name="training", description="Creates a training thread.")
@app_commands.describe(name="Name of trainee", user_id="User ID of trainee")
@app_commands.checks.has_role(adm_ping)
async def create_training(interaction: discord.Interaction, name: str, user_id: str):
    if interaction.channel.id == TRAINING_CHANNEL:
        try:
            user = await bot.fetch_user(int(user_id.strip('<@>')))
        except Exception as e:
            await interaction.response.send_message(f"An error occurred: {e}", ephemeral=True)
        else:
            new_thread = await interaction.channel.create_thread(
                name=f"t {name}",
                type=discord.ChannelType.private_thread,
                auto_archive_duration=10080
            )
            await interaction.response.send_message(f"Created a new private thread: {new_thread.jump_url}", ephemeral=True)
            await new_thread.send(f"{user.mention} <@&{staff_trainer}>")

# file

class FileModal(discord.ui.Modal, title="Create File"):
    user_id = discord.ui.TextInput(label="User ID", placeholder="Enter the user ID", required=True)
    async def on_submit(self, interaction: discord.Interaction):
        try:
            user = await bot.fetch_user(int(self.user_id.value))
        except Exception:
            await interaction.response.send_message("Invalid user ID.", ephemeral=True)
            return
        # Create public thread
        thread = await interaction.channel.create_thread(name=str(user.id), type=discord.ChannelType.public_thread)
        try:
            starter_message = await interaction.channel.fetch_message(thread.id)
            await starter_message.delete()
        except Exception:
            pass
        embed = discord.Embed(color=0xffffff)
        embed.add_field(name="User ID", value=str(user.id), inline=True)
        embed.add_field(name="Username", value=str(user.name), inline=True)
        embed.add_field(name="Tag(s)", value="", inline=False)
        embed.add_field(name="Reason", value="", inline=False)
        embed.add_field(name="Link to thread", value=thread.mention, inline=False)
        embed.set_footer(
            text=f"Last edited by {interaction.user}",
            icon_url=interaction.user.display_avatar.url
        )
        msg = await interaction.channel.send(embed=embed, view=FileView())
        filescol.insert_one({
            "_id": msg.id,
            "thread_id": thread.id
        })
        await interaction.response.send_message(f"File created for `{user.id}`.", ephemeral=True)

class EditFileModal(discord.ui.Modal, title="Edit File"):
    tags = discord.ui.TextInput(label="Tags", required=False, style=discord.TextStyle.short)
    reason = discord.ui.TextInput(label="Reason", required=False, style=discord.TextStyle.paragraph)
    def __init__(self, message: discord.Message):
        super().__init__()
        self.message = message
        embed = message.embeds[0]
        current_tags = embed.fields[2].value or ""
        current_reason = embed.fields[3].value or ""
        self.tags.default = current_tags
        self.reason.default = current_reason

    async def on_submit(self, interaction: discord.Interaction):
        embed = self.message.embeds[0]
        embed.set_field_at(
            2,
            name="Tag(s)",
            value=self.tags.value or "",
            inline=False
        )
        embed.set_field_at(
            3,
            name="Reason",
            value=self.reason.value or "",
            inline=False
        )
        embed.set_footer(text=f"Last edited by {interaction.user}", icon_url=interaction.user.display_avatar.url)
        await self.message.edit(embed=embed)
        await interaction.response.send_message("File updated.", ephemeral=True)

class ConfirmCloseView(discord.ui.View):
    def __init__(self, message_id: int):
        super().__init__(timeout=60)
        self.message_id = message_id
    @discord.ui.button(
        label="Confirm Close",
        style=discord.ButtonStyle.red
    )
    async def confirm_close(self, interaction: discord.Interaction, button: discord.ui.Button):
        if get(interaction.user.guild.roles, id=adm_ping) not in interaction.user.roles:
            await interaction.response.send_message("You do not have permission.", ephemeral=True)
            return
        data = filescol.find_one({"_id": self.message_id})
        if not data:
            await interaction.response.send_message("File data missing.", ephemeral=True)
            return
        thread = interaction.guild.get_thread(data["thread_id"])
        if thread:
            try:
                message = await interaction.channel.fetch_message(self.message_id)
                if message.embeds:
                    await thread.send(embed=message.embeds[0])
            except Exception: pass
            await thread.edit(archived=True, locked=True)
        try:
            message = await interaction.channel.fetch_message(self.message_id)
            await message.delete()
        except Exception:
            pass
        filescol.delete_one({"_id": self.message_id})
        await interaction.response.send_message("File closed.", ephemeral=True)

class FileView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Edit", style=discord.ButtonStyle.grey, custom_id="file_edit")
    async def edit_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(EditFileModal(interaction.message))

    @discord.ui.button(label="Close", style=discord.ButtonStyle.red, custom_id="file_close")
    async def close_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if get(interaction.user.guild.roles, id=adm_ping) not in interaction.user.roles:
            await interaction.response.send_message("You do not have permission.", ephemeral=True)
            return
        await interaction.response.send_message("Are you sure you want to close this file?", ephemeral=True,
            view=ConfirmCloseView(interaction.message.id))

@create.command(name="file", description="Creates a file.")
async def create_file(interaction: discord.Interaction):
    allowed_channels = [
        1503250889031418056,
        1503248643338272861,
        1503621921076674726
    ]
    if interaction.channel.id not in allowed_channels:
        await interaction.response.send_message("You cannot use this command in this channel.", ephemeral=True)
        return
    await interaction.response.send_modal(FileModal())


class TRLogModal(discord.ui.Modal, title="Create TR Log"):
    user_id = discord.ui.TextInput(label="User ID", placeholder="Enter the user ID", required=True)
    async def on_submit(self, interaction: discord.Interaction):
        try:
            user = await bot.fetch_user(int(self.user_id.value))
        except Exception:
            await interaction.response.send_message("Invalid user ID.", ephemeral=True)
            return
        # Create public thread
        thread = await interaction.channel.create_thread(name=str(user.id), type=discord.ChannelType.public_thread)
        try:
            starter_message = await interaction.channel.fetch_message(thread.id)
            await starter_message.delete()
        except Exception:
            pass
        await interaction.response.send_message(f"Log created for `{user.id}`.", ephemeral=True)
        embed = discord.Embed(color=0xffffff)
        embed.add_field(name="User ID", value=str(user.id), inline=True)
        embed.add_field(name="Username", value=str(user.name), inline=True)
        embed.add_field(name="Link to thread", value=thread.mention, inline=False)
        msg = await interaction.channel.send(embed=embed)
        thread_embed = discord.Embed(color=0xffffff)
        thread_embed.add_field(name="User ID", value=str(user.id), inline=True)
        thread_embed.add_field(name="Username", value=str(user.name), inline=True)
        thread_embed.add_field(name="Report Tickets", value="", inline=False)
        thread_embed.add_field(name="Mass Tickets", value="", inline=False)
        thread_embed.add_field(name="Appeal Tickets", value="", inline=False)
        thread_embed.add_field(name="Other Tickets", value="", inline=False)
        thread_msg = await thread.send(embed=thread_embed, view=TRLogView())

class TRLogView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
    @discord.ui.button(label="Edit", style=discord.ButtonStyle.grey, custom_id="trlog_edit")
    async def edit_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(EditTRLogModal(interaction.message))

class EditTRLogModal(discord.ui.Modal, title="Edit TR Log"):
    reports = discord.ui.TextInput(label="Report Tickets", required=False, style=discord.TextStyle.paragraph)
    masses = discord.ui.TextInput(label="Mass Tickets", required=False, style=discord.TextStyle.paragraph)
    appeals = discord.ui.TextInput(label="Appeal Tickets", required=False, style=discord.TextStyle.paragraph)
    others = discord.ui.TextInput(label="Other Tickets", required=False, style=discord.TextStyle.paragraph)
    def __init__(self, message: discord.Message):
        super().__init__()
        self.message = message
        embed = message.embeds[0]
        current_reports = embed.fields[2].value or ""
        current_masses = embed.fields[3].value or ""
        current_appeals = embed.fields[4].value or ""
        current_others = embed.fields[5].value or ""
        self.reports.default = current_reports
        self.masses.default = current_masses
        self.appeals.default = current_appeals
        self.others.default = current_others
    async def on_submit(self, interaction: discord.Interaction):
        embed = self.message.embeds[0]
        embed.set_field_at(
            2,
            name="Report Tickets",
            value=self.reports.value or "",
            inline=False
        )
        embed.set_field_at(
            3,
            name="Mass Tickets",
            value=self.masses.value or "",
            inline=False
        )
        embed.set_field_at(
            4,
            name="Appeal Tickets",
            value=self.appeals.value or "",
            inline=False
        )
        embed.set_field_at(
            5,
            name="Other Tickets",
            value=self.others.value or "",
            inline=False
        )
        embed.set_footer(
            text=f"Last edited by {interaction.user}",
            icon_url=interaction.user.display_avatar.url
        )
        await self.message.edit(embed=embed, view=TRLogView())
        await interaction.response.send_message("TR Log updated.", ephemeral=True)


@create.command(name="trlog", description="Creates a tr log.")
async def create_file(interaction: discord.Interaction):
    if interaction.channel.id != 1513548750495154246:
        return await interaction.response.send_message("You cannot use this command in this channel.", ephemeral=True)
    await interaction.response.send_modal(TRLogModal())


tickets = app_commands.Group(name="tickets", description="Add/remove users to/from ticket threads.")
bot.tree.add_command(tickets)

@tickets.command(name="add", description="Add a user or role to all active ticket threads.")
@app_commands.describe(target="User or Role ID / mention")
@app_commands.checks.has_role(adm_ping)
async def tickets_add(interaction: discord.Interaction, target: str):
    guild = interaction.guild
    ticket_channel = guild.get_channel(TICKET_CHANNEL)
    if not ticket_channel:
        return await interaction.response.send_message("Ticket channel not found.", ephemeral=True)
    threads = list(ticket_channel.threads)
    if not threads:
        return await interaction.response.send_message("No active threads found.", ephemeral=True)
    role = None
    target_display = ""
    if target.strip("<@>").isdigit():
        role = discord.utils.get(guild.roles, id=int(target.strip("<@>")))
    if not role:
        role = discord.utils.get(guild.roles, name=target)
    if role:
        member_list = role.members
        target_display = role.mention
    else:
        member = guild.get_member(int(target.strip("<@>"))) if target.strip("<@>").isdigit() else None
        if member:
            target_display = member.mention
            member_list = [member]
        else:
            return await interaction.response.send_message("Invalid user or role.", ephemeral=True)
    await interaction.response.send_message(f"Adding {len(member_list)} user(s) to {len(threads)} threads...", ephemeral=True)
    for thread in threads:
        for member in member_list:
            try:
                if member in thread.members:
                    continue
                await thread.add_user(member)
                await asyncio.sleep(0.25)
            except:
                continue
    await interaction.followup.send(f"Successfully added {target_display} to **{len(threads)}** thread(s).", ephemeral=True)

@tickets.command(name="remove", description="Remove a user or role from all active ticket threads")
@app_commands.describe(target="User or Role ID / mention")
@app_commands.checks.has_role(adm_ping)
async def tickets_remove(interaction: discord.Interaction, target: str):
    guild = interaction.guild
    ticket_channel = guild.get_channel(TICKET_CHANNEL)
    if not ticket_channel:
        return await interaction.response.send_message("Ticket channel not found.", ephemeral=True)
    threads = list(ticket_channel.threads)
    if not threads:
        return await interaction.response.send_message("No active threads found.", ephemeral=True)
    # resolve target
    role = None
    target_display = ""
    if target.strip("<@>").isdigit():
        role = discord.utils.get(guild.roles, id=int(target.strip("<@>")))
    if not role:
        role = discord.utils.get(guild.roles, name=target)
    if role:
        members = role.members
        target_display = role.mention
    else:
        member = guild.get_member(int(target.strip("<@>"))) if target.strip("<@>").isdigit() else None
        if member:
            target_display = member.mention
            members = [member]
        else:
            return await interaction.response.send_message("Invalid user or role.", ephemeral=True)
    await interaction.response.send_message(
        f"Removing {len(members)} user(s) from {len(threads)} threads...", ephemeral=True)
    for thread in threads:
        for member in members:
            try:
                if member not in thread.members:
                    await thread.remove_user(member)
                await asyncio.sleep(0.25)
            except:
                continue
    await interaction.followup.send(f"Successfully removed {target_display} from **{len(threads)}** thread(s).", ephemeral=True)


@bot.command()
async def sync(ctx: commands.Context):
    await bot.tree.sync()


bot.run(TOKEN)