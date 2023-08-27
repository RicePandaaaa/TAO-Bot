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
        self.PLACEHOLDER = "---"
        self.CUSTOM_ID = class_name

        self.prof_roles_dict = dict(zip([f"Professor {prof}" for prof in professors], prof_roles))
        self.class_role = class_role

        # Initialize with the above values
        super().__init__(options=[ discord.SelectOption(label=f"Professor {prof}") for prof in professors ],
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
            if role.name == self.CUSTOM_ID:
                return await interaction.response.send_message(content=f"You already chose your roles for {self.CUSTOM_ID}!", ephemeral=True)
            
            # Already has any physics role
            if role.name.startswith("PHYS"):
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





