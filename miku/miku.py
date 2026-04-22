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

from typing import Optional

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

intents = discord.Intents.all()
bot = commands.Bot(command_prefix=',', help_command=None, intents=intents)

GUILD_ID = 1371673839695826974

QUOTA_CHANNEL = 1375271142092308582
CMDS_CHANNEL = 1375260303817838694
VERIFY_CHANNEL = 1375260857772150804
TRAINING_CHANNEL = 1375271729680748635

# tri roles info
staff_role = 1373803879623430268
o5_role = 1372426616671834234
adm_role = 1375276457890287748
sr_role = 1375254710952661102
rep_role = 1372426736205303808
tr_role = 1372426794585817088
ban_perms = 1373517806921973900
staff_trainer = 1375277114651049984
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
    if len(before.roles) < len(after.roles):
        # Find the role that was added
        added_roles = set(after.roles) - set(before.roles)
        if tri_supporter in added_roles:
            # You can add specific logic here based on the role name or ID
            print(f"{after.name} has been assigned the role: {role.name}")


# loop tasks


@tasks.loop(time=datetime.time(hour=0, minute=0))
async def weekly_quota():
    guild = bot.get_guild(GUILD_ID)
    if datetime.datetime.now(datetime.timezone.utc).weekday() == 0:
        quota_channel = bot.get_channel(QUOTA_CHANNEL)
        total_reports = 0
        total_reviews = 0
        o5_reviews = []
        adm_reviews = []
        sr_reviews = []
        o5_reports = []
        adm_reports = []
        sr_reports = []
        rep_reports = []
        tr_reports = []
        cursor = staffweeklycol.find({})
        for doc in cursor:
            staff_weekly_profile = doc
            staff_id = staff_weekly_profile["_id"]
            staff_profile = trusteduserscol.find_one({"_id": staff_id})
            reviews = staff_profile["reviews"]
            reports = staff_profile["reports"]
            weekly_reviews = staff_weekly_profile["weekly_reviews"]
            weekly_reports = staff_weekly_profile["weekly_reports"]
            staff = guild.get_member(int(staff_id))
            if staff:
                if get(guild.roles, id=o5_role) in staff.roles:
                    o5_reviews.append([staff_id, reviews, weekly_reviews])
                    o5_reports.append([staff_id, reports, weekly_reports])
                elif get(guild.roles, id=adm_role) in staff.roles:
                    adm_reviews.append([staff_id, reviews, weekly_reviews])
                    adm_reports.append([staff_id, reports, weekly_reports])
                elif get(guild.roles, id=sr_role) in staff.roles:
                    sr_reviews.append([staff_id, reviews, weekly_reviews])
                    sr_reports.append([staff_id, reports, weekly_reports])
                elif get(guild.roles, id=rep_role) in staff.roles:
                    rep_reports.append([staff_id, reports, weekly_reports])
                elif get(guild.roles, id=tr_role) in staff.roles:
                    tr_reports.append([staff_id, reports, weekly_reports])
            staff_query = {"_id": staff_id}
            staff_weekly_profile["weekly_reports"] = "0"
            staff_weekly_profile["weekly_reviews"] = "0"
            staffweeklycol.replace_one(staff_query, staff_weekly_profile)
        o5_lbr = discord.Embed(colour=0xffffff)
        o5_lbr.description = "✦　　┈　　overseers"
        for staff_info in o5_reviews:
            staff_id = staff_info[0]
            reviews = staff_info[1]
            weekly_reviews = staff_info[2]
            total_reviews += int(weekly_reviews)
            staff = await bot.fetch_user(int(staff_id))
            o5_lbr.description += f"\n-# <:reply:1459162938303578213>　{staff.mention}　–　**{reviews}** all ﹒ {weekly_reviews} week"
        adm_lbr = discord.Embed(colour=0xffffff)
        adm_lbr.description = "✦　　┈　　admins"
        for staff_info in adm_reviews:
            staff_id = staff_info[0]
            reviews = staff_info[1]
            weekly_reviews = staff_info[2]
            total_reviews += int(weekly_reviews)
            staff = await bot.fetch_user(int(staff_id))
            adm_lbr.description += f"\n-# <:reply:1459162938303578213>　{staff.mention}　–　**{reviews}** all ﹒ {weekly_reviews} week"
        sr_lbr = discord.Embed(colour=0xffffff)
        sr_lbr.description = "✦　　┈　　senior reporters"
        for staff_info in sr_reviews:
            staff_id = staff_info[0]
            reviews = staff_info[1]
            weekly_reviews = staff_info[2]
            total_reviews += int(weekly_reviews)
            staff = await bot.fetch_user(int(staff_id))
            sr_lbr.description += f"\n-# <:reply:1459162938303578213>　{staff.mention}　–　**{reviews}** all ﹒ {weekly_reviews} week"
        embeds=[o5_lbr, adm_lbr, sr_lbr]
        await quota_channel.send(f"## _ _　　　weekly leaderboards .ᐟ\n_ _　　　　　　||<@&{staff_role}>||")
        await quota_channel.send("## _ _　　　reviews leaderboard", embeds=embeds)
        #
        o5_lb = discord.Embed(colour=0xffffff)
        o5_lb.description = "✦　　┈　　overseers"
        for staff_info in o5_reports:
            staff_id = staff_info[0]
            reports = staff_info[1]
            weekly_reports = staff_info[2]
            total_reports += int(weekly_reports)
            staff = await bot.fetch_user(int(staff_id))
            o5_lb.description += f"\n-# <:reply:1459162938303578213>　{staff.mention}　–　**{reports}** all ﹒ {weekly_reports} week"
        adm_lb = discord.Embed(colour=0xffffff)
        adm_lb.description = "✦　　┈　　admins"
        for staff_info in adm_reports:
            staff_id = staff_info[0]
            reports = staff_info[1]
            weekly_reports = staff_info[2]
            total_reports += int(weekly_reports)
            staff = await bot.fetch_user(int(staff_id))
            adm_lb.description += f"\n-# <:reply:1459162938303578213>　{staff.mention}　–　**{reports}** all ﹒ {weekly_reports} week"
        sr_lb = discord.Embed(colour=0xffffff)
        sr_lb.description = "✦　　┈　　senior reporters"
        for staff_info in sr_reports:
            staff_id = staff_info[0]
            reports = staff_info[1]
            weekly_reports = staff_info[2]
            total_reports += int(weekly_reports)
            staff = await bot.fetch_user(int(staff_id))
            sr_lb.description += f"\n-# <:reply:1459162938303578213>　{staff.mention}　–　**{reports}** all ﹒ {weekly_reports} week"
        rep_lb = discord.Embed(colour=0xffffff)
        rep_lb.description = "✦　　┈　　reporters"
        for staff_info in rep_reports:
            staff_id = staff_info[0]
            reports = staff_info[1]
            weekly_reports = staff_info[2]
            total_reports += int(weekly_reports)
            staff = await bot.fetch_user(int(staff_id))
            rep_lb.description += f"\n-# <:reply:1459162938303578213>　{staff.mention}　–　**{reports}** all ﹒ {weekly_reports} week"
        tr_lb = discord.Embed(colour=0xffffff)
        tr_lb.description = "✦　　┈　　trial reporters"
        for staff_info in tr_reports:
            staff_id = staff_info[0]
            reports = staff_info[1]
            weekly_reports = staff_info[2]
            total_reports += int(weekly_reports)
            staff = await bot.fetch_user(int(staff_id))
            tr_lb.description += f"\n-# <:reply:1459162938303578213>　{staff.mention}　–　**{reports}** all ﹒ {weekly_reports} week"
        embeds = [o5_lb, adm_lb, sr_lb, rep_lb, tr_lb]
        await quota_channel.send("## _ _　　　reports leaderboard", embeds=embeds)
        summary = discord.Embed(colour=0xffffff)
        summary.description = (f"✦　　┈　　total reviews　　┈　　**{total_reviews}**\n✦　　┈　　total reports　　┈　　**{total_reports}**")
        await quota_channel.send("## _ _　　　weekly summary", embed=summary)



