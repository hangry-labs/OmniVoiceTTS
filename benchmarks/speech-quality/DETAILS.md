# OmniVoiceTTS Speech Quality Benchmark Details

## Purpose And Limits

This benchmark does **not** measure absolute TTS accuracy, pronunciation quality, or human intelligibility. Qwen3-ASR is an automated, imperfect judge: a transcript mismatch may be an ASR recognition error even when the generated speech is correct and clearly understandable.

The results establish a repeatable baseline for detecting correlated movement between OmniVoiceTTS versions. Compare runs made with the same audio inputs, seeds, TTS configuration, ASR model, normalization rules, and runtime environment. A repeatable decline or improvement may indicate a TTS change, but the result is also dependent on the fixed ASR judge and must be investigated by listening to the retained audio. A score change is not, by itself, proof of a TTS regression or improvement, and a high score is not a substitute for human listening tests.

The current workload is intentionally narrow and provisional. Every generated language uses the same English reference recording, `examples/original_clone.mp3`, through its byte-identical packaged runtime copy. It therefore measures one fixed cross-language cloned voice rather than the full quality of OmniVoiceTTS. It does not currently cover random voices, voice design, multiple speakers, or native-language reference recordings. Those tracks may be added later; until then, the existing measurements remain useful only as a stable like-for-like degradation baseline.

This limitation has been verified directly with `polish_random_01`: human listening found the generated sentence correct, while Qwen3-ASR 0.6B consistently mistranscribed words. Qwen3-ASR 1.7B corrected one of those words but still mistranscribed another, and adding trailing silence did not change either model's result.

Each official run appends per-language results, every request error, warmup observations, every sentence with an ASR mismatch or repeat inconsistency, and the ten hardest ASR-judged calls. The complete per-call evidence is retained in `runs.json`; non-exact and failed audio is retained locally under `.ai/benchmark-speech-quality/` for listening and is intentionally not committed.

The runner has two non-overlapping phases. It first generates and temporarily stages every WAV while recording TTS timing and diagnostics. It then warms Qwen3-ASR with the localized warmup set, records the ASR baseline, transcribes the measured set, performs one final keepalive transcription, and records the ASR endpoint. Temporary passing WAVs are removed when the run ends.

The runner excludes manifest languages unsupported by the active Qwen3-ASR judge before generation. Compare runs made with the same TTS settings, Qwen model, containers, manifest, selected language count, and otherwise idle hardware.

## 06.10.2026 17:52:00 - 1.0-snapshot

- TTS build: `stable`
- ASR model: `Qwen/Qwen3-ASR-0.6B-hf`
- Workload: `20` languages, `2` sentences per language, `5` repeats
- Measured calls: `200/200` completed
- Exact normalized transcripts: `62.50%`
- Repeat-consistent sentence cases: `38/40` (`95.00%`)
- Mean normalized character similarity: `88.46%`
- Measured TTS time: `260.553s`; RTF `0.3020` (`3.31x` realtime)
- Benchmark wall time including ASR and diagnostics: `334.011s`
- TTS PyTorch peak allocated / reserved: `3714.5 MiB / 4484.0 MiB`
- Peak observed whole-device VRAM during the TTS phase: `10354 MiB` (diagnostic only; use the dedicated GPU-memory suite for clean TTS VRAM)
- ASR baseline after warmup / endpoint after final keepalive: `10566 MiB / 10572 MiB`
- Retained non-exact/error WAV files: `.ai\benchmark-speech-quality\20261006-175200` (local, git-ignored)
- Comment: v1.0-snapshot baseline; staged TTS phase followed by warmed Qwen3-ASR phase; RTX 5070 Ti

### Languages

| Language | Qwen judge | Exact | Consistent cases | Mean similarity | Avg TTS | P95 TTS | RTF | Errors |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| English | forced | 10/10 | 2/2 | 100.00% | 1.346s | 1.446s | 0.2369 | 0 |
| Chinese | forced | 10/10 | 2/2 | 100.00% | 1.270s | 1.350s | 0.2806 | 0 |
| Hindi | forced | 10/10 | 2/2 | 100.00% | 1.272s | 1.307s | 0.2752 | 0 |
| Spanish | forced | 10/10 | 2/2 | 100.00% | 1.298s | 1.450s | 0.2988 | 0 |
| French | forced | 5/10 | 2/2 | 99.16% | 1.357s | 1.455s | 0.2795 | 0 |
| Standard Arabic | forced | 5/10 | 1/2 | 96.74% | 1.313s | 1.402s | 0.2802 | 0 |
| Bengali | auto (unsupported) | 0/10 | 2/2 | 0.00% | 1.305s | 1.352s | 0.3274 | 0 |
| Russian | forced | 5/10 | 2/2 | 99.60% | 1.286s | 1.376s | 0.3076 | 0 |
| Portuguese | forced | 10/10 | 2/2 | 100.00% | 1.289s | 1.371s | 0.3231 | 0 |
| Urdu | auto (unsupported) | 0/10 | 2/2 | 0.00% | 1.300s | 1.435s | 0.2958 | 0 |
| Polish | forced | 5/10 | 1/2 | 97.45% | 1.315s | 1.376s | 0.3008 | 0 |
| Thai | forced | 5/10 | 2/2 | 98.35% | 1.262s | 1.313s | 0.3131 | 0 |
| Japanese | forced | 5/10 | 2/2 | 98.08% | 1.324s | 1.387s | 0.3100 | 0 |
| German | forced | 10/10 | 2/2 | 100.00% | 1.334s | 1.451s | 0.2967 | 0 |
| Indonesian | forced | 10/10 | 2/2 | 100.00% | 1.327s | 1.416s | 0.3294 | 0 |
| Turkish | forced | 0/10 | 2/2 | 90.59% | 1.299s | 1.388s | 0.3284 | 0 |
| Korean | forced | 10/10 | 2/2 | 100.00% | 1.319s | 1.452s | 0.3182 | 0 |
| Vietnamese | forced | 0/10 | 2/2 | 93.05% | 1.286s | 1.358s | 0.3562 | 0 |
| Italian | forced | 5/10 | 2/2 | 96.16% | 1.310s | 1.395s | 0.3115 | 0 |
| Dutch | forced | 10/10 | 2/2 | 100.00% | 1.245s | 1.377s | 0.3189 | 0 |

### Request Errors

