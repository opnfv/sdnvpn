.. This work is licensed under a Creative Commons Attribution 4.0 International License.
.. http://creativecommons.org/licenses/by/4.0
.. (c) Tim Irnich, (tim.irnich@ericsson.com) and others

Introduction
============
.. Describe the specific features and how it is realised in the scenario in a brief manner
.. to ensure the user understand the context for the user guide instructions to follow.

This document will provide an overview of how to work with the SDN VPN features in
OPNFV.  For a description of the scenarios and their provided capabilities refer to
the scenario description document:
http://artifacts.opnfv.org/colorado/sdnpvn/scenarios/os-odl_l2-bgpvpn/index.html

SDN VPN feature description
===========================
.. Describe the specific usage for <XYZ> feature.
.. Provide enough information that a user will be able to operate the feature on a deployed scenario.

The BGPVPN feature enables creation of BGP VPNs according to the OpenStack
BGPVPN blueprint at https://blueprints.launchpad.net/neutron/+spec/neutron-bgp-vpn.
In a nutshell, the blueprint defines a BGPVPN object and a number of ways
how to associate it with the existing Neutron object model, including a unique
definition of the related semantics. The BGPVPN framework supports a backend
driver model with currently available drivers for Bagpipe, OpenContrail, Nuage
and OpenDaylight.

Feature and API usage guidelines and example
============================================
.. Describe with examples how to use specific features, provide API examples and details required to
.. operate the feature on the platform.

For the details of using OpenStack BGPVPN API, please refer to the documentation
at http://docs.openstack.org/developer/networking-bgpvpn/.

Can we give a basic example here?  Pointing someone off to a generic document in reference to
this specific compilation of components feels a little like only half the job.  :)

Troubleshooting
===============

What? I thought this would work!
