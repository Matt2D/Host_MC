class tele:
    def __init__(self, author, name, x, y, z):
        self.author = author
        self.name = name
        self.x = float(x)
        self.y = float(y)
        self.z = float(z)


class Server:
    def __init__(self, file):
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

        self.running = False


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
