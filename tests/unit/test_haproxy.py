import unittest
import copy
import mock
import os

from nozzle.common import exception
from nozzle.common import validate
from nozzle.common import utils
from nozzle.worker.driver import haproxy

_msg = {
        'user_id': "user_name",
        'tenant_id': "tenant",
        'uuid': "load_balancer_id",
        'protocol': 'tcp',
        'listen_port': 32768,
        'instance_port': 544,
        'balancing_method': 'source_binding',
        'health_check_timeout_ms': 1111,
        'health_check_interval_ms': 2222,
        'health_check_healthy_threshold': 2,
        'health_check_unhealthy_threshold': 3,
        'instance_uuids': [
            u'212269a0-8f4f-11e1-acdf-001c234d5fd1',
            u'175c1a24-8f54-11e1-acdf-001c234d5fd1'],
        'instance_ips': ['10.1.2.3', '10.2.3.4']
        }


_request_template = {u'args': _msg,
                     u'cmd': u''}
fake_file = None


def fake_open(data=None):
    handle = mock.MagicMock(spec=file)
    handle.read.return_value = data
    handle.readlines.return_value = data
    handle.write.return_value = None
    handle.__enter__.return_value = handle
    return mock.Mock(return_value=handle)


def return_fake_file(new=False, data=None):
    global fake_file
    if new or fake_file is None:
        fake_file = fake_open(data)
    return fake_file


def return_create_lb_request():
    create_lb_request = copy.deepcopy(_request_template)
    create_lb_request[u'cmd'] = u'create_lb'
    return create_lb_request


def return_delete_lb_request():
    delete_lb_request = copy.deepcopy(_request_template)
    delete_lb_request[u'cmd'] = u'delete_lb'
    return delete_lb_request


def return_update_lb_request():
    update_lb_request = copy.deepcopy(_request_template)
    update_lb_request[u'cmd'] = u'update_lb'
    return update_lb_request


