import copy
import mock
import random
import unittest

from nozzle.common import exception
from nozzle.common import validate


_create_http_lb_request = {
    u'cmd': u'create_lb',
    u'args': {
        u'user_id': u'demo',
        u'tenant_id': u'demo',
        u'uuid': u'myLB',
        u'protocol': u'http',
        u'instance_port': 80,
        u'listen_port': 80,
        u'health_check_timeout_ms': 5,
        u'balancing_method': u'source_binding',
        u'health_check_unhealthy_threshold': 0,
        u'health_check_healthy_threshold': 0,
        u'health_check_interval_ms': 500,
        u'health_check_fail_count': 2,
        u'health_check_target_path': u'/',
        u'instance_uuids': [u'681500b4-d08c-4208-83b3-68b2b57c1e23'],
        u'dns_names': [u'abc.lb.com.cn', u'abc.interal.lb.com.cn'],
        u'instance_ips': [u'10.0.0.1'],
        u'http_server_names': [u"g.cn"],
    },
}


_create_tcp_lb_request = {
    'cmd': 'create_lb',
    'args': {
        'user_id': "user_name",
        'tenant_id': "tenant",
        'uuid': "load_balancer_id",
        'protocol': 'tcp',
        'listen_port': 11999,
        'instance_port': 544,
        'balancing_method': 'source_binding',
        'health_check_timeout_ms': 1111,
        'health_check_interval_ms': 2222,
        'health_check_healthy_threshold': 2,
        'health_check_unhealthy_threshold': 3,
        'instance_uuids': [
            u'212269a0-8f4f-11e1-acdf-001c234d5fd1',
            u'175c1a24-8f54-11e1-acdf-001c234d5fd1'],
        'instance_ips': ['10.1.2.3', '10.2.3.4'],
        u'dns_names': [u'abc.lb.com.cn', u'abc.interal.lb.com.cn'],
    },
}


