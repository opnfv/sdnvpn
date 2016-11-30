include ::tripleo::packages

if count(hiera('ntp::servers')) > 0 {
  include ::ntp
}

class {"opendaylight":
  extra_features => any2array(hiera('opendaylight::extra_features', 'odl-netvirt-openstack')),
  odl_rest_port  => hiera('opendaylight::odl_rest_port'),
  enable_l3      => hiera('opendaylight::enable_l3', 'no'),
  #tarball_url    =>  'file:///home/heat-admin/distribution-karaf-0.6.0-SNAPSHOT.tar.gz',
  #unitfile_url   =>  'file:///home/heat-admin/opendaylight-unitfile.tar.gz' 
}


