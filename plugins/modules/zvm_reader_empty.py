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
module: zvm_reader_empty

short_description: empty a z/VM user's virtual card reader Ansible Module

version_added: "0.0.1"

description:
    - when you want to IPL a virtual machine from the card reader the
    - reader needs to be empty before punching the boot media into it. This module
    - dumps all the cards out of a target machines 00C card reader.

options:
    name:
        description: whos card reader is getting cleaned out?
        required: true
        type: str

author:
    - Jay Brenneman (@rjbrenn)
'''


EXAMPLES = r'''
# empty the card reader
- name: clearit
  zvm_reader_empty:
    name: NEWUSER0
'''


RETURN = r'''
return_stdout:
    description: the stdout responses from smcli as a dict
    returned: always
    type: list
    elements: str
    sample: "     2 FILES PURGED"
return_stderr:
    description: the stderr responses from smcli as a dict
    returned: always
    type: list
    elements: str
    sample: "     NO FILES PURGED
        HCPCSU003E Invalid option - LEON
        Error: non-zero CP response for command PURGE LEON RDR ALL: #3"
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

    # empty the target rdr
    cmds_string = []

    cmds_string.append("vmcp")
    cmds_string.append("purge")
    cmds_string.append(module.params['name'])
    cmds_string.append("rdr")
    cmds_string.append("all")

    vmcp_results = module.run_command(cmds_string, check_rc=True)

    result['return_stdout'] = vmcp_results[1]
    result['return_stderr'] = vmcp_results[2]
    result['return_code'] = vmcp_results[0]

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
