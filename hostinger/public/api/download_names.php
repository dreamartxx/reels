<?php
declare(strict_types=1);
function downloadName(string $name,int $createdAt,string $jobId,string $filename): string {
 $name=strtr($name,['Ç'=>'C','Ğ'=>'G','İ'=>'I','Ö'=>'O','Ş'=>'S','Ü'=>'U','ç'=>'c','ğ'=>'g','ı'=>'i','ö'=>'o','ş'=>'s','ü'=>'u']);
 $slug=rtrim(substr(trim(preg_replace('/[^a-z0-9]+/','-',strtolower($name)),'-'),0,80),'-')?:'reels';
 $stamp=(new DateTimeImmutable('@'.$createdAt))->setTimezone(new DateTimeZone('Europe/Istanbul'))->format('Ymd-His');
 return $slug.'_'.$stamp.'_'.substr($jobId,0,12).'.'.pathinfo($filename,PATHINFO_EXTENSION);
}
