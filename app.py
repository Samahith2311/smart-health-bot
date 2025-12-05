from flask import (
    Flask,
    request,
    render_template,
    jsonify,
    redirect,
    url_for,
    session,
)
from flask_cors import CORS
from database import (
    create_db,
    create_user,
    verify_user,
    get_user_by_username,
    add_reminder,
    get_reminders_for_user,
)

app = Flask(__name__, template_folder="templates", static_folder="static")
CORS(app)
app.secret_key = "super-secret-key-123"  # change in real deployment

create_db()


# ---------- "AI-style" reply logic ----------

def rule_based_reply(message: str, user_id: int | None):
    msg = message.lower()
    reminder = None

    # ---- Water reminders ----
    if "water" in msg and ("remind" in msg or "reminder" in msg or "drink" in msg):
        if user_id is not None:
            interval_min = 120  # 2 hours
            add_reminder(user_id, "water", "Drink Water 💧", interval_min)
            reminder = {
                "message": "Time to drink water! 💧",
                "interval_min": interval_min,
            }
            reply_text = (
                "Got it! I’ll remind you every 2 hours to drink water. "
                "Staying hydrated helps focus, energy and skin health. 💧"
            )
        else:
            reply_text = "Please log in to set personal water reminders. 😊"
        return reply_text, reminder

    # ---- Meal reminders ----
    if ("meal" in msg or "food" in msg) and "remind" in msg:
        if user_id is not None:
            interval_min = 240  # every 4 hours
            add_reminder(user_id, "meal", "Time for a healthy meal 🥗", interval_min)
            reminder = {
                "message": "Time for a healthy meal 🥗",
                "interval_min": interval_min,
            }
            reply_text = (
                "I’ll remind you about meals every 4 hours. "
                "Try to keep a balance of protein, carbs and healthy fats. 🥗"
            )
        else:
            reply_text = "Log in to get meal reminders just for you. 🍽️"
        return reply_text, reminder

    # ---- Sleep reminders ----
    if "sleep" in msg and "remind" in msg:
        if user_id is not None:
            interval_min = 24 * 60  # daily
            add_reminder(user_id, "sleep", "Start winding down for sleep 😴", interval_min)
            reminder = {
                "message": "Start winding down for sleep 😴",
                "interval_min": interval_min,
            }
            reply_text = (
                "Sleep reminder set once a day. Aim for 7–9 hours of quality sleep, "
                "and try to keep a consistent bedtime. 😴"
            )
        else:
            reply_text = "Please log in to enable daily sleep reminders. 🌙"
        return reply_text, reminder

    # ---- Custom reminder ----
    if "remind me" in msg and "to" in msg:
        # Example: "remind me to study at 8" -> we just treat as generic reminder
        if user_id is not None:
            # simple: every 60 minutes
            interval_min = 60
            # extract message after 'remind me to'
            try:
                custom_text = msg.split("remind me to", 1)[1].strip().capitalize()
            except Exception:
                custom_text = "Do that thing you asked for ✅"

            add_reminder(user_id, "custom", custom_text, interval_min)
            reminder = {
                "message": custom_text,
                "interval_min": interval_min,
            }
            reply_text = (
                f"Custom reminder added: \"{custom_text}\" every {interval_min} minutes. ✅"
            )
        else:
            reply_text = "Log in to create custom reminders ✅"
        return reply_text, reminder

    # ---- Health tips (AI-ish responses) ----
    if "water" in msg:
        return (
            "Healthy water tip 💧\n"
            "- Aim for 2–3 litres per day.\n"
            "- Sip regularly instead of chugging.\n"
            "- Increase intake in hot weather or when you exercise.",
            None,
        )

    if "exercise" in msg or "workout" in msg:
        return (
            "Here’s a simple 15-minute routine 🏃‍♂️\n"
            "- 5 min brisk walk or marching in place\n"
            "- 5 min bodyweight squats + wall pushups\n"
            "- 5 min stretching: hamstrings, shoulders, neck.\n"
            "Always start light and listen to your body.",
            None,
        )

    if "diet" in msg or ("food" in msg and "remind" not in msg):
        return (
            "Basic healthy diet tips 🥗\n"
            "- Fill half your plate with veggies\n"
            "- Include a source of protein (eggs, paneer, lentils, chicken)\n"
            "- Prefer whole grains (oats, brown rice, chapati)\n"
            "- Cut down on sugary drinks and fried snacks.",
            None,
        )

    if "stress" in msg or "anxious" in msg or "overwhelmed" in msg:
        return (
            "Let’s handle stress together 😌\n"
            "Try this box-breathing:\n"
            "• Inhale for 4 seconds\n"
            "• Hold for 4 seconds\n"
            "• Exhale for 6 seconds\n"
            "Repeat 5 times. Also, a short walk or journaling can help a lot.",
            None,
        )

    if "sleep" in msg:
        return (
            "For better sleep 😴\n"
            "- Avoid screens 30–60 min before bed\n"
            "- Keep your room dark and cool\n"
            "- Avoid heavy meals and caffeine late at night\n"
            "- Try a consistent sleep + wake time, even on weekends.",
            None,
        )

    if "hello" in msg or "hi" in msg or "hey" in msg:
        return (
            "Hey! 👋 I’m your Smart Health Bot.\n"
            "You can ask me about water, exercise, diet, stress, or say things like:\n"
            "• \"Set a water reminder\"\n"
            "• \"Remind me to study\"\n"
            "• \"Set a sleep reminder\"",
            None,
        )

    if "reminder" in msg or "remind" in msg:
        return (
            "You can say:\n"
            "• \"Set a water reminder\"\n"
            "• \"Set a meal reminder\"\n"
            "• \"Set a sleep reminder\"\n"
            "• \"Remind me to study at night\"",
            None,
        )

    return (
        "I'm your health assistant 😊 Ask me about water, exercise, diet, stress, sleep "
        "or ask me to set water/meal/sleep/custom reminders.",
        None,
    )


