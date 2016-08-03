.. This work is licensed under a Creative Commons Attribution 4.0 International
.. License. .. http://creativecommons.org/licenses/by/4.0 ..
.. (c) Tim Irnich and Nikolas Hermanns, Ericsson AB

Introduction
============

This document provides guidelines on how to install and configure the
os-odl_l2_bgpvpn_ha and os-odl_l2_bgpvpn_ha scenarios of OPNFV including
required software and hardware configurations.

Description of bgpvpn scenarios
Internal transport tunnel mesh
Install Neutron BGPVPN additions (networking-bgpvpn)
Neutron odl additions (networking-odl)
install and configure Quagga (incl. config on ODL side)
configure OVS to connect to ODL and set up the right bridges (network architecture)
set up iptables to allow connections between OVS and ODL
set up HA proxy so that ODL can be reached

