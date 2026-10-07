const state = {
  cardAudios: [],
  currentCard: null,
  introAudio: new Audio(),
  manifest: null,
  selected: null,
  volume: 0.85,
  lastVolume: 0.85,
  pageLocale: "en",
};

const LANGUAGE_CODE_TO_SLUG = {
  ar: "standard_arabic",
  bn: "bengali",
  de: "german",
  en: "english",
  es: "spanish",
  fr: "french",
  hi: "hindi",
  id: "indonesian",
  it: "italian",
  ja: "japanese",
  ko: "korean",
  nl: "dutch",
  pl: "polish",
  pt: "portuguese",
  ru: "russian",
  th: "thai",
  tr: "turkish",
  ur: "urdu",
  vi: "vietnamese",
  zh: "chinese",
};

const LANGUAGE_STORAGE_KEY = "omnivoicetts-examples-language-v1";
const EXAMPLE_I18N = window.EXAMPLE_I18N || { en: {} };
const LANGUAGE_SLUG_TO_CODE = Object.fromEntries(
  Object.entries(LANGUAGE_CODE_TO_SLUG).map(([code, slug]) => [slug, code]),
);

function t(key, variables = {}) {
  const catalog = EXAMPLE_I18N[state.pageLocale] || EXAMPLE_I18N.en || {};
  const fallback = EXAMPLE_I18N.en?.[key] || key;
  return String(catalog[key] || fallback).replace(/\{([a-zA-Z0-9_]+)\}/g, (match, name) => (
    Object.hasOwn(variables, name) ? String(variables[name]) : match
  ));
}

function localizedLanguageName(language) {
  const code = LANGUAGE_SLUG_TO_CODE[language.slug];
  if (!code || typeof Intl.DisplayNames !== "function") {
    return language.language;
  }
  try {
    return new Intl.DisplayNames([state.pageLocale], { type: "language" }).of(code) || language.language;
  } catch {
    return language.language;
  }
}

function translatePage(locale, updateUrl = false) {
  state.pageLocale = EXAMPLE_I18N[locale] ? locale : "en";
  document.documentElement.lang = state.pageLocale;
  document.documentElement.dir = ["ar", "ur"].includes(state.pageLocale) ? "rtl" : "ltr";
  document.title = t("pageTitle");
  document.querySelectorAll("[data-i18n]").forEach((node) => {
    const variables = node.dataset.i18n === "languagesPill"
      ? { count: state.manifest?.languages?.length || 20 }
      : node.dataset.i18n === "samplesPill" ? { count: 10 } : {};
    node.textContent = t(node.dataset.i18n, variables);
  });
  document.querySelectorAll("[data-i18n-aria-label]").forEach((node) => {
    node.setAttribute("aria-label", t(node.dataset.i18nAriaLabel));
  });
  document.querySelectorAll("[data-i18n-content]").forEach((node) => {
    node.setAttribute("content", t(node.dataset.i18nContent));
  });
  if (updateUrl) {
    const url = new URL(window.location.href);
    url.searchParams.set("lang", state.pageLocale);
    history.replaceState({}, "", url);
  }
}

