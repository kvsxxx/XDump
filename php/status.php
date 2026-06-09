<style>
    :root {
        --bg: #0d0d0d;
        --surface: #141414;
        --border: #1f1f1f;
        --accent: #1d9bf0;
        --accent2: #00ba7c;
        --muted: #555;
        --text: #e7e7e7;
        --label: #888;
        --font: 'SF Mono', 'Fira Code', 'Consolas', monospace;
        --radius: 6px;
    }

    #xdump-header * {
        box-sizing: border-box;
        margin: 0;
        padding: 0;
    }

    #xdump-header {
        font-family: var(--font);
        font-size: 12px;
        background: var(--surface);
        border-bottom: 1px solid var(--border);
        padding: 10px 18px;
        display: flex;
        align-items: center;
        gap: 24px;
        flex-wrap: wrap;
        color: var(--text);
    }

    #xdump-header .xd-brand {
        font-size: 13px;
        font-weight: 700;
        color: var(--accent);
        letter-spacing: .04em;
        white-space: nowrap;
    }

    #xdump-header .xd-divider {
        display: flex;
        align-items: center;
        gap: 8px;
        flex-shrink: 0;
    }

    #xdump-header .xd-divider::before {
        content: '';
        width: 1px;
        height: 28px;
        background: var(--border);
    }

    #xdump-header .xd-divider-label {
        font-size: 9px;
        text-transform: uppercase;
        letter-spacing: .12em;
        color: var(--muted);
        font-weight: 700;
    }

    #xdump-header .xd-stat {
        display: flex;
        flex-direction: column;
        gap: 2px;
        white-space: nowrap;
    }

    #xdump-header .xd-stat .xd-label {
        font-size: 9px;
        text-transform: uppercase;
        letter-spacing: .08em;
        color: var(--label);
    }

    #xdump-header .xd-stat .xd-value {
        font-size: 13px;
        font-weight: 600;
        color: var(--text);
    }

    #xdump-header .xd-stat .xd-value.green {
        color: var(--accent2);
    }

    #xdump-header .xd-stat .xd-value.blue {
        color: var(--accent);
    }

    #xdump-header .xd-stat .xd-value.muted {
        color: var(--muted);
    }

    #xdump-header .xd-progress-wrap {
        display: flex;
        flex-direction: column;
        gap: 4px;
        min-width: 120px;
    }

    #xdump-header .xd-progress-wrap .xd-label {
        font-size: 9px;
        text-transform: uppercase;
        letter-spacing: .08em;
        color: var(--label);
    }

    #xdump-header .xd-progress-wrap .xd-bar-row {
        display: flex;
        align-items: center;
        gap: 8px;
    }

    #xdump-header .xd-bar {
        flex: 1;
        height: 4px;
        background: var(--border);
        border-radius: 2px;
        overflow: hidden;
    }

    #xdump-header .xd-bar-fill {
        height: 100%;
        background: var(--accent);
        border-radius: 2px;
        transition: width .3s ease;
    }

    #xdump-header .xd-bar-pct {
        font-size: 11px;
        font-weight: 600;
        color: var(--text);
        min-width: 28px;
        text-align: right;
    }

    #xdump-header .xd-chatid {
        font-size: 10px;
        color: var(--muted);
        max-width: 180px;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
    }

    #xdump-header .xd-live {
        display: flex;
        align-items: center;
        gap: 5px;
        font-size: 10px;
        color: var(--label);
    }

    #xdump-header .xd-dot {
        width: 6px;
        height: 6px;
        border-radius: 50%;
        background: var(--accent2);
        animation: xd-pulse 1.8s infinite;
    }

    @keyframes xd-pulse {

        0%,
        100% {
            opacity: 1;
        }

        50% {
            opacity: .3;
        }
    }
</style>

<section style="background:#0d0d0d">

    <div id="xdump-header">

        <span class="xd-brand">XDump</span>

        <div class="xd-divider">
            <span class="xd-divider-label">dump</span>
        </div>

        <!-- DUMP STATUS -->

        <div class="xd-stat">
            <span class="xd-label">dumped chats</span>
            <span id="xd-dumped-chats" class="xd-value blue">0</span>
        </div>

        <div class="xd-stat">
            <span class="xd-label">cc .dumps</span>
            <span id="xd-chat-dumps" class="xd-value">0</span>
        </div>

        <div class="xd-stat">
            <span class="xd-label">chat size</span>
            <span id="xd-chat-size" class="xd-value">0 B</span>
        </div>

        <div class="xd-divider"></div>

        <!-- STORAGE -->

        
        <div class="xd-divider">
            <span class="xd-divider-label">storage</span>
        </div>


        <div class="xd-stat">
            <span class="xd-label">all dumps</span>
            <span id="xd-all-dumps-size" class="xd-value green">0 B</span>
        </div>

        <div class="xd-stat">
            <span class="xd-label">dump files</span>
            <span id="xd-only-dumps-size" class="xd-value">0 B</span>
        </div>

        <div class="xd-stat">
            <span class="xd-label">asset files</span>
            <span id="xd-only-files-size" class="xd-value">0 B</span>
        </div>

        <div class="xd-divider"></div>

        <!-- MESSAGES -->

        
        <div class="xd-divider">
            <span class="xd-divider-label">messages</span>
        </div>


        <div class="xd-stat">
            <span class="xd-label">total msgs</span>
            <span id="xd-total-msgs" class="xd-value blue">0</span>
        </div>

        <div class="xd-stat">
            <span class="xd-label">current chat</span>
            <span id="xd-current-chat" class="xd-value">0 msg / dump #0</span>
        </div>

        <div class="xd-divider"></div>

        <!-- PERFORMANCE -->

        
        <div class="xd-divider">
            <span class="xd-divider-label">performance</span>
        </div>

        <div class="xd-stat">
            <span class="xd-label">global speed</span>
            <span id="xd-global-speed" class="xd-value green">–</span>
        </div>

        <div class="xd-stat">
            <span class="xd-label">chat speed</span>
            <span id="xd-chat-speed" class="xd-value green">–</span>
        </div>

        <div class="xd-stat">
            <span class="xd-label">running</span>
            <span id="xd-running" class="xd-value">–</span>
        </div>

        <div class="xd-stat">
            <span class="xd-label">last update</span>
            <span id="xd-last-update" class="xd-value muted">–</span>
        </div>

        <div class="xd-divider"></div>

        <div class="xd-stat">
            <span class="xd-label">active chat</span>
            <span id="xd-chat-id" class="xd-value xd-chatid">–</span>
        </div>

        <div id="xd-live" class="xd-live" style="display:none">
            <span class="xd-dot"></span>
            live
        </div>

    </div>

