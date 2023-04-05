import requests
from flask import Flask, request

app = Flask(__name__)

url_service = "http://app:5000"
creator_author = 'Createy McCreateFace'

@app.route("/", methods=["GET"])
def index():
    return "ok"

def get_prs():
    commits = requests.get("http://app:5000/commits").json()
    prs = requests.get("http://app:5000/pull-requests").json()
    user_commit_hashes = { commit["sha"] for commit in commits if commit[ "author" ] == creator_author }
    user_prs = [ pr for pr in prs if set(pr["commits"]) & user_commit_hashes ]
    return user_prs

def get_deployments():
    deployments = requests.get(url_service + '/deployments').json()
    return deployments

@app.route("/pull-requests", methods=["GET"])
def pulls():
    prs = get_prs()
    deployments = get_deployments()
    for pr in prs:
        for deployment in deployments:
            if set(pr['commits']) == set(deployment['commits']):
                pr['deployment_status'] = deployment['status']
        if 'deployment_status' not in pr:
            pr['deployment_status'] = 'undeployed'
    return prs


@app.route("/list_of_issues", methods=["GET"])
def list_of_issues():
    r = requests.get(url_service + '/issues').json()
    filtered_list = [i for i in r if i['assignee'] == creator_author]
    return filtered_list

@app.route("/available-issues", methods=["GET"])
def available_issues():
    r = requests.get(url_service + '/issues').json()
    filtered_list = [i for i in r if i['assignee'] is None]
    return filtered_list
