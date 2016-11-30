#!/bin/bash
set -e
cd "$( dirname "${BASH_SOURCE[0]}" )"
sudo ifdown enp0s4 2&>1 >> /dev/null /dev/null || true
sudo ifdown enp0s6 2&>1 >> /dev/null /dev/null || true
sudo cp ../templates/ifcfg-* /etc/network/interfaces.d/
sudo ifup enp0s4
sudo ifup enp0s6