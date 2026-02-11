import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'

// Hooks
import useAppState from './hooks/useAppState'
import useTemplates from './hooks/useTemplates'

// Components
import EditorHeader from './components/EditorHeader'
import NotificationsPanel from './components/NotificationsPanel'
import EnvVarsPanel from './components/EnvVarsPanel'
import DatabaseSelector from './components/DatabaseSelector'
import CodeEditor from './components/CodeEditor'
import MultiFileEditor from './components/MultiFileEditor'
import ChatSidebar from './components/ChatSidebar'
import TestPanel from './components/TestPanel'
import TemplatesModal from './components/TemplatesModal'
import VersionHistoryModal from './components/VersionHistoryModal'
import SaveAsTemplateModal from './components/SaveAsTemplateModal'
import WelcomeScreen from './components/WelcomeScreen'
import ConfirmModal from '../../components/ConfirmModal'
import { useToast } from '../../components/Toast'
import { useApps } from '../../context/AppsContext'

// Styles
import styles from './Editor.module.css'

function EditorPage({ user }) {
  const { appId } = useParams()
  const navigate = useNavigate()
  const toast = useToast()
  const { fetchApps } = useApps()

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
    // Database selection
    databaseId,
    setDatabaseId,
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

  // Templates - always fetch for welcome screen template count
  const { templates, loadingTemplates, fetchTemplates, deleteTemplate } = useTemplates(true)
  const [templatesModalOpen, setTemplatesModalOpen] = useState(false)
  const [saveTemplateModalOpen, setSaveTemplateModalOpen] = useState(false)
  const [envVarsExpanded, setEnvVarsExpanded] = useState(envVars.length > 0)

  // Welcome screen state - show for new apps until user makes a choice
  const [showWelcome, setShowWelcome] = useState(!appId)

  // Reset welcome screen when navigating to /editor (no appId)
  useEffect(() => {
    if (!appId) {
      setShowWelcome(true)
    }
  }, [appId])

  // Track if current template/code requires database
  const [templateRequiresDb, setTemplateRequiresDb] = useState(false)

  // Refresh apps list when deployment succeeds
  useEffect(() => {
    if (deploymentStatus?.status === 'running' && deploymentStatus?.deployment_ready) {
      fetchApps()
    }
  }, [deploymentStatus, fetchApps])

  // Version history modal
  const [historyModalOpen, setHistoryModalOpen] = useState(false)

  // Confirmation modal
  const [deleteModalOpen, setDeleteModalOpen] = useState(false)
  const [deleting, setDeleting] = useState(false)

  // Sidebar state (shared between Test and Chat panels)
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [sidebarTab, setSidebarTab] = useState('test')

  // Load sidebar state from localStorage when appId changes
  useEffect(() => {
    if (appId) {
      // Migrate from old chatSidebarOpen key if present
      const oldKey = localStorage.getItem(`chatSidebarOpen_${appId}`)
      const storedOpen = localStorage.getItem(`sidebarOpen_${appId}`)
      const storedTab = localStorage.getItem(`sidebarTab_${appId}`)

      if (storedOpen !== null) {
        setSidebarOpen(storedOpen === 'true')
      } else if (oldKey !== null) {
        setSidebarOpen(oldKey === 'true')
        setSidebarTab('chat')
        localStorage.setItem(`sidebarOpen_${appId}`, oldKey)
        localStorage.setItem(`sidebarTab_${appId}`, 'chat')
        localStorage.removeItem(`chatSidebarOpen_${appId}`)
      } else {
        setSidebarOpen(false)
      }

      if (storedTab) setSidebarTab(storedTab)
    } else {
      setSidebarOpen(false)
    }
  }, [appId])

  const toggleSidebar = (tab) => {
    if (sidebarOpen && sidebarTab === tab) {
      setSidebarOpen(false)
      if (appId) localStorage.setItem(`sidebarOpen_${appId}`, 'false')
    } else {
      setSidebarOpen(true)
      setSidebarTab(tab)
      if (appId) {
        localStorage.setItem(`sidebarOpen_${appId}`, 'true')
        localStorage.setItem(`sidebarTab_${appId}`, tab)
      }
    }
  }

  const requestDelete = () => {
    setDeleteModalOpen(true)
  }

  const confirmDelete = async () => {
    setDeleting(true)
    const deleteSuccess = await handleDelete()
    setDeleting(false)
    if (deleteSuccess) {
      setDeleteModalOpen(false)
      toast.success(`"${name}" deleted successfully`)
      await fetchApps() // Refresh sidebar apps list
      navigate('/editor') // Go to new app editor
    }
  }

  // Helper to detect if code uses MongoDB
  const detectRequiresDatabase = (template) => {
    const allCode = template.code || Object.values(template.files || {}).join('\n')
    return /MongoClient|PLATFORM_MONGO_URI|from\s+pymongo|import\s+pymongo/.test(allCode)
  }

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

    // Check if template requires database (explicit flag or code detection)
    const requiresDb = template.requires_database || detectRequiresDatabase(template)
    setTemplateRequiresDb(requiresDb)

    if (requiresDb) {
      setSuccess(`Template "${template.name}" loaded. This template uses MongoDB - a database will be auto-selected.`)
    } else {
      setSuccess(`Template "${template.name}" loaded. Edit the code before deployment.`)
    }
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

  // Welcome screen handlers (mode only; framework auto-detected by backend when multi)
  const handleSelectStarter = (selectedMode, selectedFramework) => {
    if (selectedMode === 'multi') {
      initMultiFileMode(selectedFramework || 'fastapi')
    } else {
      initSingleFileMode()
    }
    setShowWelcome(false)
  }

  const handleBrowseTemplatesFromWelcome = () => {
    setTemplatesModalOpen(true)
  }

  // Show welcome screen for new apps
  if (showWelcome && !appId) {
    return (
      <>
        <WelcomeScreen
          onSelectStarter={handleSelectStarter}
          onBrowseTemplates={handleBrowseTemplatesFromWelcome}
          templateCount={templates.length}
        />
        <TemplatesModal
          isOpen={templatesModalOpen}
          onClose={() => setTemplatesModalOpen(false)}
          templates={templates}
          loading={loadingTemplates}
          onSelectTemplate={(template) => {
            handleUseTemplate(template)
            setShowWelcome(false)
          }}
          onDeleteTemplate={deleteTemplate}
          onRefresh={fetchTemplates}
        />
      </>
    )
  }

  return (
    <div className={styles.container}>
      <EditorHeader
        isEditing={isEditing}
        loading={loading}
        deploymentStatus={deploymentStatus}
        hasUnpublishedChanges={hasUnpublishedChanges}
        hasLocalChanges={hasLocalChanges}
        savingDraft={savingDraft}
        draftSaved={draftSaved}
        onDeploy={handleDeploy}
        onSaveDraft={handleSaveDraft}
        onCancel={() => navigate('/editor')}
        onDelete={requestDelete}
        onBrowseTemplates={() => setTemplatesModalOpen(true)}
        onOpenHistory={() => setHistoryModalOpen(true)}
        onSaveAsTemplate={() => setSaveTemplateModalOpen(true)}
        sidebarOpen={sidebarOpen}
        sidebarTab={sidebarTab}
        onToggleSidebar={toggleSidebar}
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

      <div className={styles.mainWithSidebar}>
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

        {/* Database selector - only for new apps */}
        {!isEditing && (
          <DatabaseSelector
            value={databaseId}
            onChange={setDatabaseId}
            disabled={loading}
            autoSelectDefault={templateRequiresDb}
          />
        )}

        {/* Warning banner when code uses MongoDB but no database is selected */}
        {!isEditing && !databaseId && (
          (() => {
            const allCode = mode === 'multi' ? Object.values(files).join('\n') : code
            const usesMongo = /MongoClient|PLATFORM_MONGO_URI|from\s+pymongo|import\s+pymongo/.test(allCode)
            return usesMongo ? (
              <div className={styles.warningBanner}>
                <span>This code uses MongoDB but no database is connected.</span>
                <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                  Select a database above, or the default database will be used.
                </span>
              </div>
            ) : null
          })()
        )}

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
            onSaveDraft={handleSaveDraft}
          />
        )}
        </div>

        {/* Sidebar: Test or Chat */}
        {appId && sidebarOpen && (
          sidebarTab === 'test' ? (
            <TestPanel
              appId={appId}
              deploymentStatus={deploymentStatus}
              onClose={() => { setSidebarOpen(false); if (appId) localStorage.setItem(`sidebarOpen_${appId}`, 'false') }}
            />
          ) : (
            <ChatSidebar
              appId={appId}
              onClose={() => { setSidebarOpen(false); if (appId) localStorage.setItem(`sidebarOpen_${appId}`, 'false') }}
            />
          )
        )}
      </div>

      <TemplatesModal
        isOpen={templatesModalOpen}
        onClose={() => setTemplatesModalOpen(false)}
        templates={templates}
        loading={loadingTemplates}
        onSelectTemplate={handleUseTemplate}
        onDeleteTemplate={deleteTemplate}
        onRefresh={fetchTemplates}
      />

      <SaveAsTemplateModal
        isOpen={saveTemplateModalOpen}
        onClose={() => setSaveTemplateModalOpen(false)}
        code={code}
        files={files}
        mode={mode}
        framework={framework}
        onSuccess={(template) => {
          setSuccess(`Template "${template.name}" saved successfully!`)
          fetchTemplates()
        }}
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

      <ConfirmModal
        isOpen={deleteModalOpen}
        title="Delete Application"
        message={`Are you sure you want to delete "${name.trim() || 'this app'}"? This action cannot be undone.`}
        confirmText="Delete"
        confirmStyle="danger"
        onConfirm={confirmDelete}
        onCancel={() => setDeleteModalOpen(false)}
        loading={deleting}
      />
    </div>
  )
}

export default EditorPage
