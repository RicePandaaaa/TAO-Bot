import json # for log files
import os # for file path and directory creations
from datetime import datetime # timestamping events
from discord.ext import commands #base bot stuff
import discord

#drive paths for data
sorted_data_pathway = "logs/sorted_data.json"

#ROLE AND CHANNEL IDS
announcement_role = 0 #*place role id here*
bulletin_board_role = 0 #*place role id here*
tracked_role = {announcement_role: "Announcement", bulletin_board_role: "Bulletin Board"}
tracked_channel = {announcement_role: "Announcement", bulletin_board_role: "Bulletin"} #placeholders for now

class msglogger(commands.Cog):
    def __init__(self,bot: commands.Bot): #forms cog object :)
        self.bot = bot
        os.makedirs(os.path.dirname(sorted_data_pathway), exist_ok=True) #data directory exists with this now
        self.sorted_data = self._load_data() #loads each bot run to archive and keep log

    def _load_data(self) -> dict: #opens to a saved json file or start new
        if os.path.exists(sorted_data_pathway):
            with open(sorted_data_pathway, "r", encoding="utf-8") as f: #watches for emojis just in case
                return json.load(f)
        all_cat = set(tracked_role.values()) | set(tracked_channel.values()) #all categories
        return {a: {"num":1, "Message":{}} for a in all_cat}
    
    def _save_data(self): #update current dict memory in disk
        with open(sorted_data_pathway, "w", encoding="utf-8") as f:
            json.dump(self.sorted_data, f, indent=2) #sends back the data here
    
    def _match_cat(self,content:str) -> str: #matches the content to a category
        for role_id, cat in tracked_role.items():
            if f"<@&{role_id}>" in content:
                return cat #cat is category here
        return None #when message doesnt mention tracked role / will be replaced with general announcements category after
    
    def _find_msg_cat(self, msg_id:int) -> str: #check category to find message id
        for cat, data in self.sorted_data.items():
            if str(msg_id) in data["Message"]:
                return cat #is in a category already
        return None #gotta add a category still
    
    def _nowtime(self) -> tuple[str,str]: #gets time and date for timestamp if host is in Central Time Zone
        now = datetime.now()
        return now.strftime("%Y-%m-%d"), now.strftime("%H:%M:%S") #returns date and time
    
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message): #main function for logging messages
        if message.author.bot or (message.channel.id not in tracked_channel): #ignore untracked channels and bot messages
            return
        cat = self._match_cat(message.content) #find message output
        if cat is None: #if new message
            cat = tracked_channel.get(message.channel.id) #default category
        if cat is None: #channel not tracked
            return
        bucket = self.sorted_data[cat] #new entry
        date, time = self._nowtime() #current date and time
        bucket["Message"][str(message.id)] = {
            "Number": bucket["num"],
            "Date": date,
            "Time": time,
            "Content": message.content,
        }
        bucket["num"] += 1 #next num
        self._save_data() #save data

    @commands.Cog.listener()
    async def on_raw_message_edit(self, payload: discord.RawMessageUpdateEvent): #logs message edits
        if payload.channel_id not in tracked_channel or "content" not in payload.data: #wrong channel / no edit change
            return
        
        new_msg = payload.data["content"]
        cat = self._find_msg_cat(payload.message_id) #find message output
        if cat is None: #if new message
            cat = self._match_cat(new_msg)
            if cat is None:
                cat = tracked_channel.get(payload.channel_id) #default category
            if cat is None: #channel not tracked
                return
            bucket = self.sorted_data[cat] #new entry
            date, time = self._nowtime() #current date and time
            bucket["Message"][str(payload.message_id)] = {
                "Number": bucket["num"],
                "Date": date,
                "Time": time,
                "Content": new_msg,
            }
            bucket["num"]+= 1 #next num 
        else: #if already in cat
            entry = self.sorted_data[cat]["Message"][str(payload.message_id)]
            entry["Content"] = new_msg #update text
            entry["Date"], entry["Time"] = self._nowtime() #update timestamp

        self._save_data() #save data

    @commands.Cog.listener()
    async def on_raw_message_delete(self, payload: discord.RawMessageDeleteEvent): #logs
        cat = self._find_msg_cat(payload.message_id) #find message output
        if cat is None: #if new message
            return
        self.sorted_data[cat]["Message"].pop(str(payload.message_id), None) #delete entry
        self._save_data() #save data

async def setup(bot: commands.Bot):
    await bot.add_cog(msglogger(bot))