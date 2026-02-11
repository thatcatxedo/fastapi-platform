// Mock data generators for enterprise features

// Generate time-series data for charts
export const generateTimeSeries = (hours = 24, min = 0, max = 1000) => {
  const now = Date.now()
  const data = []
  for (let i = hours; i >= 0; i--) {
    const timestamp = now - (i * 60 * 60 * 1000)
    const value = Math.floor(Math.random() * (max - min) + min)
    data.push({ timestamp, value })
  }
  return data
}

// Generate request metrics
export const generateRequestMetrics = (hours = 24) => {
  return generateTimeSeries(hours, 100, 5000)
}

// Generate error metrics
export const generateErrorMetrics = (hours = 24) => {
  return generateTimeSeries(hours, 0, 50)
}

// Generate response time metrics
export const generateResponseTimeMetrics = (hours = 24) => {
  return generateTimeSeries(hours, 50, 500)
}

// Mock team members
export const mockTeamMembers = [
  {
    id: '1',
    username: 'alice',
    email: 'alice@example.com',
    role: 'owner',
    joinedAt: '2024-01-15',
    lastActive: '2 hours ago'
  },
  {
    id: '2',
    username: 'bob',
    email: 'bob@example.com',
    role: 'admin',
    joinedAt: '2024-01-20',
    lastActive: '5 minutes ago'
  },
  {
    id: '3',
    username: 'charlie',
    email: 'charlie@example.com',
    role: 'developer',
    joinedAt: '2024-02-01',
    lastActive: '1 day ago'
  },
  {
    id: '4',
    username: 'diana',
    email: 'diana@example.com',
    role: 'viewer',
    joinedAt: '2024-02-05',
    lastActive: '3 days ago'
  }
]

// Mock activity log
export const generateActivityLog = (count = 50) => {
  const actions = ['deployed', 'updated', 'created', 'deleted', 'configured', 'rolled_back']
  const users = ['alice', 'bob', 'charlie', 'diana']
  const apps = ['todo-api', 'weather-dashboard', 'kanban-board', 'analytics-service']
  
  const activities = []
  const now = Date.now()
  
  for (let i = 0; i < count; i++) {
    const timestamp = now - (Math.random() * 7 * 24 * 60 * 60 * 1000) // Last 7 days
    activities.push({
      id: `activity-${i}`,
      timestamp,
      user: users[Math.floor(Math.random() * users.length)],
      action: actions[Math.floor(Math.random() * actions.length)],
      resource: apps[Math.floor(Math.random() * apps.length)],
      details: `App ${actions[Math.floor(Math.random() * actions.length)]}`
    })
  }
  
  return activities.sort((a, b) => b.timestamp - a.timestamp)
}

// Mock deployments
export const generateDeployments = (count = 20) => {
  const statuses = ['success', 'failed', 'deploying', 'rolled_back']
  const branches = ['main', 'develop', 'feature/auth', 'feature/api', 'hotfix/bug']
  const apps = ['todo-api', 'weather-dashboard', 'kanban-board']
  
  const deployments = []
  const now = Date.now()
  
  for (let i = 0; i < count; i++) {
    const timestamp = now - (i * 2 * 60 * 60 * 1000) // Every 2 hours
    deployments.push({
      id: `deploy-${i}`,
      appId: apps[Math.floor(Math.random() * apps.length)],
      appName: apps[Math.floor(Math.random() * apps.length)],
      branch: branches[Math.floor(Math.random() * branches.length)],
      commit: `abc${Math.random().toString(36).substr(2, 7)}`,
      status: statuses[Math.floor(Math.random() * statuses.length)],
      deployedBy: 'bob',
      timestamp,
      duration: Math.floor(Math.random() * 300) + 30, // 30-330 seconds
      url: `https://app-${i}.gatorlunch.com`
    })
  }
  
  return deployments.sort((a, b) => b.timestamp - a.timestamp)
}

