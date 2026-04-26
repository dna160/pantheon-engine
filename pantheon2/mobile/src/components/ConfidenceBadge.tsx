/**
 * ConfidenceBadge.tsx — Genome confidence level badge.
 *
 * ALWAYS shown on every screen that displays genome-derived recommendations.
 * Per PRD CLAUDE.md Critical Constraint #4: never optional.
 *
 * Colors: HIGH = green, MEDIUM = yellow, LOW = red
 */

import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import type { ConfidenceBadge as ConfidenceBadgeType } from '../types';

interface Props {
  badge: ConfidenceBadgeType;
  size?: 'small' | 'normal';
}

const COLOR_MAP = {
  green: { bg: '#14532d', text: '#4ade80', border: '#166534' },
  yellow: { bg: '#713f12', text: '#fde047', border: '#854d0e' },
  red: { bg: '#450a0a', text: '#f87171', border: '#7f1d1d' },
};

const ConfidenceBadge: React.FC<Props> = ({ badge, size = 'normal' }) => {
  const colors = COLOR_MAP[badge.color];
  const isSmall = size === 'small';

  return (
    <View
      style={[
        styles.badge,
        {
          backgroundColor: colors.bg,
          borderColor: colors.border,
        },
        isSmall && styles.badgeSmall,
      ]}
    >
      <Text style={[styles.level, { color: colors.text }, isSmall && styles.textSmall]}>
        {badge.level}
      </Text>
      {!isSmall && (
        <Text style={[styles.label, { color: colors.text }]}>
          {badge.label}
        </Text>
      )}
    </View>
  );
};

const styles = StyleSheet.create({
  badge: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 6,
    borderWidth: 1,
    gap: 4,
  },
  badgeSmall: {
    paddingHorizontal: 6,
    paddingVertical: 2,
  },
  level: {
    fontSize: 11,
    fontWeight: '700',
    letterSpacing: 0.8,
  },
  label: {
    fontSize: 11,
    opacity: 0.85,
  },
  textSmall: {
    fontSize: 9,
  },
});

export default ConfidenceBadge;
