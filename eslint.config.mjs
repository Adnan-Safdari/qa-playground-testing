import nextVitals from "eslint-config-next/core-web-vitals";

const eslintConfig = [
  // Python projects (Streamlit dashboard, Selenium suite) and their virtualenvs are not JS sources.
  { ignores: ["dashboard/**", "testing/**", "**/.venv/**", "**/venv/**"] },
  ...nextVitals,
];

export default eslintConfig;
