import React from 'react';
import { motion } from 'framer-motion';
import { Database, Wrench, BarChart3, Layers, Zap } from 'lucide-react';

const FlowStep = ({ icon: Icon, label, darkMode, delay = 0, accent }) => (
  <motion.div
    initial={{ opacity: 0, y: 30 }}
    animate={{ opacity: 1, y: 0 }}
    transition={{ duration: 0.6, delay, ease: 'easeOut' }}
    className={`
      rounded-2xl p-4 flex items-center gap-3
      backdrop-blur-lg shadow-lg
      ${darkMode
        ? 'bg-slate-800/80 border border-slate-700/60 text-white'
        : 'bg-white/80 border border-slate-200/60 text-slate-800'}
      ${accent || ''}
    `}
  >
    <div className={`
      p-2 rounded-xl
      ${darkMode ? 'bg-blue-500/20 text-blue-400' : 'bg-blue-500/10 text-blue-600'}
    `}>
      <Icon size={22} />
    </div>
    <span className="font-semibold text-sm">{label}</span>
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
        <linearGradient id="arrowGradDataset" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#3b82f6" />
          <stop offset="50%" stopColor="#06b6d4" />
          <stop offset="100%" stopColor="#a855f7" />
        </linearGradient>
      </defs>
      <line
        x1="10" y1="0" x2="10" y2={height - 8}
        stroke="url(#arrowGradDataset)"
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

const ConvergingArrows = ({ delay = 0, darkMode }) => (
  <motion.div
    initial={{ opacity: 0 }}
    animate={{ opacity: 1 }}
    transition={{ duration: 0.5, delay }}
    className="flex justify-center py-2"
  >
    <svg width="320" height="60" viewBox="0 0 320 60">
      <defs>
        <linearGradient id="convGrad" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#3b82f6" />
          <stop offset="50%" stopColor="#06b6d4" />
          <stop offset="100%" stopColor="#a855f7" />
        </linearGradient>
      </defs>
      {[40, 120, 200, 280].map((x, i) => (
        <g key={i}>
          <line x1={x} y1="0" x2="160" y2="52" stroke="url(#convGrad)" strokeWidth="2" strokeDasharray="6 3">
            <animate attributeName="stroke-dashoffset" from="18" to="0" dur="1.2s" repeatCount="indefinite" />
          </line>
        </g>
      ))}
      <polygon points="155,52 160,60 165,52" fill="#a855f7" />
    </svg>
  </motion.div>
);

export default function DatasetDiagram({ darkMode }) {
  const datasets = [
    { label: 'Car Hacking Dataset', icon: Database },
    { label: 'VeReMi Dataset', icon: Database },
    { label: 'CICIDS2017 Dataset', icon: Database },
    { label: 'CANVTC Dataset', icon: Database },
  ];

  const preprocessing = [
    { label: 'Data Cleaning', icon: Wrench },
    { label: 'Normalization', icon: BarChart3 },
    { label: 'Sliding Window', icon: Layers },
  ];

  return (
    <div className="overflow-y-auto max-h-[70vh] py-8 px-6">
      <div className="flex flex-col items-center gap-2 max-w-2xl mx-auto">
        {/* Datasets row */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.5 }}
          className="grid grid-cols-2 md:grid-cols-4 gap-3 w-full"
        >
          {datasets.map((ds, i) => (
            <FlowStep
              key={i}
              icon={ds.icon}
              label={ds.label}
              darkMode={darkMode}
              delay={0.1 * i}
            />
          ))}
        </motion.div>

        {/* Converging arrows */}
        <ConvergingArrows delay={0.5} darkMode={darkMode} />

        {/* Preprocessing steps */}
        {preprocessing.map((step, i) => (
          <React.Fragment key={i}>
            <FlowStep
              icon={step.icon}
              label={step.label}
              darkMode={darkMode}
              delay={0.7 + i * 0.15}
            />
            <AnimatedArrow delay={0.8 + i * 0.15} height={36} />
          </React.Fragment>
        ))}

        {/* Output */}
        <motion.div
          initial={{ opacity: 0, scale: 0.8 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.6, delay: 1.3 }}
          className={`
            rounded-2xl p-5 flex items-center gap-3
            backdrop-blur-lg shadow-xl border-2
            ${darkMode
              ? 'bg-gradient-to-r from-blue-900/60 to-purple-900/60 border-blue-500/40 text-white'
              : 'bg-gradient-to-r from-blue-50 to-purple-50 border-blue-400/40 text-slate-800'}
          `}
        >
          <div className="p-2.5 rounded-xl bg-gradient-to-br from-blue-500 to-purple-500 text-white">
            <Zap size={24} />
          </div>
          <div>
            <span className="font-bold text-base">46 Engineered Features</span>
            <p className={`text-xs mt-0.5 ${darkMode ? 'text-slate-400' : 'text-slate-500'}`}>
              Ready for model input
            </p>
          </div>
        </motion.div>
      </div>
    </div>
  );
}
