import { Image, StyleProp, ImageStyle } from "react-native";
import { useVideoPlayer, VideoView } from "expo-video";

import type { Photo } from "../types";

interface Props {
  media: Photo;
  style?: StyleProp<ImageStyle>;
}

/** Renders a profile Photo as an <Image> or, if it's the one video slot a
 * profile can have, an inline looping muted video — same visual footprint
 * either way so callers (ProfileCard, detail modals) don't need to care. */
export default function ProfileMedia({ media, style }: Props) {
  if (media.media_type === "video") {
    return <ProfileVideo uri={media.url} style={style} />;
  }
  return <Image source={{ uri: media.url }} style={style} />;
}

function ProfileVideo({ uri, style }: { uri: string; style?: StyleProp<ImageStyle> }) {
  const player = useVideoPlayer(uri, (p) => {
    p.loop = true;
    p.muted = true;
    p.play();
  });
  return (
    <VideoView
      player={player}
      style={style}
      contentFit="cover"
      nativeControls={false}
      pointerEvents="none"
    />
  );
}
