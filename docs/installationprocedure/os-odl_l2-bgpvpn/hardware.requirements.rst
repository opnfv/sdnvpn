.. This work is licensed under a Creative Commons Attribution 4.0 International
.. License. .. http://creativecommons.org/licenses/by/4.0 ..
.. (c) Christopher Price (Ericsson AB) and others

Hardware requirements
=====================

Bare metal deployment on Pharos Lab
-----------------------------------

Hardware requirements for bare-metal deployments of the OPNFV infrastucture are specified
by the Pharos project. The Pharos project provides an OPNFV hardware specification for
configuring your hardware at: http://artifacts.opnfv.org/pharos/docs/pharos-spec.html.

Virtual deployment hardware requirements
----------------------------------------

To perform a virtual deployment of an OPNFV scenario on a single host, that host has to
meet the hardware requirements outlined in the <missing spec>.

Additional Hardware requirements
--------------------------------

Since Opendaylight is running on the controller it is recommended to give more resources
to the controller virtual machines. Our recommendation is to have +2 virtual cores and
 +8 virtual memory. Together with the commonly used recommendation this sums up to:
 4 virtual cores
 16 GB
See in Installation section how to configure this.

