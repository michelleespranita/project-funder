from flask import Flask, request, render_template, url_for, redirect
# import user
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

currentUser = 'dummy@dummy.com' # default user

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

    offeneProjekteIDs = [offenesProjekt[0] for offenesProjekt in offeneProjekte]
    spendenbetraegeIDs = [spendenbetrag[0] for spendenbetrag in spendenbetraege]
    offeneProjekteHTML = []

    i = 0
    for offenesProjektID in offeneProjekteIDs:
        if offenesProjektID in spendenbetraegeIDs:
            offenesProjekt = offeneProjekte[i]
            spendenbetrag = [spendenbetrag[1] for spendenbetrag in spendenbetraege if offenesProjektID == spendenbetrag[0]]
            spendenbetrag = spendenbetrag[0]
            offeneProjekteHTML.append((offenesProjekt[0], offenesProjekt[1], offenesProjekt[2], offenesProjekt[3], spendenbetrag))
        else:
            offenesProjekt = offeneProjekte[i]
            offeneProjekteHTML.append((offenesProjekt[0], offenesProjekt[1], offenesProjekt[2], offenesProjekt[3], 0))
        i+=1

    abgeschlosseneProjekteIDs = [abgeschlossenesProjekt[0] for abgeschlossenesProjekt in abgeschlosseneProjekte]
    abgeschlosseneProjekteHTML = []

    i = 0
    for abgeschlossenesProjektID in abgeschlosseneProjekteIDs:
        if abgeschlossenesProjektID in spendenbetraegeIDs:
            abgeschlossenesProjekt = abgeschlosseneProjekte[i]
            spendenbetrag = [spendenbetrag[1] for spendenbetrag in spendenbetraege if abgeschlossenesProjektID == spendenbetrag[0]]
            spendenbetrag = spendenbetrag[0]
            abgeschlosseneProjekteHTML.append((abgeschlossenesProjekt[0], abgeschlossenesProjekt[1], abgeschlossenesProjekt[2], abgeschlossenesProjekt[3], spendenbetrag))
        else:
            abgeschlossenesProjekt = abgeschlosseneProjekte[i]
            abgeschlosseneProjekteHTML.append((abgeschlossenesProjekt[0], abgeschlossenesProjekt[1], abgeschlossenesProjekt[2], abgeschlossenesProjekt[3], 0))
        i+=1

    return render_template("view_main.html", offeneProjekte=offeneProjekteHTML, abgeschlosseneProjekte=abgeschlosseneProjekteHTML)

@app.route('/new_project', methods=['GET'])
def newProjectGet():
    conn = connect.DBUtil().getExternalConnection()
    conn.jconn.setAutoCommit(False)
    curs = conn.cursor()
    warningTitel = request.args.get('warningTitel')
    warningLimit = request.args.get('warningLimit')
    sqlStatement = "SELECT * FROM projekt WHERE ersteller = ?", (currentUser,) # Change with prepared statement!
    curs.execute(sqlStatement)
    projekte = curs.fetchall()
    return render_template("new_project.html", vorgaenger=projekte, warningTitel=warningTitel, warningLimit=warningLimit)

@app.route('/new_project', methods=['POST'])
def newProjectPost():
    titel = request.form.get('titel')
    if titel == None:
        return redirect(url_for("newProjectGet", warningTitel=True))
    elif len(titel) > 30:
        return redirect(url_for("newProjectGet", warningTitel=True))
    finanzierungslimit = request.form.get('finanzierungslimit')
    if finanzierungslimit == None:
        return redirect(url_for("newProjectGet", warningLimit=True))
    elif float(finanzierungslimit) < 100:
        return redirect(url_for("newProjectGet", warningLimit=True))
    kategorie = request.form.get('kategorie')
    vorgaenger = request.form.get('vorgaenger')
    print(vorgaenger)
    if int(vorgaenger) == 0:
        vorgaenger = None
    beschreibung = request.form.get('beschreibung')
    ersteller = currentUser
    projectSt = projectStore.ProjectStore()
    projectSt.addProject(titel, finanzierungslimit, kategorie, beschreibung, ersteller, vorgaenger)
    projectSt.completion()
    projectSt.close() # Connection has to be closed when we want the changes that the SQL statement made to persist
    return redirect(url_for('viewMainGet'))

