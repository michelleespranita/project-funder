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
        pic = "/static/" + pic
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
    curs.execute("SELECT kennung, titel, ersteller, kategorie.icon FROM projekt JOIN kategorie ON projekt.kategorie=kategorie.id WHERE status='offen'")
    offeneProjekte = curs.fetchall()
    curs.execute("SELECT kennung, titel, ersteller, kategorie.icon FROM projekt JOIN kategorie ON projekt.kategorie=kategorie.id WHERE status='geschlossen'")
    abgeschlosseneProjekte = curs.fetchall()
    curs.execute("SELECT projekt, SUM(spendenbetrag) FROM spenden GROUP BY projekt")
    spendenbetraege = curs.fetchall()
    offeneProjekte = [(offenesProjekt[0], offenesProjekt[1], offenesProjekt[2], offenesProjekt[3], spendenbetrag[1]) if spendenbetrag[0] == offenesProjekt[0] else (offenesProjekt[0], offenesProjekt[1], offenesProjekt[2], offenesProjekt[3], 0) for offenesProjekt in offeneProjekte for spendenbetrag in spendenbetraege]
    abgeschlosseneProjekte = [(abgeschlossenesProjekt[0], abgeschlossenesProjekt[1], abgeschlossenesProjekt[2], abgeschlossenesProjekt[3], spendenbetrag[1]) for abgeschlossenesProjekt in abgeschlosseneProjekte for spendenbetrag in spendenbetraege if spendenbetrag[0] == abgeschlossenesProjekt[0]]
    return render_template("view_main.html", offeneProjekte=offeneProjekte, abgeschlosseneProjekte=abgeschlosseneProjekte)

@app.route('/delete_project', methods=['GET'])
def viewMainPost():
    conn = connect.DBUtil().getExternalConnection()
    conn.jconn.setAutoCommit(False)
    curs = conn.cursor()
    id = request.args.get('kennung')
    # 1) --- Delete Kommentare ---
    curs.execute("SELECT kommentar FROM schreibt WHERE projekt=" + str(id))
    kommentarIDs = curs.fetchall() # [(1,), (2,)]
    kommentarIDs = [str(kommentarID[0]) for kommentarID in kommentarIDs] # ['1','2'], changing it into string is necessary, otherwise .join won't work
    kommentarIDs = ",".join(kommentarIDs) # "1,2"
    # curs.execute("DELETE FROM schreibt WHERE projekt=" + str(id))
    # conn.commit()
    # curs.execute("DELETE FROM kommentar WHERE id IN (" + kommentarIDs + ")") # BEWARE OF SQL INJECTION!
    # conn.commit()
    # 2) --- Give money back to Spender ---
    curs.execute("SELECT spender, spendenbetrag FROM spenden WHERE projekt=" + str(id))
    spend = curs.fetchall() # [('alan@turing.com', 15000.0), ('donald@eKnuth.com', 1500.56)]
    # for (spender, spendenbetrag) in spend:
        # curs.execute("UPDATE konto SET guthaben = guthaben + " + str(spendenbetrag) + " WHERE inhaber = " + spender)
        # conn.commit()
    # 3) --- Delete Spenden ---
    # curs.execute("DELETE FROM spenden WHERE projekt=" + str(id))
    # conn.commit()
    # 4) --- Delete Projekt ---
    # curs.execute("DELETE FROM projekt WHERE kennung=" + str(id))
    # conn.commit()
    return redirect(url_for("viewMainGet"))


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

@app.route('/view_project', methods=['GET'])
def viewProjectGet():
    id = request.args.get('kennung')
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
    return render_template("view_project.html", kennung=id, pfad=pfad, titel=titel, ersteller=ersteller, beschreibung=beschreibung, finanzierungslimit=finanzierungslimit, spendensumme=spendensumme, status=status, vorgaenger=vorgaenger, spender=spender, kommentare=kommentare)

