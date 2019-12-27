from flask import Flask, request, render_template, url_for, redirect
import user
import connect
import userStore
import projectStore
import threading
import csv
import re
import os


app = Flask(__name__, template_folder='template')


def readUsers():
    conn = connect.DBUtil().getExternalConnection()
    conn.jconn.setAutoCommit(False)
    curs = conn.cursor()
    curs.execute("SELECT * FROM benutzer")
    users = curs.fetchall()
    return users

userList = readUsers()

def modifyPfad():
    conn = connect.DBUtil().getExternalConnection()
    conn.jconn.setAutoCommit(False)
    curs = conn.cursor()
    curs.execute("SELECT * FROM kategorie")
    rows = curs.fetchall()
    for row in rows:
        pic = re.search('[a-z]+\.png', row[2]).group(0)
        # print(pic)
        # sqlStatement = "UPDATE kategorie SET icon = '" + os.path.join(os.getcwd(), 'icons', pic) +  "' WHERE id = " + str(row[0])
        # curs.execute(sqlStatement)
        curs.execute("UPDATE kategorie SET icon = ? WHERE id = ?", (pic, row[0]))
        conn.commit()

modifyPfad()

currentUser = ''

def csv_reader(path):
    with open(path, "r") as csvfile:
        tmp = {}
        reader = csv.reader(csvfile, delimiter='=')
        for line in reader:
            tmp[line[0]] = line[1]
    return tmp

config = csv_reader("properties.settings")

@app.route('/', methods=['GET'])
@app.route('/login', methods=['GET'])
def loginGet():
    return render_template('login.html', users=userList)

@app.route('/', methods=['POST'])
@app.route('/login', methods=['POST'])
def loginPost():
    global currentUser
    currentUser = request.form['user']
    return redirect(url_for('viewMainGet')) # view_main

#region Hello
# @app.route('/hello', methods=['GET'])
# def helloGet():
#     return render_template('hello.html', users=userList)


# @app.route('/hello', methods=['POST'])
# def helloPost():
#     firstname = request.form.get('firstname')
#     lastname = request.form.get('lastname')

#     if firstname is not None and lastname is not None and firstname and lastname:
#         with threading.Lock():
#             userList.append(user.User(firstname, lastname))

#     return render_template('hello.html', users=userList)
#endregion

#region projectFunder
@app.route('/projectFunder', methods=['GET'])
def project():
    try:
        dbExists = connect.DBUtil().checkDatabaseExistsExternal()
        if dbExists:
            db2exists = 'vorhanden! Supi!'
        else:
            db2exists = 'nicht vorhanden :-('
    except Exception as e:
        print(e)

    return render_template('project.html', db2exists=db2exists)
#endregion

# region addUser
@app.route('/addUser', methods=['GET'])
def addUser():
    try:
        userSt = userStore.UserStore()
        userToAdd = user.User("Max", "Mustermann")
        userSt.addUser(userToAdd)
        userSt.completion()

        # ...
        # mach noch mehr!
    except Exception as e:
        print(e)
        return "Failed!!"
    finally:
        userSt.close()
# endregion

@app.route('/view_main', methods=['GET'])
def viewMainGet():
    conn = connect.DBUtil().getExternalConnection()
    conn.jconn.setAutoCommit(False)
    curs = conn.cursor()
    curs.execute("SELECT kennung, titel, ersteller FROM projekt WHERE status='offen'")
    offeneProjekte = curs.fetchall()
    curs.execute("SELECT kennung, titel, ersteller FROM projekt WHERE status='geschlossen'")
    abgeschlosseneProjekte = curs.fetchall()
    curs.execute("SELECT projekt, SUM(spendenbetrag) FROM spenden GROUP BY projekt")
    spendenbetraege = curs.fetchall()
    print(spendenbetraege)
    offeneProjekte = [(offenesProjekt[0], offenesProjekt[1], offenesProjekt[2], spendenbetrag[1]) if spendenbetrag[0] == offenesProjekt[0] else (offenesProjekt[0], offenesProjekt[1], offenesProjekt[2], 0) for offenesProjekt in offeneProjekte for spendenbetrag in spendenbetraege]
    abgeschlosseneProjekte = [(abgeschlossenesProjekt[0], abgeschlossenesProjekt[1], abgeschlossenesProjekt[2], spendenbetrag[1]) for abgeschlossenesProjekt in abgeschlosseneProjekte for spendenbetrag in spendenbetraege if spendenbetrag[0] == abgeschlossenesProjekt[0]]
    return render_template("view_main.html", offeneProjekte=offeneProjekte, abgeschlosseneProjekte=abgeschlosseneProjekte)

