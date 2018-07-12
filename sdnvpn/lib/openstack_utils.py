#!/usr/bin/env python
#
# jose.lausuch@ericsson.com
# valentin.boucher@orange.com
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the Apache License, Version 2.0
# which accompanies this distribution, and is available at
# http://www.apache.org/licenses/LICENSE-2.0
#

import base64
import logging
import os.path
import shutil
import sys
import time
import urllib

from keystoneauth1 import loading
from keystoneauth1 import session
from cinderclient import client as cinderclient
from heatclient import client as heatclient
from keystoneclient import client as keystoneclient
from neutronclient.neutron import client as neutronclient
from openstack import connection
from openstack import cloud as os_cloud

from functest.utils import env

logger = logging.getLogger(__name__)

DEFAULT_API_VERSION = '2'
DEFAULT_HEAT_API_VERSION = '1'


# *********************************************
#   CREDENTIALS
# *********************************************
class MissingEnvVar(Exception):

    def __init__(self, var):
        self.var = var

    def __str__(self):
        return str.format("Please set the mandatory env var: {}", self.var)


def get_os_connection():
    return connection.from_config()


def get_os_cloud():
    return os_cloud.openstack_cloud()


def is_keystone_v3():
    keystone_api_version = os.getenv('OS_IDENTITY_API_VERSION')
    if (keystone_api_version is None or
            keystone_api_version == '2'):
        return False
    else:
        return True


def get_rc_env_vars():
    env_vars = ['OS_AUTH_URL', 'OS_USERNAME', 'OS_PASSWORD']
    if is_keystone_v3():
        env_vars.extend(['OS_PROJECT_NAME',
                         'OS_USER_DOMAIN_NAME',
                         'OS_PROJECT_DOMAIN_NAME'])
    else:
        env_vars.extend(['OS_TENANT_NAME'])
    return env_vars


def check_credentials():
    """
    Check if the OpenStack credentials (openrc) are sourced
    """
    env_vars = get_rc_env_vars()
    return all(map(lambda v: v in os.environ and os.environ[v], env_vars))


def get_env_cred_dict():
    env_cred_dict = {
        'OS_USERNAME': 'username',
        'OS_PASSWORD': 'password',
        'OS_AUTH_URL': 'auth_url',
        'OS_TENANT_NAME': 'tenant_name',
        'OS_USER_DOMAIN_NAME': 'user_domain_name',
        'OS_PROJECT_DOMAIN_NAME': 'project_domain_name',
        'OS_PROJECT_NAME': 'project_name',
        'OS_ENDPOINT_TYPE': 'endpoint_type',
        'OS_REGION_NAME': 'region_name',
        'OS_CACERT': 'https_cacert',
        'OS_INSECURE': 'https_insecure'
    }
    return env_cred_dict


def get_credentials(other_creds={}):
    """Returns a creds dictionary filled with parsed from env
    """
    creds = {}
    env_vars = get_rc_env_vars()
    env_cred_dict = get_env_cred_dict()

    for envvar in env_vars:
        if os.getenv(envvar) is None:
            raise MissingEnvVar(envvar)
        else:
            creds_key = env_cred_dict.get(envvar)
            creds.update({creds_key: os.getenv(envvar)})

    if 'tenant' in other_creds.keys():
        if is_keystone_v3():
            tenant = 'project_name'
        else:
            tenant = 'tenant_name'
        other_creds[tenant] = other_creds.pop('tenant')

    creds.update(other_creds)

    return creds


def get_session_auth(other_creds={}):
    loader = loading.get_plugin_loader('password')
    creds = get_credentials(other_creds)
    auth = loader.load_from_options(**creds)
    return auth


def get_endpoint(service_type, interface='public'):
    auth = get_session_auth()
    return get_session().get_endpoint(auth=auth,
                                      service_type=service_type,
                                      interface=interface)


def get_session(other_creds={}):
    auth = get_session_auth(other_creds)
    https_cacert = os.getenv('OS_CACERT', '')
    https_insecure = os.getenv('OS_INSECURE', '').lower() == 'true'
    return session.Session(auth=auth,
                           verify=(https_cacert or not https_insecure))


# *********************************************
#   CLIENTS
# *********************************************
def get_keystone_client_version():
    api_version = os.getenv('OS_IDENTITY_API_VERSION')
    if api_version is not None:
        logger.info("OS_IDENTITY_API_VERSION is set in env as '%s'",
                    api_version)
        return api_version
    return DEFAULT_API_VERSION


def get_keystone_client(other_creds={}):
    sess = get_session(other_creds)
    return keystoneclient.Client(get_keystone_client_version(),
                                 session=sess,
                                 interface=os.getenv('OS_INTERFACE', 'admin'))


def get_cinder_client_version():
    api_version = os.getenv('OS_VOLUME_API_VERSION')
    if api_version is not None:
        logger.info("OS_VOLUME_API_VERSION is set in env as '%s'",
                    api_version)
        return api_version
    return DEFAULT_API_VERSION


def get_cinder_client(other_creds={}):
    sess = get_session(other_creds)
    return cinderclient.Client(get_cinder_client_version(), session=sess)


