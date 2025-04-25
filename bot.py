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
from threading import Thread, Event
import queue
import select
import signal
import re
from mcstatus.status_response import BedrockStatusResponse, JavaStatusResponse
load_dotenv()
# Replace 'YOUR_SERVER_IP' with the IP address of your Minecraft server
server_domain = os.getenv('SERVER_DOMAIN')
CHANNEL_NUM = os.getenv('CHANNEL')
# Replace 'YOUR_SERVER_PORT' with the port of your Minecraft server (default is 25565)
# server_port = 25565
print(server_domain)


TOKEN = os.getenv('DISCORD_TOKEN')

intents = discord.Intents.default()
intents.messages = True
intents.message_content = True

# client = discord.Client(intents=intents)
client = commands.Bot(command_prefix='!', intents=intents)
CHANNEL_NAME = "server-status"

curr_servers = []
onboard_servers = []
test_server_list = ["server0.txt", "server1.txt", "server2.txt", "server3.txt"]
saved_servers = []
past_messages = 0

on = False
thread = None

@client.event
async def on_ready():
    global saved_servers, thread
    print(f'We have logged in as {client.user}')
    send_channel = None
    for guild in client.guilds:
        existing_channel = discord.utils.get(guild.text_channels, name=CHANNEL_NAME)
        if existing_channel:
            print(f"Channel #{CHANNEL_NAME} already exists in {guild.name}.")
            send_channel = existing_channel
        else:
            print(f"Creating channel #{CHANNEL_NAME} in {guild.name}...")
            await guild.create_text_channel(CHANNEL_NAME)
            send_channel = discord.utils.get(guild.text_channels, name=CHANNEL_NAME)
    saved_servers = []
    for server in test_server_list:
        s = sc.Server(server, server_domain)
        saved_servers.append(s)
        print(s)
    client.loop.create_task(handle_discord(send_channel))



@client.event
async def on_message(message):
    if message.author == client.user:
        return

    print(message)

    if message.content.startswith('!start'):
        perm = False

        temp = message.content.split(' ')
        if len(temp) != 2:
            temp = [None, '0']
        try:
            temp[1] = int(temp[1])
        except:
            print("SERVER CAST ERROR")

        set_server = None
        if 0 <= temp[1] < len(saved_servers):
            if saved_servers[temp[1]].get_settings() and saved_servers[temp[1]].check_perm(message.author.global_name):
                set_server = saved_servers[temp[1]]
                perm = True
            if not saved_servers[temp[1]].get_settings():
                set_server = saved_servers[temp[1]]
                perm = True

        if perm:
            await message.channel.send('One sec...')

            overlap = False
            for i in onboard_servers:
                if i.port == set_server.port:
                    await message.channel.send('That port is already in use!')
                    await message.channel.purge(limit=1)
                    overlap = True
            for j in curr_servers:
                if j.port == set_server.port:
                    await message.channel.send('That port is already in use!')
                    await message.channel.purge(limit=1)
                    overlap = True
            if not overlap:

                set_server.turn_on_server()
                onboard_servers.append(set_server)
                await set_server.my_background_task()

        else:
            await message.channel.send('Invalid Permission, not approved to run server.')

    if message.content == '!list':
        display_list = "Server List\n"
        count = 0
        for server in saved_servers:
            if server.running:
                display_list = display_list + str(count-1) + ": " + "(RUNNING) " + server.get_name() + " ("+server.get_privacy()+")"+ "\n"
            else:
                display_list = display_list + str(count) + ": " + server.get_name() + " (" + server.get_privacy() + ")" + "\n"
            count += 1
        await message.channel.send(display_list)

    # TODO UPDATE COMMANDS
    if message.content.startswith('!tp_list '):
        content = message.content.split(' ', 1)
        if len(content) != 2:
            await message.channel.send('Proper format: !tp_list [int]')
            return
        else:
            try:
                server_int = int(content[1])
            except ValueError as verr:
                await message.channel.send('Specify a server by number')
                return
            except Exception as ex:
                pass
                return
            if server_int < len(saved_servers):
                display_list = f"Tp List for {saved_servers[server_int].get_name()}\n"
                for t in saved_servers[server_int].tele:
                    display_list = display_list + t.name + "\n"
                await message.channel.send(display_list)
            else:
                await message.channel.send('Specify a valid server number, here\'s the list:')
                await message.channel.send('!list')
                return

    #TODO UPDATE COMMANDS

    # if message.content == '!latency':
    #     if curr_server is not None:
    #         await message.channel.send(f"The server has a latency of {check_latency()} ms.")

    # if message.content.startswith('!say '):
    #     content = message.content.split(' ', 1)
    #     if len(content) != 2:
    #         await message.channel.send('Please enter a message to say.')
    #         return
    #      # Check if subprocess is still running
    #     send_command(r"/say " + str(content[1]) + " -"+str(message.author.global_name))
    #
    # if message.content.startswith('!run_command') and server_on:
    #     content = message.content.split(' ', 1)
    #     send_command(content[1])

async def handle_discord(send_channel):
    global past_messages, curr_servers
    await client.wait_until_ready()  # Wait until the bot is fully ready
    # channel = client.get_channel(int(CHANNEL_NUM))
    channel = send_channel
    await channel.purge(limit=10)
    await channel.send(f"Bot is on and ready!")

    while not client.is_closed():
        if len(onboard_servers) != 0:
            new_s = onboard_servers.pop()
            await channel.send(f"{new_s.name} on shortly....")
            past_messages += 1
            await asyncio.sleep(10)
            await channel.purge(limit=1)
            past_messages -= 1
            await channel.send(f"Server: {new_s.name} is now online! Use {new_s.domain}:{new_s.port}")
            curr_servers.append(new_s)
            past_messages += 1
            print("Server On")

        if len(curr_servers) != 0:
            running_servers = []
            for s in curr_servers:
                if s.running:
                    running_servers.append(s)
            if len(running_servers) != len(curr_servers):
                await channel.purge(limit=past_messages)
                past_messages = 0
                for r in running_servers:
                    await channel.send(f"Server: {r.name} is now online! Use {r.domain}:{r.port}")
                    past_messages += 1
                curr_servers = running_servers
        await asyncio.sleep(10)


@client.event
async def on_disconnect():
    # Perform cleanup tasks or save data here
    print("Bot is disconnecting...")


client.run(TOKEN)
