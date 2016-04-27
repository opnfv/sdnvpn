===============================================================================
OPNFV Release Note for the Brahmaputra.3.0 release of OPNFV for SDN VPN feature
===============================================================================

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
SDN VPN and ODL together. Make use of deployment scenarios including the SDNVPN feature.

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
| **Repo/tag**                         | brahmaputra.3.0                      |
|                                      |                                      |
+--------------------------------------+--------------------------------------+
| **Release designation**              | Brahmaputra second stable release    |
|                                      |                                      |
+--------------------------------------+--------------------------------------+
| **Release date**                     | March 28, 2016                       |
|                                      |                                      |
+--------------------------------------+--------------------------------------+
| **Purpose of the delivery**          | Including ODL bugfixes               |
|                                      |                                      |
+--------------------------------------+--------------------------------------+

Version change
--------------

Compared to the Brahmaputra base release, a new version of ODL including several critical
bugfixes is deployed.

Module version changes
~~~~~~~~~~~~~~~~~~~~~~
ODL has been upgraded to Beryllium SR1. On top of Beryllium SR1, a number of bugfix patches
are applied which will be contained in Beryllium SR2. The deployment procedure has been
enhanced to take care of previously required manual post-deployment configuration.

Document changes
~~~~~~~~~~~~~~~~
A slight readability improvement to the user guide has been made.

Reason for version
------------------

Feature additions
~~~~~~~~~~~~~~~~~

SDN VPN adds the possibility to create and associate BGP/MPLS based Virtual Private Networks (VPNs)
through the OpenStack Neutron BGPVPN API extension.

No new features are added in Brahmaputra.3.0

Bug corrections
~~~~~~~~~~~~~~~

Several bugs in ODL VPN Service have been fixed in this release.

Deliverables
------------

Software deliverables
~~~~~~~~~~~~~~~~~~~~~

- Fuel plugin for OpenStack BGPVPN
- Changes to ODL Fuel plugin to activate VPN Service Karaf feature
- Integration of VPN Service functional tests and BGPVPN API tests into Functest framework

Documentation deliverables
~~~~~~~~~~~~~~~~~~~~~~~~~~

- Paragraph on SDN VPN feature for platform overview

- Configuration guide

- User guide

- Release noes (this document)

Known Limitations, Issues and Workarounds
=========================================

System Limitations
------------------

The currently deployed system does not contain a BGP stack and hence is limited to
providing connectivity within the domain controlled by one ODL instance (e.g.
intra-DC communication). Addition of an open source BGP stack is planned for the
Colorado release.

Feature specific Yardstick test cases have not been implemented, we plan to add
these in Colorado

Known issues
------------

The ODL VPN Service does not implement Floating IP, which is used extensively by Yardstick
to run generic system tests, which do currently not pass for this reason.

Workarounds
-----------

Manual configuration of VPN Service internal transport between multiple compute nodes is needed
to enable inter-node connectivity.

Test results
============

The deployment scenarios have successfully deployed in OPNFV CI many times and all Functest tests
(general and feature specific) are passing.

References
==========
