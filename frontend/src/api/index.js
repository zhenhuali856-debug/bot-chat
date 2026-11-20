/**
 * 前端 API 统一聚合出口
 * 按领域拆分为 auth / stats / system / works / chat 五大模块，底层复用 utils/request.js 拦截器
 */
export {
  getAuthToken,
  setAuthToken,
  clearAuthToken,
  setOnUnauthorized,
  addRequestInterceptor,
  addResponseInterceptor,
  HttpError
} from '../utils/request'

export * from './auth'
export * from './stats'
export * from './monitor'
export * from './system'
export * from './works'
export * from './chat'
