# zvm_ansible_collection
a set of ansible modules for managing z/VM via SMAPI and zthin. 
these modules requre a Linux virtual machine running on the target z/VM LPAR. 
the Linux target virtual machine must be authorized to issue SMAPI commands. 
the Linux target virtual machine must have Feilong zthin installed it uses the smcli command.  

## design

This repo is just the collection of modules. The sample playbooks and documentation are at https://github.com/IBM/zvm_ansible

these modules are kinda a 1:1 wrapper around a pair of create/delete SMAPI calls

zvm_clone_disk.py : Image_Disk_Copy_DM  
zvm_minidisk.py : Image_Disk_Create_DM / Image_Disk_Delete_DM  
zvm_startstop_user.py : Image_Activate / Image_Deactivate  
zvm_update_user.py : Image_Definition_Update_DM  
zvm_user.py : Image_Create_DM / Image_Delete_DM  
zvm_dedicate_dev.py : Image_Device_Dedicate_DM / Image_Device_Undedicate_DM

these modules are wrappers around some VM card reader/punch management tools 

zvm_fileto_reader.py : vmur punch command to send a file to a target machine's RDR  
zvm_reader_empty.py : vmcp purge command to remove all files from a target machine's RDR  
zvm_startstop_user.py : vmcp xautolog command to start a virtual machine with the IPL devno argument  

## installing

On the system where you will be running your playbooks:

1. git clone https://github.com/IBM/zvm_ansible_collection.git
2. cd zvm_ansible_collection
3. ansible-galaxy collection build --output-path ..
4. ansible-galaxy collection install ../ibm-zvm_ansible-V.V.V.tar.gz

The above 'building' nonsense will go away once I'm able to get this collection into shape such that the ansible community will accept it into galaxy - then you just install it directly without having to clone/build first. 


