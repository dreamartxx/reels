<?php
$path=parse_url($_SERVER['REQUEST_URI'],PHP_URL_PATH);
if(str_starts_with($path,'/api/')){require __DIR__.'/../build/hostinger/public_html/api/index.php';return true;}
$file=__DIR__.'/../build/hostinger/public_html'.$path;
if(is_file($file))return false;
readfile(__DIR__.'/../build/hostinger/public_html/index.html');return true;
