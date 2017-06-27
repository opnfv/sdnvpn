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

#Install and start Opendaylight Carbon
apt-get --yes --force-yes update 
apt-get --yes --force-yes install default-jre
wget https://nexus.opendaylight.org/content/repositories/public/org/opendaylight/integration/distribution-karaf/0.6.1-Carbon/distribution-karaf-0.6.1-Carbon.tar.gz
tar xvfz distribution-karaf-0.6.1-Carbon.tar.gz 
cd /distribution-karaf-0.6.1-Carbon/bin/
./start
sleep 100
./client -h 127.0.0.1 "feature:install odl-netvirt-openstack"

# Download quagga/zrpc rpms
cd /root
wget https://wiki.opnfv.org/download/attachments/6827916/quagga-ubuntu.tar.gz
tar xzf quagga-ubuntu.tar.gz
cd /root/quagga
packages=$(ls |grep -vE 'debuginfo|devel|contrib')
dpkg -i $packages

BGPD_CONFIG_LOCATION="/opt/quagga/etc/bgpd.conf"
touch /opt/quagga/etc/vtysh.conf
VTYSH_CONFIG_FILE="/opt/quagga/etc/vtysh.conf"
touch /opt/quagga/var/log/quagga/bgpd.log
BGPD_LOG_FILE="/opt/quagga/var/log/quagga/bgpd.log"

touch $BGPD_LOG_FILE
chown quagga:quagga $BGPD_LOG_FILE

cat <<CATEOF > $BGPD_CONFIG_LOCATION
! -*- bgp -*-

hostname bgpd
password sdncbgpc

router bgp 100
 bgp router-id ${OWN_IP}
 neighbor ${NEIGHBOR_IP} remote-as 100
 no neighbor ${NEIGHBOR_IP} activate
 vrf 18:18
  rd 18:18
  rt import 88:88
  rt export 88:88
 exit

!
 address-family vpnv4 unicast
 neighbor ${NEIGHBOR_IP} activate
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

#Start zrpcd and enable bgp daemon
cd /distribution-karaf-0.6.1-Carbon/bin/
/opt/quagga/etc/init.d/zrpcd start
./client -h 127.0.0.1 "bgp-connect -p 7644 -h 127.0.0.1 add"
./client -h 127.0.0.1 "odl:configure-bgp -op start-bgp-server --as-num 100 --router-id $OWN_IP"

# Quagga is already installed to run as well in setups without inet
# dns fix
# echo "nameserver 8.8.8.8" > /etc/resolvconf/resolv.conf.d/head
# resolvconf -u

pgrep bgpd
pgrep zebra

# Checking for accepted BGP routes- Route exchange subcase
while true; do
accepted_routes_list=$(/opt/quagga/bin/vtysh -c 'show ip bgp neighbor' | grep 'accepted prefixes' | awk '{print $1}')
status="KO"
for i in $accepted_routes_list; do
if [ $i -gt "0" ]; then
status="OK"
sleep 1
fi
# Print "Routes: KO" if no routes where accepted else print "Routes: OK"
echo "Routes: $status"
done
sleep 1
done
