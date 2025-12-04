/**
* Copyright AGNTCY Contributors (https://github.com/agntcy)
* SPDX-License-Identifier: Apache-2.0
**/

import React, { useState } from 'react';
import { IoSendSharp } from 'react-icons/io5';
import { v4 as uuid } from 'uuid';
import axios from 'axios';
import { Role } from '../../utils/const.js';
import './styles/Messages.css';

const DEFAULT_EXCHANGE_APP_API_URL = 'http://localhost:8000';

// Helper function to detect which agent should be used based on the query
const detectAgentType = (query) => {
    const lowerQuery = query.toLowerCase();
    const weatherKeywords = ['weather', 'temperature', 'climate', 'current conditions', 'get weather', 'what\'s the weather', 'weather in', 'weather for', 'temperature in', 'climate in'];
    const flavorKeywords = ['flavor', 'taste', 'sensory', 'profile', 'notes', 'aroma', 'acidity', 'body', 'finish'];
    
    // Check for weather keywords first
    if (weatherKeywords.some(keyword => lowerQuery.includes(keyword))) {
        return 'weather';
    }
    
    // Check for flavor keywords
    if (flavorKeywords.some(keyword => lowerQuery.includes(keyword))) {
        return 'flavor';
    }
    
    // Default to both (capability question or unknown)
    return 'both';
};

function MessageInput({ messages, setMessages, setButtonClicked, setAiReplied, setActiveAgent, threadId, setThreadId, streaming }) {
    const [content, setContent] = useState("");
    const [loading, setLoading] = useState(false);

    const processMessage = async () => {
        if (!content.trim()) return;

        const userMessage = {
            role: Role.USER,
            content: content,
            id: uuid(),
            animate: false,
        };

        const loadingMessage = {
            role: 'assistant',
            content: "Loading...",
            id: uuid(),
            animate: false,
            loading: true,
        };

        const updatedMessages = [...messages, userMessage, loadingMessage];
        setLoading(true);

        // Detect which agent should be used
        const agentType = detectAgentType(content);
        if (setActiveAgent) {
            setActiveAgent(agentType);
        }

        setMessages(updatedMessages);
        setContent('');
        setButtonClicked(true);

        try {
            const apiUrl = import.meta.env.VITE_EXCHANGE_APP_API_URL || DEFAULT_EXCHANGE_APP_API_URL;
            console.log('[MessageInput] API URL:', apiUrl);
            console.log('[MessageInput] Sending request to:', `${apiUrl}/agent/prompt`);
            console.log('[MessageInput] Request payload:', { prompt: content, thread_id: threadId, stream: streaming });
            
            if (streaming) {
                // Streaming mode
                const response = await fetch(`${apiUrl}/agent/prompt`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        prompt: content,
                        thread_id: threadId,
                        stream: true,
                    }),
                });

                const reader = response.body.getReader();
                const decoder = new TextDecoder();
                let accumulatedContent = '';
                let currentThreadId = threadId;

                // Remove loading message and add streaming message
                const streamingMessage = {
                    role: 'assistant',
                    content: '',
                    id: uuid(),
                    animate: false,
                    loading: false,
                };
                setMessages([...messages, userMessage, streamingMessage]);

                while (true) {
                    const { done, value } = await reader.read();
                    if (done) break;

                    const chunk = decoder.decode(value);
                    const lines = chunk.split('\n');

                    for (const line of lines) {
                        if (line.startsWith('data: ')) {
                            try {
                                const data = JSON.parse(line.slice(6));
                                if (data.done) {
                                    if (data.thread_id && setThreadId) {
                                        setThreadId(data.thread_id);
                                    }
                                    break;
                                }
                                if (data.error) {
                                    throw new Error(data.error);
                                }
                                if (data.content) {
                                    accumulatedContent += data.content;
                                    if (data.thread_id) {
                                        currentThreadId = data.thread_id;
                                    }
                                    // Update streaming message
                                    const updatedStreamingMessage = {
                                        ...streamingMessage,
                                        content: accumulatedContent,
                                    };
                                    setMessages([...messages, userMessage, updatedStreamingMessage]);
                                }
                            } catch (e) {
                                console.error("Error parsing stream data:", e);
                            }
                        }
                    }
                }

                // Final update
                if (currentThreadId && setThreadId) {
                    setThreadId(currentThreadId);
                }
                const finalMessage = {
                    ...streamingMessage,
                    content: accumulatedContent || "No content received.",
                    animate: true,
                };
                setMessages([...messages, userMessage, finalMessage]);
            } else {
                // Non-streaming mode
                const resp = await axios.post(`${apiUrl}/agent/prompt`, {
                    prompt: content,
                    thread_id: threadId,
                    stream: false,
                });

                // Update thread_id if returned
                if (resp.data?.thread_id && setThreadId) {
                    setThreadId(resp.data.thread_id);
                }

                const aiReply = {
                    role: 'assistant',
                    content: resp.data?.response || "No content received.",
                    id: uuid(),
                    animate: true,
                };

                setMessages([...messages, userMessage, aiReply]);
            }
        } catch (error) {
            console.error("[MessageInput] Error while sending prompt to the server:", error);
            console.error("[MessageInput] Error details:", {
                message: error.message,
                response: error.response?.data,
                status: error.response?.status,
                statusText: error.response?.statusText,
                url: error.config?.url || error.request?.url
            });

            const errorReply = {
                role: 'assistant',
                content: error.response?.data?.detail || error.message || "Error from server.",
                id: uuid(),
                animate: true,
            };

            setMessages([...messages, userMessage, errorReply]);
        } finally {
            setLoading(false);
            setAiReplied(true);
        }
    };

    const handleSendMessage = () => {
        if (content.trim().length > 0) {
            processMessage();
        }
    };

    const handleKeyPressed = (event) => {
        if ((event.code === 'Enter' || event.code === 'NumpadEnter') && content.trim().length > 0) {
            processMessage();
        }
    };

    return (
        <div className="message-input-container">
            <input
                className="message-input"
                placeholder="Enter your prompt..."
                value={content}
                onChange={(e) => setContent(e.target.value)}
                onKeyDown={handleKeyPressed}
                disabled={loading}
            />
            <div
                className={`icon-container ${!content.trim() || loading ? 'disabled' : ''}`}
                onClick={!content.trim() || loading ? null : handleSendMessage}
            >
                <IoSendSharp color="#00BCEB" />
            </div>
        </div>
    );
}

export default MessageInput;