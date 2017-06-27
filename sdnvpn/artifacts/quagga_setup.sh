#! /bin/bash

set -xe
sudo -i
# change the password because this script is run on a passwordless cloud-image
echo 'ubuntu:opnfv' | chpasswd

touch id_rsa_pub
echo "ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQC22MYIJF5ztM75/k9yz4sNud+zMaBHmzUEiaLmDVQ0Pn+7RTQmskqZWJyvpspTvFbM8xgfwkdAs/sDjnS4LxP6CEhHFxrVqIJIUD0MM3kRQerJoyzWxaUOwgrc0MFYUciMhUx6JY6pQBo7ijG100RX/B5jCBEwCC0BucMQDgyT5/WK2KDGOXRu20W6AqWszvXFs1ShzMVl68Z609yNgSl+0YL4jBvatQQGpa8lhRV3ChTW0OmD/EvnBt3fkW2gLrMFh3cpA4CC0D3TNaljiOgKuAiOIc/91jA7OH3lNMU4+TaR+ncYWkYVWwj3gmvkPRjKWJfeUH2p1BydwKmIAIP7 root@overcloud-novacompute-0"> id_rsa_pub
cp id_rsa_pub /home/ubuntu/.ssh/authorized_keys
chmod 644 /home/ubuntu/.ssh/authorized_keys

# Wait for a floating IP
# as a workaround to NAT breakage
sleep 100

# Variables to be filled in with python
NEIGHBOR_IP=%s
OWN_IP=%s
# directly access the instance from the external net without NAT
EXT_NET_MASK=%s

if [[ $(getent hosts | awk '{print $2}') != *"$(cat /etc/hostname | awk '{print $1}')"* ]]
then 
echo "127.0.1.1 $(cat /etc/hostname | awk '{print $1}')" | tee -a /etc/hosts
fi

quagga_int=''
for net_int in $(netstat -ia | awk 'NR>2{print $1}');
do
if [ -z "$(ifconfig | grep $net_int)" ]
then
quagga_int=$net_int
break
fi
done
if [ -z "$quagga_int" ]
then
echo 'No available network interface'
fi

ip link set $quagga_int up
ip addr add $OWN_IP/$EXT_NET_MASK dev $quagga_int

ZEBRA_CONFIG_LOCATION="/etc/quagga/zebra.conf"
DAEMONS_FILE_LOCATION="/etc/quagga/daemons"
BGPD_CONFIG_LOCATION="/etc/quagga/bgpd.conf"
BGPD_LOG_FILE="/var/log/bgpd.log"
VTYSH_LOCATION="/etc/quagga/vtysh.conf"

touch $BGPD_LOG_FILE
chown quagga:quagga $BGPD_LOG_FILE

chown quagga:quagga $DAEMONS_FILE_LOCATION
cat <<CATEOF > $DAEMONS_FILE_LOCATION
zebra=yes
bgpd=yes
ospfd=no
ospf6d=no
ripd=no
ripngd=no
isisd=no
babeld=no
CATEOF

touch $ZEBRA_CONFIG_LOCATION
chown quagga:quagga $ZEBRA_CONFIG_LOCATION

cp /usr/share/doc/quagga/examples/vtysh.conf.sample $VTYSH_LOCATION
chown quagga:quagga $VTYSH_LOCATION
chmod 640 $VTYSH_LOCATION

cat <<CATEOF > $BGPD_CONFIG_LOCATION
! -*- bgp -*-

hostname bgpd
password sdncbgpc

router bgp 100
 bgp router-id ${OWN_IP}
 exit

!
 address-family vpnv4 unicast
 exit-address-family
!
line vty
 exec-timeout 0 0
!
debug bgp events
debug bgp  updates
log file ${BGPD_LOG_FILE}
end
CATEOF

chown quagga:quagga $BGPD_CONFIG_LOCATION
service quagga restart
pgrep bgpd
pgrep zebra
