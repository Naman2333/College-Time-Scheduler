
from flask import Flask, render_template, request, jsonify
import sqlite3

app = Flask(__name__)

DATABASE = "scheduler.db"

DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]

# Eight periods each day
PERIODS = [
    "09:00 - 10:00",
    "10:00 - 11:00",
    "11:00 - 12:00",
    "12:00 - 01:00",
    "01:00 - 02:00",
    "02:00 - 03:00",
    "03:00 - 04:00",
    "04:00 - 05:00"
]


def get_db():
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_database():
    connection = get_db()

    connection.execute("""
        CREATE TABLE IF NOT EXISTS subjects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            subject TEXT NOT NULL,
            teacher TEXT NOT NULL,
            student_group TEXT NOT NULL,
            classroom TEXT NOT NULL,
            sessions INTEGER NOT NULL
        )
    """)

    connection.execute("""
        CREATE TABLE IF NOT EXISTS timetable (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            subject_id INTEGER NOT NULL,
            day TEXT NOT NULL,
            period INTEGER NOT NULL,
            FOREIGN KEY(subject_id) REFERENCES subjects(id)
        )
    """)

    connection.commit()
    connection.close()


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/api/subjects", methods=["GET"])
def get_subjects():
    connection = get_db()

    rows = connection.execute(
        "SELECT * FROM subjects ORDER BY id DESC"
    ).fetchall()

    connection.close()

    return jsonify([dict(row) for row in rows])


@app.route("/api/subjects", methods=["POST"])
def add_subject():
    data = request.get_json(silent=True) or {}

    subject = str(data.get("subject", "")).strip()
    teacher = str(data.get("teacher", "")).strip()
    student_group = str(data.get("student_group", "")).strip()
    classroom = str(data.get("classroom", "")).strip()

    try:
        sessions = int(data.get("sessions", 1))
    except (ValueError, TypeError):
        return jsonify({"error": "Sessions must be a number."}), 400

    if not all([subject, teacher, student_group, classroom]):
        return jsonify({"error": "Please fill in every field."}), 400

    if not 1 <= sessions <= 40:
        return jsonify({
            "error": "Sessions must be between 1 and 40."
        }), 400

    connection = get_db()

    connection.execute("""
        INSERT INTO subjects
        (subject, teacher, student_group, classroom, sessions)
        VALUES (?, ?, ?, ?, ?)
    """, (subject, teacher, student_group, classroom, sessions))

    connection.commit()
    connection.close()

    return jsonify({"message": "Subject added successfully!"}), 201


@app.route("/api/subjects/<int:subject_id>", methods=["DELETE"])
def delete_subject(subject_id):
    connection = get_db()

    connection.execute(
        "DELETE FROM timetable WHERE subject_id = ?",
        (subject_id,)
    )

    cursor = connection.execute(
        "DELETE FROM subjects WHERE id = ?",
        (subject_id,)
    )

    connection.commit()
    connection.close()

    if cursor.rowcount == 0:
        return jsonify({"error": "Subject not found."}), 404

    return jsonify({"message": "Subject deleted successfully!"})


def conflicts(subject, day, period, scheduled):
    for item in scheduled:
        if item["day"] != day or item["period"] != period:
            continue

        # A teacher cannot teach two classes at once.
        if item["teacher"].casefold() == subject["teacher"].casefold():
            return True

        # A student group cannot attend two classes at once.
        if item["student_group"].casefold() == subject["student_group"].casefold():
            return True

        # A classroom cannot host two classes at once.
        if item["classroom"].casefold() == subject["classroom"].casefold():
            return True

    return False


def generate_schedule(subjects):
    scheduled = []

    # Greedy algorithm: assign each requested session
    # to the first available day and period.
    for subject in subjects:
        for _ in range(subject["sessions"]):
            placed = False

            for day in DAYS:
                for period in range(len(PERIODS)):
                    if not conflicts(subject, day, period, scheduled):
                        scheduled.append({
                            "subject_id": subject["id"],
                            "subject": subject["subject"],
                            "teacher": subject["teacher"],
                            "student_group": subject["student_group"],
                            "classroom": subject["classroom"],
                            "day": day,
                            "period": period
                        })

                        placed = True
                        break

                if placed:
                    break

            if not placed:
                return None, subject["subject"]

    return scheduled, None


@app.route("/api/generate", methods=["POST"])
def generate():
    connection = get_db()

    rows = connection.execute(
        "SELECT * FROM subjects ORDER BY sessions DESC, id ASC"
    ).fetchall()

    subjects = [dict(row) for row in rows]

    if not subjects:
        connection.close()
        return jsonify({
            "error": "Add some subjects before generating a timetable."
        }), 400

    # Generate everything before saving, so a failed
    # attempt does not overwrite the previous timetable.
    scheduled, failed_subject = generate_schedule(subjects)

    if scheduled is None:
        connection.close()
        return jsonify({
            "error": (
                "Unable to schedule all sessions. "
                f"Please reduce the workload or add more periods. "
                f"Could not place: {failed_subject}."
            )
        }), 409

    connection.execute("DELETE FROM timetable")

    connection.executemany("""
        INSERT INTO timetable (subject_id, day, period)
        VALUES (?, ?, ?)
    """, [
        (item["subject_id"], item["day"], item["period"])
        for item in scheduled
    ])

    connection.commit()
    connection.close()

    return jsonify({
        "message": "Timetable generated successfully!",
        "count": len(scheduled)
    })


@app.route("/api/timetable", methods=["GET"])
def get_timetable():
    connection = get_db()

    rows = connection.execute("""
        SELECT
            timetable.day,
            timetable.period,
            subjects.subject,
            subjects.teacher,
            subjects.student_group,
            subjects.classroom
        FROM timetable
        JOIN subjects ON subjects.id = timetable.subject_id
    """).fetchall()

    connection.close()

    return jsonify([dict(row) for row in rows])


@app.route("/api/reset", methods=["POST"])
def reset_timetable():
    connection = get_db()
    connection.execute("DELETE FROM timetable")
    connection.commit()
    connection.close()

    return jsonify({"message": "Timetable cleared successfully!"})


initialize_database()

if __name__ == "__main__":
    app.run(debug=True)
