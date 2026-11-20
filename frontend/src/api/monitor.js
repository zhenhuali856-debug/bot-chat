import request from '../utils/request'

/**
 * 运营监控中心 API
 */
export const getMonitorOverview = (range = '7d', scope = 'auto') =>
  request(`/monitor/overview?range=${encodeURIComponent(range)}&scope=${encodeURIComponent(scope)}`)

export const getMonitorModelDistribution = (range = '7d', scope = 'auto') =>
  request(`/monitor/model-distribution?range=${encodeURIComponent(range)}&scope=${encodeURIComponent(scope)}`)

export const getMonitorCalls = ({
  page = 1,
  size = 20,
  status = '',
  model = '',
  scope = 'auto'
} = {}) => {
  const params = new URLSearchParams()
  params.set('page', String(page))
  params.set('size', String(size))
  if (status && status !== 'all') {
    params.set('status', status)
  }
  if (model && model !== 'all') {
    params.set('model', model)
  }
  if (scope) {
    params.set('scope', scope)
  }
  return request(`/monitor/calls?${params.toString()}`)
}

