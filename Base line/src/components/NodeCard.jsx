import React, { memo, useState } from 'react';
import { Handle, Position } from '@xyflow/react';
import { motion } from 'framer-motion';
import { iconMap } from '../data/nodes';

const colorStyles = {
  blue: {
    gradient: 'from-blue-500 to-blue-600',
    border: 'border-blue-200/60',
    borderDark: 'border-blue-500/30',
    glow: '0 0 20px rgba(59, 130, 246, 0.3), 0 0 60px rgba(59, 130, 246, 0.1)',
    iconBg: 'bg-blue-500/10',
    iconColor: 'text-blue-500',
    ring: 'ring-blue-400/40',
  },
  cyan: {
    gradient: 'from-cyan-500 to-cyan-600',
    border: 'border-cyan-200/60',
    borderDark: 'border-cyan-500/30',
    glow: '0 0 20px rgba(6, 182, 212, 0.3), 0 0 60px rgba(6, 182, 212, 0.1)',
    iconBg: 'bg-cyan-500/10',
    iconColor: 'text-cyan-500',
    ring: 'ring-cyan-400/40',
  },
  purple: {
    gradient: 'from-purple-500 to-purple-600',
    border: 'border-purple-200/60',
    borderDark: 'border-purple-500/30',
    glow: '0 0 20px rgba(168, 85, 247, 0.3), 0 0 60px rgba(168, 85, 247, 0.1)',
    iconBg: 'bg-purple-500/10',
    iconColor: 'text-purple-500',
    ring: 'ring-purple-400/40',
  },
};

function NodeCard({ data, selected }) {
  const [isHovered, setIsHovered] = useState(false);
  const style = colorStyles[data.color] || colorStyles.blue;
  const IconComponent = iconMap[data.icon];
  const isLarge = data.large;
  const hasModule = !!data.module;

  return (
    <>
      <Handle
        type="target"
        position={Position.Top}
        className="!w-2 !h-2 !bg-slate-400 !border-none !-top-1"
      />

      <motion.div
        onHoverStart={() => setIsHovered(true)}
        onHoverEnd={() => setIsHovered(false)}
        whileHover={{ scale: 1.05, y: -2 }}
        whileTap={{ scale: 0.98 }}
        transition={{ type: 'spring', stiffness: 400, damping: 25 }}
        className={`
          relative group cursor-pointer select-none
          ${isLarge ? 'min-w-[220px]' : 'min-w-[180px]'}
        `}
        style={{
          boxShadow: isHovered ? style.glow : '0 4px 20px rgba(0, 0, 0, 0.06)',
        }}
      >
        {/* Gradient border top */}
        <div className={`absolute inset-x-0 top-0 h-[2px] rounded-t-2xl bg-gradient-to-r ${style.gradient} opacity-80`} />

        {/* Card body */}
        <div
          className={`
            glass rounded-2xl px-4 py-3
            ${style.border}
            transition-all duration-300
            ${isHovered ? `ring-2 ${style.ring}` : ''}
          `}
        >
          <div className="flex items-center gap-3">
            {/* Icon */}
            <div className={`
              flex items-center justify-center w-9 h-9 rounded-xl
              ${style.iconBg}
              transition-all duration-300
            `}>
              {IconComponent && (
                <IconComponent
                  size={18}
                  className={`${style.iconColor} transition-all duration-300`}
                />
              )}
            </div>

            {/* Label & description */}
            <div className="flex flex-col min-w-0">
              <span className="text-[13px] font-semibold text-slate-800 dark:text-slate-100 leading-tight truncate">
                {data.label}
              </span>
              {data.description && (
                <span className="text-[10px] text-slate-500 dark:text-slate-400 leading-tight mt-0.5 truncate">
                  {data.description}
                </span>
              )}
            </div>

            {/* Click indicator */}
            {hasModule && (
              <motion.div
                animate={{ scale: [1, 1.2, 1] }}
                transition={{ repeat: Infinity, duration: 2, ease: 'easeInOut' }}
                className={`
                  ml-auto w-2 h-2 rounded-full
                  bg-gradient-to-r ${style.gradient}
                `}
              />
            )}
          </div>
        </div>

        {/* Hover tooltip */}
        {hasModule && isHovered && (
          <motion.div
            initial={{ opacity: 0, y: 4 }}
            animate={{ opacity: 1, y: 0 }}
            className="absolute -bottom-7 left-1/2 -translate-x-1/2 whitespace-nowrap
                        text-[9px] font-medium text-white
                        bg-slate-800/90 backdrop-blur px-2 py-0.5 rounded-md
                        shadow-lg z-50"
          >
            Click to explore →
          </motion.div>
        )}
      </motion.div>

      <Handle
        type="source"
        position={Position.Bottom}
        className="!w-2 !h-2 !bg-slate-400 !border-none !-bottom-1"
      />
    </>
  );
}

export default memo(NodeCard);