@app.route('/view_project', methods=['GET'])
def viewProjectGet():
    id = request.args.get('kennung')
    conn = connect.DBUtil().getExternalConnection()
    conn.jconn.setAutoCommit(False)
    curs = conn.cursor()
    curs.execute("SELECT kennung, titel, CAST(beschreibung AS VARCHAR(1000)) AS beschreibung, status, finanzierungslimit, ersteller, vorgaenger, kategorie FROM projekt WHERE kennung = ?", (id,))
    result = curs.fetchall()[0]
    titel = result[1]
    beschreibung = result[2]
    status = result[3]
    finanzierungslimit = result[4]
    ersteller = result[5]
    if ersteller == currentUser:
        showEditProject = True
    else:
        showEditProject = None
    curs.execute("SELECT email, name FROM benutzer WHERE email = ?", (ersteller,))
    ersteller = (ersteller, curs.fetchall()[0][1])
    vorgaenger = result[6]
    if vorgaenger != None:
        curs.execute("SELECT kennung, titel FROM projekt WHERE kennung = ?", (vorgaenger,))
        vorgaenger = curs.fetchall()
        vorgaenger = (vorgaenger[0][0], vorgaenger[0][1])
    else:
        vorgaenger = []
    kategorie = result[7]
    curs.execute("SELECT icon FROM kategorie WHERE id = ?", (kategorie,))
    pfad = curs.fetchall()[0][0]
    curs.execute("SELECT SUM(spendenbetrag) FROM spenden GROUP BY projekt HAVING projekt = ?", (id,))
    spendensumme = curs.fetchall()
    if len(spendensumme) > 0:
        spendensumme = spendensumme[0][0]
    else:
        spendensumme = 0
    curs.execute("SELECT benutzer.name, spendenbetrag, sichtbarkeit FROM spenden JOIN benutzer ON spenden.spender=benutzer.email WHERE spenden.projekt= ? ORDER BY spendenbetrag DESC", (id,))
    spender = curs.fetchall()
    curs.execute("SELECT b.name, CAST(k.text AS VARCHAR(1000)) AS text, k.sichtbarkeit, k.datum FROM benutzer b, schreibt s, kommentar k WHERE b.email=s.benutzer AND k.id=s.kommentar AND s.projekt=? ORDER BY k.datum DESC", (id,))
    kommentare = curs.fetchall()
    kommentare = [(kom[0], kom[1], kom[2], re.match('[0-9-]+ \d+:\d+', kom[3]).group(0)) for kom in kommentare]
    return render_template("view_project.html", kennung=id, pfad=pfad, titel=titel, ersteller=ersteller, beschreibung=beschreibung, finanzierungslimit=finanzierungslimit, spendensumme=spendensumme, status=status, vorgaenger=vorgaenger, spender=spender, kommentare=kommentare, showEditProject=showEditProject)

@app.route('/edit_project', methods=['GET']) 
def editProjectGet():
    id = request.args.get('kennung') # takes the value of the button "Projekt editieren"
    warningTitel = request.args.get('warningTitel')
    warningLimit = request.args.get('warningLimit')
    conn = connect.DBUtil().getExternalConnection()
    conn.jconn.setAutoCommit(False)
    curs = conn.cursor()
    curs.execute("SELECT kennung, titel, CAST(beschreibung AS VARCHAR(1000)) AS beschreibung, status, finanzierungslimit, ersteller, vorgaenger, kategorie FROM projekt WHERE kennung = ?", (id,))
    result = curs.fetchall()[0]
    titel = result[1]
    beschreibung = result[2]
    finanzierungslimit = result[4]
    vorgaenger = result[6] # projekt id (nur 1)
    curs.execute("SELECT kennung, titel FROM projekt WHERE ersteller = ?", (currentUser,))
    projekte = curs.fetchall() # [(1, 'Ubuntu Touch'), (2, 'Ubuntu Touch Pro'),...]
    kategorie = result[7]
    health, art, edu, tech = '', '', '', ''
    if kategorie == 1:
        health = 'selected'
    elif kategorie == 2:
        art = 'selected'
    elif kategorie == 3:
        edu = 'selected'
    elif kategorie == 4:
        tech = 'selected'
    return render_template('edit_project.html', kennung=id, titel=titel, finanzierungslimit=finanzierungslimit, health=health, art=art, edu=edu, tech=tech, vorgaenger=projekte, before=vorgaenger, beschreibung=beschreibung, warningTitel=warningTitel, warningLimit=warningLimit)

