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
module: zvm_clone_disk

short_description: z/VM Clone Disk Ansible Module

version_added: "0.0.1"

description: an Ansible module for z/VM virtual machine minidisks

options:
    name:
        description: this is the target who will own the newly cloned disk
        required: true
        type: str
    diskaddr:
        description: the address of the newly cloned disk in the targets configuration
        required: true
        type: str
    srcname:
        description: source virtual machine that owns the disk to be cloned
        required: true
        type: str
    srcaddr:
        description: source virtual machine disk address to be cloned
        required: true
        type: str
    diskalloc:
        description: how should extents for the new disk be chosen? Select by Region, by Volume, by Volume Group, or a specific device?
        type: str
        choices:
            - AUTOR
            - AUTOV
            - AUTOG
            - DEVNO
    diskloc:
        description: name of the region where diskalloc managed extents should get pulled from - the specific region, volume, or group.
        type: str
    diskmode:
        description: minidisk access mode
        type: str
        choices:
            - R
            - RR
            - W
            - WR
            - M
            - MR
            - MW
    diskrpw:
        description: read-access password to access the disk
        type: str
    diskwpw:
        description: write-access password to access the disk
        type: str
    diskmpw:
        description: multi-write-access password to access the disk
        type: str

seealso:
    - name: IBM z/VM SMAPI documentation
      description: Reference for SMAPI application developers
      link: https://www.ibm.com/docs/en/zvm/7.3?topic=reference-socket-application-programming-interfaces

author:
    - Jay Brenneman (@rjbrenn)
'''


EXAMPLES = r'''
# clone GOLDMAST user disk 250 to existing NEWGUY disk 100
- name: clone NEWGUY 100 disk
  zvm_clone_disk:
    name: NEWGUY
    diskaddr: 100
    srcname: GOLDMAST
    srcaddr: 250

# Create NEWGUY 100 in BIGPOOL0 and clone GOLDMAST 250 into it
- name: make NEWGUY 100 and clone into it
  zvm_clone_disk:
    name: NEWGUY
    diskaddr: 100
    srcname: GOLDMAST
    srcaddr: 250
    diskalloc: AUTOG
    diskloc: BIGPOOL0
    diskmode: W
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
    sample: "Defining thingone in the directory...
             Failed
             Return Code: 400
             Reason Code: 8
             Description: ULGSMC5400E Image or profile name already defined
             API issued : Image_Create_DM"
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
        diskaddr=dict(type='str', required=True),
        srcname=dict(type='str', required=True),
        srcaddr=dict(type='str', required=True),
        diskalloc=dict(type='str', required=False, choices=['AUTOR', 'AUTOV', 'AUTOG', 'DEVNO']),
        diskloc=dict(type='str', required=False),
        diskmode=dict(type='str', required=False, choices=['R', 'RR', 'W', 'WR', 'M', 'MR', 'MW']),
        diskrpw=dict(type='str', required=False),
        diskwpw=dict(type='str', required=False),
        diskmpw=dict(type='str', required=False)
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
    cmd_string.append("Image_Disk_Copy_DM")
    cmd_string.append("-T")
    cmd_string.append(module.params['name'])
    cmd_string.append("-t")
    cmd_string.append(module.params['diskaddr'])
    cmd_string.append("-S")
    cmd_string.append(module.params['srcname'])
    cmd_string.append("-s")
    cmd_string.append(module.params['srcaddr'])
    if module.params['diskalloc'] is not None:
        cmd_string.append("-a")
        cmd_string.append(module.params['diskalloc'])
    if module.params['diskloc'] is not None:
        cmd_string.append("-n")
        cmd_string.append(module.params['diskloc'])
    if module.params['diskmode'] is not None:
        cmd_string.append("-m")
        cmd_string.append(module.params['diskmode'])
    if module.params['diskrpw'] is not None:
        cmd_string.append("-r")
        cmd_string.append(module.params['diskrpw'])
    if module.params['diskwpw'] is not None:
        cmd_string.append("-w")
        cmd_string.append(module.params['diskwpw'])
    if module.params['diskmpw'] is not None:
        cmd_string.append("-x")
        cmd_string.append(module.params['diskmpw'])

    # check=false because some errors are expected if we are adding a disk that already exists
    # on subsequent runs of the module - idempotently
    smcli_results = module.run_command(cmd_string, check_rc=False)
    result['return_stdout'] = smcli_results[1]
    result['return_stderr'] = smcli_results[2]
    result['return_code'] = smcli_results[0]

    if result['return_code'] == 0:
        result['changed'] = True
        module.exit_json(**result)

    if result['return_code'] >= 1:
        notreally_errs = ["Image disk already defined"]
        #
        # notreally_errs is a list of VM error messages that are OK within this contect
        noterror_count = 0

        #
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

        #
        # this is gross but I looked at alternatives and they were less readable
        # scann return stdout and stderr for
        for i in result['return_stdout']:
            for j in notreally_errs:
                if i.find(j) != -1:
                    noterror_count += 1
        if noterror_count > 0:
            #
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
