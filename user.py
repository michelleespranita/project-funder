class User:

    def __init__(self, email, name, beschreibung):
        self.email = email
        self.name = name
        self.beschreibung = beschreibung

    def getEmail(self):
        return self.email

    def getName(self):
        return self.name
    
    def getBeschreibung(self):
        return self.beschreibung
