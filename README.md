# zvm_ansible
a set of ansible modules for managing z/VM via SMAPI and zthin. 
these modules requre a Linux virtual machine running on the target z/VM LPAR. 
the Linux target virtual machine must be authorized to issue SMAPI commands. 
the Linux target virtual machine must have Feilong zthin installed it uses the smcli command.  

## design

This repo is just the collection of modules. The sample playbooks are at https://github.com/IBM/zvm_ansible

these modules are kinda a 1:1 wrapper around a pair of create/delete SMAPI calls

zvm_clone_disk.py : Image_Disk_Copy_DM  
zvm_minidisk.py : Image_Disk_Create_DM / Image_Disk_Delete_DM  
zvm_startstop_user.py : Image_Activate / Image_Deactivate  
zvm_update_user.py : Image_Definition_Update_DM  
zvm_user.py : Image_Create_DM / Image_Delete_DM  

these modules are wrappers around some VM card reader/punch management tools 

zvm_fileto_reader.py : vmur punch command to send a file to a target machine's RDR  
zvm_reader_empty.py : vmcp purge command to remove all files from a target machine's RDR  
zvm_startstop_user.py : vmcp xautolog command to start a virtual machine with the IPL devno argument  

## requirements
z/VM SMAPI must be configured and working, as well as a z/VM directory manager  
each z/VM system needs a Linux virtual machine running with permissions to use SMAPI as well as some greater than usual access. We call these linux machines the "Management Access Point" or MAPs - and each one is numbered to go with the z/VM system it serves - so z/VM LPAR LTICVMA has Linux MAPVMA, z/VM LPAR LTICVM1 has Linux MAPVM1, and so on. 

Our Linux MAP systems have class D in addition to G so that they can manage the rdr files for linux systems, as well as the ability to force and xautolog arbitrary systems. We did not want to give class A to them though, so instead we added the class A actions of the XAUTOLOG and FORCE commands to a new privclass T and gave our Linux class T also. 

Our z/VM SYSTEM CONFIG has the following to set up privclass T

    MODIFY CMD XAUTOLOG             IBMCLASS A PRIVCLAS AT
    MODIFY CMD FORCE                IBMCLASS A PRIVCLAS AT

each MAP linux system has zthin from Feilong installed and available in /opt/zthin
Specifically we need the smcli binary since we use that to talk to SMAPI

ref: https://cloudlib4zvm.readthedocs.io/en/latest/quickstart.html#installation  
ref: https://github.com/openmainframeproject/feilong  
ref: https://openmainframeproject.org/projects/feilong  

If you are also an ICIC user you can target the "Compute" Linux machine for each z/VM LPAR since it also uses smcli to talk to SMAPI, you don't need an additional machine. OOohh thats a good point - you can also follow the ICIC docs for "Setting up z/VM" at https://www.ibm.com/docs/en/cic/1.2.0?topic=environment-setting-up-zvm for guidance on getting z/VM enabled for ICIC and/or zvm_ansible_collection 

Once you have z/VM enabled , and Feilong installed on your Linux guest, you can verify its working correctly by issuing a smcli command similar to the following:

```
smcli Image_Query_DM -T OP1
```

Which should return the directory entry of the target virutal machine: 

```
IDENTITY OP1      AUTOONLY   32M   32M ABCDEFG
INCLUDE IBMDFLT
BUILD ON LTICVM1 USING SUBCONFIG OP1-1
BUILD ON LTICVM3 USING SUBCONFIG OP1-2
BUILD ON LTICVM6 USING SUBCONFIG OP1-3
BUILD ON LTICVM7 USING SUBCONFIG OP1-4
BUILD ON LTICVMA USING SUBCONFIG OP1-5
BUILD ON LTICVMB USING SUBCONFIG OP1-6
BUILD ON LTICVMC USING SUBCONFIG OP1-7
BUILD ON LTICVMD USING SUBCONFIG OP1-8
AUTOLOG AUTOLOG1 MAINT
ACCOUNT IBM
MACH ESA
IPL 190
```

Having verified that - now - on the Linux machine where you plan to run your playbooks you have to get the module collection installed.  

1. git clone https://github.com/IBM/zvm_ansible_collection.git
2. cd zvm_ansible_collection
3. ansible-galaxy collection build --output-path ..
4. ansible-galaxy collection install ../ibm-zvm_ansible-V.V.V.tar.gz

The above 'building' nonsense will go away once I'm able to get this collection into shape such that the ansible community will accept it into galaxy - then you just install it directly without having to clone/build first. 

Uhh... this probably needs a picture. I'll get one done up and put it in here. 



## limitations

