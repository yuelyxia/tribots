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

from typing import Optional

TOKEN = os.getenv("TOKEN")
CLIENT = os.getenv("CLIENT")

# mongodb info
client = pymongo.MongoClient(CLIENT)
kafu = client["kafu"]
tickets = kafu["tickets"]
servers = kafu["servers"]

TRI_Archive = 1371673839695826974

yuelyxia = 1303291812282372137

intents = discord.Intents.all()
bot = commands.Bot(command_prefix=',', help_command=None, intents=intents)

@bot.event
async def on_ready():
    bot.add_view(TRITicketView())
    bot.add_view(BanReqView())
    quota_check.start()

# loop tasks

QUOTA_CHECK_DAY = 1

@tasks.loop(time=datetime.time(hour=0, minute=0))
async def quota_check():
    now = datetime.datetime.now(datetime.timezone.utc)
    if now.day() == QUOTA_CHECK_DAY:
        # do something
        pass

# text commands

@bot.command(name="adm", help="Pings ADM+.")
async def adm(ctx):
    guild_id = ctx.guild.id
    server_query = {"_id": str(guild_id)}
    server_info = servers.find_one(server_query)
    if not server_info:
        return
    adm_role = server_info.get("adm_role")
    if adm_role:
        await ctx.reply(f"{adm_role}")

@bot.command(name='lb', help="Sends the current month's leaderboard.")
async def lb(ctx):
    guild_id = ctx.guild.id
    server_query = {"_id": str(guild_id)}
    server_info = servers.find_one(server_query)
    if not server_info:
        return
    staff = server_info.get("staff")
    if not staff:
        ctx.reply("Staff not found.")
        return
    sorted_staff = sorted(
        staff.items(),
        key=lambda item: item[1].get("monthly",0),
        reverse=True
    )
    embed = discord.Embed(colour=0xffffff)
    lines = []
    for user_id, data in sorted_staff:
        user = await bot.fetch_user(int(user_id))
        line = (
            f"-# <:greyreply:1448474301673115748>　"
            f"{user.mention}　–　"
            f"**{data.get("monthly", 0)}** month ﹒ **{data.get("alltime", 0)}** all"
        )
        lines.append(line)
    embed.description = "\n".join(lines)
    await ctx.send("## _ _　　　staff leaderboard", embed=embed)

@bot.command(name='rn')
@commands.cooldown(2, 600, commands.BucketType.channel)
async def rn(ctx, *, new_name: str):
    """Renames the current thread to the new name provided."""
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

@bot.command()
async def help(ctx):
    if not ctx.guild.id == TRI_Archive:
        embed = discord.Embed(title="KAFU commands", colour=0xffffff)
        embed.description = """wip
        """
        await ctx.send(embed=embed)

# slash commands

