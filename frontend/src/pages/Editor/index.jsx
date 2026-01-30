import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'

// Hooks
import useAppState from './hooks/useAppState'
import useTemplates from './hooks/useTemplates'

// Components
import EditorHeader from './components/EditorHeader'
import NotificationsPanel from './components/NotificationsPanel'
import EnvVarsPanel from './components/EnvVarsPanel'
import CodeEditor from './components/CodeEditor'
import TemplatesModal from './components/TemplatesModal'
import VersionHistoryModal from './components/VersionHistoryModal'

// Styles
import styles from './Editor.module.css'

function EditorPage({ user }) {
  const { appId } = useParams()
  const navigate = useNavigate()
  
  // App state management
  const {
    code,
    setCode,
    name,
    setName,
    envVars,
    setEnvVars,
    isEditing,
    // Draft/Version tracking
    hasUnpublishedChanges,
    hasLocalChanges,
    savingDraft,
    draftSaved,
    // UI state
    loading,
    validating,
    error,
    setError,
    success,
    setSuccess,
    validationMessage,
    deploymentStatus,
    deployingAppId,
    deployStage,
    deployDuration,
    handleValidate,
    handleDeploy,
    handleDelete,
    handleSaveDraft,
    setEditorRefs,
    clearErrorHighlight
  } = useAppState(appId)

  // Templates
  const { templates, loadingTemplates } = useTemplates(!appId)
  const [templatesModalOpen, setTemplatesModalOpen] = useState(false)
  const [envVarsExpanded, setEnvVarsExpanded] = useState(envVars.length > 0)
  
  // Version history modal
  const [historyModalOpen, setHistoryModalOpen] = useState(false)

  const handleUseTemplate = (template) => {
    setCode(template.code)
    setName(template.name)
    setSuccess(`Template "${template.name}" loaded. Edit the code before deployment.`)
    setError('')
    setTemplatesModalOpen(false)
  }

  const handleCodeChange = (value) => {
    setCode(value)
    clearErrorHighlight()
  }

  return (
    <div className={styles.container}>
      <EditorHeader
        isEditing={isEditing}
        loading={loading}
        validating={validating}
        deploymentStatus={deploymentStatus}
        hasUnpublishedChanges={hasUnpublishedChanges}
        hasLocalChanges={hasLocalChanges}
        savingDraft={savingDraft}
        draftSaved={draftSaved}
        onValidate={handleValidate}
        onDeploy={handleDeploy}
        onSaveDraft={handleSaveDraft}
        onCancel={() => navigate('/dashboard')}
        onDelete={handleDelete}
        onBrowseTemplates={() => setTemplatesModalOpen(true)}
        onOpenHistory={() => setHistoryModalOpen(true)}
      />

      <NotificationsPanel
        error={error}
        success={success}
        validationMessage={validationMessage}
        deploymentStatus={deploymentStatus}
        deployingAppId={deployingAppId}
        deployDuration={deployDuration}
        loading={loading}
      />

      <div className={styles.mainContent}>
        {/* App Name Input */}
        <div className={styles.appNameSection}>
          <div className={styles.appNameRow}>
            <label className={styles.appNameLabel}>App Name:</label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="fastapi-application"
              required
              className={styles.appNameInput}
            />
          </div>
        </div>

        <EnvVarsPanel
          envVars={envVars}
          onChange={setEnvVars}
          expanded={envVarsExpanded}
          onToggleExpanded={() => setEnvVarsExpanded(!envVarsExpanded)}
        />

        <CodeEditor
          code={code}
          onChange={handleCodeChange}
          onMount={setEditorRefs}
          onDeploy={handleDeploy}
          onValidate={handleValidate}
          onSaveDraft={handleSaveDraft}
        />
      </div>

      <TemplatesModal
        isOpen={templatesModalOpen}
        onClose={() => setTemplatesModalOpen(false)}
        templates={templates}
        loading={loadingTemplates}
        onSelectTemplate={handleUseTemplate}
      />
    </div>
  )
}

export default EditorPage
