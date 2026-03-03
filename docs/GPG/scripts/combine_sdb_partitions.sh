sudo umount /dev/sdb1 || true

sudo parted -s /dev/sdb mklabel gpt
sudo parted -s /dev/sdb mkpart primary ext4 0% 100%

sleep 2

sudo e2fsck -f /dev/sdb1
sudo resize2fs /dev/sdb1

sudo mount /dev/sdb1 /scratch2