import requests
from flask import Flask, request

app = Flask(__name__)

user = "Createy McCreateFace"

@app.route("/", methods=["GET"])
def index():
    return "ok"

def get_prs():
    commits = requests.get("http://app:5000/commits").json()
    prs = requests.get("http://app:5000/pull-requests").json()
    user_commit_hashes = { commit["sha"] for commit in commits if commit[ "author" ] == user }
    user_prs = [ pr for pr in prs if set(pr["commits"]) & user_commit_hashes ]
    return user_prs

@app.route("/pull-requests", methods=["GET"])
def pulls():
    return get_prs()
