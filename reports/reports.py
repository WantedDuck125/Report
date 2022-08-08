import asyncio
import datetime
import pathlib
import discord
import discord.utils
from discord.ext import commands
import os.path
import json
import time

class Reports(commands.Cog):
    @staticmethod
    class Info:
        prefix = "?"
        embed_color = discord.Color.from_rgb(0, 0, 0)
        report_channel = 0
        cases_file_location = "reports.json"

    class PagesInstance:
        message: discord.Message
        cases_arr: str
        parsed_json: json
        page_index = 0
        user: int = -1

        async def start(self):
            await asyncio.sleep(300)
            embed = await Reports.gen_case_embed(self.parsed_json, self.cases_arr[self.page_index])
            embed.set_footer(text="You can't use this menu anymore, create a new one by using the command again.")
            await self.message.edit(view=Reports.DisabledReportButtons(), embed=embed)
            self.__del__()

        def __del__(self):
            Reports.pages_dict.pop(self.message.id)

    pages_dict: {str: PagesInstance} = {}
    client: discord.ext.commands.Bot = None

    class DisabledReportButtons(discord.ui.View):
        @discord.ui.button(label="left", style=discord.ButtonStyle.blurple, disabled=True)
        async def left(self, __, _):
            pass

        @discord.ui.button(label="right", style=discord.ButtonStyle.blurple, disabled=True)
        async def right(self, __, _):
            pass

    class ReportButtons(discord.ui.View):
        @discord.ui.button(label="left", style=discord.ButtonStyle.blurple)
        async def left(self, interaction: discord.Interaction, _):
            await Reports.left_button(interaction)

        @discord.ui.button(label="right", style=discord.ButtonStyle.blurple)
        async def right(self, interaction: discord.Interaction, _):
            await Reports.right_button(interaction)

    class ReportButtonLeft(discord.ui.View):
        @discord.ui.button(label="left", style=discord.ButtonStyle.blurple)
        async def left(self, interaction: discord.Interaction, _):
            await Reports.left_button(interaction)

    class ReportButtonRight(discord.ui.View):
        @discord.ui.button(label="right", style=discord.ButtonStyle.blurple)
        async def right(self, interaction: discord.Interaction, _):
            await Reports.right_button(interaction)

    @staticmethod
    async def right_button(interaction: discord.Interaction):
        response: discord.InteractionResponse = interaction.response
        instance: Reports.PagesInstance = Reports.pages_dict[interaction.message.id]
        if instance.user != interaction.user.id:
            await response.send_message(
                "You can't interact with other messages, use the command to be able to see the reports by yourself.",
                ephemeral=True)
            return
        instance.page_index += 1
        embed: discord.Embed = await Reports.gen_case_embed(instance.parsed_json, instance.cases_arr[instance.page_index])
        results = len(instance.cases_arr)
        embed.title = "Your search returned {0} results".format(results)
        embed.set_footer(text="you are in page {0} of {1} pages".format(instance.page_index + 1, results))
        if instance.page_index == len(instance.cases_arr) - 1:
            await response.edit_message(view=Reports.ReportButtonLeft(), embed=embed)
        else:
            await response.edit_message(view=Reports.ReportButtons(), embed=embed)

    @staticmethod
    async def left_button(interaction: discord.Interaction):
        response: discord.InteractionResponse = interaction.response
        instance: Reports.PagesInstance = Reports.pages_dict[interaction.message.id]
        if instance.user != interaction.user.id:
            await response.send_message(
                "You can't interact with other messages, use the command to be able to see the reports by yourself.",
                ephemeral=True)
            return
        instance.page_index -= 1
        embed: discord.Embed = await Reports.gen_case_embed(instance.parsed_json, instance.cases_arr[instance.page_index])
        results = len(instance.cases_arr)
        embed.title = "Your search returned {0} results".format(results)
        embed.set_footer(text="you are in page {0} of {1} pages".format(instance.page_index + 1, results))
        if instance.page_index == 0:
            await response.edit_message(view=Reports.ReportButtonRight(), embed=embed)
        else:
            await response.edit_message(view=Reports.ReportButtons(), embed=embed)

    @staticmethod
    async def gen_case_embed(parsed_json, case_num) -> discord.Embed:
        parsed_case = parsed_json[case_num]
        seconds = int(parsed_case["ban_length"]) / 1000 if int(parsed_case["ban_length"]) != 0 else 0
        date_time = datetime.datetime.fromtimestamp(int(parsed_case["date"]))
        user_id = await Reports.return_user_if_exists(int(parsed_case["user_id"])) if await Reports.return_user_if_exists(int(parsed_case["user_id"])) is not None else "This user was not found."
        mod_id = await Reports.return_user_if_exists(int(parsed_case["mod_id"])) if await Reports.return_user_if_exists(int(parsed_case["mod_id"])) is not None else "This case isn't closed yet."
        return discord.Embed(color=Reports.Info.embed_color, description="```Case: {8}\nUser: {0}\nModerator: {1}\nSteamID64: {2}\nAll the offenses: {7}\n{3}Date: {4}\nReason: {5}\nNotes: {6}```".format(
                                 user_id,
                                 mod_id,
                                 parsed_case["user_steam_id"],
                                 "Ban length: {0}d {1:02d}h:{2:02d}m:{3:02d}s\n".format(int(seconds / 86400), int((seconds / 3600) % 24), int((seconds / 60)) % 60, int(seconds) % 60) if seconds != 0 else "",
                                 "{1:02d}/{0:02d}/{2} {3:02d}:{4:02d}:{5:02d}".format(date_time.day, date_time.month, date_time.year, date_time.hour, date_time.minute,date_time.second),
                                 parsed_case["reason"] if parsed_case["reason"] != "0" else "This case is not closed yet.",
                                 parsed_case["notes"],
                                 sum(1 if parsed_json[case]["user_id"] == parsed_case["user_id"] else 0 for case in parsed_json),
                                 case_num
                             ))

    @staticmethod
    def add_case(user_id, user_steam_id, notes) -> str:
        open_file = open(Reports.Info.cases_file_location, "r+")
        parsed_file = json.load(open_file)
        last_key = -1
        if parsed_file:
            last_key = sorted(parsed_file.keys())[-1]
        parsed_file[str(int(last_key) + 1)] = {
            "user_id": user_id,
            "mod_id": "0",
            "user_steam_id": user_steam_id,
            "ban_length": "0",
            "date": str(int(time.time())),
            "reason": "0",
            "notes": notes
        }
        open_file.seek(0)
        json.dump(parsed_file, open_file, indent=2)
        open_file.close()
        return str(int(last_key) + 1)

    @staticmethod
    async def return_user_if_exists(user_id) -> discord.User:
        user = None
        try:
            user = await Reports.client.fetch_user(user_id)
        except(Exception,):
            pass
        return user

    @staticmethod
    def return_channel_if_exists(guild_id, channel_id) -> discord.TextChannel:
        channel = None
        try:
            channel = discord.utils.get(Reports.client.get_guild(guild_id).channels, id=channel_id)
        except(Exception,):
            pass
        return channel

    def __init__(self, c):
        self.client = c

    @commands.Cog.listener()
    async def on_ready(self):
        config_path = pathlib.Path.joinpath(pathlib.Path(__file__).parent.resolve(), "config.json")
        if not os.path.exists(self.Info.cases_file_location):
            file = open(Reports.Info.cases_file_location, "a")
            file.write("{\n\n}")
            file.close()
        if not os.path.exists(config_path):
            file = open(config_path, "a")
            file.seek(0)
            config_data = {"prefix": "?", "embed_color": {"R": 200, "G": 70, "B": 0}, "report_channel": 768785719363256330, "cases_file_location": "reports.json"}
            json.dump(config_data, file, indent=2)
            file.close()
        config_file = json.loads(open(config_path, "r").read())
        Reports.Info.prefix = config_file["prefix"]
        Reports.Info.embed_color = discord.Color.from_rgb(config_file["embed_color"]["R"], config_file["embed_color"]["G"], config_file["embed_color"]["B"])
        Reports.Info.report_channel = config_file["report_channel"]
        Reports.Info.cases_file_location = config_file["cases_file_location"]
        print("configuration for Memw.reports.py loaded.")

    @commands.command()
    async def reports(self, ctx: commands.context.Context):
        args = ctx.message.content.lower().split(" ")
        if args[1] == "report":
            args_dict: {str: str} = {}
            try:
                i = 2
                while i < len(args):
                    if args[i] == "":
                        i += 1
                        continue
                    split_args = args[i].split("=")
                    if split_args[0] == "notes":
                        str_data = ""
                        curr_str = split_args[1].replace("\"", "")
                        i += 1
                        while not curr_str.endswith("\"") and i < len(args):
                            str_data += curr_str + " "
                            curr_str = args[i]
                            i += 1
                        str_data += curr_str.replace("\"", "")
                        args_dict[split_args[0]] = str_data
                    else:
                        args_dict[split_args[0]] = split_args[1]
                        i += 1
                if await Reports.return_user_if_exists(args_dict["user_id"]):
                    case_id = Reports.add_case(args_dict["user_id"], args_dict["user_steam_id"], args_dict["notes"] if args_dict["notes"] else "Any observation was provided.")
                    embed = discord.Embed(color=Reports.Info.embed_color, title="Report issued correctly", description="The following data was issued\n```Case: {0}\nUser: {1}\nSteamID64: {2}\nNotes: {3}```".format(
                        case_id,
                        await Reports.return_user_if_exists(args_dict["user_id"]),
                        args_dict["user_steam_id"],
                        args_dict["notes"] if args_dict["notes"] else "Any observation was provided."))
                    await ctx.reply(embed=embed, mention_author=False)
                    embed.title = f'A report was sent by {ctx.author}'
                    rp_channel = Reports.return_channel_if_exists(ctx.guild.id, Reports.Info.report_channel)
                    if rp_channel is not None:
                        await rp_channel.send(embed=embed)
                    else:
                        print("Reports channel ID is not correct.")
                else:
                    raise Exception("")
            except (Exception,):
                await ctx.reply(
                    "Your report isn't valid, it must contain\n```user_id=0 // the reported user discord id\nuser_steam_id=0 // the reported user steam ID 64\n(optional) notes=\"abc\" //notes you need to let the staff team know.```\nOther arguments are not valid and will be ignored.",
                    mention_author=False)
        if args[1] == "view":
            file = open(Reports.Info.cases_file_location, "r")
            parsed_json: json = json.loads(file.read())
            if len(args) < 3:
                await ctx.reply("The command syntax is invalid, you need a 3rd argument as your query it maybe\n```\n?reports view 1 // as your case number\n?reports view user_id=0 // as the reported user id\n\nThere are also other kinds of query, use ?reports help to view them.")
                return
            if "=" not in args[2]:
                try:
                    embed: discord.Embed = await Reports.gen_case_embed(parsed_json, args[2])
                    embed.title = "Results matching your search"
                    embed.set_footer(text="You searched by specific case number")
                    await ctx.reply(embed=embed, mention_author=False)
                except (Exception,):
                    if len(args) != 3:
                        await ctx.reply("The command syntax is invalid, use the following: `?reports view 1`. in this case 1 meaning your case number.")
                    else:
                        await ctx.reply("An entry with your query doesn't exist.", mention_author=False)
            else:
                try:
                    query = args[2].split("=")
                    cases_matching = []
                    for case in parsed_json:
                        if parsed_json[case][query[0]] == query[1]:
                            cases_matching.append(case)
                    if len(cases_matching) > 1:
                        instance_class = Reports.PagesInstance()
                        instance_class.cases_arr = cases_matching
                        instance_class.parsed_json = parsed_json
                        embed: discord.Embed = await Reports.gen_case_embed(parsed_json, cases_matching[0])
                        results = len(instance_class.cases_arr)
                        embed.title = "Your search returned {0} results".format(results)
                        embed.set_footer(text="you are in page {0} of {1} pages".format(1, results))
                        act_message = await ctx.reply(embed=embed, mention_author=False, view=Reports.ReportButtonRight())
                        instance_class.message = act_message
                        instance_class.user = ctx.message.author.id
                        Reports.pages_dict[act_message.id] = instance_class
                        asyncio.get_event_loop().create_task(instance_class.start())
                    else:
                        generated_embed: discord.Embed = await Reports.gen_case_embed(parsed_json, cases_matching[0])
                        generated_embed.title = "Results matching your search"
                        generated_embed.set_footer(text="There was only 1 result matching your search")
                        await ctx.reply(embed=generated_embed, mention_author=False)
                except (Exception,):
                    if len(args) != 3:
                        error_message = "The command syntax is invalid, use the following: `?reports view key=value`. in this case key meaning where you want to find the value.\n"
                        error_message += "In this case there are multiple keys you can use being these the main ones:\n```user_id\nmod_id\nuser_steam_id```"
                        await ctx.reply(error_message, mention_author=False)
                    else:
                        await ctx.reply("An entry with your query doesn't exist.", mention_author=False)
            file.close()
        if args[1] == "help":
            embed: discord.Embed = discord.Embed(color=Reports.Info.embed_color, title="Report command help ❓", description="All of the cases and report commands work trough arguments and are case insensitive")
            embed = embed.add_field(name="🔹 Report", value="To issue a report to any user simply use\n`{0}Reports report key=value key=value`\nto report someone you need to use all of the following keys and fill them with respective values.\n```user_id=0 // the discord user id you want to report\nuser_steam_id=0 // the steamID 64 from the user you mean to report\nnotes=abc // describe why the issued report should continue```".format(Reports.Info.prefix))
            embed = embed.add_field(name="🔹 View", value="To view other reports trough a query process user\n`{0}Reports view 0`\n`{0}Reports view key=value`\nThe first method is by providing a case ID which will result in the case info embed if the case ID exists\n\nThe second method is by providing a case query the following keys are available\n```user_steam_id=0\nuser_id=0\nmod_id=0```".format(Reports.Info.prefix))
            await ctx.reply(embed=embed, mention_author=False)

async def setup(c):
    await c.add_cog(Reports(c))