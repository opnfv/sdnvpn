.. This work is licensed under a Creative Commons Attribution 4.0 International License.
.. http://creativecommons.org/licenses/by/4.0
.. (c) Tim Irnich, Nikolas Hermanns, Christopher Price and others

Introduction
============
.. Describe the specific features and how it is realised in the scenario in a brief manner
.. to ensure the user understand the context for the user guide instructions to follow.

This document will provide an overview of how to work with the SDN VPN features in
OPNFV.

SDN VPN feature description
===========================
.. Describe the specific usage for <XYZ> feature.
.. Provide enough information that a user will be able to operate the feature on a deployed scenario.

A high-level description of the scenarios is provided in this section.
For details of the scenarios and their provided capabilities refer to
the scenario description document:
http://artifacts.opnfv.org/danube/sdnpvn/scenarios/os-odl_l2-bgpvpn/index.html

The BGPVPN feature enables creation of BGP VPNs on the Neutron API according to the OpenStack
BGPVPN blueprint at https://blueprints.launchpad.net/neutron/+spec/neutron-bgp-vpn.
In a nutshell, the blueprint defines a BGPVPN object and a number of ways
how to associate it with the existing Neutron object model, as well as a unique
definition of the related semantics. The BGPVPN framework supports a backend
driver model with currently available drivers for Bagpipe, OpenContrail, Nuage
and OpenDaylight. The OPNFV scenario makes use of the OpenDaylight driver and backend
implementation through the ODL NetVirt project.

Hardware requirements
=====================

The SDNVPN scenarios can be deployed as a bare-metal or a virtual environment on a single host.

Bare metal deployment on Pharos Lab
-----------------------------------

Hardware requirements for bare-metal deployments of the OPNFV infrastructure are specified
by the Pharos project. The Pharos project provides an OPNFV hardware specification for
configuring your hardware at: http://artifacts.opnfv.org/pharos/docs/pharos-spec.html.

Virtual deployment hardware requirements
----------------------------------------

To perform a virtual deployment of an OPNFV scenario on a single host, that host has to
meet the hardware requirements outlined in the <missing spec>.

When ODL is used as an SDN Controller in an OPNFV virtual deployment, ODL is
running on the OpenStack Controller VMs. It is therefore recommended to
increase the amount of resources for these VMs.

Our recommendation is to have 2 additional virtual cores and 8GB additional virtual memory
on top of the normally recommended configuration.

Together with the commonly used recommendation this sums up to:
::

 6 virtual cores
 16 GB virtual memory

See in Installation section below how to configure this.

[FUEL] Preparing the host to install Fuel by script
============================================
.. Not all of these options are relevant for all scenarios.  I advise following the
.. instructions applicable to the deploy tool used in the scenario.

Before starting the installation of the os-odl_l2-bgpnvp scenario some preparation of the
machine that will host the Fuel VM must be done.

[FUEL] Installation of required packages
---------------------------------
To be able to run the installation of the basic OPNFV fuel installation the
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

[FUEL] Download the source code and artifact
-------------------------------------
To be able to install the scenario os-odl_l2-bgpvpn one can follow the way
CI is deploying the scenario.
First of all the opnfv-fuel repository needs to be cloned:
::

 git clone ssh://<user>@gerrit.opnfv.org:29418/fuel

This command downloads the whole repository fuel. To checkout a specific
version of OPNFV, checkout the appropriate branch:
::

 cd fuel
 git checkout stable/<colorado|danube>

Now download the corresponding OPNFV Fuel ISO into an appropriate folder from
the website
::
 https://www.opnfv.org/software/downloads/release-archives

Have in mind that the fuel repo version needs to map with the downloaded artifact.

[FUEL] Simplified scenario deployment procedure using Fuel
===================================================

This section describes the installation of the os-odl_l2-bgpvpn-ha or
os-odl_l2-bgpvpn-noha OPNFV reference platform stack across a server cluster
or a single host as a virtual deployment.

[FUEL] Scenario Preparation
--------------------
dea.yaml and dha.yaml need to be copied and changed according to the lab-name/host
where you deploy.
Copy the full lab config from:
::

 cp <path-to-opnfv-fuel-repo>/deploy/config/labs/devel-pipeline/elx \
    <path-to-opnfv-fuel-repo>/deploy/config/labs/devel-pipeline/<your-lab-name>

