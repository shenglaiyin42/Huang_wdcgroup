# Huang WDC Group Website

Huang WDC Group 的中英文 Quarto 网站，默认显示中文。

在 `website/` 中运行 `quarto render` 或 `quarto preview --no-browser --port 4876`。构建后的每页同时包含两种语言，右上角的“中文 / EN”按钮切换显示，并记住访问者的选择；`?lang=zh` 和 `?lang=en` 可直接打开指定语言。

中文内容保存在 `website/*.qmd`，对应英文保存在 `website/assets/i18n/en.json`。修改中文后需同步英文条目，构建会检查翻译是否缺失。`website/scripts/build-bilingual.py` 使用 Python 标准库，在 Quarto 构建后自动运行，无额外依赖。生成的 `_site/` 不需要手动修改。
