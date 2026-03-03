sudo umount /dev/sdb1

sudo e2fsck -f /dev/sdb1
sudo resize2fs /dev/sdb1 100G

sudo apt -y install fdisk
sudo sfdisk /dev/sdb <<EOF
,108G,L
,,L
EOF

sudo partprobe
sleep 2

sudo resize2fs /dev/sdb1
sudo e2fsck -f /dev/sdb1

sudo mount /dev/sdb1 /scratch2

if [ ! -b /dev/sdb2 ]; then
  echo "Error: /dev/sdb2 not found. Wait a moment or check partitioning."
  return 1
fi

sudo wipefs -a /dev/sdb2