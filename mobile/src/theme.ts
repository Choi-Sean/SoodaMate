// Brand palette shared with web/ — matches the SooDaList family look: clean
// white backgrounds, navy text, and #E8A87C (SooDaList's own accent, not a
// color picked independently for this app) reserved for buttons and other
// "special" elements, rather than tinting every surface with it. `cream`/
// `creamDeep` keep their names (dozens of call sites already reference
// them) but now hold a near-white/soft-neutral value instead of a
// saturated peach — enough to separate a card from the page behind it
// without reading as its own competing color.
export const colors = {
  cream: "#FFFFFF",
  creamDeep: "#F6F2EE",
  accent: "#E8A87C",
  accentDark: "#C4875A",
  accentSoft: "#F5E2D0",
  navy: "#0B3B63",
  navyDeep: "#082944",
  ink: "#2B2118",
  muted: "#8A7A6D",
  sage: "#7FA37A",
  heart: "#E85D6B",
  border: "#ECE7E2",
  white: "#FFFFFF",
  danger: "#D92D20",
};
