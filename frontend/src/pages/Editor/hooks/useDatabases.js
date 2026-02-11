import { useState, useEffect } from 'react'
import { API_URL } from '../../../config'

export default function useDatabases() {
  const [databases, setDatabases] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const fetchDatabases = async () => {
      try {
        const token = localStorage.getItem('token')
        const response = await fetch(`${API_URL}/api/databases`, {
          headers: { 'Authorization': `Bearer ${token}` }
        })

        if (response.ok) {
          const data = await response.json()
          setDatabases(data.databases || [])
        }
      } catch (err) {
        // Silently fail — databases are optional
      } finally {
        setLoading(false)
      }
    }

    fetchDatabases()
  }, [])

  return { databases, loading }
}
