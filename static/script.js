
const form = document.getElementById("subjectForm");
const statusMessage = document.getElementById("status");
const timetableStatus = document.getElementById("timetableStatus");

const days = [
    "Monday", "Tuesday", "Wednesday",
    "Thursday", "Friday"
];

const periods = [
    "09:00 - 10:00",
    "10:00 - 11:00",
    "11:00 - 12:00",
    "12:00 - 01:00",
    "01:00 - 02:00",
    "02:00 - 03:00",
    "03:00 - 04:00",
    "04:00 - 05:00"
];

// Safely display text received from the server.
function escapeHTML(value) {
    return String(value).replace(/[&<>"']/g, function (character) {
        return {
            "&": "&amp;",
            "<": "&lt;",
            ">": "&gt;",
            '"': "&quot;",
            "'": "&#39;"
        }[character];
    });
}

// Add a subject using the Flask API.
form.addEventListener("submit", async function (event) {
    event.preventDefault();

    statusMessage.textContent = "Adding subject...";

    const data = {
        subject: form.subject.value.trim(),
        teacher: form.teacher.value.trim(),
        student_group: form.student_group.value.trim(),
        classroom: form.classroom.value.trim(),
        sessions: Number(form.sessions.value)
    };

    try {
        const response = await fetch("/api/subjects", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify(data)
        });

        const result = await response.json();

        if (!response.ok) {
            throw new Error(result.error || "Could not add subject.");
        }

        statusMessage.textContent = result.message;
        form.reset();
        form.sessions.value = 3;

        await loadSubjects();
    } catch (error) {
        statusMessage.textContent = error.message;
    }
});

// Fetch all subjects from the database.
async function loadSubjects() {
    const list = document.getElementById("subjectList");

    try {
        const response = await fetch("/api/subjects");

        if (!response.ok) {
            throw new Error("Could not load subjects.");
        }

        const subjects = await response.json();

        if (subjects.length === 0) {
            list.innerHTML =
                '<tr><td colspan="6">No subjects added yet.</td></tr>';
            return;
        }

        list.innerHTML = subjects.map(function (item) {
            return `
                <tr>
                    <td>${escapeHTML(item.subject)}</td>
                    <td>${escapeHTML(item.teacher)}</td>
                    <td>${escapeHTML(item.student_group)}</td>
                    <td>${escapeHTML(item.classroom)}</td>
                    <td>${escapeHTML(item.sessions)}</td>
                    <td>
                        <button class="delete-button"
                            onclick="deleteSubject(${Number(item.id)})">
                            Delete
                        </button>
                    </td>
                </tr>
            `;
        }).join("");
    } catch (error) {
        statusMessage.textContent = error.message;
    }
}

// Delete a subject.
async function deleteSubject(id) {
    if (!confirm("Are you sure you want to delete this subject?")) {
        return;
    }

    try {
        const response = await fetch("/api/subjects/" + id, {
            method: "DELETE"
        });

        const result = await response.json();

        if (!response.ok) {
            throw new Error(result.error || "Could not delete subject.");
        }

        statusMessage.textContent = result.message;
        await loadSubjects();
        await loadTimetable();
    } catch (error) {
        statusMessage.textContent = error.message;
    }
}

// Ask Flask to generate a timetable.
async function generateSchedule() {
    timetableStatus.textContent = "Generating timetable...";

    try {
        const response = await fetch("/api/generate", {
            method: "POST"
        });

        const result = await response.json();

        if (!response.ok) {
            throw new Error(result.error || "Generation failed.");
        }

        timetableStatus.textContent =
            result.message + " Total classes: " + result.count;

        await loadTimetable();
    } catch (error) {
        timetableStatus.textContent = error.message;
    }
}

// Display the saved timetable as a weekly grid.
async function loadTimetable() {
    const body = document.getElementById("timetableBody");

    try {
        const response = await fetch("/api/timetable");

        if (!response.ok) {
            throw new Error("Could not load timetable.");
        }

        const entries = await response.json();

        const schedule = {};

        days.forEach(function (day) {
            schedule[day] = Array(8).fill(null);
        });

        entries.forEach(function (item) {
            const dayIndex = days.indexOf(item.day);

            if (dayIndex !== -1 &&
                item.period >= 0 && item.period < 8) {
                schedule[item.day][item.period] = item;
            }
        });

        body.innerHTML = days.map(function (day) {
            const cells = schedule[day].map(function (item) {
                if (!item) {
                    return "<td>—</td>";
                }

                return `
                    <td class="class-cell">
                        <strong>${escapeHTML(item.subject)}</strong>
                        <small>${escapeHTML(item.teacher)}</small>
                        <small>${escapeHTML(item.student_group)}</small>
                        <small>Room: ${escapeHTML(item.classroom)}</small>
                    </td>
                `;
            }).join("");

            return `
                <tr>
                    <th>${day}</th>
                    ${cells}
                </tr>
            `;
        }).join("");

    } catch (error) {
        timetableStatus.textContent = error.message;
    }
}

// Clear saved timetable entries, but keep subjects.
async function resetSchedule() {
    if (!confirm("Clear the generated timetable?")) {
        return;
    }

    try {
        const response = await fetch("/api/reset", {
            method: "POST"
        });

        const result = await response.json();

        if (!response.ok) {
            throw new Error(result.error || "Could not clear timetable.");
        }

        timetableStatus.textContent = result.message;
        await loadTimetable();
    } catch (error) {
        timetableStatus.textContent = error.message;
    }
}

// Load existing data when the page opens.
loadSubjects();
loadTimetable();
