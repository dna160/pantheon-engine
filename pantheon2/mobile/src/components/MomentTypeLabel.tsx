/**
 * MomentTypeLabel.tsx — Current moment type display.
 * Shows the classified moment type with color coding and human label.
 */

import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import type { MomentType } from '../types';

interface Props {
  momentType: MomentType;
  confidence: number;   // 0.0–1.0
}

const MOMENT_CONFIG: Record<MomentType, { label: string; color: string; bg: string; icon: string }> = {
  neutral_exploratory: { label: 'EXPLORING',   color: '#9ca3af', bg: '#111827', icon: '🔍' },
  irate_resistant:     { label: 'RESISTANT',   color: '#ef4444', bg: '#450a0a', icon: '⚡' },
  topic_avoidance:     { label: 'AVOIDING',    color: '#f59e0b', bg: '#713f12', icon: '↩' },
  identity_threat:     { label: 'THREATENED',  color: '#a855f7', bg: '#2e1065', icon: '🛡' },
  high_openness:       { label: 'OPEN',        color: '#22c55e', bg: '#14532d', icon: '✨' },
  closing_signal:      { label: 'CLOSING',     color: '#10b981', bg: '#022c22', icon: '🎯' },
};

const MomentTypeLabel: React.FC<Props> = ({ momentType, confidence }) => {
  const config = MOMENT_CONFIG[momentType] ?? MOMENT_CONFIG.neutral_exploratory;
  const confPct = Math.round(confidence * 100);

  return (
    <View style={[styles.container, { backgroundColor: config.bg }]}>
      <Text style={styles.icon}>{config.icon}</Text>
      <Text style={[styles.label, { color: config.color }]}>{config.label}</Text>
      <Text style={styles.confidence}>{confPct}%</Text>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 10,
    paddingVertical: 6,
    borderRadius: 8,
    gap: 6,
  },
  icon: {
    fontSize: 15,
  },
  label: {
    fontSize: 13,
    fontWeight: '800',
    letterSpacing: 1.2,
    flex: 1,
  },
  confidence: {
    fontSize: 11,
    color: '#6b7280',
    fontWeight: '600',
  },
});

export default MomentTypeLabel;
