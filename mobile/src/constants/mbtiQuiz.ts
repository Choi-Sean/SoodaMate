/** A four-letter axis string, first letter = what picking "a" on any
 * question of this axis counts toward, second letter = "b". E.g. "EI":
 * "a" answers tally toward E, "b" answers tally toward I. */
export type MbtiAxis = "EI" | "SN" | "TF" | "JP";

export interface MbtiQuestion {
  /** 1-50, also the i18n key suffix: mbtiQuiz.q<n>.text/.a/.b */
  n: number;
  axis: MbtiAxis;
}

// 50 questions across 4 axes (13/13/12/12) — 5 pages of 10 for the quiz UI
// (MbtiTestScreen paginates PAGE_SIZE at a time), axes interleaved rather
// than grouped so no single page is "all E/I questions" and answers don't
// cluster from fatigue/pattern-matching. Question text itself lives in
// i18n (mbtiQuiz.q<n>.text/.a/.b, all 5 languages) — this file is only the
// axis-scoring metadata.
export const MBTI_QUIZ_PAGE_SIZE = 10;

export const MBTI_QUESTIONS: MbtiQuestion[] = [
  { n: 1, axis: "EI" }, { n: 2, axis: "SN" }, { n: 3, axis: "TF" }, { n: 4, axis: "JP" },
  { n: 5, axis: "EI" }, { n: 6, axis: "SN" }, { n: 7, axis: "TF" }, { n: 8, axis: "JP" },
  { n: 9, axis: "EI" }, { n: 10, axis: "SN" },
  { n: 11, axis: "TF" }, { n: 12, axis: "JP" }, { n: 13, axis: "EI" }, { n: 14, axis: "SN" },
  { n: 15, axis: "TF" }, { n: 16, axis: "JP" }, { n: 17, axis: "EI" }, { n: 18, axis: "SN" },
  { n: 19, axis: "TF" }, { n: 20, axis: "JP" },
  { n: 21, axis: "EI" }, { n: 22, axis: "SN" }, { n: 23, axis: "TF" }, { n: 24, axis: "JP" },
  { n: 25, axis: "EI" }, { n: 26, axis: "SN" }, { n: 27, axis: "TF" }, { n: 28, axis: "JP" },
  { n: 29, axis: "EI" }, { n: 30, axis: "SN" },
  { n: 31, axis: "TF" }, { n: 32, axis: "JP" }, { n: 33, axis: "EI" }, { n: 34, axis: "SN" },
  { n: 35, axis: "TF" }, { n: 36, axis: "JP" }, { n: 37, axis: "EI" }, { n: 38, axis: "SN" },
  { n: 39, axis: "TF" }, { n: 40, axis: "JP" },
  { n: 41, axis: "EI" }, { n: 42, axis: "SN" }, { n: 43, axis: "TF" }, { n: 44, axis: "JP" },
  { n: 45, axis: "EI" }, { n: 46, axis: "SN" }, { n: 47, axis: "TF" }, { n: 48, axis: "JP" },
  { n: 49, axis: "EI" }, { n: 50, axis: "SN" },
];

/** answers[n] = "a" | "b" for every question 1..50. Ties (6/6 on the two
 * 12-question axes) fall to the first letter of the axis — an arbitrary
 * but deterministic tiebreak, same convention 16personalities-style tests
 * use rather than forcing the user to break the tie themselves. */
export function scoreMbtiQuiz(answers: Record<number, "a" | "b">): string {
  const tally: Record<MbtiAxis, [number, number]> = { EI: [0, 0], SN: [0, 0], TF: [0, 0], JP: [0, 0] };
  for (const q of MBTI_QUESTIONS) {
    const answer = answers[q.n];
    if (!answer) continue;
    tally[q.axis][answer === "a" ? 0 : 1]++;
  }
  const letter = (axis: MbtiAxis) => axis[tally[axis][0] >= tally[axis][1] ? 0 : 1];
  return `${letter("EI")}${letter("SN")}${letter("TF")}${letter("JP")}`;
}
