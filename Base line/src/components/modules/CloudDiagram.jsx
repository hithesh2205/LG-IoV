import React from 'react';
import { motion } from 'framer-motion';
import {
  Mail, Cog, ShieldCheck, BarChart3, Globe, Radio
} from 'lucide-react';

const FlowStep = ({ icon: Icon, label, sublabel, darkMode, delay = 0, accent }) => (
  <motion.div
    initial={{ opacity: 0, y: 30 }}
    animate={{ opacity: 1, y: 0 }}
    transition={{ duration: 0.6, delay, ease: 'easeOut' }}
    className={`
      rounded-2xl p-4 flex items-center gap-3 w-full max-w-md
      backdrop-blur-lg shadow-lg
      ${accent
        ? darkMode ? `${accent} text-white` : `${accent} text-slate-800`
        : darkMode
          ? 'bg-slate-800/80 border border-slate-700/60 text-white'
          : 'bg-white/80 border border-slate-200/60 text-slate-800'}
    `}
  >
    <div className={`
      p-2 rounded-xl shrink-0
      ${darkMode ? 'bg-blue-500/20 text-blue-400' : 'bg-blue-500/10 text-blue-600'}
    `}>
      <Icon size={22} />
    </div>
    <div className="min-w-0">
      <span className="font-semibold text-sm block">{label}</span>
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
        <linearGradient id="arrowGradCloud" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#3b82f6" />
          <stop offset="50%" stopColor="#06b6d4" />
          <stop offset="100%" stopColor="#a855f7" />
        </linearGradient>
      </defs>
      <line
        x1="10" y1="0" x2="10" y2={height - 8}
        stroke="url(#arrowGradCloud)"
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

const IncomingModels = ({ darkMode, delay = 0 }) => {
  const sources = [
    { label: 'Vehicle A', x: 30 },
    { label: 'Vehicle B', x: 160 },
    { label: 'Vehicle C', x: 290 },
  ];

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.6, delay }}
      className="w-full max-w-md"
    >
      {/* Vehicle icons at top */}
      <div className="flex justify-between px-4 mb-1">
        {sources.map((s, i) => (
          <motion.div
            key={i}
            initial={{ opacity: 0, y: -20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: delay + 0.15 * i }}
            className={`
              rounded-xl p-2.5 flex flex-col items-center gap-1
              backdrop-blur-lg shadow-md
              ${darkMode
                ? 'bg-slate-800/80 border border-slate-700/60 text-white'
                : 'bg-white/80 border border-slate-200/60 text-slate-800'}
            `}
          >
            <div className={`p-1.5 rounded-lg ${darkMode ? 'bg-blue-500/20 text-blue-400' : 'bg-blue-500/10 text-blue-600'}`}>
              <Mail size={18} />
            </div>
            <span className="text-[10px] font-semibold">{s.label}</span>
          </motion.div>
        ))}
      </div>

      {/* Converging arrows */}
      <svg width="100%" height="50" viewBox="0 0 340 50" className="mx-auto">
        <defs>
          <linearGradient id="convGradCloud" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#3b82f6" />
            <stop offset="50%" stopColor="#06b6d4" />
            <stop offset="100%" stopColor="#a855f7" />
          </linearGradient>
        </defs>
        {[45, 170, 295].map((x, i) => (
          <g key={i}>
            <line x1={x} y1="0" x2="170" y2="42" stroke="url(#convGradCloud)" strokeWidth="2" strokeDasharray="6 3">
              <animate attributeName="stroke-dashoffset" from="18" to="0" dur="1.2s" repeatCount="indefinite" />
            </line>
            {/* Flowing particle */}
            <circle r="3" fill="#06b6d4">
              <animate attributeName="cx" from={x} to="170" dur="1.5s" begin={`${i * 0.3}s`} repeatCount="indefinite" />
              <animate attributeName="cy" from="0" to="42" dur="1.5s" begin={`${i * 0.3}s`} repeatCount="indefinite" />
              <animate attributeName="opacity" values="0;1;1;0" dur="1.5s" begin={`${i * 0.3}s`} repeatCount="indefinite" />
            </circle>
          </g>
        ))}
        <polygon points="165,42 170,50 175,42" fill="#a855f7" />
      </svg>
    </motion.div>
  );
};

