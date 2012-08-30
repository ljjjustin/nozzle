import re
import socket
import uuid

import utils
import exception


def _is_uuid_like(val):
    """For our purposes, a UUID is a string in canonical form:

        aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa
    """
    try:
        uuid.UUID(val)
        return True
    except (TypeError, ValueError, AttributeError):
        return False


def is_ipv4(value):
    if not isinstance(value, basestring):
        raise exception.InvalidType(valid_type='basestring',
                                     invalid_type=type(value))

    if len(value.split('.')) != 4:
        raise exception.InvalidIpv4Address(address=value)
    try:
        socket.inet_aton(value)
    except socket.error:
        raise exception.InvalidIpv4Address(address=value)
    return True


def is_ipv4_port_list(ip_port_list):
    if not isinstance(ip_port_list, list):
        raise exception.InvalidType(valid_type='list',
                                     invalid_type=type(ip_port_list))
    for ip_port in ip_port_list:
        ip, port = tuple(ip_port.split(":"))

        is_ipv4(ip)

        if not port.isdigit() or (int(port) < 1 or int(port) > 65535):
            raise exception.InvalidPort(port=port,
                                         msg="Valid port should"
                                         " be between 1-65535")

    return True


def _is_ipv4_list(value):
    if isinstance(value, list):
        if len(value) > 0:
            for ip in value:
                try:
                    is_ipv4(ip)
                except exception.InvalidIpv4Address as e:
                    raise exception.BadRequest(explanation=str(e))
        else:
            msg = "Empty ipv4_list"
            raise exception.BadRequest(explanation=msg)
    else:
        msg = "Valid ipv4_list should be a list: %s" % value
        raise exception.BadRequest(explanation=msg)

    return True


def _is_valid_server_names(server_names):
    if not isinstance(server_names, list):
        msg = "Valid server_names should be a list: %s" % server_names
        raise exception.BadRequest(explanation=msg)

    if len(server_names) == 0:
        # TODO(wenjianhn)
        # http://wiki.nginx.org/NginxHttpCoreModule#server_names_hash_max_size
        msg = "No server_name in request"
        raise exception.BadRequest(explanation=msg)

    for server_name in server_names:
        if re.search(r"[^a-zA-Z0-9\.\-]", server_name):
            msg = "Invalid server_name: %s" % server_name
            raise exception.BadRequest(explanation=msg)

    return True


def _check_create_or_update_lb(request):
    required_keys = ['user_id', 'tenant_id', 'uuid',
                 'balancing_method', 'instance_ips', 'instance_port',
                 'dns_names']

    for key in required_keys:
        if key not in request['msg']:
            msg = "No %s in request" % key
            raise exception.BadRequest(explanation=msg)

    # TODO (wenjianhn): UTF-8 support. discuss with lzy & cy
    for key in ['tenant_id', 'uuid']:
        if re.search(r"[^a-zA-Z0-9_\-]", request['msg'][key]):
            msg = "Invalid character '%s': %s" % \
                  (key, request['msg'][key])
            raise exception.BadRequest(explanation=msg)

    msg = request['msg']
    if msg['balancing_method'] not in ['source_binding',
                                       'round_robin']:
        msg = "Invalid balancing_method: %s" % msg['balancing_method']
        raise exception.BadRequest(explanation=msg)

    instance_ips = msg['instance_ips']
    _is_ipv4_list(instance_ips)

    port = msg['instance_port']
    if not isinstance(port, int):
        msg = 'Valid instance_port should be an integer'
        raise exception.BadRequest(explanation=msg)
    if int(port) < 1 or int(port) > 65535:
        msg = 'Valid instance_port should be between 1-65535'
        raise exception.BadRequest(explanation=msg)


def _check_delete_lb(request):
    required_keys = ['user_id', 'tenant_id', 'uuid']
    for key in required_keys:
        if key not in request['msg']:
            msg = "No %s in request" % key
            raise exception.BadRequest(explanation=msg)

    for key in ['tenant_id', 'uuid']:
        if re.search(r"[^a-zA-Z0-9_\-]", request['msg'][key]):
            msg = "Invalid character in request: '%s': %s" % \
                  (key, request['msg'][key])
            raise exception.BadRequest(explanation=msg)