def get_neutron_client_version():
    api_version = os.getenv('OS_NETWORK_API_VERSION')
    if api_version is not None:
        logger.info("OS_NETWORK_API_VERSION is set in env as '%s'",
                    api_version)
        return api_version
    return DEFAULT_API_VERSION


def get_neutron_client(other_creds={}):
    sess = get_session(other_creds)
    return neutronclient.Client(get_neutron_client_version(), session=sess)


def get_heat_client_version():
    api_version = os.getenv('OS_ORCHESTRATION_API_VERSION')
    if api_version is not None:
        logger.info("OS_ORCHESTRATION_API_VERSION is set in env as '%s'",
                    api_version)
        return api_version
    return DEFAULT_HEAT_API_VERSION


def get_heat_client(other_creds={}):
    sess = get_session(other_creds)
    return heatclient.Client(get_heat_client_version(), session=sess)


def download_url(url, dest_path):
    """
    Download a file to a destination path given a URL
    """
    name = url.rsplit('/')[-1]
    dest = dest_path + "/" + name
    try:
        response = urllib.urlopen(url)
    except Exception:
        return False

    with open(dest, 'wb') as lfile:
        shutil.copyfileobj(response, lfile)
    return True


def download_and_add_image_on_glance(conn, image_name, image_url, data_dir):
    try:
        dest_path = data_dir
        if not os.path.exists(dest_path):
            os.makedirs(dest_path)
        file_name = image_url.rsplit('/')[-1]
        if not download_url(image_url, dest_path):
            return False
    except Exception:
        raise Exception("Impossible to download image from {}".format(
                        image_url))

    try:
        image = create_glance_image(
            conn, image_name, dest_path + file_name)
        if not image:
            return False
        else:
            return image
    except Exception:
        raise Exception("Impossible to put image {} in glance".format(
                        image_name))


# *********************************************
#   NOVA
# *********************************************
def get_instances(conn):
    try:
        instances = conn.compute.servers(all_tenants=1)
        return instances
    except Exception as e:
        logger.error("Error [get_instances(compute)]: %s" % e)
        return None


def get_instance_status(conn, instance):
    try:
        instance = conn.compute.get_server(instance.id)
        return instance.status
    except Exception as e:
        logger.error("Error [get_instance_status(compute)]: %s" % e)
        return None


def get_instance_by_name(conn, instance_name):
    try:
        instance = conn.compute.find_server(instance_name,
                                            ignore_missing=False)
        return instance
    except Exception as e:
        logger.error("Error [get_instance_by_name(compute, '%s')]: %s"
                     % (instance_name, e))
        return None


def get_flavor_id(conn, flavor_name):
    flavors = conn.compute.flavors()
    id = ''
    for f in flavors:
        if f.name == flavor_name:
            id = f.id
            break
    return id


def get_flavor_id_by_ram_range(conn, min_ram, max_ram):
    flavors = conn.compute.flavors()
    id = ''
    for f in flavors:
        if min_ram <= f.ram and f.ram <= max_ram:
            id = f.id
            break
    return id


def get_aggregates(cloud):
    try:
        aggregates = cloud.list_aggregates()
        return aggregates
    except Exception as e:
        logger.error("Error [get_aggregates(compute)]: %s" % e)
        return None


def get_aggregate_id(cloud, aggregate_name):
    try:
        aggregates = get_aggregates(cloud)
        _id = [ag.id for ag in aggregates if ag.name == aggregate_name][0]
        return _id
    except Exception as e:
        logger.error("Error [get_aggregate_id(compute, %s)]:"
                     " %s" % (aggregate_name, e))
        return None


def get_availability_zones(conn):
    try:
        availability_zones = conn.compute.availability_zones()
        return availability_zones
    except Exception as e:
        logger.error("Error [get_availability_zones(compute)]: %s" % e)
        return None


def get_availability_zone_names(conn):
    try:
        az_names = [az.zoneName for az in get_availability_zones(conn)]
        return az_names
    except Exception as e:
        logger.error("Error [get_availability_zone_names(compute)]:"
                     " %s" % e)
        return None


def create_flavor(conn, flavor_name, ram, disk, vcpus, public=True):
    try:
        flavor = conn.compute.create_flavor(
            name=flavor_name, ram=ram, disk=disk, vcpus=vcpus,
            is_public=public)
    except Exception as e:
        logger.error("Error [create_flavor(compute, '%s', '%s', '%s', "
                     "'%s')]: %s" % (flavor_name, ram, disk, vcpus, e))
        return None
    return flavor.id


def get_or_create_flavor(flavor_name, ram, disk, vcpus, public=True):
    flavor_exists = False
    conn = get_os_connection()

    flavor_id = get_flavor_id(conn, flavor_name)
    if flavor_id != '':
        logger.info("Using existing flavor '%s'..." % flavor_name)
        flavor_exists = True
    else:
        logger.info("Creating flavor '%s' with '%s' RAM, '%s' disk size, "
                    "'%s' vcpus..." % (flavor_name, ram, disk, vcpus))
        flavor_id = create_flavor(
            conn, flavor_name, ram, disk, vcpus, public=public)
        if not flavor_id:
            raise Exception("Failed to create flavor '%s'..." % (flavor_name))
        else:
            logger.debug("Flavor '%s' with ID=%s created successfully."
                         % (flavor_name, flavor_id))

    return flavor_exists, flavor_id


