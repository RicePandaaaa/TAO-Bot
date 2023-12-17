import discord

class ProfSelect(discord.ui.Select):
    def __init__(self, professors: list[str], prof_roles: list[discord.Role], class_name: str, class_role: discord.Role):
        """ 
        Initializes the select menu with professors associated with a certain class 

        :param list[str] professors: A list of professor names
        :param str class_name: The name of the class they teach
        """        
        self.MIN_VALUES = 0
        self.MAX_VALUES = 1
        self.PLACEHOLDER = "---- SELECT PROF ----"
        self.CUSTOM_ID = class_name

        self.prof_roles_dict = dict(zip([f"Professor {prof.split(' ')[1]}" for prof in professors], prof_roles))
        self.class_role = class_role

        # Initialize with the above values
        super().__init__(options=[ discord.SelectOption(label=f"Professor {prof.split(' ')[1]}") for prof in professors ],
                         min_values=self.MIN_VALUES,
                         max_values=self.MAX_VALUES,
                         placeholder=self.PLACEHOLDER,
                         custom_id=self.CUSTOM_ID)
        
    async def callback(self, interaction: discord.Interaction):
        """
        Assigns roles depending on the response

        :param discord.Interaction interaction: The interaction in which the button calling back is attached to
        """
        # Get user
        user = interaction.user
    
        # Role check
        for role in user.roles:
            # Duplicate role check
            if role.name == self.class_role.name:
                return await interaction.response.send_message(content=f"You already chose your roles for {role.name}!", ephemeral=True)
            
            # Already has any physics role
            if self.CUSTOM_ID.startswith("PHYS") and role.name.startswith("PHYS"):
                return await interaction.response.send_message(content="You already have PHYS roles assigned to you!", ephemeral=True)

        # Non empty selection
        if len(self.values) > 0:
            class_role = self.class_role
            prof_role = self.prof_roles_dict[self.values[0]]

            # Professors can teach multiple courses, avoid double assigning a professor role
            if prof_role not in user.roles:
                await user.add_roles(prof_role)

            # Assign class role and inform user of assigned roles
            await user.add_roles(class_role)
            await interaction.response.send_message(content=f"You have been assigned \"{class_role.name}\" and \"{prof_role}\"!", ephemeral=True)


class YearSelect(discord.ui.Select):
    def __init__(self, student_statuses: list[str], roles: list[discord.Role]) -> None:
        """
        Initialize the select menu with the names of potential roles

        :param list[str] role_names: List of names of the potential student statuses
        :param list[discord.Role] roles: List of actual roles associated with the names
        """
        
        self.status_role_dict = dict(zip(student_statuses, roles))
        self.MIN_VALUES = 0
        self.MAX_VALUES = 1
        self.PLACEHOLDER = "-- SELECT YOUR ROLE --"

        super().__init__(options=[discord.SelectOption(label=status) for status in student_statuses],
                         min_values=self.MIN_VALUES,
                         max_values=self.MAX_VALUES,
                         placeholder=self.PLACEHOLDER)
        
    async def callback(self, interaction: discord.Interaction) -> None:
        """
        Assigns roles depending on the response

        :param discord.Interaction interaction: The interaction in which the button calling back is attached to
        """
        # Get the user
        user = interaction.user
        
        # User already has roles
        for role in self.status_role_dict.values():
            if role in user.roles:
                return await interaction.response.send_message(content="You already have a class status role!", ephemeral=True)

        # Non empty selection
        if len(self.values) > 0:
            # Assign roles
            role = self.status_role_dict[self.values[0]]
            await user.add_roles(role)
            await interaction.response.send_message(content=f"You have been assigned the \"{role.name}\" role!", ephemeral=True)


