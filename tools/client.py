#!/usr/bin/env python

import json
import time

from nozzle.client.v1_0 import client


if __name__ == '__main__':

    nozzle_client = client.Client(username="demo",
                                  password="nova",
                                  tenant_name="demo",
                                  auth_url="http://localhost:5000/v2.0")
    import pdb; pdb.set_trace()
    print nozzle_client.list_loadbalancers()
    request_body = {
        'loadbalancer': {
            'name': 'http1',
            'protocol': 'http',
            'instance_port': 80,
            'instance_uuids': ['fc7411ad-fcad-4f63-8264-c5d3ecfd0530'],
            'http_server_names': ['www.xxx.com', 'www.yyy.com'],
            'config': {
                'balancing_method': 'round_robin',
                'health_check_timeout_ms': 50000,
                'health_check_interval_ms': 15000,
                'health_check_target_path': '/',
                'health_check_healthy_threshold': 5,
                'health_check_unhealthy_threshold': 2,
            }
        }
    }
    result = nozzle_client.create_loadbalancer(body=request_body)
    uuid = result['loadbalancer']['uuid']
    nozzle_client.show_loadbalancer(uuid)
    nozzle_client.delete_loadbalancer(uuid)
