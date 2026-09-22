import { ActivityIndicator, Text, View, StyleSheet } from "react-native";
import { useQuery } from "@tanstack/react-query";
import type { NativeStackScreenProps } from "@react-navigation/native-stack";
import { useTranslation } from "react-i18next";

import ProfileCard from "../../components/ProfileCard";
import { getMatchedProfile } from "../../api/matches";
import type { ChatStackParamList } from "../../navigation/ChatStack";
import { colors } from "../../theme";

type Props = NativeStackScreenProps<ChatStackParamList, "MatchedProfile">;

/** Reached by tapping a match's name in the chat header — only offered there
 * once there's something to show (an ordinary match, or a blind one that's
 * been revealed). Reuses the exact same card Discover/Likes show, built from
 * GET /matches/{id}/profile (birth date is never sent, only the computed
 * age — same as every other candidate card in the app). */
export default function MatchedProfileScreen({ route }: Props) {
  const { t } = useTranslation();
  const { matchId } = route.params;
  const { data: candidate, isLoading, isError } = useQuery({
    queryKey: ["matchedProfile", matchId],
    queryFn: () => getMatchedProfile(matchId),
  });

  if (isLoading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" color={colors.accent} />
      </View>
    );
  }

  if (isError || !candidate) {
    return (
      <View style={styles.center}>
        <Text style={styles.errorText}>{t("common.somethingWentWrong")}</Text>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      <ProfileCard candidate={candidate} flush />
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.white },
  center: { flex: 1, alignItems: "center", justifyContent: "center", backgroundColor: colors.white },
  errorText: { color: colors.muted, fontSize: 15 },
});
