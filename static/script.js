let content = null;
let currentStep = 0;
let completedTopics = [];
let currentTopicId = null;

// Load content and user progress
async function init() {
    const res = await fetch('/static/content.json');
    content = await res.json();
    
    // Get saved progress from Flask backend
    const progRes = await fetch('/api/get_progress');
    const prog = await progRes.json();
    
    currentStep = prog.current_step || 0;
    completedTopics = JSON.parse(prog.completed_topics || '[]');
    
    renderConversation();
    renderTopics();
}

function renderConversation() {
    const chatBox = document.getElementById('chat-box');
    chatBox.innerHTML = '';
    
    // Show messages up to currentStep
    for (let i = 0; i <= currentStep && i < content.conversation.length; i++) {
        const msg = content.conversation[i];
        const div = document.createElement('div');
        div.className = `msg ${msg.speaker.toLowerCase()}`;
        
        const avatar = document.createElement('div');
        avatar.className = `avatar ${msg.speaker === 'Teacher' ? 'teacher-av' : ''}`;
        avatar.innerText = msg.speaker[0];
        
        const bubble = document.createElement('div');
        bubble.className = 'bubble';
        bubble.innerText = msg.text;
        
        if (msg.speaker === 'Teacher') {
            div.appendChild(bubble);
            div.appendChild(avatar);
        } else {
            div.appendChild(avatar);
            div.appendChild(bubble);
        }
        chatBox.appendChild(div);
    }
    chatBox.scrollTop = chatBox.scrollHeight;
    
    document.getElementById('prev-btn').disabled = currentStep === 0;
    document.getElementById('next-btn').disabled = currentStep >= content.conversation.length - 1;
    
    saveProgress();
}

function renderTopics() {
    const list = document.getElementById('topic-list');
    list.innerHTML = '';
    
    content.topics.forEach(topic => {
        const li = document.createElement('li');
        li.innerText = topic.title;
        li.dataset.id = topic.id;
        
        const isUnlocked = currentStep >= topic.unlock_step;
        const isCompleted = completedTopics.includes(topic.id);
        
        if (isCompleted) {
            li.classList.add('completed');
        } else if (!isUnlocked) {
            li.classList.add('locked');
        }
        
        if (currentTopicId === topic.id) {
            li.classList.add('active');
        }
        
        li.onclick = () => {
            if (!isUnlocked) {
                alert('Keep reading the conversation to unlock this topic!');
                return;
            }
            selectTopic(topic.id);
        };
        
        list.appendChild(li);
    });
    
    // Show submit button if all topics are completed
    const allDone = content.topics.every(t => completedTopics.includes(t.id));
    const submitBtn = document.getElementById('submit-btn');
    if (allDone) {
        submitBtn.classList.add('show');
    } else {
        submitBtn.classList.remove('show');
    }
}

function selectTopic(topicId) {
    currentTopicId = topicId;
    const topic = content.topics.find(t => t.id === topicId);
    
    document.getElementById('topic-title').innerText = topic.title;
    document.getElementById('hint-box').innerText = topic.hint;
    document.getElementById('code-editor').value = topic.starter_code;
    document.getElementById('output-console').innerText = 'Output will appear here...';
    
    renderTopics(); // Update active state
}

document.getElementById('next-btn').onclick = () => {
    if (currentStep < content.conversation.length - 1) {
        currentStep++;
        renderConversation();
        renderTopics();
    }
};

document.getElementById('prev-btn').onclick = () => {
    if (currentStep > 0) {
        currentStep--;
        renderConversation();
        renderTopics();
    }
};

document.getElementById('run-btn').onclick = async () => {
    const code = document.getElementById('code-editor').value;
    const consoleEl = document.getElementById('output-console');
    consoleEl.innerText = 'Executing...';
    
    try {
        const res = await fetch('/api/execute_code', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ code: code })
        });
        const data = await res.json();
        consoleEl.innerText = data.output;
        
        // Check if success condition is met
        if (currentTopicId) {
            const topic = content.topics.find(t => t.id === currentTopicId);
            if (data.output.includes(topic.success_condition)) {
                if (!completedTopics.includes(currentTopicId)) {
                    completedTopics.push(currentTopicId);
                    saveProgress();
                    renderTopics();
                    consoleEl.innerText += '\n\n✅ SUCCESS! Topic Completed!';
                }
            }
        }
    } catch (err) {
        consoleEl.innerText = 'Error connecting to server.';
    }
};

document.getElementById('submit-btn').onclick = () => {
    document.getElementById('modal-overlay').style.display = 'flex';
};

async function saveProgress() {
    await fetch('/api/save_progress', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            step: currentStep,
            topics: JSON.stringify(completedTopics)
        })
    });
}

// Initialize on load
window.onload = init;