import discord
from discord.ext import commands
from discord.ext.commands import Context


class TextChannels(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command()
    @commands.has_any_role("TAO Officer")
    async def send_rules(self, ctx: Context):
        """ Command for bot to send out all TAO server rules """

        # Field contents
        links = {
                "TA & PT Guidelines": "https://engineering.tamu.edu/cse/academics/peer-teachers/rules-logistics.html",
                "Student Rules": "https://student-rules.tamu.edu/",
                "Student Handbook": "https://student-rules.tamu.edu/aggiecode/",
                "Discord Code of Conduct": "https://discord.com/guidelines",
                }
        rules = {
                "Overview": "It is expected that all members of this server abide by policies set by TAMU and Discord within this server!" \
                            "The relevant PT and student code of conduct links can be found above. By participating in this server, you agree " \
                            "to obey the rules and guidelines that govern this server.",
                "PT Availability": "PTs are students as well and have classes. Therefore, please be respectful if a PT is unavailable or must" \
                                " leave when outside of their working hours!",
                "Discussions about Grades": "Questions about why you got the grade you got and similar discussions must be conducted privately " \
                                            "with one of your PTs or your professor through standard means of communication (email, office hours, in-person).",
                "Academic Integrity": "It is expected that everyone upholds the Aggie Honor Code and will refrain from any sort of discussion that may be viewed" \
                                      " as academic dishonesty or a violation of the Aggie Honor Code. This also means that discussing about exam " \
                                      "specifics involving students and revealing code for graded assignments are forbidden in this server.",
                "Faculty Guidelines and Interactions": "All PTs, Head PTs, TAMU faculty, and VIPs are expected to be respectful and be mindful that they are" \
                                                     " all in positions of power. Student-staff interactions are encouraged, but please be aware of common " \
                                                     "sense boundaries.",
                }
        nicknames = {
                "PTs": "Current PTs must have at this format: \"<firstName> | PT\". Including last name, year, and major are all optional.",
                "Head PTs": "Current PTs must have at this format: \"<firstName> | Head PT\". Including last name, year, and major are all optional. ",
                "VIPs": "Current PTs must have at this format: \"<firstName> | VIP\". Including last name, year, and major are all optional. ",
                "TAMU Faculty": "Please name yourself such that students can easily identify you!",
                "Students and Former Faculty": "For everyone else, any nickname is acceptable as long as it obeys all codes of conduct and does not " \
                                             "reasonably seem as an attempt to impersonate TAMU faculty (including PTs) or an officer of TAO. "
                }
        role_select = {
                "Channel": "https://discord.com/channels/1022962971607060540/1142107250366889985",
                "Choosing Roles": "Please go to the above channel to choose your roles and gain access to the rest of the server!",
                "Faculty Verification": "To verify yourself as staff (PT, prof, or some other official TAMU faculty position), please follow " \
                                      "the instructions in the channel linked above!"
        }

        # Match embeds to set of fields
        embed_map ={"Code of Conduct Links": links, 
                    "Server Rules":          rules, 
                    "Nickname Guidelines":   nicknames, 
                    "Selecting Roles":       role_select}
 
        # Make each embed
        for embed_title in embed_map:
            embed = discord.Embed(color=discord.Color.dark_red())
            embed.set_author(name=embed_title)

            # Add the fields
            fields = embed_map[embed_title]
            for field_name in fields:
                embed.add_field(name=field_name, value=fields[field_name], inline=False)

            # Send the embed
            await ctx.send(embed=embed)

    @commands.hybrid_command()
    @commands.has_any_role("TAO Officer")
    async def send_discord_guide(self, ctx: Context):
        """ Sends out the embeds for Discord guide for those new to the platform """

        # Field contents
        guide_links = {
            "Discord Guidelines": "https://discord.com/guidelines",
            "Text Formatting": "https://www.remote.tools/remote-work/discord-text-formatting",
            "Voice Chat": "https://support.cci.drexel.edu/getting-connected/discord/discord-voice-chat/",
            "Beginner's Guide": "https://support.discord.com/hc/en-us/articles/360045138571-Beginner-s-Guide-to-Discord",
            "Server Rules": "https://discord.com/channels/1022962971607060540/1023087608928153681"
        }
        role_descriptions = {
            "Admin": "These are server adminstrators and also part of TAO's executive team (presidents and vice presidents)." \
                     " They hold absolute power in the server.",
            "Moderator": "These are server moderators that help out the admins and some of them are also officers for TAO.",
            "Head PT": "These are PTs that are part of TAO as a \"Head PT\", meaning that they help with TAO-hosted reviews and events along" \
                       " with their regular duties as a PT.",
            "VIP": "These are trusted server members that volunteer their time in helping students in Discord.",
            "102/216/217 PT": "These are PTs that have verified themselves with us. PTs must have this role to represent themselves " \
                              "as a PT in the server.",
            "Prof": "These are TAMU faculty (not exclusive to just professors) that have verified themselves with us. Faculty must have" \
                    " this role to represent themselves as part of TAMU faculty on the server.",
            "Bot Corner": "These are Discord bots that help manage and oversee the server."
        }
        question_etiquette = {
            "Ask Away!": "Don't wait for someone to say that they are available. Just ask and someone will reply to you whenever possible.",
            "Provide Information": "Please provide any information that you are allowed to share publically, such as assignment details" \
                                   "and errors messages. Do not share any information that you cannot share with a student, such as code " \
                                   "for graded assignments.",
            "Use the Forums": "If your question would require you to type more than two sentences, it's probably best to ask in the forum channel " \
                              "rather than the help channel. Asking in the forums also helps other students as they probably will have a similar question " \
                              "and would also want to know the solution(s).",
            "Be Patient": "No one is required to be on Discord, including PTs and faculty. All time here is volunteer so please be patient when waiting " \
                          "for a reply to your question!",
            "Don't Expect the Solution": "PTs want to help you learn, not just arrive at the solution, so they will try their best to explain " \
                                         "and lead you to the right answer for some questions. Please do not expect to always have someone give " \
                                         "you the answer!"
        }
        helpful_channel_breakdown = {
            "FAQ Forum Channels": "FAQ forums are updated and verified by PTs and include answers to questions that are frequently asked to PTs. Sometimes, " \
                          "professors may even add additional info. Wwithin a FAQ forum, there are posts organized by unit or topic in order to help " \
                          "organize the questions and their answers. Students cannot ask or answer in here.",
            "Subject Forum Channels": "This is where you can get help or discuss about your problem that cannot be reasonably asked with just a couple of sentences." \
                              " Feel free to use the search functionality to see if your question has been asked before!",
            "Professor Specific Channels": "Channels with just a professor name (or subject followed by professor name) can only be seen by " \
                                           "students and PTs who have that professsor, so feel free to ask in those channels if your question is " \
                                           "specific to just your professor.",
            "General Channels": "These channels are for any sort of conversation related to the category they reside in.",
            "Help Channels": "These channels are for any sort of quick questions you have related to the subject.",
            "Resume Review: <#1135409394339807242>": "Have a resume you want reviewed by your peers? Feel free to post your resume in here for free reviews! " \
                                      "You can also anonymously have your resume posted using the link found here: https://discord.com/channels/1022962971607060540/1136675298088341636. " \
                                      "Feel free to remove or hide any personal identifying information such as your phone number and address.",
            "Server and Club Updates: <#1022962972060037222> and <#1146937486610792468>": "Keep up to date with any news regarding TAO and other clubs with these two channels! " \
                                                                                          "Only members with the \"Announcements\" and \"Bulletin Board\" will be pinged, so " \
                                                                                         "feel free to opt-in or opt-out of these roles in <#1142107250366889985>!"
        }

        # Connect fields to their embeds
        embed_map = {
            "Useful Links": guide_links,
            "Role Descriptions": role_descriptions,
            "Question Etiquette": question_etiquette,
            "Helpful Channels": helpful_channel_breakdown
        }

        # Make each embed
        for embed_title in embed_map:
            embed = discord.Embed(color=discord.Color.dark_red())
            embed.set_author(name=embed_title)

            # Add the fields
            fields = embed_map[embed_title]
            for field_name in fields:
                embed.add_field(name=field_name, value=fields[field_name], inline=False)

            # Send the embed
            await ctx.send(embed=embed)

    @commands.hybrid_command()
    @commands.has_any_role("TAO Officer")
    async def send_verification_prompt(self, ctx: Context):
        """ Sends the prompt for faculty to verify themselves with the club """

        # Field contents
        fields = {
            "Overview": "In order to be a verified PT (for ENGR 102 or ENGR/PHYS 216/217) or faculty member and to represent yourself as such, " \
                        "please follow the instructions below for verification!",
            "For PTs": "Please send an email to `anthony.ha.pham@tamu.edu` (this email belongs to <@256186886907756545>) with the following information:" \
                       "\n- What classes you PT for (include course and section number such as PHYS 216 504 or ENGR 102 522)" \
                       "\n- Your Discord username (not the nickname). If you go to User Settings -> My Account, the username should be listed under \"Username\"",
            "For Faculty": "Please send an email to `anthony.ha.pham@tamu.edu` (this email belongs to <@256186886907756545>) with the following information:" \
                           "\n- Your Discord username (not the nickname). If you go to User Settings -> My Account, the username should be listed under \"Username\".",
            "Subject Line and Response Time": "Please send the email from your TAMU email! Also, please put something along the lines of \"Faculty Verification\" " \
                           "in the email subject line so that <@256186886907756545> can more easily find your email. He will reply back to you within 24 hours: if not, " \
                           "feel free to re-send the email or message him in Discord.",
            "Verification Status": "If Anthony is unable to verify you, he will email you back asking for additional information or for you to re-send corrected information." \
                                   "\n\nIf he is able to verify you, then you will be granted the following roles:" \
                                   "\n- The \"PT\" role and course specific PT role (for PTs)" \
                                   "\n- The \"Prof\" role (for faculty)" \
                                   "\n- Roles for your class (for PTs and faculty that teach ENGR 102 or ENGR/PHYS 216/217)"
        }

        # Make the embed
        embed = discord.Embed(color=discord.Color.dark_red())
        embed.set_author(name="PT and Faculty Verification")

        # Add the fields
        for field_name in fields:
            embed.add_field(name=field_name, value=fields[field_name], inline=False)

        # Send the embed
        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(TextChannels(bot))