# --------------------------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for license information.
# --------------------------------------------------------------------------------------------

import unittest
try:
    import unittest.mock as mock
except ImportError:
    import mock

from azure.cli.core.application import APPLICATION, Configuration


def mock_echo_args(command_name, parameters):
    try:
        argv = ' '.join((command_name, parameters)).split()
        APPLICATION.initialize(Configuration())
        command_table = APPLICATION.configuration.get_command_table(argv)
        prefunc = command_table[command_name].handler
        command_table[command_name].handler = lambda args: args
        parsed_namespace = APPLICATION.execute(argv)
        return parsed_namespace
    finally:
        command_table[command_name].handler = prefunc


class TestVMValidators(unittest.TestCase):

    def _mock_get_subscription_id():
        return '00000000-0000-0000-0000-000000000000'

    @mock.patch('azure.cli.core.commands.client_factory.get_subscription_id', _mock_get_subscription_id)
    def test_vm_nics(self):

        from argparse import Namespace
        from azure.cli.command_modules.vm._validators import _validate_vm_create_nics

        for i in range(0, 100):
            ns = Namespace()
            ns.resource_group_name = 'rg'
            ns.nics = ['nic1', 'nic2']
            _validate_vm_create_nics(ns)

            nic1_expected = {
                "id": "/subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/rg/providers/Microsoft.Network/networkInterfaces/nic1",
                "properties": {
                    "primary": True
                }
            }

            nic2_expected = {
                "id": "/subscriptions/00000000-0000-0000-0000-000000000000/resourceGroups/rg/providers/Microsoft.Network/networkInterfaces/nic2",
                "properties": {
                    "primary": False
                }
            }
            self.assertEqual(ns.nics[0], nic1_expected)
            self.assertEqual(ns.nics[1], nic2_expected)


class Test_ArgumentParser(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pass

    def test_parse_vm_show(self):

        # If we use an ID as the positional parameter, we should
        # extract the resource group and name from it...
        args = mock_echo_args('vm show',
                              '--id /subscriptions/00000000-0000-0000-0000-0123456789abc/resourceGroups/thisisaresourcegroup/providers/Microsoft.Compute/virtualMachines/thisisavmname')  # pylint: disable=line-too-long
        self.assertDictEqual({
            'resource_group_name': 'thisisaresourcegroup',
            'vm_name': 'thisisavmname',
            'show_details': False
        }, args.result)

        # Invalid resource ID should trigger the missing resource group
        # parameter failure
        with self.assertRaises(SystemExit):
            mock_echo_args('vm show', '--id /broken')

        # Got to provide a resource group if you are using a simple name and
        # not an ID as a parameter
        with self.assertRaises(SystemExit):
            mock_echo_args('vm show', '--id missing-resource-group')

    def test_parse_vm_list(self):
        # Resource group name is optional for vm list, so
        # we should see a successfully parsed namespace
        args = mock_echo_args('vm list', '')
        self.assertDictEqual({
            'resource_group_name': None,
            'show_details': False
        }, args.result)

        # if resource group name is specified, however,
        # it should get passed through...
        args = mock_echo_args('vm list', '-g hullo')
        self.assertDictEqual({
            'resource_group_name': 'hullo',
            'show_details': False
        }, args.result)

    consistent_arguments = {
        'resource_group_name': ('--resource-group', '-g'),
        'virtual_machine_name': ('--vm-name',),
    }

    def test_command_consistency(self):
        argv = ['vm']
        APPLICATION.initialize(Configuration())
        command_table = APPLICATION.configuration.get_command_table(argv)
        vm_commands = ((vm_command, metadata) for vm_command, metadata
                       in command_table.items() if vm_command.startswith('vm'))

        for command_name, command_metadata in vm_commands:
            for argument_name, expected_options_list in self.consistent_arguments.items():
                try:
                    actual_options_list = command_metadata.arguments[argument_name].options_list
                    self.assertEqual(actual_options_list, expected_options_list,
                                     'Argument {} of command {} has inconsistent flags'.format(
                                         argument_name,
                                         command_name
                                     ))
                except KeyError:
                    pass


if __name__ == '__main__':
    unittest.main()