def get_floating_ips(conn):
    try:
        floating_ips = conn.network.ips()
        return floating_ips
    except Exception as e:
        logger.error("Error [get_floating_ips(network)]: %s" % e)
        return None


def get_hypervisors(conn):
    try:
        nodes = []
        hypervisors = conn.compute.hypervisors()
        for hypervisor in hypervisors:
            if hypervisor.state == "up":
                nodes.append(hypervisor.name)
        return nodes
    except Exception as e:
        logger.error("Error [get_hypervisors(compute)]: %s" % e)
        return None


def create_aggregate(cloud, aggregate_name, av_zone):
    try:
        cloud.create_aggregate(aggregate_name, av_zone)
        return True
    except Exception as e:
        logger.error("Error [create_aggregate(compute, %s, %s)]: %s"
                     % (aggregate_name, av_zone, e))
        return None


def add_host_to_aggregate(cloud, aggregate_name, compute_host):
    try:
        aggregate_id = get_aggregate_id(cloud, aggregate_name)
        cloud.add_host_to_aggregate(aggregate_id, compute_host)
        return True
    except Exception as e:
        logger.error("Error [add_host_to_aggregate(compute, %s, %s)]: %s"
                     % (aggregate_name, compute_host, e))
        return None


def create_aggregate_with_host(
        cloud, aggregate_name, av_zone, compute_host):
    try:
        create_aggregate(cloud, aggregate_name, av_zone)
        add_host_to_aggregate(cloud, aggregate_name, compute_host)
        return True
    except Exception as e:
        logger.error("Error [create_aggregate_with_host("
                     "compute, %s, %s, %s)]: %s"
                     % (aggregate_name, av_zone, compute_host, e))
        return None


def create_instance(flavor_name,
                    image_id,
                    network_id,
                    instance_name="functest-vm",
                    confdrive=True,
                    userdata=None,
                    av_zone=None,
                    fixed_ip=None,
                    files=[]):
    conn = get_os_connection()
    try:
        flavor = conn.compute.find_flavor(flavor_name, ignore_missing=False)
    except:
        flavors = [flavor.name for flavor in conn.compute.flavors()]
        logger.error("Error: Flavor '%s' not found. Available flavors are: "
                     "\n%s" % (flavor_name, flavors))
        return None
    if fixed_ip is not None:
        networks = {"uuid": network_id, "fixed_ip": fixed_ip}
    else:
        networks = {"uuid": network_id}

    server_attrs = {
        'name': instance_name,
        'flavor_id': flavor.id,
        'image_id': image_id,
        'networks': [networks],
        'personality': files
    }
    if userdata is not None:
        server_attrs['config_drive'] = confdrive
        server_attrs['user_data'] = base64.b64encode(userdata.encode())
    if av_zone is not None:
        server_attrs['availability_zone'] = av_zone

    instance = conn.compute.create_server(**server_attrs)
    return instance


def create_instance_and_wait_for_active(flavor_name,
                                        image_id,
                                        network_id,
                                        instance_name="",
                                        config_drive=False,
                                        userdata="",
                                        av_zone=None,
                                        fixed_ip=None,
                                        files=[]):
    SLEEP = 3
    VM_BOOT_TIMEOUT = 180
    conn = get_os_connection()
    instance = create_instance(flavor_name,
                               image_id,
                               network_id,
                               instance_name,
                               config_drive,
                               userdata,
                               av_zone=av_zone,
                               fixed_ip=fixed_ip,
                               files=files)
    count = VM_BOOT_TIMEOUT / SLEEP
    for n in range(count, -1, -1):
        status = get_instance_status(conn, instance)
        if status is None:
            time.sleep(SLEEP)
            continue
        elif status.lower() == "active":
            return instance
        elif status.lower() == "error":
            logger.error("The instance %s went to ERROR status."
                         % instance_name)
            return None
        time.sleep(SLEEP)
    logger.error("Timeout booting the instance %s." % instance_name)
    return None


def create_floating_ip(conn):
    extnet_id = get_external_net_id(conn)
    try:
        fip = conn.network.create_ip(floating_network_id=extnet_id)
        fip_addr = fip.floating_ip_address
        fip_id = fip.id
    except Exception as e:
        logger.error("Error [create_floating_ip(network)]: %s" % e)
        return None
    return {'fip_addr': fip_addr, 'fip_id': fip_id}


def attach_floating_ip(conn, port_id):
    extnet_id = get_external_net_id(conn)
    try:
        return conn.network.create_ip(floating_network_id=extnet_id,
                                      port_id=port_id)
    except Exception as e:
        logger.error("Error [Attach_floating_ip(network), %s]: %s"
                     % (port_id, e))
        return None


def add_floating_ip(conn, server_id, floatingip_addr):
    try:
        conn.compute.add_floating_ip_to_server(server_id, floatingip_addr)
        return True
    except Exception as e:
        logger.error("Error [add_floating_ip(compute, '%s', '%s')]: %s"
                     % (server_id, floatingip_addr, e))
        return False


