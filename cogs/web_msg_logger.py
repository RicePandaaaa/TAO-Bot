import json # for log files
import os # for file path and directory creations
from datetime import date, datetime
from typing import Literal
from discord.ext import commands #base bot stuff
import discord
from discord import app_commands

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
        return [cat for cat, data in self.sorted_data.items() if str(msg_id) in data["Message"]]
    
    def _nowtime(self) -> tuple[str,str]: #gets time and date for timestamp in Central Time Zone
        now = datetime.now() #if host is in central time zone
        return now.strftime("%Y-%m-%d"), now.strftime("%H:%M:%S") #returns date and time
    
    def _renum_bucket(self, cat:str): #renumber after deletion
        bucket = self.sorted_data[cat]
        ordered_ids = sorted(bucket["Message"].keys(), key = lambda ognum: bucket["Message"][ognum]["Number"]) #preserves the og number per message
        for i, ognum in enumerate(ordered_ids, start=1):
            bucket["Message"][ognum]["Number"] = i #renumber
        bucket["next num"] = len(ordered_ids) + 1 #next num of set
    
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message): #main function for logging messages
        if message.author.bot or (message.channel.id not in tracked_channel): #ignore untracked channels and bot messages
            return
        date, time = self._nowtime() #current date and time
        ccat = {tracked_channel[message.channel.id]} #find channel
        ccat.update(self._match_cat(message.content)) #find role
        for cat in ccat - {None}: #if no category then none
            bucket = self.sorted_data[cat] #new entry
            bucket["Message"][str(message.id)] = {
                "Number": bucket["next num"],
                "Date": date,
                "Time": time,
                "Content": message.content,
            }
            bucket["next num"] += 1 #next num
        self._save_data() #save data

    @commands.Cog.listener()
    async def on_raw_message_edit(self, payload: discord.RawMessageUpdateEvent): #logs message edits
        if payload.channel_id not in tracked_channel or "content" not in payload.data: #wrong channel / no edit change
            return
        
        new_msg = payload.data["content"]
        date, time = self._nowtime() #current date and time
        ecat = set(self._find_msg_cat(payload.message_id)) #find existing
        ccat = {tracked_channel[payload.channel_id]} #find channel
        ccat.update(self._match_cat(new_msg)) #find role
        wcat = ccat - {None} #wanted categories
        for cat in ecat: #if existing already
            entry = self.sorted_data[cat]["Message"][str(payload.message_id)]
            entry["Content"] = new_msg #update text
            entry["Date"], entry["Time"] = self._nowtime() #update timestamp

        for cat in wcat - set(ecat): #if new msg and category
            bucket = self.sorted_data[cat] #new entry
            bucket["Message"][str(payload.message_id)] = {
                "Number": bucket["next num"],
                "Date": date,
                "Time": time,
                "Content": new_msg,
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

    @app_commands.command(name="weblog", description="Manage the website message log tracking of roles and channels")
    @app_commands.default_permissions(administrator=True) #must be admin to use this :)
    async def weblog(self, interaction: discord.Interaction,
                     action: Literal["add", "delete", "list"],
                     name: str = None,
                     channel: discord.TextChannel = None,
                     role: discord.Role = None):
        
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True)
            return
        
        if action == "list":
            await interaction.response.send_message(f"Tracked channels: {list(tracked_channel.values())}\nTracked roles: {list(tracked_role.values())}", ephemeral=False)
            return

        if (channel is None) == (role is None):
            await interaction.response.send_message("You must specify either a channel or a role", ephemeral=True)
            return
        
        target_dict = tracked_channel if channel else tracked_role
        target_id = (channel or role).id

        if action == "add":
            if name is None:
                await interaction.response.send_message("You must specify a name for the new category.", ephemeral=True)
                return
            elif (name in tracked_channel.values()) or (name in tracked_role.values()):
                await interaction.response.send_message(f"The name '{name}' is already in use. Please choose a different name.", ephemeral=True)
                return
            if target_id in target_dict:
                await interaction.response.send_message("That channel or role is already being tracked.", ephemeral=True)
                return
            target_dict[target_id] = name
            self.sorted_data.setdefault(name, {"next num": 1, "Message": {}})
            self._save_data()
            _save_tracked()
            await interaction.response.send_message(f"Added {channel or role} tracking to category '{name}'.", ephemeral=False)
        elif action == "delete":
            cat = target_dict.pop(target_id, None)
            if cat is not None:
                self.sorted_data.pop(cat, None)
                self._save_data()

            _save_tracked()

            await interaction.response.send_message(f"Stopped {channel or role} tracking.", ephemeral=False)
        
async def setup(bot: commands.Bot):
    await bot.add_cog(msglogger(bot))