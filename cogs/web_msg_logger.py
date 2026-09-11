import json # for log files
import os # for file path and directory creations
import datetime
from typing import Literal
from discord.ext import commands #base bot stuff
import discord
from discord import app_commands
import re

#drive paths here
tracked_pathway = "logs/tracked_IDs.json" #roles and channels tracked marked here
sorted_data_pathway = "logs/sorted_data.json" #message log here

tracked_role = {}
tracked_channel = {}

def _load_tracked():
    if not os.path.exists(tracked_pathway):
        return
    try: #try except to help good boot regardless of damaged or empty json file
        with open(tracked_pathway, "r", encoding="utf-8") as f:
            saved = json.load(f)
        tracked_role.update({int(k): v for k,v in saved.get("role",{}).items()}) #load roles
        tracked_channel.update({int(k): v for k,v in saved.get("channel",{}).items()}) #load channels
    except (json.JSONDecodeError, OSError, ValueError):
        tracked_role.clear()
        tracked_channel.clear()

def _save_tracked():
    temp_path = f"{tracked_pathway}.tmp"
    with open(temp_path, "w", encoding="utf-8") as f:
        json.dump({"role": {str(k): v for k,v in tracked_role.items()},
                   "channel": {str(k): v for k,v in tracked_channel.items()}}, f, indent=2)
        f.flush()
        os.fsync(f.fileno())
    os.replace(temp_path, tracked_pathway) #only swaps if successful write to temp file
        
_load_tracked() #restores all before any commands used

