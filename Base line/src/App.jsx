import React, { useState, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Search, Moon, Sun, X, Shield, Cpu } from 'lucide-react';
import ArchitectureCanvas from './components/ArchitectureCanvas';
import ModulePopup from './components/ModulePopup';

export default function App() {
  const [darkMode, setDarkMode] = useState(false);
  const [activeModule, setActiveModule] = useState(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [searchOpen, setSearchOpen] = useState(false);

  const handleNodeClick = useCallback((moduleId) => {
    setActiveModule(moduleId);
  }, []);

  const handleCloseModule = useCallback(() => {
    setActiveModule(null);
  }, []);

  return (
    <div className={`w-full h-screen flex flex-col ${darkMode ? 'dark bg-slate-950' : 'bg-slate-50'}`}>
      {/* ========== HEADER ========== */}
      <header
        className={`
          relative z-30 flex items-center justify-between px-5 py-3
          border-b
          ${darkMode
            ? 'bg-slate-900/90 border-slate-800/80'
            : 'bg-white/80 border-slate-200/60'
          }
        `}
        style={{ backdropFilter: 'blur(16px)' }}
      >
        {/* Left: Title */}
        <div className="flex items-center gap-3 min-w-0">
          <div className="flex items-center justify-center w-9 h-9 rounded-xl bg-gradient-to-br from-blue-500 via-cyan-400 to-purple-500 shadow-lg">
            <Shield size={18} className="text-white" />
          </div>
          <div className="min-w-0">
            <h1 className={`text-sm font-bold leading-tight truncate ${darkMode ? 'text-white' : 'text-slate-800'}`}>
              <span className="gradient-text">FedIDS-IoV</span>
            </h1>
            <p className={`text-[10px] font-mono leading-tight truncate max-w-[400px] ${darkMode ? 'text-slate-400' : 'text-slate-500'}`}>
              Privacy-Preserving Federated Intrusion Detection • MamKANFormer • CKKS FHE
            </p>
          </div>
        </div>

        {/* Right: Controls */}
        <div className="flex items-center gap-2">
          {/* Search */}
          <AnimatePresence>
            {searchOpen && (
              <motion.div
                initial={{ width: 0, opacity: 0 }}
                animate={{ width: 220, opacity: 1 }}
                exit={{ width: 0, opacity: 0 }}
                transition={{ type: 'spring', stiffness: 400, damping: 30 }}
                className="overflow-hidden"
              >
                <input
                  type="text"
                  value={searchTerm}
                  onChange={(e) => setSearchTerm(e.target.value)}
                  placeholder="Search blocks..."
                  autoFocus
                  className={`
                    w-full text-xs px-3 py-2 rounded-xl outline-none
                    ${darkMode
                      ? 'bg-slate-800 text-slate-200 border-slate-700 placeholder-slate-500'
                      : 'bg-slate-100 text-slate-800 border-slate-200 placeholder-slate-400'
                    }
                    border focus:ring-2 focus:ring-blue-400/40
                  `}
                />
              </motion.div>
            )}
          </AnimatePresence>

          <motion.button
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            onClick={() => {
              setSearchOpen(!searchOpen);
              if (searchOpen) setSearchTerm('');
            }}
            className={`
              p-2 rounded-xl transition-colors
              ${darkMode
                ? 'hover:bg-slate-800 text-slate-400 hover:text-white'
                : 'hover:bg-slate-100 text-slate-500 hover:text-slate-800'
              }
            `}
            title="Search blocks"
          >
            {searchOpen ? <X size={18} /> : <Search size={18} />}
          </motion.button>

          {/* Dark mode toggle */}
          <motion.button
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            onClick={() => setDarkMode(!darkMode)}
            className={`
              p-2 rounded-xl transition-colors
              ${darkMode
                ? 'hover:bg-slate-800 text-amber-400 hover:text-amber-300'
                : 'hover:bg-slate-100 text-slate-500 hover:text-slate-800'
              }
            `}
            title="Toggle dark mode"
          >
            {darkMode ? <Sun size={18} /> : <Moon size={18} />}
          </motion.button>

          {/* IEEE badge */}
          <div className={`
            hidden sm:flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-[10px] font-mono font-semibold
            ${darkMode
              ? 'bg-blue-500/10 text-blue-400 border border-blue-500/20'
              : 'bg-blue-50 text-blue-600 border border-blue-200/60'
            }
          `}>
            <Cpu size={12} />
            System Architecture
          </div>
        </div>
      </header>

      {/* ========== CANVAS ========== */}
      <main className="flex-1 relative">
        <ArchitectureCanvas
          onNodeClick={handleNodeClick}
          darkMode={darkMode}
          searchTerm={searchTerm}
        />

        {/* Bottom info bar */}
        <div className={`
          absolute bottom-4 left-1/2 -translate-x-1/2 z-20
          flex items-center gap-2 px-4 py-2 rounded-2xl
          text-[10px] font-mono
          ${darkMode
            ? 'bg-slate-900/80 text-slate-400 border border-slate-700/50'
            : 'bg-white/80 text-slate-500 border border-slate-200/60'
          }
        `}
        style={{ backdropFilter: 'blur(12px)' }}
        >
          <span className="w-2 h-2 rounded-full bg-gradient-to-r from-blue-500 to-cyan-400 animate-pulse" />
          <span>Click any module to explore • Scroll to zoom • Drag to pan</span>
        </div>
      </main>

      {/* ========== MODULE POPUP ========== */}
      <AnimatePresence>
        {activeModule && (
          <ModulePopup
            moduleId={activeModule}
            onClose={handleCloseModule}
            darkMode={darkMode}
          />
        )}
      </AnimatePresence>
    </div>
  );
}