@app.route('/edit_project', methods=['GET']) 
def editProjectGet():
    id = request.args.get('kennung') # takes the value of the button "Projekt editieren"
    conn = connect.DBUtil().getExternalConnection()
    conn.jconn.setAutoCommit(False)
    curs = conn.cursor()
    curs.execute("SELECT kennung, titel, CAST(beschreibung AS VARCHAR(1000)) AS beschreibung, status, finanzierungslimit, ersteller, vorgaenger, kategorie FROM projekt WHERE kennung = " + str(id))
    result = curs.fetchall()[0]
    titel = result[1]
    beschreibung = result[2]
    finanzierungslimit = result[4]
    vorgaenger = result[6] # projekt id (nur 1)
    curs.execute("SELECT kennung, titel FROM projekt WHERE ersteller = '" + currentUser + "'")
    projekte = curs.fetchall()
    kategorie = result[7]
    health, art, edu, tech = '', '', '', ''
    if kategorie == 1:
        health = 'checked'
    elif kategorie == 2:
        art = 'checked'
    elif kategorie == 3:
        edu = 'checked'
    elif kategorie == 4:
        tech = 'checked'
    return render_template('edit_project.html', kennung=id, titel=titel, finanzierungslimit=finanzierungslimit, health=health, art=art, edu=edu, tech=tech, vorgaenger=projekte, before=vorgaenger, beschreibung=beschreibung)

@app.route('/edit_project', methods=['POST']) 
def editProjectPost():
    id = request.form['kennung']
    titel = request.form['titel']
    finanzierungslimit = request.form['finanzierungslimit']
    kategorie = request.form['kategorie']
    vorgaenger = request.form['vorgaenger']
    beschreibung = request.form['beschreibung']
    conn = connect.DBUtil().getExternalConnection()
    conn.jconn.setAutoCommit(False)
    curs = conn.cursor()
    curs.execute("UPDATE projekt SET titel = ?, finanzierungslimit = ?, kategorie = ?, vorgaenger = ?, beschreibung = ? WHERE kennung = ?", (titel, finanzierungslimit, kategorie, vorgaenger, beschreibung, id))
    conn.commit()
    return redirect(url_for('viewProjectGet', kennung=id))

@app.route('/new_project_fund', methods=['GET'])
def newProjectFundGet():
    id = request.args.get('kennung')
    conn = connect.DBUtil().getExternalConnection()
    conn.jconn.setAutoCommit(False)
    curs = conn.cursor()
    curs.execute("SELECT titel FROM projekt WHERE kennung = " + str(id))
    titel = curs.fetchall()
    titel = titel[0][0]
    return render_template('new_project_fund.html', titel=titel, kennung=id)

@app.route('/new_project_fund', methods=['POST'])
def newProjectFundPost():
    id = request.form['kennung']
    spender = currentUser
    spendenbetrag = request.form['spendenbetrag']
    if request.form.get('anonym'):
        sichtbarkeit = request.form.get('anonym')
    else:
        sichtbarkeit = 'oeffentlich'
    conn = connect.DBUtil().getExternalConnection()
    conn.jconn.setAutoCommit(False)
    curs = conn.cursor()
    curs.execute("INSERT INTO spenden (spender, projekt, spendenbetrag, sichtbarkeit) VALUES (?,?,?,?)", (spender, id, spendenbetrag, sichtbarkeit))
    # conn.commit()
    curs.execute("UPDATE konto SET guthaben=guthaben-" + str(spendenbetrag) + " WHERE inhaber = '" + spender + "'")
    # conn.commit()
    return redirect(url_for('viewProjectGet', kennung=id))

