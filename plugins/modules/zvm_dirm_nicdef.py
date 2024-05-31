#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright (c) IBM Corporation 2023
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#     http://www.apache.org/licenses/LICENSE-2.0
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type


DOCUMENTATION = r'''
author:
    - Jay Brenneman (@rjbrenn)
'''


EXAMPLES = r'''
'''


RETURN = r'''
'''


from ansible.module_utils.basic import AnsibleModule
from ansible_collections.ibm.zvm_ansible.plugins.module_utils.psmapi import(call_client)


def run_module():
    module_args = dict(
        name=dict(type='str', required=True),
        zvmhost=dict(type='str', required=True),
        port=dict(type='int', required=True),
        authuser=dict(type='str', required=True),
        authpass=dict(type='str', required=True, no_log=True),
        devno=dict(type='str', required=True),
        nictype=dict(type='str', required=False, choices=['QDIO', 'HIPER'], default='HIPER'),
        lanname=dict(type='str', required=False),
        lanowner=dict(type='str', required=False, default='SYSTEM'),
        vlanid=dict(type='str', required=False),
        macid=dict(type='str', required=False),
        exists=dict(type='bool', required=False)
    )

    result = dict(
        changed=False,
        return_stdout=[],
        return_stderr=[],
        return_code=-9,
        reason_code=-9
    )

    module = AnsibleModule(
        argument_spec=module_args,
        supports_check_mode=True
    )

    if module.check_mode:
        module.exit_json(**result)

    cmd_string = ""
    cmd_string += module.params['devno']

    if module.params['exists'] == True:
        cmd_string += " TYPE " + str(module.params['nictype'])
        if module.params['lanname'] is not None:
            cmd_string += " LAN " + module.params['lanowner'] + ' ' + module.params['lanname'] 
        if module.params['vlanid'] is not None:
            cmd_string += " VLAN " + module.params['vlanid']
        if module.params['macid'] is not None:
            cmd_string += " MACID " + module.params['macid']
    else:
        cmd_string += " DELETE"

    smcli_results = call_client( module.params['zvmhost'],  \
                                 module.params['port'],     \
                                 module.params['authuser'], \
                                 module.params['authpass'], \
                                 module.params['name'], "Dirm_Nicdef", cmd_string)
    result['return_code'] = smcli_results[0]
    result['reason_code'] = smcli_results[1]
    result['return_stdout'] = smcli_results[2]

    if result['return_code'] == 0:
        result['changed'] = True
        module.exit_json(**result)

    if result['return_code'] >= 1:
        notreally_errs = []
        # notreally_errs is a list of VM error messages that are OK within this contect
        noterror_count = 0

        for j in notreally_errs:
            if result['return_stdout'].find(j) != -1:
                noterror_count += 1
        if noterror_count > 0:
            # optimistically guessing this is not an error condition
            # it might still actually be an error condition if there is a real error among the not-errors
            # will figure that out later if it ends up happening
            # exit no error
            result['return_stdout'] += ">> skipping an error because its probably OK in this situation <<"
            module.exit_json(**result)
        # here we are in error condition
        errormsg = "failing return code from smcli is: " + str(result['return_code'])
        module.fail_json(errormsg, **result)

    errormsg = "unknown return code from smcli: " + str(result['return_code'])
    result['return_stderr'] = ["how did we get here???"]
    module.fail_json(errormsg, **result)


def main():
    run_module()


if __name__ == '__main__':
    main()