@bot.event
async def on_ready():
    bot.add_view(StaffGuideView())
    bot.add_view(StaffRulesView())
    bot.add_view(ClosingView())
    bot.add_view(TagsView())
    weekly_quota.start()


# text commands


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


def user_info(user):
    profile = discord.Embed()
    profile.set_thumbnail(url=f"{user.display_avatar}")
    profile.description = f"{user.name}\n`{user.id}`\n{user.mention}"
    profile.description += f"\n**Account Created:** <t:{round(int(user.created_at.timestamp()))}:D> (<t:{round(int(user.created_at.timestamp()))}:R>)\n"
    profile.set_footer(text="✦　Use ,c to check if user is reported, unreported or trusted.")
    return profile

@bot.command()
async def ui(ctx, *, to_check: str = None):
    if to_check == None:
        user = ctx.author
        await ctx.reply(embed=user_info(user))
    else:
        try:
            user = await bot.fetch_user(int(to_check.strip('<@>')))
        except Exception:
            await ctx.reply("Please provide a valid user ID.")
        else:
            await ctx.reply(embed=user_info(user))

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

@bot.command(name='tags', help="Sends the descriptions of demerit tags.")
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
    discord.SelectOption(emoji="<:whiteheart:1434538078747365507>", label="﹒﹒Report", value="report"),
    discord.SelectOption(emoji="<:whiteheart:1434538078747365507>", label="﹒﹒Appeal", value="appeal"),
    discord.SelectOption(emoji="<:whiteheart:1434538078747365507>", label="﹒﹒Verify", value="verify"),
    discord.SelectOption(emoji="<:whiteheart:1434538078747365507>", label="﹒﹒Others", value="others"),
    discord.SelectOption(emoji="<:whiteheart:1434538078747365507>", label="﹒﹒SR+", value="sr+"),
]


