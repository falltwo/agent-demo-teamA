# 前端設計 tokens（方案 A）

**可執行的 Vue 應用程式在上一層目錄 `../web/`**（請見 `web/README.md`）。

本目錄保留 **`styles/direction-a-tokens.css`** 作為單一來源時，請與 `web/src/assets/direction-a-tokens.css` 同步維護。

## Tailwind（v4 範例）

在 CSS 中 `@import "./styles/direction-a-tokens.css";` 後以 `@theme { --color-accent: var(--color-accent); }` 對應語意色，或於 `tailwind.config` 的 `theme.extend.colors` 指向同一變數。