@bot.tree.command(name="ban", description="Bans a user.")
@app_commands.describe(user="User to ban", reason="Reason for ban")
async def ban(interaction: discord.Interaction, user: str, reason: Optional[str], image1: Optional[discord.Attachment], image2: Optional[discord.Attachment], image3: Optional[discord.Attachment], image4: Optional[discord.Attachment], image5: Optional[discord.Attachment], image6: Optional[discord.Attachment], image7: Optional[discord.Attachment], image8: Optional[discord.Attachment], image9: Optional[discord.Attachment], image10: Optional[discord.Attachment]):
    await interaction.response.defer(ephemeral=True)
    try:
        user = await bot.fetch_user(int(user.strip("<@>")))
        member = await interaction.guild.fetch_member(user.id)
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
    if interaction.user.top_role <= member.top_role:
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
        await member.ban(reason=reason)
        guild_id = interaction.guild.id
        server_query = {"_id": str(guild_id)}
        server_info = servers.find_one(server_query)
        if server_info:
            if not server_info.get("bans_warns_channel"):
                await interaction.followup.send("**bans warns channel** has not been set up for this server.")
                return
            bans_warns_channel = server_info.get("bans_warns_channel")
            bans_warns_channel = bot.get_channel(bans_warns_channel.strip("<#>"))
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
                        content=f"**Ban**\n﹒　User ID: {user.id}\n﹒　Reason: {reason}\n﹒　Banned by:{interaction.user.id}\n﹒　Proof:",
                        files=files_to_send)
                else:
                    await bans_warns_channel.send(
                        content=f"**Ban**\n﹒　User ID: {user.id}\n﹒　Reason: {reason}\n﹒　Banned by:{interaction.user.id}")
                    await interaction.followup.send(f"Unable to send ban log images.")
            except Exception:
                await bans_warns_channel.send(
                    content=f"**Ban**\n﹒　User ID: {user.id}\n﹒　Reason: {reason}\n﹒　Banned by:{interaction.user.id}")
                await interaction.followup.send(f"Unable to send ban log images.", ephemeral=True)
            try:
                server_info.get("staff").get(str(interaction.user.id))["monthly"] = server_info.get("staff").get(
                    str(interaction.user.id)).get("monthly", 0) + 1
                server_info.get("staff").get(str(interaction.user.id))["alltime"] = server_info.get("staff").get(
                    str(interaction.user.id)).get("alltime", 0) + 1
            except KeyError:
                await interaction.followup.send(f"Unable to add staff credits to {interaction.user.mention}`.", ephemeral=True)
            servers.replace_one(server_query, server_info)
    else:
        guild_id = interaction.guild.id
        server_query = {"_id": str(guild_id)}
        server_info = servers.find_one(server_query)
        if server_info:
            if not server_info.get("staff_role"):
                await interaction.followup.send("**staff role** has not been set up for this server.", ephemeral=True)
                return
            if not server_info.get("bans_warns_channel"):
                await interaction.followup.send("**bans warns channel** has not been set up for this server.", ephemeral=True)
                return
            staff_role = server_info.get("staff_role")
            adm_role = server_info.get("adm_role")
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
                            if adm_role:
                                ban_req = await bot.get_channel(int(bans_warns_channel.strip("<#>"))).send(
                                    content=f"{adm_role}\n**Ban Request**\n﹒　User ID: {user.id}\n﹒　Reason: {reason}\n﹒　Requested by: {interaction.user.id}\n﹒　Proof:",
                                    files=files_to_send, view=BanReqView())
                            else:
                                ban_req = await bot.get_channel(int(bans_warns_channel.strip("<#>"))).send(
                                    content=f"**Ban Request**\n﹒　User ID: {user.id}\n﹒　Reason: {reason}\n﹒　Requested by: {interaction.user.id}\n﹒　Proof:",
                                    files=files_to_send, view=BanReqView())
                        else:
                            if adm_role:
                                ban_req = await bot.get_channel(int(bans_warns_channel.strip("<#>"))).send(
                                    content=f"{adm_role}\n**Ban Request**\n﹒　User ID: {user.id}\n﹒　Reason: {reason}\n﹒　Requested by: {interaction.user.id}\n﹒　Proof:",
                                    view=BanReqView())
                            else:
                                ban_req = await bot.get_channel(int(bans_warns_channel.strip("<#>"))).send(
                                    content=f"**Ban Request**\n﹒　User ID: {user.id}\n﹒　Reason: {reason}\n﹒　Requested by: {interaction.user.id}\n﹒　Proof:",
                                    view=BanReqView())
                    except Exception:
                        if adm_role:
                            ban_req = await bot.get_channel(int(bans_warns_channel.strip("<#>"))).send(
                                content=f"{adm_role}\n**Ban Request**\n﹒　User ID: {user.id}\n﹒　Reason: {reason}\n﹒　Requested by: {interaction.user.id}\n﹒　Proof:",
                                view=BanReqView())
                        else:
                            ban_req = await bot.get_channel(int(bans_warns_channel.strip("<#>"))).send(
                                content=f"**Ban Request**\n﹒　User ID: {user.id}\n﹒　Reason: {reason}\n﹒　Requested by: {interaction.user.id}\n﹒　Proof:",
                                view=BanReqView())
                        await interaction.followup.send(f"Unable to send ban log images.", ephemeral=True)
                    await interaction.followup.send(f"A ban request has been sent: [Jump]({ban_req.jump_url})",
                                                            ephemeral=True)
                    server_info["bans_warns_req"][str(user.id)] = [reason, str(interaction.user.id), str(ban_req.jump_url)]
                    server_info["bans_warns_req"][str(ban_req.id)] = str(user.id)
                    servers.replace_one(server_query, server_info)
        else:
            await interaction.followup.send(f"This server is not whitelisted.", ephemeral=True)