function escapeHtml(value) {
  return String(value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

function assetUrl(file) {
  return `assets/${file}`;
}

function formatTime(value) {
  if (!Number.isFinite(value)) {
    return "0:00";
  }

  const minutes = Math.floor(value / 60);
  const seconds = Math.floor(value % 60).toString().padStart(2, "0");
  return `${minutes}:${seconds}`;
}

function metaFor(language) {
  return window.LANGUAGE_META?.[language.slug] || {
    nativeName: language.language,
    icon: language.language.slice(0, 2).toUpperCase(),
  };
}

function randomItem(items) {
  return items[Math.floor(Math.random() * items.length)];
}

function sampleBadge(sample) {
  const parts = [];
  if (sample.voice_profile) {
    parts.push(sample.voice_profile.replace(/_/g, " "));
  }
  if (sample.nonverbal_tag) {
    parts.push(sample.nonverbal_tag);
  }
  return parts.length ? parts.join(" / ") : t("voiceSample");
}

function setNowPlaying(label) {
  const target = document.querySelector("[data-now-playing]");
  if (target) {
    target.textContent = label || t("ready");
  }
}

function pauseCards(exceptAudio = null) {
  state.cardAudios.forEach((audio) => {
    if (audio !== exceptAudio) {
      audio.pause();
    }
  });
}

function clearCurrentCard() {
  if (state.currentCard) {
    state.currentCard.classList.remove("is-playing");
    state.currentCard.removeAttribute("aria-current");
  }
  state.currentCard = null;
}

function applyAudioVolume(audio) {
  const isMuted = state.volume <= 0.001;
  audio.volume = state.volume;
  audio.muted = isMuted;
}

function allAudios() {
  return [state.introAudio, ...state.cardAudios];
}

function updateVolumeControl() {
  const volumeButton = document.querySelector(".volume-button");
  const volumeSlider = document.querySelector(".volume-slider");
  const volumeIconOn = document.querySelector(".volume-icon-on");
  const volumeIconMuted = document.querySelector(".volume-icon-muted");
  const isMuted = state.volume <= 0.001;

  allAudios().forEach(applyAudioVolume);

  if (volumeSlider) {
    volumeSlider.value = state.volume.toString();
  }

  if (volumeButton) {
    volumeButton.dataset.muted = isMuted.toString();
    volumeButton.setAttribute("aria-label", isMuted ? t("unmuteAudio") : t("muteAudio"));
  }

  if (volumeIconOn && volumeIconMuted) {
    volumeIconOn.hidden = isMuted;
    volumeIconMuted.hidden = !isMuted;
    volumeIconOn.style.display = isMuted ? "none" : "block";
    volumeIconMuted.style.display = isMuted ? "block" : "none";
  }
}

function initVolumeControl() {
  const volumeButton = document.querySelector(".volume-button");
  const volumeSlider = document.querySelector(".volume-slider");
  if (volumeSlider) {
    state.volume = Number.parseFloat(volumeSlider.value || "0.85");
    state.lastVolume = state.volume > 0 ? state.volume : 0.85;
    volumeSlider.addEventListener("input", () => {
      state.volume = Number.parseFloat(volumeSlider.value);
      if (state.volume > 0) {
        state.lastVolume = state.volume;
      }
      updateVolumeControl();
    });
  }

  if (volumeButton) {
    volumeButton.addEventListener("click", () => {
      if (state.volume > 0) {
        state.lastVolume = state.volume;
        state.volume = 0;
      } else {
        state.volume = state.lastVolume || 0.85;
      }
      updateVolumeControl();
    });
  }

  updateVolumeControl();
}

function playIntro(file, label) {
  pauseCards();
  clearCurrentCard();
  state.introAudio.pause();
  state.introAudio.src = assetUrl(file);
  state.introAudio.currentTime = 0;
  applyAudioVolume(state.introAudio);
  setNowPlaying(label);
  state.introAudio.play().catch(() => {
    setNowPlaying(t("autoplayBlocked"));
  });
}

function renderLanguageButtons() {
  const target = document.querySelector("[data-language-list]");
  if (!target) {
    return;
  }

  target.innerHTML = state.manifest.languages
    .map((language) => {
      const meta = metaFor(language);
      return `
        <button class="language-button" type="button" data-language-button="${escapeHtml(language.slug)}" aria-pressed="false">
          <span class="language-icon" aria-hidden="true">${escapeHtml(meta.icon)}</span>
          <span>${escapeHtml(meta.nativeName)}</span>
        </button>
      `;
    })
    .join("");

  target.querySelectorAll("[data-language-button]").forEach((button) => {
    button.addEventListener("click", () => chooseLanguage(button.dataset.languageButton, true));
  });
}

function renderAudioCard({ classes = "", eyebrow, title, description, file, label, badge = "" }) {
  return `
    <article class="brand-card ${classes}" data-audio-card data-audio-label="${escapeHtml(label)}">
      <div class="card-head">
        <div>
          <p>${escapeHtml(eyebrow)}</p>
          <h3>${escapeHtml(title)}</h3>
        </div>
        ${badge ? `<span class="sample-badge">${escapeHtml(badge)}</span>` : ""}
      </div>
      <p class="card-description">${escapeHtml(description)}</p>
      <audio preload="metadata" src="${escapeHtml(assetUrl(file))}"></audio>
    </article>
  `;
}

function renderSelectedLanguage() {
  const language = state.selected;
  const target = document.querySelector("[data-language-detail]");
  if (!target || !language) {
    return;
  }

  state.introAudio.pause();
  pauseCards();
  clearCurrentCard();

  const meta = metaFor(language);
  const clone = language.clone[0];
  const randomSamples = language.random
    .map((sample, index) =>
      renderAudioCard({
        eyebrow: t("sample", { number: String(index + 1).padStart(2, "0") }),
        title: sampleBadge(sample),
        description: sample.text,
        file: sample.file,
        label: `${meta.nativeName} ${t("sample", { number: index + 1 })}`,
        badge: t("play"),
      }),
    )
    .join("");

  target.innerHTML = `
    <section>
      <div class="language-heading">
          <div class="language-title">
            <span class="language-icon large" aria-hidden="true">${escapeHtml(meta.icon)}</span>
            <div>
              <h2>${escapeHtml(meta.nativeName)}</h2>
              <p>${escapeHtml(localizedLanguageName(language))}</p>
            </div>
          </div>
          <button class="filter-button is-active" type="button" data-random-intro="${escapeHtml(language.slug)}">${escapeHtml(t("playRandomIntro"))}</button>
      </div>

      <div class="clone-grid">
        ${renderAudioCard({
          classes: "clone-card",
          eyebrow: t("cloneEyebrow"),
          title: t("cloneTitle"),
          description: t("cloneDescription"),
          file: clone.file,
          label: t("cloneLabel", { language: meta.nativeName }),
          badge: t("clone"),
        })}
      </div>

      <div class="sample-grid">
        ${randomSamples}
      </div>
    </section>
  `;

  target.querySelector("[data-random-intro]")?.addEventListener("click", () => {
    const intro = randomItem(language.intro);
    playIntro(intro.file, t("introLabel", { language: meta.nativeName }));
  });

  enhanceAudioCards(target);
}

function chooseLanguage(slug, autoplayIntro = true, requestedPageLocale = null) {
  const language = state.manifest.languages.find((item) => item.slug === slug);
  if (!language) {
    return;
  }

  state.selected = language;
  translatePage(requestedPageLocale || LANGUAGE_SLUG_TO_CODE[slug] || "en", true);
  try {
    localStorage.setItem(LANGUAGE_STORAGE_KEY, slug);
  } catch {
    // Local storage can be disabled without affecting the examples.
  }
  renderSelectedLanguage();

  document.querySelectorAll("[data-language-button]").forEach((button) => {
    const active = button.dataset.languageButton === slug;
    button.classList.toggle("is-active", active);
    button.setAttribute("aria-pressed", active ? "true" : "false");
  });

  if (autoplayIntro) {
    const intro = randomItem(language.intro);
    playIntro(intro.file, t("introLabel", { language: metaFor(language).nativeName }));
  } else {
    setNowPlaying(t("ready"));
  }
}

function enhanceAudioCards(container) {
  state.cardAudios = Array.from(container.querySelectorAll("[data-audio-card] audio"));

  state.cardAudios.forEach((audio) => {
    const card = audio.closest("[data-audio-card]");
    const label = card?.dataset.audioLabel || t("voiceSample");
    applyAudioVolume(audio);
    audio.removeAttribute("controls");

    if (!card || audio.nextElementSibling?.classList.contains("player")) {
      return;
    }

    const controls = document.createElement("div");
    controls.className = "player";
    controls.innerHTML = `
      <button class="progress-button" type="button" aria-label="${escapeHtml(t("seekSample"))}">
        <span class="progress-track" aria-hidden="true">
          <span class="progress-fill"></span>
          <span class="progress-knob"></span>
        </span>
      </button>
      <span class="duration">0:00</span>
    `;
    audio.insertAdjacentElement("afterend", controls);

    const progressButton = controls.querySelector(".progress-button");
    const progressFill = controls.querySelector(".progress-fill");
    const progressKnob = controls.querySelector(".progress-knob");
    const duration = controls.querySelector(".duration");

    function setProgress(value) {
      const progress = Math.max(0, Math.min(100, value));
      progressFill.style.width = `${progress}%`;
      progressKnob.style.left = `${progress}%`;
    }

    function seekToPosition(event) {
      if (!Number.isFinite(audio.duration) || audio.duration <= 0) {
        return;
      }
      const rect = progressButton.getBoundingClientRect();
      const position = (event.clientX - rect.left) / rect.width;
      const progress = Math.max(0, Math.min(1, position));
      audio.currentTime = progress * audio.duration;
      setProgress(progress * 100);
    }

    function togglePlayback() {
      if (audio.paused) {
        state.introAudio.pause();
        pauseCards(audio);
        audio.play();
      } else {
        audio.pause();
      }
    }

    card.setAttribute("role", "button");
    card.setAttribute("tabindex", "0");
    card.setAttribute("aria-label", t("playLabel", { label }));

    card.addEventListener("click", togglePlayback);
    card.addEventListener("keydown", (event) => {
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        togglePlayback();
      }
    });

    progressButton.addEventListener("click", (event) => {
      event.stopPropagation();
      seekToPosition(event);
    });

    progressButton.addEventListener("pointerdown", (event) => {
      event.preventDefault();
      event.stopPropagation();
      progressButton.setPointerCapture(event.pointerId);
      seekToPosition(event);
    });

    progressButton.addEventListener("pointermove", (event) => {
      if (progressButton.hasPointerCapture(event.pointerId)) {
        event.preventDefault();
        event.stopPropagation();
        seekToPosition(event);
      }
    });

    progressButton.addEventListener("pointerup", (event) => {
      event.preventDefault();
      event.stopPropagation();
      if (progressButton.hasPointerCapture(event.pointerId)) {
        progressButton.releasePointerCapture(event.pointerId);
      }
    });

    progressButton.addEventListener("pointercancel", (event) => {
      if (progressButton.hasPointerCapture(event.pointerId)) {
        progressButton.releasePointerCapture(event.pointerId);
      }
    });

    audio.addEventListener("loadedmetadata", () => {
      duration.textContent = `0:00 / ${formatTime(audio.duration)}`;
    });

    audio.addEventListener("timeupdate", () => {
      if (Number.isFinite(audio.duration) && audio.duration > 0) {
        setProgress((audio.currentTime / audio.duration) * 100);
        duration.textContent = `${formatTime(audio.currentTime)} / ${formatTime(audio.duration)}`;
      }
    });

    audio.addEventListener("play", () => {
      clearCurrentCard();
      state.currentCard = card;
      card.classList.add("is-playing");
      card.setAttribute("aria-current", "true");
      card.setAttribute("aria-label", t("pauseLabel", { label }));
      setNowPlaying(label);
    });

    audio.addEventListener("pause", () => {
      card.classList.remove("is-playing");
      card.removeAttribute("aria-current");
      card.setAttribute("aria-label", t("playLabel", { label }));
      if (state.currentCard === card) {
        state.currentCard = null;
      }
    });

    audio.addEventListener("ended", () => {
      setProgress(0);
      card.classList.remove("is-playing");
      card.removeAttribute("aria-current");
      card.setAttribute("aria-label", t("playLabel", { label }));
      setNowPlaying(t("ready"));
    });
  });

  updateVolumeControl();
}

function initExamples() {
  const status = document.querySelector("[data-load-status]");
  try {
    if (!window.EXAMPLE_MANIFEST) {
      throw new Error("embedded example data is missing");
    }
    state.manifest = window.EXAMPLE_MANIFEST;
    if (status) {
      status.textContent = t("languagesLoaded", { count: state.manifest.languages.length });
    }
    initVolumeControl();
    renderLanguageButtons();
    const params = new URLSearchParams(window.location.search);
    let storedSlug = "";
    try {
      storedSlug = localStorage.getItem(LANGUAGE_STORAGE_KEY) || "";
    } catch {
      storedSlug = "";
    }
    const requestedLocale = String(params.get("lang") || "").toLowerCase();
    const requestedSlug = LANGUAGE_CODE_TO_SLUG[requestedLocale] || params.get("language") || storedSlug;
    const initialSlug = state.manifest.languages.some((item) => item.slug === requestedSlug)
      ? requestedSlug
      : "english";
    chooseLanguage(initialSlug, false, EXAMPLE_I18N[requestedLocale] ? requestedLocale : null);
  } catch (error) {
    if (status) {
      status.textContent = t("unavailable", { error: error.message });
    }
  }
}

state.introAudio.addEventListener("ended", () => setNowPlaying(t("ready")));
initExamples();
