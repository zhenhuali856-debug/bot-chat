import request from '../utils/request'

/**
 * 会话、消息、搜索、Prompt 文件与 SSE 流式对话 API
 */
export const getSessions = () => request('/sessions')

export const createSession = (data = { title: '新建对话', work_id: null }) =>
  request('/sessions', {
    method: 'POST',
    body: JSON.stringify(data)
  })

export const getSessionMessages = (sessionId) =>
  request(`/sessions/${sessionId}/messages`)

export const getSessionContinuity = (sessionId) =>
  request(`/sessions/${sessionId}/continuity`)

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

export const clearSessionMessages = clearSession

export const deleteMessage = (sessionId, messageId, truncateAfter = false) =>
  request(
    `/sessions/${sessionId}/messages/${messageId}?truncate_after=${truncateAfter}`,
    {
      method: 'DELETE'
    }
  )

export const exportSession = (sessionId, format = 'json') =>
  request(`/sessions/${sessionId}/export?format=${format}`, {
    responseType: format === 'markdown' ? 'text' : 'json'
  })

export const exportSessionJson = (sessionId) => exportSession(sessionId, 'json')

export const exportSessionMarkdown = (sessionId) => exportSession(sessionId, 'markdown')

export const exportAllSessions = () => request('/sessions/export/all')

export const importSession = (data) =>
  request('/sessions/import', {
    method: 'POST',
    body: JSON.stringify(data)
  })

export const searchHistory = (keyword) =>
  request(`/search?q=${encodeURIComponent(keyword)}`)

export const searchGlobal = (keyword, limit = 50) =>
  request(`/search/global?q=${encodeURIComponent(keyword)}&limit=${limit}`)

export const autoGenerateSessionTitle = (sessionId) =>
  request(`/sessions/${sessionId}/auto-title`, {
    method: 'POST'
  })

// Markdown 提示词文件
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

export const getPromptFile = (id) => request(`/prompt-files/${id}`)

export const updatePromptFile = (id, data) =>
  request(`/prompt-files/${id}`, {
    method: 'PUT',
    body: JSON.stringify(data)
  })

export const deletePromptFile = (id) =>
  request(`/prompt-files/${id}`, {
    method: 'DELETE'
  })

// SSE 核心流式对话接口（走统一请求拦截器注入 Token，返回原生 Response 流）
export const sendChatStream = (payload, signal) =>
  request('/chat', {
    method: 'POST',
    body: JSON.stringify(payload),
    signal,
    responseType: 'raw'
  })
