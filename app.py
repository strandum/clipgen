import os
import subprocess
import threading
import shutil
from flask import Flask, request, jsonify, render_template_string, send_from_directory
from pathlib import Path
import logging
logging.getLogger('werkzeug').setLevel(logging.ERROR)

app = Flask(__name__)

BASE_DIR = Path(__file__).parent
OUTPUT_DIR = BASE_DIR / "output"
STATUS_FILE = BASE_DIR / "status.json"

# ---------------- STATUS ----------------

def write_status(message="Idle", progress=0, working=False):
    STATUS_FILE.write_text(
        f'{{"message":"{message}","progress":{progress},"working":{str(working).lower()}}}',
        encoding="utf-8"
    )

def read_status():
    if not STATUS_FILE.exists():
        write_status()
    return STATUS_FILE.read_text(encoding="utf-8")

# ---------------- MAIN PAGE ----------------

INDEX_HTML = """
<!DOCTYPE html>
<html>
<head>
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>ClipGen</title>

<style>
body {
    margin:0;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto;
    background: linear-gradient(135deg, #f5f7fa, #e4edf5);
    overflow-x:hidden;
}

.blur-bg {
    position:fixed;
    width:500px;
    height:500px;
    background:radial-gradient(circle, #ffb6e6, transparent);
    filter:blur(120px);
    top:-100px;
    left:-100px;
    z-index:-1;
}

.blur-bg2 {
    position:fixed;
    width:600px;
    height:600px;
    background:radial-gradient(circle, #a0e9ff, transparent);
    filter:blur(140px);
    bottom:-200px;
    right:-200px;
    z-index:-1;
}

.container {
    max-width:600px;
    margin:60px auto;
    background:rgba(255,255,255,0.6);
    backdrop-filter: blur(20px);
    padding:30px;
    border-radius:20px;
    box-shadow:0 10px 40px rgba(0,0,0,0.1);
}

h1 {
    text-align:center;
}

label {
    display:block;
    margin-top:15px;
    font-size:14px;
}

input, select {
    width:100%;
    padding:10px;
    margin-top:5px;
    border-radius:10px;
    border:1px solid #ddd;
}

button {
    width:100%;
    padding:12px;
    margin-top:20px;
    border:none;
    border-radius:12px;
    background:#4CAF50;
    color:white;
    font-weight:bold;
    cursor:pointer;
}

button:disabled {
    background:#aaa;
    cursor:not-allowed;
}

.progress {
    margin-top:15px;
    height:8px;
    background:#eee;
    border-radius:6px;
    overflow:hidden;
}

.progress-bar {
    height:100%;
    width:0%;
    background:#4CAF50;
}

.projects {
    margin-top:40px;
}

.project-card {
    padding:15px;
    margin-bottom:10px;
    background:white;
    border-radius:12px;
    display:flex;
    justify-content:space-between;
    align-items:center;
    box-shadow:0 5px 20px rgba(0,0,0,0.05);
}

.project-card a {
    text-decoration:none;
    font-weight:bold;
    color:#333;
}

.delete-btn {
    background:#ff5c5c;
    padding:8px 12px;
    border-radius:8px;
    color:white;
    border:none;
    cursor:pointer;
}
</style>
</head>

<body>

<div class="blur-bg"></div>
<div class="blur-bg2"></div>

<div class="container">
<h1>🌸 ClipGen</h1>

<form id="clipForm">
<label>YouTube URL</label>
<input name="url" required>

<label>Antall klipp</label>
<select name="clip_count">
<option value="1">1</option>
<option value="2">2</option>
<option value="3" selected>3</option>
<option value="5">5</option>
</select>

<label>Språk</label>
<select name="language">
<option value="auto">Auto detect</option>
<option value="en">English</option>
<option value="no">Norsk</option>
</select>

<button type="submit" id="startBtn">Start</button>
</form>

<div class="progress">
<div class="progress-bar" id="progressBar"></div>
</div>

<div id="statusText">Idle</div>

<div class="projects">
<h3>Prosjekter</h3>
{% for p in projects %}
<div class="project-card">
<a href="/project/{{p}}">{{p}}</a>
<form method="POST" action="/delete/{{p}}">
<button class="delete-btn">Slett</button>
</form>
</div>
{% endfor %}
</div>

</div>

<script>
const form = document.getElementById("clipForm");
const btn = document.getElementById("startBtn");

let polling = null;

form.addEventListener("submit", async function(e){
    e.preventDefault();
    btn.disabled = true;

    const formData = new FormData(form);

    await fetch("/start", {
        method:"POST",
        body:formData
    });

    startPolling();
});

function startPolling(){
    if (polling) return;
    polling = setInterval(updateStatus, 1500);
}

function stopPolling(){
    if (polling){
        clearInterval(polling);
        polling = null;
    }
}

async function updateStatus(){
    const res = await fetch("/status");
    const data = await res.json();

    document.getElementById("statusText").innerText = data.message;
    document.getElementById("progressBar").style.width = data.progress + "%";

    if(!data.working){
        btn.disabled = false;
        stopPolling();
    }
}

// 🔥 THIS IS THE FIX
// Check status immediately when page loads
window.addEventListener("load", async function(){
    const res = await fetch("/status");
    const data = await res.json();

    document.getElementById("statusText").innerText = data.message;
    document.getElementById("progressBar").style.width = data.progress + "%";

    if(data.working){
        btn.disabled = true;
        startPolling();
    }
});
</script>

</body>
</html>
"""

