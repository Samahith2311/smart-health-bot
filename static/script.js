const chatbox = document.getElementById("chatbox");
const userInput = document.getElementById("userInput");
const sendBtn = document.getElementById("sendBtn");
const voiceBtn = document.getElementById("voiceBtn");
const quickWater = document.getElementById("quickWater");
const quickStress = document.getElementById("quickStress");
const typingIndicator = document.getElementById("typingIndicator");

let recognition = null;
let reminders = [];

// ------------- Chat helpers -------------

function showTyping(show) {
    if (!typingIndicator) return;
    typingIndicator.style.display = show ? "block" : "none";
}

function addMessage(text, sender = "bot") {
    if (!chatbox) return; // on login/register/dashboard we might not have it
    const div = document.createElement("div");
    div.classList.add("message", sender);
    div.innerText = text;
    chatbox.appendChild(div);
    chatbox.scrollTop = chatbox.scrollHeight;

    if (sender === "bot") {
        speak(text);
    }
}

function sendMessage() {
    if (!userInput) return;
    const text = userInput.value.trim();
    if (!text) return;

    addMessage(text, "user");
    userInput.value = "";

    showTyping(true);

    fetch("/chat", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({ msg: text })
    })
    .then(res => {
        showTyping(false);
        if (res.status === 401) {
            return res.json().then(data => {
                addMessage(data.reply || "Please log in first.", "bot");
                return;
            });
        }
        return res.json();
    })
    .then(data => {
        if (!data) return;
        if (data.reply) addMessage(data.reply, "bot");
        if (data.reminder) setupReminder(data.reminder);
    })
    .catch(err => {
        showTyping(false);
        console.error(err);
        addMessage("Oops, something went wrong. Try again.", "bot");
    });
}

// ------------- Reminders + Notifications -------------

function requestNotificationPermission() {
    if (!("Notification" in window)) {
        console.log("This browser does not support notifications.");
        return;
    }
    if (Notification.permission === "default") {
        Notification.requestPermission();
    }
}

function showNotification(message) {
    if (!("Notification" in window)) {
        alert(message);
        return;
    }
    if (Notification.permission === "granted") {
        new Notification("Smart Health Bot", { body: message });
    } else {
        alert(message);
    }
}

function setupReminder(reminder) {
    const { message, interval_min } = reminder;
    const interval_ms = interval_min * 60 * 1000;

    addMessage(`Reminder set: "${message}" every ${interval_min} minutes. ⏰`, "bot");
    requestNotificationPermission();

    const id = setInterval(() => {
        showNotification(message);
    }, interval_ms);

    reminders.push({ id, message, interval_ms });
}

// ------------- Voice: text-to-speech -------------

function speak(text) {
    if (!("speechSynthesis" in window)) return;
    const utter = new SpeechSynthesisUtterance(text);
    window.speechSynthesis.speak(utter);
}

// ------------- Voice: speech-to-text -------------

function initSpeechRecognition() {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
        console.log("Speech recognition not supported.");
        return;
    }

    recognition = new SpeechRecognition();
    recognition.lang = "en-US";
    recognition.continuous = false;
    recognition.interimResults = false;

    recognition.onresult = (event) => {
        const transcript = event.results[0][0].transcript;
        userInput.value = transcript;
        sendMessage();
    };

    recognition.onerror = (event) => {
        console.log("Speech recognition error:", event.error);
    };
}

// ------------- Event listeners -------------

if (sendBtn && userInput) {
    sendBtn.addEventListener("click", sendMessage);
    userInput.addEventListener("keydown", (e) => {
        if (e.key === "Enter") sendMessage();
    });
}

if (voiceBtn && userInput) {
    voiceBtn.addEventListener("click", () => {
        if (!recognition) {
            initSpeechRecognition();
        }
        if (recognition) {
            recognition.start();
        } else {
            addMessage("Voice input is not supported in this browser.", "bot");
        }
    });
}

if (quickWater && userInput) {
    quickWater.addEventListener("click", () => {
        userInput.value = "Set a water reminder";
        sendMessage();
    });
}

if (quickStress && userInput) {
    quickStress.addEventListener("click", () => {
        userInput.value = "I'm feeling stressed";
        sendMessage();
    });
}

// ------------- Initial welcome message on chat page -------------

if (chatbox) {
    addMessage(
        "Hey! 👋 I'm your upgraded Smart Health Bot.\n" +
        "Ask me about water, exercise, diet, stress, sleep or say things like:\n" +
        "• 'Set a water reminder'\n" +
        "• 'Set a meal reminder'\n" +
        "• 'Set a sleep reminder'\n" +
        "• 'Remind me to study'"
    );
    requestNotificationPermission();
}
