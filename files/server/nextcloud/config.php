<?php
$CONFIG = array (
  'datadirectory' => '/mnt/HDD/nextcloud/data/',
  'skeletondirectory' => '',
  'memcache.local' => '\OC\Memcache\APCu',
  'default_phone_region' => 'FI',
  'logfile' => '/var/log/nextcloud/nextcloud.log',
  'filesystem_check_changes' => 1,
  'apps_paths' =>
  array (
    0 =>
    array (
      'path' => '/usr/share/webapps/nextcloud/apps',
      'url' => '/apps',
      'writable' => false,
    ),
    1 =>
    array (
      'path' => '/var/lib/nextcloud/apps',
      'url' => '/wapps',
      'writable' => true,
    ),
  ),
  'passwordsalt' => 'REMOVED-FROM-GITHUB',
  'secret' => 'REMOVED-FROM-GITHUB',
  'trusted_domains' =>
  array (
    0 => 'nextcloud.eniemela.fi',
  ),
  'dbtype' => 'pgsql',
  'version' => '22.2.3.0',
  'overwrite.cli.url' => 'https://nextcloud.eniemela.fi',
  'dbname' => 'nextcloud',
  'dbhost' => 'localhost',
  'dbport' => '',
  'dbtableprefix' => 'oc_',
  'dbuser' => 'nextcloud',
  'dbpassword' => 'REMOVED-FROM-GITHUB',
  'installed' => true,
  'instanceid' => 'REMOVED-FROM-GITHUB',
  'theme' => '',
  'loglevel' => 2,
  'maintenance' => false,
  'mail_smtpmode' => 'smtp',
  'mail_smtpsecure' => 'ssl',
  'mail_sendmailmode' => 'smtp',
  'mail_from_address' => 'niemela.elmeri',
  'mail_domain' => 'gmail.com',
  'mail_smtpauthtype' => 'LOGIN',
  'mail_smtpauth' => 1,
  'mail_smtphost' => 'smtp.gmail.com',
  'mail_smtpport' => '465',
  'mail_smtpname' => 'niemela.elmeri',
  'mail_smtppassword' => 'REMOVED-FROM-GITHUB',
);
