<!DOCTYPE html>
<html lang="en">

<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>DM Archive</title>
    <script src="https://cdn.jsdelivr.net/npm/@tailwindcss/browser@4"></script>
    <style>
        body {
            background: #000;
            color: #e7e9ea;
        }
    </style>
</head>

<body class="min-h-screen">
    <?php include "status.php"; ?>
    <div class="max-w-xl mx-auto py-8 px-4">
        <h1 class="text-2xl font-bold mb-6">DM Archive</h1>
        <div class="flex flex-col gap-1" id="chatlist"></div>
    </div>


    <script>
        chatInterval = null;

        async function loadChats() {
            const container = document.getElementById("chatlist");
            try {
                const response = await fetch("/php/api/chats.php");
                const chats = await response.json();

                container.innerHTML = chats.map(chat => {
                    const info = chat.info;

                    const avatarHtml =
                        info.avatars && info.avatars.length > 1 ?
                        renderGroupAvatars(info.avatars) :
                        renderSingleAvatar(info);

                    return `
                <a href="/php/chat.php?for=${encodeURIComponent(chat.dirname)}"
                    class="flex items-center gap-4 px-4 py-3 rounded-xl hover:bg-white/5 transition cursor-pointer">

                    ${avatarHtml}

                    <div class="flex flex-col min-w-0 flex-1">
                        <div class="flex justify-between items-start gap-2 mb-0.5">
                            <span class="font-bold truncate">
                                ${escapeHtml(info.name || info.username)}
                            </span>

                            <span class="text-gray-600 text-sm font-light flex-shrink-0">
                                ${info.lastMessageTime || ""}
                            </span>
                        </div>

                        ${
                        !info.isGroupchat
                        ? `<span class="text-gray-500 text-sm">${escapeHtml(info.username)}</span>`
                        : ""
                        }

                        <span class="text-gray-100 truncate">
                            ${escapeHtml(info.lastMessage || "")}
                        </span>
                    </div>
                </a>
                `;
                }).join("");

                if (window.cp_done === true && chatInterval) {
                    clearInterval(chatInterval);
                    chatInterval = null;
                }

            } catch (e) {
                container.innerHTML =
                    '<div class="text-red-500">Fehler beim Laden.</div>';
                console.error(e);
            }
        }

        function renderSingleAvatar(info) {
            if (info.avatar) {
                return `
                <div class="w-12 h-12 rounded-full overflow-hidden shrink-0">
                    <img src="${info.avatar}"
                        class="w-full h-full object-cover">
                </div>
                `;
            }

            return `
                <div class="w-12 h-12 rounded-full bg-gray-700 flex items-center justify-center text-xl font-bold shrink-0">
                    ${(info.username || "?")[0].toUpperCase()}
                </div>
                `;
        }

        function renderGroupAvatars(avatars) {
            const items = [...avatars];

            const lastAvatar = items.pop();

            return `
                <div>
                    <div class="flex flex-row-reverse rounded-lg"
                        style="margin-top: calc(12px);">

                        ${items.map(avatar => `
                            <div
                                class="rounded-full bg-background"
                                style="
                                    z-index: 2;
                                    padding: 2px;
                                    width: 44px;
                                    height: 44px;
                                ">
                                <div class="min-size flex overflow-hidden rounded-full bg-gray-300 min-h-10 min-w-10 size-10">
                                    <img
                                        alt="user avatar"
                                        class="size-full brightness-100"
                                        loading="lazy"
                                        src="${avatar}"
                                        draggable="false">
                                </div>
                            </div>
                        `).join("")}

                        <div
                            style="
                                width: 40px;
                                height: 40px;
                                margin-inline-end: -28px;
                                margin-top: -12px;
                            ">
                            <div class="min-size flex overflow-hidden rounded-full bg-gray-300 min-h-10 min-w-10 size-10">
                                <img
                                    alt="user avatar"
                                    class="size-full brightness-100"
                                    loading="lazy"
                                    src="${lastAvatar}"
                                    draggable="false">
                            </div>
                        </div>

                    </div>
                </div>
            `;
        }

        function escapeHtml(text) {
            const div = document.createElement("div");
            div.textContent = text ?? "";
            return div.innerHTML;
        }

        
        loadChats();
        chatInterval = setInterval(loadChats, 4000);
    </script>
</body>

</html>