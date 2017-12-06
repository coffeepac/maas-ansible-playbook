#!/usr/bin/env python
import argparse
import base64
import json
import sys
import uuid
import os
import oauth.oauth as oauth
import requests
import cloudconfigcleanup
import subprocess

# set these vars in your terminal
# export MAAS_API_KEY=<my_api_key>
# export MAAS_API_URL=http://<my_maas_server>/MAAS/api/2.0
MAAS = os.environ.get("MAAS_API_URL", None)
if not MAAS:
    sys.exit("no MAAS_API_URL environmental variable found. Set this to http<s>://<IP>/MAAS/api/2.0")
TOKEN = os.environ.get("MAAS_API_KEY", None)
if not TOKEN:
    sys.exit("no MAAS_API_KEY environmental variable found. See " \
        + "https://maas.ubuntu.com/docs/juju-quick-start.html#getting-a-key for getting a MAAS " \
        + "API KEY")

# Split the token from MaaS (Maas UI > username@domain > Account > MaaS Keys)  into its parts
def auth():
    global MAAS, TOKEN
    (consumer_key, key, secret) = TOKEN.split(':')
    # Format an OAuth header
    resource_token_string = "oauth_token_secret=%s&oauth_token=%s" % (secret, key)
    resource_token = oauth.OAuthToken.from_string(resource_token_string)
    consumer_token = oauth.OAuthConsumer(consumer_key, "")
    oauth_request = oauth.OAuthRequest.from_consumer_and_token(
        consumer_token, token=resource_token, http_url=MAAS,
        parameters={'auth_nonce': uuid.uuid4().get_hex()})
    oauth_request.sign_request(
        oauth.OAuthSignatureMethod_PLAINTEXT(), consumer_token, resource_token)
    headers = oauth_request.to_header()
    return headers

def allocate_node(tag=""):
    print "allocate node tag: %s" % (tag)

    headers = auth()
    headers['Accept'] = 'application/json'
    url = "%s/machines/?op=allocate" % (MAAS.rstrip())
    params = {"tags":('', tag)}
    response = requests.post(url, headers=headers, files=params)
    data = json.loads(response.text)
    return data

def deploy_node(system_id, cloud_config_path):
    print "deploy node id: %s and config: %s" % (system_id, cloud_config_path)
    # deploy Ubuntu
    headers = auth()
    headers['Accept'] = 'application/json'
    url = "%s/machines/%s/?op=deploy" % (MAAS.rstrip(), system_id)

    cloud_init_script = open(cloud_config_path, 'r').read()
    print cloud_init_script
    user_data = base64.b64encode(cloud_init_script)
    # NOTE: the requests API lets you pass a map of parameters which will
    # be encoded using the multipart/form-data encoding. ***If you
    # pass the obvious of {'user_data': user_data} the user_data part will
    # be encoded like:
    # Content-Disposition: form-data; name="user_data"; filename="user_data"
    # This extra filename property will cause the MAAS API to fail to parse
    # the parameter.
    # Instead, you must pass a tuple with an empty first param
    # to remove the filename parameter and appease MAAS.
    # passing: params = {'user_data': ('', user_data)}
    # will be encoded like:
    # Content-Disposition: form-data; name="user_data"
    params = {'user_data': ('', user_data), 'distro_series': ('', 'zesty')}
    response = requests.post(url, headers=headers, files=params)
    data = json.loads(response.text)
    return data


#  home dir
HOME = os.path.expanduser("~")
CWD = os.getcwd()

#  generate cloud config files
subprocess.call(["docker", "run", "-v", "%s/.kraken/:%s/.kraken/" % (HOME, HOME), "-v", "%s/:%s/" \
    % (CWD, CWD), "-v", "%s/.ssh/:%s/.ssh/" % (HOME, HOME), "-e", \
    "KRAKEN_EXTRA_VARS=distro=ubuntu", "-e", "HOME=%s" % (HOME), \
    "quay.io/samsung_cnct/kraken-lib:maas-handrolled", "/kraken/bin/up.sh", "--config", \
    "%s/maas.yaml" % (CWD), "--tags", "pre_provider"])

#  munge and deploy etcd node
ETCD_CLOUD_CONFIG = HOME + "/.kraken/maas/cloud-config/etcd.cloud-config.yaml"
cloudconfigcleanup.clean_etcd(ETCD_CLOUD_CONFIG)
ETCD_ALLOCATE = allocate_node("etcd")
ETCD_DEPLOY = deploy_node(ETCD_ALLOCATE["system_id"], ETCD_CLOUD_CONFIG)
ETCD_IP = ETCD_DEPLOY['interface_set'][0]['links'][0]['ip_address']

#  munge and deploy master node
MASTER_CLOUD_CONFIG = HOME + "/.kraken/maas/cloud-config/master.cloud-config.yaml"
cloudconfigcleanup.clean_master(MASTER_CLOUD_CONFIG, ETCD_IP)
MASTER_ALLOCATE = allocate_node("master")
MASTER_DEPLOY = deploy_node(MASTER_ALLOCATE["system_id"], MASTER_CLOUD_CONFIG)
MASTER_IP = MASTER_DEPLOY['interface_set'][0]['links'][0]['ip_address']

#  munge and deploy worker nodes
WORKER_CLOUD_CONFIG = HOME + "/.kraken/maas/cloud-config/worker.cloud-config.yaml"
cloudconfigcleanup.clean_worker(WORKER_CLOUD_CONFIG, MASTER_IP)
for i in range(0, 5):
    WORKER_ALLOCATE = allocate_node("worker")
    WORKER_DEPLOY = deploy_node(WORKER_ALLOCATE["system_id"], WORKER_CLOUD_CONFIG)

#  configure kubernetes cluster
subprocess.call(["docker", "run", "-v", "%s/.kraken/:%s/.kraken/" % (HOME, HOME), "-v", "%s/:%s/" \
    % (CWD, CWD), "-v", "%s/.ssh/:%s/.ssh/" % (HOME, HOME), "-e", \
    "KRAKEN_EXTRA_VARS=distro=ubuntu", "-e", "HOME=%s" % (HOME), \
    "quay.io/samsung_cnct/kraken-lib:maas-handrolled", "/kraken/bin/up.sh", "--config", \
    "%s/maas.yaml" % (CWD), "--tags", "post_provider", "-k", MASTER_IP])