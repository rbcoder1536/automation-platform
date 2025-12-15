from flask import Flask, render_template, request, redirect, session, url_for
from backend.database import connect, create_tables
import os

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "render-demo-secret")

# -------------------------------
# DATABASE INITIALIZATION
# -------------------------------
create_tables()

def auto_seed_users():
    conn = connect()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM users")
    count = c.fetchone()[0]

    if count == 0:
        users = [
            ("admin", "admin123", "Admin"),
            ("manager", "manager123", "Manager"),
            ("employee", "employee123", "Employee")
        ]
        for u in users:
            c.execute(
                "INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
                u
            )
        conn.commit()

    conn.close()

auto_seed_users()

# -------------------------------
# AUTHENTICATION
# -------------------------------
@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        conn = connect()
        c = conn.cursor()
        c.execute(
            "SELECT id, role FROM users WHERE username=? AND password=?",
            (username, password)
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


# -------------------------------
# DASHBOARD
# -------------------------------
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


# -------------------------------
# CREATE TASK
# -------------------------------
@app.route("/tasks/create", methods=["POST"])
def create_task():
    if "user_id" not in session or session["role"] != "Employee":
        return redirect("/dashboard")

    title = request.form["title"]
    assigned_to = request.form["assigned_to"]

    conn = connect()
    c = conn.cursor()
    c.execute("""
        INSERT INTO tasks (title, assigned_to, status, created_by)
        VALUES (?, ?, 'Pending', ?)
    """, (title, assigned_to, session["user_id"]))
    conn.commit()
    conn.close()

    return redirect("/dashboard")


# -------------------------------
# AUDIT LOGGING
# -------------------------------
def log_action(task_id, action):
    conn = connect()
    c = conn.cursor()
    c.execute("""
        INSERT INTO activity_logs (task_id, action, performed_by)
        VALUES (?, ?, ?)
    """, (task_id, action, session["user_id"]))
    conn.commit()
    conn.close()


@app.route("/tasks/approve/<int:task_id>")
def approve_task(task_id):
    if session.get("role") != "Manager":
        return redirect("/dashboard")

    conn = connect()
    c = conn.cursor()
    c.execute("UPDATE tasks SET status='Approved' WHERE id=?", (task_id,))
    conn.commit()
    conn.close()

    log_action(task_id, "Approved")
    return redirect("/dashboard")


@app.route("/tasks/reject/<int:task_id>")
def reject_task(task_id):
    if session.get("role") != "Manager":
        return redirect("/dashboard")

    conn = connect()
    c = conn.cursor()
    c.execute("UPDATE tasks SET status='Rejected' WHERE id=?", (task_id,))
    conn.commit()
    conn.close()

    log_action(task_id, "Rejected")
    return redirect("/dashboard")


# -------------------------------
# AUDIT LOGS VIEW
# -------------------------------
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

    return render_template("audit.html", logs=logs, role=session["role"])


# -------------------------------
# DEBUG (SAFE TO REMOVE LATER)
# -------------------------------
@app.route("/debug-users")
def debug_users():
    conn = connect()
    c = conn.cursor()
    c.execute("SELECT id, username, role FROM users")
    users = c.fetchall()
    conn.close()
    return {"users": users}


# -------------------------------
# LOCAL RUN
# -------------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
