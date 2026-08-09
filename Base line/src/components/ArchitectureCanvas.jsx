import React, { useCallback, useMemo, useRef } from 'react';
import {
  ReactFlow,
  MiniMap,
  Controls,
  Background,
  BackgroundVariant,
  useNodesState,
  useEdgesState,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';

import NodeCard from './NodeCard';
import AnimatedArrow from './AnimatedArrow';
import { nodeData } from '../data/nodes';
import { edgeData } from '../data/edges';

const nodeTypes = { archNode: NodeCard };
const edgeTypes = { animatedEdge: AnimatedArrow };

const defaultEdgeOptions = {
  type: 'animatedEdge',
  animated: true,
};

const proOptions = { hideAttribution: true };

export default function ArchitectureCanvas({ onNodeClick, darkMode, searchTerm }) {
  const [nodes, setNodes, onNodesChange] = useNodesState(nodeData);
  const [edges, setEdges, onEdgesChange] = useEdgesState(edgeData);

  const handleNodeClick = useCallback(
    (event, node) => {
      if (node.data.module) {
        onNodeClick(node.data.module);
      }
    },
    [onNodeClick]
  );

  // Filter nodes based on search
  const filteredNodes = useMemo(() => {
    if (!searchTerm) return nodes;
    return nodes.map((node) => ({
      ...node,
      className: node.data.label.toLowerCase().includes(searchTerm.toLowerCase())
        ? 'matched'
        : '',
      style: {
        ...node.style,
        opacity: node.data.label.toLowerCase().includes(searchTerm.toLowerCase()) ? 1 : 0.25,
        transition: 'opacity 0.3s ease',
      },
    }));
  }, [nodes, searchTerm]);

  return (
    <div className="w-full h-full">
      <ReactFlow
        nodes={filteredNodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onNodeClick={handleNodeClick}
        nodeTypes={nodeTypes}
        edgeTypes={edgeTypes}
        defaultEdgeOptions={defaultEdgeOptions}
        proOptions={proOptions}
        fitView
        fitViewOptions={{ padding: 0.15, maxZoom: 1.2 }}
        minZoom={0.3}
        maxZoom={2.5}
        nodesDraggable={false}
        nodesConnectable={false}
        elementsSelectable={true}
        panOnScroll={true}
        zoomOnScroll={true}
        className={darkMode ? 'dark' : ''}
      >
        {/* SVG Defs for gradient */}
        <svg width="0" height="0">
          <defs>
            <linearGradient id="edge-gradient" x1="0%" y1="0%" x2="0%" y2="100%">
              <stop offset="0%" stopColor="#3b82f6" />
              <stop offset="50%" stopColor="#06b6d4" />
              <stop offset="100%" stopColor="#a855f7" />
            </linearGradient>
            <marker
              id="arrow-marker"
              viewBox="0 0 10 10"
              refX="5"
              refY="5"
              markerWidth="6"
              markerHeight="6"
              orient="auto-start-reverse"
            >
              <path d="M 0 0 L 10 5 L 0 10 z" fill="#06b6d4" />
            </marker>
          </defs>
        </svg>

        <Background
          variant={BackgroundVariant.Dots}
          gap={24}
          size={1.5}
          color={darkMode ? 'rgba(148, 163, 184, 0.15)' : 'rgba(148, 163, 184, 0.35)'}
        />

        <Controls
          showInteractive={false}
          className={darkMode ? '!bg-slate-800/90 !border-slate-700/50' : '!bg-white/90'}
        />

        <MiniMap
          nodeColor={(n) => {
            const colorMap = { blue: '#3b82f6', cyan: '#06b6d4', purple: '#a855f7' };
            return colorMap[n.data?.color] || '#94a3b8';
          }}
          maskColor={darkMode ? 'rgba(15, 23, 42, 0.8)' : 'rgba(241, 245, 249, 0.8)'}
          style={{
            backgroundColor: darkMode ? 'rgba(15, 23, 42, 0.9)' : 'rgba(255, 255, 255, 0.9)',
          }}
          pannable
          zoomable
        />
      </ReactFlow>
    </div>
  );
}
