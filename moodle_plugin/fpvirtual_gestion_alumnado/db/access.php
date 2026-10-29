<?php
// Capacidades del plugin.

defined('MOODLE_INTERNAL') || die();

$capabilities = [
    // Consumo de la función webservice del snapshot. El acceso real se
    // restringe además configurando el servicio web externo (usuarios
    // autorizados con token); aquí se permite a cualquier usuario
    // autenticado para no bloquear al usuario de servicio.
    'local/fpvirtual_gestion_alumnado:usewebservice' => [
        'captype' => 'read',
        'contextlevel' => CONTEXT_SYSTEM,
        'archetypes' => [
            'user' => CAP_ALLOW,
        ],
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