No TTS or ASR request errors were recorded.

### Warmup Observations

- `chinese_clone_01_warmup` scored `99.24%`: 你好，这里是来自 Angry Labs 的 OmniVoice TTS。我们打造本地运行、简单易用的语音工具，让人们能用自己的语言私密离线地生成语音。
- `hindi_clone_01_warmup` scored `87.06%`: नमस्ते, यह Hangry Labs का अपनी वॉइस टीटीएस है। हम स्थानीय और आसानी से चलने वाले वॉइस टूल बनाते हैं, ताकि लोग अपनी भाषा में निजी और ऑफलाइन तरीके से आवाज बना सकें।
- `spanish_clone_01_warmup` scored `99.32%`: Hola, esto es OmniVoice TTS de Hungry Labs. Creamos herramientas de voz locales y fáciles de usar para que la gente pueda crear voz de forma privada, sin conexión y en su propio idioma.
- `french_clone_01_warmup` scored `99.67%`: Bonjour, ici Omnivoice TTS de Angry Labs. Nous créons des outils vocaux locaux et faciles à lancer pour que chacun puisse générer de la parole en privé, hors ligne et dans sa propre langue.
- `standard_arabic_clone_01_warmup` scored `99.12%`: مرحباً، هذا هو omnivoice tts من hungry labs. نصنع أدوات صوت محليّة وسهلة التشغيل كي يتمكن الناس من إنشاء الكلام بخصوصية ومن دون اتصال وبلغتهم.
- `bengali_clone_01_warmup` scored `0.00%`: नमस्कार, यह टी हैंग्री लैब्स और ओमनी वॉइस टीटीएस। अमृत स्थानीय भावे चालाशाहों जो भौहे स्टूल तैरी करी, जाते मानुष निजर भाषा बेक्टीगोट भावे और ऑफलाइन एस पीच तैरी करते पड़े.
- `russian_clone_01_warmup` scored `95.34%`: Здравствуйте, это OmniVoice TTS от Hangry Labs. Мы создаем локальные и простые голосовые инструменты, чтобы люди могли создавать речь приватно, offline и на своем языке.
- `portuguese_clone_01_warmup` scored `99.66%`: Olá, este é o Omni Voice TTS da Angry Labs. Criamos ferramentas de voz locais e fáceis de usar para que as pessoas possam gerar fala com privacidade, offline e em seu próprio idioma.
- `urdu_clone_01_warmup` scored `0.00%`: सलाम यह हैंग्री लैब्स का ओमनी वोइस टीटीएस है। हम मकामी और आसानी से चलने वाले वाई स्टोल बनाते हैं, ताकि लोग अपनी ज़बान में नजीर तौर पर और ऑफलाइन आवाज बना सकें।
- `polish_clone_01_warmup` scored `97.08%`: Cześć, uomni voice tts od hungry laps. Tworzymy lokalne łatwe w uruchomieniu narzędzia głosowe, żeby ludzie mogli tworzyć mowy prywatnie, offline i w własnym języku.
- `thai_clone_01_warmup` scored `93.70%`: สวัสดีนี่คือ OmniVoice TTS จาก Henry Labs เราสร้างเครื่องมือเสียงที่รันในเครื่องและใช้งานง่าย เพื่อให้ผู้คนสร้างเสียงพูดได้อย่างเป็นส่วนตัว offline และเป็นภาษาของตัวเอง
- `japanese_clone_01_warmup` scored `95.29%`: こんにちは、Hengry Loves の Omni Voices TTS です。私たちは誰でも自分の言葉で、プライベートに、オフラインで音声を作れる、ローカルで簡単に動く音声ツールを作っています。
- `german_clone_01_warmup` scored `99.67%`: Hallo, hier ist OmniVoice TTS von Angry Labs. Wir bauen lokale, einfach nutzbare Sprachwerkzeuge, damit Menschen privat, offline und in ihrer eigenen Sprache Sprache erzeugen können.
- `indonesian_clone_01_warmup` scored `99.00%`: Hello, ini Omni Voice TTS dari Hangry Labs. Kami membuat alat suara lokal yang mudah dijalankan agar orang dapat membuat ucapan secara privat, offline, dan dalam bahasa mereka sendiri.
- `turkish_clone_01_warmup` scored `96.97%`: Merhaba, bu hungry lapsen amni voice tts. İnsanların kendi dillerinde özel olarak ve çevrim dışı konuşma üretilebilmesi için yerel ve kolay çalışan ses araçları geliştiriyoruz.
- `korean_clone_01_warmup` scored `87.50%`: 안녕하세요, 행위랩스의 엄리 voice tts입니다. 우리는 사람들이 자신의 언어로 개인적으로 오프라인에서도 음성을 만들 수 있도록 로컬에서 쉽게 실행되는 음성 도구를 만듭니다.
- `dutch_clone_01_warmup` scored `98.53%`: Hallo, dit is OmniVoice TTS van Hangry Labs. We bouwen lokale voor eenvoudig te gebruiken stemtools zodat mensen privé, offline en in hun eigen taal spraak kunnen maken.

### Mismatches And Inconsistent Cases

#### french_random_02

- Expected: Le croissant était si croustillant que même le silence a fait des miettes.
- Exact repeats: `0/5`
- Repeat consistent: `yes`
- Mean / minimum similarity: `98.33% / 98.33%`
- Transcript (`5x`): Le croissant était croustillant que même le silence. A fait des miettes.

#### standard_arabic_random_01

- Expected: قلت سأعود بعد خمس دقائق، فضحكت الساعة وقالت: نعرف هذه القصة.
- Exact repeats: `0/5`
- Repeat consistent: `no`
- Mean / minimum similarity: `93.48% / 93.48%`
- Transcript (`4x`): قصد سأعود بعد خمس دقائق فضحكت ساعة وقالت نعرف هذه القصة.
- Transcript (`1x`): قُود سأعود بعد خمس دقائق فضحكت ساعة وقالت نعرف هذه القصة.

#### bengali_random_01

- Expected: আমি বললাম পাঁচ মিনিটে আসছি, আর পাঁচ মিনিট চুপচাপ এক ঘণ্টা হয়ে গেল।
- Exact repeats: `0/5`
- Repeat consistent: `yes`
- Mean / minimum similarity: `0.00% / 0.00%`
- Transcript (`5x`): Ami bolong 5 minit aksi, atau 5 minit chop chop agak hanta oleh galo.