@bot.command(name='cl', help="Sends closing guide.")
async def cl(ctx, *, string: str = None):
    if ctx.guild.id == TRI_Archive:
        await ctx.reply(embed=discord.Embed(colour=0xffffff, title = "closing　guide　⸝⸝.ᐟ", description="""
﹒rename ticket　┈　`,rn (name) tbc`
﹒ping sr+　┈　`,sr`
﹒see format for closing statements using the dropdown below.
﹒please merge identical reasons.
﹒for mass reports, you may wish to use `,pr` after reports are published to retrieve IDs easily.
        """), view=ClosingView())



class ClosingView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.select(options=closing_options, placeholder="‎　　Select a closing type . . .　　　", custom_id="closing",
                       max_values=1)
    async def select_callback(self, interaction, select):
        if self.select_callback.values[0] == "report":
            await interaction.response.send_message(embed=discord.Embed(description="""
﹒new report　┈　`new report on (ID) as (tags)`
﹒added report　┈　`report added on (ID) as (tags)`
﹒edited alts　┈　`edited alts for (ID) - added (alt alt alt), removed (alt alt alt)`
﹒edited server owner　┈　`server owner edited for (ID)`
﹒insufficient proof　┈　`no report on (ID) // insufficient proof`
﹒unresponsive contributor　┈　`no report on (ID) // unresponsive contributor`
﹒contributor left server　┈　`no report on (ID) // contributor left server`
"""), ephemeral=True)
        if self.select_callback.values[0] == "appeal":
            await interaction.response.send_message(embed=discord.Embed(description="""
﹒accepted appeal　┈　`appeal on (ID) as (tags)`
﹒rejected appeal　┈　`no appeal on (ID) // invalid reason`
﹒insufficient proof　┈　`no appeal on (ID) // insufficient proof`
﹒unresponsive contributor　┈　`no appeal on (ID) // unresponsive contributor`
﹒contributor left server　┈　`no appeal on (ID) // contributor left server`
"""), ephemeral=True)
        if self.select_callback.values[0] == "verify":
            await interaction.response.send_message(embed=discord.Embed(description="""
﹒successful manual verification　┈　`(ID) manually verified`
﹒unresponsive contributor　┈　`unresponsive contributor`
﹒contributor left server　┈　`contributor left server`
"""), ephemeral=True)
        if self.select_callback.values[0] == "others":
            await interaction.response.send_message(embed=discord.Embed(description="""
﹒answered question(s)　┈　`query answered`
﹒banned user(s)　┈　`no report // banned (ID) for (reason)`
"""), ephemeral=True)
        if self.select_callback.values[0] == "sr+":
            await interaction.response.send_message(embed=discord.Embed(description="""
﹒rename ticket　┈　`,rn (name) tbc (sr name)`
﹒check active reports and give feedback　┈　`,ar`
﹒if done correctly, accept reports for voting in order.
﹒check reports in voting　┈　`,vr`
﹒wait until 4 agree votes before you can publish. 8 agree votes = auto-publish, 12 disagree votes = auto-reject.
﹒check published reports　┈　`,pr` and `,c (ID)` or `,mc (IDs)`
﹒ask reporter for closing and close the ticket.
"""), ephemeral=True)


