# https://discordpy.readthedocs.io/en/latest/#documentation-contents

from sys import argv, path
path.append("\\".join(argv[0].split("\\")[:-2]))

import time
import discord
import requests
import asyncio
import json
import re
import random
import bs4
import os
import traceback
import math
import PyBoiler

from runescape.lootsim.lootsim import LootSimManager
from markov.markov_handler import MarkovHandler
from mothtypes import UserCollection, Channel, Reactable
from runescape.progression.progression import ProgressManager
from casino.blackjack.blackjack import BlackjackTable
from casino.poker.poker import PokerTable
from remindme.remindme import RemindMeManager

my = PyBoiler.Boilerplate()

if not os.path.exists(my.m_path("SECRET\\token.txt")):
    print("Missing token. Place token into the 'token.txt' file.")
    exit(-1)

client = discord.Client()

macros = {
    "bruh.mp4":"https://www.youtube.com/watch?v=2ZIpFytCSVc",
    "amazin":"https://youtu.be/hC6CZKkEh4A",
    "true": """True and yeah that's pretty true that's true and yeah that's true that's true that's true that's pretty true that's pretty true I mean that's true yeah that's true that's true that's fucking true amm that's how it is dude"""
}

reactables = [
    Reactable(":COOM:675430755350085706", r"c[ou]{2,}m")
]

