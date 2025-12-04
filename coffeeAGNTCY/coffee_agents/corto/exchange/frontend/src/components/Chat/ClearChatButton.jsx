/**
* Copyright AGNTCY Contributors (https://github.com/agntcy)
* SPDX-License-Identifier: Apache-2.0
**/

import React, { useState } from 'react';
import { LOCAL_STORAGE_KEY } from './Messages';
import { v4 as uuid } from 'uuid';
import { MdDeleteSweep } from 'react-icons/md';
import { Role } from '../../utils/const.js';
import './styles/Chat.css';

const ClearChatButton = ({ 
    setMessages, 
    setButtonClicked, 
    setAiReplied, 
    setActiveAgent 
}) => {
    const [showConfirm, setShowConfirm] = useState(false);

    const clearChat = () => {
        const initialMessage = {
            role: Role.ASSISTANT,
            content: 'Hi! How can I assist you?',
            id: uuid(),
            animate: false,
        };
        
        // Reset all conversation state
        setMessages([initialMessage]);
        if (setButtonClicked) setButtonClicked(false);
        if (setAiReplied) setAiReplied(false);
        if (setActiveAgent) setActiveAgent('both');
        
        // Clear localStorage
        localStorage.setItem(LOCAL_STORAGE_KEY, JSON.stringify([initialMessage]));
        
        // Hide confirmation dialog
        setShowConfirm(false);
    };

    const handleClick = (e) => {
        e.stopPropagation();
        if (showConfirm) {
            clearChat();
        } else {
            setShowConfirm(true);
            // Auto-hide confirmation after 3 seconds if not clicked
            setTimeout(() => setShowConfirm(false), 3000);
        }
    };

    return (
        <div className="clear-chat-button-wrapper">
            <button 
                onClick={handleClick} 
                className="clear-chat-button" 
                title={showConfirm ? "Click again to confirm" : "Clear Chat"}
            >
                <MdDeleteSweep size={20} />
            </button>
            {showConfirm && (
                <div className="clear-chat-confirm" onClick={(e) => e.stopPropagation()}>
                    <span>Clear conversation?</span>
                </div>
            )}
        </div>
    );
};

export default ClearChatButton;