@ban.error
async def ban_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    await interaction.response.send_message(f"An error occurred: {error}", ephemeral=True)

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
                member = await interaction.guild.fetch_member(int(user_id.strip("<@>")))
                try:
                    await user.send(
                        f"You have been banned from {interaction.guild.name} for the following reason: {reason}")
                except discord.Forbidden:
                    pass
                await member.ban(reason=reason)
                await interaction.response.edit_message(
                    content=f"**Ban Accepted**\n﹒　User ID: {user_id}\n﹒　Reason: {reason}\n﹒　Requested by: <@{requested_by}>\n﹒　Accepted by: {interaction.user.mention}\n﹒　Proof:",
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
                    await interaction.followup.send(f"Unable to add staff credits to {interaction.user.mention}`.", ephemeral=True)
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
                    content=f"> **Ban Rejected**\n> ﹒　User ID: {user_id}\n> ﹒　Reason: {reason}\n> ﹒　Requested by: <@{requested_by}>\n> ﹒　Rejected by: {interaction.user.mention}\n> ﹒　Proof:",
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
    banned_users = [ban_entry.user for ban_entry in await interaction.guild.bans()]
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
            bans_warns_channel = bot.get_channel(bans_warns_channel.strip("<#>"))
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
                        content=f"**Unban**\n﹒　User ID: {user.id}\n﹒　Reason: {reason}\n﹒　Unbanned by:{interaction.user.id}\n﹒　Proof:",
                        files=files_to_send)
                else:
                    await bans_warns_channel.send(
                        content=f"**Unban**\n﹒　User ID: {user.id}\n﹒　Reason: {reason}\n﹒　Unbanned by:{interaction.user.id}")
                    await interaction.followup.send(f"Unable to send ban log images.")
            except Exception:
                await bans_warns_channel.send(
                    content=f"**Unban**\n﹒　User ID: {user.id}\n﹒　Reason: {reason}\n﹒　Unbanned by:{interaction.user.id}")
                await interaction.followup.send(f"Unable to send ban log images.", ephemeral=True)
            try:
                server_info.get("staff").get(str(interaction.user.id))["monthly"] = server_info.get("staff").get(
                    str(interaction.user.id)).get("monthly", 0) + 1
                server_info.get("staff").get(str(interaction.user.id))["alltime"] = server_info.get("staff").get(
                    str(interaction.user.id)).get("alltime", 0) + 1
            except KeyError:
                await interaction.followup.send(f"Unable to add staff credits to {interaction.user.mention}`.",
                                                ephemeral=True)
            servers.replace_one(server_query, server_info)
    else:
        guild_id = interaction.guild.id
        server_query = {"_id": str(guild_id)}
        server_info = servers.find_one(server_query)
        if server_info:
            if not server_info.get("staff_role"):
                await interaction.followup.send("**staff role** has not been set up for this server.", ephemeral=True)
                return
            if not server_info.get("bans_warns_channel"):
                await interaction.followup.send("**bans warns channel** has not been set up for this server.",
                                                ephemeral=True)
                return
            staff_role = server_info.get("staff_role")
            adm_role = server_info.get("adm_role")
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
                            if adm_role:
                                ban_req = await bot.get_channel(int(bans_warns_channel.strip("<#>"))).send(
                                    content=f"{adm_role}\n**Unban Request**\n﹒　User ID: {user.id}\n﹒　Reason: {reason}\n﹒　Requested by: {interaction.user.id}\n﹒　Proof:",
                                    files=files_to_send, view=UnbanReqView())
                            else:
                                ban_req = await bot.get_channel(int(bans_warns_channel.strip("<#>"))).send(
                                    content=f"**Unban Request**\n﹒　User ID: {user.id}\n﹒　Reason: {reason}\n﹒　Requested by: {interaction.user.id}\n﹒　Proof:",
                                    files=files_to_send, view=UnbanReqView())
                        else:
                            if adm_role:
                                ban_req = await bot.get_channel(int(bans_warns_channel.strip("<#>"))).send(
                                    content=f"{adm_role}\n**Unban Request**\n﹒　User ID: {user.id}\n﹒　Reason: {reason}\n﹒　Requested by: {interaction.user.id}\n﹒　Proof:",
                                    view=UnbanReqView())
                            else:
                                ban_req = await bot.get_channel(int(bans_warns_channel.strip("<#>"))).send(
                                    content=f"**Unban Request**\n﹒　User ID: {user.id}\n﹒　Reason: {reason}\n﹒　Requested by: {interaction.user.id}\n﹒　Proof:",
                                    view=UnbanReqView())
                    except Exception:
                        if adm_role:
                            ban_req = await bot.get_channel(int(bans_warns_channel.strip("<#>"))).send(
                                content=f"{adm_role}\n**Unban Request**\n﹒　User ID: {user.id}\n﹒　Reason: {reason}\n﹒　Requested by: {interaction.user.id}\n﹒　Proof:",
                                view=BanReqView())
                        else:
                            ban_req = await bot.get_channel(int(bans_warns_channel.strip("<#>"))).send(
                                content=f"**Unban Request**\n﹒　User ID: {user.id}\n﹒　Reason: {reason}\n﹒　Requested by: {interaction.user.id}\n﹒　Proof:",
                                view=BanReqView())
                        await interaction.followup.send(f"Unable to send unban log images.", ephemeral=True)
                    await interaction.followup.send(f"An unban request has been sent: [Jump]({ban_req.jump_url})",
                                                    ephemeral=True)
                    server_info["bans_warns_req"][str(user.id)] = [reason, str(interaction.user.id),
                                                                   str(ban_req.jump_url)]
                    server_info["bans_warns_req"][str(ban_req.id)] = str(user.id)
                    servers.replace_one(server_query, server_info)
        else:
            await interaction.followup.send(f"This server is not whitelisted.", ephemeral=True)
