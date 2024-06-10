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
module: zvm_dirm_nicdef

short_description: z/VM Dirmaint NICDEF command ansible module

version_added: "0.0.3"

description: Expose more of the Dirmaint NICDEF command syntax via SMAPI to permit ansible
    based management of options such as setting a MAC address or VLAN tags in the directory

options:
    name:
        description: this is the target who will have their NICDEF changed
        required: true
        type: str
    zvmhost:
        description: the hostname of the z/VM system where the target is running
        required: true
        type: str
    port:
        description: the TCP port number where SMAPI listens
        required: true
        type: int
    authuser:
        description: the z/VM user in VSMWORK1 AUTHLIST who is authorized to call this SMAPI function
        required: true
        type: str
    authpass:
        description: the z/VM users password for authuser
        required: true
        type: str
    devno:
        description: device number of the virtual network adapter
        required: true
        type: str
    nictype:
        description: device type - QDIO or HIPERsocket
        required: false
        type: str
        choices:
            - 'QDIO'
            - 'HIPER'
        default: 'HIPER'
    lanname:
        description: the name of the LAN or VSWITCH this virtual network adapter attaches to
        required: false
        type: str
    lanowner:
        description: the name of the LAN owning user if its a GuestLAN and is user owned.
            SYSTEM is the default for all VSWITCHes and can also be correct for some GuestLANs
        required: false
        type: str
        default: 'SYSTEM'
    vlanid:
        description: the VLAN ID string. It can be a single VLAN, a range, or a comma seperated list, or combination.
        required: false
        type: str
    macid:
        description: the last 6 characters of the MAC ID if using User Controlled MAC addresses
        required: false
        type: str
    exists:
        description: are we creating or deleting this NICDEV device?
        required: false
        type: bool
        default: true

author:
    - Jay Brenneman (@rjbrenn)
'''


EXAMPLES = r'''
- name: connect to 9DOTLAN2
  zvm_dirm_nicdef:
    name: JTU001
    zvmhost: 'lticvmc.example.net'
    port: 44444
    authuser: mapauth
    authpass: '{{ mappassw }}'
    devno: 888
    nictype: QDIO
    lanname: 9DOTLAN2
    vlanid: 2230
    exists: true
'''


RETURN = r'''
return_code:
    description: the integer return code from the SMAPI function.
    returned: always
    type: int
    sample: 0
reason_code:
    description: the integer reason code from the SMAPI function.
    returned: always
    type: int
    sample: 0
return_stdout:
    description: messages captured by the SMAPI function while running the requested command
    returned: always
    type: str
    sample: "DVHELD1190I Command EXECLOAD complete; RC= 0.\n
        Request number 20: DVHSAPI FOR JTU001 NICDEF 888 TYPE QDIO LAN SYSTEM 9DOTLAN2 V\n
        LAN 2230 \n
        resulted in the following 5 responses:\n
        DVHXMT1191I Your NICDEF request has been sent for processing to DIRMAINT\n
        DVHXMT1191I at LTICVM1 via DIRMSAT7.\n
        DVHREQ2288I Your NICDEF request for JTU001 at * has been accepted.\n
        DVHBIU3450I The source for directory entry JTU001 has been updated.\n
        DVHBIU3425I The next ONLINE will take place as scheduled.\n
        DVHREQ2289I Your NICDEF request for JTU001 at * has completed; with RC =\n
        DVHREQ2289I 0.\n
        DVHELD1190I Command EXECDROP complete; RC= 0.\n"
'''


from ansible.module_utils.basic import AnsibleModule
from ansible_collections.ibm.zvm_ansible.plugins.module_utils.psmapi import (call_client)


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
        exists=dict(type='bool', required=False, default='True')
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

    if module.params['exists']:
        cmd_string += " TYPE " + str(module.params['nictype'])
        if module.params['lanname'] is not None:
            cmd_string += " LAN " + module.params['lanowner'] + ' ' + module.params['lanname']
        if module.params['vlanid'] is not None:
            cmd_string += " VLAN " + module.params['vlanid']
        if module.params['macid'] is not None:
            cmd_string += " MACID " + module.params['macid']
    else:
        cmd_string += " DELETE"

    smcli_results = call_client(module.params['zvmhost'],
                                module.params['port'],
                                module.params['authuser'],
                                module.params['authpass'],
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
