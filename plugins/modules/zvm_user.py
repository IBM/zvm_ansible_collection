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
module: zvm_user

short_description: z/VM User Management Ansible Module

version_added: "0.0.1"

description: an Ansible module for managing z/VM virtual machines

options:
    name:
        description: this is the user to create/destroy
        required: true
        type: str
    newpass:
        description: password for the new user
        type: str
    prototype:
        description: directory prototype to base the new user on, if not using a dirfile
        type: str
    accounting:
        description: accounting code for the new user
        type: str
    dirfile:
        description: text file containing the directory statements for the new user, if not using a prototype
        type: str
    erasemode:
        description:
            - should we wipe the disks, if any, when destorying the user definition
            - 0 = unspecified
            - 1 = do not wipe
            - 2 = wipe
        type: int
        choices:
            - 0
            - 1
            - 2
    exists:
        description: should the target exist or not
        required: false
        type: bool

author:
    - Jay Brenneman (@rjbrenn)
'''


EXAMPLES = r'''
# add user
- name: add user directory entry
  zvm_user:
      name: LINUX01
      dirfile: linux01.direct
      exists: true

# del  user
- name: del user directory entry
  zvm_user:
      name: LINUX01
      exists: false
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
    sample: " Deleting LINUX01 from the directory...
        Failed
        Return Code: 400
        Reason Code: 4
        Description: ULGSMC5400E Image or profile definition not found
        API issued : Image_Delete_DM"
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
        prototype=dict(type='str', required=False),
        accounting=dict(type='str', required=False),
        dirfile=dict(type='str', required=False),
        erasemode=dict(type='int', required=False, choices=[0, 1, 2]),
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

    cmd_string = []

    if module.params['exists']:
        # make the user
        cmd_string = []
        cmd_string.append("/opt/zthin/bin/smcli")
        cmd_string.append("Image_Create_DM")
        cmd_string.append("-T")
        cmd_string.append(module.params['name'])
        if module.params['prototype'] is not None:
            cmd_string.append("-p")
            cmd_string.append(module.params['prototype'])
        if module.params['newpass'] is not None:
            cmd_string.append("-w")
            cmd_string.append(module.params['newpass'])
        if module.params['accounting'] is not None:
            cmd_string.append("-a")
            cmd_string.append(module.params['accounting'])
        if module.params['dirfile'] is not None:
            cmd_string.append("-f")
            cmd_string.append(module.params['dirfile'])
    else:
        # unmake the user
        cmd_string.append("/opt/zthin/bin/smcli")
        cmd_string.append("Image_Delete_DM")
        cmd_string.append("-T")
        cmd_string.append(module.params['name'])
        if module.params['erasemode'] is not None:
            cmd_string.append("-e")
            cmd_string.append(str(module.params['erasemode']))
        else:
            cmd_string.append("-e")
            cmd_string.append("0")

    # check_rc=False because if we get rerun idempotently this may fail with 'not found'
    smcli_results = module.run_command(cmd_string, check_rc=False)
    result['return_stdout'] = smcli_results[1]
    result['return_stderr'] = smcli_results[2]
    result['return_code'] = smcli_results[0]

    if result['return_code'] == 0:
        result['changed'] = True
        module.exit_json(**result)

    if result['return_code'] >= 1:
        notreally_errs = ["Image or profile name already defined", "Image or profile definition not found"]
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
