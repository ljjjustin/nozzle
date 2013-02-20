import copy
import mox
import unittest

from nozzle import db
from nozzle.db.sqlalchemy import models
from nozzle.common import context
from nozzle.common import exception
from nozzle.common import utils
from nozzle.server import state
from nozzle.server.protocol import http


class HttpTestCase(unittest.TestCase):

    def setUp(self):
        super(HttpTestCase, self).setUp()
        self.mox = mox.Mox()
        self.load_balancer_id = '123'
        self.uuid = 'lb-uuid-1'
        self.name = 'test-lb-1'
        self.user_id = 'a-fake-user-0'
        self.project_id = 'a-fake-project-0'
        self.protocol = 'http'
        self.listen_port = 80
        self.instance_port = 80
        self.dns_prefix = 'abcdefghij'
        self.config_id = '123'
        self.instance_uuids = ['a-uuid', 'b-uuid', 'c-uuid']
        self.http_server_names = ['www.abc.com', 'www.xyz.com']
        self.lb = {
                'uuid': self.uuid,
                'name': self.name,
                'user_id': self.user_id,
                'project_id': self.project_id,
                'protocol': self.protocol,
                'state': state.CREATING,
                'free': False,
                'dns_prefix': self.dns_prefix,
                'listen_port': self.listen_port,
                'instance_port': self.instance_port,
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
        self.create_kwargs = {
                'name': self.name,
                'user_id': self.user_id,
                'tenant_id': self.project_id,
                'protocol': self.protocol,
                'instance_port': self.instance_port,
                'instance_uuids': self.instance_uuids,
                'http_server_names': self.http_server_names,
                'config': self.config,
        }
        self.delete_kwargs = {
                'user_id': self.user_id,
                'tenant_id': self.project_id,
                'protocol': self.protocol,
                'uuid': self.uuid,
        }
        self.ctxt = context.get_context(tenant_id=self.project_id)

    def tearDown(self):
        self.mox.UnsetStubs()

    def test_create_load_balancer(self):
        def _raise_exception(*args):
            raise exception.LoadBalancerNotFoundByName(
                    load_balancer_name=self.create_kwargs['name'])

        self.mox.StubOutWithMock(utils, 'get_all_domain_names')
        self.mox.StubOutWithMock(utils, 'str_uuid')
        self.mox.StubOutWithMock(utils, 'gen_dns_prefix')
        self.mox.StubOutWithMock(db, 'load_balancer_get_by_name')
        self.mox.StubOutWithMock(db, 'load_balancer_create')
        self.mox.StubOutWithMock(db, 'load_balancer_config_create')
        self.mox.StubOutWithMock(db, 'load_balancer_domain_create')
        self.mox.StubOutWithMock(db,
                'load_balancer_instance_association_create')

        db.load_balancer_get_by_name(self.ctxt,
                                     self.create_kwargs['name']).\
                                     WithSideEffects(_raise_exception).\
                                     AndReturn(None)
        utils.get_all_domain_names().AndReturn(list())
        utils.str_uuid().AndReturn(self.uuid)
        utils.gen_dns_prefix().AndReturn(self.dns_prefix)
        db.load_balancer_create(self.ctxt, self.lb).AndReturn(self.lb_ref)
        db.load_balancer_config_create(self.ctxt, self.config).\
                AndReturn(self.config_ref)
        for index, domain in enumerate(self.http_server_names):
            domain_values = {
                'load_balancer_id': self.load_balancer_id,
                'name': domain,
            }
            self.tmp = copy.deepcopy(domain_values)
            self.tmp['id'] = index + 1
            domain_ref = models.LoadBalancerDomain()
            domain_ref.update(self.tmp)
            db.load_balancer_domain_create(self.ctxt, domain_values).\
                    AndReturn(domain_ref)
        for uuid in self.create_kwargs['instance_uuids']:
            association_values = {
                'load_balancer_id': self.load_balancer_id,
                'instance_uuid': uuid,
            }
            association_ref = models.LoadBalancerInstanceAssociation()
            association_ref.update(association_values)
            db.load_balancer_instance_association_create(self.ctxt,
                    association_values).AndReturn(association_ref)
        self.mox.ReplayAll()
        r = http.create_load_balancer(self.ctxt, **self.create_kwargs)
        self.mox.VerifyAll()
        self.assertEqual(r, {'data': {'uuid': self.uuid}})

    def test_create_load_balancer_with_duplicate_name(self):
        def _raise_exception(*args):
            raise Exception()

        self.mox.StubOutWithMock(db, 'load_balancer_get_by_name')
        db.load_balancer_get_by_name(self.ctxt,
                                     self.create_kwargs['name']).\
                                     WithSideEffects(_raise_exception).\
                                     AndReturn(None)
        self.mox.ReplayAll()
        self.assertRaises(Exception, http.create_load_balancer,
                          self.ctxt, **self.create_kwargs)
        self.mox.VerifyAll()

    def test_create_load_balancer_failed_on_lb_create(self):
        def _raise_exception1(*args):
            raise exception.LoadBalancerNotFoundByName(
                    load_balancer_name=self.create_kwargs['name'])

        def _raise_exception2(*args):
            raise Exception()

        self.mox.StubOutWithMock(db, 'load_balancer_create')
        self.mox.StubOutWithMock(db, 'load_balancer_get_by_name')
        self.mox.StubOutWithMock(utils, 'get_all_domain_names')
        self.mox.StubOutWithMock(utils, 'str_uuid')
        self.mox.StubOutWithMock(utils, 'gen_dns_prefix')
        db.load_balancer_get_by_name(self.ctxt,
                                     self.create_kwargs['name']).\
                                     WithSideEffects(_raise_exception1).\
                                     AndReturn(None)
        utils.get_all_domain_names().AndReturn(list())
        utils.str_uuid().AndReturn(self.uuid)
        utils.gen_dns_prefix().AndReturn(self.dns_prefix)
        db.load_balancer_create(self.ctxt, self.lb).\
                                WithSideEffects(_raise_exception2).\
                                AndReturn(None)
        self.mox.ReplayAll()
        self.assertRaises(exception.CreateLoadBalancerFailed,
                          http.create_load_balancer,
                          self.ctxt, **self.create_kwargs)
        self.mox.VerifyAll()

    def test_create_load_balancer_with_incomplete_parameters(self):
        expect_keys = [
            'user_id', 'tenant_id', 'name',
            'instance_port', 'instance_uuids', 'config',
        ]
        for key in expect_keys:
            values = copy.deepcopy(self.create_kwargs)
            del values[key]
            self.assertRaises(exception.MissingParameter,
                              http.create_load_balancer,
                              self.ctxt, **values)

    def test_create_load_balancer_with_incomplete_configs(self):
        expect_configs = [
            'balancing_method',
            'health_check_timeout_ms',
            'health_check_interval_ms',
            'health_check_target_path',
        ]
        for config in expect_configs:
            values = copy.deepcopy(self.config)
            del values[config]
            self.create_kwargs['config'] = values
            self.assertRaises(exception.MissingParameter,
                              http.create_load_balancer,
                              self.ctxt, **self.create_kwargs)

    def test_create_load_balancer_with_invalid_instance_port(self):
        invalid_ports = [-1, 0, 66636, 100000]
        for port in invalid_ports:
            self.create_kwargs['instance_port'] = port
            self.assertRaises(exception.InvalidParameter,
                              http.create_load_balancer,
                              self.ctxt, **self.create_kwargs)

    def test_create_load_balancer_with_invalid_balancing_method(self):
        self.config['balancing_method'] = 'test'
        self.create_kwargs['config'] = self.config
        self.assertRaises(exception.InvalidParameter,
                          http.create_load_balancer,
                          self.ctxt, **self.create_kwargs)

    def test_create_load_balancer_with_invalid_health_check_timeout(self):
        invalid_values = [-1, 0, 99]
        for value in invalid_values:
            self.config['health_check_timeout_ms'] = value
            self.assertRaises(exception.InvalidParameter,
                              http.create_load_balancer,
                              self.ctxt, **self.create_kwargs)

    def test_create_load_balancer_with_invalid_health_check_interval(self):
        invalid_values = [-1, 0, 99]
        for value in invalid_values:
            self.config['health_check_timeout_ms'] = value
            self.assertRaises(exception.InvalidParameter,
                              http.create_load_balancer,
                              self.ctxt, **self.create_kwargs)

    def test_create_load_balancer_with_invalid_health_check_path(self):
        self.config['health_check_target_path'] = ''
        self.create_kwargs['config'] = self.config
        self.assertRaises(exception.InvalidParameter,
                          http.create_load_balancer,
                          self.ctxt, **self.create_kwargs)

    def test_update_load_balancer_config(self):
        update_kwargs = copy.deepcopy(self.delete_kwargs)
        update_kwargs['config'] = self.config

        self.mox.StubOutWithMock(db, 'load_balancer_get_by_uuid')
        self.mox.StubOutWithMock(db, 'load_balancer_config_create')
        self.mox.StubOutWithMock(db, 'load_balancer_config_destroy')
        self.mox.StubOutWithMock(db, 'load_balancer_update_state')

        load_balancer_ref = self.lb_ref
        load_balancer_ref.config = self.config_ref
        db.load_balancer_get_by_uuid(self.ctxt, self.uuid).\
                                     AndReturn(load_balancer_ref)
        db.load_balancer_config_destroy(self.ctxt,
                                        load_balancer_ref.config.id).\
                                        AndReturn(None)
        db.load_balancer_config_create(self.ctxt, self.config).\
                                       AndReturn(self.config_ref)
        db.load_balancer_update_state(self.ctxt, self.uuid, state.UPDATING).\
                                      AndReturn(None)
        self.mox.ReplayAll()
        r = http.update_load_balancer_config(self.ctxt, **update_kwargs)
        self.mox.VerifyAll()
        self.assertEqual(r, None)

    def test_update_load_balancer_config_with_invalid_uuid(self):
        def _raise_exception(*args):
            raise exception.LoadBalancerNotFoundByUUID(
                    uuid=self.delete_kwargs['uuid'])

        update_kwargs = copy.deepcopy(self.delete_kwargs)
        update_kwargs['config'] = self.config

        self.mox.StubOutWithMock(db, 'load_balancer_get_by_uuid')
        db.load_balancer_get_by_uuid(self.ctxt, self.uuid).\
                                     WithSideEffects(_raise_exception).\
                                     AndReturn(None)
        self.mox.ReplayAll()
        self.assertRaises(exception.UpdateLoadBalancerFailed,
                          http.update_load_balancer_config,
                          self.ctxt, **update_kwargs)
        self.mox.VerifyAll()

    def test_update_load_balancer_instances(self):
        update_kwargs = copy.deepcopy(self.delete_kwargs)
        new_instance_uuids = ['a-uuid', 'd-uuid', 'e-uuid']
        update_kwargs['instance_uuids'] = new_instance_uuids

        self.mox.StubOutWithMock(db, 'load_balancer_get_by_uuid')
        self.mox.StubOutWithMock(db,
                'load_balancer_instance_association_create')
        self.mox.StubOutWithMock(db,
                'load_balancer_instance_association_destroy')
        self.mox.StubOutWithMock(db, 'load_balancer_update_state')

        load_balancer_ref = self.lb_ref
        for uuid in self.instance_uuids:
            association_values = {
                    'load_balancer_id': load_balancer_ref.id,
                    'instance_uuid': uuid,
            }
            association_ref = models.LoadBalancerInstanceAssociation()
            association_ref.update(association_values)
            load_balancer_ref.instances.append(association_ref)

        db.load_balancer_get_by_uuid(self.ctxt, self.uuid).\
                                     AndReturn(load_balancer_ref)
        old_instance_uuids = map(lambda x: x['instance_uuid'],
                                        load_balancer_ref.instances)
        need_deleted_instances = filter(lambda x: x not in new_instance_uuids,
                                        old_instance_uuids)
        need_created_instances = filter(lambda x: x not in old_instance_uuids,
                                        new_instance_uuids)
        for instance_uuid in need_deleted_instances:
            db.load_balancer_instance_association_destroy(self.ctxt,
                                        load_balancer_ref.id,
                                        instance_uuid).\
                                        AndReturn(None)
        for instance_uuid in need_created_instances:
            association_values = {
                    'load_balancer_id': load_balancer_ref.id,
                    'instance_uuid': instance_uuid,
            }
            db.load_balancer_instance_association_create(self.ctxt,
                                        association_values).\
                                        AndReturn(None)
        db.load_balancer_update_state(self.ctxt, self.uuid, state.UPDATING).\
                AndReturn(None)
        self.mox.ReplayAll()
        r = http.update_load_balancer_instances(self.ctxt, **update_kwargs)
        self.mox.VerifyAll()
        self.assertEqual(r, None)

    def test_update_load_balancer_http_servers(self):
        kwargs = copy.deepcopy(self.delete_kwargs)
        new_http_servers = ['www.abc.com', 'www.123.com']
        kwargs['http_server_names'] = new_http_servers

        self.mox.StubOutWithMock(utils, 'get_all_domain_names')
        self.mox.StubOutWithMock(db, 'load_balancer_get_by_uuid')
        self.mox.StubOutWithMock(db, 'load_balancer_domain_create')
        self.mox.StubOutWithMock(db, 'load_balancer_domain_destroy')
        self.mox.StubOutWithMock(db, 'load_balancer_update_state')

        load_balancer_ref = self.lb_ref
        for index, domain in enumerate(self.http_server_names):
            domain_values = {
                    'id': index + 1,
                    'load_balancer_id': load_balancer_ref.id,
                    'name': domain,
            }
            domain_ref = models.LoadBalancerDomain()
            domain_ref.update(domain_values)
            load_balancer_ref.domains.append(domain_ref)

        db.load_balancer_get_by_uuid(self.ctxt, self.uuid).\
                AndReturn(load_balancer_ref)
        utils.get_all_domain_names().AndReturn(list())

        old_http_servers = map(lambda x: x['name'], load_balancer_ref.domains)
        need_deleted_domains = filter(lambda x: x not in new_http_servers,
                                      old_http_servers)
        need_created_domains = filter(lambda x: x not in old_http_servers,
                                      new_http_servers)

        for domain in load_balancer_ref.domains:
            if domain.name in need_deleted_domains:
                db.load_balancer_domain_destroy(self.ctxt, domain.id).\
                        AndReturn(None)
        for domain in need_created_domains:
            domain_values = {
                    'load_balancer_id': load_balancer_ref.id,
                    'name': domain,
            }
            db.load_balancer_domain_create(self.ctxt, domain_values).\
                    AndReturn(None)
        db.load_balancer_update_state(self.ctxt, self.uuid, state.UPDATING).\
                AndReturn(None)
        self.mox.ReplayAll()
        r = http.update_load_balancer_http_servers(self.ctxt, **kwargs)
        self.mox.VerifyAll()
        self.assertRaises(r, None)
