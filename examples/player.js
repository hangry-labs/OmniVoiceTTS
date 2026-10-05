const state = {
  cardAudios: [],
  currentCard: null,
  introAudio: new Audio(),
  manifest: null,
  selected: null,
  volume: 0.85,
  lastVolume: 0.85,
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
  return parts.length ? parts.join(" / ") : "voice sample";
}

function setNowPlaying(label) {
  const target = document.querySelector("[data-now-playing]");
  if (target) {
    target.textContent = label || "Ready";
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
    volumeButton.setAttribute("aria-label", isMuted ? "Unmute audio" : "Mute audio");
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
    setNowPlaying("Press play again if your browser blocked autoplay.");
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
        eyebrow: `Sample ${String(index + 1).padStart(2, "0")}`,
        title: sampleBadge(sample),
        description: sample.text,
        file: sample.file,
        label: `${meta.nativeName} sample ${index + 1}`,
        badge: "Play",
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
              <p>${escapeHtml(language.language)}</p>
            </div>
          </div>
          <button class="filter-button is-active" type="button" data-random-intro="${escapeHtml(language.slug)}">Play random intro</button>
      </div>

      <div class="clone-grid">
        ${renderAudioCard({
          classes: "clone-card",
          eyebrow: "Cross-language clone demo",
          title: "Same English reference voice, different language",
          description:
            "Cloned from examples/original_clone.mp3. The accent may not be perfect because the reference is English, but it demonstrates that the same voice identity can be carried across languages.",
          file: clone.file,
          label: `${meta.nativeName} cloned voice demo`,
          badge: "Clone",
        })}
      </div>

      <div class="sample-grid">
        ${randomSamples}
      </div>
    </section>
  `;

  target.querySelector("[data-random-intro]")?.addEventListener("click", () => {
    const intro = randomItem(language.intro);
    playIntro(intro.file, `${meta.nativeName} intro`);
  });

  enhanceAudioCards(target);
}

function chooseLanguage(slug, autoplayIntro = true) {
  const language = state.manifest.languages.find((item) => item.slug === slug);
  if (!language) {
    return;
  }

  state.selected = language;
  document.documentElement.lang = Object.entries(LANGUAGE_CODE_TO_SLUG).find(([, value]) => value === slug)?.[0] || "en";
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
    playIntro(intro.file, `${metaFor(language).nativeName} intro`);
  } else {
    setNowPlaying("Ready");
  }
}

function enhanceAudioCards(container) {
  state.cardAudios = Array.from(container.querySelectorAll("[data-audio-card] audio"));

  state.cardAudios.forEach((audio) => {
    const card = audio.closest("[data-audio-card]");
    const label = card?.dataset.audioLabel || "voice sample";
    applyAudioVolume(audio);
    audio.removeAttribute("controls");

    if (!card || audio.nextElementSibling?.classList.contains("player")) {
      return;
    }

    const controls = document.createElement("div");
    controls.className = "player";
    controls.innerHTML = `
      <button class="progress-button" type="button" aria-label="Seek sample">
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
    card.setAttribute("aria-label", `Play ${label}`);

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
      card.setAttribute("aria-label", `Pause ${label}`);
      setNowPlaying(label);
    });

    audio.addEventListener("pause", () => {
      card.classList.remove("is-playing");
      card.removeAttribute("aria-current");
      card.setAttribute("aria-label", `Play ${label}`);
      if (state.currentCard === card) {
        state.currentCard = null;
      }
    });

    audio.addEventListener("ended", () => {
      setProgress(0);
      card.classList.remove("is-playing");
      card.removeAttribute("aria-current");
      card.setAttribute("aria-label", `Play ${label}`);
      setNowPlaying("Ready");
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
      status.textContent = `${state.manifest.languages.length} languages loaded`;
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
    const requestedSlug = LANGUAGE_CODE_TO_SLUG[params.get("lang")] || params.get("language") || storedSlug;
    const initialSlug = state.manifest.languages.some((item) => item.slug === requestedSlug)
      ? requestedSlug
      : "english";
    chooseLanguage(initialSlug, false);
  } catch (error) {
    if (status) {
      status.textContent = `Examples unavailable: ${error.message}`;
    }
  }
}

state.introAudio.addEventListener("ended", () => setNowPlaying("Ready"));
initExamples();
