# Stop and disable k8s service
sudo systemctl stop kubelet
sudo systemctl disable kubelet

# Reset node state
sudo kubeadm reset --cri-socket /var/run/containerd/containerd.sock --force

# Remove CNI config files
sudo rm -rf /etc/cni/net.d

# Remove kube files
rm -rf ~/.kube
sudo rm -rf /etc/kubernetes
sudo rm -rf /var/lib/etcd
sudo rm -rf /var/lib/kubelet
sudo rm -rf /var/lib/cni
sudo rm -rf /run/kubernetes

# Remove ceph and rook files
sudo rm -rf /var/lib/rook /var/lib/ceph

# Stop and diable containerd
sudo systemctl stop containerd
sudo rm -rf /var/lib/containerd
sudo systemctl disable containerd

# Clear iptables rules
sudo iptables -F
sudo iptables -t nat -F
sudo iptables -t mangle -F
sudo iptables -X

# Unload kernel modules
sudo modprobe -r br_netfilter
sudo modprobe -r overlay

# Re-enable swap
sudo swapon --all
