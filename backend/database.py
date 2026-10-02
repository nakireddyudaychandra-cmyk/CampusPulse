import sqlite3

DATABASE = "campuspulse.db"


def get_connection():
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row
    return connection


def create_tables():

    connection = get_connection()
    cursor = connection.cursor()

    # ==========================================
    # ISSUES TABLE
    # ==========================================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS issues (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            location TEXT NOT NULL,
            category TEXT,
            priority TEXT,
            status TEXT DEFAULT 'OPEN'
        )
    """)

    # ==========================================
    # STAFF TABLE
    # ==========================================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS staff (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            specialization TEXT NOT NULL,
            phone TEXT,
            available INTEGER DEFAULT 1
        )
    """)

    # ==========================================
    # CHECK WHETHER assigned_staff_id EXISTS
    # ==========================================

    cursor.execute("PRAGMA table_info(issues)")

    columns = [
        row["name"]
        for row in cursor.fetchall()
    ]

    # Add assigned_staff_id only if it doesn't exist

    if "assigned_staff_id" not in columns:

        cursor.execute("""
            ALTER TABLE issues
            ADD COLUMN assigned_staff_id INTEGER
        """)

    # ==========================================
    # ADD SAMPLE STAFF
    # ==========================================

    cursor.execute("SELECT COUNT(*) FROM staff")

    staff_count = cursor.fetchone()[0]

    if staff_count == 0:

        cursor.execute("""
            INSERT INTO staff
            (name, specialization, phone, available)
            VALUES (?, ?, ?, ?)
        """, (
            "Ravi Kumar",
            "AC/HVAC",
            "9876543210",
            1
        ))

        cursor.execute("""
            INSERT INTO staff
            (name, specialization, phone, available)
            VALUES (?, ?, ?, ?)
        """, (
            "Suresh Babu",
            "Electrical",
            "9876543211",
            1
        ))

        cursor.execute("""
            INSERT INTO staff
            (name, specialization, phone, available)
            VALUES (?, ?, ?, ?)
        """, (
            "Arjun Reddy",
            "Network",
            "9876543212",
            1
        ))

        cursor.execute("""
            INSERT INTO staff
            (name, specialization, phone, available)
            VALUES (?, ?, ?, ?)
        """, (
            "Manoj Kumar",
            "Plumbing",
            "9876543213",
            1
        ))

        cursor.execute("""
            INSERT INTO staff
            (name, specialization, phone, available)
            VALUES (?, ?, ?, ?)
        """, (
            "Kiran Rao",
            "General Maintenance",
            "9876543214",
            1
        ))

    connection.commit()

    connection.close()