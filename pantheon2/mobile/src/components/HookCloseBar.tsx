/**
 * HookCloseBar.tsx — Hook and Close bar visualization.
 *
 * Renders two horizontal bars (0–100) with trend indicators.
 * Hook bar: attention activation (starts at 50)
 * Close bar: decision proximity (starts at 30 — must be earned)
 *
 * Color coding:
 *   Hook:  0–39 = red, 40–65 = amber, 66–100 = green
 *   Close: 0–39 = red, 40–59 = amber, 60–79 = lime, 80–100 = green (peak)
 */

import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import type { BarState, BarTrend } from '../types';

interface Props {
  barState: BarState;
  compact?: boolean;   // Watch-style compact layout
}

const TREND_ARROW: Record<BarTrend, string> = {
  rising: '↑',
  falling: '↓',
  stable: '→',
};

function hookColor(score: number): string {
  if (score >= 66) return '#22c55e';   // green-500
  if (score >= 40) return '#f59e0b';   // amber-500
  return '#ef4444';                    // red-500
}

function closeColor(score: number): string {
  if (score >= 80) return '#10b981';   // emerald-500
  if (score >= 60) return '#84cc16';   // lime-500
  if (score >= 40) return '#f59e0b';   // amber-500
  return '#ef4444';                    // red-500
}

const HookCloseBar: React.FC<Props> = ({ barState, compact = false }) => {
  const { hook_score, close_score, hook_trend, close_trend } = barState;

  return (
    <View style={[styles.container, compact && styles.compact]}>
      {/* Hook Bar */}
      <View style={styles.row}>
        <Text style={[styles.label, compact && styles.labelCompact]}>
          HOOK {TREND_ARROW[hook_trend]}
        </Text>
        <View style={styles.track}>
          <View
            style={[
              styles.fill,
              { width: `${hook_score}%`, backgroundColor: hookColor(hook_score) },
            ]}
          />
        </View>
        {!compact && (
          <Text style={[styles.score, { color: hookColor(hook_score) }]}>
            {hook_score}
          </Text>
        )}
      </View>

      {/* Close Bar */}
      <View style={[styles.row, compact && styles.rowCompactSpacing]}>
        <Text style={[styles.label, compact && styles.labelCompact]}>
          CLOSE {TREND_ARROW[close_trend]}
        </Text>
        <View style={styles.track}>
          <View
            style={[
              styles.fill,
              { width: `${close_score}%`, backgroundColor: closeColor(close_score) },
            ]}
          />
        </View>
        {!compact && (
          <Text style={[styles.score, { color: closeColor(close_score) }]}>
            {close_score}
          </Text>
        )}
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    gap: 10,
  },
  compact: {
    gap: 6,
  },
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  rowCompactSpacing: {
    gap: 6,
  },
  label: {
    color: '#9ca3af',        // gray-400
    fontSize: 11,
    fontWeight: '600',
    letterSpacing: 0.8,
    width: 72,
  },
  labelCompact: {
    fontSize: 10,
    width: 60,
  },
  track: {
    flex: 1,
    height: 8,
    backgroundColor: '#1f2937',   // gray-800
    borderRadius: 4,
    overflow: 'hidden',
  },
  fill: {
    height: '100%',
    borderRadius: 4,
  },
  score: {
    fontSize: 14,
    fontWeight: '700',
    width: 32,
    textAlign: 'right',
  },
});

export default HookCloseBar;