class MothBot:
    def __init__(self):
        self.user_collection = UserCollection(my.m_path("casino\\tokens"), client)

        self.build_managers()
        self.hook_background_tasks()
        self.hook_commands()
        
        p = my.m_path("SECRET")
        self.secrets = dict()
        for filename in os.listdir(p):
            with open(f"{p}\\{filename}", "r") as fptr:
                key = filename.split(".")[0]
                self.secrets[key] = fptr.read()

    def build_managers(self):
        start_time = time.time()
        PyBoiler.Log("Building casino").to_larva()
        self.poker_table = PokerTable(client, Channel.Kasiino, self.user_collection)
        self.blackjack_table = BlackjackTable(my.m_path("casino\\blackjack\\achievements"),
                                              client,
                                              Channel.Kasiino,
                                              self.user_collection)
        PyBoiler.Log("Building Markov chains").to_larva()
        self.markov_handler = MarkovHandler(my.m_path("markov"), self.user_collection)
        PyBoiler.Log("Building lootsim handler").to_larva()
        self.lootsim_handler = LootSimManager(my.m_path("runescape\\lootsim\\lootsim_data"))
        PyBoiler.Log("Building progress manager").to_larva()
        self.progress_manager = ProgressManager(self.user_collection,
                                                my.m_path("runescape\\data\\osrs"),
                                                my.m_path("runescape\\data\\rs3"))
        self.remindme_manager = RemindMeManager(client, my.m_path("remindme\\tracking"))
        PyBoiler.Log(f"Took {round(time.time() - start_time, 2)}s").to_larva()

    def hook_background_tasks(self):
        tasks = (
                (self.progress_manager.loop,             (client, Channel.Grupiteraapia)),
                (self.markov_handler.chatroom_loop,      (client, Channel.Jututuba)),
                (self.user_collection.token_incrementer, (client, Channel.Kasiino)),
                (self.remindme_manager.loop,              tuple()),
                (self.corona_updater,                     tuple()),
                (self.maku_live_checker,                  tuple())
        )
        for method, args in tasks:
            client.loop.create_task(method(*args))
        PyBoiler.Log(f"Hooked {len(tasks)} background tasks").to_larva()

    def hook_commands(self):
        self.cmds = {
            "mothbot":self.help,
            "eval":self.evaluate,
            "imiteeri":self.markov_generate,
            "lootsim":self.lootsim,
            "jututuba":self.chatroom_change_interval,
            "tokens":self.get_tokens,
            "remindme":self.remindme_manager.new_tracker,
            "dab":self.dab,
            "corona":self.corona,
            "wiki":self.wiki
        }
        for cmd_collection, method in zip(
            (BlackjackTable.VALID_COMMANDS, PokerTable.VALID_COMMANDS),
            (self.blackjack_table.handle_input, self.poker_table.handle_input)):
            self.cmds.update(dict.fromkeys(cmd_collection, method))

    async def handle_message(self, message) -> None:
        first_word = message.content.split(" ")[0].lower()

        for r in reactables:
            if r.match(message.content.lower()):
                await message.add_reaction(str(r))
        
        if message.content in macros:
            await message.channel.send(macros[message.content])
        elif first_word in self.cmds:
            await self.handle_command(first_word, message)
        else:
            for fname in os.listdir(my.m_path("macros")):
                if message.content == fname.split(".")[0]:
                    await message.channel.send(file=discord.File(my.m_path(f"macros\\{fname}")))
                    break
    
    async def handle_command(self, cmd: str, message) -> bool:
        try:
            await self.cmds[cmd](message)
        except:
            error_msg = f"```\n{traceback.format_exc()}\n```"
            await message.channel.send(error_msg)

    async def help(self, message):
        await message.channel.send("; ".join(self.cmds))

    async def evaluate(self, message):
        if message.author.id in self.user_collection.god_access:
            r = eval(" ".join(message.content.split(" ")[1:]))
        else:
            r = "Ei :)"
        await message.channel.send(r)

    async def markov_generate(self, message):
        spl = message.content.split(" ")
        if len(spl) < 2:
            await message.channel.send(self.markov_handler.err_msg)
        else:
            count = int(spl[2]) if len(spl) > 2 and spl[2].isnumeric() else 1
            results = self.markov_handler.generate_sentences(spl[1], count, True)
            await message.channel.send("\n".join(results))

    async def lootsim(self, message):
        messages_to_send = self.lootsim_handler.handle(message)
        for m in messages_to_send:
            await message.channel.send(m)
    
    async def chatroom_change_interval(self, message):
        msg_split = message.content.split(" ")
        if len(msg_split) >= 2:
            arg = msg_split[1]
            if re.search(r"^\d+,\d+$", arg):
                x, y = (int(x) for x in arg.split(","))
                if 2 <= y <= 600 and 1 <= x < y:
                    with open(my.m_path("markov\\interval.txt"), "w") as fptr:
                        fptr.write(f"{x},{y}")
                    await message.channel.send(f"intervall nüüd {x}-{y}")
                    return
        await message.channel.send("jututuba x,y -- säti intervall sekundites, kus 2 <= y <= 600 ja 1 <= x < y") 

    async def get_tokens(self, message):
        msg_spl = message.content.split(" ")
        if len(msg_spl) >= 2 and msg_spl[1] == "top":
            await self.tokens_hiscore(message)
        elif len(msg_spl) >= 4 and msg_spl[1] == "gift":
            if message.author.id in self.user_collection.god_access:
                user_to_gift = self.user_collection.get(int(msg_spl[2]))
                user_to_gift.tokens_account.change(int(msg_spl[3]))
                await message.channel.send(f"Kantud üle {msg_spl[3]}")
            else:
                await message.channel.send("Ei :)")
        elif (user := self.user_collection.get(message.author.id)) is not None:
            await message.channel.send(
                f"Sul on {user.tokens_account.amount} tokenit"
            )
        else:
            await message.channel.send(f"{message.author.name} - sul pole tokenite rahakotti")

    async def tokens_hiscore(self, message):
        data = dict()
        out = ["Kasiino hiscores"]
        for user in self.user_collection.users:
            if hasattr(user, "tokens_account"):
                data[str(user)] = user.tokens_account.amount
        for name in sorted(data, key=lambda name: data[name], reverse=True):
            out.append(f"{name} - {data[name]}")
        await message.channel.send("\n".join(out))

    async def dab(self, message):
        dance = list()
        p = my.m_path("fortdance")
        for filename in sorted(os.listdir(p)):
            with open(f"{p}\\{filename}", "r", encoding="utf-8") as fptr:
                dance.append(fptr.read())
        count = 0
        i = 1
        msg = await message.channel.send(f"```{dance[0]}```")
        while count < 2:
            await msg.edit(content=f"```{dance[i]}```")
            i = (i + 1) % len(dance)
            if not i:
                count += 1
            await asyncio.sleep(0.5)

    async def corona_updater(self):
        await client.wait_until_ready()
        while not client.is_closed():
            response = requests.get(r"https://www.worldometers.info/coronavirus/")
            if response.status_code == 200:
                parsed = bs4.BeautifulSoup(response.content, "html.parser")
                vals = parsed.findAll("div", {"class":"maincounter-number"})
                if len(vals) == 3:
                    cases, dead, recovered = (x.text.strip() for x in vals)
                    with open(my.m_path("corona\\world.json"), "w") as fptr:
                        json.dump({"cases":cases, "dead":dead, "recovered":recovered, "updated":time.strftime(r"%B %d - %H:%M")}, fptr)
            response = requests.get(r"https://www.terviseamet.ee/et/uuskoroonaviirus")
            if response.status_code == 200:
                parsed = bs4.BeautifulSoup(response.content, "html.parser")
                e = parsed.find(string="OLUKORD EESTIS").findParent("div")
                infected_container, dead_container = e.findChildren("div", recursive=False)[1:]
                infected = infected_container.findAll("strong")[1].text.strip()
                dead = dead_container.find("b").text.strip()
                with open(my.m_path("corona\\eesti.txt"), "w") as fptr:
                    fptr.write(f"{infected}:{dead}")
            await asyncio.sleep(120)
    
    async def corona(self, message):
        with open(my.m_path("corona\\world.json"), "r") as fptr:
            parsed = json.load(fptr)
        with open(my.m_path("corona\\eesti.txt"), "r") as fptr:
            estonia_infected, estonia_dead = fptr.read().split(":")
        msg = [f":biohazard: Koroona seis - uuendatud {parsed['updated']}"]
        for prefix, val in zip(("Kokku nakatanuid", "Kokku surnuid", "Eestis nakatanuid", "Eestis surnuid"),
                               (parsed["cases"], parsed["dead"], estonia_infected, estonia_dead)):
            msg.append(f"{prefix} <:monkas:418538700260114433> :point_right: {val}")
        await message.channel.send("\n".join(msg))

    async def maku_live_checker(self):
        await client.wait_until_ready()
        previously_live = True
        query = "https://api.twitch.tv/helix/streams?user_login=xmakuest"
        headers = {"Client-ID": self.secrets["twitch_client_id"]}
        while not client.is_closed():
            r = requests.get(query, headers=headers)
            if r.status_code == 200:
                is_live = len(r.json()["data"]) > 0
                if not previously_live and is_live:
                    msg = "Maku on live :)\nhttps://www.twitch.tv/xmakuest"
                    await client.get_channel(Channel.Grupiteraapia).send(msg)
                previously_live = is_live
            await asyncio.sleep(10)

    async def wiki(self, message):
        query = "https://en.wikipedia.org/wiki/" + " ".join(message.content.split(" ")[1:])
        response = requests.get(query)
        if response.status_code == 404:
            await message.channel.send("Sellist artiklit ei leitud")
        elif response.status_code == 200:
            parsed = bs4.BeautifulSoup(response.content, "html.parser")
            real_url = "https://en.wikipedia.org/wiki/" + "_".join(parsed.find("h1", {"id":"firstHeading"}).text.strip().split(" "))
            await message.channel.send(real_url)
        else:
            await message.channel.send(f"Error {response.status_code}, wiki on maas või mingi muu jama")

mothbot = MothBot()

@client.event
async def on_ready():
    PyBoiler.Log("online").to_larva()
    await client.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="your every move"))

@client.event
async def on_message(message):
    if message.channel.id == Channel.Send_To_Grupiteraapia:
        await client.get_channel(Channel.Grupiteraapia).send(message.content)
    elif message.author.id != client.user.id:
        await mothbot.handle_message(message)

try:
    client.run(mothbot.secrets["token"])
except discord.errors.LoginFailure:
    print("Connection to the Discord API was disrupted. Bad token?")