# ---------- Auth + pages ----------

@app.route("/")
def home():
    if "user_id" not in session:
        return redirect(url_for("login"))
    return render_template("index.html", username=session.get("username"))


@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect(url_for("login"))
    user_id = session["user_id"]
    reminders = get_reminders_for_user(user_id)

    # simple stats
    stats = {"water": 0, "meal": 0, "sleep": 0, "custom": 0}
    for _, r_type, _, _ in reminders:
        if r_type in stats:
            stats[r_type] += 1
        else:
            stats["custom"] += 1

    return render_template("dashboard.html", username=session.get("username"), reminders=reminders, stats=stats)


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        user_id = verify_user(username, password)
        if user_id:
            session["user_id"] = user_id
            session["username"] = username
            return redirect(url_for("home"))
        else:
            error = "Invalid username or password."
            return render_template("login.html", error=error)
    return render_template("login.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "").strip()
        confirm = request.form.get("confirm", "").strip()

        if not username or not password:
            error = "Username and password are required."
            return render_template("register.html", error=error)

        if password != confirm:
            error = "Passwords do not match."
            return render_template("register.html", error=error)

        if get_user_by_username(username):
            error = "Username already taken."
            return render_template("register.html", error=error)

        created = create_user(username, email, password)
        if created:
            return redirect(url_for("login"))
        else:
            error = "Could not create user (maybe username already exists)."
            return render_template("register.html", error=error)

    return render_template("register.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# ---------- API routes ----------

@app.post("/chat")
def chat():
    if "user_id" not in session:
        return jsonify({"reply": "Please log in to chat with me 😊"}), 401

    data = request.get_json()
    user_msg = data.get("msg", "")
    user_id = session["user_id"]

    reply_text, reminder = rule_based_reply(user_msg, user_id)
    response = {"reply": reply_text}
    if reminder is not None:
        response["reminder"] = reminder
    return jsonify(response)


@app.get("/reminders")
def list_reminders():
    if "user_id" not in session:
        return jsonify({"reminders": []}), 401

    user_id = session["user_id"]
    rows = get_reminders_for_user(user_id)
    reminders = [
        {"id": r[0], "type": r[1], "message": r[2], "interval_min": r[3]}
        for r in rows
    ]
    return jsonify({"reminders": reminders})


if __name__ == "__main__":
    app.run(debug=True)