// Mock API keys
export const mockApiKeys = [
  {
    id: 'key-1',
    name: 'Production API Key',
    key: 'fp_live_abc123...xyz789',
    created: '2024-01-15',
    lastUsed: '2 hours ago',
    scopes: ['read:apps', 'write:apps', 'read:metrics'],
    expiresAt: null
  },
  {
    id: 'key-2',
    name: 'CI/CD Key',
    key: 'fp_test_def456...uvw012',
    created: '2024-01-20',
    lastUsed: '1 day ago',
    scopes: ['read:apps', 'write:deployments'],
    expiresAt: '2024-12-31'
  },
  {
    id: 'key-3',
    name: 'Monitoring Key',
    key: 'fp_mon_ghi789...rst345',
    created: '2024-02-01',
    lastUsed: '5 minutes ago',
    scopes: ['read:metrics', 'read:logs'],
    expiresAt: null
  }
]

// Mock secrets
export const mockSecrets = [
  {
    id: 'secret-1',
    name: 'DATABASE_URL',
    encrypted: true,
    lastUpdated: '2024-01-15',
    updatedBy: 'alice',
    apps: ['todo-api', 'weather-dashboard']
  },
  {
    id: 'secret-2',
    name: 'API_KEY',
    encrypted: true,
    lastUpdated: '2024-01-20',
    updatedBy: 'bob',
    apps: ['kanban-board']
  },
  {
    id: 'secret-3',
    name: 'STRIPE_SECRET',
    encrypted: true,
    lastUpdated: '2024-02-01',
    updatedBy: 'alice',
    apps: ['analytics-service']
  }
]

// Mock security scan results
export const mockSecurityScan = {
  lastScanned: Date.now() - (2 * 60 * 60 * 1000), // 2 hours ago
  vulnerabilities: {
    critical: 2,
    high: 5,
    medium: 12,
    low: 8
  },
  dependencies: {
    total: 145,
    outdated: 23,
    vulnerable: 15
  },
  issues: [
    {
      id: 'vuln-1',
      severity: 'critical',
      package: 'requests@2.25.1',
      cve: 'CVE-2024-1234',
      description: 'Remote code execution vulnerability',
      fixedIn: '2.28.0'
    },
    {
      id: 'vuln-2',
      severity: 'high',
      package: 'urllib3@1.26.5',
      cve: 'CVE-2024-5678',
      description: 'HTTP header injection',
      fixedIn: '1.26.12'
    }
  ]
}

// Mock analytics data
export const generateAnalytics = () => {
  return {
    requests: {
      total: 1250000,
      last24h: 45000,
      last7d: 280000,
      last30d: 1200000
    },
    errors: {
      total: 1250,
      last24h: 45,
      last7d: 280,
      last30d: 1200
    },
    computeTime: {
      total: 1250, // hours
      last24h: 45,
      last7d: 280,
      last30d: 1200
    },
    topEndpoints: [
      { path: '/api/items', requests: 45000, errors: 12, avgTime: 45 },
      { path: '/api/users', requests: 32000, errors: 8, avgTime: 38 },
      { path: '/api/health', requests: 28000, errors: 0, avgTime: 5 },
      { path: '/api/data', requests: 15000, errors: 25, avgTime: 120 }
    ]
  }
}

// Mock test results
export const mockTestResults = {
  lastRun: Date.now() - (30 * 60 * 1000), // 30 minutes ago
  total: 45,
  passed: 42,
  failed: 2,
  skipped: 1,
  duration: 12.5, // seconds
  coverage: 87.5,
  tests: [
    { name: 'test_get_items', status: 'passed', duration: 0.12 },
    { name: 'test_create_item', status: 'passed', duration: 0.15 },
    { name: 'test_delete_item', status: 'failed', duration: 0.08, error: 'AssertionError: Expected 200, got 404' },
    { name: 'test_update_item', status: 'passed', duration: 0.10 },
    { name: 'test_validation', status: 'skipped', duration: 0 }
  ]
}

// Mock performance insights
export const mockPerformanceInsights = {
  recommendations: [
    {
      type: 'optimization',
      severity: 'high',
      title: 'Slow endpoint detected',
      description: '/api/data has average response time of 120ms. Consider caching.',
      impact: 'Could reduce response time by 60%'
    },
    {
      type: 'scaling',
      severity: 'medium',
      title: 'High error rate',
      description: '/api/items has 12 errors in last 24h. Review error logs.',
      impact: 'May affect user experience'
    }
  ],
  trends: {
    responseTime: { current: 45, previous: 52, change: -13.5 },
    errorRate: { current: 0.1, previous: 0.15, change: -33.3 },
    throughput: { current: 1875, previous: 1650, change: 13.6 }
  }
}
