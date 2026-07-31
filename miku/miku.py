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
import time

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
kafu = client["kafu"]
reminders = kafu["reminders"]
tickets = kafu["tickets"]
transcripts = kafu["transcripts"]
counters = kafu["counters"]

intents = discord.Intents.all()
bot = commands.Bot(command_prefix=',', help_command=None, intents=intents)

LB_CHANNEL = 1375271142092308582
CMDS_CHANNEL = 1375260303817838694
VERIFY_CHANNEL = 1375260857772150804
TRAINING_CHANNEL = 1375271729680748635
TICKET_CHANNEL = 1375261699111784478
QUOTA_CHANNEL = 1505563131655749712
JSON_CHANNEL = 1520096583595724982
ATTACHMENT_CHANNEL = 1520096619012292659

# tri roles info
staff_role = 1373803879623430268
ticket_ping = 1449382692671193294
o5_role = 1372426616671834234
adm_role = 1372426657335345163
tadm_role = 1373517323914448906
adm_ping = 1375276457890287748
sr_of_the_month = 1498909625263722537
sr_role = 1372426698242658324
tsr_role = 1462972920467951728
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
new_staff = 1527528889939787786
tri_supporter = 1465630182462460040
archived_staff = 1505062096336064552

STAFF_ROLES = [ban_perms, files_access, defender, sr_of_the_month, sr_role, tsr_role, staff_trainer, sr_ping,
               reporter_of_the_month, rep_role, tr_role, t_role]

TRI_Archive = 1371673839695826974

KAFU = 1457009979817988241

#tethys roles info
tethys_adm_role = 1435570385960833024
tethys_staff_role = 1434809295953854475
tethys_tri_supporter = 1465634056015450270
tethys_ban_perms = 1465576138226139220
professional_pilot_role = 1435205527452778597
professional_mm_role = 1435205320300302396

tethys = 1434471275723493388

TAG_ROLES_MAP = {
    "ex-offender": 1523198664707674112,
    "scammer": 1523197275445137569,
    "scam server owner": 1523197278675009617,
    "raider": 1523197277227974747,
    "impersonator": 1523197280310530058,
    "vouch Scammer": 1523197280910442496,
    "plagiarist": 1523197279232720966,
    "fake event host": 1523197279366942882,
    "suspect": 1523197276418473984,
    "service ban": 1523198697540682000,
}

banned_words = os.getenv("banned_words").split(",")

def is_sr(user):
    return any(role.id in (sr_ping, adm_ping) for role in user.roles)

def is_active_staff(user):
    return any(role.id in (ticket_ping, adm_ping) for role in user.roles)

def extract_user_tags(user_profile: dict) -> set:
    found_tags = set()
    r_profile_list = user_profile.get("r_profile_list", [])
    if len(r_profile_list) > 1 and isinstance(r_profile_list[1], str):
        for tag in r_profile_list[1].split(","):
            if tag.strip():
                found_tags.add(tag.strip().lower())
    for key, val in user_profile.items():
        if key.isdigit() and isinstance(val, dict):
            tags_str = val.get("tags", "")
            if tags_str:
                for tag in tags_str.split(","):
                    if tag.strip():
                        found_tags.add(tag.strip().lower())
    return found_tags

async def sync_tag_roles(member: discord.Member) -> bool:
    if member.bot:
        return False
    user_id_str = str(member.id)
    user_profile = await asyncio.to_thread(userscol.find_one, {"_id": user_id_str})
    if user_profile:
        if len(user_profile) == 2:
            main = str(user_profile["main"])
            user_profile = await asyncio.to_thread(userscol.find_one, {"_id": main})
    all_tag_roles = set()
    for role_id in TAG_ROLES_MAP.values():
        role = member.guild.get_role(role_id)
        if role:
            all_tag_roles.add(role)

    if not user_profile:
        roles_to_remove = [r for r in all_tag_roles if r in member.roles]
        if roles_to_remove:
            try:
                await member.remove_roles(*roles_to_remove, reason="User is not reported; clearing tag roles.")
                return True
            except (discord.Forbidden, discord.HTTPException):
                pass
        return False

    user_tags = extract_user_tags(user_profile)
    roles_to_add = []
    roles_to_keep = set()
    for tag in user_tags:
        if tag in TAG_ROLES_MAP:
            role_id = TAG_ROLES_MAP[tag]
            role = member.guild.get_role(role_id)
            if role:
                roles_to_keep.add(role)
                if role not in member.roles:
                    roles_to_add.append(role)
    roles_to_remove = [r for r in all_tag_roles if r in member.roles and r not in roles_to_keep]
    changes_made = False
    if roles_to_add:
        try:
            await member.add_roles(*roles_to_add, reason="Automatic report tag role sync.")
            changes_made = True
        except (discord.Forbidden, discord.HTTPException):
            pass
    if roles_to_remove:
        try:
            await member.remove_roles(*roles_to_remove, reason="Removing unassigned report tag roles.")
            changes_made = True
        except (discord.Forbidden, discord.HTTPException):
            pass
    return changes_made

# events

@tasks.loop(hours=1)
async def periodic_role_sync():
    guild = bot.get_guild(TRI_Archive)
    if not guild:
        try:
            guild = await bot.fetch_guild(TRI_Archive)
        except (discord.NotFound, discord.HTTPException):
            return
    async for member in guild.fetch_members(limit=None):
        await sync_tag_roles(member)

@periodic_role_sync.before_loop
async def before_periodic_sync():
    await bot.wait_until_ready()

@bot.event
async def on_message(message):
    if message.author.id == KAFU:
        if message.embeds:
            for embed in message.embeds:
                if embed.description and "。。。ticket　ೀ　" in embed.description:
                    embed = discord.Embed(colour=0xffffff)
                    embed.add_field(name="Closing", value="", inline=False)
                    await message.channel.send(embed=embed, view=InputClosingView())
                    break

    if message.channel.id == CMDS_CHANNEL:
        if message.author.bot:
            return
        if not message.content.startswith(","):
            try: await message.delete()
            except Exception: pass
    await bot.process_commands(message)

class InputClosingView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Closing", style=discord.ButtonStyle.grey, custom_id="inputclosing_edit")
    async def edit_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if is_active_staff(interaction.user):
            await interaction.response.send_modal(InputClosingModal(interaction.message))

class InputClosingModal(discord.ui.Modal, title="Closing"):
    closing = discord.ui.TextInput(label="Closing", required=False, style=discord.TextStyle.paragraph, max_length=1000)
    def __init__(self, message: discord.Message):
        super().__init__()
        self.message = message
        embed = message.embeds[0]
        current_closing = embed.fields[0].value.strip("`") if embed.fields else ""
        self.closing.default = current_closing
    async def on_submit(self, interaction: discord.Interaction):
        embed = discord.Embed(colour=0xffffff)
        display_text = f"`{self.closing.value}`" if self.closing.value.strip() else ""

        embed.add_field(name="Closing", value=display_text, inline=False)
        embed.set_footer(
            text=f"Last edited by {interaction.user}",
            icon_url=interaction.user.display_avatar.url
        )

        await self.message.edit(embed=embed, view=InputClosingView())
        await interaction.response.send_message("Closing updated.", ephemeral=True)


@bot.event
async def on_member_join(member):
    if member.guild.id == TRI_Archive:
        channel = bot.get_channel(VERIFY_CHANNEL)
        await channel.send(f"Welcome to TRI Archive, {member.mention}! Please verify.", delete_after=0)
        await sync_tag_roles(member)

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
    bot.add_view(InputClosingView())
    bot.add_view(FAQOverviewView())
    bot.add_view(FAQReportsView())
    bot.add_view(FAQAppealsView())
    bot.add_view(FAQDefinitionsStandardsView())
    bot.add_view(FAQScamPreventionView())
    bot.add_view(FAQStaffTransparencyView())
    bot.add_view(LanguageRolesView())
    if not reminder_loop.is_running():
        reminder_loop.start()
    if not weekly_quota.is_running():
        weekly_quota.start()
    if not periodic_role_sync.is_running():
        periodic_role_sync.start()
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

