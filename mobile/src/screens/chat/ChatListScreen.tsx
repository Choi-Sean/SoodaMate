import { ActivityIndicator, FlatList, Pressable, Text, View, StyleSheet } from "react-native";
import type { NativeStackScreenProps } from "@react-navigation/native-stack";
import { useTranslation } from "react-i18next";

import { useMatches } from "../../hooks/useMatches";
import type { ChatStackParamList } from "../../navigation/ChatStack";
import type { Match } from "../../types";
import { colors } from "../../theme";

type Props = NativeStackScreenProps<ChatStackParamList, "ChatList">;

export default function ChatListScreen({ navigation }: Props) {
  const { t, i18n } = useTranslation();
  const { data: matches, isLoading } = useMatches();

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
        <Text style={styles.emptyText}>{t("chat.empty")}</Text>
      </View>
    );
  }

  const renderItem = ({ item }: { item: Match }) => (
    <Pressable
      style={styles.row}
      onPress={() =>
        navigation.navigate("ChatRoom", {
          matchId: item.id,
          otherUserId: item.other_user_id,
          otherDisplayName: item.other_display_name,
        })
      }
    >
      <View style={styles.avatarPlaceholder} />
      <View style={styles.rowText}>
        <Text style={styles.name}>{item.other_display_name}</Text>
        <Text style={styles.subtext}>
          {t("chat.matchedOn", { date: new Date(item.matched_at).toLocaleDateString(i18n.language) })}
        </Text>
      </View>
    </Pressable>
  );

  return (
    <View style={styles.container}>
      <Text style={styles.header}>{t("chat.title")}</Text>
      <FlatList data={matches} keyExtractor={(m) => m.id} renderItem={renderItem} />
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.white },
  header: { fontSize: 24, fontWeight: "700", padding: 16, paddingTop: 48, color: colors.navy },
  centered: { flex: 1, alignItems: "center", justifyContent: "center", padding: 24 },
  emptyText: { color: colors.muted },
  row: { flexDirection: "row", alignItems: "center", padding: 16, borderBottomWidth: 1, borderBottomColor: colors.border },
  avatarPlaceholder: { width: 48, height: 48, borderRadius: 24, backgroundColor: colors.creamDeep, marginRight: 12 },
  rowText: { flex: 1 },
  name: { fontSize: 16, fontWeight: "600", color: colors.ink },
  subtext: { fontSize: 13, color: colors.muted, marginTop: 2 },
});
