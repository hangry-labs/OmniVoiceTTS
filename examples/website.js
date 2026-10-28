// SPDX-License-Identifier: Apache-2.0. Connect website locales to the original player.
// Keep speech-language selection separate from the six documentation locales.
const requestedSpeechLanguage = new URLSearchParams(location.search).get('language');
const initialGalleryLocale = state.pageLocale;
document.addEventListener('DOMContentLoaded', () => {
  const gallery = document.querySelector('.gallery-content');
  const selector = document.querySelector('#site-language');
  if (!gallery || !selector || !state.manifest) return;
  const reflectLanguage = () => {
    gallery.lang = state.pageLocale;
    gallery.dir = ['ar', 'ur'].includes(state.pageLocale) ? 'rtl' : 'ltr';
    document.documentElement.dir = 'ltr';
    document.documentElement.lang = selector.value;
    document.querySelector('#translation-notice').hidden = true;
    gallery.querySelector('[data-load-status]').textContent = t('languagesLoaded', {count: state.manifest.languages.length});
    const url = new URL(location.href);
    url.searchParams.set('lang', selector.value);
    url.searchParams.set('language', state.selected.slug);
    history.replaceState({}, '', url);
  };
  const selectLanguage = () => {
    chooseLanguage(LANGUAGE_CODE_TO_SLUG[selector.value] || 'english', false, selector.value);
    reflectLanguage();
  };
  if (requestedSpeechLanguage && state.manifest.languages.some(item => item.slug === requestedSpeechLanguage)) {
    const locale = LANGUAGE_SLUG_TO_CODE[requestedSpeechLanguage];
    chooseLanguage(requestedSpeechLanguage, false, locale === 'en' && selector.value === 'nb' ? 'nb' : locale);
    reflectLanguage();
  } else if (Object.hasOwn(LANGUAGE_CODE_TO_SLUG, initialGalleryLocale) && ![...selector.options].some(option => option.value === initialGalleryLocale)) {
    chooseLanguage(LANGUAGE_CODE_TO_SLUG[initialGalleryLocale], false);
    reflectLanguage();
  } else if (state.pageLocale === selector.value) reflectLanguage();
  else selectLanguage();
  selector.addEventListener('change', selectLanguage);
  gallery.querySelector('[data-language-list]').addEventListener('click', event => {
    if (event.target.closest('[data-language-button]')) reflectLanguage();
  });
});
