/**
 * 统一 HTTP 请求客户端（内置请求拦截器 + 响应拦截器 + 超时控制 + 401 鉴权回调）
 */

const BASE_URL = '/api'
const AUTH_TOKEN_KEY = 'rabbit_auth_token'
const DEFAULT_TIMEOUT = 60_000

let onUnauthorizedHandler = null

export class HttpError extends Error {
  constructor(message, status = 0, data = null) {
    super(message)
    this.name = 'HttpError'
    this.status = status
    this.data = data
  }
}

export const getAuthToken = () => {
  try {
    return localStorage.getItem(AUTH_TOKEN_KEY) || ''
  } catch {
    return ''
  }
}

export const setAuthToken = (token) => {
  try {
    if (token) localStorage.setItem(AUTH_TOKEN_KEY, token)
    else localStorage.removeItem(AUTH_TOKEN_KEY)
  } catch {
    // ignore storage errors
  }
}

export const clearAuthToken = () => setAuthToken('')

export const setOnUnauthorized = (cb) => {
  onUnauthorizedHandler = typeof cb === 'function' ? cb : null
}

// ============================================================
// 拦截器注册表
// ============================================================
const requestInterceptors = []
const responseInterceptors = []

export const addRequestInterceptor = (fn) => {
  if (typeof fn === 'function') requestInterceptors.push(fn)
}

export const addResponseInterceptor = (onFulfilled, onRejected) => {
  responseInterceptors.push({ onFulfilled, onRejected })
}

// 默认请求拦截器：统一注入 JSON Header 与 Bearer Token
addRequestInterceptor((config) => {
  const token = getAuthToken()
  const headers = {
    ...(config.body && !(config.body instanceof FormData)
      ? { 'Content-Type': 'application/json' }
      : {}),
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...(config.headers || {})
  }
  return { ...config, headers }
})

// 默认响应拦截器：统一处理 401 过期、错误文案提取与解析
addResponseInterceptor(
  async ({ response, config }) => {
    if (response.status === 401 && !config.url.startsWith('/auth/login')) {
      clearAuthToken()
      if (onUnauthorizedHandler) onUnauthorizedHandler()
    }

    if (config.responseType === 'raw') {
      return response
    }

    if (!response.ok) {
      let errData = {}
      try {
        errData = await response.json()
      } catch {
        // ignore non-json body
      }
      const msg = errData.detail || errData.message || `请求失败 (${response.status})`
      throw new HttpError(msg, response.status, errData)
    }

    if (config.responseType === 'text') {
      return response.text()
    }
    return response.json()
  },
  (error) => {
    throw error
  }
)

/**
 * 发起 HTTP 请求
 * @param {string} url 相对 /api 路径
 * @param {object} options fetch 选项 + { responseType: 'json'|'text'|'raw', timeout }
 */
export async function httpRequest(url, options = {}) {
  let config = {
    url,
    method: 'GET',
    responseType: 'json',
    timeout: DEFAULT_TIMEOUT,
    ...options
  }

  for (const interceptor of requestInterceptors) {
    config = (await interceptor(config)) || config
  }

  // 若调用方未传 signal 且非流式请求，挂载超时中止控制器
  let timeoutId = null
  let internalController = null
  if (!config.signal && config.responseType !== 'raw' && config.timeout > 0) {
    internalController = new AbortController()
    config.signal = internalController.signal
    timeoutId = setTimeout(() => internalController.abort(), config.timeout)
  }

  try {
    const response = await fetch(`${BASE_URL}${config.url}`, {
      method: config.method,
      headers: config.headers,
      body: config.body,
      signal: config.signal
    })

    let result = { response, config }
    for (const { onFulfilled } of responseInterceptors) {
      if (onFulfilled) {
        result = await onFulfilled(result)
      }
    }
    return result
  } catch (err) {
    let error = err
    if (err?.name === 'AbortError' && internalController) {
      error = new HttpError('请求超时，请检查后端服务状态', 408)
    }
    for (const { onRejected } of responseInterceptors) {
      if (onRejected) {
        try {
          return await onRejected(error)
        } catch (nextErr) {
          error = nextErr
        }
      }
    }
    throw error
  } finally {
    if (timeoutId) clearTimeout(timeoutId)
  }
}

export default httpRequest

