<?php
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
foreach (new DirectoryIterator('./dump') as $dir) {
    if ($dir->isDot() || !$dir->isDir()) continue;
    $dirname = $dir->getFilename();
    $json = "./dump/$dirname/info.json";
    $info = file_exists($json) ? json_decode(file_get_contents($json), true) : [];
    
    // Update lastMessageTime falls vorhanden
    if (!empty($info['lastMessageTime'])) {
        $info['lastMessageTime'] = updateMessageTime($info['lastMessageTime'], $json);
    }
    
    $chats[] = ['dirname' => $dirname, 'info' => $info];
}

// Nach letzter Nachrichtenzeit sortieren (neueste zuerst)
// usort($chats, function($a, $b) {
//     $timeA = parseMessageTime($a['info']['lastMessageTime'] ?? '');
//     $timeB = parseMessageTime($b['info']['lastMessageTime'] ?? '');
//     return $timeA - $timeB; // Neueste zuerst (kleinere Zahlen)
// });

usort($chats, function($a, $b) {
    return ($a['info']['position'] - $b['info']['position']) * $a['info']['order'];
});

?>
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>DM Archive</title>
    <script src="https://cdn.jsdelivr.net/npm/@tailwindcss/browser@4"></script>
    <style>
        body { background: #000; color: #e7e9ea; }
    </style>
</head>
<body class="min-h-screen">
    <div class="max-w-xl mx-auto py-8 px-4">
        <h1 class="text-2xl font-bold mb-6">DM Archive</h1>
        <div class="flex flex-col gap-1">
            <?php foreach ($chats as $chat): ?>
            <a href="chat.php?for=<?= urlencode($chat['dirname']) ?>"
               class="flex items-center gap-4 px-4 py-3 rounded-xl hover:bg-white/5 transition cursor-pointer">
                <?php if(count($chat['info']['avatars']) > 1) { ?>
                    <div>
                        <div class="flex flex-row-reverse rounded-lg" style="margin-top: calc(12px);">
                            <?php 
                            $avatars = $chat['info']['avatars'];
                            $lastAvatar = array_pop($avatars);
                            foreach ($avatars as $avatar): 
                            ?>
                            <div class="rounded-full bg-background" style="z-index: 2; padding: 2px; width: calc(44px); height: calc(44px);">
                                <div class="min-size flex overflow-hidden rounded-full bg-gray-300 min-h-10 min-w-10 size-10">
                                    <img alt="user avatar" class="size-full brightness-100 [dynamic-range-limit:standard]" loading="lazy" src="<?= $avatar ?>" draggable="false">
                                </div>
                            </div>
                            <?php endforeach; ?>
                            <div style="width: 40px; height: 40px; margin-inline-end: calc(-28px); margin-top: calc(-12px);">
                                <div class="min-size flex overflow-hidden rounded-full bg-gray-300 min-h-10 min-w-10 size-10">
                                    <img alt="user avatar" class="size-full brightness-100 [dynamic-range-limit:standard]" loading="lazy" src="<?= $lastAvatar ?>" draggable="false">
                                </div>
                            </div>
                        </div>
                    </div>
                <?php } else { ?>
                <div class="w-12 h-12 rounded-full bg-gray-700 flex items-center justify-center text-xl font-bold shrink-0 overflow-hidden">
                    <?php if (!empty($chat['info']['avatar'])): ?>
                        <img src="<?= htmlspecialchars($chat['info']['avatar']) ?>" class="w-full h-full object-cover">
                    <?php else: ?>
                        <?= strtoupper(substr($chat['info']['username'], 0, 1)) ?>
                    <?php endif; ?>
                </div>
                <?php } ?>
                <div class="flex flex-col min-w-0 flex-1">
                    <div class="flex justify-between items-start gap-2 mb-0.5">
                        <span class="font-bold truncate"><?= htmlspecialchars($chat['info']['name'] ?? $chat['info']['username']) ?></span>
                        <span class="text-gray-600 text-sm font-light flex-shrink-0"><?= $chat['info']['lastMessageTime'] ?></span>
                    </div>
                    <?php if (!$chat['info']['isGroupchat']) { ?>
                    <span class="text-gray-500 text-sm"><?= htmlspecialchars($chat['info']['username']) ?></span>
                    <?php } ?>
                    <span class="text-gray-100 truncate"><?= htmlspecialchars($chat['info']['lastMessage']) ?></span>
                </div>
            </a>
            <?php endforeach; ?>
        </div>
    </div>
</body>
</html>