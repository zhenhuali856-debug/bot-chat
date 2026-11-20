import request from '../utils/request'

/**
 * 用户认证与后台权限管理 API
 */
export const login = (username, password) =>
  request('/auth/login', {
    method: 'POST',
    body: JSON.stringify({ username, password })
  })

export const logout = () =>
  request('/auth/logout', {
    method: 'POST'
  })

export const getAuthMe = () => request('/auth/me')

export const changeOwnPassword = (oldPassword, newPassword) =>
  request('/auth/password', {
    method: 'PUT',
    body: JSON.stringify({ old_password: oldPassword, new_password: newPassword })
  })

export const setAuthMode = (multiUserMode) =>
  request('/admin/auth-mode', {
    method: 'PUT',
    body: JSON.stringify({ multi_user_mode: multiUserMode })
  })

export const listAdminUsers = () => request('/admin/users')

export const createAdminUser = (data) =>
  request('/admin/users', {
    method: 'POST',
    body: JSON.stringify(data)
  })

export const updateAdminUser = (userId, data) =>
  request(`/admin/users/${userId}`, {
    method: 'PUT',
    body: JSON.stringify(data)
  })

export const resetAdminUserPassword = (userId, newPassword) =>
  updateAdminUser(userId, { new_password: newPassword })

export const deleteAdminUser = (userId, strategy = 'transfer') =>
  request(`/admin/users/${userId}?strategy=${encodeURIComponent(strategy)}`, {
    method: 'DELETE'
  })

