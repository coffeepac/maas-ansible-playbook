#!/usr/bin/env python
import argparse
import re
import sys
import os

def clean_start(filepath):
    cloud_config_fd = open(filepath, "r")
    cloud_config = cloud_config_fd.read()
    cloud_config_fd.close()

    return cloud_config

def clean_end(filepath, cloud_config):
    cloud_config_fd = open(filepath, "w")
    cloud_config_fd.write(cloud_config)
    cloud_config_fd.close()
 

def clean_etcd(filepath):
    if filepath is None:
        print "no filepath passed to script.  do nothing"
        return

    cloud_config = clean_start(filepath)

    #  rule:  remove SRV record check
    #  note:  any whitespace can be replaced with line wrap escaping, so all spaces need be replaced with non-greedy char classes
    #         that represent either white space or line wrap + whitespace
    cloud_config = re.sub("ExecStartPre=/bin/bash[\\\\ \\n]*?-xc[\\\\ \\n]*?'while.*?done'\\\\n", "", cloud_config, count=0, flags=re.S)

    #  rule: change /usr/bin/mkdir to /bin/mkdir
    cloud_config = re.sub("/usr/bin/mkdir", "/bin/mkdir", cloud_config, count=0)

    #  rule: remove 'srv' discovery flag
    cloud_config = re.sub("--discovery-srv.*?\\\\n", "", cloud_config, count=0, flags=re.S)

    clean_end(filepath, cloud_config)
    
def clean_master(filepath, ipaddress):
    if filepath is None:
        print "no filepath passed to script.  do nothing"
        return

    if ipaddress is None:
        print "ipaddress of etcd not provided.  this is not going to work"
        return

    cloud_config = clean_start(filepath)

    #  rule: change dns entry for etcd cluster to passed-in ip address
    cloud_config = re.sub("etcd[\w\.\-]*internal", ipaddress, cloud_config)

    #  rule:  change occurances of /usr/bin/[mkdir|bash|systemctl] to /bin/[mkdir|bash|systemctl]
    cloud_config = re.sub("/usr/bin/([mkdir|bash|systemctl])", "/bin/\g<1>", cloud_config)

    #  rule:  remove '- --cloud-provider=maas\n' from manifests
    cloud_config = re.sub("\\\\n[\\\\ \\n]*?-[\\\\ \\n]*?--cloud-provider=maas[ ]*?\\\\n", "\\\\n", cloud_config, flags=re.S)

    #  rule:  remove '--cloud-provider=maas' from kubelet unit file
    cloud_config = re.sub("\\\\\\n[\\\\ \n]*?--cloud-provider=maas[\\\\ \n]*?\\\\\\n", "\\\\\\n", cloud_config, flags=re.S|re.DEBUG)

    clean_end(filepath, cloud_config)




clean_etcd("/Users/pat/.kraken/charles-fresh/cloud-config/etcd.cloud-config.yaml")
clean_master("/Users/pat/.kraken/charles-fresh/cloud-config/master.cloud-config.yaml", "10.0.0.0")