@tasks.loop(minutes=10)
async def reminder_loop():
    now = datetime.datetime.now(datetime.timezone.utc).timestamp()
    for reminder in reminders.find():
        thread_id = reminder["thread_id"]
        channel = bot.get_channel(thread_id)
        if not channel:
            continue
        remaining = reminder["end_time"] - now
        if remaining <= 0:
            try:
                await channel.edit(name=reminder["base_name"])
                await channel.send(
                    f"<@{reminder["user_id"]}> time’s up."
                )
            except:
                pass
            reminders.delete_one({"thread_id": thread_id})
            continue
        hours_left = max(1, int((remaining + 3599) // 3600))
        expected_name = f"{reminder["base_name"]} - {hours_left}h"
        if channel.name != expected_name:
            try:
                await channel.edit(name=expected_name)
            except:
                pass

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
    total_closes = 0
    total_tickets = 0

    o5_r = get(guild.roles, id=o5_role)
    adm_r = get(guild.roles, id=adm_role)
    sr_r = get(guild.roles, id=sr_role)
    rep_r = get(guild.roles, id=rep_role)
    tr_r = get(guild.roles, id=tr_role)
    full_break_role = get(guild.roles, id=full_break)
    half_break_role = get(guild.roles, id=half_break)
    new_staff_role = get(guild.roles, id=new_staff)
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
        "tickets_quota": 0,
        "sr_reports_quota": 0,
        "sr_reviews_quota": 0,
        "sr_tickets_quota": 0,
        "sr_closes_quota": 0
    }
    staff_members = set(o5_r.members + adm_r.members + sr_r.members + rep_r.members + tr_r.members + full_break_role.members + half_break_role.members)
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
        weekly_closes = int(weekly_profile.get("weekly_closes", 0))
        weekly_tickets = int(weekly_profile.get("weekly_tickets", 0))
        if is_sr(member):
            rq = config.get("sr_reports_quota", 0)
            tq = config.get("sr_tickets_quota", 0)
        else:
            rq = config.get("reports_quota", 0)
            tq = config.get("tickets_quota", 0)
        rq = apply_break(rq, member)
        tq = apply_break(tq, member)
        rr = ratio(weekly_reports, rq)
        tr = ratio(weekly_tickets, tq)
        if member.get_role(new_staff):
            rr = 1.0
            tr = 1.0
            await member.remove_roles(new_staff_role)
        weekly_profile.setdefault("reports_quota_list", [])
        weekly_profile["reports_quota_list"].append([weekly_reports, rq, rr])
        weekly_profile["reports_quota_list"] = weekly_profile["reports_quota_list"][-8:]
        weekly_profile.setdefault("tickets_quota_list", [])
        weekly_profile["tickets_quota_list"].append([weekly_tickets, tq, tr])
        weekly_profile["tickets_quota_list"] = weekly_profile["tickets_quota_list"][-8:]
        effective_report_ticket_ratio = max(rr, tr)
        if is_sr(member):
            vq = config.get("sr_reviews_quota", 0)
            cq = config.get("sr_closes_quota", 0)
            vq = apply_break(vq, member)
            cq = apply_break(cq, member)
            vr = ratio(weekly_reviews, vq)
            cr = ratio(weekly_closes, cq)
            weekly_profile.setdefault("reviews_quota_list", [])
            weekly_profile["reviews_quota_list"].append([weekly_reviews, vq, vr])
            weekly_profile["reviews_quota_list"] = weekly_profile["reviews_quota_list"][-8:]
            weekly_profile.setdefault("closes_quota_list", [])
            weekly_profile["closes_quota_list"].append([weekly_closes, cq, cr])
            weekly_profile["closes_quota_list"] = weekly_profile["closes_quota_list"][-8:]
            effective_review_close_ratio = max(vr, cr)
            if effective_review_close_ratio != -1 and effective_review_close_ratio < 1:
                if vr >= cr:
                    sr_not_met_quota.append([staff_id, "reviews", weekly_reviews, vq, vr])
                    await send_incomplete_quota_dm(member, weekly_reviews, vq, vr, "reviews")
                else:
                    sr_not_met_quota.append([staff_id, "closes", weekly_closes, cq, cr])
                    await send_incomplete_quota_dm(member, weekly_closes, cq, cr, "closes")
            if effective_report_ticket_ratio != -1 and effective_report_ticket_ratio < 1:
                if rr >= tr:
                    sr_not_met_quota.append([staff_id, "reports", weekly_reports, rq, rr])
                    await send_incomplete_quota_dm(member, weekly_reports, rq, rr, "reports")
                else:
                    sr_not_met_quota.append([staff_id, "tickets", weekly_tickets, tq, tr])
                    await send_incomplete_quota_dm(member, weekly_tickets, tq, tr, "tickets")
        else:
            if effective_report_ticket_ratio != -1 and effective_report_ticket_ratio < 1:
                if rr >= tr:
                    not_met_quota.append([staff_id, weekly_reports, rq, rr])
                    await send_incomplete_quota_dm(member, weekly_reports, rq, rr)
                else:
                    not_met_quota.append([staff_id, weekly_tickets, tq, tr])
                    await send_incomplete_quota_dm(member, weekly_tickets, tq, tr)
        staffweeklycol.replace_one({"_id": staff_id}, weekly_profile, upsert=True)
        rratios = [x[2] for x in weekly_profile["reports_quota_list"] if x[2] != -1]
        tratios = [x[2] for x in weekly_profile["tickets_quota_list"] if x[2] != -1]
        best_report_ticket_ratios = []
        for i in range(min(len(rratios), len(tratios))):
            best_report_ticket_ratios.append(max(rratios[i], tratios[i]))
        ravg = sum(best_report_ticket_ratios) / len(best_report_ticket_ratios) if best_report_ticket_ratios else None
        if is_sr(member):
            vratios = [x[2] for x in weekly_profile["reviews_quota_list"] if x[2] != -1]
            cratios = [x[2] for x in weekly_profile["closes_quota_list"] if x[2] != -1]

            best_review_close_ratios = []
            for i in range(min(len(vratios), len(cratios))):
                best_review_close_ratios.append(max(vratios[i], cratios[i]))
            vavg = sum(best_review_close_ratios) / len(best_review_close_ratios) if best_review_close_ratios else None
            if (ravg is not None and ravg < 0.5 and len(weekly_profile.get("reports_quota_list", [])) > 7) or (
                    vavg is not None and vavg < 0.5 and len(weekly_profile.get("reviews_quota_list", [])) > 7):
                sr_demotion_list.append([staff_id, round(ravg or 0, 3), round(vavg or 0, 3)])
            if (ravg is not None and ravg < 0.8 and len(weekly_profile.get("reports_quota_list", [])) > 2) or (
                    vavg is not None and vavg < 0.8 and len(weekly_profile.get("reviews_quota_list", [])) > 2):
                member_obj = guild.get_member(int(staff_id))
                if member_obj:
                    await send_low_performance_dm(member_obj, vavg or 0, ravg or 0)
        else:
            if ravg is not None and ravg < 0.5 and len(weekly_profile.get("reports_quota_list", [])) > 7:
                demotion_list.append([staff_id, round(ravg, 3)])
            if ravg is not None and ravg < 0.8 and len(weekly_profile.get("reports_quota_list", [])) > 2:
                member_obj = guild.get_member(int(staff_id))
                if member_obj:
                    await send_low_performance_dm(member_obj, ravg)
        matched_role = None
        for role_id in reports_role_categories:
            if get(member.roles, id=role_id):
                matched_role = role_id
                break
        if matched_role:
            reports_total = staff_profile.get("reports", 0)
            tickets_total = staff_profile.get("tickets", 0)
            reports_role_categories[matched_role][1].append(
                (member, reports_total, weekly_reports, tickets_total, weekly_tickets))
        matched_role = None
        for rid in reviews_role_categories:
            if get(member.roles, id=rid):
                matched_role = rid
                break
        if matched_role:
            reviews_total = staff_profile.get("reviews", 0)
            closes_total = staff_profile.get("closes", 0)
            reviews_role_categories[matched_role][1].append(
                (member, reviews_total, weekly_reviews, closes_total, weekly_closes))

    # closes/reviews
    embeds = []
    for role_id, (title, staff_list) in reviews_role_categories.items():
        if not staff_list:
            continue
        embed = discord.Embed(colour=0xffffff)
        embed.description = f"**✦　　–　　{title}**"
        staff_list.sort(key=lambda x: (x[4], x[2]), reverse=True)
        for i, (member, reviews, weekly_reviews, closes, weekly_closes) in enumerate(staff_list, start=1):
            total_reviews += weekly_reviews
            total_closes += weekly_closes
            embed.description += (
                f"\n-# {i}ㆍ{member.mention}"
                f"\n-# _ _　closes　–　**{closes}** all ㆍ **{weekly_closes}** week"
                f"\n-# _ _　reviews　–　**{reviews}** all ㆍ **{weekly_reviews}** week"
            )
        embeds.append(embed)
    await lb_channel.send(f"## _ _　　　weekly leaderboards .ᐟ\n_ _　　　　　　||<@&{staff_role}>||")
    await lb_channel.send("## _ _　　　sr+ leaderboard", embeds=embeds)

    # tickets/reports
    embeds = []
    for role_id, (title, staff_list) in reports_role_categories.items():
        if not staff_list:
            continue
        embed = discord.Embed(colour=0xffffff)
        embed.description = f"**✦　　–　　{title}**"
        staff_list.sort(key=lambda x: (x[4], x[2]), reverse=True)
        for i, (member, reports, weekly_reports, tickets, weekly_tickets) in enumerate(staff_list, start=1):
            total_reports += weekly_reports
            total_tickets += weekly_tickets
            embed.description += (
                f"\n-# {i}ㆍ{member.mention}"
                f"\n-# _ _　tickets　–　**{tickets}** all ㆍ **{weekly_tickets}** week"
                f"\n-# _ _　reports　–　**{reports}** all ㆍ **{weekly_reports}** week"
            )
        embeds.append(embed)
    await lb_channel.send("## _ _　　　staff leaderboard", embeds=embeds)

    summary = discord.Embed(colour=0xffffff)
    summary.description = (
        f"✦　　–　　total closes　　–　　**{total_closes}**\n"
        f"✦　　–　　total reviews　　–　　**{total_reviews}**\n"
        f"✦　　–　　total tickets　　–　　**{total_tickets}**\n"
        f"✦　　–　　total reports　　–　　**{total_reports}**"
    )
    await lb_channel.send("## _ _　　　weekly summary", embed=summary)

    sr_nmq_embed = discord.Embed(
        title="sr+ weekly quota summary",
        colour=0xffffff
    )
    if not sr_not_met_quota:
        sr_nmq_embed.description = "All staff met their weekly quota <a:tri_pinkconfetti:1505564994731905065>"
    else:
        desc = ""
        for user, qtype, done, quota, ratio in sorted(sr_not_met_quota, key=lambda x: x[4]):
            member = guild.get_member(int(user))
            mention = member.mention if member else f"`{user}`"
            desc += f"\n-# ㆍ　{mention}　–　{qtype}: **{done}** / {quota}　({ratio:.2f})"
        sr_nmq_embed.description = desc[:4000]
    nmq_embed = discord.Embed(
        title="staff weekly quota summary",
        colour=0xffffff
    )
    if not not_met_quota:
        nmq_embed.description = "All staff met their weekly quota <a:tri_pinkconfetti:1505564994731905065>"
    else:
        desc = ""
        for user, done, quota, ratio in sorted(not_met_quota, key=lambda x: x[3]):
            member = guild.get_member(int(user))
            mention = member.mention if member else f"`{user}`"
            desc += f"\n-# ㆍ　{mention}　–　**{done}** / {quota}　({ratio:.2f})"
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
            title="demotion candidates",
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
        {"$set": {"weekly_reports": 0, "weekly_reviews": 0, "weekly_tickets": 0, "weekly_closes": 0}}
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


@settings.command(name="quota", description="Set weekly quota for staff")
@app_commands.describe(quota="Weekly quota", type="Reports/Tickets")
@app_commands.checks.has_role(adm_ping)
async def set_quota(interaction: discord.Interaction, quota: int, type: Literal["reports", "tickets"]):
    if quota < 0:
        return await interaction.response.send_message("Quota must be at least 0.", ephemeral=True)
    if type == "reports":
        field = "reports_quota"
    elif type == "tickets":
        field = "tickets_quota"
    staffweeklycol.update_one(
        {"_id": "global"},
        {"$set": {field: quota}},
        upsert=True
    )
    await interaction.response.send_message(
        f"**staff** {type} quota set to **{quota}**.",
        ephemeral=True
    )

@settings.command(name="srquota", description="Set weekly quota for sr+")
@app_commands.describe(quota="Weekly quota", type="Reports/Reviews/Tickets/Closes")
@app_commands.checks.has_role(adm_ping)
async def set_srquota(interaction: discord.Interaction, quota: int,
                      type: Literal["reports", "reviews", "tickets", "closes"]):
    if quota < 0:
        return await interaction.response.send_message("Quota must be at least 0.", ephemeral=True)
    if type == "reports":
        field = "sr_reports_quota"
    elif type == "reviews":
        field = "sr_reviews_quota"
    elif type == "tickets":
        field = "sr_tickets_quota"
    elif type == "closes":
        field = "sr_closes_quota"
    staffweeklycol.update_one(
        {"_id": "global"},
        {"$set": {field: quota}},
        upsert=True
    )
    await interaction.response.send_message(f"**sr+** {type} quota set to **{quota}**.", ephemeral=True)

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
    profile = discord.Embed(colour=0xffffff, title=f"{member.display_name.replace('||', '\\|\\|').replace('_', '\\_')}")
    profile.set_thumbnail(url=f"{member.display_avatar}")
    profile.description = f"`{member.id}`\n{member.mention}\n`{member.name}`\n**Rank:** {rank}"
    embeds.append(profile)
    embed = discord.Embed(title="quota progress", colour=0xffffff, description="")
    if is_sr(member):
        current_closes = weekly_profile.get("weekly_closes", 0)
        current_closes_quota = get_quota_config().get("sr_closes_quota", 0)
        current_closes_quota = apply_break(current_closes_quota, member)
        current_closes_ratio = (
            round(min(current_closes / current_closes_quota, 1), 2)
            if current_closes_quota >= 0 else -1
        )
        quota_display = "FULL BREAK" if current_closes_quota == -1 else str(current_closes_quota)
        ratio_display = "N/A" if current_closes_ratio == -1 else f"{current_closes_ratio:.2f}"
        embed.description += f"\ncloses　–　**{current_closes}** / {quota_display}　–　`{ratio_display}`"
        if ratio_display == "1.00": embed.description += "　<a:tri_pinkconfetti:1505564994731905065>"
    if is_sr(member):
        current_reviews = weekly_profile.get("weekly_reviews", 0)
        current_reviews_quota = (get_quota_config().get("sr_reviews_quota", 0))
        current_reviews_quota = apply_break(current_reviews_quota, member)
        current_reviews_ratio = (
            round(min(current_reviews / current_reviews_quota, 1), 2)
            if current_reviews_quota >= 0 else -1
        )
        quota_display = "FULL BREAK" if current_reviews_quota == -1 else str(current_reviews_quota)
        ratio_display = "N/A" if current_reviews_ratio == -1 else f"{current_reviews_ratio:.2f}"
        embed.description += f"\nreviews　–　**{current_reviews}** / {quota_display}　–　`{ratio_display}`"
        if ratio_display == "1.00": embed.description += "　<a:tri_pinkconfetti:1505564994731905065>"
    current_tickets = weekly_profile.get("weekly_tickets", 0)
    if is_sr(member):
        current_tickets_quota = get_quota_config().get("sr_tickets_quota", 0)
    else:
        current_tickets_quota = get_quota_config().get("tickets_quota", 0)
    current_tickets_quota = apply_break(current_tickets_quota, member)
    current_tickets_ratio = round(min(current_tickets / current_tickets_quota, 1),
                                  2) if current_tickets_quota >= 0 else -1
    quota_display = "FULL BREAK" if current_tickets_quota == -1 else str(current_tickets_quota)
    ratio_display = "N/A" if current_tickets_ratio == -1 else f"{current_tickets_ratio:.2f}"
    embed.description += f"\ntickets　–　**{current_tickets}** / {quota_display}　–　`{ratio_display}`"
    if ratio_display == "1.00": embed.description += "　<a:tri_pinkconfetti:1505564994731905065>"
    current_reports = weekly_profile.get("weekly_reports", 0)
    if is_sr(member):
        current_reports_quota = get_quota_config().get("sr_reports_quota", 0)
    else:
        current_reports_quota = get_quota_config().get("reports_quota", 0)
    current_reports_quota = apply_break(current_reports_quota, member)
    current_reports_ratio = round(min(current_reports / current_reports_quota, 1), 2) if current_reports_quota >= 0 else -1
    quota_display = "FULL BREAK" if current_reports_quota == -1 else str(current_reports_quota)
    ratio_display = "N/A" if current_reports_ratio == -1 else f"{current_reports_ratio:.2f}"
    embed.description += f"\nreports　–　**{current_reports}** / {quota_display}　–　`{ratio_display}`"
    if ratio_display == "1.00": embed.description += "　<a:tri_pinkconfetti:1505564994731905065>"
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
    profile = discord.Embed(colour=0xffffff, title=f"{member.display_name.replace('||', '\\|\\|').replace('_', '\\_')}")
    profile.set_thumbnail(url=f"{member.display_avatar}")
    profile.description = f"`{member.id}`\n{member.mention}\n`{member.name}`\n**Rank:** {rank}"
    embeds.append(profile)
    if is_sr(member):
        closes_history = weekly_profile.get("closes_quota_list", [])
        reviews_history = weekly_profile.get("reviews_quota_list", [])
        cr_embed = discord.Embed(title="closes & reviews history", colour=0xffffff)
        desc = ""
        max_weeks = max(len(closes_history), len(reviews_history))
        while len(closes_history) < max_weeks:
            closes_history.insert(0, [0, 0, 0.00])
        while len(reviews_history) < max_weeks:
            reviews_history.insert(0, [0, 0, 0.00])
        start_idx = max(0, max_weeks - 7)

        for idx in range(start_idx, max_weeks):
            week_num = (idx - start_idx) + 1
            if idx < len(closes_history):
                c_done, c_quota, c_ratio = closes_history[idx]
                c_q_disp = "FULL BREAK" if c_quota == -1 else str(c_quota)
                c_r_disp = "N/A" if c_ratio == -1 else f"{c_ratio:.2f}"
            else:
                c_done, c_q_disp, c_r_disp = 0, "0", "0.00"
            if idx < len(reviews_history):
                r_done, r_quota, r_ratio = reviews_history[idx]
                r_q_disp = "FULL BREAK" if r_quota == -1 else str(r_quota)
                r_r_disp = "N/A" if r_ratio == -1 else f"{r_ratio:.2f}"
            else:
                r_done, r_q_disp, r_r_disp = 0, "0", "0.00"
            desc += (
                f"\n**Week {week_num}**"
                f"\n-# _ _ closes　–　**{c_done}** / {c_q_disp}　–　`{c_r_disp}`"
                f"\n-# _ _ reviews　–　**{r_done}** / {r_q_disp}　–　`{r_r_disp}`"
            )
        cr_embed.description = desc
        current_closes = weekly_profile.get("weekly_closes", 0)
        current_closes_quota = apply_break(get_quota_config().get("sr_closes_quota", 0), member)
        current_closes_ratio = round(min(current_closes / current_closes_quota, 1),
                                     2) if current_closes_quota >= 0 else -1
        c_q_now = "FULL BREAK" if current_closes_quota == -1 else str(current_closes_quota)
        c_r_now = "N/A" if current_closes_ratio == -1 else f"{current_closes_ratio:.2f}"
        current_reviews = weekly_profile.get("weekly_reviews", 0)
        current_reviews_quota = apply_break(get_quota_config().get("sr_reviews_quota", 0), member)
        current_reviews_ratio = round(min(current_reviews / current_reviews_quota, 1),
                                      2) if current_reviews_quota >= 0 else -1
        r_q_now = "FULL BREAK" if current_reviews_quota == -1 else str(current_reviews_quota)
        r_r_now = "N/A" if current_reviews_ratio == -1 else f"{current_reviews_ratio:.2f}"

        cr_embed.description += (
            f"\n**Current Week**"
            f"\n-# _ _ closes　–　**{current_closes}** / {c_q_now}　–　`{c_r_now}`"
            f"\n-# _ _ reviews　–　**{current_reviews}** / {r_q_now}　–　`{r_r_now}`"
        )
        hist_c_ratios = [x[2] for x in closes_history[-7:] if x[2] != -1]
        if current_closes_ratio != -1: hist_c_ratios.append(current_closes_ratio)
        ovr_c = round(sum(hist_c_ratios) / len(hist_c_ratios), 3) if hist_c_ratios else 0
        hist_r_ratios = [x[2] for x in reviews_history[-7:] if x[2] != -1]
        if current_reviews_ratio != -1: hist_r_ratios.append(current_reviews_ratio)
        ovr_r = round(sum(hist_r_ratios) / len(hist_r_ratios), 3) if hist_r_ratios else 0
        cr_embed.description += f"\n\n**Overall Closes Ratio**　ㆍ　`{ovr_c:.2f}`\n**Overall Reviews Ratio**　ㆍ　`{ovr_r:.2f}`"

        best_cr_ratios = []
        weeks_to_check = min(7, max(len(closes_history), len(reviews_history)))
        for i in range(1, weeks_to_check + 1):
            c_ratio = closes_history[-i][2] if i <= len(closes_history) else -1
            r_ratio = reviews_history[-i][2] if i <= len(reviews_history) else -1
            if c_ratio != -1 or r_ratio != -1:
                best_cr_ratios.append(max(c_ratio, r_ratio))
        if current_closes_ratio != -1 or current_reviews_ratio != -1:
            best_cr_ratios.append(max(current_closes_ratio, current_reviews_ratio))
        ovr_performance = round(sum(best_cr_ratios) / len(best_cr_ratios), 3) if best_cr_ratios else 0
        cr_embed.description += f"\n**Overall Ratio**　ㆍ　`{ovr_performance:.2f}`"
        embeds.append(cr_embed)
    tickets_history = weekly_profile.get("tickets_quota_list", [])
    reports_history = weekly_profile.get("reports_quota_list", [])

    tr_embed = discord.Embed(title="tickets & reports history", colour=0xffffff)
    desc = ""
    max_weeks = max(len(tickets_history), len(reports_history))
    while len(tickets_history) < max_weeks:
        tickets_history.insert(0, [0, 0, 0.00])
    while len(reports_history) < max_weeks:
        reports_history.insert(0, [0, 0, 0.00])
    start_idx = max(0, max_weeks - 7)
    for idx in range(start_idx, max_weeks):
        week_num = (idx - start_idx) + 1
        if idx < len(tickets_history):
            t_done, t_quota, t_ratio = tickets_history[idx]
            t_q_disp = "FULL BREAK" if t_quota == -1 else str(t_quota)
            t_r_disp = "N/A" if t_ratio == -1 else f"{t_ratio:.2f}"
        else:
            t_done, t_q_disp, t_r_disp = 0, "0", "0.00"
        if idx < len(reports_history):
            rep_done, rep_quota, rep_ratio = reports_history[idx]
            rep_q_disp = "FULL BREAK" if rep_quota == -1 else str(rep_quota)
            rep_r_disp = "N/A" if rep_ratio == -1 else f"{rep_ratio:.2f}"
        else:
            rep_done, rep_q_disp, rep_r_disp = 0, "0", "0.00"
        desc += (
            f"\n**Week {week_num}**"
            f"\n-# _ _ tickets　–　**{t_done}** / {t_q_disp}　–　`{t_r_disp}`"
            f"\n-# _ _ reports　–　**{rep_done}** / {rep_q_disp}　–　`{rep_r_disp}`"
        )
    tr_embed.description = desc
    current_tickets = weekly_profile.get("weekly_tickets", 0)
    t_quota_val = get_quota_config().get("sr_tickets_quota" if is_sr(member) else "tickets_quota", 0)
    current_tickets_quota = apply_break(t_quota_val, member)
    current_tickets_ratio = round(min(current_tickets / current_tickets_quota, 1),
                                  2) if current_tickets_quota >= 0 else -1
    t_q_now = "FULL BREAK" if current_tickets_quota == -1 else str(current_tickets_quota)
    t_r_now = "N/A" if current_tickets_ratio == -1 else f"{current_tickets_ratio:.2f}"
    current_reports = weekly_profile.get("weekly_reports", 0)
    rep_quota_val = get_quota_config().get("sr_reports_quota" if is_sr(member) else "reports_quota", 0)
    current_reports_quota = apply_break(rep_quota_val, member)
    current_reports_ratio = round(min(current_reports / current_reports_quota, 1),
                                  2) if current_reports_quota >= 0 else -1
    rep_q_now = "FULL BREAK" if current_reports_quota == -1 else str(current_reports_quota)
    rep_r_now = "N/A" if current_reports_ratio == -1 else f"{current_reports_ratio:.2f}"
    tr_embed.description += (
        f"\n**Current Week**"
        f"\n-# _ _ tickets　–　**{current_tickets}** / {t_q_now}　–　`{t_r_now}`"
        f"\n-# _ _ reports　–　**{current_reports}** / {rep_q_now}　–　`{rep_r_now}`"
    )
    hist_t_ratios = [x[2] for x in tickets_history[-7:] if x[2] != -1]
    if current_tickets_ratio != -1: hist_t_ratios.append(current_tickets_ratio)
    ovr_t = round(sum(hist_t_ratios) / len(hist_t_ratios), 3) if hist_t_ratios else 0
    hist_rep_ratios = [x[2] for x in reports_history[-7:] if x[2] != -1]
    if current_reports_ratio != -1: hist_rep_ratios.append(current_reports_ratio)
    ovr_rep = round(sum(hist_rep_ratios) / len(hist_rep_ratios), 3) if hist_rep_ratios else 0

    tr_embed.description += f"\n\n**Overall Tickets Ratio**　ㆍ　`{ovr_t:.2f}`\n**Overall Reports Ratio**　ㆍ　`{ovr_rep:.2f}`"
    best_tr_ratios = []
    weeks_to_check_tr = min(7, max(len(tickets_history), len(reports_history)))
    for i in range(1, weeks_to_check_tr + 1):
        t_ratio = tickets_history[-i][2] if i <= len(tickets_history) else -1
        rep_ratio = reports_history[-i][2] if i <= len(reports_history) else -1
        if t_ratio != -1 or rep_ratio != -1:
            best_tr_ratios.append(max(t_ratio, rep_ratio))
    if current_tickets_ratio != -1 or current_reports_ratio != -1:
        best_tr_ratios.append(max(current_tickets_ratio, current_reports_ratio))
    ovr_tr_performance = round(sum(best_tr_ratios) / len(best_tr_ratios), 3) if best_tr_ratios else 0
    tr_embed.description += f"\n**Overall Ratio**　ㆍ　`{ovr_tr_performance:.2f}`"
    embeds.append(tr_embed)
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
    profile = discord.Embed(colour=0xffffff, title=f"{member.display_name.replace('||', '\\|\\|').replace('_', '\\_')}")
    profile.set_thumbnail(url=f"{member.display_avatar}")
    profile.description = f"`{member.id}`\n{member.mention}\n`{member.name}`\n**Rank:** {rank}"
    embeds.append(profile)
    staff_id = str(member.id)
    weekly_profile = staffweeklycol.find_one({"_id": staff_id}) or {}
    full_break_role = ctx.guild.get_role(full_break)
    half_break_role = ctx.guild.get_role(half_break)
    bal = weekly_profile.get("breakbal", 12)
    is_full = full_break_role in member.roles
    is_half = half_break_role in member.roles
    if is_sr(member):
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
`c`　–　Checks a user or server.
`mc`　–　Checks a list of users (max 100), leave a space between users.
`a`　–　Checks a user for logged alts.
`ma`　–　Checks a list of users (max 100) for logged alts, leave a space between users.
`ca`　–　Checks a user and for their alts.
### utils
`t`　–　Searches for active/closed/all tickets based on text provided.
`ar`　–　Sends jump urls to all active reports in the thread.
`vr`　–　Sends a list of all reports in voting in the thread.
`pr`　–　Sends a list of all published reports in the thread.
`fm`　–　Sends a jump url to the first message in the thread.
`rn`　–　Renames the current thread to the new name provided.
`getids`　–　Extracts valid user IDs from the string provided.
### autoresponders
`sr`　–　Pings sr+.
`adm`　–　Pings adm+.
`tp`　–　Pings ticket ping.
`ban perms`　–　Pings ban perms.
`cl`　–　Sends closing guide.
`tags`　–　Sends tags descriptions.
### quota
`q`　–　Sends quota progress for this week.
`qh`　–　Sends quota history for the past 8 weeks.
`bb`　–　Sends break balance.
### leaderboard
`lb`　–　Sends the current week’s staff leaderboard.
`lbsr`　–　Sends the current week’s sr+ leaderboard.
        """
        await ctx.send(embed=embed)

tags_options = [
    discord.SelectOption(emoji="<:tri_redheart:1462285627243499655>", label="scammer", value="scammer"),
    discord.SelectOption(emoji="<:tri_redheart:1462285627243499655>", label="scam server owner", value="scam server owner"),
    discord.SelectOption(emoji="<:tri_redheart:1462285627243499655>", label="raider", value="raider"),
    discord.SelectOption(emoji="<:tri_redheart:1462285627243499655>", label="plagiarist", value="plagiarist"),
    discord.SelectOption(emoji="<:tri_redheart:1462285627243499655>", label="fake event host", value="fake event host"),
    discord.SelectOption(emoji="<:tri_redheart:1462285627243499655>", label="impersonator", value="impersonator"),
    discord.SelectOption(emoji="<:tri_redheart:1462285627243499655>", label="vouch scammer", value="vouch scammer"),
    discord.SelectOption(emoji="<:tri_yellowheart:1478132316122644544>", label="suspect", value="suspect"),
    discord.SelectOption(emoji="<:tri_yellowheart:1478132316122644544>", label="unprofessional mm", value="unprofessional mm"),
    discord.SelectOption(emoji="<:tri_yellowheart:1478132316122644544>", label="unprofessional pilot", value="unprofessional pilot"),
    discord.SelectOption(emoji="<:tri_yellowheart:1478132316122644544>", label="unprofessional supervisor", value="unprofessional supervisor"),
    discord.SelectOption(emoji="<:tri_yellowheart:1478132316122644544>", label="ex-offender", value="ex-offender"),
    discord.SelectOption(emoji="<:tri_yellowheart:1478132316122644544>", label="improper conduct", value="improper conduct"),
    discord.SelectOption(emoji="<:tri_yellowheart:1478132316122644544>", label="service ban", value="service ban"),
    discord.SelectOption(emoji="<:tri_redheart:1462285627243499655>", label="scam server", value="scam server"),
    discord.SelectOption(emoji="<:tri_redheart:1462285627243499655>", label="impersonator server", value="impersonator server"),
    discord.SelectOption(emoji="<:tri_redheart:1462285627243499655>", label="fake vouch server", value="fake vouch server"),
    discord.SelectOption(emoji="<:tri_redheart:1462285627243499655>", label="fake event server", value="fake event server"),
    discord.SelectOption(emoji="<:tri_yellowheart:1478132316122644544>", label="suspect server", value="suspect server"),
]

@bot.command(name="tags", help="Sends the descriptions of demerit tags.")
async def tags(ctx, *, tag: str = None):
    embed = discord.Embed(colour=0xffffff, title = "demerit　tags　⸝⸝.ᐟ", description="""
　　use the dropdown to select a tag and view its description.
    """)
    embed.add_field(
        name="user tags",
        value="""
-# <:tri_redheart:1462285627243499655> scammer
-# <:tri_redheart:1462285627243499655> scam server owner
-# <:tri_redheart:1462285627243499655> raider
-# <:tri_redheart:1462285627243499655> plagiarist
-# <:tri_redheart:1462285627243499655> fake event host
-# <:tri_redheart:1462285627243499655> impersonator
-# <:tri_redheart:1462285627243499655> vouch scammer
""",
        inline=True
    )
    embed.add_field(
        name="\u200b",
        value="""
-# <:tri_yellowheart:1478132316122644544> suspect
-# <:tri_yellowheart:1478132316122644544> unprofessional mm
-# <:tri_yellowheart:1478132316122644544> unprofessional pilot
-# <:tri_yellowheart:1478132316122644544> unprofessional supervisor
-# <:tri_yellowheart:1478132316122644544> ex-offender
-# <:tri_yellowheart:1478132316122644544> improper conduct
-# <:tri_yellowheart:1478132316122644544> service ban
""",
        inline=True
    )
    embed.add_field(
        name="server tags",
        value="""
-# <:tri_redheart:1462285627243499655> scam server
-# <:tri_redheart:1462285627243499655> impersonator server
-# <:tri_redheart:1462285627243499655> fake vouch server
-# <:tri_redheart:1462285627243499655> fake event server
-# <:tri_yellowheart:1478132316122644544> suspect server
    """,
        inline=False
    )
    await ctx.reply(embed=embed, view=TagsView())

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
## <a:tri_redarrow:1388148121242177726>　　scammer
　　**__definition__**

> users who have shown the **intention to, have attempted to, have admitted to, and/or have scammed**.
> 　⤷　applies __regardless__ of **whether the scam succeeded, and whether victim was able to recover the scammed possessions**.

　　**__examples__**

> - gaining possession of victim’s account/item(s) (directly or via MM), then ghosting/blocking without completing the trade and/or refusing to return account/item(s).
> - sending malicious links (e.g. beam links) used to steal accounts, items, or information. confrontation required.
> - providing a different account/item than agreed and refusing to compensate or trade back.
> - refusal, failure, or unreasonable delay in providing mutually accepted payment for services rendered.
> - refusing to refund or provide agreed items after receiving payment, including attempts to justify non-fulfilment under a “final sale” policy.
> - refusing to provide warranty, replacement, or refund for an account or item after a trade when no prior “no warranty” agreement was clearly stated or mutually accepted.
> - faking account/item details (e.g. advertising using edited or stolen screenshots).
> - retrieving an account or filing chargebacks after a completed trade to reclaim money or assets.
> - causing damage to others’ account or items, especially with malicious intent.

　　**__notes__**

> - **admitting to scamming** – only reportable with proof & context (e.g. hit logs). claims alone aren’t enough.
> - **scam backs** – open a ticket before attempting a scam back to avoid being reported. please provide proof of original ownership and proof of the scam.

-# **confrontation is __strongly preferred__ and in some cases, required.** do be polite as much as possible. if ghosted/blocked upon confrontation, it is considered reportable.
""")
            await interaction.response.send_message(embed=embed, ephemeral=True)
        if self.select_callback.values[0] == "scam server owner":
            embed = discord.Embed(colour=0xFF0045, description="""
## <a:tri_redarrow:1388148121242177726>　　scam server owner
　　**__definition__**

> users who **own scam servers** or have owned scam servers in the past.

　　**__examples__**

> - owner of shop server, using the server to scam.
> - guild ownership holder of hitter server.

　　**__notes__**

> - screenshots of **vencord** or **serverinfo bot command** are preferred. if you do not have vencord, ask another staff for help.
> - the scam server owner may only be appealed if the scam server has been appealed.
""")
            await interaction.response.send_message(embed=embed, ephemeral=True)
        if self.select_callback.values[0] == "raider":
            embed = discord.Embed(colour=0xFF0045, description="""
## <a:tri_redarrow:1388148121242177726>　　raider
　　**__definition__**

> users who have **raided** or threatened to raid server(s).
> 　⤷　raiding is defined as: mass-banning server members, mass-deleting channels, spamming messages in server channels or server members’ dms, etc.

　　**__examples__**

> - participating in, coordinating, or assisting a raid, regardless of success or scale.
> - supplying raid tools, bots, or scripts to others for the purpose of raiding.

　　**__notes__**

> - it is not reportable if
>   - the raid targets a server primarily used for malicious, fraudulent, or otherwise unlawful activities.
>   - the threat to raid was meant as a joke.

-# **confrontation is __strongly preferred__ and in some cases, required.** do be polite as much as possible. if ghosted/blocked upon confrontation, it is considered reportable.
""")
            await interaction.response.send_message(embed=embed, ephemeral=True)
        if self.select_callback.values[0] == "plagiarist":
            embed = discord.Embed(colour=0xFF0045, description="""
## <a:tri_redarrow:1388148121242177726>　　plagiarist
　　**__definition__**

> users who have claimed others’ creative works as their own, or have shared/used such works without the rightful owner’s permission.
> 　⤷　includes audio, visual, written works etc.

　　**__examples__**

> - claiming others’ creative works as one’s own, including ai-generated works.
> - heavily referencing, copying, or tracing another person’s artwork and claiming it as original.
> - failing to disclose significant references, tracing, or use of another’s work when offering the creative work(s) for sale.

-# **confrontation is __required__.** do be polite as much as possible. if ghosted/blocked upon confrontation, it is considered reportable.
""")
            await interaction.response.send_message(embed=embed, ephemeral=True)
        if self.select_callback.values[0] == "fake event host":
            embed = discord.Embed(colour=0xFF0045, description="""
## <a:tri_redarrow:1388148121242177726>　　fake event host
　　**__definition__**

> users who have hosted events and refused to or repeatedly delayed giving the participant their prize/reward provided that the participant had followed all rules strictly.
> 　⤷　e.g. giveaways, invite rewards.

-# **confrontation is __required__.** do be polite as much as possible. if ghosted/blocked upon confrontation, it is considered reportable.
""")
            await interaction.response.send_message(embed=embed, ephemeral=True)
        if self.select_callback.values[0] == "impersonator":
            embed = discord.Embed(colour=0xFF0045, description="""
## <a:tri_redarrow:1388148121242177726>　　impersonator
　　**__definition__**

> users who deliberately imitate or copy the profile, name, layout and/or description of another user without the real user’s permission, with the intent of deception
> 　⤷　use of another’s identity with malicious intent.

-# **confrontation is __required__.** do be polite as much as possible. if ghosted/blocked upon confrontation, it is considered reportable.
""")
            await interaction.response.send_message(embed=embed, ephemeral=True)
        if self.select_callback.values[0] == "vouch scammer":
            embed = discord.Embed(colour=0xFF0045, description="""
## <a:tri_redarrow:1388148121242177726>　　vouch scammer
　　**__definition__**

> users who use fake or spammed (often botted) vouches or stolen proofs/vouches, with the intent of deceiving others.
> users who sell/trade fake or spammed vouches, therefore enabling vouch scammers to deceive others.
> 　⤷　show evidence of vouches left by ≥4 users with similar account creation dates.

　　**__notes__**

> - a server owner may be reported as vouch scammer for allowing spammed vouches in a trading server.
> - neither the vouched user nor voucher are reportable unless there is evidence of them scamming/attempting to scam.

-# **confrontation is __required__.** do be polite as much as possible. if ghosted/blocked upon confrontation, it is considered reportable.
""")
            await interaction.response.send_message(embed=embed, ephemeral=True)
        if self.select_callback.values[0] == "suspect":
            embed = discord.Embed(colour=0xFFD643, description="""
## <a:tri_yellowarrow:1509836964453548133>　　suspect
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

-# **confrontation is __required__.** do be polite as much as possible. if ghosted/blocked upon confrontation, it is considered reportable.
""")
            await interaction.response.send_message(embed=embed, ephemeral=True)
        if self.select_callback.values[0] == "unprofessional mm":
            embed = discord.Embed(colour=0xFFD643, description="""
wip
            
## <a:tri_yellowarrow:1509836964453548133>　　unprofessional mm
　　**__definition__**

> mm is deemed unprofessional if they have proven to be irresponsible in their service.
> 　⤷　reports relating to idv will have additional remarks.

　　**__examples__**

> - failing to follow essential mm procedures, resulting in item(s)/account(s) being exposed to preventable, unnecessary, or unreasonable risk(s), including reduced recoverability in the event of a scam.
>   - failing to verify the validity of receipts provided in DMs or the ticket, regardless of whether the trader consented to the lost receipts risk.
>   - failing to verify basic account details before transferring the account.
> - failing to resolve discrepancies or follow the trading server’s required mm procedure before proceeding.
>   - proceeding despite incomplete or inaccurate mm forms, and failure to provide documented proof that both traders agreed to the trade before it proceeded, creating ambiguity between the account(s)/item(s) described and those actually traded.
> - knowingly breaking reasonable service rules of a trading server in which they are a mm, especially rules set in place to ensure the mm’s and traders’ safety.
> - failing to disclose foreseeable, material risk(s) before proceeding with a trade, where a reasonable trader may have chosen not to proceed if informed.
> - negligently handling an account or item, resulting in avoidable loss, damage, or retrieval.
>   - incorrectly securing an account and/or its linked email, resulting in retrieval.
>   - altering the state of an account without both traders’ permission.
>   - losing an account through negligence.
> - knowingly mming for scammer(s) which resulted in item(s)/account(s) being lost, damaged, or retrieved.

　　**__notes__**

> - it is not reportable if
>   - mm lost an account in an unpreventable situation and offered compensation that the trader was satisfied with, or continually attempted to offer compensation, subject to limitations such as the mm’s financial ability.
>   - account was retrieved in an unpreventable situation and the trader consented to the risks beforehand.
>   - mm is new/unfamiliar with the rules of the discord trading community.
""")
            await interaction.response.send_message(embed=embed, ephemeral=True)
        if self.select_callback.values[0] == "unprofessional pilot":
            embed = discord.Embed(colour=0xFFD643, description="""
## <a:tri_yellowarrow:1509836964453548133>　　unprofessional pilot
　　**__definition__**

> pilot is deemed unprofessional if they have proven to be irresponsible in their service.

　　**__examples__**

> - failing to exercise reasonable care while handling a client’s account, resulting in preventable, unnecessary and unreasonable risk(s). including but not limited to:
>   - leaking or sharing login information without the client’s or account owner’s permission.
>   - using a virtual machine to run a game that prohibits the use of virtual machines (especially hoyoverse games) without the client’s permission.
>   - using cheats or modifications without the client’s prior consent.
>   - adding third party links to the account without the client’s permission.
> - knowingly violating reasonable service rules of a trading server in which they are a pilot, particularly rules intended to protect the pilot and client. this will be reviewed on a case-by-case basis.
> - negligently handling a client’s account, resulting in avoidable loss, damage, or penalties in a preventable situation.
>   - failing to generate a transfer code after completing a project sekai piloting service.
>   - performing actions beyond the agreed service (e.g. wishing without permission, opening additional chests, or completing quests not requested by the client).
>   - using cheats or plugins that result in temporary or permanent account bans.
>   - trainees disregarding their supervisor's instructions or failing to seek guidance, resulting in account loss or damage.
> - failing to complete the agreed service within a reasonable timeframe without sufficient justification. this will be reviewed on a case-by-case basis, taking into account factors including but not limited to:
>   - insufficient effort relative to the size of the task;
>   - failing to request an extension;
>   - completing less than 50% of the agreed service by the deadline;
>   - the service fee having been paid, in part or in full, beforehand.
> - failing to follow essential pilot procedures or maintain adequate documentation.
>   - failing to send login and/or logout screenshots, unless prevented by exceptional circumstances (e.g. the client traded away the account or scammed the pilot).

　　**__notes__**

> - it is not reportable if
>   - the agreed time limit was unreasonable, the pilot was actively working on the service and providing updates, and/or the client failed to provide reasonable reminders or warnings before reporting.
>   - account received a temporary ban and there is insufficient evidence that the pilot caused it.
>   - pilot is new/unfamiliar with the rules of the discord trading community.
""")
            await interaction.response.send_message(embed=embed, ephemeral=True)
        if self.select_callback.values[0] == "unprofessional supervisor":
            embed = discord.Embed(colour=0xFFD643, description="""
## <a:tri_yellowarrow:1509836964453548133>　　unprofessional supervisor
　　**__definition__**

> supervisor is deemed unprofessional if they have proven to be irresponsible in their supervision of trainee(s).

　　**__examples__**

> - not ensuring that the correct mm/pilot form has been sent and correctly filled at the start of the service.
> - not checking login and/or logout screenshots fully, or telling the trainee to proceed when there are several missing screenshots. refer to appendix (screenshots) for more details.
> - not instructing the trainee to ping them before proceeding and the trainee proceeded to put the client’s item(s)/account(s) at risk.

　　**__notes__**

> - it is not reportable if
>   - supervisor instructed the trainee to ping them before proceeding, but the trainee ignored this instruction and proceeded to put the client’s item(s)/account(s) at risk.
""")
            await interaction.response.send_message(embed=embed, ephemeral=True)
        if self.select_callback.values[0] == "ex-offender":
            embed = discord.Embed(colour=0xFFD643, description="""
## <a:tri_yellowarrow:1509836964453548133>　　ex-offender
　　**__definition__**

> users who have committed offences reportable under any of the following tags: scammer, scam server owner, raider, plagiarist, fake event host, impersonator, vouch scammer and have shown themselves to no longer have committed such offences after a minimum report period.
> 　⤷　they must also provide proofs showing that they have genuinely changed since the incident. simply claiming to be sorry or promising not to repeat the offense is generally insufficient.
""")
            await interaction.response.send_message(embed=embed, ephemeral=True)
        if self.select_callback.values[0] == "improper conduct":
            embed = discord.Embed(colour=0xFFD643, description="""
## <a:tri_yellowarrow:1509836964453548133>　　improper conduct
　　**__definition__**

> users who have been excessively rude or disruptive in report/appeal tickets, breaking server rule(s).

　　**__examples__**

> - expressing homophobic, xenophobic, racist, sexist, etc. sentiments towards others
> - threats of violence or intimidation.
> - insults, harassment, or hostility towards staff or other users.
> - attempts at bribery, coercion, blackmail, or manipulation.

　　**__notes__**

> - this tag does not affect the credibility of a user, but serves to discourage inappropriate behaviour towards staff and maintain respectful proceedings.
""")
            await interaction.response.send_message(embed=embed, ephemeral=True)
        if self.select_callback.values[0] == "service ban":
            embed = discord.Embed(colour=0xFFD643, description="""
## <a:tri_yellowarrow:1509836964453548133>　　service ban
　　**__definition__**

> users who have made services unpleasant for others, which may include the mm/pilot.

　　**__examples__**

> - constantly ghosting or slow responses without informing beforehand.
> - frequently ghosting or refusing to vouch on 3 or more separate occasions despite 3 or more reminders that are minimally 1h apart.
> - delaying the giving of fee or changing fee to something unsatisfactory.
> - changing the task and/or fee that has been initially agreed-upon by both parties and refusing to pay the initially agreed-upon fee if the pilot declines to change to the new task.

　　**__notes__**

> - it is not reportable if
>   - there is only evidence of a singular occurrence.
>   - the user made an effort to compensate for the trouble within their ability.
> - this is usually determined based on the shared sentiments of 2 or more mms/pilots, and will be reviewed on a case-by-case basis.
""")
            await interaction.response.send_message(embed=embed, ephemeral=True)
        if self.select_callback.values[0] == "scam server":
            embed = discord.Embed(colour=0xFF0045, description="""
## <a:tri_redarrow:1388148121242177726>　　scam server
　　**__definition__**

> server promotes or is used for scamming, e.g. fake mm or hitter services.
> server owner(s) must be involved, or allow scams to happen within the server.
> users are reportable as scam server owner for simply having ownership of scam server(s), as shown via vencord, serverinfo bot command or the built-in crown symbol.
> server staff and/or members are only reportable as scammer if there is sufficient evidence of them scamming. simply being part of a scam server is, on its own, insufficient.
> higher staff (e.g. mm and above) may be reportable as suspect if they hold such roles and are active in such scam servers.

　　**__notes__**

> - it is not reportable if
>   - the server owner(s) refuse to ban scammer(s) who have not scammed within the server.
> - not reportable under this tag
>   - impersonator server, fake vouch server or fake event server that does not have any scam activity.
>   - however, if there is scam activity occurring in any of the above types of servers, the server will be reportable under all relevant tags.
> - it is appealable if
>   - ownership of the server has changed and the new owner is taking steps to prevent all scam activity within the server.
""")
            await interaction.response.send_message(embed=embed, ephemeral=True)
        if self.select_callback.values[0] == "impersonator server":
            embed = discord.Embed(colour=0xFF0045, description="""
## <a:tri_redarrow:1388148121242177726>　　impersonator server
　　**__definition__**

> server which deliberately imitates or copies the icon, name, layout, bots, roles and/or channels of another server without the real server’s owners’ permission, or falsely claims to be the official discord server of a known/registered website/organisation, with the intent of deception, i.e. impersonation with intent to defraud.
> users are reportable as scam server owner for simply having ownership of impersonator server(s), as shown via vencord, serverinfo bot command or the built-in crown symbol.
> users are reportable as scammers if there is evidence of them scamming, or reportable as impersonator if there is evidence of them impersonating. however, they are not reportable for simply being a member of an impersonator server.

　　**__notes__**

> - it is not reportable if
>   - it may be a joke.
>   - the server owner(s) were unaware/did not have malicious intent and agree to change the icon, name, layout, bots, roles and/or channels.
""")
            await interaction.response.send_message(embed=embed, ephemeral=True)
        if self.select_callback.values[0] == "fake vouch server":
            embed = discord.Embed(colour=0xFF0045, description="""
## <a:tri_redarrow:1388148121242177726>　　fake vouch server
　　**__definition__**

> server with fake or spammed (often botted) vouches, vouch server owned by scammer, or server that steals vouches, with the intent of deceiving others.
> servers that sell, buy or trade fake or spammed vouches.

""")
            await interaction.response.send_message(embed=embed, ephemeral=True)
        if self.select_callback.values[0] == "fake event server":
            embed = discord.Embed(colour=0xFF0045, description="""
## <a:tri_redarrow:1388148121242177726>　　fake event server
　　**__definition__**

> server which hosted events e.g. giveaways, invite rewards and refused to or repeatedly delayed giving the participant their prize/reward provided that the participant had followed all rules strictly, and owners and/or other staff made no effort to resolve the situation, such as prohibiting the host from further hosting events.
> the event host is reportable as fake event host.
""")
            await interaction.response.send_message(embed=embed, ephemeral=True)
        if self.select_callback.values[0] == "suspect server":
            embed = discord.Embed(colour=0xFFD643, description="""
## <a:tri_yellowarrow:1509836964453548133>　　suspect server
　　**__definition__**

> server within which scam activity is suspected to have been occurring, or suspected backup server of a scam server.
""")
            await interaction.response.send_message(embed=embed, ephemeral=True)

