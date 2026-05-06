#  yuelyxia  ©  2025 – 2026

from dotenv import load_dotenv
import os
load_dotenv()

import pymongo
from pymongo import UpdateOne

import io
import aiohttp
from asyncio import Lock
import re
from collections import defaultdict

from zoneinfo import available_timezones, ZoneInfo

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
kafu = client["kafu"]
tickets = kafu["tickets"]
servers = kafu["servers"]
timezones = kafu["timezones"]

TRI_Archive = 1371673839695826974
Tethys = 1434471275723493388
ticket_ping = 1449382692671193294
KAFU = 1457009979817988241

yuelyxia = 1303291812282372137

intents = discord.Intents.all()
bot = commands.Bot(command_prefix=',', help_command=None, intents=intents)

@bot.event
async def on_ready():
    bot.add_view(TRITicketView())
    bot.add_view(BanReqView())
    bot.add_view(PilotView())
    bot.add_view(PilotFormsView())
    bot.add_view(MMView())
    bot.add_view(MMFormsView())
    bot.add_view(MMRisksView())
    quota_check.start()

TIMEZONES = sorted(available_timezones())

guild_locks = {}
def get_lock(guild_id):
    if guild_id not in guild_locks:
        guild_locks[guild_id] = Lock()
    return guild_locks[guild_id]

def parse_duration(s: str):
    match = re.fullmatch(r"(\d+)([smhd])", s.lower())
    if not match:
        return None
    value, unit = match.groups()
    value = int(value)
    multipliers = {
        "s": 1,
        "m": 60,
        "h": 3600,
        "d": 86400
    }
    return value * multipliers[unit]

@bot.command()
async def help(ctx):
    if not ctx.guild.id == TRI_Archive:
        embed = discord.Embed(title="KAFU commands", colour=0xffffff)
        embed.description = """wip
        """
        await ctx.send(embed=embed)

# loop tasks

QUOTA_CHECK_DAY = 1

@tasks.loop(time=datetime.time(hour=0, minute=0))
async def quota_check():
    now = datetime.datetime.now(datetime.timezone.utc)
    if now.day == QUOTA_CHECK_DAY:
        guilds = servers.find({})  # all servers
        for server_info in guilds:
            guild_id = int(server_info["_id"])
            try:
                guild = await bot.fetch_guild(guild_id)
            except discord.NotFound:
                continue  # bot is not in this guild anymore
            except discord.Forbidden:
                continue  # no access
            else:
                staff_lb_channel = server_info.get("staff_lb_channel")
                if staff_lb_channel:
                    try:
                        channel = await guild.fetch_channel(int(staff_lb_channel.strip("<#>")))
                        total_credits = 0
                        total_tickets = 0
                        staff = server_info.get("staff", {})
                        sorted_staff = sorted(
                            staff.items(),
                            key=lambda x: x[1].get("monthly", 0),
                            reverse=True
                        )
                        desc = ""
                        for rank, (user_id, data) in enumerate(sorted_staff, start=1):
                            monthly = data.get("monthly", 0)
                            alltime = data.get("alltime", 0)
                            desc += f"-# {rank}ㆍ　<@{user_id}>　–　**{alltime}** all ㆍ **{monthly}** month\n"
                            total_credits += monthly
                        staff_embed = discord.Embed(description=desc if desc else "No staff found.", colour = 0xffffff)
                        sorted_tickets = sorted(
                            staff.items(),
                            key=lambda x: x[1].get("monthly_tickets", 0),
                            reverse=True
                        )
                        desc = ""
                        for rank, (user_id, data) in enumerate(sorted_tickets, start=1):
                            monthly_tickets = data.get("monthly_tickets", 0)
                            tickets = data.get("tickets", 0)
                            desc += f"-# {rank}ㆍ　<@{user_id}>　–　**{tickets}** all ㆍ **{monthly_tickets}** month\n"
                            total_tickets += monthly_tickets
                        tickets_embed = discord.Embed(description=desc if desc else "No staff found.", colour = 0xffffff)
                        summary = discord.Embed(colour=0xffffff)
                        summary.description = (
                            f"✦　　┈　　total credits　　┈　　**{total_credits}**\n✦　　┈　　total tickets　　┈　　**{total_tickets}**")
                        await channel.send("## _ _　　　staff leaderboard", embed=staff_embed)
                        await channel.send("## _ _　　　tickets leaderboard", embed=tickets_embed)
                        await channel.send("## _ _　　　monthly summary", embed=summary)
                    except discord.NotFound: pass
                    except discord.Forbidden: pass
                services_lb_channel = server_info.get("services_lb_channel")
                if services_lb_channel:
                    try:
                        channel = await guild.fetch_channel(int(services_lb_channel.strip("<#>")))
                        total_services = 0
                        total_mm_services = 0
                        total_pilot_services = 0
                        mms = server_info.get("mms", {})
                        sorted_mms = sorted(
                            mms.items(),
                            key=lambda x: x[1].get("monthly", 0),
                            reverse=True
                        )
                        desc = ""
                        for rank, (user_id, data) in enumerate(sorted_mms, start=1):
                            monthly = data.get("monthly", 0)
                            alltime = data.get("alltime", 0)
                            desc += f"-# {rank}ㆍ　<@{user_id}>　–　**{alltime}** all ㆍ **{monthly}** month\n"
                            total_services += monthly
                            total_mm_services += monthly
                        mms_embed = discord.Embed(description=desc if desc else "No mms found.", colour = 0xffffff)
                        pilots = server_info.get("pilots", {})
                        sorted_pilots = sorted(
                            pilots.items(),
                            key=lambda x: x[1].get("monthly", 0),
                            reverse=True
                        )
                        desc = ""
                        for rank, (user_id, data) in enumerate(sorted_pilots, start=1):
                            monthly = data.get("monthly", 0)
                            alltime = data.get("alltime", 0)
                            desc += f"-# {rank}ㆍ　<@{user_id}>　–　**{alltime}** all ㆍ **{monthly}** month\n"
                            total_services += monthly
                            total_pilot_services += monthly
                        pilots_embed = discord.Embed(description=desc if desc else "No pilots found.", colour = 0xffffff)
                        summary = discord.Embed(colour=0xffffff)
                        summary.description = (
                            f"✦　　┈　　total services　　┈　　**{total_services}**\n✦　　┈　　total mm services　　┈　　**{total_mm_services}**\n✦　　┈　　total pilot services　　┈　　**{total_pilot_services}**")
                        await channel.send("## _ _　　　mm leaderboard", embed=mms_embed)
                        await channel.send("## _ _　　　pilot leaderboard", embed=pilots_embed)
                        await channel.send("## _ _　　　monthly summary", embed=summary)
                    except discord.NotFound: pass
                    except discord.Forbidden: pass
                for category in ["staff", "mms", "pilots"]:
                    if category in server_info:
                        for user_id in server_info[category]:
                            server_info[category][user_id]["monthly"] = 0
                servers.replace_one({"_id": server_info["_id"]}, server_info)

@bot.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return
    if message.guild is None:
        return
    guild_id = message.guild.id
    server_query = {"_id": str(guild_id)}
    server_info = servers.find_one(server_query)
    if server_info:
        mm_vouch_channel = server_info.get("mm_vouch_channel")
        if mm_vouch_channel:
            if message.channel.id == int(mm_vouch_channel.strip("<#>")):
                if message.mentions:
                    first_user = message.mentions[0]
                    user_id = str(first_user.id)
                    if user_id in server_info.get("mms", {}):
                        server_info["mms"][user_id]["monthly"] = (server_info["mms"][user_id].get("monthly", 0) + 1)
                        server_info["mms"][user_id]["alltime"] = (server_info["mms"][user_id].get("alltime", 0) + 1)
                        servers.replace_one(server_query, server_info)
                        await message.add_reaction("<:whitetick:1462774288020013161>")
                    else:
                        await message.add_reaction("<:whitecross:1462774085737119828>")
        pilot_vouch_channel = server_info.get("pilot_vouch_channel")
        if pilot_vouch_channel:
            if message.channel.id == int(pilot_vouch_channel.strip("<#>")):
                if message.mentions:
                    first_user = message.mentions[0]
                    user_id = str(first_user.id)
                    if user_id in server_info.get("pilots", {}):
                        server_info["pilots"][user_id]["monthly"] = (
                                    server_info["pilots"][user_id].get("monthly", 0) + 1)
                        server_info["pilots"][user_id]["alltime"] = (
                                    server_info["pilots"][user_id].get("alltime", 0) + 1)
                        servers.replace_one(server_query, server_info)
                        await message.add_reaction("<:whitetick:1462774288020013161>")
                    else:
                        await message.add_reaction("<:whitecross:1462774085737119828>")

    await bot.process_commands(message)

@bot.event
async def on_member_remove(member):
    server = servers.find_one({"_id": str(member.guild.id)})
    if server:
        roles = server.get("custom_roles", {})
        async with get_lock(member.guild.id):
            for role_id, data in list(roles.items()):
                if data["owner"] == str(member.id):
                    role = member.guild.get_role(int(role_id))
                    if role:
                        await role.delete()
                    servers.update_one(
                        {"_id": member.guild.id},
                        {"$unset": {f"custom_roles.{role_id}": ""}}
                )

# text commands

@bot.command(name="pilot")
async def pilot(ctx, *, desc:str=None):
    if not desc:
        await ctx.send(view=PilotView())
    if desc == "forms":
        await ctx.send("> By filling any of the forms below, you agree to vouch if the account has been logged into, give **partial** fee if services worth **≥$3** has been completed, and give **__full__** fee if at least **50%** of the task was done before cancellation.", view=PilotFormsView())

class PilotView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
    @discord.ui.button(label="forms", style=discord.ButtonStyle.grey, custom_id="pilot:forms")
    async def forms_button(self, interaction, button):
        await interaction.response.send_message(view=PilotFormsView())

class PilotFormsView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
    @discord.ui.button(label="genshin", style=discord.ButtonStyle.grey, custom_id="pilot_forms:genshin")
    async def genshin_button(self, interaction, button):
        await interaction.response.send_message("""
### Genshin Impact Pilot Form
Account Size: 
Server: 
Task: 
Time Limit:
Fee:
Do’s & Don’ts: 
Account Issues: 
> By filling in the form, you agree to vouch if the account has been logged into, give **partial** fee if services worth **≥$3** has been completed, and give **__full__** fee if at least **50%** of the task was done before cancellation.
""")

    @discord.ui.button(label="hsr", style=discord.ButtonStyle.grey, custom_id="pilot_forms:hsr")
    async def hsr_button(self, interaction, button):
        await interaction.response.send_message("""
### Honkai: Star Rail Pilot Form
Account Size: 
Server: 
Task: 
Time Limit:
Fee:
Do’s & Don’ts: 
Account Issues: 
> By filling in the form, you agree to vouch if the account has been logged into, give **partial** fee if services worth **≥$3** has been completed, and give **__full__** fee if at least **50%** of the task was done before cancellation.
""")

    @discord.ui.button(label="wuwa", style=discord.ButtonStyle.grey, custom_id="pilot_forms:wuwa")
    async def wuwa_button(self, interaction, button):
        await interaction.response.send_message("""
### Wuthering Waves Pilot Form
Account Size: 
Server: 
Task: 
Time Limit:
Fee:
Do’s & Don’ts: 
Account Issues: 
> By filling in the form, you agree to vouch if the account has been logged into, give **partial** fee if services worth **≥$3** has been completed, and give **__full__** fee if at least **50%** of the task was done before cancellation.
""")

    @discord.ui.button(label="roblox", style=discord.ButtonStyle.grey, custom_id="pilot_forms:roblox")
    async def roblox_button(self, interaction, button):
        await interaction.response.send_message("""
### Roblox Pilot Form
Roblox Game: 
Task: 
Time Limit:
Fee:
Do’s & Don’ts: 
> By filling in the form, you agree to vouch if the account has been logged into, give **partial** fee if services worth **≥$3** has been completed, and give **__full__** fee if at least **50%** of the task was done before cancellation.
""")


@bot.command(name="mm")
async def mm(ctx, *, desc: str=None):
    if not desc:
        await ctx.send(view=MMView())
    if desc == "forms":
        await ctx.send("> By filling any of the forms below, you agree to vouch if at least **one** account was checked, and give fee if at least **one** account was **checked and __secured__** OR **two** accounts were checked before cancellation.", view=MMFormsView())
    if desc == "risks":
        await ctx.send(view=MMRisksView())

class MMView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
    @discord.ui.button(label="forms", style=discord.ButtonStyle.grey, custom_id="mm:forms")
    async def forms_button(self, interaction, button):
        await interaction.response.send_message(view=MMFormsView())
    @discord.ui.button(label="risks", style=discord.ButtonStyle.grey, custom_id="mm:risks")
    async def risks_button(self, interaction, button):
        await interaction.response.send_message(view=MMRisksView())

class MMFormsView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
    @discord.ui.button(label="genshin", style=discord.ButtonStyle.grey, custom_id="mm_forms:genshin")
    async def genshin_button(self, interaction, button):
        await interaction.response.send_message("""
### Genshin Impact MM Form
Account Size: 
Adventure Rank: 
Server: 
5 star characters, constellations & weapons: 
Deadlinks: 
H.abyss? 
Lost Receipts? 
Are you the original owner? 
Can the email be surrendered? 
Other Issues: 
Fee + who’s providing: 
> By filling any of the forms below, you agree to vouch if at least **one** account was checked, and give fee if at least **one** account was **checked and __secured__** OR **two** accounts were checked before cancellation.
""")

    @discord.ui.button(label="hsr", style=discord.ButtonStyle.grey, custom_id="mm_forms:hsr")
    async def hsr_button(self, interaction, button):
        await interaction.response.send_message("""
### Honkai: Star Rail MM form
Account Size: 
Trailblaze Level: 
Server: 
5 star characters, eidolons & lightcones: 
Deadlinks: 
Lost Receipts? 
Are you the original owner? 
Can the email be surrendered? 
Other Issues: 
Fee + who’s providing: 
> By filling any of the forms below, you agree to vouch if at least **one** account was checked, and give fee if at least **one** account was **checked and __secured__** OR **two** accounts were checked before cancellation.
""")

    @discord.ui.button(label="wuwa", style=discord.ButtonStyle.grey, custom_id="mm_forms:wuwa")
    async def wuwa_button(self, interaction, button):
        await interaction.response.send_message("""
### Wuthering Waves MM form
Account Size: 
Union Level: 
Server: 
5 star characters, sequences & weapons: 
Deadlinks: 
H.tower? 
Lost Receipts? 
Are you the original owner? 
**Please note that email __must__ be surrendered for wuwa accounts.**
Other Issues: 
Fee + who’s providing: 
> By filling any of the forms below, you agree to vouch if at least **one** account was checked, and give fee if at least **one** account was **checked and __secured__** OR **two** accounts were checked before cancellation.
""")

    @discord.ui.button(label="roblox", style=discord.ButtonStyle.grey, custom_id="mm_forms:roblox")
    async def roblox_button(self, interaction, button):
        await interaction.response.send_message("""
### Roblox MM form
Username: 
Do you have the original email? 
Can the email be surrendered? 
PIN Set or Unset? 
Lost Receipts? 
Are you the original owner? 
Other Issues: 
Fee + who’s providing: 
> By filling any of the forms below, you agree to vouch if at least **one** account was checked, and give fee if at least **one** account was **checked and __secured__** OR **two** accounts were checked before cancellation.
""")

    @discord.ui.button(label="roblox items", style=discord.ButtonStyle.grey, custom_id="mm_forms:roblox_items")
    async def roblox_items_button(self, interaction, button):
        await interaction.response.send_message("""
### Roblox Items MM form
Username: 
Roblox Game:
Roblox Game Items:
Fee + who’s providing: 
> By filling any of the forms below, you agree to vouch if at least **one** account was checked, and give fee if at least **one** account was **checked and __secured__** OR **two** accounts were checked before cancellation.
""")

