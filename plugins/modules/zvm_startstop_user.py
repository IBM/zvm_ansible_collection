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
module: zvm_startstop_user

short_description: z/VM start and stop guest/user Ansible Module

version_added: "0.0.1"

description:
    an Ansible module starting and stopping z/VM virtual machines.
    One option is to use SMAPI, but SMAPI does not provide an API to direct a
    virtual machine to IPL from a specific device, nor does it allow to pass
    a 'first command' to a virtual machine. the z/VM XAUTOLOG command does allow
    that however, so we support both methods.

options:
    name:
        description: this is the target user to be started or stopped
        required: true
        type: str
    loggedon:
        description: kinda like "exists" but for virtual machine instantiation
        required: true
        type: bool
    viaSMAPI:
        description: are we using SMAPI or CP XAUTOLOG|FORCE to start/stop the target user
        type: bool
    IPLdev:
        description: what device should the virtual machine IPL/Boot from once it logs on ?
        type: str
    CMD:
        description: pass a command to the operating system as it starts
        type: str
    stoptime:
        description:
            if we are logging a virtual machine off how long should we allow the OS to
            complete its internal shutdown. Time is in seconds.
        type: int

author:
    - Jay Brenneman (@rjbrenn)
'''


EXAMPLES = r'''
# start one up via SMAPI
- name: starting
  zvm_startstop_user:
    name: LINUX02
    loggedon: true
    viaSMAPI: true

# start one with XAUTOLOG and ask it to IPL the card reader
- name: start rdr
  zvm_startstop_user:
    name: LINUX02
    loggedon: true
    viaSMAPI: false
    IPLdev: 00c

# stop one with very little waiting
- name: force
  zvm_startstop_user:
    name: LINUX02
    loggedon: false
    viaSMAPI: false
    stoptime: 2

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
    sample: "HCPAUT053E LARRY not in CP directory"
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
        loggedon=dict(type='bool', required=True),
        viaSMAPI=dict(type='bool', required=False),
        stoptime=dict(type='int', required=False),
        IPLdev=dict(type='str', required=False),
        CMD=dict(type='str', required=False)
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

    if module.params['loggedon']:
        # we are starting systems up
        # should we use SMAPI ?
        if module.params['viaSMAPI']:
            # we are starting systems using SMAPI
            smapi_up_cmd = []
            smapi_up_cmd.append("/opt/zthin/bin/smcli")
            smapi_up_cmd.append("Image_Activate")
            smapi_up_cmd.append("-T")
            smapi_up_cmd.append(module.params['name'])

            # check_rc=False because if we get rerun idempotently this may fail with 'already running'
            smcli_results = module.run_command(smapi_up_cmd, check_rc=False)
            result['return_stdout'] = smcli_results[1]
            result['return_stderr'] = smcli_results[2]
            result['return_code'] = smcli_results[0]
        else:
            # we are starting systems using XAUTOLOG
            xauto_up_cmd = []
            xauto_up_cmd.append("vmcp")
            xauto_up_cmd.append("xautolog")
            xauto_up_cmd.append(module.params['name'])
            if module.params['IPLdev'] is not None:
                xauto_up_cmd.append("IPL")
                xauto_up_cmd.append(module.params['IPLdev'])
            if module.params['CMD'] is not None:
                xauto_up_cmd.append("CMD")
                xauto_up_cmd.append(module.params['CMD'])

            # check_rc=False because if we get rerun idempotently this may fail with 'already running'
            vmcp_results = module.run_command(xauto_up_cmd, check_rc=False)
            result['return_stdout'] = vmcp_results[1]
            result['return_stderr'] = vmcp_results[2]
            result['return_code'] = vmcp_results[0]
    else:
        # we are shutting systems down
        # should we use SMAPI ?
        if module.params['viaSMAPI']:
            # we are shutting doen systems using SMAPI
            smapi_down_cmd = []
            smapi_down_cmd.append("/opt/zthin/bin/smcli")
            smapi_down_cmd.append("Image_Deactivate")
            smapi_down_cmd.append("-T")
            smapi_down_cmd.append(module.params['name'])
            if module.params['stoptime'] is not None:
                smapi_down_cmd.append("-f")
                smapi_down_cmd.append(str(module.params['stoptime']))

            # check_rc=False because if we get rerun idempotently this may fail with 'not running'
            smcli_results = module.run_command(smapi_down_cmd, check_rc=False)
            result['return_stdout'] = smcli_results[1]
            result['return_stderr'] = smcli_results[2]
            result['return_code'] = smcli_results[0]
        else:
            # we are shutting down systems using FORCE
            force_dn_cmd = []
            force_dn_cmd.append("vmcp")
            force_dn_cmd.append("force")
            force_dn_cmd.append(module.params['name'])
            if module.params['stoptime'] is not None:
                force_dn_cmd.append("within")
                force_dn_cmd.append(str(module.params['stoptime']))

            # check_rc=False because if we get rerun idempotently this may fail with 'not running'
            vmcp_results = module.run_command(force_dn_cmd, check_rc=False)
            result['return_stdout'] = vmcp_results[1]
            result['return_stderr'] = vmcp_results[2]
            result['return_code'] = vmcp_results[0]

    if result['return_code'] == 0:
        result['changed'] = True
        module.exit_json(**result)

    if result['return_code'] >= 1:
        notreally_errs = ["Image already active", "HCPUSO045E", "not logged on"]
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
        for j in notreally_errs:
            if result['return_stdout'].find(j) != -1:
                noterror_count += 1
        if noterror_count > 0:
            # optimistically guessing this is not an error condition
            # it might still actually be an error condition if there is a real error among the not-errors
            # will figure that out later if it ends up happening
            # exit no error
            result['return_stdout'] += ">>skipping an error because its probably OK in this situation<<"
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
