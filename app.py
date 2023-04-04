import factory
import json
import logging
import requests
from time import sleep
from threading import Thread
from faker import Faker
from flask import Flask, request

logging.basicConfig()
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

fake = Faker()

app = Flask(__name__)


commits_list = []
pull_requests_list = []
deployments_list = []
already_deployed_prs = []
incidents_list = []

creator_author = 'Createy McCreateFace'

class CommitFactory(factory.DictFactory):
    sha = factory.Faker('sha256')

    @factory.lazy_attribute
    def author(self):
        return creator_author if fake.pyint(max_value=10) > 9 else fake.name()


class PullRequestFactory(factory.DictFactory):
    status = 'open'
    title = factory.Faker('sentence')
    commits = []


class DeploymentFactory(factory.DictFactory):
    id = factory.Faker('uuid4')
    commits = []
    status = 'queued'


def generate_commits():
    return CommitFactory.build_batch(fake.pyint(max_value=10))

def generate_pull_requests(all_pull_requests, all_commits):
    commits_in_prs = [commit for pull_request in all_pull_requests for commit in pull_request['commits']]
    commits_without_prs = [commit['sha'] for commit in all_commits if commit['sha'] not in commits_in_prs]
    prs = []
    for _ in range(fake.pyint(max_value=4)):
        commit_count = fake.pyint(min_value=1, max_value=3)
        if len(commits_without_prs) < commit_count:
            break

        commits_to_add_pr = []
        for i in range(commit_count):
            commits_to_add_pr.append(commits_without_prs.pop())
        prs.append(PullRequestFactory.build(commits=commits_to_add_pr, status='open'))
    return prs

def close_pull_requests(all_pull_requests):
    open_prs = [pr for pr in all_pull_requests if pr['status'] == 'open']
    for _ in range(fake.pyint(max_value=len(open_prs))):
        pr_to_close = fake.random_element(open_prs)
        pr_to_close['status'] = 'merged'
        logger.info('PR merged', pr_to_close)


def generate_deployment(all_deployments, all_pull_requests, all_already_deployed_prs):
    commits_in_existing_deployments = [commit for deployment in all_deployments for commit in deployment['commits']]
    merged_prs_not_in_deployments = [pr for pr in all_pull_requests if pr not in all_already_deployed_prs and pr['status'] == 'merged']
    if len(merged_prs_not_in_deployments) < 2:
        return

    prs_to_merge = fake.random_elements(merged_prs_not_in_deployments, length=fake.pyint(min_value=1, max_value=2))

    commits = [commit for pr in prs_to_merge for commit in pr['commits']]
    all_already_deployed_prs.extend(prs_to_merge)
    return DeploymentFactory.build(commits=commits)


def complete_deployments(all_deployments):
    queued_deployments = [deployment for deployment in all_deployments if deployment['status'] == 'queued']
    if not queued_deployments:
        return
    deployment_to_complete = fake.random_element(queued_deployments)
    deployment_to_complete['status'] = 'active' if fake.pyint(max_value=10) > 1 else 'failed'
    if deployment_to_complete['status'] == 'failed':
        logger.info('Deployment failed')
    else:
        logger.info('Deployment succeeded %s', deployment_to_complete['id'])
        # This really should be only one...
        active_deployments = [deployment for deployment in all_deployments if deployment['status'] == 'active' and deployment['id'] != deployment_to_complete['id']]
        for deployment in active_deployments:
            deployment['status'] = 'stale'
    try:
        requests.post('http://host.docker.internal:8000/webhooks', json={
            'deployment': json.dumps(deployment_to_complete),
            'stacktrace': fake.paragraph()
        })
    except requests.exceptions.RequestException:
        logger.exception('Failed to send notification')
    

def run_loop(deployments_list, pull_requests_list, commits_list, already_deployed_prs, incidents_list):
    def do_inner_loop():
        new_commits = generate_commits()
        commits_list.extend(new_commits)
        new_prs = generate_pull_requests(pull_requests_list, commits_list)
        pull_requests_list.extend(new_prs)
        close_pull_requests(pull_requests_list)
        new_deployment = generate_deployment(deployments_list, pull_requests_list, already_deployed_prs)
        if new_deployment:
            deployments_list.append(new_deployment)

    while True:
        do_inner_loop()
        sleep(5)
        do_inner_loop()
        if not incidents_list:
            complete_deployments(deployments_list)
        sleep(5)


thread = Thread(target=run_loop, args=(deployments_list, pull_requests_list, commits_list, already_deployed_prs, incidents_list,))
thread.start()


@app.route("/commits", methods=["GET"])
def commits():
    return commits_list

@app.route("/pull-requests", methods=["GET"])
def pull_requests():
    return pull_requests_list

@app.route("/deployments", methods=["GET"])
def deployments():
    return deployments_list

@app.route("/incidents", methods=["POST"])
def incidents():
    data = request.get_json()
    deployment_id = data['deployment_id']
    message = data['message']
    new_incident = {
        'id': fake.uuid4(),
        'deployment_id': deployment_id,
        'message': message,
    }
    incidents_list.append(new_incident)
    logger.info('Incidents: %s', incidents_list)
    return new_incident

@app.route("/resolutions", methods=["POST"])
def resolutions():
    data = request.get_json()
    existing_incident = next((incident for incident in incidents_list if incident['id'] == data['incident_id']), None)
    incidents_list.remove(existing_incident)
    return {}

