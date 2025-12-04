/**
* Copyright AGNTCY Contributors (https://github.com/agntcy)
* SPDX-License-Identifier: Apache-2.0
**/

/** @jsxImportSource @emotion/react */
import React from 'react';
import { EdgeLabelRenderer } from '@xyflow/react';
import { css } from '@emotion/react';
import './styles/CustomEdgeLabel.css';

const CustomEdgeLabel = ({ x, y, label, icon, topic, messageCount = 0 }) => {
    const [showTooltip, setShowTooltip] = React.useState(false);
    
    const dynamicStyle = css`
        position: absolute;
        left: ${x}px;
        top: ${y}px;
    `;

    const getLabelClasses = (label) => {
        const baseClass = 'custom-edge-label';
        const iconClass = 'custom-edge-label-icon';
        const textClass = 'custom-edge-label-text';

        if (label?.toLowerCase().endsWith('slim')) {
            return {
                labelClass: `${baseClass} ${baseClass}-with-slim`,
                iconClass: `${iconClass} ${iconClass}-with-slim`,
                textClass: `${textClass} ${textClass}-with-slim`,
            };
        }

        return { labelClass: baseClass, iconClass, textClass };
    };

    const { labelClass, iconClass, textClass } = getLabelClasses(label);

    const EdgeLabelWrapper = topic ? 'button' : 'div';
    const wrapperProps = topic ? {
        onFocus: () => setShowTooltip(true),
        onBlur: () => setShowTooltip(false),
        onKeyDown: (e) => {
            if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                setShowTooltip(!showTooltip);
            }
        },
        tabIndex: 0,
        'aria-label': `SLIM Topic: ${topic}`,
        style: { position: 'relative', cursor: 'help', border: 'none', background: 'transparent', padding: 0, margin: 0 }
    } : {
        style: { position: 'relative' }
    };

    return (
        <EdgeLabelRenderer>
            <EdgeLabelWrapper
                className={labelClass} 
                css={dynamicStyle}
                onMouseEnter={() => topic && setShowTooltip(true)}
                onMouseLeave={() => setShowTooltip(false)}
                title={topic || undefined}
                {...wrapperProps}
            >
                <div className={iconClass}>{icon}</div>
                <div className={textClass}>
                    {label}
                    {messageCount > 0 && (
                        <span className="message-count-badge" title={`${messageCount} message${messageCount !== 1 ? 's' : ''} sent`}>
                            {messageCount}
                        </span>
                    )}
                </div>
                {showTooltip && topic && (
                    <div className="edge-tooltip" role="tooltip">
                        <div className="edge-tooltip-content">
                            <div className="edge-tooltip-title">SLIM Topic:</div>
                            <div className="edge-tooltip-text">{topic}</div>
                            {messageCount > 0 && (
                                <>
                                    <div className="edge-tooltip-divider"></div>
                                    <div className="edge-tooltip-title">Messages:</div>
                                    <div className="edge-tooltip-text">{messageCount} message{messageCount !== 1 ? 's' : ''} sent</div>
                                </>
                            )}
                        </div>
                    </div>
                )}
            </EdgeLabelWrapper>
        </EdgeLabelRenderer>
    );
};

export default CustomEdgeLabel;