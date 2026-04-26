/**
 * HiddenSignalPanel.tsx — Phone-only: Stream B paralinguistic display.
 *
 * Shows real-time paralinguistic signals from Stream B (raw audio analysis).
 * Phone-only: never rendered on watch or glasses.
 *
 * Field names match Python paralinguistic_extractor.ParalinguisticSignals exactly:
 *   - speech_rate_delta   (-1.0 to +1.0 relative to baseline)
 *   - volume_level        (0.0–1.0 normalized)
 *   - pause_duration      (seconds)
 *   - voice_tension_index (0.0–1.0)
 *   - cadence_consistency_score (0.0–1.0)
 */

import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import type { ParalinguisticSignals } from '../types';

interface Props {
  para: ParalinguisticSignals;
}

function tensionColor(index: number): string {
  if (index >= 0.7) return '#ef4444';
  if (index >= 0.4) return '#f59e0b';
  return '#22c55e';
}

function speechRateInfo(delta: number): { label: string; color: string } {
  if (delta > 0.15) return { label: 'FAST', color: '#f59e0b' };
  if (delta < -0.15) return { label: 'SLOW', color: '#6366f1' };
  return { label: 'NORMAL', color: '#6b7280' };
}

function volumeInfo(level: number): { icon: string; label: string; color: string } {
  if (level >= 0.65) return { icon: '↑', label: 'HIGH', color: '#22c55e' };
  if (level <= 0.35) return { icon: '↓', label: 'LOW', color: '#ef4444' };
  return { icon: '→', label: 'MED', color: '#6b7280' };
}

const HiddenSignalPanel: React.FC<Props> = ({ para }) => {
  const rateInfo = speechRateInfo(para.speech_rate_delta);
  const volInfo = volumeInfo(para.volume_level);
  const tensionPct = Math.round(para.voice_tension_index * 100);
  const tensionCol = tensionColor(para.voice_tension_index);
  const cadencePct = Math.round(para.cadence_consistency_score * 100);

  return (
    <View style={styles.container}>
      <Text style={styles.sectionLabel}>STREAM B — PARALINGUISTICS</Text>

      <View style={styles.grid}>
        {/* Speech rate delta */}
        <View style={styles.cell}>
          <Text style={styles.cellLabel}>SPEECH RATE</Text>
          <View style={styles.cellRow}>
            <Text style={[styles.cellValue, { color: rateInfo.color }]}>
              {para.speech_rate_delta >= 0 ? '+' : ''}
              {(para.speech_rate_delta * 100).toFixed(0)}%
            </Text>
            <Text style={[styles.rateTag, { color: rateInfo.color }]}>{rateInfo.label}</Text>
          </View>
        </View>

        {/* Volume level */}
        <View style={styles.cell}>
          <Text style={styles.cellLabel}>VOLUME</Text>
          <View style={styles.cellRow}>
            <Text style={[styles.trendArrow, { color: volInfo.color }]}>{volInfo.icon}</Text>
            <Text style={[styles.cellValue, { color: volInfo.color }]}>{volInfo.label}</Text>
          </View>
        </View>

        {/* Pause duration */}
        <View style={styles.cell}>
          <Text style={styles.cellLabel}>PAUSE</Text>
          <View style={styles.cellRow}>
            <Text style={styles.cellValue}>{para.pause_duration.toFixed(1)}</Text>
            <Text style={styles.cellUnit}>s</Text>
          </View>
        </View>

        {/* Cadence consistency */}
        <View style={styles.cell}>
          <Text style={styles.cellLabel}>CADENCE</Text>
          <Text style={styles.cellValue}>{cadencePct}%</Text>
        </View>
      </View>

      {/* Tension bar */}
      <View style={styles.tensionRow}>
        <Text style={styles.cellLabel}>TENSION</Text>
        <View style={styles.tensionBarTrack}>
          <View
            style={[
              styles.tensionBarFill,
              { width: `${tensionPct}%`, backgroundColor: tensionCol },
            ]}
          />
        </View>
        <Text style={[styles.tensionScore, { color: tensionCol }]}>{tensionPct}</Text>
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    backgroundColor: '#0d1117',
    borderRadius: 10,
    padding: 12,
    gap: 10,
    borderWidth: 1,
    borderColor: '#1f2937',
  },
  sectionLabel: {
    fontSize: 9,
    fontWeight: '600',
    color: '#4b5563',
    letterSpacing: 1,
  },
  grid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8,
  },
  cell: {
    flex: 1,
    minWidth: '40%',
    gap: 2,
  },
  cellLabel: {
    fontSize: 9,
    color: '#6b7280',
    fontWeight: '600',
    letterSpacing: 0.6,
  },
  cellRow: {
    flexDirection: 'row',
    alignItems: 'baseline',
    gap: 3,
  },
  cellValue: {
    fontSize: 14,
    fontWeight: '700',
    color: '#d1d5db',
  },
  cellUnit: {
    fontSize: 10,
    color: '#6b7280',
  },
  rateTag: {
    fontSize: 9,
    fontWeight: '700',
    letterSpacing: 0.5,
    marginLeft: 2,
  },
  trendArrow: {
    fontSize: 16,
    fontWeight: '700',
  },
  tensionRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  tensionBarTrack: {
    flex: 1,
    height: 4,
    backgroundColor: '#1f2937',
    borderRadius: 2,
    overflow: 'hidden',
  },
  tensionBarFill: {
    height: '100%',
    borderRadius: 2,
  },
  tensionScore: {
    fontSize: 12,
    fontWeight: '700',
    minWidth: 24,
    textAlign: 'right',
  },
  flagRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 5,
  },
  flagDot: {
    fontSize: 8,
    color: '#f59e0b',
  },
  flagText: {
    fontSize: 10,
    color: '#9ca3af',
    fontStyle: 'italic',
  },
});

export default HiddenSignalPanel;