#### bengali_random_02

- Expected: চা এত ভালো ছিল যে বিস্কুট নিজেই ডুব দিতে রাজি হয়ে গেল।
- Exact repeats: `0/5`
- Repeat consistent: `yes`
- Mean / minimum similarity: `0.00% / 0.00%`
- Transcript (`5x`): ช้า แต่ตัวพอลชิลล์จะบิสกุกดนี้เจ๊ดูดดิเทรากิโอยแก่โล

#### russian_random_01

- Expected: Я сказал, что приду через пять минут; часы посмотрели на меня с русской грустью.
- Exact repeats: `0/5`
- Repeat consistent: `yes`
- Mean / minimum similarity: `99.21% / 99.21%`
- Transcript (`5x`): Я сказал, что приду через пять минут. Часы посмотрели на меня с руской грустью.

#### urdu_random_01

- Expected: میں نے کہا پانچ منٹ میں آتا ہوں، گھڑی نے کہا یہ جملہ پہلے بھی سنا ہے۔
- Exact repeats: `0/5`
- Repeat consistent: `yes`
- Mean / minimum similarity: `0.00% / 0.00%`
- Transcript (`5x`): मैंने कहा पाँच मिनट में आता हूँ। घड़ी ने कहा ये जुमला पहले भी सुना है।

#### urdu_random_02

- Expected: چائے اتنی اچھی تھی کہ بسکٹ نے خود ہی ڈبکی لگا دی۔
- Exact repeats: `0/5`
- Repeat consistent: `yes`
- Mean / minimum similarity: `0.00% / 0.00%`
- Transcript (`5x`): चाय इतनी अच्छी थी कि बेस्टकेट ने खुद ही डब्बी लगा दी

#### polish_random_01

- Expected: Powiedziałem, że będę za pięć minut; zegarek tylko spojrzał po polsku i westchnął.
- Exact repeats: `0/5`
- Repeat consistent: `no`
- Mean / minimum similarity: `94.89% / 94.57%`
- Transcript (`4x`): Powiedziałem, że będę za pięć minut. Zegarek tylko spojł po Polsku i wstgnął.
- Transcript (`1x`): Powiedziałem, że będę za pięć minut. Zegar ektyko spojrzał po Polsku i wstgnął.

#### thai_random_01

- Expected: บอกว่าจะถึงในห้านาที แต่นาฬิกาหันมามองเหมือนรู้ความจริงแล้ว
- Exact repeats: `0/5`
- Repeat consistent: `yes`
- Mean / minimum similarity: `96.70% / 96.70%`
- Transcript (`5x`): บอกว่าจะถึงใน 5 นาที แต่นาฬิกาหันมามอง เหมือนรู้ความจริงแล้ว

#### japanese_random_01

- Expected: 五分で行きますと言ったら、時計が静かに首をかしげました。
- Exact repeats: `0/5`
- Repeat consistent: `yes`
- Mean / minimum similarity: `96.15% / 96.15%`
- Transcript (`5x`): 5分で行きますと言ったら、時計が静かに首をかしげました。

#### turkish_random_01

- Expected: Beş dakikaya geliyorum dedim; saat bana Türk kahvesi falı gibi baktı.
- Exact repeats: `0/5`
- Repeat consistent: `yes`
- Mean / minimum similarity: `92.86% / 92.86%`
- Transcript (`5x`): 5 dakikaya geliyorum dedim. Saat bana Türk kahve sıfali gibi baktı.

#### turkish_random_02

- Expected: Kahve o kadar güçlüydü ki, neredeyse benim yerime toplantıya girecekti.
- Exact repeats: `0/5`
- Repeat consistent: `yes`
- Mean / minimum similarity: `88.33% / 88.33%`
- Transcript (`5x`): KV o kadar güçlüydü ki neredeyse benim yerime dopantiyaya girecek tete.

#### vietnamese_random_01

- Expected: Tôi nói năm phút nữa tới, cái đồng hồ nghe xong im lặng rất sâu.
- Exact repeats: `0/5`
- Repeat consistent: `yes`
- Mean / minimum similarity: `97.92% / 97.92%`
- Transcript (`5x`): Tôi nói năm phút nữa tới, cái đồng hồ nghe xong im lặng rất sầu.

#### vietnamese_random_02

- Expected: Ly cà phê sáng nay mạnh đến mức suýt trả lời email thay tôi.
- Exact repeats: `0/5`
- Repeat consistent: `yes`
- Mean / minimum similarity: `88.17% / 88.17%`
- Transcript (`5x`): Lịch café sáng nay, mạnh đến mức suýt trả lời email thay tội.

#### italian_random_02

- Expected: Il caffè era così forte che quasi ha parlato al posto mio.
- Exact repeats: `0/5`
- Repeat consistent: `yes`
- Mean / minimum similarity: `92.31% / 92.31%`
- Transcript (`5x`): Il caffè era così forte che quasi appariva al posto mio.


### Hardest ASR-Judged Calls

