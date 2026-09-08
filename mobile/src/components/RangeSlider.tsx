import { useRef, useState } from "react";
import { PanResponder, Text, View, StyleSheet, LayoutChangeEvent } from "react-native";

import { colors } from "../theme";

interface Props {
  label: string;
  min: number;
  max: number;
  valueMin: number;
  valueMax: number;
  step?: number;
  onChange: (min: number, max: number) => void;
  formatValue?: (value: number) => string;
}

const THUMB_SIZE = 24;

/** Dual-handle range slider — drag either end of the track. Pure
 * View + PanResponder (both built into react-native core), so it works on
 * web/iOS/Android without a new native dependency like
 * @react-native-community/slider (see feedback_no_eas_builds_without_asking:
 * no native rebuild while EAS builds are on hold). */
export default function RangeSlider({ label, min, max, valueMin, valueMax, step = 1, onChange, formatValue }: Props) {
  const [trackWidth, setTrackWidth] = useState(0);
  const startValueRef = useRef(0);

  // The two PanResponders below are created exactly once via useRef (see
  // the .current pattern further down) — recreating them every render
  // would risk resetting the gesture responder's negotiation mid-drag.
  // But that means their callbacks close over whatever min/max/valueMin/
  // valueMax/onChange existed at that very first render, unless they read
  // through this ref instead — kept in sync on every render — so a drag
  // always computes from the current values. Without this, every drag
  // after the first one used the stale mount-time values: e.g. dragging
  // the min handle would silently snap the max handle back to whatever it
  // was when the component first mounted, since onPanResponderMove's own
  // `onChange(next, valueMax)` call would pass that frozen valueMax.
  const latest = useRef({ min, max, step, valueMin, valueMax, trackWidth, onChange });
  latest.current = { min, max, step, valueMin, valueMax, trackWidth, onChange };

  const range = max - min;
  const usableWidth = Math.max(1, trackWidth - THUMB_SIZE);

  function valueToX(value: number): number {
    if (range <= 0) return 0;
    return ((value - min) / range) * usableWidth;
  }

  function dxToValue(startValue: number, dx: number): number {
    const { min, max, step, trackWidth } = latest.current;
    const range = max - min;
    const usableWidth = Math.max(1, trackWidth - THUMB_SIZE);
    if (usableWidth <= 0) return startValue;
    const deltaValue = (dx / usableWidth) * range;
    const raw = startValue + deltaValue;
    const stepped = Math.round(raw / step) * step;
    return Math.min(max, Math.max(min, stepped));
  }

  function onLayout(e: LayoutChangeEvent) {
    setTrackWidth(e.nativeEvent.layout.width);
  }

  const minPanResponder = useRef(
    PanResponder.create({
      onStartShouldSetPanResponder: () => true,
      onMoveShouldSetPanResponder: () => true,
      onPanResponderGrant: () => {
        startValueRef.current = latest.current.valueMin;
      },
      onPanResponderMove: (_evt, gesture) => {
        const { valueMax, onChange } = latest.current;
        const next = dxToValue(startValueRef.current, gesture.dx);
        onChange(Math.min(next, valueMax), valueMax);
      },
    })
  ).current;

  const maxPanResponder = useRef(
    PanResponder.create({
      onStartShouldSetPanResponder: () => true,
      onMoveShouldSetPanResponder: () => true,
      onPanResponderGrant: () => {
        startValueRef.current = latest.current.valueMax;
      },
      onPanResponderMove: (_evt, gesture) => {
        const { valueMin, onChange } = latest.current;
        const next = dxToValue(startValueRef.current, gesture.dx);
        onChange(valueMin, Math.max(next, valueMin));
      },
    })
  ).current;

  const minX = valueToX(valueMin);
  const maxX = valueToX(valueMax);
  const fmt = formatValue ?? ((v: number) => String(v));

  return (
    <View style={styles.container}>
      <View style={styles.headerRow}>
        <Text style={styles.label}>{label}</Text>
        <Text style={styles.valueText}>
          {fmt(valueMin)} – {fmt(valueMax)}
        </Text>
      </View>
      <View style={styles.track} onLayout={onLayout}>
        <View style={styles.trackBg} />
        {trackWidth > 0 && (
          <>
            <View style={[styles.trackFill, { left: minX + THUMB_SIZE / 2, width: Math.max(0, maxX - minX) }]} />
            <View style={[styles.thumb, { left: minX }]} {...minPanResponder.panHandlers} hitSlop={12} />
            <View style={[styles.thumb, { left: maxX }]} {...maxPanResponder.panHandlers} hitSlop={12} />
          </>
        )}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { marginTop: 12, marginBottom: 8 },
  headerRow: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", marginBottom: 12 },
  label: { fontSize: 14, fontWeight: "600", color: colors.muted },
  valueText: { fontSize: 14, fontWeight: "700", color: colors.navy },
  track: { height: THUMB_SIZE, justifyContent: "center" },
  trackBg: { position: "absolute", left: THUMB_SIZE / 2, right: THUMB_SIZE / 2, height: 4, borderRadius: 2, backgroundColor: colors.border },
  trackFill: { position: "absolute", height: 4, borderRadius: 2, backgroundColor: colors.accent },
  thumb: {
    position: "absolute",
    width: THUMB_SIZE,
    height: THUMB_SIZE,
    borderRadius: THUMB_SIZE / 2,
    backgroundColor: colors.white,
    borderWidth: 3,
    borderColor: colors.accent,
    shadowColor: "#000",
    shadowOpacity: 0.2,
    shadowRadius: 3,
    shadowOffset: { width: 0, height: 1 },
    elevation: 2,
  },
});
