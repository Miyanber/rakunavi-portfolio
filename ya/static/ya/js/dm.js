document.addEventListener("DOMContentLoaded", () => {
    const form = document.getElementById("dm-form");
    // robust textarea selection: first try id, then named field, then first textarea
    const textarea = document.getElementById("dm-content") ||
        form.querySelector('textarea[name="content"], input[name="content"]') ||
        form.querySelector("textarea") ||
        form.querySelector("input[type=text]");

    const messagesEl = document.getElementById("messages");
    const typingIndicator = document.getElementById("typing-indicator");

    const partnerId = window.partnerId;
    const myUserId = window.myUserId;

    const protocol = location.protocol === "https:" ? "wss" : "ws";
    const chatSocket = new WebSocket(`${protocol}://${location.host}/ws/dm/${partnerId}/`);

    // --- helpers ---
    function scrollToBottom() {
        if (!messagesEl) return;
        messagesEl.scrollTop = messagesEl.scrollHeight;
    }

    function createReadIcon(count) {
        const span = document.createElement("span");
        span.className = "material-symbols-rounded read-icon";
        if (count >= 2) span.textContent = "done_all";
        else span.textContent = "check";
        return span;
    }

    function appendMessage(message) {
        // message: {id, content, sender_id, sender_icon, send_at, read_by_count}
        const wrapper = document.createElement("div");
        wrapper.className = (message.sender_id === myUserId) ? "mine" : "yours";
        wrapper.dataset.messageId = message.id;

        wrapper.innerHTML = `
            <div class="icon_background">
                <img class="sender icon" src="${message.sender_icon || '/static/main/img/default-icon_1x1.webp'}">
            </div>
            <div class="bubble polygon-clip-n23">
                <span class="content"></span>
            </div>
            <span class="send_at">${message.send_at || ""}</span>
        `;

        wrapper.querySelector(".content").textContent = message.content;
        // add read icon only for messages sent by me (mine)
        if (message.sender_id === myUserId) {
            wrapper.querySelector(".send_at").appendChild(createReadIcon(message.read_by_count || 1));
        }

        messagesEl.appendChild(wrapper);
        scrollToBottom();
    }

    function setMessagesReadByIds(ids) {
        if (!Array.isArray(ids)) return;
        ids.forEach(id => {
            const el = document.querySelector(`[data-message-id="${id}"]`);
            if (!el) return;
            const sendAt = el.querySelector(".send_at");
            if (!sendAt) return;
            // remove existing read icons
            const existing = sendAt.querySelectorAll(".read-icon, .material-symbols-rounded");
            existing.forEach(n => n.remove());
            const icon = document.createElement("span");
            icon.className = "material-symbols-rounded read-icon";
            icon.textContent = "done_all";
            sendAt.appendChild(icon);
        });
    }

    // --- WebSocket handlers ---
    chatSocket.onopen = () => {
        console.log("WS connected");
        // ask server to mark all unread partner->me as read (and notify room)
        chatSocket.send(JSON.stringify({ type: "read" }));
        // optionally for Discord semantics use: chatSocket.send(JSON.stringify({ type: "read_all" }));
    };

    chatSocket.onmessage = (e) => {
        let data;
        try {
            data = JSON.parse(e.data);
        } catch (err) {
            console.error("invalid ws json", e.data);
            return;
        }

        // console.debug("ws recv", data);

        if (data.type === "message") {
            appendMessage(data.message);
            // if it's someone else's message, immediately mark read
            if (data.message.sender_id !== myUserId) {
                // small delay to avoid race
                setTimeout(() => {
                    if (chatSocket.readyState === WebSocket.OPEN) {
                        chatSocket.send(JSON.stringify({ type: "read" }));
                    }
                }, 120);
            }
            return;
        }

        if (data.type === "read" || data.type === "read_all") {
            // don't act on our own read broadcasts (avoid redundant UI changes)
            if (data.reader_id === myUserId) return;
            setMessagesReadByIds(data.message_ids || []);
            return;
        }

        if (data.type === "typing") {
            if (data.user_id === myUserId) return;
            typingIndicator.style.visibility = data.is_typing ? "visible" : "hidden";
            return;
        }
    };

    chatSocket.onclose = (e) => {
        console.warn("WS closed", e);
    };
    chatSocket.onerror = (e) => {
        console.error("WS error", e);
    };

    // --- sending ---
    function sendMessage() {
        if (!textarea) {
            console.error("no input found");
            return;
        }
        const content = textarea.value.trim();
        if (!content) return;
        if (chatSocket.readyState !== WebSocket.OPEN) {
            console.warn("socket not open", chatSocket.readyState);
            return;
        }
        chatSocket.send(JSON.stringify({ type: "send", content }));
        textarea.value = "";
        // mark our own message in DOM optimistically? We rely on server broadcast to append.
    }

    if (form) {
        form.addEventListener("submit", (e) => {
            e.preventDefault();
            sendMessage();
        });
    }

    if (textarea) {
        textarea.addEventListener("keydown", (e) => {
            if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                sendMessage();
            }
        });

        // typing debounce
        let typingTimer = null;
        textarea.addEventListener("input", () => {
            if (chatSocket.readyState === WebSocket.OPEN) {
                chatSocket.send(JSON.stringify({ type: "typing", is_typing: true }));
            }
            clearTimeout(typingTimer);
            typingTimer = setTimeout(() => {
                if (chatSocket.readyState === WebSocket.OPEN) {
                    chatSocket.send(JSON.stringify({ type: "typing", is_typing: false }));
                }
            }, 800);
        });
    }

    // initial scroll
    scrollToBottom();
});
