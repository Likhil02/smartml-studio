const colors = ["slate", "indigo", "emerald", "amber", "red"];
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  safelist: colors.flatMap((c) => [`bg-${c}-100`, `text-${c}-700`]),
  theme: { extend: {} }, plugins: [],
};