class AnnouncementsView(discord.ui.View):
    def __init__(self, server_role: discord.Role, board_role: discord.Role):
        """
        Initialize the view with four buttons for adding or removing announcements roles

        :param discord.Role server_role: The announcements role regarding server/club announcements
        :param discord.Role board_role: The announcements role regarding bulletin board announcements
        """
        super().__init__(timeout=None)
        self.server_role = server_role
        self.board_role = board_role

    # Add the four buttons and link them to their callback functions
    @discord.ui.button(label="1", style=discord.ButtonStyle.green)
    async def add_server_role(self, interaction: discord.Interaction, button: discord.Button):
        """
        Add the role attached to server_role if already not added
        """
        # Check if role is already added
        if self.server_role in interaction.user.roles:
            return await interaction.response.send_message(content=f"You already have the \"{self.server_role.name}\" role!", ephemeral=True)
        
        await interaction.user.add_roles(self.server_role)
        message = f"\"{self.server_role.name}\" has been added: you will be pinged whenever a server/TAO club announcement goes out!"
        await interaction.response.send_message(content=message, ephemeral=True)

    @discord.ui.button(label="2", style=discord.ButtonStyle.green)
    async def add_board_role(self, interaction: discord.Interaction, button: discord.Button):
        """
        Add the role attached to board_role if already not added
        """
        # Check if role is already added
        if self.board_role in interaction.user.roles:
            return await interaction.response.send_message(content=f"You already have the \"{self.board_role.name}\" role!", ephemeral=True)
        
        await interaction.user.add_roles(self.board_role)
        message = f"\"{self.board_role.name}\" has been added: you will be pinged whenever an announcement goes out in our bulletin board channel!"
        await interaction.response.send_message(content=message, ephemeral=True)

    @discord.ui.button(label="3", style=discord.ButtonStyle.red)
    async def remove_server_role(self, interaction: discord.Interaction, button: discord.Button):
        """
        Remove the role attached to server_role if already added
        """
        # Check if role is not already added
        if self.server_role not in interaction.user.roles:
            return await interaction.response.send_message(content=f"You don't have the \"{self.server_role.name}\" role!", ephemeral=True)
        
        await interaction.user.remove_roles(self.server_role)
        message = f"\"{self.server_role.name}\" has been removed: you will not be pinged whenever a server/TAO club announcement goes out!"
        await interaction.response.send_message(content=message, ephemeral=True)

    @discord.ui.button(label="4", style=discord.ButtonStyle.red)
    async def remove_board_role(self, interaction: discord.Interaction, button: discord.Button):
        """
        Remove the role attached to board_role if already added
        """
        # Check if role is not already added
        if self.board_role not in interaction.user.roles:
            return await interaction.response.send_message(content=f"You don't have the \"{self.board_role.name}\" role!", ephemeral=True)
        
        await interaction.user.remove_roles(self.board_role)
        message = f"\"{self.board_role.name}\" has been removed: you will not be pinged whenever an announcement goes out in our bulletin board channel!"
        await interaction.response.send_message(content=message, ephemeral=True)

    async def has_role(self, role: discord.Role, user: discord.User) -> bool:
        return role in user.roles

class ReviewView(discord.ui.View):
    def __init__(self, review_role: discord.Role):
        """
        Initialize the view with two buttons for adding or removing TAO Review role

        :param discord.Role review_role: The role associated with TAO Review
        """
        super().__init__(timeout=None)
        self.review_role = review_role

    # Add the four buttons and link them to their callback functions
    @discord.ui.button(label="1", style=discord.ButtonStyle.green)
    async def add_review_role(self, interaction: discord.Interaction, button: discord.Button):
        """
        Add the role attached to server_role if already not added
        """
        # Check if role is already added
        if self.review_role in interaction.user.roles:
            return await interaction.response.send_message(content=f"You already have the \"{self.review_role}\" role!", ephemeral=True)
        
        await interaction.user.add_roles(self.review_role)
        message = f"\"{self.review_role.name}\" has been added: you will be pinged whenever a TAO review announcement goes out!"
        await interaction.response.send_message(content=message, ephemeral=True)

    @discord.ui.button(label="2", style=discord.ButtonStyle.red)
    async def remove_review_role(self, interaction: discord.Interaction, button: discord.Button):
        """
        Remove the role attached to server_role if already added
        """
        # Check if role is not already added
        if self.review_role not in interaction.user.roles:
            return await interaction.response.send_message(content=f"You don't have the \"{self.review_role.name}\" role!", ephemeral=True)
        
        await interaction.user.remove_roles(self.review_role)
        message = f"\"{self.review_role.name}\" has been removed: you will not be pinged whenever a TAO review announcement goes out!"
        await interaction.response.send_message(content=message, ephemeral=True)