class TestHaproxyConfigurer(unittest.TestCase):

    def setUp(self):
        self.manager = haproxy.HaproxyConfigurer()
        self.requests = {'create_lb': return_create_lb_request(),
                         'delete_lb': return_delete_lb_request(),
                         'update_lb': return_update_lb_request()}

    @mock.patch('lockfile.FileLock', mock.MagicMock())
    def test_do_config(self):
        self.manager._validate_request = mock.MagicMock()
        self.manager._create_lb = mock.MagicMock()
        self.manager._delete_lb = mock.MagicMock()
        self.manager._update_lb = mock.MagicMock()

        for request in self.requests:
            self.manager.do_config(self.requests[request])
            self.manager._validate_request.assert_called_with(
                                            self.requests[request])

        self.manager._create_lb.assert_called_once_with(
                                    self.requests['create_lb']['args'])
        self.manager._delete_lb.assert_called_once_with(
                                    self.requests['delete_lb']['args'])
        self.manager._update_lb.assert_called_once_with(
                                    self.requests['update_lb']['args'])

    @mock.patch('lockfile.FileLock', mock.MagicMock())
    def test_do_config_with_bad_request(self):
        self.manager._validate_request = \
                mock.MagicMock(side_effect=exception.BadRequest)

        for method in self.requests:
            self.assertRaises(exception.HaproxyConfigureError,
                                self.manager.do_config, self.requests[method])

    @mock.patch('lockfile.FileLock', mock.MagicMock())
    def test_do_config_with_create_lb_failed(self):
        request = return_create_lb_request()
        self.manager._validate_request = mock.MagicMock()
        self.manager._create_lb = \
                mock.MagicMock(side_effect=exception.HaproxyCreateError)

        self.assertRaises(exception.HaproxyConfigureError,
                            self.manager.do_config, request)

    @mock.patch('lockfile.FileLock', mock.MagicMock())
    def test_do_config_with_delete_lb_failed(self):
        request = return_delete_lb_request()
        self.manager._validate_request = mock.MagicMock()
        self.manager._delete_lb = \
                mock.MagicMock(side_effect=exception.HaproxyDeleteError)

        self.assertRaises(exception.HaproxyConfigureError,
                            self.manager.do_config, request)

    @mock.patch('lockfile.FileLock', mock.MagicMock())
    def test_do_config_with_update_lb_failed(self):
        request = return_update_lb_request()
        self.manager._validate_request = mock.MagicMock()
        self.manager._update_lb = \
                mock.MagicMock(side_effect=exception.HaproxyUpdateError)

        self.assertRaises(exception.HaproxyConfigureError,
                            self.manager.do_config, request)

    def test_create_lb(self):
        args = self.requests['create_lb']['args']
        self.manager.cfg_backup_dir = '/path/backup'
        backup_path = os.path.join(self.manager.cfg_backup_dir,
                                    'haproxy.cfg_W_M_1_12')
        new_cfg_path = '/etc/haproxy/haproxy.cfg.new'

        self.manager._create_lb_haproxy_cfg = mock.MagicMock(
                        return_value=new_cfg_path)
        self.manager._test_haproxy_config = mock.MagicMock()
        self.manager._backup_original_cfg = mock.MagicMock(
                        return_value=(0, backup_path))
        self.manager._replace_original_cfg_with_new = mock.MagicMock(
                        return_value=(0, None))
        self.manager._reload_haproxy_cfg = mock.MagicMock(return_value=0)

        self.manager._create_lb(args)

        self.manager._create_lb_haproxy_cfg.assert_called_once_with(args)
        self.manager._test_haproxy_config.assert_called_once_with(new_cfg_path)
        self.manager._backup_original_cfg.assert_called_once_with()
        self.manager._replace_original_cfg_with_new.assert_called_once_with(
                                                        new_cfg_path)
        self.manager._reload_haproxy_cfg.assert_called_once_with(backup_path)

    def test_create_lb_with_create_lb_haproxy_cfg_failed(self):
        args = self.requests['create_lb']['args']
        self.manager._create_lb_haproxy_cfg = mock.MagicMock(
                        side_effect=exception.HaproxyCreateCfgError)

        self.assertRaises(exception.HaproxyCreateError,
                            self.manager._create_lb, args)

    def test_create_lb_with_test_haproxy_config_failed(self):
        args = self.requests['create_lb']['args']
        new_cfg_path = '/etc/haproxy/haproxy.cfg.new'

        self.manager._create_lb_haproxy_cfg = mock.MagicMock(
                        return_value=new_cfg_path)
        self.manager._test_haproxy_config = mock.MagicMock(
                        side_effect=exception.ProcessExecutionError)

        self.assertRaises(exception.HaproxyCreateError,
                            self.manager._create_lb, args)

    def test_create_lb_with_backup_original_cfg_failed(self):
        args = self.requests['create_lb']['args']
        self.manager._create_lb_haproxy_cfg = mock.MagicMock()
        self.manager._test_haproxy_config = mock.MagicMock()
        self.manager._backup_original_cfg = mock.MagicMock(
                        return_value=(-1, 'backup failed'))

        self.assertRaises(exception.HaproxyCreateError,
                            self.manager._create_lb, args)

    def test_create_lb_with_replace_original_cfg_with_new_failed(self):
        args = self.requests['create_lb']['args']
        self.manager._create_lb_haproxy_cfg = mock.MagicMock()
        self.manager._test_haproxy_config = mock.MagicMock()
        self.manager._replace_original_cfg_with_new = mock.MagicMock(
                        return_value=(-1, 'replace failed'))

        self.assertRaises(exception.HaproxyCreateError,
                            self.manager._create_lb, args)

    def test_create_lb_with_reload_haproxy_cfg_failed(self):
        args = self.requests['create_lb']['args']
        self.manager.cfg_backup_dir = '/path/backup'
        backup_path = os.path.join(self.manager.cfg_backup_dir,
                                    'haproxy.cfg_W_M_1_12')
        new_cfg_path = '/etc/haproxy/haproxy.cfg.new'

        self.manager._create_lb_haproxy_cfg = mock.MagicMock(
                        return_value=new_cfg_path)
        self.manager._test_haproxy_config = mock.MagicMock()
        self.manager._backup_original_cfg = mock.MagicMock(
                        return_value=(0, backup_path))
        self.manager._replace_original_cfg_with_new = mock.MagicMock(
                        return_value=(0, None))
        self.manager._reload_haproxy_cfg = mock.MagicMock(return_value=-1)

        self.assertRaises(exception.HaproxyCreateError,
                            self.manager._create_lb, args)

    def test_delete_lb(self):
        args = self.requests['delete_lb']['args']
        self.manager.cfg_backup_dir = '/path/backup'
        backup_path = os.path.join(self.manager.cfg_backup_dir,
                                    'haproxy.cfg_W_M_1_12')
        new_cfg_path = '/etc/haproxy/haproxy.cfg.new.lb_deleted'
        self.manager._create_lb_deleted_haproxy_cfg = mock.MagicMock(
                        return_value=new_cfg_path)
        self.manager._test_haproxy_config = mock.MagicMock()
        self.manager._backup_original_cfg = mock.MagicMock(
                        return_value=(0, backup_path))
        self.manager._replace_original_cfg_with_new = mock.MagicMock(
                        return_value=(0, None))
        self.manager._reload_haproxy_cfg = mock.MagicMock(return_value=0)

        self.manager._delete_lb(args)

        self.manager._create_lb_deleted_haproxy_cfg.assert_called_once_with(
                                                        args)
        self.manager._test_haproxy_config.assert_called_once_with(new_cfg_path)
        self.manager._backup_original_cfg.assert_called_once_with()
        self.manager._replace_original_cfg_with_new.assert_called_once_with(
                                                        new_cfg_path)
        self.manager._reload_haproxy_cfg.assert_called_once_with(backup_path)

    def test_delete_lb_with_test_haproxy_config_failed(self):
        args = self.requests['delete_lb']['args']
        new_cfg_path = '/etc/haproxy/haproxy.cfg.new'

        self.manager._create_lb_deleted_haproxy_cfg = mock.MagicMock(
                        return_value=new_cfg_path)
        self.manager._test_haproxy_config = mock.MagicMock(
                        side_effect=exception.ProcessExecutionError)

        self.assertRaises(exception.HaproxyDeleteError,
                            self.manager._delete_lb, args)

    def test_delete_lb_with_backup_original_cfg_failed(self):
        args = self.requests['delete_lb']['args']
        self.manager._create_lb_deleted_haproxy_cfg = mock.MagicMock()
        self.manager._test_haproxy_config = mock.MagicMock()
        self.manager._backup_original_cfg = mock.MagicMock(
                        return_value=(-1, 'backup failed'))

        self.assertRaises(exception.HaproxyDeleteError,
                          self.manager._delete_lb, args)

    def test_delete_lb_with_replace_original_cfg_with_new_failed(self):
        args = self.requests['delete_lb']['args']
        self.manager._create_lb_deleted_haproxy_cfg = mock.MagicMock()
        self.manager._test_haproxy_config = mock.MagicMock()
        self.manager._replace_original_cfg_with_new = mock.MagicMock(
                        return_value=(-1, 'replace failed'))

        self.assertRaises(exception.HaproxyDeleteError,
                          self.manager._delete_lb, args)

    def test_delete_lb_with_reload_haproxy_cfg_failed(self):
        args = self.requests['create_lb']['args']
        self.manager.cfg_backup_dir = '/path/backup'
        backup_path = os.path.join(self.manager.cfg_backup_dir,
                                    'haproxy.cfg_W_M_1_12')
        new_cfg_path = '/etc/haproxy/haproxy.cfg.new'

        self.manager._create_lb_deleted_haproxy_cfg = mock.MagicMock(
            return_value=new_cfg_path)
        self.manager._test_haproxy_config = mock.MagicMock()
        self.manager._backup_original_cfg = mock.MagicMock(
            return_value=(0, backup_path))
        self.manager._replace_original_cfg_with_new = mock.MagicMock(
            return_value=(0, None))
        self.manager._reload_haproxy_cfg = mock.MagicMock(return_value=-1)

        self.assertRaises(exception.HaproxyDeleteError,
                          self.manager._delete_lb, args)

    def test_update_lb(self):
        args = self.requests['update_lb']['args']
        self.manager.cfg_backup_dir = '/path/backup'
        backup_path = os.path.join(self.manager.cfg_backup_dir,
                                   'haproxy.cfg_W_M_1_12')
        deleted_cfg_path = '/etc/haproxy/haproxy.cfg.deleted'
        new_cfg_path = '/etc/haproxy/haproxy.cfg.new'
        self.manager._create_lb_deleted_haproxy_cfg = mock.MagicMock(
                        return_value=deleted_cfg_path)
        self.manager._create_lb_haproxy_cfg = mock.MagicMock(
                        return_value=new_cfg_path)
        self.manager._test_haproxy_config = mock.MagicMock()
        self.manager._backup_original_cfg = mock.MagicMock(
                        return_value=(0, backup_path))
        self.manager._replace_original_cfg_with_new = mock.MagicMock(
                        return_value=(0, None))
        self.manager._reload_haproxy_cfg = mock.MagicMock(return_value=0)

        self.manager._update_lb(args)

        self.manager._create_lb_deleted_haproxy_cfg.assert_called_once_with(
                                                        args)
        self.manager._create_lb_haproxy_cfg.assert_called_once_with(
                        args, base_cfg_path=deleted_cfg_path)
        self.manager._test_haproxy_config.assert_called_once_with(new_cfg_path)
        self.manager._backup_original_cfg.assert_called_once_with()
        self.manager._replace_original_cfg_with_new.assert_called_once_with(
                                                        new_cfg_path)
        self.manager._reload_haproxy_cfg.assert_called_once_with(backup_path)

    def test_update_lb_with_create_lb_deleted_haproxy_cfg_failed(self):
        args = self.requests['update_lb']['args']
        self.manager._create_lb_deleted_haproxy_cfg = mock.MagicMock(
                        side_effect=exception.HaproxyLBNotExists)

        self.assertRaises(exception.HaproxyUpdateError,
                            self.manager._update_lb, args)

    def test_update_lb_with_create_lb_haproxy_cfg_failed(self):
        args = self.requests['update_lb']['args']
        deleted_cfg_path = '/etc/haproxy/haproxy.cfg.deleted'
        self.manager._create_lb_deleted_haproxy_cfg = mock.MagicMock(
                        return_value=deleted_cfg_path)
        self.manager._create_lb_haproxy_cfg = mock.MagicMock(
                        side_effect=exception.HaproxyCreateCfgError)

        self.assertRaises(exception.HaproxyUpdateError,
                            self.manager._update_lb, args)

    def test_update_lb_with_test_haproxy_config_failed(self):
        args = self.requests['update_lb']['args']
        deleted_cfg_path = '/etc/haproxy/haproxy.cfg.deleted'
        new_cfg_path = '/etc/haproxy/haproxy.cfg.new'
        self.manager._create_lb_deleted_haproxy_cfg = mock.MagicMock(
                        return_value=deleted_cfg_path)
        self.manager._create_lb_haproxy_cfg = mock.MagicMock(
                        return_value=new_cfg_path)
        self.manager._test_haproxy_config = mock.MagicMock(
                        side_effect=exception.ProcessExecutionError)

        self.assertRaises(exception.HaproxyUpdateError,
                            self.manager._update_lb, args)

    def test_update_lb_with_backup_original_cfg_failed(self):
        args = self.requests['update_lb']['args']
        self.manager._create_lb_deleted_haproxy_cfg = mock.MagicMock()
        self.manager._create_lb_haproxy_cfg = mock.MagicMock()
        self.manager._test_haproxy_config = mock.MagicMock()
        self.manager._backup_original_cfg = mock.MagicMock(
                        return_value=(-1, 'backup failed'))

        self.assertRaises(exception.HaproxyUpdateError,
                            self.manager._update_lb, args)

    def test_update_lb_with_replace_original_cfg_with_new_failed(self):
        args = self.requests['update_lb']['args']
        self.manager.cfg_backup_dir = '/path/backup'
        backup_path = os.path.join(self.manager.cfg_backup_dir,
                                    'haproxy.cfg_W_M_1_12')
        self.manager._create_lb_deleted_haproxy_cfg = mock.MagicMock()
        self.manager._create_lb_haproxy_cfg = mock.MagicMock()
        self.manager._test_haproxy_config = mock.MagicMock()
        self.manager._backup_original_cfg = mock.MagicMock(
                        return_value=(0, backup_path))
        self.manager._replace_original_cfg_with_new = mock.MagicMock(
                        return_value=(-1, 'replace failed'))

        self.assertRaises(exception.HaproxyUpdateError,
                            self.manager._update_lb, args)

    def test_update_lb_with_reload_haproxy_cfg_failed(self):
        args = self.requests['update_lb']['args']
        self.manager.cfg_backup_dir = '/path/backup'
        backup_path = os.path.join(self.manager.cfg_backup_dir,
                                    'haproxy.cfg_W_M_1_12')
        deleted_cfg_path = '/etc/haproxy/haproxy.cfg.deleted'
        new_cfg_path = '/etc/haproxy/haproxy.cfg.new'
        self.manager._create_lb_deleted_haproxy_cfg = mock.MagicMock(
                        return_value=deleted_cfg_path)
        self.manager._create_lb_haproxy_cfg = mock.MagicMock(
                        return_value=new_cfg_path)
        self.manager._test_haproxy_config = mock.MagicMock()
        self.manager._backup_original_cfg = mock.MagicMock(
                        return_value=(0, backup_path))
        self.manager._replace_original_cfg_with_new = mock.MagicMock(
                        return_value=(0, None))
        self.manager._reload_haproxy_cfg = mock.MagicMock(return_value=-1)

        self.assertRaises(exception.HaproxyUpdateError,
                            self.manager._update_lb, args)

    def test_validate_request(self):
        args = self.requests['create_lb']['args']
        validate.check_tcp_request = mock.MagicMock()

        self.manager._validate_request(args)

        validate.check_tcp_request.assert_called_once_with(args)

    def test_get_lb_name(self):
        args = self.requests['create_lb']['args']
        lb_name = "%s" % args['uuid']
        self.assertEqual(lb_name, self.manager._get_lb_name(args))

    def test_create_haproxy_lb_server_directive(self):
        args = self.requests['create_lb']['args']
        server_fmt = '\tserver %s %s:%s check inter %sms rise %s fall %s'
        servers = [server_fmt % (args['instance_uuids'][i],
                                 args['instance_ips'][i],
                                 args['instance_port'],
                                 args['health_check_interval_ms'],
                                 args['health_check_healthy_threshold'],
                                 args['health_check_unhealthy_threshold'])
                                 for i in range(len(args['instance_uuids']))]
        expected = '\n'.join(servers)

        self.assertEqual(expected,
                self.manager._create_haproxy_lb_server_directive(args))

    @mock.patch('time.asctime', mock.MagicMock(return_value='W_M_1_12'))
    @mock.patch('os.path.join', mock.MagicMock(return_value='/path/to/cfg'))
    def test_backup_original_cfg(self):
        backup_filename = 'haproxy.cfg_W_M_1_12'
        self.manager.cfg_backup_dir = '/path/backup'
        utils.execute = mock.MagicMock()

        rc, backup_path = self.manager._backup_original_cfg()

        self.assertEqual(rc, 0)
        self.assertEqual(backup_path, '/path/to/cfg')
        cmd = "cp /etc/haproxy/haproxy.cfg /path/to/cfg"
        utils.execute.assert_called_with(cmd)

    @mock.patch('time.asctime', mock.MagicMock(return_value='W_M_1_12'))
    @mock.patch('os.path.join', mock.MagicMock(return_value='/path/to/cfg'))
    def test_backup_original_cfg_with_execute_failed(self):
        backup_filename = 'haproxy.cfg_W_M_1_12'
        self.manager.cfg_backup_dir = '/path/backup'
        utils.execute = mock.MagicMock(
                side_effect=exception.ProcessExecutionError)

        rc, backup_path = self.manager._backup_original_cfg()

        self.assertEqual(rc, -1)
        cmd = "cp /etc/haproxy/haproxy.cfg /path/to/cfg"
        utils.execute.assert_called_with(cmd)

    def test_replace_original_cfg_with_new(self):
        utils.execute = mock.MagicMock()
        new_cfg_path = '/path/to/new_cfg'
        cmd = "cp /path/to/new_cfg /etc/haproxy/haproxy.cfg"

        rc, desc = self.manager._replace_original_cfg_with_new(new_cfg_path)

        self.assertEqual(rc, 0)
        self.assertEqual(desc, None)
        utils.execute.assert_called_once_with(cmd)

    def test_replace_original_cfg_with_new_with_execute_failed(self):
        new_cfg_path = '/path/to/new_cfg'
        cmd = "cp /path/to/new_cfg /etc/haproxy/haproxy.cfg"
        utils.execute = mock.MagicMock(
                side_effect=exception.ProcessExecutionError)

        rc, desc = self.manager._replace_original_cfg_with_new(new_cfg_path)

        self.assertEqual(rc, -1)
        utils.execute.assert_called_once_with(cmd)

    def test_create_lb_haproxy_cfg(self):
        args = self.requests['create_lb']['args']
        base_cfg_path = '/etc/haproxy/haproxy.cfg'
        new_cfg_path = '/etc/haproxy/haproxy.cfg.new'
        cmd = "cp %s %s" % (base_cfg_path, new_cfg_path)
        new_cfg_content = '# haproxy proxy configuation'
        self.manager._create_haproxy_listen_cfg = \
                mock.MagicMock(return_value=new_cfg_content)
        utils.execute = mock.MagicMock()

        with mock.patch('__builtin__.open',
                        return_fake_file(new=True), create=True):
            rc = self.manager._create_lb_haproxy_cfg(args)

        self.assertEqual(rc, new_cfg_path)
        self.manager._create_haproxy_listen_cfg.assert_called_once_with(args,
                                                    base_cfg_path)
        utils.execute.assert_called_once_with(cmd)
        fake_file.assert_called_once_with(new_cfg_path, 'a')
        fake_file().write.assert_called_once_with(new_cfg_content)

    def test_create_lb_haproxy_cfg_with_create_haproxy_listen_cfg_failed(self):
        args = self.requests['create_lb']['args']
        self.manager._create_haproxy_listen_cfg = mock.MagicMock(
                        side_effect=exception.HaproxyLBExists)

        self.assertRaises(exception.HaproxyCreateCfgError,
                            self.manager._create_lb_haproxy_cfg, args)

    def test_create_lb_haproxy_cfg_with_execute_failed(self):
        args = self.requests['create_lb']['args']
        self.manager._create_haproxy_listen_cfg = mock.MagicMock()
        utils.execute = mock.MagicMock(
                        side_effect=exception.ProcessExecutionError)

        self.assertRaises(exception.HaproxyCreateCfgError,
                            self.manager._create_lb_haproxy_cfg, args)

    @mock.patch('__builtin__.open', mock.MagicMock(side_effect=IOError))
    def test_create_lb_haproxy_cfg_with_io_failed(self):
        args = self.requests['create_lb']['args']
        self.manager._create_haproxy_listen_cfg = mock.MagicMock()
        utils.execute = mock.MagicMock()

        self.assertRaises(exception.HaproxyCreateCfgError,
                            self.manager._create_lb_haproxy_cfg, args)

    def test_create_haproxy_listen_cfg(self):
        args = self.requests['create_lb']['args']
        base_cfg_path = '/etc/haproxy/haproxy.cfg'
        lb_name = "%s_%s_%s" % (args['user_id'],
                                args['tenant_id'],
                                args['uuid'])
        server_fmt = '\tserver %s %s:%s check inter %sms rise %s fall %s'
        servers = [server_fmt % (args['instance_uuids'][i],
                                 args['instance_ips'][i],
                                 args['instance_port'],
                                 args['health_check_interval_ms'],
                                 args['health_check_healthy_threshold'],
                                 args['health_check_unhealthy_threshold'])
                                 for i in range(len(args['instance_uuids']))]
        server_directives = '\n'.join(servers)
        self.manager._get_lb_name = mock.MagicMock(return_value=lb_name)
        self.manager._is_lb_in_use = mock.MagicMock(return_value=False)
        self.manager._create_haproxy_lb_server_directive = \
                        mock.MagicMock(return_value=server_directives)

        ret = self.manager._create_haproxy_listen_cfg(args)

        bind_ips = self.manager._bind_ip
        bind_directive = ','.join(map(lambda ip: "%s:%s" % (
                                    ip, args['listen_port']), bind_ips))
        haproxy_lb_fmt = \
            '\nlisten\t%s\n\tmode tcp\n\tbind %s\n\tbalance %s\n\ttimeout check %sms\n%s'
        expected = haproxy_lb_fmt % (lb_name, bind_directive, 'source',
                                    args['health_check_timeout_ms'],
                                    server_directives)
        self.assertEqual(expected, ret)
        self.manager._get_lb_name.assert_called_once_with(args)
        self.manager._is_lb_in_use.assert_called_once_with(lb_name,
                                                            base_cfg_path)
        ls_server_directive = self.manager._create_haproxy_lb_server_directive
        ls_server_directive.assert_called_once_with(args)

    def test_create_haproxy_listen_cfg_with_is_lb_in_use_failed(self):
        args = self.requests['create_lb']['args']
        self.manager._get_lb_name = mock.MagicMock()
        self.manager._is_lb_in_use = mock.MagicMock(return_value=True)

        self.assertRaises(exception.HaproxyLBExists,
                            self.manager._create_haproxy_listen_cfg, args)

    def test_create_haproxy_listen_cfg_with_illegal_port(self):
        args = self.requests['create_lb']['args']
        args['listen_port'] = '65535'
        self.manager.listen_port_min = 10000
        self.manager.listen_port_max = 61000
        self.manager._get_lb_name = mock.MagicMock()
        self.manager._is_lb_in_use = mock.MagicMock(return_value=False)

        self.assertRaises(exception.HaproxyCreateError,
                            self.manager._create_haproxy_listen_cfg, args)

    def test_create_lb_deleted_haproxy_cfg(self):
        args = self.requests['delete_lb']['args']
        lb_name = 'user_name_tenant_load_balancer_id'
        new_cfg_path = '/etc/haproxy/haproxy.cfg.new.lb_deleted'
        cfg_body = {'listen app1': {'balance source'}}
        cfg_header = ['global\n\tlog 127.0.0.1\tl0']
        config = {}
        config['body'] = cfg_body
        config['header'] = cfg_header
        new_config = '''global\n\tlog 127.0.0.1\tl0listen app1balance source'''
        self.manager._get_lb_name = mock.MagicMock(return_value=lb_name)
        self.manager._is_lb_in_use = mock.MagicMock(return_value=True)
        self.manager._format_haproxy_config = \
                        mock.MagicMock(return_value=config)
        self.manager._del_one_lb_info = mock.MagicMock()

        with mock.patch('__builtin__.open',
                        return_fake_file(new=True), create=True):
            self.manager._create_lb_deleted_haproxy_cfg(args)

        self.manager._get_lb_name.assert_called_once_with(args)
        self.manager._is_lb_in_use.assert_called_once_with(lb_name)
        self.manager._format_haproxy_config.assert_called_once_with()
        self.manager._del_one_lb_info.assert_called_once_with(config['body'],
                                                                lb_name)
        fake_file.assert_called_once_with(new_cfg_path, 'w')
        fake_file().write.assert_called_once_with(new_config)

    def test_get_haproxy_pid(self):
        with mock.patch('__builtin__.open',
                        return_fake_file(new=True, data='11111'), create=True):
            self.assertEqual(11111, self.manager._get_haproxy_pid())

    @mock.patch('__builtin__.open', mock.MagicMock(side_effect=IOError))
    def test_get_haproxy_pid_with_io_error(self):
        self.assertRaises(IOError, self.manager._get_haproxy_pid)

    @mock.patch('__builtin__.open', mock.MagicMock(side_effect=ValueError))
    def test_get_haproxy_pid_with_value_error(self):
        self.assertRaises(ValueError, self.manager._get_haproxy_pid)

    def test_test_haproxy_config(self):
        cfg_path = '/path/to/cfg'
        utils.execute = mock.MagicMock()

        self.manager._test_haproxy_config(cfg_path)

        cmd = "haproxy -c -f %s" % cfg_path
        utils.execute.assert_called_with(cmd)

    def test_test_haproxy_config_with_execute_failed(self):
        cfg_path = '/path/to/cfg'
        utils.execute = mock.MagicMock(
                            side_effect=exception.ProcessExecutionError)

        self.assertRaises(exception.ProcessExecutionError,
                            self.manager._test_haproxy_config, cfg_path)

    def test_reload_haproxy_cfg(self):
        pid = 12345
        backup_path = '/path/to/cfg'
        self.manager._get_haproxy_pid = mock.MagicMock(return_value=pid)
        utils.execute = mock.MagicMock()

        self.manager._reload_haproxy_cfg(backup_path)

        cmd = ("haproxy -f /etc/haproxy/haproxy.cfg -p "
                "/var/run/haproxy.pid -sf %s " % pid)
        utils.execute.assert_called_with(cmd)

    def test_format_haproxy_config(self):
        pass

    def test_get_one_lb_info(self):
        pass

    def test_del_one_lb_info(self):
        pass
