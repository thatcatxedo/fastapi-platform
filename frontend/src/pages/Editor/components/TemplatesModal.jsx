import { useState } from 'react'

function TemplatesModal({ isOpen, onClose, templates, loading, onSelectTemplate, onDeleteTemplate, onRefresh }) {
  const [selectedComplexity, setSelectedComplexity] = useState('all')
  const [selectedTab, setSelectedTab] = useState('all') // 'all', 'my', 'global'
  const [deletingId, setDeletingId] = useState(null)

  if (!isOpen) return null

  // Separate global and user templates
  const globalTemplates = templates.filter(t => t.is_global)
  const userTemplates = templates.filter(t => !t.is_global)

  // Filter by tab
  let tabFilteredTemplates = templates
  if (selectedTab === 'my') {
    tabFilteredTemplates = userTemplates
  } else if (selectedTab === 'global') {
    tabFilteredTemplates = globalTemplates
  }

  // Filter by complexity
  const filteredTemplates = tabFilteredTemplates.filter(t =>
    selectedComplexity === 'all' || t.complexity === selectedComplexity
  )

  const handleDelete = async (template, e) => {
    e.stopPropagation()
    if (!confirm(`Delete template "${template.name}"? This cannot be undone.`)) {
      return
    }

    setDeletingId(template.id)
    try {
      await onDeleteTemplate(template.id)
      if (onRefresh) onRefresh()
    } catch (err) {
      alert(err.message)
    } finally {
      setDeletingId(null)
    }
  }

  return (
    <div
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        background: 'rgba(0, 0, 0, 0.5)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 1000,
        padding: '1rem'
      }}
      onClick={onClose}
    >
      <div
        style={{
          background: 'var(--bg)',
          border: '1px solid var(--border)',
          borderRadius: '0.75rem',
          width: '100%',
          maxWidth: '850px',
          maxHeight: '90vh',
          display: 'flex',
          flexDirection: 'column',
          boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04)'
        }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Modal Header */}
        <div style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          padding: '1.5rem',
          borderBottom: '1px solid var(--border)'
        }}>
          <h2 style={{ margin: 0, fontSize: '1.25rem' }}>Application Templates</h2>
          <button
            onClick={onClose}
            style={{
              padding: '0.5rem',
              background: 'transparent',
              border: 'none',
              fontSize: '1.5rem',
              color: 'var(--text-muted)',
              cursor: 'pointer',
              lineHeight: 1
            }}
            title="Close"
          >
            ×
          </button>
        </div>

        {/* Modal Content */}
        <div style={{
          padding: '1.5rem',
          overflowY: 'auto',
          flex: 1
        }}>
          {/* Tabs */}
          <div style={{ marginBottom: '1rem' }}>
            <div style={{ display: 'flex', gap: '0.25rem', borderBottom: '1px solid var(--border)', paddingBottom: '0' }}>
              {[
                { key: 'all', label: 'All Templates', count: templates.length },
                { key: 'my', label: 'My Templates', count: userTemplates.length },
                { key: 'global', label: 'Global Templates', count: globalTemplates.length }
              ].map(tab => (
                <button
                  key={tab.key}
                  onClick={() => setSelectedTab(tab.key)}
                  style={{
                    padding: '0.75rem 1rem',
                    fontSize: '0.875rem',
                    background: 'transparent',
                    color: selectedTab === tab.key ? 'var(--primary)' : 'var(--text-muted)',
                    border: 'none',
                    borderBottom: selectedTab === tab.key ? '2px solid var(--primary)' : '2px solid transparent',
                    cursor: 'pointer',
                    fontWeight: selectedTab === tab.key ? '600' : '400',
                    marginBottom: '-1px'
                  }}
                >
                  {tab.label} ({tab.count})
                </button>
              ))}
            </div>
          </div>

          {/* Complexity Filter */}
          <div style={{ marginBottom: '1.5rem' }}>
            <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
              {['all', 'simple', 'medium', 'complex'].map(comp => (
                <button
                  key={comp}
                  onClick={() => setSelectedComplexity(comp)}
                  style={{
                    padding: '0.5rem 1rem',
                    fontSize: '0.875rem',
                    background: selectedComplexity === comp ? 'var(--primary)' : 'var(--bg-light)',
                    color: selectedComplexity === comp ? 'white' : 'var(--text)',
                    border: '1px solid var(--border)',
                    borderRadius: '0.5rem',
                    cursor: 'pointer',
                    textTransform: 'capitalize',
                    fontWeight: selectedComplexity === comp ? '600' : '400'
                  }}
                >
                  {comp}
                </button>
              ))}
            </div>
          </div>

          {/* Templates Grid */}
          {loading ? (
            <div style={{ textAlign: 'center', padding: '3rem', color: 'var(--text-muted)' }}>
              Loading templates...
            </div>
          ) : filteredTemplates.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '3rem', color: 'var(--text-muted)' }}>
              {selectedTab === 'my' ? (
                <>
                  <p style={{ marginBottom: '0.5rem' }}>You don't have any templates yet.</p>
                  <p style={{ fontSize: '0.875rem' }}>Use "Save as Template" in the editor to create one!</p>
                </>
              ) : (
                'No templates found'
              )}
            </div>
          ) : (
            <div style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))',
              gap: '1rem'
            }}>
              {filteredTemplates.map(template => (
                <div
                  key={template.id}
                  style={{
                    background: 'var(--bg-light)',
                    border: '1px solid var(--border)',
                    borderRadius: '0.5rem',
                    padding: '1rem',
                    display: 'flex',
                    flexDirection: 'column',
                    transition: 'all 0.2s',
                    cursor: 'pointer',
                    position: 'relative'
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.borderColor = 'var(--primary)'
                    e.currentTarget.style.transform = 'translateY(-2px)'
                    e.currentTarget.style.boxShadow = '0 4px 6px -1px rgba(0, 0, 0, 0.1)'
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.borderColor = 'var(--border)'
                    e.currentTarget.style.transform = 'translateY(0)'
                    e.currentTarget.style.boxShadow = 'none'
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start', marginBottom: '0.75rem' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flex: 1 }}>
                      <h3 style={{ margin: 0, fontSize: '1rem', fontWeight: '600' }}>{template.name}</h3>
                      {/* User template badge */}
                      {!template.is_global && (
                        <span style={{
                          fontSize: '0.65rem',
                          padding: '0.15rem 0.4rem',
                          background: 'var(--primary)',
                          color: 'white',
                          borderRadius: '0.25rem',
                          fontWeight: '500'
                        }}>
                          Mine
                        </span>
                      )}
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                      <span style={{
                        fontSize: '0.7rem',
                        padding: '0.2rem 0.5rem',
                        background: template.complexity === 'simple' ? '#10b981' : template.complexity === 'medium' ? '#f59e0b' : '#ef4444',
                        color: 'white',
                        borderRadius: '0.25rem',
                        textTransform: 'capitalize',
                        fontWeight: '500'
                      }}>
                        {template.complexity}
                      </span>
                    </div>
                  </div>

                  {/* Mode badge */}
                  {template.mode === 'multi' && (
                    <div style={{ marginBottom: '0.5rem' }}>
                      <span style={{
                        fontSize: '0.7rem',
                        padding: '0.15rem 0.4rem',
                        background: 'var(--bg-secondary)',
                        border: '1px solid var(--border)',
                        borderRadius: '0.25rem',
                        color: 'var(--text-muted)'
                      }}>
                        {template.framework === 'fasthtml' ? 'FastHTML' : 'FastAPI'} Multi-File
                      </span>
                    </div>
                  )}

                  <p style={{
                    margin: '0 0 1rem 0',
                    fontSize: '0.875rem',
                    color: 'var(--text-muted)',
                    lineHeight: '1.5',
                    flex: 1
                  }}>
                    {template.description}
                  </p>

                  {/* Tags */}
                  {template.tags && template.tags.length > 0 && (
                    <div style={{ marginBottom: '0.75rem', display: 'flex', gap: '0.25rem', flexWrap: 'wrap' }}>
                      {template.tags.slice(0, 4).map((tag, i) => (
                        <span key={i} style={{
                          fontSize: '0.65rem',
                          padding: '0.1rem 0.3rem',
                          background: 'var(--bg-secondary)',
                          borderRadius: '0.25rem',
                          color: 'var(--text-muted)'
                        }}>
                          {tag}
                        </span>
                      ))}
                      {template.tags.length > 4 && (
                        <span style={{
                          fontSize: '0.65rem',
                          padding: '0.1rem 0.3rem',
                          color: 'var(--text-muted)'
                        }}>
                          +{template.tags.length - 4}
                        </span>
                      )}
                    </div>
                  )}

                  {/* Action buttons */}
                  <div style={{ display: 'flex', gap: '0.5rem' }}>
                    <button
                      onClick={() => onSelectTemplate(template)}
                      className="btn btn-primary"
                      style={{
                        flex: 1,
                        padding: '0.625rem',
                        fontSize: '0.875rem',
                        fontWeight: '500'
                      }}
                    >
                      Load Template
                    </button>
                    {/* Delete button for user templates */}
                    {!template.is_global && onDeleteTemplate && (
                      <button
                        onClick={(e) => handleDelete(template, e)}
                        disabled={deletingId === template.id}
                        className="btn btn-danger"
                        style={{
                          padding: '0.625rem 0.75rem',
                          fontSize: '0.875rem'
                        }}
                        title="Delete template"
                      >
                        {deletingId === template.id ? '...' : '×'}
                      </button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export default TemplatesModal