class msglogger(commands.Cog):
    def __init__(self,bot: commands.Bot): #forms cog object :)
        self.bot = bot
        self._synced = False
        os.makedirs(os.path.dirname(sorted_data_pathway), exist_ok=True) #data directory exists with this now
        self.sorted_data = self._load_data() #loads each bot run to archive and keep log

    def _load_data(self) -> dict: #opens to a saved json file or start new
        all_cat = set(tracked_role.values()) | set(tracked_channel.values()) #all categories
        if os.path.exists(sorted_data_pathway):
            try:
                with open(sorted_data_pathway, "r", encoding="utf-8") as f: #watches for emojis just in case
                    data = json.load(f)
                if not isinstance(data, dict):
                    data={}
            except (json.JSONDecodeError, OSError):
                data = {}
        else:
            data = {}
        for cat in all_cat: 
            bucket = data.setdefault(cat, {"next num":1, "Message":{}}) #creates new category if not there prior to last save
            if not isinstance(bucket, dict):
                data[cat] = {"next num":1, "Message":{}}
                continue
            messages = bucket.setdefault("Message", {})
            if not isinstance(messages, dict):
                bucket["Message"] = {}
                messages = bucket["Message"]
            for message in messages.values():
                if isinstance(message, dict):
                    message.setdefault("Number", 0)

            bucket.setdefault("next num", max((entry.get("Number",0) for entry in bucket["Message"].values()),
                default = 0) + 1)
        return data
    
    def _save_data(self): #update current dict memory in disk
        temp_path = f"{sorted_data_pathway}.tmp"
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(self.sorted_data, f, indent=2) #sends back the data here
            f.flush()
            os.fsync(f.fileno())
        
        os.replace(temp_path, sorted_data_pathway)
    
    def _match_cat(self,content:str) -> str: #matches the content to a category
        return{cat for role_id, cat in tracked_role.items() if f"<@&{role_id}>" in content}
      
    def _find_msg_cat(self, msg_id:int) -> str: #check category to find message id
        return [cat for cat, data in self.sorted_data.items() if isinstance(data, dict) and "Message" in data and str(msg_id) in data["Message"]]

    def _renum_bucket(self, cat:str): #renumber after deletion
        if cat not in self.sorted_data or "Message" not in self.sorted_data[cat]:
            return
        bucket = self.sorted_data[cat]
        ordered_ids = sorted(bucket["Message"].keys(), key = lambda ognum: bucket["Message"][ognum]["Number"]) #preserves the og number per message
        for i, ognum in enumerate(ordered_ids, start=1):
            bucket["Message"][ognum]["Number"] = i #renumber
        bucket["next num"] = len(ordered_ids) + 1 #next num of set

    def _clean_content(self, content: str, guild: discord.Guild = None) -> str: #makes text content pretty with replacing raw discord message with pretty roles and channels for web viewing
        def replace_mention(match):
            role_id = int(match.group(1))
            if role_id in tracked_role: #tracked role use local log stored names
                return f"@{tracked_role[role_id]}"
            if guild: #untracked role use discord stored names
                role = guild.get_role(role_id)
                if role:
                    return f"@{role.name}"
            return match.group(0) #role not found anywhere so leave the role be
        return re.sub(r"<@&(\d+)>", replace_mention, content)
    
    async def _synclog(self, channel:discord.TextChannel, limits: int | None = None) -> set[str]: #gets all of the missed messages when offline and first load and sends to .json
        live_msg = set()
        try:
            fetched = [msg async for msg in channel.history(limit=None, oldest_first=True)] #gets all of them

            for msg in fetched:
                if msg.author.bot:
                    continue
                msg_id = str(msg.id)
                live_msg.add(msg_id)
                ccat = {tracked_channel.get(channel.id)}
                ccat.update(self._match_cat(msg.content))
                wcat = ccat - {None}
                ecat = set(self._find_msg_cat(msg.id))

                dt = msg.edited_at or msg.created_at
                dates = dt.astimezone().strftime("%Y-%m-%d")
                times = dt.astimezone().strftime("%H:%M:%S")

                for cat in ecat & wcat: #update when content changed (valid category)
                    entry = self.sorted_data[cat]["Message"][msg_id]
                    if entry["Content"] != self._clean_content(msg.content, msg.guild):
                        entry["Content"] = self._clean_content(msg.content, msg.guild)
                        entry["Date"] = dates
                        entry["Time"] = times

                for cat in wcat - ecat: #new message and new categories
                    bucket = self.sorted_data.setdefault(cat, {"next num": 1, "Message": {}})
                    if msg_id not in bucket["Message"]:
                        bucket["Message"][msg_id] = {
                            "Number": bucket["next num"],
                            "Date": dates,
                            "Time": times,
                            "Content": self._clean_content(msg.content, msg.guild),
                        }
                        bucket["next num"] += 1

                for cat in ecat - wcat: #remove category
                    self.sorted_data[cat]["Message"].pop(msg_id, None)
                    self._renum_bucket(cat)

        except (discord.Forbidden, discord.HTTPException) as e:
            print(f"Failed on syncing channel {channel.id}: {e}")

        return live_msg
    
    @commands.Cog.listener()
    async def on_ready(self):
        if self._synced:
            return
        self._synced = True
        print("Syncing histories and offline missed messages")
        all_live = set()
        for channel_id in list(tracked_channel.keys()):
            channel = self.bot.get_channel(channel_id)
            if not channel:
                try:
                    channel = await self.bot.fetch_channel(channel_id)
                except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                    continue

            if hasattr(channel, 'history'):
                live = await self._synclog(channel)
                all_live.update(live)

        for cat, cat_data in list(self.sorted_data.items()):
            if not isinstance(cat_data, dict) or "Message" not in cat_data:
                continue
            begone = set(cat_data["Message"]) - all_live
            for msg_id in begone:
                cat_data["Message"].pop(msg_id, None)
            if begone:
                self._renum_bucket(cat)

        self._save_data()
        print("Sync Complete.")

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message): #main function for logging messages
        if message.author.bot or (message.channel.id not in tracked_channel): #ignore untracked channels and bot messages
            return
        dt = message.created_at.astimezone() 
        date, time = dt.strftime("%Y-%m-%d"), dt.strftime("%H:%M:%S")        
        ccat = {tracked_channel[message.channel.id]} #find channel
        ccat.update(self._match_cat(message.content)) #find role
        for cat in ccat - {None}: #if no category then none
            bucket = self.sorted_data.setdefault(cat, {"next num": 1, "Message": {}}) #new entry
            bucket["Message"][str(message.id)] = {
                "Number": bucket["next num"],
                "Date": date,
                "Time": time,
                "Content": self._clean_content(message.content, message.guild),
            }
            bucket["next num"] += 1 #next num
        self._save_data() #save data

    @commands.Cog.listener()
    async def on_raw_message_edit(self, payload: discord.RawMessageUpdateEvent): #logs message edits
        if payload.channel_id not in tracked_channel or "content" not in payload.data: #wrong channel / no edit change
            return
        guild = self.bot.get_guild(payload.guild_id)
        new_msg = payload.data["content"]
        edits = payload.data.get("edited_timestamp")
        if edits:
            dt = datetime.datetime.fromisoformat(edits).astimezone()
        else:
            dt = datetime.datetime.now().astimezone()
        date, time = dt.strftime("%Y-%m-%d"), dt.strftime("%H:%M:%S")
        ecat = set(self._find_msg_cat(payload.message_id)) #find existing
        ccat = {tracked_channel[payload.channel_id]} #find channel
        ccat.update(self._match_cat(new_msg)) #find role
        wcat = ccat - {None} #wanted categories
        for cat in ecat: #if existing already
            entry = self.sorted_data[cat]["Message"][str(payload.message_id)]
            entry["Content"] = self._clean_content(new_msg, guild) #update text
            entry["Date"], entry["Time"] = date,time #update timestamp

        for cat in wcat - set(ecat): #if new msg and category
            bucket = self.sorted_data.setdefault(cat, {"next num": 1, "Message": {}})            
            bucket["Message"][str(payload.message_id)] = {
                "Number": bucket["next num"],
                "Date": date,
                "Time": time,
                "Content": self._clean_content(new_msg, guild),
            }
            bucket["next num"] += 1 #next num
        
        for cat in set(ecat) - wcat: #if existing but no longer wanted (replace one role mention with another)
            self.sorted_data[cat]["Message"].pop(str(payload.message_id), None)
            self._renum_bucket(cat) #reorganise numbers

        self._save_data() #save data

    @commands.Cog.listener()
    async def on_raw_message_delete(self, payload: discord.RawMessageDeleteEvent): #logs
        for cat in self._find_msg_cat(payload.message_id): #find message output
            self.sorted_data[cat]["Message"].pop(str(payload.message_id), None) #delete entry
            self._renum_bucket(cat) #reorganise numbers
        self._save_data() #save data

    @commands.hybrid_command(name="weblog", description="Manage the website message log tracking of roles and channels")
    @app_commands.describe(action = "Add/delete to or list all of the tracked for logging.",
                     name = "Name of the Category of Tracked Data.",
                     channel = "Channel to be tracked (Can only add 1 at a time)",
                     role = "Role to be tracked (Can only add 1 at a time)"
                    )
    @commands.has_any_role("TAO Officer")
    async def weblog(self, ctx: commands.Context,
                     action: Literal["add", "delete", "list"] = commands.parameter(default=None, description="Add/delete to or list all of the tracked for logging."),
                     name: str = commands.parameter(default=None, description="Name of the Category of Tracked Data."),
                     channel: discord.TextChannel = commands.parameter(default=None, description="Channel to be tracked (Can only add 1 at a time)"),
                     role: discord.Role = commands.parameter(default=None, description="Role to be tracked (Can only add 1 at a time)")
                    ):
        """Manage the website message log tracking of roles and channels"""

        if action == "list":
            channelping = [f"<#{cid}> → {name}" for cid, name in tracked_channel.items()] or ["None tracked"]
            roleping = [f"<@&{rid}> → {name}" for rid, name in tracked_role.items()] or ["None tracked"]
            await ctx.send(f"**Tracked channels:**\n" + "\n".join(channelping) + f"\n**Tracked roles:**\n" + "\n".join(roleping))
            return

        if (channel is None) == (role is None):
            await ctx.send("You must specify either a channel or a role", ephemeral=True)
            return
        
        target_dict = tracked_channel if channel else tracked_role
        target_id = (channel or role).id

        if action == "add":
            if name is None:
                await ctx.send("You must specify a name for the new category.", ephemeral=True)
                return
            elif (name in tracked_channel.values()) or (name in tracked_role.values()):
                await ctx.send(f"The name '{name}' is already in use. Please choose a different name.", ephemeral=True)
                return
            if target_id in target_dict:
                await ctx.send("That channel or role is already being tracked.", ephemeral=True)
                return
            await ctx.defer(ephemeral=False) #discord interaction timeout prevention so bot can read all the history there is in new channel or role

            target_dict[target_id] = name
            self.sorted_data.setdefault(name, {"next num": 1, "Message": {}})
            _save_tracked()
            if channel:
                await self._synclog(channel, limits = None) #get the channel synced asap
            elif role:
                for channels in list(tracked_channel.keys()): #search all the channels for this role
                    chat = self.bot.get_channel(channels) or await self.bot.fetch_channel(channels)
                    if not chat: #sync all the chats now asap
                        try:
                            chat = await self.bot.fetch_channel(channels)
                        except(discord.NotFound, discord.Forbidden):
                            continue
                    if hasattr(chat, 'history'):
                        await self._synclog(chat, limits = None)

            self._save_data()
            await ctx.send(f"Added {channel or role} tracking to category '{name}'.", ephemeral=False)
        elif action == "delete":
            cat = target_dict.pop(target_id, None)
            if cat is not None:
                still_cat = cat in tracked_channel.values() or cat in tracked_role.values()
                if not still_cat:
                    self.sorted_data.pop(cat, None)
                    self._save_data()

            _save_tracked()

            await ctx.send(f"Stopped {channel or role} tracking.", ephemeral=False)
        
async def setup(bot: commands.Bot):
    await bot.add_cog(msglogger(bot))