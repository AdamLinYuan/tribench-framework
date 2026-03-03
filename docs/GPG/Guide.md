Guide and scripts assembled by [Youssef Moawad](https://devdude.me). Any questions or clarifications, please reach out!

Copying commands from a PDF is painful! So the markdown version of this document is provided for an easier time copying.😊
# Overview

This guide describes steps required to bring up and tear the K8s cluster on the GPG nodes. It is accompanied by a few scripts to automate some steps.

Bringing up the cluster involves:

1. *If using Ceph for storage:* Partitioning `/dev/sdb` (typically mounted as a single partition `/scratch2`) to allow Ceph to use it for storage
2. Initialising Kubernetes, disabling swap, loading kernel modules, setting up sysctl params (`k8s_preinit.sh`)
3. Control Plane setup
4. Install network plugin
5. Worker nodes joining cluster
6. Installing Ceph through Rook
7. Configuring a StorageClass and a PVC for Ceph
8. Setting up Nextflow
9. Setting up Prometheus
10. Setting up Kepler

# Partitioning `/dev/sdb`

Ceph [OSDs](https://documentation.suse.com/ses/7.1/html/ses-all/admin-caasp-cephosd.html) require unmounted partitions to be used for storage. This section explains to partition physical drives on the worker nodes so they can be discovered and used by the *OSD prepare pods* (which start up before the OSD pods themselves to check for valid devices for the OSDs).

We assume there's a device on the worker node at `/dev/sdb` which is currently formatted as one partition `/dev/sdb1` mounted at `/scratch2` (as is the default setup on GPG nodes). **Nothing important should be left on `/scratch2`. There is no guarantee any files will be kept after the partitioning process.** (Though in my experience, as long as there's not too much filling up the drive, it should still be there on the shrunk `/scratch2` after the partitioning is done).

Run the script `scripts/partition_sdb.sh` on each intended worker node.
### Completely wiping the new partition and cache files
I ran into an issue where the `osd-prepare` pods would always fail to find a suitable device to launch an OSD on a partition which previously had an OSD, even after this partition was presumably wiped as above. To be completely sure, it's best to do the following:

- Completely wipe the partitions intended for OSD use: `sudo dd if=/dev/zero of=/dev/sdb2 bs=1M status=progress` on all the worker nodes
- Delete any leftover ceph files in /var on the control plane node: `sudo find /var -name ceph -exec rm -rf {} +`
- To avoid the `mon` pods from taking ages (20mins each instead of 5mins for all, in my experience) to start, these caches need to be cleared from the worker nodes:
	`sudo rm -rf /var/lib/rook /var/lib/ceph`
# Initialising Kubernetes

The provided `scripts/k8_preinit.sh` installs and sets up what is needed for running Kubernetes on the cluster. Run it on the control plane and all the worker nodes.

## Change the containerd root

We need to change containerd so it stores its images on a larger partition. Either do this automatically by running the script: `scripts/update_containerd_paths.sh` or manually:

 `sudo vim /etc/containerd/config.toml`

And set `root` and `state`:

```
root = "/scratch2/containerd"
state = "/scratch2/containerd_state"
```

on each worker node.
### Restart containerd
Now restart both containerd on each worker node:

```
sudo systemctl daemon-reload
sudo systemctl restart containerd
```
# Control Plane Setup

To start the control plane, run:

```bash
sudo kubeadm init --pod-network-cidr=192.168.0.0/16
```

You will now need to execute the commands to setup the `.kube/config` file in your home directory. For the GPG cluster this doesn't work automatically as sudo cannot write into the home dir of the users so we have to use `tee` to write the file:

```shell
mkdir -p $HOME/.kube
sudo cat /etc/kubernetes/admin.conf | tee $HOME/.kube/config > /dev/null
chown $(id -u):$(id -g) $HOME/.kube/config
```

This will generate a join command to run on the worker nodes, save this until after the next step.

# Install network plugin

Install a network plugin. The latest version of Cisco Calico should work:

```bash
kubectl apply -f https://raw.githubusercontent.com/projectcalico/calico/v3.29.3/manifests/calico.yaml
```

or find the latest version here: https://github.com/projectcalico/calico.

### Wait for the network plugin to start everything

Run `kubectl get pods --all-namespaces -o wide -w` to monitor the pods. Once everything is stable, proceed to the next section. My sample output looks like this:

```shell
NAMESPACE     NAME                                      READY   STATUS    RESTARTS   AGE     IP                NODE         NOMINATED NODE   READINESS GATES
kube-system   calico-kube-controllers-79949b87d-xh5mb   1/1     Running   0          106s    192.168.254.197   gpgnode-04   <none>           <none>
kube-system   calico-node-l446f                         1/1     Running   0          106s    130.209.255.4     gpgnode-04   <none>           <none>
kube-system   coredns-668d6bf9bc-l5sdq                  1/1     Running   0          6m7s    192.168.254.198   gpgnode-04   <none>           <none>
kube-system   coredns-668d6bf9bc-qcq2b                  1/1     Running   0          6m7s    192.168.254.194   gpgnode-04   <none>           <none>
kube-system   etcd-gpgnode-04                           1/1     Running   25         6m15s   130.209.255.4     gpgnode-04   <none>           <none>
kube-system   kube-apiserver-gpgnode-04                 1/1     Running   0          6m14s   130.209.255.4     gpgnode-04   <none>           <none>
kube-system   kube-controller-manager-gpgnode-04        1/1     Running   0          6m12s   130.209.255.4     gpgnode-04   <none>           <none>
kube-system   kube-proxy-58jwn                          1/1     Running   0          6m7s    130.209.255.4     gpgnode-04   <none>           <none>
kube-system   kube-scheduler-gpgnode-04                 1/1     Running   0          6m12s   130.209.255.4     gpgnode-04   <none>           <none>
```

# Worker nodes join

Regenerate the join command on the control plane if the older one is lost:

```bash
sudo kubeadm token create --print-join-command
```

Run the output from this command on each intended worker node.

Verify they joined by running:
```bash
kubectl get nodes
```
on the control plane.

Also, if you are still watching the pods, you should get new `calico-node-` pods for each node you add.
# Installing Ceph through Rook

Rook is simply a [repository]() that contains various YAML files to set up the Ceph pods/storageclasses/other resources on the K8s cluster. This section describes how to use it to set up Ceph.
### Clone the repo
Clone a specific version of the repository using:
```bash
git clone --single-branch --branch v1.16.6 https://github.com/rook/rook.git 
cd rook/deploy/examples
```
### Install the Rook CRDs and Operator
```bash
kubectl apply -f crds.yaml
kubectl apply -f common.yaml
kubectl apply -f operator.yaml
```

These commands install the required Rook components on the k8s cluster in user. **CRDs** are [**Custom Resource Definitions**](https://kubernetes.io/docs/concepts/extend-kubernetes/api-extension/custom-resources/). 

`crds.yaml` are the Rook CRDs.
`common.yaml` setups up the `rook-ceph` namespace, service account, and basic config for the operator.
`operator.yaml` launches the **Rook Ceph operator**, which is the controller that watches for `CephCluster` and other custom resources.

### Create the Ceph Cluster
```bash
kubectl apply -f cluster.yaml
```

Applying the `cluster.yaml` file will launch the pods needed to prepare the cluster, including mons, mgrs, and osds.

It typically takes about 5mins for the `mon-a` pod to launch, and when it's ready the rest of the mons start launching and generally take a few seconds each. 
#### Potential issue: mons taking ~20mins to launch
I ran into an issue where sometimes mon pods would take a long time to reach the running state (and they launch one at a time, potentially wasting significant time!). This tends to happen if you have previously tried to run the ceph cluster (which happens a lot when you encounter various issues!). To avoid this, make sure these caches are cleared on the control plane and all the worker nodes:
```bash
sudo rm -rf /var/lib/rook /var/lib/ceph
```
Remember you can check the status of the pods by running:
```bash
kubectl get pods --all-namespaces [-w]
```
with the optional `-w` flag to watch for updates.

#### Ensuring OSDs start properly
After the mon pods launch, the mgr and osd prepare pods will follow. If the osd prepare pods find valid devices, the osd pods themselves will startup afterwards. If no OSD pods have launched when the prepare pods have finished, you need to check the logs of the prepare pods. E.g.:
```bash
kubectl -n rook-ceph logs rook-ceph-osd-prepare-gpgnode-05-8wtjj
```

If you followed the steps in the *Completely wiping the new partition and cache files* section above, you *should* have no issues. Common issues I encountered were:

```
2025-05-06 14:44:24.833171 D | exec: Running command: ceph-volume inventory --format json /dev/sda3 
2025-05-06 14:44:26.174511 I | cephosd: skipping device "sda3": ["Insufficient space (<5GB)"]. 
2025-05-06 14:44:26.174557 I | cephosd: skipping device "sda5" with mountpoint "var" 
2025-05-06 14:44:26.174564 I | cephosd: skipping device "sda6" with mountpoint "gpg" 
2025-05-06 14:44:26.174570 I | cephosd: skipping device "sda7" with mountpoint "scratch1" 
2025-05-06 14:44:26.174575 I | cephosd: skipping device "sdb1" with mountpoint "scratch2" 
2025-05-06 14:44:26.174581 I | cephosd: old lsblk can't detect bluestore signature, so try to detect here 
2025-05-06 14:44:26.174683 E | cephosd: skipping device "nbd0", failed to get OSD information. failed to read signature from "nbd0". EOF 
2025-05-06 14:44:26.174694 I | cephosd: old lsblk can't detect bluestore signature, so try to detect here 
2025-05-06 14:44:26.174745 E | cephosd: skipping device "nbd1", failed to get OSD information. failed to read signature from "nbd1". EOF
```

In this error, the osd prepare pod failed to find any unmounted partitions. Make sure there's an unmounted partition on that worker node.

Another error I encountered related to re-upping ceph after a valid OSD was found and presumably "cleaned-up" was:

```
2025-05-09 13:14:05.949654 I | cephosd: configuring osd devices: {"Entries":{"sdb2":{"Data":-1,"Metadata":null,"Config":{"Name":"","OSDsPerDevice":0,"MetadataDevice":"","DatabaseSizeMB":0,"DeviceClass":"","InitialWeight":"","IsFilter":false,"IsDevicePathFilter":false},"PersistentDevicePaths":null,"DeviceInfo":{"name":"sdb2","parent":"sdb","hasChildren":false,"devLinks":"/dev/disk/by-id/wwn-0x5000c50071521147-part2 /dev/disk/by-path/pci-0000:82:00.0-sas-phy1-lun-0-part2 /dev/disk/by-id/scsi-35000c50071521147-part2 /dev/disk/by-partuuid/000e460c-02","size":191999508480,"uuid":"","serial":"35000c50071521147","type":"part","rotational":true,"readOnly":false,"Partitions":null,"filesystem":"","mountpoint":"","vendor":"SEAGATE","model":"ST9300653SS","wwn":"0x5000c50071521147","wwnVendorExtension":"0x5000c50071521147","empty":false,"real-path":"/dev/sdb2","kernel-name":"sdb2"},"RestoreOSD":false}}} 
2025-05-09 13:14:05.949704 I | cephclient: getting or creating ceph auth key "client.bootstrap-osd" 
2025-05-09 13:14:05.949721 D | exec: Running command: ceph auth get-or-create-key client.bootstrap-osd mon allow profile bootstrap-osd --connect-timeout=15 --cluster=rook-ceph --conf=/var/lib/rook/rook-ceph/rook-ceph.config --name=client.admin --keyring=/var/lib/rook/rook-ceph/client.admin.keyring --format json 
2025-05-09 13:14:06.294390 I | cephosd: configuring new raw device "/dev/sdb2" 
2025-05-09 13:14:06.294416 D | exec: Running command: stdbuf -oL ceph-volume raw prepare --bluestore --data /dev/sdb2 
2025-05-09 13:14:07.462748 I | cephosd: --> Raw device /dev/sdb2 is already prepared. 
2025-05-09 13:14:07.463017 D | exec: Running command: stdbuf -oL ceph-volume --log-path /tmp/ceph-log lvm list --format json 
2025-05-09 13:14:07.887813 D | cephosd: {} 
2025-05-09 13:14:07.887862 I | cephosd: 0 ceph-volume lvm osd devices configured on this node 
2025-05-09 13:14:07.887898 D | exec: Running command: stdbuf -oL ceph-volume --log-path /tmp/ceph-log raw list --format json 
2025-05-09 13:14:13.029117 D | cephosd: { "f6d925db-0130-4028-acd2-c555d53848be": { "ceph_fsid": "e0e27aff-7fba-44a1-bc9c-bbf99b4a7529", "device": "/dev/sdb2", "osd_id": 0, "osd_uuid": "f6d925db-0130-4028-acd2-c555d53848be", "type": "bluestore" } } 
2025-05-09 13:14:13.029278 I | cephosd: skipping osd.0: "f6d925db-0130-4028-acd2-c555d53848be" belonging to a different ceph cluster "e0e27aff-7fba-44a1-bc9c-bbf99b4a7529" 
2025-05-09 13:14:13.029302 I | cephosd: 0 ceph-volume raw osd devices configured on this node 
2025-05-09 13:14:13.029316 W | cephosd: skipping OSD configuration as no devices matched the storage settings for this node "gpgnode-05"
```

This is because after the OSD was cleaned up, the partition still had traces of the OSD setup on it. Follow the steps in the *Completely wiping the new partition and cache files* section above to fix this.

Remember you can run `kubectl -n rook-ceph delete pod -l app=rook-ceph-operator` to restart the osd prepare pods without having to take down the entire ceph cluster setup so far.
#### Check Ceph Cluster health

Rook provides a ceph tools pod to check the health and status of the Ceph cluster. Install this pod by running:
```bash
kubectl apply -f toolbox.yaml
```

Now, login to it:
```bash
kubectl -n rook-ceph exec -it deploy/rook-ceph-tools -- bash
```

Check the status of the ceph cluster:
```bash
ceph status
```

Example output from a 6-node setup:
```
  cluster:
    id:     416867bd-6ca2-4853-971b-9f6159a95c2d
    health: HEALTH_OK

  services:
    mon: 3 daemons, quorum a,b,c (age 8m)
    mgr: a(active, since 87s), standbys: b
    osd: 6 osds: 6 up (since 98s), 6 in (since 2m)

  data:
    pools:   1 pools, 1 pgs
    objects: 2 objects, 705 KiB
    usage:   163 MiB used, 972 GiB / 973 GiB avail
    pgs:     1 active+clean
```

# Configuring a StorageClass and PVC for Ceph

Apply these three files from the `config` directory:
```bash
kubectl apply -f cephfs.yaml
kubectl apply -f rook-cephfs-sc.yaml
kubectl apply -f ceph-pvc.yaml
```

By default, `ceph-pvc.yaml` will start the PVC with 10GB, you can change this by editing the file before applying it.

# Setting up Nextflow

With Ceph now configured on Kubernetes for distributed storage, we are ready to set up a *nextflow-manager* pod that we will use to start up nextflow tasks and workflows. This pod will be responsible for launching new pods that execute Nextflow tasks. To do this, we need a [service account](https://kubernetes.io/docs/concepts/security/service-accounts/) with the [roles](https://kubernetes.io/docs/reference/access-authn-authz/rbac/) to create and manage pods.

## Configuring a service account with the required roles

For simplicity, we will use the `default` service account. We need to create a pod access role and a pod access binding, which binds the role to the service account.

Apply these files from the `config` dir:

`kubectl apply -f pod-access-role.yaml -f pod-access-binding.yaml`

## Creating the Nextflow Manager pod

Start the pod by applying:
```bash
kubectl apply -f nf-manager-base-image.yaml
```

We can log in to the pod by running:

```bash
kubectl exec -it nextflow-manager -- /bin/bash
```

The nextflow image lacks some essential software to allow us to copy file into and out of the pod, and to conveniently edit files, so we need to install `tar`, `vim`, and `git`.
```bash
dnf install tar vim git
```

Let's also update nextflow to the latest version:
```bash
NXF_EDGE=0 nextflow self-update
```

Now exit the pod: `exit`.

Move the directory `nf-manager-pod`, containing a basic nextflow config file and some test files, to the control plane node. Then copy its contents into the workspace folder on the pod by running:
```bash
kubectl cp nf-manager-pod/. nextflow-manager:/workspace
```

## Testing Nextflow tasks

Now we have a nextflow manager pod that has a couple of nextflow files and a config ready to test our setup. I recommend having a window with
```bash
kubectl get pods -o wide --all-namespaces -w
```
running, to get a live view of pods being created.

Log back into the nextflow manager pod: `kubectl exec -it nextflow-manager -- /bin/bash`, `cd /workspace` and run:
```bash
nextflow run helloworld.nf
```

You should see one new pod start up and finish if everything has been set up correctly. The pod will finish and get cleaned up once it's done. The results of the nextflow run should be in the /workspace/work folder in the nextflow-manager pod.

To confirm that multiple parallel tasks will be launched on different nodes, run the parallel hello world workflow:
```bash
nextflow run helloparallel.nf
```

You should see three pods start up, one per task, on separate nodes.

**Big thanks to [Vasilis Bountris](https://bountrisv.github.io) for providing instructions on setting up the nextflow manager pod and the test nextflow scripts!**

## Setting $NXF_ASSETS to run workflows

Finally, to run an NF-Core workflow, make sure to set the `NXF_ASSETS` environment variable to a specific folder (doesn't actually matter where it is), e.g.:

`NXF_ASSETS=./nf_assets nextflow run nf-core/rnaseq --outdir rnaseq_out -profile test,k8s -resume`

# Setting up Prometheus
## Install helm

```bash
curl https://baltocdn.com/helm/signing.asc | gpg --dearmor | sudo tee /usr/share/keyrings/helm.gpg > /dev/null
sudo apt-get install apt-transport-https --yes
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/helm.gpg] https://baltocdn.com/helm/stable/debian/ all main" | sudo tee /etc/apt/sources.list.d/helm-stable-debian.list
sudo apt-get update
sudo apt-get install helm
```
## Install Prometheus Operator

```shell
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update
helm install prometheus prometheus-community/kube-prometheus-stack --namespace monitoring --create-namespace -f prometheus-values.yaml --wait
```
where `prometheus-values.yaml` is in the `config` dir.
## Access the Prometheus portal

- Port forward from the control plane to the GPG node's local network: `kubectl port-forward -n monitoring svc/prometheus-operated 9090:9090`
- Tunnel to your local machine using `ssh`, e.g.:  `ssh -J dcs-ssh1 youssef@gpgnode-04 -L 8080:localhost:9090`
- Access the portal from your browser on `localhost:8080`
# Setting up Kepler

```
helm install kepler kepler/kepler --namespace monitoring -f kepler-values.yaml --wait
```
where `kepler-values.yaml` is in the `config` dir.

Now we need to connect Kepler to Prometheus via a service and servicemonitor:

```bash
kubectl apply -f kepler-service.yaml -f kepler-servicemonitor.yaml
```

Wait 1-2mins and in `Status > Target health` in the Prometheus portal, you should see `serviceMonitor/monitoring/kepler-monitor/0` with as many endpoints as nodes you have.

# Tearing down the cluster

Run the script `scripts/reset_k8s.sh` on each nodes (starting with the worker nodes) to reset kubernetes.

Optionally clean up apt packages:
```shell
sudo apt-get purge -y containerd
sudo apt-mark unhold kubelet kubeadm kubectl
sudo apt-get purge -y kubelet kubeadm kubectl
sudo apt-get autoremove -y
sudo rm /etc/apt/sources.list.d/kubernetes.list
sudo rm /etc/apt/keyrings/kubernetes-apt-keyring.gpg
sudo apt-get update
```

Or simply run `scripts/reset_k8s_and_uninstall_packages.sh` to reset k8s and clean up apt stuff.

Then run the script `combine_sdb_paritions.sh` to combine the partitions, if you partitioned the drives to use Ceph.