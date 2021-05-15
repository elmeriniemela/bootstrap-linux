# Linux Enviroment install scripts

I Reinstall my system regularly, so having apps and bash scripts in version control is very useful.

Install instructions:

* `git clone https://github.com/elmeriniemela/bootstrap-linux.git ~/.config/bootstrap-linux`
* `cd ~/.config/bootstrap-linux`
* `sudo -H pip install -e .`

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