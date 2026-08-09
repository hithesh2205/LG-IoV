import React from 'react';
import { motion } from 'framer-motion';
import {
  Package, Calculator, Lock, KeyRound, Send,
  Plus, Globe, Unlock
} from 'lucide-react';

const FlowStep = ({ icon: Icon, label, darkMode, delay = 0, accent }) => (
  <motion.div
    initial={{ opacity: 0, y: 30 }}
    animate={{ opacity: 1, y: 0 }}
    transition={{ duration: 0.6, delay, ease: 'easeOut' }}
    className={`
      rounded-2xl p-4 flex items-center gap-3 w-full max-w-sm relative
      backdrop-blur-lg shadow-lg
      ${accent
        ? darkMode
          ? `${accent} text-white`
          : `${accent} text-slate-800`
        : darkMode
          ? 'bg-slate-800/80 border border-slate-700/60 text-white'
          : 'bg-white/80 border border-slate-200/60 text-slate-800'}
    `}
  >
    <div className={`
      p-2 rounded-xl shrink-0
      ${darkMode ? 'bg-cyan-500/20 text-cyan-400' : 'bg-cyan-500/10 text-cyan-600'}
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
        <linearGradient id="arrowGradCKKS" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#3b82f6" />
          <stop offset="50%" stopColor="#06b6d4" />
          <stop offset="100%" stopColor="#a855f7" />
        </linearGradient>
      </defs>
      <line
        x1="10" y1="0" x2="10" y2={height - 8}
        stroke="url(#arrowGradCKKS)"
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

const FloatingParticles = ({ count = 8, darkMode }) => (
  <div className="absolute inset-0 pointer-events-none overflow-hidden rounded-2xl">
    {Array.from({ length: count }).map((_, i) => (
      <motion.div
        key={i}
        className={`absolute w-1.5 h-1.5 rounded-full ${
          i % 3 === 0 ? 'bg-cyan-400' : i % 3 === 1 ? 'bg-blue-400' : 'bg-purple-400'
        }`}
        style={{
          left: `${10 + Math.random() * 80}%`,
          top: `${10 + Math.random() * 80}%`,
        }}
        animate={{
          y: [0, -12, 0, 12, 0],
          x: [0, 8, -8, 4, 0],
          opacity: [0.3, 0.8, 0.3],
          scale: [0.8, 1.2, 0.8],
        }}
        transition={{
          duration: 2 + Math.random() * 2,
          repeat: Infinity,
          delay: Math.random() * 2,
          ease: 'easeInOut',
        }}
      />
    ))}
  </div>
);

const PhaseLabel = ({ label, darkMode, delay = 0 }) => (
  <motion.div
    initial={{ opacity: 0, x: -20 }}
    animate={{ opacity: 1, x: 0 }}
    transition={{ duration: 0.5, delay }}
    className={`
      text-xs font-bold uppercase tracking-widest mb-2 mt-4
      ${darkMode ? 'text-cyan-400' : 'text-cyan-600'}
    `}
  >
    {label}
  </motion.div>
);

const EncryptionStep = ({ icon: Icon, label, darkMode, delay = 0, hasParticles }) => (
  <motion.div
    initial={{ opacity: 0, y: 30 }}
    animate={{ opacity: 1, y: 0 }}
    transition={{ duration: 0.6, delay, ease: 'easeOut' }}
    className={`
      rounded-2xl p-4 flex items-center gap-3 w-full max-w-sm relative
      backdrop-blur-lg shadow-lg
      ${darkMode
        ? 'bg-slate-800/80 border border-slate-700/60 text-white'
        : 'bg-white/80 border border-slate-200/60 text-slate-800'}
    `}
  >
    {hasParticles && <FloatingParticles count={10} darkMode={darkMode} />}
    <div className={`
      p-2 rounded-xl shrink-0 relative z-10
      ${darkMode ? 'bg-cyan-500/20 text-cyan-400' : 'bg-cyan-500/10 text-cyan-600'}
    `}>
      <Icon size={22} />
    </div>
    <span className="font-semibold text-sm relative z-10">{label}</span>
  </motion.div>
);

const encryptionSteps = [
  { icon: Package, label: 'Model Weights' },
  { icon: Calculator, label: 'Polynomial Encoding' },
  { icon: Lock, label: 'CKKS Encryption', hasParticles: true },
  { icon: KeyRound, label: 'Ciphertext', hasParticles: true },
  { icon: Send, label: 'Encrypted Model' },
];

const aggregationSteps = [
  { icon: Send, label: 'Encrypted Models (×3)', isMulti: true },
  { icon: Plus, label: 'Homomorphic Addition', hasParticles: true },
  { icon: Globe, label: 'Encrypted Global Model', hasParticles: true },
  { icon: Unlock, label: 'Vehicle Decryption' },
];

const MultiSendIcon = ({ darkMode }) => (
  <div className="flex -space-x-2">
    {[0, 1, 2].map(i => (
      <motion.div
        key={i}
        initial={{ opacity: 0, x: -10 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ delay: 0.8 + i * 0.1 }}
        className={`
          p-1.5 rounded-lg
          ${darkMode ? 'bg-cyan-500/20 text-cyan-400' : 'bg-cyan-500/10 text-cyan-600'}
        `}
      >
        <Send size={16} />
      </motion.div>
    ))}
  </div>
);

export default function CKKSDiagram({ darkMode }) {
  return (
    <div className="overflow-y-auto max-h-[70vh] py-8 px-6">
      <div className="flex flex-col items-center gap-1">
        {/* Phase 1 */}
        <PhaseLabel label="Phase 1 — Encryption" darkMode={darkMode} delay={0} />

        {encryptionSteps.map((step, i) => (
          <React.Fragment key={`enc-${i}`}>
            <EncryptionStep
              icon={step.icon}
              label={step.label}
              darkMode={darkMode}
              delay={0.1 + i * 0.12}
              hasParticles={step.hasParticles}
            />
            {i < encryptionSteps.length - 1 && (
              <AnimatedArrow delay={0.15 + i * 0.12} height={34} />
            )}
          </React.Fragment>
        ))}

        {/* Phase divider */}
        <motion.div
          initial={{ scaleX: 0 }}
          animate={{ scaleX: 1 }}
          transition={{ duration: 0.6, delay: 0.8 }}
          className={`
            w-full max-w-sm h-px my-4
            ${darkMode ? 'bg-gradient-to-r from-transparent via-cyan-500/40 to-transparent'
                       : 'bg-gradient-to-r from-transparent via-cyan-400/40 to-transparent'}
          `}
        />

        {/* Phase 2 */}
        <PhaseLabel label="Phase 2 — Aggregation" darkMode={darkMode} delay={0.85} />

        {aggregationSteps.map((step, i) => (
          <React.Fragment key={`agg-${i}`}>
            {step.isMulti ? (
              <motion.div
                initial={{ opacity: 0, y: 30 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.6, delay: 0.9 + i * 0.12, ease: 'easeOut' }}
                className={`
                  rounded-2xl p-4 flex items-center gap-3 w-full max-w-sm
                  backdrop-blur-lg shadow-lg
                  ${darkMode
                    ? 'bg-slate-800/80 border border-slate-700/60 text-white'
                    : 'bg-white/80 border border-slate-200/60 text-slate-800'}
                `}
              >
                <MultiSendIcon darkMode={darkMode} />
                <span className="font-semibold text-sm">{step.label}</span>
              </motion.div>
            ) : (
              <EncryptionStep
                icon={step.icon}
                label={step.label}
                darkMode={darkMode}
                delay={0.9 + i * 0.12}
                hasParticles={step.hasParticles}
              />
            )}
            {i < aggregationSteps.length - 1 && (
              <AnimatedArrow delay={0.95 + i * 0.12} height={34} />
            )}
          </React.Fragment>
        ))}
      </div>
    </div>
  );
}
