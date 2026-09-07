import { Image, StyleProp, ImageStyle } from "react-native";

interface Props {
  size?: number;
  style?: StyleProp<ImageStyle>;
}

/** Instagram-style scalloped verified badge, in the app's own brand orange
 * rather than a plain green checkmark or Instagram's blue — a static PNG
 * (generated once, see docs/ARCHITECTURE.md) rather than an SVG shape,
 * since react-native-svg isn't a dependency and adding one would need a new
 * native build (see feedback_no_eas_builds_without_asking). */
export default function VerifiedBadge({ size = 18, style }: Props) {
  return (
    <Image
      source={require("../../assets/verified-badge.png")}
      style={[{ width: size, height: size }, style]}
      resizeMode="contain"
    />
  );
}
