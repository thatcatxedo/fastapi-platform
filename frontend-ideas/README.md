# FastAPI Platform - Frontend Mockup

A standalone frontend mockup that matches the actual frontend structure and AWS-style design. This mockup serves as a starting point for future UI ideas and design explorations.

## Features

- **Sidebar Navigation**: Matches actual frontend layout with apps list and navigation
- **Dashboard**: Table-based layout showing running apps with metrics
- **IDE Editor**: Code editor with single-file or multi-file mode toggle
- **AI Chat Assistant**: Built-in AI helper sidebar for building and improving apps
- **Database Management**: MongoDB database cards matching actual frontend structure
- **App Configuration**: Configure environment variables and database connections

## Getting Started

```bash
cd frontend-ideas
npm install
npm run dev
```

The app will open at `http://localhost:5174`

## Design Philosophy

This mockup matches the actual frontend's:
- **AWS Console Style**: Light theme, rectangular components, utilitarian design
- **Sidebar Layout**: Left sidebar with apps list and navigation (not top nav)
- **Table-Based Dashboard**: Apps displayed in tables rather than cards
- **Component Structure**: Matches actual frontend component organization

## Structure

```
frontend-ideas/
├── src/
│   ├── pages/
│   │   ├── Dashboard.jsx    # Table-based dashboard matching actual frontend
│   │   ├── Editor.jsx       # IDE with editor and sidebars
│   │   └── Databases.jsx    # MongoDB database cards
│   ├── components/
│   │   ├── Sidebar.jsx      # Sidebar navigation matching actual frontend
│   │   ├── CodeEditor.jsx   # Monaco editor component
│   │   ├── AIChat.jsx       # AI chat sidebar
│   │   └── AppConfig.jsx    # App configuration panel
│   ├── App.jsx              # Main app router with sidebar layout
│   └── index.css            # AWS-style CSS variables matching actual frontend
```

## Note

This is a **standalone mockup** with no backend dependencies. All data is mocked for demonstration purposes. The structure and styling match the actual frontend to make it easier to prototype new ideas that can be migrated to the real app.
