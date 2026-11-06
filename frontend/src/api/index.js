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
 * 会话管理 API
 */
export const getSessions = () => request('/sessions')

export const createSession = (data = { title: '新建对话' }) =>
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
