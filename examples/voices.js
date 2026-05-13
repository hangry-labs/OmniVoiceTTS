window.LANGUAGE_META = {
  bengali: { nativeName: "বাংলা", icon: "বাং" },
  chinese: { nativeName: "中文", icon: "中" },
  dutch: { nativeName: "Nederlands", icon: "NL" },
  english: { nativeName: "English", icon: "EN" },
  french: { nativeName: "Français", icon: "FR" },
  german: { nativeName: "Deutsch", icon: "DE" },
  hindi: { nativeName: "हिन्दी", icon: "हि" },
  indonesian: { nativeName: "Bahasa Indonesia", icon: "ID" },
  italian: { nativeName: "Italiano", icon: "IT" },
  japanese: { nativeName: "日本語", icon: "日" },
  korean: { nativeName: "한국어", icon: "한" },
  polish: { nativeName: "Polski", icon: "PL" },
  portuguese: { nativeName: "Português", icon: "PT" },
  russian: { nativeName: "Русский", icon: "РУ" },
  spanish: { nativeName: "Español", icon: "ES" },
  standard_arabic: { nativeName: "العربية", icon: "عر" },
  thai: { nativeName: "ไทย", icon: "ไทย" },
  turkish: { nativeName: "Türkçe", icon: "TR" },
  urdu: { nativeName: "اردو", icon: "ار" },
  vietnamese: { nativeName: "Tiếng Việt", icon: "VI" },
};
window.EXAMPLE_MANIFEST = {
  "base_url": "http://127.0.0.1:7864",
  "ref_audio": "/data/examples/original_clone.mp3",
  "num_step": 24,
  "format": "mp3",
  "languages": [
    {
      "slug": "english",
      "language": "English",
      "bucket": "top_total_speakers",
      "intro_text": "Hello, this is OmniVoiceTTS from Hangry Labs. We build local, easy-to-run voice tools so people can create speech privately, offline, and in their own language.",
      "random": [
        {
          "file": "english/random/01.mp3",
          "text": "I tried to make a cup of tea, but the kettle said, 'I'll put you on the list.' Very British, very serious.",
          "bytes": 125804,
          "voice_profile": "bright_female",
          "instruct": "female, young adult, high pitch",
          "nonverbal_tag": null
        },
        {
          "file": "english/random/02.mp3",
          "text": "Never trust a queue that forms by accident; in England it becomes a national institution.",
          "bytes": 113804,
          "voice_profile": "warm_male",
          "instruct": "male, middle-aged, low pitch",
          "nonverbal_tag": null
        },
        {
          "file": "english/random/03.mp3",
          "text": "The weather forecast said sunshine, so naturally I brought an umbrella and emotional backup. [laughter] Maybe the umbrella knew more than the forecast.",
          "bytes": 190604,
          "voice_profile": "auto_nonverbal",
          "instruct": null,
          "nonverbal_tag": "laughter"
        },
        {
          "file": "english/random/04.mp3",
          "text": "I told my toast to hurry up. It popped up offended, but still slightly underdone.",
          "bytes": 101804,
          "voice_profile": "clear_male",
          "instruct": "male, young adult, moderate pitch",
          "nonverbal_tag": null
        },
        {
          "file": "english/random/05.mp3",
          "text": "A polite ghost would say 'boo, if that's all right with you.'",
          "bytes": 75404,
          "voice_profile": "calm_female",
          "instruct": "female, middle-aged, moderate pitch",
          "nonverbal_tag": null
        },
        {
          "file": "english/random/06.mp3",
          "text": "My calendar has a sense of humor: it put Monday right after Sunday again. [sigh] Apparently Sunday filed a complaint, but nobody read it.",
          "bytes": 168524,
          "voice_profile": "auto_nonverbal",
          "instruct": null,
          "nonverbal_tag": "sigh"
        },
        {
          "file": "english/random/07.mp3",
          "text": "I asked for a small favor, and my inbox replied with a meeting invitation.",
          "bytes": 93164,
          "voice_profile": "low_female",
          "instruct": "female, young adult, low pitch",
          "nonverbal_tag": null
        },
        {
          "file": "english/random/08.mp3",
          "text": "The biscuit fell into the tea like it had accepted its destiny.",
          "bytes": 81164,
          "voice_profile": "deep_male",
          "instruct": "male, middle-aged, very low pitch",
          "nonverbal_tag": null
        },
        {
          "file": "english/random/09.mp3",
          "text": "If sarcasm burned calories, half the office would be Olympic athletes. [surprise-ah] Wait, that may explain the mystery doughnut.",
          "bytes": 161324,
          "voice_profile": "auto_nonverbal",
          "instruct": null,
          "nonverbal_tag": "surprise-ah"
        },
        {
          "file": "english/random/10.mp3",
          "text": "I cleaned my desk and found a pen older than my latest life plan.",
          "bytes": 81164,
          "voice_profile": "balanced_female",
          "instruct": "female, young adult, moderate pitch",
          "nonverbal_tag": null
        }
      ],
      "intro": [
        {
          "file": "english/intro/01.mp3",
          "text": "Hello, this is OmniVoiceTTS from Hangry Labs. We build local, easy-to-run voice tools so people can create speech privately, offline, and in their own language.",
          "bytes": 198764
        },
        {
          "file": "english/intro/02.mp3",
          "text": "Hello, this is OmniVoiceTTS from Hangry Labs. We build local, easy-to-run voice tools so people can create speech privately, offline, and in their own language.",
          "bytes": 198764
        },
        {
          "file": "english/intro/03.mp3",
          "text": "Hello, this is OmniVoiceTTS from Hangry Labs. We build local, easy-to-run voice tools so people can create speech privately, offline, and in their own language.",
          "bytes": 198764
        }
      ],
      "clone": [
        {
          "file": "english/clone/01.mp3",
          "text": "Hello, this is OmniVoiceTTS from Hangry Labs. We build local, easy-to-run voice tools so people can create speech privately, offline, and in their own language.",
          "ref_audio": "/data/examples/original_clone.mp3",
          "bytes": 191564
        }
      ]
    },
    {
      "slug": "chinese",
      "language": "Chinese",
      "bucket": "top_total_speakers",
      "intro_text": "你好，这里是来自 Hangry Labs 的 OmniVoiceTTS。我们打造本地运行、简单易用的语音工具，让人们能用自己的语言，私密、离线地生成语音。",
      "random": [
        {
          "file": "chinese/random/01.mp3",
          "text": "今天的奶茶很懂事，三分糖，却给了我十分的快乐。",
          "bytes": 91724,
          "voice_profile": "bright_female",
          "instruct": "female, young adult, high pitch",
          "nonverbal_tag": null
        },
        {
          "file": "chinese/random/02.mp3",
          "text": "我说要早睡，手机说：再看一个视频吧，就一个。结果天亮了。",
          "bytes": 94604,
          "voice_profile": "warm_male",
          "instruct": "male, middle-aged, low pitch",
          "nonverbal_tag": null
        },
        {
          "file": "chinese/random/03.mp3",
          "text": "老板说这个需求很简单，我听见键盘在偷偷叹气。 [laughter] 看来键盘比我更懂职场。",
          "bytes": 147404,
          "voice_profile": "auto_nonverbal",
          "instruct": null,
          "nonverbal_tag": "laughter"
        },
        {
          "file": "chinese/random/04.mp3",
          "text": "人生就像火锅，别急着下结论，先看看谁被烫到了。",
          "bytes": 87884,
          "voice_profile": "clear_male",
          "instruct": "male, young adult, moderate pitch",
          "nonverbal_tag": null
        },
        {
          "file": "chinese/random/05.mp3",
          "text": "我不是拖延症，我只是给灵感一点自由活动时间。",
          "bytes": 75884,
          "voice_profile": "calm_female",
          "instruct": "female, middle-aged, moderate pitch",
          "nonverbal_tag": null
        },
        {
          "file": "chinese/random/06.mp3",
          "text": "电梯到了，门一开，尴尬也一起上来了。 [sigh] 尴尬还按了最近的楼层。",
          "bytes": 121964,
          "voice_profile": "auto_nonverbal",
          "instruct": null,
          "nonverbal_tag": "sigh"
        },
        {
          "file": "chinese/random/07.mp3",
          "text": "减肥计划写得很认真，夜宵看了都感动哭了。",
          "bytes": 81164,
          "voice_profile": "low_female",
          "instruct": "female, young adult, low pitch",
          "nonverbal_tag": null
        },
        {
          "file": "chinese/random/08.mp3",
          "text": "朋友说他马上到，中文里的马上，可能是一匹很慢的马。",
          "bytes": 99884,
          "voice_profile": "deep_male",
          "instruct": "male, middle-aged, very low pitch",
          "nonverbal_tag": null
        },
        {
          "file": "chinese/random/09.mp3",
          "text": "今天风很大，连我的计划都被吹散了。 [surprise-ah] 原来计划也会请假。",
          "bytes": 121964,
          "voice_profile": "auto_nonverbal",
          "instruct": null,
          "nonverbal_tag": "surprise-ah"
        },
        {
          "file": "chinese/random/10.mp3",
          "text": "我和闹钟的关系很好，它每天叫我，我每天不理它。",
          "bytes": 84044,
          "voice_profile": "balanced_female",
          "instruct": "female, young adult, moderate pitch",
          "nonverbal_tag": null
        }
      ],
      "intro": [
        {
          "file": "chinese/intro/01.mp3",
          "text": "你好，这里是来自 Hangry Labs 的 OmniVoiceTTS。我们打造本地运行、简单易用的语音工具，让人们能用自己的语言，私密、离线地生成语音。",
          "bytes": 229004
        },
        {
          "file": "chinese/intro/02.mp3",
          "text": "你好，这里是来自 Hangry Labs 的 OmniVoiceTTS。我们打造本地运行、简单易用的语音工具，让人们能用自己的语言，私密、离线地生成语音。",
          "bytes": 229004
        },
        {
          "file": "chinese/intro/03.mp3",
          "text": "你好，这里是来自 Hangry Labs 的 OmniVoiceTTS。我们打造本地运行、简单易用的语音工具，让人们能用自己的语言，私密、离线地生成语音。",
          "bytes": 229004
        }
      ],
      "clone": [
        {
          "file": "chinese/clone/01.mp3",
          "text": "你好，这里是来自 Hangry Labs 的 OmniVoiceTTS。我们打造本地运行、简单易用的语音工具，让人们能用自己的语言，私密、离线地生成语音。",
          "ref_audio": "/data/examples/original_clone.mp3",
          "bytes": 223724
        }
      ]
    },
    {
      "slug": "hindi",
      "language": "Hindi",
      "bucket": "top_total_speakers",
      "intro_text": "नमस्ते, यह Hangry Labs का OmniVoiceTTS है। हम स्थानीय और आसानी से चलने वाले वॉइस टूल बनाते हैं, ताकि लोग अपनी भाषा में निजी और ऑफलाइन तरीके से आवाज़ बना सकें।",
      "random": [
        {
          "file": "hindi/random/01.mp3",
          "text": "मैंने कहा पाँच मिनट में आता हूँ, और भारतीय पाँच मिनट ने फिर से इतिहास बना दिया।",
          "bytes": 102284,
          "voice_profile": "bright_female",
          "instruct": "female, young adult, high pitch",
          "nonverbal_tag": null
        },
        {
          "file": "hindi/random/02.mp3",
          "text": "चाय इतनी अच्छी थी कि बिस्कुट ने भी उसमें डुबकी लगाकर मोक्ष पा लिया।",
          "bytes": 90284,
          "voice_profile": "warm_male",
          "instruct": "male, middle-aged, low pitch",
          "nonverbal_tag": null
        },
        {
          "file": "hindi/random/03.mp3",
          "text": "माँ ने पूछा खाना खाया? मैंने कहा हाँ, और फ्रिज ने चुपचाप सच्चाई छिपा ली। [laughter] शायद फ्रिज भी परिवार की इज्जत बचा रहा था।",
          "bytes": 157004,
          "voice_profile": "auto_nonverbal",
          "instruct": null,
          "nonverbal_tag": "laughter"
        },
        {
          "file": "hindi/random/04.mp3",
          "text": "सोमवार ऐसा आता है जैसे बिना बुलाए रिश्तेदार।",
          "bytes": 59564,
          "voice_profile": "clear_male",
          "instruct": "male, young adult, moderate pitch",
          "nonverbal_tag": null
        },
        {
          "file": "hindi/random/05.mp3",
          "text": "ऑटो वाले भैया ने बोला पास ही है, फिर मीटर ने दर्शन करा दिए।",
          "bytes": 78764,
          "voice_profile": "calm_female",
          "instruct": "female, middle-aged, moderate pitch",
          "nonverbal_tag": null
        },
        {
          "file": "hindi/random/06.mp3",
          "text": "मैंने डाइट शुरू की, समोसे ने कहा पहले मुझसे तो मिल लो। [sigh] समोसे की दलील सच में मजबूत थी।",
          "bytes": 118604,
          "voice_profile": "auto_nonverbal",
          "instruct": null,
          "nonverbal_tag": "sigh"
        },
        {
          "file": "hindi/random/07.mp3",
          "text": "इंटरनेट चला गया, घर वालों से बात करनी पड़ी, लोग अच्छे निकले।",
          "bytes": 84524,
          "voice_profile": "low_female",
          "instruct": "female, young adult, low pitch",
          "nonverbal_tag": null
        },
        {
          "file": "hindi/random/08.mp3",
          "text": "मेरी अलार्म घड़ी भी जानती है कि मैं बहस जीत जाऊँगा और फिर सो जाऊँगा।",
          "bytes": 88364,
          "voice_profile": "deep_male",
          "instruct": "male, middle-aged, very low pitch",
          "nonverbal_tag": null
        },
        {
          "file": "hindi/random/09.mp3",
          "text": "बारिश आई और सड़क ने तुरंत स्विमिंग पूल बनने का फैसला कर लिया। [surprise-ah] लगता है प्लान भी छुट्टी पर चला गया।",
          "bytes": 150764,
          "voice_profile": "auto_nonverbal",
          "instruct": null,
          "nonverbal_tag": "surprise-ah"
        },
        {
          "file": "hindi/random/10.mp3",
          "text": "कंप्यूटर हैंग हुआ तो लगा जैसे वह भी चाय ब्रेक पर चला गया।",
          "bytes": 80204,
          "voice_profile": "balanced_female",
          "instruct": "female, young adult, moderate pitch",
          "nonverbal_tag": null
        }
      ],
      "intro": [
        {
          "file": "hindi/intro/01.mp3",
          "text": "नमस्ते, यह Hangry Labs का OmniVoiceTTS है। हम स्थानीय और आसानी से चलने वाले वॉइस टूल बनाते हैं, ताकि लोग अपनी भाषा में निजी और ऑफलाइन तरीके से आवाज़ बना सकें।",
          "bytes": 210764
        },
        {
          "file": "hindi/intro/02.mp3",
          "text": "नमस्ते, यह Hangry Labs का OmniVoiceTTS है। हम स्थानीय और आसानी से चलने वाले वॉइस टूल बनाते हैं, ताकि लोग अपनी भाषा में निजी और ऑफलाइन तरीके से आवाज़ बना सकें।",
          "bytes": 210764
        },
        {
          "file": "hindi/intro/03.mp3",
          "text": "नमस्ते, यह Hangry Labs का OmniVoiceTTS है। हम स्थानीय और आसानी से चलने वाले वॉइस टूल बनाते हैं, ताकि लोग अपनी भाषा में निजी और ऑफलाइन तरीके से आवाज़ बना सकें।",
          "bytes": 210764
        }
      ],
      "clone": [
        {
          "file": "hindi/clone/01.mp3",
          "text": "नमस्ते, यह Hangry Labs का OmniVoiceTTS है। हम स्थानीय और आसानी से चलने वाले वॉइस टूल बनाते हैं, ताकि लोग अपनी भाषा में निजी और ऑफलाइन तरीके से आवाज़ बना सकें।",
          "ref_audio": "/data/examples/original_clone.mp3",
          "bytes": 203084
        }
      ]
    },
    {
      "slug": "spanish",
      "language": "Spanish",
      "bucket": "top_total_speakers",
      "intro_text": "Hola, esto es OmniVoiceTTS de Hangry Labs. Creamos herramientas de voz locales y fáciles de usar para que la gente pueda crear voz de forma privada, sin conexión y en su propio idioma.",
      "random": [
        {
          "file": "spanish/random/01.mp3",
          "text": "Dije que llegaba en cinco minutos, pero eran cinco minutos latinoamericanos, con banda sonora y tráfico.",
          "bytes": 133004,
          "voice_profile": "bright_female",
          "instruct": "female, young adult, high pitch",
          "nonverbal_tag": null
        },
        {
          "file": "spanish/random/02.mp3",
          "text": "El café me miró y dijo: hoy yo soy tu personalidad.",
          "bytes": 64364,
          "voice_profile": "warm_male",
          "instruct": "male, middle-aged, low pitch",
          "nonverbal_tag": null
        },
        {
          "file": "spanish/random/03.mp3",
          "text": "Mi plan era madrugar, pero mi almohada presentó mejores argumentos. [laughter] La almohada debería estudiar derecho.",
          "bytes": 148364,
          "voice_profile": "auto_nonverbal",
          "instruct": null,
          "nonverbal_tag": "laughter"
        },
        {
          "file": "spanish/random/04.mp3",
          "text": "Quien guarda comida para mañana, conoce el optimismo; quien la encuentra intacta, conoce el milagro.",
          "bytes": 127724,
          "voice_profile": "clear_male",
          "instruct": "male, young adult, moderate pitch",
          "nonverbal_tag": null
        },
        {
          "file": "spanish/random/05.mp3",
          "text": "La abuela dijo come poquito, y apareció un plato con arquitectura colonial.",
          "bytes": 89804,
          "voice_profile": "calm_female",
          "instruct": "female, middle-aged, moderate pitch",
          "nonverbal_tag": null
        },
        {
          "file": "spanish/random/06.mp3",
          "text": "El lunes llegó tan puntual que sospecho que no tiene amigos. [sigh] Quizá por eso nadie lo invita.",
          "bytes": 115244,
          "voice_profile": "auto_nonverbal",
          "instruct": null,
          "nonverbal_tag": "sigh"
        },
        {
          "file": "spanish/random/07.mp3",
          "text": "Fui al gimnasio en mi mente, y hasta ahí me dio flojera.",
          "bytes": 69644,
          "voice_profile": "low_female",
          "instruct": "female, young adult, low pitch",
          "nonverbal_tag": null
        },
        {
          "file": "spanish/random/08.mp3",
          "text": "El pan caliente no se compra, se adopta con cariño; y si cruje bonito, hasta la dieta aplaude en silencio.",
          "bytes": 123404,
          "voice_profile": "deep_male",
          "instruct": "male, middle-aged, very low pitch",
          "nonverbal_tag": null
        },
        {
          "file": "spanish/random/09.mp3",
          "text": "Mi celular tiene poca batería, igual que mis ganas de hacer trámites. [surprise-ah] Ahora entiendo por qué desapareció el último churro.",
          "bytes": 170924,
          "voice_profile": "auto_nonverbal",
          "instruct": null,
          "nonverbal_tag": "surprise-ah"
        },
        {
          "file": "spanish/random/10.mp3",
          "text": "Prometí ordenar la casa; moví una silla y me sentí arquitecto.",
          "bytes": 79724,
          "voice_profile": "balanced_female",
          "instruct": "female, young adult, moderate pitch",
          "nonverbal_tag": null
        }
      ],
      "intro": [
        {
          "file": "spanish/intro/01.mp3",
          "text": "Hola, esto es OmniVoiceTTS de Hangry Labs. Creamos herramientas de voz locales y fáciles de usar para que la gente pueda crear voz de forma privada, sin conexión y en su propio idioma.",
          "bytes": 220364
        },
        {
          "file": "spanish/intro/02.mp3",
          "text": "Hola, esto es OmniVoiceTTS de Hangry Labs. Creamos herramientas de voz locales y fáciles de usar para que la gente pueda crear voz de forma privada, sin conexión y en su propio idioma.",
          "bytes": 222284
        },
        {
          "file": "spanish/intro/03.mp3",
          "text": "Hola, esto es OmniVoiceTTS de Hangry Labs. Creamos herramientas de voz locales y fáciles de usar para que la gente pueda crear voz de forma privada, sin conexión y en su propio idioma.",
          "bytes": 213644
        }
      ],
      "clone": [
        {
          "file": "spanish/clone/01.mp3",
          "text": "Hola, esto es OmniVoiceTTS de Hangry Labs. Creamos herramientas de voz locales y fáciles de usar para que la gente pueda crear voz de forma privada, sin conexión y en su propio idioma.",
          "ref_audio": "/data/examples/original_clone.mp3",
          "bytes": 219404
        }
      ]
    },
    {
      "slug": "french",
      "language": "French",
      "bucket": "top_total_speakers",
      "intro_text": "Bonjour, ici OmniVoiceTTS de Hangry Labs. Nous créons des outils vocaux locaux et faciles à lancer pour que chacun puisse générer de la parole en privé, hors ligne, et dans sa propre langue.",
      "random": [
        {
          "file": "french/random/01.mp3",
          "text": "J'ai dit que je venais dans cinq minutes; en France, c'est parfois une unité poétique.",
          "bytes": 107564,
          "voice_profile": "bright_female",
          "instruct": "female, young adult, high pitch",
          "nonverbal_tag": null
        },
        {
          "file": "french/random/02.mp3",
          "text": "Le croissant était si croustillant que même le silence a fait des miettes.",
          "bytes": 95564,
          "voice_profile": "warm_male",
          "instruct": "male, middle-aged, low pitch",
          "nonverbal_tag": null
        },
        {
          "file": "french/random/03.mp3",
          "text": "Mon réveil a sonné, j'ai négocié comme à un sommet international. [laughter] Mon réveil a perdu, mais il a demandé un appel.",
          "bytes": 150764,
          "voice_profile": "auto_nonverbal",
          "instruct": null,
          "nonverbal_tag": "laughter"
        },
        {
          "file": "french/random/04.mp3",
          "text": "Le fromage avait plus de caractère que moi un lundi matin.",
          "bytes": 73004,
          "voice_profile": "clear_male",
          "instruct": "male, young adult, moderate pitch",
          "nonverbal_tag": null
        },
        {
          "file": "french/random/05.mp3",
          "text": "J'ai rangé mon bureau; maintenant je ne retrouve plus mon chaos organisé.",
          "bytes": 94124,
          "voice_profile": "calm_female",
          "instruct": "female, middle-aged, moderate pitch",
          "nonverbal_tag": null
        },
        {
          "file": "french/random/06.mp3",
          "text": "Le café du matin ne réveille pas seulement le corps, il signe un traité de paix. [sigh] Le traité n'a duré que jusqu'au deuxième courriel.",
          "bytes": 168524,
          "voice_profile": "auto_nonverbal",
          "instruct": null,
          "nonverbal_tag": "sigh"
        },
        {
          "file": "french/random/07.mp3",
          "text": "La météo a annoncé du soleil; j'ai pris un parapluie par respect pour la tradition.",
          "bytes": 104204,
          "voice_profile": "low_female",
          "instruct": "female, young adult, low pitch",
          "nonverbal_tag": null
        },
        {
          "file": "french/random/08.mp3",
          "text": "J'ai voulu faire simple, puis l'administration a souri.",
          "bytes": 67724,
          "voice_profile": "deep_male",
          "instruct": "male, middle-aged, very low pitch",
          "nonverbal_tag": null
        },
        {
          "file": "french/random/09.mp3",
          "text": "Le pain frais a une odeur qui annule toutes les bonnes résolutions. [surprise-ah] Voilà donc où le dernier croissant est passé.",
          "bytes": 158924,
          "voice_profile": "auto_nonverbal",
          "instruct": null,
          "nonverbal_tag": "surprise-ah"
        },
        {
          "file": "french/random/10.mp3",
          "text": "Mon chat m'ignore en français, c'est plus élégant.",
          "bytes": 65324,
          "voice_profile": "balanced_female",
          "instruct": "female, young adult, moderate pitch",
          "nonverbal_tag": null
        }
      ],
      "intro": [
        {
          "file": "french/intro/01.mp3",
          "text": "Bonjour, ici OmniVoiceTTS de Hangry Labs. Nous créons des outils vocaux locaux et faciles à lancer pour que chacun puisse générer de la parole en privé, hors ligne, et dans sa propre langue.",
          "bytes": 234764
        },
        {
          "file": "french/intro/02.mp3",
          "text": "Bonjour, ici OmniVoiceTTS de Hangry Labs. Nous créons des outils vocaux locaux et faciles à lancer pour que chacun puisse générer de la parole en privé, hors ligne, et dans sa propre langue.",
          "bytes": 234284
        },
        {
          "file": "french/intro/03.mp3",
          "text": "Bonjour, ici OmniVoiceTTS de Hangry Labs. Nous créons des outils vocaux locaux et faciles à lancer pour que chacun puisse générer de la parole en privé, hors ligne, et dans sa propre langue.",
          "bytes": 223244
        }
      ],
      "clone": [
        {
          "file": "french/clone/01.mp3",
          "text": "Bonjour, ici OmniVoiceTTS de Hangry Labs. Nous créons des outils vocaux locaux et faciles à lancer pour que chacun puisse générer de la parole en privé, hors ligne, et dans sa propre langue.",
          "ref_audio": "/data/examples/original_clone.mp3",
          "bytes": 223724
        }
      ]
    },
    {
      "slug": "standard_arabic",
      "language": "Standard Arabic",
      "bucket": "top_total_speakers",
      "intro_text": "مرحباً، هذا هو OmniVoiceTTS من Hangry Labs. نصنع أدوات صوت محلية وسهلة التشغيل كي يتمكن الناس من إنشاء الكلام بخصوصية، ومن دون اتصال، وبلغتهم.",
      "random": [
        {
          "file": "standard_arabic/random/01.mp3",
          "text": "قلت سأعود بعد خمس دقائق، فضحكت الساعة وقالت: نعرف هذه القصة.",
          "bytes": 98444,
          "voice_profile": "bright_female",
          "instruct": "female, young adult, high pitch",
          "nonverbal_tag": null
        },
        {
          "file": "standard_arabic/random/02.mp3",
          "text": "القهوة قالت لي صباح الخير، فأجبتها: أنتِ الخير كله.",
          "bytes": 91244,
          "voice_profile": "warm_male",
          "instruct": "male, middle-aged, low pitch",
          "nonverbal_tag": null
        },
        {
          "file": "standard_arabic/random/03.mp3",
          "text": "فتحت الثلاجة ثلاث مرات، كأن الطعام سيظهر من شدة الإصرار. [laughter] يبدو أن الثلاجة تعرف أسراري أكثر مما ينبغي.",
          "bytes": 184844,
          "voice_profile": "auto_nonverbal",
          "instruct": null,
          "nonverbal_tag": "laughter"
        },
        {
          "file": "standard_arabic/random/04.mp3",
          "text": "من طلب الراحة يوم الاثنين، فقد طلب المستحيل بأدب.",
          "bytes": 84524,
          "voice_profile": "clear_male",
          "instruct": "male, young adult, moderate pitch",
          "nonverbal_tag": null
        },
        {
          "file": "standard_arabic/random/05.mp3",
          "text": "الخبز الساخن لا يحتاج إلى إعلان، رائحته تقوم بالمهمة.",
          "bytes": 84044,
          "voice_profile": "calm_female",
          "instruct": "female, middle-aged, moderate pitch",
          "nonverbal_tag": null
        },
        {
          "file": "standard_arabic/random/06.mp3",
          "text": "قلت سأبدأ الحمية غداً، فابتسمت الحلوى ابتسامة المنتصر. [sigh] كانت ابتسامة الحلوى مقنعة جداً.",
          "bytes": 145484,
          "voice_profile": "auto_nonverbal",
          "instruct": null,
          "nonverbal_tag": "sigh"
        },
        {
          "file": "standard_arabic/random/07.mp3",
          "text": "الإنترنت انقطع، فاكتشفت أن في البيت أناساً طيبين.",
          "bytes": 83564,
          "voice_profile": "low_female",
          "instruct": "female, young adult, low pitch",
          "nonverbal_tag": null
        },
        {
          "file": "standard_arabic/random/08.mp3",
          "text": "رتبت مكتبي، والآن أبحث عن الفوضى التي كنت أفهمها.",
          "bytes": 87404,
          "voice_profile": "deep_male",
          "instruct": "male, middle-aged, very low pitch",
          "nonverbal_tag": null
        },
        {
          "file": "standard_arabic/random/09.mp3",
          "text": "المنبه يوقظني كل يوم، وأنا أعلّمه معنى الصبر. [surprise-ah] ربما اختفت الخطة مع آخر قطعة كعك.",
          "bytes": 153164,
          "voice_profile": "auto_nonverbal",
          "instruct": null,
          "nonverbal_tag": "surprise-ah"
        },
        {
          "file": "standard_arabic/random/10.mp3",
          "text": "الطقس قال مشمس، فحملت مظلة احتراماً للمفاجآت.",
          "bytes": 83084,
          "voice_profile": "balanced_female",
          "instruct": "female, young adult, moderate pitch",
          "nonverbal_tag": null
        }
      ],
      "intro": [
        {
          "file": "standard_arabic/intro/01.mp3",
          "text": "مرحباً، هذا هو OmniVoiceTTS من Hangry Labs. نصنع أدوات صوت محلية وسهلة التشغيل كي يتمكن الناس من إنشاء الكلام بخصوصية، ومن دون اتصال، وبلغتهم.",
          "bytes": 213644
        },
        {
          "file": "standard_arabic/intro/02.mp3",
          "text": "مرحباً، هذا هو OmniVoiceTTS من Hangry Labs. نصنع أدوات صوت محلية وسهلة التشغيل كي يتمكن الناس من إنشاء الكلام بخصوصية، ومن دون اتصال، وبلغتهم.",
          "bytes": 216044
        },
        {
          "file": "standard_arabic/intro/03.mp3",
          "text": "مرحباً، هذا هو OmniVoiceTTS من Hangry Labs. نصنع أدوات صوت محلية وسهلة التشغيل كي يتمكن الناس من إنشاء الكلام بخصوصية، ومن دون اتصال، وبلغتهم.",
          "bytes": 217004
        }
      ],
      "clone": [
        {
          "file": "standard_arabic/clone/01.mp3",
          "text": "مرحباً، هذا هو OmniVoiceTTS من Hangry Labs. نصنع أدوات صوت محلية وسهلة التشغيل كي يتمكن الناس من إنشاء الكلام بخصوصية، ومن دون اتصال، وبلغتهم.",
          "ref_audio": "/data/examples/original_clone.mp3",
          "bytes": 229004
        }
      ]
    },
    {
      "slug": "bengali",
      "language": "Bengali",
      "bucket": "top_total_speakers",
      "intro_text": "নমস্কার, এটি Hangry Labs-এর OmniVoiceTTS। আমরা স্থানীয়ভাবে চলা সহজ ভয়েস টুল তৈরি করি, যাতে মানুষ নিজের ভাষায় ব্যক্তিগতভাবে ও অফলাইনে speech তৈরি করতে পারে।",
      "random": [
        {
          "file": "bengali/random/01.mp3",
          "text": "আমি বললাম পাঁচ মিনিটে আসছি, আর পাঁচ মিনিট চুপচাপ এক ঘণ্টা হয়ে গেল।",
          "bytes": 96524,
          "voice_profile": "bright_female",
          "instruct": "female, young adult, high pitch",
          "nonverbal_tag": null
        },
        {
          "file": "bengali/random/02.mp3",
          "text": "চা এত ভালো ছিল যে বিস্কুট নিজেই ডুব দিতে রাজি হয়ে গেল।",
          "bytes": 72524,
          "voice_profile": "warm_male",
          "instruct": "male, middle-aged, low pitch",
          "nonverbal_tag": null
        },
        {
          "file": "bengali/random/03.mp3",
          "text": "সোমবার এমনভাবে আসে, যেন সে ক্যালেন্ডারের বাড়িওয়ালা। [laughter] মনে হয় সোমবারের চাবিটা খুবই আসল।",
          "bytes": 135404,
          "voice_profile": "auto_nonverbal",
          "instruct": null,
          "nonverbal_tag": "laughter"
        },
        {
          "file": "bengali/random/04.mp3",
          "text": "ফ্রিজ খুললাম তিনবার, খাবারটা লজ্জা পেয়ে বেরিয়ে আসবে ভেবেছিলাম।",
          "bytes": 87404,
          "voice_profile": "clear_male",
          "instruct": "male, young adult, moderate pitch",
          "nonverbal_tag": null
        },
        {
          "file": "bengali/random/05.mp3",
          "text": "ডায়েট শুরু করেছিলাম, কিন্তু রসগোল্লা বলল, আগে শেষ দেখা করে যাও।",
          "bytes": 89324,
          "voice_profile": "calm_female",
          "instruct": "female, middle-aged, moderate pitch",
          "nonverbal_tag": null
        },
        {
          "file": "bengali/random/06.mp3",
          "text": "ঘুম থেকে ওঠার আগে অ্যালার্মের সঙ্গে আমার প্রতিদিন সংসদ বসে। [sigh] অ্যালার্মের ধৈর্য সত্যিই প্রশংসনীয়।",
          "bytes": 145004,
          "voice_profile": "auto_nonverbal",
          "instruct": null,
          "nonverbal_tag": "sigh"
        },
        {
          "file": "bengali/random/07.mp3",
          "text": "বৃষ্টি নামল, আর রাস্তা ভাবল আজ একটু নদী হয়ে যাই।",
          "bytes": 72524,
          "voice_profile": "low_female",
          "instruct": "female, young adult, low pitch",
          "nonverbal_tag": null
        },
        {
          "file": "bengali/random/08.mp3",
          "text": "ইন্টারনেট বন্ধ হলে বুঝলাম বাড়ির মানুষগুলো আসলে মন্দ নয়।",
          "bytes": 86924,
          "voice_profile": "deep_male",
          "instruct": "male, middle-aged, very low pitch",
          "nonverbal_tag": null
        },
        {
          "file": "bengali/random/09.mp3",
          "text": "আমার ডেস্ক গুছিয়ে এত পরিষ্কার করেছি যে এখন কাজটাই খুঁজে পাচ্ছি না। [surprise-ah] তাহলে মিষ্টিটা নিজে নিজেই হারায়নি।",
          "bytes": 152204,
          "voice_profile": "auto_nonverbal",
          "instruct": null,
          "nonverbal_tag": "surprise-ah"
        },
        {
          "file": "bengali/random/10.mp3",
          "text": "মাছের কাঁটা যেমন সাবধানে খেতে হয়, তেমনি আত্মীয়ের প্রশ্নও।",
          "bytes": 82604,
          "voice_profile": "balanced_female",
          "instruct": "female, young adult, moderate pitch",
          "nonverbal_tag": null
        }
      ],
      "intro": [
        {
          "file": "bengali/intro/01.mp3",
          "text": "নমস্কার, এটি Hangry Labs-এর OmniVoiceTTS। আমরা স্থানীয়ভাবে চলা সহজ ভয়েস টুল তৈরি করি, যাতে মানুষ নিজের ভাষায় ব্যক্তিগতভাবে ও অফলাইনে speech তৈরি করতে পারে।",
          "bytes": 202124
        },
        {
          "file": "bengali/intro/02.mp3",
          "text": "নমস্কার, এটি Hangry Labs-এর OmniVoiceTTS। আমরা স্থানীয়ভাবে চলা সহজ ভয়েস টুল তৈরি করি, যাতে মানুষ নিজের ভাষায় ব্যক্তিগতভাবে ও অফলাইনে speech তৈরি করতে পারে।",
          "bytes": 204524
        },
        {
          "file": "bengali/intro/03.mp3",
          "text": "নমস্কার, এটি Hangry Labs-এর OmniVoiceTTS। আমরা স্থানীয়ভাবে চলা সহজ ভয়েস টুল তৈরি করি, যাতে মানুষ নিজের ভাষায় ব্যক্তিগতভাবে ও অফলাইনে speech তৈরি করতে পারে।",
          "bytes": 196844
        }
      ],
      "clone": [
        {
          "file": "bengali/clone/01.mp3",
          "text": "নমস্কার, এটি Hangry Labs-এর OmniVoiceTTS। আমরা স্থানীয়ভাবে চলা সহজ ভয়েস টুল তৈরি করি, যাতে মানুষ নিজের ভাষায় ব্যক্তিগতভাবে ও অফলাইনে speech তৈরি করতে পারে।",
          "ref_audio": "/data/examples/original_clone.mp3",
          "bytes": 210764
        }
      ]
    },
    {
      "slug": "russian",
      "language": "Russian",
      "bucket": "top_total_speakers",
      "intro_text": "Здравствуйте, это OmniVoiceTTS от Hangry Labs. Мы создаем локальные и простые голосовые инструменты, чтобы люди могли создавать речь приватно, офлайн и на своем языке.",
      "random": [
        {
          "file": "russian/random/01.mp3",
          "text": "Я сказал, что приду через пять минут; часы посмотрели на меня с русской грустью.",
          "bytes": 101324,
          "voice_profile": "bright_female",
          "instruct": "female, young adult, high pitch",
          "nonverbal_tag": null
        },
        {
          "file": "russian/random/02.mp3",
          "text": "Чай был такой крепкий, что сам предложил решить мои проблемы.",
          "bytes": 79724,
          "voice_profile": "warm_male",
          "instruct": "male, middle-aged, low pitch",
          "nonverbal_tag": null
        },
        {
          "file": "russian/random/03.mp3",
          "text": "Понедельник пришел без стука, как будто ему все можно. [laughter] Похоже, понедельник давно сделал дубликат ключей.",
          "bytes": 146924,
          "voice_profile": "auto_nonverbal",
          "instruct": null,
          "nonverbal_tag": "laughter"
        },
        {
          "file": "russian/random/04.mp3",
          "text": "Я открыл холодильник третий раз, надеясь, что еда проявит инициативу.",
          "bytes": 89804,
          "voice_profile": "clear_male",
          "instruct": "male, young adult, moderate pitch",
          "nonverbal_tag": null
        },
        {
          "file": "russian/random/05.mp3",
          "text": "Будильник звонит, а я каждый день доказываю силу переговоров.",
          "bytes": 81164,
          "voice_profile": "calm_female",
          "instruct": "female, middle-aged, moderate pitch",
          "nonverbal_tag": null
        },
        {
          "file": "russian/random/06.mp3",
          "text": "План был простой, пока я не начал его выполнять. [sigh] Простой план просто хорошо маскировался.",
          "bytes": 121004,
          "voice_profile": "auto_nonverbal",
          "instruct": null,
          "nonverbal_tag": "sigh"
        },
        {
          "file": "russian/random/07.mp3",
          "text": "Я убрал стол, и теперь не могу найти свою систему хаоса.",
          "bytes": 71564,
          "voice_profile": "low_female",
          "instruct": "female, young adult, low pitch",
          "nonverbal_tag": null
        },
        {
          "file": "russian/random/08.mp3",
          "text": "Снег выпал так уверенно, будто его никто не просил.",
          "bytes": 66764,
          "voice_profile": "deep_male",
          "instruct": "male, middle-aged, very low pitch",
          "nonverbal_tag": null
        },
        {
          "file": "russian/random/09.mp3",
          "text": "Кот посмотрел на меня так, будто аренду плачу я, а квартира его. [surprise-ah] Вот куда делся последний пряник.",
          "bytes": 137804,
          "voice_profile": "auto_nonverbal",
          "instruct": null,
          "nonverbal_tag": "surprise-ah"
        },
        {
          "file": "russian/random/10.mp3",
          "text": "Интернет пропал, и чай внезапно стал главным приложением.",
          "bytes": 76364,
          "voice_profile": "balanced_female",
          "instruct": "female, young adult, moderate pitch",
          "nonverbal_tag": null
        }
      ],
      "intro": [
        {
          "file": "russian/intro/01.mp3",
          "text": "Здравствуйте, это OmniVoiceTTS от Hangry Labs. Мы создаем локальные и простые голосовые инструменты, чтобы люди могли создавать речь приватно, офлайн и на своем языке.",
          "bytes": 212204
        },
        {
          "file": "russian/intro/02.mp3",
          "text": "Здравствуйте, это OmniVoiceTTS от Hangry Labs. Мы создаем локальные и простые голосовые инструменты, чтобы люди могли создавать речь приватно, офлайн и на своем языке.",
          "bytes": 211724
        },
        {
          "file": "russian/intro/03.mp3",
          "text": "Здравствуйте, это OmniVoiceTTS от Hangry Labs. Мы создаем локальные и простые голосовые инструменты, чтобы люди могли создавать речь приватно, офлайн и на своем языке.",
          "bytes": 212204
        }
      ],
      "clone": [
        {
          "file": "russian/clone/01.mp3",
          "text": "Здравствуйте, это OmniVoiceTTS от Hangry Labs. Мы создаем локальные и простые голосовые инструменты, чтобы люди могли создавать речь приватно, офлайн и на своем языке.",
          "ref_audio": "/data/examples/original_clone.mp3",
          "bytes": 202604
        }
      ]
    },
    {
      "slug": "portuguese",
      "language": "Portuguese",
      "bucket": "top_total_speakers",
      "intro_text": "Olá, este é o OmniVoiceTTS da Hangry Labs. Criamos ferramentas de voz locais e fáceis de usar para que as pessoas possam gerar fala com privacidade, offline e em seu próprio idioma.",
      "random": [
        {
          "file": "portuguese/random/01.mp3",
          "text": "Eu disse que chegava em cinco minutos; o relógio ouviu e pediu paciência.",
          "bytes": 93164,
          "voice_profile": "bright_female",
          "instruct": "female, young adult, high pitch",
          "nonverbal_tag": null
        },
        {
          "file": "portuguese/random/02.mp3",
          "text": "O café estava tão forte que quase respondeu meus e-mails.",
          "bytes": 73964,
          "voice_profile": "warm_male",
          "instruct": "male, middle-aged, low pitch",
          "nonverbal_tag": null
        },
        {
          "file": "portuguese/random/03.mp3",
          "text": "Segunda-feira chegou sorrindo, e isso já foi suspeito. [laughter] Agora desconfio que a segunda-feira tem agenda própria.",
          "bytes": 153164,
          "voice_profile": "auto_nonverbal",
          "instruct": null,
          "nonverbal_tag": "laughter"
        },
        {
          "file": "portuguese/random/04.mp3",
          "text": "Abri a geladeira três vezes, esperando que a comida tivesse iniciativa.",
          "bytes": 92204,
          "voice_profile": "clear_male",
          "instruct": "male, young adult, moderate pitch",
          "nonverbal_tag": null
        },
        {
          "file": "portuguese/random/05.mp3",
          "text": "Comecei a dieta, mas o pão de queijo falou comigo pelo nome.",
          "bytes": 76364,
          "voice_profile": "calm_female",
          "instruct": "female, middle-aged, moderate pitch",
          "nonverbal_tag": null
        },
        {
          "file": "portuguese/random/06.mp3",
          "text": "Meu plano era acordar cedo; meu travesseiro ganhou no argumento. [sigh] Meu travesseiro deveria virar advogado.",
          "bytes": 142124,
          "voice_profile": "auto_nonverbal",
          "instruct": null,
          "nonverbal_tag": "sigh"
        },
        {
          "file": "portuguese/random/07.mp3",
          "text": "Chuva caiu e a rua decidiu virar piscina comunitária.",
          "bytes": 70124,
          "voice_profile": "low_female",
          "instruct": "female, young adult, low pitch",
          "nonverbal_tag": null
        },
        {
          "file": "portuguese/random/08.mp3",
          "text": "Organizei a mesa e perdi a localização oficial da bagunça.",
          "bytes": 73964,
          "voice_profile": "deep_male",
          "instruct": "male, middle-aged, very low pitch",
          "nonverbal_tag": null
        },
        {
          "file": "portuguese/random/09.mp3",
          "text": "O cachorro me olhou como quem sabe todos os meus segredos e quer petisco. [surprise-ah] Então foi ali que sumiu o último brigadeiro.",
          "bytes": 163724,
          "voice_profile": "auto_nonverbal",
          "instruct": null,
          "nonverbal_tag": "surprise-ah"
        },
        {
          "file": "portuguese/random/10.mp3",
          "text": "Prometi fazer só uma pausa, mas a pausa abriu uma filial.",
          "bytes": 73004,
          "voice_profile": "balanced_female",
          "instruct": "female, young adult, moderate pitch",
          "nonverbal_tag": null
        }
      ],
      "intro": [
        {
          "file": "portuguese/intro/01.mp3",
          "text": "Olá, este é o OmniVoiceTTS da Hangry Labs. Criamos ferramentas de voz locais e fáceis de usar para que as pessoas possam gerar fala com privacidade, offline e em seu próprio idioma.",
          "bytes": 218444
        },
        {
          "file": "portuguese/intro/02.mp3",
          "text": "Olá, este é o OmniVoiceTTS da Hangry Labs. Criamos ferramentas de voz locais e fáceis de usar para que as pessoas possam gerar fala com privacidade, offline e em seu próprio idioma.",
          "bytes": 223724
        },
        {
          "file": "portuguese/intro/03.mp3",
          "text": "Olá, este é o OmniVoiceTTS da Hangry Labs. Criamos ferramentas de voz locais e fáceis de usar para que as pessoas possam gerar fala com privacidade, offline e em seu próprio idioma.",
          "bytes": 223724
        }
      ],
      "clone": [
        {
          "file": "portuguese/clone/01.mp3",
          "text": "Olá, este é o OmniVoiceTTS da Hangry Labs. Criamos ferramentas de voz locais e fáceis de usar para que as pessoas possam gerar fala com privacidade, offline e em seu próprio idioma.",
          "ref_audio": "/data/examples/original_clone.mp3",
          "bytes": 216524
        }
      ]
    },
    {
      "slug": "urdu",
      "language": "Urdu",
      "bucket": "top_total_speakers",
      "intro_text": "سلام، یہ Hangry Labs کا OmniVoiceTTS ہے۔ ہم مقامی اور آسانی سے چلنے والے وائس ٹول بناتے ہیں تاکہ لوگ اپنی زبان میں، نجی طور پر اور آف لائن آواز بنا سکیں۔",
      "random": [
        {
          "file": "urdu/random/01.mp3",
          "text": "میں نے کہا پانچ منٹ میں آتا ہوں، گھڑی نے کہا یہ جملہ پہلے بھی سنا ہے۔",
          "bytes": 118604,
          "voice_profile": "bright_female",
          "instruct": "female, young adult, high pitch",
          "nonverbal_tag": null
        },
        {
          "file": "urdu/random/02.mp3",
          "text": "چائے اتنی اچھی تھی کہ بسکٹ نے خود ہی ڈبکی لگا دی۔",
          "bytes": 83084,
          "voice_profile": "warm_male",
          "instruct": "male, middle-aged, low pitch",
          "nonverbal_tag": null
        },
        {
          "file": "urdu/random/03.mp3",
          "text": "پیر کا دن ایسے آتا ہے جیسے بغیر بلایا مہمان۔ [laughter] لگتا ہے پیر کے پاس واقعی اپنی چابی ہے۔",
          "bytes": 158924,
          "voice_profile": "auto_nonverbal",
          "instruct": null,
          "nonverbal_tag": "laughter"
        },
        {
          "file": "urdu/random/04.mp3",
          "text": "میں نے فریج تین بار کھولا، شاید کھانا شرما کر سامنے آ جائے۔",
          "bytes": 88844,
          "voice_profile": "clear_male",
          "instruct": "male, young adult, moderate pitch",
          "nonverbal_tag": null
        },
        {
          "file": "urdu/random/05.mp3",
          "text": "ڈائٹ شروع کی تو سموسے نے کہا پہلے آخری ملاقات کر لو۔",
          "bytes": 83084,
          "voice_profile": "calm_female",
          "instruct": "female, middle-aged, moderate pitch",
          "nonverbal_tag": null
        },
        {
          "file": "urdu/random/06.mp3",
          "text": "الارم روز مجھے جگاتا ہے، اور میں روز اسے امید کا سبق دیتا ہوں۔ [sigh] الارم کی امید واقعی قابل تعریف ہے۔",
          "bytes": 172364,
          "voice_profile": "auto_nonverbal",
          "instruct": null,
          "nonverbal_tag": "sigh"
        },
        {
          "file": "urdu/random/07.mp3",
          "text": "انٹرنیٹ بند ہوا تو گھر والوں سے بات ہوئی، لوگ اچھے نکلے۔",
          "bytes": 91244,
          "voice_profile": "low_female",
          "instruct": "female, young adult, low pitch",
          "nonverbal_tag": null
        },
        {
          "file": "urdu/random/08.mp3",
          "text": "بارش ہوئی اور سڑک نے فوراً تالاب بننے کا فیصلہ کر لیا۔",
          "bytes": 91244,
          "voice_profile": "deep_male",
          "instruct": "male, middle-aged, very low pitch",
          "nonverbal_tag": null
        },
        {
          "file": "urdu/random/09.mp3",
          "text": "کام آسان تھا، جب تک واقعی شروع نہیں کیا تھا۔ [surprise-ah] تو آخری سموسہ یوں غائب نہیں ہوا تھا۔",
          "bytes": 157964,
          "voice_profile": "auto_nonverbal",
          "instruct": null,
          "nonverbal_tag": "surprise-ah"
        },
        {
          "file": "urdu/random/10.mp3",
          "text": "میں نے میز صاف کی، اب اپنی ہی چیزیں مجھ سے ناراض ہیں۔",
          "bytes": 78764,
          "voice_profile": "balanced_female",
          "instruct": "female, young adult, moderate pitch",
          "nonverbal_tag": null
        }
      ],
      "intro": [
        {
          "file": "urdu/intro/01.mp3",
          "text": "سلام، یہ Hangry Labs کا OmniVoiceTTS ہے۔ ہم مقامی اور آسانی سے چلنے والے وائس ٹول بناتے ہیں تاکہ لوگ اپنی زبان میں، نجی طور پر اور آف لائن آواز بنا سکیں۔",
          "bytes": 249644
        },
        {
          "file": "urdu/intro/02.mp3",
          "text": "سلام، یہ Hangry Labs کا OmniVoiceTTS ہے۔ ہم مقامی اور آسانی سے چلنے والے وائس ٹول بناتے ہیں تاکہ لوگ اپنی زبان میں، نجی طور پر اور آف لائن آواز بنا سکیں۔",
          "bytes": 251564
        },
        {
          "file": "urdu/intro/03.mp3",
          "text": "سلام، یہ Hangry Labs کا OmniVoiceTTS ہے۔ ہم مقامی اور آسانی سے چلنے والے وائس ٹول بناتے ہیں تاکہ لوگ اپنی زبان میں، نجی طور پر اور آف لائن آواز بنا سکیں۔",
          "bytes": 251564
        }
      ],
      "clone": [
        {
          "file": "urdu/clone/01.mp3",
          "text": "سلام، یہ Hangry Labs کا OmniVoiceTTS ہے۔ ہم مقامی اور آسانی سے چلنے والے وائس ٹول بناتے ہیں تاکہ لوگ اپنی زبان میں، نجی طور پر اور آف لائن آواز بنا سکیں۔",
          "ref_audio": "/data/examples/original_clone.mp3",
          "bytes": 239564
        }
      ]
    },
    {
      "slug": "polish",
      "language": "Polish",
      "bucket": "popular_showcase",
      "intro_text": "Cześć, tu OmniVoiceTTS od Hangry Labs. Tworzymy lokalne, łatwe w uruchomieniu narzędzia głosowe, żeby ludzie mogli tworzyć mowę prywatnie, offline i we własnym języku.",
      "random": [
        {
          "file": "polish/random/01.mp3",
          "text": "Powiedziałem, że będę za pięć minut; zegarek tylko spojrzał po polsku i westchnął.",
          "bytes": 105164,
          "voice_profile": "bright_female",
          "instruct": "female, young adult, high pitch",
          "nonverbal_tag": null
        },
        {
          "file": "polish/random/02.mp3",
          "text": "Herbata była tak mocna, że sama zapytała, co dziś załatwiamy.",
          "bytes": 76844,
          "voice_profile": "warm_male",
          "instruct": "male, middle-aged, low pitch",
          "nonverbal_tag": null
        },
        {
          "file": "polish/random/03.mp3",
          "text": "Poniedziałek przyszedł bez pukania, jakby miał klucze do mieszkania. [laughter] Może to nie był najlepszy żart.",
          "bytes": 140684,
          "voice_profile": "auto_nonverbal",
          "instruct": null,
          "nonverbal_tag": "laughter"
        },
        {
          "file": "polish/random/04.mp3",
          "text": "Otworzyłem lodówkę trzeci raz, licząc, że pierogi same się ujawnią.",
          "bytes": 84044,
          "voice_profile": "clear_male",
          "instruct": "male, young adult, moderate pitch",
          "nonverbal_tag": null
        },
        {
          "file": "polish/random/05.mp3",
          "text": "Zacząłem dietę, ale pączek powiedział: jeszcze tylko raz.",
          "bytes": 75404,
          "voice_profile": "calm_female",
          "instruct": "female, middle-aged, moderate pitch",
          "nonverbal_tag": null
        },
        {
          "file": "polish/random/06.mp3",
          "text": "Budzik dzwoni, a ja codziennie prowadzę z nim trudne negocjacje. [sigh] Negocjacje trwają, ale budzik ma przewagę.",
          "bytes": 144524,
          "voice_profile": "auto_nonverbal",
          "instruct": null,
          "nonverbal_tag": "sigh"
        },
        {
          "file": "polish/random/07.mp3",
          "text": "Posprzątałem biurko i zgubiłem cały system porządnego bałaganu.",
          "bytes": 85004,
          "voice_profile": "low_female",
          "instruct": "female, young adult, low pitch",
          "nonverbal_tag": null
        },
        {
          "file": "polish/random/08.mp3",
          "text": "Paragon był dłuższy niż moja lista planów życiowych.",
          "bytes": 68204,
          "voice_profile": "deep_male",
          "instruct": "male, middle-aged, very low pitch",
          "nonverbal_tag": null
        },
        {
          "file": "polish/random/09.mp3",
          "text": "Pogoda obiecała słońce, więc oczywiście wziąłem parasol. [surprise-ah] Czyli pączek jednak miał plan awaryjny.",
          "bytes": 137804,
          "voice_profile": "auto_nonverbal",
          "instruct": null,
          "nonverbal_tag": "surprise-ah"
        },
        {
          "file": "polish/random/10.mp3",
          "text": "Kawa rano nie budzi człowieka, ona przywraca mu wersję demonstracyjną.",
          "bytes": 85004,
          "voice_profile": "balanced_female",
          "instruct": "female, young adult, moderate pitch",
          "nonverbal_tag": null
        }
      ],
      "intro": [
        {
          "file": "polish/intro/01.mp3",
          "text": "Cześć, tu OmniVoiceTTS od Hangry Labs. Tworzymy lokalne, łatwe w uruchomieniu narzędzia głosowe, żeby ludzie mogli tworzyć mowę prywatnie, offline i we własnym języku.",
          "bytes": 211724
        },
        {
          "file": "polish/intro/02.mp3",
          "text": "Cześć, tu OmniVoiceTTS od Hangry Labs. Tworzymy lokalne, łatwe w uruchomieniu narzędzia głosowe, żeby ludzie mogli tworzyć mowę prywatnie, offline i we własnym języku.",
          "bytes": 206444
        },
        {
          "file": "polish/intro/03.mp3",
          "text": "Cześć, tu OmniVoiceTTS od Hangry Labs. Tworzymy lokalne, łatwe w uruchomieniu narzędzia głosowe, żeby ludzie mogli tworzyć mowę prywatnie, offline i we własnym języku.",
          "bytes": 211724
        }
      ],
      "clone": [
        {
          "file": "polish/clone/01.mp3",
          "text": "Cześć, tu OmniVoiceTTS od Hangry Labs. Tworzymy lokalne, łatwe w uruchomieniu narzędzia głosowe, żeby ludzie mogli tworzyć mowę prywatnie, offline i we własnym języku.",
          "ref_audio": "/data/examples/original_clone.mp3",
          "bytes": 205964
        }
      ]
    },
    {
      "slug": "thai",
      "language": "Thai",
      "bucket": "popular_showcase",
      "intro_text": "สวัสดี นี่คือ OmniVoiceTTS จาก Hangry Labs เราสร้างเครื่องมือเสียงที่รันในเครื่องและใช้งานง่าย เพื่อให้ผู้คนสร้างเสียงพูดได้อย่างเป็นส่วนตัว ออฟไลน์ และเป็นภาษาของตัวเอง",
      "random": [
        {
          "file": "thai/random/01.mp3",
          "text": "บอกว่าจะถึงในห้านาที แต่นาฬิกาหันมามองเหมือนรู้ความจริงแล้ว",
          "bytes": 88364,
          "voice_profile": "bright_female",
          "instruct": "female, young adult, high pitch",
          "nonverbal_tag": null
        },
        {
          "file": "thai/random/02.mp3",
          "text": "กาแฟแก้วนี้เข้มจนเหมือนพร้อมไปประชุมแทนฉัน",
          "bytes": 77324,
          "voice_profile": "warm_male",
          "instruct": "male, middle-aged, low pitch",
          "nonverbal_tag": null
        },
        {
          "file": "thai/random/03.mp3",
          "text": "วันจันทร์มาไวเหมือนเน็ตตอนยังไม่หมดโปร [laughter] ดูเหมือนวันจันทร์จะมีกุญแจสำรองจริง ๆ",
          "bytes": 124844,
          "voice_profile": "auto_nonverbal",
          "instruct": null,
          "nonverbal_tag": "laughter"
        },
        {
          "file": "thai/random/04.mp3",
          "text": "เปิดตู้เย็นรอบที่สาม เผื่อของกินจะสงสารแล้วโผล่มาเอง",
          "bytes": 72524,
          "voice_profile": "clear_male",
          "instruct": "male, young adult, moderate pitch",
          "nonverbal_tag": null
        },
        {
          "file": "thai/random/05.mp3",
          "text": "เริ่มลดน้ำหนักได้หนึ่งชั่วโมง ข้าวเหนียวหมูปิ้งก็เรียกชื่อฉัน",
          "bytes": 81644,
          "voice_profile": "calm_female",
          "instruct": "female, middle-aged, moderate pitch",
          "nonverbal_tag": null
        },
        {
          "file": "thai/random/06.mp3",
          "text": "นาฬิกาปลุกดังทุกเช้า ส่วนฉันก็กดเลื่อนอย่างมีวินัย [sigh] นาฬิกาปลุกคงเหนื่อยกับการเจรจานี้เหมือนกัน",
          "bytes": 149804,
          "voice_profile": "auto_nonverbal",
          "instruct": null,
          "nonverbal_tag": "sigh"
        },
        {
          "file": "thai/random/07.mp3",
          "text": "ฝนตกทีไร ถนนแถวบ้านก็อยากเป็นคลองทันที",
          "bytes": 68684,
          "voice_profile": "low_female",
          "instruct": "female, young adult, low pitch",
          "nonverbal_tag": null
        },
        {
          "file": "thai/random/08.mp3",
          "text": "จัดโต๊ะจนเรียบร้อย แล้วก็หาอะไรไม่เจอเลยสักอย่าง",
          "bytes": 69644,
          "voice_profile": "deep_male",
          "instruct": "male, middle-aged, very low pitch",
          "nonverbal_tag": null
        },
        {
          "file": "thai/random/09.mp3",
          "text": "ยิ้มไว้ก่อน เดี๋ยวค่อยไปงงต่อข้างใน [surprise-ah] อย่างนี้ขนมชิ้นสุดท้ายก็มีผู้ต้องสงสัยแล้ว",
          "bytes": 118124,
          "voice_profile": "auto_nonverbal",
          "instruct": null,
          "nonverbal_tag": "surprise-ah"
        },
        {
          "file": "thai/random/10.mp3",
          "text": "ชานมหวานน้อย แต่ความสุขหวานมาก",
          "bytes": 53324,
          "voice_profile": "balanced_female",
          "instruct": "female, young adult, moderate pitch",
          "nonverbal_tag": null
        }
      ],
      "intro": [
        {
          "file": "thai/intro/01.mp3",
          "text": "สวัสดี นี่คือ OmniVoiceTTS จาก Hangry Labs เราสร้างเครื่องมือเสียงที่รันในเครื่องและใช้งานง่าย เพื่อให้ผู้คนสร้างเสียงพูดได้อย่างเป็นส่วนตัว ออฟไลน์ และเป็นภาษาของตัวเอง",
          "bytes": 243404
        },
        {
          "file": "thai/intro/02.mp3",
          "text": "สวัสดี นี่คือ OmniVoiceTTS จาก Hangry Labs เราสร้างเครื่องมือเสียงที่รันในเครื่องและใช้งานง่าย เพื่อให้ผู้คนสร้างเสียงพูดได้อย่างเป็นส่วนตัว ออฟไลน์ และเป็นภาษาของตัวเอง",
          "bytes": 229964
        },
        {
          "file": "thai/intro/03.mp3",
          "text": "สวัสดี นี่คือ OmniVoiceTTS จาก Hangry Labs เราสร้างเครื่องมือเสียงที่รันในเครื่องและใช้งานง่าย เพื่อให้ผู้คนสร้างเสียงพูดได้อย่างเป็นส่วนตัว ออฟไลน์ และเป็นภาษาของตัวเอง",
          "bytes": 243404
        }
      ],
      "clone": [
        {
          "file": "thai/clone/01.mp3",
          "text": "สวัสดี นี่คือ OmniVoiceTTS จาก Hangry Labs เราสร้างเครื่องมือเสียงที่รันในเครื่องและใช้งานง่าย เพื่อให้ผู้คนสร้างเสียงพูดได้อย่างเป็นส่วนตัว ออฟไลน์ และเป็นภาษาของตัวเอง",
          "ref_audio": "/data/examples/original_clone.mp3",
          "bytes": 247724
        }
      ]
    },
    {
      "slug": "japanese",
      "language": "Japanese",
      "bucket": "popular_showcase",
      "intro_text": "こんにちは、Hangry Labs の OmniVoiceTTS です。私たちは、誰でも自分の言葉で、プライベートに、オフラインで音声を作れる、ローカルで簡単に動く音声ツールを作っています。",
      "random": [
        {
          "file": "japanese/random/01.mp3",
          "text": "五分で行きますと言ったら、時計が静かに首をかしげました。",
          "bytes": 87404,
          "voice_profile": "bright_female",
          "instruct": "female, young adult, high pitch",
          "nonverbal_tag": null
        },
        {
          "file": "japanese/random/02.mp3",
          "text": "朝のコーヒーは目覚ましではなく、私の再起動ボタンです。",
          "bytes": 92204,
          "voice_profile": "warm_male",
          "instruct": "male, middle-aged, low pitch",
          "nonverbal_tag": null
        },
        {
          "file": "japanese/random/03.mp3",
          "text": "月曜日は招待していないのに、毎週きちんと来ます。 [laughter] 月曜日は合鍵まで持っているのかもしれません。",
          "bytes": 169964,
          "voice_profile": "auto_nonverbal",
          "instruct": null,
          "nonverbal_tag": "laughter"
        },
        {
          "file": "japanese/random/04.mp3",
          "text": "冷蔵庫を三回開けました。食べ物が増える魔法はまだ未実装です。",
          "bytes": 93164,
          "voice_profile": "clear_male",
          "instruct": "male, young adult, moderate pitch",
          "nonverbal_tag": null
        },
        {
          "file": "japanese/random/05.mp3",
          "text": "ダイエットを始めた瞬間、たい焼きがこちらを見ていました。",
          "bytes": 82604,
          "voice_profile": "calm_female",
          "instruct": "female, middle-aged, moderate pitch",
          "nonverbal_tag": null
        },
        {
          "file": "japanese/random/06.mp3",
          "text": "目覚まし時計とは毎朝、小さな外交交渉をしています。 [sigh] 目覚ましのほうが交渉上手でした。",
          "bytes": 152204,
          "voice_profile": "auto_nonverbal",
          "instruct": null,
          "nonverbal_tag": "sigh"
        },
        {
          "file": "japanese/random/07.mp3",
          "text": "机を片づけたら、どこに何があるのか完全に迷子になりました。",
          "bytes": 98924,
          "voice_profile": "low_female",
          "instruct": "female, young adult, low pitch",
          "nonverbal_tag": null
        },
        {
          "file": "japanese/random/08.mp3",
          "text": "猫に無視されると、なぜかこちらが反省します。",
          "bytes": 73964,
          "voice_profile": "deep_male",
          "instruct": "male, middle-aged, very low pitch",
          "nonverbal_tag": null
        },
        {
          "file": "japanese/random/09.mp3",
          "text": "雨の日の靴下は、だいたい冒険者です。 [surprise-ah] つまり最後の団子には事情があったんですね。",
          "bytes": 147884,
          "voice_profile": "auto_nonverbal",
          "instruct": null,
          "nonverbal_tag": "surprise-ah"
        },
        {
          "file": "japanese/random/10.mp3",
          "text": "早口言葉は得意です。となりの客はよく柿食う客だ、と言えた気がします。",
          "bytes": 97964,
          "voice_profile": "balanced_female",
          "instruct": "female, young adult, moderate pitch",
          "nonverbal_tag": null
        }
      ],
      "intro": [
        {
          "file": "japanese/intro/01.mp3",
          "text": "こんにちは、Hangry Labs の OmniVoiceTTS です。私たちは、誰でも自分の言葉で、プライベートに、オフラインで音声を作れる、ローカルで簡単に動く音声ツールを作っています。",
          "bytes": 252524
        },
        {
          "file": "japanese/intro/02.mp3",
          "text": "こんにちは、Hangry Labs の OmniVoiceTTS です。私たちは、誰でも自分の言葉で、プライベートに、オフラインで音声を作れる、ローカルで簡単に動く音声ツールを作っています。",
          "bytes": 252524
        },
        {
          "file": "japanese/intro/03.mp3",
          "text": "こんにちは、Hangry Labs の OmniVoiceTTS です。私たちは、誰でも自分の言葉で、プライベートに、オフラインで音声を作れる、ローカルで簡単に動く音声ツールを作っています。",
          "bytes": 252524
        }
      ],
      "clone": [
        {
          "file": "japanese/clone/01.mp3",
          "text": "こんにちは、Hangry Labs の OmniVoiceTTS です。私たちは、誰でも自分の言葉で、プライベートに、オフラインで音声を作れる、ローカルで簡単に動く音声ツールを作っています。",
          "ref_audio": "/data/examples/original_clone.mp3",
          "bytes": 245804
        }
      ]
    },
    {
      "slug": "german",
      "language": "German",
      "bucket": "popular_showcase",
      "intro_text": "Hallo, hier ist OmniVoiceTTS von Hangry Labs. Wir bauen lokale, einfach nutzbare Sprachwerkzeuge, damit Menschen privat, offline und in ihrer eigenen Sprache Sprache erzeugen können.",
      "random": [
        {
          "file": "german/random/01.mp3",
          "text": "Ich sagte, ich bin in fünf Minuten da; die Uhr hat sehr deutsch gezweifelt.",
          "bytes": 94124,
          "voice_profile": "bright_female",
          "instruct": "female, young adult, high pitch",
          "nonverbal_tag": null
        },
        {
          "file": "german/random/02.mp3",
          "text": "Der Kaffee war so stark, dass er fast meine Steuererklärung machen wollte.",
          "bytes": 92204,
          "voice_profile": "warm_male",
          "instruct": "male, middle-aged, low pitch",
          "nonverbal_tag": null
        },
        {
          "file": "german/random/03.mp3",
          "text": "Der Montag kam pünktlich, und genau das war das Problem. [laughter] Vielleicht hat der Montag wirklich einen Ersatzschlüssel.",
          "bytes": 151724,
          "voice_profile": "auto_nonverbal",
          "instruct": null,
          "nonverbal_tag": "laughter"
        },
        {
          "file": "german/random/04.mp3",
          "text": "Ich öffnete den Kühlschrank dreimal, aber die Ordnung blieb unbeeindruckt.",
          "bytes": 97964,
          "voice_profile": "clear_male",
          "instruct": "male, young adult, moderate pitch",
          "nonverbal_tag": null
        },
        {
          "file": "german/random/05.mp3",
          "text": "Ich wollte aufräumen, jetzt ist mein Chaos nur besser dokumentiert.",
          "bytes": 88364,
          "voice_profile": "calm_female",
          "instruct": "female, middle-aged, moderate pitch",
          "nonverbal_tag": null
        },
        {
          "file": "german/random/06.mp3",
          "text": "Das Brötchen war so frisch, dass meine Vorsätze sofort gekündigt haben. [sigh] Der Wecker verhandelt leider ziemlich hart.",
          "bytes": 152204,
          "voice_profile": "auto_nonverbal",
          "instruct": null,
          "nonverbal_tag": "sigh"
        },
        {
          "file": "german/random/07.mp3",
          "text": "Mein Wecker klingelt jeden Morgen mit unangemessenem Optimismus.",
          "bytes": 86444,
          "voice_profile": "low_female",
          "instruct": "female, young adult, low pitch",
          "nonverbal_tag": null
        },
        {
          "file": "german/random/08.mp3",
          "text": "Der Zug hatte Verspätung, aber immerhin sehr zuverlässig.",
          "bytes": 76364,
          "voice_profile": "deep_male",
          "instruct": "male, middle-aged, very low pitch",
          "nonverbal_tag": null
        },
        {
          "file": "german/random/09.mp3",
          "text": "Ich machte eine kurze Pause; sie beantragte sofort Verlängerung. [surprise-ah] Dann war das letzte Brötchen doch nicht unschuldig.",
          "bytes": 156044,
          "voice_profile": "auto_nonverbal",
          "instruct": null,
          "nonverbal_tag": "surprise-ah"
        },
        {
          "file": "german/random/10.mp3",
          "text": "Der Hund schaute mich an, als hätte er den Mietvertrag gelesen.",
          "bytes": 81164,
          "voice_profile": "balanced_female",
          "instruct": "female, young adult, moderate pitch",
          "nonverbal_tag": null
        }
      ],
      "intro": [
        {
          "file": "german/intro/01.mp3",
          "text": "Hallo, hier ist OmniVoiceTTS von Hangry Labs. Wir bauen lokale, einfach nutzbare Sprachwerkzeuge, damit Menschen privat, offline und in ihrer eigenen Sprache Sprache erzeugen können.",
          "bytes": 207884
        },
        {
          "file": "german/intro/02.mp3",
          "text": "Hallo, hier ist OmniVoiceTTS von Hangry Labs. Wir bauen lokale, einfach nutzbare Sprachwerkzeuge, damit Menschen privat, offline und in ihrer eigenen Sprache Sprache erzeugen können.",
          "bytes": 223244
        },
        {
          "file": "german/intro/03.mp3",
          "text": "Hallo, hier ist OmniVoiceTTS von Hangry Labs. Wir bauen lokale, einfach nutzbare Sprachwerkzeuge, damit Menschen privat, offline und in ihrer eigenen Sprache Sprache erzeugen können.",
          "bytes": 231404
        }
      ],
      "clone": [
        {
          "file": "german/clone/01.mp3",
          "text": "Hallo, hier ist OmniVoiceTTS von Hangry Labs. Wir bauen lokale, einfach nutzbare Sprachwerkzeuge, damit Menschen privat, offline und in ihrer eigenen Sprache Sprache erzeugen können.",
          "ref_audio": "/data/examples/original_clone.mp3",
          "bytes": 217004
        }
      ]
    },
    {
      "slug": "indonesian",
      "language": "Indonesian",
      "bucket": "popular_showcase",
      "intro_text": "Halo, ini OmniVoiceTTS dari Hangry Labs. Kami membuat alat suara lokal yang mudah dijalankan agar orang dapat membuat ucapan secara privat, offline, dan dalam bahasa mereka sendiri.",
      "random": [
        {
          "file": "indonesian/random/01.mp3",
          "text": "Saya bilang lima menit lagi sampai, dan jam langsung pura-pura tidak dengar.",
          "bytes": 81644,
          "voice_profile": "bright_female",
          "instruct": "female, young adult, high pitch",
          "nonverbal_tag": null
        },
        {
          "file": "indonesian/random/02.mp3",
          "text": "Kopi pagi ini kuat sekali, hampir saja ikut membalas email.",
          "bytes": 77324,
          "voice_profile": "warm_male",
          "instruct": "male, middle-aged, low pitch",
          "nonverbal_tag": null
        },
        {
          "file": "indonesian/random/03.mp3",
          "text": "Hari Senin datang tepat waktu, padahal tidak ada yang mengundang. [laughter] Sepertinya Senin memang punya kunci cadangan.",
          "bytes": 151724,
          "voice_profile": "auto_nonverbal",
          "instruct": null,
          "nonverbal_tag": "laughter"
        },
        {
          "file": "indonesian/random/04.mp3",
          "text": "Saya buka kulkas tiga kali, berharap nasi goreng muncul karena kasihan.",
          "bytes": 82124,
          "voice_profile": "clear_male",
          "instruct": "male, young adult, moderate pitch",
          "nonverbal_tag": null
        },
        {
          "file": "indonesian/random/05.mp3",
          "text": "Mulai diet pagi ini, sore harinya gorengan menyapa dengan ramah.",
          "bytes": 72524,
          "voice_profile": "calm_female",
          "instruct": "female, middle-aged, moderate pitch",
          "nonverbal_tag": null
        },
        {
          "file": "indonesian/random/06.mp3",
          "text": "Alarm berbunyi, saya tekan tunda dengan rasa tanggung jawab yang besar. [sigh] Alarm itu ternyata lawan negosiasi yang tangguh.",
          "bytes": 161324,
          "voice_profile": "auto_nonverbal",
          "instruct": null,
          "nonverbal_tag": "sigh"
        },
        {
          "file": "indonesian/random/07.mp3",
          "text": "Hujan turun sebentar, jalan depan rumah langsung latihan jadi sungai.",
          "bytes": 90764,
          "voice_profile": "low_female",
          "instruct": "female, young adult, low pitch",
          "nonverbal_tag": null
        },
        {
          "file": "indonesian/random/08.mp3",
          "text": "Meja sudah rapi, sekarang barang-barang saya seperti pindah negara.",
          "bytes": 82604,
          "voice_profile": "deep_male",
          "instruct": "male, middle-aged, very low pitch",
          "nonverbal_tag": null
        },
        {
          "file": "indonesian/random/09.mp3",
          "text": "Rencana sederhana berubah menjadi rapat kecil dengan diri sendiri. [surprise-ah] Jadi camilan terakhir punya alibi yang lemah.",
          "bytes": 154604,
          "voice_profile": "auto_nonverbal",
          "instruct": null,
          "nonverbal_tag": "surprise-ah"
        },
        {
          "file": "indonesian/random/10.mp3",
          "text": "Teh manisnya biasa saja, tapi obrolannya langsung jadi hangat.",
          "bytes": 70124,
          "voice_profile": "balanced_female",
          "instruct": "female, young adult, moderate pitch",
          "nonverbal_tag": null
        }
      ],
      "intro": [
        {
          "file": "indonesian/intro/01.mp3",
          "text": "Halo, ini OmniVoiceTTS dari Hangry Labs. Kami membuat alat suara lokal yang mudah dijalankan agar orang dapat membuat ucapan secara privat, offline, dan dalam bahasa mereka sendiri.",
          "bytes": 211724
        },
        {
          "file": "indonesian/intro/02.mp3",
          "text": "Halo, ini OmniVoiceTTS dari Hangry Labs. Kami membuat alat suara lokal yang mudah dijalankan agar orang dapat membuat ucapan secara privat, offline, dan dalam bahasa mereka sendiri.",
          "bytes": 228524
        },
        {
          "file": "indonesian/intro/03.mp3",
          "text": "Halo, ini OmniVoiceTTS dari Hangry Labs. Kami membuat alat suara lokal yang mudah dijalankan agar orang dapat membuat ucapan secara privat, offline, dan dalam bahasa mereka sendiri.",
          "bytes": 220364
        }
      ],
      "clone": [
        {
          "file": "indonesian/clone/01.mp3",
          "text": "Halo, ini OmniVoiceTTS dari Hangry Labs. Kami membuat alat suara lokal yang mudah dijalankan agar orang dapat membuat ucapan secara privat, offline, dan dalam bahasa mereka sendiri.",
          "ref_audio": "/data/examples/original_clone.mp3",
          "bytes": 219404
        }
      ]
    },
    {
      "slug": "turkish",
      "language": "Turkish",
      "bucket": "popular_showcase",
      "intro_text": "Merhaba, bu Hangry Labs'ten OmniVoiceTTS. İnsanların kendi dillerinde, özel olarak ve çevrimdışı konuşma üretebilmesi için yerel ve kolay çalışan ses araçları geliştiriyoruz.",
      "random": [
        {
          "file": "turkish/random/01.mp3",
          "text": "Beş dakikaya geliyorum dedim; saat bana Türk kahvesi falı gibi baktı.",
          "bytes": 86444,
          "voice_profile": "bright_female",
          "instruct": "female, young adult, high pitch",
          "nonverbal_tag": null
        },
        {
          "file": "turkish/random/02.mp3",
          "text": "Kahve o kadar güçlüydü ki, neredeyse benim yerime toplantıya girecekti.",
          "bytes": 88844,
          "voice_profile": "warm_male",
          "instruct": "male, middle-aged, low pitch",
          "nonverbal_tag": null
        },
        {
          "file": "turkish/random/03.mp3",
          "text": "Pazartesi kapıyı çalmadan geldi, sanki evin anahtarı onda. [laughter] Galiba pazartesinin gerçekten yedek anahtarı var.",
          "bytes": 142604,
          "voice_profile": "auto_nonverbal",
          "instruct": null,
          "nonverbal_tag": "laughter"
        },
        {
          "file": "turkish/random/04.mp3",
          "text": "Buzdolabını üç kez açtım; yemeklerin ikna olmasını bekledim.",
          "bytes": 70604,
          "voice_profile": "clear_male",
          "instruct": "male, young adult, moderate pitch",
          "nonverbal_tag": null
        },
        {
          "file": "turkish/random/05.mp3",
          "text": "Diyete başladım, simit uzaktan göz kırptı.",
          "bytes": 50924,
          "voice_profile": "calm_female",
          "instruct": "female, middle-aged, moderate pitch",
          "nonverbal_tag": null
        },
        {
          "file": "turkish/random/06.mp3",
          "text": "Alarm çalıyor, ben her sabah erteleme sanatını geliştiriyorum. [sigh] Alarm bu pazarlıkta oldukça inatçı çıktı.",
          "bytes": 142604,
          "voice_profile": "auto_nonverbal",
          "instruct": null,
          "nonverbal_tag": "sigh"
        },
        {
          "file": "turkish/random/07.mp3",
          "text": "Yağmur yağdı, sokak hemen küçük bir boğaz turuna döndü.",
          "bytes": 72524,
          "voice_profile": "low_female",
          "instruct": "female, young adult, low pitch",
          "nonverbal_tag": null
        },
        {
          "file": "turkish/random/08.mp3",
          "text": "Masayı topladım, şimdi düzenin içinde kayboldum.",
          "bytes": 57644,
          "voice_profile": "deep_male",
          "instruct": "male, middle-aged, very low pitch",
          "nonverbal_tag": null
        },
        {
          "file": "turkish/random/09.mp3",
          "text": "Çay demlenene kadar hayatın anlamı biraz bekleyebilir. [surprise-ah] Demek son baklavanın da bir hikayesi varmış.",
          "bytes": 136844,
          "voice_profile": "auto_nonverbal",
          "instruct": null,
          "nonverbal_tag": "surprise-ah"
        },
        {
          "file": "turkish/random/10.mp3",
          "text": "Kedi bana baktı; kira sözleşmesini o imzalamış gibi.",
          "bytes": 69164,
          "voice_profile": "balanced_female",
          "instruct": "female, young adult, moderate pitch",
          "nonverbal_tag": null
        }
      ],
      "intro": [
        {
          "file": "turkish/intro/01.mp3",
          "text": "Merhaba, bu Hangry Labs'ten OmniVoiceTTS. İnsanların kendi dillerinde, özel olarak ve çevrimdışı konuşma üretebilmesi için yerel ve kolay çalışan ses araçları geliştiriyoruz.",
          "bytes": 193964
        },
        {
          "file": "turkish/intro/02.mp3",
          "text": "Merhaba, bu Hangry Labs'ten OmniVoiceTTS. İnsanların kendi dillerinde, özel olarak ve çevrimdışı konuşma üretebilmesi için yerel ve kolay çalışan ses araçları geliştiriyoruz.",
          "bytes": 201644
        },
        {
          "file": "turkish/intro/03.mp3",
          "text": "Merhaba, bu Hangry Labs'ten OmniVoiceTTS. İnsanların kendi dillerinde, özel olarak ve çevrimdışı konuşma üretebilmesi için yerel ve kolay çalışan ses araçları geliştiriyoruz.",
          "bytes": 204044
        }
      ],
      "clone": [
        {
          "file": "turkish/clone/01.mp3",
          "text": "Merhaba, bu Hangry Labs'ten OmniVoiceTTS. İnsanların kendi dillerinde, özel olarak ve çevrimdışı konuşma üretebilmesi için yerel ve kolay çalışan ses araçları geliştiriyoruz.",
          "ref_audio": "/data/examples/original_clone.mp3",
          "bytes": 209804
        }
      ]
    },
    {
      "slug": "korean",
      "language": "Korean",
      "bucket": "popular_showcase",
      "intro_text": "안녕하세요, Hangry Labs의 OmniVoiceTTS입니다. 우리는 사람들이 자신의 언어로, 개인적으로, 오프라인에서도 음성을 만들 수 있도록 로컬에서 쉽게 실행되는 음성 도구를 만듭니다.",
      "random": [
        {
          "file": "korean/random/01.mp3",
          "text": "오 분 뒤에 도착한다고 했더니, 시계가 조용히 웃는 것 같았어요.",
          "bytes": 91724,
          "voice_profile": "bright_female",
          "instruct": "female, young adult, high pitch",
          "nonverbal_tag": null
        },
        {
          "file": "korean/random/02.mp3",
          "text": "아침 커피가 너무 진해서 제 대신 출근할 뻔했어요.",
          "bytes": 78764,
          "voice_profile": "warm_male",
          "instruct": "male, middle-aged, low pitch",
          "nonverbal_tag": null
        },
        {
          "file": "korean/random/03.mp3",
          "text": "월요일은 초대하지 않았는데도 매주 성실하게 옵니다. [laughter] 월요일은 아마 예비 열쇠까지 갖고 있나 봅니다.",
          "bytes": 168524,
          "voice_profile": "auto_nonverbal",
          "instruct": null,
          "nonverbal_tag": "laughter"
        },
        {
          "file": "korean/random/04.mp3",
          "text": "냉장고를 세 번 열었지만, 김치찌개는 아직 자동 생성되지 않았습니다.",
          "bytes": 107564,
          "voice_profile": "clear_male",
          "instruct": "male, young adult, moderate pitch",
          "nonverbal_tag": null
        },
        {
          "file": "korean/random/05.mp3",
          "text": "다이어트를 시작하자마자 떡볶이가 제 이름을 불렀어요.",
          "bytes": 88364,
          "voice_profile": "calm_female",
          "instruct": "female, middle-aged, moderate pitch",
          "nonverbal_tag": null
        },
        {
          "file": "korean/random/06.mp3",
          "text": "알람은 매일 울리고, 저는 매일 협상의 달인이 됩니다. [sigh] 알람은 협상에서 꽤 강한 상대였습니다.",
          "bytes": 143084,
          "voice_profile": "auto_nonverbal",
          "instruct": null,
          "nonverbal_tag": "sigh"
        },
        {
          "file": "korean/random/07.mp3",
          "text": "책상을 정리했더니 제 물건들이 단체로 이사 갔습니다.",
          "bytes": 83564,
          "voice_profile": "low_female",
          "instruct": "female, young adult, low pitch",
          "nonverbal_tag": null
        },
        {
          "file": "korean/random/08.mp3",
          "text": "비가 오자 양말이 모험을 시작했습니다.",
          "bytes": 63404,
          "voice_profile": "deep_male",
          "instruct": "male, middle-aged, very low pitch",
          "nonverbal_tag": null
        },
        {
          "file": "korean/random/09.mp3",
          "text": "고양이가 저를 무시하면, 왠지 제가 사과해야 할 것 같아요. [surprise-ah] 그러면 마지막 떡은 그냥 사라진 게 아니었군요.",
          "bytes": 172844,
          "voice_profile": "auto_nonverbal",
          "instruct": null,
          "nonverbal_tag": "surprise-ah"
        },
        {
          "file": "korean/random/10.mp3",
          "text": "잠깐 쉬려고 했는데, 잠깐이 퇴근 시간을 데려왔습니다.",
          "bytes": 80204,
          "voice_profile": "balanced_female",
          "instruct": "female, young adult, moderate pitch",
          "nonverbal_tag": null
        }
      ],
      "intro": [
        {
          "file": "korean/intro/01.mp3",
          "text": "안녕하세요, Hangry Labs의 OmniVoiceTTS입니다. 우리는 사람들이 자신의 언어로, 개인적으로, 오프라인에서도 음성을 만들 수 있도록 로컬에서 쉽게 실행되는 음성 도구를 만듭니다.",
          "bytes": 251564
        },
        {
          "file": "korean/intro/02.mp3",
          "text": "안녕하세요, Hangry Labs의 OmniVoiceTTS입니다. 우리는 사람들이 자신의 언어로, 개인적으로, 오프라인에서도 음성을 만들 수 있도록 로컬에서 쉽게 실행되는 음성 도구를 만듭니다.",
          "bytes": 248204
        },
        {
          "file": "korean/intro/03.mp3",
          "text": "안녕하세요, Hangry Labs의 OmniVoiceTTS입니다. 우리는 사람들이 자신의 언어로, 개인적으로, 오프라인에서도 음성을 만들 수 있도록 로컬에서 쉽게 실행되는 음성 도구를 만듭니다.",
          "bytes": 256844
        }
      ],
      "clone": [
        {
          "file": "korean/clone/01.mp3",
          "text": "안녕하세요, Hangry Labs의 OmniVoiceTTS입니다. 우리는 사람들이 자신의 언어로, 개인적으로, 오프라인에서도 음성을 만들 수 있도록 로컬에서 쉽게 실행되는 음성 도구를 만듭니다.",
          "ref_audio": "/data/examples/original_clone.mp3",
          "bytes": 257804
        }
      ]
    },
    {
      "slug": "vietnamese",
      "language": "Vietnamese",
      "bucket": "popular_showcase",
      "intro_text": "Xin chào, đây là OmniVoiceTTS từ Hangry Labs. Chúng tôi xây dựng công cụ giọng nói chạy cục bộ, dễ dùng, để mọi người tạo lời nói riêng tư, ngoại tuyến và bằng ngôn ngữ của mình.",
      "random": [
        {
          "file": "vietnamese/random/01.mp3",
          "text": "Tôi nói năm phút nữa tới, cái đồng hồ nghe xong im lặng rất sâu.",
          "bytes": 77324,
          "voice_profile": "bright_female",
          "instruct": "female, young adult, high pitch",
          "nonverbal_tag": null
        },
        {
          "file": "vietnamese/random/02.mp3",
          "text": "Ly cà phê sáng nay mạnh đến mức suýt trả lời email thay tôi.",
          "bytes": 74444,
          "voice_profile": "warm_male",
          "instruct": "male, middle-aged, low pitch",
          "nonverbal_tag": null
        },
        {
          "file": "vietnamese/random/03.mp3",
          "text": "Thứ Hai đến đúng giờ, và đó là điều đáng ngại nhất. [laughter] Có lẽ thứ Hai thật sự có chìa khóa dự phòng.",
          "bytes": 126764,
          "voice_profile": "auto_nonverbal",
          "instruct": null,
          "nonverbal_tag": "laughter"
        },
        {
          "file": "vietnamese/random/04.mp3",
          "text": "Tôi mở tủ lạnh ba lần, hy vọng đồ ăn tự biết thương mình.",
          "bytes": 69164,
          "voice_profile": "clear_male",
          "instruct": "male, young adult, moderate pitch",
          "nonverbal_tag": null
        },
        {
          "file": "vietnamese/random/05.mp3",
          "text": "Vừa bắt đầu ăn kiêng thì bánh mì đã gọi tên tôi rất thân thiết.",
          "bytes": 75884,
          "voice_profile": "calm_female",
          "instruct": "female, middle-aged, moderate pitch",
          "nonverbal_tag": null
        },
        {
          "file": "vietnamese/random/06.mp3",
          "text": "Báo thức reo mỗi sáng, còn tôi luyện kỹ năng hoãn binh. [sigh] Cái báo thức đúng là đối thủ đàm phán cứng rắn.",
          "bytes": 130604,
          "voice_profile": "auto_nonverbal",
          "instruct": null,
          "nonverbal_tag": "sigh"
        },
        {
          "file": "vietnamese/random/07.mp3",
          "text": "Trời mưa một chút, con đường trước nhà lập tức muốn làm sông.",
          "bytes": 75404,
          "voice_profile": "low_female",
          "instruct": "female, young adult, low pitch",
          "nonverbal_tag": null
        },
        {
          "file": "vietnamese/random/08.mp3",
          "text": "Dọn bàn xong, tôi không tìm thấy cả sự lộn xộn quen thuộc.",
          "bytes": 72524,
          "voice_profile": "deep_male",
          "instruct": "male, middle-aged, very low pitch",
          "nonverbal_tag": null
        },
        {
          "file": "vietnamese/random/09.mp3",
          "text": "Kế hoạch thì đơn giản, cho đến khi tôi bắt đầu làm thật. [surprise-ah] Vậy chiếc bánh cuối cùng cũng có câu chuyện riêng.",
          "bytes": 143084,
          "voice_profile": "auto_nonverbal",
          "instruct": null,
          "nonverbal_tag": "surprise-ah"
        },
        {
          "file": "vietnamese/random/10.mp3",
          "text": "Trà đá vỉa hè đôi khi hiểu đời hơn cả lịch làm việc.",
          "bytes": 63404,
          "voice_profile": "balanced_female",
          "instruct": "female, young adult, moderate pitch",
          "nonverbal_tag": null
        }
      ],
      "intro": [
        {
          "file": "vietnamese/intro/01.mp3",
          "text": "Xin chào, đây là OmniVoiceTTS từ Hangry Labs. Chúng tôi xây dựng công cụ giọng nói chạy cục bộ, dễ dùng, để mọi người tạo lời nói riêng tư, ngoại tuyến và bằng ngôn ngữ của mình.",
          "bytes": 211724
        },
        {
          "file": "vietnamese/intro/02.mp3",
          "text": "Xin chào, đây là OmniVoiceTTS từ Hangry Labs. Chúng tôi xây dựng công cụ giọng nói chạy cục bộ, dễ dùng, để mọi người tạo lời nói riêng tư, ngoại tuyến và bằng ngôn ngữ của mình.",
          "bytes": 211724
        },
        {
          "file": "vietnamese/intro/03.mp3",
          "text": "Xin chào, đây là OmniVoiceTTS từ Hangry Labs. Chúng tôi xây dựng công cụ giọng nói chạy cục bộ, dễ dùng, để mọi người tạo lời nói riêng tư, ngoại tuyến và bằng ngôn ngữ của mình.",
          "bytes": 211244
        }
      ],
      "clone": [
        {
          "file": "vietnamese/clone/01.mp3",
          "text": "Xin chào, đây là OmniVoiceTTS từ Hangry Labs. Chúng tôi xây dựng công cụ giọng nói chạy cục bộ, dễ dùng, để mọi người tạo lời nói riêng tư, ngoại tuyến và bằng ngôn ngữ của mình.",
          "ref_audio": "/data/examples/original_clone.mp3",
          "bytes": 205484
        }
      ]
    },
    {
      "slug": "italian",
      "language": "Italian",
      "bucket": "popular_showcase",
      "intro_text": "Ciao, questo è OmniVoiceTTS di Hangry Labs. Costruiamo strumenti vocali locali e facili da usare, così le persone possono creare parlato in privato, offline e nella propria lingua.",
      "random": [
        {
          "file": "italian/random/01.mp3",
          "text": "Ho detto arrivo tra cinque minuti; l'orologio mi ha guardato con gesto italiano.",
          "bytes": 102764,
          "voice_profile": "bright_female",
          "instruct": "female, young adult, high pitch",
          "nonverbal_tag": null
        },
        {
          "file": "italian/random/02.mp3",
          "text": "Il caffè era così forte che quasi ha parlato al posto mio.",
          "bytes": 73964,
          "voice_profile": "warm_male",
          "instruct": "male, middle-aged, low pitch",
          "nonverbal_tag": null
        },
        {
          "file": "italian/random/03.mp3",
          "text": "Il lunedì è arrivato puntuale, e già questo mi sembrava provocatorio. [laughter] Forse il lunedì ha davvero una copia delle chiavi.",
          "bytes": 157004,
          "voice_profile": "auto_nonverbal",
          "instruct": null,
          "nonverbal_tag": "laughter"
        },
        {
          "file": "italian/random/04.mp3",
          "text": "Ho aperto il frigo tre volte, sperando che la pasta si organizzasse da sola.",
          "bytes": 96524,
          "voice_profile": "clear_male",
          "instruct": "male, young adult, moderate pitch",
          "nonverbal_tag": null
        },
        {
          "file": "italian/random/05.mp3",
          "text": "Ho iniziato la dieta, poi la pizza ha detto: parliamone.",
          "bytes": 71564,
          "voice_profile": "calm_female",
          "instruct": "female, middle-aged, moderate pitch",
          "nonverbal_tag": null
        },
        {
          "file": "italian/random/06.mp3",
          "text": "La sveglia suona, io rispondo con una trattativa sindacale. [sigh] La sveglia però negozia con troppa esperienza.",
          "bytes": 143564,
          "voice_profile": "auto_nonverbal",
          "instruct": null,
          "nonverbal_tag": "sigh"
        },
        {
          "file": "italian/random/07.mp3",
          "text": "Ho messo in ordine la scrivania e ho perso il mio caos di fiducia.",
          "bytes": 82604,
          "voice_profile": "low_female",
          "instruct": "female, young adult, low pitch",
          "nonverbal_tag": null
        },
        {
          "file": "italian/random/08.mp3",
          "text": "Il pane caldo non profuma, convince.",
          "bytes": 46124,
          "voice_profile": "deep_male",
          "instruct": "male, middle-aged, very low pitch",
          "nonverbal_tag": null
        },
        {
          "file": "italian/random/09.mp3",
          "text": "Il gatto mi ignora con una professionalità impressionante. [surprise-ah] Allora l'ultimo cannolo non era innocente.",
          "bytes": 140204,
          "voice_profile": "auto_nonverbal",
          "instruct": null,
          "nonverbal_tag": "surprise-ah"
        },
        {
          "file": "italian/random/10.mp3",
          "text": "Volevo fare una pausa breve, ma la pausa ha ordinato un espresso.",
          "bytes": 72044,
          "voice_profile": "balanced_female",
          "instruct": "female, young adult, moderate pitch",
          "nonverbal_tag": null
        }
      ],
      "intro": [
        {
          "file": "italian/intro/01.mp3",
          "text": "Ciao, questo è OmniVoiceTTS di Hangry Labs. Costruiamo strumenti vocali locali e facili da usare, così le persone possono creare parlato in privato, offline e nella propria lingua.",
          "bytes": 225164
        },
        {
          "file": "italian/intro/02.mp3",
          "text": "Ciao, questo è OmniVoiceTTS di Hangry Labs. Costruiamo strumenti vocali locali e facili da usare, così le persone possono creare parlato in privato, offline e nella propria lingua.",
          "bytes": 224684
        },
        {
          "file": "italian/intro/03.mp3",
          "text": "Ciao, questo è OmniVoiceTTS di Hangry Labs. Costruiamo strumenti vocali locali e facili da usare, così le persone possono creare parlato in privato, offline e nella propria lingua.",
          "bytes": 217484
        }
      ],
      "clone": [
        {
          "file": "italian/clone/01.mp3",
          "text": "Ciao, questo è OmniVoiceTTS di Hangry Labs. Costruiamo strumenti vocali locali e facili da usare, così le persone possono creare parlato in privato, offline e nella propria lingua.",
          "ref_audio": "/data/examples/original_clone.mp3",
          "bytes": 220364
        }
      ]
    },
    {
      "slug": "dutch",
      "language": "Dutch",
      "bucket": "popular_showcase",
      "intro_text": "Hallo, dit is OmniVoiceTTS van Hangry Labs. We bouwen lokale, eenvoudig te gebruiken stemtools zodat mensen privé, offline en in hun eigen taal spraak kunnen maken.",
      "random": [
        {
          "file": "dutch/random/01.mp3",
          "text": "Ik zei dat ik er over vijf minuten was; de klok bleef verdacht stil.",
          "bytes": 85004,
          "voice_profile": "bright_female",
          "instruct": "female, young adult, high pitch",
          "nonverbal_tag": null
        },
        {
          "file": "dutch/random/02.mp3",
          "text": "De koffie was zo sterk dat hij bijna mijn agenda wilde beheren.",
          "bytes": 73004,
          "voice_profile": "warm_male",
          "instruct": "male, middle-aged, low pitch",
          "nonverbal_tag": null
        },
        {
          "file": "dutch/random/03.mp3",
          "text": "Maandag kwam precies op tijd, en dat voelde onnodig efficiënt. [laughter] Misschien heeft maandag echt een reservesleutel.",
          "bytes": 156524,
          "voice_profile": "auto_nonverbal",
          "instruct": null,
          "nonverbal_tag": "laughter"
        },
        {
          "file": "dutch/random/04.mp3",
          "text": "Ik opende de koelkast drie keer, maar de kaas nam geen initiatief.",
          "bytes": 84524,
          "voice_profile": "clear_male",
          "instruct": "male, young adult, moderate pitch",
          "nonverbal_tag": null
        },
        {
          "file": "dutch/random/05.mp3",
          "text": "Ik begon met gezond eten, toen keek een stroopwafel me vriendelijk aan.",
          "bytes": 91724,
          "voice_profile": "calm_female",
          "instruct": "female, middle-aged, moderate pitch",
          "nonverbal_tag": null
        },
        {
          "file": "dutch/random/06.mp3",
          "text": "Mijn wekker rinkelt elke ochtend met veel te veel vertrouwen. [sigh] Die wekker onderhandelt helaas veel te goed.",
          "bytes": 136844,
          "voice_profile": "auto_nonverbal",
          "instruct": null,
          "nonverbal_tag": "sigh"
        },
        {
          "file": "dutch/random/07.mp3",
          "text": "Ik ruimde mijn bureau op en raakte mijn vertrouwde chaos kwijt.",
          "bytes": 82124,
          "voice_profile": "low_female",
          "instruct": "female, young adult, low pitch",
          "nonverbal_tag": null
        },
        {
          "file": "dutch/random/08.mp3",
          "text": "De regen begon, en mijn fiets deed alsof dit normaal was.",
          "bytes": 73004,
          "voice_profile": "deep_male",
          "instruct": "male, middle-aged, very low pitch",
          "nonverbal_tag": null
        },
        {
          "file": "dutch/random/09.mp3",
          "text": "Een korte pauze nemen in Nederland kan zomaar met koffie en overleg eindigen. [surprise-ah] Dan was het laatste koekje toch niet onschuldig.",
          "bytes": 169004,
          "voice_profile": "auto_nonverbal",
          "instruct": null,
          "nonverbal_tag": "surprise-ah"
        },
        {
          "file": "dutch/random/10.mp3",
          "text": "De kat keek me aan alsof hij de hypotheek betaalt.",
          "bytes": 65324,
          "voice_profile": "balanced_female",
          "instruct": "female, young adult, moderate pitch",
          "nonverbal_tag": null
        }
      ],
      "intro": [
        {
          "file": "dutch/intro/01.mp3",
          "text": "Hallo, dit is OmniVoiceTTS van Hangry Labs. We bouwen lokale, eenvoudig te gebruiken stemtools zodat mensen privé, offline en in hun eigen taal spraak kunnen maken.",
          "bytes": 200204
        },
        {
          "file": "dutch/intro/02.mp3",
          "text": "Hallo, dit is OmniVoiceTTS van Hangry Labs. We bouwen lokale, eenvoudig te gebruiken stemtools zodat mensen privé, offline en in hun eigen taal spraak kunnen maken.",
          "bytes": 194444
        },
        {
          "file": "dutch/intro/03.mp3",
          "text": "Hallo, dit is OmniVoiceTTS van Hangry Labs. We bouwen lokale, eenvoudig te gebruiken stemtools zodat mensen privé, offline en in hun eigen taal spraak kunnen maken.",
          "bytes": 199244
        }
      ],
      "clone": [
        {
          "file": "dutch/clone/01.mp3",
          "text": "Hallo, dit is OmniVoiceTTS van Hangry Labs. We bouwen lokale, eenvoudig te gebruiken stemtools zodat mensen privé, offline en in hun eigen taal spraak kunnen maken.",
          "ref_audio": "/data/examples/original_clone.mp3",
          "bytes": 196844
        }
      ]
    }
  ],
  "random_voice_showcase": {
    "format": "mp3",
    "num_step": 24,
    "profiles": [
      {
        "name": "bright_female",
        "instruct": "female, young adult, high pitch"
      },
      {
        "name": "warm_male",
        "instruct": "male, middle-aged, low pitch"
      },
      {
        "name": "whisper_female",
        "instruct": "female, young adult, moderate pitch, whisper"
      },
      {
        "name": "clear_male",
        "instruct": "male, young adult, moderate pitch"
      },
      {
        "name": "calm_female",
        "instruct": "female, middle-aged, moderate pitch"
      },
      {
        "name": "playful_male",
        "instruct": "male, young adult, high pitch"
      },
      {
        "name": "low_female",
        "instruct": "female, young adult, low pitch"
      },
      {
        "name": "deep_male",
        "instruct": "male, middle-aged, very low pitch"
      },
      {
        "name": "whisper_male",
        "instruct": "male, young adult, low pitch, whisper"
      },
      {
        "name": "balanced_female",
        "instruct": "female, young adult, moderate pitch"
      }
    ],
    "nonverbal_tags": [
      "[laughter]",
      "[sigh]",
      "[surprise-ah]"
    ],
    "notes": "Random samples rotate voice-design settings for normal text. Samples with bracket expression tags are generated without voice design/instruct because OmniVoice can produce unstable non-speech audio when bracket tags are combined with voice design. Whisper profiles are not used with bracket tags."
  }
}
;