class MMRisksView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="deadlinks", style=discord.ButtonStyle.grey, custom_id="mm_risks:deadlinks")
    async def deadlinks_button(self, interaction, button):
        await interaction.response.send_message("""
## Deadlinks <a:whitealert:1496542298908000257>
> 3rd party links are links binded to the hoyoverse account which serves as an alternative way to login - Facebook, Game Center, Google, PSN, Apple, Twitter. A deadlink is a 3rd party link where the owner no longer has access to the 3rd party account and is unable to unlink it, but also unable to login via the link, e.g. Twitter account was deleted.
**__Risks__**
- **Hoyoverse:** Facebook, Twitter, Google, Apple and Game Center links are __safe__ and can be secured easily by removing all trusted devices via the [Hoyoverse website](https://account.hoyoverse.com). Attempts to login via these links will require a verification code sent to the linked email.
- **Wuthering Waves:** Note that in Wuwa, ANY 3rd party links attached can be used to log into the account __without a verification code__, even after the password has been changed.
- A deadlink may not be truly dead; scammers may lie about deadlinks and use them to attempt to retrieve the account later on.
- **PSN and Xbox links are especially __dangerous__** as they do not require new device verification and require Hoyoverse CS to unlink. a PSN link may be considered dead if the most recent trophy was gained >6 months ago.
> **Please __react__** once you have read and acknowledged that your middleman is __not__ responsible if these risks occur after the trade. choose to proceed only if you are willing to take the risks.
                    """)

    @discord.ui.button(label="hacked abyss", style=discord.ButtonStyle.grey, custom_id="mm_risks:hacked_abyss")
    async def hacked_abyss_button(self, interaction, button):
        await interaction.response.send_message("""
## Hαcked Abyss <a:whitealert:1496542298908000257>
> A h.abyss account is where a bot was used to complete spiral abyss to gain primogems. A h.abyss account can be identified when a high number of stars has been obtained with missing stats (e.g. most damage taken) or an unusually low "strongest single strike" in the abyss challenge summary. They typically apply to reroll accounts using starter characters. However, other characters can also be used.
**__Risks__**
- As it is against Hoyoverse’s ToS, your account and/or IP address may get banned.
- Asia accounts seem to be riskier than EU or NA accounts.
- The risk may not be high, but it is always there and should always be mentioned when trading.
> **Please __react__** once you have read and acknowledged that your middleman is __not__ responsible if these risks occur after the trade. choose to proceed only if you are willing to take the risks.
                    """)

    @discord.ui.button(label="lost receipts", style=discord.ButtonStyle.grey, custom_id="mm_risks:lost_receipts")
    async def lost_receipts_button(self, interaction, button):
        await interaction.response.send_message("""
## Lost Receipts <a:whitealert:1496542298908000257>
> These risks apply to **ALL __P2W__ accounts**, even if you have receipts. P2W is when there has been **any** purchase on the account, regardless of amount, when the purchase was made and from where (in-game top-up, codashop, giveaway win etc.)
> Receipts must have the __amount spent, transaction ID and what was purchased__ in a **__full__ screenshot** (preferably uncropped) to be a valid receipt.
**__Risks__**
- Increased chances of retrieval from the owner who purchased something. the older the receipt, the easier the retrieval.
- Scammers may lie about having lost the receipts when they still have possession of them but are unwilling to provide them so that they can retrieve the account from Hoyoverse CS later on.
- Purchase records are only kept for 6 months in currency records.
- Purchases made within 2 weeks can be __refunded.__ It will result in **negative premium currency (e.g. primogems) which needs to be brought back to 0 or more within __1 week__ or the account will be banned.
> **Please __react__** once you have read and acknowledged that your middleman is __not__ responsible if these risks occur after the trade. choose to proceed only if you are willing to take the risks.
                        """)

    @discord.ui.button(label="email surrender", style=discord.ButtonStyle.grey, custom_id="mm_risks:email_surrender")
    async def email_surrender_button(self, interaction, button):
        await interaction.response.send_message("""
## Email Surrender <a:whitealert:1496542298908000257>
> Email surrender requires giving up the entire email, fully losing access of it, so ensure you will never need it in the future.
**__Risks__**
- Higher chance of retrieval.
- Email can be disabled/frozen, meaning you cannot receive any new verification codes.
- Previously surrendered emails are more risky.
- Gmail holds recovery info for up to 2 weeks.
**__FOR GMAILS: Do not change password within the first 72h__ and avoid changing recovery info frequently to prevent locking.** __Outlook__ emails are __safe__ to change password immediately.
> **Please __react__** once you have read and acknowledged that your middleman is __not__ responsible if these risks occur after the trade. choose to proceed only if you are willing to take the risks.
                            """)

@bot.command(name="adm", help="Pings ADM+.")
async def adm(ctx):
    if ctx.guild.id == TRI_Archive:
        return
    guild_id = ctx.guild.id
    server_query = {"_id": str(guild_id)}
    server_info = servers.find_one(server_query)
    if not server_info:
        return
    adm_role = server_info.get("adm_role")
    if adm_role:
        await ctx.reply(f"{adm_role}")

@bot.command(name="revive", help="Pings revive.")
async def revive(ctx):
    guild_id = ctx.guild.id
    server_query = {"_id": str(guild_id)}
    server_info = servers.find_one(server_query)
    if not server_info:
        return
    revive_ping = server_info.get("revive_ping")
    if revive_ping:
        await ctx.reply(f"{revive_ping}")

@bot.command(name="lb", help="Sends the current month’s leaderboard.")
async def lb(ctx, *, category: str=None):
    guild_id = ctx.guild.id
    server_query = {"_id": str(guild_id)}
    server_info = servers.find_one(server_query)
    if not server_info:
        return
    if category == "s":
        staff = server_info.get("staff", {})
        sorted_staff = sorted(
            staff.items(),
            key=lambda x: x[1].get("monthly", 0),
            reverse=True
        )
        desc = ""
        for rank, (user_id, data) in enumerate(sorted_staff, start=1):
            if rank > 50:
                break
            monthly = data.get("monthly", 0)
            alltime = data.get("alltime", 0)
            desc += f"-# {rank}ㆍ　<@{user_id}>　–　**{alltime}** all ㆍ **{monthly}** month\n"
        embed = discord.Embed(description=desc if desc else "No staff found.", colour = 0xffffff)
        await ctx.send("## _ _　　　staff leaderboard", embed=embed)
    if category == "t":
        staff = server_info.get("staff", {})
        sorted_tickets = sorted(
            staff.items(),
            key=lambda x: x[1].get("monthly_tickets", 0),
            reverse=True
        )
        desc = ""
        for rank, (user_id, data) in enumerate(sorted_tickets, start=1):
            if rank > 50:
                break
            monthly_tickets = data.get("monthly_tickets", 0)
            tickets = data.get("tickets", 0)
            desc += f"-# {rank}ㆍ　<@{user_id}>　–　**{tickets}** all ㆍ **{monthly_tickets}** month\n"
        embed = discord.Embed(description=desc if desc else "No staff found.", colour=0xffffff)
        await ctx.send("## _ _　　　tickets leaderboard", embed=embed)
    if category == "m":
        mms = server_info.get("mms", {})
        sorted_mms = sorted(
            mms.items(),
            key=lambda x: x[1].get("monthly", 0),
            reverse=True
        )
        desc = ""
        for rank, (user_id, data) in enumerate(sorted_mms, start=1):
            if rank > 50:
                break
            monthly = data.get("monthly", 0)
            alltime = data.get("alltime", 0)
            desc += f"-# {rank}ㆍ　<@{user_id}>　–　**{alltime}** all ㆍ **{monthly}** month\n"
        embed = discord.Embed(description=desc if desc else "No mms found.", colour = 0xffffff)
        await ctx.send("## _ _　　　mm leaderboard", embed=embed)
    if category == "p":
        pilots = server_info.get("pilots", {})
        sorted_pilots = sorted(
            pilots.items(),
            key=lambda x: x[1].get("monthly", 0),
            reverse=True
        )
        desc = ""
        for rank, (user_id, data) in enumerate(sorted_pilots, start=1):
            if rank > 50:
                break
            monthly = data.get("monthly", 0)
            alltime = data.get("alltime", 0)
            desc += f"-# {rank}ㆍ　<@{user_id}>　–　**{alltime}** all ㆍ **{monthly}** month\n"
        embed = discord.Embed(description=desc if desc else "No pilots found.", colour = 0xffffff)
        await ctx.send("## _ _　　　pilot leaderboard", embed=embed)


@bot.command(name="rn")
@commands.cooldown(2, 600, commands.BucketType.channel)
async def rn(ctx, *, new_name: str):
    if ctx.guild.id == TRI_Archive or ctx.guild.id == Tethys:
        return
    guild_id = str(ctx.guild.id)
    server_info = servers.find_one({"_id": guild_id})
    if server_info:
        staff_role = server_info.get("staff_role")
    if (staff_role and get(ctx.guild.roles, id=int(staff_role.strip("<@&>")))) in ctx.author.roles or ctx.author.guild_permissions.manage_channels:
        if isinstance(ctx.channel, discord.Thread):
            try:
                await ctx.channel.edit(name=new_name)
                await ctx.send(f"Thread renamed to **{new_name}**.")
            except Exception as e:
                await ctx.send(f"Renaming failed due to an error: {e}", ephemeral=True)
        elif isinstance(ctx.channel, discord.TextChannel):
            try:
                await ctx.channel.edit(name=new_name)
                await ctx.send(f"Channel renamed to **{new_name}**.")
            except Exception as e:
                await ctx.send(f"Renaming failed due to an error: {e}", ephemeral=True)
        else:
            await ctx.send("This command can only be used in a channel or thread.", ephemeral=True)
@rn.error
async def rn_error(ctx, error):
    if isinstance(error, commands.CommandOnCooldown):
        remaining = error.retry_after  # cooldown time in seconds
        return await ctx.send(f"This command is on cooldown. Retry in {round(remaining)} seconds.", ephemeral=True)
    raise error

CLAIM_REGEX = re.compile(r"<@!?(\d+)> has claimed the ticket\.")
UNCLAIM_REGEX = re.compile(r"<@!?(\d+)> has unclaimed the ticket\.")

async def get_active_claims(channel):
    claim_counts = defaultdict(int)
    async for msg in channel.history(limit=None, oldest_first=True):
        if msg.author.id != KAFU:
            continue
        if not msg.embeds:
            continue
        for embed in msg.embeds:
            content = embed.description or ""
            match = CLAIM_REGEX.search(content)
            if match:
                user_id = int(match.group(1))
                claim_counts[user_id] += 1
                continue
            match = UNCLAIM_REGEX.search(content)
            if match:
                user_id = int(match.group(1))
                claim_counts[user_id] -= 1
                continue
    active_users = [uid for uid, count in claim_counts.items() if count > 0]
    return active_users

async def active_claim(channel, user_id):
    count = 0
    async for msg in channel.history(limit=None, oldest_first=True):
        if msg.author.id != KAFU or not msg.embeds:
            continue
        for embed in msg.embeds:
            content = embed.description
            claim_match = CLAIM_REGEX.search(content)
            if claim_match and int(claim_match.group(1)) == user_id:
                count += 1
                continue
            unclaim_match = UNCLAIM_REGEX.search(content)
            if unclaim_match and int(unclaim_match.group(1)) == user_id:
                count -= 1
                continue
    return count > 0

async def credits_already_given(channel):
    async for msg in channel.history(limit=50, oldest_first=False):  # bottom → top
        if msg.author.id != KAFU:
            continue
        if msg.content and "Ticket credit(s) have been given" in msg.content:
            return True
    return False

@bot.command(name="claim")
async def claim(ctx, mode: str = None, member: discord.Member = None):
    server_info = servers.find_one_and_update(
        {"_id": str(ctx.guild.id)},
        {"$setOnInsert": {"_id": str(ctx.guild.id)}},
        upsert=True,
        return_document=True
    )
    if server_info:
        if not server_info.get("staff_role"):
            await ctx.reply("**staff role** has not been set up for this server.")
            return
        if not server_info.get("adm_role"):
            await ctx.reply("**adm role** has not been set up for this server.")
            return
        staff_role = server_info.get("staff_role")
        adm_role = server_info.get("adm_role")
        if get(ctx.guild.roles, id=int(staff_role.strip("<@&>"))) in ctx.author.roles:
            if mode == "force":
                if get(ctx.guild.roles, id=int(adm_role.strip("<@&>"))) in ctx.author.roles or ctx.author.guild_permissions.manage_roles:
                    if not member:
                        await ctx.send("Please specify a user to force claim.")
                        return
                    already_claimed = await active_claim(channel=ctx.channel, user_id=member.id)
                    if already_claimed:
                        await ctx.reply("They have already claimed this ticket.")
                        return
                    target = member
                else:
                    await ctx.reply("Unauthorised.")
                    return
            else:
                target = ctx.author
                already_claimed = await active_claim(channel=ctx.channel, user_id=ctx.author.id)
                if already_claimed:
                    await ctx.reply("You have already claimed this ticket.")
                    return
            embed = discord.Embed(colour=0xffffff, description=f"{target.mention} has claimed the ticket.")
            await ctx.reply(embed=embed)

@bot.command(name="unclaim")
async def unclaim(ctx, mode: str = None, member: discord.Member = None):
    server_info = servers.find_one_and_update(
        {"_id": str(ctx.guild.id)},
        {"$setOnInsert": {"_id": str(ctx.guild.id)}},
        upsert=True,
        return_document=True
    )
    if server_info:
        if not server_info.get("staff_role"):
            await ctx.reply("**staff role** has not been set up for this server.")
            return
        if not server_info.get("adm_role"):
            await ctx.reply("**adm role** has not been set up for this server.")
            return
        staff_role = server_info.get("staff_role")
        adm_role = server_info.get("adm_role")
        if get(ctx.guild.roles, id=int(staff_role.strip("<@&>"))) in ctx.author.roles:
            if mode == "force":
                if get(ctx.guild.roles, id=int(adm_role.strip("<@&>"))) in ctx.author.roles or ctx.author.guild_permissions.manage_roles:
                    if not member:
                        await ctx.send("Please specify a user to force claim.")
                        return
                    already_claimed = await active_claim(channel=ctx.channel, user_id=member.id)
                    if not already_claimed:
                        await ctx.reply("They have not claimed this ticket.")
                        return
                    target = member
                else:
                    await ctx.reply("Unauthorised.")
                    return
            else:
                target = ctx.author
                already_claimed = await active_claim(channel=ctx.channel, user_id=ctx.author.id)
                if not already_claimed:
                    await ctx.reply("You have not claimed this ticket.")
                    return
            embed = discord.Embed(colour=0xffffff, description=f"{target.mention} has unclaimed the ticket.")
            await ctx.reply(embed=embed)

@bot.command(name="claims")
async def claims(ctx):
    server_info = servers.find_one_and_update(
        {"_id": str(ctx.guild.id)},
        {"$setOnInsert": {"_id": str(ctx.guild.id)}},
        upsert=True,
        return_document=True
    )
    if not server_info.get("staff_role"):
        await ctx.reply("**staff role** has not been set up for this server.")
        return
    staff_role = server_info.get("staff_role")
    if get(ctx.guild.roles, id=int(staff_role.strip("<@&>"))) in ctx.author.roles:
        active_claims = await get_active_claims(ctx.channel)
        mentions = [f"<@{uid}>" for uid in active_claims]
        embed = discord.Embed(colour=0xffffff, description = f"Ticket has been claimed by **{len(mentions)}** user(s)\n" + ", ".join(mentions))
        await ctx.reply(embed=embed)

