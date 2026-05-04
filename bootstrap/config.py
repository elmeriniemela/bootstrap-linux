
import os
import subprocess

from .lib import (
    _path,
    _enable,
    _link,
    _lineinfile,
    _copy,
    _run,
    _packages,
    _aur,
    api,
    FILES_DIR,
)



@api
def pgtune():
    '''Alter postgres according to pgtune
    # DB Version: 18
    # OS Type: linux
    # DB Type: oltp
    # Total Memory (RAM): 64 GB
    # CPUs num: 14
    # Data Storage: ssd

    '''
    postgres_config = {
        'shared_buffers': '16GB',
        'effective_cache_size': '48GB',
        'maintenance_work_mem': '2GB',
        'checkpoint_completion_target': '0.9',
        'wal_buffers': '16MB',
        'default_statistics_target': '100',
        'random_page_cost': '1.1',
        'effective_io_concurrency': '200',
        'work_mem': '100MB',
        'huge_pages': 'try',
        'min_wal_size': '2GB',
        'max_wal_size': '8GB',
        'max_worker_processes': '14',
        'max_parallel_workers_per_gather': '4',
        'max_parallel_workers': '14',
        'max_parallel_maintenance_workers': '4',
        'log_min_duration_statement': '100',
    }

    for key, value in postgres_config.items():
        try:
            _run([
                f"""psql postgres -c "ALTER SYSTEM SET {key} = '{value}'" """,
            ])
        except:
            pass


@api
def local_ufw():
    ''' Machine with only local network connections. Use with archinstall d base installation.
    '''
    _enable(['ufw'], try_now=True)
    _run([
        'sudo ufw default deny incoming',
        'sudo ufw default deny outgoing',
        'sudo ufw allow out to 192.168.1.250',
        'sudo ufw enable',
    ])


@api
def secure():
    ''' Install and setup ufw and fail2ban.
    '''
    _packages(['ufw', 'fail2ban'], flags=('-S', '--needed'))
    _enable(['fail2ban', 'ufw'])
    _run([
        # 'sudo ufw allow 22/tcp',
        # 'sudo ufw allow 80/tcp',
        # 'sudo ufw allow 443/tcp',
        # 'sudo ufw allow syncthing',
        # 'sudo ufw allow from 192.168.1.0/16',
        'sudo ufw default deny incoming',
        'sudo ufw default allow outgoing',
        'sudo ufw enable',
    ])

@api
def swapfile(gigabytes=False):
    ''' Generate and enable a swapfile
    '''
    if not gigabytes:
        kilobytes = int(subprocess.check_output("grep MemTotal /proc/meminfo | tr -s ' ' | cut -d ' ' -f2", shell=True, encoding='utf-8'))
        gigabytes = int(kilobytes/(1024*1024))
        if gigabytes % 2 != 0:
            gigabytes += 1

    dst = '/home/swapfile'
    if not os.path.isfile(dst):
        print(f"Create swapfile of {gigabytes}Gb")
        _run([
            f'sudo dd if=/dev/zero of={dst} bs=1M count={int(gigabytes) * 1024} status=progress',
            f'sudo chmod 600 {dst}',
            f'sudo mkswap {dst}',
            f'sudo swapon {dst}',
        ])
        _lineinfile({
            '/etc/fstab': f'{dst} none swap defaults 0 0',
        })
        _run(['sudo findmnt --verify --verbose'])
    else:
        print("Swapfile already exists")

@api
def bashrc():
    ''' Generate global bashrc
    '''
    if os.geteuid() == 0:
        print("Do not run this as root")
        return

    _lineinfile({
        '/etc/bash.bashrc': f'[ -r {FILES_DIR}/global.bashrc   ] && . {FILES_DIR}/global.bashrc',
    })

    _run([
        'rm -f ~/.bashrc',
        'rm -f ~/.bash_profile',
        'sudo rm -f /root/.bash_profile',
        'sudo rm -f /root/.bashrc',
    ])

@api
def dotfiles():
    ''' This setups basic configuration: 1. Generate global bashrc 2. Clone dotfiles
    '''
    bashrc()
    if not os.path.exists(_path('~/.dotfiles')):
        _run([
            'git clone --bare https://github.com/elmeriniemela/dotfiles.git $HOME/.dotfiles',
            'git --git-dir=$HOME/.dotfiles/ --work-tree=$HOME reset --hard',
            'git --git-dir=$HOME/.dotfiles/ --work-tree=$HOME submodule update --init',
            'git --git-dir=$HOME/.dotfiles/ --work-tree=$HOME config --local status.showUntrackedFiles no',
        ])

@api
def gitconfig():
    "Enable ~/.gitconfig"
    _link({
        '.gitconfig': '~/.gitconfig',
    })



@api
def link_agentmd():
    "Enable AGENTS.md"
    _link({'skills/AGENTS.md': f'{os.getcwd()}/AGENTS.md'}, allow_sudo=False)
    _link({'skills/AGENTS.md': f'{os.getcwd()}/GEMINI.md'}, allow_sudo=False)
    _link({'skills/AGENTS.md': f'{os.getcwd()}/CLAUDE.md'}, allow_sudo=False)

