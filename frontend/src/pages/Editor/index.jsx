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
import MultiFileEditor from './components/MultiFileEditor'
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
    // Multi-file state
    mode,
    framework,
    setFramework,
    files,
    setFiles,
    initMultiFileMode,
    initSingleFileMode,
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
    // Validation error tracking
    errorLine,
    errorFile,
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
    // Handle multi-file templates
    if (template.mode === 'multi' && template.files) {
      initMultiFileMode(template.framework || 'fastapi')
      setFiles(template.files)
      setName(template.name)
    } else {
      initSingleFileMode()
      setCode(template.code)
      setName(template.name)
    }
    setSuccess(`Template "${template.name}" loaded. Edit the code before deployment.`)
    setError('')
    setTemplatesModalOpen(false)
  }

  const handleCodeChange = (value) => {
    setCode(value)
    clearErrorHighlight()
  }

  const handleFilesChange = (newFiles) => {
    setFiles(newFiles)
  }

  const handleModeChange = (newMode) => {
    if (newMode === 'multi') {
      initMultiFileMode(framework)
    } else {
      initSingleFileMode()
    }
  }

  const handleFrameworkChange = (newFramework) => {
    setFramework(newFramework)
    initMultiFileMode(newFramework)
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

          {/* Mode selector - only for new apps */}
          {!isEditing && (
            <div className={styles.modeSelector}>
              <label className={styles.modeSelectorLabel}>Mode:</label>
              <div className={styles.modeOptions}>
                <label className={styles.modeOption}>
                  <input
                    type="radio"
                    name="mode"
                    value="single"
                    checked={mode === 'single'}
                    onChange={() => handleModeChange('single')}
                  />
                  Single File
                </label>
                <label className={styles.modeOption}>
                  <input
                    type="radio"
                    name="mode"
                    value="multi"
                    checked={mode === 'multi'}
                    onChange={() => handleModeChange('multi')}
                  />
                  Multi-File
                </label>
              </div>

              {mode === 'multi' && (
                <div className={styles.frameworkSelector}>
                  <label className={styles.frameworkLabel}>Framework:</label>
                  <select
                    value={framework}
                    onChange={(e) => handleFrameworkChange(e.target.value)}
                    className={styles.frameworkSelect}
                  >
                    <option value="fastapi">FastAPI (API-focused)</option>
                    <option value="fasthtml">FastHTML (HTML/HTMX)</option>
                  </select>
                </div>
              )}
            </div>
          )}

          {/* Show mode badge for existing apps */}
          {isEditing && mode === 'multi' && (
            <div className={styles.modeBadge}>
              <span className={styles.modeBadgeLabel}>
                {framework === 'fasthtml' ? 'FastHTML' : 'FastAPI'} Multi-File
              </span>
            </div>
          )}
        </div>

        <EnvVarsPanel
          envVars={envVars}
          onChange={setEnvVars}
          expanded={envVarsExpanded}
          onToggleExpanded={() => setEnvVarsExpanded(!envVarsExpanded)}
        />

        {mode === 'multi' ? (
          <MultiFileEditor
            files={files}
            framework={framework}
            onChange={handleFilesChange}
            onMount={setEditorRefs}
            errorLine={errorLine}
            errorFile={errorFile}
          />
        ) : (
          <CodeEditor
            code={code}
            onChange={handleCodeChange}
            onMount={setEditorRefs}
            onDeploy={handleDeploy}
            onValidate={handleValidate}
            onSaveDraft={handleSaveDraft}
          />
        )}
      </div>

      <TemplatesModal
        isOpen={templatesModalOpen}
        onClose={() => setTemplatesModalOpen(false)}
        templates={templates}
        loading={loadingTemplates}
        onSelectTemplate={handleUseTemplate}
      />

      {isEditing && (
        <VersionHistoryModal
          isOpen={historyModalOpen}
          onClose={() => setHistoryModalOpen(false)}
          appId={appId}
          onRollbackSuccess={() => {
            setHistoryModalOpen(false)
            // Refresh the app data
            window.location.reload()
          }}
        />
      )}
    </div>
  )
}

export default EditorPage