def _do_basic_check(request):
    if not isinstance(request, dict):
        msg = "Valid Request should be a dict"
        raise exception.BadRequest(explanation=msg)

    if 'cmd' not in request:
        msg = 'No cmd in request'
        raise exception.BadRequest(explanation=msg)

    if 'msg' not in request:
        msg = 'No msg in request'
        raise exception.BadRequest(explanation=msg)

    cmd = request['cmd']
    if cmd not in ['create_lb', 'update_lb', 'delete_lb']:
        msg = 'Invalid cmd: %s' % request['cmd']
        raise exception.BadRequest(explanation=msg)

    if cmd in ['create_lb', 'update_lb']:
        _check_create_or_update_lb(request)
    else:
        _check_delete_lb(request)


def check_http_request(request):
    _do_basic_check(request)

    if request['cmd'] == 'delete_lb':
        # NOTE(wenjianhn)
        # All the checking stuff has been done in _do_basic_check()
        return

    for key in ['http_server_names', 'health_check_target_path']:
        if key not in request['msg']:
            msg = "No %s in request" % key
            raise exception.BadRequest(explanation=msg)

    server_names = request['msg']['http_server_names']
    _is_valid_server_names(server_names)

    # is_valid_conf_health_check
    # TODO(wenjianhn): healthcheck_field
    # 'health_check_target_path': '/',


def _check_haproxy_health_check_config(request):
    required_keys = ['health_check_timeout_ms',
                     'health_check_interval_ms',
                     'health_check_healthy_threshold',
                     'health_check_unhealthy_threshold']

    msg = request['msg']
    for key in required_keys:
        if key not in msg:
            strerror = "No %s in request" % key
            raise exception.BadRequest(explanation=strerror)
        else:
            if not isinstance(msg[key], int):
                strerror = "Error. %s should be an integer" % msg[key]
                raise exception.BadRequest(explanation=strerror)

    time_out = msg['health_check_timeout_ms']
    if time_out <= 0:
        strerror = "Health check timeout should be an positive integer"
        raise exception.BadRequest(explanation=strerror)

    interval = msg['health_check_interval_ms']
    if interval <= 0:
        strerror = "Health check timeout should be an positive integer"
        raise exception.BadRequest(explanation=strerror)

    healthy_threshold = msg['health_check_healthy_threshold']
    if healthy_threshold < 1 or healthy_threshold > 10:
        # TODO(wenjianhn): configuable value, check in conf_haproxy.py
        strerror = "healthy_threshold should between 1 and 10"
        raise exception.BadRequest(explanation=strerror)

    unhealthy_threshold = msg['health_check_unhealthy_threshold']
    if unhealthy_threshold < 1 or unhealthy_threshold > 10:
        # TODO(wenjianhn): configuable value, check in conf_haproxy.py
        strerror = "unhealthy_threshold should between 1 and 10"
        raise exception.BadRequest(explanation=strerror)


def _check_haproxy_instance_uuid(request):
    instance_uuids = request['msg']['instance_uuids']
    instance_ips = request['msg']['instance_ips']

    if len(instance_uuids) != len(instance_ips):
        strerror = ("Count of instance_uuids (%s) is "
                    "not equal to count of instance_ips (%s)" %
                    (len(instance_uuids), len(instance_ips)))
        raise exception.BadRequest(explanation=strerror)

    for uuid in instance_uuids:
        if not _is_uuid_like(uuid):
            strerror = "Invalid uuid format (%s)" % uuid
            raise exception.BadRequest(explanation=strerror)


def check_tcp_request(request):
    _do_basic_check(request)

    if request['cmd'] == 'delete_lb':
        # NOTE(wenjianhn)
        # All the checking stuff has been done in _do_basic_check()
        return

    _check_haproxy_health_check_config(request)

    _check_haproxy_instance_uuid(request)
