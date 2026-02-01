import DropdownMenu from '../../../components/DropdownMenu'

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
  onOpenHistory,
  onSaveAsTemplate
}) {
  const isDeploying = deploymentStatus && deploymentStatus.status === 'deploying'

  // Determine status indicator
  const getStatusIndicator = () => {
    if (!isEditing) return null

    if (draftSaved) {
      return { text: 'Saved', type: 'saved' }
    }
    if (hasLocalChanges) {
      return { text: 'Unsaved changes', type: 'unsaved' }
    }
    if (hasUnpublishedChanges) {
      return { text: 'Changes not deployed', type: 'unsaved' }
    }
    return { text: 'Up to date', type: 'saved' }
  }

  const status = getStatusIndicator()

  // Build dropdown menu items
  const dropdownItems = [
    {
      label: isEditing ? 'Load Template' : 'Browse Templates',
      onClick: onBrowseTemplates
    },
    {
      label: 'Save as Template',
      onClick: onSaveAsTemplate
    },
    {
      label: 'Version History',
      onClick: onOpenHistory,
      show: isEditing
    },
    {
      type: 'separator',
      show: isEditing
    },
    {
      label: 'Delete App',
      onClick: onDelete,
      danger: true,
      show: isEditing,
      disabled: loading || validating
    }
  ]

  return (
    <div className="editor-header">
      <div className="editor-header-left">
        <h1>{isEditing ? 'Edit Application' : 'Create Application'}</h1>
        {status && (
          <div className={`editor-status editor-status-${status.type}`}>
            <span className="editor-status-dot" />
            {status.text}
          </div>
        )}
      </div>
      <div className="editor-header-right">
        {isEditing && (
          <button
            className="btn btn-secondary"
            onClick={onSaveDraft}
            disabled={savingDraft || loading || !hasLocalChanges}
            title="Save draft (Ctrl+S)"
          >
            {savingDraft ? 'Saving...' : 'Save Draft'}
          </button>
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
        >
          {loading || isDeploying ? (
            <>
              <span style={{ marginRight: '0.5rem' }}>•••</span>
              {isEditing ? 'Updating...' : 'Deploying...'}
            </>
          ) : (
            isEditing ? 'Update' : 'Deploy'
          )}
        </button>
        <DropdownMenu
          trigger={<>More <span style={{ fontSize: '0.7rem' }}>▼</span></>}
          items={dropdownItems}
        />
        <button
          className="btn btn-secondary"
          onClick={onCancel}
        >
          ← Back
        </button>
      </div>
    </div>
  )
}

export default EditorHeader
