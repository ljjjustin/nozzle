#!/usr/bin/env python

import json
import os
import sys
import time
import uuid


auth_url = os.environ['OS_AUTH_URL']
username = os.environ['OS_USERNAME']
password = os.environ['OS_PASSWORD']
tenant_name = os.environ['OS_TENANT_NAME']


def get_all_instance_uuids():
    from novaclient.v1_1 import client
    nova_client = client.Client(username,
                                password,
                                tenant_name,
                                auth_url=auth_url)
    instances = nova_client.servers.list()
    return [instance.id for instance in instances]

if __name__ == '__main__':

    from nozzle.client.v2_0 import client

    instance_uuids = get_all_instance_uuids()
    if len(instance_uuids) < 1:
        print 'there is no instance, exit...'
        sys.exit(0)
    first_instance = instance_uuids[0]
    selected_instances = [instance_uuids[i] for i in xrange(2)]

    nozzle_client = client.Client(username=username,
                                  password=password,
                                  tenant_name=tenant_name,
                                  auth_url=auth_url)
    load_balancers = []

    ## create a load balancer in order to login
    request_body = {
        'loadbalancer': {
            'instance_uuid': first_instance,
            'instance_port': 22,
        }
    }

    result = nozzle_client.create_for_instance(body=request_body)
    id = result['data']['uuid']
    print nozzle_client.show_loadbalancer(id)

    load_balancer_config = {
        'balancing_method': 'round_robin',
        'health_check_timeout_ms': 50000,
        'health_check_interval_ms': 15000,
        'health_check_target_path': '/',
        'health_check_healthy_threshold': 5,
        'health_check_unhealthy_threshold': 2,
    }

    ## create a http load balancer
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
    id = result['data']['uuid']
    load_balancers.append(id)
    print nozzle_client.show_loadbalancer(id)
    print nozzle_client.list_loadbalancer_domains()

    ## update http load balancer
    domains = ['www.111.com', 'www.222.com']
    request_body['loadbalancer']['instance_uuids'] = selected_instances
    request_body['loadbalancer']['http_server_names'] = domains
    nozzle_client.update_loadbalancer(id, body=request_body)
    print nozzle_client.show_loadbalancer(id)
    print nozzle_client.list_loadbalancer_domains()

    ## create a tcp load balancer
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
    id = result['data']['uuid']
    load_balancers.append(id)
    print nozzle_client.show_loadbalancer(id)
    print nozzle_client.list_loadbalancer_domains()

    ## update tcp load balancer
    request_body['loadbalancer']['instance_uuids'] = selected_instances
    nozzle_client.update_loadbalancer(id, body=request_body)
    print nozzle_client.show_loadbalancer(id)

    ## get all tenant's load balancer
    params = {'all_tenants': 1}
    print nozzle_client.list_loadbalancers(**params)

    for lb in load_balancers:
        nozzle_client.delete_loadbalancer(lb)

    ## delete instance and update associated load balancer
    nozzle_client.delete_for_instance(first_instance)
