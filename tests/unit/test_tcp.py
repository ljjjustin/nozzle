import copy
import mox
import unittest

from nozzle import db
from nozzle.db.sqlalchemy import models
from nozzle.common import context
from nozzle.common import exception
from nozzle.common import utils
from nozzle.server import state
from nozzle.server.protocol import tcp


class TcpTestCase(unittest.TestCase):

    def setUp(self):
        super(TcpTestCase, self).setUp()
        self.mox = mox.Mox()
        self.load_balancer_id = '123'
        self.uuid = 'lb-uuid-1'
        self.name = 'test-lb-1'
        self.user_id = 'a-fake-user-0'
        self.project_id = 'a-fake-project-0'
        self.protocol = 'tcp'
        self.listen_port = 11000
        self.instance_port = 22
        self.dns_prefix = 'abcdefghij'
        self.config_id = '123'
        self.instance_uuids = ['a-uuid', 'b-uuid', 'c-uuid']
        self.lb_values = {
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
        self.tmp = copy.deepcopy(self.lb_values)
        self.tmp['id'] = self.load_balancer_id
        self.lb_ref = models.LoadBalancer()
        self.lb_ref.update(self.tmp)
        self.config_values = {
            'load_balancer_id': self.load_balancer_id,
            'balancing_method': 'round_robin',
            'health_check_timeout_ms': 100,
            'health_check_interval_ms': 500,
            'health_check_target_path': '',
            'health_check_healthy_threshold': 3,
            'health_check_unhealthy_threshold': 3,
        }
        self.tmp = copy.deepcopy(self.config_values)
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
            'config': self.config_values,
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

        self.mox.StubOutWithMock(utils, 'str_uuid')
        self.mox.StubOutWithMock(utils, 'gen_dns_prefix')
        self.mox.StubOutWithMock(utils, 'allocate_listen_port')
        self.mox.StubOutWithMock(db, 'load_balancer_get_by_name')
        self.mox.StubOutWithMock(db, 'load_balancer_create')
        self.mox.StubOutWithMock(db, 'load_balancer_config_create')
        self.mox.StubOutWithMock(db, 'load_balancer_domain_create')
        self.mox.StubOutWithMock(
            db, 'load_balancer_instance_association_create')

        db.load_balancer_get_by_name(self.ctxt,
                                     self.create_kwargs['name']).\
                                     WithSideEffects(_raise_exception).\
                                     AndReturn(None)
        utils.str_uuid().AndReturn(self.uuid)
        utils.gen_dns_prefix().AndReturn(self.dns_prefix)
        utils.allocate_listen_port().AndReturn(self.listen_port)

        db.load_balancer_create(self.ctxt, self.lb_values).\
                AndReturn(self.lb_ref)
        db.load_balancer_config_create(self.ctxt, self.config_values).\
                AndReturn(self.config_ref)
        for uuid in self.create_kwargs['instance_uuids']:
            association_values = {
                'load_balancer_id': self.load_balancer_id,
                'instance_uuid': uuid,
            }
            association_ref = models.LoadBalancerInstanceAssociation()
            association_ref.update(association_values)
            db.load_balancer_instance_association_create(
                self.ctxt, association_values).AndReturn(association_ref)
        self.mox.ReplayAll()
        r = tcp.create_load_balancer(self.ctxt, **self.create_kwargs)
        self.mox.VerifyAll()
        self.assertEqual(r, {'data': {'uuid': self.uuid}})

    def test_update_load_balancer_config(self):
        update_kwargs = copy.deepcopy(self.delete_kwargs)
        update_kwargs['config'] = self.config_values

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
        db.load_balancer_config_create(self.ctxt, self.config_values).\
                                       AndReturn(self.config_ref)
        db.load_balancer_update_state(self.ctxt, self.uuid, state.UPDATING).\
                AndReturn(None)
        self.mox.ReplayAll()
        r = tcp.update_load_balancer_config(self.ctxt, **update_kwargs)
        self.mox.VerifyAll()
        self.assertEqual(r, None)

    def test_update_load_balancer_config_with_invalid_uuid(self):
        def _raise_exception(*args):
            raise exception.LoadBalancerNotFoundByUUID(
                uuid=self.delete_kwargs['uuid'])

        update_kwargs = copy.deepcopy(self.delete_kwargs)
        update_kwargs['config'] = self.config_values

        self.mox.StubOutWithMock(db, 'load_balancer_get_by_uuid')
        db.load_balancer_get_by_uuid(self.ctxt, self.uuid).\
                                     WithSideEffects(_raise_exception).\
                                     AndReturn(None)
        self.mox.ReplayAll()
        self.assertRaises(exception.UpdateLoadBalancerFailed,
                          tcp.update_load_balancer_config,
                          self.ctxt, **update_kwargs)
        self.mox.VerifyAll()

    def test_update_load_balancer_instances(self):
        update_kwargs = copy.deepcopy(self.delete_kwargs)
        new_instance_uuids = ['a-uuid', 'd-uuid', 'e-uuid']
        update_kwargs['instance_uuids'] = new_instance_uuids

        self.mox.StubOutWithMock(db, 'load_balancer_get_by_uuid')
        self.mox.StubOutWithMock(
            db, 'load_balancer_instance_association_create')
        self.mox.StubOutWithMock(
            db, 'load_balancer_instance_association_destroy')
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

        db.load_balancer_get_by_uuid(
            self.ctxt, self.uuid).AndReturn(load_balancer_ref)

        old_instance_uuids = map(lambda x: x['instance_uuid'],
                                        load_balancer_ref.instances)
        need_deleted_instances = filter(lambda x: x not in new_instance_uuids,
                                        old_instance_uuids)
        need_created_instances = filter(lambda x: x not in old_instance_uuids,
                                        new_instance_uuids)
        for instance_uuid in need_deleted_instances:
            db.load_balancer_instance_association_destroy(
                self.ctxt, load_balancer_ref.id, instance_uuid).AndReturn(None)
        for instance_uuid in need_created_instances:
            association_values = {
                'load_balancer_id': load_balancer_ref.id,
                'instance_uuid': instance_uuid,
            }
            db.load_balancer_instance_association_create(
                self.ctxt, association_values).AndReturn(None)
        db.load_balancer_update_state(
            self.ctxt, self.uuid, state.UPDATING).AndReturn(None)
        self.mox.ReplayAll()
        r = tcp.update_load_balancer_instances(self.ctxt, **update_kwargs)
        self.mox.VerifyAll()
        self.assertEqual(r, None)
