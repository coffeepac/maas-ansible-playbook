#!/usr/bin/env python
import argparse
import re
import sys
import os

def clean_etcd(filepath):
    if filepath is None:
        print "no filepath passed to script.  do nothing"
        return

    etcd_cloud_config_fd = open(filepath, "r")
    etcd_cloud_config = etcd_cloud_config_fd.read()
    etcd_cloud_config_fd.close()

    #  rule:  remove SRV record check
    #  note:  any whitespace can be replaced with line wrap escaping, so all spaces need be replaced with non-greedy char classes
    #         that represent either white space or line wrap + whitespace
    etcd_cloud_config = re.sub("ExecStartPre=/bin/bash[\\\\ \\n]*?-xc[\\\\ \\n]*?'while.*?done'\\\\n", "", etcd_cloud_config, count=0, flags=re.S)

    #  rule: change /usr/bin/mkdir to /bin/mkdir
    etcd_cloud_config = re.sub("/usr/bin/mkdir", "/bin/mkdir", etcd_cloud_config, count=0)

    #  rule: remove 'srv' discovery flag
    etcd_cloud_config = re.sub("--discovery-srv.*?\\\\n", "", etcd_cloud_config, count=0, flags=re.S)

    etcd_cloud_config_fd = open(filepath, "w")
    etcd_cloud_config_fd.write(etcd_cloud_config)
    etcd_cloud_config_fd.close()
    




clean_etcd("/Users/pat/.kraken/charles-fresh/cloud-config/etcd.cloud-config.yaml")