SMAPI does not provide an API to manage the vlan tag of a NICDEF statement.  
SMAPI does not provide an API to manage CRYPTO statements for APVIRT or to Dedicate a domain. 

due to the above we have to either:  
a) do full directory parsing and replacement with jinja templated directory stubs   
b) craft a set of prototype directory entries that provide all possible required VLANs and CRYPTO configs     

we felt like B was kinda gross and we'd eventually end up doing A anyway - so thats what our examples show. The zvm_user.py module supports creating virtual machines from a prototype though so feel free to use that if it works for you. 

SMAPI does not provide an API to IPL a virtual machine from a specific device: you can effectively `XAUTOLOG SOMEDUDE` but you cannot `XAUTOLOG SOMEDUDE IPL 00C`. If you need to direct the IPL of a virtual machine you can do so by telling zvm_startstop_user.py viaSMAPI=no and setting a device for IPL=<dev>. This does require your Linux system have either class A or the above modified privclass enabled.


Some Debugging tips: 

do to the nature of ansible calling SMAPI which in turn calls DIRMAINT sometimes error messages you get back to your ansible driving machine are ... less than helpful.  For example if you use the zvm_update_user.py to try to set the Default Memory larger than the Maximum Memory you would see an error like this in your ansible return json: 

    <mapvma.fpet.pokprv.stglabs.ibm.com> (0, b'', b'')
    fatal: [jtu0001.fpet.pokprv.stglabs.ibm.com]: FAILED! => {
        "changed": false,
        "invocation": {
            "module_args": {
                "accounting": null,
                "dirfile": "/tmp/jtu001.direct",
                "erasemode": null,
                "exists": true,
                "name": "jtu001",
                "newpass": null,
                "prototype": null
            }
        },
        "msg": "failing return code from smcli is: 1",
        "reason_code": -9,
        "return_code": 1,
        "return_stderr": [],
        "return_stdout": [
            "Defining jtu001 in the directory... ",
            "Failed",
            "  Return Code: 596",
            "  Reason Code: 6213",
            "  Description: ULGSMC5596E Internal directory manager error - product-specific return code : 6213",
            "  API issued : Image_Create_DM"
        ]
    }

RC 596 RS 6213 means "Dirmaint got some CP error when it tried to do something examine DIRMAINT console messages at this time for what the deal is" 

which can look like so for default memory being larger than max memory:

    14:00:06 DIRMAINT LTICVM1. - 2023/07/19; T=0.01/0.01 14:00:06
    14:00:06 DVHREQ2290I Request is: REQUEST 107659 ASUSER VSMWORK2 ADD JTU001
    14:00:06 DVHREQ2288I REQUEST=107659 RTN=DVHREQ MSG=2288 FMT=01 SUBS= ADD ,
    14:00:06 DVHREQ2288I CONT=JTU001 * VSMWORK2
    14:00:06 DVHBXX6213E REQUEST=107659 RTN=DVHBXX MSG=6213 FMT=01 SUBS= 1 2 ,
    14:00:06 DVHBXX6213E CONT=3 4 5 6 7 8  z/VM USER DIRECTORY CREATION PROGRAM - ,
    14:00:06 DVHBXX6213E CONT=VERSION 7 RELEASE 3.0
    14:00:06 DVHBXX6213E REQUEST=107659 RTN=DVHBXX MSG=6213 FMT=01 SUBS= 1 2 ,
    14:00:06 DVHBXX6213E CONT=3 4 5 6 7 8  HCPDIR750I RESTRICTED PASSWORD FILE NOT,
    14:00:06 DVHBXX6213E CONT= FOUND
    14:00:06 DVHBXX6213E REQUEST=107659 RTN=DVHBXX MSG=6213 FMT=01 SUBS= 1 2 ,
    14:00:06 DVHBXX6213E CONT=3 4 5 6 7 8  HCPDIR1776E DEFAULT STORAGE SIZE EXCEED,
    14:00:06 DVHBXX6213E CONT=S MAXIMUM STORAGE SIZE FOR USER JTU001.
    14:00:06 DVHBXX6213E REQUEST=107659 RTN=DVHBXX MSG=6213 FMT=01 SUBS= 1 2 ,
    14:00:06 DVHBXX6213E CONT=3 4 5 6 7 8  EOJ DIRECTORY NOT UPDATED
    14:00:06 DVHADD3212E REQUEST=107659 RTN=DVHADD MSG=3212 FMT=01 SUBS= 2 EX,
    14:00:06 DVHADD3212E CONT=EC DVHBBXXA U
    14:00:06 DVHREQ2289E REQUEST=107659 RTN=DVHREQ MSG=2289 FMT=02 SUBS= 3212,
    14:00:06 DVHREQ2289E CONT= ADD JTU001 *
    