- `bengali_random_01_r1` - `0.00%` - expected: আমি বললাম পাঁচ মিনিটে আসছি, আর পাঁচ মিনিট চুপচাপ এক ঘণ্টা হয়ে গেল। - transcript: Ami bolong 5 minit aksi, atau 5 minit chop chop agak hanta oleh galo.
- `bengali_random_01_r2` - `0.00%` - expected: আমি বললাম পাঁচ মিনিটে আসছি, আর পাঁচ মিনিট চুপচাপ এক ঘণ্টা হয়ে গেল। - transcript: Ami bolong 5 minit aksi, atau 5 minit chop chop agak hanta oleh galo.
- `bengali_random_01_r3` - `0.00%` - expected: আমি বললাম পাঁচ মিনিটে আসছি, আর পাঁচ মিনিট চুপচাপ এক ঘণ্টা হয়ে গেল। - transcript: Ami bolong 5 minit aksi, atau 5 minit chop chop agak hanta oleh galo.
- `bengali_random_01_r4` - `0.00%` - expected: আমি বললাম পাঁচ মিনিটে আসছি, আর পাঁচ মিনিট চুপচাপ এক ঘণ্টা হয়ে গেল। - transcript: Ami bolong 5 minit aksi, atau 5 minit chop chop agak hanta oleh galo.
- `bengali_random_01_r5` - `0.00%` - expected: আমি বললাম পাঁচ মিনিটে আসছি, আর পাঁচ মিনিট চুপচাপ এক ঘণ্টা হয়ে গেল। - transcript: Ami bolong 5 minit aksi, atau 5 minit chop chop agak hanta oleh galo.
- `bengali_random_02_r1` - `0.00%` - expected: চা এত ভালো ছিল যে বিস্কুট নিজেই ডুব দিতে রাজি হয়ে গেল। - transcript: ช้า แต่ตัวพอลชิลล์จะบิสกุกดนี้เจ๊ดูดดิเทรากิโอยแก่โล
- `bengali_random_02_r2` - `0.00%` - expected: চা এত ভালো ছিল যে বিস্কুট নিজেই ডুব দিতে রাজি হয়ে গেল। - transcript: ช้า แต่ตัวพอลชิลล์จะบิสกุกดนี้เจ๊ดูดดิเทรากิโอยแก่โล
- `bengali_random_02_r3` - `0.00%` - expected: চা এত ভালো ছিল যে বিস্কুট নিজেই ডুব দিতে রাজি হয়ে গেল। - transcript: ช้า แต่ตัวพอลชิลล์จะบิสกุกดนี้เจ๊ดูดดิเทรากิโอยแก่โล
- `bengali_random_02_r4` - `0.00%` - expected: চা এত ভালো ছিল যে বিস্কুট নিজেই ডুব দিতে রাজি হয়ে গেল। - transcript: ช้า แต่ตัวพอลชิลล์จะบิสกุกดนี้เจ๊ดูดดิเทรากิโอยแก่โล
- `bengali_random_02_r5` - `0.00%` - expected: চা এত ভালো ছিল যে বিস্কুট নিজেই ডুব দিতে রাজি হয়ে গেল। - transcript: ช้า แต่ตัวพอลชิลล์จะบิสกุกดนี้เจ๊ดูดดิเทรากิโอยแก่โล

## 06.10.2026 18:27:34 - 1.0-snapshot

- TTS build: `stable`
- ASR model: `Qwen/Qwen3-ASR-0.6B-hf`
- Workload: `18` languages, `2` sentences per language, `5` repeats
- Measured calls: `180/180` completed
- Exact normalized transcripts: `69.44%`
- Repeat-consistent sentence cases: `34/36` (`94.44%`)
- Mean normalized character similarity: `98.29%`
- Measured TTS time: `235.685s`; RTF `0.3026` (`3.31x` realtime)
- Benchmark wall time including ASR and diagnostics: `306.830s`
- TTS PyTorch peak allocated / reserved: `3379.2 MiB / 3798.0 MiB`
- Peak observed whole-device VRAM during the TTS phase: `9700 MiB` (diagnostic only; use the dedicated GPU-memory suite for clean TTS VRAM)
- ASR baseline after warmup / endpoint after final keepalive: `9918 MiB / 9918 MiB`
- Retained non-exact/error WAV files: `.ai\benchmark-speech-quality\20261006-182734` (local, git-ignored)
- Comment: v1.0-snapshot canonical supported-language repeat; staged TTS then warmed Qwen3-ASR; RTX 5070 Ti

### Languages

| Language | Qwen judge | Exact | Consistent cases | Mean similarity | Avg TTS | P95 TTS | RTF | Errors |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| English | forced | 10/10 | 2/2 | 100.00% | 1.326s | 1.411s | 0.2335 | 0 |
| Chinese | forced | 10/10 | 2/2 | 100.00% | 1.315s | 1.401s | 0.2906 | 0 |
| Hindi | forced | 10/10 | 2/2 | 100.00% | 1.286s | 1.323s | 0.2784 | 0 |
| Spanish | forced | 10/10 | 2/2 | 100.00% | 1.285s | 1.378s | 0.2957 | 0 |
| French | forced | 5/10 | 2/2 | 99.16% | 1.301s | 1.415s | 0.2681 | 0 |
| Standard Arabic | forced | 5/10 | 1/2 | 96.74% | 1.334s | 1.425s | 0.2847 | 0 |
| Russian | forced | 5/10 | 2/2 | 99.60% | 1.277s | 1.336s | 0.3056 | 0 |
| Portuguese | forced | 10/10 | 2/2 | 100.00% | 1.325s | 1.375s | 0.3320 | 0 |
| Polish | forced | 5/10 | 1/2 | 97.45% | 1.321s | 1.460s | 0.3024 | 0 |
| Thai | forced | 5/10 | 2/2 | 98.35% | 1.313s | 1.454s | 0.3259 | 0 |
| Japanese | forced | 5/10 | 2/2 | 98.08% | 1.366s | 1.486s | 0.3198 | 0 |
| German | forced | 10/10 | 2/2 | 100.00% | 1.311s | 1.560s | 0.2916 | 0 |
| Indonesian | forced | 10/10 | 2/2 | 100.00% | 1.310s | 1.373s | 0.3250 | 0 |
| Turkish | forced | 0/10 | 2/2 | 90.59% | 1.295s | 1.362s | 0.3275 | 0 |
| Korean | forced | 10/10 | 2/2 | 100.00% | 1.360s | 1.471s | 0.3280 | 0 |
| Vietnamese | forced | 0/10 | 2/2 | 93.05% | 1.303s | 1.350s | 0.3609 | 0 |
| Italian | forced | 5/10 | 2/2 | 96.16% | 1.300s | 1.409s | 0.3091 | 0 |
| Dutch | forced | 10/10 | 2/2 | 100.00% | 1.241s | 1.350s | 0.3177 | 0 |

### Request Errors

No TTS or ASR request errors were recorded.

### Warmup Observations