@app.route('/edit_project', methods=['POST']) 
def editProjectPost():
    id = request.form.get('kennung')
    titel = request.form.get('titel')
    if titel == None:
        return redirect(url_for("editProjectGet", kennung=id, warningTitel=True))
    elif len(titel) > 30:
        return redirect(url_for("editProjectGet", kennung=id, warningTitel=True))
    finanzierungslimit = request.form.get('finanzierungslimit')
    conn = connect.DBUtil().getExternalConnection()
    conn.jconn.setAutoCommit(False)
    curs = conn.cursor()
    curs.execute("SELECT finanzierungslimit FROM projekt WHERE kennung = ?", (id,))
    limitBefore = curs.fetchall()[0][0]
    if finanzierungslimit == None:
        return redirect(url_for("editProjectGet", kennung=id, warningLimit=True))
    elif float(finanzierungslimit) < 100 or float(finanzierungslimit) < float(limitBefore):
        return redirect(url_for("editProjectGet", kennung=id, warningLimit=True))
    kategorie = request.form.get('kategorie')
    vorgaenger = request.form.get('vorgaenger')
    if int(vorgaenger) == 0:
        vorgaenger = None
    beschreibung = request.form.get('beschreibung')
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

@app.route('/delete_project', methods=['GET'])
def viewMainPost():
    conn = connect.DBUtil().getExternalConnection()
    conn.jconn.setAutoCommit(False)
    curs = conn.cursor()
    id = request.args.get('kennung')
    # 1) --- Delete Kommentare ---
    curs.execute("SELECT kommentar FROM schreibt WHERE projekt = ?", (id,))
    kommentarIDs = curs.fetchall() # [(1,), (2,)]
    kommentarIDs = [kommentarID[0] for kommentarID in kommentarIDs] # [1,2]
    if len(kommentarIDs) > 0: # If there are actually any
        curs.execute("DELETE FROM schreibt WHERE projekt = ?", (id,))
        conn.commit()
        for kommentarID in kommentarIDs:
            curs.execute("DELETE FROM kommentar WHERE id = ?", (kommentarID,))
            conn.commit()
    # 2) --- Give money back to Spender ---
    curs.execute("SELECT spender, spendenbetrag FROM spenden WHERE projekt = ?", (id,))
    spend = curs.fetchall() # [('alan@turing.com', 15000.0), ('donald@eKnuth.com', 1500.56)]
    print(spend)
    for (spender, spendenbetrag) in spend:
        curs.execute("UPDATE konto SET guthaben = guthaben + ? WHERE inhaber = ?", (spendenbetrag, spender))
        conn.commit()
    # 3) --- Delete Spenden ---
    curs.execute("DELETE FROM spenden WHERE projekt = ?", (id,))
    conn.commit()
    # 4) --- Delete Projekt ---
    curs.execute("UPDATE projekt SET vorgaenger = NULL WHERE vorgaenger = ?", (id,))
    conn.commit()
    curs.execute("DELETE FROM projekt WHERE kennung = ?", (id,))
    conn.commit()
    return redirect(url_for("viewMainGet"))

@app.route('/new_project_fund', methods=['GET'])
def newProjectFundGet():
    conn = connect.DBUtil().getExternalConnection()
    conn.jconn.setAutoCommit(False)
    curs = conn.cursor()
    id = request.args.get('kennung')
    warning = request.args.get('warning')
    curs.execute("SELECT titel FROM projekt WHERE kennung = ?", (id,))
    titel = curs.fetchall()
    titel = titel[0][0]
    return render_template('new_project_fund.html', titel=titel, kennung=id, warning=warning)