closing_options = [
    discord.SelectOption(emoji="<:tri_whiteheart:1434538078747365507>", label="ㆍㆍreport", value="report"),
    discord.SelectOption(emoji="<:tri_whiteheart:1434538078747365507>", label="ㆍㆍappeal", value="appeal"),
    discord.SelectOption(emoji="<:tri_whiteheart:1434538078747365507>", label="ㆍㆍverify", value="verify"),
    discord.SelectOption(emoji="<:tri_whiteheart:1434538078747365507>", label="ㆍㆍothers", value="others"),
    discord.SelectOption(emoji="<:tri_whiteheart:1434538078747365507>", label="ㆍㆍsr+", value="sr+"),
]

@bot.command(name="cl", help="Sends closing guide.")
async def cl(ctx, *, string: str = None):
    if ctx.guild.id == TRI_Archive:
        await ctx.reply(embed=discord.Embed(colour=0xffffff, title = "closing　guide　⸝⸝.ᐟ", description="""
- rename ticket　–　`,rn 𝐧𝐚𝐦𝐞 tbc`
- ping sr+　–　`,sr`
- see format for closing statements using the dropdown below.
- please merge identical reasons.
- for mass reports, you may wish to use `,pr` after reports are published to retrieve ids easily.
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
  - `new report on 𝐢𝐝 (alt 𝐢𝐝) as 𝐭𝐚𝐠`
  - `new report on 𝐢𝐝 (alt 𝐢𝐝) 𝐢𝐝 (alts 𝐢𝐝 𝐢𝐝) as 𝐭𝐚𝐠, 𝐭𝐚𝐠`
  - `new report on 𝐠𝐚𝐦𝐞ㆍ𝐮𝐢𝐝 as 𝐭𝐚𝐠`
  - `new report on 𝐠𝐚𝐦𝐞ㆍ𝐮𝐢𝐝 (link 𝐠𝐚𝐦𝐞ㆍ𝐮𝐢𝐝) as 𝐭𝐚𝐠`
- added report
  - `added report on 𝐢𝐝 as 𝐭𝐚𝐠`
- edited alts only
  - `edited alts for 𝐢𝐝 - added 𝐢𝐝 𝐢𝐝, removed 𝐢𝐝`
  - `edited alts for 𝐢𝐝 - 𝐢𝐝 merged into 𝐢𝐝`
- edited server owner
  - `edited server owner for 𝐢𝐝 - from 𝐢𝐝 to 𝐢𝐝`
- edited links only
  - `edited links for 𝐠𝐚𝐦𝐞ㆍ𝐮𝐢𝐝 - added 𝐠𝐚𝐦𝐞ㆍ𝐮𝐢𝐝 𝐠𝐚𝐦𝐞ㆍ𝐮𝐢𝐝, removed 𝐠𝐚𝐦𝐞ㆍ𝐮𝐢𝐝`
- no report
  - `no report on 𝐢𝐝 // invalid reason`
  - `no report on 𝐢𝐝 // insufficient proof`
  - `no report on 𝐢𝐝 // warned for service ban`
  - `no report on 𝐢𝐝 // deleted user`
  - `no report on 𝐢𝐝 // issue resolved`
  - `no report on 𝐢𝐝 // unresponsive contributor`
  - `no report on 𝐢𝐝 // contributor left server`
"""), ephemeral=True)
        if self.select_callback.values[0] == "appeal":
            await interaction.response.send_message(embed=discord.Embed(description="""
- accepted appeal
  - `accepted appeal on 𝐢𝐝 as 𝐭𝐚𝐠`
- no appeal / rejected appeal
  - `no appeal on 𝐢𝐝 // invalid reason`
  - `no appeal on 𝐢𝐝 // insufficient proof`
  - `no appeal on 𝐢𝐝 // unreported`
  - `no appeal on 𝐢𝐝 // unresponsive contributor`
  - `no appeal on 𝐢𝐝 // contributor left server`
"""), ephemeral=True)
        if self.select_callback.values[0] == "verify":
            await interaction.response.send_message(embed=discord.Embed(description="""
- successful manual verification
  - `𝐢𝐝 manually verified`
- user verified themselves
  - `successfully verified`
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
  - `unresponsive contributor`
  - `contributor left server`
"""), ephemeral=True)
        if self.select_callback.values[0] == "sr+":
            await interaction.response.send_message(embed=discord.Embed(description="""
- rename ticket
  - `,rn 𝐧𝐚𝐦𝐞 tbc (𝐬𝐫 𝐧𝐚𝐦𝐞)`
- check active reports and give feedback. set a reminder for 3h to reping reporter if needed.
  - `,ar`
  - `,rm 3`
- if done correctly, accept reports for voting in order.
- check reports in voting. set a reminder for 6h to check if reports can be published.
  - `,vr`
  - `,rm 6`
- requires 5 agree votes to publish. 8 agree votes = auto-publish, 12 disagree votes = auto-reject.
- check published reports
  - `,pr`
  - `,c 𝐢𝐝` or `,mc 𝐢𝐝 𝐢𝐝 𝐢𝐝`
- `,close` to close the ticket. ask reporter for closing if not provided in closing embed. **check** the closing and ensure it’s correct.
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
async def ban_perms(ctx, *, perms: str):
    if not perms or perms.lower() != "perms":
        return
    if ctx.guild.id == TRI_Archive:
        await ctx.reply(f"<@&{ban_perms}>")
    elif ctx.guild.id == tethys:
        await ctx.reply(f"<@&{tethys_ban_perms}>")

@bot.command(name="proof", help="Sends proof autoresponder.")
async def proof(ctx):
    if ctx.guild.id == TRI_Archive:
        embed = discord.Embed(colour=0xffffff, description="""
## ‎　report proofs

provide relevant user ids, server invites & ids, or game uids. 
-# _not just usernames, since usernames can change._
-# 　⤷　how to obtain user/server id? guide [here](https://support.discord.com/hc/en-us/articles/206346498-Where-can-I-find-my-User-Server-Message-ID).

**screenshots are strongly preferred**, followed by screen recordings or html files.

please show **entire conversation, _from start to end_**
-# _do not crop, omit, delete, or edit any messages related to the report until the investigation is complete._

- for **breach of agreement** reports, show the following
  - trade agreement
  - proof you fulfilled your side
  - proof of payment
  - confrontation & outcome (excuses, blocking, ghosting)

- additional requirements
  - **timestamps** should be visible
  - if you've blocked the other user, **temporarily unblock them** before taking screenshots so the conversation displays correctly.
  - for crypto payments, send **blockchain txids**.

**__uncropped__ & unedited**
show your **entire screen**. sensitive personal information such as real names, passwords, ip addresses, or other private information may be blurred.

**video too large**
upload your video at [catbox.moe](https://catbox.moe) and copy & paste the link here.
        """)
        await ctx.channel.send(embed=embed, view=ProofView(ctx.author))

class ProofView(discord.ui.View):
    def __init__(self, requested_by: discord.User):
        super().__init__(timeout=120)
        self.requested_by = requested_by

        self.report_button = discord.ui.Button(
            label="report",
            emoji="<:tri_redheart:1462285627243499655>",
            style=discord.ButtonStyle.grey,
            disabled=True,
            custom_id="proof:report"
        )
        self.appeal_button = discord.ui.Button(
            label="appeal",
            emoji="<:greenheart:1522917891090026650>",
            style=discord.ButtonStyle.grey,
            disabled=False,
            custom_id="proof:appeal"
        )

        self.report_button.callback = self.report_callback
        self.appeal_button.callback = self.appeal_callback

        self.add_item(self.report_button)
        self.add_item(self.appeal_button)

    async def appeal_callback(self, interaction: discord.Interaction):
        self.appeal_button.disabled = True
        self.report_button.disabled = False

        if interaction.user.id != self.requested_by.id:
            return

        embed=(discord.Embed(colour=0xffffff, description="""
## ‎　appeal proofs

**screenshots are strongly preferred**, followed by screen recordings or html files.

please provide clear proofs supporting your appeal.
-# _do not crop, omit, delete, or edit any messages related to the appeal until the investigation is complete._

- depending on your appeal, show the following
  - the full context surrounding the incident.
  - any proofs that contradicts or explains the report against you.
  - if you believe the report contains **false** or **misleading** information, clearly identify which parts and provide supporting evidence.

- additional requirements
  - **timestamps** should be visible
  - if you've blocked the other user, **temporarily unblock them** before taking screenshots so the conversation displays correctly.
  - for crypto payments, send **blockchain txids**.

- appeals based on minimum report period (mrp)
  - appeals based solely on meeting the mrp are **not guaranteed** and are reviewed on a case by case basis.
  - you must provide proofs showing that you have genuinely changed since the incident. simply claiming to be sorry or promising not to repeat the offense is generally insufficient.

**__uncropped__ & unedited**
show your **entire screen**. sensitive personal information such as real names, passwords, ip addresses, or other private information may be blurred.

**video too large**
upload your video at [catbox.moe](https://catbox.moe) and copy & paste the link here.
"""))
        await interaction.response.edit_message(embed=embed, view=self)

    async def report_callback(self, interaction: discord.Interaction):
        self.appeal_button.disabled = False
        self.report_button.disabled = True

        if interaction.user.id != self.requested_by.id:
            return

        embed=(discord.Embed(colour=0xffffff, description="""
## ‎　report proofs

provide relevant user ids, server invites & ids, or game uids. 
-# _not just usernames, since usernames can change._
-# 　⤷　how to obtain user/server id? guide [here](https://support.discord.com/hc/en-us/articles/206346498-Where-can-I-find-my-User-Server-Message-ID).

**screenshots are strongly preferred**, followed by screen recordings or html files.

please show **entire conversation, _from start to end_**
-# _do not crop, omit, delete, or edit any messages related to the report until the investigation is complete._

- for **breach of agreement** reports, show the following
  - trade agreement
  - proof you fulfilled your side
  - proof of payment
  - confrontation & outcome (excuses, blocking, ghosting)

- additional requirements
  - **timestamps** should be visible
  - if you've blocked the other user, **temporarily unblock them** before taking screenshots so the conversation displays correctly.
  - for crypto payments, send **blockchain txids**.

**__uncropped__ & unedited**
show your **entire screen**. sensitive personal information such as real names, passwords, ip addresses, or other private information may be blurred.

**video too large**
upload your video at [catbox.moe](https://catbox.moe) and copy & paste the link here.
"""))
        await interaction.response.edit_message(embed=embed, view=self)

@bot.command(name="rm")
@commands.cooldown(2, 600, commands.BucketType.channel)
@commands.has_any_role(staff_role)
async def rm(ctx, hours: int = None):
    if isinstance(ctx.channel, discord.Thread):
        if ctx.channel.parent_id != TICKET_CHANNEL:
            return
    else:
        return await ctx.send("This command can only be used in a thread.")
    thread = ctx.channel
    if hours is None:
        reminder = reminders.find_one({"thread_id": thread.id})
        if reminder:
            now = datetime.datetime.now(datetime.timezone.utc).timestamp()
            remaining = reminder["end_time"] - now
            hours_left = max(1, int((remaining + 3599) // 3600))
            expected_name = f"{reminder['base_name']} - {hours_left}h"
            if thread.name != expected_name:
                try:
                    await thread.edit(name=expected_name)
                except:
                    pass
        return
    if hours < 0:
        return await ctx.reply("Hours must be at least 0.")
    elif hours < 1:
        reminder = reminders.find_one({"thread_id": thread.id})
        if reminder:
            base_name = reminder["base_name"]
            if thread.name != base_name:
                try:
                    await thread.edit(name=base_name)
                except:
                    pass
            reminders.delete_one({"thread_id": thread.id})
            await ctx.reply(f"Reminder deleted.")
        return
    base_name = (thread.name.rsplit(" - ", 1)[0]).replace("on hold", "").strip()
    await thread.edit(name=f"{base_name} - {hours}h")
    reminders.update_one(
        {"thread_id": thread.id},
        {
            "$set": {
                "thread_id": thread.id,
                "user_id": ctx.author.id,
                "end_time": (
                        datetime.datetime.now(datetime.timezone.utc)
                        + datetime.timedelta(hours=hours)
                ).timestamp(),
                "base_name": base_name
            }
        },
        upsert=True
    )
    await ctx.reply(f"Reminder set for {hours}h.")

@rm.error
async def rm_error(ctx, error):
    if isinstance(error, commands.CommandOnCooldown):
        now_ts = datetime.datetime.now(datetime.timezone.utc).timestamp()
        retry_at = int(now_ts + error.retry_after)
        return await ctx.send(
            f"This command is on cooldown. Retry <t:{retry_at}:R>."
        )
    raise error

@bot.command(name="rn")
@commands.cooldown(2, 600, commands.BucketType.channel)
@commands.has_any_role(staff_role, tethys_staff_role)
async def rn(ctx, *, new_name: str):
    if isinstance(ctx.channel, discord.Thread):
        if ctx.channel.parent_id != TICKET_CHANNEL and ctx.channel.parent_id != TRAINING_CHANNEL:
            return
        try:
            new_name = int(new_name)
        except ValueError: pass
        else:
            await ctx.reply(f"Did you mean `,rm {new_name}`?")
        try:
            reminder = reminders.find_one({"thread_id": ctx.channel.id})
            reminder_text = ""
            if reminder:
                reminders.delete_one({"thread_id": ctx.channel.id})
                reminder_text = "Reminder deleted."
            await ctx.channel.edit(name=new_name)
            if reminder_text:
                await ctx.reply(reminder_text)
        except Exception as e:
            await ctx.send(f"Renaming failed due to an error: {e}")
    else:
        await ctx.send("This command can only be used in a thread.")
@rn.error
async def rn_error(ctx, error):
    if isinstance(error, commands.CommandOnCooldown):
        now_ts = datetime.datetime.now(datetime.timezone.utc).timestamp()
        retry_at = int(now_ts + error.retry_after)
        return await ctx.send(
            f"This command is on cooldown. Retry <t:{retry_at}:R>."
        )
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


@bot.command(name="lb", help="Sends the current week’s staff leaderboard.")
@commands.has_any_role(staff_role)
async def lb(ctx, *args):
    if args:
        return
    role_categories = {
        o5_role: ("overseers", []),
        adm_role: ("admins", []),
        sr_role: ("senior reporters", []),
        tsr_role: ("trial senior reporters", []),
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
        tickets = staff_profile.get("tickets", 0)
        weekly_tickets = weekly_profile.get("weekly_tickets", 0)
        role_categories[matched_role][1].append(
            (member, reports, weekly_reports, tickets, weekly_tickets)
        )
    all_embeds = []
    for role_id, (title, staff_list) in role_categories.items():
        if not staff_list:
            continue
        embed = discord.Embed(colour=0xffffff, description=f"\n\n**✦　　–　　{title}**")
        staff_list.sort(key=lambda x: (x[4], x[2]), reverse=True)
        for i, (member, reports, weekly_reports, tickets, weekly_tickets) in enumerate(staff_list, start=1):
            embed.description += (
                f"\n-# {i}ㆍ{member.mention}"
                f"\n-# _ _　tickets　–　**{tickets}** all ㆍ **{weekly_tickets}** week"
                f"\n-# _ _　reports　–　**{reports}** all ㆍ **{weekly_reports}** week"
            )
        all_embeds.append(embed)
    if all_embeds:
        await ctx.reply("## _ _　　　staff leaderboard", embeds=all_embeds)

@bot.command(name="lbsr", help="Sends the current week’s sr+ leaderboard.")
@commands.has_any_role(staff_role)
async def lbsr(ctx):
    role_categories = {
        o5_role: ("overseers", []),
        adm_role: ("admins", []),
        sr_role: ("senior reporters", []),
        tsr_role: ("trial senior reporters", [])
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
        closes = staff_profile.get("closes", 0)
        weekly_closes = weekly_profile.get("weekly_closes", 0)
        role_categories[matched_role][1].append(
            (member, reviews, weekly_reviews, closes, weekly_closes)
        )

    all_embeds = []
    for role_id, (title, staff_list) in role_categories.items():
        if not staff_list:
            continue
        embed = discord.Embed(colour=0xffffff, description=f"\n\n**✦　　–　　{title}**")
        staff_list.sort(key=lambda x: (x[4], x[2]), reverse=True)
        for i, (member, reviews, weekly_reviews, closes, weekly_closes) in enumerate(staff_list, start=1):
            embed.description += (
                f"\n-# {i}ㆍ{member.mention}"
                f"\n-# _ _　closes　–　**{closes}** all ㆍ **{weekly_closes}** week"
                f"\n-# _ _　reviews　–　**{reviews}** all ㆍ **{weekly_reviews}** week"
            )
        all_embeds.append(embed)
    if all_embeds:
        await ctx.reply("## _ _　　　sr+ leaderboard", embeds=all_embeds)

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

LANGUAGE_ROLES = {
    "Chinese": 1527931955482460271,
    "Japanese": 1527932415551602750,
    "Korean": 1527932443284471829,
    "Indonesian": 1527933151723126965,
    "Malay": 1527933164918411284,
    "Thai": 1527933184556404819,
    "Vietnamese": 1527933269965017118,
    "Filipino": 1527933646562918410,
    "Hindi": 1527933660232155176,
    "Urdu": 1527933690812960860,
    "Arabic": 1527933714313510973,
    "Persian": 1527933736036073472,
    "Turkish": 1527933069342937109,
    "Spanish": 1527932559936327740,
    "French": 1527932583420100719,
    "German": 1527932613673746543,
    "Portuguese": 1527932709769576529,
    "Russian": 1527932642899660881,
    "Italian": 1527932770536390726,
    "Polish": 1527933109545205914,
    "Dutch": 1527933121872400504,
}

class TranslateSelect(discord.ui.Select):
    def __init__(self):
        options = [discord.SelectOption(label=name, value=str(role)) for name, role in LANGUAGE_ROLES.items()]
        super().__init__(
            placeholder="‎　　Select a language . . .　　　",
            min_values=1,
            max_values=1,
            options=options,
            custom_id="translate_select"
        )
    async def callback(self, interaction: discord.Interaction):
        role_id = int(self.values[0])
        await interaction.response.defer()
        await interaction.channel.send(f"<@&{role_id}>")
        await interaction.message.delete()

class TranslateView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TranslateSelect())

@bot.command(name="translate")
async def translate(ctx):
    if any(role.id in (ticket_ping, staff_role) for role in ctx.author.roles):
        await ctx.send(view=TranslateView())

class LanguagesSelect(discord.ui.Select):
    def __init__(self):
        options = [discord.SelectOption(label=name, value=str(role_id)) for name, role_id in LANGUAGE_ROLES.items()]
        super().__init__(
            placeholder="‎　　Select a language . . .　　　",
            min_values=1,
            max_values=1,
            options=options,
            custom_id="language_roles"
        )

    async def callback(self, interaction: discord.Interaction):
        role = interaction.guild.get_role(int(self.values[0]))
        if role in interaction.user.roles:
            await interaction.user.remove_roles(role)
            msg = f"Removed {role.mention}."
        else:
            await interaction.user.add_roles(role)
            msg = f"Added {role.mention}."
        await interaction.response.send_message(msg, ephemeral=True)

class LanguageRolesView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(LanguagesSelect())

# slash commands

staff = app_commands.Group(name="staff", description="Staff.")
bot.tree.add_command(staff)

@staff.command(name="accepted", description="Assigns trainee roles to accepted staff.")
@app_commands.checks.has_role(adm_ping)
@app_commands.describe(user="User to assign roles.")
async def staff_accepted(interaction: discord.Interaction, user: discord.Member):
    try:
        await user.add_roles(interaction.guild.get_role(int(t_role)), interaction.guild.get_role(int(staff_role)), interaction.guild.get_role(int(new_staff)))
        await user.edit(nick=f"tㆍ{user.display_name}")
    except:
        return await interaction.response.send_message("Unable to assign trainee roles to the user.")
    else:
        await interaction.response.send_message("Successfully assigned trainee roles to the user.")

send = app_commands.Group(name="send", description="Send embeds/rules/guides.")
bot.tree.add_command(send)

@send.command(name="verify", description="Sends verify embed.")
@app_commands.checks.has_role(adm_ping)
async def send_verify(interaction: discord.Interaction, colour: str=None, image: discord.Attachment=None):
    await interaction.response.defer(ephemeral=True)
    colour = discord.Colour(int(colour.strip("#"), 16)) if colour else 0xffffff
    if image:
        image_embed = discord.Embed(colour=colour)
        image_embed.set_image(url=image.url)
        await interaction.channel.send("_ _", embed=image_embed)
    await interaction.channel.send(embed=discord.Embed(colour=colour, description="""
<:tri_whiteheart:1434538078747365507>　verify  to  access  the  rest  of  the  server

### _ _　　꒰ <a:tri_purpleflower:1515565233798778930>　Verify　Below　⟣
_ _
◟　if access denied, miku will **automatically verify you** .ᐟ
◟　other issues or still need help? _[open ticket](https://discord.com/channels/1371673839695826974/1375261699111784478)_
"""))
    await interaction.followup.send("Verify embed has been sent.", ephemeral=True)


class StaffRulesView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(discord.ui.Button(label="Staff Legal Codex", style=discord.ButtonStyle.grey,
                                        url="https://docs.google.com/document/d/18GPfRrvzJ4b1d6cJ_yLyd1HELJbE4y9PqBH5-FVQktc/"))

staff_guide_options = [
    discord.SelectOption(emoji="<:tri_whiteheart:1434538078747365507>", label="ㆍㆍtrial", value="trial"),
    discord.SelectOption(emoji="<:tri_whiteheart:1434538078747365507>", label="ㆍㆍbreaks", value="breaks"),
    discord.SelectOption(emoji="<:tri_whiteheart:1434538078747365507>", label="ㆍㆍquota", value="quota"),
    discord.SelectOption(emoji="<:tri_whiteheart:1434538078747365507>", label="ㆍㆍtickets", value="tickets"),
    discord.SelectOption(emoji="<:tri_whiteheart:1434538078747365507>", label="ㆍㆍautoresponders", value="autoresponders"),
]

class StaffGuideView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.select(options=staff_guide_options, placeholder="‎　　Select a guide topic . . .　　　", custom_id="guide",
                       max_values=1)
    async def select_callback(self, interaction, select):
        if self.select_callback.values[0] == "trial":
            await interaction.response.send_message(embed=discord.Embed(description="""
### trial period
- **14–90 days**
- exceeding 90 days results in an **unappealable demotion** (you may reapply)
- **asking questions is encouraged** and will not affect your status
- **no breaks in the first 14 days** unless it’s an emergency
### promotion requirements
- **2 weeks of quota** (not necessarily consecutive)
- **10 non-hitter report tickets**
- **1 appeal ticket**
- **20 votes**
            """), ephemeral=True)
        if self.select_callback.values[0] == "breaks":
            await interaction.response.send_message(embed=discord.Embed(description="""
### break types
- **half break** — weekly quota is **halved (rounded down)**
- **full break** — weekly quota is **not counted**
### break rules
- staff **cannot earn annual leave** while on break.
- you may go on break as long as you have remaining break balance.
### annual leave
- includes **all types of leaves**.
- basic entitlement: **12 full breaks**
- **1/8 full break** for each **week of completed quota**.
            """), ephemeral=True)
        if self.select_callback.values[0] == "quota":
            await interaction.response.send_message(embed=discord.Embed(description="""
### quota basics
- `,q` to check your quota progress for the week.
- `,qh` to check your quota history for the past 8 weeks.
- fulfilling _either ticket or report quota_ will be considered quota completed (same goes for close or review quota for sr+).
- hitter reports count toward ticket quota but have **low promotion value**.
### strikes
- each week of **incomplete quota** while **not on a full break = 1 strike**
### consequences for incomplete quota
- **demotion in rank:**
  - 2 consecutive strikes with **no breaks taken**
  - 3 consecutive strikes with **≤ 1 full break** taken in total
  - 4 or more strikes (not necessarily consecutive) within the **past 8 weeks**
- **demotion from staff:**
  - average activity of **below 50%** over the **past 8 weeks**
  - full break weeks are **excluded** from calculation, but half break weeks are **included**
  - activity is measured by **quota fulfilled**, capped at **100% per week**
            """), ephemeral=True)
        if self.select_callback.values[0] == "tickets":
            await interaction.response.send_message(embed=discord.Embed(description="""
### ticket claiming
- the **first staff** to send a proper greeting (e.g. hi) handles the ticket
- if multiple greetings are sent, **reload discord** to see who was first
- other staff must **delete their messages**
### ticket handling
- only **one staff** may handle a ticket at a time
- a **defender** may assist if required
- only **one senior reporter** may review when requested
- after acceptance for voting, the **sr+ who publishes** the report is responsible for **closing the ticket**
### ticket priority
- handle **older tickets first**
- do not skip tickets because they seem difficult
### ticket limits
- **trial reporter** — 1 active, 2 on-hold, 1 self ticket
- **reporter** — 2 active, 2 on-hold, 1 self ticket
- if an on-hold ticket becomes active and exceeds your limit, you must **open one active ticket to other staff**
### reminders / on hold
- staff may place **their own tickets** on a reminder when necessary, using `,rm`
  - example: `,rm 3` creates a reminder for 3 hours. miku will ping you after the reminder expires.
- common reasons include
  - waiting for defendant response
  - waiting for contributor response
- do not set reminders longer than 12h as it will spam the ticket.
  - do not bypass this by setting consecutive reminders of 12h without a response from the contributor.
- if a ticket needs to be put **on hold** for an extended period (e.g. several days), rename your ticket to _hold request_, and ping sr+. if approved, sr+ will rename your ticket to _on hold_.
- abuse of reminders / on hold may result in **warnings or demotion**.
### ticket closure
- if the contributor does not reply within **12 hours**, you may request closure
- if no meaningful proof is provided within **4 hours**, you may request closure
            """), ephemeral=True)
        if self.select_callback.values[0] == "autoresponders":
            await interaction.response.send_message(embed=discord.Embed(description="""
`,sr`　–　pings sr+.
`,adm`　–　pings adm+.
`,tp`　–　pings ticket ping.
`,ban perms`　–　pings ban perms.
`,cl`　–　sends closing guide.
`,tags`　–　sends tags descriptions.
`.dm`　–　sends dm confrontation template.
`.yue`　–　pings <@1303291812282372137>.
`.ping`　–　sends a troll reply!
                """), ephemeral=True)

@send.command(name="staffrules", description="Sends staff rules.")
@app_commands.checks.has_role(adm_ping)
async def send_staffrules(interaction: discord.Interaction, colour: str=None, image: discord.Attachment=None):
    await interaction.response.defer(ephemeral=True)
    colour = discord.Colour(int(colour.strip("#"), 16)) if colour else 0xffffff
    if image:
        image_embed = discord.Embed(colour=colour)
        image_embed.set_image(url=image.url)
        await interaction.channel.send("_ _", embed=image_embed)
    await interaction.channel.send(embed=discord.Embed(colour=colour, description="""
## <:2paperclip:1449650494044639335>　　staff　　rules　　ꫂ᭪
**　⸝⸝⊹　follow server rulesㆍ**
– adhere to all [server rules](https://discord.com/channels/1371673839695826974/1371674470611161160)
– particular focus on **no discrimination**, **no hate or threats**, and **no nsfw content**

**　⊹⸝⸝　confidentialityㆍ**
– follow the non-disclosure agreement (nda)
– violation may result in removal from staff and/or a server ban depending on severity

**　⸝⸝⊹　ticket protocolㆍ**
– only one staff should handle a ticket at a time, unless a defender is required
– do not hijack tickets claimed by others
– avoid tickets where you are related to the defendant
– keep communication on-topic and case-related; refrain from side-chatting
– when handling multiple reports in a ticket, address one at a time in order

**　⊹⸝⸝　professionalismㆍ**
– reports on staff may result in quarantine and demotion if accepted
– speaking negatively about ticket participants or staff (current or former) is unprofessional and will be addressed

**　⸝⸝⊹　respectㆍ**
– remain respectful, even toward those you dislike
– personal feelings are not an excuse for rudeness or unprofessional behavior

**　⊹⸝⸝　no inappropriate jokesㆍ**
– jokes about ||suicide||, ||self-harm||, or ||body shaming|| (e.g., "||kys||", "||fat||", "||keep yourself safe||") are strictly prohibited
– even if said without ill-intention, these are not acceptable as they may make others uncomfortable

**　⸝⸝⊹　no dramaㆍ**
– keep personal conflicts out of the server
– resolve issues privately and respectfully, or seek proper mediation

**　⊹⸝⸝　no favouritismㆍ**
– do not excessively praise, defend, or favour specific individuals
– favoritism that undermines neutrality, decision-making, or report handling is prohibited
"""), view=StaffRulesView())
    await interaction.followup.send("Staff Rules have been sent.", ephemeral=True)

@send.command(name="staffguide", description="Sends staff guide.")
@app_commands.checks.has_role(adm_ping)
async def send_staffguide(interaction: discord.Interaction, colour: str=None, image: discord.Attachment=None):
    await interaction.response.defer(ephemeral=True)
    colour = discord.Colour(int(colour.strip("#"), 16)) if colour else 0xffffff
    if image:
        image_embed = discord.Embed(colour=colour)
        image_embed.set_image(url=image.url)
        await interaction.channel.send("_ _", embed=image_embed)
    await interaction.channel.send(embed=discord.Embed(colour=colour, description="""
## <:tri_whitebow:1388714593211125971>　　staff　　guide　　ꫂ᭪
　　`,help` for list of tri bots commands.
> -# – trial
> -# – breaks
> -# – quota
> -# – tickets
> -# – autoresponders
"""), view=StaffGuideView())
    await interaction.followup.send("Staff Guide has been sent.", ephemeral=True)

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
– read discord terms of service & guidelines fully to ensure you don’t break them.

**　⊹⸝⸝　be respectful﹐strictly no hateㆍ**
– be civil, any form of harassment, discrimination, bullying, etc will not be tolerated.

**　⸝⸝⊹　do not reveal or ask for personal infoㆍ**
– this includes other’s info and your own, please do not share too much for your own and others’ safety.

**　⊹⸝⸝　no plagiarismㆍ**
– inspiration is allowed but do not plagiarise any content, please give proper credits.

**　⊹⸝⸝　respect the staff﹐open a ticket for help ／ concernsㆍ**
– listen to staff and respect them, do not block them as they are here to help you. if you have concerns, need help or would like to report someone who broke the rules please open a ticket and do not deal with the problem yourself.

**　⸝⸝⊹　no ads ／ self - promo﹙includes dms﹚ㆍ**
– any form of self promotion is strictly __prohibited__.
    """)
    await interaction.channel.send("_ _", embed=embed1)
    embed2 = discord.Embed(colour=colour, title="_ _　　✦，　〝　language　etiquette　◝", description="""
**　⸝⸝⊹　nsfw is strictly prohibitedㆍ**
– includes both images and nsfw text, this is a public server and minors are present.

**　⊹⸝⸝　no excessive swearing﹐or slursㆍ**
– swearing is alright, as long as it isn’t unnecessarily excessive or targeted towards someone in a serious matter. slurs will strictly result in an immediate ban, even if it is reclaimable by you.

**　⸝⸝⊹ 　do not spam anything for any reasonㆍ**
– this includes text, images, pings, etc..
    """)
    await interaction.channel.send("_ _", embed=embed2)
    embed3 = discord.Embed(colour=colour, title="_ _　　✦，　〝　reporting　don’ts　◝", description="""
**　⸝⸝⊹　no false reportsㆍ**
– falsely reporting someone and producing fake evidence will result in a ban.

**　⸝⸝⊹　no briberyㆍ**
– any attempt to bribe someone or any attempt to take a bribe, is strictly prohibited.
    """)
    await interaction.channel.send("_ _", embed=embed3)
    embed4 = discord.Embed(colour=colour, description="""
**　ㆍ<:tri_whitebow:1388714593211125971>　full version of rules [here](https://docs.google.com/document/d/1ef3bb0l1EdXELcAbLDT7QOXFwbQco-600G-4HE6E7KM/edit?pli=1&tab=t.0#heading=h.1qtqm2f0dk9x)　♪**
    """)
    await interaction.channel.send("_ _", embed=embed4)
    await interaction.followup.send("Sent!")

@send.command(name="languageroles", description="Sends language roles embeds.")
@app_commands.checks.has_role(adm_ping)
async def send_languageroles(interaction: discord.Interaction, colour: str=None, image: discord.Attachment=None):
    await interaction.response.defer(ephemeral=True)
    colour = discord.Colour(int(colour.strip("#"), 16)) if colour else 0xffffff
    if image:
        image_embed = discord.Embed(colour=colour)
        image_embed.set_image(url=image.url)
        await interaction.channel.send("_ _", embed=image_embed)
    await interaction.channel.send("""
_ _
_ _　_if you’d like to be **pinged** to help **translate proofs**_

_ _　　<:cutie:1388714793585606656>ㆍ**claim  language roles  here** ㆍㆍ
-# <:greyreply:1448474301673115748>　select  for  the  role ,  select  again  to  remove .
_ _
    """, view=LanguageRolesView())
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
　❜ <:tri_whiteheart:1434538078747365507> ㆍ18 +　︵
　 <:tri_whitebow:1388714593211125971> ㆍ16 — 17　❜
　❜ <:tri_whitestar:1388147381152911381> ㆍ13 — 15　︵
""")
    msg1 = await interaction.channel.send("_ _", embed=embed1)
    embed2 = discord.Embed(colour=colour, title="★．．　pronouns　⊹⁺₊", description="""  
-# _ _
　┅ <:tri_whitebutterfly:1459750881611354237> ㆍhe 　❀
　 <:tri_whitepaperclip:1449650494044639335> ㆍ she 　┅
　┅ <:tri_whitestar:1388147381152911381> ㆍthey 　❀
　 <:tri_whitebowheart:1459750975710691410> ㆍ ask 　┅
    """)
    msg2 = await interaction.channel.send("_ _", embed=embed2)
    embed3 = discord.Embed(colour=colour, title="★．．　user　update　pings　⊹⁺₊", description="""  
-# _ _
　∿ <:tri_whitestar:1388147381152911381> ㆍnew user report　⿻
　 <:tri_whitebow:1388714593211125971> ㆍupdated user report　∿
　∿ <:tri_whitepaperclip:1449650494044639335> ㆍappealed user report　⿻
""")
    msg3 = await interaction.channel.send("_ _", embed=embed3)
    embed4 = discord.Embed(colour=colour, title="★．．　server　update　pings　⊹⁺₊", description="""  
-# _ _
　 <:tri_whiteheart:1434538078747365507> ㆍnew server report　∿
　∿ <:tri_whitebutterfly:1459750881611354237> ㆍupdated server report　⿻
　 <:tri_whitebowheart:1459750975710691410> ㆍappealed server report　∿
""")
    msg4 = await interaction.channel.send("_ _", embed=embed4)
    embed5 = discord.Embed(colour=colour, title="★．．　account　update　pings　⊹⁺₊", description="""  
-# _ _
　 <:tri_whitebutterfly:1459750881611354237> ㆍnew account report　⿻
　∿ <:tri_whitepaperclip:1449650494044639335> ㆍupdated account report　∿
　 <:tri_whitestar:1388147381152911381> ㆍappealed account report　⿻
""")
    msg5 = await interaction.channel.send("_ _", embed=embed5)
    embed6 = discord.Embed(colour=colour, description="""  
-# _ _
　⬩ <:tri_whitebutterfly:1459750881611354237> ㆍnews　✿
　 <:tri_whitebow:1388714593211125971> ㆍticket status　⬩
    """)
    msg6 = await interaction.channel.send("_ _", embed=embed6)
    await interaction.followup.send("Sent!")
    await interaction.followup.send(f"""
Use the following commands to add react roles:

`!rr addmany {interaction.channel.id} {msg1.id}
<:tri_whiteheart:1434538078747365507> 1375276990096998440 
<:tri_whitebow:1388714593211125971> 1375277014679818332 
<:tri_whitestar:1388147381152911381> 1375277046204203148`

`!rr addmany {interaction.channel.id} {msg2.id}
<:tri_whitebutterfly:1459750881611354237> 1375274759507411034
<:tri_whitepaperclip:1449650494044639335> 1375274745616011355
<:tri_whitestar:1388147381152911381> 1375274890894250045
<:tri_whitebowheart:1459750975710691410> 1375274908275445780`

`!rr addmany {interaction.channel.id} {msg3.id}
<:tri_whitestar:1388147381152911381> 1375275062185168957
<:tri_whitebow:1388714593211125971> 1459590866724323625
<:tri_whitepaperclip:1449650494044639335> 1459590865335877663`

`!rr addmany {interaction.channel.id} {msg4.id}
<:tri_whiteheart:1434538078747365507> 1375275002537971742
<:tri_whitebutterfly:1459750881611354237> 1459590362703204405 
<:tri_whitebowheart:1459750975710691410> 1459590364292972776`

`!rr addmany {interaction.channel.id} {msg5.id}
<:tri_whitebutterfly:1459750881611354237> 1515589534438395914
<:tri_whitepaperclip:1449650494044639335> 1515589535059284148
<:tri_whitestar:1388147381152911381> 1515589539069169844`

`!rr addmany {interaction.channel.id} {msg6.id}
<:tri_whitebutterfly:1459750881611354237> 1375276744956706916
<:tri_whitebow:1388714593211125971> 1459594319110602833`

""", ephemeral=True)





faq_overview_options = [
    discord.SelectOption(label="what is tri?", value="what is tri?"),
    discord.SelectOption(label="terms of service", value="terms of service"),
    discord.SelectOption(label="privacy policy", value="privacy policy"),
    discord.SelectOption(label="ban policy", value="ban policy"),
    discord.SelectOption(label="how can I contact admin+?", value="how can I contact admin+?"),
    discord.SelectOption(label="how can I request a collaboration?", value="how can I request a collaboration?"),
]

class FAQOverviewView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.select(options=faq_overview_options, placeholder="‎　　Select a question . . .　　　", custom_id="faqoverview",
                       max_values=1)
    async def select_callback(self, interaction, select):
        if self.select_callback.values[0] == "what is tri?":
            await interaction.response.send_message(embed=discord.Embed(description="""
### <a:tri_whitearrow2:1388147186654515273>　　what is tri?
trade report investigation archive (**tri archive**) est. may 2025 is a server dedicated to **spreading awareness on dangerous, unlawful, or suspicious activity** and promoting community safety.
            """), ephemeral=True)
        if self.select_callback.values[0] == "terms of service":
            await interaction.response.send_message(embed=discord.Embed(description=f"""
### <a:tri_whitearrow2:1388147186654515273>　　terms of service
this server allows users to report scams, attempted scams and other unlawful activities, report suspicious behavior to spread awareness, and view or share reports to stay informed.
by using the services of tri archive (“we”, “our” or “us”), you agree to the following terms:
- user responsibilities
  - you must provide accurate and truthful information when submitting scam reports. false or malicious reports are strictly prohibited and will result in a ban.
- content use and moderation
  - all reports will be posted to the public without exceptions. by opening a ticket to report, you grant this server the right to display and share the content or evidence attached to the report(s), with the exception of private information which will be blocked out accordingly.
  - you are responsible for checking through the proofs to be posted to ensure that all private information has been blocked out from the report(s). this server is not liable for any private information posted publicly on accident, although we will remove them immediately once it is brought to our attention. please view our privacy policy for more details.
- privacy
  - this server will collect minimal data on private information, only those that are crucial to the report. this private information will not be viewable to or shared with anyone beyond the staff team without your consent. 
- access to our service
  - we may ban any users that abuse the service, violate the terms, or submit harmful content. we value the safety and wellbeing of our staff.
- modifications to the terms
  - all info is accessible at [this document](https://docs.google.com/document/d/1ef3bb0l1EdXELcAbLDT7QOXFwbQco-600G-4HE6E7KM/) which may be updated from time to time. major changes will be announced but minor changes will not. continued use of our service means you accept the new terms.
- contact
  - questions or concerns? [open a ticket](https://discord.com/channels/{TRI_Archive}/{TICKET_CHANNEL}).
            """), ephemeral=True)
        if self.select_callback.values[0] == "privacy policy":
            await interaction.response.send_message(embed=discord.Embed(description="""
### <a:tri_whitearrow2:1388147186654515273>　　privacy policy
this server (“we”, “our”, or “us”) is committed to protecting your privacy. this policy explains how we collect, use, and protect your information.
- information we collect
  - when you submit a report, we collect the content you provide (e.g. scam description, conversation history with scammer).
  - if an account is involved, we may collect your email address, username or password, but it will be blocked out on the report that is posted publicly.
- how we use your information
  - to publish and share scam reports publicly.
  - to contact you about your report/appeal, if needed.
- data sharing
  - we do **not** sell your data to or share your data with anyone beyond the staff team.
  - if there is any staff whom you do not wish to give access to your data, please state so clearly and we will remove their access to the ticket.
- your rights
  - you may request for us to remove or block out evidence which contains your private information, either during or after the report.
  - however, please note that requesting removal of non-private evidence after a report is confirmed in an attempt to make the report invalid is prohibited. if you are the victim, you may instead make an appeal on behalf of the defendant.
  - please consider these privacy concerns carefully before making a report, and check through all evidence attached to the report carefully, as any subsequent updates may take some time to confirm.
            """), ephemeral=True)
        if self.select_callback.values[0] == "ban policy":
            await interaction.response.send_message(embed=discord.Embed(description=f"""
### <a:tri_whitearrow2:1388147186654515273>　　ban policy
please read through [server rules](https://discord.com/channels/{TRI_Archive}/1371674470611161160) carefully. not following rules may result in warns or bans.
_we do not ban scammers so that they may make an appeal._

**what does tri ban?**
- not following discord [tos](https://discord.com/terms) or [guidelines](https://discord.com/guidelines).
- racist, sexist, homophobic, xenophobic, or similar slurs and sentiments
- targeted hate, threats of violence, doxxing, or sharing private info.
- false or malicious reports. this includes editing proofs.
- advertising products, services, events, or servers.
- attempting to bribe or gain favours from staff, even outside the server.
- nsfw material, even if mentioned as a joke.
            """), ephemeral=True)
        if self.select_callback.values[0] == "how can I contact admin+?":
            await interaction.response.send_message(embed=discord.Embed(description="""
### <a:tri_whitearrow2:1388147186654515273>　　how can I contact admin+?

                """), ephemeral=True)
        if self.select_callback.values[0] == "how can I request a collaboration?":
            await interaction.response.send_message(embed=discord.Embed(description="""
### <a:tri_whitearrow2:1388147186654515273>　　how can I request a collaboration?

                """), ephemeral=True)


faq_reports_options = [
    discord.SelectOption(label="how do I check for reports?", value="how do I check for reports?"),
    discord.SelectOption(label="what can be reported?", value="what can be reported?"),
    discord.SelectOption(label="what proofs are required for reports?", value="what proofs are required for reports?"),
    discord.SelectOption(label="can I remain anonymous?", value="can I remain anonymous?"),
    discord.SelectOption(label="can I report someone who has already been reported?", value="can I report someone who has already been reported?"),
    discord.SelectOption(label="can I update or withdraw my report?", value="can I update or withdraw my report?"),
    discord.SelectOption(label="how long does it take for reports to be published?", value="how long does it take for reports to be published?"),
    discord.SelectOption(label="how do I stay updated with new reports?", value="how do I stay updated with new reports?"),
    discord.SelectOption(label="what if someone files a false report?", value="what if someone files a false report?"),
]


class FAQReportsView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.select(options=faq_reports_options, placeholder="‎　　Select a question . . .　　　", custom_id="faqreports",
                       max_values=1)
    async def select_callback(self, interaction, select):
        if self.select_callback.values[0] == "how do I check for reports?":
            await interaction.response.send_message(embed=discord.Embed(description=f"""
### <a:tri_whitearrow2:1388147186654515273>　　how do I check for reports?
you can check if a user, server or game account is reported using tri’s bot <@1457249982104211467>.
to check for reports, you need some form of **id**. guides [here](https://discord.com/channels/{TRI_Archive}/1523977533115207820).
-# 　⤷　how to obtain user/server id? guide [here](https://support.discord.com/hc/en-us/articles/206346498-Where-can-I-find-my-User-Server-Message-ID).
- `,c` to check
  - `,c 𝐮𝐬𝐞𝐫 𝐢𝐝`
  - `,c 𝐢𝐧𝐯𝐢𝐭𝐞`
  - `,c 𝐠𝐚𝐦𝐞 𝐮𝐢𝐝`
- you can also check a link against a database of known malicious links using `/check link`.

**examples**
- `,c 1450073025818136598`
- `,c` <@1450073025818136598>
- `,c tri`
- `,c https://discord.gg/tri`
- `,c genshin 676767676`
- `,c Honkai: Star Rail 767676767`
- `,c roblox 6767676767`
- `,c idv eu/na10101010`
            """), ephemeral=True)
        if self.select_callback.values[0] == "what can be reported?":
            await interaction.response.send_message(embed=discord.Embed(description="""
### <a:tri_whitearrow2:1388147186654515273>　　what can be reported?
you may report users or servers for a variety of reasons, including but not limited to
- scamming or attempted scams.
- suspicious or high risk behaviour.
- unprofessional conduct by staff, middlemen, pilots, or other service providers.
- misconduct during report or appeal proceedings (e.g. harassment, threats, bribery, blackmail, or excessive hostility).
- other behaviour that may pose a risk to the community.
we also report game accounts to provide greater transparency regarding account histories to help traders make more informed decisions.

if you are unsure whether a situation is reportable, feel free to open a ticket. our staff will review the information and advise you accordingly.
            """), ephemeral=True)
        if self.select_callback.values[0] == "what proofs are required for reports?":
            await interaction.response.send_message(embed=discord.Embed(description="""
### <a:tri_whitearrow2:1388147186654515273>　　what proofs are required for reports?
provide relevant user ids, server invites & ids, or game uids. 
-# _not just usernames, since usernames can change._
-# 　⤷　how to obtain user/server id? guide [here](https://support.discord.com/hc/en-us/articles/206346498-Where-can-I-find-my-User-Server-Message-ID).

**screenshots are strongly preferred**, followed by screen recordings or html files.

please show **entire conversation, _from start to end_**
-# _do not crop, omit, delete, or edit any messages related to the report until the investigation is complete._

- for **breach of agreement** reports, show the following
  - trade agreement
  - proof you fulfilled your side
  - proof of payment
  - confrontation & outcome (excuses, blocking, ghosting)

- additional requirements
  - **timestamps** should be visible
  - if you've blocked the other user, **temporarily unblock them** before taking screenshots so the conversation displays correctly.
  - for crypto payments, send **blockchain txids**.

**__uncropped__ & unedited**
show your **entire screen**. sensitive personal information such as real names, passwords, ip addresses, or other private information may be blurred.

**video too large**
upload your video at [catbox.moe](https://catbox.moe) and copy & paste the link here.
            """), ephemeral=True)
        if self.select_callback.values[0] == "can I remain anonymous?":
            await interaction.response.send_message(embed=discord.Embed(description="""
### <a:tri_whitearrow2:1388147186654515273>　　can I remain anonymous?
yes, you may choose to remain anonymous when reporting by requesting it when opening a ticket. the staff assisting you will ensure your identity is not disclosed in the proofs attached to the report.
- however, if dm screenshots are included, the other party may still recognise the conversation and infer who provided the proofs.
- please also check through all evidence attached to the report carefully, as any subsequent updates may take some time to confirm. 
            """), ephemeral=True)
        if self.select_callback.values[0] == "can I report someone who has already been reported?":
            await interaction.response.send_message(embed=discord.Embed(description="""
### <a:tri_whitearrow2:1388147186654515273>　　can I report someone who has already been reported?
yes, the same user may be reported multiple times to keep track of their latest activity, especially if
- they are being reported for a separate incident under a different report tag/reason.
- the new incident occurred 6 or more months after their latest report.
            """), ephemeral=True)
        if self.select_callback.values[0] == "can I update or withdraw my report?":
            await interaction.response.send_message(embed=discord.Embed(description="""
### <a:tri_whitearrow2:1388147186654515273>　　can I update or withdraw my report?
yes, you may request to update or withdraw your report before it is confirmed, subject to staff review.
after a report has been confirmed, you may still request for evidence containing your private information to be removed or censored.
- however, requesting the removal of non-private evidence after a report has been confirmed in an attempt to invalidate or weaken the report is prohibited.
  - if you are the victim and no longer wish for the report to remain, you may instead submit an appeal on behalf of the defendant, which will be reviewed based on the available evidence.
            """), ephemeral=True)
        if self.select_callback.values[0] == "how long does it take for reports to be published?":
            await interaction.response.send_message(embed=discord.Embed(description="""
### <a:tri_whitearrow2:1388147186654515273>　　how long does it take for reports to be published?
there is no fixed timeframe for how long a report takes to be reviewed and published.
- the time required depends on factors such as the complexity of the case, the amount of evidence submitted, whether additional information is needed, and our current report volume.
you will be kept informed of your report's progress by the staff handling your ticket. we appreciate your patience while we ensure each report is reviewed thoroughly and fairly.
            """), ephemeral=True)
        if self.select_callback.values[0] == "how do I stay updated with new reports?":
            await interaction.response.send_message(embed=discord.Embed(description="""
### <a:tri_whitearrow2:1388147186654515273>　　how do I stay updated with new reports?
follow tri’s report announcement channels <#1375132097605406721>, <#1375184563675856916> and <#1515531623045533716> to receive updates in your own server.
-# 　⤷　how to follow a channel? guide [here](https://support.discord.com/hc/en-us/articles/360028384531-Channel-Following-FAQ).

add tri’s bot <@1457249982104211467> to your server by clicking **add app** on the bot’s profile, or click [here](https://discord.com/oauth2/authorize?client_id=1457249982104211467).
- `,c` to check users, servers or accounts using <@1457249982104211467>.
- `/check all` to check your server for users with bannable reports.
            """), ephemeral=True)
        if self.select_callback.values[0] == "what if someone files a false report?":
            await interaction.response.send_message(embed=discord.Embed(description="""
### <a:tri_whitearrow2:1388147186654515273>　　what if someone files a false report?
wip
            """), ephemeral=True)

faq_appeals_options = [
    discord.SelectOption(label="how to make an appeal?", value="how to make an appeal?"),
    discord.SelectOption(label="what can be appealed?", value="what can be appealed?"),
    discord.SelectOption(label="what proofs are required for appeals?", value="what proofs are required for appeals?"),
    discord.SelectOption(label="can someone else appeal on my behalf?", value="can someone else appeal on my behalf?"),
]

class FAQAppealsView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.select(options=faq_appeals_options, placeholder="‎　　Select a question . . .　　　", custom_id="faqappeals",
                       max_values=1)
    async def select_callback(self, interaction, select):
        if self.select_callback.values[0] == "how to make an appeal?":
            await interaction.response.send_message(embed=discord.Embed(description=f"""
### <a:tri_whitearrow2:1388147186654515273>　　how to make an appeal?
- <#1375261699111784478> to make an appeal if you believe your report is inaccurate or unfair, or if you have served the minimum report period (mrp) as stated on your report or in [legal codex](https://docs.google.com/document/d/1ef3bb0l1EdXELcAbLDT7QOXFwbQco-600G-4HE6E7KM/).
  - note that appeals based on mrp are not guaranteed and will be reviewed on a case by case basis.
- please provide all relevant information that may prove your report to be inaccurate or unfair.
- you may request for a staff to be your defender i.e. argue in favour of your appeal. however, defenders will remain unbiased, and appeals will still be judged based on the facts and evidence presented.
            """), ephemeral=True)
        if self.select_callback.values[0] == "what can be appealed?":
            await interaction.response.send_message(embed=discord.Embed(description=f"""
### <a:tri_whitearrow2:1388147186654515273>　　what can be appealed?
wip
            """), ephemeral=True)
        if self.select_callback.values[0] == "what proofs are required for appeals?":
            await interaction.response.send_message(embed=discord.Embed(description=f"""
### <a:tri_whitearrow2:1388147186654515273>　　what proofs are required for appeals?
**screenshots are strongly preferred**, followed by screen recordings or html files.

please provide clear proofs supporting your appeal.
-# _do not crop, omit, delete, or edit any messages related to the appeal until the investigation is complete._

- depending on your appeal, show the following
  - the full context surrounding the incident.
  - any proofs that contradicts or explains the report against you.
  - if you believe the report contains **false** or **misleading** information, clearly identify which parts and provide supporting evidence.

- additional requirements
  - **timestamps** should be visible
  - if you've blocked the other user, **temporarily unblock them** before taking screenshots so the conversation displays correctly.
  - for crypto payments, send **blockchain txids**.

- appeals based on minimum report period (mrp)
  - appeals based solely on meeting the mrp are **not guaranteed** and are reviewed on a case by case basis.
  - you must provide proofs showing that you have genuinely changed since the incident. simply claiming to be sorry or promising not to repeat the offense is generally insufficient.

**__uncropped__ & unedited**
show your **entire screen**. sensitive personal information such as real names, passwords, ip addresses, or other private information may be blurred.

**video too large**
upload your video at [catbox.moe](https://catbox.moe) and copy & paste the link here.
            """), ephemeral=True)
        if self.select_callback.values[0] == "can someone else appeal on my behalf?":
            await interaction.response.send_message(embed=discord.Embed(description=f"""
### <a:tri_whitearrow2:1388147186654515273>　　
wip
            """), ephemeral=True)

faq_definitionsstandards_options = [
    discord.SelectOption(label="what is scamming?", value="what is scamming?"),
    discord.SelectOption(label="what is a suspect?", value="what is a suspect?"),
    discord.SelectOption(label="what is impersonation?", value="what is impersonation?"),
    discord.SelectOption(label="what do the report tags mean?", value="what do the report tags mean?"),
    discord.SelectOption(label="what is beaming?", value="what is beaming?"),
    discord.SelectOption(label="what is hitting?", value="what is hitting?"),
    discord.SelectOption(label="what is proof beyond reasonable doubt?", value="what is proof beyond reasonable doubt?"),
    discord.SelectOption(label="what does “insufficient proofs” mean?", value="what does “insufficient proofs” mean?"),
    discord.SelectOption(label="what does “invalid reason” mean?", value="what does “invalid reason” mean?"),
]

class FAQDefinitionsStandardsView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.select(options=faq_definitionsstandards_options, placeholder="‎　　Select a question . . .　　　", custom_id="faqdefinitionsstandards",
                       max_values=1)
    async def select_callback(self, interaction, select):
        if self.select_callback.values[0] == "what is scamming?":
            await interaction.response.send_message(embed=discord.Embed(description=f"""
### <a:tri_whitearrow2:1388147186654515273>　　what is scamming?
wip
            """), ephemeral=True)
        if self.select_callback.values[0] == "what is a suspect?":
            await interaction.response.send_message(embed=discord.Embed(description=f"""
### <a:tri_whitearrow2:1388147186654515273>　　what is a suspect?
wip
            """), ephemeral=True)
        if self.select_callback.values[0] == "what is impersonation?":
            await interaction.response.send_message(embed=discord.Embed(description=f"""
### <a:tri_whitearrow2:1388147186654515273>　　what is impersonation?
wip
            """), ephemeral=True)
        if self.select_callback.values[0] == "what do the report tags mean?":
            await interaction.response.send_message(embed=discord.Embed(description=f"""
### <a:tri_whitearrow2:1388147186654515273>　　what do the report tags mean?
wip
            """), ephemeral=True)
        if self.select_callback.values[0] == "what is beaming?":
            await interaction.response.send_message(embed=discord.Embed(description=f"""
### <a:tri_whitearrow2:1388147186654515273>　　what is beaming?
wip
            """), ephemeral=True)
        if self.select_callback.values[0] == "what is hitting?":
            await interaction.response.send_message(embed=discord.Embed(description=f"""
### <a:tri_whitearrow2:1388147186654515273>　　what is hitting?
wip
            """), ephemeral=True)
        if self.select_callback.values[0] == "what is proof beyond reasonable doubt?":
            await interaction.response.send_message(embed=discord.Embed(description=f"""
### <a:tri_whitearrow2:1388147186654515273>　　what is proof beyond reasonable doubt?
wip
            """), ephemeral=True)
        if self.select_callback.values[0] == "what does “insufficient proofs” mean?":
            await interaction.response.send_message(embed=discord.Embed(description=f"""
### <a:tri_whitearrow2:1388147186654515273>　　what does “insufficient proofs” mean?
wip
            """), ephemeral=True)
        if self.select_callback.values[0] == "what does “invalid reason” mean?":
            await interaction.response.send_message(embed=discord.Embed(description=f"""
### <a:tri_whitearrow2:1388147186654515273>　　what does “invalid reason” mean?
wip
            """), ephemeral=True)

faq_scamprevention_options = [
    discord.SelectOption(label="how can I avoid being scammed?", value="how can I avoid being scammed?"),
    discord.SelectOption(label="how do I identify impersonators?", value="how do I identify impersonators?"),
    discord.SelectOption(label="how do I identify malicious links?", value="how do I identify malicious links?"),
    discord.SelectOption(label="can I report someone for refusing to use a middleman?", value="can I report someone for refusing to use a middleman?"),
    discord.SelectOption(label="what should I do immediately after being scammed?", value="what should I do immediately after being scammed?"),
    discord.SelectOption(label="can tri recover my lost items or money?", value="can tri recover my lost items or money?"),
    discord.SelectOption(label="what should I do if my account has been compromised?", value="what should I do if my account has been compromised?"),
]

class FAQScamPreventionView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.select(options=faq_scamprevention_options, placeholder="‎　　Select a question . . .　　　", custom_id="faqscamprevention",
                       max_values=1)
    async def select_callback(self, interaction, select):
        if self.select_callback.values[0] == "how can I avoid being scammed?":
            await interaction.response.send_message(embed=discord.Embed(description=f"""
### <a:tri_whitearrow2:1388147186654515273>　　how can I avoid being scammed?
wip
            """), ephemeral=True)
        if self.select_callback.values[0] == "how do I identify impersonators?":
            await interaction.response.send_message(embed=discord.Embed(description=f"""
### <a:tri_whitearrow2:1388147186654515273>　　how do I identify impersonators?
wip
            """), ephemeral=True)
        if self.select_callback.values[0] == "how do I identify malicious links?":
            await interaction.response.send_message(embed=discord.Embed(description=f"""
### <a:tri_whitearrow2:1388147186654515273>　　how do I identify malicious links?
wip
            """), ephemeral=True)
        if self.select_callback.values[0] == "can I report someone for refusing to use a middleman?":
            await interaction.response.send_message(embed=discord.Embed(description=f"""
### <a:tri_whitearrow2:1388147186654515273>　　can I report someone for refusing to use a middleman?
wip
            """), ephemeral=True)
        if self.select_callback.values[0] == "what should I do immediately after being scammed?":
            await interaction.response.send_message(embed=discord.Embed(description=f"""
### <a:tri_whitearrow2:1388147186654515273>　　what should I do immediately after being scammed?
wip
            """), ephemeral=True)
        if self.select_callback.values[0] == "can tri recover my lost items or money?":
            await interaction.response.send_message(embed=discord.Embed(description=f"""
### <a:tri_whitearrow2:1388147186654515273>　　can tri recover my lost items or money?
wip
            """), ephemeral=True)
        if self.select_callback.values[0] == "what should I do if my account has been compromised?":
            await interaction.response.send_message(embed=discord.Embed(description=f"""
### <a:tri_whitearrow2:1388147186654515273>　　what should I do if my account has been compromised?
wip
            """), ephemeral=True)

faq_stafftransparency_options = [
    discord.SelectOption(label="who can access tickets & ongoing reports?", value="who can access tickets & ongoing reports?"),
    discord.SelectOption(label="how does tri ensure reports & appeals are not biased?", value="how does tri ensure reports & appeals are not biased?"),
    discord.SelectOption(label="how can I apply to be staff?", value="how can I apply to be staff?"),
    discord.SelectOption(label="how can I report a tri staff?", value="how can I report a tri staff?"),
]

class FAQStaffTransparencyView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.select(options=faq_stafftransparency_options, placeholder="‎　　Select a question . . .　　　", custom_id="faqstafftransparency",
                       max_values=1)
    async def select_callback(self, interaction, select):
        if self.select_callback.values[0] == "who can access tickets & ongoing reports?":
            await interaction.response.send_message(embed=discord.Embed(description=f"""
### <a:tri_whitearrow2:1388147186654515273>　　who can access tickets & ongoing reports?
wip
            """), ephemeral=True)
        if self.select_callback.values[0] == "how does tri ensure reports & appeals are not biased?":
            await interaction.response.send_message(embed=discord.Embed(description=f"""
### <a:tri_whitearrow2:1388147186654515273>　　how does tri ensure reports & appeals are not biased?
wip
            """), ephemeral=True)
        if self.select_callback.values[0] == "how can I apply to be staff?":
            await interaction.response.send_message(embed=discord.Embed(description=f"""
### <a:tri_whitearrow2:1388147186654515273>　　how can I apply to be staff?
wip
            """), ephemeral=True)
        if self.select_callback.values[0] == "how can I report a tri staff?":
            await interaction.response.send_message(embed=discord.Embed(description=f"""
### <a:tri_whitearrow2:1388147186654515273>　　how can I report a tri staff?
wip
            """), ephemeral=True)

@send.command(name="faq", description="Sends faq.")
@app_commands.checks.has_role(adm_ping)
async def send_faq(interaction: discord.Interaction, colour: str=None, image: discord.Attachment=None):
    await interaction.response.defer(ephemeral=True)
    colour = discord.Colour(int(colour.strip("#"), 16)) if colour else 0xffffff
    if image:
        image_embed = discord.Embed(colour=colour)
        image_embed.set_image(url=image.url)
        await interaction.channel.send("_ _", embed=image_embed)
    embed1 = discord.Embed(colour=colour, description="""
### _ _　　overview
-# – what is tri?
-# – terms of service
-# – privacy policy
-# – ban policy
-# – how can I contact admin+?
-# – how can I request a collaboration?
""")
    msg1 = await interaction.channel.send("_ _", embed=embed1, view=FAQOverviewView())
    embed2 = discord.Embed(colour=colour, description="""
### _ _　　reports
-# – how do I check for reports?
-# – what can be reported?
-# – what proofs are required for reports?
-# – can I remain anonymous?
-# – can I report someone who has already been reported?
-# – can I update or withdraw my report?
-# – how long does it take for reports to be published?
-# – how do I stay updated with new reports?
-# – what if someone files a false report?
""")
    msg2 = await interaction.channel.send("_ _", embed=embed2, view=FAQReportsView())
    embed3 = discord.Embed(colour=colour, description="""
### _ _　　appeals
-# – how to make an appeal?
-# – what can be appealed?
-# – what proofs are required for appeals?
-# – can someone else appeal on my behalf?
""")
    msg3 = await interaction.channel.send("_ _", embed=embed3, view=FAQAppealsView())
    embed4 = discord.Embed(colour=colour, description="""
### _ _　　definitions & standards
-# – what is scamming?
-# – what is a suspect?
-# – what is impersonation?
-# – what do the report tags mean?
-# – what is beaming?
-# – what is hitting?
-# – what is proof beyond reasonable doubt?
-# – what does “insufficient proofs” mean?
-# – what does “invalid reason” mean?
""")
    msg4 = await interaction.channel.send("_ _", embed=embed4, view=FAQDefinitionsStandardsView())
    embed5 = discord.Embed(colour=colour, description="""
### _ _　　scam prevention
-# – how can I avoid being scammed?
-# – how do I identify impersonators?
-# – how do I identify malicious links?
-# – can I report someone for refusing to use a middleman?
-# – what should I do immediately after being scammed?
-# – can tri recover my lost items or money?
-# – what should I do if my account has been compromised?
""")
    msg5 = await interaction.channel.send("_ _", embed=embed5, view=FAQScamPreventionView())
    embed6 = discord.Embed(colour=colour, description="""
### _ _　　staff & transparency
-# – who can access tickets & ongoing reports?
-# – how does tri ensure reports & appeals are not biased?
-# – how can I apply to be staff?
-# – how can I report a tri staff?
""")
    msg6 = await interaction.channel.send("_ _", embed=embed6, view=FAQStaffTransparencyView())
    embed = discord.Embed(colour=colour, description=f"""
<:tri_whiteheart:1434538078747365507>　　[overview]({msg1.jump_url})
-# <:blank:1383116055550890095>
<:tri_whiteheart:1434538078747365507>　　[reports]({msg2.jump_url})
-# <:blank:1383116055550890095>
<:tri_whiteheart:1434538078747365507>　　[appeals]({msg3.jump_url})
-# <:blank:1383116055550890095>
<:tri_whiteheart:1434538078747365507>　　[definitions & standards]({msg4.jump_url})
-# <:blank:1383116055550890095>
<:tri_whiteheart:1434538078747365507>　　[scam prevention]({msg5.jump_url})
-# <:blank:1383116055550890095>
<:tri_whiteheart:1434538078747365507>　　[staff & transparency]({msg6.jump_url})
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

@app_commands.allowed_contexts(guilds=True, dms=False, private_channels=True)
@app_commands.guild_install()
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
            await interaction.followup.send("I can only edit messages sent by MIKU.", ephemeral=True)
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
                auto_archive_duration=10080,
                invitable=False,
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
        embed.add_field(name="User", value=f"{user.mention} ({user.name})", inline=True)
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

@bot.command(name="t")
@commands.has_any_role(staff_role)
async def t(ctx, text: str = None, ticket_type: str = None):
    ticket_channel = ctx.guild.get_channel(TICKET_CHANNEL)
    if not ticket_channel:
        return await ctx.reply("Ticket channel not found.")
    msg = await ctx.reply("_Searching for tickets..._")
    def get_default_text():
        nickname = ctx.author.nick or ctx.author.display_name
        if "ㆍ" in nickname:
            _, t = nickname.split("ㆍ", 1)
            return t
        return nickname

    if not text:
        text = get_default_text()
    show_all = text.lower() == "all"
    if show_all:
        text = get_default_text()
    text_lower = text.lower()
    if text_lower == "all":
        text = get_default_text()
        text_lower = text.lower()
        ticket_type = "all"
    ticket_type_lower = ticket_type.lower() if ticket_type else None
    matching_threads = []

    async def format_thread_line(thread_obj):
        try:
            ticket_data = tickets.find_one({"thread_id": int(thread_obj.id)})
            if ticket_data and "creator_id" in ticket_data:
                creator_id = ticket_data["creator_id"]
                owner_text = f"<@{creator_id}>"
            else:
                owner_text = "Unknown"
        except Exception as e:
            owner_text = "Unknown"
            print(e)
        return f"> {thread_obj.mention} – {owner_text}"

    try:
        if ticket_type_lower in [None, "all"]:
            for thread in ticket_channel.threads:
                if show_all or text_lower in thread.name.lower():
                    matching_threads.append(await format_thread_line(thread))
        if ticket_type_lower in ["all", "closed"]:
            async for thread in ticket_channel.archived_threads(limit=None, private=False):
                if show_all or text_lower in thread.name.lower():
                    matching_threads.append(f"> {thread.mention}")
            async for thread in ticket_channel.archived_threads(limit=None, private=True):
                if show_all or text_lower in thread.name.lower():
                    matching_threads.append(f"> {thread.mention}")
    except Exception as e:
        return await msg.edit(content=f"An error occurred while fetching threads: {e}")
    if not matching_threads:
        return await msg.edit(content=f"No tickets found containing `{text}`.")
    field_groups = [matching_threads[i:i + 10] for i in range(0, len(matching_threads), 10)]
    embed_pages = [field_groups[i:i + 2] for i in range(0, len(field_groups), 2)]
    embeds = []
    total_pages = len(embed_pages)
    for page_idx, page_fields in enumerate(embed_pages):
        title = "all active tickets" if show_all else f"ticket search results for `{text}`"
        embed = discord.Embed(
            title=title,
            color=0xffffff
        )
        for field_threads in page_fields:
            field_value = "\n".join(field_threads)
            embed.add_field(
                name="\u200b",
                value=field_value,
                inline=True
            )
        embed.set_footer(text=f"Page {page_idx + 1} of {total_pages}　–　{len(matching_threads)} ticket(s) found")
        embeds.append(embed)
    await msg.edit(content="", embed=embeds[0])
    if len(embeds) > 1:
        for embed in embeds[1:]:
            await ctx.send(embed=embed)

@bot.command(name="notify")
@commands.has_any_role(staff_role)
async def notify(ctx, user: discord.User):
    try:
        await user.send(
            f"hello! this is a reminder to please check and reply to your ticket when you’re available.\n"
            f"{ctx.channel.jump_url}"
        )
        await ctx.message.add_reaction("<:tri_whitetick:1462774288020013161>")
    except discord.Forbidden:
        await ctx.message.add_reaction("<:tri_whitecross:1462774085737119828>")

@bot.command()
@commands.has_any_role(adm_ping)
async def syncroles(ctx: commands.Context):
    msg = await ctx.send("Syncing tree commands and member tag roles...")
    guild = bot.get_guild(TRI_Archive)
    if not guild:
        try:
            guild = await bot.fetch_guild(TRI_Archive)
        except (discord.NotFound, discord.HTTPException):
            return
    members = guild.members
    if not members:
        try:
            members = [m async for m in guild.fetch_members(limit=None)]
        except (discord.Forbidden, discord.HTTPException):
            return await msg.edit(content="Failed to fetch guild members. Check bot permissions/intents.")

    total_members = len(members)
    synced_count = 0
    roles_changed = 0

    for index, member in enumerate(members, start=1):
        changed = await sync_tag_roles(member)
        synced_count += 1
        if changed:
            roles_changed += 1

        if index % 10 == 0 or index == total_members:
            try:
                await msg.edit(
                    content=(
                        f"**Syncing member roles...**\n"
                        f"Progress: {index:,}/{total_members:,} ({index / total_members:.1%})\n"
                        f"Roles Updated: `{roles_changed}`"
                    )
                )
                await asyncio.sleep(2)
            except discord.HTTPException:
                pass

    await msg.edit(
        content=(
            f"**Sync complete!**\n"
            f"Synced tree commands and checked **{total_members}** member(s).\n"
            f"Updated roles for **{roles_changed}** member(s)."
        )
    )

@bot.command()
async def sync(ctx: commands.Context):
    await bot.tree.sync()


bot.run(TOKEN)