- `chinese_clone_01_warmup` scored `99.24%`: 你好，这里是来自 Angry Labs 的 OmniVoice TTS。我们打造本地运行、简单易用的语音工具，让人们能用自己的语言私密离线地生成语音。
- `hindi_clone_01_warmup` scored `87.06%`: नमस्ते, यह Hangry Labs का अपनी वॉइस टीटीएस है। हम स्थानीय और आसानी से चलने वाले वॉइस टूल बनाते हैं, ताकि लोग अपनी भाषा में निजी और ऑफलाइन तरीके से आवाज बना सकें।
- `spanish_clone_01_warmup` scored `99.32%`: Hola, esto es OmniVoice TTS de Hungry Labs. Creamos herramientas de voz locales y fáciles de usar para que la gente pueda crear voz de forma privada, sin conexión y en su propio idioma.
- `french_clone_01_warmup` scored `99.67%`: Bonjour, ici Omnivoice TTS de Angry Labs. Nous créons des outils vocaux locaux et faciles à lancer pour que chacun puisse générer de la parole en privé, hors ligne et dans sa propre langue.
- `standard_arabic_clone_01_warmup` scored `99.12%`: مرحباً، هذا هو omnivoice tts من hungry labs. نصنع أدوات صوت محليّة وسهلة التشغيل كي يتمكن الناس من إنشاء الكلام بخصوصية ومن دون اتصال وبلغتهم.
- `russian_clone_01_warmup` scored `95.34%`: Здравствуйте, это OmniVoice TTS от Hangry Labs. Мы создаем локальные и простые голосовые инструменты, чтобы люди могли создавать речь приватно, offline и на своем языке.
- `portuguese_clone_01_warmup` scored `99.66%`: Olá, este é o Omni Voice TTS da Angry Labs. Criamos ferramentas de voz locais e fáceis de usar para que as pessoas possam gerar fala com privacidade, offline e em seu próprio idioma.
- `polish_clone_01_warmup` scored `97.08%`: Cześć, uomni voice tts od hungry laps. Tworzymy lokalne łatwe w uruchomieniu narzędzia głosowe, żeby ludzie mogli tworzyć mowy prywatnie, offline i w własnym języku.
- `thai_clone_01_warmup` scored `93.70%`: สวัสดีนี่คือ OmniVoice TTS จาก Henry Labs เราสร้างเครื่องมือเสียงที่รันในเครื่องและใช้งานง่าย เพื่อให้ผู้คนสร้างเสียงพูดได้อย่างเป็นส่วนตัว offline และเป็นภาษาของตัวเอง
- `japanese_clone_01_warmup` scored `95.29%`: こんにちは、Hengry Loves の Omni Voices TTS です。私たちは誰でも自分の言葉で、プライベートに、オフラインで音声を作れる、ローカルで簡単に動く音声ツールを作っています。
- `german_clone_01_warmup` scored `99.67%`: Hallo, hier ist OmniVoice TTS von Angry Labs. Wir bauen lokale, einfach nutzbare Sprachwerkzeuge, damit Menschen privat, offline und in ihrer eigenen Sprache Sprache erzeugen können.
- `indonesian_clone_01_warmup` scored `99.00%`: Hello, ini Omni Voice TTS dari Hangry Labs. Kami membuat alat suara lokal yang mudah dijalankan agar orang dapat membuat ucapan secara privat, offline, dan dalam bahasa mereka sendiri.
- `turkish_clone_01_warmup` scored `96.97%`: Merhaba, bu hungry lapsen amni voice tts. İnsanların kendi dillerinde özel olarak ve çevrim dışı konuşma üretilebilmesi için yerel ve kolay çalışan ses araçları geliştiriyoruz.
- `korean_clone_01_warmup` scored `87.50%`: 안녕하세요, 행위랩스의 엄리 voice tts입니다. 우리는 사람들이 자신의 언어로 개인적으로 오프라인에서도 음성을 만들 수 있도록 로컬에서 쉽게 실행되는 음성 도구를 만듭니다.
- `dutch_clone_01_warmup` scored `98.53%`: Hallo, dit is OmniVoice TTS van Hangry Labs. We bouwen lokale voor eenvoudig te gebruiken stemtools zodat mensen privé, offline en in hun eigen taal spraak kunnen maken.

### Mismatches And Inconsistent Cases

#### french_random_02

- Expected: Le croissant était si croustillant que même le silence a fait des miettes.
- Exact repeats: `0/5`
- Repeat consistent: `yes`
- Mean / minimum similarity: `98.33% / 98.33%`
- Transcript (`5x`): Le croissant était croustillant que même le silence. A fait des miettes.

#### standard_arabic_random_01

- Expected: قلت سأعود بعد خمس دقائق، فضحكت الساعة وقالت: نعرف هذه القصة.
- Exact repeats: `0/5`
- Repeat consistent: `no`
- Mean / minimum similarity: `93.48% / 93.48%`
- Transcript (`4x`): قصد سأعود بعد خمس دقائق فضحكت ساعة وقالت نعرف هذه القصة.
- Transcript (`1x`): قُود سأعود بعد خمس دقائق فضحكت ساعة وقالت نعرف هذه القصة.

#### russian_random_01

- Expected: Я сказал, что приду через пять минут; часы посмотрели на меня с русской грустью.
- Exact repeats: `0/5`
- Repeat consistent: `yes`
- Mean / minimum similarity: `99.21% / 99.21%`
- Transcript (`5x`): Я сказал, что приду через пять минут. Часы посмотрели на меня с руской грустью.

#### polish_random_01

- Expected: Powiedziałem, że będę za pięć minut; zegarek tylko spojrzał po polsku i westchnął.
- Exact repeats: `0/5`
- Repeat consistent: `no`
- Mean / minimum similarity: `94.89% / 94.57%`
- Transcript (`4x`): Powiedziałem, że będę za pięć minut. Zegarek tylko spojł po Polsku i wstgnął.
- Transcript (`1x`): Powiedziałem, że będę za pięć minut. Zegar ektyko spojrzał po Polsku i wstgnął.

#### thai_random_01

- Expected: บอกว่าจะถึงในห้านาที แต่นาฬิกาหันมามองเหมือนรู้ความจริงแล้ว
- Exact repeats: `0/5`
- Repeat consistent: `yes`
- Mean / minimum similarity: `96.70% / 96.70%`
- Transcript (`5x`): บอกว่าจะถึงใน 5 นาที แต่นาฬิกาหันมามอง เหมือนรู้ความจริงแล้ว

#### japanese_random_01

- Expected: 五分で行きますと言ったら、時計が静かに首をかしげました。
- Exact repeats: `0/5`
- Repeat consistent: `yes`
- Mean / minimum similarity: `96.15% / 96.15%`
- Transcript (`5x`): 5分で行きますと言ったら、時計が静かに首をかしげました。

#### turkish_random_01