@app.route('/view_profile', methods=['GET'])
def viewProfileGet():
    if request.args.get('benutzer'):
        email = request.args.get('benutzer')
    else:
        email = currentUser
    conn = connect.DBUtil().getExternalConnection()
    conn.jconn.setAutoCommit(False)
    curs = conn.cursor()
    curs.execute("SELECT name FROM benutzer WHERE email = '" + email + "'")
    name = curs.fetchall()
    name = name[0][0]
    curs.execute("SELECT kennung, titel, status, kategorie.icon FROM projekt JOIN kategorie ON projekt.kategorie=kategorie.id WHERE ersteller='" + email + "'")
    # curs.execute("WITH s(proj, totalSpende) AS (SELECT projekt, SUM(spendenbetrag) AS totalSpende FROM spenden GROUP BY projekt) SELECT p.kennung, p.titel, s.totalSpende, p.status, k.icon FROM projekt p, kategorie k, s WHERE p.kategorie=k.id AND p.kennung=s.proj AND p.ersteller = '" + email + "'")
    erstellt = curs.fetchall() # [(1, 'Ubuntu Touch', 1500.56, 'offen', '/static/...'), ...]
    print(erstellt)
    projektIDs = [str(er[0]) for er in erstellt]
    projektIDs = ','.join(projektIDs)
    curs.execute("SELECT projekt, SUM(spendenbetrag) FROM spenden WHERE projekt IN (" + projektIDs + ") GROUP BY projekt")
    spendenbetraege = curs.fetchall()
    if len(spendenbetraege)>0:
        erstellt = [(er[0], er[1], spendenbetrag[1], er[2], er[3]) if spendenbetrag[0] == er[0] else (er[0], er[1], 0, er[2], er[3]) for er in erstellt for spendenbetrag in spendenbetraege]
    else:
        erstellt = [(er[0], er[1], 0, er[2], er[3]) for er in erstellt]
    curs.execute("SELECT p.kennung, p.titel, p.finanzierungslimit, p.status, k.icon, s.spendenbetrag FROM spenden s, projekt p, kategorie k WHERE p.kategorie=k.id AND s.projekt=p.kennung AND s.sichtbarkeit='oeffentlich' AND s.spender='" + email + "'")
    unterstuetzt = curs.fetchall() # [(1, 'Ubuntu Touch', 50000, 'offen', '/static/...', 1500.56), ...]
    return render_template("view_profile.html", email=email, name=name, noErstellt=len(erstellt), noUnterstuetzt=len(unterstuetzt), erstellt=erstellt, unterstuetzt=unterstuetzt)

@app.route('/new_comment', methods=['GET'])
def newCommentGet():
    id = request.args.get('kennung')
    conn = connect.DBUtil().getExternalConnection()
    conn.jconn.setAutoCommit(False)
    curs = conn.cursor()
    curs.execute("SELECT titel FROM projekt WHERE kennung = " + str(id))
    titel = curs.fetchall()
    titel = titel[0][0]
    return render_template('new_comment.html', titel=titel, kennung=id)

@app.route('/new_comment', methods=['POST'])
def newCommentPost():
    id = request.form['kennung']
    print("projekt id:", id)
    text = request.form.get('comment')
    if request.form.get('anonym'):
        sichtbarkeit = request.form.get('anonym')
    else:
        sichtbarkeit = 'oeffentlich'
    conn = connect.DBUtil().getExternalConnection()
    conn.jconn.setAutoCommit(False)
    curs = conn.cursor()
    curs.execute("INSERT INTO kommentar (text, sichtbarkeit) VALUES (?,?)", (text, sichtbarkeit))
    conn.commit()
    curs.execute("SELECT MAX(id) FROM kommentar")
    kid = curs.fetchall()
    kid = kid[0][0]
    curs.execute("INSERT INTO schreibt (benutzer, projekt, kommentar) VALUES (?,?,?)", (currentUser, id, kid))
    conn.commit()
    return redirect(url_for('viewProjectGet', kennung=id))

if __name__ == "__main__":
    port = int("9" + re.match(r"([a-z]+)([0-9]+)", config["username"], re.I).groups()[1])
    app.run(host='0.0.0.0', port=port, debug=True)