@app.route('/new_project_fund', methods=['POST'])
def newProjectFundPost():
    conn = connect.DBUtil().getExternalConnection()
    conn.jconn.setAutoCommit(False)
    curs = conn.cursor()
    id = request.form['kennung']
    spender = currentUser
    curs.execute('SELECT * FROM spenden WHERE spender = ? AND projekt = ?', (spender, id))
    results = curs.fetchall()
    if len(results) > 0:
        return redirect(url_for('newProjectFundGet', kennung=id, warning=2))
    spendenbetrag = request.form['spendenbetrag']
    curs.execute("SELECT guthaben FROM konto WHERE inhaber = ?", (spender,))
    guthaben = curs.fetchall()[0][0]
    if float(spendenbetrag) > guthaben:
        return redirect(url_for('newProjectFundGet', kennung=id, warning=1))
    if request.form.get('anonym'):
        sichtbarkeit = request.form.get('anonym')
        print(sichtbarkeit)
    else:
        sichtbarkeit = 'oeffentlich'

    curs.execute("INSERT INTO spenden (spender, projekt, spendenbetrag, sichtbarkeit) VALUES (?,?,?,?)", (spender, id, spendenbetrag, sichtbarkeit))
    conn.commit()
    curs.execute("UPDATE konto SET guthaben=guthaben - ? WHERE inhaber = ?", (spendenbetrag, spender))
    conn.commit()

    # --- Überprüfe ob das Finanzierungslimit schon erreicht wird. Wenn ja, status offen -> geschlossen ---
    curs.execute("SELECT SUM(spendenbetrag) FROM spenden GROUP BY projekt HAVING projekt = ?", (id,))
    spendensumme = curs.fetchall()[0][0]
    curs.execute("SELECT finanzierungslimit FROM projekt WHERE kennung = ?", (id,))
    finanzierungslimit = curs.fetchall()[0][0]
    if spendensumme >= finanzierungslimit:
        curs.execute("UPDATE projekt SET status = 'geschlossen' WHERE kennung = ?", (id,))
        conn.commit()
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
    curs.execute("SELECT name FROM benutzer WHERE email =  ?", (email,))
    name = curs.fetchall()
    name = name[0][0]
    curs.execute("SELECT p.kennung, p.titel, p.status, k.icon, s.totalSpende FROM projekt p JOIN kategorie k ON p.kategorie=k.id LEFT JOIN (SELECT projekt, SUM(spendenbetrag) AS totalSpende FROM spenden GROUP BY projekt) AS s ON p.kennung=s.projekt WHERE p.ersteller = ? ORDER BY p.kennung", (email,))
    erstellt = curs.fetchall() # [(1, 'Ubuntu Touch', 'offen', '/static/...', 17351), ...]
    erstellt = [(er[0], er[1], er[2], er[3], er[4]) if er[4] != None else (er[0], er[1], er[2], er[3], 0) for er in erstellt]
    curs.execute("SELECT p.kennung, p.titel, p.finanzierungslimit, p.status, k.icon, s.spendenbetrag FROM spenden s, projekt p, kategorie k WHERE p.kategorie=k.id AND s.projekt=p.kennung AND s.sichtbarkeit='oeffentlich' AND s.spender=?", (email,))
    unterstuetzt = curs.fetchall() # [(1, 'Ubuntu Touch', 50000, 'offen', '/static/...', 1500.56), ...]
    return render_template("view_profile.html", email=email, name=name, noErstellt=len(erstellt), noUnterstuetzt=len(unterstuetzt), erstellt=erstellt, unterstuetzt=unterstuetzt)

@app.route('/new_comment', methods=['GET'])
def newCommentGet():
    id = request.args.get('kennung')
    conn = connect.DBUtil().getExternalConnection()
    conn.jconn.setAutoCommit(False)
    curs = conn.cursor()
    curs.execute("SELECT titel FROM projekt WHERE kennung = ?", (id,))
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
