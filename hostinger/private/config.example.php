<?php
// Copy OUTSIDE public_html to ../reels-private/config.php. Never commit credentials.
return [
 'dsn' => 'mysql:host=localhost;dbname=YOUR_DATABASE;charset=utf8mb4',
 'db_user' => 'YOUR_DATABASE_USER', 'db_password' => 'YOUR_DATABASE_PASSWORD',
 'origin' => 'https://lightgrey-butterfly-581707.hostingersite.com',
 'password_hash' => 'GENERATE_WITH_scripts/configure_cloud.py',
 'worker_hash' => 'SHA256_OF_WORKER_TOKEN',
 'storage' => __DIR__.'/storage',
];