@bot.command(name='getids', help="Extracts valid user IDs from the string provided.")
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



@bot.command(name='rn')
@commands.cooldown(2, 600, commands.BucketType.channel)
@commands.has_any_role(staff_role, tethys_staff_role)
async def rn(ctx, *, new_name: str):
    """Renames the current thread to the new name provided."""
    if isinstance(ctx.channel, discord.Thread):
        try:
            await ctx.channel.edit(name=new_name)
            await ctx.send(f"Thread renamed to **{new_name}**.")
        except Exception as e:
            await ctx.send(f"Renaming failed due to an error: {e}", ephemeral=True)
    else:
        await ctx.send("This command can only be used in a thread.", ephemeral=True)
@rn.error
async def rn_error(ctx, error):
    if isinstance(error, commands.CommandOnCooldown):
        remaining = error.retry_after  # cooldown time in seconds
        return await ctx.send(f"This command is on cooldown. Retry in {round(remaining)} seconds.", ephemeral=True)
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




@bot.command(name='lb', help="Sends the current week's reports leaderboard.")
@commands.has_any_role(staff_role)
async def lb(ctx):
    o5 = []
    adm = []
    sr = []
    rep = []
    tr = []
    cursor = staffweeklycol.find({})
    for doc in cursor:
        staff_weekly_profile = doc
        staff_id = staff_weekly_profile["_id"]
        staff_profile = trusteduserscol.find_one({"_id": staff_id})
        reports = staff_profile["reports"]
        weekly_reports = staff_weekly_profile["weekly_reports"]
        staff = ctx.guild.get_member(int(staff_id))
        if staff:
            if get(ctx.guild.roles, id=o5_role) in staff.roles:
                o5.append([staff_id, reports, weekly_reports])
            elif get(ctx.guild.roles, id=adm_role) in staff.roles:
                adm.append([staff_id, reports, weekly_reports])
            elif get(ctx.guild.roles, id=sr_role) in staff.roles:
                sr.append([staff_id, reports, weekly_reports])
            elif get(ctx.guild.roles, id=rep_role) in staff.roles:
                rep.append([staff_id, reports, weekly_reports])
            elif get(ctx.guild.roles, id=tr_role) in staff.roles:
                tr.append([staff_id, reports, weekly_reports])
        else: await ctx.reply(f"`{staff_id}` is no longer in this server.")
    o5_lb = discord.Embed(colour=0xffffff)
    o5_lb.description = "✦　　┈　　overseers"
    for staff_info in o5:
        staff_id = staff_info[0]
        reports = staff_info[1]
        weekly_reports = staff_info[2]
        staff = await bot.fetch_user(int(staff_id))
        o5_lb.description += f"\n-# <:reply:1459162938303578213>　{staff.mention}　–　**{reports}** all ﹒ **{weekly_reports}** week"
    adm_lb = discord.Embed(colour=0xffffff)
    adm_lb.description = "✦　　┈　　admins"
    for staff_info in adm:
        staff_id = staff_info[0]
        reports = staff_info[1]
        weekly_reports = staff_info[2]
        staff = await bot.fetch_user(int(staff_id))
        adm_lb.description += f"\n-# <:reply:1459162938303578213>　{staff.mention}　–　**{reports}** all ﹒ **{weekly_reports}** week"
    sr_lb = discord.Embed(colour=0xffffff)
    sr_lb.description = "✦　　┈　　senior reporters"
    for staff_info in sr:
        staff_id = staff_info[0]
        reports = staff_info[1]
        weekly_reports = staff_info[2]
        staff = await bot.fetch_user(int(staff_id))
        sr_lb.description += f"\n-# <:reply:1459162938303578213>　{staff.mention}　–　**{reports}** all ﹒ **{weekly_reports}** week"
    rep_lb = discord.Embed(colour=0xffffff)
    rep_lb.description = "✦　　┈　　reporters"
    for staff_info in rep:
        staff_id = staff_info[0]
        reports = staff_info[1]
        weekly_reports = staff_info[2]
        staff = await bot.fetch_user(int(staff_id))
        rep_lb.description += f"\n-# <:reply:1459162938303578213>　{staff.mention}　–　**{reports}** all ﹒ **{weekly_reports}** week"
    tr_lb = discord.Embed(colour=0xffffff)
    tr_lb.description = "✦　　┈　　trial reporters"
    for staff_info in tr:
        staff_id = staff_info[0]
        reports = staff_info[1]
        weekly_reports = staff_info[2]
        staff = await bot.fetch_user(int(staff_id))
        tr_lb.description += f"\n-# <:reply:1459162938303578213>　{staff.mention}　–　**{reports}** all ﹒ **{weekly_reports}** week"
    embeds=[o5_lb, adm_lb, sr_lb, rep_lb, tr_lb]
    await ctx.reply("## _ _　　　reports leaderboard", embeds=embeds)

