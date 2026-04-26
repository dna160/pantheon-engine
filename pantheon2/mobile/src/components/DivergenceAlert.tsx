/**
 * DivergenceAlert.tsx — Verbal vs paralinguistic state mismatch alert.
 *
 * Fires when Stream A (verbal/transcript) and Stream B (paralinguistics)
 * disagree significantly. Indicates concealed state — prospect says one
 * thing but physiological signals say another.
 *
 * Severity tiers:
 *   HIGH   → solid red border, full message
 *   MEDIUM → amber border, abbreviated message
 *
 * Auto-dismissed by parent when divergence_alert.active becomes false.
 */

import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import type { DivergenceAlert as DivergenceAlertType } from '../types';

interface Props {
  alert: DivergenceAlertType;
}

const DivergenceAlert: React.FC<Props> = ({ alert }) => {
  if (!alert.active) return null;

  const isHigh = alert.severity === 'HIGH';

  return (
    <View style={[styles.container, isHigh ? styles.containerHigh : styles.containerMedium]}>
      <View style={styles.headerRow}>
        <Text style={styles.icon}>{isHigh ? '⚡' : '⚠'}</Text>
        <Text style={[styles.label, isHigh ? styles.labelHigh : styles.labelMedium]}>
          SIGNAL DIVERGENCE
        </Text>
        <Text style={[styles.severity, isHigh ? styles.labelHigh : styles.labelMedium]}>
          {alert.severity}
        </Text>
      </View>

      <Text style={styles.description}>{alert.description}</Text>

      <View style={styles.streamsRow}>
        <View style={styles.streamChip}>
          <Text style={styles.streamLabel}>VERBAL</Text>
          <Text style={styles.streamValue}>{alert.verbal_state}</Text>
        </View>
        <Text style={styles.vsText}>≠</Text>
        <View style={styles.streamChip}>
          <Text style={styles.streamLabel}>PARA</Text>
          <Text style={styles.streamValue}>{alert.para_state}</Text>
        </View>
      </View>

      {alert.recommendation && (
        <Text style={styles.recommendation}>{alert.recommendation}</Text>
      )}
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    borderRadius: 10,
    borderWidth: 1,
    padding: 12,
    gap: 8,
  },
  containerHigh: {
    backgroundColor: '#450a0a',
    borderColor: '#ef4444',
  },
  containerMedium: {
    backgroundColor: '#713f12',
    borderColor: '#f59e0b',
  },
  headerRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
  },
  icon: {
    fontSize: 14,
  },
  label: {
    fontSize: 11,
    fontWeight: '800',
    letterSpacing: 1,
    flex: 1,
  },
  labelHigh: {
    color: '#ef4444',
  },
  labelMedium: {
    color: '#f59e0b',
  },
  severity: {
    fontSize: 10,
    fontWeight: '700',
    letterSpacing: 0.5,
  },
  description: {
    fontSize: 13,
    color: '#f3f4f6',
    lineHeight: 18,
  },
  streamsRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  streamChip: {
    flex: 1,
    backgroundColor: '#0d1117',
    borderRadius: 6,
    paddingHorizontal: 8,
    paddingVertical: 5,
    gap: 1,
  },
  streamLabel: {
    fontSize: 8,
    color: '#6b7280',
    fontWeight: '600',
    letterSpacing: 0.5,
  },
  streamValue: {
    fontSize: 11,
    color: '#d1d5db',
    fontWeight: '600',
  },
  vsText: {
    fontSize: 16,
    color: '#ef4444',
    fontWeight: '700',
  },
  recommendation: {
    fontSize: 11,
    color: '#d1d5db',
    fontStyle: 'italic',
    lineHeight: 16,
  },
});

export default DivergenceAlert;
