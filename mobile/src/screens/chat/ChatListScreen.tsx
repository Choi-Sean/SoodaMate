import { ActivityIndicator, FlatList, Image, Pressable, Text, View, StyleSheet } from "react-native";
import { Ionicons } from "@expo/vector-icons";
import type { NativeStackScreenProps } from "@react-navigation/native-stack";
import { useTranslation } from "react-i18next";

import ScreenHeader from "../../components/ScreenHeader";
import { useMatches } from "../../hooks/useMatches";
import type { ChatStackParamList } from "../../navigation/ChatStack";
import type { Match } from "../../types";
import { colors } from "../../theme";

type Props = NativeStackScreenProps<ChatStackParamList, "ChatList">;

export default function ChatListScreen({ navigation }: Props) {
  const { t, i18n } = useTranslation();
  const { data: matches, isLoading } = useMatches();

  const renderItem = ({ item }: { item: Match }) => {
    const expired = !item.is_active;
    return (
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
        {item.other_photo_url ? (
          <Image source={{ uri: item.other_photo_url }} style={[styles.avatar, expired && styles.avatarExpired]} />
        ) : (
          <View style={[styles.avatar, styles.avatarPlaceholder, expired && styles.avatarExpired]}>
            <Ionicons name="person" size={22} color={colors.border} />
          </View>
        )}
        <View style={styles.rowText}>
          <Text style={[styles.name, expired && styles.textExpired]}>{item.other_display_name}</Text>
          {expired ? (
            <View style={styles.expiredPill}>
              <Ionicons name="time-outline" size={11} color={colors.muted} />
              <Text style={styles.expiredPillText}>{t("chat.expired")}</Text>
            </View>
          ) : (
            <Text style={styles.subtext}>
              {t("chat.matchedOn", { date: new Date(item.matched_at).toLocaleDateString(i18n.language) })}
            </Text>
          )}
        </View>
        <Ionicons name="chevron-forward" size={18} color={colors.border} />
      </Pressable>
    );
  };

  return (
    <View style={styles.container}>
      <ScreenHeader title={t("chat.title")} />
      {isLoading ? (
        <View style={styles.centered}>
          <ActivityIndicator size="large" color={colors.accent} />
        </View>
      ) : !matches || matches.length === 0 ? (
        <View style={styles.centered}>
          <Text style={styles.emptyText}>{t("chat.empty")}</Text>
        </View>
      ) : (
        <FlatList data={matches} keyExtractor={(m) => m.id} renderItem={renderItem} />
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.cream },
  centered: { flex: 1, alignItems: "center", justifyContent: "center", padding: 24 },
  emptyText: { color: colors.muted },
  row: { flexDirection: "row", alignItems: "center", padding: 16, borderBottomWidth: 1, borderBottomColor: colors.border, gap: 4 },
  avatar: { width: 52, height: 52, borderRadius: 26, marginRight: 12 },
  avatarExpired: { opacity: 0.45 },
  avatarPlaceholder: { backgroundColor: colors.creamDeep, alignItems: "center", justifyContent: "center" },
  rowText: { flex: 1 },
  name: { fontSize: 16, fontWeight: "700", color: colors.ink },
  textExpired: { color: colors.muted },
  subtext: { fontSize: 13, color: colors.muted, marginTop: 2 },
  expiredPill: { flexDirection: "row", alignItems: "center", gap: 4, marginTop: 3 },
  expiredPillText: { fontSize: 12, color: colors.muted, fontWeight: "600" },
});
