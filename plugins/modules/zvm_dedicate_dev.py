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
module: zvm_dedicate_dev

short_description: z/VM User Dedicated Device management Ansible Module

version_added: "0.0.2"

description: an Ansible module for managing z/VM virtual machine dedicated devices. Should work for OSA, DASD, and FCP devices.

options:
    name:
        description: this is the target who will own or lose the device
        required: true
        type: str
    virtaddr:
        description: the virtual address of the device as seen by the guest
        required: true
        type: str
    realaddr:
        description: the real address of the device on the system
        type: str
    readonly:
        description: if a DASD, should it be RO as viewed by the guest?
        type: bool
    exists:
        description: add / remove the dedicated virtaddr
        type: bool
        required: true

seealso:
    - name: IBM z/VM SMAPI documentation
      description: Reference for SMAPI application developers
      link: https://www.ibm.com/docs/en/zvm/7.3?topic=reference-socket-application-programming-interfaces

author:
    - Jay Brenneman (@rjbrenn)
'''


EXAMPLES = r'''
# Add a dasd vol
- name: add data disk 1
  zvm_dedicate_dev:
    name: LINUX02
    virtaddr: 202
    realaddr: d022
    exists: True

# Add an OSA
- name: add osa read
  zvm_dedicate_dev:
    name: LINUX03
    virtaddr: 900
    realaddr: 906
    exists: True
- name: add osa write
  zvm_dedicate_dev:
    name: LINUX03
    virtaddr: 901
    realaddr: 907
    exists: True
- name: add osa data
  zvm_dedicate_dev:
    name: LINUX03
    virtaddr: 902
    realaddr: 905
    exists: True

# Delete a dasd vol
- name: delete data disk 1
  zvm_dedicate_dev:
    name: LINUX02
    virtaddr: 202
    exists: False
'''


RETURN = r'''
return_stdout:
    description: the stdout responses from smcli as a dict
    returned: always
    type: list
    elements: str
    sample: "...Done"
return_stderr:
    description: the stderr responses from smcli as a dict
    returned: always
    type: list
    elements: str
    sample: "Deleting a disk from litstsm's directory entry...
        Failed
          Return Code: 208
          Reason Code: 36
          Description: ULGSMC5208E Image disk does not exist
          API issued : Image_Disk_Delete_DM"
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
import os
import binascii
import time


def run_module():
    module_args = dict(
        name=dict(type='str', required=True),
        virtaddr=dict(type='str', required=True),
        realaddr=dict(type='str', required=False),
        readonly=dict(type='bool', required=False),
        exists=dict(type='bool', required=True)
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

    if module.params['exists']:
        cmd_string = []
        cmd_string.append("/opt/zthin/bin/smcli")
        cmd_string.append("Image_Device_Dedicate_DM")
        cmd_string.append("-T")
        cmd_string.append(module.params['name'])
        if module.params['virtaddr'] is not None:
            cmd_string.append("-v")
            cmd_string.append(str(module.params['virtaddr']))
        if module.params['realaddr'] is not None:
            cmd_string.append("-r")
            cmd_string.append(str(module.params['realaddr']))
        if module.params['readonly'] is True:
            cmd_string.append("-R 1")
        else:
            cmd_string.append("-R 0")

        # check_rc=False because if we get rerun idempotently the disk will already be there
        smcli_results = module.run_command(cmd_string, check_rc=False)
        result['return_stdout'] = smcli_results[1]
        result['return_stderr'] = smcli_results[2]
        result['return_code'] = smcli_results[0]

        if result['return_code'] == 0:
            result['changed'] = True
            module.exit_json(**result)
            # end if rc=0

        if result['return_code'] >= 1:
            notreally_errs = ["Image device already defined"]
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
            # scan return stdout and stderr for
            for i in notreally_errs:
                if result['return_stdout'].find(i) != -1:
                    noterror_count += 1
            if noterror_count > 0:
                # optimistically guessing this is not an error condition
                # it might still actually be an error condition if there is a real error among the not-errors
                # will figure that out later if it ends up happening
                # exit no error
                result['return_stdout'] += "\n\n >> skipping an error because its probably OK in this situation  <<"
                module.exit_json(**result)
            # here we are in error condition
            errormsg = "failing return code from smcli is: " + str(result['return_code'])
            module.fail_json(errormsg, **result)
            # end if result rc>=1

        # catch all other weird return code conditions, should not happen ever
        errormsg = "unknown return code from smcli: " + str(result['return_code'])
        result['return_stderr'] = ["how did we get here???"]
        module.fail_json(errormsg, **result)
        # end if exists block

    else:
        # make it not exist anymore
        cmd_string = []
        cmd_string.append("/opt/zthin/bin/smcli")
        cmd_string.append("Image_Device_Undedicate_DM")
        cmd_string.append("-T")
        cmd_string.append(module.params['name'])
        if module.params['virtaddr'] is not None:
            cmd_string.append("-v")
            cmd_string.append(str(module.params['virtaddr']))

        # check_rc=False because if we get rerun idempotently the disk may already be gone
        smcli_results = module.run_command(cmd_string, check_rc=False)
        result['return_stdout'] = smcli_results[1]
        result['return_stderr'] = smcli_results[2]
        result['return_code'] = smcli_results[0]

        if result['return_code'] == 0:
            result['changed'] = True

            module.exit_json(**result)
            # end if rc=0

        if result['return_code'] >= 1:
            notreally_errs = ["Image device not defined"]
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
            for i in notreally_errs:
                if result['return_stdout'].find(i) != -1:
                    noterror_count += 1
            if noterror_count > 0:
                # optimistically guessing this is not an error condition
                # it might still actually be an error condition if there is a real error among the not-errors
                # will figure that out later if it ends up happening
                # exit no error
                result['return_stdout'] += "\n\n >> skipping an error because its probably OK in this situation  <<"
                module.exit_json(**result)
            # here we are in error condition
            errormsg = "failing return code from smcli is: " + str(result['return_code'])
            module.fail_json(errormsg, **result)
            # end if result rc>=1

        # catch all other weird return code conditions, should not happen ever
        errormsg = "unknown return code from smcli: " + str(result['return_code'])
        result['return_stderr'] = ["how did we get here???"]
        module.fail_json(errormsg, **result)
        # end make not exist block


def main():
    run_module()


if __name__ == '__main__':
    main()

