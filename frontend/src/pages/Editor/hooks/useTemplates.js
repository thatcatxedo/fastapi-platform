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

  return {
    templates,
    loadingTemplates,
    fetchTemplates
  }
}

export default useTemplates
