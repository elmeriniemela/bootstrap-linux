
from .lib import _packages, _aur, api

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
