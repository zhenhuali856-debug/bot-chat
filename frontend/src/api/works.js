import request from '../utils/request'

/**
 * 作品、章节、版本、角色卡、素材库与 M3 创作工具 API
 */
export const listWorks = () => request('/works')

export const createWork = (data) =>
  request('/works', {
    method: 'POST',
    body: JSON.stringify(data)
  })

export const getWork = (workId) => request(`/works/${workId}`)

export const updateWork = (workId, data) =>
  request(`/works/${workId}`, {
    method: 'PUT',
    body: JSON.stringify(data)
  })

export const deleteWork = (workId) =>
  request(`/works/${workId}`, {
    method: 'DELETE'
  })

export const getWorkSessions = (workId) => request(`/works/${workId}/sessions`)

// 正文章节
export const listChapters = (workId = null) =>
  request(workId ? `/chapters?work_id=${encodeURIComponent(workId)}` : '/chapters')

export const createChapter = (workId, data) =>
  request(`/works/${workId}/chapters`, {
    method: 'POST',
    body: JSON.stringify(data)
  })

export const getChapter = (chapterId) => request(`/chapters/${chapterId}`)

export const updateChapter = (chapterId, data) =>
  request(`/chapters/${chapterId}`, {
    method: 'PUT',
    body: JSON.stringify(data)
  })

export const deleteChapter = (chapterId) =>
  request(`/chapters/${chapterId}`, {
    method: 'DELETE'
  })

// M3c 章节版本对比
export const listChapterVersions = (chapterId) =>
  request(`/chapters/${chapterId}/versions`)

export const createChapterVersion = (chapterId, data = {}) =>
  request(`/chapters/${chapterId}/versions`, {
    method: 'POST',
    body: JSON.stringify(data)
  })

// M2a 角色卡
export const listCharacters = (workId) => request(`/works/${workId}/characters`)

export const createCharacter = (workId, data) =>
  request(`/works/${workId}/characters`, {
    method: 'POST',
    body: JSON.stringify(data)
  })

export const getCharacter = (charId) => request(`/characters/${charId}`)

export const updateCharacter = (charId, data) =>
  request(`/characters/${charId}`, {
    method: 'PUT',
    body: JSON.stringify(data)
  })

export const deleteCharacter = (charId) =>
  request(`/characters/${charId}`, {
    method: 'DELETE'
  })

// M2b 素材库
export const listMaterials = (workId, type = '') => {
  const qs = type && type !== '全部' ? `?type=${encodeURIComponent(type)}` : ''
  return request(`/works/${workId}/materials${qs}`)
}

export const createMaterial = (workId, data) =>
  request(`/works/${workId}/materials`, {
    method: 'POST',
    body: JSON.stringify(data)
  })

export const getMaterial = (matId) => request(`/materials/${matId}`)

export const updateMaterial = (matId, data) =>
  request(`/materials/${matId}`, {
    method: 'PUT',
    body: JSON.stringify(data)
  })

export const deleteMaterial = (matId) =>
  request(`/materials/${matId}`, {
    method: 'DELETE'
  })

// M3 体裁模板 / 整书导出 / AI 拆章
export const getGenreTemplates = () => request('/genre-templates')

export const exportWorkBook = (workId, format = 'md') =>
  request(`/works/${workId}/export?format=${encodeURIComponent(format)}`, {
    responseType: 'text'
  })

export const splitOutline = (workId, payload) =>
  request(`/works/${workId}/split-outline`, {
    method: 'POST',
    body: JSON.stringify(payload)
  })

export const batchCreateChapters = (workId, chapters) =>
  request(`/works/${workId}/chapters/batch`, {
    method: 'POST',
    body: JSON.stringify({ chapters })
  })