# ---------------- PROJECT PAGE ----------------

PROJECT_HTML = """
<!DOCTYPE html>
<html>
<head>
<title>{{project}}</title>
<style>
body {
    margin:0;
    font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto;
    background:linear-gradient(135deg,#f5f7fa,#e4edf5);
    padding:40px;
}

h2 {
    margin-bottom:20px;
}

.back {
    display:inline-block;
    margin-bottom:20px;
    text-decoration:none;
    font-weight:bold;
}

.grid {
    display:grid;
    grid-template-columns:repeat(auto-fill,minmax(250px,1fr));
    gap:20px;
}

.card {
    background:white;
    padding:15px;
    border-radius:15px;
    box-shadow:0 5px 20px rgba(0,0,0,0.05);
}

video {
    width:100%;
    border-radius:12px;
}

.download {
    display:block;
    margin-top:10px;
    padding:8px;
    background:#4CAF50;
    color:white;
    text-align:center;
    border-radius:8px;
    text-decoration:none;
}
</style>
</head>
<body>

<a href="/" class="back">← Tilbake</a>
<h2>{{project}}</h2>

<div class="grid">
{% for f in files %}
<div class="card">
<video controls>
<source src="/video/{{project}}/{{f}}" type="video/mp4">
</video>
<a class="download" href="/video/{{project}}/{{f}}" download>Last ned</a>
</div>
{% endfor %}
</div>

</body>
</html>
"""

# ---------------- ROUTES ----------------

import sys

@app.route("/")
def index():
    projects = []
    if OUTPUT_DIR.exists():
        projects = [p.name for p in OUTPUT_DIR.iterdir() if p.is_dir()]
    return render_template_string(INDEX_HTML, projects=projects)


@app.route("/start", methods=["POST"])
def start():
    url = request.form.get("url")
    clip_count = request.form.get("clip_count", "3")
    language = request.form.get("language", "auto")

    write_status("Starter...", 5, True)

    def run():
        try:
            env = os.environ.copy()
            env["CLIP_COUNT"] = clip_count
            env["CLIP_LANGUAGE"] = language

            process = subprocess.Popen(
                [sys.executable, "-m", "clipgen.core.pipeline"],
                stdin=subprocess.PIPE,
                env=env
            )

            process.communicate(input=url.encode("utf-8"))

            write_status("Ferdig!", 100, False)

        except Exception as e:
            print("ERROR:", e)
            write_status("Feil oppstod", 0, False)

    threading.Thread(target=run).start()

    return "", 204


@app.route("/status")
def status():
    return read_status(), 200, {"Content-Type": "application/json"}


@app.route("/project/<project>")
def project(project):
    project_dir = OUTPUT_DIR / project
    if not project_dir.exists():
        return "Project not found", 404

    files = sorted([f.name for f in project_dir.glob("*.mp4")])

    return render_template_string(
        PROJECT_HTML,
        project=project,
        files=files
    )


@app.route("/video/<project>/<filename>")
def video(project, filename):
    return send_from_directory(OUTPUT_DIR / project, filename)


@app.route("/delete/<project>", methods=["POST"])
def delete_project(project):
    project_dir = OUTPUT_DIR / project

    if project_dir.exists():
        shutil.rmtree(project_dir, ignore_errors=True)

    return """
    <script>
        window.location.href = "/";
    </script>
    """

# ---------------- RUN ----------------

if __name__ == "__main__":
    write_status()
    app.run(host="0.0.0.0", port=5000)
