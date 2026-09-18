import { useState } from "react";
import { Modal, Pressable, ScrollView, Text, View, StyleSheet } from "react-native";
import { Ionicons } from "@expo/vector-icons";
import { useTranslation } from "react-i18next";

import { MBTI_QUESTIONS, MBTI_QUIZ_PAGE_SIZE, scoreMbtiQuiz } from "../constants/mbtiQuiz";
import { MBTI_COMPATIBLE_TYPE, type MbtiType } from "../constants/mbtiTypes";
import { colors } from "../theme";

interface Props {
  visible: boolean;
  onCancel: () => void;
  onApply: (mbti: MbtiType) => void;
}

const TOTAL_PAGES = Math.ceil(MBTI_QUESTIONS.length / MBTI_QUIZ_PAGE_SIZE);

/** Fullscreen "50 questions, 5 pages of 10 -> result" quiz, self-contained
 * (quiz + result both live here, like PhotoCropEditor's own
 * visible/onCancel/onApply shape) since ProfileSetupScreen renders directly
 * from RootNavigator with no navigation prop to push a real screen onto —
 * EditProfileScreen reuses this exact same component rather than a second,
 * stack-screen version, so the quiz only has to be written once. */
export default function MbtiQuizModal({ visible, onCancel, onApply }: Props) {
  const { t } = useTranslation();
  const [phase, setPhase] = useState<"quiz" | "result">("quiz");
  const [page, setPage] = useState(0);
  const [answers, setAnswers] = useState<Record<number, "a" | "b">>({});
  const [result, setResult] = useState<MbtiType | null>(null);
  const [showValidation, setShowValidation] = useState(false);

  const pageQuestions = MBTI_QUESTIONS.slice(page * MBTI_QUIZ_PAGE_SIZE, (page + 1) * MBTI_QUIZ_PAGE_SIZE);
  const pageComplete = pageQuestions.every((q) => answers[q.n]);

  function reset() {
    setPhase("quiz");
    setPage(0);
    setAnswers({});
    setResult(null);
    setShowValidation(false);
  }

  function handleClose() {
    reset();
    onCancel();
  }

  function selectAnswer(n: number, value: "a" | "b") {
    setAnswers((prev) => ({ ...prev, [n]: value }));
    setShowValidation(false);
  }

  function handleNext() {
    if (!pageComplete) {
      setShowValidation(true);
      return;
    }
    if (page < TOTAL_PAGES - 1) {
      setPage((p) => p + 1);
      return;
    }
    setResult(scoreMbtiQuiz(answers) as MbtiType);
    setPhase("result");
  }

  function handlePrev() {
    if (page === 0) return;
    setPage((p) => p - 1);
  }

  function handleApply() {
    if (!result) return;
    onApply(result);
    reset();
  }

  const compatibleType = result ? MBTI_COMPATIBLE_TYPE[result] : null;

  return (
    <Modal visible={visible} animationType="slide" transparent={false} onRequestClose={handleClose}>
      <View style={styles.container}>
        <View style={styles.header}>
          <Pressable onPress={handleClose} hitSlop={12}>
            <Ionicons name="close" size={24} color={colors.navy} />
          </Pressable>
          <Text style={styles.headerTitle}>{t("mbtiQuiz.title")}</Text>
          <View style={{ width: 24 }} />
        </View>

        {phase === "quiz" ? (
          <>
            <Text style={styles.pageIndicator}>{t("mbtiQuiz.pageIndicator", { page: page + 1, total: TOTAL_PAGES })}</Text>
            <ScrollView contentContainerStyle={styles.scrollContent}>
              {page === 0 && <Text style={styles.intro}>{t("mbtiQuiz.intro")}</Text>}
              {pageQuestions.map((q) => (
                <View key={q.n} style={styles.questionCard}>
                  <Text style={styles.questionText}>{t(`mbtiQuiz.q${q.n}.text`)}</Text>
                  {(["a", "b"] as const).map((opt) => (
                    <Pressable
                      key={opt}
                      style={[styles.optionRow, answers[q.n] === opt && styles.optionRowSelected]}
                      onPress={() => selectAnswer(q.n, opt)}
                    >
                      <View style={[styles.radio, answers[q.n] === opt && styles.radioSelected]} />
                      <Text style={[styles.optionText, answers[q.n] === opt && styles.optionTextSelected]}>
                        {t(`mbtiQuiz.q${q.n}.${opt}`)}
                      </Text>
                    </Pressable>
                  ))}
                </View>
              ))}
              {showValidation && <Text style={styles.validationText}>{t("mbtiQuiz.validationIncomplete")}</Text>}
            </ScrollView>
            <View style={styles.footer}>
              {page > 0 && (
                <Pressable style={styles.secondaryButton} onPress={handlePrev}>
                  <Text style={styles.secondaryButtonText}>{t("mbtiQuiz.prev")}</Text>
                </Pressable>
              )}
              <Pressable style={styles.primaryButton} onPress={handleNext}>
                <Text style={styles.primaryButtonText}>{page < TOTAL_PAGES - 1 ? t("mbtiQuiz.next") : t("mbtiQuiz.submit")}</Text>
              </Pressable>
            </View>
          </>
        ) : (
          result && (
            <ScrollView contentContainerStyle={styles.resultContent}>
              <Text style={styles.resultType}>{result}</Text>
              <Text style={styles.resultTitle}>{t("mbtiResult.title", { type: result })}</Text>

              <Text style={styles.resultSectionLabel}>{t("mbtiResult.traitLabel")}</Text>
              <Text style={styles.resultBody}>{t(`mbtiResult.trait.${result}`)}</Text>

              {compatibleType && (
                <>
                  <Text style={styles.resultSectionLabel}>{t("mbtiResult.compatibleLabel")}</Text>
                  <Text style={styles.resultBody}>{t(`mbtiResult.compatible.${result}`)}</Text>
                </>
              )}

              <Pressable style={styles.primaryButton} onPress={handleApply}>
                <Text style={styles.primaryButtonText}>{t("mbtiResult.apply")}</Text>
              </Pressable>
              <Pressable style={styles.secondaryButtonFull} onPress={reset}>
                <Text style={styles.secondaryButtonText}>{t("mbtiResult.retry")}</Text>
              </Pressable>
            </ScrollView>
          )
        )}
      </View>
    </Modal>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.white, paddingTop: 56, paddingHorizontal: 20 },
  header: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", marginBottom: 12 },
  headerTitle: { fontSize: 16, fontWeight: "800", color: colors.navy },
  pageIndicator: { fontSize: 12.5, fontWeight: "700", color: colors.accentDark, marginBottom: 12 },
  scrollContent: { paddingBottom: 24 },
  intro: { fontSize: 13, color: colors.muted, lineHeight: 19, marginBottom: 16 },
  questionCard: {
    backgroundColor: colors.creamDeep,
    borderRadius: 16,
    padding: 16,
    marginBottom: 12,
  },
  questionText: { fontSize: 15, fontWeight: "700", color: colors.navy, marginBottom: 12 },
  optionRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 10,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: 10,
    padding: 12,
    marginBottom: 8,
    backgroundColor: colors.white,
  },
  optionRowSelected: { borderColor: colors.accent, backgroundColor: "#FBEEE2" },
  radio: { width: 18, height: 18, borderRadius: 9, borderWidth: 2, borderColor: colors.border },
  radioSelected: { borderColor: colors.accent, backgroundColor: colors.accent },
  optionText: { flex: 1, fontSize: 14, color: colors.ink },
  optionTextSelected: { color: colors.navy, fontWeight: "700" },
  validationText: { color: colors.danger, fontSize: 12.5, textAlign: "center", marginTop: 4 },
  footer: { flexDirection: "row", gap: 10, paddingVertical: 16 },
  primaryButton: { flex: 1, backgroundColor: colors.accent, borderRadius: 12, paddingVertical: 15, alignItems: "center" },
  primaryButtonText: { color: "#fff", fontWeight: "700", fontSize: 15 },
  secondaryButton: { flex: 1, backgroundColor: colors.creamDeep, borderRadius: 12, paddingVertical: 15, alignItems: "center" },
  secondaryButtonFull: {
    backgroundColor: colors.creamDeep,
    borderRadius: 12,
    paddingVertical: 15,
    alignItems: "center",
    marginTop: 10,
  },
  secondaryButtonText: { color: colors.muted, fontWeight: "700", fontSize: 15 },
  resultContent: { alignItems: "center", paddingBottom: 40 },
  resultType: { fontSize: 40, fontWeight: "900", color: colors.accentDark, marginTop: 12 },
  resultTitle: { fontSize: 17, fontWeight: "800", color: colors.navy, marginTop: 6, marginBottom: 20, textAlign: "center" },
  resultSectionLabel: { alignSelf: "flex-start", fontSize: 12.5, fontWeight: "700", color: colors.accentDark, marginTop: 8, marginBottom: 6 },
  resultBody: { fontSize: 14.5, color: colors.ink, lineHeight: 21, marginBottom: 12 },
});
