import os

import discord
from discord.ext import commands
from dotenv import load_dotenv
import asyncio
import subprocess
from mcstatus import BedrockServer, JavaServer
import time
import psutil
import server_class as sc
import threading
import queue
import select
import signal
import re
from mcstatus.status_response import BedrockStatusResponse, JavaStatusResponse

# Replace 'YOUR_SERVER_IP' with the IP address of your Minecraft server
server_domain = os.getenv('SERVER_DOMAIN')
# Replace 'YOUR_SERVER_PORT' with the port of your Minecraft server (default is 25565)
server_port = 25565

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

intents = discord.Intents.default()
intents.messages = True
intents.message_content = True

# client = discord.Client(intents=intents)
client = commands.Bot(command_prefix='!', intents=intents)

server_on = False
curr_server = None
test_server_list = ["server0.txt", "server1.txt", "server2.txt", "server3.txt"]
saved_servers = []
process = None

curr_time = None
thread = None
stop_event = threading.Event()

afk_mode = False
curr_sleep_vote = []

def send_command(command: str):
    if process is not None:
        if process.poll() is None:
            print(command)
            process.stdin.write(command + "\n")
            process.stdin.flush()

def read_output(pipe):
    global afk_mode, curr_time
    for line in iter(pipe.readline, ''):

        print("Thread:")
        print(line.strip())
        line = line.strip()
        x = re.findall("<(.*?)>", line)
        if x is None:
            return None
        if "!tp" in line:
            print(line)
            x = re.findall("<(.*?)>", line)
            print(x)
            temp = line.split("!tp")
            temp = temp[1].strip()
            if curr_server is not None:
                loc = curr_server.tele_place(temp)
                if loc is not None:
                    name = x[0]
                    print(name)
                    send_command(r"/tp " + str(name) + " " + str(loc[0]) + " " + str(loc[1]) + " " + str(loc[2]))
                else:
                    send_command(r"/tp " + str(x[0]) + " " + temp)

        if "!save" in line:
            x = re.findall("<(.*?)>", line)
            temp = line.split("!save")
            temp = temp[1].strip().split(" ")
            if curr_server is not None:
                name = x[0]
                if len(temp) == 4:
                    curr_server.record_tele(name, temp[0], int(temp[1]), int(temp[2]), int(temp[3]))

        if "!rm" in line:
            x = re.findall("<(.*?)>", line)
            temp = line.split("!rm")
            temp = temp[1].strip().split(" ")
            if curr_server is not None:
                name = x[0]
                curr_server.remove_tele(temp[0])
        #
        if "!sun" in line:
            x = re.findall("<(.*?)>", line)
            if curr_server is not None:
                send_command(r"/weather clear")

        if "!afk" in line:
            x = re.findall("<(.*?)>", line)
            if curr_server is not None:
                afk_mode = not afk_mode
                minecraft_message("AFK is set to "+str(afk_mode))
                send_command(r"/time set 700")
                curr_time = time.time()


        if "!sleep" in line:
            x = re.findall("<(.*?)>", line)
            if curr_server is not None:
                name = x[0]
                checkName = False
                for i in curr_sleep_vote:
                    if name == i:
                        checkName = True
                if not checkName:
                    curr_sleep_vote.append(name)

        if "!unsleep" in line:
            x = re.findall("<(.*?)>", line)
            if curr_server is not None:
                name = x[0]
                checkName = -1
                for i in range(len(curr_sleep_vote)):
                    if name == curr_sleep_vote[i]:
                        checkName = i
                if checkName != -1:
                    curr_sleep_vote.remove(name)


def minecraft_message(mess):
    send_command(r"/say " + mess)






@client.event
async def on_ready():
    global saved_servers
    print(f'We have logged in as {client.user}')
    check_server_status()
    for server in test_server_list:
        s = sc.Server(server)
        saved_servers.append(sc.Server(server))
        print(s)


@client.event
async def on_message(message):
    global server_on
    global curr_server
    global process
    if message.author == client.user:
        return

    print(message)
    channel = client.get_channel(1241564851084591257)
    if message.content.startswith('!start') and not server_on:
        perm = False

        temp = message.content.split(' ')
        if len(temp) != 2:
            temp = [None, '0']
        try:
            temp[1] = int(temp[1])
        except:
            print("SERVER CAST ERROR")

        if 0 <= temp[1] < len(saved_servers):
            if saved_servers[temp[1]].get_settings() and saved_servers[temp[1]].check_perm(message.author.global_name):
                curr_server = saved_servers[temp[1]]
                perm = True
            if not saved_servers[temp[1]].get_settings():
                curr_server = saved_servers[temp[1]]
                perm = True
        # if temp[1] == '0':
        #     if saved_servers[0].get_settings() and saved_servers[0].check_perm(message.author.global_name):
        #         curr_server = saved_servers[0]
        #         perm = True
        #     if not saved_servers[0].get_settings():
        #         curr_server = saved_servers[0]
        #         perm = True
        #
        # elif temp[1] == '1':
        #     if saved_servers[1].get_settings() and saved_servers[1].check_perm(message.author):
        #         curr_server = saved_servers[1]
        #         perm = True
        #     if not saved_servers[1].get_settings():
        #         curr_server = saved_servers[1]
        #         perm = True
        # elif temp[1] == '2':
        #     if saved_servers[2].get_settings() and saved_servers[2].check_perm(message.author):
        #         curr_server = saved_servers[2]
        #         perm = True
        #     if not saved_servers[2].get_settings():
        #         curr_server = saved_servers[2]
        #         perm = True

        if perm:
            await message.channel.send('One sec...')
            server_on = True

            await channel.purge(limit=5)
            process = turn_on_server(curr_server)
            print(process)
            await my_background_task(curr_server)
        else:
            await message.channel.send('Invalid Permission, not approved to run server.')

    if message.content == '!list':
        display_list = "Server List\n"
        count = 0
        for server in saved_servers:
            print(count)
            if curr_server is not None and server.get_name() == curr_server.get_name():
                display_list = display_list + str(count-1) + ": " + "(RUNNING) " + server.get_name() + " ("+server.get_privacy()+")"+ "\n"
            else:
                display_list = display_list + str(count) + ": " + server.get_name() + " (" + server.get_privacy() + ")" + "\n"
            count += 1
            print(display_list)
        await message.channel.send(display_list)

    if message.content == '!tp_list':
        if curr_server is not None:
            display_list = f"Tp List for {curr_server.get_name()}\n"
            for t in curr_server.tele:
                display_list = display_list + t.name + "\n"
            await message.channel.send(display_list)

    if message.content == '!latency':
        if curr_server is not None:
            await message.channel.send(f"The server has a latency of {check_latency()} ms.")

    if message.content.startswith('!say '):
        content = message.content.split(' ', 1)
        if len(content) != 2:
            await message.channel.send('Please enter a message to say.')
            return
         # Check if subprocess is still running
        send_command(r"/say " + str(content[1]) + " -"+str(message.author.global_name))

    if message.content.startswith('!run_command') and server_on:
        content = message.content.split(' ', 1)
        send_command(content[1])


