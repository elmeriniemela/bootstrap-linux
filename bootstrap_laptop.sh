#!/usr/bin/bash


new_user=elmeri

ln -sf /usr/share/zoneinfo/Europe/Helsinki /etc/localtime
timedatectl set-ntp true
hwclock --systohc
# For Intel processors, install the intel-ucode package. For AMD processors, install the amd-ucode package.
pacman -S --needed grub efibootmgr intel-ucode archlinux-keyring vim git python python-pip

sed -i '/^HOOKS=/c\HOOKS=(base udev autodetect keyboard keymap consolefont modconf block encrypt filesystems fsck)' /etc/mkinitcpio.conf
mkinitcpio -p linux

sed -i "/^GRUB_CMDLINE_LINUX=/c\GRUB_CMDLINE_LINUX=\"cryptdevice=LABEL=cryptrootpart:cryptroot root=/dev/mapper/cryptroot\"" /etc/default/grub


grub-install --target=x86_64-efi --efi-directory=/boot --bootloader-id=INSTALLED-ARCH-GRUB
grub-mkconfig -o /boot/grub/grub.cfg

passwd

grep $new_user /etc/passwd > /dev/null || (useradd -m -G video,wheel,rfkill,systemd-journal -s /bin/bash $new_user && passwd $new_user)

git clone https://github.com/elmeriniemela/bootstrap-linux.git /home/$new_user/.config/bootstrap-linux
cd /home/$new_user/.config/bootstrap-linux
pip install -e .
chown $new_user:$new_user -R /home/$new_user/.config

bootstrap-linux distro
bootstrap-linux secure
bootstrap-linux swapfile 8

sudo -u $new_user bootstrap-linux desktop
sudo -u $new_user bootstrap-linux dotfiles

