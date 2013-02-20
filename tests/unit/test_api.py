import copy
import mox
import unittest
import uuid

from nozzle import db
from nozzle.db.sqlalchemy import models
from nozzle.common import context
from nozzle.common import exception
from nozzle.common import utils
from nozzle.server import api
from nozzle.server import protocol
from nozzle.server import state


class FakeModule(object):

    def __init__(self, uuid=None):
        self.uuid = uuid

    def create_load_balancer(self, context, **kwargs):
        return {'data': {'uuid': self.uuid}}

    def delete_load_balancer(self, context, **kwargs):
        return None

    def update_load_balancer_config(self, context, **kwargs):
        return None

    def update_load_balancer_instances(self, context, **kwargs):
        return None

    def update_load_balancer_http_servers(self, context, **kwargs):
        return None


class ApiTestCase(unittest.TestCase):

    def setUp(self):
        super(ApiTestCase, self).setUp()
        ##NOTE DISABLE Rabbitmq notification on test
        api.FLAGS.notification_enabled = False
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
            'uuid': self.lb_uuid,
            'all_tenants': True,
        }
        self.all_domains = []
        for name in self.http_server_names:
            self.all_domains.append(models.LoadBalancerDomain(name=name))
        self.context = context.get_context(tenant_id=self.project_id)

    def tearDown(self):
        self.mox.UnsetStubs()

    def test_create_load_balancer(self):
        fake_module = FakeModule(self.lb_uuid)
        self.mox.StubOutWithMock(protocol, 'get_protocol_module')
        self.mox.StubOutWithMock(db, 'load_balancer_get_by_uuid')
        self.lb_ref.config = self.config_ref
        protocol.get_protocol_module(self.protocol).AndReturn(fake_module)
        db.load_balancer_get_by_uuid(
            self.context, self.lb_uuid).AndReturn(self.lb_ref)
        self.mox.ReplayAll()
        r = api.create_load_balancer(self.context, **self.kwargs)
        self.mox.VerifyAll()
        self.assertEqual(r['data']['uuid'], self.lb_uuid)

    def test_delete_load_balancer(self):
        self.mox.StubOutWithMock(db, 'load_balancer_get_by_uuid')
        self.mox.StubOutWithMock(db, 'load_balancer_update_state')
        db.load_balancer_get_by_uuid(
            self.context, self.lb_uuid).AndReturn(self.lb_ref)
        db.load_balancer_update_state(
            self.context, self.lb_uuid, state.DELETING)
        self.mox.ReplayAll()
        r = api.delete_load_balancer(self.context, **self.kwargs)
        self.mox.VerifyAll()
        self.assertEqual(r, None)

    def test_update_load_balancer_config(self):
        fake_module = FakeModule()
        self.mox.StubOutWithMock(protocol, 'get_protocol_module')
        protocol.get_protocol_module(self.protocol).AndReturn(fake_module)
        self.mox.ReplayAll()
        r = api.update_load_balancer_config(self.context, **self.kwargs)
        self.mox.VerifyAll()
        self.assertEqual(r, None)

    def test_update_load_balancer_instances(self):
        fake_module = FakeModule()
        self.mox.StubOutWithMock(protocol, 'get_protocol_module')
        protocol.get_protocol_module(self.protocol).AndReturn(fake_module)
        self.mox.ReplayAll()
        r = api.update_load_balancer_instances(self.context, **self.kwargs)
        self.mox.VerifyAll()
        self.assertEqual(r, None)

    def test_update_load_balancer_http_servers(self):
        fake_module = FakeModule()
        self.mox.StubOutWithMock(protocol, 'get_protocol_module')
        protocol.get_protocol_module(self.protocol).AndReturn(fake_module)
        self.mox.ReplayAll()
        r = api.update_load_balancer_http_servers(self.context, **self.kwargs)
        self.mox.VerifyAll()
        self.assertEqual(r, None)

    def test_get_load_balancer(self):
        self.mox.StubOutWithMock(db, 'load_balancer_get_by_uuid')

        load_balancer_ref = copy.deepcopy(self.lb_ref)
        load_balancer_ref.config = self.config_ref
        expect = dict()
        expect['created_at'] = None
        expect['updated_at'] = None
        expect['user_id'] = load_balancer_ref.user_id
        expect['project_id'] = load_balancer_ref.project_id
        expect['free'] = load_balancer_ref.free
        expect['uuid'] = load_balancer_ref.uuid
        expect['name'] = load_balancer_ref.name
        expect['state'] = load_balancer_ref.state
        expect['protocol'] = load_balancer_ref.protocol
        expect['listen_port'] = load_balancer_ref.listen_port
        expect['instance_port'] = load_balancer_ref.instance_port
        expect_configs = copy.deepcopy(self.config)
        del expect_configs['load_balancer_id']
        expect['config'] = expect_configs
        expect['dns_names'] = []
        expect['instance_uuids'] = []
        expect['http_server_names'] = []
        for index, domain in enumerate(self.http_server_names):
            domain_values = {
                'id': index + 1,
                'load_balancer_id': load_balancer_ref.id,
                'name': domain,
            }
            expect['http_server_names'].append(domain)
            domain_ref = models.LoadBalancerDomain()
            domain_ref.update(domain_values)
            load_balancer_ref.domains.append(domain_ref)
        for uuid in self.instance_uuids:
            association_values = {
                'load_balancer_id': load_balancer_ref.id,
                'instance_uuid': uuid,
            }
            expect['instance_uuids'].append(uuid)
            association_ref = models.LoadBalancerInstanceAssociation()
            association_ref.update(association_values)
            load_balancer_ref.instances.append(association_ref)
        db.load_balancer_get_by_uuid(
            self.context, self.lb_uuid).AndReturn(load_balancer_ref)
        self.mox.ReplayAll()
        r = api.get_load_balancer(self.context, **self.kwargs)
        self.mox.VerifyAll()
        self.assertEqual(r, {'data': expect})

    def test_get_all_load_balancers(self):
        admin_context = self.context.elevated(read_deleted='no')
        self.mox.StubOutWithMock(db, 'load_balancer_get_all')
        self.mox.StubOutWithMock(self.context, 'elevated')

        load_balancer_ref = copy.deepcopy(self.lb_ref)
        load_balancer_ref.config = self.config_ref
        expect = dict()
        expect['created_at'] = None
        expect['updated_at'] = None
        expect['user_id'] = load_balancer_ref.user_id
        expect['project_id'] = load_balancer_ref.project_id
        expect['free'] = load_balancer_ref.free
        expect['uuid'] = load_balancer_ref.uuid
        expect['name'] = load_balancer_ref.name
        expect['state'] = load_balancer_ref.state
        expect['protocol'] = load_balancer_ref.protocol
        expect['listen_port'] = load_balancer_ref.listen_port
        expect['instance_port'] = load_balancer_ref.instance_port
        expect_configs = copy.deepcopy(self.config)
        del expect_configs['load_balancer_id']
        expect['config'] = expect_configs
        expect['dns_names'] = []
        expect['instance_uuids'] = []
        expect['http_server_names'] = []
        for index, domain in enumerate(self.http_server_names):
            domain_values = {
                'id': index + 1,
                'load_balancer_id': load_balancer_ref.id,
                'name': domain,
            }
            expect['http_server_names'].append(domain)
            domain_ref = models.LoadBalancerDomain()
            domain_ref.update(domain_values)
            load_balancer_ref.domains.append(domain_ref)
        for uuid in self.instance_uuids:
            association_values = {
                'load_balancer_id': load_balancer_ref.id,
                'instance_uuid': uuid,
            }
            expect['instance_uuids'].append(uuid)
            association_ref = models.LoadBalancerInstanceAssociation()
            association_ref.update(association_values)
            load_balancer_ref.instances.append(association_ref)
        filters = dict()
        if self.context.is_admin and kwargs['all_tenants']:
            pass
        else:
            filters['project_id'] = self.project_id
            self.context.elevated(read_deleted='no').AndReturn(admin_context)
        db.load_balancer_get_all(
            admin_context, filters=filters).AndReturn([load_balancer_ref])
        self.mox.ReplayAll()
        r = api.get_all_load_balancers(self.context, **self.kwargs)
        self.mox.VerifyAll()
        self.assertEqual(r, {'data': [expect]})

    def test_get_all_http_servers(self):
        kwargs = {
            'user_id': 'a-fake-user-0',
            'tenant_id': self.project_id,
        }
        admin_context = self.context.elevated(read_deleted='no')
        self.mox.StubOutWithMock(db, 'load_balancer_domain_get_all')
        self.mox.StubOutWithMock(self.context, 'elevated')
        self.context.elevated(read_deleted='no').AndReturn(admin_context)
        db.load_balancer_domain_get_all(
            admin_context).AndReturn(self.all_domains)
        self.mox.ReplayAll()
        r = api.get_all_http_servers(self.context, **kwargs)
        self.mox.VerifyAll()
        self.assertEqual(r, {'data': self.http_server_names})
