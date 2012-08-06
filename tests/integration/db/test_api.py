import datetime
import logging
import unittest
import sys

from nozzle.common import exceptions
from nozzle.common.context import get_context
from nozzle.common import utils
from nozzle import db
from nozzle.db import models
from nozzle.db.sqlalchemy.session import get_engine


class DBApiTestCase(unittest.TestCase):

    def setUp(self):
        super(DBApiTestCase, self).setUp()
        engine = get_engine()
        self.connection = engine.connect()
        self.configs = dict()
        self.user_id = 'fake-user-0'
        self.tenant_id = 'fake-project-0'
        self.load_balancer_id = utils.str_uuid()
        self.lb = {
                'id': self.load_balancer_id,
                'user_id': self.user_id,
                'tenant_id': self.tenant_id,
                'free': False,
                'name': 'test-lb-1',
                'state': 'creating',
                'protocol': 'proto-1',
                'dns_prefix': 'abcdefg',
                'listen_port': 80,
                'instance_port': 80,
        }
        self.configs['lb'] = self.lb
        self.config = {
                'load_balancer_id': self.load_balancer_id,
                'balancing_method': 'round_robin',
                'health_check_timeout_ms': 5,
                'health_check_interval_ms': 500,
                'health_check_target_path': '/',
                'health_check_healthy_threshold': 5,
                'health_check_unhealthy_threshold': 3,
        }
        self.configs['config'] = self.config
        self.domain = {
                'load_balancer_id': self.load_balancer_id,
                'name': "www.abc.com",
        }
        self.configs['domains'] = [self.domain]
        self.association = {
                'load_balancer_id': self.load_balancer_id,
                'instance_uuid': 'inst-0',
                'instance_ip': '192.168.1.1',
        }
        self.configs['associations'] = [self.association]
        self.context = get_context(self.user_id, self.tenant_id)

    def tearDown(self):
        pass

    def truncate_table(self, table):
        self.connection.execution_options(autocommit=True).\
                execute("TRUNCATE %s;" % table)

    def truncate_all_tables(self):
        self.truncate_table('load_balancer_instance_association')
        self.truncate_table('load_balancer_domains')
        self.truncate_table('load_balancer_configs')
        self.truncate_table('load_balancers')

    def compare_records(self, expect, actual, skiped=None):
        for k, v in actual.__dict__.iteritems():
            if k.startswith('_') or k in skiped:
                continue
            elif isinstance(v, datetime.datetime):
                continue
            self.assertEqual(expect[k], v)

    def test_load_balancer_create(self):
        self.truncate_all_tables()
        expect = db.load_balancer_create(self.context, self.configs)
        actual = db.load_balancer_get(self.context, expect.id)
        self.compare_records(expect, actual, skiped=['id'])

    def test_load_balancer_destroy(self):
        self.truncate_all_tables()
        db.load_balancer_create(self.context, self.configs)
        db.load_balancer_destroy(self.context, self.load_balancer_id)
        self.assertRaises(exceptions.LoadBalancerNotFound,
                          db.load_balancer_get,
                          self.context, self.load_balancer_id)

    def test_load_balancer_update_state(self):
        self.truncate_all_tables()
        db.load_balancer_create(self.context, self.configs)
        db.load_balancer_update_state(self.context,
                                      self.load_balancer_id, 'active')
        actual = db.load_balancer_get(self.context, self.load_balancer_id)
        self.assertEqual(actual.state, 'active')

    def test_load_balancer_update_config(self):
        self.truncate_all_tables()
        db.load_balancer_create(self.context, self.configs)
        self.config['balancing_method'] = 'test_method'
        self.config['health_check_target_path'] = '/index.html'
        db.load_balancer_update_config(self.context,
                                      self.load_balancer_id, self.config)
        actual = db.load_balancer_get(self.context, self.load_balancer_id)
        config_ref = models.LoadBalancerConfig()
        config_ref.update(self.config)
        self.compare_records(actual.config, config_ref, skiped=['id'])

    def test_load_balancer_update_domains(self):
        self.truncate_all_tables()
        new_domains = [
                {'name': 'www.hao.com'},
                {'name': 'www.xyz.com'},
        ]
        db.load_balancer_create(self.context, self.configs)
        actual = db.load_balancer_get(self.context, self.load_balancer_id)
        db.load_balancer_update_domains(self.context,
                                        self.load_balancer_id, new_domains)
        actual = db.load_balancer_get(self.context, self.load_balancer_id)
        actual_domains = map(lambda x: x['name'], actual.domains)
        expect_domains = map(lambda x: x['name'], new_domains)
        self.assertEqual(expect_domains.sort(), actual_domains.sort())

    def test_load_balancer_update_instances(self):
        self.truncate_all_tables()
        new_instances = [
            {
                'instance_uuid': 'inst-1',
                'instance_ip': '192.168.1.1',
            },
            {
                'instance_uuid': 'inst-2',
                'instance_ip': '192.168.1.2',
            },
        ]
        db.load_balancer_create(self.context, self.configs)
        actual = db.load_balancer_get(self.context, self.load_balancer_id)
        db.load_balancer_update_instances(self.context,
                                          self.load_balancer_id, new_instances)
        actual = db.load_balancer_get(self.context, self.load_balancer_id)
        actual_instances = map(lambda x: x['instance_uuid'], actual.instances)
        expect_instances = map(lambda x: x['instance_uuid'], new_instances)
        self.assertEqual(expect_instances.sort(), actual_instances.sort())


if __name__ == '__main__':
    unittest.main()
