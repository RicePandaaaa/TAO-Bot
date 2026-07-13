import io
import typing
from collections import defaultdict
from datetime import datetime, timedelta

import matplotlib
matplotlib.use("Agg")  # Headless host, no display
import matplotlib.pyplot as plt

import discord
from discord.ext import commands, tasks
from discord.ext.commands import Context

from db import CENTRAL

Period = typing.Literal["week", "month", "semester"]
PERIOD_DAYS = {"week": 7, "month": 30, "semester": 120}
DAY_NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


class Stats(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

        # Message counts pending flush, keyed by (channel_id, 'YYYY-MM-DDTHH:00' Central time)
        self.pending: dict[tuple[int, str], int] = defaultdict(int)
        self.flush_pending.start()

    async def cog_unload(self):
        self.flush_pending.cancel()
        await self.flush()

    # ---------- Collection ----------

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        # Only count human messages inside the server (no content is ever stored)
        if message.author.bot or message.guild is None:
            return

        hour_ts = datetime.now(CENTRAL).strftime("%Y-%m-%dT%H:00")
        self.pending[(message.channel.id, hour_ts)] += 1

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        await self.bot.db.add_member_event(joined=True)

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        await self.bot.db.add_member_event(joined=False)

    @tasks.loop(seconds=60)
    async def flush_pending(self):
        await self.flush()

    @flush_pending.before_loop
    async def before_flush(self):
        await self.bot.wait_until_ready()

    async def flush(self):
        if not self.pending:
            return

        counts, self.pending = self.pending, defaultdict(int)
        await self.bot.db.add_message_counts(counts)

    # ---------- Helpers ----------

    def since(self, period: str) -> str:
        """ The 'YYYY-MM-DD' Central-time date where the given period starts """
        return (datetime.now(CENTRAL) - timedelta(days=PERIOD_DAYS[period])).strftime("%Y-%m-%d")

    def render_chart(self, fig) -> discord.File:
        """ Renders a matplotlib figure into a Discord file attachment """
        buffer = io.BytesIO()
        fig.savefig(buffer, format="png", dpi=150, bbox_inches="tight")
        plt.close(fig)
        buffer.seek(0)
        return discord.File(buffer, filename="chart.png")

    async def send_chart(self, ctx: Context, embed: discord.Embed, fig) -> None:
        file = self.render_chart(fig)
        embed.set_image(url="attachment://chart.png")
        await ctx.send(embed=embed, file=file)

    def daily_chart(self, days: list[str], totals: list[int], title: str):
        """ Builds a messages-per-day line chart """
        fig, ax = plt.subplots(figsize=(10, 4))
        ax.plot(days, totals, marker="o", color="#500000")  # Maroon, of course
        ax.set_title(title)
        ax.set_ylabel("Messages")
        ax.grid(True, alpha=0.3)
        ax.margins(y=0.1)

        # Avoid unreadable x-axis when the period is long
        step = max(1, len(days) // 14)
        ax.set_xticks(range(0, len(days), step))
        fig.autofmt_xdate(rotation=45)
        return fig

    # ---------- Commands ----------

    @commands.hybrid_group(fallback="server", invoke_without_command=True)
    @commands.has_any_role("TAO Officer")
    async def stats(self, ctx: Context,
                    period: Period = commands.parameter(default="week", description="How far back to look")):
        """ Shows server-wide message activity for the given period """

        await ctx.defer()
        since = self.since(period)

        rows = await self.bot.db.messages_per_day(since)
        if not rows:
            await ctx.send("No message activity has been recorded for this period yet!")
            return

        days = [day for day, _ in rows]
        totals = [total for _, total in rows]
        top = await self.bot.db.top_channels(since, limit=5)

        embed = discord.Embed(color=discord.Color.dark_red())
        embed.set_author(name=f"Server Activity — last {period}")
        embed.add_field(name="Total Messages", value=f"{sum(totals):,}")
        embed.add_field(name="Daily Average", value=f"{sum(totals) / len(totals):,.1f}")
        busiest_day, busiest_total = max(rows, key=lambda row: row[1])
        embed.add_field(name="Busiest Day", value=f"{busiest_day} ({busiest_total:,})")
        embed.add_field(name="Most Active Channels",
                        value="\n".join(f"<#{channel_id}>: {total:,}" for channel_id, total in top),
                        inline=False)

        await self.send_chart(ctx, embed, self.daily_chart(days, totals, f"Messages per day — last {period}"))

    @stats.command()
    @commands.has_any_role("TAO Officer")
    async def channel(self, ctx: Context,
                      channel: discord.TextChannel = commands.parameter(description="The channel to look at"),
                      period: Period = commands.parameter(default="week", description="How far back to look")):
        """ Shows message activity for one channel for the given period """

        await ctx.defer()
        rows = await self.bot.db.messages_per_day(self.since(period), channel_id=channel.id)

        if not rows:
            await ctx.send(f"No message activity has been recorded in {channel.mention} for this period yet!")
            return

        days = [day for day, _ in rows]
        totals = [total for _, total in rows]

        embed = discord.Embed(color=discord.Color.dark_red())
        embed.set_author(name=f"#{channel.name} Activity — last {period}")
        embed.add_field(name="Total Messages", value=f"{sum(totals):,}")
        embed.add_field(name="Daily Average", value=f"{sum(totals) / len(totals):,.1f}")
        busiest_day, busiest_total = max(rows, key=lambda row: row[1])
        embed.add_field(name="Busiest Day", value=f"{busiest_day} ({busiest_total:,})")

        await self.send_chart(ctx, embed, self.daily_chart(days, totals, f"#{channel.name} — messages per day, last {period}"))

    @stats.command()
    @commands.has_any_role("TAO Officer")
    async def growth(self, ctx: Context,
                     period: Period = commands.parameter(default="month", description="How far back to look")):
        """ Shows member joins and leaves for the given period """

        await ctx.defer()
        rows = await self.bot.db.member_events_per_day(self.since(period))

        if not rows:
            await ctx.send("No member joins or leaves have been recorded for this period yet!")
            return

        days = [day for day, _, _ in rows]
        joins = [join_count for _, join_count, _ in rows]
        leaves = [leave_count for _, _, leave_count in rows]
        net = [join_count - leave_count for join_count, leave_count in zip(joins, leaves)]

        fig, ax = plt.subplots(figsize=(10, 4))
        positions = range(len(days))
        ax.bar([p - 0.2 for p in positions], joins, width=0.4, label="Joins", color="#2e7d32")
        ax.bar([p + 0.2 for p in positions], leaves, width=0.4, label="Leaves", color="#c62828")
        ax.plot(positions, net, marker="o", label="Net", color="#500000")
        ax.set_title(f"Member joins and leaves — last {period}")
        ax.legend()
        ax.grid(True, alpha=0.3)

        step = max(1, len(days) // 14)
        ax.set_xticks(range(0, len(days), step))
        ax.set_xticklabels(days[::step])
        fig.autofmt_xdate(rotation=45)

        embed = discord.Embed(color=discord.Color.dark_red())
        embed.set_author(name=f"Server Growth — last {period}")
        embed.add_field(name="Joins", value=f"{sum(joins):,}")
        embed.add_field(name="Leaves", value=f"{sum(leaves):,}")
        embed.add_field(name="Net Change", value=f"{sum(net):+,}")
        if ctx.guild is not None:
            embed.add_field(name="Current Members", value=f"{ctx.guild.member_count:,}")

        await self.send_chart(ctx, embed, fig)

    @stats.command()
    @commands.has_any_role("TAO Officer")
    async def heatmap(self, ctx: Context,
                      weeks: int = commands.parameter(default=4, description="How many weeks back to look")):
        """ Shows a day-of-week by hour-of-day heatmap of message activity (prime time finder) """

        await ctx.defer()
        since = (datetime.now(CENTRAL) - timedelta(weeks=weeks)).strftime("%Y-%m-%d")
        rows = await self.bot.db.heatmap_counts(since)

        if not rows:
            await ctx.send("No message activity has been recorded for this period yet!")
            return

        grid = [[0] * 24 for _ in range(7)]
        for dow, hour, total in rows:
            grid[dow][hour] = total

        fig, ax = plt.subplots(figsize=(12, 4))
        image = ax.imshow(grid, aspect="auto", cmap="YlOrRd")
        ax.set_title(f"Message activity by day and hour — last {weeks} week(s), Central time")
        ax.set_yticks(range(7))
        ax.set_yticklabels(DAY_NAMES)
        ax.set_xticks(range(0, 24, 2))
        ax.set_xticklabels([f"{hour}:00" for hour in range(0, 24, 2)])
        fig.colorbar(image, ax=ax, label="Messages")

        prime_dow, prime_hour, prime_total = max(rows, key=lambda row: row[2])

        embed = discord.Embed(color=discord.Color.dark_red())
        embed.set_author(name=f"Activity Heatmap — last {weeks} week(s)")
        embed.add_field(name="Prime Time",
                        value=f"{DAY_NAMES[prime_dow]} {prime_hour}:00–{prime_hour + 1}:00 ({prime_total:,} messages)")

        await self.send_chart(ctx, embed, fig)


async def setup(bot):
    await bot.add_cog(Stats(bot))
