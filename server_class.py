from mcstatus import BedrockServer, JavaServer
import psutil
import re
import subprocess
import time
import threading
import asyncio

class tele:
    def __init__(self, author, name, x, y, z):
        self.author = author
        self.name = name
        self.x = float(x)
        self.y = float(y)
        self.z = float(z)


class Server:
    def __init__(self, file, s_domain):
        f = open(file, 'r')
        self.loc = file
        self.name = f.readline().strip()
        self.port = f.readline().strip()
        self.folder = f.readline().strip()
        self.settings = f.readline().strip()
        self.people = f.readline().strip().split(',')
        self.tele = []
        for line in f.readlines():
            line = line.strip().split(":")
            x, y, z = line[2].split(",")
            self.tele.append(tele(line[0], line[1], x, y, z))
        f.close()

        self.domain = s_domain
        self.running = False
        self.process = None
        self.afk_mode = False
        self.curr_sleep_vote = []
        self.player_c = 0
        self.thread = None
        self.curr_time = 0



    def __str__(self):
        return self.name + ", " + self.folder + ", " + self.settings

    def record_tele(self, author, name, x, y, z):
        check = False
        for i in self.tele:
            if i.name == name:
                check = True
        if not check:
            self.tele.append(tele(author, name, x, y, z))
        self.save()

    def tele_place(self, name):
        for i in self.tele:
            if i.name == name:
                return i.x, i.y, i.z
        return None

    def remove_tele(self, name):
        for i in self.tele:
            if i.name == name:
                self.tele.remove(i)
        self.save()

    def save(self):
        f = open(self.loc, 'w')
        f.write(self.name + "\n")
        f.write(self.folder + "\n")
        f.write(self.settings + "\n")
        people_string = ""
        for person in self.people:
            people_string += "," + person
        f.write(people_string[1:] + "\n")
        for tel in self.tele:
            f.write(tel.author + ":" + tel.name + ":" + str(tel.x) + "," + str(tel.y) + "," + str(tel.z) + "\n")
        f.close()

    def get_name(self):
        return self.name

    def get_privacy(self):
        return self.settings

    def get_folder(self):
        return self.folder

    def get_people(self):
        return self.people

    def get_settings(self):
        if self.settings == "private":
            return True
        return False

    def check_perm(self, name):
        if self.get_settings():
            for i in self.people:
                if i == name:
                    return True
            return False
        else:
            return True

    def check_latency(self):
        server = JavaServer.lookup(f"{self.domain}:{self.port}")
        # Query the server status
        status = server.status()

        # print(f"The server has a latency of {status.latency} ms.")
        return status.latency

    def check_server_status(self):
        try:
            # Create a server object with the domain and port of your Minecraft server
            server = JavaServer.lookup(f"{self.domain}:{self.port}")
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

    def check_sleep(self):
        if len(self.curr_sleep_vote) > 0:
            self.send_command(r"/time set 700")
            self.send_command(r"/say Snoozed")
            self.curr_sleep_vote = []
        if self.afk_mode:
            if time.time() - self.curr_time > 500:
                self.send_command(r"/time set 700")
                self.curr_time = time.time()

    def start_proc(self):
        proc = subprocess.Popen(
            [f"{self.name}_start_mc.bat"],
            shell=True,
            cwd=self.get_folder(),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        return proc
    def turn_on_server(self):
        self.running = True
        self.process = self.start_proc()

        self.thread = threading.Thread(target=self.read_output, args=(self.process.stdout,))
        self.thread.start()


    def turn_off_server(self):
        #CHANGE TO NAME
        self.running = False
        process_thing = psutil.Process(self.process.pid)
        for proc in process_thing.children(recursive=True):
            proc.terminate()
        process_thing.terminate()

        batch_file_name = f"{self.name}_start_mc.bat"
        try:
            for proc in psutil.process_iter():
                if proc.name() == batch_file_name:
                    proc.kill()
                    print(f"Cancelled batch file: {batch_file_name}")
        except Exception as e:
            print(f"Error cancelling batch file: {e}")
        self.afk_mode = False
        self.running = False
        self.process = None
        self.thread = None

    def send_command(self, command: str):
        if self.process is not None:
            if self.process.poll() is None:
                print(command)
                self.process.stdin.write(command + "\n")
                self.process.stdin.flush()

    def read_output(self, pipe):
        for line in iter(pipe.readline, ''):

            print(f"Thread{self.name}:")
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
                if self.running:
                    loc = self.tele_place(temp)
                    if loc is not None:
                        name = x[0]
                        print(name)
                        self.send_command(r"/tp " + str(name) + " " + str(loc[0]) + " " + str(loc[1]) + " " + str(loc[2]))
                    else:
                        self.send_command(r"/tp " + str(x[0]) + " " + temp)

            if "!save" in line:
                x = re.findall("<(.*?)>", line)
                temp = line.split("!save")
                temp = temp[1].strip().split(" ")
                if self.running:
                    name = x[0]
                    if len(temp) == 4:
                        self.record_tele(name, temp[0], int(temp[1]), int(temp[2]), int(temp[3]))

            if "!rm" in line:
                x = re.findall("<(.*?)>", line)
                temp = line.split("!rm")
                temp = temp[1].strip().split(" ")
                if self.running:
                    name = x[0]
                    self.remove_tele(temp[0])
            #
            if "!sun" in line:
                x = re.findall("<(.*?)>", line)
                if self.running:
                    self.send_command(r"/weather clear")

            if "!afk" in line:
                x = re.findall("<(.*?)>", line)
                if self.running:
                    self.afk_mode = not self.afk_mode
                    self.minecraft_message("AFK is set to " + str(self.afk_mode))
                    self.send_command(r"/time set 700")
                    self.curr_time = time.time()

            if "!sleep" in line:
                x = re.findall("<(.*?)>", line)
                if self.running:
                    name = x[0]
                    checkName = False
                    for i in self.curr_sleep_vote:
                        if name == i:
                            checkName = True
                    if not checkName:
                        self.curr_sleep_vote.append(name)

            if "!unsleep" in line:
                x = re.findall("<(.*?)>", line)
                if self.running:
                    name = x[0]
                    checkName = -1
                    for i in range(len(self.curr_sleep_vote)):
                        if name == self.curr_sleep_vote[i]:
                            checkName = i
                    if checkName != -1:
                        self.curr_sleep_vote.remove(name)

    def minecraft_message(self, mess):
        self.send_command(r"/say " + mess)

    async def my_background_task(self):
        await asyncio.sleep(10)

        player_c = self.check_server_status()
        while player_c is None:
            await asyncio.sleep(1)
            player_c = self.check_server_status()
        print("Server On")
        await asyncio.sleep(25)
        self.send_command(r"/time set 700")

        while self.running:

            print("This function runs every 10 seconds")
            player_c = self.check_server_status()
            if player_c == 0:
                self.turn_off_server()
                await asyncio.sleep(5)
                print("Process terminated")
                break
            else:
                print("Players on")
            for i in range(6):
                self.check_sleep()
                await asyncio.sleep(10)