@bot.command(name="close")
async def close(ctx):
    server_info = servers.find_one_and_update(
        {"_id": str(ctx.guild.id)},
        {"$setOnInsert": {"_id": str(ctx.guild.id)}},
        upsert=True,
        return_document=True
    )
    if server_info:
        if not server_info.get("staff_role"):
            await ctx.reply("**staff role** has not been set up for this server.")
            return
        staff_role = server_info.get("staff_role")
        adm_role = server_info.get("adm_role")
        if get(ctx.guild.roles, id=int(staff_role.strip("<@&>"))) in ctx.author.roles:
            if ctx.guild.id == TRI_Archive and not get(ctx.guild.roles, id=int(adm_role.strip("<@&>"))) in ctx.author.roles:
                await ctx.reply("You are not authorised to close this ticket.")
                return
            already_given = await credits_already_given(ctx.channel)
            if already_given:
                await ctx.reply("Ticket credits have already been given.")
                return
            active_claims = await get_active_claims(ctx.channel)
            mentions = [f"<@{uid}>" for uid in active_claims]
            embed = discord.Embed(colour=0xffffff, description=f"Ticket has been claimed by **{len(mentions)}** user(s)\n" + ", ".join(mentions))
            await ctx.reply(embed=embed, view=TicketCloseView(active_claims))

class TicketCloseView(discord.ui.View):
    def __init__(self, active_claims):
        super().__init__(timeout=120)
        self.active_claims = active_claims

    @discord.ui.button(label="Confirm", style=discord.ButtonStyle.green, custom_id="ticketclose:confirm")
    async def confirm_button(self, interaction, button):
        await interaction.response.defer(ephemeral=True)
        server_query = {"_id": str(interaction.guild.id)}
        server_info = servers.find_one(server_query)
        if not server_info: return
        staff_role = server_info.get("staff_role")
        adm_role = server_info.get("adm_role")
        if not staff_role: return
        if get(interaction.guild.roles, id=int(staff_role.strip("<@&>"))) in interaction.user.roles:
            if interaction.guild.id == TRI_Archive and not get(interaction.guild.roles, id=int(adm_role.strip("<@&>"))) in interaction.user.roles:
                await interaction.followup.send("You are not authorised to close this ticket.", ephemeral=True)
            operations = []
            for uid in self.active_claims:
                try:
                    staff_data = server_info.get("staff").get(str(uid))
                    if not staff_data:
                        raise KeyError(uid)
                    staff_data["monthly_tickets"] = staff_data.get("monthly_tickets", 0) + 1
                    staff_data["tickets"] = staff_data.get("tickets", 0) + 1
                    operations.append(UpdateOne(
                        {"_id": str(interaction.guild.id), f"staff.{str(uid)}": {"$exists": True}},
                        {"$inc": {f"staff.{str(uid)}.monthly_tickets": 1, f"staff.{str(uid)}.tickets": 1},
                         }))
                except KeyError:
                    await interaction.followup.send(f"Unable to add ticket credit to <@{uid}>.", ephemeral=True)
                    continue
            if operations:
                servers.bulk_write(operations)
            await interaction.edit_original_response(content="Ticket credit(s) have been given.", view=None)

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.red, custom_id="ticketclose:cancel")
    async def cancel_button(self, interaction, button):
        await interaction.response.defer()
        await interaction.edit_original_response(content="**Cancelled.** Ticket credit(s) have not been given.",view=None)

def user_info(user, staff_data=None, mm_data=None, pilot_data=None):
    profile = discord.Embed()
    profile.set_thumbnail(url=f"{user.display_avatar}")
    profile.description = f"{user.name}\n`{user.id}`\n{user.mention}"
    profile.description += f"\n**Account Created:** <t:{round(int(user.created_at.timestamp()))}:D> (<t:{round(int(user.created_at.timestamp()))}:R>)\n"
    if staff_data is not None:
        profile.add_field(
            name="staff",
            value=f"**{staff_data.get('alltime', 0)}** all ㆍ **{staff_data.get('monthly', 0)}** month",
            inline=False
        )
        profile.add_field(
            name="tickets",
            value=f"**{staff_data.get('tickets', 0)}** all ㆍ **{staff_data.get('monthly_tickets', 0)}** month",
            inline=False
        )
    if mm_data is not None:
        profile.add_field(
            name="mm",
            value=f"**{mm_data.get('alltime', 0)}** all ㆍ **{mm_data.get('monthly', 0)}** month",
            inline=False
        )
    if pilot_data is not None:
        profile.add_field(
            name="pilot",
            value=f"**{pilot_data.get('alltime', 0)}** all ㆍ **{pilot_data.get('monthly', 0)}** month",
            inline=False
        )
    profile.set_footer(text="✦　Use ,c to check if user is reported, unreported or trusted.")
    return profile

@bot.command(name="p")
async def profile(ctx, user:str = None):
    if user is None:
        user = ctx.author
    else:
        try:
            user = await bot.fetch_user(int(user.strip('<@>')))
        except Exception:
            await ctx.reply("Please provide a valid user ID.")
            return
    guild_id = str(ctx.guild.id)
    server_info = servers.find_one({"_id": guild_id})
    if not server_info:
        await ctx.reply(embed=user_info(user))
        return
    uid = str(user.id)
    staff = server_info.get("staff", {})
    mms = server_info.get("mms", {})
    pilots = server_info.get("pilots", {})
    roles = []
    if uid in staff:
        roles.append("staff")
        staff_data = staff.get(uid, {})
    else:
        staff_data = None
    if uid in mms:
        roles.append("mm")
        mm_data = mms.get(uid, {})
    else:
        mm_data = None
    if uid in pilots:
        roles.append("pilot")
        pilot_data = pilots.get(uid, {})
    else:
        pilot_data = None
    await ctx.reply(embed=user_info(user, staff_data, mm_data, pilot_data))