@bot.command(name='lbr', help="Sends the current week's reviews leaderboard.")
@commands.has_any_role(staff_role)
async def lbr(ctx):
    o5 = []
    adm = []
    sr = []
    cursor = staffweeklycol.find({})
    for doc in cursor:
        staff_weekly_profile = doc
        staff_id = staff_weekly_profile["_id"]
        staff_profile = trusteduserscol.find_one({"_id": staff_id})
        reviews = staff_profile["reviews"]
        weekly_reviews = staff_weekly_profile["weekly_reviews"]
        staff = ctx.guild.get_member(int(staff_id))
        if staff:
            if get(ctx.guild.roles, id=o5_role) in staff.roles:
                o5.append([staff_id, reviews, weekly_reviews])
            elif get(ctx.guild.roles, id=adm_role) in staff.roles:
                adm.append([staff_id, reviews, weekly_reviews])
            elif get(ctx.guild.roles, id=sr_role) in staff.roles:
                sr.append([staff_id, reviews, weekly_reviews])
        else:
            await ctx.reply(f"`{staff_id}` is no longer in this server.")
    o5_lb = discord.Embed(colour=0xffffff)
    o5_lb.description = "✦　　┈　　overseers"
    for staff_info in o5:
        staff_id = staff_info[0]
        reviews = staff_info[1]
        weekly_reviews = staff_info[2]
        staff = await bot.fetch_user(int(staff_id))
        o5_lb.description += f"\n-# <:reply:1459162938303578213>　{staff.mention}　–　**{reviews}** all ﹒ **{weekly_reviews}** week"
    adm_lb = discord.Embed(colour=0xffffff)
    adm_lb.description = "✦　　┈　　admins"
    for staff_info in adm:
        staff_id = staff_info[0]
        reviews = staff_info[1]
        weekly_reviews = staff_info[2]
        staff = await bot.fetch_user(int(staff_id))
        adm_lb.description += f"\n-# <:reply:1459162938303578213>　{staff.mention}　–　**{reviews}** all ﹒ **{weekly_reviews}** week"
    sr_lb = discord.Embed(colour=0xffffff)
    sr_lb.description = "✦　　┈　　senior reporters"
    for staff_info in sr:
        staff_id = staff_info[0]
        reviews = staff_info[1]
        weekly_reviews = staff_info[2]
        staff = await bot.fetch_user(int(staff_id))
        sr_lb.description += f"\n-# <:reply:1459162938303578213>　{staff.mention}　–　**{reviews}** all ﹒ **{weekly_reviews}** week"
    embeds=[o5_lb, adm_lb, sr_lb]
    await ctx.reply("## _ _　　　reviews leaderboard", embeds=embeds)



class StaffRulesView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(discord.ui.Button(label="Staff Legal Codex", style=discord.ButtonStyle.grey,
                                        url="https://docs.google.com/document/d/18GPfRrvzJ4b1d6cJ_yLyd1HELJbE4y9PqBH5-FVQktc/"))