@unban.error
async def unban_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    await interaction.response.send_message(f"An error occurred: {error}", ephemeral=True)

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
                    content=f"**Unban Accepted**\n﹒　User ID: {user_id}\n﹒　Reason: {reason}\n﹒　Requested by: <@{requested_by}>\n﹒　Accepted by: {interaction.user.mention}\n﹒　Proof:",
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
                    await interaction.followup.send(f"Unable to add staff credits to {interaction.user.mention}`.", ephemeral=True)
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
                    content=f"> **Unban Rejected**\n> ﹒　User ID: {user_id}\n> ﹒　Reason: {reason}\n> ﹒　Requested by: <@{requested_by}>\n> ﹒　Rejected by: {interaction.user.mention}\n> ﹒　Proof:",
                    view=None)
                server_info["bans_warns_req"].pop(str(interaction.message.id))
                server_info["bans_warns_req"].pop(str(user_id))
                servers.replace_one(server_query, server_info)
                await interaction.followup.send(f"Unban request rejected.", ephemeral=True)












#




@bot.tree.command(name="panel", description="Sends a ticket panel.")
@app_commands.checks.has_permissions(administrator=True)
async def panel(interaction: discord.Interaction):
    if interaction.guild.id == TRI_Archive:
        await interaction.channel.send(embed=discord.Embed(colour=0xffffff, description="""
## 　　<:2paperclip:1449650494044639335>　　┈　　open ticket　　୭
　<:00_reply:1448474301673115748>　provide __uncropped__ & **unedited** proofs
　<:00_reply:1448474301673115748>　fake proofs / disrespect = **ban**
　<:00_reply:1448474301673115748>　**do not open** for appeals on bans
-# _ _　✦ 　not following rules / ghosting = close
            """), view=TRITicketView())
        await interaction.response.send_message("Panel has been sent.", ephemeral=True)


class TranscriptView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)


@bot.tree.command(name="whitelist")
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
                await interaction.response.send_message(f"`{guild_id}` has been whitelisted.")