</section>

<script>
    function xdumpElapsed(from, to = Date.now() / 1000) {
        const diff = to - from;

        if (diff < 60)
            return Math.round(diff) + 's';

        if (diff < 3600)
            return Math.round(diff / 60) + 'm ' + (Math.round(diff) % 60) + 's';

        return Math.round(diff / 3600) + 'h ' + (Math.round(diff / 60) % 60) + 'm';
    }

    function xdumpMsgPerSec(cp) {
        const started = cp.started_at;
        if (!started) return '–';

        const elapsed = Date.now() / 1000 - started;
        if (elapsed <= 0) return '–';

        const msgs = cp.total_messages_dumped || 0;
        const mps = msgs / elapsed;

        return mps >= 1 ?
            mps.toFixed(1) + ' msg/s' :
            (mps * 60).toFixed(1) + ' msg/min';
    }

    function xdumpChatSpeed(cp) {
        const start = cp.current_chat_started_at;
        const msgs = cp.current_chat_messages || 0;

        if (!start || msgs === 0)
            return '–';

        const elapsed = Date.now() / 1000 - start;

        if (elapsed <= 0)
            return '–';

        const mps = msgs / elapsed;

        return mps >= 1 ?
            mps.toFixed(1) + ' msg/s' :
            (mps * 60).toFixed(1) + ' msg/min';
    }

    function formatBytes(bytes) {
        if (!bytes)
            return '0 B';

        const units = ['B', 'KB', 'MB', 'GB', 'TB'];

        let i = 0;

        while (bytes >= 1024 && i < units.length - 1) {
            bytes /= 1024;
            i++;
        }

        return bytes.toFixed(i === 0 ? 0 : 1) + ' ' + units[i];
    }

    async function updateXDumpStats() {
        try {
            const res = await fetch('/php/api/checkpoint.php');
            const cp = await res.json();

            const totalMsgs = cp.total_messages_dumped || 0;
            const chatMsgs = cp.current_chat_messages || 0;
            const dumpIndex = cp.last_dump_index || 0;
            const lastChatId = cp.current_chat_name || '-';
            const dumpedChats = (cp.done_ids || []).length;
            const chatDumpCount = cp.current_chat_dump_count || 0;
            const chatSize = cp.current_dump_size || 0;
            const allDumpSize = cp.all_dumps_size || 0;
            const onlyDumpSize = cp.total_dump_size || 0;
            const onlyFileSize = cp.total_file_size || 0;
            window.cp_done = cp.done;

            document.getElementById('xd-dumped-chats').textContent =
                dumpedChats.toLocaleString();

            document.getElementById('xd-chat-dumps').textContent =
                chatDumpCount.toLocaleString();

            document.getElementById('xd-chat-size').textContent =
                formatBytes(chatSize);

            document.getElementById('xd-all-dumps-size').textContent =
                formatBytes(allDumpSize);

            document.getElementById('xd-only-dumps-size').textContent =
                formatBytes(onlyDumpSize);

            document.getElementById('xd-only-files-size').textContent =
                formatBytes(onlyFileSize);

            document.getElementById('xd-total-msgs').textContent =
                totalMsgs.toLocaleString();

            document.getElementById('xd-current-chat').textContent =
                `${chatMsgs.toLocaleString()} msg / dump #${dumpIndex}`;

            document.getElementById('xd-global-speed').textContent =
                xdumpMsgPerSec(cp);

            document.getElementById('xd-chat-speed').textContent =
                xdumpChatSpeed(cp);
            
            document.getElementById('xd-running').textContent =
                cp.done ? 'Done' :
                cp.started_at ? xdumpElapsed(cp.started_at) : '-';

            document.getElementById('xd-last-update').textContent =
                cp.last_update ?
                xdumpElapsed(cp.last_update) + ' ago' :
                '–';

            
            const chatIdEl = document.getElementById('xd-chat-id');
            chatIdEl.textContent = lastChatId;
            chatIdEl.title = lastChatId;

            const live =
                cp.last_update &&
                ((Date.now() / 1000) - cp.last_update) < 30;

            document.getElementById('xd-live').style.display =
                live ? 'flex' : 'none';

        } catch (err) {
            console.error('Failed to fetch checkpoint:', err);
        }
    }

    updateXDumpStats();
    setInterval(updateXDumpStats, 5000);
</script>