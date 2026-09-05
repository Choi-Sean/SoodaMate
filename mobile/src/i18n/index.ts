import i18n from "i18next";
import { initReactI18next } from "react-i18next";
import * as Localization from "expo-localization";

import * as secureStorage from "../services/secureStorage";
import ko from "./locales/ko.json";
import en from "./locales/en.json";
import es from "./locales/es.json";
import zh from "./locales/zh.json";
import ja from "./locales/ja.json";

export const SUPPORTED_LANGUAGES = ["ko", "en", "es", "zh", "ja"] as const;
export type SupportedLanguage = (typeof SUPPORTED_LANGUAGES)[number];

const LANG_STORAGE_KEY = "suda_language";

const resources = {
  ko: { translation: ko },
  en: { translation: en },
  es: { translation: es },
  zh: { translation: zh },
  ja: { translation: ja },
};

function detectDeviceLanguage(): SupportedLanguage {
  const deviceLang = Localization.getLocales()[0]?.languageCode ?? "en";
  return (SUPPORTED_LANGUAGES as readonly string[]).includes(deviceLang)
    ? (deviceLang as SupportedLanguage)
    : "en";
}

export async function initI18n(): Promise<void> {
  const saved = await secureStorage.getItem(LANG_STORAGE_KEY);
  const initialLanguage =
    saved && (SUPPORTED_LANGUAGES as readonly string[]).includes(saved)
      ? (saved as SupportedLanguage)
      : detectDeviceLanguage();

  await i18n.use(initReactI18next).init({
    resources,
    lng: initialLanguage,
    fallbackLng: "en",
    interpolation: { escapeValue: false },
    compatibilityJSON: "v4",
  });
}

export async function setLanguage(lang: SupportedLanguage): Promise<void> {
  await i18n.changeLanguage(lang);
  await secureStorage.setItem(LANG_STORAGE_KEY, lang);
}

export default i18n;
