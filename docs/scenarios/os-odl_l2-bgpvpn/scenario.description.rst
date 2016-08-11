.. This work is licensed under a Creative Commons Attribution 4.0 International License.
.. http://creativecommons.org/licenses/by/4.0
.. (c) <optionally add copywriters name>

Introduction
============
.. In this section explain the purpose of the scenario and the types of capabilities provided

This document provides an outline of the os-odl_l2-bgpvpn scenarios of OPNFV including
guidelines and references to required installation, software and hardware configuration documents.

<To be completed, this outlines the basic content and flow>
Description of bgpvpn scenarios
Description of the internal transport tunnel mesh

Install Neutron BGPVPN additions (networking-bgpvpn)
Neutron odl additions (networking-odl)
install and configure Quagga (incl. config on ODL side)
configure OVS to connect to ODL and set up the right bridges (network architecture)
set up iptables to allow connections between OVS and ODL
set up HA proxy so that ODL can be reached

Scenario components and composition
===================================
.. In this section describe the unique components that make up the scenario,
.. what each component provides and why it has been included in order
.. to communicate to the user the capabilities available in this scenario.

<Where applicable and without copying the installation procedure in the install guides>
Describe Neutron BGPVPN additions (networking-bgpvpn)
Neutron odl additions (networking-odl)
Usage and the role of Quagga (incl. config on ODL side)
OVS and ODL specifics around setting up the right bridges (network architecture)
"" iptables to allow connections between OVS and ODL
"" HA proxy so that ODL can be reached

Scenario usage overview
=======================
.. Provide a brief overview on how to use the scenario and the features available to the
.. user.  This should be an "introduction" to the userguide document, and explicitly link to it,
.. where the specifics of the features are covered including examples and API's

When would I use this scenario, what value does it provide?  Refer to the userguide for details
of configuration etc...

Limitations, Issues and Workarounds
===================================
.. Explain scenario limitations here, this should be at a design level rather than discussing
.. faults or bugs.  If the system design only provide some expected functionality then provide
.. some insight at this point.

Are there places these basic procedures will not work.  Do we have constraints on the use of
Quagga that may change in the future?

References
==========

For more information on the OPNFV Colorado release, please visit
http://www.opnfv.org/colorado

