"use client";

import { motion, useReducedMotion } from "framer-motion";

/**
 * Fade-and-lift a block the first time it scrolls into view.
 *
 * Deliberately small: 12px of travel and 500ms. Anything larger reads as a
 * template. Honours the operating system's reduced-motion setting, in which
 * case the content simply appears.
 */
export function Reveal({
  children,
  delay = 0,
  className,
}: {
  children: React.ReactNode;
  delay?: number;
  className?: string;
}) {
  const reduced = useReducedMotion();

  return (
    <motion.div
      className={className}
      initial={reduced ? false : { opacity: 0, y: 12 }}
      whileInView={reduced ? undefined : { opacity: 1, y: 0 }}
      viewport={{ once: true, margin: "-64px" }}
      transition={{ duration: 0.5, delay, ease: [0.22, 1, 0.36, 1] }}
    >
      {children}
    </motion.div>
  );
}
