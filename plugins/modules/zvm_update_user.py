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
---
module: zvm_update_user

short_description: z/VM User Update Ansible Module

version_added: "0.0.1"

description: "an Ansible module for changing the password, cpu configuration, and memory configuration of z/VM virtual machines via SMAPI"

options:
    name:
        description: the user we are modifying
        required: true
        type: str
    newpass:
        description: new password value for the user
        type: str
    vcpus:
        description: number of virtual CPUs the user should have
        type: int
    vcputype:
        description: type of CPUs the user should have. Linux should generally be on IFL.
        type: str
        choices:
            - CP
            - IFL
            - ZIIP
            - ICF
    maxcpus:
        description: maximum number of CPUs the user can dynamically define for themselves beyond what the directory provides
        type: int
    mem:
        description: how much memory should the user have by default
        type: int
    maxmem:
        description: how much total memory should the user be able to configure
        type: int
    memsuffix:
        description: whats the unit of the memory values
        type: str
        choices:
            - M
            - G
            - T

author:
    - Jay Brenneman (@rjbrenn)
'''

EXAMPLES = r'''
- name: resize a user
  zvm_update_user:
      name: LINUX01
      vcpus: 4
      vcputype: IFL
      maxcpus: 12
      mem: 20
      maxmem: 30
      memsuffix: G
'''


RETURN = r'''
return_stdout:
    description: the stdout responses from smcli as a dict
    returned: always
    type: list
    elements: str
    sample: "Updating LINUX01 virtual machine directory entry...
        ...Done"
return_stderr:
    description: the stderr responses from smcli as a dict
    returned: always
    type: list
    elements: str
    sample: "Updating LINUX01 virtual machine directory entry...
        Failed
        Return Code: 596
        Reason Code: 3213
        Description: ULGSMC5596E Internal directory manager error - product-specific return code : 3213
        API issued : Image_Definition_Update_DM
        Details: COMMAND_IN_ERROR=FOR LITSTSM STORAGE 128G (SMAPI 596,3213)
        DVHSTO3213E Your current maximum storage size is 32G, your requested  amount was 128G
        Your request can not be satisfied. FOR LINUX01 REPLACE (SMAPI 596,1172)"
return_code:
    description: The results of doing the thing
    type: int
    returned: always
    sample: 0
reason_code:
    description: The reason for the result
    type: int
    returned: always
    sample: 0
'''


from ansible.module_utils.basic import AnsibleModule


def run_module():
    module_args = dict(
        name=dict(type='str', required=True),
        newpass=dict(type='str', required=False, no_log=True),
        vcpus=dict(type='int', required=False),
        vcputype=dict(type='str', required=False, choices=['CP', 'IFL', 'ZIIP', 'ICF']),
        maxcpus=dict(type='int', required=False),
        mem=dict(type='int', required=False),
        maxmem=dict(type='int', required=False),
        memsuffix=dict(type='str', required=False, choices=['M', 'G', 'T'])
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

    cmd_string = []

    cmd_string.append("/opt/zthin/bin/smcli")
    cmd_string.append("Image_Definition_Update_DM")
    cmd_string.append("-T")
    cmd_string.append(module.params['name'])
    if module.params['newpass'] is not None:
        cmd_string.append("-k")
        cmd_string.append("PASSWORD=" + module.params['newpass'])
    if module.params['vcpus'] is not None:
        if module.params['vcpus'] > 1:
            # asking for 2 or more CPUs
            if module.params['vcputype'] is not None:
                # asking for a specific cpu type
                cmd_string.append("-k")
                cmd_string.append("COMMAND_DEFINE_CPU= CPUADDR=0-" + str(module.params['vcpus'] - 1) + " TYPE=" + module.params['vcputype'])
            else:
                # asking for default cpu type
                cmd_string.append("-k")
                cmd_string.append("COMMAND_DEFINE_CPU= CPUADDR=0-" + str(module.params['vcpus'] - 1))
        else:
            # asking for only 1 CPU
            if module.params['vcputype'] is not None:
                # asking for a specific cpu type
                cmd_string.append("-k")
                cmd_string.append("COMMAND_DEFINE_CPU= CPUADDR=0 TYPE=" + module.params['vcputype'])
            else:
                # asking for default cpu type
                cmd_string.append("-k")
                cmd_string.append("COMMAND_DEFINE_CPU= CPUADDR=0")
    if module.params['maxcpus'] is not None:
        cmd_string.append("-k")
        cmd_string.append("CPU_MAXIMUM= COUNT=" + str(module.params['maxcpus']) + " TYPE=Z")
    if module.params['mem'] is not None:
        cmd_string.append("-k")
        cmd_string.append("STORAGE_INITIAL=" + str(module.params['mem']) + module.params['memsuffix'])
    if module.params['maxmem'] is not None:
        cmd_string.append("-k")
        cmd_string.append("STORAGE_MAXIMUM=" + str(module.params['maxmem']) + module.params['memsuffix'])

    # check_rc=False because if we get rerun idempotently this may fail due to 'already exits'
    smcli_results = module.run_command(cmd_string, check_rc=False)
    result['return_stdout'] = smcli_results[1]
    result['return_stderr'] = smcli_results[2]
    result['return_code'] = smcli_results[0]

    if result['return_code'] == 0:
        result['changed'] = True
        module.exit_json(**result)

    if result['return_code'] >= 1:
        notreally_errs = ["Image or profile name already defined"]
        # notreally_errs is a list of VM error messages that are OK within this contect
        noterror_count = 0

        # an SMAPI error message comes back like this. The important parts are the
        # return code and the reason code
        #    "return_stdout": [
        #        "Defining thingone in the directory... ",
        #        "Failed",
        #        "  Return Code: 400",
        #        "  Reason Code: 8",
        #        "  Description: ULGSMC5400E Image or profile name already defined",
        #        "  API issued : Image_Create_DM"
        #    ]

        # this is gross but I looked at alternatives and they were less readable
        # scann return stdout and stderr for
        for i in result['return_stdout']:
            for j in notreally_errs:
                if i.find(j) != -1:
                    noterror_count += 1
        if noterror_count > 0:
            # optimistically guessing this is not an error condition
            # it might still actually be an error condition if there is a real error among the not-errors
            # will figure that out later if it ends up happening
            # exit no error
            result['return_stdout'].append("skipping an error because its probably OK in this situation")
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
