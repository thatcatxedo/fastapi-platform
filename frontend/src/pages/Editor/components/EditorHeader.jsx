function EditorHeader({
  isEditing,
  loading,
  validating,
  deploymentStatus,
  onValidate,
  onDeploy,
  onCancel,
  onDelete,
  onBrowseTemplates
}) {
  const isDeploying = deploymentStatus && deploymentStatus.status === 'deploying'

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
      </div>
      <div style={{ display: 'flex', gap: '0.75rem' }}>
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
