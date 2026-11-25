<?php
// Capacidades del plugin.

defined('MOODLE_INTERNAL') || die();

$capabilities = [
    // Consumo de la función webservice del snapshot (expone datos personales
    // de todo el alumnado). Sin arquetipos: se asigna explícitamente al rol
    // del usuario de servicio web; el administrador la tiene siempre.
    'local/fpvirtual_gestion_alumnado:usewebservice' => [
        'captype' => 'read',
        'riskbitmask' => RISK_PERSONAL,
        'contextlevel' => CONTEXT_SYSTEM,
        'archetypes' => [],
    ],

    // Ver estado de la última ejecución y el historial de logs.
    'local/fpvirtual_gestion_alumnado:viewstatus' => [
        'captype' => 'read',
        'contextlevel' => CONTEXT_SYSTEM,
        'archetypes' => [
            'manager' => CAP_ALLOW,
        ],
    ],

    // Lanzar el proceso manualmente (dry-run o apply).
    'local/fpvirtual_gestion_alumnado:launch' => [
        'captype' => 'write',
        'contextlevel' => CONTEXT_SYSTEM,
        'archetypes' => [
            'manager' => CAP_ALLOW,
        ],
    ],
];
