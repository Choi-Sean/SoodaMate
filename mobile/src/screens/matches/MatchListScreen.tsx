import { ActivityIndicator, FlatList, Pressable, Text, View, StyleSheet } from "react-native";
import { useNavigation } from "@react-navigation/native";
import { useTranslation } from "react-i18next";

import { useMatches } from "../../hooks/useMatches";
import type { Match } from "../../types";
import { colors } from "../../theme";

export default function MatchListScreen() {
  const { t } = useTranslation();
  const { data: matches, isLoading } = useMatches();
  const navigation = useNavigation<any>();

  if (isLoading) {
    return (
      <View style={styles.centered}>
        <ActivityIndicator size="large" color={colors.accent} />
      </View>
    );
  }

  if (!matches || matches.length === 0) {
    return (
      <View style={styles.centered}>
        <Text style={styles.emptyText}>{t("matches.empty")}</Text>
      </View>
    );
  }

  const renderItem = ({ item }: { item: Match }) => (
    <Pressable
      style={styles.tile}
      onPress={() =>
        navigation.navigate("Chat", {
          screen: "ChatRoom",
          params: { matchId: item.id, otherUserId: item.other_user_id, otherDisplayName: item.other_display_name },
        })
      }
    >
      <View style={styles.avatarPlaceholder} />
      <Text style={styles.name}>{item.other_display_name}</Text>
    </Pressable>
  );

  return (
    <View style={styles.container}>
      <Text style={styles.header}>{t("matches.title")}</Text>
      <FlatList
        data={matches}
        keyExtractor={(m) => m.id}
        renderItem={renderItem}
        numColumns={3}
        contentContainerStyle={styles.grid}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.white },
  header: { fontSize: 24, fontWeight: "700", padding: 16, paddingTop: 48, color: colors.navy },
  centered: { flex: 1, alignItems: "center", justifyContent: "center", padding: 24 },
  emptyText: { color: colors.muted },
  grid: { paddingHorizontal: 8 },
  tile: { flex: 1 / 3, alignItems: "center", padding: 8 },
  avatarPlaceholder: { width: 80, height: 80, borderRadius: 40, backgroundColor: colors.creamDeep, marginBottom: 6 },
  name: { fontSize: 13, fontWeight: "500", textAlign: "center", color: colors.ink },
});
