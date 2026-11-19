import request from '../utils/request'

/**
 * 系统健康、模型配置、助手人设与本地同步 API
 */
export const checkHealth = () => request('/health')
export const getModels = () => request('/models')

export const getBotSettings = () => request('/settings')

export const updateBotSettings = (data) =>
  request('/settings', {
    method: 'PUT',
    body: JSON.stringify(data)
  })

export const getSyncSettings = () => request('/sync/settings')

export const updateSyncSettings = (data) =>
  request('/sync/settings', {
    method: 'PUT',
    body: JSON.stringify(data)
  })

export const browseSyncFolder = (initialDir = '') =>
  request('/sync/browse', {
    method: 'POST',
    body: JSON.stringify({ initial_dir: initialDir })
  })

export const runLocalSync = (workId = null) =>
  request('/sync/run', {
    method: 'POST',
    body: JSON.stringify(workId ? { work_id: workId } : {})
  })

export const openSyncFolder = () =>
  request('/sync/open-folder', {
    method: 'POST'
  })