Add at the bottom of dha.yaml
::

 disks:
   fuel: 100G
   controller: 100G
   compute: 100G

 define_vms:
   controller:
     vcpu:
       value: 4
     memory:
       attribute_equlas:
         unit: KiB
       value: 16388608
     currentMemory:
       attribute_equlas:
         unit: KiB
       value: 16388608


Check if the default settings in dea.yaml are in line with your intentions
and make changes as required.

[FUEL] Installation procedures
-----------------------

We describe several alternative procedures in the following.
First, we describe several methods that are based on the deploy.sh script,
which is also used by the OPNFV CI system.
It can be found in the Fuel repository.

In addition, the SDNVPN feature can also be configured manually in the Fuel GUI.
This is described in the last subsection.

Before starting any of the following procedures, go to
::

 cd <opnfv-fuel-repo>/ci

[FUEL] Full automatic virtual deployment High Availablity Mode
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The following command will deploy the high-availability flavor of SDNVPN scenario os-odl_l2-bgpvpn-ha
in a fully automatic way, i.e. all installation steps (Fuel server installation, configuration,
node discovery and platform deployment) will take place without any further prompt for user input.
::

 sudo bash ./deploy.sh -b file://<path-to-opnfv-fuel-repo>/config/ -l devel-pipeline -p <your-lab-name> -s os-odl_l2-bgpvpn-ha -i file://<path-to-fuel-iso>

[FUEL] Full automatic virtual deployment NO High Availability Mode
******************************************************************

The following command will deploy the SDNVPN scenario in its non-high-availability flavor (note the
different scenario name for the -s switch). Otherwise it does the same as described above.
::

 sudo bash ./deploy.sh -b file://<path-to-opnfv-fuel-repo>/config/ -l devel-pipeline -p <your-lab-name> -s os-odl_l2-bgpvpn-noha -i file://<path-to-fuel-iso>

[FUEL] Automatic Fuel installation and manual scenario deployment
*****************************************************************

A useful alternative to the full automatic procedure is to only autodeploy the Fuel host and to run host selection, role assignment and SDNVPN scenario configuration manually.
::

 sudo bash ./deploy.sh -b file://<path-to-opnfv-fuel-repo>/config/ -l devel-pipeline -p <your-lab-name> -s os-odl_l2-bgpvpn-ha -i file://<path-to-fuel-iso> -e

With -e option the installer does not launch environment deployment, so
a user can do some modification before the scenario is really deployed.
Another interesting option is the -f option which deploys the scenario using an existing Fuel host.

The result of this installation is a fuel sever with the right config for
BGPVPN. Now the deploy button on fuel dashboard can be used to deploy the environment.
It is as well possible to do the configuration manuell.

[FUEL] Feature configuration on existing Fuel
*********************************************
If a Fuel server is already provided but the fuel plugins for Opendaylight, Openvswitch
and BGPVPN are not provided install them by:
::

 cd /opt/opnfv/
 fuel plugins --install fuel-plugin-ovs-*.noarch.rpm
 fuel plugins --install opendaylight-*.noarch.rpm
 fuel plugins --install bgpvpn-*.noarch.rpm

If plugins are installed and you want to update them use --force flag.

Now the feature can be configured. Create a new environment with "Neutron with ML2 plugin" and
in there "Neutron with tunneling segmentation".
Go to Networks/Settings/Other and check "Assign public network to all nodes". This is required for
features such as floating IP, which require the Compute hosts to have public interfaces.
Then go to settings/other and check "OpenDaylight plugin", "Use ODL to manage L3 traffic",
"BGPVPN plugin" and set the OpenDaylight package version to "5.2.0-1". Then you should
be able to check "BGPVPN extensions" in OpenDaylight plugin section.

Now the deploy button on fuel dashboard can be used to deploy the environment.

[APEX] Virtual deployment
=========================

[APEX] Prerequisites
********************
For Virtual Apex deployment a host with Centos 7 is needed. This installation
was tested on centos-release-7-2.1511.el7.centos.2.10.x86_64 however any other
Centos 7 version should be fine.

[APEX] Build and Deploy
=======================
Download the Apex repo from opnfv gerrit and checkout stable/danube:
::

 git clone ssh://<user>@gerrit.opnfv.org:29418/apex
 cd apex
 git checkout stable/danube

