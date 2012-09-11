#!/usr/bin/env python

import json
import sqlalchemy
import sys
import time
import uuid

from sqlalchemy.ext.sqlsoup import SqlSoup

from nozzle.client.v1_0 import client


def str_uuid():
    return str(uuid.uuid4())


def warning(msg):
    print msg
    sys.exit(0)


if __name__ == '__main__':

    db = SqlSoup('mysql://root:nova@localhost/nova')
    instances = db.instances.filter_by(deleted=False).all()
    instance_uuids = map(lambda x: x.uuid, instances)
    if len(instance_uuids) < 1:
        warning('there is no instance, exit...')
    first_instance = instance_uuids[0]
    selected_instances = [instance_uuids[i] for i in xrange(2)]

    nozzle_client = client.Client(username="demo",
                                  password="nova",
                                  tenant_name="demo",
                                  auth_url="http://localhost:5000/v2.0")
    load_balancer_config = {
        'balancing_method': 'round_robin',
        'health_check_timeout_ms': 50000,
        'health_check_interval_ms': 15000,
        'health_check_target_path': '/',
        'health_check_healthy_threshold': 5,
        'health_check_unhealthy_threshold': 2,
    }
    request_body = {
        'loadbalancer': {
            'name': 'http1',
            'protocol': 'http',
            'instance_port': 80,
            'instance_uuids': [first_instance],
            'http_server_names': ['www.xxx.com', 'www.yyy.com'],
            'config': load_balancer_config,
        }
    }
    result = nozzle_client.create_loadbalancer(body=request_body)
    id = result['loadbalancer']['uuid']
    print nozzle_client.show_loadbalancer(id)

    domains = ['www.111.com', 'www.222.com']
    request_body['loadbalancer']['instance_uuids'] = selected_instances
    request_body['loadbalancer']['http_server_names'] = domains
    nozzle_client.update_loadbalancer(id, body=request_body)
    print nozzle_client.show_loadbalancer(id)

    nozzle_client.delete_loadbalancer(id)

    request_body = {
        'loadbalancer': {
            'name': 'tcp1',
            'protocol': 'tcp',
            'instance_port': 22,
            'instance_uuids': [first_instance],
            'http_server_names': [],
            'config': load_balancer_config,
        }
    }
    result = nozzle_client.create_loadbalancer(body=request_body)
    id = result['loadbalancer']['uuid']
    print nozzle_client.show_loadbalancer(id)

    instances = [str_uuid(), str_uuid()]
    request_body['loadbalancer']['instance_uuids'] = selected_instances
    nozzle_client.update_loadbalancer(id, body=request_body)
    print nozzle_client.show_loadbalancer(id)

    nozzle_client.delete_loadbalancer(id)
