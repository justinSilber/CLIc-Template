# CLIc-Template
CLIc (Command Line Interface chat) server and client. A personal project to learn more about Python, sockets, and get the hang of Ansible and Terraform. The Template repo comes without my personal config.

The idea behind this project was to use Python to build a chat client and server, apply TLS to that connection, and set up automated deployment to a Linode instance using Ansible and Terrform, running the the server in a Docker container, including the generation of LetsEncrypt TLS certificates and creation of Cloudflare DNS A record.

## Requirements
  1. Python3 (Confirmed client works with v. >=3.7.3)
  2. Ansible
  3. Terraform
  4. Linode account
  5. Cloudflare account
  6. A domain managed by the Cloudflare account
  7. pass (unix password manager)

## Instructions
In its current state the program has three main points of interface:
  1. client.py - The client software. Very simple, since I'm trying to get the server to do as much of the lifting as I can. So far tested on Linux and Windows, with Python 3 version 3.7.3 and up.
  2. clic-server.py - The server software. Due to the 'select' module will not run on Windows. Linux will work, and I haven't tested MacOS.
  3. deploy_clic.sh - A simple shell script used to launch the deployment. Takes one of three arguments:
      i. init   - Runs the script with 'terraform init'
     ii. plan   - Runs the script with 'terraform plan'
    iii. create - You guessed it, runs the script with 'terraform create'

By default the deployment is configured to create a Linode instance of type g6-nanode-1 in the us-west region running Ubuntu 20.04, then run this server in another Ubuntu 20.04 Docker container. Ubiquitous Ubuntu was chosen to make my life slightly easier while I got everything else working, at some point I may work to make things lighter and more specific to the needs of the software.

There are several config files that need editing. Merging them in to one is on my list, but I ran in to trouble with the different ways Ansible and Terraform parse single- and double-quotes so for now I just wanted to get things working. There are templates for secrets.yml and secrets.tfvars, just be sure to save yours with the correct name after filling them out. The main points to pay attention to:
  1. secrets.yml - Contains API keys and variables for setting passwords and DNS records *should be encrypted with Ansible Vault*
  2. /tf/secrets.tf - Contains similar info to secrets.yml, but formatted for Terraform. *should be encrypted with Ansible Vault*
  3. client.py - Mainly make sure that the hostname is pointing to the DNS hostname you're using for the server, as well as other vars if you've customized them.
  4. server.py - Can generally be left alone and will pull its IP and hostname automatically.
  5. ansible.cfg - You may want to customize this, particularly the location of your local SSH private key.

In addition to those config changes I highly recommend setting up the 'pass' unix password manager for this. You'll need to generate a GPG key if you don't have one you want to use; there are a bunch of tutorials that do a much better job of explaining this than I would. Within pass create a password named *ansible-vault* to use for your Ansible vault. When you run deploy_clic.sh it will ask you for the password of your GPG key then use the vault_pass.sh shell script to pull the Ansible Vault password from pass. This seemed to be the simplest solution to encrypting and decrypting multiple files. As a side note, this also seemed like the simplest way to deal with encrypting the tfvars file. It's a little clunky using Ansible to decrypt it at the start of the Terraform role and encrypt it again after, plus it can be an issue if Terraform fails before re-encryption, but the recommended encryption options for Terraform seemed way  overwrought for my current needs and I had trouble using Ansible to set environment variables that Terraform was happy with so this is the way until I figure out something better.

Within the config files there are a number of variables to configure with the specifics detailed in my templates. These include Linode API key, Cloudflare API key, your SSH public keys, and other info. After your config files and Ansible Vault are set up you'll want to run *ansible-vault encrypt secrets.yml* and *ansible-vault encrypt /tf/secrets.tfvars* to make sure they're encrypted when you start.

At this point you can run *./deploy_clic.sh init* to initialize Terraform, followed by *./deploy_clic.sh plan* and finally, if those are clear of errors, *./deploy_clic.sh create* to deploy the server. Once that is complete you can SSH in and take a look or just try launching the client.py client app and try chatting!

## To-Do List
As of right now I'm stoked to have gotten the basic functionality of everything working, along with some simple server controls. Here's my list of additional features I'm planning to implement, in no particular order:
  1. Better user help for the client
  2. Consistent message spacing on client
  3. Active user list on client-side
  4. Username database with password access
  5. Mod powers
  6. Ban list
  7. Replacing the inaccurate user counting by threads with psutil for active connections
  8. MFA for server access
  9. Unit tests
  10. CI/CD pipeline with Jenkins
  11. Rooms
  12. Checking for orphaned sessions

## Technical Debts of Gratitude
I owe the following people and sources for inspiration, learning, and the occasional cribbed code snippet on this project:

Marc Weisel (https://github.com/mweisel) for my first exposure to Ansible and Terraform through his GNS3 Azure deployment that also helped me earn my CCNA.
TechWithTim (@techwithtimm) for his socket programming tutorial that helped me wrap my head around sockets, and expanded on his basic server config.
This StreamHacker article by "Jacob" (https://streamhacker.com/2020/02/24/using-lastpass-with-ansible-vault/) that I adapted to use pass instead of LastPass
Rahul Rai (@rahulrai_in) for his excellent article on incorporating Terraform in to Ansible playbooks (https://thecloudblog.net/post/simplifying-terraform-deployments-with-ansible-part-2/)


