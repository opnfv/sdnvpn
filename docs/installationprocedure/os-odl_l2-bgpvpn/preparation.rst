.. This work is licensed under a Creative Commons Attribution 4.0 International
.. License. .. http://creativecommons.org/licenses/by/4.0 ..
.. (c) Tim Irnich (Ericsson AB) and others

Preparing your host to install Fuel by script
=================================================
.. Not all of these options are relevant for all scenario's.  I advise following the
.. instructions applicable to the deploy tool used in the scenario.

Before starting the installation of the <scenario> scenario some preparation of the
machine that will host the Fuel VM must be done.

Installation of required packages
---------------------------------
To be able to run the installation of the basic opnfv fuel installation the
Jumphost (or the host which serves the VMs for the virtual deployment) needs to
install the following packages:
::

 sudo apt-get install -y git make curl libvirt-bin libpq-dev qemu-kvm \
                         qemu-system tightvncserver virt-manager sshpass \
                         fuseiso genisoimage blackbox xterm python-pip \
                         python-git python-dev python-oslo.config \
                         python-pip python-dev libffi-dev libxml2-dev \
                        libxslt1-dev libffi-dev libxml2-dev libxslt1-dev \
                        expect curl python-netaddr p7zip-full

 sudo pip install GitPython pyyaml netaddr paramiko lxml scp \
                  python-novaclient python-neutronclient python-glanceclient \
                  python-keystoneclient debtcollector netifaces enum

Download the source code and artifact
-------------------------------------
To be able to install the scenario os-odl_l2-bgpvpn one can follow the way
CI is deploying the scenario.
First of all the opnfv-fuel repo needs to be cloned:
::

 git clone ssh://<user>@gerrit.opnfv.org:29418/fuel

This command downloads the whole repo fuel. We need now to switch it to
the stable Brahmaputra branch:
::

 cd fuel
 git checkout stable/brahmaputra

Now download the appropriate OPNFV Fuel ISO into an appropriate folder:
::

 wget http://artifacts.opnfv.org/fuel/brahmaputra/opnfv-brahmaputra.3.0.iso

The ISO version may change.
Check https://www.opnfv.org/opnfv-brahmaputra-fuel-users to get the latest ISO.
