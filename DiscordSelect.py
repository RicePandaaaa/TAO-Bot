import re
import discord

# All items in this module are DynamicItems: their state is encoded entirely in their
# custom_id, so they keep working after a bot restart (registered in bot.setup_hook).

STUDENT_STATUSES = ["Doing ETAM", "Done with ETAM", "Visiting Student", "Alumni"]


class ProfSelect(discord.ui.DynamicItem[discord.ui.Select],
                 template=r"tao:prof:(?P<class_role_id>[0-9]+):(?P<class_name>.+)"):
    def __init__(self, class_name: str, class_role_id: int, professors: list[str]):
        """
        Initializes the select menu with professors associated with a certain class

        :param str class_name: The name of the class they teach (e.g. "PHYS 216")
        :param int class_role_id: The ID of the role associated with the class
        :param list[str] professors: A list of professor last names (e.g. "Brooks")
        """
        self.class_name = class_name
        self.class_role_id = class_role_id

        super().__init__(discord.ui.Select(
            options=[discord.SelectOption(label=f"Professor {prof}") for prof in professors],
            min_values=0,
            max_values=1,
            placeholder="---- SELECT PROF ----",
            custom_id=f"tao:prof:{class_role_id}:{class_name}"))

    @classmethod
    async def from_custom_id(cls, interaction: discord.Interaction, item: discord.ui.Select, match: re.Match[str]):
        """ Rebuilds the select menu from its custom_id after a restart """
        class_name = match["class_name"]
        professors = await interaction.client.db.get_professors(class_name)  # type: ignore[attr-defined]
        return cls(class_name, int(match["class_role_id"]), professors)

    async def callback(self, interaction: discord.Interaction):
        """
        Assigns roles depending on the response

        :param discord.Interaction interaction: The interaction in which the select calling back is attached to
        """
        # Get user
        user = interaction.user

        # Role check
        if not isinstance(user, discord.Member) or interaction.guild is None:
            return await interaction.response.send_message(content="This command can only be used in a server!", ephemeral=True)

        class_role = interaction.guild.get_role(self.class_role_id)
        if class_role is None:
            return await interaction.response.send_message(content="This prompt is outdated, please ask an officer to repost it!", ephemeral=True)

        for role in user.roles:
            # Duplicate role check
            if role.name == class_role.name:
                return await interaction.response.send_message(content=f"You already chose your roles for {role.name}!", ephemeral=True)

            # Already has any physics role
            if self.class_name.startswith("PHYS") and role.name.startswith("PHYS"):
                return await interaction.response.send_message(content="You already have PHYS roles assigned to you!", ephemeral=True)

        # Non empty selection
        if len(self.item.values) > 0:
            prof = self.item.values[0].removeprefix("Professor ")

            # The professor may have been removed from the list since this prompt was posted
            current_professors = await interaction.client.db.get_professors(self.class_name)  # type: ignore[attr-defined]
            prof_role = discord.utils.get(interaction.guild.roles, name=f"{self.class_name.split(' ')[1]} {prof}")

            if prof not in current_professors or prof_role is None:
                return await interaction.response.send_message(content="This prompt is outdated, please ask an officer to repost it!", ephemeral=True)

            # Professors can teach multiple courses, avoid double assigning a professor role
            if prof_role not in user.roles:
                await user.add_roles(prof_role)

            # Assign class role and inform user of assigned roles
            await user.add_roles(class_role)
            await interaction.response.send_message(content=f"You have been assigned \"{class_role.name}\" and \"{prof_role.name}\"!", ephemeral=True)


class StudentSelect(discord.ui.DynamicItem[discord.ui.Select],
                    template=r"tao:student:(?P<role_ids>[0-9]+(?::[0-9]+)*)"):
    def __init__(self, role_ids: list[int]) -> None:
        """
        Initialize the select menu with the names of potential student statuses

        :param list[int] role_ids: The role IDs matching STUDENT_STATUSES, in order
        """
        self.role_ids = role_ids

        super().__init__(discord.ui.Select(
            options=[discord.SelectOption(label=status) for status in STUDENT_STATUSES],
            min_values=0,
            max_values=1,
            placeholder="-- SELECT YOUR STUDENT STATUS --",
            custom_id=f"tao:student:{':'.join(str(role_id) for role_id in role_ids)}"))

    @classmethod
    async def from_custom_id(cls, interaction: discord.Interaction, item: discord.ui.Select, match: re.Match[str]):
        return cls([int(role_id) for role_id in match["role_ids"].split(":")])

    async def callback(self, interaction: discord.Interaction) -> None:
        """
        Assigns roles depending on the response

        :param discord.Interaction interaction: The interaction in which the select calling back is attached to
        """
        # Get the user
        user = interaction.user

        # Role check
        if not isinstance(user, discord.Member) or interaction.guild is None:
            return await interaction.response.send_message(content="This command can only be used in a server!", ephemeral=True)

        status_role_dict = {status: interaction.guild.get_role(role_id)
                            for status, role_id in zip(STUDENT_STATUSES, self.role_ids)}

        # User already has roles
        for role in status_role_dict.values():
            if role is not None and role in user.roles:
                return await interaction.response.send_message(content="You already have a class status role!", ephemeral=True)

        # Non empty selection
        if len(self.item.values) > 0:
            # Assign roles
            role = status_role_dict[self.item.values[0]]

            if role is None:
                return await interaction.response.send_message(content="This prompt is outdated, please ask an officer to repost it!", ephemeral=True)

            await user.add_roles(role)
            await interaction.response.send_message(content=f"You have been assigned the \"{role.name}\" role!", ephemeral=True)


