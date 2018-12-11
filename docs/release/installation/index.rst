.. This work is licensed under a Creative Commons Attribution 4.0 International License.
.. SPDX-License-Identifier: CC-BY-4.0
.. (c) OPNFV, Ericsson AB and others.

============================
SDN VPN feature installation
============================

Hardware requirements
=====================

The SDNVPN scenarios can be deployed as a bare-metal or a virtual
environment on a single host.


Bare metal deployment on Pharos Lab
-----------------------------------

Hardware requirements for bare-metal deployments of the OPNFV
infrastructure are specified by the Pharos project. The Pharos project
provides an OPNFV hardware specification for configuring your hardware
at: http://artifacts.opnfv.org/pharos/docs/pharos-spec.html.


Virtual deployment on a single server
-------------------------------------

To perform a virtual deployment of an OPNFV scenario on a single host,
that host has to meet the hardware requirements outlined in the <missing
spec>.

When ODL is used as an SDN Controller in an OPNFV virtual deployment, ODL is
running on the OpenStack Controller VMs. It is therefore recommended to
increase the amount of resources for these VMs. ODL is running in a separate
VM in case of Fuel, thus, the below recommendation is not applicable when
deploying the scenario on Fuel installer.

Our recommendation is to have 2 additional virtual cores and 8GB
additional virtual memory on top of the normally recommended
configuration.

Together with the commonly used recommendation this sums up to:
::

 6 virtual CPU cores
 16 GB virtual memory

The installation section below has more details on how to configure this.

Installation using Fuel installer
=================================

Preparing the host to install Fuel by script
============================================
.. Not all of these options are relevant for all scenarios. I advise following the
.. instructions applicable to the deploy tool used in the scenario.

Before starting the installation of the os-odl-bgpnvp scenario some
preparation of the machine that will host the Fuel VM must be done.


Installation of required packages
---------------------------------
To be able to run the installation of the basic OPNFV fuel installation the
Jumphost (or the host which serves the VMs for the virtual deployment) needs to
install the following packages:
::

 sudo apt-get install -y git make curl libvirt-bin qemu-kvm \
                         python-pip python-dev

Download the source code and artifact
-------------------------------------
To be able to install the scenario os-odl-bgpvpn one can follow the way
CI is deploying the scenario.
First of all the opnfv-fuel repository needs to be cloned:
::

 git clone ssh://<user>@gerrit.opnfv.org:29418/fuel

To check out a specific version of OPNFV, checkout the appropriate branch:
::

 cd fuel
 git checkout stable/gambia

Simplified scenario deployment procedure using Fuel
===================================================

This section describes the installation of the
os-odl-bgpvpn-noha OPNFV reference platform stack across a server cluster
or a single host as a virtual deployment.

Installation procedures
-----------------------

We describe how to deploy the scenario with the use of deploy.sh script,
which is also used by the OPNFV CI system. Script can be found in the Fuel
repository.

Full automatic virtual deployment NO High Availability Mode
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The following command will deploy the SDNVPN scenario in its non-high-availability flavor.
::

 ci/deploy.sh -l <lab_name> \
              -p <pod_name> \
              -b <URI to configuration repo containing the PDF file> \
              -s os-odl-bgpvpn-noha \
              -D \
              -S <Storage directory for disk images> |& tee deploy.log

Virtual deployment using Apex installer
=======================================

Prerequisites
-------------

For Virtual Apex deployment a host with Centos 7 is needed. This installation
was tested on centos-release-7-2.1511.el7.centos.2.10.x86_64 however any other
Centos 7 version should be fine.

Build and Deploy
----------------

Download the Apex repo from opnfv gerrit and checkout stable/gambia:
::

 git clone ssh://<user>@gerrit.opnfv.org:29418/apex
 cd apex
 git checkout stable/gambia

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

Edit the script and change the scenario to os-odl-bgpvpn-noha.yaml. More scenraios can be found:
./apex/config/deploy/

Execute the script in a own screen process:
::

 yum install -y screen
 screen -S deploy
 bash ./simple_deploy.sh

Accessing the undercloud
^^^^^^^^^^^^^^^^^^^^^^^^
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


Access the overcloud hosts
^^^^^^^^^^^^^^^^^^^^^^^^^^
On the undercloud:
::

 # . stackrc
 # nova list
 # ssh heat-admin@<ip-of-host>
 -> there is no password the user has direct sudo rights.
