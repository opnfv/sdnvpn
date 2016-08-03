.. This work is licensed under a Creative Commons Attribution 4.0 International
.. License. .. http://creativecommons.org/licenses/by/4.0 ..
.. (c) Christopher Price (Ericsson AB) and others

Fuel server installation and scenario deployment
================================================

.. Let's figure out how to structure this to highlight both virtual and
.. bare metal deployments.  I need some help from the scenrio  owners to get
.. that right.

This section describes the installation of the OPNFV installation
server (jumphost) as well as the deployment of the os-odl_l2-bgpvpn-ha or
os-odl_l2-bgpvpn-noha OPNFV reference platform stack across a server cluster.

Preparation
-----------

clone fuel repo
download opnfv iso
create dea.yaml and dha.yaml based on existing examples from FUel repo

Installation procedures
-----------------------

We describe several alternative procedures in the following.

Full automatic jumphost installation and deployment
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

call deploy.sh with scenario string

Automatic Fuel server installation and manual scenario deployment
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

call deploy.sh with -e option to only install FUel server i.e. no platform deployment
Log into Fuel web GUI and configure scenario options, including activation of SDN VPN feature
PXE boot compute nodes from Fuel server
Trigger deployment through web GUI

Update Fuel server settings without re-installation
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

In case of having to change the jumphost settings without having the reinstall the
whole jumphost, it is possible to call deploy-sh with the -f option, which will only
update the settings without reinstalling the host, saving a lot of time.

