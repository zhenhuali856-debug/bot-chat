import request from '../utils/request'

/**
 * 创作数据看板统计 API
 */
export const getStatsOverview = (scope = 'auto') =>
  request(`/stats/overview?scope=${encodeURIComponent(scope)}`)

export const getStatsTrend = (range = 'day', scope = 'auto') =>
  request(`/stats/trend?range=${encodeURIComponent(range)}&scope=${encodeURIComponent(scope)}`)

export const getStatsWorksProgress = (scope = 'auto') =>
  request(`/stats/works-progress?scope=${encodeURIComponent(scope)}`)

export const getStatsGenreDistribution = (scope = 'auto') =>
  request(`/stats/genre-distribution?scope=${encodeURIComponent(scope)}`)

