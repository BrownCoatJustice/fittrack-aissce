from flask import Flask, render_template, request, redirect, session
import sqlite3
from datetime import date

app = Flask(__name__)
app.secret_key = "fitness-final-project"
DB = "fitness.db"

def get_db():
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    return con

def init_db():
    con = get_db()
    con.executescript("""
    CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL
    );
    CREATE TABLE IF NOT EXISTS logs(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        log_date TEXT NOT NULL,
        steps INTEGER DEFAULT 0,
        workout INTEGER DEFAULT 0,
        water INTEGER DEFAULT 0,
        sleep REAL DEFAULT 0,
        FOREIGN KEY(user_id) REFERENCES users(id)
    );
    """)
    con.commit(); con.close()

@app.route("/", methods=["GET","POST"])
def login():
    if request.method=="POST":
        name=request.form["name"].strip()
        con=get_db()
        user=con.execute("SELECT id FROM users WHERE name=?",(name,)).fetchone()
        if user: uid=user["id"]
        else:
            cur=con.execute("INSERT INTO users(name) VALUES(?)",(name,))
            con.commit(); uid=cur.lastrowid
        con.close()
        session["uid"]=uid; session["name"]=name
        return redirect("/dashboard")
    return render_template("login.html")

@app.route("/dashboard", methods=["GET","POST"])
def dashboard():
    if "uid" not in session: return redirect("/")
    con=get_db()
    if request.method=="POST":
        con.execute("""INSERT INTO logs(user_id,log_date,steps,workout,water,sleep)
                       VALUES(?,?,?,?,?,?)""",
                    (session["uid"],str(date.today()),
                     int(request.form["steps"] or 0),
                     int(request.form["workout"] or 0),
                     int(request.form["water"] or 0),
                     float(request.form["sleep"] or 0)))
        con.commit()
    stats=con.execute("""SELECT COALESCE(SUM(steps),0) steps,
        COALESCE(SUM(workout),0) workout, COALESCE(SUM(water),0) water,
        COALESCE(AVG(sleep),0) sleep FROM logs WHERE user_id=?""",
        (session["uid"],)).fetchone()
    logs=con.execute("""SELECT log_date,steps,workout,water,sleep FROM logs
        WHERE user_id=? ORDER BY log_date DESC,id DESC LIMIT 10""",
        (session["uid"],)).fetchall()
    chart_rows=con.execute("""SELECT log_date,steps,workout FROM logs
        WHERE user_id=? ORDER BY log_date ASC,id ASC""",
        (session["uid"],)).fetchall()
    points=int(stats["steps"]/1000+stats["workout"]+stats["water"]*2)
    con.close()
    return render_template("dashboard.html",name=session["name"],stats=stats,
                           points=points,logs=logs,chart_rows=chart_rows)

@app.route("/leaderboard")
def leaderboard():
    con=get_db()
    board=con.execute("""SELECT u.name,
        COALESCE(SUM(l.steps/1000+l.workout+l.water*2),0) score
        FROM users u LEFT JOIN logs l ON l.user_id=u.id
        GROUP BY u.id ORDER BY score DESC""").fetchall()
    con.close()
    return render_template("leaderboard.html",board=board)

@app.route("/logout")
def logout():
    session.clear(); return redirect("/")

if __name__=="__main__":
    init_db()
    app.run(debug=True)