In apex/contrib you will find simple_deploy.sh:
::

 #!/bin/bash
 set -e
 apex_home=$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )/../
 export CONFIG=$apex_home/build
 export LIB=$apex_home/lib
 export RESOURCES=$apex_home/.build/
 export PYTHONPATH=$PYTHONPATH:$apex_home/lib/python
 $apex_home/ci/dev_dep_check.sh || true
 $apex_home/ci/clean.sh
 pushd $apex_home/build
 make clean
 make undercloud
 make overcloud-opendaylight
 popd
 pushd $apex_home/ci
 echo "All further output will be piped to $PWD/nohup.out"
 (nohup ./deploy.sh -v -n $apex_home/config/network/network_settings.yaml -d $apex_home/config/deploy/os-odl_l3-nofeature-noha.yaml &)
 tail -f nohup.out
 popd

This script will:

- "dev_dep_check.sh" install all required packages.
- "clean.sh" clean existing deployments
- "make clean" clean existing builds
- "make undercloud" building the undercloud image
- "make overcloud-opendaylight" build the overcloud image and convert that to a overcloud with opendaylight image
- "deploy.sh" deploy the os-odl_l3-nofeature-nohs.yaml scenario

Change the scenario to os-odl-bgpvpn-noha.yaml. More scenraios can be found:
./apex/config/deploy/

Execute the script in a own screen process:
::

 yum install -y screen
 screen -S deploy
 bash ./simple_deploy.sh

[APEX] Accessing the undercloud
*******************************
Determin the mac address of the undercloud vm:
::

 # virsh domiflist undercloud
 -> Default network
 Interface  Type       Source     Model       MAC
 -------------------------------------------------------
 vnet0      network    default    virtio      00:6a:9d:24:02:31
 vnet1      bridge     admin      virtio      00:6a:9d:24:02:33
 vnet2      bridge     external   virtio      00:6a:9d:24:02:35
 # arp -n |grep 00:6a:9d:24:02:31
 192.168.122.34           ether   00:6a:9d:24:02:31   C                     virbr0
 # ssh stack@192.168.122.34
 -> no password needed (password stack)

List overcloud deployment info:
::

 # source stackrc
 # # Compute and controller:
 # nova list
 # # Networks
 # neutron net-list

List overcloud openstack info:
::

 # source overcloudrc
 # nova list
 # ...


[APEX] Access the overcloud hosts
*********************************
On the undercloud:
::

 # . stackrc
 # nova list
 # ssh heat-admin@<ip-of-host>
 -> there is no password the user has direct sudo rights.


Feature and API usage guidelines and example [For Apex and Fuel]
============================================
.. Describe with examples how to use specific features, provide API examples and details required to
.. operate the feature on the platform.

For the details of using OpenStack BGPVPN API, please refer to the documentation
at http://docs.openstack.org/developer/networking-bgpvpn/.

Example
-------
In the example we will show a BGPVPN associated to 2 neutron networks. The BGPVPN
will have the import and export routes in the way that it imports its own Route. The outcome will be that vms sitting on these two networks will be able to have a full L3
connectivity.

Some defines:
::

 net_1="Network1"
 net_2="Network2"
 subnet_net1="10.10.10.0/24"
 subnet_net2="10.10.11.0/24"

Create neutron networks and save network IDs:
::

 neutron net-create --provider:network_type=local $net_1
 export net_1_id=`echo "$rv" | grep " id " |awk '{print $4}'`
 neutron net-create --provider:network_type=local $net_2
 export net_2_id=`echo "$rv" | grep " id " |awk '{print $4}'`

Create neutron subnets:
::

 neutron subnet-create $net_1 --disable-dhcp $subnet_net1
 neutron subnet-create $net_2 --disable-dhcp $subnet_net2

Create BGPVPN:
::

 neutron bgpvpn-create --route-distinguishers 100:100 --route-targets 100:2530 --name L3_VPN

Start VMs on both networks:
::

 nova boot --flavor 1 --image <some-image> --nic net-id=$net_1_id vm1
 nova boot --flavor 1 --image <some-image> --nic net-id=$net_2_id vm2

The VMs should not be able to see each other.

Associate to Neutron networks:
::

 neutron bgpvpn-net-assoc-create L3_VPN --network $net_1_id
 neutron bgpvpn-net-assoc-create L3_VPN --network $net_2_id

Now the VMs should be able to ping each other

Troubleshooting
===============
Check neutron logs on the controller:
::

 tail -f /var/log/neutron/server.log |grep -E "ERROR|TRACE"

Check Opendaylight logs:
::

 tail -f /opt/opendaylight/data/logs/karaf.log

Restart Opendaylight:
::

 service opendaylight restart
