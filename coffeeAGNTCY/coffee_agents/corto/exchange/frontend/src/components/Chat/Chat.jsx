/**
* Copyright AGNTCY Contributors (https://github.com/agntcy)
* SPDX-License-Identifier: Apache-2.0
**/

import React, { useEffect, useRef, useState } from 'react';
import './styles/Chat.css';
import MessageInput from './MessageInput';
import Messages, { LOCAL_STORAGE_KEY } from './Messages';
import ClearChatButton from "./ClearChatButton.jsx";
import { Role } from '../../utils/const.js';

const Chat = ({ messages, setMessages, setButtonClicked, setAiReplied, setActiveAgent, threadId, setThreadId, streaming, setStreaming, setMessageCounts }) => {
    const [headerVisible, setHeaderVisible] = useState(true);

    const handleScroll = (e) => {
        const { scrollTop } = e.target;
        setHeaderVisible(scrollTop === 0); // Show header when at the top

    };

    useEffect(() => {
    localStorage.setItem(LOCAL_STORAGE_KEY, JSON.stringify(messages));
    }, [messages]);

    useEffect(() => {
    const updated = messages.map((msg) =>
        msg.role === Role.ASSISTANT && msg.animate ? { ...msg, animate: false } : msg
    );

    const needsUpdate = JSON.stringify(messages) !== JSON.stringify(updated);
    if (needsUpdate) {
      setMessages(updated);
      localStorage.setItem(LOCAL_STORAGE_KEY, JSON.stringify(updated));
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []);

    return (
        <div className="chat_container">
            <div className="chat_header_info">
                <div className="thread_id_display">
                    <span className="thread_id_label">Thread ID:</span>
                    {threadId ? (
                        <span className="thread_id_value" title={threadId}>
                            {threadId.substring(0, 8)}...
                        </span>
                    ) : (
                        <span className="thread_id_placeholder">Not set</span>
                    )}
                </div>
                <div className="streaming_toggle_container">
                    <label className="streaming_toggle_label">
                        <input
                            type="checkbox"
                            checked={streaming}
                            onChange={(e) => setStreaming(e.target.checked)}
                            className="streaming_toggle"
                        />
                        <span>Streaming</span>
                    </label>
                </div>
            </div>
            <div className="clear_chat_button_container">
                <ClearChatButton 
                    setMessages={setMessages}
                    setButtonClicked={setButtonClicked}
                    setAiReplied={setAiReplied}
                    setActiveAgent={setActiveAgent}
                    setThreadId={setThreadId}
                    setMessageCounts={setMessageCounts}
                />
            </div>
            <div className="messages_container" onScroll={handleScroll}>
                <Messages messages={messages} setMessages={setMessages} />
            </div>
            <div className="message_input_container">
                <MessageInput
                    messages={messages}
                    setMessages={setMessages}
                    setButtonClicked={setButtonClicked}
                    setAiReplied={setAiReplied}
                    setActiveAgent={setActiveAgent}
                    threadId={threadId}
                    setThreadId={setThreadId}
                    streaming={streaming}
                />
            </div>
        </div>
    );
};

export default Chat;