def delete_instance(conn, instance_id):
    try:
        conn.compute.delete_server(instance_id, force=True)
        return True
    except Exception as e:
        logger.error("Error [delete_instance(compute, '%s')]: %s"
                     % (instance_id, e))
        return False


def delete_floating_ip(conn, floatingip_id):
    try:
        conn.network.delete_ip(floatingip_id)
        return True
    except Exception as e:
        logger.error("Error [delete_floating_ip(network, '%s')]: %s"
                     % (floatingip_id, e))
        return False


def remove_host_from_aggregate(cloud, aggregate_name, compute_host):
    try:
        aggregate_id = get_aggregate_id(cloud, aggregate_name)
        cloud.remove_host_from_aggregate(aggregate_id, compute_host)
        return True
    except Exception as e:
        logger.error("Error [remove_host_from_aggregate(compute, %s, %s)]:"
                     " %s" % (aggregate_name, compute_host, e))
        return False


def remove_hosts_from_aggregate(cloud, aggregate_name):
    aggregate_id = get_aggregate_id(cloud, aggregate_name)
    hosts = cloud.get_aggregate(aggregate_id).hosts
    assert(
        all(remove_host_from_aggregate(cloud, aggregate_name, host)
            for host in hosts))


def delete_aggregate(cloud, aggregate_name):
    try:
        remove_hosts_from_aggregate(cloud, aggregate_name)
        cloud.delete_aggregate(aggregate_name)
        return True
    except Exception as e:
        logger.error("Error [delete_aggregate(compute, %s)]: %s"
                     % (aggregate_name, e))
        return False


# *********************************************
#   NEUTRON
# *********************************************
def get_network_list(conn):
    return conn.network.networks()


def get_router_list(conn):
    return conn.network.routers()


def get_port_list(conn):
    return conn.network.ports()


def get_network_id(conn, network_name):
    networks = conn.network.networks()
    id = ''
    for n in networks:
        if n.name == network_name:
            id = n.id
            break
    return id


def get_subnet_id(conn, subnet_name):
    subnets = conn.network.subnets()
    id = ''
    for s in subnets:
        if s.name == subnet_name:
            id = s.id
            break
    return id


def get_router_id(conn, router_name):
    routers = conn.network.routers()
    id = ''
    for r in routers:
        if r.name == router_name:
            id = r.id
            break
    return id


def get_private_net(conn):
    # Checks if there is an existing shared private network
    networks = conn.network.networks()
    for net in networks:
        if (net.is_router_external is False) and (net.is_shared is True):
            return net
    return None


def get_external_net(conn):
    if (env.get('EXTERNAL_NETWORK')):
        return env.get('EXTERNAL_NETWORK')
    for network in conn.network.networks():
        if network.is_router_external:
            return network.name
    return None


def get_external_net_id(conn):
    if (env.get('EXTERNAL_NETWORK')):
        networks = conn.network.networks(name=env.get('EXTERNAL_NETWORK'))
        net_id = networks.next().id
        return net_id
    for network in conn.network.networks():
        if network.is_router_external:
            return network.id
    return None


def check_neutron_net(conn, net_name):
    for network in conn.network.networks():
        if network.name == net_name:
            for subnet in network.subnet_ids:
                return True
    return False


def create_neutron_net(conn, name):
    try:
        network = conn.network.create_network(name=name)
        return network.id
    except Exception as e:
        logger.error("Error [create_neutron_net(network, '%s')]: %s"
                     % (name, e))
        return None


def create_neutron_subnet(conn, name, cidr, net_id,
                          dns=['8.8.8.8', '8.8.4.4']):
    try:
        subnet = conn.network.create_subnet(name=name,
                                            cidr=cidr,
                                            ip_version='4',
                                            network_id=net_id,
                                            dns_nameservers=dns)
        return subnet.id
    except Exception as e:
        logger.error("Error [create_neutron_subnet(network, '%s', "
                     "'%s', '%s')]: %s" % (name, cidr, net_id, e))
        return None


def create_neutron_router(conn, name):
    try:
        router = conn.network.create_router(name=name)
        return router.id
    except Exception as e:
        logger.error("Error [create_neutron_router(network, '%s')]: %s"
                     % (name, e))
        return None


def create_neutron_port(conn, name, network_id, ip):
    try:
        port = conn.network.create_port(name=name,
                                        network_id=network_id,
                                        fixed_ips=[{'ip_address': ip}])
        return port.id
    except Exception as e:
        logger.error("Error [create_neutron_port(network, '%s', '%s', "
                     "'%s')]: %s" % (name, network_id, ip, e))
        return None


def update_neutron_net(conn, network_id, shared=False):
    try:
        conn.network.update_network(network_id, is_shared=shared)
        return True
    except Exception as e:
        logger.error("Error [update_neutron_net(network, '%s', '%s')]: "
                     "%s" % (network_id, str(shared), e))
        return False


def update_neutron_port(conn, port_id, device_owner):
    try:
        port = conn.network.update_port(port_id, device_owner=device_owner)
        return port.id
    except Exception as e:
        logger.error("Error [update_neutron_port(network, '%s', '%s')]:"
                     " %s" % (port_id, device_owner, e))
        return None