class AnnouncementsButton(discord.ui.DynamicItem[discord.ui.Button],
                          template=r"tao:ann:(?P<action>add|remove):(?P<kind>server|board):(?P<role_id>[0-9]+)"):
    # Explanation of what each role kind means, appended to the add/remove confirmation
    KIND_MESSAGES = {
        "server": "a server/TAO club announcement goes out",
        "board": "an announcement goes out in our bulletin board channel",
    }

    def __init__(self, action: str, kind: str, role_id: int, label: str):
        """
        Initialize a button that adds or removes one of the announcements roles

        :param str action: "add" or "remove"
        :param str kind: "server" or "board"
        :param int role_id: The ID of the role to add or remove
        :param str label: The label shown on the button
        """
        self.action = action
        self.kind = kind
        self.role_id = role_id

        style = discord.ButtonStyle.green if action == "add" else discord.ButtonStyle.red
        super().__init__(discord.ui.Button(
            label=label, style=style, custom_id=f"tao:ann:{action}:{kind}:{role_id}"))

    @classmethod
    async def from_custom_id(cls, interaction: discord.Interaction, item: discord.ui.Button, match: re.Match[str]):
        return cls(match["action"], match["kind"], int(match["role_id"]), item.label or "")

    async def callback(self, interaction: discord.Interaction) -> None:
        """ Add or remove the announcements role encoded in the custom_id """
        await toggle_role(interaction, self.role_id, self.action, self.KIND_MESSAGES[self.kind])


class ReviewButton(discord.ui.DynamicItem[discord.ui.Button],
                   template=r"tao:review:(?P<action>add|remove):(?P<role_id>[0-9]+)"):
    def __init__(self, action: str, role_id: int, label: str):
        """
        Initialize a button that adds or removes the TAO Review role

        :param str action: "add" or "remove"
        :param int role_id: The ID of the role to add or remove
        :param str label: The label shown on the button
        """
        self.action = action
        self.role_id = role_id

        style = discord.ButtonStyle.green if action == "add" else discord.ButtonStyle.red
        super().__init__(discord.ui.Button(
            label=label, style=style, custom_id=f"tao:review:{action}:{role_id}"))

    @classmethod
    async def from_custom_id(cls, interaction: discord.Interaction, item: discord.ui.Button, match: re.Match[str]):
        return cls(match["action"], int(match["role_id"]), item.label or "")

    async def callback(self, interaction: discord.Interaction) -> None:
        """ Add or remove the TAO review role encoded in the custom_id """
        await toggle_role(interaction, self.role_id, self.action, "a TAO review announcement goes out")


async def toggle_role(interaction: discord.Interaction, role_id: int, action: str, ping_description: str) -> None:
    """
    Shared add/remove logic for the opt-in/opt-out role buttons

    :param discord.Interaction interaction: The interaction in which the button calling back is attached to
    :param int role_id: The ID of the role to add or remove
    :param str action: "add" or "remove"
    :param str ping_description: Describes when the role gets pinged, used in the confirmation message
    """
    # Ensure role selection is done in a server
    if not isinstance(interaction.user, discord.Member) or interaction.guild is None:
        return await interaction.response.send_message(content="This role selection can only be used in a server!", ephemeral=True)

    role = interaction.guild.get_role(role_id)
    if role is None:
        return await interaction.response.send_message(content="This prompt is outdated, please ask an officer to repost it!", ephemeral=True)

    if action == "add":
        # Check if role is already added
        if role in interaction.user.roles:
            return await interaction.response.send_message(content=f"You already have the \"{role.name}\" role!", ephemeral=True)

        await interaction.user.add_roles(role)
        message = f"\"{role.name}\" has been added: you will be pinged whenever {ping_description}!"
    else:
        # Check if role is not already added
        if role not in interaction.user.roles:
            return await interaction.response.send_message(content=f"You don't have the \"{role.name}\" role!", ephemeral=True)

        await interaction.user.remove_roles(role)
        message = f"\"{role.name}\" has been removed: you will not be pinged whenever {ping_description}!"

    await interaction.response.send_message(content=message, ephemeral=True)


def announcements_view(server_role: discord.Role, board_role: discord.Role) -> discord.ui.View:
    """
    Builds the view with four buttons for adding or removing announcements roles

    :param discord.Role server_role: The announcements role regarding server/club announcements
    :param discord.Role board_role: The announcements role regarding bulletin board announcements
    """
    view = discord.ui.View(timeout=None)
    view.add_item(AnnouncementsButton("add", "server", server_role.id, "1"))
    view.add_item(AnnouncementsButton("add", "board", board_role.id, "2"))
    view.add_item(AnnouncementsButton("remove", "server", server_role.id, "3"))
    view.add_item(AnnouncementsButton("remove", "board", board_role.id, "4"))
    return view


def review_view(review_role: discord.Role) -> discord.ui.View:
    """
    Builds the view with two buttons for adding or removing the TAO Review role

    :param discord.Role review_role: The role associated with TAO Review
    """
    view = discord.ui.View(timeout=None)
    view.add_item(ReviewButton("add", review_role.id, "1"))
    view.add_item(ReviewButton("remove", review_role.id, "2"))
    return view
