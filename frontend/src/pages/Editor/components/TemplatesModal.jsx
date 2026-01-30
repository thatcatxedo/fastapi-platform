import { useState } from 'react'

function TemplatesModal({ isOpen, onClose, templates, loading, onSelectTemplate }) {
  const [selectedComplexity, setSelectedComplexity] = useState('all')

  if (!isOpen) return null

  const filteredTemplates = templates.filter(t =>
    selectedComplexity === 'all' || t.complexity === selectedComplexity
  )

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
          maxWidth: '800px',
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
              No templates found
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
                    cursor: 'pointer'
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
                    <h3 style={{ margin: 0, fontSize: '1rem', fontWeight: '600' }}>{template.name}</h3>
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
                  <p style={{
                    margin: '0 0 1rem 0',
                    fontSize: '0.875rem',
                    color: 'var(--text-muted)',
                    lineHeight: '1.5',
                    flex: 1
                  }}>
                    {template.description}
                  </p>
                  <button
                    onClick={() => onSelectTemplate(template)}
                    className="btn btn-primary"
                    style={{
                      width: '100%',
                      padding: '0.625rem',
                      fontSize: '0.875rem',
                      fontWeight: '500'
                    }}
                  >
                    Load Template
                  </button>
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
