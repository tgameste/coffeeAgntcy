/**
* Copyright AGNTCY Contributors (https://github.com/agntcy)
* SPDX-License-Identifier: Apache-2.0
**/

import React, { useEffect, useRef, useState } from 'react';
import { HiUser } from 'react-icons/hi';
import { RiRobot2Fill } from "react-icons/ri";
import { Waveform } from 'ldrs/react';
import 'ldrs/react/Waveform.css';
import './styles/Messages.css';

const SlowText = ({ text, speed = 25 }) => {
    const [displayedText, setDisplayedText] = useState('');
    const idx = useRef(-1);

    useEffect(() => {
        // Reset when text changes
        idx.current = -1;
        setDisplayedText('');
        
        function tick() {
            idx.current++;
            if (idx.current < text.length) {
                setDisplayedText((prev) => prev + text[idx.current]);
            }
        }

        if (text.length > 0) {
            const addChar = setInterval(() => {
                if (idx.current < text.length - 1) {
                    tick();
                } else {
                    clearInterval(addChar);
                }
            }, speed);
            return () => clearInterval(addChar);
        }
    }, [speed, text]);

    return <span>{displayedText}</span>;
};

function Message({ content, aiMessage, animate, loading, agentType }) {
    // Determine agent label and styling
    const getAgentInfo = () => {
        switch (agentType) {
            case 'supervisor':
                return { label: 'Supervisor', color: '#187ADC', icon: <RiRobot2Fill color="#187ADC" /> };
            case 'weather':
                return { label: 'Weather Agent', color: '#10B981', icon: <RiRobot2Fill color="#10B981" /> };
            case 'flavor':
                return { label: 'Flavor Agent', color: '#F59E0B', icon: <RiRobot2Fill color="#F59E0B" /> };
            default:
                return { label: 'Assistant', color: '#049FD9', icon: <RiRobot2Fill color="#049FD9" /> };
        }
    };

    const agentInfo = aiMessage ? getAgentInfo() : null;

    return (
        <div className={`message-container ${aiMessage ? 'ai-message' : ''} ${agentType ? `agent-${agentType}` : ''}`}>
            <div className="avatar-container">
                {aiMessage ? agentInfo.icon : <HiUser />}
            </div>
            <div className="message-content-wrapper">
                {aiMessage && agentType && (
                    <div className="agent-label" style={{ color: agentInfo.color }}>
                        {agentInfo.label}
                    </div>
                )}
                <div className="message-text">
                    {loading ? (
                        <div style={{ opacity: 0.5 }}>
                            <Waveform size="20" stroke="3.5" speed="1" color={agentInfo?.color || "#049FD9"} />
                        </div>
                    ) : animate ? (
                        <SlowText speed={20} text={content} />
                    ) : (
                        content
                    )}
                </div>
            </div>
        </div>
    );
}

export default Message;