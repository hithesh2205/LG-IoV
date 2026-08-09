import React from 'react';
import { motion } from 'framer-motion';
import { Zap, Brain, Sparkles, Target, AlertTriangle } from 'lucide-react';

const FlowStep = ({ icon: Icon, label, sublabel, darkMode, delay = 0, highlight }) => (
  <motion.div
    initial={{ opacity: 0, y: 30 }}
    animate={{ opacity: 1, y: 0 }}
    transition={{ duration: 0.6, delay, ease: 'easeOut' }}
    className={`
      rounded-2xl p-4 flex items-center gap-3 w-full max-w-md
      backdrop-blur-lg shadow-lg
      ${highlight
        ? darkMode
          ? 'bg-gradient-to-r from-red-900/50 to-orange-900/50 border border-red-500/40 text-white'
          : 'bg-gradient-to-r from-red-50 to-orange-50 border border-red-300/60 text-slate-800'
        : darkMode
          ? 'bg-slate-800/80 border border-slate-700/60 text-white'
          : 'bg-white/80 border border-slate-200/60 text-slate-800'}
    `}
  >
    <div className={`
      p-2 rounded-xl shrink-0
      ${highlight
        ? 'bg-red-500/20 text-red-400'
        : darkMode ? 'bg-purple-500/20 text-purple-400' : 'bg-purple-500/10 text-purple-600'}
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

const AnimatedArrowWithParticles = ({ delay = 0, height = 50 }) => (
  <motion.div
    initial={{ opacity: 0 }}
    animate={{ opacity: 1 }}
    transition={{ duration: 0.4, delay }}
    className="flex justify-center"
  >
    <svg width="40" height={height} viewBox={`0 0 40 ${height}`} className="overflow-visible">
      <defs>
        <linearGradient id="arrowGradMam" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#3b82f6" />
          <stop offset="50%" stopColor="#06b6d4" />
          <stop offset="100%" stopColor="#a855f7" />
        </linearGradient>
        <radialGradient id="particleGlow">
          <stop offset="0%" stopColor="#06b6d4" stopOpacity="1" />
          <stop offset="100%" stopColor="#06b6d4" stopOpacity="0" />
        </radialGradient>
      </defs>
      {/* Main line */}
      <line
        x1="20" y1="0" x2="20" y2={height - 8}
        stroke="url(#arrowGradMam)"
        strokeWidth="2"
        strokeDasharray="6 3"
      >
        <animate attributeName="stroke-dashoffset" from="18" to="0" dur="1s" repeatCount="indefinite" />
      </line>
      {/* Arrow head */}
      <polygon
        points={`15,${height - 8} 20,${height} 25,${height - 8}`}
        fill="#a855f7"
      />
      {/* Flowing particle 1 */}
      <circle r="3" fill="#06b6d4">
        <animate attributeName="cy" from="0" to={height} dur="1.5s" repeatCount="indefinite" />
        <animate attributeName="opacity" values="0;1;1;0" dur="1.5s" repeatCount="indefinite" />
      </circle>
      <circle r="3" cx="20" fill="#06b6d4">
        <animate attributeName="cy" from="0" to={height} dur="1.5s" begin="0.5s" repeatCount="indefinite" />
        <animate attributeName="opacity" values="0;1;1;0" dur="1.5s" begin="0.5s" repeatCount="indefinite" />
      </circle>
      {/* Flowing particle 2 (offset) */}
      <circle r="2.5" fill="#a855f7">
        <animate attributeName="cy" from="0" to={height} dur="1.8s" begin="0.3s" repeatCount="indefinite" />
        <animate attributeName="cx" values="18;22;18" dur="1.8s" begin="0.3s" repeatCount="indefinite" />
        <animate attributeName="opacity" values="0;0.8;0.8;0" dur="1.8s" begin="0.3s" repeatCount="indefinite" />
      </circle>
      {/* Flowing particle 3 */}
      <circle r="2" fill="#3b82f6">
        <animate attributeName="cy" from="0" to={height} dur="2s" begin="0.8s" repeatCount="indefinite" />
        <animate attributeName="cx" values="22;18;22" dur="2s" begin="0.8s" repeatCount="indefinite" />
        <animate attributeName="opacity" values="0;0.7;0.7;0" dur="2s" begin="0.8s" repeatCount="indefinite" />
      </circle>
    </svg>
  </motion.div>
);

const steps = [
  { icon: Zap, label: '46 Input Features', sublabel: 'Engineered feature vector' },
  { icon: Brain, label: 'Mamba Encoder', sublabel: 'SSM-based Sequence Modeling' },
  { icon: Sparkles, label: 'KAN Layer 1', sublabel: 'B-Spline Activations' },
  { icon: Sparkles, label: 'KAN Layer 2', sublabel: 'B-Spline Activations' },
  { icon: Sparkles, label: 'KAN Layer 3', sublabel: 'B-Spline Activations' },
  { icon: Target, label: 'Multi-Head Attention Classifier', sublabel: 'Attention-weighted classification' },
  { icon: AlertTriangle, label: 'Attack Prediction', sublabel: 'Final output', highlight: true },
];

export default function MamKANFormerDiagram({ darkMode }) {
  return (
    <div className="overflow-y-auto max-h-[70vh] py-8 px-6">
      <div className="flex flex-col items-center gap-1">
        {steps.map((step, i) => (
          <React.Fragment key={i}>
            <FlowStep
              icon={step.icon}
              label={step.label}
              sublabel={step.sublabel}
              darkMode={darkMode}
              delay={0.15 * i}
              highlight={step.highlight}
            />
            {i < steps.length - 1 && (
              <AnimatedArrowWithParticles delay={0.15 * i + 0.1} height={46} />
            )}
          </React.Fragment>
        ))}
      </div>
    </div>
  );
}
