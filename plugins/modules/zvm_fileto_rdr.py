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
module: zvm_fileto_rdr

short_description: z/VM send file to user virtual card reader Ansible Module

version_added: "0.0.1"

description: an Ansible module for sending files to a z/VM user's virtual card reader

options:
    name:
        description: the user you are sending the file to
        required: true
        type: str
    filename:
        description: name of the file you are sending
        required: true
        type: str
    punchaddr:
        description: device address of the local card punch you are using to send the file to the user
        default: 0.0.000d
        type: str
    fileclass:
        description: a Single character A-Z output class of the file we are sending.
            This can be used as a filter on the receiving side for making decisions on what to do with a file when it arrives.
            Set as required by the automation on the target side.
        type: str
    asfilename:
        description: name of the file as observed on the receivers end.
            Note that VM only supports 8.8 char file names if that matters.
            FILEONE1.COOLTYPE is OK, VERYLOOOOONG.NAME.TOOMANYDOTS is not.
        type: str

author:
    - Jay Brenneman (@rjbrenn)
'''


EXAMPLES = r'''
# send a file to a user
- name: punch file to user
  zvm_fileto_rdr:
    name: SOMEGUY
    filename: /tmp/a_really_cool_script.sh
    asfilename: coolscr.sh
'''


RETURN = r'''
return_stdout:
    description: the stdout responses from smcli as a dict
    returned: always
    type: list
    elements: str
    sample: ""
return_stderr:
    description: the stderr responses from smcli as a dict
    returned: always
    type: list
    elements: str
    sample: "vmur: Unable to get status for /dev/vmpun-0.0.000a: No such file or directory
             vmur: Please check if device is online!"
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
        punchaddr=dict(type='str', required=False, default="0.0.000d"),
        fileclass=dict(type='str', required=False),
        asfilename=dict(type='str', required=False),
        filename=dict(type='str', required=True)
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

    # configure the local punch device online
    devonln_string = []

    devonln_string.append("cio_ignore")
    devonln_string.append("-r")
    if module.params['punchaddr'] is not None:
        devonln_string.append(module.params['punchaddr'])
    else:
        devonln_string.append("0.0.000d")

    # check_rc=False because the device may not be in the ignore list
    devonln1_results = module.run_command(devonln_string, check_rc=False)

    devonln_string = []
    devonln_string.append("sleep")
    devonln_string.append("1s")

    devonln2_results = module.run_command(devonln_string, check_rc=True)

    devonln_string = []
    devonln_string.append("chccwdev")
    devonln_string.append("-e")
    if module.params['punchaddr'] is not None:
        devonln_string.append(module.params['punchaddr'])
    else:
        devonln_string.append("0.0.000d")

    # check_rc=False because the device may already be online
    devonln3_results = module.run_command(devonln_string, check_rc=False)

    # punch the files
    # vmcp will consume the entire string after it, so we cant online a bunch of cmds at once
    # with &&
    punchcmds_string = []
    punchcmds_string.append("vmur")
    punchcmds_string.append("punch")
    if module.params['punchaddr'] is not None:
        punchcmds_string.append("-d")
        punchcmds_string.append("/dev/vmpun-" + module.params['punchaddr'])
    else:
        punchcmds_string.append("-d")
        punchcmds_string.append("/dev/vmpun-0.0.000d")
    if module.params['asfilename'] is not None:
        punchcmds_string.append("-N")
        punchcmds_string.append(module.params['asfilename'])
    if module.params['fileclass'] is not None:
        punchcmds_string.append("-C")
        punchcmds_string.append(module.params['fileclass'])
    else:
        punchcmds_string.append("-C")
        punchcmds_string.append('X')
    punchcmds_string.append("-r")
    punchcmds_string.append("-u")
    punchcmds_string.append(module.params['name'])
    punchcmds_string.append(module.params['filename'])

    smcli_results = module.run_command(punchcmds_string, check_rc=True)

    result['return_stdout'] = smcli_results[1]
    result['return_stderr'] = smcli_results[2]
    result['return_code'] = smcli_results[0]

    if result['return_code'] == 0:
        result['changed'] = True
        module.exit_json(**result)

    if result['return_code'] >= 1:
        notreally_errs = ["Image or profile name already defined"]
        # notreally_errs is a list of VM error messages that are OK within this context
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
        errormsg = "failing message from vmur is: " + str(result['return_stdout'])
        module.fail_json(errormsg, **result)

    errormsg = "unknown return code from vmur: " + str(result['return_code'])
    result['return_stderr'] = ["how did we get here???"]
    module.fail_json(errormsg, **result)


def main():
    run_module()


if __name__ == '__main__':
    main()
