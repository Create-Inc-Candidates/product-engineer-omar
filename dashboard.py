from flask import Flask, request
import requests

app = Flask(__name__)

url_service = "http://app:5000"
creator_author = 'Createy McCreateFace'

@app.route("/", methods=["GET"])
def index():
    return "ok"


@app.route("/list_of_issues", methods=["GET"])
def list_of_issues():
    r = requests.get(url_service + '/issues').json()
    filtered_list = [i for i in r if i['assignee'] == creator_author]
    return filtered_list
