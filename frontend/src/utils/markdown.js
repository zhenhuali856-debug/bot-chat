import MarkdownIt from 'markdown-it'
import hljs from 'highlight.js'

// 配置支持代码高亮与自动断行的 Markdown 解析器
export const md = new MarkdownIt({
  html: false,
  linkify: true,
  breaks: true,
  highlight: function (str, lang) {
    if (lang && hljs.getLanguage(lang)) {
      try {
        return `<pre class="hljs"><div class="code-header"><span class="lang-tag">${lang}</span></div><code>${hljs.highlight(str, { language: lang, ignoreIllegals: true }).value}</code></pre>`
      } catch (__) {}
    }
    return `<pre class="hljs"><code>${md.utils.escapeHtml(str)}</code></pre>`
  }
})

export const renderMarkdown = (text) => {
  return md.render(text || '')
}