def add_interface_router(conn, router_id, subnet_id):
    try:
        conn.network.add_interface_to_router(router_id, subnet_id=subnet_id)
        return True
    except Exception as e:
        logger.error("Error [add_interface_router(network, '%s', "
                     "'%s')]: %s" % (router_id, subnet_id, e))
        return False


def add_gateway_router(conn, router_id):
    ext_net_id = get_external_net_id(conn)
    router_dict = {'network_id': ext_net_id}
    try:
        conn.network.update_router(router_id,
                                   external_gateway_info=router_dict)
        return True
    except Exception as e:
        logger.error("Error [add_gateway_router(network, '%s')]: %s"
                     % (router_id, e))
        return False


def delete_neutron_net(conn, network_id):
    try:
        conn.network.delete_network(network_id, ignore_missing=False)
        return True
    except Exception as e:
        logger.error("Error [delete_neutron_net(network, '%s')]: %s"
                     % (network_id, e))
        return False


def delete_neutron_subnet(conn, subnet_id):
    try:
        conn.network.delete_subnet(subnet_id, ignore_missing=False)
        return True
    except Exception as e:
        logger.error("Error [delete_neutron_subnet(network, '%s')]: %s"
                     % (subnet_id, e))
        return False


def delete_neutron_router(conn, router_id):
    try:
        conn.network.delete_router(router_id, ignore_missing=False)
        return True
    except Exception as e:
        logger.error("Error [delete_neutron_router(network, '%s')]: %s"
                     % (router_id, e))
        return False


def delete_neutron_port(conn, port_id):
    try:
        conn.network.delete_port(port_id, ignore_missing=False)
        return True
    except Exception as e:
        logger.error("Error [delete_neutron_port(network, '%s')]: %s"
                     % (port_id, e))
        return False


def remove_interface_router(conn, router_id, subnet_id):
    try:
        conn.network.remove_interface_from_router(router_id,
                                                  subnet_id=subnet_id)
        return True
    except Exception as e:
        logger.error("Error [remove_interface_router(network, '%s', "
                     "'%s')]: %s" % (router_id, subnet_id, e))
        return False


def remove_gateway_router(conn, router_id):
    try:
        conn.network.update_router(router_id, external_gateway_info=None)
        return True
    except Exception as e:
        logger.error("Error [remove_gateway_router(network, '%s')]: %s"
                     % (router_id, e))
        return False


def create_network_full(conn,
                        net_name,
                        subnet_name,
                        router_name,
                        cidr,
                        dns=['8.8.8.8', '8.8.4.4']):

    # Check if the network already exists
    network_id = get_network_id(conn, net_name)
    subnet_id = get_subnet_id(conn, subnet_name)
    router_id = get_router_id(conn, router_name)

    if network_id != '' and subnet_id != '' and router_id != '':
        logger.info("A network with name '%s' already exists..." % net_name)
    else:
        logger.info('Creating neutron network %s...' % net_name)
        if network_id == '':
            network_id = create_neutron_net(conn, net_name)
        if not network_id:
            return False
        logger.debug("Network '%s' created successfully" % network_id)

        logger.debug('Creating Subnet....')
        if subnet_id == '':
            subnet_id = create_neutron_subnet(conn, subnet_name, cidr,
                                              network_id, dns)
        if not subnet_id:
            return None
        logger.debug("Subnet '%s' created successfully" % subnet_id)

        logger.debug('Creating Router...')
        if router_id == '':
            router_id = create_neutron_router(conn, router_name)
        if not router_id:
            return None
        logger.debug("Router '%s' created successfully" % router_id)

        logger.debug('Adding router to subnet...')

        if not add_interface_router(conn, router_id, subnet_id):
            return None
        logger.debug("Interface added successfully.")

        logger.debug('Adding gateway to router...')
        if not add_gateway_router(conn, router_id):
            return None
        logger.debug("Gateway added successfully.")

    network_dic = {'net_id': network_id,
                   'subnet_id': subnet_id,
                   'router_id': router_id}
    return network_dic


def create_shared_network_full(net_name, subnt_name, router_name, subnet_cidr):
    conn = get_os_connection()

    network_dic = create_network_full(conn,
                                      net_name,
                                      subnt_name,
                                      router_name,
                                      subnet_cidr)
    if network_dic:
        if not update_neutron_net(conn,
                                  network_dic['net_id'],
                                  shared=True):
            logger.error("Failed to update network %s..." % net_name)
            return None
        else:
            logger.debug("Network '%s' is available..." % net_name)
    else:
        logger.error("Network %s creation failed" % net_name)
        return None
    return network_dic


# *********************************************
#   SEC GROUPS
# *********************************************


def get_security_groups(conn):
    return conn.network.security_groups()


def get_security_group_id(conn, sg_name):
    security_groups = get_security_groups(conn)
    id = ''
    for sg in security_groups:
        if sg.name == sg_name:
            id = sg.id
            break
    return id


def create_security_group(conn, sg_name, sg_description):
    try:
        secgroup = conn.network.\
            create_security_group(name=sg_name, description=sg_description)
        return secgroup
    except Exception as e:
        logger.error("Error [create_security_group(network, '%s', "
                     "'%s')]: %s" % (sg_name, sg_description, e))
        return None