- Expected: Beş dakikaya geliyorum dedim; saat bana Türk kahvesi falı gibi baktı.
- Exact repeats: `0/5`
- Repeat consistent: `yes`
- Mean / minimum similarity: `92.86% / 92.86%`
- Transcript (`5x`): 5 dakikaya geliyorum dedim. Saat bana Türk kahve sıfali gibi baktı.

#### turkish_random_02

- Expected: Kahve o kadar güçlüydü ki, neredeyse benim yerime toplantıya girecekti.
- Exact repeats: `0/5`
- Repeat consistent: `yes`
- Mean / minimum similarity: `88.33% / 88.33%`
- Transcript (`5x`): KV o kadar güçlüydü ki neredeyse benim yerime dopantiyaya girecek tete.

#### vietnamese_random_01

- Expected: Tôi nói năm phút nữa tới, cái đồng hồ nghe xong im lặng rất sâu.
- Exact repeats: `0/5`
- Repeat consistent: `yes`
- Mean / minimum similarity: `97.92% / 97.92%`
- Transcript (`5x`): Tôi nói năm phút nữa tới, cái đồng hồ nghe xong im lặng rất sầu.

#### vietnamese_random_02

- Expected: Ly cà phê sáng nay mạnh đến mức suýt trả lời email thay tôi.
- Exact repeats: `0/5`
- Repeat consistent: `yes`
- Mean / minimum similarity: `88.17% / 88.17%`
- Transcript (`5x`): Lịch café sáng nay, mạnh đến mức suýt trả lời email thay tội.

#### italian_random_02

- Expected: Il caffè era così forte che quasi ha parlato al posto mio.
- Exact repeats: `0/5`
- Repeat consistent: `yes`
- Mean / minimum similarity: `92.31% / 92.31%`
- Transcript (`5x`): Il caffè era così forte che quasi appariva al posto mio.


### Hardest ASR-Judged Calls

- `vietnamese_random_02_r1` - `88.17%` - expected: Ly cà phê sáng nay mạnh đến mức suýt trả lời email thay tôi. - transcript: Lịch café sáng nay, mạnh đến mức suýt trả lời email thay tội.
- `vietnamese_random_02_r2` - `88.17%` - expected: Ly cà phê sáng nay mạnh đến mức suýt trả lời email thay tôi. - transcript: Lịch café sáng nay, mạnh đến mức suýt trả lời email thay tội.
- `vietnamese_random_02_r3` - `88.17%` - expected: Ly cà phê sáng nay mạnh đến mức suýt trả lời email thay tôi. - transcript: Lịch café sáng nay, mạnh đến mức suýt trả lời email thay tội.
- `vietnamese_random_02_r4` - `88.17%` - expected: Ly cà phê sáng nay mạnh đến mức suýt trả lời email thay tôi. - transcript: Lịch café sáng nay, mạnh đến mức suýt trả lời email thay tội.
- `vietnamese_random_02_r5` - `88.17%` - expected: Ly cà phê sáng nay mạnh đến mức suýt trả lời email thay tôi. - transcript: Lịch café sáng nay, mạnh đến mức suýt trả lời email thay tội.
- `turkish_random_02_r1` - `88.33%` - expected: Kahve o kadar güçlüydü ki, neredeyse benim yerime toplantıya girecekti. - transcript: KV o kadar güçlüydü ki neredeyse benim yerime dopantiyaya girecek tete.
- `turkish_random_02_r2` - `88.33%` - expected: Kahve o kadar güçlüydü ki, neredeyse benim yerime toplantıya girecekti. - transcript: KV o kadar güçlüydü ki neredeyse benim yerime dopantiyaya girecek tete.
- `turkish_random_02_r3` - `88.33%` - expected: Kahve o kadar güçlüydü ki, neredeyse benim yerime toplantıya girecekti. - transcript: KV o kadar güçlüydü ki neredeyse benim yerime dopantiyaya girecek tete.
- `turkish_random_02_r4` - `88.33%` - expected: Kahve o kadar güçlüydü ki, neredeyse benim yerime toplantıya girecekti. - transcript: KV o kadar güçlüydü ki neredeyse benim yerime dopantiyaya girecek tete.
- `turkish_random_02_r5` - `88.33%` - expected: Kahve o kadar güçlüydü ki, neredeyse benim yerime toplantıya girecekti. - transcript: KV o kadar güçlüydü ki neredeyse benim yerime dopantiyaya girecek tete.

## 06.10.2026 18:40:59 - 1.0-snapshot

- TTS build: `stable`
- ASR model: `Qwen/Qwen3-ASR-0.6B-hf`
- Workload: `18` languages, `2` sentences per language, `5` repeats
- Measured calls: `180/180` completed
- Exact normalized transcripts: `69.44%`
- Repeat-consistent sentence cases: `36/36` (`100.00%`)
- Mean normalized character similarity: `98.28%`
- Measured TTS time: `229.603s`; RTF `0.2948` (`3.39x` realtime)
- Benchmark wall time including ASR and diagnostics: `291.456s`
- TTS PyTorch peak allocated / reserved: `2167.3 MiB / 2760.0 MiB`
- Peak observed whole-device VRAM during the TTS phase: `8829 MiB` (diagnostic only; use the dedicated GPU-memory suite for clean TTS VRAM)
- ASR baseline after warmup / endpoint after final keepalive: `8829 MiB / 8829 MiB`
- Retained non-exact/error WAV files: `.ai\benchmark-speech-quality\20261006-184059` (local, git-ignored)
- Comment: v1.0-snapshot canonical supported-language repeat 2; staged TTS then warmed Qwen3-ASR; RTX 5070 Ti

### Languages

