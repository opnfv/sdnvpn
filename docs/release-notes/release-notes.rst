===========================================================================
OPNFV Release Note for the Brahmaputra release of OPNFV for SDN VPN feature
===========================================================================

License
=======

This work is licensed under a Creative Commons Attribution 4.0 International
License. .. http://creativecommons.org/licenses/by/4.0 ..
(c) Tim Irnich (Ericsson) and others

Abstract
========

This document comprises the release notes for the SDN VPN feature contained in the Brahmaputra 
release of OPNFV.

Important notes
===============

In the Brahmaputra release, SDN VPN only supports ODL as a backend. Make sure to always deploy 
SDN VPN and ODL together. 

Summary
=======

SDN VPN adds the possibility to create and associate BGP/MPLS based Virtual Private Networks (VPNs) 
through the OpenStack Neutron BGPVPN API extension. 

Release Data
============

+--------------------------------------+--------------------------------------+
| **Project**                          | sdnvpn                               |
|                                      |                                      |
+--------------------------------------+--------------------------------------+
| **Repo/tag**                         | brahmaputra.1.0                      |
|                                      |                                      |
+--------------------------------------+--------------------------------------+
| **Release designation**              | Brahmaputra base release             |
|                                      |                                      |
+--------------------------------------+--------------------------------------+
| **Release date**                     | February 25 2016                     |
|                                      |                                      |
+--------------------------------------+--------------------------------------+
| **Purpose of the delivery**          | Brahmaputra base release             |
|                                      |                                      |
+--------------------------------------+--------------------------------------+

Version change
--------------

Brahmaputra is the first OPNFV release that contains the SDN VPN feature.

Module version changes
~~~~~~~~~~~~~~~~~~~~~~

Since this is the first release containing SDN VPN, there are no module version changes to report. 

Document changes
~~~~~~~~~~~~~~~~

All documentation is new and hence not changes to previous releases are to be reported. 

Reason for version
------------------

Feature additions
~~~~~~~~~~~~~~~~~

SDN VPN adds the possibility to create and associate BGP/MPLS based Virtual Private Networks (VPNs) 
through the OpenStack Neutron BGPVPN API extension. 

Bug corrections
~~~~~~~~~~~~~~~

No bugs have been reported during the Brahmaputra release cycle. 

Deliverables
------------

Software deliverables
~~~~~~~~~~~~~~~~~~~~~

- Fuel plugin for OpenStack BGPVPN
- Changes to ODL Fuel plugin to activate VPN Service Karaf feature
- Integration of VPN Service functional tests and BGPVPN API tests into Functest framework

Documentation deliverables
~~~~~~~~~~~~~~~~~~~~~~~~~~

- Platform overview

- Configuration guide 

- User guide

- Release notes (this document)

Known Limitations, Issues and Workarounds
=========================================

System Limitations
------------------

None known beyond the general system limitations of the base system. 

Known issues
------------

SDN VPN is known to deploy successfully in OPNFV CI but is not fully tested at release date. 
Patches to fix failing tests will occur early in the SR1 cycle. 

Workarounds
-----------

Manual configuration of VPN Service internal transport between multiple compute nodes is needed 
to enable inter-node connectivity. 

Test results
============

tests for SDN VPN have been integrated into Functest but have not been fully passing before release 
deadline. 

References
==========