def create_secgroup_rule(conn, sg_id, direction, protocol,
                         port_range_min=None, port_range_max=None):
    # We create a security group in 2 steps
    # 1 - we check the format and set the secgroup rule attributes accordingly
    # 2 - we call openstacksdk to create the security group

    # Format check
    secgroup_rule_attrs = {'direction': direction,
                           'security_group_id': sg_id,
                           'protocol': protocol}
    # parameters may be
    # - both None => we do nothing
    # - both Not None => we add them to the secgroup rule attributes
    # but one cannot be None is the other is not None
    if (port_range_min is not None and port_range_max is not None):
        # add port_range in secgroup rule attributes
        secgroup_rule_attrs['port_range_min'] = port_range_min
        secgroup_rule_attrs['port_range_max'] = port_range_max
        logger.debug("Security_group format set (port range included)")
    else:
        # either both port range are set to None => do nothing
        # or one is set but not the other => log it and return False
        if port_range_min is None and port_range_max is None:
            logger.debug("Security_group format set (no port range mentioned)")
        else:
            logger.error("Bad security group format."
                         "One of the port range is not properly set:"
                         "range min: {},"
                         "range max: {}".format(port_range_min,
                                                port_range_max))
            return False

    # Create security group using neutron client
    try:
        conn.network.create_security_group_rule(**secgroup_rule_attrs)
        return True
    except:
        logger.exception("Impossible to create_security_group_rule,"
                         "security group rule probably already exists")
        return False


def get_security_group_rules(conn, sg_id):
    try:
        security_rules = conn.network.security_group_rules()
        security_rules = [rule for rule in security_rules
                          if rule.security_group_id == sg_id]
        return security_rules
    except Exception as e:
        logger.error("Error [get_security_group_rules(network, sg_id)]:"
                     " %s" % e)
        return None


def check_security_group_rules(conn, sg_id, direction, protocol,
                               port_min=None, port_max=None):
    try:
        security_rules = get_security_group_rules(conn, sg_id)
        security_rules = [rule for rule in security_rules
                          if (rule.direction.lower() == direction and
                              rule.protocol.lower() == protocol and
                              rule.port_range_min == port_min and
                              rule.port_range_max == port_max)]
        if len(security_rules) == 0:
            return True
        else:
            return False
    except Exception as e:
        logger.error("Error [check_security_group_rules("
                     " network, sg_id, direction,"
                     " protocol, port_min=None, port_max=None)]: "
                     "%s" % e)
        return None


def create_security_group_full(conn,
                               sg_name, sg_description):
    sg_id = get_security_group_id(conn, sg_name)
    if sg_id != '':
        logger.info("Using existing security group '%s'..." % sg_name)
    else:
        logger.info("Creating security group  '%s'..." % sg_name)
        SECGROUP = create_security_group(conn,
                                         sg_name,
                                         sg_description)
        if not SECGROUP:
            logger.error("Failed to create the security group...")
            return None

        sg_id = SECGROUP.id

        logger.debug("Security group '%s' with ID=%s created successfully."
                     % (SECGROUP.name, sg_id))

        logger.debug("Adding ICMP rules in security group '%s'..."
                     % sg_name)
        if not create_secgroup_rule(conn, sg_id,
                                    'ingress', 'icmp'):
            logger.error("Failed to create the security group rule...")
            return None

        logger.debug("Adding SSH rules in security group '%s'..."
                     % sg_name)
        if not create_secgroup_rule(
                conn, sg_id, 'ingress', 'tcp', '22', '22'):
            logger.error("Failed to create the security group rule...")
            return None

        if not create_secgroup_rule(
                conn, sg_id, 'egress', 'tcp', '22', '22'):
            logger.error("Failed to create the security group rule...")
            return None
    return sg_id


def add_secgroup_to_instance(conn, instance_id, secgroup_id):
    try:
        conn.compute.add_security_group_to_server(instance_id, secgroup_id)
        return True
    except Exception as e:
        logger.error("Error [add_secgroup_to_instance(compute, '%s', "
                     "'%s')]: %s" % (instance_id, secgroup_id, e))
        return False


def update_sg_quota(conn, tenant_id, sg_quota, sg_rule_quota):
    try:
        conn.network.update_quota(tenant_id,
                                  security_group_rules=sg_rule_quota,
                                  security_groups=sg_quota)
        return True
    except Exception as e:
        logger.error("Error [update_sg_quota(network, '%s', '%s', "
                     "'%s')]: %s" % (tenant_id, sg_quota, sg_rule_quota, e))
        return False


def delete_security_group(conn, secgroup_id):
    try:
        conn.network.delete_security_group(secgroup_id, ignore_missing=False)
        return True
    except Exception as e:
        logger.error("Error [delete_security_group(network, '%s')]: %s"
                     % (secgroup_id, e))
        return False


# *********************************************
#   GLANCE
# *********************************************
def get_images(conn):
    try:
        images = conn.image.images()
        return images
    except Exception as e:
        logger.error("Error [get_images]: %s" % e)
        return None


def get_image_id(conn, image_name):
    images = conn.image.images()
    id = ''
    for i in images:
        if i.name == image_name:
            id = i.id
            break
    return id


