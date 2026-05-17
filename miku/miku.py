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

GUILD_ID = 1371673839695826974

LB_CHANNEL = 1375271142092308582
CMDS_CHANNEL = 1375260303817838694
VERIFY_CHANNEL = 1375260857772150804
TRAINING_CHANNEL = 1375271729680748635
TICKET_CHANNEL = 1375261699111784478
QUOTA_CHANNEL = 1505563131655749712

# tri roles info
staff_role = 1373803879623430268
o5_role = 1372426616671834234
adm_role = 1375276457890287748
sr_role = 1375254710952661102
rep_role = 1372426736205303808
tr_role = 1372426794585817088
ban_perms = 1373517806921973900
staff_trainer = 1498599499893837874
full_break = 1505568168880636014
half_break = 1505568134617235546
tri_supporter = 1465630182462460040

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
    weekly_quota.start()

# loop tasks

async def send_low_performance_dm(member, rratio, vratio=None):
    try:
        embed = discord.Embed(
            title="Performance Warning",
            description=(
                "Your recent staff activity is below expected quota levels.\n\n"
                f"8-week average **reports** quota completion: **{rratio:.2f}**\n"
            ),
            colour=0xE74C3C
        )
        if rratio < 0.7:
            embed.title = "CRITICAL Performance Warning"
        if vratio:
            embed.description+=f"8-week average **reviews** quota completion: **{vratio:.2f}**\n"
            if vratio < 0.7:
                embed.title = "CRITICAL Performance Warning"
        embed.description+="\nPlease improve your activity. Thank you."
        await member.send(embed=embed)
    except:
        pass

def get_quota_config():
    return staffweeklycol.find_one({"_id": "global"}) or {
        "reports_quota": 0,
        "sr_reports_quota": 0,
        "sr_reviews_quota": 0
    }