staff_guide_options = [
    discord.SelectOption(emoji="<:whiteheart:1434538078747365507>", label="﹒﹒Trial", value="trial"),
    discord.SelectOption(emoji="<:whiteheart:1434538078747365507>", label="﹒﹒Breaks", value="breaks"),
    discord.SelectOption(emoji="<:whiteheart:1434538078747365507>", label="﹒﹒Quota", value="quota"),
    discord.SelectOption(emoji="<:whiteheart:1434538078747365507>", label="﹒﹒Tickets", value="tickets"),
    discord.SelectOption(emoji="<:whiteheart:1434538078747365507>", label="﹒﹒Autoresponders", value="autoresponders"),
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
﹒**14–90 days**
﹒Exceeding 90 days results in an **unappealable demotion** (you may reapply)
﹒**Asking questions is encouraged** and will not affect your status
﹒**No breaks in the first 14 days** unless it’s an emergency
### Promotion Requirements
﹒**2 weeks of quota** (not necessarily consecutive)
﹒**15 non-hitter reports**
﹒**3 appeals**
﹒**20 votes**
            """), ephemeral=True)
        if self.select_callback.values[0] == "breaks":
            await interaction.response.send_message(embed=discord.Embed(description="""
### Break Types
﹒**Half Break** — weekly quota is **halved (rounded down)**
﹒**Full Break** — weekly quota is **not counted**
### Break Rules
﹒Staff **cannot earn Annual Leave** while on break
﹒**1 Full Break** may be split into **2 Half Breaks**
### Annual Leave
﹒Includes **all types of leave**
﹒Basic entitlement: **12 Full Breaks**
﹒**1/8 Full Break** for each **week of completed quota**
            """), ephemeral=True)
        if self.select_callback.values[0] == "quota":
            await interaction.response.send_message(embed=discord.Embed(description="""
### Quota Basics
﹒Weekly quota ranges between **5–10 reports/appeals**
﹒Only **successfully published** reports/appeals are counted
﹒Hitter reports count toward quota but have **low promotion value**
### Strikes
﹒Each week of **incomplete quota** while **not on a Full Break = 1 strike**
### Consequences for Incomplete Quota
﹒**Demotion in rank:**
　﹒2 consecutive strikes with **no breaks taken**
　﹒3 consecutive strikes with **≤ 1 Full Break** taken in total
　﹒4 or more strikes (not necessarily consecutive) within the **past 8 weeks**
﹒**Demotion from Staff:**
　﹒Average activity of **below 50%** over the **past 8 weeks**
　﹒Full Break weeks are **excluded** from calculation, but Half Break weeks are **included**
　﹒Activity is measured by **quota fulfilled**, capped at **100% per week**
            """), ephemeral=True)
        if self.select_callback.values[0] == "tickets":
            await interaction.response.send_message(embed=discord.Embed(description="""
### Ticket Claiming
﹒The **first Staff** to send a proper greeting (e.g. hi) handles the ticket
﹒If multiple greetings are sent, **reload Discord** to see who was first
﹒Other Staff must **delete their messages**
### Ticket Handling
﹒Only **one Staff** may handle a ticket at a time
﹒A **Defender** may assist if required
﹒Only **one Senior Reporter** may review when requested
﹒After acceptance for voting, the **sr+ who publishes** the report is responsible for **closing the ticket**
### Ticket Priority
﹒Handle **older tickets first**
﹒Do not skip tickets because they seem difficult
### Ticket Limits
﹒**Trial Reporter** — 1 active, 2 on-hold, 1 self ticket
﹒**Reporter** — 2 active, 2 on-hold, 1 self ticket
﹒If an on-hold ticket becomes active and exceeds your limit, you must **open one active ticket to other Staff**
### On-Hold
﹒Staff may place **their own tickets** on hold when necessary
﹒Common reasons include:
　﹒Waiting for Defendant response
　﹒Waiting for Contributor response
﹒Abuse of on-hold may result in **warnings or demotion**
### Ticket Closure
﹒If the Contributor does not reply within **12 hours**, you may request closure
﹒If no meaningful proof is provided within **4 hours**, you may request closure
            """), ephemeral=True)
        if self.select_callback.values[0] == "autoresponders":
            await interaction.response.send_message(embed=discord.Embed(description="""
### ,adm
﹒Pings adm+.
### ,sr
﹒Pings sr+.
### ,tp
﹒Pings ticket ping, e.g. when you want open a ticket to other Staff.
### ,ban
﹒Pings ban perms.
### ,cl
﹒Sends closing guide.
                """), ephemeral=True)



# slash commands

@bot.tree.command(name="staff_rules", description="Sends staff rules.")
@app_commands.checks.has_role(adm_role)
async def staff_rules(interaction: discord.Interaction):
    await interaction.channel.send(embed=discord.Embed(colour=0xffffff, description="""
## <:2paperclip:1449650494044639335>　　staff　　rules　　୨୧
### Follow Server Rules
﹒Adhere to all [server rules](https://discord.com/channels/1371673839695826974/1371674470611161160)
﹒Particular focus on **No Discrimination**, **No Hate or Threats**, and **No NSFW Content**
### Confidentiality
﹒Follow the Non-Disclosure Agreement (NDA)
﹒Violation may result in immediate removal from Staff, a report as Unprofessional Staff, and/or a server ban depending on severity
### Ticket Protocol
﹒Only one Staff should handle a ticket at a time, unless a Defender is required
﹒Do not hijack tickets assigned to others
﹒Avoid tickets where you are related to the Defendant
﹒Keep communication on-topic and case-related; no side-chatting
﹒When handling multiple reports in a ticket, address one at a time in order
### Professionalism
﹒Reports on Staff may result in quarantine and demotion if accepted
﹒Speaking negatively about ticket participants or Staff (current or former) is Unprofessional and will be addressed
### Respect
﹒Remain respectful, even toward those you dislike
﹒Personal feelings are not an excuse for rudeness or unprofessional behavior
### No Inappropriate Jokes
﹒Jokes about ||suicide||, ||self-harm||, or ||body shaming|| (e.g., "||kys||", "||fat||", "||keep yourself safe||") are strictly prohibited
﹒Even if said without ill-intention, these are not acceptable as they may make others uncomfortable
### No Drama
﹒Keep personal conflicts out of the server
﹒Resolve issues privately and respectfully, or seek proper mediation
### No Favouritism
﹒Do not excessively praise, defend, or favour specific individuals
﹒Favoritism that undermines neutrality, decision-making, or report handling is prohibited
"""), view=StaffRulesView())
    await interaction.response.send_message("Staff Rules have been sent.", ephemeral=True)



@bot.tree.command(name="staff_guide", description="Sends staff guide.")
@app_commands.checks.has_role(adm_role)
async def staff_guide(interaction: discord.Interaction):
    await interaction.channel.send(embed=discord.Embed(colour=0xffffff, description="""
## <:whitebow:1388714593211125971>　　staff　　guide　　୨୧
　　`,help` for list of TRI bots commands.
"""), view=StaffGuideView())
    await interaction.response.send_message("Staff Guide has been sent.", ephemeral=True)



@bot.tree.command(name='anon_say', description='Miku will speak on your behalf.')
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

@bot.tree.command(name='ban_log', description='Post a ban log.')
@app_commands.describe(user_id="User ID of banned user(s).", reason="Reason.", image1="Image 1 (optional)", image2="Image 2 (optional)", image3="Image 3 (optional)", image4="Image 4 (optional)", image5="Image 5 (optional)", image6="Image 6 (optional)", image7="Image 7 (optional)", image8="Image 8 (optional)", image9="Image 9 (optional)", image10="Image 10 (optional)")
@app_commands.checks.has_role(ban_perms)
async def ban_log(interaction: discord.Interaction, user_id: str, reason: str, image1: Optional[discord.Attachment], image2: Optional[discord.Attachment], image3: Optional[discord.Attachment], image4: Optional[discord.Attachment], image5: Optional[discord.Attachment], image6: Optional[discord.Attachment], image7: Optional[discord.Attachment], image8: Optional[discord.Attachment], image9: Optional[discord.Attachment], image10: Optional[discord.Attachment]):
    await interaction.response.defer(ephemeral=True)
    try:
        images = [img for img in [image1, image2, image3, image4, image5, image6, image7, image8, image9, image10] if img is not None]
        files_to_send = []
        async with aiohttp.ClientSession() as session:
            for img in images:
                if img.content_type and img.content_type.startswith('image/'):
                    async with session.get(img.url) as resp:
                        if resp.status == 200:
                            data = io.BytesIO(await resp.read())
                            files_to_send.append(discord.File(data, filename=img.filename))
        if files_to_send:
            await interaction.channel.send(content=f"﹒　User ID: {user_id}\n﹒　Reason: {reason}\n﹒　Proof:",
                                           files=files_to_send)
            await interaction.followup.send("Your message has been sent.", ephemeral=True)
        else:
            await interaction.followup.send(f"Please attach proof(s).", ephemeral=True)
    except Exception:
        await interaction.followup.send(f"Unable to send message.", ephemeral=True)


@bot.tree.command(name='create_training', description='Creates training thread.')
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


#



@bot.command()
async def sync(ctx: commands.Context):
    await bot.tree.sync()


bot.run(TOKEN)

