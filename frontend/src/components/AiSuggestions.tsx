'use client';

import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { RefreshCw } from 'lucide-react';

interface AiSuggestionsProps {
  suggestions: string[];
  onSelect: (query: string) => void;
  onRefresh?: () => void;
  isLoading?: boolean;
}

export const AiSuggestions: React.FC<AiSuggestionsProps> = ({
  suggestions,
  onSelect,
  onRefresh,
  isLoading = false,
}) => {
  if (!suggestions || suggestions.length === 0) return null;

  return (
    <div className="pt-1 flex flex-wrap items-center gap-1.5 text-xs">
      <span className="text-zinc-500 text-xs font-medium mr-0.5 select-none">
        Try:
      </span>

      <AnimatePresence mode="popLayout">
        {suggestions.map((topic, idx) => (
          <motion.button
            key={topic}
            type="button"
            onClick={() => onSelect(topic)}
            initial={{ opacity: 0, y: 3 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.96 }}
            transition={{
              duration: 0.18,
              delay: idx * 0.04,
              ease: 'easeOut',
            }}
            whileTap={{ scale: 0.98 }}
            className="inline-flex items-center text-zinc-300 hover:text-zinc-100 bg-zinc-900/80 hover:bg-zinc-800/90 border border-white/[0.08] hover:border-white/20 px-2.5 py-1 rounded-lg transition-[background-color,border-color,color] cursor-pointer text-xs font-normal"
          >
            <span>{topic}</span>
          </motion.button>
        ))}
      </AnimatePresence>

      {onRefresh && (
        <motion.button
          type="button"
          onClick={onRefresh}
          disabled={isLoading}
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          whileTap={{ scale: 0.9 }}
          className="p-1 rounded-md text-zinc-500 hover:text-zinc-300 hover:bg-zinc-900/60 transition-colors cursor-pointer disabled:opacity-40 ml-0.5"
          title="Shuffle suggestions"
          aria-label="Shuffle suggestions"
        >
          <RefreshCw
            className={`w-3 h-3 ${isLoading ? 'animate-spin text-zinc-400' : ''}`}
          />
        </motion.button>
      )}
    </div>
  );
};