class TestValidate(unittest.TestCase):

    def setUp(self):
        super(TestValidate, self).setUp()
        self.http_lb_request = copy.deepcopy(_create_http_lb_request)
        self.tcp_lb_request = copy.deepcopy(_create_tcp_lb_request)

    def test_is_ipv4(self):
        ip = 123
        self.assertRaises(exception.InvalidType,
                          validate.is_ipv4, ip)

        ip = 'ip'
        self.assertRaises(exception.InvalidIpv4Address,
                          validate.is_ipv4, ip)

        ip = '192.168.1.300'
        self.assertRaises(exception.InvalidIpv4Address,
                          validate.is_ipv4, ip)

        ip = '192.168.1.1'
        self.assertTrue(validate.is_ipv4(ip))

    def test_is_ipv4_port_list(self):
        ip_port_list = {}
        self.assertRaises(exception.InvalidType,
                          validate.is_ipv4_port_list, ip_port_list)

        ip_port_list = ['192.168.1:80']
        self.assertRaises(exception.InvalidIpv4Address,
                          validate.is_ipv4_port_list, ip_port_list)

        ip_port_list = ['192.168.1.1:a']
        self.assertRaises(exception.InvalidPort,
                          validate.is_ipv4_port_list, ip_port_list)

        ip_port_list = ['192.168.1.1:-1']
        self.assertRaises(exception.InvalidPort,
                          validate.is_ipv4_port_list, ip_port_list)

        ip_port_list = ['192.168.1.1:800000']
        self.assertRaises(exception.InvalidPort,
                          validate.is_ipv4_port_list, ip_port_list)

        ip_port_list = ['192.168.2.3:80', '192.168.2.4:80']
        validate.is_ipv4_port_list(ip_port_list)

    def test_is_ipv4_list(self):
        ip_list = {}
        self.assertRaises(exception.BadRequest,
                          validate._is_ipv4_list, ip_list)

        ip_list = []
        self.assertRaises(exception.BadRequest,
                          validate._is_ipv4_list, ip_list)

        ip_list = ['192.168.1.1', '192.168.1']
        self.assertRaises(exception.BadRequest,
                          validate._is_ipv4_list, ip_list)

        ip_list = ['192.168.1.1', '10.1.1.1']
        validate._is_ipv4_list(ip_list)

    def test_is_valid_server_names(self):
        server_names = 123
        self.assertRaises(exception.BadRequest,
                          validate._is_valid_server_names, server_names)

        server_names = []
        self.assertRaises(exception.BadRequest,
                          validate._is_valid_server_names, server_names)

        server_names = ['g.cn', 'badname+.cn']
        self.assertRaises(exception.BadRequest,
                          validate._is_valid_server_names, server_names)

        server_names = ['g.cn', 't.cn', 'www.google.com']
        self.assertTrue(validate._is_valid_server_names(server_names))

    def test_check_create_or_update_lb_with_incomplete_msg(self):
        request = copy.deepcopy(_create_http_lb_request)
        required_keys = ['user_id', 'tenant_id', 'uuid',
                         'balancing_method', 'instance_ips', 'instance_port']

        for key in required_keys:
            value = self.http_lb_request['args'][key]
            del self.http_lb_request['args'][key]
            self.assertRaises(exception.BadRequest,
                              validate._check_create_or_update_lb,
                              self.http_lb_request)
            self.http_lb_request['args'][key] = value

    def test_check_create_or_update_lb_with_invalid_charactor(self):
        # TODO(wenjianhn) base64
        pass

    def test_check_create_or_update_lb_with_invalid_balancing_method(self):
        args = self.http_lb_request['args']
        args['balancing_method'] = 'invalid_method'

        self.assertRaises(exception.BadRequest,
                          validate._check_create_or_update_lb,
                          self.http_lb_request)

    def test_check_create_or_update_lb_with_valid_balancing_method(self):
        args = self.http_lb_request['args']
        valid_methods = ['source_binding', 'round_robin']
        for method in valid_methods:
            args['balancing_method'] = method
            validate._check_create_or_update_lb(self.http_lb_request)

    def test_check_create_or_update_lb_with_invalid_ip(self):
        args = self.http_lb_request['args']
        args['instance_ips'] = ['192.168.1', '10.0.0.1']

        self.assertRaises(exception.BadRequest,
                          validate._check_create_or_update_lb,
                          self.http_lb_request)

    def test_check_create_or_update_lb_with_invalid_port(self):
        args = self.http_lb_request['args']

        invalid_ports = ['invalid_port', -1, 65536]
        for value in invalid_ports:
            args['instance_port'] = value
            self.assertRaises(exception.BadRequest,
                              validate._check_create_or_update_lb,
                              self.http_lb_request)

    def test_check_delete_lb(self):
        # TODO(wenjianhn): )
        pass

    def test_do_basic_check_with_invalid_request_type(self):
        request = []

        self.assertRaises(exception.BadRequest,
                          validate._do_basic_check, request)

    def test_do_basic_check_without_cmd_in_request(self):
        request = {u'args': u'...'}

        self.assertRaises(exception.BadRequest,
                          validate._do_basic_check, request)

    def test_do_basic_check_without_msg_in_request(self):
        request = {u'cmd': u'...'}

        self.assertRaises(exception.BadRequest,
                          validate._do_basic_check, request)

    def test_do_basic_check_with_invalid_cmd_in_request(self):
        request = {u'args': u'...',
                   u'cmd': u'abcd_lb'}

        self.assertRaises(exception.BadRequest,
                          validate._do_basic_check, request)

    @mock.patch.object(validate, '_check_create_or_update_lb',
                       mock.MagicMock())
    @mock.patch.object(validate, '_check_delete_lb', mock.MagicMock())
    def test_do_basic_check(self):
        request = {u'args': u'...',
                   u'cmd': u'create_lb'}

        validate._do_basic_check(request)

        request['cmd'] = 'update_lb'
        validate._do_basic_check(request)

        self.assertEqual(validate._check_create_or_update_lb.call_args_list,
                         [(({u'args': u'...', u'cmd': 'update_lb'},), {}),
                          (({u'args': u'...', u'cmd': 'update_lb'},), {})])

        request['cmd'] = 'delete_lb'
        validate._do_basic_check(request)
        validate._check_delete_lb.assert_called_once_with(request)

    @mock.patch.object(validate, '_do_basic_check', mock.MagicMock())
    def test_check_http_request_without_http_server_names(self):
        del self.http_lb_request['args']['http_server_names']

        self.assertRaises(exception.BadRequest,
                          validate.check_http_request, self.http_lb_request)
        validate._do_basic_check.assert_called_once_with(self.http_lb_request)

    @mock.patch.object(validate, '_do_basic_check', mock.MagicMock())
    def test_check_http_request_without_health_check_target_path(self):
        del self.http_lb_request['args']['health_check_target_path']

        self.assertRaises(exception.BadRequest,
                          validate.check_http_request, self.http_lb_request)
        validate._do_basic_check.assert_called_once_with(self.http_lb_request)

    @mock.patch.object(validate, '_do_basic_check', mock.MagicMock())
    @mock.patch.object(validate, '_is_valid_server_names',
                       mock.MagicMock(side_effect=exception.BadRequest))
    def test_check_http_request_with_invalid_http_server_names(self):
        self.assertRaises(exception.BadRequest,
                          validate.check_http_request, self.http_lb_request)
        validate._do_basic_check.assert_called_once_with(self.http_lb_request)

    def test_check_haproxy_health_check_config_without_enough_info(self):
        # TODO(wenjianhn): )
        pass

    def test_check_haproxy_instance_uuid_without_enough_uuid(self):
        self.tcp_lb_request['args']['instance_uuids'].pop()
        self.assertRaises(exception.BadRequest,
                          validate._check_haproxy_instance_uuid,
                          self.tcp_lb_request)

    def test_check_haproxy_instance_uuid_with_invalid_uuid(self):
        self.tcp_lb_request['args']['instance_uuids'][0] = 'invalid_uuid'
        self.assertRaises(exception.BadRequest,
                          validate._check_haproxy_instance_uuid,
                          self.tcp_lb_request)

    def test_check_haproxy_instance_uuid(self):
        validate._check_haproxy_instance_uuid(self.tcp_lb_request)
