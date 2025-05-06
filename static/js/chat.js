// JavaScript logic
/**
 * Chat page functionality
 */

document.addEventListener('DOMContentLoaded', function() {
    // Set up chat input
    const chatInput = document.getElementById('chat-input');
    const sendButton = document.getElementById('chat-send-btn');
    
    // Handle send button click
    sendButton.addEventListener('click', function() {
        sendChatMessage();
    });
    
    // Handle Enter key in input
    chatInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            sendChatMessage();
        }
    });
    
    // Set up example questions
    const exampleQuestions = document.querySelectorAll('.example-question');
    exampleQuestions.forEach(example => {
        example.addEventListener('click', function() {
            const question = this.getAttribute('data-question');
            // Set the question in the input field
            chatInput.value = question;
            
            // Send the message
            sendChatMessage();
        });
    });
});

function sendChatMessage() {
    const chatInput = document.getElementById('chat-input');
    const chatContainer = document.getElementById('chat-container');
    const query = chatInput.value.trim();
    
    if (!query) return;
    
    // Add user message to chat
    addMessage('user', query);
    
    // Clear input
    chatInput.value = '';
    
    // Add loading message
    const loadingMsgId = addMessage('assistant', 'Thinking...');
    
    // Send request to server
    fetchChatResponse(query, loadingMsgId);
}

function addMessage(sender, text) {
    const chatContainer = document.getElementById('chat-container');
    const messageId = 'msg-' + Date.now();
    
    const messageDiv = document.createElement('div');
    messageDiv.id = messageId;
    messageDiv.className = `chat-message ${sender}-message`;
    
    const messageText = document.createElement('p');
    messageText.innerHTML = text;
    
    messageDiv.appendChild(messageText);
    chatContainer.appendChild(messageDiv);
    
    // Scroll to bottom
    chatContainer.scrollTop = chatContainer.scrollHeight;
    
    return messageId;
}

function updateMessage(messageId, text) {
    const messageDiv = document.getElementById(messageId);
    if (messageDiv) {
        const messageText = messageDiv.querySelector('p');
        messageText.innerHTML = text;
        
        // Scroll to bottom
        const chatContainer = document.getElementById('chat-container');
        chatContainer.scrollTop = chatContainer.scrollHeight;
    }
}

function addSourcesMessage(sources) {
    const chatContainer = document.getElementById('chat-container');
    
    const sourceDiv = document.createElement('div');
    sourceDiv.className = 'chat-message sources-message';
    
    const sourceText = document.createElement('p');
    sourceText.innerHTML = '<small><strong>Sources:</strong></small>';
    
    const sourceList = document.createElement('ul');
    sourceList.className = 'source-list';
    
    sources.forEach(source => {
        const sourceItem = document.createElement('li');
        const sourceLink = document.createElement('a');
        sourceLink.href = source;
        sourceLink.target = '_blank';
        sourceLink.textContent = source;
        sourceItem.appendChild(sourceLink);
        sourceList.appendChild(sourceItem);
    });
    
    sourceDiv.appendChild(sourceText);
    sourceDiv.appendChild(sourceList);
    chatContainer.appendChild(sourceDiv);
    
    // Scroll to bottom
    chatContainer.scrollTop = chatContainer.scrollHeight;
}

async function fetchChatResponse(query, loadingMsgId) {
    try {
        // Try to use streaming if available
        if (window.EventSource) {
            fetchStreamingResponse(query, loadingMsgId);
        } else {
            // Fall back to regular request
            const response = await apiRequest('/chat', 'POST', { query });
            
            // Update the message
            updateMessage(loadingMsgId, response.response);
            
            // Add sources if available
            if (response.sources && response.sources.length > 0) {
                addSourcesMessage(response.sources);
            }
        }
    } catch (error) {
        console.error('Error fetching chat response:', error);
        updateMessage(loadingMsgId, 'Sorry, I encountered an error while generating a response. Please try again.');
    }
}

function fetchStreamingResponse(query, loadingMsgId) {
    // Create event source for streaming
    const eventSource = new EventSource(`/api/chat/stream?${new URLSearchParams({ query })}`, { withCredentials: true });
    
    let responseText = '';
    
    // Handle incoming data
    eventSource.addEventListener('message', function(e) {
        const data = e.data;
        
        // Check if it's the end event
        if (data === '[END]') {
            eventSource.close();
            return;
        }
        
        // Append to response
        responseText += data;
        
        // Update the message
        updateMessage(loadingMsgId, responseText);
    });
    
    // Handle errors
    eventSource.addEventListener('error', function(e) {
        console.error('EventSource error:', e);
        eventSource.close();
        
        if (!responseText) {
            updateMessage(loadingMsgId, 'Sorry, I encountered an error while generating a response. Please try again.');
        }
    });
}