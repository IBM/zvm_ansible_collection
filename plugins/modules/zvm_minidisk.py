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
module: zvm_minidisk

short_description: z/VM User Minidisk management Ansible Module

version_added: "0.0.1"

description: an Ansible module for managing z/VM virtual machine minidisks. This does not dedicate devices, or handle ZFCP host adapters

options:
    name:
        description: this is the target who will own or lose the disk
        required: true
        type: str
    diskaddr:
        description: the address of the disk in question
        required: true
        type: str
    disktype:
        description: what kind of disk are we talking about, here
        type: str
        choices:
            - '3390'
            - '9336'
            - 'AUTO'
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
    diskunits:
        description: If disktype = 3390, then use 1 here for CYLINDERS.
            If disktype = 9336, then use 2 for 512 byte blocks.
            options 3-5 are for VM internal CMS disk stuff dont bother for Linux use.
        type: int
        choices:
            - 1
            - 2
            - 3
            - 4
            - 5
    disksize:
        description: how many (diskunits) large is the new device going to be
        type: int
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
    diskformat:
        description: Do we want to dasdfmt this device after allocating it ?
            the dasdfmt command is hardcoded in the module to use CDL layout and 4K block size.
            No partitions will be created.
        type: bool
    diskrpw:
        description: read-access password to access the disk
        type: str
    diskwpw:
        description: write-access password to access the disk
        type: str
    diskmpw:
        description: multi-write-access password to access the disk
        type: str
    diskwipe:
        description: if we are deleting the minidisk do we want to wipe it before releasing the space back to the pool ?
                     0 = Unspecified
                     1 = do not wipe
                     2 = wipe
        type: int
        default: 0
        choices:
            - 0
            - 1
            - 2
    exists:
        description: create / delete the disk
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
# Add a disk from pool EAVPOOL
- name: add data disk 1
  zvm_minidisk:
    name: LINUX02
    diskaddr: 202
    disktype: 3390
    diskalloc: AUTOG
    diskloc: EAVPOOL
    diskunits: 1
    disksize: 10016
    diskmode: MR
    diskformat: True
    exists: True