@bot.tree.command(name="appoint", description="Appoint a staff/mm/pilot.")
@app_commands.describe(user="User to appoint", role="staff/mm/pilot")
@app_commands.checks.has_permissions(manage_roles=True)
async def appoint(interaction: discord.Interaction, user: str, role: str, desc: Optional[str]=None):
    guild_id = interaction.guild.id
    server_query = {"_id": str(guild_id)}
    server_info = servers.find_one(server_query)
    if not server_info:
        await interaction.response.send_message(f"This server is not whitelisted.")
        return
    try:
        user = await bot.fetch_user(int(user.strip("<@>")))
    except Exception:
        await interaction.response.send_message(f"Please enter a valid user ID.", ephemeral=True)
    else:
        user_id = user.id
        member = interaction.guild.get_member(int(user_id))
        if not member: return
        if role.lower() == "staff":
            server_info.setdefault("staff", {})
            server_info["staff"].setdefault(str(user_id), {})
            servers.replace_one(server_query, server_info)
            await interaction.response.send_message(f"`{user_id}` has been added to staff.")
            if desc is not None and server_info.get("staff_roles"):
                staff_roles = server_info["staff_roles"].split()
                if desc in staff_roles:
                    for role in staff_roles:
                        await member.remove_roles(role)
                    await member.add_roles(desc)
                    await interaction.followup.send(f"`{user_id}` has been assigned the {desc} role.", ephemeral=True)
            elif desc is not None:
                await interaction.followup.send("**staff roles** have not been set up.", ephemeral=True)
        if role.lower() == "mm":
            server_info.setdefault("mms", {})
            server_info["mms"].setdefault(str(user_id), {})
            servers.replace_one(server_query, server_info)
            await interaction.response.send_message(f"`{user_id}` has been added to mms.")
            if desc is not None and server_info.get("mm_roles"):
                mm_roles = server_info["mm_roles"].split()
                if desc in mm_roles:
                    for role in mm_roles:
                        await member.remove_roles(role)
                    await member.add_roles(desc)
                    await interaction.followup.send(f"`{user_id}` has been assigned the {desc} role.", ephemeral=True)
            elif desc is not None:
                await interaction.followup.send("**mm roles** have not been set up.", ephemeral=True)
        if role.lower() == "pilot":
            server_info.setdefault("pilots", {})
            server_info["pilots"].setdefault(str(user_id), {})
            servers.replace_one(server_query, server_info)
            await interaction.response.send_message(f"`{user_id}` has been added to pilots.")
            if desc is not None and server_info.get("pilots_roles"):
                pilots_roles = server_info["pilots_roles"].split()
                if desc in pilots_roles:
                    for role in pilots_roles:
                        await member.remove_roles(role)
                    await member.add_roles(desc)
                    await interaction.followup.send(f"`{user_id}` has been assigned the {desc} role.", ephemeral=True)
            elif desc is not None:
                await interaction.followup.send("**pilot roles** have not been set up.", ephemeral=True)




@bot.tree.command(name="setup")
@app_commands.checks.has_permissions(administrator=True)
async def setup(interaction: discord.Interaction, topic: Optional[str]=None, desc: Optional[str]=None):
    guild_id = interaction.guild.id
    server_query = {"_id": str(guild_id)}
    server_info = servers.find_one(server_query)
    if not server_info:
        await interaction.response.send_message(f"This server is not whitelisted.")
        return
    if topic is None:
        general_embed = discord.Embed(colour=0xffffff)
        general_embed.add_field(name="bans warns channel", value=server_info.get("bans_warns_channel", "unset"), inline=False) #
        general_embed.add_field(name="staff roles", value=server_info.get("staff_roles", "unset"), inline=False) #
        general_embed.add_field(name="staff role", value=server_info.get("staff_role", "unset"), inline=False) #
        general_embed.add_field(name="adm role", value=server_info.get("adm_role", "unset"), inline=False) #
        service_embed = discord.Embed(colour=0xffffff)
        service_embed.add_field(name="mm roles", value=server_info.get("mm_roles", "unset"), inline=False) #
        service_embed.add_field(name="mm role", value=server_info.get("mm_role", "unset"), inline=False)
        service_embed.add_field(name="mm ping", value=server_info.get("mm_ping", "unset"), inline=False)
        service_embed.add_field(name="mm vouch channel", value=server_info.get("mm_vouch_channel", "unset"), inline=False)
        service_embed.add_field(name="pilot roles", value=server_info.get("pilot_roles", "unset"), inline=False) #
        service_embed.add_field(name="pilot role", value=server_info.get("pilot_role", "unset"), inline=False)
        service_embed.add_field(name="pilot ping", value=server_info.get("pilot_ping", "unset"), inline=False)
        service_embed.add_field(name="pilot vouch channel", value=server_info.get("pilot_vouch_channel", "unset"), inline=False)
        embeds = [general_embed, service_embed]
        await interaction.response.send_message(embeds=embeds, ephemeral=True)
    if topic == "bans warns channel" and desc is not None:
        try: bans_warns_channel = await interaction.guild.fetch_channel(int(desc.strip("<#>")))
        except discord.NotFound: await interaction.response.send_message("Invalid channel.")
        else:
            bans_warns_channel = f"<#{bans_warns_channel.id}>"
            server_info["bans_warns_channel"] = bans_warns_channel
            servers.replace_one(server_query, server_info)
            await interaction.response.send_message(f"The **bans warns channel** has been set to {bans_warns_channel}.")
    if topic == "staff roles" and desc is not None:
        staff_roles = desc.strip("<@&>").split()
        valid_roles = []
        for staff_role in staff_roles:
            role = interaction.guild.get_role(int(staff_role))
            if role:
                valid_roles.append(staff_role)
        staff_roles = " ".join(f"<@&{role.id}>" for role in valid_roles)
        if staff_roles:
            server_info["staff_roles"] = staff_roles
            servers.replace_one(server_query, server_info)
            await interaction.response.send_message(f"**staff roles** have been set to {staff_roles}.")
        else:
            await interaction.response.send_message(f"Invalid roles.")
    if topic == "staff role" and desc is not None:
        staff_role = desc.strip("<@&>")
        role = interaction.guild.get_role(int(staff_role))
        if role:
            staff_role = f"<@&{role.id}>"
            server_info["staff_role"] = staff_role
            servers.replace_one(server_query, server_info)
            await interaction.response.send_message(f"**staff role** has been set to {staff_role}.")
        else:
            await interaction.response.send_message(f"Invalid role.")
    if topic == "adm role" and desc is not None:
        adm_role = desc.strip("<@&>")
        role = interaction.guild.get_role(int(adm_role))
        if role:
            adm_role = f"<@&{role.id}>"
            server_info["adm_role"] = adm_role
            servers.replace_one(server_query, server_info)
            await interaction.response.send_message(f"**adm role** has been set to {adm_role}.")
        else:
            await interaction.response.send_message(f"Invalid role.")
    if topic == "mm roles" and desc is not None:
        mm_roles = desc.strip("<@&>").split()
        valid_roles = []
        for mm_role in mm_roles:
            role = interaction.guild.get_role(int(mm_role))
            if role:
                valid_roles.append(mm_role)
        mm_roles = " ".join(f"<@&{role.id}>" for role in valid_roles)
        if mm_roles:
            server_info["mm_roles"] = mm_roles
            servers.replace_one(server_query, server_info)
            await interaction.response.send_message(f"**mm roles** have been set to {mm_roles}.")
        else:
            await interaction.response.send_message(f"Invalid roles.")
    if topic == "pilot roles" and desc is not None:
        pilot_roles = desc.strip("<@&>").split()
        valid_roles = []
        for pilot_role in pilot_roles:
            role = interaction.guild.get_role(int(pilot_role))
            if role:
                valid_roles.append(pilot_role)
        pilot_roles = " ".join(f"<@&{role.id}>" for role in valid_roles)
        if pilot_roles:
            server_info["pilot_roles"] = pilot_roles
            servers.replace_one(server_query, server_info)
            await interaction.response.send_message(f"**pilot roles** have been set to {pilot_roles}.")
        else:
            await interaction.response.send_message(f"Invalid roles.")


