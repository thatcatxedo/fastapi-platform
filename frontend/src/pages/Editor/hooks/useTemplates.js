import { useState, useEffect } from 'react'
import { API_URL } from '../../../App'

function useTemplates(shouldFetch = true) {
  const [templates, setTemplates] = useState([])
  const [loadingTemplates, setLoadingTemplates] = useState(false)

  useEffect(() => {
    if (shouldFetch) {
      fetchTemplates()
    }
  }, [shouldFetch])

  const fetchTemplates = async () => {
    setLoadingTemplates(true)
    try {
      const token = localStorage.getItem('token')
      const response = await fetch(`${API_URL}/api/templates`, {
        headers: { 'Authorization': `Bearer ${token}` }
      })
      if (response.ok) {
        const data = await response.json()
        setTemplates(data)
      }
    } catch (err) {
      console.error('Failed to fetch templates:', err)
    } finally {
      setLoadingTemplates(false)
    }
  }

  const createTemplate = async (templateData) => {
    const token = localStorage.getItem('token')
    const response = await fetch(`${API_URL}/api/templates`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      body: JSON.stringify(templateData)
    })
    const data = await response.json()
    if (!response.ok) {
      throw new Error(data.detail || 'Failed to create template')
    }
    // Refresh templates list
    await fetchTemplates()
    return data
  }

  const updateTemplate = async (templateId, templateData) => {
    const token = localStorage.getItem('token')
    const response = await fetch(`${API_URL}/api/templates/${templateId}`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      body: JSON.stringify(templateData)
    })
    const data = await response.json()
    if (!response.ok) {
      throw new Error(data.detail || 'Failed to update template')
    }
    // Refresh templates list
    await fetchTemplates()
    return data
  }

  const deleteTemplate = async (templateId) => {
    const token = localStorage.getItem('token')
    const response = await fetch(`${API_URL}/api/templates/${templateId}`, {
      method: 'DELETE',
      headers: { 'Authorization': `Bearer ${token}` }
    })
    if (!response.ok) {
      const data = await response.json()
      throw new Error(data.detail || 'Failed to delete template')
    }
    // Refresh templates list
    await fetchTemplates()
    return true
  }

  // Separate global and user templates
  const globalTemplates = templates.filter(t => t.is_global)
  const userTemplates = templates.filter(t => !t.is_global)

  return {
    templates,
    globalTemplates,
    userTemplates,
    loadingTemplates,
    fetchTemplates,
    createTemplate,
    updateTemplate,
    deleteTemplate
  }
}

export default useTemplates
