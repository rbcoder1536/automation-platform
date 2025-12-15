from flask import Flask, render_template, request, redirect, session
import os
from backend.database import connect, create_tables

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret")

create_tables()

# ---------- LOGIN ----------
@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        u = request.form["username"]
        p = request.form["password"]

        conn = connect()
        c = conn.cursor()
        c.execute(
            "SELECT id, role FROM users WHERE username=? AND password=?",
            (u, p)
        )
        user = c.fetchone()
        conn.close()

        if user:
            session["user_id"] = user[0]
            session["role"] = user[1]
            return redirect("/dashboard")

    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

# ---------- DASHBOARD ----------
@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect("/")

    conn = connect()
    c = conn.cursor()

    c.execute("SELECT COUNT(*) FROM tasks")
    total = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM tasks WHERE status='Approved'")
    approved = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM tasks WHERE status='Rejected'")
    rejected = c.fetchone()[0]

    c.execute("SELECT COUNT(*) FROM tasks WHERE status='Pending'")
    pending = c.fetchone()[0]

    c.execute("""
        SELECT tasks.id, tasks.title, users.username, tasks.status
        FROM tasks
        JOIN users ON tasks.assigned_to = users.id
        ORDER BY tasks.id DESC
    """)
    tasks = c.fetchall()
    conn.close()

    return render_template(
        "dashboard.html",
        total=total,
        approved=approved,
        rejected=rejected,
        pending=pending,
        tasks=tasks,
        role=session["role"]
    )

# ---------- CREATE TASK ----------
@app.route("/tasks/create", methods=["POST"])
def create_task():
    if session["role"] != "Employee":
        return redirect("/dashboard")

    conn = connect()
    c = conn.cursor()
    c.execute("""
        INSERT INTO tasks (title, assigned_to, status, created_by)
        VALUES (?, ?, 'Pending', ?)
    """, (
        request.form["title"],
        request.form["assigned_to"],
        session["user_id"]
    ))
    conn.commit()
    conn.close()

    return redirect("/dashboard")

# ---------- LOG ACTION ----------
def log_action(task_id, action):
    conn = connect()
    c = conn.cursor()
    c.execute("""
        INSERT INTO activity_logs (task_id, action, performed_by)
        VALUES (?, ?, ?)
    """, (task_id, action, session["user_id"]))
    conn.commit()
    conn.close()

# ---------- APPROVE / REJECT ----------
@app.route("/tasks/approve/<int:id>")
def approve(id):
    if session["role"] == "Manager":
        conn = connect()
        c = conn.cursor()
        c.execute("UPDATE tasks SET status='Approved' WHERE id=?", (id,))
        conn.commit()
        conn.close()
        log_action(id, "Approved")
    return redirect("/dashboard")

@app.route("/tasks/reject/<int:id>")
def reject(id):
    if session["role"] == "Manager":
        conn = connect()
        c = conn.cursor()
        c.execute("UPDATE tasks SET status='Rejected' WHERE id=?", (id,))
        conn.commit()
        conn.close()
        log_action(id, "Rejected")
    return redirect("/dashboard")

# ---------- AUDIT LOGS ----------
@app.route("/audit")
def audit():
    if "user_id" not in session:
        return redirect("/")

    conn = connect()
    c = conn.cursor()
    c.execute("""
        SELECT activity_logs.task_id,
               activity_logs.action,
               users.username,
               activity_logs.timestamp
        FROM activity_logs
        JOIN users ON activity_logs.performed_by = users.id
        ORDER BY activity_logs.timestamp DESC
    """)
    logs = c.fetchall()
    conn.close()

    return render_template(
        "audit.html",
        logs=logs,
        role=session["role"]
    )

@app.route("/seed")
def seed():
    from backend.seed_users import seed_users
    seed_users()
    return "Users seeded"


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
