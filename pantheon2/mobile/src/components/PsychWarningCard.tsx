/**
 * PsychWarningCard.tsx — Adversarial psychology review flag card.
 *
 * Shown on PreSessionScreen for each psych flag from PsychReviewAgent.
 * HIGH severity flags require acknowledgment before GO is unlocked.
 * MODERATE flags are shown but do not block start.
 * LOW flags are filtered out before display (session_init.py rule).
 *
 * Per PRD CLAUDE.md Critical Constraint #5:
 *   HIGH flags must be acknowledged. Session cannot start until all are confirmed.
 */

import React from 'react';
import { View, Text, TouchableOpacity, StyleSheet } from 'react-native';
import type { PsychFlag } from '../types';

interface Props {
  flag: PsychFlag;
  acknowledged: boolean;
  onAcknowledge: (flagId: string) => void;
}

const SEVERITY_STYLE = {
  HIGH:     { border: '#ef4444', bg: '#450a0a', icon: '⛔', labelColor: '#ef4444' },
  MODERATE: { border: '#f59e0b', bg: '#713f12', icon: '⚠️', labelColor: '#f59e0b' },
  LOW:      { border: '#6b7280', bg: '#111827', icon: 'ℹ️', labelColor: '#9ca3af' },
};

const PsychWarningCard: React.FC<Props> = ({ flag, acknowledged, onAcknowledge }) => {
  const style = SEVERITY_STYLE[flag.severity] ?? SEVERITY_STYLE.MODERATE;

  return (
    <View style={[styles.card, { borderColor: style.border, backgroundColor: style.bg }]}>
      <View style={styles.header}>
        <Text style={styles.icon}>{style.icon}</Text>
        <Text style={[styles.severity, { color: style.labelColor }]}>
          {flag.severity}
        </Text>
        <Text style={styles.flagType}>{flag.flag_type}</Text>
      </View>

      <Text style={styles.message}>{flag.message}</Text>
      <Text style={styles.recommendation}>{flag.recommendation}</Text>

      {flag.severity === 'HIGH' && !acknowledged && (
        <TouchableOpacity
          style={styles.acknowledgeButton}
          onPress={() => onAcknowledge(flag.flag_id)}
        >
          <Text style={styles.acknowledgeText}>I understand — acknowledge risk</Text>
        </TouchableOpacity>
      )}

      {flag.severity === 'HIGH' && acknowledged && (
        <View style={styles.acknowledgedBadge}>
          <Text style={styles.acknowledgedText}>✓ Acknowledged</Text>
        </View>
      )}
    </View>
  );
};

const styles = StyleSheet.create({
  card: {
    borderRadius: 10,
    borderWidth: 1,
    padding: 12,
    gap: 8,
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
  },
  icon: {
    fontSize: 16,
  },
  severity: {
    fontSize: 11,
    fontWeight: '800',
    letterSpacing: 0.8,
  },
  flagType: {
    fontSize: 11,
    color: '#9ca3af',
    flex: 1,
    marginLeft: 4,
  },
  message: {
    fontSize: 14,
    color: '#f3f4f6',
    lineHeight: 20,
  },
  recommendation: {
    fontSize: 12,
    color: '#d1d5db',
    fontStyle: 'italic',
    lineHeight: 18,
  },
  acknowledgeButton: {
    backgroundColor: '#1f2937',
    borderRadius: 6,
    paddingVertical: 8,
    paddingHorizontal: 12,
    alignItems: 'center',
    marginTop: 4,
  },
  acknowledgeText: {
    color: '#f87171',
    fontSize: 12,
    fontWeight: '600',
  },
  acknowledgedBadge: {
    paddingVertical: 6,
    alignItems: 'center',
  },
  acknowledgedText: {
    color: '#4ade80',
    fontSize: 12,
    fontWeight: '600',
  },
});

export default PsychWarningCard;
