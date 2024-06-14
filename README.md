# zvm_ansible_collection
a set of ansible modules for managing z/VM via SMAPI and zthin. 
some of these modules requre a Linux virtual machine running on the target z/VM LPAR, some just require TCPIP connectivity to the target z/VM LPAR but then also require that the SMAPI port on z/VM TCPIP is SSL protected. 

## design

This repo is just the collection of modules. The sample playbooks and documentation are at https://github.com/IBM/zvm_ansible

### modules that must run on Linux on the target z/VM system

these modules are kinda a 1:1 wrapper around a pair of create/delete SMAPI calls. they all take advantage of smcli and implicit IUCV authorization.
the Linux target virtual machine must be authorized to issue SMAPI commands. 
the Linux target virtual machine must have Feilong zthin installed it uses the smcli command.  

zvm_clone_disk.py : Image_Disk_Copy_DM  
zvm_minidisk.py : Image_Disk_Create_DM / Image_Disk_Delete_DM  
zvm_startstop_user.py : Image_Activate / Image_Deactivate  
zvm_update_user.py : Image_Definition_Update_DM  
zvm_user.py : Image_Create_DM / Image_Delete_DM  
zvm_dedicate_dev.py : Image_Device_Dedicate_DM / Image_Device_Undedicate_DM

these modules are wrappers around some VM card reader/punch management tools. They don't use smcli internally, but require additional VM privclas beyond G

zvm_fileto_reader.py : vmur punch command to send a file to a target machine's RDR  
zvm_reader_empty.py : vmcp purge command to remove all files from a target machine's RDR  
zvm_startstop_user.py : vmcp xautolog command to start a virtual machine with the IPL devno argument  

### modules that can run anywhere that has TCPIP connectivity to the target z/VM system

Since these modules use TCPIP connectivity to converse with z/VM SMAPI and pass z/VM userids and passwords for authorization, the SMAPI port must be SSL protected on the z/VM side. The z/VM userid used for authorization also must be authorized to issue SMAPI commands. 

zvm_setshare.py : CP_SetShare - Local SMAPI extension, requires rexx/setshare.exec on target z/VM and setup to enable it in SMAPI
zvm_dirm_nicdef.py : Dirm_Nicdef - Local SMAPI extension, requires rexx/nicdef.exec on target z/VM and setup to enable it in SMAPI 


## installing

On the system where you will be running your playbooks:

1. git clone https://github.com/IBM/zvm_ansible_collection.git
2. cd zvm_ansible_collection
3. ansible-galaxy collection build --output-path ..
4. ansible-galaxy collection install ../ibm-zvm_ansible-V.V.V.tar.gz

The above 'building' nonsense will go away once I'm able to get this collection into shape such that the ansible community will accept it into galaxy - then you just install it directly without having to clone/build first. 