# Delete a disk
- name: delete data disk 1 and wipe it with zeros
  zvm_minidisk:
    name: LINUX03
    diskaddr: 501
    diskwipe: 2
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
        diskaddr=dict(type='str', required=True),
        disktype=dict(type='str', required=False, choices=['3390', '9336', 'AUTO']),
        diskalloc=dict(type='str', required=False, choices=['AUTOR', 'AUTOV', 'AUTOG', 'DEVNO']),
        diskloc=dict(type='str', required=False),
        diskunits=dict(type='int', required=False, choices=[1, 2, 3, 4, 5]),
        disksize=dict(type='int', required=False),
        diskmode=dict(type='str', required=False, choices=['R', 'RR', 'W', 'WR', 'M', 'MR', 'MW']),
        diskformat=dict(type='bool', required=False),
        diskrpw=dict(type='str', required=False),
        diskwpw=dict(type='str', required=False),
        diskmpw=dict(type='str', required=False),
        diskwipe=dict(type='int', required=False, choices=[0, 1, 2]),
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
    dasdfmt_string = []
    flag_format = False

    if module.params['exists']:
        cmd_string = []
        cmd_string.append("/opt/zthin/bin/smcli")
        cmd_string.append("Image_Disk_Create_DM")
        cmd_string.append("-T")
        cmd_string.append(module.params['name'])
        if module.params['diskaddr'] is not None:
            cmd_string.append("-v")
            cmd_string.append(str(module.params['diskaddr']))
        if module.params['disktype'] is not None:
            cmd_string.append("-t")
            cmd_string.append(str(module.params['disktype']))
        if module.params['diskalloc'] is not None:
            cmd_string.append("-a")
            cmd_string.append(module.params['diskalloc'])
        if module.params['diskloc'] is not None:
            cmd_string.append("-r")
            cmd_string.append(module.params['diskloc'])
        if module.params['diskunits'] is not None:
            cmd_string.append("-u")
            cmd_string.append(str(module.params['diskunits']))
        if module.params['disksize'] is not None:
            cmd_string.append("-z")
            cmd_string.append(str(module.params['disksize']))
        if module.params['diskmode'] is not None:
            cmd_string.append("-m")
            cmd_string.append(module.params['diskmode'])
        if module.params['diskformat'] is not None:
            # we are mooching this parm and using it to mean something else
            # this is intended to signal a CMS block format of a new minidisk,
            # but we are never going to need that. ( yeah guaranteeed to need that
            # at some point now that I said it )
            # instead we use this as a signal later whether to attach and
            # dasdfmt the new disk
            flag_format = True
            # get out of the if clause and always signal "no Format" to SMCLI
        cmd_string.append("-f")
        cmd_string.append("1")
        if module.params['diskrpw'] is not None:
            cmd_string.append("-R")
            cmd_string.append(module.params['diskrpw'])
        if module.params['diskwpw'] is not None:
            cmd_string.append("-W")
            cmd_string.append(module.params['diskwpw'])
        if module.params['diskmpw'] is not None:
            cmd_string.append("-M")
            cmd_string.append(module.params['diskmpw'])

        # check_rc=False because if we get rerun idempotently the disk will already be there
        smcli_results = module.run_command(cmd_string, check_rc=False)
        result['return_stdout'] = smcli_results[1]
        result['return_stderr'] = smcli_results[2]
        result['return_code'] = smcli_results[0]

        if result['return_code'] == 0:
            result['changed'] = True
            if flag_format:
                # weve been asked to dasdfmt the above new disk
                # find a free device address
                locladdr = 0000
                mounted = False
                link_string = []
                while mounted is False:
                    locladdr = binascii.b2a_hex(os.urandom(2))
                    link_string.append('vmcp')
                    link_string.append('link')
                    link_string.append(module.params['name'])
                    link_string.append(str(module.params['diskaddr']))
                    link_string.append(locladdr)
                    link_string.append("W")
                    link_results = module.run_command(link_string, check_rc=True)
                    if int(link_results[0]) == 0:
                        mounted = True
                    link_string = []

                # config the drive online
                chzdev_string = []
                chzdev_string.append("chccwdev")
                chzdev_string.append("-e")
                chzdev_string.append(locladdr)
                chzdev_results = module.run_command(chzdev_string, check_rc=True)

                # wait 5 seconds for udev to find it and make the symlinks
                time.sleep(5)

                # format it
                dasdfmt_string.append("dasdfmt")
                dasdfmt_string.append("-b")
                dasdfmt_string.append("4096")
                dasdfmt_string.append("-d")
                dasdfmt_string.append("CDL")
                dasdfmt_string.append("-y")
                dasdfmt_string.append("/dev/disk/by-path/ccw-0.0." + locladdr.decode())
                dasdfmt_results = module.run_command(dasdfmt_string, check_rc=True)

                # wait 5 seconds for udev to find it and make the symlinks
                time.sleep(5)

                # config the drive offline
                chzdev_string = []
                chzdev_string.append("chccwdev")
                chzdev_string.append("-d")
                chzdev_string.append(locladdr)
                chzdev_results = module.run_command(chzdev_string, check_rc=True)

                # wait 5 seconds for udev to find it and make the symlinks
                time.sleep(5)

                # detach it
                det_string = []
                det_string.append("vmcp")
                det_string.append("detach")
                det_string.append(locladdr)
                det_results = module.run_command(det_string, check_rc=True)

                # end of if flag_format

            module.exit_json(**result)
            # end if rc=0

        if result['return_code'] >= 1:
            notreally_errs = ["Image disk already defined"]
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
        cmd_string.append("Image_Disk_Delete_DM")
        cmd_string.append("-T")
        cmd_string.append(module.params['name'])
        if module.params['diskaddr'] is not None:
            cmd_string.append("-v")
            cmd_string.append(str(module.params['diskaddr']))
        if module.params['diskwipe'] is not None:
            cmd_string.append("-e")
            cmd_string.append(str(module.params['diskwipe']))
        else:
            cmd_string.append("-e")
            cmd_string.append("0")

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
            notreally_errs = ["Image disk does not exist"]
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
