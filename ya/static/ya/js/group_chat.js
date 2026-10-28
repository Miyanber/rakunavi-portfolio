// ya/static/ya/js/group_chat.js
document.addEventListener("DOMContentLoaded", () => {
    const messagesEl = document.getElementById("messages");
    const form = document.getElementById("group-form");
    const textarea = document.getElementById("group-content") || form.querySelector("textarea");
    const typingIndicator = document.getElementById("typing-indicator");

    const groupId = window.groupId;
    const myUserId = window.myUserId;
    const protocol = location.protocol === "https:" ? "wss" : "ws";
    const socket = new WebSocket(`${protocol}://${location.host}/ws/group/${groupId}/`);

    function scrollToBottom() {
        messagesEl.scrollTop = messagesEl.scrollHeight;
    }

    function createReadIcon(readCount, memberCount) {
        const el = document.createElement("span");
        el.className = "material-symbols-rounded read-icon";
        if (readCount >= memberCount) el.textContent = "done_all";
        else if (readCount >= 1) el.textContent = "check";
        else el.textContent = "";
        return el;
    }

    function appendMessage(msg) {
        // msg: { id, content, sender_id, sender_username, sender_icon, send_at, read_by_count, member_count }
        const wrapper = document.createElement("div");
        wrapper.className = msg.sender_id === myUserId ? "mine" : "yours";
        wrapper.dataset.messageId = msg.id;
        wrapper.innerHTML = `
            <div class="icon_background">
                <img class="sender icon" src="${msg.sender_icon || '/static/main/img/default-icon_1x1.webp'}">
            </div>
            <div class="bubble polygon-clip-n23">
                <span class="content"></span>
            </div>
            <span class="send_at">${msg.send_at || 'たった今'}</span>
        `;
        wrapper.querySelector(".content").textContent = msg.content;

        // add read icon + read count if mine
        if (msg.sender_id === myUserId) {
            const sendAt = wrapper.querySelector(".send_at");
            sendAt.appendChild(createReadIcon(msg.read_by_count || 1, msg.member_count || 1));
            const small = document.createElement("small");
            small.className = "read-count";
            small.textContent = `（${msg.read_by_count || 1} / ${msg.member_count || 1}）`;
            sendAt.appendChild(small);
        }

        messagesEl.appendChild(wrapper);
        scrollToBottom();
    }

    function updateReadCounts(ids, reader_id) {
        if (!Array.isArray(ids)) return;
        ids.forEach(id => {
            const el = document.querySelector(`[data-message-id="${id}"]`);
            if (!el) return;
            // find send_at and update icon + count
            const sendAt = el.querySelector(".send_at");
            if (!sendAt) return;
            // remove existing icons and small
            sendAt.querySelectorAll(".read-icon, .read-count, .material-symbols-rounded").forEach(n => n.remove());
            // we need new counts: server doesn't send new counts per message to avoid heavy payload,
            // but for accuracy server sends read_by_count and member_count in chat.message payload.
            // For read notifications we will set to done_all if all read, otherwise add a simple done_all icon.
            const icon = document.createElement("span");
            icon.className = "material-symbols-rounded read-icon";
            icon.textContent = "done_all";
            sendAt.appendChild(icon);
            // Optionally show small "(x / n)" if you want full accuracy; needs extra data from server.
        });
    }

    socket.onopen = () => {
        console.log("group ws open");
        // ask server to mark unread as read (this will trigger broadcast)
        socket.send(JSON.stringify({ type: "read" }));
    };

    socket.onmessage = (e) => {
        const data = JSON.parse(e.data);
        if (data.type === "message") {
            appendMessage(data.message);
            // immediately mark as read for other participants
            if (data.message.sender_id !== myUserId) {
                setTimeout(() => socket.send(JSON.stringify({ type: "read" })), 150);
            }
            return;
        }
        if (data.type === "read" || data.type === "read_all") {
            if (data.reader_id === myUserId) return;
            updateReadCounts(data.message_ids || [], data.reader_id);
            return;
        }
        if (data.type === "typing") {
            if (data.user_id === myUserId) return;
            typingIndicator.style.display = data.is_typing ? "block" : "none";
            return;
        }
    };

    socket.onclose = () => console.warn("ws closed");
    socket.onerror = e => console.error("ws error", e);

    // send message
    form.addEventListener("submit", (e) => {
        e.preventDefault();
        const content = textarea.value.trim();
        if (!content) return;
        socket.send(JSON.stringify({ type: "send", content }));
        textarea.value = "";
    });

    textarea.addEventListener("keydown", (e) => {
        if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            form.dispatchEvent(new Event("submit", { bubbles: true }));
        }
    });

    // typing
    let typingTimer = null;
    textarea.addEventListener("input", () => {
        if (socket.readyState === WebSocket.OPEN) socket.send(JSON.stringify({ type: "typing", is_typing: true }));
        clearTimeout(typingTimer);
        typingTimer = setTimeout(() => {
            if (socket.readyState === WebSocket.OPEN) socket.send(JSON.stringify({ type: "typing", is_typing: false }));
        }, 800);
    });

    // scroll on load
    scrollToBottom();
});
