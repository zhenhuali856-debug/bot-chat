/**
 * 读取本地 Markdown / 文本文件内容
 * 自动检测 UTF-8 编码；若检测到乱码占位符 (\uFFFD)，自动回退到 GB18030 重读
 */
export const readMarkdownFile = (file) => {
  return new Promise((resolve, reject) => {
    const readWithEncoding = (encoding, onDone) => {
      const reader = new FileReader()
      reader.onload = (e) => onDone(e.target?.result ?? '')
      reader.onerror = () => reject(new Error(`读取文件 ${file.name} 失败`))
      reader.readAsText(file, encoding)
    }

    readWithEncoding('utf-8', (text) => {
      if (text.includes('\uFFFD')) {
        readWithEncoding('gb18030', (gbText) => {
          resolve(gbText)
        })
      } else {
        resolve(text)
      }
    })
  })
}

export const isMarkdownLikeFile = (fileName = '') => {
  const lower = fileName.toLowerCase()
  return lower.endsWith('.md') || lower.endsWith('.markdown') || lower.endsWith('.txt')
}

export const formatCharCount = (count = 0) => {
  if (count >= 1000) {
    return `${(count / 1000).toFixed(1)}k 字`
  }
  return `${count} 字`
}

