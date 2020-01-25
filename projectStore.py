import connect


class ProjectStore:

    def __init__(self):
        #dbUtil = connect.DBUtil().getExternalConnection("testdb")
        self.conn = connect.DBUtil().getExternalConnection()
        self.conn.jconn.setAutoCommit(False)
        self.complete = None

    # PREPARED STATEMENT (WITH PLACEHOLDERS)
    def addProject(self, titel, finanzierungslimit, kategorie, beschreibung, ersteller, vorgaenger):
        curs = self.conn.cursor()
        sqlStatement= "INSERT INTO PROJEKT (titel, beschreibung, finanzierungslimit, ersteller, vorgaenger, kategorie) VALUES(?, ?, ?, ?, ?, ?)"
        curs.execute(sqlStatement, (titel, beschreibung, finanzierungslimit, ersteller, vorgaenger, kategorie))
        print('addProject')

    def completion(self):
        self.complete = True

    def close(self):
        if self.conn is not None:
            try:
                if self.complete:
                    self.conn.commit()
                else:
                    self.conn.rollback()
            except Exception as e:
                print(e)
            finally:
                try:
                    self.conn.close()
                except Exception as e:
                    print(e)
