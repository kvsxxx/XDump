<?php
$directory = __DIR__ . "/../../dump";
if (!file_exists($directory)) {
    echo "{}";
    die();
}

$data = json_decode(file_get_contents("$directory/checkpoint.json"), true);

$totalSize = 0;
$currentSize = 0;
$currentDumpCount = 0;
$dumpSize = 0;

$current = $data['current_dump_path'];
$currentDir = $current ? realpath("$directory/$current") : null;

foreach (
    new RecursiveIteratorIterator(
        new RecursiveDirectoryIterator(
            $directory,
            FilesystemIterator::SKIP_DOTS
        )
    ) as $file
) {
    if (!$file->isFile()) {
        continue;
    }

    $path = $file->getPathname();
    $size = $file->getSize();

    $totalSize += $size;

    if (str_ends_with($file, '.dump')) {
        $dumpSize += $size;
    }

    if (
        $currentDir &&
        str_starts_with(realpath($path), $currentDir)
    ) {
        $currentSize += $size;

        if (str_ends_with($path, '.dump')) {
            $currentDumpCount++;
        }
    }
}

$data['current_chat_dump_count'] = $currentDumpCount;
$data['current_dump_size'] = $currentSize;
$data['all_dumps_size'] = $totalSize;
$data['total_dump_size'] = $dumpSize;
$data['total_file_size'] = $totalSize - $dumpSize;

echo json_encode($data);

?>