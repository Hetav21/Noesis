'use client';

import React, { useEffect } from 'react';
import { motion, stagger, useAnimate } from 'framer-motion';
import { cn } from '@/lib/utils';

export interface TextGenerateEffectProps {
  words: string;
  className?: string;
  filter?: boolean;
  duration?: number;
  delayOffset?: number;
}

/**
 * Aceternity UI - Text Generate Effect
 * Staggers word-by-word reveal with blur-to-sharp opacity transition
 * to emulate real-time AI token generation.
 */
export const TextGenerateEffect: React.FC<TextGenerateEffectProps> = ({
  words,
  className,
  filter = true,
  duration = 0.35,
  delayOffset = 0,
}) => {
  const [scope, animate] = useAnimate();
  const wordsArray = words.split(' ');

  useEffect(() => {
    if (scope.current) {
      animate(
        'span',
        {
          opacity: 1,
          filter: filter ? 'blur(0px)' : 'none',
        },
        {
          duration,
          delay: stagger(0.04, { startDelay: delayOffset }),
        }
      );
    }
  }, [scope, animate, filter, duration, delayOffset, words]);

  return (
    <span ref={scope} className={cn('inline', className)}>
      {wordsArray.map((word, idx) => (
        <motion.span
          key={`${word}-${idx}`}
          className="inline-block opacity-0"
          style={{
            filter: filter ? 'blur(8px)' : 'none',
          }}
        >
          {word}&nbsp;
        </motion.span>
      ))}
    </span>
  );
};