| Language | Qwen judge | Exact | Consistent cases | Mean similarity | Avg TTS | P95 TTS | RTF | Errors |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| English | forced | 10/10 | 2/2 | 100.00% | 1.326s | 1.404s | 0.2334 | 0 |
| Chinese | forced | 10/10 | 2/2 | 100.00% | 1.247s | 1.334s | 0.2756 | 0 |
| Hindi | forced | 10/10 | 2/2 | 100.00% | 1.272s | 1.425s | 0.2754 | 0 |
| Spanish | forced | 10/10 | 2/2 | 100.00% | 1.263s | 1.340s | 0.2907 | 0 |
| French | forced | 5/10 | 2/2 | 99.16% | 1.274s | 1.338s | 0.2624 | 0 |
| Standard Arabic | forced | 5/10 | 2/2 | 96.74% | 1.281s | 1.331s | 0.2734 | 0 |
| Russian | forced | 5/10 | 2/2 | 99.60% | 1.238s | 1.326s | 0.2962 | 0 |
| Portuguese | forced | 10/10 | 2/2 | 100.00% | 1.274s | 1.343s | 0.3192 | 0 |
| Polish | forced | 5/10 | 2/2 | 97.28% | 1.288s | 1.332s | 0.2948 | 0 |
| Thai | forced | 5/10 | 2/2 | 98.35% | 1.233s | 1.287s | 0.3061 | 0 |
| Japanese | forced | 5/10 | 2/2 | 98.08% | 1.280s | 1.335s | 0.2996 | 0 |
| German | forced | 10/10 | 2/2 | 100.00% | 1.250s | 1.329s | 0.2781 | 0 |
| Indonesian | forced | 10/10 | 2/2 | 100.00% | 1.290s | 1.396s | 0.3200 | 0 |
| Turkish | forced | 0/10 | 2/2 | 90.59% | 1.264s | 1.357s | 0.3197 | 0 |
| Korean | forced | 10/10 | 2/2 | 100.00% | 1.287s | 1.345s | 0.3104 | 0 |
| Vietnamese | forced | 0/10 | 2/2 | 93.05% | 1.319s | 1.467s | 0.3653 | 0 |
| Italian | forced | 5/10 | 2/2 | 96.16% | 1.292s | 1.451s | 0.3071 | 0 |
| Dutch | forced | 10/10 | 2/2 | 100.00% | 1.284s | 1.479s | 0.3287 | 0 |

### Request Errors

No TTS or ASR request errors were recorded.

### Warmup Observations

- `chinese_clone_01_warmup` scored `99.24%`: 你好，这里是来自 Angry Labs 的 OmniVoice TTS。我们打造本地运行、简单易用的语音工具，让人们能用自己的语言私密离线地生成语音。
- `hindi_clone_01_warmup` scored `87.06%`: नमस्ते, यह Hangry Labs का अपनी वॉइस टीटीएस है। हम स्थानीय और आसानी से चलने वाले वॉइस टूल बनाते हैं, ताकि लोग अपनी भाषा में निजी और ऑफलाइन तरीके से आवाज बना सकें।
- `spanish_clone_01_warmup` scored `99.32%`: Hola, esto es OmniVoice TTS de Hungry Labs. Creamos herramientas de voz locales y fáciles de usar para que la gente pueda crear voz de forma privada, sin conexión y en su propio idioma.
- `french_clone_01_warmup` scored `99.67%`: Bonjour, ici Omnivoice TTS de Angry Labs. Nous créons des outils vocaux locaux et faciles à lancer pour que chacun puisse générer de la parole en privé, hors ligne et dans sa propre langue.
- `standard_arabic_clone_01_warmup` scored `99.12%`: مرحباً، هذا هو omnivoice tts من hungry labs. نصنع أدوات صوت محليّة وسهلة التشغيل كي يتمكن الناس من إنشاء الكلام بخصوصية ومن دون اتصال وبلغتهم.
- `russian_clone_01_warmup` scored `95.34%`: Здравствуйте, это OmniVoice TTS от Hangry Labs. Мы создаем локальные и простые голосовые инструменты, чтобы люди могли создавать речь приватно, offline и на своем языке.
- `portuguese_clone_01_warmup` scored `99.66%`: Olá, este é o Omni Voice TTS da Angry Labs. Criamos ferramentas de voz locais e fáceis de usar para que as pessoas possam gerar fala com privacidade, offline e em seu próprio idioma.
- `polish_clone_01_warmup` scored `97.08%`: Cześć, uomni voice tts od hungry laps. Tworzymy lokalne łatwe w uruchomieniu narzędzia głosowe, żeby ludzie mogli tworzyć mowy prywatnie, offline i w własnym języku.
- `thai_clone_01_warmup` scored `93.70%`: สวัสดีนี่คือ OmniVoice TTS จาก Henry Labs เราสร้างเครื่องมือเสียงที่รันในเครื่องและใช้งานง่าย เพื่อให้ผู้คนสร้างเสียงพูดได้อย่างเป็นส่วนตัว offline และเป็นภาษาของตัวเอง
- `japanese_clone_01_warmup` scored `95.29%`: こんにちは、Hengry Loves の Omni Voices TTS です。私たちは誰でも自分の言葉で、プライベートに、オフラインで音声を作れる、ローカルで簡単に動く音声ツールを作っています。
- `german_clone_01_warmup` scored `99.67%`: Hallo, hier ist OmniVoice TTS von Angry Labs. Wir bauen lokale, einfach nutzbare Sprachwerkzeuge, damit Menschen privat, offline und in ihrer eigenen Sprache Sprache erzeugen können.
- `indonesian_clone_01_warmup` scored `99.00%`: Hello, ini Omni Voice TTS dari Hangry Labs. Kami membuat alat suara lokal yang mudah dijalankan agar orang dapat membuat ucapan secara privat, offline, dan dalam bahasa mereka sendiri.
- `turkish_clone_01_warmup` scored `96.97%`: Merhaba, bu hungry lapsen amni voice tts. İnsanların kendi dillerinde özel olarak ve çevrim dışı konuşma üretilebilmesi için yerel ve kolay çalışan ses araçları geliştiriyoruz.
- `korean_clone_01_warmup` scored `87.50%`: 안녕하세요, 행위랩스의 엄리 voice tts입니다. 우리는 사람들이 자신의 언어로 개인적으로 오프라인에서도 음성을 만들 수 있도록 로컬에서 쉽게 실행되는 음성 도구를 만듭니다.
- `dutch_clone_01_warmup` scored `98.53%`: Hallo, dit is OmniVoice TTS van Hangry Labs. We bouwen lokale voor eenvoudig te gebruiken stemtools zodat mensen privé, offline en in hun eigen taal spraak kunnen maken.

### Mismatches And Inconsistent Cases

#### french_random_02

- Expected: Le croissant était si croustillant que même le silence a fait des miettes.
- Exact repeats: `0/5`
- Repeat consistent: `yes`
- Mean / minimum similarity: `98.33% / 98.33%`
- Transcript (`5x`): Le croissant était croustillant que même le silence. A fait des miettes.

#### standard_arabic_random_01