@tasks.loop(time=datetime.time(hour=9, minute=9))
async def weekly_quota():
    guild = bot.get_guild(GUILD_ID)
    if not guild:
        return
    if datetime.datetime.now(datetime.timezone.utc).weekday() != 5:
        return
    lb_channel = bot.get_channel(LB_CHANNEL)
    if not lb_channel:
        return
    sr_not_met_quota = []
    not_met_quota = []
    sr_demotion_list = []
    demotion_list = []
    o5_reviews, adm_reviews, sr_reviews = [], [], []
    o5_reports, adm_reports, sr_reports = [], [], []
    rep_reports, tr_reports = [], []
    total_reviews = 0
    total_reports = 0
    o5_r = get(guild.roles, id=o5_role)
    adm_r = get(guild.roles, id=adm_role)
    sr_r = get(guild.roles, id=sr_role)
    rep_r = get(guild.roles, id=rep_role)
    tr_r = get(guild.roles, id=tr_role)
    staff_r = get(guild.roles, id=staff_role)
    # helpers
    def apply_break(quota, member):
        if get(member.guild.roles, id=full_break) in member.roles:
            return -1
        if get(member.guild.roles, id=half_break) in member.roles:
            return max(1, quota // 2)
        return quota
    def ratio(done, quota):
        if quota in (-1, 0):
            return -1 if quota == -1 else 1
        return round(min(done / quota, 1), 3)
    staff_members = set(staff_r.members)
    for member in staff_members:
        staff_id = str(member.id)
        staff_profile = trusteduserscol.find_one({"_id": staff_id}) or {}
        weekly_profile = staffweeklycol.find_one({"_id": staff_id}) or {}
        reviews = staff_profile.get("reviews", 0)
        reports = staff_profile.get("reports", 0)
        weekly_reviews = int(weekly_profile.get("weekly_reviews", 0))
        weekly_reports = int(weekly_profile.get("weekly_reports", 0))
        config = staffweeklycol.find_one({"_id": "global"}) or {
            "reports_quota": 0,
            "sr_reports_quota": 0,
            "sr_reviews_quota": 0
        }
        is_sr = any(role.id == sr_role for role in member.roles)
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
            if rq != -1 and rr != -1 and rr < 1:
                sr_not_met_quota.append([staff_id, "reports", weekly_reports, rq, rr])
        else:
            if rq != -1 and rr != -1 and rr < 1:
                not_met_quota.append([staff_id, weekly_reports, rq, rr])
        staffweeklycol.replace_one({"_id": staff_id}, weekly_profile, upsert=True)
        rratios = [x[2] for x in weekly_profile["reports_quota_list"] if x[2] != -1]
        if is_sr:
            vratios = [x[2] for x in weekly_profile["reviews_quota_list"] if x[2] != -1]
            ravg = sum(rratios) / len(rratios) if rratios else None
            vavg = sum(vratios) / len(vratios) if vratios else None
            if (ravg is not None and ravg < 0.5) or (vavg is not None and vavg < 0.5):
                sr_demotion_list.append([staff_id, round(ravg, 3), round(vavg, 3)])
            if (ravg is not None and ravg < 1) or (vavg is not None and vavg < 1):
                member = guild.get_member(int(staff_id))
                if member:
                    await send_low_performance_dm(member, vavg, ravg)
        else:
            if rratios:
                ravg = sum(rratios) / len(rratios)
                if ravg is not None and ravg < 0.5:
                    demotion_list.append([staff_id, round(ravg, 3)])
                if ravg is not None and ravg < 1:
                    member = guild.get_member(int(staff_id))
                    if member:
                        await send_low_performance_dm(member, ravg)

        staffweeklycol.update_one(
            {"_id": staff_id},
            {"$set": {"weekly_reports": 0, "weekly_reviews": 0}}
        )

        if o5_r in member.roles:
            o5_reviews.append((member, reviews, weekly_reviews))
            o5_reports.append((member, reports, weekly_reports))
        elif adm_r in member.roles:
            adm_reviews.append((member, reviews, weekly_reviews))
            adm_reports.append((member, reports, weekly_reports))
        elif sr_r in member.roles:
            sr_reviews.append((member, reviews, weekly_reviews))
            sr_reports.append((member, reports, weekly_reports))
        elif rep_r in member.roles:
            rep_reports.append((member, reports, weekly_reports))
        elif tr_r in member.roles:
            tr_reports.append((member, reports, weekly_reports))
    # reviews
    o5_lbr = discord.Embed(colour=0xffffff)
    o5_lbr.description = "✦　　┈　　overseers"
    for m, r, w in o5_reviews:
        total_reviews += w
        o5_lbr.description += f"\n-# <:reply:1459162938303578213>　{m.mention}　–　**{r}** all ㆍ {w} week"
    adm_lbr = discord.Embed(colour=0xffffff)
    adm_lbr.description = "✦　　┈　　admins"
    for m, r, w in adm_reviews:
        total_reviews += w
        adm_lbr.description += f"\n-# <:reply:1459162938303578213>　{m.mention}　–　**{r}** all ㆍ {w} week"
    sr_lbr = discord.Embed(colour=0xffffff)
    sr_lbr.description = "✦　　┈　　senior reporters"
    for m, r, w in sr_reviews:
        total_reviews += w
        sr_lbr.description += f"\n-# <:reply:1459162938303578213>　{m.mention}　–　**{r}** all ㆍ {w} week"
    await lb_channel.send(f"## _ _　　　weekly leaderboards .ᐟ\n_ _　　　　　　||<@&{staff_role}>||")
    await lb_channel.send("## _ _　　　reviews leaderboard", embeds=[o5_lbr, adm_lbr, sr_lbr])
    # reports
    o5_lb = discord.Embed(colour=0xffffff)
    o5_lb.description = "✦　　┈　　overseers"
    for m, r, w in o5_reports:
        total_reports += w
        o5_lb.description += f"\n-# <:reply:1459162938303578213>　{m.mention}　–　**{r}** all ㆍ {w} week"
    adm_lb = discord.Embed(colour=0xffffff)
    adm_lb.description = "✦　　┈　　admins"
    for m, r, w in adm_reports:
        total_reports += w
        adm_lb.description += f"\n-# <:reply:1459162938303578213>　{m.mention}　–　**{r}** all ㆍ {w} week"
    sr_lb = discord.Embed(colour=0xffffff)
    sr_lb.description = "✦　　┈　　senior reporters"
    for m, r, w in sr_reports:
        total_reports += w
        sr_lb.description += f"\n-# <:reply:1459162938303578213>　{m.mention}　–　**{r}** all ㆍ {w} week"
    rep_lb = discord.Embed(colour=0xffffff)
    rep_lb.description = "✦　　┈　　reporters"
    for m, r, w in rep_reports:
        total_reports += w
        rep_lb.description += f"\n-# <:reply:1459162938303578213>　{m.mention}　–　**{r}** all ㆍ {w} week"
    tr_lb = discord.Embed(colour=0xffffff)
    tr_lb.description = "✦　　┈　　trial reporters"
    for m, r, w in tr_reports:
        total_reports += w
        tr_lb.description += f"\n-# <:reply:1459162938303578213>　{m.mention}　–　**{r}** all ㆍ {w} week"
    await lb_channel.send("## _ _　　　reports leaderboard", embeds=[o5_lb, adm_lb, sr_lb, rep_lb, tr_lb])
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
            desc += (
                f"\n-# <:reply:1459162938303578213>　<@{user}>　–　{qtype}: "
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
            desc += (
                f"\n-# <:reply:1459162938303578213>　<@{user}>　–　**{done}** / {quota}　"
                f"({ratio:.2f})"
            )
        nmq_embed.description = desc[:4000]
    await QUOTA_CHANNEL.send(embed=sr_nmq_embed)
    await QUOTA_CHANNEL.send(embed=nmq_embed)

settings = app_commands.Group(name="set", description="Set.")
bot.tree.add_command(settings)

@settings.command(name="quota", description="Set weekly report quota for staff")
@app_commands.describe(quota="Weekly report quota")
@app_commands.checks.has_role(adm_role)
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
@app_commands.checks.has_role(adm_role)
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
    elif get(member.guild.roles, id=sr_role) in member.roles:
        return "Senior Reporter"
    elif get(member.guild.roles, id=rep_role) in member.roles:
        return "Reporter"
    elif get(member.guild.roles, id=tr_role) in member.roles:
        return "Trial Reporter"
    return "Staff"

@bot.command(name="qh")
async def quota_history(ctx, user_id: str = None):
    target_id = user_id or str(ctx.author.id)
    member = ctx.guild.get_member(int(target_id))
    if not member:
        return await ctx.send("Invalid user or user not in this server.")
    weekly_profile = staffweeklycol.find_one({"_id": target_id})
    if not weekly_profile:
        return await ctx.send("No quota history found for this user.")
    embeds = []
    rank = get_staff_rank(member)
    profile = discord.Embed(colour=0xffffff)
    profile.set_thumbnail(url=f"{member.display_avatar}")
    profile.description = f"{member.name}\n`{member.id}`\n{member.mention}\n**Rank:** {rank}"
    embeds.append(profile)
    is_sr = any(role.id == sr_role for role in member.roles)
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
        reviews_embed.description = (f"Staff: {member.mention}\n" + desc)
        current_reviews = weekly_profile.get("weekly_reviews", 0)
        current_reviews_quota = (
            get_quota_config().get("sr_reviews_quota", 0)
        )
        current_reviews_ratio = (
            round(min(current_reviews / current_reviews_quota, 1), 2)
            if current_reviews_quota > 0 else 0
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
    reports_embed.description = (f"Staff: {member.mention}\n" + desc)
    current_reports = weekly_profile.get("weekly_reports", 0)
    current_reports_quota = (
        get_quota_config().get("reports_quota", 0)
    )
    current_reports_ratio = (
        round(min(current_reports / current_reports_quota, 1), 2)
        if current_reports_quota > 0 else 0
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

@bot.command()
async def help(ctx):
    if ctx.guild.id == TRI_Archive:
        embed = discord.Embed(title="TRI bots commands", colour=0xffffff)
        # Add fields for each command/category
        embed.description = """
-# *Prefix:* `,`
### checks
`c`　┈　Checks a user or server.
`mc`　┈　Checks a list of users (max 200), leave a space between users.
`a`　┈　Checks a user for logged alts.
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
### leaderboard
`lb`　┈　Sends the current week's reports leaderboard.
`lbr`　┈　Sends the current week's reviews leaderboard.
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
async def tags(ctx, *, string: str = None):
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
## <a:red_arrow1:1388148121242177726>　　　　　scammer
　　**__definition__**

> users who have shown the **intention to, have attempted to, have admitted to, and/or have scammed**.
> 　⤷　applies __regardless__ of **whether the scam succeeded, and whether victim was able to recover the scammed possessions**.

　　**__examples__**

> - gaining control of a victim’s account (directly or via MM) and ghosting/blocking without completing the trade.
> - sending malicious links (e.g., scam/beam links) to steal accounts, items, or information.
> - providing a different account/item than agreed and refusing to refund or trade back.
> - faking account details (e.g. edited or stolen screenshots).
> - retrieving an account or filing chargebacks after a completed trade to reclaim money or assets.

　　**__notes__**

> - **admitting to scamming:** only reportable with proof (e.g., hit logs). claims alone aren’t enough.
> - **scam backs:** open a ticket before attempting a scam back to avoid being reported. please provide proof of original ownership and proof of the scam.

-# **confrontation is __strongly preferred__ and in some cases, required.** do be polite as much as possible. if ghosted/blocked upon confrontation, it is considered reportable.
            """)
            await interaction.response.send_message(embed=embed, ephemeral=True)

closing_options = [
    discord.SelectOption(emoji="<:whiteheart:1434538078747365507>", label="ㆍㆍReport", value="report"),
    discord.SelectOption(emoji="<:whiteheart:1434538078747365507>", label="ㆍㆍAppeal", value="appeal"),
    discord.SelectOption(emoji="<:whiteheart:1434538078747365507>", label="ㆍㆍVerify", value="verify"),
    discord.SelectOption(emoji="<:whiteheart:1434538078747365507>", label="ㆍㆍOthers", value="others"),
    discord.SelectOption(emoji="<:whiteheart:1434538078747365507>", label="ㆍㆍSR+", value="sr+"),
]

@bot.command(name="cl", help="Sends closing guide.")
async def cl(ctx, *, string: str = None):
    if ctx.guild.id == TRI_Archive:
        await ctx.reply(embed=discord.Embed(colour=0xffffff, title = "closing　guide　⸝⸝.ᐟ", description="""
ㆍrename ticket　┈　`,rn (name) tbc`
ㆍping sr+　┈　`,sr`
ㆍsee format for closing statements using the dropdown below.
ㆍplease merge identical reasons.
ㆍfor mass reports, you may wish to use `,pr` after reports are published to retrieve IDs easily.
        """), view=ClosingView())

class ClosingView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.select(options=closing_options, placeholder="‎　　Select a closing type . . .　　　", custom_id="closing",
                       max_values=1)
    async def select_callback(self, interaction, select):
        if self.select_callback.values[0] == "report":
            await interaction.response.send_message(embed=discord.Embed(description="""
ㆍnew report　┈　`new report on (ID) as (tags)`
ㆍadded report　┈　`added report on (ID) as (tags)`
ㆍedited alts　┈　`edited alts for (ID) - added (alt alt alt), removed (alt alt alt)`
ㆍedited server owner　┈　`server owner edited for (ID)`
ㆍinsufficient proof　┈　`no report on (ID) // insufficient proof`
ㆍunresponsive contributor　┈　`no report on (ID) // unresponsive contributor`
ㆍcontributor left server　┈　`no report on (ID) // contributor left server`
"""), ephemeral=True)
        if self.select_callback.values[0] == "appeal":
            await interaction.response.send_message(embed=discord.Embed(description="""
ㆍaccepted appeal　┈　`appeal on (ID) as (tags)`
ㆍrejected appeal　┈　`no appeal on (ID) // invalid reason`
ㆍinsufficient proof　┈　`no appeal on (ID) // insufficient proof`
ㆍunresponsive contributor　┈　`no appeal on (ID) // unresponsive contributor`
ㆍcontributor left server　┈　`no appeal on (ID) // contributor left server`
"""), ephemeral=True)
        if self.select_callback.values[0] == "verify":
            await interaction.response.send_message(embed=discord.Embed(description="""
ㆍsuccessful manual verification　┈　`(ID) manually verified`
ㆍunresponsive contributor　┈　`unresponsive contributor`
ㆍcontributor left server　┈　`contributor left server`
"""), ephemeral=True)
        if self.select_callback.values[0] == "others":
            await interaction.response.send_message(embed=discord.Embed(description="""
ㆍanswered question(s)　┈　`query answered`
ㆍbanned user(s)　┈　`no report // banned (ID) for (reason)`
"""), ephemeral=True)
        if self.select_callback.values[0] == "sr+":
            await interaction.response.send_message(embed=discord.Embed(description="""
ㆍrename ticket　┈　`,rn (name) tbc (sr name)`
ㆍcheck active reports and give feedback　┈　`,ar`
ㆍif done correctly, accept reports for voting in order.
ㆍcheck reports in voting　┈　`,vr`
ㆍwait until 4 agree votes before you can publish. 8 agree votes = auto-publish, 12 disagree votes = auto-reject.
ㆍcheck published reports　┈　`,pr` and `,c (ID)` or `,mc (IDs)`
ㆍask reporter for closing and close the ticket.
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
    """Renames the current thread to the new name provided."""
    if isinstance(ctx.channel, discord.Thread):
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
            await ctx.reply(f"First message: [Jump]({msg.jump_url})")
    else:
        await ctx.reply("This command can only be used in a thread.")

@bot.command(name="lb", help="Sends the current week's reports leaderboard.")
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
    # only iterate current server members
    for member in ctx.guild.members:
        matched_role = None
        for role_id in role_categories:
            if get(member.roles, id=role_id):
                matched_role = role_id
                break
        if not matched_role:
            continue
        staff_id = str(member.id)
        # fetch only needed db entries
        staff_profile = trusteduserscol.find_one({"_id": staff_id}) or {}
        weekly_profile = staffweeklycol.find_one({"_id": staff_id}) or {}
        reports = staff_profile.get("reports", 0)
        weekly_reports = weekly_profile.get("weekly_reports", 0)
        role_categories[matched_role][1].append((member, reports, weekly_reports))
    embeds = []
    for role_id, (title, staff_list) in role_categories.items():
        embed = discord.Embed(colour=0xffffff)
        embed.description = f"✦　　┈　　{title}"
        # optional sorting
        staff_list.sort(key=lambda x: x[2], reverse=True)
        for member, reports, weekly_reports in staff_list:
            embed.description += (
                f"\n-# <:reply:1459162938303578213>　"
                f"{member.mention}　–　"
                f"**{reports}** all ㆍ **{weekly_reports}** week")
        embeds.append(embed)
    await ctx.reply("## _ _　　　reports leaderboard", embeds=embeds)

@bot.command(name="lbr", help="Sends the current week's reviews leaderboard.")
@commands.has_any_role(staff_role)
async def lbr(ctx):
    role_categories = {
        o5_role: ("overseers", []),
        adm_role: ("admins", []),
        sr_role: ("senior reporters", [])
    }
    for member in ctx.guild.members:
        matched_role = None
        for rid in role_categories:
            if get(member.roles, id=rid):
                matched_role = rid
                break
        if not matched_role:
            continue
        staff_id = str(member.id)
        staff_profile = trusteduserscol.find_one({"_id": staff_id}) or {}
        weekly_profile = staffweeklycol.find_one({"_id": staff_id}) or {}
        reviews = staff_profile.get("reviews", 0)
        weekly_reviews = weekly_profile.get("weekly_reviews", 0)
        role_categories[matched_role][1].append((member, reviews, weekly_reviews))
    embeds = []
    for role_id, (title, staff_list) in role_categories.items():
        embed = discord.Embed(colour=0xffffff)
        embed.description = f"✦　　┈　　{title}"
        staff_list.sort(key=lambda x: x[2], reverse=True)
        for member, reviews, weekly_reviews in staff_list:
            embed.description += (
                f"\n-# <:reply:1459162938303578213>　"
                f"{member.mention}　–　"
                f"**{reviews}** all ㆍ **{weekly_reviews}** week")
        embeds.append(embed)
    await ctx.reply("## _ _　　　reviews leaderboard", embeds=embeds)

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
ㆍ**14–90 days**
ㆍExceeding 90 days results in an **unappealable demotion** (you may reapply)
ㆍ**Asking questions is encouraged** and will not affect your status
ㆍ**No breaks in the first 14 days** unless it’s an emergency
### Promotion Requirements
ㆍ**2 weeks of quota** (not necessarily consecutive)
ㆍ**15 non-hitter reports**
ㆍ**3 appeals**
ㆍ**20 votes**
            """), ephemeral=True)
        if self.select_callback.values[0] == "breaks":
            await interaction.response.send_message(embed=discord.Embed(description="""
### Break Types
ㆍ**Half Break** — weekly quota is **halved (rounded down)**
ㆍ**Full Break** — weekly quota is **not counted**
### Break Rules
ㆍStaff **cannot earn Annual Leave** while on break
ㆍ**1 Full Break** may be split into **2 Half Breaks**
### Annual Leave
ㆍIncludes **all types of leave**
ㆍBasic entitlement: **12 Full Breaks**
ㆍ**1/8 Full Break** for each **week of completed quota**
            """), ephemeral=True)
        if self.select_callback.values[0] == "quota":
            await interaction.response.send_message(embed=discord.Embed(description="""
### Quota Basics
ㆍWeekly quota ranges between **5–10 reports/appeals**
ㆍOnly **successfully published** reports/appeals are counted
ㆍHitter reports count toward quota but have **low promotion value**
### Strikes
ㆍEach week of **incomplete quota** while **not on a Full Break = 1 strike**
### Consequences for Incomplete Quota
ㆍ**Demotion in rank:**
　ㆍ2 consecutive strikes with **no breaks taken**
　ㆍ3 consecutive strikes with **≤ 1 Full Break** taken in total
　ㆍ4 or more strikes (not necessarily consecutive) within the **past 8 weeks**
ㆍ**Demotion from Staff:**
　ㆍAverage activity of **below 50%** over the **past 8 weeks**
　ㆍFull Break weeks are **excluded** from calculation, but Half Break weeks are **included**
　ㆍActivity is measured by **quota fulfilled**, capped at **100% per week**
            """), ephemeral=True)
        if self.select_callback.values[0] == "tickets":
            await interaction.response.send_message(embed=discord.Embed(description="""
### Ticket Claiming
ㆍThe **first Staff** to send a proper greeting (e.g. hi) handles the ticket
ㆍIf multiple greetings are sent, **reload Discord** to see who was first
ㆍOther Staff must **delete their messages**
### Ticket Handling
ㆍOnly **one Staff** may handle a ticket at a time
ㆍA **Defender** may assist if required
ㆍOnly **one Senior Reporter** may review when requested
ㆍAfter acceptance for voting, the **sr+ who publishes** the report is responsible for **closing the ticket**
### Ticket Priority
ㆍHandle **older tickets first**
ㆍDo not skip tickets because they seem difficult
### Ticket Limits
ㆍ**Trial Reporter** — 1 active, 2 on-hold, 1 self ticket
ㆍ**Reporter** — 2 active, 2 on-hold, 1 self ticket
ㆍIf an on-hold ticket becomes active and exceeds your limit, you must **open one active ticket to other Staff**
### On-Hold
ㆍStaff may place **their own tickets** on hold when necessary
ㆍCommon reasons include:
　ㆍWaiting for Defendant response
　ㆍWaiting for Contributor response
ㆍAbuse of on-hold may result in **warnings or demotion**
### Ticket Closure
ㆍIf the Contributor does not reply within **12 hours**, you may request closure
ㆍIf no meaningful proof is provided within **4 hours**, you may request closure
            """), ephemeral=True)
        if self.select_callback.values[0] == "autoresponders":
            await interaction.response.send_message(embed=discord.Embed(description="""
### ,adm
ㆍPings adm+.
### ,sr
ㆍPings sr+.
### ,tp
ㆍPings ticket ping, e.g. when you want open a ticket to other Staff.
### ,ban
ㆍPings ban perms.
### ,cl
ㆍSends closing guide.
                """), ephemeral=True)


# slash commands

staff = app_commands.Group(name="staff", description="Staff.")
bot.tree.add_command(staff)

@staff.command(name="rules", description="Sends staff rules.")
@app_commands.checks.has_role(adm_role)
async def staff_rules(interaction: discord.Interaction):
    await interaction.channel.send(embed=discord.Embed(colour=0xffffff, description="""
## <:2paperclip:1449650494044639335>　　staff　　rules　　୨୧
### Follow Server Rules
ㆍAdhere to all [server rules](https://discord.com/channels/1371673839695826974/1371674470611161160)
ㆍParticular focus on **No Discrimination**, **No Hate or Threats**, and **No NSFW Content**
### Confidentiality
ㆍFollow the Non-Disclosure Agreement (NDA)
ㆍViolation may result in immediate removal from Staff, a report as Unprofessional Staff, and/or a server ban depending on severity
### Ticket Protocol
ㆍOnly one Staff should handle a ticket at a time, unless a Defender is required
ㆍDo not hijack tickets assigned to others
ㆍAvoid tickets where you are related to the Defendant
ㆍKeep communication on-topic and case-related; no side-chatting
ㆍWhen handling multiple reports in a ticket, address one at a time in order
### Professionalism
ㆍReports on Staff may result in quarantine and demotion if accepted
ㆍSpeaking negatively about ticket participants or Staff (current or former) is Unprofessional and will be addressed
### Respect
ㆍRemain respectful, even toward those you dislike
ㆍPersonal feelings are not an excuse for rudeness or unprofessional behavior
### No Inappropriate Jokes
ㆍJokes about ||suicide||, ||self-harm||, or ||body shaming|| (e.g., "||kys||", "||fat||", "||keep yourself safe||") are strictly prohibited
ㆍEven if said without ill-intention, these are not acceptable as they may make others uncomfortable
### No Drama
ㆍKeep personal conflicts out of the server
ㆍResolve issues privately and respectfully, or seek proper mediation
### No Favouritism
ㆍDo not excessively praise, defend, or favour specific individuals
ㆍFavoritism that undermines neutrality, decision-making, or report handling is prohibited
"""), view=StaffRulesView())
    await interaction.response.send_message("Staff Rules have been sent.", ephemeral=True)

@staff.command(name="guide", description="Sends staff guide.")
@app_commands.checks.has_role(adm_role)
async def staff_guide(interaction: discord.Interaction):
    await interaction.channel.send(embed=discord.Embed(colour=0xffffff, description="""
## <:whitebow:1388714593211125971>　　staff　　guide　　୨୧
　　`,help` for list of TRI bots commands.
"""), view=StaffGuideView())
    await interaction.response.send_message("Staff Guide has been sent.", ephemeral=True)

anon = app_commands.Group(name="anon", description="Do something anonymously.")
bot.tree.add_command(anon)

@anon.command(name="say", description="MIKU will speak on your behalf.")
@app_commands.describe(message="Your message", image1="Image 1 (optional)", image2="Image 2 (optional)", image3="Image 3 (optional)", image4="Image 4 (optional)", image5="Image 5 (optional)", image6="Image 6 (optional)", image7="Image 7 (optional)", image8="Image 8 (optional)", image9="Image 9 (optional)", image10="Image 10 (optional)")
@app_commands.checks.has_any_role(staff_role, tethys_adm_role)
async def anon_say(interaction: discord.Interaction, message: str, image1: Optional[discord.Attachment], image2: Optional[discord.Attachment], image3: Optional[discord.Attachment], image4: Optional[discord.Attachment], image5: Optional[discord.Attachment], image6: Optional[discord.Attachment], image7: Optional[discord.Attachment], image8: Optional[discord.Attachment], image9: Optional[discord.Attachment], image10: Optional[discord.Attachment]):
    await interaction.response.defer(ephemeral=True)
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
        if get(interaction.user.guild.roles, id=adm_role) in interaction.user.roles or get(interaction.user.guild.roles, id=tethys_adm_role) in interaction.user.roles:
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
        await interaction.followup.send("Your message has been sent.", ephemeral=True)
    except Exception:
        await interaction.followup.send(f"Unable to send message.", ephemeral=True)

@anon.command(name="edit", description="Edit MIKU's message.")
@app_commands.describe(message_id="The message to edit", message="Your message", image1="Image 1 (optional)", image2="Image 2 (optional)", image3="Image 3 (optional)", image4="Image 4 (optional)", image5="Image 5 (optional)", image6="Image 6 (optional)", image7="Image 7 (optional)", image8="Image 8 (optional)", image9="Image 9 (optional)", image10="Image 10 (optional)")
@app_commands.checks.has_permissions(administrator=True)
async def anon_edit(interaction: discord.Interaction, message_id: str, message: str, image1: Optional[discord.Attachment] = None, image2: Optional[discord.Attachment] = None, image3: Optional[discord.Attachment] = None, image4: Optional[discord.Attachment] = None, image5: Optional[discord.Attachment] = None, image6: Optional[discord.Attachment] = None, image7: Optional[discord.Attachment] = None, image8: Optional[discord.Attachment] = None, image9: Optional[discord.Attachment] = None, image10: Optional[discord.Attachment] = None):
    await interaction.response.defer(ephemeral=True)
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
@app_commands.checks.has_role(adm_role)
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
        if get(interaction.user.guild.roles, id=adm_role) not in interaction.user.roles:
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
        if get(interaction.user.guild.roles, id=adm_role) not in interaction.user.roles:
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

tickets = app_commands.Group(name="tickets", description="Add/remove users to/from ticket threads.")
bot.tree.add_command(tickets)

@tickets.command(name="add", description="Add a user or role to all active ticket threads.")
@app_commands.describe(target="User or Role ID / mention")
@app_commands.checks.has_role(adm_role)
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
    if target.isdigit():
        role = discord.utils.get(guild.roles, id=int(target))
    if not role:
        role = discord.utils.get(guild.roles, name=target)
    if role:
        member_list = role.members
        target_display = role.mention
    else:
        member = guild.get_member(int(target)) if target.isdigit() else None
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
@app_commands.checks.has_role(adm_role)
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
    if target.isdigit():
        role = discord.utils.get(guild.roles, id=int(target))
    if not role:
        role = discord.utils.get(guild.roles, name=target)
    if role:
        members = role.members
        target_display = role.mention
    else:
        member = guild.get_member(int(target)) if target.isdigit() else None
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

