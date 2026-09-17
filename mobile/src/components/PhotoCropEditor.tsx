import { useEffect, useRef, useState } from "react";
import { ActivityIndicator, Dimensions, Image, Modal, PanResponder, Pressable, StyleSheet, Text, View } from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { ImageManipulator, SaveFormat } from "expo-image-manipulator";
import { useTranslation } from "react-i18next";

import SingleSlider from "./SingleSlider";
import { colors } from "../theme";

interface Props {
  visible: boolean;
  uri: string | null;
  naturalWidth: number;
  naturalHeight: number;
  onCancel: () => void;
  onConfirm: (result: { uri: string; width: number; height: number }) => void;
}

// Same width:height ratio MediaCarousel/DiscoverScreen/LikesScreen use to
// actually display a profile's photos to other people (see those files'
// own `aspectRatio: 0.72`) — the frame below previews exactly that shape
// live while dragging/zooming, so what's inside it IS what a guest will
// see, not an approximation of it.
const DISPLAY_ASPECT_RATIO = 0.72;
const MAX_ZOOM = 3;

function clampPos(
  pos: { x: number; y: number },
  scale: number,
  frameWidth: number,
  frameHeight: number,
  naturalWidth: number,
  naturalHeight: number
) {
  const displayedW = naturalWidth * scale;
  const displayedH = naturalHeight * scale;
  const minX = Math.min(0, frameWidth - displayedW);
  const minY = Math.min(0, frameHeight - displayedH);
  return {
    x: Math.min(0, Math.max(minX, pos.x)),
    y: Math.min(0, Math.max(minY, pos.y)),
  };
}

/** Fullscreen "select area -> crop" editor: drag to reposition, slider to
 * zoom, both live-clamped so the frame is always fully covered (no gaps).
 * Confirming computes the crop rectangle in the ORIGINAL image's pixel
 * coordinates from the current pan/zoom and runs it through
 * expo-image-manipulator — no server round-trip, this all happens on the
 * local file before it's ever uploaded. PanResponder (not a gesture-handler
 * dependency) to match the drag-slider convention already used by
 * RangeSlider/SingleSlider elsewhere in this app. */
