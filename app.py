from flask import Flask, render_template, request, session, redirect, url_for
from groq import Groq
import os
import sqlite3

app = Flask(__name__)
app.secret_key = "quizsecret"

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

# ---------------- DATABASE ----------------

def init_db():
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT UNIQUE,
        password TEXT
    )
    """)

    conn.commit()
    conn.close()

init_db()

# ---------------- QUIZ GENERATION ----------------

def generate_quiz(topic, num_questions):

    prompt = f"""
    Generate {num_questions} multiple choice questions on {topic}.

    Format strictly like this:

    Question: <question text>
    A) option
    B) option
    C) option
    D) option
    Answer: A/B/C/D
    """

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}]
    )

    quiz_text = str(response.choices[0].message.content)

    questions = []
    blocks = quiz_text.split("Question:")

    for block in blocks[1:]:
        lines = block.strip().split("\n")

        question = lines[0]

        options = {
            "A": lines[1][3:],
            "B": lines[2][3:],
            "C": lines[3][3:],
            "D": lines[4][3:]
        }

        answer = lines[5].split(":")[1].strip()

        questions.append({
            "question": question,
            "options": options,
            "answer": answer
        })

    return questions


# ---------------- HOME ----------------

@app.route("/")
def home():

    if "user" not in session:
        return render_template("index.html", login_required=True)

    return render_template("index.html", login_required=False)

# ---------------- REGISTER ----------------

@app.route("/register", methods=["POST"])
def register():

    email = request.form["email"]
    password = request.form["password"]

    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()

    try:
        cursor.execute(
            "INSERT INTO users (email,password) VALUES (?,?)",
            (email, password)
        )
        conn.commit()
    except:
        conn.close()
        return render_template(
            "index.html",
            login_required=True,
            message="User already exists. Please login."
        )

    conn.close()

    return render_template(
        "index.html",
        login_required=True,
        message="Registration successful. Please login."
    )

# ---------------- LOGIN ----------------

@app.route("/login", methods=["POST"])
def login():

    email = request.form["email"]
    password = request.form["password"]

    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()

    cursor.execute(
        "SELECT * FROM users WHERE email=? AND password=?",
        (email, password)
    )

    user = cursor.fetchone()
    conn.close()

    if user:
        session["user"] = email
        return redirect(url_for("home"))

    return render_template(
        "index.html",
        login_required=True,
        message="Invalid email or password"
    )

# ---------------- LOGOUT ----------------

@app.route("/logout")
def logout():

    session.pop("user", None)
    return redirect(url_for("home"))

# ---------------- GENERATE QUIZ ----------------

@app.route("/generate", methods=["POST"])
def generate():

    if "user" not in session:
        return redirect(url_for("home"))

    topic = request.form["topic"]
    num_questions = int(request.form["num_questions"])

    questions = generate_quiz(topic, num_questions)

    session["questions"] = questions
    session["current"] = 0
    session["score"] = 0

    return redirect(url_for("quiz"))

# ---------------- QUIZ ----------------

@app.route("/quiz", methods=["GET", "POST"])
def quiz():

    if "user" not in session:
        return redirect(url_for("home"))

    questions = session.get("questions",[])
    current = session.get("current",0)
    score = session.get("score",0)

    if request.method == "POST":

        selected = request.form.get("answer")
        correct = questions[current]["answer"]

        if selected == correct:
            score += 1

        session["score"] = score
        session["current"] = current + 1

        current += 1

    if current >= len(questions):
        return render_template(
            "result.html",
            score=score,
            total=len(questions),
            finished=True
        )

    question = questions[current]


    progress = int((current + 1) / len(questions) * 100)

    return render_template(
    "result.html",
    question=question,
    qno=current + 1,
    total=len(questions),
    progress=progress,
    correct_answer=question["answer"],
    finished=False
)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=7860)