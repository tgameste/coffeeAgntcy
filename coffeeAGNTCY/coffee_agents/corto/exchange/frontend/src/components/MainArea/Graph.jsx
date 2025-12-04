/**
* Copyright AGNTCY Contributors (https://github.com/agntcy)
* SPDX-License-Identifier: Apache-2.0
**/

import React, { useEffect, useRef, useCallback } from 'react';
import {
    ReactFlow,
    ReactFlowProvider,
    useNodesState,
    useEdgesState,
    Controls,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import { FaCloudSun } from 'react-icons/fa';
import SlimNode from './SlimNode';
import CustomEdge from './CustomEdge';
import CustomNode from './CustomNode';
import { EdgeLabelIcon } from '../../utils/const.js';
import supervisorIcon from '../../assets/supervisor.png'; // Adjust the path to your PNG file
import { PiCoffeeBeanThin } from "react-icons/pi";

const CoffeeBeanIcon = <PiCoffeeBeanThin style={{ transform: 'rotate(-30deg)', fontSize: '1.65em' }} />;

const proOptions = { hideAttribution: true };

// Node types
const nodeTypes = {
    slimNode: SlimNode,
    customNode: CustomNode,
};

// Constants
const DELAY_DURATION = 500; // Animation delay in milliseconds

// Colors
const COLORS = {
    NODE: {
        ORIGINAL: { BACKGROUND: '#F5F5F5' },
    },
};

const HIGHLIGHT = {
    ON: true,
    OFF: false,
};

// Node and Edge IDs
const NODE_IDS = {
    SUPERVISOR: '1',
    FLAVOR_AGENT: '2',
    WEATHER_AGENT: '3',
};

const EDGE_IDS = {
    SUPERVISOR_TO_FLAVOR: '1-2',
    SUPERVISOR_TO_WEATHER: '1-3',
};

// Initial nodes
const commonNodeData = {
    backgroundColor: COLORS.NODE.ORIGINAL.BACKGROUND,
};

const initialNodes = [
    {
        id: NODE_IDS.SUPERVISOR,
        type: 'customNode',
        data: {
            ...commonNodeData,
            icon: <img src={supervisorIcon} alt="Supervisor Icon" style={{ marginLeft: '2.5px', width: '120%', height: '100%' }} />,
            label1: 'Supervisor Agent',
            label2: 'Exchange',
            handles: 'source',
        },
        position: { x: 400, y: 50 },
    },
    {
        id: NODE_IDS.FLAVOR_AGENT,
        type: 'customNode',
        data: {
            ...commonNodeData,
            icon: CoffeeBeanIcon,
            label1: 'Flavor Agent',
            label2: 'Farm',
            handles: 'target',
        },
        position: { x: 200, y: 350 },
    },
    {
        id: NODE_IDS.WEATHER_AGENT,
        type: 'customNode',
        data: {
            ...commonNodeData,
            icon: <FaCloudSun style={{ fontSize: '1.65em' }} />,
            label1: 'Weather Agent',
            label2: 'Weather',
            handles: 'target',
        },
        position: { x: 600, y: 350 },
    },
];

// Edge types
const edgeTypes = {
    custom: CustomEdge,
};

// Initial edges
const initialEdges = [
    {
        id: EDGE_IDS.SUPERVISOR_TO_FLAVOR,
        source: NODE_IDS.SUPERVISOR,
        target: NODE_IDS.FLAVOR_AGENT,
        data: { 
            label: 'A2A : SLIM', 
            labelIconType: EdgeLabelIcon.A2A,
            topic: 'default/default/Coffee_Farm_Flavor_Agent_1.0.0'
        },
        type: 'custom',
    },
    {
        id: EDGE_IDS.SUPERVISOR_TO_WEATHER,
        source: NODE_IDS.SUPERVISOR,
        target: NODE_IDS.WEATHER_AGENT,
        data: { 
            label: 'A2A : SLIM', 
            labelIconType: EdgeLabelIcon.A2A,
            topic: 'default/default/Coffee_Weather_Agent_1.0.0'
        },
        type: 'custom',
    },
];

const Graph = ({ buttonClicked, setButtonClicked, aiReplied, setAiReplied, activeAgent = 'both', messageCounts = { flavor: 0, weather: 0 }, setMessageCounts }) => {
    const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
    const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);
    const animationLock = useRef(false); // Lock to prevent overlapping animations
    
    // Update edge data with message counts
    useEffect(() => {
        setEdges((currentEdges) =>
            currentEdges.map((edge) => {
                if (edge.id === EDGE_IDS.SUPERVISOR_TO_FLAVOR) {
                    return {
                        ...edge,
                        data: {
                            ...edge.data,
                            messageCount: messageCounts.flavor || 0,
                        },
                    };
                }
                if (edge.id === EDGE_IDS.SUPERVISOR_TO_WEATHER) {
                    return {
                        ...edge,
                        data: {
                            ...edge.data,
                            messageCount: messageCounts.weather || 0,
                        },
                    };
                }
                return edge;
            })
        );
    }, [messageCounts, setEdges]);

    useEffect(() => {
        if (nodes) {
            nodes.forEach((node) => {
                console.log(`Node ID: ${node.id}, Position: X=${node.position.x}, Y=${node.position.y}`);
            });
        }
    }, [nodes]);

    const delay = useCallback((ms) => new Promise((resolve) => setTimeout(resolve, ms)), []);

    const updateStyle = useCallback((id, active) => {
        setNodes((objs) =>
            objs.map((obj) =>
                obj.id === id
                    ? { ...obj, data: { ...obj.data, active } }
                    : obj
            )
        );
        setEdges((objs) =>
            objs.map((obj) =>
                obj.id === id
                    ? { ...obj, data: { ...obj.data, active } }
                    : obj
            )
        );
    }, [setNodes, setEdges]);

    useEffect(() => {
        if (!buttonClicked && !aiReplied) return;
        if (animationLock.current) return; // Prevent overlapping animations
        animationLock.current = true;

        const animate = async (ids, active) => {
            ids.forEach((id) => updateStyle(id, active));
            await delay(DELAY_DURATION);
        };

        const animateGraph = async () => {
            if (!aiReplied) {
                // Increment message counts based on activeAgent
                if (setMessageCounts) {
                    setMessageCounts((prev) => {
                        const newCounts = { ...prev };
                        if (activeAgent === 'weather') {
                            newCounts.weather = (newCounts.weather || 0) + 1;
                        } else if (activeAgent === 'flavor') {
                            newCounts.flavor = (newCounts.flavor || 0) + 1;
                        } else if (activeAgent === 'both') {
                            // For 'both', increment both counts
                            newCounts.flavor = (newCounts.flavor || 0) + 1;
                            newCounts.weather = (newCounts.weather || 0) + 1;
                        }
                        return newCounts;
                    });
                }
                
                // Forward animation - Supervisor first
                await animate([NODE_IDS.SUPERVISOR], HIGHLIGHT.ON);
                await animate([NODE_IDS.SUPERVISOR], HIGHLIGHT.OFF);

                // Determine which edges and nodes to animate based on activeAgent
                let edgesToAnimate = [];
                let nodesToAnimate = [];

                if (activeAgent === 'weather') {
                    // Only weather agent
                    edgesToAnimate = [EDGE_IDS.SUPERVISOR_TO_WEATHER];
                    nodesToAnimate = [NODE_IDS.WEATHER_AGENT];
                } else if (activeAgent === 'flavor') {
                    // Only flavor agent
                    edgesToAnimate = [EDGE_IDS.SUPERVISOR_TO_FLAVOR];
                    nodesToAnimate = [NODE_IDS.FLAVOR_AGENT];
                } else {
                    // Both agents (capability question or unknown)
                    edgesToAnimate = [EDGE_IDS.SUPERVISOR_TO_FLAVOR, EDGE_IDS.SUPERVISOR_TO_WEATHER];
                    nodesToAnimate = [NODE_IDS.FLAVOR_AGENT, NODE_IDS.WEATHER_AGENT];
                }

                // Animate only the relevant edges
                await animate(edgesToAnimate, HIGHLIGHT.ON);
                await animate(edgesToAnimate, HIGHLIGHT.OFF);

                // Animate only the relevant target agents
                await animate(nodesToAnimate, HIGHLIGHT.ON);
                await animate(nodesToAnimate, HIGHLIGHT.OFF);
            } else {
                // Backward animation
                setAiReplied(false);
            }

            setButtonClicked(false);
            animationLock.current = false; // Release the lock
        };

        animateGraph();
    }, [buttonClicked, setButtonClicked, aiReplied, setAiReplied, activeAgent, setMessageCounts, delay, updateStyle]);

    return (
        <div style={{ width: '100%', height: '100%' }}>
            <ReactFlow
                nodes={nodes}
                edges={edges}
                nodeTypes={nodeTypes}
                edgeTypes={edgeTypes}
                onNodesChange={onNodesChange}
                onEdgesChange={onEdgesChange}
                proOptions={proOptions}
            >
                <Controls />
            </ReactFlow>
        </div>
    );
};

const FlowWithProvider = (props) => (
    <ReactFlowProvider>
        <Graph {...props} />
    </ReactFlowProvider>
);

export default FlowWithProvider;