export default function PhotoCropEditor({ visible, uri, naturalWidth, naturalHeight, onCancel, onConfirm }: Props) {
  const { t } = useTranslation();
  const screen = Dimensions.get("window");
  const frameWidth = Math.min(screen.width - 64, 340);
  const frameHeight = frameWidth / DISPLAY_ASPECT_RATIO;

  const [zoom, setZoom] = useState(1);
  const [pos, setPos] = useState({ x: 0, y: 0 });
  const [saving, setSaving] = useState(false);

  const baseScale = naturalWidth > 0 && naturalHeight > 0 ? Math.max(frameWidth / naturalWidth, frameHeight / naturalHeight) : 1;
  const scale = baseScale * zoom;

  // Mirrors of the latest render's values for the PanResponder's callbacks,
  // which are only ever created once (see the useRef below) — same fix
  // SingleSlider.tsx uses for the identical stale-closure problem.
  const latest = useRef({ scale, frameWidth, frameHeight, naturalWidth, naturalHeight, pos });
  latest.current = { scale, frameWidth, frameHeight, naturalWidth, naturalHeight, pos };
  const dragStart = useRef({ x: 0, y: 0 });

  useEffect(() => {
    if (!visible) return;
    setZoom(1);
    const s = baseScale;
    const centered = { x: (frameWidth - naturalWidth * s) / 2, y: (frameHeight - naturalHeight * s) / 2 };
    setPos(clampPos(centered, s, frameWidth, frameHeight, naturalWidth, naturalHeight));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [visible, uri]);

  useEffect(() => {
    setPos((p) => clampPos(p, scale, frameWidth, frameHeight, naturalWidth, naturalHeight));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [zoom]);

  const panResponder = useRef(
    PanResponder.create({
      onStartShouldSetPanResponder: () => true,
      onMoveShouldSetPanResponder: (_evt, gesture) => Math.abs(gesture.dx) > 2 || Math.abs(gesture.dy) > 2,
      onPanResponderGrant: () => {
        dragStart.current = latest.current.pos;
      },
      onPanResponderMove: (_evt, gesture) => {
        const { scale, frameWidth, frameHeight, naturalWidth, naturalHeight } = latest.current;
        setPos(
          clampPos(
            { x: dragStart.current.x + gesture.dx, y: dragStart.current.y + gesture.dy },
            scale,
            frameWidth,
            frameHeight,
            naturalWidth,
            naturalHeight
          )
        );
      },
    })
  ).current;

  async function handleConfirm() {
    if (!uri || naturalWidth <= 0 || naturalHeight <= 0) return;
    setSaving(true);
    try {
      const cropOriginX = Math.min(naturalWidth, Math.max(0, -pos.x / scale));
      const cropOriginY = Math.min(naturalHeight, Math.max(0, -pos.y / scale));
      const cropWidth = Math.min(frameWidth / scale, naturalWidth - cropOriginX);
      const cropHeight = Math.min(frameHeight / scale, naturalHeight - cropOriginY);

      const context = ImageManipulator.manipulate(uri);
      context.crop({
        originX: Math.round(cropOriginX),
        originY: Math.round(cropOriginY),
        width: Math.round(cropWidth),
        height: Math.round(cropHeight),
      });
      const rendered = await context.renderAsync();
      const saved = await rendered.saveAsync({ format: SaveFormat.JPEG, compress: 0.85 });
      onConfirm({ uri: saved.uri, width: Math.round(cropWidth), height: Math.round(cropHeight) });
    } catch {
      // Leaves the original photo in place — a failed crop shouldn't lose
      // the photo the user already picked.
      onCancel();
    } finally {
      setSaving(false);
    }
  }

  if (!uri) return null;

  const displayedW = naturalWidth * scale;
  const displayedH = naturalHeight * scale;

  return (
    <Modal visible={visible} animationType="fade" transparent={false} onRequestClose={onCancel}>
      <View style={styles.container}>
        <View style={styles.header}>
          <Pressable onPress={onCancel} hitSlop={10}>
            <Text style={styles.headerButton}>{t("common.cancel")}</Text>
          </Pressable>
          <Text style={styles.headerTitle}>{t("photoCrop.title")}</Text>
          <Pressable onPress={handleConfirm} disabled={saving} hitSlop={10}>
            {saving ? <ActivityIndicator color={colors.accent} /> : <Text style={styles.headerButtonPrimary}>{t("photoCrop.done")}</Text>}
          </Pressable>
        </View>

        <Text style={styles.hint}>{t("photoCrop.hint")}</Text>

        <View style={styles.frameOuter}>
          <View style={[styles.frame, { width: frameWidth, height: frameHeight }]}>
            <View
              style={[styles.imageWrap, { width: frameWidth, height: frameHeight }]}
              {...panResponder.panHandlers}
            >
              <Image
                source={{ uri }}
                style={{ position: "absolute", left: pos.x, top: pos.y, width: displayedW, height: displayedH }}
                resizeMode="cover"
              />
            </View>
          </View>
          <Text style={styles.previewLabel}>{t("photoCrop.previewLabel")}</Text>
        </View>

        <View style={styles.zoomRow}>
          <Ionicons name="remove-circle-outline" size={20} color={colors.muted} />
          <View style={styles.zoomSlider}>
            <SingleSlider label={t("photoCrop.zoomLabel")} min={1} max={MAX_ZOOM} step={0.05} value={zoom} onChange={setZoom} formatValue={(v) => `${v.toFixed(1)}x`} />
          </View>
          <Ionicons name="add-circle-outline" size={20} color={colors.muted} />
        </View>
      </View>
    </Modal>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.navyDeep, paddingTop: 56, paddingHorizontal: 20 },
  header: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", marginBottom: 8 },
  headerButton: { color: "rgba(255,255,255,0.8)", fontSize: 15, fontWeight: "600" },
  headerButtonPrimary: { color: colors.accent, fontSize: 15, fontWeight: "800" },
  headerTitle: { color: "#fff", fontSize: 15, fontWeight: "700" },
  hint: { color: "rgba(255,255,255,0.65)", fontSize: 12.5, textAlign: "center", marginBottom: 18, lineHeight: 18 },
  frameOuter: { alignItems: "center" },
  frame: {
    overflow: "hidden",
    borderRadius: 16,
    borderWidth: 2,
    borderColor: colors.accent,
    backgroundColor: "#000",
  },
  imageWrap: { overflow: "hidden" },
  previewLabel: { color: "rgba(255,255,255,0.5)", fontSize: 11.5, marginTop: 10 },
  zoomRow: { flexDirection: "row", alignItems: "center", gap: 8, marginTop: "auto", marginBottom: 40 },
  zoomSlider: { flex: 1 },
});