def create_glance_image(conn,
                        image_name,
                        file_path,
                        disk="qcow2",
                        extra_properties={},
                        container="bare",
                        public="public"):
    if not os.path.isfile(file_path):
        logger.error("Error: file %s does not exist." % file_path)
        return None
    try:
        image_id = get_image_id(conn, image_name)
        if image_id != '':
            logger.info("Image %s already exists." % image_name)
        else:
            logger.info("Creating image '%s' from '%s'..." % (image_name,
                                                              file_path))
            with open(file_path) as image_data:
                image = conn.image.upload_image(name=image_name,
                                                is_public=public,
                                                disk_format=disk,
                                                container_format=container,
                                                data=image_data,
                                                **extra_properties)
            image_id = image.id
        return image_id
    except Exception as e:
        logger.error("Error [create_glance_image(image, '%s', '%s', "
                     "'%s')]: %s" % (image_name, file_path, public, e))
        return None


def get_or_create_image(name, path, format, extra_properties):
    image_exists = False
    conn = get_os_connection()

    image_id = get_image_id(conn, name)
    if image_id != '':
        logger.info("Using existing image '%s'..." % name)
        image_exists = True
    else:
        logger.info("Creating image '%s' from '%s'..." % (name, path))
        image_id = create_glance_image(conn,
                                       name,
                                       path,
                                       format,
                                       extra_properties)
        if not image_id:
            logger.error("Failed to create a Glance image...")
        else:
            logger.debug("Image '%s' with ID=%s created successfully."
                         % (name, image_id))

    return image_exists, image_id


def delete_glance_image(conn, image_id):
    try:
        conn.image.delete_image(image_id)
        return True
    except Exception as e:
        logger.error("Error [delete_glance_image(image, '%s')]: %s"
                     % (image_id, e))
        return False


# *********************************************
#   CINDER
# *********************************************
def get_volumes(cinder_client):
    try:
        volumes = cinder_client.volumes.list(search_opts={'all_tenants': 1})
        return volumes
    except Exception as e:
        logger.error("Error [get_volumes(cinder_client)]: %s" % e)
        return None


def update_cinder_quota(cinder_client, tenant_id, vols_quota,
                        snapshots_quota, gigabytes_quota):
    quotas_values = {"volumes": vols_quota,
                     "snapshots": snapshots_quota,
                     "gigabytes": gigabytes_quota}

    try:
        cinder_client.quotas.update(tenant_id, **quotas_values)
        return True
    except Exception as e:
        logger.error("Error [update_cinder_quota(cinder_client, '%s', '%s', "
                     "'%s' '%s')]: %s" % (tenant_id, vols_quota,
                                          snapshots_quota, gigabytes_quota, e))
        return False


def delete_volume(cinder_client, volume_id, forced=False):
    try:
        if forced:
            try:
                cinder_client.volumes.detach(volume_id)
            except:
                logger.error(sys.exc_info()[0])
            cinder_client.volumes.force_delete(volume_id)
        else:
            cinder_client.volumes.delete(volume_id)
        return True
    except Exception as e:
        logger.error("Error [delete_volume(cinder_client, '%s', '%s')]: %s"
                     % (volume_id, str(forced), e))
        return False


# *********************************************
#   KEYSTONE
# *********************************************
def get_tenants(keystone_client):
    try:
        if is_keystone_v3():
            tenants = keystone_client.projects.list()
        else:
            tenants = keystone_client.tenants.list()
        return tenants
    except Exception as e:
        logger.error("Error [get_tenants(keystone_client)]: %s" % e)
        return None


def get_users(keystone_client):
    try:
        users = keystone_client.users.list()
        return users
    except Exception as e:
        logger.error("Error [get_users(keystone_client)]: %s" % e)
        return None


def get_tenant_id(keystone_client, tenant_name):
    tenants = get_tenants(keystone_client)
    id = ''
    for t in tenants:
        if t.name == tenant_name:
            id = t.id
            break
    return id


def get_user_id(keystone_client, user_name):
    users = get_users(keystone_client)
    id = ''
    for u in users:
        if u.name == user_name:
            id = u.id
            break
    return id


def get_role_id(keystone_client, role_name):
    roles = keystone_client.roles.list()
    id = ''
    for r in roles:
        if r.name == role_name:
            id = r.id
            break
    return id


def get_domain_id(keystone_client, domain_name):
    domains = keystone_client.domains.list()
    id = ''
    for d in domains:
        if d.name == domain_name:
            id = d.id
            break
    return id


def create_tenant(keystone_client, tenant_name, tenant_description):
    try:
        if is_keystone_v3():
            domain_name = os.environ['OS_PROJECT_DOMAIN_NAME']
            domain_id = get_domain_id(keystone_client, domain_name)
            tenant = keystone_client.projects.create(
                name=tenant_name,
                description=tenant_description,
                domain=domain_id,
                enabled=True)
        else:
            tenant = keystone_client.tenants.create(tenant_name,
                                                    tenant_description,
                                                    enabled=True)
        return tenant.id
    except Exception as e:
        logger.error("Error [create_tenant(keystone_client, '%s', '%s')]: %s"
                     % (tenant_name, tenant_description, e))
        return None


