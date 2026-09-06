import { ScrollView, StyleSheet, View } from "react-native";

import MediaCarousel from "./MediaCarousel";
import ProfileInfoSections from "./ProfileInfoSections";
import type { Candidate } from "../types";
import { colors } from "../theme";

interface Props {
  candidate: Candidate;
}

/** A whole scrollable profile, Hinge/Bumble-style: photo/video carousel up
 * top (name/age/gender overlaid on it, Bumble-style), then scrolling down
 * reveals fact rows, bio, and pill-grid detail sections (Hinge's plain
 * fact list + Bumble's rounded "About me"/"Looking for" pills), followed
 * by any additional photos/video. Pass `key={candidate.user_id}` from the
 * caller so the carousel resets to the first item on a new candidate. */
export default function ProfileCard({ candidate }: Props) {
  return (
    <View style={styles.card}>
      <ScrollView bounces={false} showsVerticalScrollIndicator={false}>
        <MediaCarousel
          media={candidate.photos}
          displayName={candidate.display_name}
          age={candidate.age}
          gender={candidate.gender}
          distanceKm={candidate.distance_km}
          superlikedMe={candidate.superliked_me}
          verifiedBadge={candidate.verified_badge}
        />
        <ProfileInfoSections candidate={candidate} />
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    flex: 1,
    borderRadius: 24,
    overflow: "hidden",
    backgroundColor: colors.creamDeep,
    shadowColor: "#000",
    shadowOpacity: 0.2,
    shadowRadius: 16,
    shadowOffset: { width: 0, height: 8 },
    elevation: 8,
  },
});
