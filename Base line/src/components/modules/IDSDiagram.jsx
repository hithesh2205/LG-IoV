import React from 'react';
import { motion } from 'framer-motion';
import {
  Radio, Search, Brain, BarChart3,
  CheckCircle, AlertTriangle, Bell, FileText
} from 'lucide-react';

const FlowStep = ({ icon: Icon, label, sublabel, darkMode, delay = 0, accent, small }) => (
  <motion.div
    initial={{ opacity: 0, y: 30 }}
    animate={{ opacity: 1, y: 0 }}
    transition={{ duration: 0.6, delay, ease: 'easeOut' }}
    className={`
      rounded-2xl ${small ? 'p-3' : 'p-4'} flex items-center gap-3
      backdrop-blur-lg shadow-lg
      ${accent
        ? `${accent}`
        : darkMode
          ? 'bg-slate-800/80 border border-slate-700/60 text-white'
          : 'bg-white/80 border border-slate-200/60 text-slate-800'}
      ${small ? 'w-full' : 'w-full max-w-md'}
    `}
  >
    <div className={`
      ${small ? 'p-1.5' : 'p-2'} rounded-xl shrink-0
      ${accent
        ? 'bg-white/20'
        : darkMode ? 'bg-blue-500/20 text-blue-400' : 'bg-blue-500/10 text-blue-600'}
    `}>
      <Icon size={small ? 18 : 22} />
    </div>
    <div className="min-w-0">
      <span className={`font-semibold ${small ? 'text-xs' : 'text-sm'} block`}>{label}</span>
      {sublabel && (
        <span className={`text-xs ${darkMode ? 'text-slate-400' : 'text-slate-500'}`}>
          {sublabel}
        </span>
      )}
    </div>
  </motion.div>
);

const AnimatedArrow = ({ delay = 0, height = 40 }) => (
  <motion.div
    initial={{ opacity: 0 }}
    animate={{ opacity: 1 }}
    transition={{ duration: 0.4, delay }}
    className="flex justify-center"
  >
    <svg width="20" height={height} viewBox={`0 0 20 ${height}`}>
      <defs>
        <linearGradient id="arrowGradIDS" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#3b82f6" />
          <stop offset="50%" stopColor="#06b6d4" />
          <stop offset="100%" stopColor="#a855f7" />
        </linearGradient>
      </defs>
      <line
        x1="10" y1="0" x2="10" y2={height - 8}
        stroke="url(#arrowGradIDS)"
        strokeWidth="2"
        strokeDasharray="6 3"
      >
        <animate attributeName="stroke-dashoffset" from="18" to="0" dur="1s" repeatCount="indefinite" />
      </line>
      <polygon
        points={`5,${height - 8} 10,${height} 15,${height - 8}`}
        fill="#a855f7"
      />
    </svg>
  </motion.div>
);

const DecisionDiamond = ({ darkMode, delay = 0 }) => (
  <motion.div
    initial={{ opacity: 0, scale: 0.7, rotate: 45 }}
    animate={{ opacity: 1, scale: 1, rotate: 45 }}
    transition={{ duration: 0.6, delay, type: 'spring', stiffness: 200 }}
    className="flex justify-center my-1"
  >
    <div
      className={`
        w-14 h-14 flex items-center justify-center
        border-2 shadow-lg
        ${darkMode
          ? 'bg-slate-800/90 border-cyan-500/50'
          : 'bg-white/90 border-cyan-400/50'}
      `}
    >
      <span
        className={`text-xs font-bold -rotate-45 ${darkMode ? 'text-cyan-400' : 'text-cyan-600'}`}
      >
        ?
      </span>
    </div>
  </motion.div>
);

const BranchSplit = ({ darkMode, delay = 0 }) => (
  <motion.div
    initial={{ opacity: 0 }}
    animate={{ opacity: 1 }}
    transition={{ duration: 0.5, delay }}
    className="w-full max-w-lg"
  >
    <svg width="100%" height="50" viewBox="0 0 400 50" className="mx-auto">
      <defs>
        <linearGradient id="greenGrad" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#06b6d4" />
          <stop offset="100%" stopColor="#22c55e" />
        </linearGradient>
        <linearGradient id="redGrad" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#06b6d4" />
          <stop offset="100%" stopColor="#ef4444" />
        </linearGradient>
      </defs>
      {/* Left branch (Normal) */}
      <line x1="200" y1="0" x2="100" y2="42" stroke="url(#greenGrad)" strokeWidth="2" strokeDasharray="6 3">
        <animate attributeName="stroke-dashoffset" from="18" to="0" dur="1.2s" repeatCount="indefinite" />
      </line>
      <polygon points="96,38 100,46 104,38" fill="#22c55e" />
      {/* Right branch (Attack) */}
      <line x1="200" y1="0" x2="300" y2="42" stroke="url(#redGrad)" strokeWidth="2" strokeDasharray="6 3">
        <animate attributeName="stroke-dashoffset" from="18" to="0" dur="1.2s" repeatCount="indefinite" />
      </line>
      <polygon points="296,38 300,46 304,38" fill="#ef4444" />
    </svg>
  </motion.div>
);

