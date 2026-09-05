import { Text, View, StyleSheet } from "react-native";

import { colors } from "../theme";

interface Props {
  content: string;
  isMine: boolean;
}

export default function ChatBubble({ content, isMine }: Props) {
  return (
    <View style={[styles.row, isMine ? styles.rowMine : styles.rowTheirs]}>
      <View style={[styles.bubble, isMine ? styles.bubbleMine : styles.bubbleTheirs]}>
        <Text style={isMine ? styles.textMine : styles.textTheirs}>{content}</Text>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  row: { flexDirection: "row", marginVertical: 4, paddingHorizontal: 12 },
  rowMine: { justifyContent: "flex-end" },
  rowTheirs: { justifyContent: "flex-start" },
  bubble: { maxWidth: "78%", borderRadius: 16, paddingVertical: 10, paddingHorizontal: 14 },
  bubbleMine: { backgroundColor: colors.accent, borderBottomRightRadius: 4 },
  bubbleTheirs: { backgroundColor: colors.creamDeep, borderBottomLeftRadius: 4 },
  textMine: { color: "#fff", fontSize: 15 },
  textTheirs: { color: colors.ink, fontSize: 15 },
});
