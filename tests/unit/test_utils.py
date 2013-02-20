import copy
import mox
import unittest

from nozzle import db
from nozzle.db.sqlalchemy import models
from nozzle.common import context
from nozzle.common import exception
from nozzle.common import utils


class ApiTestCase(unittest.TestCase):

    def setUp(self):
        super(ApiTestCase, self).setUp()
        self.mox = mox.Mox()
        self.project_id = 'a-fake-project-0'
        self.protocol = 'proto-1'
        self.instance_uuids = ['a-uuid', 'b-uuid', 'c-uuid']
        self.http_server_names = ['www.abc.com', 'www.xyz.com']
        self.load_balancer_id = '123'
        self.config_id = '123'
        self.lb_uuid = 'lb-uuid-1'
        self.dns_prefix = 'abcdefghij'
        self.lb = {
                'name': 'test-lb-1',
                'user_id': 'a-fake-user-0',
                'project_id': self.project_id,
                'uuid': self.lb_uuid,
                'protocol': self.protocol,
                'dns_prefix': self.dns_prefix,
                'instance_port': 80,
        }
        self.tmp = copy.deepcopy(self.lb)
        self.tmp['id'] = self.load_balancer_id
        self.lb_ref = models.LoadBalancer()
        self.lb_ref.update(self.tmp)
        self.config = {
                'load_balancer_id': self.load_balancer_id,
                'balancing_method': 'round_robin',
                'health_check_timeout_ms': 100,
                'health_check_interval_ms': 500,
                'health_check_target_path': '/',
                'health_check_healthy_threshold': 0,
                'health_check_unhealthy_threshold': 0,
        }
        self.tmp = copy.deepcopy(self.config)
        self.tmp['id'] = self.config_id
        self.config_ref = models.LoadBalancerConfig()
        self.config_ref.update(self.tmp)
        self.kwargs = {
                'user_id': 'a-fake-user-0',
                'tenant_id': self.project_id,
                'protocol': self.protocol,
                'load_balancer_uuid': self.lb_uuid,
        }
        self.context = get_context(tenant_id=self.project_id)

    def tearDown(self):
        self.mox.UnsetStubs()
