
from .lib import (
    _lineinfile,
    _enable,
    _run,
    _packages,
    _aur,
    api,
)

@api
def nvidia_prime():
    "Install nvidia prime"
    # https://wiki.archlinux.org/title/PRIME#PRIME_render_offload
    _packages([
        'nvidia-prime',
        'mesa-utils',
        'vulkan-tools',
    ])
    _aur([
        'nvidia-prime-rtd3pm', # Configure your discrete NVIDIA GPU to power down when not in use.
    ])
    # cat /sys/bus/pci/devices/0000:03:00.0/power/runtime_status


@api
def latex():
    "Install latex"
    _packages([
        'texlive-basic',
        'texlive-latex',
        'texlive-binextra',
        'texlive-latexrecommended',
        'texlive-fontsrecommended',
        'texlive-fontsextra',
        'texlive-xetex',
        'texlive-luatex',
        'texlive-latexextra',
        'texlive-pictures',
        'texlive-bibtexextra',
    ])

@api
def server():
    '''Setup server.
    '''
    _packages([
        'php',
        'php-pgsql',
        'nginx',
        'nginx-mod-stream', # for electrs
        'php-apcu',
        'php-gd',
        'php-intl',
        'php-cgi',
        'php-fpm',
        'php-imagick',
        'php-sodium',
    ])

    _aur([
        'ums',
    ], deps=True)

    php_extensions = [
        'bcmath',
        'curl',
        'exif',
        'gd',
        'gmp',
        'intl',
        'pdo_pgsql',
        'pgsql',
        'sodium',
        'sysvsem',
        'zip',
        'fileinfo', # (highly recommended, enhances file analysis performance; required to set custom theming images or if PHP module imagick with SVG support is installed)
        # 'imagick', # this should be enabled in /etc/php/conf.d/imagick.ini
        # 'apcu', # this should be enabled in /etc/php/conf.d/apcu.ini
    ]
    _lineinfile({'/etc/php/conf.d/apcu.ini': 'extension=apcu.so'})
    _lineinfile({'/etc/php/conf.d/apcu.ini': 'apc.enable_cli=1'})
    _lineinfile({'/etc/php/conf.d/imagick.ini': 'extension=imagick'})

    _run([
        'chmod 755 /home/elmeri' # nextcloud needs this.
    ])
    _run([f"sudo sed -i 's/;extension={ext}/extension={ext}/g' /etc/php/php.ini" for ext in php_extensions])


    _enable(['nginx', 'php-fpm'])
