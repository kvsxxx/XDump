<?php


$directory = __DIR__ . '/../../dump';
if (!file_exists($directory)) {
    echo "[]";
    die();
}

// Konvertiert Twitter's Zeitformate zu Sekunden für Vergleich
function parseMessageTime($timeStr) {
    if (empty($timeStr)) return PHP_INT_MAX; // Am weitesten oben (älteste)
    
    if (preg_match('/^(\d+)([dwmy])$/i', trim($timeStr), $matches)) {
        $num = (int)$matches[1];
        $unit = strtolower($matches[2]);
        
        switch ($unit) {
            case 'd': return $num * 86400;           // Tage
            case 'w': return $num * 604800;          // Wochen
            case 'm': return $num * 2592000;         // Monate (30 Tage)
            case 'y': return $num * 31536000;        // Jahre
        }
    }
    
    return PHP_INT_MAX;
}

// Konvertiert Sekunden zurück zu Twitter Format
function secondsToTwitterFormat($seconds) {
    if ($seconds < 86400) {
        return null; // Weniger als 1 Tag
    }
    
    if ($seconds < 604800) {
        $days = ceil($seconds / 86400);
        return $days . "d";
    }
    
    if ($seconds < 2592000) {
        $weeks = ceil($seconds / 604800);
        return $weeks . "w";
    }
    
    if ($seconds < 31536000) {
        $months = ceil($seconds / 2592000);
        return $months . "m";
    }
    
    $years = ceil($seconds / 31536000);
    return $years . "y";
}

// Berechnet die aktualisierte lastMessageTime mit Dump-Alter
function updateMessageTime($lastMessageTime, $jsonPath) {
    if (empty($lastMessageTime) || !file_exists($jsonPath)) {
        return $lastMessageTime;
    }
    
    // Parse die Original-Zeit zu Sekunden
    $messageSeconds = parseMessageTime($lastMessageTime);
    if ($messageSeconds === PHP_INT_MAX) {
        return $lastMessageTime;
    }
    
    // Berechne wie lange der Dump alt ist
    $dumpAge = time() - filemtime($jsonPath);
    
    // Addiere die Zeit
    $totalSeconds = $messageSeconds + $dumpAge;
    
    // Konvertiere zurück zu Twitter Format
    $updated = secondsToTwitterFormat($totalSeconds);
    return $updated ?? $lastMessageTime;
}

$chats = [];
foreach (new DirectoryIterator($directory) as $dir) {
    if ($dir->isDot() || !$dir->isDir()) continue;
    $dirname = $dir->getFilename();
    $json = "$directory/$dirname/info.json";
    if (!file_exists($json)) continue;
    $info = json_decode(file_get_contents($json), true);
    
    // Update lastMessageTime falls vorhanden
    if (!empty($info['lastMessageTime'])) {
        $info['lastMessageTime'] = updateMessageTime($info['lastMessageTime'], $json);
    }
    
    $chats[] = ['dirname' => $dirname, 'info' => $info];
}

usort($chats, function($a, $b) {
    return ($a['info']['position'] - $b['info']['position']) * $a['info']['order'];
});

echo json_encode($chats);

?>