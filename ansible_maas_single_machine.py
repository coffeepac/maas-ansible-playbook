#!/usr/bin/env python
import argparse
import base64
import json
import re
import sys
import uuid
import os
import time
import oauth.oauth as oauth
import requests
import cloudconfigcleanup


# set these vars in your terminal
# export MAAS_API_KEY=<my_api_key>
# export MAAS_API_URL=http://<my_maas_server>/MAAS/api/2.0
maas = os.environ.get("MAAS_API_URL", None)
if not maas:
    sys.exit("no MAAS_API_URL environmental variable found. Set this to http<s>://<IP>/MAAS/api/2.0")
token = os.environ.get("MAAS_API_KEY", None)
if not token:
    sys.exit("no MAAS_API_KEY environmental variable found. See https://maas.ubuntu.com/docs/juju-quick-start.html#getting-a-key for getting a MAAS API KEY")
args = None


# Split the token from MaaS (Maas UI > username@domain > Account > MaaS Keys)  into its component parts
def auth():
    global maas, token, args
    (consumer_key, key, secret) = token.split(':')
    # Format an OAuth header
    resource_token_string = "oauth_token_secret=%s&oauth_token=%s" % (secret, key)
    resource_token = oauth.OAuthToken.from_string(resource_token_string)
    consumer_token = oauth.OAuthConsumer(consumer_key, "")
    oauth_request = oauth.OAuthRequest.from_consumer_and_token(
        consumer_token, token=resource_token, http_url=maas,
        parameters={'auth_nonce': uuid.uuid4().get_hex()})
    oauth_request.sign_request(
        oauth.OAuthSignatureMethod_PLAINTEXT(), consumer_token, resource_token)
    headers = oauth_request.to_header()
    return headers

# NOTE: following is useful for debugging how your requests 
# are being formatted.
#
#def pretty_print_POST(req):
#    """
#    At this point it is completely built and ready
#    to be fired; it is "prepared".
#
#    However pay attention at the formatting used in 
#    this function because it is programmed to be pretty 
#    printed and may differ from the actual request.
#    """
#    print('{}\n{}\n{}\n\n{}'.format(
#        '-----------START-----------',
#        req.method + ' ' + req.url,
#        '\n'.join('{}: {}'.format(k, v) for k, v in req.headers.items()),
#        req.body,
#    ))

#req = requests.Request('POST', url, headers=headers, files=params)
#prepared = req.prepare()
#pretty_print_POST(prepared)

def allocate_node(tag=""):
    headers = auth()
    headers['Accept'] = 'application/json'
    url = "%s/machines/?op=allocate" % (maas.rstrip())
    params = {"tags":('',tag)}
    response = requests.post(url, headers=headers, files=params)
    data = json.loads(response.text)
    return data

def deploy_node(system_id, cloud_config_path):
    # deploy Ubuntu
    headers = auth()
    headers['Accept'] = 'application/json'
    url = "%s/machines/%s/?op=deploy" % (maas.rstrip(), system_id)

    cloud_init_script = open(cloud_config_path, 'r').read()
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


def get_info():
    headers = auth()
    headers['Accept'] = 'application/json'
    #url = "%s/maas/?op=get_config&name=default_distro_series" % (maas.rstrip())
    url = "%s/machines/" % (maas.rstrip())
    params = {'name': ('', 'default_distro_series')}
    response = requests.get(url, headers=headers, files=params)
    #print response.text
    jsoned = json.loads(response.text)
    for node in jsoned:
        if node['hostname'] == "nuc-03":
            print node
    exit()

def tag_mgmt(tag):
    #  this block creates a new tag
    #headers = auth()
    #headers['Accept'] = 'application/json'
    #url = "%s/tags/" % (maas.rstrip())
    #params = {'name': ('', tag+"_working")}
    #response = requests.post(url, headers=headers, files=params)
    #print response.text



    headers = auth()
    headers['Accept'] = 'application/json'
    #url = "%s/maas/?op=get_config&name=default_distro_series" % (maas.rstrip())
    url = "%s/tags/%s/?op=nodes" % (maas.rstrip(), tag)
    
    response = requests.get(url, headers=headers)
    for node in json.loads(response.text):
        headers = auth()
        headers['Accept'] = 'application/json'
        url = "%s/tags/%s/?op=update_nodes" % (maas.rstrip(), tag)
        params = {'remove': ('', node['system_id'])}
        response = requests.post(url, headers=headers, files=params)
        print response.text



    exit()

def add_tag(tag, system_id):
    headers = auth()
    headers['Accept'] = 'application/json'
    url = "%s/tags/%s/?op=update_nodes" % (maas.rstrip(), tag)
    params = {'add': ('', system_id)}
    response = requests.post(url, headers=headers, files=params)
    print response.text

    exit()

#add_tag("etcd", "6nhkyc")
#tag_mgmt("etcd")
#get_info()

tag = "etcd"
cloudconfigcleanup.clean_etcd("/Users/pat/.kraken/charles-fresh/cloud-config/" + tag + ".cloud-config.yaml")
data = allocate_node(tag)
data = deploy_node(data["system_id"], "/Users/pat/.kraken/charles-fresh/cloud-config/" + tag + ".cloud-config.yaml")
etcd_ip_address = data['interface_set'][0]['links'][0]['ip_address']

print "etcd endpoint is: %s" % (etcd_ip_address)
'''
tag = "master"
cloudconfigcleanup.clean_master("/Users/pat/.kraken/charles-fresh/cloud-config/" + tag + ".cloud-config.yaml", etcd_ip_address)
data = allocate_node(tag)
data = deploy_node(data["system_id"], "/Users/pat/.kraken/charles-fresh/cloud-config/" + tag + ".cloud-config.yaml")
master_ip_address = data['interface_set'][0]['links'][0]['ip_address']

print "master endpoint is: %s" % (master_ip_address)

tag = "worker"
cloudconfigcleanup.clean_worker("/Users/pat/.kraken/charles-fresh/cloud-config/" + tag + ".cloud-config.yaml", master_ip_address)
data = allocate_node(tag)
data = deploy_node(data["system_id"], "/Users/pat/.kraken/charles-fresh/cloud-config/" + tag + ".cloud-config.yaml")
worker_ip_address = data['interface_set'][0]['links'][0]['ip_address']

print "worker endpoint is: %s" % (worker_ip_address)
'''