# TRI


tri_ticket_options = [
    discord.SelectOption(emoji="<:whitebutterfly:1459750881611354237>", label="﹒﹒Report", value="report"),
    discord.SelectOption(emoji="<:redheart:1462285627243499655>", label="﹒﹒Appeal", value="appeal"),
    discord.SelectOption(emoji="<:whiteheart:1434538078747365507>", label="﹒﹒Verify", value="verify"),
    discord.SelectOption(emoji="<:redbow:1462286246763040921>", label="﹒﹒Others", value="others"),
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

class ReportModal(discord.ui.Modal, title="﹒﹒Report"):
    user_id = discord.ui.TextInput(
        label='﹒﹒Who are you reporting?',
        style=discord.TextStyle.short,
        placeholder='User ID / Server Invite',
    )
    game = discord.ui.TextInput(
        label='﹒﹒Game?',
        style=discord.TextStyle.short,
        placeholder='N/A if not applicable',
    )
    anon = discord.ui.TextInput(
        label='﹒﹒Anonymous?',
        style=discord.TextStyle.short,
        placeholder='Yes (Remain Anonymous) / No (Credit as Contributor)',
    )
    desc = discord.ui.TextInput(
        label='﹒﹒Briefly describe the situation.',
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

class AppealModal(discord.ui.Modal, title="﹒﹒Appeal"):
    user_id = discord.ui.TextInput(
        label='﹒﹒Who are you appealing?',
        style=discord.TextStyle.short,
        placeholder='Self / User ID',
    )
    desc = discord.ui.TextInput(
        label='﹒﹒Briefly describe the situation.',
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

class VerifyModal(discord.ui.Modal, title="﹒﹒Verify"):
    desc = discord.ui.TextInput(
        label='﹒﹒Verification issue?',
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

class OthersModal(discord.ui.Modal, title="﹒﹒Others"):
    desc = discord.ui.TextInput(
        label='﹒﹒Reason for opening?',
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

