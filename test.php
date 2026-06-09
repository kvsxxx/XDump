<?php

$file = $_GET['file'];

$fp = fopen($file, 'rb');
$data = fread($fp, filesize($file));
fclose($fp);

$content = gzuncompress($data);
echo $content;


?>