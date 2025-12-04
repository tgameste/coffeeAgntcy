/**
* Copyright AGNTCY Contributors (https://github.com/agntcy)
* SPDX-License-Identifier: Apache-2.0
**/

import React, { useState, useEffect } from 'react';
import Graph from './components/MainArea/Graph';
import Chat from './components/Chat/Chat';
import './App.css';
import { v4 as uuid } from 'uuid';
import { LOCAL_STORAGE_KEY } from './components/Chat/Messages';
import ChatLogo from './components/Chat/ChatLogo';
import CodePopUp from "./components/MainArea/CodePopUp.jsx"; // Import the ChatLogo component

const App = () => {
    const [aiReplied, setAiReplied] = useState(false);
    const [messages, setMessages] = useState(() => {
        const saved = localStorage.getItem(LOCAL_STORAGE_KEY);
        return saved
            ? JSON.parse(saved)
            : [{ role: 'assistant', content: 'Hi! How can I assist you?', id: uuid(), animate: false }];
    });

    const [buttonClicked, setButtonClicked] = useState(false);
    const [activeAgent, setActiveAgent] = useState('both'); // 'weather', 'flavor', or 'both'
    const [threadId, setThreadId] = useState(() => {
        const saved = localStorage.getItem('thread_id');
        return saved || null;
    });
    const [streaming, setStreaming] = useState(false);
    
    // Message counts for each SLIM edge
    const [messageCounts, setMessageCounts] = useState(() => {
        const saved = localStorage.getItem('slim_message_counts');
        return saved ? JSON.parse(saved) : { flavor: 0, weather: 0 };
    });

    useEffect(() => {
        localStorage.setItem(LOCAL_STORAGE_KEY, JSON.stringify(messages));
    }, [messages]);

    useEffect(() => {
        if (threadId) {
            localStorage.setItem('thread_id', threadId);
        }
    }, [threadId]);

    useEffect(() => {
        localStorage.setItem('slim_message_counts', JSON.stringify(messageCounts));
    }, [messageCounts]);

    return (
        <div className="app-container">
            <div className="sidebar">
                <ChatLogo />
                <Chat
                    messages={messages}
                    setMessages={setMessages}
                    setButtonClicked={setButtonClicked}
                    setAiReplied={setAiReplied}
                    setActiveAgent={setActiveAgent}
                    threadId={threadId}
                    setThreadId={setThreadId}
                    streaming={streaming}
                    setStreaming={setStreaming}
                    setMessageCounts={setMessageCounts}
                />
            </div>
            <div className="main-area">
                <header className="header">
                    Grader Conversation
                </header>
                <div className="code_popup_container">
                    <CodePopUp/>
                </div>
                <div className="graph_container">
                    <Graph buttonClicked={buttonClicked}
                           setButtonClicked={setButtonClicked}
                           aiReplied={aiReplied}
                           setAiReplied={setAiReplied}
                           activeAgent={activeAgent}
                           messageCounts={messageCounts}
                           setMessageCounts={setMessageCounts}
                    />
                </div>
            </div>
        </div>
    );
};

export default App;
