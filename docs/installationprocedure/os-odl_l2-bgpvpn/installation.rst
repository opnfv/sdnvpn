.. This work is licensed under a Creative Commons Attribution 4.0 International
.. License. .. http://creativecommons.org/licenses/by/4.0 ..
.. (c) Christopher Price (Ericsson AB) and others

Fuel installation and scenario deployment
================================================

This section describes the installation of the os-odl_l2-bgpvpn-ha or
os-odl_l2-bgpvpn-noha OPNFV reference platform stack across a server cluster.

Scenario Preparation
--------------------
dea.yaml and dha.yaml need to be copied and changed to the purpose of
the lap where you deploy.
Copy the full lap config from:
 <path-to-opnfv-fuel-repo>/deploy/config/labs/devel-pipeline/elx
 to <path-to-opnfv-fuel-repo>/deploy/config/labs/devel-pipeline/<your-lab-name>
Add at the bottom of dha.yaml:
 disks:
   fuel: 100G
   controller: 100G
   compute: 100G

 # Here the infrastructure VMs can be defined.
 # The entries are not mandatory! If it is left empty
 # the default defined in deploy/templates will
 # be used.
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

Check if dea.yaml contains all your needed changes.

Installation procedures
-----------------------

We describe several alternative procedures in the following.
Go to
 cd <opnfv-fuel-repo>/ci

Full automatic virtual deployment High Availablity Mode
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
 sudo bash ./deploy.sh -b file://<path-to-opnfv-fuel-repo>/config/ -l devel-pipeline -p <your-lab-name> -s os-odl_l2-bgpvpn-ha -i file://<path-to-fuel-iso>

Full automatic virtual deployment NO High Availablity Mode
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
 sudo bash ./deploy.sh -b file://<path-to-opnfv-fuel-repo>/config/ -l devel-pipeline -p <your-lab-name> -s os-odl_l2-bgpvpn-noha -i file://<path-to-fuel-iso>

Automatic Fuel installation and manual scenario deployment
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
 sudo bash ./deploy.sh -b file://<path-to-opnfv-fuel-repo>/config/ -l devel-pipeline -p <your-lab-name> -s os-odl_l2-bgpvpn-ha -i file://<path-to-fuel-iso> -e

With -e option the installer does not launch environment deployment, so
a user can do some modification before the scenario is realy deployed. Another interesting option is the -f option which deploys the scenario  on existing Fuel.