def format_time_utc(tz_str: str):
    now = datetime.datetime.now(ZoneInfo(tz_str))
    offset = now.utcoffset()
    total_minutes = int(offset.total_seconds() // 60)
    hours = total_minutes // 60
    minutes = abs(total_minutes % 60)
    if minutes == 0:
        utc_str = f"UTC{hours:+}"
    else:
        utc_str = f"UTC{hours:+}:{minutes:02d}"
    time_str = now.strftime("%I:%M %p")
    return f"{time_str} ({utc_str})"

@bot.command(name="tz")
async def tz(ctx, user:str = None):
    if user is None:
        user = ctx.author
    else:
        try:
            user = await bot.fetch_user(int(user.strip('<@>')))
        except Exception:
            await ctx.reply("Please provide a valid user ID.")
            return
    guild_id = str(ctx.guild.id)
    server_info = servers.find_one({"_id": guild_id})
    uid = str(user.id)
    if server_info:
        staff = server_info.get("staff", {})
        if uid in staff:
            profile = timezones.find_one({"_id": uid})
            user_tz = profile.get("timezone") if profile else None
            if user_tz is not None:
                formatted = format_time_utc(user_tz)
                await ctx.reply(f"It is now **{formatted}** for **{user.name}**")
            else:
                await ctx.reply(f"`{user.id}` has not set their timezone.")
        else:
            await ctx.reply(f"`{user.id}` is not appointed as staff.")

async def timezone_autocomplete(interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
    matches = [tz for tz in TIMEZONES if current.lower() in tz.lower()][:25]
    return [app_commands.Choice(name=tz.replace("_", " "), value=tz) for tz in matches]

settings = app_commands.Group(name="set", description="Set.")
bot.tree.add_command(settings)

@settings.command(name="timezone", description="Set your timezone")
@app_commands.autocomplete(timezone=timezone_autocomplete)
async def set_timezone(interaction: discord.Interaction, timezone: str):
    if timezone not in TIMEZONES:
        await interaction.response.send_message("Invalid timezone.", ephemeral=True)
        return
    guild_id = interaction.guild.id
    if interaction.guild is None:
        await interaction.response.send_message("This command can only be used in a server.", ephemeral=True)
        return
    server_info = servers.find_one_and_update(
        {"_id": str(interaction.guild.id)},
        {"$setOnInsert": {"_id": str(interaction.guild.id)}},
        upsert=True,
        return_document=True
    )
    if server_info:
        if not server_info.get("staff_role"):
            await interaction.followup.send("**staff role** has not been set up for this server.", ephemeral=True)
            return
        staff_role = server_info.get("staff_role")
        if get(interaction.user.guild.roles, id=int(staff_role.strip("<@&>"))) in interaction.user.roles:
            server_info.setdefault("staff", {})
            uid = str(interaction.user.id)
            staff = server_info.get("staff", {})
            if uid in staff:
                timezones.update_one(
                    {"_id": uid},
                    {"$set": {"timezone": timezone}},
                    upsert=True
                )
            now = datetime.datetime.now(ZoneInfo(timezone))
            offset = now.utcoffset()
            total_minutes = int(offset.total_seconds() // 60)
            hours = total_minutes // 60
            minutes = abs(total_minutes % 60)
            if minutes == 0:
                utc = f"UTC{hours:+}"
            else:
                utc = f"UTC{hours:+}:{minutes:02d}"
            await interaction.response.send_message(f"Your timezone has been set to **{timezone.replace("_", " ")} ({utc})**.")

@settings.command(name="points", description="Set points to a certain value.")
async def set_points(interaction: discord.Interaction, user: str, category: Literal["staff", "mm", "pilot", "tickets"], timeframe: Literal["monthly", "alltime"], value: str):
    await interaction.response.defer(ephemeral=True)
    if not is_int(value):
        await interaction.followup.send("Please input a valid integer value.", ephemeral=True)
        return
    guild_id = interaction.guild.id
    server_query = {"_id": str(guild_id)}
    server_info = servers.find_one_and_update(
        {"_id": str(interaction.guild.id)},
        {"$setOnInsert": {"_id": str(interaction.guild.id)}},
        upsert=True,
        return_document=True
    )
    if not server_info.get("staff_role"):
        await interaction.followup.send("**staff role** has not been set up for this server.", ephemeral=True)
        return
    if not server_info.get("bans_warns_channel"):
        await interaction.followup.send("**bans warns channel** has not been set up for this server.",
                                        ephemeral=True)
        return
    staff_role = server_info.get("staff_role")
    if get(interaction.user.guild.roles, id=int(staff_role.strip("<@&>"))) in interaction.user.roles:
        try:
            user = await bot.fetch_user(int(user.strip("<@>")))
        except Exception:
            await interaction.followup.send(f"Please enter a valid user ID.", ephemeral=True)
        else:
            user_id = user.id
            member = interaction.guild.get_member(int(user_id))
            if not member: return
            if category == "staff":
                if not interaction.user.guild_permissions.manage_roles:
                    await interaction.followup.send(f"Unauthorised.", ephemeral=True)
                    return
                staff = server_info.get("staff", {}).get(str(user_id))
                if staff:
                    if timeframe == "monthly":
                        staff["monthly"] = int(value)
                    if timeframe == "alltime":
                        staff["alltime"] = int(value)
            if category == "mm":
                mm = server_info.get("mm", {}).get(str(user_id))
                if mm:
                    if timeframe == "monthly":
                        mm["monthly"] = int(value)
                    if timeframe == "alltime":
                        mm["alltime"] = int(value)
            if category == "pilot":
                pilot = server_info.get("pilot", {}).get(str(user_id))
                if pilot:
                    if timeframe == "monthly":
                        pilot["monthly"] = int(value)
                    if timeframe == "alltime":
                        pilot["alltime"] = int(value)
            if category == "tickets":
                if not interaction.user.guild_permissions.manage_roles:
                    await interaction.followup.send(f"Unauthorised.", ephemeral=True)
                    return
                staff = server_info.get("staff", {}).get(str(user_id))
                if staff:
                    if timeframe == "monthly":
                        staff["monthly_tickets"] = int(value)
                    if timeframe == "alltime":
                        staff["tickets"] = int(value)
            servers.replace_one(server_query, server_info)
            await interaction.followup.send(f"`{user_id}`’s **{timeframe} {category}** points has been set to **{value}**.", ephemeral=True)


@bot.command(name="cr")
async def cr(ctx):
    server_info = servers.find_one_and_update(
        {"_id": str(ctx.guild.id)},
        {"$setOnInsert": {"_id": str(ctx.guild.id)}},
        upsert=True,
        return_document=True
    )
    custom_roles = server_info.get("custom_roles", {})
    role_id = next((r for r, d in custom_roles.items() if d.get("owner") == str(ctx.author.id)), None)
    if not role_id:
        await ctx.reply("You do not have a custom role.")
        return
    role = ctx.guild.get_role(int(role_id))
    if not role:
        await ctx.reply("Your custom role no longer exists.")
        return
    data = custom_roles[role_id]
    if data["type"] == "booster":
        expiry = "booster (active while boosting)"
    elif data.get("expires_at"):
        expiry = f"<t:{data["expires_at"]}:R>"
    else:
        expiry = "no expiry"
    embed = discord.Embed(
        colour=role.colour,
        description=f"**Role:** {role.mention} `{role.id}`\n**Owner:** {ctx.author.mention}\n**Expires:** {expiry}"
    )
    embed.set_author(name=role.name, icon_url=role.icon.url if role.icon else None)
    await ctx.reply(embed=embed)

@tasks.loop(hours=1)
async def customrole_expiry_loop():
    now = int(time.time())
    for server_info in servers.find({}):
        guild = bot.get_guild(int(server_info["_id"]))
        if not guild:
            continue
        roles = server_info.get("custom_roles", {})
        for role_id, data in list(roles.items()):
            role = guild.get_role(int(role_id))
            if not role:
                continue
            owner = guild.get_member(int(data["owner"]))
            if data["type"] == "booster":
                if not owner or not owner.premium_since:
                    await role.delete(reason="Booster custom role expired")
                    servers.update_one(
                        {"_id": server_info["_id"]},
                        {"$unset": {f"custom_roles.{role_id}": ""}}
                    )
                continue
            if data["expires_at"] and now >= data["expires_at"]:
                await role.delete(reason="Custom role expired")
                servers.update_one(
                    {"_id": server_info["_id"]},
                    {"$unset": {f"custom_roles.{role_id}": ""}}
                )

@tasks.loop(hours=6)
async def cleanup_custom_roles():
    for server in servers.find({}):
        guild = bot.get_guild(int(server["_id"]))
        if not guild:
            continue
        custom_roles = server.get("custom_roles", {})
        for role_id in list(custom_roles.keys()):
            role = guild.get_role(int(role_id))
            if role is None:
                servers.update_one(
                    {"_id": server["_id"]},
                    {"$unset": {f"custom_roles.{role_id}": ""}}
                )

customrole = app_commands.Group(name="customrole", description="Manage custom roles.")
bot.tree.add_command(customrole)

@customrole.command(name="list", description="List all custom roles.")
async def customrole_list(interaction: discord.Interaction):
    server_info = servers.find_one({"_id": str(interaction.guild.id)})
    roles = server_info.get("custom_roles", {})
    desc = ""
    for role_id, data in roles.items():
        role = interaction.guild.get_role(int(role_id))
        if not role:
            continue
        owner = f"<@{data["owner"]}>"
        if data["type"] == "booster":
            expiry = "booster"
        elif data["expires_at"]:
            expiry = f"<t:{data["expires_at"]}:R>"
        else:
            expiry = "no expiry"
        desc += f"{role.mention}　–　{owner}　–　expires {expiry}\n"
    embed = discord.Embed(description=desc or "No custom roles.")
    await interaction.response.send_message(embed=embed)

@customrole.command(name="edit", description="Edit a custom role.")
async def customrole_edit(interaction: discord.Interaction,
                            name: Optional[str]=None,
                            colour: Optional[str] = None,
                            emoji: Optional[str] = None,
                            image: Optional[discord.Attachment] = None
                            ):
    await interaction.response.defer(ephemeral=True)
    server_info = servers.find_one_and_update(
        {"_id": str(interaction.guild.id)},
        {"$setOnInsert": {"_id": str(interaction.guild.id)}},
        upsert=True,
        return_document=True
    )
    custom_roles = server_info.get("custom_roles", {})
    role_id = next((r for r, d in custom_roles.items() if d.get("owner") == str(interaction.user.id)), None)
    if not role_id:
        await interaction.followup.send("You do not have a custom role.")
        return
    role = interaction.guild.get_role(int(role_id))
    if not role:
        await interaction.followup.send("Your custom role no longer exists.")
        return
    if not name and not colour and not emoji and not image:
        await interaction.followup.send("Specify at least one change.")
    bot_member = interaction.guild.me
    if role.position >= bot_member.top_role.position:
        await interaction.followup.send(
            "Missing permissions. Check if KAFU’s highest role is above the role you are trying to edit.",
            ephemeral=True)
        return
    if role.managed:
        await interaction.followup.send("KAFU cannot edit integration-managed roles.", ephemeral=True)
        return
    if name:
        await role.edit(name=name)
    if colour:
        try: await role.edit(colour=discord.Colour(int(colour.strip("#"), 16)))
        except Exception: await interaction.followup.send("Invalid HEX code.", ephemeral=True)
    # role icon
    if image:
        data = await image.read()
        try: await role.edit(display_icon=data)
        except Exception:
            await interaction.followup.send("An error occured while uploading role icon.", ephemeral=True)
    if emoji:
        match = re.search(r"<a?:\w+:(\d+)>", emoji or "")
        if not match:
            await interaction.followup.send("Invalid custom emoji format.", ephemeral=True)
        if match:
            emoji_id = match.group(1)
            is_animated = emoji.startswith("<a:")
            ext = "gif" if is_animated else "png"
            url = f"https://cdn.discordapp.com/emojis/{emoji_id}.{ext}"
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as resp:
                    if resp.status != 200:
                        await interaction.followup.send("Failed to fetch emoji.", ephemeral=True)
                    else:
                        data = await resp.read()
                        try:
                            await role.edit(display_icon=data)
                        except Exception:
                            await interaction.followup.send("An error occured while uploading role icon.", ephemeral=True)

@customrole.command(name="create", description="Create a custom role.")
@app_commands.default_permissions(manage_roles=True)
async def customrole_create(interaction: discord.Interaction,
    owner: discord.Member,
    name: str,
    duration: Optional[str] = None,  # seconds
    booster: Optional[bool] = False,
    colour: Optional[str] = None,
    emoji: Optional[str] = None,
    image: Optional[discord.Attachment] = None
):
    await interaction.response.defer(ephemeral=True)
    server_info = servers.find_one_and_update(
        {"_id": str(interaction.guild.id)},
        {"$setOnInsert": {"_id": str(interaction.guild.id)}},
        upsert=True,
        return_document=True
    )
    custom_roles = server_info.get("custom_roles", {})
    for role_id, data in custom_roles.items():
        if data["owner"] == str(owner.id):
            role = interaction.guild.get_role(int(role_id))
            if role:
                await interaction.followup.send("User already has a custom role.", ephemeral=True)
                return
    # create role
    role = await interaction.guild.create_role(
        name=name,
        colour=discord.Colour(int(colour.strip("#"), 16)) if colour else discord.Colour.default()
    )
    # move role under bot
    bot_top = interaction.guild.me.top_role
    await interaction.guild.edit_role_positions({role: bot_top.position - 1})
    # role icon
    if image:
        data = await image.read()
        try: await role.edit(display_icon=data)
        except Exception:
            await interaction.followup.send("An error occured while uploading role icon.", ephemeral=True)
    if emoji:
        match = re.search(r"<a?:\w+:(\d+)>", emoji or "")
        if not match:
            await interaction.followup.send("Invalid custom emoji format.", ephemeral=True)
        if match:
            emoji_id = match.group(1)
            is_animated = emoji.startswith("<a:")
            ext = "gif" if is_animated else "png"
            url = f"https://cdn.discordapp.com/emojis/{emoji_id}.{ext}"
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as resp:
                    if resp.status != 200:
                        await interaction.followup.send("Failed to fetch emoji.", ephemeral=True)
                    else:
                        data = await resp.read()
                        try:
                            await role.edit(display_icon=data)
                        except Exception:
                            await interaction.followup.send("An error occured while uploading role icon.", ephemeral=True)
    # assign
    await owner.add_roles(role)
    # expiry
    if booster:
        expires_at = None
        role_type = "booster"
    else:
        duration = parse_duration(duration) if duration else None
        expires_at = int(time.time()) + duration if duration else None
        role_type = "time"
    servers.update_one(
        {"_id": str(interaction.guild.id)},
        {
            "$set": {
                f"custom_roles.{role.id}": {
                    "owner": str(owner.id),
                    "expires_at": expires_at,
                    "type": role_type
                }
            }
        },
        upsert=True
    )
    await interaction.followup.send(f"Custom role {role.mention} created for {owner.mention}")

@customrole.command(name="delete", description="Delete a custom role.")
async def customrole_delete(interaction: discord.Interaction, role: discord.Role):
    await interaction.response.defer(ephemeral=True)
    server_info = servers.find_one_and_update(
        {"_id": str(interaction.guild.id)},
        {"$setOnInsert": {"_id": str(interaction.guild.id)}},
        upsert=True,
        return_document=True
    )
    bot_member = interaction.guild.me
    if role:
        if role.managed:
            await interaction.followup.send("Cannot delete integration-managed role.")
        elif role.position >= bot_member.top_role.position:
            await interaction.followup.send("Missing permissions. Check if KAFU’s highest role is above the role you are trying to delete.")
        else:
            try:
                await role.delete(reason="Custom role deleted")
            except discord.Forbidden:
                await interaction.followup.send("Missing permissions to delete role.")
    if str(role.id) in server_info.get("custom_roles", {}):
        servers.update_one(
            {"_id": str(interaction.guild.id)},
            {"$unset": {f"custom_roles.{role.id}": ""}}
        )
    await interaction.followup.send(f"Custom role deleted.")

@customrole.command(name="add", description="Add an existing role to custom roles.")
@app_commands.default_permissions(manage_roles=True)
async def customrole_add(
    interaction: discord.Interaction,
    role: discord.Role,
    owner: discord.Member,
    duration: Optional[str] = None,
    booster: Optional[bool] = False
):
    await interaction.response.defer(ephemeral=True)
    server_info = servers.find_one_and_update(
        {"_id": str(interaction.guild.id)},
        {"$setOnInsert": {"_id": str(interaction.guild.id)}},
        upsert=True,
        return_document=True
    )
    custom_roles = server_info.get("custom_roles", {})
    for role_id, data in custom_roles.items():
        if data["owner"] == str(owner.id):
            role = interaction.guild.get_role(int(role_id))
            if role:
                await interaction.followup.send("User already has a custom role.", ephemeral=True)
                return
    bot_top = interaction.guild.me.top_role
    try: await interaction.guild.edit_role_positions({role: bot_top.position - 1})
    except discord.Forbidden: pass
    duration = parse_duration(duration) if duration else None
    expires_at = None if booster else int(time.time()) + duration if duration else None
    servers.update_one(
        {"_id": str(interaction.guild.id)},
        {
            "$set": {
                f"custom_roles.{role.id}": {
                    "owner": str(owner.id),
                    "expires_at": expires_at,
                    "type": "booster" if booster else "time"
                }
            }
        },
        upsert=True
    )
    await interaction.followup.send("Custom role added.")

@customrole.command(name="remove", description="Remove a role from custom roles.")
@app_commands.default_permissions(manage_roles=True)
async def customrole_remove(interaction: discord.Interaction, role: discord.Role):
    await interaction.response.defer(ephemeral=True)
    server_info = servers.find_one_and_update(
        {"_id": str(interaction.guild.id)},
        {"$setOnInsert": {"_id": str(interaction.guild.id)}},
        upsert=True,
        return_document=True
    )
    if str(role.id) not in server_info.get("custom_roles", {}):
        await interaction.followup.send("This role is not registered as a custom role.")
        return
    servers.update_one(
        {"_id": str(interaction.guild.id)},
        {"$unset": {f"custom_roles.{role.id}": ""}}
    )
    await interaction.followup.send(f"{role.mention} removed from database.")

@customrole.command(name="setexpiry", description="Set expiry for an existing custom role.")
@app_commands.default_permissions(manage_roles=True)
async def customrole_setexpiry(
    interaction: discord.Interaction,
    role: discord.Role,
    duration: Optional[str] = None,
    booster: Optional[bool] = False
):
    await interaction.response.defer(ephemeral=True)
    server_info = servers.find_one_and_update(
        {"_id": str(interaction.guild.id)},
        {"$setOnInsert": {"_id": str(interaction.guild.id)}},
        upsert=True,
        return_document=True
    )
    custom_roles = server_info.get("custom_roles", {})
    for role_id, data in custom_roles.items():
        role = interaction.guild.get_role(int(role_id))
        if not role:
            await interaction.followup.send("Custom role no longer exists.", ephemeral=True)
            return
    duration = parse_duration(duration) if duration else None
    expires_at = None if booster else int(time.time()) + duration if duration else None
    servers.update_one(
        {"_id": str(interaction.guild.id)},
        {
            "$set": {
            f"custom_roles.{role.id}.expires_at": expires_at,
            f"custom_roles.{role.id}.type": "booster" if booster else "time"
        }}, upsert=True)
    await interaction.followup.send("Custom role updated.")

role = app_commands.Group(name="role", description="Manage roles.")
bot.tree.add_command(role)

@role.command(name="massadd", description="Adds a role to multiple users.")
@app_commands.describe(role="Role to add", users="Users or IDs (separate with a space)")
@app_commands.default_permissions(manage_roles=True)
async def role_massadd(interaction: discord.Interaction, role: discord.Role, users: str):
    await interaction.response.defer()
    guild = interaction.guild
    bot_member = guild.me
    if role.position >= bot_member.top_role.position:
        await interaction.followup.send("Missing permissions. Check if KAFU’s highest role is above the role you are trying to assign.")
        return
    ids = re.findall(r"\d+", users)
    if not ids:
        await interaction.followup.send("No valid users provided.")
        return
    success = 0
    failed = 0
    failed_ids = []
    for uid in ids:
        member = guild.get_member(int(uid))
        if not member:
            failed += 1
            failed_ids.append(uid)
            continue
        if member.bot:
            failed += 1
            failed_ids.append(uid)
            continue
        try:
            await member.add_roles(role)
            success += 1
        except discord.Forbidden:
            failed += 1
            failed_ids.append(uid)
        except Exception:
            failed += 1
            failed_ids.append(uid)
    await interaction.followup.send(f"Added {role.mention} to **{success}** users. Failed: `{"` `".join(failed_ids)}`" if failed_ids else f"Added {role.mention} to **{success}** users.")

@bot.tree.command(name="ban", description="Bans a user.")
@app_commands.describe(user="User to ban", reason="Reason for ban")
async def ban(interaction: discord.Interaction, user: str, reason: Optional[str], image1: Optional[discord.Attachment], image2: Optional[discord.Attachment], image3: Optional[discord.Attachment], image4: Optional[discord.Attachment], image5: Optional[discord.Attachment], image6: Optional[discord.Attachment], image7: Optional[discord.Attachment], image8: Optional[discord.Attachment], image9: Optional[discord.Attachment], image10: Optional[discord.Attachment]):
    await interaction.response.defer(ephemeral=True)
    try:
        user = await bot.fetch_user(int(user.strip("<@>")))
    except ValueError:
        await interaction.followup.send("Please provide a valid user or user ID.", ephemeral=True)
        return
    except discord.NotFound:
        await interaction.followup.send("User not found.", ephemeral=True)
        return
    except discord.HTTPException:
        await interaction.followup.send("An error occurred while fetching the user.", ephemeral=True)
        return
    if user == interaction.user:
        await interaction.followup.send("You cannot ban yourself!", ephemeral=True)
        return
    try: member = await interaction.guild.fetch_member(user.id)
    except discord.NotFound: pass
    else:
        if member and interaction.user.top_role <= member.top_role:
            await interaction.followup.send("You cannot ban a user with an equal or higher role than yourself.",
                                                ephemeral=True)
            return
    if reason is None:
        reason = "No reason specified."
    #
    if interaction.user.guild_permissions.ban_members:
        await interaction.followup.send(
            embed=discord.Embed(description=f'{user.mention} `{user.id}` has been banned. Reason: {reason}'))
        try:
            await user.send(f"You have been banned from {interaction.guild.name} for the following reason: {reason}")
        except discord.Forbidden:
            pass
        await interaction.guild.ban(user, reason=reason)
        guild_id = interaction.guild.id
        server_query = {"_id": str(guild_id)}
        server_info = servers.find_one(server_query)
        if server_info:
            if not server_info.get("bans_warns_channel"):
                await interaction.followup.send("**bans warns channel** has not been set up for this server.")
                return
            bans_warns_channel = server_info.get("bans_warns_channel")
            bans_warns_channel = bot.get_channel(int(bans_warns_channel.strip("<#>")))
            try:
                images = [img for img in [image1, image2, image3, image4, image5, image6, image7, image8, image9, image10] if
                          img is not None]
                files_to_send = []
                async with aiohttp.ClientSession() as session:
                    for img in images:
                        if img.content_type and img.content_type.startswith('image/'):
                            async with session.get(img.url) as resp:
                                if resp.status == 200:
                                    data = io.BytesIO(await resp.read())
                                    files_to_send.append(discord.File(data, filename=img.filename))
                if files_to_send:
                    await bans_warns_channel.send(
                        content=f"**Ban**\nㆍ　User ID: {user.id}\nㆍ　Reason: {reason}\nㆍ　Banned by: {interaction.user.id}\nㆍ　Proof:",
                        files=files_to_send)
                else:
                    await bans_warns_channel.send(
                        content=f"**Ban**\nㆍ　User ID: {user.id}\nㆍ　Reason: {reason}\nㆍ　Banned by: {interaction.user.id}")
            except Exception:
                await bans_warns_channel.send(
                    content=f"**Ban**\nㆍ　User ID: {user.id}\nㆍ　Reason: {reason}\nㆍ　Banned by: {interaction.user.id}")
                await interaction.followup.send(f"Unable to send ban log images.", ephemeral=True)
            try:
                server_info.get("staff").get(str(interaction.user.id))["monthly"] = server_info.get("staff").get(
                    str(interaction.user.id)).get("monthly", 0) + 1
                server_info.get("staff").get(str(interaction.user.id))["alltime"] = server_info.get("staff").get(
                    str(interaction.user.id)).get("alltime", 0) + 1
            except KeyError:
                await interaction.followup.send(f"Unable to add staff credits to {interaction.user.mention}.", ephemeral=True)
            servers.replace_one(server_query, server_info)
    else:
        guild_id = interaction.guild.id
        server_query = {"_id": str(guild_id)}
        server_info = servers.find_one_and_update(
            {"_id": str(interaction.guild.id)},
            {"$setOnInsert": {"_id": str(interaction.guild.id)}},
            upsert=True,
            return_document=True
        )
        if not server_info.get("staff_role"):
            await interaction.followup.send("**staff role** has not been set up for this server.", ephemeral=True)
            return
        if not server_info.get("bans_warns_channel"):
            await interaction.followup.send("**bans warns channel** has not been set up for this server.", ephemeral=True)
            return
        staff_role = server_info.get("staff_role")
        ban_perms = server_info.get("ban_perms")
        bans_warns_channel = server_info.get("bans_warns_channel")
        server_info.setdefault("bans_warns_req", {})
        if get(interaction.user.guild.roles, id=int(staff_role.strip("<@&>"))) in interaction.user.roles:
            if str(user.id) in server_info["bans_warns_req"]:
                await interaction.followup.send(f"There already exists a ban/unban request on `{user.id}`: [Jump]({server_info["bans_warns_req"][str(user.id)][2]}).")
            else:
                try:
                    images = [img for img in
                              [image1, image2, image3, image4, image5, image6, image7, image8, image9, image10] if
                              img is not None]
                    files_to_send = []
                    async with aiohttp.ClientSession() as session:
                        for img in images:
                            if img.content_type and img.content_type.startswith('image/'):
                                async with session.get(img.url) as resp:
                                    if resp.status == 200:
                                        data = io.BytesIO(await resp.read())
                                        files_to_send.append(discord.File(data, filename=img.filename))
                    if files_to_send:
                        if ban_perms:
                            ban_req = await bot.get_channel(int(bans_warns_channel.strip("<#>"))).send(
                                content=f"{ban_perms}\n**Ban Request**\nㆍ　User ID: {user.id}\nㆍ　Reason: {reason}\nㆍ　Requested by: {interaction.user.id}\nㆍ　Proof:",
                                files=files_to_send, view=BanReqView())
                        else:
                            ban_req = await bot.get_channel(int(bans_warns_channel.strip("<#>"))).send(
                                content=f"**Ban Request**\nㆍ　User ID: {user.id}\nㆍ　Reason: {reason}\nㆍ　Requested by: {interaction.user.id}\nㆍ　Proof:",
                                files=files_to_send, view=BanReqView())
                    else:
                        if ban_perms:
                            ban_req = await bot.get_channel(int(bans_warns_channel.strip("<#>"))).send(
                                content=f"{ban_perms}\n**Ban Request**\nㆍ　User ID: {user.id}\nㆍ　Reason: {reason}\nㆍ　Requested by: {interaction.user.id}\nㆍ　Proof:",
                                view=BanReqView())
                        else:
                            ban_req = await bot.get_channel(int(bans_warns_channel.strip("<#>"))).send(
                                content=f"**Ban Request**\nㆍ　User ID: {user.id}\nㆍ　Reason: {reason}\nㆍ　Requested by: {interaction.user.id}\nㆍ　Proof:",
                                view=BanReqView())
                except Exception:
                    if ban_perms:
                        ban_req = await bot.get_channel(int(bans_warns_channel.strip("<#>"))).send(
                            content=f"{ban_perms}\n**Ban Request**\nㆍ　User ID: {user.id}\nㆍ　Reason: {reason}\nㆍ　Requested by: {interaction.user.id}\nㆍ　Proof:",
                            view=BanReqView())
                    else:
                        ban_req = await bot.get_channel(int(bans_warns_channel.strip("<#>"))).send(
                            content=f"**Ban Request**\nㆍ　User ID: {user.id}\nㆍ　Reason: {reason}\nㆍ　Requested by: {interaction.user.id}\nㆍ　Proof:",
                            view=BanReqView())
                    await interaction.followup.send(f"Unable to send ban log images.", ephemeral=True)
                await interaction.followup.send(f"A ban request has been sent: [Jump]({ban_req.jump_url})",
                                                        ephemeral=True)
                server_info["bans_warns_req"][str(user.id)] = [reason, str(interaction.user.id), str(ban_req.jump_url)]
                server_info["bans_warns_req"][str(ban_req.id)] = str(user.id)
                servers.replace_one(server_query, server_info)
@ban.error
async def ban_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    await interaction.followup.send(f"An error occurred: {error}", ephemeral=True)

class BanReqView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
    @discord.ui.button(label="Accept", style=discord.ButtonStyle.green, custom_id="accept")
    async def accept_button(self, interaction, button):
        guild_id = interaction.guild.id
        server_query = {"_id": str(guild_id)}
        server_info = servers.find_one(server_query)
        if server_info:
            if interaction.user.guild_permissions.ban_members:
                user_id = server_info["bans_warns_req"][str(interaction.message.id)]
                reason = server_info["bans_warns_req"][user_id][0]
                requested_by = server_info["bans_warns_req"][user_id][1]
                user = await bot.fetch_user(int(user_id.strip("<@>")))
                try:
                    await user.send(
                        f"You have been banned from {interaction.guild.name} for the following reason: {reason}")
                except discord.Forbidden:
                    pass
                await interaction.guild.ban(user, reason=reason)
                await interaction.response.edit_message(
                    content=f"**Ban Accepted**\nㆍ　User ID: {user_id}\nㆍ　Reason: {reason}\nㆍ　Requested by: <@{requested_by}>\nㆍ　Accepted by: {interaction.user.mention}\nㆍ　Proof:",
                    view=None)
                server_info["bans_warns_req"].pop(str(interaction.message.id))
                server_info["bans_warns_req"].pop(str(user_id))
                await interaction.followup.send(f"Ban request accepted.", ephemeral=True)
                try:
                    server_info.get("staff").get(requested_by)["monthly"] = server_info.get("staff").get(requested_by).get(
                        "monthly", 0) + 1
                    server_info.get("staff").get(requested_by)["alltime"] = server_info.get("staff").get(requested_by).get(
                        "alltime", 0) + 1
                except KeyError:
                    await interaction.followup.send(f"Unable to add staff credits to <@{requested_by}>.", ephemeral=True)
                try:
                    server_info.get("staff").get(str(interaction.user.id))["monthly"] = server_info.get("staff").get(
                        str(interaction.user.id)).get("monthly", 0) + 1
                    server_info.get("staff").get(str(interaction.user.id))["alltime"] = server_info.get("staff").get(
                        str(interaction.user.id)).get("alltime", 0) + 1
                except KeyError:
                    await interaction.followup.send(f"Unable to add staff credits to {interaction.user.mention}.", ephemeral=True)
                servers.replace_one(server_query, server_info)

    @discord.ui.button(label="Reject", style=discord.ButtonStyle.red, custom_id="reject")
    async def reject_button(self, interaction, button):
        guild_id = interaction.guild.id
        server_query = {"_id": str(guild_id)}
        server_info = servers.find_one(server_query)
        if server_info:
            if interaction.user.guild_permissions.ban_members:
                user_id = server_info["bans_warns_req"][str(interaction.message.id)]
                reason = server_info["bans_warns_req"][user_id][0]
                requested_by = server_info["bans_warns_req"][user_id][1]
                await interaction.response.edit_message(
                    content=f"> **Ban Rejected**\n> ㆍ　User ID: {user_id}\n> ㆍ　Reason: {reason}\n> ㆍ　Requested by: <@{requested_by}>\n> ㆍ　Rejected by: {interaction.user.mention}\n> ㆍ　Proof:",
                    view=None)
                server_info["bans_warns_req"].pop(str(interaction.message.id))
                server_info["bans_warns_req"].pop(str(user_id))
                servers.replace_one(server_query, server_info)
                await interaction.followup.send(f"Ban request rejected.", ephemeral=True)

@bot.tree.command(name="unban", description="Unbans a user.")
@app_commands.describe(user="User to unban", reason="Reason for unban")
async def unban(interaction: discord.Interaction, user: str, reason: Optional[str], image1: Optional[discord.Attachment], image2: Optional[discord.Attachment], image3: Optional[discord.Attachment], image4: Optional[discord.Attachment], image5: Optional[discord.Attachment], image6: Optional[discord.Attachment], image7: Optional[discord.Attachment], image8: Optional[discord.Attachment], image9: Optional[discord.Attachment], image10: Optional[discord.Attachment]):
    await interaction.response.defer(ephemeral=True)
    try:
        user = await bot.fetch_user(int(user.strip("<@>")))
    except ValueError:
        await interaction.followup.send("Please provide a valid user or user ID.", ephemeral=True)
        return
    except discord.NotFound:
        await interaction.followup.send("User not found.", ephemeral=True)
        return
    except discord.HTTPException:
        await interaction.followup.send("An error occurred while fetching the user.", ephemeral=True)
        return
    if user == interaction.user:
        await interaction.followup.send("You cannot unban yourself!", ephemeral=True)
        return
    if reason is None:
        reason = "No reason specified"
    banned_users = []
    async for ban_entry in interaction.guild.bans():
        banned_users.append(ban_entry.user)
    if user not in banned_users:
        await interaction.response.send_message(f"{user.mention} is not currently banned.", ephemeral=True)
        return
    if interaction.user.guild_permissions.ban_members:
        await interaction.guild.unban(user, reason=reason)
        await interaction.followup.send(embed=discord.Embed(description=
            f"Successfully unbanned {user.mention} `{user.id}`. Reason: {reason}"))
        try:
            await user.send(f"You have been unbanned from {interaction.guild.name} for the following reason: {reason}")
        except discord.Forbidden:
            pass
        guild_id = interaction.guild.id
        server_query = {"_id": str(guild_id)}
        server_info = servers.find_one(server_query)
        if server_info:
            if not server_info.get("bans_warns_channel"):
                await interaction.followup.send("**bans warns channel** has not been set up for this server.")
                return
            bans_warns_channel = server_info.get("bans_warns_channel")
            bans_warns_channel = bot.get_channel(int(bans_warns_channel.strip("<#>")))
            try:
                images = [img for img in
                          [image1, image2, image3, image4, image5, image6, image7, image8, image9, image10] if
                          img is not None]
                files_to_send = []
                async with aiohttp.ClientSession() as session:
                    for img in images:
                        if img.content_type and img.content_type.startswith('image/'):
                            async with session.get(img.url) as resp:
                                if resp.status == 200:
                                    data = io.BytesIO(await resp.read())
                                    files_to_send.append(discord.File(data, filename=img.filename))
                if files_to_send:
                    await bans_warns_channel.send(
                        content=f"**Unban**\nㆍ　User ID: {user.id}\nㆍ　Reason: {reason}\nㆍ　Unbanned by: {interaction.user.id}\nㆍ　Proof:",
                        files=files_to_send)
                else:
                    await bans_warns_channel.send(
                        content=f"**Unban**\nㆍ　User ID: {user.id}\nㆍ　Reason: {reason}\nㆍ　Unbanned by: {interaction.user.id}")
            except Exception:
                await bans_warns_channel.send(
                    content=f"**Unban**\nㆍ　User ID: {user.id}\nㆍ　Reason: {reason}\nㆍ　Unbanned by: {interaction.user.id}")
                await interaction.followup.send(f"Unable to send ban log images.", ephemeral=True)
            try:
                server_info.get("staff").get(str(interaction.user.id))["monthly"] = server_info.get("staff").get(
                    str(interaction.user.id)).get("monthly", 0) + 1
                server_info.get("staff").get(str(interaction.user.id))["alltime"] = server_info.get("staff").get(
                    str(interaction.user.id)).get("alltime", 0) + 1
            except KeyError:
                await interaction.followup.send(f"Unable to add staff credits to {interaction.user.mention}.",
                                                ephemeral=True)
            servers.replace_one(server_query, server_info)
    else:
        guild_id = interaction.guild.id
        server_query = {"_id": str(guild_id)}
        server_info = servers.find_one_and_update(
            {"_id": str(interaction.guild.id)},
            {"$setOnInsert": {"_id": str(interaction.guild.id)}},
            upsert=True,
            return_document=True
        )
        if not server_info.get("staff_role"):
            await interaction.followup.send("**staff role** has not been set up for this server.", ephemeral=True)
            return
        if not server_info.get("bans_warns_channel"):
            await interaction.followup.send("**bans warns channel** has not been set up for this server.",
                                            ephemeral=True)
            return
        staff_role = server_info.get("staff_role")
        ban_perms = server_info.get("ban_perms")
        bans_warns_channel = server_info.get("bans_warns_channel")
        server_info.setdefault("bans_warns_req", {})
        if get(interaction.user.guild.roles, id=int(staff_role.strip("<@&>"))) in interaction.user.roles:
            if str(user.id) in server_info["bans_warns_req"]:
                await interaction.followup.send(
                    f"There already exists a ban/unban request on `{user.id}`: [Jump]({server_info["bans_warns_req"][str(user.id)][2]}).")
            else:
                try:
                    images = [img for img in
                              [image1, image2, image3, image4, image5, image6, image7, image8, image9, image10] if
                              img is not None]
                    files_to_send = []
                    async with aiohttp.ClientSession() as session:
                        for img in images:
                            if img.content_type and img.content_type.startswith('image/'):
                                async with session.get(img.url) as resp:
                                    if resp.status == 200:
                                        data = io.BytesIO(await resp.read())
                                        files_to_send.append(discord.File(data, filename=img.filename))
                    if files_to_send:
                        if ban_perms:
                            ban_req = await bot.get_channel(int(bans_warns_channel.strip("<#>"))).send(
                                content=f"{ban_perms}\n**Unban Request**\nㆍ　User ID: {user.id}\nㆍ　Reason: {reason}\nㆍ　Requested by: {interaction.user.id}\nㆍ　Proof:",
                                files=files_to_send, view=UnbanReqView())
                        else:
                            ban_req = await bot.get_channel(int(bans_warns_channel.strip("<#>"))).send(
                                content=f"**Unban Request**\nㆍ　User ID: {user.id}\nㆍ　Reason: {reason}\nㆍ　Requested by: {interaction.user.id}\nㆍ　Proof:",
                                files=files_to_send, view=UnbanReqView())
                    else:
                        if ban_perms:
                            ban_req = await bot.get_channel(int(bans_warns_channel.strip("<#>"))).send(
                                content=f"{ban_perms}\n**Unban Request**\nㆍ　User ID: {user.id}\nㆍ　Reason: {reason}\nㆍ　Requested by: {interaction.user.id}\nㆍ　Proof:",
                                view=UnbanReqView())
                        else:
                            ban_req = await bot.get_channel(int(bans_warns_channel.strip("<#>"))).send(
                                content=f"**Unban Request**\nㆍ　User ID: {user.id}\nㆍ　Reason: {reason}\nㆍ　Requested by: {interaction.user.id}\nㆍ　Proof:",
                                view=UnbanReqView())
                except Exception:
                    if ban_perms:
                        ban_req = await bot.get_channel(int(bans_warns_channel.strip("<#>"))).send(
                            content=f"{ban_perms}\n**Unban Request**\nㆍ　User ID: {user.id}\nㆍ　Reason: {reason}\nㆍ　Requested by: {interaction.user.id}\nㆍ　Proof:",
                            view=BanReqView())
                    else:
                        ban_req = await bot.get_channel(int(bans_warns_channel.strip("<#>"))).send(
                            content=f"**Unban Request**\nㆍ　User ID: {user.id}\nㆍ　Reason: {reason}\nㆍ　Requested by: {interaction.user.id}\nㆍ　Proof:",
                            view=BanReqView())
                    await interaction.followup.send(f"Unable to send unban log images.", ephemeral=True)
                await interaction.followup.send(f"An unban request has been sent: [Jump]({ban_req.jump_url})",
                                                ephemeral=True)
                server_info["bans_warns_req"][str(user.id)] = [reason, str(interaction.user.id),
                                                               str(ban_req.jump_url)]
                server_info["bans_warns_req"][str(ban_req.id)] = str(user.id)
                servers.replace_one(server_query, server_info)

@unban.error
async def unban_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    await interaction.followup.send(f"An error occurred: {error}", ephemeral=True)

class UnbanReqView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
    @discord.ui.button(label="Accept", style=discord.ButtonStyle.green, custom_id="accept")
    async def accept_button(self, interaction, button):
        guild_id = interaction.guild.id
        server_query = {"_id": str(guild_id)}
        server_info = servers.find_one(server_query)
        if server_info:
            if interaction.user.guild_permissions.ban_members:
                user_id = server_info["bans_warns_req"][str(interaction.message.id)]
                reason = server_info["bans_warns_req"][user_id][0]
                requested_by = server_info["bans_warns_req"][user_id][1]
                user = await bot.fetch_user(int(user_id.strip("<@>")))
                await interaction.guild.unban(user, reason=reason)
                await interaction.followup.send(embed=discord.Embed(description=
                                                                    f"Successfully unbanned {user.mention} `{user.id}`. Reason: {reason}"))
                try:
                    await user.send(
                        f"You have been unbanned from {interaction.guild.name} for the following reason: {reason}")
                except discord.Forbidden:
                    pass
                await interaction.response.edit_message(
                    content=f"**Unban Accepted**\nㆍ　User ID: {user_id}\nㆍ　Reason: {reason}\nㆍ　Requested by: <@{requested_by}>\nㆍ　Accepted by: {interaction.user.mention}\nㆍ　Proof:",
                    view=None)
                server_info["bans_warns_req"].pop(str(interaction.message.id))
                server_info["bans_warns_req"].pop(str(user_id))
                await interaction.followup.send(f"Unban request accepted.", ephemeral=True)
                try:
                    server_info.get("staff").get(requested_by)["monthly"] = server_info.get("staff").get(requested_by).get(
                        "monthly", 0) + 1
                    server_info.get("staff").get(requested_by)["alltime"] = server_info.get("staff").get(requested_by).get(
                        "alltime", 0) + 1
                except KeyError:
                    await interaction.followup.send(f"Unable to add staff credits to <@{requested_by}>.", ephemeral=True)
                try:
                    server_info.get("staff").get(str(interaction.user.id))["monthly"] = server_info.get("staff").get(
                        str(interaction.user.id)).get("monthly", 0) + 1
                    server_info.get("staff").get(str(interaction.user.id))["alltime"] = server_info.get("staff").get(
                        str(interaction.user.id)).get("alltime", 0) + 1
                except KeyError:
                    await interaction.followup.send(f"Unable to add staff credits to {interaction.user.mention}.", ephemeral=True)
                servers.replace_one(server_query, server_info)
    @discord.ui.button(label="Reject", style=discord.ButtonStyle.red, custom_id="reject")
    async def reject_button(self, interaction, button):
        guild_id = interaction.guild.id
        server_query = {"_id": str(guild_id)}
        server_info = servers.find_one(server_query)
        if server_info:
            if interaction.user.guild_permissions.ban_members:
                user_id = server_info["bans_warns_req"][str(interaction.message.id)]
                reason = server_info["bans_warns_req"][user_id][0]
                requested_by = server_info["bans_warns_req"][user_id][1]
                await interaction.response.edit_message(
                    content=f"> **Unban Rejected**\n> ㆍ　User ID: {user_id}\n> ㆍ　Reason: {reason}\n> ㆍ　Requested by: <@{requested_by}>\n> ㆍ　Rejected by: {interaction.user.mention}\n> ㆍ　Proof:",
                    view=None)
                server_info["bans_warns_req"].pop(str(interaction.message.id))
                server_info["bans_warns_req"].pop(str(user_id))
                servers.replace_one(server_query, server_info)
                await interaction.followup.send(f"Unban request rejected.", ephemeral=True)

#

@bot.tree.command(name="panel", description="Sends a ticket panel.")
@app_commands.checks.has_permissions(administrator=True)
async def panel(interaction: discord.Interaction, type: Optional[str]):
    guild_id = interaction.guild.id
    if guild_id == TRI_Archive:
        await interaction.channel.send(embed=discord.Embed(colour=0xffffff, description="""
    ## 　　<:2paperclip:1449650494044639335>　　┈　　open ticket　　୭
    　<:00_reply:1448474301673115748>　provide __uncropped__ & **unedited** proofs
    　<:00_reply:1448474301673115748>　fake proofs / disrespect = **ban**
    　<:00_reply:1448474301673115748>　**do not open** for appeals on bans
    -# _ _　✦ 　not following rules / ghosting = close
                """), view=TRITicketView())
        await interaction.response.send_message("Panel has been sent.", ephemeral=True)
    else:
        """guild_id = interaction.guild.id
        server_query = {"_id": str(guild_id)}
        server_info = servers.find_one_and_update(
            {"_id": str(interaction.guild.id)},
            {"$setOnInsert": {"_id": str(interaction.guild.id)}},
            upsert=True,
            return_document=True
        )"""
        if type == "support":
            pass
        elif type == "services":
            pass

class TranscriptView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)


"""@bot.tree.command(name="whitelist")
@app_commands.describe(server="Server invite")
@app_commands.checks.has_permissions(administrator=True)
async def whitelist(interaction: discord.Interaction, server: str):
    if interaction.user.id == yuelyxia:
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
            server_info = servers.find_one(server_query)
            if server_info:
                await interaction.response.send_message(f"`{guild_id}` is already whitelisted.")
            else:
                server_info = {
                    "_id": str(guild_id),
                }
                servers.insert_one(server_info)
                await interaction.response.send_message(f"`{guild_id}` has been whitelisted.")"""

@bot.tree.command(name="break", description="Toggle staff/mm/pilot break.")
async def break_command(interaction: discord.Interaction, category: Literal["staff", "mm", "pilot"]):
    await interaction.response.defer()
    server_info = servers.find_one_and_update(
        {"_id": str(interaction.guild.id)},
        {"$setOnInsert": {"_id": str(interaction.guild.id)}},
        upsert=True,
        return_document=True
    )
    staff_break = server_info.get("staff_break")
    mm_break = server_info.get("mm_break")
    pilot_break = server_info.get("pilot_break")
    staff_ping = server_info.get("staff_ping")
    mm_ping = server_info.get("mm_ping")
    pilot_ping = server_info.get("pilot_ping")
    uid = str(interaction.user.id)
    if category == "staff":
        if staff_break:
            if uid in server_info.get("staff", {}):
                if get(interaction.user.guild.roles, id=int(staff_break.strip("<@&>"))) in interaction.user.roles:
                    await interaction.user.remove_roles(interaction.guild.get_role(int(staff_break.strip("<@&>"))))
                    if staff_ping: await interaction.user.add_roles(interaction.guild.get_role(int(staff_ping.strip("<@&>"))))
                    await interaction.followup.send(f"You have been unroled **staff break**.")
                else:
                    await interaction.user.add_roles(interaction.guild.get_role(int(staff_break.strip("<@&>"))))
                    if staff_ping: await interaction.user.remove_roles(interaction.guild.get_role(int(staff_ping.strip("<@&>"))))
                    await interaction.followup.send(f"You have been roled **staff break**.")
            else:
                await interaction.followup.send(f"Unauthorised.")
                return
        else:
            await interaction.followup.send("**staff break** has not been set up for this server.")
    if category == "mm":
        if mm_break:
            if uid in server_info.get("mms", {}):
                if get(interaction.user.guild.roles, id=int(mm_break.strip("<@&>"))) in interaction.user.roles:
                    await interaction.user.remove_roles(interaction.guild.get_role(int(mm_break.strip("<@&>"))))
                    if mm_ping: await interaction.user.add_roles(interaction.guild.get_role(int(mm_ping.strip("<@&>"))))
                    await interaction.followup.send(f"You have been unroled **mm break**.")
                else:
                    await interaction.user.add_roles(interaction.guild.get_role(int(mm_break.strip("<@&>"))))
                    if mm_ping: await interaction.user.remove_roles(interaction.guild.get_role(int(mm_ping.strip("<@&>"))))
                    await interaction.followup.send(f"You have been roled **mm break**.")
            else:
                await interaction.followup.send(f"Unauthorised.")
                return
        else:
            await interaction.followup.send("**mm break** has not been set up for this server.")
    if category == "pilot":
        if pilot_break:
            if uid in server_info.get("pilots", {}):
                if get(interaction.user.guild.roles, id=int(pilot_break.strip("<@&>"))) in interaction.user.roles:
                    await interaction.user.remove_roles(interaction.guild.get_role(int(pilot_break.strip("<@&>"))))
                    if pilot_ping: await interaction.user.add_roles(interaction.guild.get_role(int(pilot_ping.strip("<@&>"))))
                    await interaction.followup.send(f"You have been unroled **pilot break**.")
                else:
                    await interaction.user.add_roles(interaction.guild.get_role(int(pilot_break.strip("<@&>"))))
                    if pilot_ping: await interaction.user.remove_roles(interaction.guild.get_role(int(pilot_ping.strip("<@&>"))))
                    await interaction.followup.send(f"You have been roled **pilot break**.")
            else:
                await interaction.followup.send(f"Unauthorised.")
                return
        else:
            await interaction.followup.send("**staff break** has not been set up for this server.")

def is_int(value):
    try:
        int(value)
        return True
    except (ValueError, TypeError):
        return False

appoint = app_commands.Group(name="appoint", description="Appoint a staff/mm/pilot.")
bot.tree.add_command(appoint)

@appoint.command(name="staff", description="Appoint a staff.")
@app_commands.describe(user="User/role to appoint as staff", role="Staff role to assign.")
async def appoint_staff(interaction: discord.Interaction, user: str, role: Optional[discord.Role]=None):
    await interaction.response.defer(ephemeral=True)
    guild_id = interaction.guild.id
    server_query = {"_id": str(guild_id)}
    server_info = servers.find_one_and_update(
        {"_id": str(interaction.guild.id)},
        {"$setOnInsert": {"_id": str(interaction.guild.id)}},
        upsert=True,
        return_document=True
    )
    staff_role = server_info.get("staff_role")
    if staff_role and not get(interaction.user.guild.roles, id=int(staff_role.strip("<@&>"))) in interaction.user.roles:
        await interaction.followup.send(f"Unauthorised.", ephemeral=True)
        return
    try:
        user = await bot.fetch_user(int(user.strip("<@>")))
    except Exception:
        try: user_role = interaction.guild.get_role(int(user.strip("<@&>")))
        except Exception:
            await interaction.followup.send(f"Please enter a valid user ID.", ephemeral=True)
        else:
            if not interaction.user.guild_permissions.manage_roles:
                await interaction.followup.send(f"Unauthorised.", ephemeral=True)
                return
            role_members = user_role.members
            await interaction.followup.send(f"Adding {len(role_members)} users to staff.", ephemeral=True)
            for m in role_members:
                user_id = m.id
                server_info.setdefault("staff", {})
                server_info["staff"].setdefault(str(user_id), {})
                servers.replace_one(server_query, server_info)
                await interaction.followup.send(f"`{user_id}` has been added to staff.")
    else:
        user_id = user.id
        if user_id == interaction.user.id and not interaction.user.guild_permissions.administrator:
            await interaction.followup.send(f"You cannot appoint yourself.", ephemeral=True)
            return
        member = interaction.guild.get_member(int(user_id))
        if not member: return
        if not interaction.user.guild_permissions.manage_roles:
            await interaction.followup.send(f"Unauthorised.", ephemeral=True)
            return
        server_info.setdefault("staff", {})
        server_info["staff"].setdefault(str(user_id), {})
        servers.replace_one(server_query, server_info)
        await interaction.followup.send(f"`{user_id}` has been added to staff.")
        staff_role = server_info.get("staff_role")
        if staff_role: await member.add_roles(interaction.guild.get_role(int(staff_role.strip("<@&>"))))
        staff_ping = server_info.get("staff_ping")
        if staff_ping: await member.add_roles(interaction.guild.get_role(int(staff_ping.strip("<@&>"))))
        if role is not None and server_info.get("staff_roles"):
            staff_roles = server_info["staff_roles"].split()
            if str(role.mention) in staff_roles:
                for r in staff_roles:
                    await member.remove_roles(interaction.guild.get_role(int(r.strip("<@&>"))))
                await member.add_roles(role)
                await interaction.followup.send(f"`{user_id}` has been assigned the {role.mention} role.",
                                                ephemeral=True)
        elif role is not None:
            await interaction.followup.send("**staff roles** have not been set up.", ephemeral=True)

@appoint.command(name="mm", description="Appoint a mm.")
@app_commands.describe(user="User/role to appoint as mm", role="mm role to assign.")
async def appoint_mm(interaction: discord.Interaction, user: str, role: Optional[discord.Role]=None):
    await interaction.response.defer(ephemeral=True)
    guild_id = interaction.guild.id
    server_query = {"_id": str(guild_id)}
    server_info = servers.find_one_and_update(
        {"_id": str(interaction.guild.id)},
        {"$setOnInsert": {"_id": str(interaction.guild.id)}},
        upsert=True,
        return_document=True
    )
    staff_role = server_info.get("staff_role")
    if not get(interaction.user.guild.roles, id=int(staff_role.strip("<@&>"))) in interaction.user.roles:
        await interaction.followup.send(f"Unauthorised.", ephemeral=True)
        return
    try:
        user = await bot.fetch_user(int(user.strip("<@>")))
    except Exception:
        try: user_role = interaction.guild.get_role(int(user.strip("<@&>")))
        except Exception:
            await interaction.followup.send(f"Please enter a valid user ID.", ephemeral=True)
        else:
            if not interaction.user.guild_permissions.manage_roles:
                await interaction.followup.send(f"Unauthorised.", ephemeral=True)
                return
            role_members = user_role.members
            await interaction.followup.send(f"Adding {len(role_members)} users to mms.", ephemeral=True)
            for m in role_members:
                user_id = m.id
                server_info.setdefault("mms", {})
                server_info["mms"].setdefault(str(user_id), {})
                servers.replace_one(server_query, server_info)
                await interaction.followup.send(f"`{user_id}` has been added to mms.")
    else:
        user_id = user.id
        if user_id == interaction.user.id and not interaction.user.guild_permissions.administrator:
            await interaction.followup.send(f"You cannot appoint yourself.", ephemeral=True)
            return
        member = interaction.guild.get_member(int(user_id))
        if not member: return
        server_info.setdefault("mms", {})
        server_info["mms"].setdefault(str(user_id), {})
        servers.replace_one(server_query, server_info)
        await interaction.followup.send(f"`{user_id}` has been added to mms.")
        mm_role = server_info.get("mm_role")
        if mm_role: await member.add_roles(interaction.guild.get_role(int(mm_role.strip("<@&>"))))
        mm_ping = server_info.get("mm_ping")
        if mm_ping: await member.add_roles(interaction.guild.get_role(int(mm_ping.strip("<@&>"))))
        if role is not None and server_info.get("mm_roles"):
            mm_roles = server_info["mm_roles"].split()
            if str(role.mention) in mm_roles:
                for r in mm_roles:
                    await member.remove_roles(interaction.guild.get_role(int(r.strip("<@&>"))))
                await member.add_roles(role)
                await interaction.followup.send(f"`{user_id}` has been assigned the {role.mention} role.",
                                                ephemeral=True)
        elif role is not None:
            await interaction.followup.send("**mm roles** have not been set up.", ephemeral=True)

@appoint.command(name="pilot", description="Appoint a pilot.")
@app_commands.describe(user="User/role to appoint as pilot", role="pilot role to assign.")
async def appoint_pilot(interaction: discord.Interaction, user: str, role: Optional[discord.Role]=None):
    await interaction.response.defer(ephemeral=True)
    guild_id = interaction.guild.id
    server_query = {"_id": str(guild_id)}
    server_info = servers.find_one_and_update(
        {"_id": str(interaction.guild.id)},
        {"$setOnInsert": {"_id": str(interaction.guild.id)}},
        upsert=True,
        return_document=True
    )
    staff_role = server_info.get("staff_role")
    if not get(interaction.user.guild.roles, id=int(staff_role.strip("<@&>"))) in interaction.user.roles:
        await interaction.followup.send(f"Unauthorised.", ephemeral=True)
        return
    try:
        user = await bot.fetch_user(int(user.strip("<@>")))
    except Exception:
        try: user_role = interaction.guild.get_role(int(user.strip("<@&>")))
        except Exception:
            await interaction.followup.send(f"Please enter a valid user ID.", ephemeral=True)
        else:
            if not interaction.user.guild_permissions.manage_roles:
                await interaction.followup.send(f"Unauthorised.", ephemeral=True)
                return
            role_members = user_role.members
            await interaction.followup.send(f"Adding {len(role_members)} users to pilots.", ephemeral=True)
            for m in role_members:
                user_id = m.id
                server_info.setdefault("pilots", {})
                server_info["pilots"].setdefault(str(user_id), {})
                servers.replace_one(server_query, server_info)
                await interaction.followup.send(f"`{user_id}` has been added to pilots.")
    else:
        user_id = user.id
        if user_id == interaction.user.id and not interaction.user.guild_permissions.administrator:
            await interaction.followup.send(f"You cannot appoint yourself.", ephemeral=True)
            return
        member = interaction.guild.get_member(int(user_id))
        if not member: return
        server_info.setdefault("pilots", {})
        server_info["pilots"].setdefault(str(user_id), {})
        servers.replace_one(server_query, server_info)
        await interaction.followup.send(f"`{user_id}` has been added to pilots.")
        pilot_role = server_info.get("pilot_role")
        if pilot_role: await member.add_roles(interaction.guild.get_role(int(pilot_role.strip("<@&>"))))
        pilot_ping = server_info.get("pilot_ping")
        if pilot_ping: await member.add_roles(interaction.guild.get_role(int(pilot_ping.strip("<@&>"))))
        if role is not None and server_info.get("pilot_roles"):
            pilot_roles = server_info["pilot_roles"].split()
            if str(role.mention) in pilot_roles:
                for r in pilot_roles:
                    await member.remove_roles(interaction.guild.get_role(int(r.strip("<@&>"))))
                await member.add_roles(role)
                await interaction.followup.send(f"`{user_id}` has been assigned the {role.mention} role.", ephemeral=True)
        elif role is not None:
            await interaction.followup.send("**pilot roles** have not been set up.", ephemeral=True)

@appoint.error
async def appoint_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    original = getattr(error, "original", error)
    if isinstance(original, discord.Forbidden):
        await interaction.followup.send("Missing permissions. Check if KAFU’s highest role is above the role you are trying to assign.", ephemeral=True)
    else:
        await interaction.followup.send(f"An error occurred: {error}", ephemeral=True)

@bot.tree.command(name="dismiss", description="Dismiss staff/mm/pilot.")
@app_commands.describe(user="User to dismiss")
async def dismiss(interaction: discord.Interaction, user: str, category: Literal["staff", "mm", "pilot"]):
    await interaction.response.defer(ephemeral=True)
    guild_id = interaction.guild.id
    server_query = {"_id": str(guild_id)}
    server_info = servers.find_one_and_update(
        {"_id": str(interaction.guild.id)},
        {"$setOnInsert": {"_id": str(interaction.guild.id)}},
        upsert=True,
        return_document=True
    )
    staff_role = server_info.get("staff_role")
    if not get(interaction.user.guild.roles, id=int(staff_role.strip("<@&>"))) in interaction.user.roles:
        await interaction.followup.send(f"Unauthorised.", ephemeral=True)
        return
    try:
        user = await bot.fetch_user(int(user.strip("<@>")))
    except Exception:
        try: user_role = interaction.guild.get_role(int(user.strip("<@&>")))
        except Exception:
            await interaction.followup.send(f"Please enter a valid user ID.", ephemeral=True)
        else:
            if not interaction.user.guild_permissions.manage_roles:
                await interaction.followup.send(f"Unauthorised.", ephemeral=True)
                return
            if category in ["staff", "mm", "pilot"]:
                role_members = user_role.members
                await interaction.followup.send(f"Dismissing {len(role_members)} users from {category}.", ephemeral=True)
                #
                def parse_roles(raw):
                    if not raw:
                        return []
                    return raw.replace("<@&", "").replace(">", "").split()
                staff_roles = parse_roles(server_info.get("staff_roles"))
                staff_roles += parse_roles(server_info.get("staff_role"))
                staff_roles += parse_roles(server_info.get("staff_ping"))
                staff_roles += parse_roles(server_info.get("staff_break"))
                staff_roles += parse_roles(server_info.get("adm_role"))
                staff_roles += parse_roles(server_info.get("ban_perms"))
                mm_roles = parse_roles(server_info.get("mm_roles"))
                mm_roles += parse_roles(server_info.get("mm_role"))
                mm_roles += parse_roles(server_info.get("mm_ping"))
                mm_roles += parse_roles(server_info.get("mm_break"))
                mm_roles += parse_roles(server_info.get("mm_supervisor"))
                mm_roles += parse_roles(server_info.get("mm_trainer"))
                mm_roles += parse_roles(server_info.get("mm_break"))
                pilot_roles = parse_roles(server_info.get("pilot_roles"))
                pilot_roles += parse_roles(server_info.get("pilot_role"))
                pilot_roles += parse_roles(server_info.get("pilot_ping"))
                pilot_roles += parse_roles(server_info.get("pilot_break"))
                pilot_roles += parse_roles(server_info.get("pilot_supervisor"))
                pilot_roles += parse_roles(server_info.get("pilot_trainer"))
                pilot_roles += parse_roles(server_info.get("pilot_break"))
                for m in role_members:
                    uid = str(m.id)
                    if category == "staff":
                        server_info.setdefault("staff", {}).pop(uid, None)
                        roles = staff_roles
                        await interaction.followup.send(f"`{uid}` has been dismissed from staff.")
                        still_staff = servers.find_one({
                            f"staff.{uid}": {"$exists": True}
                        })
                        if not still_staff:
                            timezones.delete_one({"_id": uid})
                    elif category == "mm":
                        server_info.setdefault("mms", {}).pop(uid, None)
                        roles = mm_roles
                        await interaction.followup.send(f"`{uid}` has been dismissed from mms.")
                    elif category == "pilot":
                        server_info.setdefault("pilots", {}).pop(uid, None)
                        roles = pilot_roles
                        await interaction.followup.send(f"`{uid}` has been dismissed from pilots.")
                    # remove roles
                    for role_id in roles:
                        role = interaction.guild.get_role(int(role_id))
                        if role:
                            await m.remove_roles(role)
                servers.replace_one(server_query, server_info)
    else:
        user_id = user.id
        if user_id == interaction.user.id and not interaction.user.guild_permissions.administrator:
            await interaction.followup.send(f"You cannot dismiss yourself.", ephemeral=True)
            return
        member = interaction.guild.get_member(int(user_id))
        if not member: return
        if category in ["staff", "mm", "pilot"]:
            def parse_roles(raw):
                if not raw:
                    return []
                return raw.replace("<@&", "").replace(">", "").split()
            staff_roles = parse_roles(server_info.get("staff_roles"))
            staff_roles += parse_roles(server_info.get("staff_role"))
            staff_roles += parse_roles(server_info.get("staff_ping"))
            staff_roles += parse_roles(server_info.get("staff_break"))
            staff_roles += parse_roles(server_info.get("adm_role"))
            staff_roles += parse_roles(server_info.get("ban_perms"))
            mm_roles = parse_roles(server_info.get("mm_roles"))
            mm_roles += parse_roles(server_info.get("mm_role"))
            mm_roles += parse_roles(server_info.get("mm_ping"))
            mm_roles += parse_roles(server_info.get("mm_break"))
            mm_roles += parse_roles(server_info.get("mm_supervisor"))
            mm_roles += parse_roles(server_info.get("mm_trainer"))
            mm_roles += parse_roles(server_info.get("mm_break"))
            pilot_roles = parse_roles(server_info.get("pilot_roles"))
            pilot_roles += parse_roles(server_info.get("pilot_role"))
            pilot_roles += parse_roles(server_info.get("pilot_ping"))
            pilot_roles += parse_roles(server_info.get("pilot_break"))
            pilot_roles += parse_roles(server_info.get("pilot_supervisor"))
            pilot_roles += parse_roles(server_info.get("pilot_trainer"))
            pilot_roles += parse_roles(server_info.get("pilot_break"))
            if category == "staff":
                if not interaction.user.guild_permissions.manage_roles:
                    await interaction.followup.send(f"Unauthorised.", ephemeral=True)
                    return
                server_info.setdefault("staff", {}).pop(str(user_id), None)
                roles = staff_roles
                await interaction.followup.send(f"`{str(user_id)}` has been dismissed from staff.")
                still_staff = servers.find_one({
                    f"staff.{str(user_id)}": {"$exists": True}
                })
                if not still_staff:
                    timezones.delete_one({"_id": str(user_id)})
            elif category == "mm":
                server_info.setdefault("mms", {}).pop(str(user_id), None)
                roles = mm_roles
                await interaction.followup.send(f"`{str(user_id)}` has been dismissed from mms.")
            elif category == "pilot":
                server_info.setdefault("pilots", {}).pop(str(user_id), None)
                roles = pilot_roles
                await interaction.followup.send(f"`{str(user_id)}` has been dismissed from pilots.")
            # remove roles
            for role_id in roles:
                role = interaction.guild.get_role(int(role_id))
                if role:
                    await member.remove_roles(role)
        servers.replace_one(server_query, server_info)

@dismiss.error
async def dismiss_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    original = getattr(error, "original", error)
    if isinstance(original, discord.Forbidden):
        await interaction.followup.send("Missing permissions. Check if KAFU’s highest role is above the role you are trying to assign.", ephemeral=True)
    else:
        await interaction.followup.send(f"An error occurred: {error}", ephemeral=True)

@bot.tree.command(name="setup", description="Set up KAFU.")
@app_commands.checks.has_permissions(administrator=True)
async def setup(interaction: discord.Interaction, topic: Optional[Literal[
    "bans warns channel", "transcripts channel", "staff lb channel", "services lb channel", "revive ping",
    "staff roles", "staff role", "staff ping", "staff break", "adm role", "ban perms",
    "mm roles", "mm role", "mm ping", "mm supervisor", "mm trainer", "mm break", "mm vouch channel",
    "pilot roles", "pilot role", "pilot ping", "pilot supervisor", "pilot trainer", "pilot break", "pilot vouch channel"
]]=None, input: Optional[str]=None):
    guild_id = interaction.guild.id
    server_query = {"_id": str(guild_id)}
    server_info = servers.find_one_and_update(
        {"_id": str(interaction.guild.id)},
        {"$setOnInsert": {"_id": str(interaction.guild.id)}},
        upsert=True,
        return_document=True
    )
    if topic is None:
        general_embed = discord.Embed(colour=0xffffff)
        general_embed.add_field(name="bans warns channel", value=server_info.get("bans_warns_channel", "unset"), inline=False) #
        general_embed.add_field(name="transcripts channel", value=server_info.get("transcripts_channel", "unset"), inline=False) #
        general_embed.add_field(name="staff lb channel", value=server_info.get("staff_lb_channel", "unset"), inline=False) #
        general_embed.add_field(name="services lb channel", value=server_info.get("services_lb_channel", "unset"), inline=False) #
        general_embed.add_field(name="revive ping", value=server_info.get("services_lb_channel", "unset"), inline=False)  #
        staff_embed = discord.Embed(colour=0xffffff)
        staff_embed.add_field(name="staff roles", value=server_info.get("staff_roles", "unset"), inline=False) #
        staff_embed.add_field(name="staff role", value=server_info.get("staff_role", "unset"), inline=False) #
        staff_embed.add_field(name="staff ping", value=server_info.get("staff_ping", "unset"), inline=False) #
        staff_embed.add_field(name="staff break", value=server_info.get("staff_break", "unset"), inline=False)  #
        staff_embed.add_field(name="adm role", value=server_info.get("adm_role", "unset"), inline=False) #
        staff_embed.add_field(name="ban perms", value=server_info.get("ban_perms", "unset"), inline=False)  #
        service_embed = discord.Embed(colour=0xffffff)
        service_embed.add_field(name="mm roles", value=server_info.get("mm_roles", "unset"), inline=False) #
        service_embed.add_field(name="mm role", value=server_info.get("mm_role", "unset"), inline=False) #
        service_embed.add_field(name="mm ping", value=server_info.get("mm_ping", "unset"), inline=False) #
        service_embed.add_field(name="mm supervisor", value=server_info.get("mm_supervisor", "unset"), inline=False) #
        service_embed.add_field(name="mm trainer", value=server_info.get("mm_trainer", "unset"), inline=False) #
        service_embed.add_field(name="mm break", value=server_info.get("mm_break", "unset"), inline=False) #
        service_embed.add_field(name="mm vouch channel", value=server_info.get("mm_vouch_channel", "unset"), inline=False)
        service_embed.add_field(name="pilot roles", value=server_info.get("pilot_roles", "unset"), inline=False) #
        service_embed.add_field(name="pilot role", value=server_info.get("pilot_role", "unset"), inline=False) #
        service_embed.add_field(name="pilot ping", value=server_info.get("pilot_ping", "unset"), inline=False) #
        service_embed.add_field(name="pilot supervisor", value=server_info.get("pilot_supervisor", "unset"), inline=False) #
        service_embed.add_field(name="pilot trainer", value=server_info.get("pilot_trainer", "unset"), inline=False) #
        service_embed.add_field(name="pilot break", value=server_info.get("pilot_break", "unset"), inline=False) #
        service_embed.add_field(name="pilot vouch channel", value=server_info.get("pilot_vouch_channel", "unset"), inline=False)
        embeds = [general_embed, staff_embed, service_embed]
        await interaction.response.send_message(embeds=embeds, ephemeral=True)
    if topic == "bans warns channel" and input is not None:
        try: bans_warns_channel = await interaction.guild.fetch_channel(int(input.strip("<#>")))
        except discord.NotFound: await interaction.response.send_message("Invalid channel.")
        else:
            bans_warns_channel = f"<#{bans_warns_channel.id}>"
            server_info["bans_warns_channel"] = bans_warns_channel
            servers.replace_one(server_query, server_info)
            await interaction.response.send_message(f"The **bans warns channel** has been set to {bans_warns_channel}.")
    if topic == "transcripts channel" and input is not None:
        try: transcripts_channel = await interaction.guild.fetch_channel(int(input.strip("<#>")))
        except discord.NotFound: await interaction.response.send_message("Invalid channel.")
        else:
            transcripts_channel = f"<#{transcripts_channel.id}>"
            server_info["transcripts_channel"] = transcripts_channel
            servers.replace_one(server_query, server_info)
            await interaction.response.send_message(f"The **transcripts channel** has been set to {transcripts_channel}.")
    if topic == "staff lb channel" and input is not None:
        try: staff_lb_channel = await interaction.guild.fetch_channel(int(input.strip("<#>")))
        except discord.NotFound: await interaction.response.send_message("Invalid channel.")
        else:
            staff_lb_channel = f"<#{staff_lb_channel.id}>"
            server_info["staff_lb_channel"] = staff_lb_channel
            servers.replace_one(server_query, server_info)
            await interaction.response.send_message(f"The **staff lb channel** has been set to {staff_lb_channel}.")
    if topic == "services lb channel" and input is not None:
        try:
            services_lb_channel = await interaction.guild.fetch_channel(int(input.strip("<#>")))
        except discord.NotFound:
            await interaction.response.send_message("Invalid channel.")
        else:
            services_lb_channel = f"<#{services_lb_channel.id}>"
            server_info["services_lb_channel"] = services_lb_channel
            servers.replace_one(server_query, server_info)
            await interaction.response.send_message(
                f"The **services lb channel** has been set to {services_lb_channel}.")
    if topic == "revive ping" and input is not None:
        revive_ping = input.strip("<@&>")
        role = interaction.guild.get_role(int(revive_ping))
        if role:
            revive_ping = f"<@&{role.id}>"
            server_info["revive_ping"] = revive_ping
            servers.replace_one(server_query, server_info)
            await interaction.response.send_message(f"**revive ping** has been set to {revive_ping}.")
        else:
            await interaction.response.send_message(f"Invalid role.")
    if topic == "staff roles" and input is not None:
        staff_roles = input.replace("<@&", "").replace(">", "").split()
        valid_roles = []
        for staff_role in staff_roles:
            role = interaction.guild.get_role(int(staff_role))
            if role:
                valid_roles.append(staff_role)
        staff_roles = " ".join(f"<@&{role}>" for role in valid_roles)
        if staff_roles:
            server_info["staff_roles"] = staff_roles
            servers.replace_one(server_query, server_info)
            await interaction.response.send_message(f"**staff roles** have been set to {staff_roles}.")
        else:
            await interaction.response.send_message(f"Invalid roles.")
    if topic == "staff role" and input is not None:
        staff_role = input.strip("<@&>")
        role = interaction.guild.get_role(int(staff_role))
        if role:
            staff_role = f"<@&{role.id}>"
            server_info["staff_role"] = staff_role
            servers.replace_one(server_query, server_info)
            await interaction.response.send_message(f"**staff role** has been set to {staff_role}.")
        else:
            await interaction.response.send_message(f"Invalid role.")
    if topic == "staff ping" and input is not None:
        staff_ping = input.strip("<@&>")
        role = interaction.guild.get_role(int(staff_ping))
        if role:
            staff_ping = f"<@&{role.id}>"
            server_info["staff_ping"] = staff_ping
            servers.replace_one(server_query, server_info)
            await interaction.response.send_message(f"**staff ping** has been set to {staff_ping}.")
        else:
            await interaction.response.send_message(f"Invalid role.")
    if topic == "staff break" and input is not None:
        staff_break = input.strip("<@&>")
        role = interaction.guild.get_role(int(staff_break))
        if role:
            staff_break = f"<@&{role.id}>"
            server_info["staff_break"] = staff_break
            servers.replace_one(server_query, server_info)
            await interaction.response.send_message(f"**staff break** has been set to {staff_break}.")
        else:
            await interaction.response.send_message(f"Invalid role.")
    if topic == "adm role" and input is not None:
        adm_role = input.strip("<@&>")
        role = interaction.guild.get_role(int(adm_role))
        if role:
            adm_role = f"<@&{role.id}>"
            server_info["adm_role"] = adm_role
            servers.replace_one(server_query, server_info)
            await interaction.response.send_message(f"**adm role** has been set to {adm_role}.")
        else:
            await interaction.response.send_message(f"Invalid role.")
    if topic == "ban perms" and input is not None:
        ban_perms = input.strip("<@&>")
        role = interaction.guild.get_role(int(ban_perms))
        if role:
            ban_perms = f"<@&{role.id}>"
            server_info["ban_perms"] = ban_perms
            servers.replace_one(server_query, server_info)
            await interaction.response.send_message(f"**ban perms** has been set to {ban_perms}.")
        else:
            await interaction.response.send_message(f"Invalid role.")
    if topic == "mm roles" and input is not None:
        mm_roles = input.replace("<@&", "").replace(">", "").split()
        valid_roles = []
        for mm_role in mm_roles:
            role = interaction.guild.get_role(int(mm_role))
            if role:
                valid_roles.append(mm_role)
        mm_roles = " ".join(f"<@&{role}>" for role in valid_roles)
        if mm_roles:
            server_info["mm_roles"] = mm_roles
            servers.replace_one(server_query, server_info)
            await interaction.response.send_message(f"**mm roles** have been set to {mm_roles}.")
        else:
            await interaction.response.send_message(f"Invalid roles.")
    if topic == "mm role" and input is not None:
        mm_role = input.strip("<@&>")
        role = interaction.guild.get_role(int(mm_role))
        if role:
            mm_role = f"<@&{role.id}>"
            server_info["mm_role"] = mm_role
            servers.replace_one(server_query, server_info)
            await interaction.response.send_message(f"**mm role** has been set to {mm_role}.")
        else:
            await interaction.response.send_message(f"Invalid role.")
    if topic == "mm ping" and input is not None:
        mm_ping = input.strip("<@&>")
        role = interaction.guild.get_role(int(mm_ping))
        if role:
            mm_ping = f"<@&{role.id}>"
            server_info["mm_ping"] = mm_ping
            servers.replace_one(server_query, server_info)
            await interaction.response.send_message(f"**mm ping** has been set to {mm_ping}.")
        else:
            await interaction.response.send_message(f"Invalid role.")
    if topic == "mm supervisor" and input is not None:
        mm_supervisor = input.strip("<@&>")
        role = interaction.guild.get_role(int(mm_supervisor))
        if role:
            mm_supervisor = f"<@&{role.id}>"
            server_info["mm_supervisor"] = mm_supervisor
            servers.replace_one(server_query, server_info)
            await interaction.response.send_message(f"**mm supervisor** has been set to {mm_supervisor}.")
        else:
            await interaction.response.send_message(f"Invalid role.")
    if topic == "mm trainer" and input is not None:
        mm_trainer = input.strip("<@&>")
        role = interaction.guild.get_role(int(mm_trainer))
        if role:
            mm_trainer = f"<@&{role.id}>"
            server_info["mm_trainer"] = mm_trainer
            servers.replace_one(server_query, server_info)
            await interaction.response.send_message(f"**mm trainer** has been set to {mm_trainer}.")
        else:
            await interaction.response.send_message(f"Invalid role.")
    if topic == "mm break" and input is not None:
        mm_break = input.strip("<@&>")
        role = interaction.guild.get_role(int(mm_break))
        if role:
            mm_break = f"<@&{role.id}>"
            server_info["mm_break"] = mm_break
            servers.replace_one(server_query, server_info)
            await interaction.response.send_message(f"**mm break** has been set to {mm_break}.")
        else:
            await interaction.response.send_message(f"Invalid role.")
    if topic == "mm vouch channel" and input is not None:
        try:
            mm_vouch_channel = await interaction.guild.fetch_channel(int(input.strip("<#>")))
        except discord.NotFound:
            await interaction.response.send_message("Invalid channel.")
        else:
            mm_vouch_channel = f"<#{mm_vouch_channel.id}>"
            server_info["mm_vouch_channel"] = mm_vouch_channel
            servers.replace_one(server_query, server_info)
            await interaction.response.send_message(f"The **mm vouch channel** has been set to {mm_vouch_channel}.")
    if topic == "pilot roles" and input is not None:
        pilot_roles = input.replace("<@&", "").replace(">", "").split()
        valid_roles = []
        for pilot_role in pilot_roles:
            role = interaction.guild.get_role(int(pilot_role))
            if role:
                valid_roles.append(pilot_role)
        pilot_roles = " ".join(f"<@&{role}>" for role in valid_roles)
        if pilot_roles:
            server_info["pilot_roles"] = pilot_roles
            servers.replace_one(server_query, server_info)
            await interaction.response.send_message(f"**pilot roles** have been set to {pilot_roles}.")
        else:
            await interaction.response.send_message(f"Invalid roles.")
    if topic == "pilot role" and input is not None:
        pilot_role = input.strip("<@&>")
        role = interaction.guild.get_role(int(pilot_role))
        if role:
            pilot_role = f"<@&{role.id}>"
            server_info["pilot_role"] = pilot_role
            servers.replace_one(server_query, server_info)
            await interaction.response.send_message(f"**pilot role** has been set to {pilot_role}.")
        else:
            await interaction.response.send_message(f"Invalid role.")
    if topic == "pilot ping" and input is not None:
        pilot_ping = input.strip("<@&>")
        role = interaction.guild.get_role(int(pilot_ping))
        if role:
            pilot_ping = f"<@&{role.id}>"
            server_info["pilot_ping"] = pilot_ping
            servers.replace_one(server_query, server_info)
            await interaction.response.send_message(f"**pilot ping** has been set to {pilot_ping}.")
        else:
            await interaction.response.send_message(f"Invalid role.")
    if topic == "pilot supervisor" and input is not None:
        pilot_supervisor = input.strip("<@&>")
        role = interaction.guild.get_role(int(pilot_supervisor))
        if role:
            pilot_supervisor = f"<@&{role.id}>"
            server_info["pilot_supervisor"] = pilot_supervisor
            servers.replace_one(server_query, server_info)
            await interaction.response.send_message(f"**pilot supervisor** has been set to {pilot_supervisor}.")
        else:
            await interaction.response.send_message(f"Invalid role.")
    if topic == "pilot trainer" and input is not None:
        pilot_trainer = input.strip("<@&>")
        role = interaction.guild.get_role(int(pilot_trainer))
        if role:
            pilot_trainer = f"<@&{role.id}>"
            server_info["pilot_trainer"] = pilot_trainer
            servers.replace_one(server_query, server_info)
            await interaction.response.send_message(f"**pilot trainer** has been set to {pilot_trainer}.")
        else:
            await interaction.response.send_message(f"Invalid role.")
    if topic == "pilot break" and input is not None:
        pilot_break = input.strip("<@&>")
        role = interaction.guild.get_role(int(pilot_break))
        if role:
            pilot_break = f"<@&{role.id}>"
            server_info["pilot_break"] = pilot_break
            servers.replace_one(server_query, server_info)
            await interaction.response.send_message(f"**pilot break** has been set to {pilot_break}.")
        else:
            await interaction.response.send_message(f"Invalid role.")
    if topic == "pilot vouch channel" and input is not None:
        try:
            pilot_vouch_channel = await interaction.guild.fetch_channel(int(input.strip("<#>")))
        except discord.NotFound:
            await interaction.response.send_message("Invalid channel.")
        else:
            pilot_vouch_channel = f"<#{pilot_vouch_channel.id}>"
            server_info["pilot_vouch_channel"] = pilot_vouch_channel
            servers.replace_one(server_query, server_info)
            await interaction.response.send_message(
                f"The **pilot vouch channel** has been set to {pilot_vouch_channel}.")


# TRI

tri_ticket_options = [
    discord.SelectOption(emoji="<:whitebutterfly:1459750881611354237>", label="ㆍㆍReport", value="report"),
    discord.SelectOption(emoji="<:redheart:1462285627243499655>", label="ㆍㆍAppeal", value="appeal"),
    discord.SelectOption(emoji="<:whiteheart:1434538078747365507>", label="ㆍㆍVerify", value="verify"),
    discord.SelectOption(emoji="<:redbow:1462286246763040921>", label="ㆍㆍOthers", value="others"),
    ]

class TRITicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.select(options=tri_ticket_options, placeholder="‎　　Select a ticket type . . .　　　", custom_id="ticket",
                       max_values=1)
    async def select_callback(self, interaction, select):
        if interaction.guild.id == TRI_Archive:
            if self.select_callback.values[0] == "report":
                await interaction.response.send_modal(ReportModal())
            elif self.select_callback.values[0] == "appeal":
                await interaction.response.send_modal(AppealModal())
            elif self.select_callback.values[0] == "verify":
                await interaction.response.send_modal(VerifyModal())
            elif self.select_callback.values[0] == "others":
                await interaction.response.send_modal(OthersModal())

class ReportModal(discord.ui.Modal, title="ㆍㆍReport"):
    user_id = discord.ui.TextInput(
        label='ㆍㆍWho are you reporting?',
        style=discord.TextStyle.short,
        placeholder='User ID / Server Invite',
    )
    game = discord.ui.TextInput(
        label='ㆍㆍGame?',
        style=discord.TextStyle.short,
        placeholder='N/A if not applicable',
    )
    anon = discord.ui.TextInput(
        label='ㆍㆍAnonymous?',
        style=discord.TextStyle.short,
        placeholder='Yes (Remain Anonymous) / No (Credit as Contributor)',
    )
    desc = discord.ui.TextInput(
        label='ㆍㆍBriefly describe the situation.',
        style=discord.TextStyle.long,
    )

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer()
        channel = interaction.channel
        thread = await channel.create_thread(
            name=f"report-{interaction.user.name}",
            auto_archive_duration=10080,
            type=discord.ChannelType.private_thread
        )
        await interaction.followup.send(f"Created new ticket: {thread.jump_url}", ephemeral=True)
        await thread.send(f"{interaction.user.mention}")  # <@&{ticket_ping}>
        embed=discord.Embed(colour=0xffffff, description=f"""
# ‎　　　　report 　𓈒　𓈒　𓈒　　ticket　　ೀ　

-# _ _　<:dot66:1449656949632139405>　opened by: {interaction.user.mention} `{interaction.user.id}`
-# _ _　<:dot66:1449656949632139405>　reporting on: <@{self.user_id.value}> `{self.user_id.value}`
-# _ _　<:dot66:1449656949632139405>　game: {self.game.value}
-# _ _　<:dot66:1449656949632139405>　anonymous: {self.anon.value}

➴　 description: {self.desc.value}
        """)
        await thread.send(embed=embed)
        new_ticket = {
            "_id": str(thread.id),
            "opened_by": f"{interaction.user.id}",
            "opened_at": f"{time.time()}",
            "claimed_by": [],
            "closed_by": "",
            "closed_at": "",
        }
        tickets.insert_one(new_ticket)

class AppealModal(discord.ui.Modal, title="ㆍㆍAppeal"):
    user_id = discord.ui.TextInput(
        label='ㆍㆍWho are you appealing?',
        style=discord.TextStyle.short,
        placeholder='Self / User ID',
    )
    desc = discord.ui.TextInput(
        label='ㆍㆍBriefly describe the situation.',
        style=discord.TextStyle.long,
    )
    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer()
        channel = interaction.channel
        thread = await channel.create_thread(
            name=f"appeal-{interaction.user.name}",
            auto_archive_duration=10080,
            type=discord.ChannelType.private_thread
        )
        await interaction.followup.send(f"Created new ticket: {thread.jump_url}", ephemeral=True)
        await thread.send(f"{interaction.user.mention}")  # <@&{ticket_ping}>
        embed = discord.Embed(colour=0xffffff, description=f"""
# ‎　　　　appeal 　𓈒　𓈒　𓈒　　ticket　　ೀ　

-# _ _　<:dot66:1449656949632139405>　opened by: {interaction.user.mention} `{interaction.user.id}`
-# _ _　<:dot66:1449656949632139405>　appealing for: <@{self.user_id.value}> `{self.user_id.value}`

➴　 description: {self.desc.value}
""")
        await thread.send(embed=embed)
        new_ticket = {
            "_id": str(thread.id),
            "opened_by": f"{interaction.user.id}",
            "opened_at": f"{time.time()}",
            "claimed_by": [],
            "closed_by": "",
            "closed_at": "",
        }
        tickets.insert_one(new_ticket)

class VerifyModal(discord.ui.Modal, title="ㆍㆍVerify"):
    desc = discord.ui.TextInput(
        label='ㆍㆍVerification issue?',
        style=discord.TextStyle.long,
        placeholder='Alt Intrusion / VPN, explain if needed.',
    )
    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer()
        channel = interaction.channel
        thread = await channel.create_thread(
            name=f"verify-{interaction.user.name}",
            auto_archive_duration=10080,
            type=discord.ChannelType.private_thread
        )
        await interaction.followup.send(f"Created new ticket: {thread.jump_url}", ephemeral=True)
        await thread.send(f"{interaction.user.mention}")  # <@&{ticket_ping}>
        embed = discord.Embed(colour=0xffffff, description=f"""
# ‎　　　　verify 　𓈒　𓈒　𓈒　　ticket　　ೀ　

-# _ _　<:dot66:1449656949632139405>　opened by: {interaction.user.mention} `{interaction.user.id}`

➴　 description: {self.desc.value}
""")
        await thread.send(embed=embed)
        new_ticket = {
            "_id": str(thread.id),
            "opened_by": f"{interaction.user.id}",
            "opened_at": f"{time.time()}",
            "claimed_by": [],
            "closed_by": "",
            "closed_at": "",
        }
        tickets.insert_one(new_ticket)

class OthersModal(discord.ui.Modal, title="ㆍㆍOthers"):
    desc = discord.ui.TextInput(
        label='ㆍㆍReason for opening?',
        style=discord.TextStyle.long,
    )
    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer()
        channel = interaction.channel
        thread = await channel.create_thread(
            name=f"others-{interaction.user.name}",
            auto_archive_duration=10080,
            type=discord.ChannelType.private_thread
        )
        await interaction.followup.send(f"Created new ticket: {thread.jump_url}", ephemeral=True)
        await thread.send(f"{interaction.user.mention}")  # <@&{ticket_ping}>
        embed = discord.Embed(colour=0xffffff, description=f"""
# ‎　　　　others 　𓈒　𓈒　𓈒　　ticket　　ೀ　

-# _ _　<:dot66:1449656949632139405>　opened by: {interaction.user.mention} `{interaction.user.id}`

➴　 description: {self.desc.value}
""")
        await thread.send(embed=embed)
        new_ticket = {
            "_id": str(thread.id),
            "opened_by": f"{interaction.user.id}",
            "opened_at": f"{time.time()}",
            "claimed_by": [],
            "closed_by": "",
            "closed_at": "",
        }
        tickets.insert_one(new_ticket)




@bot.command()
async def sync(ctx: commands.Context):
    await bot.tree.sync()


bot.run(TOKEN)