const BroadcastArrows = ({ darkMode, delay = 0 }) => (
  <motion.div
    initial={{ opacity: 0 }}
    animate={{ opacity: 1 }}
    transition={{ duration: 0.5, delay }}
    className="w-full max-w-md"
  >
    <svg width="100%" height="50" viewBox="0 0 340 50" className="mx-auto">
      <defs>
        <linearGradient id="bcastGrad" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#a855f7" />
          <stop offset="50%" stopColor="#06b6d4" />
          <stop offset="100%" stopColor="#3b82f6" />
        </linearGradient>
      </defs>
      {[45, 120, 220, 295].map((x, i) => (
        <g key={i}>
          <line x1="170" y1="0" x2={x} y2="42" stroke="url(#bcastGrad)" strokeWidth="2" strokeDasharray="6 3">
            <animate attributeName="stroke-dashoffset" from="18" to="0" dur="1s" repeatCount="indefinite" />
          </line>
          <circle r="2.5" fill="#3b82f6">
            <animate attributeName="cx" from="170" to={x} dur="1.3s" begin={`${i * 0.2}s`} repeatCount="indefinite" />
            <animate attributeName="cy" from="0" to="42" dur="1.3s" begin={`${i * 0.2}s`} repeatCount="indefinite" />
            <animate attributeName="opacity" values="0;1;1;0" dur="1.3s" begin={`${i * 0.2}s`} repeatCount="indefinite" />
          </circle>
          <polygon
            points={`${x - 4},${38} ${x},${46} ${x + 4},${38}`}
            fill="#3b82f6"
          />
        </g>
      ))}
    </svg>
    <div className="flex justify-between px-2">
      {['V1', 'V2', 'V3', 'V4'].map((v, i) => (
        <motion.div
          key={i}
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: delay + 0.1 * i }}
          className={`
            text-[10px] font-bold px-2.5 py-1 rounded-lg
            ${darkMode ? 'bg-blue-500/20 text-blue-400' : 'bg-blue-500/10 text-blue-600'}
          `}
        >
          {v}
        </motion.div>
      ))}
    </div>
  </motion.div>
);

const steps = [
  { icon: Cog, label: 'Homomorphic Aggregation', sublabel: 'Encrypted parameter summing' },
  { icon: ShieldCheck, label: 'Multi-Krum', sublabel: 'Byzantine-Robust Selection' },
  { icon: BarChart3, label: 'TOPSIS', sublabel: 'Multi-Criteria Decision Making' },
  { icon: Globe, label: 'Global Model', sublabel: 'Aggregated & validated' },
  { icon: Radio, label: 'Broadcast to All Vehicles', sublabel: 'Encrypted distribution' },
];

export default function CloudDiagram({ darkMode }) {
  return (
    <div className="overflow-y-auto max-h-[70vh] py-8 px-6">
      <div className="flex flex-col items-center gap-1">
        {/* Incoming models */}
        <IncomingModels darkMode={darkMode} delay={0} />

        {/* Processing steps */}
        {steps.map((step, i) => (
          <React.Fragment key={i}>
            {i === 0 ? null : <AnimatedArrow delay={0.5 + i * 0.12} height={36} />}
            <FlowStep
              icon={step.icon}
              label={step.label}
              sublabel={step.sublabel}
              darkMode={darkMode}
              delay={0.5 + i * 0.15}
            />
          </React.Fragment>
        ))}

        {/* Broadcast arrows */}
        <AnimatedArrow delay={1.3} height={36} />
        <BroadcastArrows darkMode={darkMode} delay={1.4} />
      </div>
    </div>
  );
}