def get_or_create_tenant(keystone_client, tenant_name, tenant_description):
    tenant_id = get_tenant_id(keystone_client, tenant_name)
    if not tenant_id:
        tenant_id = create_tenant(keystone_client, tenant_name,
                                  tenant_description)

    return tenant_id


def get_or_create_tenant_for_vnf(keystone_client, tenant_name,
                                 tenant_description):
    """Get or Create a Tenant

        Args:
            keystone_client: keystone client reference
            tenant_name: the name of the tenant
            tenant_description: the description of the tenant

        return False if tenant retrieved though get
        return True if tenant created
        raise Exception if error during processing
    """
    try:
        tenant_id = get_tenant_id(keystone_client, tenant_name)
        if not tenant_id:
            tenant_id = create_tenant(keystone_client, tenant_name,
                                      tenant_description)
            return True
        else:
            return False
    except:
        raise Exception("Impossible to create a Tenant for the VNF {}".format(
                            tenant_name))


def create_user(keystone_client, user_name, user_password,
                user_email, tenant_id):
    try:
        if is_keystone_v3():
            user = keystone_client.users.create(name=user_name,
                                                password=user_password,
                                                email=user_email,
                                                project_id=tenant_id,
                                                enabled=True)
        else:
            user = keystone_client.users.create(user_name,
                                                user_password,
                                                user_email,
                                                tenant_id,
                                                enabled=True)
        return user.id
    except Exception as e:
        logger.error("Error [create_user(keystone_client, '%s', '%s', '%s'"
                     "'%s')]: %s" % (user_name, user_password,
                                     user_email, tenant_id, e))
        return None


def get_or_create_user(keystone_client, user_name, user_password,
                       tenant_id, user_email=None):
    user_id = get_user_id(keystone_client, user_name)
    if not user_id:
        user_id = create_user(keystone_client, user_name, user_password,
                              user_email, tenant_id)
    return user_id


def get_or_create_user_for_vnf(keystone_client, vnf_ref):
    """Get or Create user for VNF

        Args:
            keystone_client: keystone client reference
            vnf_ref: VNF reference used as user name & password, tenant name

        return False if user retrieved through get
        return True if user created
        raise Exception if error during processing
    """
    try:
        user_id = get_user_id(keystone_client, vnf_ref)
        tenant_id = get_tenant_id(keystone_client, vnf_ref)
        created = False
        if not user_id:
            user_id = create_user(keystone_client, vnf_ref, vnf_ref,
                                  "", tenant_id)
            created = True
        try:
            role_id = get_role_id(keystone_client, 'admin')
            tenant_id = get_tenant_id(keystone_client, vnf_ref)
            add_role_user(keystone_client, user_id, role_id, tenant_id)
        except:
            logger.warn("Cannot associate user to role admin on tenant")
        return created
    except:
        raise Exception("Impossible to create a user for the VNF {}".format(
            vnf_ref))


def add_role_user(keystone_client, user_id, role_id, tenant_id):
    try:
        if is_keystone_v3():
            keystone_client.roles.grant(role=role_id,
                                        user=user_id,
                                        project=tenant_id)
        else:
            keystone_client.roles.add_user_role(user_id, role_id, tenant_id)
        return True
    except Exception as e:
        logger.error("Error [add_role_user(keystone_client, '%s', '%s'"
                     "'%s')]: %s " % (user_id, role_id, tenant_id, e))
        return False


def delete_tenant(keystone_client, tenant_id):
    try:
        if is_keystone_v3():
            keystone_client.projects.delete(tenant_id)
        else:
            keystone_client.tenants.delete(tenant_id)
        return True
    except Exception as e:
        logger.error("Error [delete_tenant(keystone_client, '%s')]: %s"
                     % (tenant_id, e))
        return False


def delete_user(keystone_client, user_id):
    try:
        keystone_client.users.delete(user_id)
        return True
    except Exception as e:
        logger.error("Error [delete_user(keystone_client, '%s')]: %s"
                     % (user_id, e))
        return False


# *********************************************
#   HEAT
# *********************************************
def get_resource(heat_client, stack_id, resource):
    try:
        resources = heat_client.resources.get(stack_id, resource)
        return resources
    except Exception as e:
        logger.error("Error [get_resource]: %s" % e)
        return None


def create_stack(heat_client, **kwargs):
    try:
        stack = heat_client.stacks.create(**kwargs)
        stack_id = stack['stack']['id']
        if stack_id is None:
            logger.error("Stack create start failed")
            raise SystemError("Stack create start failed")
        return stack_id
    except Exception as e:
        logger.error("Error [create_stack]: %s" % e)
        return None


def delete_stack(heat_client, stack_id):
    try:
        heat_client.stacks.delete(stack_id)
        return True
    except Exception as e:
        logger.error("Error [delete_stack]: %s" % e)
        return False


def list_stack(heat_client, **kwargs):
    try:
        result = heat_client.stacks.list(**kwargs)
        return result
    except Exception as e:
        logger.error("Error [list_stack]: %s" % e)
        return None


def get_output(heat_client, stack_id, output_key):
    try:
        output = heat_client.stacks.output_show(stack_id, output_key)
        return output
    except Exception as e:
        logger.error("Error [get_output]: %s" % e)
        return None
