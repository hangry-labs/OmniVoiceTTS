---
layout: default
title: Voice examples
permalink: /examples/
sidebar: false
wide: true
content_class: gallery-content omni-gallery page-shell
stylesheets:
  - /examples/styles.css
  - /examples/website.css
scripts:
  - /examples/i18n.js
  - /examples/voices.js
  - /examples/player.js
  - /examples/website.js
---
{% capture gallery %}{% include_relative index.html %}{% endcapture %}
{{ gallery | split: '<main class="page-shell">' | last | split: '</main>' | first | strip }}
