function EditorHeader({
  isEditing,
  loading,
  validating,
  deploymentStatus,
  hasUnpublishedChanges,
  hasLocalChanges,
  savingDraft,
  draftSaved,
  onValidate,
  onDeploy,
  onSaveDraft,
  onCancel,
  onDelete,
  onBrowseTemplates,
  onOpenHistory
}) {
  const isDeploying = deploymentStatus && deploymentStatus.status === 'deploying'

  // Determine status indicator
  const getStatusIndicator = () => {
    if (!isEditing) return null
    
    if (draftSaved) {
      return { text: 'Saved', color: 'var(--success)' }
    }
    if (hasLocalChanges) {
      return { text: 'Unsaved changes', color: 'var(--warning, #f59e0b)' }
    }
    if (hasUnpublishedChanges) {
      return { text: 'Changes not deployed', color: 'var(--warning, #f59e0b)' }
    }
    return { text: 'Up to date', color: 'var(--success)' }
  }

  const status = getStatusIndicator()

  return (
    <div style={{
      display: 'flex',
      justifyContent: 'space-between',
      alignItems: 'center',
      marginBottom: '1rem',
      flexShrink: 0
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
        <h1 style={{ margin: 0 }}>
          {isEditing ? 'Edit Application' : 'Create Application'}
        </h1>
        {!isEditing && (
          <button
            onClick={onBrowseTemplates}
            className="btn btn-secondary"
            style={{ padding: '0.5rem 1rem', fontSize: '0.875rem' }}
          >
            Browse Templates
          </button>
        )}
        {status && (
          <span style={{
            fontSize: '0.75rem',
            color: status.color,
            padding: '0.25rem 0.5rem',
            borderRadius: '0.25rem',
            background: 'var(--bg-secondary, rgba(0,0,0,0.1))'
          }}>
            {status.text}
          </span>
        )}
      </div>
      <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center' }}>
        {isEditing && (
          <>
            <button
              className="btn btn-secondary"
              onClick={onSaveDraft}
              disabled={savingDraft || loading || !hasLocalChanges}
              style={{ padding: '0.5rem 1rem', fontSize: '0.875rem' }}
              title="Save draft (Ctrl+S)"
            >
              {savingDraft ? 'Saving...' : 'Save Draft'}
            </button>
            <button
              className="btn btn-secondary"
              onClick={onOpenHistory}
              style={{ padding: '0.5rem 1rem', fontSize: '0.875rem' }}
              title="View version history"
            >
              History
            </button>
          </>
        )}
        <button
          className="btn btn-secondary"
          onClick={onValidate}
          disabled={validating || loading}
        >
          {validating ? 'Validating...' : 'Validate'}
        </button>
        <button
          className="btn btn-primary"
          onClick={onDeploy}
          disabled={loading || validating || isDeploying}
          style={{ position: 'relative' }}
        >
          {loading || isDeploying ? (
            <>
              <span style={{ marginRight: '0.5rem' }}>•••</span>
              {isEditing ? 'Updating...' : 'Deploying...'}
            </>
          ) : (
            isEditing ? 'Update Application' : 'Deploy Application'
          )}
        </button>
        <button
          className="btn btn-secondary"
          onClick={onCancel}
        >
          Cancel
        </button>
        {isEditing && (
          <button
            className="btn btn-danger"
            onClick={onDelete}
            disabled={loading || validating}
            style={{ padding: '0.5rem 1rem' }}
          >
            Delete App
          </button>
        )}
      </div>
    </div>
  )
}

export default EditorHeader
