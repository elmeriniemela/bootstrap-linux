#!/usr/bin/bash


new_user=elmeri

ln -sf /usr/share/zoneinfo/Europe/Helsinki /etc/localtime
timedatectl set-ntp true
hwclock --systohc
# For Intel processors, install the intel-ucode package. For AMD processors, install the amd-ucode package.
pacman -S grub efibootmgr intel-ucode
grub-install --target=x86_64-efi --efi-directory=boot --bootloader-id=GRUB
grub-mkconfig -o /boot/grub/grub.cfg

passwd

grep $new_user /etc/passwd > /dev/null || (useradd -m -G video,wheel,rfkill -s /bin/bash $new_user && passwd $new_user)

git clone https://github.com/elmeriniemela/bootstrap-linux.git /home/$new_user/.config/bootstrap-linux
cd /home/$new_user/.config/bootstrap-linux
pip install -e .
chown $new_user:$new_user -R /home/$new_user/.config

bootstrap-linux distro
bootstrap-linux secure
bootstrap-linux swapfile 8

sudo -u $new_user bootstrap-linux desktop
sudo -u $new_user bootstrap-linux dotfiles

