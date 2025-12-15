from backend.database import connect

conn = connect()
c = conn.cursor()

users = [
    ("admin", "admin123", "Admin"),
    ("manager", "manager123", "Manager"),
    ("employee", "employee123", "Employee")
]

for u in users:
    try:
        c.execute(
            "INSERT INTO users (username,password,role) VALUES (?,?,?)", u
        )
    except:
        pass

conn.commit()
conn.close()
print("Users seeded successfully")