- Expected: قلت سأعود بعد خمس دقائق، فضحكت الساعة وقالت: نعرف هذه القصة.
- Exact repeats: `0/5`
- Repeat consistent: `yes`
- Mean / minimum similarity: `93.48% / 93.48%`
- Transcript (`5x`): قصد سأعود بعد خمس دقائق فضحكت ساعة وقالت نعرف هذه القصة.

#### russian_random_01

- Expected: Я сказал, что приду через пять минут; часы посмотрели на меня с русской грустью.
- Exact repeats: `0/5`
- Repeat consistent: `yes`
- Mean / minimum similarity: `99.21% / 99.21%`
- Transcript (`5x`): Я сказал, что приду через пять минут. Часы посмотрели на меня с руской грустью.

#### polish_random_01

- Expected: Powiedziałem, że będę za pięć minut; zegarek tylko spojrzał po polsku i westchnął.
- Exact repeats: `0/5`
- Repeat consistent: `yes`
- Mean / minimum similarity: `94.57% / 94.57%`
- Transcript (`5x`): Powiedziałem, że będę za pięć minut. Zegarek tylko spojł po Polsku i wstgnął.

#### thai_random_01

- Expected: บอกว่าจะถึงในห้านาที แต่นาฬิกาหันมามองเหมือนรู้ความจริงแล้ว
- Exact repeats: `0/5`
- Repeat consistent: `yes`
- Mean / minimum similarity: `96.70% / 96.70%`
- Transcript (`5x`): บอกว่าจะถึงใน 5 นาที แต่นาฬิกาหันมามอง เหมือนรู้ความจริงแล้ว

#### japanese_random_01

- Expected: 五分で行きますと言ったら、時計が静かに首をかしげました。
- Exact repeats: `0/5`
- Repeat consistent: `yes`
- Mean / minimum similarity: `96.15% / 96.15%`
- Transcript (`5x`): 5分で行きますと言ったら、時計が静かに首をかしげました。

#### turkish_random_01

- Expected: Beş dakikaya geliyorum dedim; saat bana Türk kahvesi falı gibi baktı.
- Exact repeats: `0/5`
- Repeat consistent: `yes`
- Mean / minimum similarity: `92.86% / 92.86%`
- Transcript (`5x`): 5 dakikaya geliyorum dedim. Saat bana Türk kahve sıfali gibi baktı.

#### turkish_random_02

- Expected: Kahve o kadar güçlüydü ki, neredeyse benim yerime toplantıya girecekti.
- Exact repeats: `0/5`
- Repeat consistent: `yes`
- Mean / minimum similarity: `88.33% / 88.33%`
- Transcript (`5x`): KV o kadar güçlüydü ki neredeyse benim yerime dopantiyaya girecek tete.

#### vietnamese_random_01

- Expected: Tôi nói năm phút nữa tới, cái đồng hồ nghe xong im lặng rất sâu.
- Exact repeats: `0/5`
- Repeat consistent: `yes`
- Mean / minimum similarity: `97.92% / 97.92%`
- Transcript (`5x`): Tôi nói năm phút nữa tới, cái đồng hồ nghe xong im lặng rất sầu.

#### vietnamese_random_02

- Expected: Ly cà phê sáng nay mạnh đến mức suýt trả lời email thay tôi.
- Exact repeats: `0/5`
- Repeat consistent: `yes`
- Mean / minimum similarity: `88.17% / 88.17%`
- Transcript (`5x`): Lịch café sáng nay, mạnh đến mức suýt trả lời email thay tội.

#### italian_random_02

- Expected: Il caffè era così forte che quasi ha parlato al posto mio.
- Exact repeats: `0/5`
- Repeat consistent: `yes`
- Mean / minimum similarity: `92.31% / 92.31%`
- Transcript (`5x`): Il caffè era così forte che quasi appariva al posto mio.


### Hardest ASR-Judged Calls

- `vietnamese_random_02_r1` - `88.17%` - expected: Ly cà phê sáng nay mạnh đến mức suýt trả lời email thay tôi. - transcript: Lịch café sáng nay, mạnh đến mức suýt trả lời email thay tội.
- `vietnamese_random_02_r2` - `88.17%` - expected: Ly cà phê sáng nay mạnh đến mức suýt trả lời email thay tôi. - transcript: Lịch café sáng nay, mạnh đến mức suýt trả lời email thay tội.
- `vietnamese_random_02_r3` - `88.17%` - expected: Ly cà phê sáng nay mạnh đến mức suýt trả lời email thay tôi. - transcript: Lịch café sáng nay, mạnh đến mức suýt trả lời email thay tội.
- `vietnamese_random_02_r4` - `88.17%` - expected: Ly cà phê sáng nay mạnh đến mức suýt trả lời email thay tôi. - transcript: Lịch café sáng nay, mạnh đến mức suýt trả lời email thay tội.
- `vietnamese_random_02_r5` - `88.17%` - expected: Ly cà phê sáng nay mạnh đến mức suýt trả lời email thay tôi. - transcript: Lịch café sáng nay, mạnh đến mức suýt trả lời email thay tội.
- `turkish_random_02_r1` - `88.33%` - expected: Kahve o kadar güçlüydü ki, neredeyse benim yerime toplantıya girecekti. - transcript: KV o kadar güçlüydü ki neredeyse benim yerime dopantiyaya girecek tete.
- `turkish_random_02_r2` - `88.33%` - expected: Kahve o kadar güçlüydü ki, neredeyse benim yerime toplantıya girecekti. - transcript: KV o kadar güçlüydü ki neredeyse benim yerime dopantiyaya girecek tete.
- `turkish_random_02_r3` - `88.33%` - expected: Kahve o kadar güçlüydü ki, neredeyse benim yerime toplantıya girecekti. - transcript: KV o kadar güçlüydü ki neredeyse benim yerime dopantiyaya girecek tete.
- `turkish_random_02_r4` - `88.33%` - expected: Kahve o kadar güçlüydü ki, neredeyse benim yerime toplantıya girecekti. - transcript: KV o kadar güçlüydü ki neredeyse benim yerime dopantiyaya girecek tete.
- `turkish_random_02_r5` - `88.33%` - expected: Kahve o kadar güçlüydü ki, neredeyse benim yerime toplantıya girecekti. - transcript: KV o kadar güçlüydü ki neredeyse benim yerime dopantiyaya girecek tete.
