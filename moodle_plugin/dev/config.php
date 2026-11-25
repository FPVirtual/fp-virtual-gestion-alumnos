<?php
// config.php del entorno Docker de desarrollo/tests (no es de ningún entorno real).
unset($CFG);
global $CFG;
$CFG = new stdClass();

$CFG->dbtype    = 'mariadb';
$CFG->dblibrary = 'native';
$CFG->dbhost    = 'db';
$CFG->dbname    = 'moodle';
$CFG->dbuser    = 'moodle';
$CFG->dbpass    = 'moodle';
$CFG->prefix    = 'mdl_';
$CFG->dboptions = ['dbcollation' => 'utf8mb4_unicode_ci'];

$CFG->wwwroot   = 'http://localhost:8000';
$CFG->dataroot  = '/var/www/moodledata';
$CFG->admin     = 'admin';
$CFG->directorypermissions = 0777;

$CFG->phpunit_prefix   = 'phpu_';
$CFG->phpunit_dataroot = '/var/www/phpunitdata';

$CFG->debug = E_ALL;
$CFG->debugdisplay = 1;

require_once(__DIR__ . '/lib/setup.php');