@app.route('/new_project', methods=['GET'])
def newProjectGet():
    conn = connect.DBUtil().getExternalConnection()
    conn.jconn.setAutoCommit(False)
    curs = conn.cursor()
    sqlStatement = "SELECT * FROM projekt WHERE ersteller = '" + currentUser + "'" # Change with prepared statement!
    curs.execute(sqlStatement)
    projekte = curs.fetchall()
    return render_template("new_project.html", vorgaenger=projekte)

@app.route('/new_project', methods=['POST'])
def newProjectPost():
    titel = request.form.get('titel')
    finanzierungslimit = request.form.get('finanzierungslimit')
    kategorie = request.form.get('kategorie')
    beschreibung = request.form.get('beschreibung')
    ersteller = currentUser
    projectSt = projectStore.ProjectStore()
    projectSt.addProject(titel, finanzierungslimit, kategorie, beschreibung, ersteller)
    projectSt.completion()
    projectSt.close() # Connection has to be closed when we want the changes that the SQL statement made to persist
    return redirect(url_for('viewMainGet'))

@app.route('/view_project', methods=['POST'])
def viewProjectGet():
    id = request.form['kennung']
    conn = connect.DBUtil().getExternalConnection()
    conn.jconn.setAutoCommit(False)
    curs = conn.cursor()
    curs.execute("SELECT kennung, titel, CAST(beschreibung AS VARCHAR(1000)) AS beschreibung, status, finanzierungslimit, ersteller, vorgaenger, kategorie FROM projekt WHERE kennung = " + str(id))
    result = curs.fetchall()[0]
    titel = result[1]
    beschreibung = result[2]
    status = result[3]
    finanzierungslimit = result[4]
    ersteller = result[5]
    curs.execute("SELECT name FROM benutzer WHERE email = '" + ersteller + "'")
    ersteller = curs.fetchall()[0][0]
    vorgaenger = result[6]
    if vorgaenger != None:
        curs.execute("SELECT titel FROM projekt WHERE kennung = " + str(vorgaenger))
        vorgaenger = curs.fetchall()
        vorgaenger = vorgaenger[0][0]
    else:
        vorgaenger = []
    kategorie = result[7]
    curs.execute("SELECT icon FROM kategorie WHERE id = " + str(kategorie))
    pfad = curs.fetchall()[0][0]
    curs.execute("SELECT SUM(spendenbetrag) FROM spenden GROUP BY projekt HAVING projekt = " + str(id))
    spendensumme = curs.fetchall()
    if len(spendensumme) > 0:
        spendensumme = spendensumme[0][0]
    else:
        spendensumme = 0
    curs.execute("SELECT benutzer.name, spendenbetrag FROM spenden JOIN benutzer ON spenden.spender=benutzer.email WHERE spenden.projekt= " + str(id) + " ORDER BY spendenbetrag DESC")
    spender = curs.fetchall()
    curs.execute("SELECT b.name, CAST(k.text AS VARCHAR(1000)) AS text, k.sichtbarkeit FROM benutzer b, schreibt s, kommentar k WHERE b.email=s.benutzer AND k.id=s.kommentar AND s.projekt=" + str(id) + " ORDER BY k.datum DESC")
    kommentare = curs.fetchall()
    return render_template("view_project.html", pfad=pfad, titel=titel, ersteller=ersteller, beschreibung=beschreibung, finanzierungslimit=finanzierungslimit, spendensumme=spendensumme, status=status, vorgaenger=vorgaenger, spender=spender, kommentare=kommentare)

@app.route('/edit_project')

if __name__ == "__main__":
    port = int("9" + re.match(r"([a-z]+)([0-9]+)", config["username"], re.I).groups()[1])
    app.run(host='0.0.0.0', port=port, debug=True)
