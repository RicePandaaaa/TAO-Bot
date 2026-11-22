import logging
import re
import typing

import discord

from views.confirm import ConfirmView


# The only courses the server has professor prompts for
Course = typing.Literal["ENGR 102", "PHYS 216", "PHYS 217"]
COURSES: tuple[str, ...] = typing.get_args(Course)

# Students can't be in more than one PHYS course: switching from one to the other must be confirmed
PHYS_COURSES = tuple(course for course in COURSES if course.startswith("PHYS"))

# Every professor list includes this so students outside College Station have something to pick
OFF_CAMPUS = "Off-Campus"

PROF_PROMPT = ("If you are taking {course}, please choose your professor below! "
               "For those taking the course OUTSIDE of College Station, please choose \"Off-Campus\"!")

# Additional roles a student may pick up
STUDENT_STATUSES = ["Doing ETAM", "Done with ETAM", "Visiting Student", "Alumni"]
PRONOUNS = ["She/Her", "He/Him", "They/Them", "Any Pronouns", "Other Pronouns"]
PRONOUN_ROLES_KEY = "pronoun_roles"

# Opt-in ping roles, in the order their role IDs are stored in the PingsSelect custom_id
PINGS = [("Announcements", "Server and TAO club announcements"),
         ("Bulletin Board", "Posts in the bulletin board channel"),
         ("TAO Review", "TAO review session announcements")]

OUTDATED_MESSAGE = "This prompt is outdated, please ask an officer to repost it!"

# Every role menu ends with a Clear option. Deselecting also works, but only while the menu still shows the
# member's pick: once Discord reloads it shows the placeholder and an empty selection can't be sent.
CLEAR_VALUE = "__clear__"


def clear_option(label: str) -> discord.SelectOption:
    return discord.SelectOption(label=label, value=CLEAR_VALUE, description="Removes the roles this menu gave you")


def picked(values: list[str]) -> list[str]:
    """ The menu's selected values, or nothing if Clear was picked (Clear wins over anything else selected) """
    return [] if CLEAR_VALUE in values else list(values)


def class_role_key(course: str) -> str:
    """ Config key holding a course's class role ID (saved whenever its prof prompt is posted) """
    return f"class_role:{course}"


def professor_role_name(course: str, professor: str) -> str:
    """ Name of the role for a professor's students, e.g. "216 Brooks" """
    return f"{course.split(' ')[1]} {professor}"


def menu_order(professors: list[str]) -> list[str]:
    """ Professors in the order shown in the menu: alphabetical, with Off-Campus last """
    return (sorted((prof for prof in professors if prof != OFF_CAMPUS), key=str.lower)
            + ([OFF_CAMPUS] if OFF_CAMPUS in professors else []))


async def sync_menu_roles(member: discord.Member, menu_roles: list[discord.Role | None],
                          selected_roles: list[discord.Role]) -> tuple[list[discord.Role], list[discord.Role]]:
    """
    Makes the member's roles match a menu selection: adds the selected roles and removes the menu's other roles

    :param discord.Member member: The member who used the menu
    :param list menu_roles: Every role the menu controls (None entries are ignored, e.g. deleted roles)
    :param list selected_roles: The roles the member should have after the change
    :return: The roles that were added and the roles that were removed
    """
    added = [role for role in selected_roles if role not in member.roles]
    removed = [role for role in menu_roles
               if role is not None and role in member.roles and role not in selected_roles]

    if added:
        await member.add_roles(*added, reason="Role menu selection")
    if removed:
        await member.remove_roles(*removed, reason="Role menu selection")
    return added, removed


async def respond_with_sync(interaction: discord.Interaction, menu_roles: list[discord.Role | None],
                            selected_roles: list[discord.Role]) -> None:
    """ Syncs the member's roles to their selection and tells them (privately) what changed """
    assert isinstance(interaction.user, discord.Member)

    # Role edits can be slow, so acknowledge the interaction before Discord's 3 second limit
    # (unless it was already answered, e.g. by the PHYS switch confirmation)
    if not interaction.response.is_done():
        await interaction.response.defer(ephemeral=True, thinking=True)

    try:
        added, removed = await sync_menu_roles(interaction.user, menu_roles, selected_roles)
    except discord.HTTPException:
        logging.exception("Failed to update menu roles for %s", interaction.user)
        await interaction.followup.send("Something went wrong updating your roles, please let an officer know!", ephemeral=True)
        return

    def names(roles: list[discord.Role]) -> str:
        return ", ".join(f"\"{role.name}\"" for role in roles)

    changes = []
    if added:
        changes.append(f"Added {names(added)}")
    if removed:
        changes.append(f"Removed {names(removed)}")
    message = ". ".join(changes) + "." if changes else "Nothing changed, your roles already match your selection!"

    await interaction.followup.send(message, ephemeral=True)


