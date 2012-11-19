# vim: tabstop=4 shiftwidth=4 softtabstop=4
#
# Copyright 2012 Sina Corporation
# All Rights Reserved.
# Author: Justin Ljj <iamljj@gmail.com>
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

from nozzle.openstack.common import jsonutils

from cliff.command import Command
from cliff.lister import Lister
from cliff.show import ShowOne


class NozzleCommand(Command):
    """Base class for nozzle commands"""

    def get_client(self):
        return self.app.client_manager.get_client()

    def run(self, parsed_args):
        return super(NozzleCommand, self).run(parsed_args)

    def take_action(self, parsed_args):
        return self.get_data(parsed_args)

    def get_data(self, parsed_args):
        pass


class CreateCommand(NozzleCommand, ShowOne):
    """Create a resource for a given tenant."""

    resource = None

    def get_parser(self, prog_name):
        parser = super(CreateCommand, self).get_parser(prog_name)
        self.add_known_arguments(parser)
        return parser

    def add_known_arguments(self, parser):
        pass

    def make_request_body(self, parsed_args):
        return dict()

    def get_data(self, parsed_args):
        nozzle_client = self.get_client()
        body = self.make_request_body(parsed_args)
        obj_creator = getattr(nozzle_client, "create_%s" % self.resource)
        data = obj_creator(body)
        ## deal with result
        if data['code'] != 200:
            raise Exception("error: %s" % data['message'])
        info = data['data']
        for k, v in info.iteritems():
            if isinstance(v, list):
                value = ""
                for item in v:
                    if value:
                        value += "\n"
                    if isinstance(item, dict):
                        value += jsonutils.dumps(item)
                    else:
                        value += str(item)
                info[k] = value
            elif v is None:
                info[k] = ""
        return zip(*sorted(info.iteritems()))


class UpdateCommand(NozzleCommand):
    """Update resource's information."""

    resource = None

    def get_parser(self, prog_name):
        parser = super(UpdateCommand, self).get_parser(prog_name)
        parser.add_argument(
            'id', metavar='ID or name of %s to update' % self.resource)
        self.add_known_arguments(parser)
        return parser

    def add_known_arguments(self, parser):
        pass

    def run(self, parsed_args):
        nozzle_client = self.get_client()
        ## prepare body
        data = self.make_request_body(parsed_args)
        obj_updator = getattr(nozzle_client, "update_%s" % self.resource)
        obj_updator(parsed_args.id, body=data)
        return


class DeleteCommand(NozzleCommand):
    """Delete a given resource."""

    resource = None

    def get_parser(self, prog_name):
        parser = super(DeleteCommand, self).get_parser(prog_name)
        parser.add_argument(
            'id', metavar='ID or name of %s to delete' % self.resource)
        return parser

    def run(self, parsed_args):
        nozzle_client = self.get_client()
        ## prepare body
        if not parsed_args.id:
            raise Exception("Specify the uuid of the load balancer to delete")
        obj_deleter = getattr(nozzle_client, "delete_%s" % self.resource)
        obj_deleter(parsed_args.id)
        return


class ListCommand(NozzleCommand, Lister):
    """List resources that belong to a given tenant."""

    resource = None

    def get_parser(self, prog_name):
        parser = super(ListCommand, self).get_parser(prog_name)
        self.add_known_arguments(parser)
        return parser

    def add_known_arguments(self, parser):
        pass

    def get_data(self, parsed_args):
        nozzle_client = self.get_client()
        obj_lister = getattr(nozzle_client, "list_%ss" % self.resource)

        if parsed_args.all_tenants:
            params = {'all_tenants': 1}
        else:
            params = {'all_tenants': 0}
        data = obj_lister(**params)
        if data['code'] != 200:
            raise Exception("error: %s" % data['message'])
        info = data['data']
        columns = ['name', 'uuid', 'state', 'protocol']
        rows = []
        for i in info:
            row = []
            for k, v in i.items():
                if k in columns:
                    row.append(v)
            rows.append(tuple(row))

        return (columns, tuple(rows))


class ShowCommand(NozzleCommand, ShowOne):
    """Show information of a given resource."""

    resource = None

    def get_parser(self, prog_name):
        parser = super(ShowCommand, self).get_parser(prog_name)
        parser.add_argument(
            'id', metavar='ID or name of %s to show' % self.resource)
        return parser

    def get_data(self, parsed_args):
        nozzle_client = self.get_client()
        obj_shower = getattr(nozzle_client, "show_%s" % self.resource)
        data = obj_shower(parsed_args.id)
        if data['code'] != 200:
            raise Exception("error: %s" % data['message'])
        info = data['data']

        for k, v in info.iteritems():
            if v is None:
                info[k] = ""
            elif isinstance(v, list):
                value = ""
                for item in v:
                    if value:
                        value += "\n"
                    if isinstance(item, dict):
                        value += jsonutils.dumps(item)
                    else:
                        value += str(item)
                info[k] = value
        return zip(*sorted(info.iteritems()))
