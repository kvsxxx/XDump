<?php 
$for = $_GET['for'] ?? '';
$path = "./dump/$for";
if (!$for || !is_dir($path)) {
    header('Location: index.php');
    exit;
}
$info = json_decode(file_get_contents("$path/info.json"), true);
if ($info['isGroupchat'])
    $uname = $info['name'];
else
    $uname = $info['username'];
$members = $info['members'] ?? [];
$isGroup = $info['isGroupchat'] ?? false;

?>
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title><?= htmlspecialchars($uname) ?> — DM Archive</title>
    <script src="https://cdn.jsdelivr.net/npm/@tailwindcss/browser@4"></script>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap');

        * { box-sizing: border-box; }

        :root {
            font-family: "Chirp", "Inter", -apple-system, BlinkMacSystemFont, sans-serif;
            --primary: #1d9bf0;
            --bg: #000;
            --surface: #0f0f0f;
            --border: #2f3336;
            --text: #e7e9ea;
            --muted: #71767b;
        }

        body {
            background: var(--bg);
            color: var(--text);
            margin: 0;
            min-height: 100vh;
        }

        /* ── Clickable header title area ── */
        #header-info {
            cursor: <?= $isGroup && count($members) > 0 ? 'pointer' : 'default' ?>;
            border-radius: 8px;
            padding: 4px 8px;
            margin: -4px -8px;
            transition: background 0.15s;
            user-select: none;
        }
        <?php if ($isGroup && count($members) > 0): ?>
        #header-info:hover { background: rgba(255,255,255,0.06); }
        #header-info:active { background: rgba(255,255,255,0.1); }
        <?php endif; ?>

        /* ── Members Panel (slide-in from right) ── */
        #members-overlay {
            position: fixed;
            inset: 0;
            background: rgba(0,0,0,0.5);
            z-index: 200;
            opacity: 0;
            pointer-events: none;
            transition: opacity 0.25s ease;
        }
        #members-overlay.open {
            opacity: 1;
            pointer-events: all;
        }
        #members-panel {
            position: fixed;
            top: 0;
            right: 0;
            bottom: 0;
            width: 300px;
            max-width: 90vw;
            background: #16181c;
            border-left: 1px solid var(--border);
            z-index: 201;
            transform: translateX(100%);
            transition: transform 0.28s cubic-bezier(0.4, 0, 0.2, 1);
            display: flex;
            flex-direction: column;
            overflow: hidden;
        }
        #members-panel.open {
            transform: translateX(0);
        }
        #members-panel-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 16px 20px;
            border-bottom: 1px solid var(--border);
            flex-shrink: 0;
        }
        #members-panel-title {
            font-weight: 700;
            font-size: 17px;
        }
        #members-panel-close {
            display: flex;
            align-items: center;
            justify-content: center;
            width: 34px;
            height: 34px;
            border-radius: 50%;
            border: none;
            background: transparent;
            color: var(--text);
            cursor: pointer;
            transition: background 0.15s;
        }
        #members-panel-close:hover { background: rgba(255,255,255,0.08); }
        #members-list {
            overflow-y: auto;
            flex: 1;
            padding: 8px 0;
        }
        #members-list::-webkit-scrollbar { width: 4px; }
        #members-list::-webkit-scrollbar-track { background: transparent; }
        #members-list::-webkit-scrollbar-thumb { background: #333; border-radius: 2px; }
        .member-item {
            display: flex;
            align-items: center;
            gap: 12px;
            padding: 10px 20px;
            transition: background 0.15s;
            cursor: pointer;
        }
        .member-item:hover { background: rgba(255,255,255,0.04); }
        .member-avatar {
            width: 44px;
            height: 44px;
            border-radius: 50%;
            background: #333;
            flex-shrink: 0;
            overflow: hidden;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: 700;
            font-size: 16px;
            color: #fff;
        }
        .member-avatar img {
            width: 100%;
            height: 100%;
            object-fit: cover;
        }
        .member-info { min-width: 0; flex: 1; }
        .member-name {
            font-weight: 600;
            font-size: 15px;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }
        .member-status {
            font-size: 12px;
            color: var(--primary);
            margin-top: 2px;
        }
        #members-count {
            font-size: 13px;
            color: var(--muted);
            padding: 8px 20px 4px;
        }

        /* ── Messages container ── */
        #messages-wrap {
            max-width: 80vw;
            margin: 0 auto;
            padding: 24px 0 80px;
        }

        /* ── Header ── */
        #chat-header {
            position: sticky;
            top: 0;
            z-index: 100;
            display: flex;
            align-items: center;
            gap: 16px;
            padding: 12px 16px;
            background: rgba(0,0,0,0.85);
            backdrop-filter: blur(12px);
            border-bottom: 1px solid var(--border);
        }

        #back-btn {
            display: flex;
            align-items: center;
            justify-content: center;
            width: 36px;
            height: 36px;
            border-radius: 50%;
            border: none;
            background: transparent;
            color: var(--text);
            cursor: pointer;
            transition: background 0.15s;
            text-decoration: none;
            flex-shrink: 0;
        }
        #back-btn:hover { background: rgba(255,255,255,0.08); }

        #chat-avatar {
            width: 40px;
            height: 40px;
            border-radius: 50%;
            background: #333;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: 700;
            font-size: 16px;
            color: #fff;
            flex-shrink: 0;
            overflow: hidden;
        }
        #chat-avatar img { width: 100%; height: 100%; object-fit: cover; }

        #chat-title { font-weight: 700; font-size: 16px; line-height: 1.2; }
        #chat-handle { font-size: 13px; color: var(--muted); }

        /* ── Messages container ── */
        #messages-wrap {
            max-width: 80vw;
            margin: 0 auto;
            padding: 24px 0 80px;
        }

        /* ── Twitter DOM overrides ── */
        .scrollbar-thin-custom { height: auto !important; overflow: visible !important; }
        .relative.flex.h-full.flex-1,
        .relative.flex.h-full.flex-grow.flex-col,
        .isolate.flex-1.overflow-hidden,
        .relative.h-full { height: auto !important; overflow: visible !important; }

        li { position: unset !important; }
        li > div { position: relative !important; }

        *[data-testid="dm-composer-container"] { display: none !important; }
        *[data-testid="dm-conversation-header"] { display: none !important; }

        .absolute.top-0.bottom-0.flex.items-center {
            display: none !important;
        }

        li img[alt="attachment"] {
            width: auto !important;
            height: auto !important;
            max-height: 400px !important;
            max-width: 100% !important;
        }

        /* Bubbles */
        li > div > div > div > div.justify-start > div > div > div > div {
            background: var(--surface) !important;
            border: 1px solid var(--border) !important;
        }
        li > div > div > div > div.justify-end > div > div > div {
            background: var(--primary) !important;
            border: 2px solid var(--primary) !important;
            border-radius: 20px !important;
        }

        /* Date separators */
        .text-subtext2 {
            color: var(--muted) !important;
            font-size: 12px !important;
        }

        /* Scrollbar */
        ::-webkit-scrollbar { width: 6px; }
        ::-webkit-scrollbar-track { background: transparent; }
        ::-webkit-scrollbar-thumb { background: #333; border-radius: 3px; }

        /* ──=========================== Video fixes ===========================── */

        /* Container: fixe Größe raus */
        li div.max-w-1\/3 {
            width: auto !important;
            height: auto !important;
            max-width: min(480px, 80vw) !important;
        }

        /* Aspect-ratio Container: natürliche Größe, kein erzwungenes 16:9 */
        li div.group.relative.isolate {
            height: auto !important;
            aspect-ratio: unset !important;
            width: 100% !important;
        }

        /* Das Video selbst: native Größe, max begrenzt */
        li video {
            width: 100% !important;
            height: auto !important;
            max-height: 70vh !important;
            object-fit: unset !important;
            border-radius: 12px !important;
            display: block !important;
        }

        /* Controls-Bar */
        li div.absolute.bottom-0.end-0.start-0.z-20 {
            display: flex !important;
        }

        div.group.relative.isolate:fullscreen {
            width: 100vw !important;
            height: 100vh !important;
            background: black;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        div.group.relative.isolate:fullscreen video {
            width: 100% !important;
            height: 100% !important;
            object-fit: contain !important;
        }
        div.group.relative.isolate:fullscreen div.absolute.bottom-0.end-0.start-0.z-20 {
            opacity: 1 !important;
        }


        /* =============== Button fixes ============== */

        /* Für files */
        [data-testid^="message-"][type="file"] button div:nth-child(1) {
            background-color: black
        }

        /* Audio play button */
        [data-testid^="message-"] [type="audio"] button {
            background-color: white;
        }
        /* Audio play icon */
        [data-testid^="message-"] [type="audio"] button svg path {
            fill: black;
        }
    </style>
</head>
<body>

<header id="chat-header">
    <a id="back-btn" href="index.php" title="Back">
        <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" fill="currentColor" viewBox="0 0 24 24">
            <path d="M7.414 13l5.043 5.05-1.414 1.42L3.586 12l7.457-7.47 1.414 1.42L7.414 11H21v2H7.414z"/>
        </svg>
    </a>
    <div id="chat-avatar"><?= strtoupper(substr($uname, 0, 1)) ?></div>
    <div id="header-info"<?= ($isGroup && count($members) > 0) ? ' onclick="openMembersPanel()" title="Mitglieder anzeigen"' : '' ?>>
        <div id="chat-title"><?= htmlspecialchars($uname) ?></div>
        <div id="chat-handle">
            <?php if ($isGroup && count($members) > 0): ?>
                DM Archive &middot; <span style="color: var(--primary);"><?= count($members) ?> Mitglieder</span>
            <?php else: ?>
                DM Archive
            <?php endif; ?>
        </div>
    </div>
</header>
 
<?php if ($isGroup && count($members) > 0): ?>
<!-- Members Panel Overlay -->
<div id="members-overlay" onclick="closeMembersPanel()"></div>
 
<!-- Members Panel -->
<div id="members-panel">
    <div id="members-panel-header">
        <div id="members-panel-title">Mitglieder</div>
        <button id="members-panel-close" onclick="closeMembersPanel()" title="Schließen">
            <svg xmlns="http://www.w3.org/2000/svg" fill="currentColor" viewBox="0 0 24 24" width="18" height="18">
                <path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/>
            </svg>
        </button>
    </div>
    <div id="members-count"><?= count($members) ?> Mitglieder</div>
    <div id="members-list">
        <?php foreach ($members as $member): ?>
        <a class="member-item" href="<?= isset($member['url']) ? $member['url'] : '' ?>" target="_blank">
            <div class="member-avatar">
                <?php if (!empty($member['avatar']) && !str_contains($member['avatar'], 'default_profile')): ?>
                    <img src="<?= htmlspecialchars($member['avatar']) ?>" alt="<?= htmlspecialchars($member['name']) ?>" onerror="this.parentElement.innerHTML='<?= strtoupper(substr($member['name'], 0, 1)) ?>'">
                <?php else: ?>
                    <?= strtoupper(substr($member['name'], 0, 1)) ?>
                <?php endif; ?>
            </div>
            <div class="member-info">
                <div class="member-name"><?= htmlspecialchars($member['name']) ?></div>
                <?php if (!empty($member['status'])): ?>
                    <div class="member-status"><?= htmlspecialchars($member['status']) ?></div>
                <?php endif; ?>
            </div>
        </a>
        <?php endforeach; ?>
    </div>
</div>
<?php endif; ?>

<div id="messages-wrap">
    <?php
        $files = array_diff(scandir($path), ['.', '..']);

        // only html files, reversed
        $htmlFiles = array_filter($files, fn($f) => str_ends_with($f, '.dump'));
        foreach (array_reverse(array_values($htmlFiles)) as $datei) {
            # Then decompress the dump
            $fp = fopen("$path/$datei", 'rb');
            $data = fread($fp, filesize("$path/$datei"));
            fclose($fp);

            $content = gzuncompress($data);
            echo $content;
            // require "$path/$datei";
        }
    ?>
    <!-- Ersetze das alte <audio controls style="display:none; ..."> mit: -->
    <div id="audio-player" style="
        display: none;
        position: fixed;
        bottom: 20px;
        left: 50%;
        transform: translateX(-50%);
        background: #1a1a1a;
        border: 1px solid #2f3336;
        border-radius: 16px;
        padding: 12px 16px;
        min-width: 320px;
        max-width: 90vw;
        z-index: 9999;
        box-shadow: 0 8px 32px rgba(0,0,0,0.6);
        display: none;
        flex-direction: column;
        gap: 8px;
    ">
        <div style="display:flex; align-items:center; gap:12px;">
            <button id="ap-playpause" style="
                width:36px; height:36px; border-radius:50%;
                background:#1d9bf0; border:none; cursor:pointer;
                display:flex; align-items:center; justify-content:center; flex-shrink:0;
                color:#fff;
            ">
                <svg id="ap-icon-play" xmlns="http://www.w3.org/2000/svg" fill="currentColor" viewBox="0 0 24 24" width="16" height="16"><path d="M21 12L4 2v20l17-10z"/></svg>
                <svg id="ap-icon-pause" xmlns="http://www.w3.org/2000/svg" fill="currentColor" viewBox="0 0 24 24" width="16" height="16" style="display:none"><path d="M6 19h4V5H6v14zm8-14v14h4V5h-4z"/></svg>
            </button>
            <div style="flex:1; min-width:0;">
                <div id="ap-filename" style="font-size:13px; font-weight:600; color:#e7e9ea; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;"></div>
                <div style="display:flex; align-items:center; gap:8px; margin-top:4px;">
                    <span id="ap-current" style="font-size:11px; color:#71767b; font-variant-numeric:tabular-nums; flex-shrink:0;">0:00</span>
                    <div id="ap-bar-bg" style="flex:1; height:3px; background:#2f3336; border-radius:2px; cursor:pointer; position:relative;">
                        <div id="ap-bar-fill" style="height:100%; background:#1d9bf0; border-radius:2px; width:0%; transition:width 0.1s linear;"></div>
                    </div>
                    <span id="ap-duration" style="font-size:11px; color:#71767b; font-variant-numeric:tabular-nums; flex-shrink:0;">0:00</span>
                </div>
            </div>
            <button id="ap-close" style="background:none;border:none;cursor:pointer;color:#71767b;padding:4px;flex-shrink:0;" title="Schließen">
                <svg xmlns="http://www.w3.org/2000/svg" fill="currentColor" viewBox="0 0 24 24" width="16" height="16"><path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/></svg>
            </button>
        </div>
    </div>
    <audio id="ap-audio"></audio>
</div>

<script>
    // ======================= Members Panel =======================
    function openMembersPanel() {
        document.getElementById('members-overlay')?.classList.add('open');
        document.getElementById('members-panel')?.classList.add('open');
        document.body.style.overflow = 'hidden';
    }
    function closeMembersPanel() {
        document.getElementById('members-overlay')?.classList.remove('open');
        document.getElementById('members-panel')?.classList.remove('open');
        document.body.style.overflow = '';
    }
    document.addEventListener('keydown', e => {
        if (e.key === 'Escape') closeMembersPanel();
    });

    
    // Remove duplicate messages
    const seenMessages = new Map();
    document.querySelectorAll('div[data-testid]').forEach(el => {
        if (!el.dataset.testid.startsWith('message-')) return;
        
        const id = el.dataset.testid;
        const hasGrabbed = el.querySelector('[grabbed]') !== null;
        
        if (seenMessages.has(id)) {
            const existing = seenMessages.get(id);
            const existingHasGrabbed = existing.el.querySelector('[grabbed]') !== null;

            // Wenn neues Element grabbed hat und altes nicht -> altes ersetzen
            if (hasGrabbed && !existingHasGrabbed) {
                existing.el.remove();
                seenMessages.set(id, { el, hasGrabbed });
            } else {
                // Sonst neues entfernen
                el.remove();
            }
        } else {
            seenMessages.set(id, { el, hasGrabbed });
        }
    });

    // Remove duplicate date headers
    const seenDates = new Set();
    document.querySelectorAll('li:has(.text-subtext2)').forEach(li => {
        const text = li.querySelector('.text-subtext2').textContent.trim();
        if (seenDates.has(text)) li.remove();
        else seenDates.add(text);
    });

    // Remove duplicate conversation headers
    const headers = [...document.querySelectorAll('div[data-testid="dm-conversation-header"]')];
    headers.shift();
    headers.forEach(h => h.remove());

    // Merge all <ul>s into first
    const uls = [...document.querySelectorAll('ul')];
    const first = uls.shift();
    const panels = [...document.querySelectorAll('div[data-testid="dm-conversation-panel"]')];
    uls.forEach((ul, i) => {
        first.append(...ul.children);
        panels[i + 1]?.remove();
    });
    
    // Remove scroll-to-bottom button
    document.querySelector('[data-testid="dm-scroll-to-bottom-button-container"]')?.parentElement?.remove();

    // Try to set avatar from first profile img
    const avatarImg = document.querySelector('li img[alt="user avatar"]');
    if (avatarImg?.src !== null && !avatarImg.src.includes('default_profile')) {
        const avatarEl = document.getElementById('chat-avatar');
        avatarEl.innerHTML = `<img src="${avatarImg.src}" alt="avatar">`;
    }

    // Try to set real name from profile block
    const nameEl = document.querySelector('li .text-headline2.font-bold');
    if (nameEl) {
        document.getElementById('chat-title').textContent = nameEl.textContent.trim();
        document.getElementById('chat-handle').textContent = '<?= htmlspecialchars($uname) ?>';
    }

    // Blobs src fixen
    [...document.querySelectorAll("[grabbed][src*='/___/assets/']")].map(c => c.src = c.src.replace('/___/assets/', `/<?= $for ?>/assets/`));

    // Poster rausfiltern aus videos, weil die blobs haben
    [...document.querySelectorAll('li video[poster*="blob:"]')].forEach(video => {
        video.removeAttribute('poster');
    });


    // ======================= Event listeners für Audio, Zips etc. =======================
    // #region ======================= Audio Player =======================
    const apAudio    = document.getElementById('ap-audio');
    const apPlayer   = document.getElementById('audio-player');
    const apFilename = document.getElementById('ap-filename');
    const apCurrent  = document.getElementById('ap-current');
    const apDuration = document.getElementById('ap-duration');
    const apFill     = document.getElementById('ap-bar-fill');
    const apBarBg    = document.getElementById('ap-bar-bg');
    const apPlayPause= document.getElementById('ap-playpause');
    const apIconPlay = document.getElementById('ap-icon-play');
    const apIconPause= document.getElementById('ap-icon-pause');

    function fmtTime(s) {
        if (!isFinite(s)) return '0:00';
        const m = Math.floor(s / 60);
        return m + ':' + String(Math.floor(s % 60)).padStart(2, '0');
    }

    function setPlaying(playing) {
        apIconPlay.style.display  = playing ? 'none'  : '';
        apIconPause.style.display = playing ? ''      : 'none';
    }

    apAudio.addEventListener('timeupdate', () => {
        apCurrent.textContent = fmtTime(apAudio.currentTime);
        if (apAudio.duration)
            apFill.style.width = (apAudio.currentTime / apAudio.duration * 100) + '%';
    });
    apAudio.addEventListener('loadedmetadata', () => {
        apDuration.textContent = fmtTime(apAudio.duration);
    });
    apAudio.addEventListener('ended', () => setPlaying(false));
    apAudio.addEventListener('play',  () => setPlaying(true));
    apAudio.addEventListener('pause', () => setPlaying(false));

    apPlayPause.addEventListener('click', () => {
        apAudio.paused ? apAudio.play() : apAudio.pause();
    });

    apBarBg.addEventListener('click', e => {
        const rect = apBarBg.getBoundingClientRect();
        const ratio = (e.clientX - rect.left) / rect.width;
        if (apAudio.duration) apAudio.currentTime = ratio * apAudio.duration;
    });

    document.getElementById('ap-close').addEventListener('click', () => {
        apAudio.pause();
        apPlayer.style.display = 'none';
    });

    document.querySelectorAll('[grabbed][type="audio"]').forEach(elem => {
        const file = elem.getAttribute('filename');
        // Dateiname ohne Extension für Voice Messages
        const isVoice = file && file.startsWith('voicemessage_');
        const displayName = isVoice ? '🎤 Sprachnachricht' : (file || 'Audio');

        elem.querySelector('button').addEventListener('click', () => {
            apFilename.textContent = displayName;
            apAudio.src = `./dump/<?= $for ?>/assets/${file}`;
            apPlayer.style.display = 'flex';
            apFill.style.width = '0%';
            apCurrent.textContent = '0:00';
            apDuration.textContent = '0:00';
            apAudio.load();
            apAudio.play();
        });
    });
    // #endregion

    // #region ======================= Video Player Controls =======================
    document.querySelectorAll('li video[grabbed]').forEach(video => {
        video.removeAttribute('autoplay')
        const container = video.closest('div.group.relative.isolate');
        if (!container) return;

        const controlsBar = container.querySelector('div.absolute.bottom-0.end-0.start-0.z-20');
        
        // Buttons NUR innerhalb der Controls-Bar suchen, nicht den Overlay-Button
        const playBtn  = controlsBar?.querySelector('button[aria-label="Play"], button[aria-label="Pause"]');
        playBtn.style.cursor = 'pointer';
        const muteBtn  = controlsBar?.querySelector('button[aria-label="Unmute"], button[aria-label="Mute"]');
        muteBtn.style.cursor = 'pointer';
        const seekBar  = controlsBar?.querySelector('[role="group"][aria-label="Seek slider"] > div');
        const seekFill = seekBar?.querySelector('div.bg-white');
        const timeDisplay = controlsBar?.querySelector('.font-chirp');
        const pipBtn   = controlsBar?.querySelector('button[aria-label="Picture-in-Picture"]');
        pipBtn.style.cursor = 'pointer';
        const fullscreenBtn = controlsBar?.querySelector('button[aria-label="Exit full screen"], button[aria-label="Full screen"]');
        fullscreenBtn.style.cursor = 'pointer';

        // Pointer-events fix
        container.querySelectorAll('button svg, button svg *').forEach(el => {
            el.style.pointerEvents = 'none';
        });

        function updatePlayBtn() {
            const path = playBtn?.querySelector('path');
            if (!path) return;
            path.setAttribute('d', video.paused
                ? 'M6 17.9284V6.07151C6 4.50848 7.71248 3.54952 9.04512 4.3663L18.7178 10.2947C19.991 11.0751 19.991 12.9248 18.7178 13.7051L9.04512 19.6336C7.71249 20.4503 6 19.4914 6 17.9284Z'
                : 'M6 19h4V5H6v14zm8-14v14h4V5h-4z'
            );
        }

        playBtn?.addEventListener('click', () => {
            video.paused ? video.play() : video.pause();
        });

        const overlayBtn = container.querySelector('button.absolute.bottom-0.top-0.z-0.bg-transparent');
        overlayBtn.style.cursor = 'default';
        overlayBtn?.addEventListener('click', () => {
            video.paused ? video.play() : video.pause();
        });

        video.addEventListener('click', () => {
            video.paused ? video.play() : video.pause();
        });

        video.addEventListener('play',  updatePlayBtn);
        video.addEventListener('pause', updatePlayBtn);

        const soundHighSVG = `<path fill-rule="evenodd" d="M14 22H11.6494L11.375 21.7812L6.64844 18H4.5C2.567 18 1 16.433 1 14.5V9.5C1 7.567 2.567 6 4.5 6H6.64844L11.375 2.21875L11.6494 2H14V22ZM7.625 7.78125L7.35059 8H4.5C3.67157 8 3 8.67157 3 9.5V14.5C3 15.3284 3.67157 16 4.5 16H7.35059L7.625 16.2188L12 19.7188V4.28125L7.625 7.78125Z" clip-rule="evenodd"></path><path d="M20.8174 5.09766C22.1922 7.05003 23 9.43242 23 12C23 14.5676 22.1922 16.95 20.8174 18.9023L19.1826 17.75C20.3277 16.1238 21 14.1419 21 12C21 9.85812 20.3277 7.87625 19.1826 6.25L20.8174 5.09766Z"></path><path d="M17.5654 7.42773C18.4696 8.72394 19 10.3016 19 12C19 13.6984 18.4696 15.2761 17.5654 16.5723L15.9248 15.4277C16.6024 14.4563 17 13.2761 17 12C17 10.7239 16.6024 9.54371 15.9248 8.57227L17.5654 7.42773Z"></path>`;
        const soundOffSVG = `<path d="M16 22H13.6494L13.375 21.7812L9.5332 18.708L10.957 17.2842L14 19.7188V14.2422L16 12.2422V22Z"></path><path fill-rule="evenodd" d="M16 6.58594L20.293 2.29297L21.707 3.70703L3.70703 21.707L2.29297 20.293L4.9502 17.6348C3.79536 17.0632 3 15.8759 3 14.5V9.5C3 7.567 4.567 6 6.5 6H8.64844L13.375 2.21875L13.6494 2H16V6.58594ZM9.625 7.78125L9.35059 8H6.5C5.67157 8 5 8.67157 5 9.5V14.5C5 15.3284 5.67157 16 6.5 16H6.58594L14 8.58594V4.28125L9.625 7.78125Z" clip-rule="evenodd"></path>`;

        muteBtn?.addEventListener('click', () => {
            video.muted = !video.muted;
            const svg = muteBtn.querySelector('svg');
            if (svg) svg.innerHTML = video.muted ? soundOffSVG : soundHighSVG;
            muteBtn.setAttribute('aria-label', video.muted ? 'Unmute' : 'Mute');
        });

        function updateSeek() {
            if (!video.duration || !seekFill) return;
            seekFill.style.width = (video.currentTime / video.duration * 100).toFixed(2) + '%';
            if (timeDisplay) {
                const fmt = s => String(Math.floor(s/60)).padStart(2,'0') + ':' + String(Math.floor(s%60)).padStart(2,'0');
                timeDisplay.textContent = `${fmt(video.currentTime)} / ${fmt(video.duration)}`;
            }
        }
        video.addEventListener('timeupdate', updateSeek);

        seekBar?.addEventListener('click', e => {
            const rect = seekBar.getBoundingClientRect();
            video.currentTime = ((e.clientX - rect.left) / rect.width) * video.duration;
        });

        pipBtn?.addEventListener('click', () => {
            document.pictureInPictureElement
                ? document.exitPictureInPicture()
                : video.requestPictureInPicture?.();
        });

        const fsIconExpand   = 'M13 3h8v8h-2V6.41l-5.043 5.05-1.414-1.42L17.586 5H13V3zm-1.543 10.96L6.414 19H11v2H3v-8h2v4.59l5.043-5.05 1.414 1.42z';
        const fsIconCollapse = 'M21.457 3.96L16.414 9H21v2h-8V3h2v4.59l5.043-5.05 1.414 1.42zM3 13h8v8H9v-4.59l-5.043 5.05-1.414-1.42L7.586 15H3v-2z';

        fullscreenBtn?.addEventListener('click', () => {
            if (document.fullscreenElement) {
                document.exitFullscreen();
            } else {
                container.requestFullscreen?.();
            }
        });

        fullscreenBtn?.setAttribute('aria-label', 'Full screen');
        fullscreenBtn?.querySelector('path')?.setAttribute('d', fsIconExpand);
        document.addEventListener('fullscreenchange', () => {
            const isFs = document.fullscreenElement === container;
            const path = fullscreenBtn?.querySelector('path');
            if (path) path.setAttribute('d', isFs ? fsIconCollapse : fsIconExpand);
            fullscreenBtn?.setAttribute('aria-label', isFs ? 'Exit full screen' : 'Full screen');
        });

        if (controlsBar) {
            Object.assign(controlsBar.style, { opacity: '0', transition: 'opacity 0.2s' });
            container.addEventListener('mouseenter', () => controlsBar.style.opacity = '1');
            container.addEventListener('mouseleave', () => controlsBar.style.opacity = '0');
        }
    });

</script>
</body>
</html>