async def my_background_task(server):
    global server_on, curr_time
    global curr_server, process, thread, curr_sleep_vote

    await client.wait_until_ready()  # Wait until the bot is fully ready
    channel = client.get_channel(1241564851084591257)

    await channel.send("Server on shortly....")

    # process = subprocess.Popen(
    #     ["start_mc.bat"],
    #     shell=True,
    #     cwd=server.get_folder()
    # )


    time.sleep(10)
    player_c = check_server_status()
    while player_c is None:
        time.sleep(1)
        player_c = check_server_status()
    await channel.send("Server: " + server.get_name() + " is now online!")
    print("Server On")

    thread = threading.Thread(target=read_output, args=(process.stdout,))
    thread.start()

    await asyncio.sleep(25)
    send_command(r"/time set 700")
    # prev_pc = player_c
    # message = await channel.send("Server has just started! No one is on yet.")
    while not client.is_closed():
        print("This function runs every 10 seconds")
        player_c = check_server_status()
        # if prev_pc != player_c:
        #     await channel.purge(limit=1)
        #     if player_c == 1:
        #         await message.edit(content="Server has 1 player on!")
        #     elif player_c != 0:
        #         await message.edit(content=f"Server has {player_c} players on!")
        prev_pc = player_c
        if player_c == 0:
            process = psutil.Process(process.pid)
            for proc in process.children(recursive=True):
                proc.terminate()
            process.terminate()
            await asyncio.sleep(5)
            print("Process terminated")
            await channel.purge(limit=5)
            await channel.send("Server offline.")
            server_on = False
            curr_server = None
            break
        else:
            print("Players on")

        print(len(curr_sleep_vote))
        print(player_c)
        # if player_c <= 2*len(curr_sleep_vote):
        #     send_command(r"/time set 700")
        #     send_command(r"/say Snoozed")
        #     curr_sleep_vote = []
        if len(curr_sleep_vote) > 0:
            send_command(r"/time set 700")
            send_command(r"/say Snoozed")
            curr_sleep_vote = []
        if afk_mode:
            if time.time() - curr_time > 500:
                send_command(r"/time set 700")
                curr_time = time.time()

        await asyncio.sleep(10)


@client.event
async def on_disconnect():
    # Perform cleanup tasks or save data here
    print("Bot is disconnecting...")

def check_latency():
    server = JavaServer.lookup(f"{server_domain}:{server_port}")
    # Query the server status
    status = server.status()

    # print(f"The server has a latency of {status.latency} ms.")
    return status.latency
def check_server_status():
    try:
        # Create a server object with the domain and port of your Minecraft server
        server = JavaServer.lookup(f"{server_domain}:{server_port}")
        # Query the server status

        status = server.status()

        # Print the server status
        print(f"Server is online, there are {status.players.online} players online.")

        # query = server.query()
        #
        # # Print player names
        # print("Players currently online:")
        # for player in query.players.names:
        #     print(player)

        print()
        # print(f"The server has a latency of {status.latency} ms.")
        # # Additional server information
        # print(f"Server version: {status.version.name}")
        # print(f"Server description: {status.description}")
        return status.players.online

    except Exception as e:
        print(f"Failed to retrieve server status: {e}")
        return None


def turn_on_server(server):
    proc = subprocess.Popen(
        ["start_mc.bat"],
        shell=True,
        cwd=server.get_folder(),
        stdin = subprocess.PIPE,
        stdout = subprocess.PIPE,
        stderr = subprocess.PIPE,
        text = True
    )
    return proc


def turn_off_server():
    global afk_mode
    batch_file_name = "start_mc.bat"
    try:
        for proc in psutil.process_iter():
            if proc.name() == batch_file_name:
                proc.kill()
                print(f"Cancelled batch file: {batch_file_name}")
    except Exception as e:
        print(f"Error cancelling batch file: {e}")
    afk_mode = False

client.run(TOKEN)
