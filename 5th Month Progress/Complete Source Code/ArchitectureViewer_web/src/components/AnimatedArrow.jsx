import React, { memo } from 'react';
import { getBezierPath } from '@xyflow/react';

function AnimatedArrow({
  id,
  sourceX,
  sourceY,
  targetX,
  targetY,
  sourcePosition,
  targetPosition,
  style = {},
  markerEnd,
}) {
  const [edgePath] = getBezierPath({
    sourceX,
    sourceY,
    targetX,
    targetY,
    sourcePosition,
    targetPosition,
  });

  return (
    <>
      {/* Glow behind */}
      <path
        d={edgePath}
        fill="none"
        stroke="url(#edge-gradient)"
        strokeWidth={4}
        strokeOpacity={0.15}
        filter="blur(4px)"
      />

      {/* Main animated path */}
      <path
        id={id}
        d={edgePath}
        fill="none"
        stroke="url(#edge-gradient)"
        strokeWidth={2}
        className="animated-edge-path"
        markerEnd={markerEnd}
      />

      {/* Flowing particle */}
      <circle r="3" fill="url(#edge-gradient)">
        <animateMotion
          dur="2.5s"
          repeatCount="indefinite"
          path={edgePath}
        />
      </circle>

      <circle r="2" fill="#22d3ee" opacity="0.6">
        <animateMotion
          dur="2.5s"
          repeatCount="indefinite"
          path={edgePath}
          begin="0.8s"
        />
      </circle>
    </>
  );
}

export default memo(AnimatedArrow);
