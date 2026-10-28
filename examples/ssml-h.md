---
layout: default
title: SSML-H conversations
permalink: /examples/ssml-h.html
sidebar: false
wide: true
content_class: ssml-content ssml-page
stylesheets:
  - /examples/ssml-h.css
  - /examples/website.css
scripts:
  - /examples/ssml-h.js
---
{% capture showcase %}{% include_relative ssml-h.html %}{% endcapture %}
<div class="page-shell">
{{ showcase | split: '<main class="page-shell">' | last | split: '</main>' | first | strip }}
</div>
<div class="toast" role="status" aria-live="polite" hidden></div>
