import React, { lazy, Suspense } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, Loader2 } from 'lucide-react';

const DatasetDiagram = lazy(() => import('./modules/DatasetDiagram'));
const MamKANFormerDiagram = lazy(() => import('./modules/MamKANFormerDiagram'));
const CKKSDiagram = lazy(() => import('./modules/CKKSDiagram'));
const CloudDiagram = lazy(() => import('./modules/CloudDiagram'));
const IDSDiagram = lazy(() => import('./modules/IDSDiagram'));

const moduleMap = {
  datasets: { Component: DatasetDiagram, title: 'Datasets & Preprocessing Pipeline' },
  preprocessing: { Component: DatasetDiagram, title: 'Datasets & Preprocessing Pipeline' },
  features: { Component: DatasetDiagram, title: 'Feature Engineering Pipeline' },
  distribution: { Component: DatasetDiagram, title: 'Non-IID Distribution' },
  mamkanformer: { Component: MamKANFormerDiagram, title: 'MamKANFormer Architecture' },
  ckks: { Component: CKKSDiagram, title: 'CKKS Fully Homomorphic Encryption' },
  cloud: { Component: CloudDiagram, title: 'Federated Cloud Server' },
  ids: { Component: IDSDiagram, title: 'Intrusion Detection System' },
};

const backdrop = {
  hidden: { opacity: 0 },
  visible: { opacity: 1 },
  exit: { opacity: 0 },
};

const panel = {
  hidden: { opacity: 0, scale: 0.85, y: 40 },
  visible: {
    opacity: 1,
    scale: 1,
    y: 0,
    transition: { type: 'spring', stiffness: 300, damping: 30, mass: 0.8 },
  },
  exit: {
    opacity: 0,
    scale: 0.9,
    y: 20,
    transition: { duration: 0.2 },
  },
};

export default function ModulePopup({ moduleId, onClose, darkMode }) {
  const entry = moduleMap[moduleId];
  if (!entry) return null;

  const { Component, title } = entry;

  return (
    <AnimatePresence>
      <motion.div
        key="backdrop"
        variants={backdrop}
        initial="hidden"
        animate="visible"
        exit="exit"
        onClick={onClose}
        className="fixed inset-0 z-50 flex items-center justify-center"
        style={{
          background: darkMode
            ? 'rgba(2, 6, 23, 0.85)'
            : 'rgba(148, 163, 184, 0.25)',
          backdropFilter: 'blur(12px)',
        }}
      >
        <motion.div
          key="panel"
          variants={panel}
          initial="hidden"
          animate="visible"
          exit="exit"
          onClick={(e) => e.stopPropagation()}
          className={`
            relative w-[90vw] max-w-[720px] max-h-[85vh]
            rounded-3xl overflow-hidden
            ${darkMode
              ? 'bg-slate-900/95 border border-slate-700/50'
              : 'bg-white/95 border border-slate-200/80'
            }
            shadow-2xl
          `}
          style={{
            backdropFilter: 'blur(24px)',
            boxShadow: darkMode
              ? '0 25px 80px rgba(0, 0, 0, 0.5), 0 0 40px rgba(59, 130, 246, 0.1)'
              : '0 25px 80px rgba(0, 0, 0, 0.12), 0 0 40px rgba(59, 130, 246, 0.05)',
          }}
        >
          {/* Header gradient bar */}
          <div className="h-1 w-full bg-gradient-to-r from-blue-500 via-cyan-400 to-purple-500" />

          {/* Header */}
          <div className={`
            flex items-center justify-between px-6 py-4
            border-b
            ${darkMode ? 'border-slate-700/50' : 'border-slate-200/60'}
          `}>
            <h2 className={`text-lg font-bold font-mono tracking-tight ${darkMode ? 'text-white' : 'text-slate-800'}`}>
              {title}
            </h2>
            <motion.button
              whileHover={{ scale: 1.1, rotate: 90 }}
              whileTap={{ scale: 0.9 }}
              onClick={onClose}
              className={`
                p-2 rounded-xl transition-colors
                ${darkMode
                  ? 'hover:bg-slate-700/60 text-slate-400 hover:text-white'
                  : 'hover:bg-slate-100 text-slate-500 hover:text-slate-800'
                }
              `}
            >
              <X size={20} />
            </motion.button>
          </div>

          {/* Content */}
          <div className="overflow-y-auto max-h-[calc(85vh-80px)] module-scroll">
            <Suspense
              fallback={
                <div className="flex items-center justify-center py-20">
                  <Loader2 className="w-8 h-8 animate-spin text-blue-500" />
                </div>
              }
            >
              <Component darkMode={darkMode} />
            </Suspense>
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
}
