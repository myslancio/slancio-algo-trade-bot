import requests
import json
import time

token = "b01f6db0-47d8-4fea-ab5a-71dc0df40fd5"
headers = {
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/json"
}
projectId = "a4e25d60-0e42-47f5-b478-aa67779798f7"
envId = "da843dcb-5cb5-41c7-80f2-e81cdcc93c49"
repo = "myslancio/slancio-algo-trade-bot"
botToken = "8524370554:AAEFvJAi4lrZsoSXiyVOdp_d03Khb7N-9Lw"

# 1. Create New Service
q_create = """
mutation serviceCreate($input: ServiceCreateInput!) {
  serviceCreate(input: $input) { id }
}
"""
vars_create = {"input": {"projectId": projectId, "name": "slancio-elite-terminal", "source": {"repo": repo}}}
r = requests.post("https://backboard.railway.app/graphql/v2", headers=headers, json={"query": q_create, "variables": vars_create})
newSid = r.json()['data']['serviceCreate']['id']
print(f"Service Created: {newSid}")

# 2. Set Domain
q_domain = """
mutation serviceDomainCreate($input: ServiceDomainCreateInput!) {
  serviceDomainCreate(input: $input) { domain }
}
"""
vars_domain = {"input": {"serviceId": newSid, "environmentId": envId}}
r = requests.post("https://backboard.railway.app/graphql/v2", headers=headers, json={"query": q_domain, "variables": vars_domain})
newDomain = r.json()['data']['serviceDomainCreate']['domain']
print(f"Domain Created: {newDomain}")

# 3. Set Variables
q_var = """
mutation variableUpsert($input: VariableUpsertInput!) {
  variableUpsert(input: $input)
}
"""
env_vars = {
    "TELEGRAM_BOT_TOKEN": botToken,
    "DJANGO_ALLOW_ASYNC_UNSAFE": "true",
    "PYTHONUNBUFFERED": "1",
    "ADMIN_TELEGRAM_IDS": "6616646849"
}

for k, v in env_vars.items():
    v_vars = {"input": {"projectId": projectId, "serviceId": newSid, "environmentId": envId, "name": k, "value": v}}
    requests.post("https://backboard.railway.app/graphql/v2", headers=headers, json={"query": q_var, "variables": v_vars})
print("Variables Set.")

# 4. Trigger Deploy
q_deploy = """
mutation serviceInstanceDeploy($serviceId: String!, $environmentId: String!) {
  serviceInstanceDeploy(serviceId: $serviceId, environmentId: $environmentId)
}
"""
vars_deploy = {"serviceId": newSid, "environmentId": envId}
r = requests.post("https://backboard.railway.app/graphql/v2", headers=headers, json={"query": q_deploy, "variables": vars_deploy})
print(f"Build Triggered: {r.json()['data']['serviceInstanceDeploy']}")
