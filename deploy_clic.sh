#!/bin/bash
#deploy_clic.sh

case $1 in
"init")
    ansible-playbook clic_main.yml -e operation=init
    ;;
"create")
    ansible-playbook clic_main.yml -e operation=create
    ;;
"create-plan" | *)
    ansible-playbook clic_main.yml -e operation=plan
#    if [ ! -f "/tf/clicserv.tfplan" ]; then
#        (
#            cd tf
#            terraform show clicserv.tfplan
#        )
#    fi
#    ;;
esac
