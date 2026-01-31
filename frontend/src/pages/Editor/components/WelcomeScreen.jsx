import styles from '../Editor.module.css'

function StarterCard({ title, subtitle, description, icon, onClick }) {
  return (
    <button className={styles.starterCard} onClick={onClick}>
      <div className={styles.starterCardIcon}>{icon}</div>
      <div className={styles.starterCardContent}>
        <h3 className={styles.starterCardTitle}>{title}</h3>
        <p className={styles.starterCardSubtitle}>{subtitle}</p>
        {description && (
          <p className={styles.starterCardDescription}>{description}</p>
        )}
      </div>
    </button>
  )
}

function WelcomeScreen({ onSelectStarter, onBrowseTemplates, templateCount }) {
  return (
    <div className={styles.welcomeScreen}>
      <div className={styles.welcomeHeader}>
        <h1 className={styles.welcomeTitle}>Create a New Application</h1>
        <p className={styles.welcomeSubtitle}>Choose how you want to start:</p>
      </div>

      <div className={styles.starterCards}>
        <StarterCard
          title="Single File"
          subtitle="Simple API in one file"
          description="Best for beginners and quick experiments"
          icon="📄"
          onClick={() => onSelectStarter('single', 'fastapi')}
        />
        <StarterCard
          title="Multi-File FastAPI"
          subtitle="Organized project structure"
          description="Routes, models, and services in separate files"
          icon="📁"
          onClick={() => onSelectStarter('multi', 'fastapi')}
        />
        <StarterCard
          title="Multi-File FastHTML"
          subtitle="HTML + HTMX components"
          description="Build interactive web UIs with Python"
          icon="🌐"
          onClick={() => onSelectStarter('multi', 'fasthtml')}
        />
      </div>

      <div className={styles.welcomeDivider}>
        <span>or</span>
      </div>

      <button className={styles.browseTemplatesButton} onClick={onBrowseTemplates}>
        <div className={styles.browseTemplatesContent}>
          <span className={styles.browseTemplatesIcon}>📚</span>
          <div className={styles.browseTemplatesText}>
            <span className={styles.browseTemplatesTitle}>Browse Template Gallery</span>
            <span className={styles.browseTemplatesSubtitle}>
              {templateCount > 0 ? `${templateCount}+ ready-to-use templates` : 'Explore ready-to-use templates'}
            </span>
          </div>
        </div>
        <span className={styles.browseTemplatesArrow}>→</span>
      </button>
    </div>
  )
}

export default WelcomeScreen