const attackActions = [
  { icon: Bell, label: 'Alert Driver' },
  { icon: Radio, label: 'Notify RSU' },
  { icon: FileText, label: 'Log Event' },
];

const initialSteps = [
  { icon: Radio, label: 'Incoming CAN Frame', sublabel: 'Raw bus data' },
  { icon: Search, label: 'Feature Extraction', sublabel: '46-dimensional vector' },
  { icon: Brain, label: 'MamKANFormer Inference', sublabel: 'Neural network prediction' },
  { icon: BarChart3, label: 'Probability Score', sublabel: 'Classification confidence' },
];

export default function IDSDiagram({ darkMode }) {
  return (
    <div className="overflow-y-auto max-h-[70vh] py-8 px-6">
      <div className="flex flex-col items-center gap-1">
        {/* Initial linear flow */}
        {initialSteps.map((step, i) => (
          <React.Fragment key={i}>
            <FlowStep
              icon={step.icon}
              label={step.label}
              sublabel={step.sublabel}
              darkMode={darkMode}
              delay={0.12 * i}
            />
            {i < initialSteps.length - 1 && (
              <AnimatedArrow delay={0.12 * i + 0.08} height={36} />
            )}
          </React.Fragment>
        ))}

        {/* Decision diamond */}
        <AnimatedArrow delay={0.55} height={30} />
        <DecisionDiamond darkMode={darkMode} delay={0.6} />

        {/* Branch */}
        <BranchSplit darkMode={darkMode} delay={0.7} />

        {/* Two branch cards */}
        <div className="grid grid-cols-2 gap-4 w-full max-w-lg">
          {/* Normal */}
          <FlowStep
            icon={CheckCircle}
            label="Normal Traffic"
            darkMode={darkMode}
            delay={0.8}
            accent={
              darkMode
                ? 'bg-green-900/50 border border-green-500/40 text-green-300'
                : 'bg-green-50 border border-green-300/60 text-green-800'
            }
          />
          {/* Attack */}
          <FlowStep
            icon={AlertTriangle}
            label="Attack Detected"
            darkMode={darkMode}
            delay={0.85}
            accent={
              darkMode
                ? 'bg-red-900/50 border border-red-500/40 text-red-300'
                : 'bg-red-50 border border-red-300/60 text-red-800'
            }
          />
        </div>

        {/* Attack branch actions */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.5, delay: 0.95 }}
          className="w-full max-w-lg flex justify-end"
        >
          <div className="w-1/2 pl-2">
            <svg width="100%" height="30" viewBox="0 0 200 30" className="mb-1">
              <defs>
                <linearGradient id="redArrowDown" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#ef4444" />
                  <stop offset="100%" stopColor="#f97316" />
                </linearGradient>
              </defs>
              {/* Three diverging lines from center */}
              {[40, 100, 160].map((x, i) => (
                <g key={i}>
                  <line x1="100" y1="0" x2={x} y2="22" stroke="url(#redArrowDown)" strokeWidth="1.5" strokeDasharray="4 3">
                    <animate attributeName="stroke-dashoffset" from="14" to="0" dur="1s" repeatCount="indefinite" />
                  </line>
                  <polygon points={`${x - 3},${19} ${x},${25} ${x + 3},${19}`} fill="#ef4444" />
                </g>
              ))}
            </svg>

            <div className="flex flex-col gap-2">
              {attackActions.map((action, i) => (
                <FlowStep
                  key={i}
                  icon={action.icon}
                  label={action.label}
                  darkMode={darkMode}
                  delay={1.0 + i * 0.1}
                  small
                  accent={
                    darkMode
                      ? 'bg-orange-900/40 border border-orange-500/30 text-orange-300'
                      : 'bg-orange-50 border border-orange-300/50 text-orange-800'
                  }
                />
              ))}
            </div>
          </div>
        </motion.div>
      </div>
    </div>
  );
}
