/**
 * 前端 API 模块化请求层
 * 统一管理所有与后端的 HTTP 交互
 */

const BASE_URL = '/api'

/**
 * 通用 JSON fetch 辅助方法
 */
async function request(url, options = {}) {
  const defaultHeaders = {
    'Content-Type': 'application/json'
  }

  const response = await fetch(`${BASE_URL}${url}`, {
    ...options,
    headers: {
      ...defaultHeaders,
      ...options.headers
    }
  })

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}))
    throw new Error(errorData.detail || `请求失败 (${response.status})`)
  }

  return response.json()
}

/**
 * 全局开发助手配置 API (全局昵称与人设)
 */
export const getBotSettings = () => request('/settings')

export const updateBotSettings = (data) =>
  request('/settings', {
    method: 'PUT',
    body: JSON.stringify(data)
  })

/**
 * 系统健康与模型配置
 */
export const checkHealth = () => request('/health')
export const getModels = () => request('/models')

/**
 * 创作工作台作品管理 API (M1)
 */
export const listWorks = () => request('/works')

export const createWork = (data) =>
  request('/works', {
    method: 'POST',
    body: JSON.stringify(data)
  })

export const getWork = (id) => request(`/works/${id}`)

export const updateWork = (id, data) =>
  request(`/works/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data)
  })

export const deleteWork = (id) =>
  request(`/works/${id}`, {
    method: 'DELETE'
  })

export const getWorkSessions = (id) => request(`/works/${id}/sessions`)

/**
 * 作品正文章节管理 API (Chapters)
 */
export const listChapters = (workId = null) =>
  request(workId ? `/works/${workId}/chapters` : '/chapters')

export const createChapter = (workId, data) =>
  request(`/works/${workId}/chapters`, {
    method: 'POST',
    body: JSON.stringify(data)
  })

export const getChapter = (chapterId) =>
  request(`/chapters/${chapterId}`)

export const updateChapter = (chapterId, data) =>
  request(`/chapters/${chapterId}`, {
    method: 'PUT',
    body: JSON.stringify(data)
  })

export const deleteChapter = (chapterId) =>
  request(`/chapters/${chapterId}`, {
    method: 'DELETE'
  })

/**
 * 会话/章节管理 API
 */
export const getSessions = () => request('/sessions')

export const createSession = (data = { title: '新建对话', work_id: null }) =>
  request('/sessions', {
    method: 'POST',
    body: JSON.stringify(data)
  })

export const getSessionMessages = (sessionId) =>
  request(`/sessions/${sessionId}/messages`)

export const updateSession = (sessionId, data) =>
  request(`/sessions/${sessionId}`, {
    method: 'PATCH',
    body: JSON.stringify(data)
  })

export const deleteSession = (sessionId) =>
  request(`/sessions/${sessionId}`, {
    method: 'DELETE'
  })

export const clearSession = (sessionId) =>
  request(`/sessions/${sessionId}/clear`, {
    method: 'POST'
  })

export const deleteMessage = (sessionId, messageId, truncateAfter = false) =>
  request(`/sessions/${sessionId}/messages/${messageId}${truncateAfter ? '?truncate_after=true' : ''}`, {
    method: 'DELETE'
  })

/**
 * 对话导入与导出 API
 */
export const exportSessionJson = (sessionId) =>
  request(`/sessions/${sessionId}/export?format=json`)

export const exportSessionMarkdown = async (sessionId) => {
  const res = await fetch(`${BASE_URL}/sessions/${sessionId}/export?format=markdown`)
  if (!res.ok) throw new Error('导出 Markdown 失败')
  return res.text()
}

export const exportAllSessions = () =>
  request('/sessions/export/all')

export const importSession = (data) =>
  request('/sessions/import', {
    method: 'POST',
    body: JSON.stringify(data)
  })

/**
 * 历史对话与关键词搜索 API
 */
export const searchHistory = (keyword) =>
  request(`/search?q=${encodeURIComponent(keyword)}`)

/**
 * Markdown 提示词文件管理 API (.md Prompt Files)
 */
export const listPromptFiles = (params = {}) => {
  const query = new URLSearchParams()
  if (params.session_id) query.set('session_id', params.session_id)
  if (params.work_id) query.set('work_id', params.work_id)
  if (params.include_all) query.set('include_all', 'true')
  const qs = query.toString()
  return request(`/prompt-files${qs ? `?${qs}` : ''}`)
}

export const createPromptFile = (data) =>
  request('/prompt-files', {
    method: 'POST',
    body: JSON.stringify(data)
  })

export const getPromptFile = (id) =>
  request(`/prompt-files/${id}`)

export const updatePromptFile = (id, data) =>
  request(`/prompt-files/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data)
  })

export const deletePromptFile = (id) =>
  request(`/prompt-files/${id}`, {
    method: 'DELETE'
  })

/**
 * 核心聊天流式接口（调用原生的 fetch，返回 response）
 */
export const sendChatStream = (payload, signal) => {
  return fetch(`${BASE_URL}/chat`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(payload),
    signal
  })
}