class ProfSelect(discord.ui.DynamicItem[discord.ui.Select],
                 template=r"tao:prof:(?P<class_role_id>[0-9]+):(?P<class_name>.+)"):
    def __init__(self, class_name: str, class_role_id: int, professors: list[str]):
        """
        Initializes the select menu with professors associated with a certain class.
        Picking a professor gives the class role and that professor's role, replacing an earlier pick;
        picking Clear (or deselecting) removes them.

        :param str class_name: The name of the class they teach (e.g. "PHYS 216")
        :param int class_role_id: The ID of the role associated with the class
        :param list[str] professors: A list of professor last names (e.g. "Brooks")
        """
        self.class_name = class_name
        self.class_role_id = class_role_id

        super().__init__(discord.ui.Select(
            options=[discord.SelectOption(label=prof if prof == OFF_CAMPUS else f"Professor {prof}", value=prof)
                     for prof in menu_order(professors)] + [clear_option("--- CLEAR ROLE ---")],
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

    @staticmethod
    async def course_roles(interaction: discord.Interaction, course: str,
                           class_role: discord.Role | None = None) -> list[discord.Role | None]:
        """ A course's class role and all of its professor roles """
        guild = interaction.guild
        assert guild is not None

        if class_role is None:
            # Saved when the course's prompt is posted; fall back to a role named after the course
            role_id = await interaction.client.db.get_config_id(class_role_key(course))  # type: ignore[attr-defined]
            class_role = guild.get_role(role_id) if role_id is not None else discord.utils.get(guild.roles, name=course)

        professors = await interaction.client.db.get_professors(course)  # type: ignore[attr-defined]
        return [class_role] + [discord.utils.get(guild.roles, name=professor_role_name(course, prof)) for prof in professors]

    async def callback(self, interaction: discord.Interaction):
        """
        Assigns roles depending on the response

        :param discord.Interaction interaction: The interaction in which the select calling back is attached to
        """
        # Role check
        if not isinstance(interaction.user, discord.Member) or interaction.guild is None:
            return await interaction.response.send_message(content="This command can only be used in a server!", ephemeral=True)

        class_role = interaction.guild.get_role(self.class_role_id)
        if class_role is None:
            return await interaction.response.send_message(content=OUTDATED_MESSAGE, ephemeral=True)

        menu_roles = await self.course_roles(interaction, self.class_name, class_role)
        selected_roles = []

        values = picked(self.item.values)
        if values:
            # Menus posted before professor values existed use the "Professor X" label as the value
            prof = values[0].removeprefix("Professor ")

            # The professor may have been removed from the list since this prompt was posted
            current_professors = await interaction.client.db.get_professors(self.class_name)  # type: ignore[attr-defined]
            prof_role = discord.utils.get(interaction.guild.roles, name=professor_role_name(self.class_name, prof))
            if prof not in current_professors or prof_role is None:
                return await interaction.response.send_message(content=OUTDATED_MESSAGE, ephemeral=True)

            selected_roles = [class_role, prof_role]

            # Nobody can take both PHYS courses at once: switching must be confirmed explicitly
            if self.class_name in PHYS_COURSES:
                for other in PHYS_COURSES:
                    if other == self.class_name:
                        continue

                    other_roles = [role for role in await self.course_roles(interaction, other)
                                   if role is not None and role in interaction.user.roles]
                    if not other_roles:
                        continue

                    if not await self.confirm_switch(interaction, other, prof):
                        return
                    menu_roles += other_roles

        await respond_with_sync(interaction, menu_roles, selected_roles)

    async def confirm_switch(self, interaction: discord.Interaction, current: str, prof: str) -> bool:
        """ Tells the member they can't be in both PHYS courses and asks whether to switch. True if they confirm """
        choice = OFF_CAMPUS if prof == OFF_CAMPUS else f"Professor {prof}"
        view = ConfirmView(interaction.user.id)
        await interaction.response.send_message(
            content=f"You can't be in **{current}** and **{self.class_name}** at the same time, and you're currently in {current}.\n"
                    f"Press **Confirm** to leave {current} and switch to {self.class_name} ({choice}), or **Cancel** to stay in {current}.",
            view=view, ephemeral=True)
        await view.wait()

        if view.value is None:
            await interaction.edit_original_response(content="Timed out, nothing was changed.", view=None)
        return bool(view.value)


class StudentSelect(discord.ui.DynamicItem[discord.ui.Select],
                    template=r"tao:student:(?P<role_ids>[0-9]+(?::[0-9]+)*)"):
    def __init__(self, role_ids: list[int]) -> None:
        """
        Initialize the select menu with the names of potential student statuses.
        Picking a status replaces an earlier pick; picking Clear (or deselecting) removes it.

        :param list[int] role_ids: The role IDs matching STUDENT_STATUSES, in order
        """
        self.role_ids = role_ids

        super().__init__(discord.ui.Select(
            options=[discord.SelectOption(label=status) for status in STUDENT_STATUSES] + [clear_option("--- CLEAR ROLE ---")],
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
        # Role check
        if not isinstance(interaction.user, discord.Member) or interaction.guild is None:
            return await interaction.response.send_message(content="This command can only be used in a server!", ephemeral=True)

        status_roles = {status: interaction.guild.get_role(role_id)
                        for status, role_id in zip(STUDENT_STATUSES, self.role_ids)}

        selected_roles = [status_roles[status] for status in picked(self.item.values)]
        if None in selected_roles:
            return await interaction.response.send_message(content=OUTDATED_MESSAGE, ephemeral=True)

        await respond_with_sync(interaction, list(status_roles.values()), selected_roles)  # type: ignore[arg-type]


class PronounsSelect(discord.ui.DynamicItem[discord.ui.Select],
                 template=r"tao:pronouns:(?P<guild_id>\d+)"):
    def __init__(self, guild_id: int, role_ids: list[int]) -> None:
        """
        Initialize the select menu with the names of pronouns

        :param int guild_id: The guild's ID
        :param list[int] role_ids: The role IDs matching PRONOUNS, in order (stored under PRONOUN_ROLES_KEY)
        """
        self.role_ids = role_ids
        self.guild_id = guild_id

        super().__init__(discord.ui.Select(
            options=[discord.SelectOption(label=pronouns) for pronouns in PRONOUNS] + [clear_option("--- CLEAR ROLES ---")],
            min_values=0,
            max_values=3,
            placeholder="-- SELECT YOUR PRONOUNS --",
            custom_id=f"tao:pronouns:{guild_id}"))

    @classmethod
    async def from_custom_id(cls, interaction: discord.Interaction, item: discord.ui.Select, match: re.Match[str]):
        stored = await interaction.client.db.get_config(PRONOUN_ROLES_KEY)  # type: ignore[attr-defined]
        role_ids = [int(role_id) for role_id in stored.split(",")] if stored else []
        return cls(int(match["guild_id"]), role_ids)

    async def callback(self, interaction: discord.Interaction) -> None:
        """
        Assigns roles depending on the response

        :param discord.Interaction interaction: The interaction in which the select calling back is attached to
        """
        # Guild check
        if not isinstance(interaction.user, discord.Member) or interaction.guild is None:
            return await interaction.response.send_message(content="This command can only be used in a server!", ephemeral=True)

        pronoun_roles = {pronouns: interaction.guild.get_role(role_id)
                         for pronouns, role_id in zip(PRONOUNS, self.role_ids)}

        # Roles were never stored, or one has since been deleted
        if len(pronoun_roles) != len(PRONOUNS) or None in pronoun_roles.values():
            return await interaction.response.send_message(content=OUTDATED_MESSAGE, ephemeral=True)

        selected_roles = [pronoun_roles[pronouns] for pronouns in picked(self.item.values)]
        await respond_with_sync(interaction, list(pronoun_roles.values()), selected_roles)  # type: ignore[arg-type]


class PingsSelect(discord.ui.DynamicItem[discord.ui.Select],
                  template=r"tao:pings:(?P<role_ids>[0-9]+:[0-9]+:[0-9]+)"):
    def __init__(self, role_ids: list[int]) -> None:
        """
        Initialize the select menu for the opt-in ping roles. Any combination is allowed: the member ends up
        with exactly the pings they selected.

        :param list[int] role_ids: The role IDs matching PINGS, in order
        """
        self.role_ids = role_ids

        super().__init__(discord.ui.Select(
            options=[discord.SelectOption(label=label, description=description) for label, description in PINGS]
                    + [clear_option("--- CLEAR ROLES ---")],
            min_values=0,
            max_values=len(PINGS),
            placeholder="-- SELECT YOUR PINGS --",
            custom_id=f"tao:pings:{':'.join(str(role_id) for role_id in role_ids)}"))

    @classmethod
    async def from_custom_id(cls, interaction: discord.Interaction, item: discord.ui.Select, match: re.Match[str]):
        return cls([int(role_id) for role_id in match["role_ids"].split(":")])

    async def callback(self, interaction: discord.Interaction) -> None:
        """ Gives the selected ping roles and removes the unselected ones """
        if not isinstance(interaction.user, discord.Member) or interaction.guild is None:
            return await interaction.response.send_message(content="This command can only be used in a server!", ephemeral=True)

        ping_roles = {label: interaction.guild.get_role(role_id) for (label, _), role_id in zip(PINGS, self.role_ids)}

        selected_roles = [ping_roles[label] for label in picked(self.item.values)]
        if None in selected_roles:
            return await interaction.response.send_message(content=OUTDATED_MESSAGE, ephemeral=True)

        await respond_with_sync(interaction, list(ping_roles.values()), selected_roles)  # type: ignore[arg-type]


# The opt-in/opt-out buttons below were replaced by PingsSelect (`/post pings`). They stay registered
# so already-posted button prompts keep working until they are replaced; remove them after that.
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
