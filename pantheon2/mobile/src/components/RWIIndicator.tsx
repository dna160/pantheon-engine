/**
 * RWIIndicator.tsx — Receptivity Window Index score + status badge.
 *
 * Shows live RWI score (0–100) and window_status:
 *   closed   → red, lock icon
 *   narrowing → amber, hourglass
 *   open     → lime, open window
 *   peak     → green + pulse animation, fire
 */

import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import type { RWIWindowStatus } from '../types';

interface Props {
  score: number;
  status: RWIWindowStatus;
  compact?: boolean;
}

const STATUS_CONFIG: Record<RWIWindowStatus, {
  icon: string;
  color: string;
  label: string;
  bg: string;
}> = {
  closed:    { icon: '🔒', color: '#ef4444', label: 'CLOSED',    bg: '#450a0a' },
  narrowing: { icon: '⏳', color: '#f59e0b', label: 'NARROWING', bg: '#713f12' },
  open:      { icon: '🪟', color: '#84cc16', label: 'OPEN',      bg: '#1a2e05' },
  peak:      { icon: '🔥', color: '#10b981', label: 'PEAK',      bg: '#022c22' },
};

const RWIIndicator: React.FC<Props> = ({ score, status, compact = false }) => {
  const config = STATUS_CONFIG[status];

  if (compact) {
    return (
      <View style={[styles.compact, { backgroundColor: config.bg }]}>
        <Text style={styles.compactIcon}>{config.icon}</Text>
        <Text style={[styles.compactLabel, { color: config.color }]}>
          {config.label}
        </Text>
        <Text style={[styles.compactScore, { color: config.color }]}>
          {score}
        </Text>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <Text style={styles.sectionLabel}>RECEPTIVITY WINDOW</Text>
      <View style={[styles.badge, { backgroundColor: config.bg, borderColor: config.color }]}>
        <Text style={styles.icon}>{config.icon}</Text>
        <Text style={[styles.statusLabel, { color: config.color }]}>
          {config.label}
        </Text>
        <Text style={[styles.score, { color: config.color }]}>
          {score}
        </Text>
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    gap: 4,
  },
  sectionLabel: {
    fontSize: 10,
    fontWeight: '600',
    color: '#6b7280',
    letterSpacing: 0.8,
  },
  badge: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 10,
    paddingVertical: 6,
    borderRadius: 8,
    borderWidth: 1,
    gap: 6,
  },
  icon: {
    fontSize: 16,
  },
  statusLabel: {
    fontSize: 12,
    fontWeight: '700',
    letterSpacing: 0.8,
    flex: 1,
  },
  score: {
    fontSize: 16,
    fontWeight: '800',
  },
  compact: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 6,
    paddingVertical: 3,
    borderRadius: 6,
    gap: 3,
  },
  compactIcon: {
    fontSize: 12,
  },
  compactLabel: {
    fontSize: 10,
    fontWeight: '700',
  },
  compactScore: {
    fontSize: 11,
    fontWeight: '700',
  },
});

export default RWIIndicator;
