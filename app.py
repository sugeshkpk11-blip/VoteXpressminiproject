from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps

app = Flask(__name__)
app.secret_key = "change-this-secret-key"
DB = "voting.db"

def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS voters (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        voter_id TEXT UNIQUE NOT NULL,
        name TEXT NOT NULL,
        email TEXT NOT NULL,
        password TEXT NOT NULL,
        has_voted INTEGER DEFAULT 0
    );

    CREATE TABLE IF NOT EXISTS candidates (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        party TEXT NOT NULL,
        symbol TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS votes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        voter_id INTEGER NOT NULL,
        candidate_id INTEGER NOT NULL,
        voted_at TEXT DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(voter_id),
        FOREIGN KEY(voter_id) REFERENCES voters(id),
        FOREIGN KEY(candidate_id) REFERENCES candidates(id)
    );

    CREATE TABLE IF NOT EXISTS admins (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL
    );
    """)
    admin = conn.execute("SELECT id FROM admins WHERE username=?", ("admin",)).fetchone()
    if not admin:
        conn.execute(
            "INSERT INTO admins(username,password) VALUES(?,?)",
            ("admin", generate_password_hash("admin123"))
        )
    count = conn.execute("SELECT COUNT(*) AS c FROM candidates").fetchone()["c"]
    if count == 0:
        conn.executemany(
            "INSERT INTO candidates(name,party,symbol) VALUES(?,?,?)",
            [
                ("Arun Kumar", "People's Party", "🌳"),
                ("Priya Devi", "Development Party", "⭐"),
                ("Rahul Raj", "Progress Party", "🕊️")
            ]
        )
    conn.commit()
    conn.close()

def voter_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if "voter_db_id" not in session:
            flash("Please log in as a voter.", "error")
            return redirect(url_for("voter_login"))
        return f(*args, **kwargs)
    return wrapper

def admin_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if "admin_id" not in session:
            flash("Please log in as administrator.", "error")
            return redirect(url_for("admin_login"))
        return f(*args, **kwargs)
    return wrapper

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        voter_id = request.form["voter_id"].strip()
        name = request.form["name"].strip()
        email = request.form["email"].strip()
        password = request.form["password"]

        if not voter_id or not name or not email or len(password) < 6:
            flash("Enter all details. Password must contain at least 6 characters.", "error")
            return render_template("voter_register.html")

        conn = get_db()
        try:
            conn.execute(
                "INSERT INTO voters(voter_id,name,email,password) VALUES(?,?,?,?)",
                (voter_id, name, email, generate_password_hash(password))
            )
            conn.commit()
            flash("Registration successful. You can now log in.", "success")
            return redirect(url_for("voter_login"))
        except sqlite3.IntegrityError:
            flash("Voter ID already exists.", "error")
        finally:
            conn.close()
    return render_template("voter_register.html")

@app.route("/voter/login", methods=["GET", "POST"])
def voter_login():
    if request.method == "POST":
        voter_id = request.form["voter_id"].strip()
        password = request.form["password"]

        conn = get_db()
        voter = conn.execute("SELECT * FROM voters WHERE voter_id=?", (voter_id,)).fetchone()
        conn.close()

        if voter and check_password_hash(voter["password"], password):
            session.clear()
            session["voter_db_id"] = voter["id"]
            session["voter_name"] = voter["name"]
            return redirect(url_for("vote"))
        flash("Invalid Voter ID or password.", "error")
    return render_template("voter_login.html")

@app.route("/vote", methods=["GET", "POST"])
@voter_required
def vote():
    conn = get_db()
    voter = conn.execute("SELECT * FROM voters WHERE id=?", (session["voter_db_id"],)).fetchone()

    if request.method == "POST":
        if voter["has_voted"]:
            conn.close()
            flash("You have already voted.", "error")
            return redirect(url_for("vote"))

        candidate_id = request.form.get("candidate_id")
        candidate = conn.execute("SELECT * FROM candidates WHERE id=?", (candidate_id,)).fetchone()

        if not candidate:
            conn.close()
            flash("Invalid candidate selected.", "error")
            return redirect(url_for("vote"))

        try:
            conn.execute("INSERT INTO votes(voter_id,candidate_id) VALUES(?,?)",
                         (voter["id"], candidate["id"]))
            conn.execute("UPDATE voters SET has_voted=1 WHERE id=?", (voter["id"],))
            conn.commit()
            flash("Your vote has been recorded successfully!", "success")
            return redirect(url_for("results"))
        except sqlite3.IntegrityError:
            conn.rollback()
            flash("A vote already exists for this voter.", "error")
            return redirect(url_for("vote"))

    candidates = conn.execute("SELECT * FROM candidates ORDER BY id").fetchall()
    conn.close()
    return render_template("vote.html", voter=voter, candidates=candidates)

@app.route("/results")
def results():
    conn = get_db()
    results = conn.execute("""
        SELECT c.id, c.name, c.party, c.symbol, COUNT(v.id) AS vote_count
        FROM candidates c
        LEFT JOIN votes v ON c.id = v.candidate_id
        GROUP BY c.id
        ORDER BY vote_count DESC, c.name ASC
    """).fetchall()
    total = conn.execute("SELECT COUNT(*) AS c FROM votes").fetchone()["c"]
    conn.close()
    return render_template("result.html", results=results, total=total)

@app.route("/voter/logout")
def voter_logout():
    session.clear()
    return redirect(url_for("index"))

@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        username = request.form["username"].strip()
        password = request.form["password"]

        conn = get_db()
        admin = conn.execute("SELECT * FROM admins WHERE username=?", (username,)).fetchone()
        conn.close()

        if admin and check_password_hash(admin["password"], password):
            session.clear()
            session["admin_id"] = admin["id"]
            session["admin_username"] = admin["username"]
            return redirect(url_for("admin_dashboard"))
        flash("Invalid administrator credentials.", "error")
    return render_template("admin_login.html")

@app.route("/admin/dashboard")
@admin_required
def admin_dashboard():
    conn = get_db()
    candidates = conn.execute("""
        SELECT c.*, COUNT(v.id) AS vote_count
        FROM candidates c
        LEFT JOIN votes v ON c.id=v.candidate_id
        GROUP BY c.id
        ORDER BY c.id
    """).fetchall()
    voter_count = conn.execute("SELECT COUNT(*) AS c FROM voters").fetchone()["c"]
    voted_count = conn.execute("SELECT COUNT(*) AS c FROM voters WHERE has_voted=1").fetchone()["c"]
    conn.close()
    return render_template(
        "admin_dashboard.html",
        candidates=candidates,
        voter_count=voter_count,
        voted_count=voted_count
    )

@app.route("/admin/candidate/add", methods=["POST"])
@admin_required
def add_candidate():
    name = request.form["name"].strip()
    party = request.form["party"].strip()
    symbol = request.form["symbol"].strip()

    if not name or not party or not symbol:
        flash("All candidate fields are required.", "error")
        return redirect(url_for("admin_dashboard"))

    conn = get_db()
    conn.execute("INSERT INTO candidates(name,party,symbol) VALUES(?,?,?)",
                 (name, party, symbol))
    conn.commit()
    conn.close()
    flash("Candidate added successfully.", "success")
    return redirect(url_for("admin_dashboard"))

@app.route("/admin/candidate/delete/<int:candidate_id>", methods=["POST"])
@admin_required
def delete_candidate(candidate_id):
    conn = get_db()
    used = conn.execute("SELECT COUNT(*) AS c FROM votes WHERE candidate_id=?",
                        (candidate_id,)).fetchone()["c"]
    if used:
        flash("This candidate cannot be deleted after receiving votes.", "error")
    else:
        conn.execute("DELETE FROM candidates WHERE id=?", (candidate_id,))
        conn.commit()
        flash("Candidate deleted.", "success")
    conn.close()
    return redirect(url_for("admin_dashboard"))

@app.route("/admin/logout")
def admin_logout():
    session.clear()
    return redirect(url_for("index"))

if __name__ == "__main__":
    init_db()
    app.run(debug=True)
