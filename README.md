# Linux Enviroment install scripts

I Reinstall my system regularly, so having apps and bash scripts in version control is very useful.

Install instructions:

* `git clone https://github.com/elmeriniemela/bootstrap-linux.git ~/.config/bootstrap-linux`
* `cd ~/.config/bootstrap-linux`
* `sudo -H pip install -e .`

For laptop initial setup:

* Boot into arch ISO.
* `loadkeys fi`
* `iwctl --passphrase <passphrase> station wlan0 connect eramies-5G`
* `timedatectl set-ntp true`
* `timedatectl status`

* Partition table with `fdisk`
* `cryptsetup --label=cryptrootpart -y -v luksFormat /dev/<root_partition>`
* `cryptsetup open /dev/<root_partition> cryptroot`
* `mkfs.ext4 /dev/mapper/cryptroot`
* `mkfs.fat -F32 /dev/<efi_partition>`
* `e2label /dev/mapper/cryptroot arch`
* `fatlabel /dev/<efi_partition> EFI`
* `mount /dev/mapper/cryptroot /mnt`
* `mkdir /mnt/boot`
* `mount /dev/<efi_partition> /mnt/boot`
* `lsblk -o name,size,label,mountpoint,fstype`

* `reflector --country Finland --sort rate --save /etc/pacman.d/mirrorlist`
* `pacstrap /mnt base linux linux-firmware`
* `genfstab -U /mnt >> /mnt/etc/fstab`
* `arch-chroot /mnt`
* `timedatectl status`
* `bash <(curl -sL https://raw.githubusercontent.com/elmeriniemela/bootstrap-linux/arch/bootstrap_laptop.sh)`


Usage instructions:

* `bootstrap-linux` <-- this will start the CLI-interface and print available functions


![alt text](https://raw.githubusercontent.com/elmeriniemela/bootstrap-linux/arch/files/bootstrap-linux.png)

### TODO:

* Xorg disable screen off:
    * `xset -dpms` for disabling energy star features and
    * `xset s off` for disable screensaver
    * Run these in  `~/.xprofile` or `/etc/xprofile`?
* Xorg disable right mouse up click (ButtonRelease on 3).
    * Maybe this is a feature that I should learn?
    * https://www.reddit.com/r/linuxquestions/comments/dbf1ht/disable_mouse_button_release_x11/
* Awesome disable notifications:
    * Do a widget that toggles naughty
    * https://awesomewm.org/doc/api/libraries/naughty.html
* Application that better handles screen shutdown
* Firefox Google Meets share screen select sreen
* Copyq force center of screen and size
